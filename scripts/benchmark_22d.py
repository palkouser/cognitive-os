"""Sprint 22D W0. The readings §2.2 freezes, and the runner that executes them.

This module is the sprint's substance. Every later record — the pre-registration, the
fixture-scale slice, W2's baselines, W3's four measured exits — imports its definitions from
here and hashes them from here rather than retyping them (22B W1-F2: pin the readings, not
the driver's bytes), so a driver that drifts drifts the sealed records too and `--check`
catches it.

Five exit sentences come from `execution-sprint-allocation.md` verbatim and this module moves
none of them. What it fixes is the *reading* of each, before any measured number exists,
because a sprint whose numbers arrive before its definitions can always find a definition its
numbers meet.

The one structural decision worth stating here. **"No large external LLM is called" is a
construction, never an audit.** The benchmark run composes a provider registry into which no
network adapter was ever built; an attempted external call raises and fails the run. There is
no log for anybody to inspect afterwards, and no place for a call to hide in one.

    UV_CACHE_DIR=.cache/uv uv run python scripts/benchmark_22d.py --slice
    UV_CACHE_DIR=.cache/uv uv run python scripts/benchmark_22d.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import inspect
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from cognitive_os.config.provider_config import (  # noqa: E402
    ClaudeCodeProviderConfig,
    CodexCliProviderConfig,
    MiniMaxProviderConfig,
    OpenRouterProviderConfig,
)
from cognitive_os.domain.benchmarks import (  # noqa: E402
    BenchmarkDomain,
    BenchmarkResourceBudget,
)
from cognitive_os.domain.enums import VerifierStatus  # noqa: E402
from cognitive_os.domain.provider import ProviderKind  # noqa: E402
from cognitive_os.domain.verifiers import (  # noqa: E402
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.verification.factory import build_builtin_registry  # noqa: E402

#: Every timestamp this module writes into a rebuildable structure. A `--check` that
#: re-derived "now" would rebuild a different record every run (22C W1-F1).
SLICE_TIME = datetime(2026, 8, 15, 0, 0, 0, tzinfo=UTC)

NAMESPACE = UUID("22d0da11-0000-4000-8000-000000000000")


# ---------------------------------------------------------------------------
# §2.2(a). What "large external LLM" names, enumerated rather than described
# ---------------------------------------------------------------------------

#: **The enumeration, by name.** 22A W4-F1's rule is that a coverage word is an enumeration
#: with a test asserting it, so this is not a description of "network providers" — it is the
#: complete list of adapters `providers/factory.py` can construct that reach outside this
#: host, derived from the discriminated configuration union rather than retyped from it.
#: `tests/.../test_external_provider_enumeration.py` fails if the union grows a member this
#: tuple does not name, which is the only way the boundary stays true after W0.
EXTERNAL_PROVIDER_CONFIGS = (
    MiniMaxProviderConfig,
    OpenRouterProviderConfig,
    ClaudeCodeProviderConfig,
    CodexCliProviderConfig,
)

EXTERNAL_PROVIDER_IDS = ("claude-code", "codex-cli", "minimax", "openrouter")

#: Out of scope by name, so the boundary cannot be argued about once a number exists. These
#: run on this host today and are not "large external LLMs" in any reading of the exit; they
#: are named here rather than left to inference.
LOCAL_COMPONENTS_OUT_OF_SCOPE = (
    "embedding model (local, already resident)",
    "reranking model (local, already resident)",
    "the deterministic verifier registry",
    "the local model under measurement — its calls are counted and are not external calls",
)

#: The provider kinds a local microbenchmark run may register. `LOCAL_API` is the model under
#: measurement; `MOCK` is the fixture-scale stand-in the §3.1 slice uses before any weights
#: exist. Everything else is a construction error inside a benchmark run.
PERMITTED_BENCHMARK_PROVIDER_KINDS = (ProviderKind.LOCAL_API, ProviderKind.MOCK)


class ExternalProviderRefused(RuntimeError):
    """Raised where an external adapter would have been constructed. §2.2(a).

    This is the whole of the first exit criterion. It is an exception and not a counter
    because a counter is something a later reader has to remember to read, and this has to
    fail the run.
    """


def refuse_external_providers(provider_ids: Iterable[str]) -> None:
    """Fail closed before a benchmark run, on the enumeration rather than on a guess."""
    offending = sorted(set(provider_ids) & set(EXTERNAL_PROVIDER_IDS))
    if offending:
        raise ExternalProviderRefused(
            f"external providers are not constructible during the local microbenchmark: {offending}"
        )


def local_benchmark_budget() -> BenchmarkResourceBudget:
    """The budget half of §2.2(a): zero external calls, expressed where a run reads it."""
    return BenchmarkResourceBudget(
        maximum_elapsed_seconds=36_000,
        maximum_provider_calls=0,
        maximum_tool_calls=0,
        maximum_input_tokens=0,
        maximum_output_tokens=0,
        maximum_cost_units=0,
        maximum_artifact_bytes=64 * 1024 * 1024,
    )


# ---------------------------------------------------------------------------
# §2.2(b). The four arms, and what "verified" means
# ---------------------------------------------------------------------------

#: The four arms named in the allocation. `retrieval_only` is the comparator the ten-point
#: margin reads against, and it is deliberately model-free: it returns what the index found
#: and nothing interprets it. That is what makes "the acquired layer contributed something"
#: a decidable claim rather than a description of a better prompt.
ARMS = ("no_memory", "retrieval_only", "external_teacher", "local_model")

#: The comparison the ten-point margin reads, both sides measured in this sprint.
MARGIN_COMPARISON = ("local_model", "retrieval_only")

#: **W3's workload, and deliberately not a fifth arm.** §2.2 freezes `arms` as four and the
#: pre-registration hashes that reading, so the composition §2.2(c) measures the reduction on
#: is named separately rather than appended. It is scored by *this* runner all the same: a
#: second runner would be a second set of accounting, and the whole point of the 25 % is that
#: both sides of it were computed by one definition.
MIXED_WORKLOAD = "mixed_workload"

#: Who may reach a network at all. The local microbenchmark's no-external-call reading is a
#: construction (§2.2a), and the construction is this tuple: an arm outside it that records a
#: provider call fails the run rather than leaving a line in a log someone checks afterwards.
EXTERNAL_CALLS_PERMITTED = ("external_teacher", MIXED_WORKLOAD)

#: The absolute verified-success floor, and the margin over the retrieval-only arm. The
#: allocation's numbers, unmoved.
MINIMUM_LOCAL_SUCCESS_PERCENT = 70.0
MINIMUM_MARGIN_POINTS = 10.0

#: §2.2(c). The maximum tolerated *absolute* drop in verified success against the
#: external-teacher arm, fixed here before any arm runs. A mixed workload that beats the cost
#: target while falling outside this is a failed exit, not a trade-off to narrate.
NON_INFERIORITY_MARGIN_POINTS = 3.0

#: §2.2(c). The reduction, read on two quantities separately so it cannot be claimed on
#: whichever moved further.
MINIMUM_COST_REDUCTION_PERCENT = 25.0
COST_REDUCTION_QUANTITIES = ("external_provider_calls", "accounted_cost_units")

#: The verifiers the hundred may use. Every one is a *registered* verifier from the released
#: builtin registry and every one is deterministic: a model judging a model is the failure
#: mode this programme exists to avoid, so no LLM appears anywhere in the decision path.
BENCHMARK_VERIFIER_IDS = (
    "generic.exact",
    "mathematics.numeric",
    "physics.dimension",
    "physics.quantity",
    "physics.unit_conversion",
)

#: `BenchmarkDomain` has nine members and none of them is English or language. Per the
#: 22C W2-F4 rule — a pipeline may not invent a value for a released vocabulary — the
#: microbenchmark declares under an existing member and the mismatch is recorded as a
#: finding rather than dissolved by adding an enum member, which is the exact shape 22A
#: spent a sprint removing.
BENCHMARK_DECLARED_DOMAIN = BenchmarkDomain.GENERIC
BENCHMARK_DOMAIN_MISMATCH = (
    "BenchmarkDomain carries no English or language member; the microbenchmark is declared "
    "under GENERIC and the mismatch is carried as W0-F2 rather than resolved by widening a "
    "released enum"
)

#: A task the verifier cannot decide is a failure for *every* arm, and the count is reported.
#: Naming it here stops it becoming an arm-specific allowance later.
UNDECIDABLE_COUNTS_AS = "failure for every arm, and the count is reported"

#: The optional extras the frozen verifier set depends on. `verification-physics` supplies
#: Pint, and half the hundred cannot be decided without it.
REQUIRED_VERIFIER_EXTRAS = ("verification-physics",)


class BenchmarkVerifiersUnavailable(RuntimeError):
    """**W0-F1.** An absent extra is an environment defect, never a measured result.

    `build_builtin_registry()` registers the physics verifiers as *unavailable* when Pint is
    missing rather than omitting them, and `list_all()` returns them alongside the ones that
    can actually run — so a set chosen by reading the registry looks complete and half of it
    errors at run time. `VerifierRegistry.get()` then answers `None`, the runner's honest
    reading of an undecidable task counts it a failure for every arm, and fifty of the
    hundred score zero for a reason no number in the record mentions. The 70 % exit becomes
    unreachable and the shortfall reads as capability.

    So this is a refusal before the first arm rather than a count afterwards. §2.2(b)'s
    "counted as a failure for every arm" is about an *answer* the verifier cannot decide; it
    was never about a verifier that cannot start.
    """


def require_benchmark_verifiers() -> tuple[str, ...]:
    """Refuse a benchmark run whose frozen verifier set cannot run here. Returns the set."""
    registry = build_builtin_registry()
    available = {item.verifier_id for item in registry.list_available()}
    missing = tuple(sorted(set(BENCHMARK_VERIFIER_IDS) - available))
    if missing:
        raise BenchmarkVerifiersUnavailable(
            f"frozen verifiers are registered but unavailable: {list(missing)}; install the "
            f"{list(REQUIRED_VERIFIER_EXTRAS)} extra — an undecidable count caused by a "
            f"missing dependency is an environment defect, not a measurement"
        )
    return BENCHMARK_VERIFIER_IDS


# ---------------------------------------------------------------------------
# §2.2(d). Grounded, uncertain, and the third case the exit reads as zero
# ---------------------------------------------------------------------------

#: **The typed abstention.** A value the runtime produces and the verifier recognises — not a
#: hedging phrase detected in prose, which would make the fourth exit a string-matching
#: exercise. An abstained outcome carries no answer at all, so there is nothing for a
#: verifier to mistake for one.
ABSTENTION_VALUE = "cogos.abstain.insufficient_grounding.v1"

#: The three cases every factual output falls into, exhaustively. The exit reads
#: `ungrounded_assertion` being zero; the other two are both acceptable outcomes.
OUTPUT_DISPOSITIONS = ("grounded", "typed_abstention", "ungrounded_assertion")

#: **What counts as a factual output**, frozen and asserted by a test. A task is a factual
#: output when answering it requires asserting a value the system did not compute from the
#: prompt alone — a declarative fact, or a derivation that consumes one. A pure computation
#: over numbers stated in the prompt asserts nothing about the world and is not in scope for
#: the grounding exit; counting it would inflate the denominator with outputs that cannot be
#: ungrounded.
FACTUAL_OUTPUT_KINDS = ("declarative_fact", "fact_dependent_derivation")
NON_FACTUAL_OUTPUT_KINDS = ("closed_form_computation",)
OUTPUT_KINDS = FACTUAL_OUTPUT_KINDS + NON_FACTUAL_OUTPUT_KINDS

#: §1.5's ladder, frozen before any fact is admitted. A status boundary chosen after seeing
#: which facts fall on which side is the same defect as a tolerance chosen after seeing the
#: answer (22C W1-F3, W3-F2).
#:
#: A declarative fact cannot be recomputed, but it can be *corroborated*: if the retained
#: fact reproduces a worked example's printed result exactly, that example is evidence for
#: it. The kernel becomes a consistency oracle rather than a recomputation.
GROUNDING_LADDER = (
    {
        "status": "corroborated",
        "requires": (
            "a resolvable span into registered source bytes",
            "promotion through the twelve released semantic verifiers",
            "at least one kernel-checkable consequence that reproduces a printed result "
            "exactly, compared as numbers and never within a tolerance",
        ),
        "retrievable": True,
    },
    {
        "status": "grounded",
        "requires": (
            "a resolvable span into registered source bytes",
            "promotion through the twelve released semantic verifiers",
        ),
        "retrievable": True,
        "weaker_because": "no kernel-checkable consequence corroborates it, and the record "
        "says so for every retained fact rather than for the layer as a whole",
    },
    {
        "status": "refused",
        "requires": ("nothing — this is the absence of a resolvable span",),
        "retrievable": False,
    },
)

#: The floor beneath the ladder: **every** factual output resolves to source bytes, whatever
#: its status. The ladder decides how strong a retained fact is; it never decides whether an
#: answer needs a citation.
GROUNDING_FLOOR = "every factual output resolves to loaded source bytes or abstains"


# ---------------------------------------------------------------------------
# §2.2(c) and §3.2. The escalation policy, as a decision function
# ---------------------------------------------------------------------------

#: The threshold, and it is an integer over a quantity the runtime already produces rather
#: than a knob over a model's opinion of itself. 22C W3-D1's rule applies with force to a
#: language model: a component that demands an input it does not use is a refusal with a
#: name, and a self-reported confidence is exactly the value a model will always produce.
#: Grounding support is counted, not asked for.
MINIMUM_GROUNDED_SPANS = 1


@dataclass(frozen=True)
class Citation:
    """A span the citation walk can resolve by loading the cited bytes."""

    source_id: str
    content_hash: str
    start: int
    end: int

    def as_json(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "content_hash": self.content_hash,
            "start": self.start,
            "end": self.end,
        }


@dataclass(frozen=True)
class ArmOutcome:
    """What one arm produced for one task, in the vocabulary every exit reads."""

    task_id: str
    arm: str
    #: Whatever shape the task's registered verifier reads — a string for `generic.exact`,
    #: a magnitude/unit mapping for the physics verifiers. `None` iff the arm abstained.
    answer: Any
    abstained: bool
    citations: tuple[Citation, ...] = ()
    answer_form_valid: bool = True
    external_provider_calls: int = 0
    local_model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    local_compute_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.abstained and self.answer is not None:
            raise ValueError("an abstention carries no answer")
        if not self.abstained and self.answer is None:
            raise ValueError("a non-abstaining outcome must carry an answer")

    @property
    def grounded_span_count(self) -> int:
        return len(self.citations)


def escalate(outcome: ArmOutcome) -> bool:
    """**The frozen decision function.** Not a prompt instruction, and not tunable.

    Three mechanical signals, all produced by the runtime before this is called:

    * the local arm emitted the typed abstention;
    * it asserted something with fewer resolved grounding spans than the floor requires;
    * its answer does not have the form the task's verifier can decide at all.

    §3.2 names this as the place the sprint could cheat without noticing — a threshold tuned
    until the mixed workload hits both the 25 % target and the non-inferiority margin is a
    number met by moving what the number reads. It is frozen here, before the first measured
    number, and §2.3 forbids touching it afterwards.
    """
    return (
        outcome.abstained
        or outcome.grounded_span_count < MINIMUM_GROUNDED_SPANS
        or not outcome.answer_form_valid
    )


# ---------------------------------------------------------------------------
# §2.2(c). The accounting record
# ---------------------------------------------------------------------------

#: Cost units, frozen here so both sides of the 25 % are computed by one definition. These
#: are *accounting* units, not currency: §4 already refuses the claim that a reduction
#: measured on one workload is an operating cost, and giving these a dollar sign would invite
#: exactly that reading.
EXTERNAL_CALL_COST_UNITS = 1.0
EXTERNAL_TOKEN_COST_UNITS_PER_1K = 0.5
LOCAL_COMPUTE_COST_UNITS_PER_SECOND = 0.01


def accounted_cost(outcomes: Sequence[ArmOutcome]) -> float:
    """One definition, applied to every arm, so the two reported quantities cannot diverge."""
    calls = sum(item.external_provider_calls for item in outcomes)
    tokens = sum(item.input_tokens + item.output_tokens for item in outcomes)
    seconds = sum(item.local_compute_seconds for item in outcomes)
    return (
        calls * EXTERNAL_CALL_COST_UNITS
        + tokens / 1000 * EXTERNAL_TOKEN_COST_UNITS_PER_1K
        + seconds * LOCAL_COMPUTE_COST_UNITS_PER_SECOND
    )


# ---------------------------------------------------------------------------
# The local runtime harness
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LocalRuntime:
    """Everything about the local model that a measured number is conditioned on. §4.

    Pinned and hashed rather than described, because "one model is one model" is only an
    honest limitation if the record says *which* one. `weights_sha256` is empty exactly while
    no model has been cleared; `require_cleared()` is the refusal that keeps a benchmark from
    running on unclear weights.
    """

    model_id: str
    weights_sha256: str
    quantization: str
    context_tokens: int
    temperature: float
    top_p: float
    seed: int
    device: str
    clearance_id: str | None = None

    def require_cleared(self) -> None:
        if not self.clearance_id or not self.weights_sha256:
            raise RuntimeError(
                "no local model may be benchmarked without an OperatorLicenseClearance and "
                "a pinned weight hash: a benchmark run on unclear weights is evidence that "
                "cannot be released (§3.2)"
            )

    def as_json(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "weights_sha256": self.weights_sha256,
            "quantization": self.quantization,
            "context_tokens": self.context_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "seed": self.seed,
            "device": self.device,
            "clearance_id": self.clearance_id,
        }


#: The §3.1 stand-in. A fixture-scale runtime with no weights and no clearance, which is what
#: makes the slice honest: it exercises the runner, the arms, the refusal, the walk and the
#: abstention *before* a model exists, exactly as §3.1 asks.
FIXTURE_RUNTIME = LocalRuntime(
    model_id="fixture-local-model",
    weights_sha256="",
    quantization="none",
    context_tokens=4096,
    temperature=0.0,
    top_p=1.0,
    seed=22_040,
    device="cpu",
    clearance_id=None,
)

#: The measured configuration of record is CPU. §1.3: the exit asks for CPU viability — a
#: claim about owned resources, not about speed — and a claim measured only on a GPU is not
#: the claim the allocation asks for. GPU numbers are reported beside it, never in place.
CONFIGURATION_OF_RECORD = "cpu"


# ---------------------------------------------------------------------------
# The runner
# ---------------------------------------------------------------------------


@dataclass
class ArmAccounting:
    """The provider/local compute accounting record, per arm."""

    arm: str
    tasks: int = 0
    verified: int = 0
    undecidable: int = 0
    abstained: int = 0
    grounded: int = 0
    ungrounded_assertions: int = 0
    escalated: int = 0
    external_provider_calls: int = 0
    local_model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    local_compute_seconds: float = 0.0
    accounted_cost_units: float = 0.0
    per_task: dict[str, Any] = field(default_factory=dict)

    @property
    def verified_percent(self) -> float:
        return 0.0 if not self.tasks else round(100.0 * self.verified / self.tasks, 4)

    def as_json(self) -> dict[str, Any]:
        return {
            "arm": self.arm,
            "tasks": self.tasks,
            "verified": self.verified,
            "verified_percent": self.verified_percent,
            "undecidable": self.undecidable,
            "abstained": self.abstained,
            "grounded": self.grounded,
            "ungrounded_assertions": self.ungrounded_assertions,
            "escalated": self.escalated,
            "external_provider_calls": self.external_provider_calls,
            "local_model_calls": self.local_model_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "local_compute_seconds": round(self.local_compute_seconds, 6),
            "accounted_cost_units": round(self.accounted_cost_units, 6),
            "per_task": self.per_task,
        }


async def verify_answer(task: Mapping[str, Any], outcome: ArmOutcome) -> tuple[bool, bool]:
    """Run the task's *registered* verifier. Returns (verified, undecidable).

    An abstention is never submitted: there is no answer to verify, so it is a failure for
    the success reading and a pass for the grounding reading, which are different questions
    and are counted separately on purpose.
    """
    if outcome.abstained or outcome.answer is None:
        return False, False
    # `require`, not `get`. `get` answers `None` for a verifier that is registered but
    # unavailable, and the caller cannot tell that from a verifier that decided nothing —
    # which is W0-F1 in one line.
    verifier = build_builtin_registry().require(task["verifier_id"], "1")
    # Identity comes from the outcome, not from the task mapping: a microbenchmark task keys
    # it `task_id` and a holdout case keys it `case_id`, and one verifier serves both.
    identity = outcome.task_id
    request = VerificationRequest(
        verification_id=uuid5(NAMESPACE, f"{identity}:{outcome.arm}:verification"),
        task_run_id=uuid5(NAMESPACE, f"{identity}:{outcome.arm}:run"),
        criterion_id=uuid5(NAMESPACE, f"{identity}:criterion"),
        verifier_id=task["verifier_id"],
        verifier_version="1",
        subject=VerificationSubject(
            subject_type=VerificationSubjectType(task["subject_type"]),
            inline_value=outcome.answer,
        ),
        configuration=dict(task["verifier_configuration"]),
        requested_at=SLICE_TIME,
        correlation_id=uuid5(NAMESPACE, f"{identity}:{outcome.arm}:correlation"),
    )
    result = await verifier.verify(request)
    if result.status is VerifierStatus.ERROR:
        return False, True
    return result.status is VerifierStatus.PASSED, False


def walk_answer_citations(outcome: ArmOutcome, sources: Mapping[str, bytes]) -> dict[str, Any]:
    """From a *generated sentence* back to loaded source bytes. §3.1's predicted finding.

    22C's walker starts from a promoted artifact whose provenance bundle the pipeline built.
    A sentence a language model just produced has no bundle, so this walk starts one hop
    earlier: the answer's own citation names a registered source and a byte range, the range
    is sliced out of the loaded bytes, and the slice is hashed. A digest proves bytes and not
    usability (D7 W3-F1), so the bytes are loaded and cut rather than trusted.
    """
    hops: list[dict[str, Any]] = []
    for citation in outcome.citations:
        data = sources.get(citation.source_id)
        loaded = data is not None
        in_range = loaded and 0 <= citation.start < citation.end <= len(data or b"")
        span = (data or b"")[citation.start : citation.end] if in_range else b""
        hops.append(
            {
                "hop": "answer_citation -> registered_source_bytes",
                **citation.as_json(),
                "source_loaded": loaded,
                "span_in_range": in_range,
                "span_bytes": len(span),
                "span_hash": _sha256(span) if in_range else None,
                "resolves": bool(in_range and _sha256(span) == citation.content_hash),
            }
        )
    return {
        "citations": len(outcome.citations),
        "hops": hops,
        "all_citations_resolve": bool(hops) and all(hop["resolves"] for hop in hops),
        "sampled": False,
    }


def disposition(task: Mapping[str, Any], outcome: ArmOutcome, walk: Mapping[str, Any]) -> str:
    """Which of the three §2.2(d) cases this output is. Exhaustive by construction."""
    if task["output_kind"] not in FACTUAL_OUTPUT_KINDS:
        return "not_a_factual_output"
    if outcome.abstained:
        return "typed_abstention"
    return "grounded" if walk["all_citations_resolve"] else "ungrounded_assertion"


async def run_arm(
    arm: str,
    tasks: Sequence[Mapping[str, Any]],
    answerer: Any,
    sources: Mapping[str, bytes],
) -> ArmAccounting:
    """One arm over one task set, with the accounting and the grounding walk on every task.

    `answerer` is a callable `(arm, task) -> ArmOutcome`. The runner owns verification,
    accounting, escalation and the walk; the arm owns only what it answered, which is what
    keeps the four arms comparable.
    """
    if arm not in ARMS and arm != MIXED_WORKLOAD:
        raise ValueError(f"unknown arm: {arm}")
    require_benchmark_verifiers()
    accounting = ArmAccounting(arm=arm)
    for task in tasks:
        outcome = answerer(arm, task)
        # An arm that reaches a network reaches it through an async governed boundary, and an
        # arm that reads an index does not. Awaiting only what is awaitable lets both be the
        # same kind of thing to this runner, which is what keeps the four arms comparable —
        # the alternative was a second runner, and two runners are two sets of accounting.
        if inspect.isawaitable(outcome):
            outcome = await outcome
        if outcome.external_provider_calls and arm not in EXTERNAL_CALLS_PERMITTED:
            raise ExternalProviderRefused(
                f"arm {arm!r} recorded an external provider call; only "
                f"{', '.join(EXTERNAL_CALLS_PERMITTED)} may call one (§2.2a)"
            )
        verified, undecidable = await verify_answer(task, outcome)
        walk = walk_answer_citations(outcome, sources)
        case = disposition(task, outcome, walk)
        accounting.tasks += 1
        accounting.verified += int(verified)
        accounting.undecidable += int(undecidable)
        accounting.abstained += int(outcome.abstained)
        accounting.grounded += int(case == "grounded")
        accounting.ungrounded_assertions += int(case == "ungrounded_assertion")
        accounting.escalated += int(escalate(outcome))
        accounting.external_provider_calls += outcome.external_provider_calls
        accounting.local_model_calls += outcome.local_model_calls
        accounting.input_tokens += outcome.input_tokens
        accounting.output_tokens += outcome.output_tokens
        accounting.local_compute_seconds += outcome.local_compute_seconds
        accounting.per_task[str(task["task_id"])] = {
            "verified": verified,
            "undecidable": undecidable,
            "abstained": outcome.abstained,
            "disposition": case,
            "citations_resolve": walk["all_citations_resolve"],
            "escalated": escalate(outcome),
        }
    accounting.accounted_cost_units = accounted_cost(
        [
            ArmOutcome(
                task_id="_total",
                arm=arm,
                answer="",
                abstained=False,
                external_provider_calls=accounting.external_provider_calls,
                input_tokens=accounting.input_tokens,
                output_tokens=accounting.output_tokens,
                local_compute_seconds=accounting.local_compute_seconds,
            )
        ]
    )
    return accounting


# ---------------------------------------------------------------------------
# Hashing helpers, shared with every 22D driver
# ---------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def readings_hash() -> str:
    """One hash over every reading §2.2 freezes, imported from here and never retyped."""
    return _sha256(canonical(readings()))


def readings() -> dict[str, Any]:
    """The frozen readings, as data, so the pre-registration hashes them from their source."""
    return {
        "external_provider_enumeration": list(EXTERNAL_PROVIDER_IDS),
        "external_provider_config_classes": [item.__name__ for item in EXTERNAL_PROVIDER_CONFIGS],
        "local_components_out_of_scope": list(LOCAL_COMPONENTS_OUT_OF_SCOPE),
        "permitted_benchmark_provider_kinds": [
            item.value for item in PERMITTED_BENCHMARK_PROVIDER_KINDS
        ],
        "arms": list(ARMS),
        "margin_comparison": list(MARGIN_COMPARISON),
        "minimum_local_success_percent": MINIMUM_LOCAL_SUCCESS_PERCENT,
        "minimum_margin_points": MINIMUM_MARGIN_POINTS,
        "non_inferiority_margin_points": NON_INFERIORITY_MARGIN_POINTS,
        "minimum_cost_reduction_percent": MINIMUM_COST_REDUCTION_PERCENT,
        "cost_reduction_quantities": list(COST_REDUCTION_QUANTITIES),
        "benchmark_verifier_ids": list(BENCHMARK_VERIFIER_IDS),
        "benchmark_declared_domain": BENCHMARK_DECLARED_DOMAIN.value,
        "benchmark_domain_mismatch": BENCHMARK_DOMAIN_MISMATCH,
        "undecidable_counts_as": UNDECIDABLE_COUNTS_AS,
        "abstention_value": ABSTENTION_VALUE,
        "output_dispositions": list(OUTPUT_DISPOSITIONS),
        "factual_output_kinds": list(FACTUAL_OUTPUT_KINDS),
        "non_factual_output_kinds": list(NON_FACTUAL_OUTPUT_KINDS),
        "grounding_floor": GROUNDING_FLOOR,
        "grounding_ladder": [
            {
                key: (list(value) if isinstance(value, tuple) else value)
                for key, value in rung.items()
            }
            for rung in GROUNDING_LADDER
        ],
        "minimum_grounded_spans": MINIMUM_GROUNDED_SPANS,
        "escalation_policy": (
            "escalate(outcome) = outcome.abstained or "
            "outcome.grounded_span_count < MINIMUM_GROUNDED_SPANS or "
            "not outcome.answer_form_valid"
        ),
        "cost_units": {
            "external_call": EXTERNAL_CALL_COST_UNITS,
            "external_tokens_per_1k": EXTERNAL_TOKEN_COST_UNITS_PER_1K,
            "local_compute_per_second": LOCAL_COMPUTE_COST_UNITS_PER_SECOND,
        },
        "configuration_of_record": CONFIGURATION_OF_RECORD,
        "local_benchmark_budget": local_benchmark_budget().model_dump(mode="json"),
    }


# ---------------------------------------------------------------------------
# §3.1. The first vertical slice
# ---------------------------------------------------------------------------


def _slice_answerer(sources: Mapping[str, bytes]) -> Any:
    """A deterministic stand-in for four arms, at fixture scale and before any model exists.

    Each arm answers by a *mechanically different* route, because the slice's job is to prove
    the runner can tell them apart — 22C's pre-registration paid for that lesson by proving
    two arms differed before spending a holdout on discovering they did not.
    """
    from tasks_22d import FIXTURE_ANSWERS

    def answer(arm: str, task: Mapping[str, Any]) -> ArmOutcome:
        spec = FIXTURE_ANSWERS[str(task["task_id"])][arm]
        # A citation names a quote, and the offsets are *found* in the loaded bytes rather
        # than written down beside them. Hard-coded offsets are a citation that stops
        # resolving the moment a fixture sentence gains a comma, and nobody notices because
        # the number still looks like a number.
        citations = []
        for item in spec.get("citations", ()):
            data = sources[item["source_id"]]
            start = data.index(item["quote"].encode("utf-8"))
            end = start + len(item["quote"].encode("utf-8"))
            citations.append(
                Citation(
                    source_id=item["source_id"],
                    content_hash=_sha256(data[start:end]),
                    start=start,
                    end=end,
                )
            )
        return ArmOutcome(
            task_id=str(task["task_id"]),
            arm=arm,
            answer=spec.get("answer"),
            abstained=spec.get("abstained", False),
            citations=tuple(citations),
            answer_form_valid=spec.get("answer_form_valid", True),
            external_provider_calls=1 if arm == "external_teacher" else 0,
            local_model_calls=1 if arm in {"no_memory", "local_model"} else 0,
            input_tokens=spec.get("input_tokens", 0),
            output_tokens=spec.get("output_tokens", 0),
            local_compute_seconds=spec.get("local_compute_seconds", 0.0),
        )

    return answer


async def run_slice() -> dict[str, Any]:
    """Ten fixture tasks, four arms, one refused external call, one walk, one abstention."""
    from tasks_22d import FIXTURE_SOURCES, FIXTURE_TASKS

    sources = {key: value.encode("utf-8") for key, value in FIXTURE_SOURCES.items()}
    answerer = _slice_answerer(sources)
    arms = {}
    for arm in ARMS:
        arms[arm] = (await run_arm(arm, FIXTURE_TASKS, answerer, sources)).as_json()

    # The refusal, executed rather than described. A gate that has never refused anything is
    # a gate nobody has tested (22A W4-F2).
    refusals = []
    try:
        refuse_external_providers(["openrouter"])
    except ExternalProviderRefused as error:
        refusals.append({"attempt": "register openrouter", "refused": True, "message": str(error)})
    else:  # pragma: no cover - the refusal is the point
        refusals.append({"attempt": "register openrouter", "refused": False})
    try:
        FIXTURE_RUNTIME.require_cleared()
    except RuntimeError as error:
        refusals.append(
            {"attempt": "benchmark uncleared weights", "refused": True, "message": str(error)}
        )
    else:  # pragma: no cover
        refusals.append({"attempt": "benchmark uncleared weights", "refused": False})

    local, retrieval = arms["local_model"], arms["retrieval_only"]
    return {
        "schema_version": 1,
        "items": ["S22D-030"],
        "slice_scale": "fixture",
        "tasks": len(FIXTURE_TASKS),
        "arms_run": list(ARMS),
        "arms": arms,
        "refusals": refusals,
        "every_refusal_refused": all(item["refused"] for item in refusals),
        "external_calls_outside_the_teacher_arm": sum(
            arms[arm]["external_provider_calls"] for arm in ARMS if arm != "external_teacher"
        ),
        "arms_are_mechanically_different": local["verified"] != retrieval["verified"],
        "at_least_one_typed_abstention": any(arms[arm]["abstained"] for arm in ARMS),
        "at_least_one_resolved_citation_walk": any(arms[arm]["grounded"] for arm in ARMS),
        "ungrounded_assertions_by_arm": {arm: arms[arm]["ungrounded_assertions"] for arm in ARMS},
        "runtime": FIXTURE_RUNTIME.as_json(),
        "readings_hash": readings_hash(),
        "decides_no_exit_criterion": (
            "the slice runs ten fixture tasks against a fixture runtime; every 22D exit is a "
            "claim about the frozen hundred and a cleared model, and none of them is read here"
        ),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

OUTPUT = EVIDENCE / "sprint-22d-w0-slice.json"


def _seal(record: dict[str, Any]) -> dict[str, Any]:
    record["recorded_at"] = SLICE_TIME.isoformat().replace("+00:00", "Z")
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", action="store_true", help="run the §3.1 fixture slice")
    parser.add_argument("--check", action="store_true", help="rebuild the slice and compare")
    args = parser.parse_args()
    if not (args.slice or args.check):
        parser.error("pass --slice or --check")

    record = _seal(asyncio.run(run_slice()))
    if args.check:
        if not OUTPUT.exists():
            print(f"MISSING {OUTPUT}")
            return 1
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(canonical(body)) == stored["integrity_content_hash"]
        identical = stored == record
        print(f"seal_recomputes={sealed} rebuild_identical={identical}")
        return 0 if sealed and identical else 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO)}")
    print(f"readings_hash={record['readings_hash']}")
    for arm in ARMS:
        entry = record["arms"][arm]
        print(
            f"  {arm:<17} verified={entry['verified']}/{entry['tasks']} "
            f"grounded={entry['grounded']} abstained={entry['abstained']} "
            f"ungrounded={entry['ungrounded_assertions']} escalated={entry['escalated']} "
            f"external_calls={entry['external_provider_calls']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
