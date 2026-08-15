"""S22C-041a. The governed provider call that formalises a passage, and its seal.

§3.2's third schedule risk, stated as a rule: *a cycle that can only be reproduced by
re-calling a provider is not replayable evidence.* This module is that rule implemented.

**What the provider is actually for.** A worked example is prose. A deterministic kernel
needs `{"speed": {"magnitude": "2.4", "unit": "m/s"}, "time": …}`. Turning the first into the
second is reading comprehension, it is not decidable by a regular expression, and it is
exactly the job §1.2 gives a provider: *a proposal revalidated on the host, with no semantic
write authority*. The provider is never asked whether the physics is right — it is asked only
what the passage says. Whether the passage is right is the kernel's answer, two stages later,
and no provider output reaches an active state without it.

**The seal, and why replay runs through the released provider path.** Every call goes through
the released `GovernedTeacherService`, which returns a receipt carrying the request hash, the
normalized response hash and the completed model-call envelope, and records a governance
revision. Beside it this module writes a released `ReplayFixture`. Ordinary runs then load
those fixtures into the released `ReplayProvider` and **execute the same governed path
again**, so the seal is verified by re-execution rather than by trust: if a sealed response
had been edited, the replayed normalized response hash would not match the sealed one and the
cycle would refuse to run.

    UV_CACHE_DIR=.cache/uv uv run python scripts/provider_22c.py --live   # calls a provider
    UV_CACHE_DIR=.cache/uv uv run python scripts/provider_22c.py          # replays the seals

`--live` is the opt-in §1.3 requires, and it is the only way a network call happens.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
PROPOSALS = EVIDENCE / "sprint-22c-w2-proposals"
sys.path.insert(0, str(REPO / "scripts"))

from chapter_22c import Passage, locate_passages  # noqa: E402

from cognitive_os.application.services.governed_teacher import (  # noqa: E402
    GovernedTeacherService,
    RightsDecision,
    VerifierOutcome,
)
from cognitive_os.application.services.model_execution import ModelExecutionService  # noqa: E402
from cognitive_os.config.provider_config import ClaudeCodeProviderConfig  # noqa: E402
from cognitive_os.domain.memory import MemorySensitivity  # noqa: E402
from cognitive_os.domain.model_requests import (  # noqa: E402
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ResponseFormat  # noqa: E402
from cognitive_os.domain.provider_output import (  # noqa: E402
    ProviderAdapterKind,
    ProviderOutputIntendedUse,
    ProviderOutputRetentionMode,
    ProviderOutputVerifierStatus,
    ProviderRetentionDirective,
    UsageRightsDecision,
)
from cognitive_os.events.memory_store import MemoryEventStore  # noqa: E402
from cognitive_os.events.provider_event_service import (  # noqa: E402
    ProviderArtifactPolicy,
    ProviderArtifactService,
    ProviderEventService,
)
from cognitive_os.infrastructure.learned.memory_provider_output import (  # noqa: E402
    InMemoryProviderOutputRepository,
)
from cognitive_os.providers.claude_code import ClaudeCodeAdvisoryProvider  # noqa: E402
from cognitive_os.providers.registry import ProviderRegistry  # noqa: E402
from cognitive_os.providers.replay import ReplayFixture, ReplayProvider  # noqa: E402

NAMESPACE = uuid5(NAMESPACE_URL, "cognitive-os:sprint-22c:w2:extraction")

#: Bumped whenever the prompt or the schema changes, and recorded in the governance
#: directive. A sealed proposal that was answered under a different question is not a seal of
#: this one, and the version is how a reader tells.
PROMPT_TEMPLATE_ID = "s22c-w2-formalise-worked-example"
PROMPT_TEMPLATE_VERSION = "1"

#: A cost and latency bound. The passage is supplied inline, so the run needs no file reads
#: and one turn is enough; the adapter's read-only tool allowlist stands either way.
MAXIMUM_TURNS = 2
MAXIMUM_OUTPUT_TOKENS = 4096

#: The three problem types `engineering.mechanics` registers, and the exact input shape each
#: kernel reads. Written out rather than generated, because this text is the contract the
#: provider is held to and a generated prompt would drift with an unrelated refactor. The
#: kernels refuse floats by design, so the instruction to use strings is the kernel's rule
#: restated, not a preference.
KERNEL_GUIDE = """\
engineering.mechanics registers exactly three problem types.

mechanics.uniform-motion — a displacement from a constant (or average) speed and a duration.
  formal_inputs: {"speed": {"magnitude": <exact>, "unit": "m/s"},
                  "time": {"magnitude": <exact>, "unit": "s"},
                  "result_unit": "m"}
  answer shape: {"exact_value": "<exact>", "units": "m"}

mechanics.statics-equilibrium — whether coplanar forces on one body balance.
  formal_inputs: {"forces": [{"name": "<unique>", "fx": <exact>, "fy": <exact>}, ...],
                  "force_unit": "N"}
  answer shape: {"structured": {"equilibrium": true|false}}

mechanics.moment-balance — the resultant moment of forces about a stated pivot.
  formal_inputs: {"pivot": {"x": <exact>, "y": <exact>},
                  "forces": [{"name": "<unique>", "x": <exact>, "y": <exact>,
                              "fx": <exact>, "fy": <exact>}, ...],
                  "force_unit": "N", "length_unit": "m", "moment_unit": "N*m"}
  answer shape: {"exact_value": "<exact>", "units": "N*m"}

Every <exact> is an integer or a decimal **string** such as "2.4" or "110.4". Never a JSON
float, never a rounded value, never scientific notation.
"""

SYSTEM_INSTRUCTIONS = f"""\
You formalise one worked example from a physics textbook so that a deterministic kernel can
recompute it. You are not asked whether the physics is correct and you must not correct it.

{KERNEL_GUIDE}

Rules.
1. `formal_inputs` carries only the quantities the passage itself states as *given*. Never
   the answer, and never a quantity you inferred from the answer.
2. `asserted` carries the result the passage *claims*, in the answer shape above, and only
   when the passage states that result in words or digits you can read. If the computation
   is a figure, an equation number with no value, or a graph, then the passage asserts no
   readable result: set `formalisable` to false with reason `no_readable_result`.
3. When a passage states its result at more than one precision, take the **exact** one it
   gives and quote it verbatim in `asserted_value_quoted_from_the_passage`. Never round, and
   never reconcile two figures for it.
4. If the passage is not one of the three problem types — a distance, an acceleration, a
   slope, an area under a curve — set `formalisable` to false with reason
   `no_registered_problem_type`. Do not bend it into the nearest type.
5. If you cannot do rule 1 or rule 2 honestly, say so. A refusal is a correct answer here and
   a guess is not.

Return only the JSON object the schema describes.
"""

REASONS = (
    "no_readable_result",
    "no_registered_problem_type",
    "given_quantities_not_stated",
    "other",
)

#: **W3-D1, and the decision is recorded because it decides what the wave measures.**
#: `chemistry.mass-balance` demands `atomic_masses` on every case, and a passage that balances
#: an equation never states them — the verdict does not depend on their values, only on their
#: presence. Two ways out, and only one of them is honest: let the provider supply "standard"
#: masses the passage does not contain, which is inventing data to satisfy a kernel and
#: exactly the move rule 1 exists to refuse; or refuse the passage and *name why*, so a
#: domain that demands an input its answer does not use becomes a number rather than a fudge.
#: The wave takes the second, and this reason is what carries it.
CHEMISTRY_REASONS = (*REASONS, "kernel_requires_unstated_input")

#: The two problem types `science.chemistry` registers. The same discipline as the mechanics
#: guide: written out, because this text is the contract the provider is held to.
CHEMISTRY_KERNEL_GUIDE = """\
science.chemistry registers exactly two problem types.

chemistry.molar-conversion — an amount in moles from a mass and a molar mass.
  formal_inputs: {"formula": "<formula>",
                  "atomic_masses": {"<symbol>": <exact>, ...},
                  "mass": {"magnitude": <exact>, "unit": "g"},
                  "molar_mass_unit": "g/mol"}
  answer shape: {"exact_value": "<exact>", "units": "mol"}

chemistry.mass-balance — whether a written equation conserves atoms and mass.
  formal_inputs: {"reactants": [{"formula": "<formula>", "coefficient": <integer>}, ...],
                  "products": [{"formula": "<formula>", "coefficient": <integer>}, ...],
                  "atomic_masses": {"<symbol>": <exact>, ...}}
  answer shape: {"structured": {"balanced": true|false}}

Every <exact> is an integer or a decimal **string** such as "39.10". Never a JSON float,
never a rounded value, never scientific notation.
"""

CHEMISTRY_SYSTEM_INSTRUCTIONS = f"""\
You formalise one worked example from a chemistry textbook so that a deterministic kernel can
recompute it. You are not asked whether the chemistry is correct and you must not correct it.

{CHEMISTRY_KERNEL_GUIDE}

Rules.
1. `formal_inputs` carries only the quantities the passage itself states as *given*. Never
   the answer, and never a quantity you inferred from the answer. An atomic mass counts as
   stated only if the passage prints it; "referring to the periodic table" is not a value.
2. `asserted` carries the result the passage *claims*, in the answer shape above, and only
   when the passage states that result in words or digits you can read. A chemistry example
   often prints its result twice — once in the Solution's discussion and once after
   `Answer:` for the Check Your Learning question. Those are answers to **different**
   questions: take the one that belongs to the quantities in `formal_inputs`, and never mix
   a Check Your Learning answer with the worked example's own givens.
3. Take the value exactly as printed and quote it verbatim in
   `asserted_value_quoted_from_the_passage`. Never round it and never extend it.
4. If the passage is not one of the two problem types — a formula mass, a percent
   composition, an empirical formula, a molarity, a dilution, a limiting reactant, a percent
   yield, a titration — set `formalisable` to false with reason
   `no_registered_problem_type`. Do not bend it into the nearest type.
5. If a registered problem type fits but its `formal_inputs` require a value the passage does
   not state — most often `atomic_masses` for a balancing example, which the kernel demands
   and the verdict does not use — set `formalisable` to false with reason
   `kernel_requires_unstated_input`. Do not supply a standard value from your own knowledge:
   the campaign is measuring what this source states, not what you know.
6. If you cannot do rules 1 to 3 honestly, say so. A refusal is a correct answer here and a
   guess is not.

Return only the JSON object the schema describes.
"""


def extraction_schema(reasons: tuple[str, ...], problem_types: tuple[str, ...]) -> dict[str, Any]:
    """One frozen answer shape per source.

    Built rather than shared, because the request fingerprint a sealed proposal is keyed on
    covers the schema: adding chemistry's extra refusal reason to one global schema would
    have changed every physics request and orphaned eighteen seals.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "formalisable",
            "reason",
            "problem_type",
            "formal_inputs",
            "asserted",
            "asserted_value_quoted_from_the_passage",
            "statement",
            "notes",
        ],
        "properties": {
            "formalisable": {"type": "boolean"},
            "reason": {"type": "string", "enum": ["formalisable", *reasons]},
            "problem_type": {"type": "string", "enum": ["", *problem_types]},
            "formal_inputs": {"type": "object", "additionalProperties": True},
            "asserted": {"type": "object", "additionalProperties": True},
            "asserted_value_quoted_from_the_passage": {"type": "string"},
            "statement": {"type": "string"},
            "notes": {"type": "string"},
        },
    }


@dataclass(frozen=True, slots=True)
class ExtractionProfile:
    """One source's extraction contract: which domain, which question, which answer shape.

    Frozen per source rather than shared, because the request fingerprint a sealed proposal
    is keyed on covers all three. Physics keeps its template id and version exactly as W2
    sealed them; chemistry is a new template, not a new version of the old one, because it
    asks a different question of a different book.
    """

    key: str
    domain_id: str
    template_id: str
    template_version: str
    instructions: str
    reasons: tuple[str, ...]
    problem_types: tuple[str, ...]

    @property
    def schema(self) -> dict[str, Any]:
        return extraction_schema(self.reasons, self.problem_types)

    @property
    def template(self) -> str:
        return f"{self.template_id}@{self.template_version}"


PHYSICS_EXTRACTION = ExtractionProfile(
    key="physics",
    domain_id="engineering.mechanics",
    template_id=PROMPT_TEMPLATE_ID,
    template_version=PROMPT_TEMPLATE_VERSION,
    instructions=SYSTEM_INSTRUCTIONS,
    reasons=REASONS,
    problem_types=(
        "mechanics.uniform-motion",
        "mechanics.statics-equilibrium",
        "mechanics.moment-balance",
    ),
)

CHEMISTRY_EXTRACTION = ExtractionProfile(
    key="chemistry",
    domain_id="science.chemistry",
    template_id="s22c-w3-formalise-worked-example",
    template_version="1",
    instructions=CHEMISTRY_SYSTEM_INSTRUCTIONS,
    reasons=CHEMISTRY_REASONS,
    problem_types=("chemistry.molar-conversion", "chemistry.mass-balance"),
)

EXTRACTION_PROFILES: dict[str, ExtractionProfile] = {
    "physics": PHYSICS_EXTRACTION,
    "chemistry": CHEMISTRY_EXTRACTION,
}


def proposals_directory(profile: ExtractionProfile) -> Path:
    return PROPOSALS if profile.key == "physics" else EVIDENCE / "sprint-22c-w3-proposals"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identifier(label: str) -> UUID:
    return uuid5(NAMESPACE, label)


def build_request(passage: Passage, profile: ExtractionProfile) -> ModelProviderRequest:
    """One request per passage, derived only from the passage. No clock, no counter.

    Everything the released `request_fingerprint` hashes is a function of the passage and the
    prompt template, so the same passage asks the same question forever — which is what makes
    a sealed answer replayable at all.
    """
    return ModelProviderRequest(
        model_call_id=_identifier(f"model-call:{passage.passage_id}"),
        task_run_id=_identifier("task-run:cycle-1"),
        correlation_id=_identifier(f"correlation:{passage.passage_id}"),
        requested_model="claude-code",
        system_instructions=profile.instructions,
        messages=(
            ProviderMessage(
                role=ProviderMessageRole.USER,
                content=(
                    f"Section {passage.section}, page {passage.first_page}.\n"
                    "The passage, exactly as the document's text layer carries it, page "
                    "furniture included:\n\n"
                    f"{passage.text}"
                ),
            ),
        ),
        response_format=ResponseFormat.JSON_SCHEMA,
        response_schema=profile.schema,
        temperature=0,
        max_output_tokens=MAXIMUM_OUTPUT_TOKENS,
    )


def directive_for(profile: ExtractionProfile) -> ProviderRetentionDirective:
    return ProviderRetentionDirective(
        intended_use=ProviderOutputIntendedUse.CORPUS_CANDIDATE,
        retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
        sensitivity=MemorySensitivity.INTERNAL,
        prompt_template_id=profile.template_id,
        prompt_template_version=profile.template_version,
    )


def _working_directory() -> Path:
    """A directory with nothing in it, because the adapter's cwd is a read scope.

    The passage travels in the prompt, so the run needs no files at all; pointing the CLI at
    the repository would grant a read scope this call has no use for.
    """
    root = REPO / ".cache" / "s22c-provider-cwd"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass(frozen=True, slots=True)
class Governed:
    """One governed execution, in the two shapes the campaign needs it."""

    passage_id: str
    receipt_provider_id: str
    adapter_kind: str
    resolved_model: str
    request_hash: str
    normalized_response_hash: str
    retention_mode: str
    rights_decision: str
    provider_output_id: str | None
    template: str
    answer: dict[str, Any]
    live: bool

    def as_sealed(self) -> dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "provider_id": self.receipt_provider_id,
            "adapter_kind": self.adapter_kind,
            "resolved_model": self.resolved_model,
            "request_hash": self.request_hash,
            "normalized_response_hash": self.normalized_response_hash,
            "retention_mode": self.retention_mode,
            "rights_decision": self.rights_decision,
            "receipt": f"provider-output:{self.provider_output_id}",
            "prompt_template": self.template,
            "answer": self.answer,
        }


def _teacher(provider: Any) -> GovernedTeacherService:
    """The released governed path, composed exactly as the provider benchmark composes it."""
    from cognitive_os.benchmarks.provider_harness import MemoryArtifactStore

    execution = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id=provider.provider_id,
        event_service=ProviderEventService(MemoryEventStore()),
        artifact_service=ProviderArtifactService(
            MemoryArtifactStore(),  # type: ignore[arg-type]
            policy=ProviderArtifactPolicy.NORMALIZED_ONLY,
        ),
    )
    return GovernedTeacherService(execution, repository=InMemoryProviderOutputRepository())


def live_provider() -> ClaudeCodeAdvisoryProvider:
    """The one adapter this host can actually reach, configured read-only.

    `live_smoke_enabled` is the released flag §1.3's opt-in maps onto: live execution is off
    unless configuration turns it on *and* a runtime flag is passed. Both are required here.
    """
    return ClaudeCodeAdvisoryProvider(
        ClaudeCodeProviderConfig(
            working_directory=_working_directory(),
            live_smoke_enabled=True,
            maximum_turns=MAXIMUM_TURNS,
        )
    )


def replay_provider(profile: ExtractionProfile) -> ReplayProvider:
    directory = proposals_directory(profile)
    if not directory.exists():
        raise SystemExit(
            f"no sealed proposals at {directory}. Run scripts/provider_22c.py --live once "
            f"for {profile.key}; §1.3 makes that an explicit opt-in"
        )
    return ReplayProvider.from_directory(directory)


async def govern(
    passage: Passage, provider: Any, profile: ExtractionProfile, *, live: bool
) -> Governed:
    """One passage through the released governed teacher, live or replayed."""
    request = build_request(passage, profile)
    rights = RightsDecision(
        decision=UsageRightsDecision.VERIFIED,
        # The gate owner's clearance, by hash. The rights question the governed teacher
        # refuses to answer for itself is answered here by the record that answered it in
        # S22C-020 — the same discipline W1-D2 put into the Corpus Factory.
        evidence_hash=_clearance_evidence_hash(profile.key),
    )
    receipt = await provider_receipt(provider, request, profile, rights=rights, live=live)
    answer = receipt.execution.response.structured_output
    if not isinstance(answer, dict):
        raise SystemExit(
            f"{passage.passage_id}: the provider returned no structured answer; a proposal "
            "that cannot be read cannot be revalidated"
        )
    return Governed(
        passage_id=passage.passage_id,
        receipt_provider_id=receipt.execution.provider_id,
        adapter_kind=receipt.execution.adapter_kind.value,
        resolved_model=receipt.execution.resolved_model,
        request_hash=receipt.execution.request_hash,
        normalized_response_hash=receipt.execution.normalized_response_hash,
        retention_mode=receipt.execution.retention_mode.value,
        rights_decision=rights.decision.value,
        provider_output_id=(
            str(receipt.governance.provider_output_id) if receipt.governance else None
        ),
        template=profile.template,
        answer=answer,
        live=live,
    )


async def provider_receipt(
    provider: Any,
    request: ModelProviderRequest,
    profile: ExtractionProfile,
    *,
    rights: RightsDecision,
    live: bool,
) -> Any:
    del live
    teacher = _teacher(provider)
    return await teacher.execute_with_receipt(
        request,
        directive=directive_for(profile),
        # The adapter the answer came from, which a replay does not change: the fixture
        # carries a Claude Code answer whether it is being produced or re-read. The receipt's
        # own `provider_id` is what says which of the two happened, and both are sealed.
        adapter_kind=ProviderAdapterKind.CLAUDE_CODE,
        rights=rights,
        # The provider does not verify itself and nothing has verified it yet: the
        # verification of this answer is the domain kernel's, four stages later in the cycle.
        verifier=VerifierOutcome(status=ProviderOutputVerifierStatus.NOT_RUN),
    )


def _clearance_evidence_hash(source_key: str) -> str:
    record = json.loads((EVIDENCE / "sprint-22c-source-rights.json").read_text(encoding="utf-8"))
    entry = next(item for item in record["sources"] if item["key"] == source_key)
    return str(entry["evidence_hash"])


def fixture_path(profile: ExtractionProfile, passage_id: str) -> Path:
    return proposals_directory(profile) / f"{passage_id}.json"


async def seal_live(
    passages: tuple[Passage, ...], profile: ExtractionProfile
) -> dict[str, dict[str, Any]]:
    """Call the provider once per passage and seal both halves of the answer."""
    from cognitive_os.providers.replay import request_fingerprint

    provider = live_provider()
    health = await provider.health_check()
    if health.status.value != "available":
        raise SystemExit(f"the live provider is not available: {health.message}")

    proposals_directory(profile).mkdir(parents=True, exist_ok=True)
    sealed: dict[str, dict[str, Any]] = {}
    for passage in passages:
        request = build_request(passage, profile)
        existing = fixture_path(profile, passage.passage_id)
        if existing.exists():
            stored = ReplayFixture.model_validate_json(existing.read_text(encoding="utf-8"))
            if stored.request_fingerprint == request_fingerprint(request):
                # The seal already answers *this* question. Re-asking would spend a call to
                # obtain a different answer to the same prompt, and then the record would
                # depend on which run wrote it.
                sealed[passage.passage_id] = {}
                continue
        response = await provider.complete(request)
        fixture = ReplayFixture(
            request_fingerprint=request_fingerprint(request),
            source_provider=provider.provider_id,
            response=response,
        )
        fixture_path(profile, passage.passage_id).write_text(
            fixture.model_dump_json(indent=1) + "\n", encoding="utf-8"
        )
        sealed[passage.passage_id] = {}
    return sealed


async def proposals(
    passages: tuple[Passage, ...], profile: ExtractionProfile, *, live: bool
) -> dict[str, dict[str, Any]]:
    """The campaign's sealed proposals, one per passage.

    A live run seals first and then replays its own seals, so the record a live run writes is
    the record a replay writes — otherwise "reproduced" would mean "reproduced except the
    first time".
    """
    if live:
        await seal_live(passages, profile)
    provider = replay_provider(profile)
    sealed: dict[str, dict[str, Any]] = {}
    for passage in passages:
        governed = await govern(passage, provider, profile, live=False)
        stored = json.loads(fixture_path(profile, passage.passage_id).read_text(encoding="utf-8"))
        sealed[passage.passage_id] = {
            **governed.as_sealed(),
            "origin_provider_id": stored["source_provider"],
            "sealed_fixture_sha256": _sha256(
                json.dumps(stored, sort_keys=True, separators=(",", ":")).encode()
            ),
            "replayed_through_the_released_provider_path": True,
            "live": False,
        }
    return sealed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="call the provider; §1.3's explicit opt-in"
    )
    parser.add_argument("--source", choices=sorted(EXTRACTION_PROFILES), default="physics")
    arguments = parser.parse_args()

    from chapter_22c import PROFILES

    profile = EXTRACTION_PROFILES[arguments.source]
    passages = locate_passages(PROFILES[arguments.source])
    sealed = asyncio.run(proposals(passages, profile, live=arguments.live))
    print(
        json.dumps(
            {
                "source": arguments.source,
                "template": profile.template,
                "passages": len(passages),
                "sealed_proposals": len(sealed),
                "live_call": arguments.live,
                "formalisable": sum(
                    1 for item in sealed.values() if item["answer"].get("formalisable")
                ),
                "refused_by_the_provider": sorted(
                    f"{key}:{value['answer'].get('reason')}"
                    for key, value in sealed.items()
                    if not value["answer"].get("formalisable")
                ),
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
