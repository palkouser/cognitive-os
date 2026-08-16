"""S22D-300..302. W3: the local-model arm, the mixed workload, and the four measured exits.

W2 measured three baselines and left the fourth arm and the deployed composition to this wave.
Nothing here is a new instrument: `run_arm` still owns verification, accounting, escalation and
the citation walk, the readers still refuse rather than repair, and the retrieval predicate is
the one S22D-200 priced *before* any arm ran. What is new is two things and only two.

**The local model reads the acquired layer.** Where the layer holds the quantity a task asks
for, the fact is stated to the model and the span it was read from travels with the answer. The
rest of the hundred is answered exactly as `no_memory` answered it, which is what makes
`local_model` minus `no_memory` the layer's contribution and `local_model` minus
`retrieval_only` the model's — two different subtractions, and §2.2(b) reads the second.

**A citation is earned, not attached.** §3.1 predicted this sprint's slice finding would be
that *grounded* has no executable meaning for generated prose, and it is right: a runner that
staples the retrieved span onto whatever the model said would make every retrieved task
"grounded" while the walk happily resolves bytes that support nothing. So the span is attached
only when the answer **is** the value those bytes carry — checked twice, in bytes, by
`grounded_in`. This is stricter than §2.2(d) as frozen, which asks only that the walk resolve
the cited bytes. Stricter is allowed and looser is not; the record says so rather than leaving
a later reader to discover that the exit could have been passed by stapling.

**The mixed workload is the frozen escalation policy, executed.** `escalate` was fixed in W0 as
a decision function over three mechanical signals, before any measured number existed, and §2.3
forbids touching it now. It is applied as written — including to the seventy tasks whose output
kind the grounding exit never reads — and what that costs is W3-F1 rather than a threshold this
wave quietly moved.

    UV_CACHE_DIR=.cache/uv uv run --extra verification-physics python scripts/w3_22d.py \
        --arm local_model
    UV_CACHE_DIR=.cache/uv uv run --extra verification-physics python scripts/w3_22d.py --mixed
    UV_CACHE_DIR=.cache/uv uv run --extra verification-physics python scripts/w3_22d.py --exits
    UV_CACHE_DIR=.cache/uv uv run python scripts/w3_22d.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from arms_22d import (  # noqa: E402
    ARM_OUTPUTS,
    COVERAGE_OUTPUT,
    EXTERNAL_ATTEMPTS,
    MALFORMED,
    PROVIDER_FAILURES,
    RECEIPTS,
    TEACHER_OF_RECORD,
    ArmRefused,
    _ask_local,
    _external_service,
    _matches,
    _seal,
    _sha256,
    _write,
    build_prompt,
    build_retrieval_index,
    external_teacher_answerer,
    local_server,
    read_answer,
)
from benchmark_22d import (  # noqa: E402
    COST_REDUCTION_QUANTITIES,
    EXTERNAL_PROVIDER_IDS,
    FACTUAL_OUTPUT_KINDS,
    MINIMUM_COST_REDUCTION_PERCENT,
    MINIMUM_LOCAL_SUCCESS_PERCENT,
    MINIMUM_MARGIN_POINTS,
    MIXED_WORKLOAD,
    NON_INFERIORITY_MARGIN_POINTS,
    ArmOutcome,
    Citation,
    ExternalProviderRefused,
    canonical,
    escalate,
    local_benchmark_budget,
    readings_hash,
    refuse_external_providers,
    run_arm,
)
from model_runtime_22d import MODEL, REASONING_OF_RECORD, SAMPLING, SERVER_ARGS  # noqa: E402
from tasks_22d import MICROBENCHMARK_TASKS  # noqa: E402

LOCAL_OUTPUT = EVIDENCE / "sprint-22d-w3-local-model.json"
MIXED_OUTPUT = EVIDENCE / "sprint-22d-w3-mixed-workload.json"
EXITS_OUTPUT = EVIDENCE / "sprint-22d-w3-exits.json"

W3_OUTPUTS = (LOCAL_OUTPUT, MIXED_OUTPUT, EXITS_OUTPUT)


# ---------------------------------------------------------------------------
# S22D-301. Retrieval-augmented local inference, and a citation that is earned
# ---------------------------------------------------------------------------


def retrieve(task: Mapping[str, Any], facts: Sequence[Mapping[str, Any]]) -> Any:
    """The layer's answer to one task, or `None`.

    **The same predicate `retrieval_only` uses**, deliberately. S22D-200 priced this predicate's
    coverage at four of the hundred before any arm ran; swapping in a wider retriever now that
    the four is a measured number is exactly the tuning §2.3 forbids, and it would also destroy
    the only clean subtraction this sprint has — `local_model` against `retrieval_only` with the
    same index behind both, so what differs between them is the model and nothing else.
    """
    for fact in facts:
        if _matches(task, fact):
            return fact
    return None


def build_grounded_prompt(task: Mapping[str, Any], fact: Mapping[str, Any]) -> str:
    """The task, with what the layer holds stated ahead of it.

    The layer is a store of *facts*, not of chunks, so what is retrieved is the fact as W1
    recorded it — subject, quantity, value, unit — rather than a window of prose around the
    span. The span still travels with the answer as the citation; the prompt and the citation
    are two different things and conflating them is how a citation stops meaning anything.
    """
    unit = str(fact["unit"] or "").strip()
    value = f"{fact['value']} {unit}".strip()
    stated = f"the {fact['quantity']} of {fact['subject']} is {value}"
    return f"Retrieved from the acquired knowledge layer: {stated}.\n\n{build_prompt(task)}"


def grounded_in(answer: Any, fact: Mapping[str, Any], span: bytes) -> bool:
    """Whether this answer rests on those bytes. §3.1's predicted finding, answered mechanically.

    Two checks, both in bytes, neither of them a model judging a model:

    * the answer carries **the value the source states**, compared as a number so that `12.010`
      and `12.01` are the same claim and `12.011` is a different one; and where the answer
      carries a unit, it is the unit the layer holds — a right magnitude under a wrong unit is
      a wrong claim resting on nothing;
    * the cited span **contains that value**, so the bytes the walk will load are the bytes the
      claim came from rather than an arbitrary range that happens to resolve.

    A model that ignored the retrieved fact and answered from its weights gets no citation, and
    lands in the third §2.2(d) case as an ungrounded assertion. That is the honest reading: the
    sentence may even be correct, and nothing here can show it rested on a source.
    """
    if answer is None:
        return False
    if isinstance(answer, Mapping):
        magnitude, unit = str(answer.get("magnitude", "")), str(answer.get("unit", "")).strip()
        if unit and unit != str(fact["unit"] or "").strip():
            return False
    else:
        magnitude = str(answer)
    try:
        if Decimal(magnitude) != Decimal(str(fact["value"])):
            return False
    except (InvalidOperation, ValueError):
        return False
    return str(fact["value"]).encode("utf-8") in span


#: Per task: what the layer offered, what the model did with it, and why the span was or was
#: not attached. Recorded because "retrieval found nothing" and "retrieval found something the
#: model then ignored" are different facts about the layer, and only one of them is its fault.
RETRIEVAL_LOG: list[dict[str, Any]] = []


def local_model_answerer(facts: Sequence[Mapping[str, Any]], sources: Mapping[str, bytes]) -> Any:
    """The fourth arm: the cleared local model, with the acquired layer behind it."""

    def answer(arm: str, task: Mapping[str, Any]) -> ArmOutcome:
        fact = retrieve(task, facts)
        prompt = build_prompt(task) if fact is None else build_grounded_prompt(task, fact)
        text, input_tokens, output_tokens, seconds = _ask_local(prompt)
        parsed, abstained, form_valid = read_answer(task, text)
        if not form_valid:
            MALFORMED.setdefault(arm, []).append(str(task["task_id"]))
        citations: tuple[Citation, ...] = ()
        rests_on_the_span = False
        if fact is not None and not abstained and form_valid:
            key = f"{fact['source_key']}-ch{fact['chapter']}"
            data = sources[key]
            start, end = int(fact["span"]["start"]), int(fact["span"]["end"])
            span = data[start:end]
            rests_on_the_span = grounded_in(parsed, fact, span)
            if rests_on_the_span:
                citations = (
                    Citation(
                        source_id=key,
                        content_hash=_sha256(span),
                        start=start,
                        end=end,
                    ),
                )
        RETRIEVAL_LOG.append(
            {
                "task_id": str(task["task_id"]),
                "output_kind": str(task["output_kind"]),
                "layer_offered_a_fact": fact is not None,
                "subject": None if fact is None else fact["subject"],
                "answer_rests_on_the_span": rests_on_the_span,
                "abstained": abstained,
                "answer_form_valid": form_valid,
            }
        )
        return ArmOutcome(
            task_id=str(task["task_id"]),
            arm=arm,
            answer=None if abstained else parsed,
            abstained=abstained,
            citations=citations,
            answer_form_valid=form_valid,
            local_model_calls=1,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            local_compute_seconds=round(seconds, 3),
        )

    return answer


# ---------------------------------------------------------------------------
# S22D-302. The mixed workload: the frozen escalation policy, executed
# ---------------------------------------------------------------------------

#: One entry per task: what the local side produced, whether the frozen policy escalated it,
#: and which side's answer the workload kept.
ESCALATION_LOG: list[dict[str, Any]] = []


def mixed_answerer(local: Any, external: Any) -> Any:
    """Local first; the teacher only where `escalate` says so, and both sides accounted.

    The composition is deliberately dumb — there is no confidence estimate asked of the model,
    because a self-reported confidence is exactly the value a model will always produce (22C
    W3-D1, carried into `escalate`'s own docstring). The three signals the policy reads are
    produced by the runtime: the typed abstention, the count of grounding spans, and whether
    the answer has a form the task's verifier can decide at all.
    """

    async def answer(arm: str, task: Mapping[str, Any]) -> ArmOutcome:
        near = local("local_model", task)
        escalated = escalate(near)
        entry = {
            "task_id": str(task["task_id"]),
            "output_kind": str(task["output_kind"]),
            "escalated": escalated,
            "local_abstained": near.abstained,
            "local_grounded_spans": near.grounded_span_count,
            "local_answer_form_valid": near.answer_form_valid,
        }
        if not escalated:
            ESCALATION_LOG.append({**entry, "answered_by": "local_model"})
            return replace(near, arm=arm)
        far = await external("external_teacher", task)
        ESCALATION_LOG.append({**entry, "answered_by": "external_teacher"})
        if not far.answer_form_valid:
            MALFORMED.setdefault(arm, []).append(str(task["task_id"]))
        # Both sides are charged. The local call happened whether or not its answer was kept,
        # and a workload that billed only the answer it used would report a saving it did not
        # make — the same reading W2 took when it counted every failed external attempt.
        return ArmOutcome(
            task_id=str(task["task_id"]),
            arm=arm,
            answer=far.answer,
            abstained=far.abstained,
            citations=far.citations,
            answer_form_valid=far.answer_form_valid,
            external_provider_calls=far.external_provider_calls,
            local_model_calls=near.local_model_calls,
            input_tokens=near.input_tokens + far.input_tokens,
            output_tokens=near.output_tokens + far.output_tokens,
            local_compute_seconds=near.local_compute_seconds,
        )

    return answer


# ---------------------------------------------------------------------------
# Running the wave
# ---------------------------------------------------------------------------


def _runtime_of_record() -> dict[str, Any]:
    return {
        "model": MODEL["weight_file"],
        "quantization": MODEL["quantization"],
        "reasoning": REASONING_OF_RECORD,
        "sampling": dict(SAMPLING),
        "server_arguments": list(SERVER_ARGS),
        "weights_sha256": MODEL["publisher_lfs_oid"],
    }


async def run_local_model() -> dict[str, Any]:
    """S22D-301. The fourth arm on the frozen hundred, read once."""
    MALFORMED.pop("local_model", None)
    RETRIEVAL_LOG.clear()
    facts, sources = build_retrieval_index()
    answerer = local_model_answerer(facts, sources)
    with local_server():
        accounting = await run_arm("local_model", MICROBENCHMARK_TASKS, answerer, sources)
    malformed = sorted(MALFORMED.get("local_model", ()))
    offered = [item for item in RETRIEVAL_LOG if item["layer_offered_a_fact"]]
    rested = [item for item in offered if item["answer_rests_on_the_span"]]
    return _seal(
        {
            "schema_version": 1,
            "items": ["S22D-301"],
            "arm": "local_model",
            "tasks": len(MICROBENCHMARK_TASKS),
            "measured_values": len(MICROBENCHMARK_TASKS),
            "accounting": accounting.as_json(),
            "malformed_answers": len(malformed),
            "malformed_task_ids": malformed,
            "runtime": _runtime_of_record(),
            "retrieval": {
                "predicate": "the S22D-200 predicate, unchanged and unwidened",
                "layer_facts": len(facts),
                "tasks_the_layer_offered_a_fact_for": len(offered),
                "tasks_whose_answer_rested_on_the_span": len(rested),
                "per_task": RETRIEVAL_LOG,
                "why_the_predicate_was_not_widened": (
                    "S22D-200 priced this predicate's coverage at four of the hundred before "
                    "any arm ran. Widening it now that four is a measured number is the tuning "
                    "§2.3 forbids, and it would also destroy the one clean subtraction this "
                    "sprint has: local_model against retrieval_only with the same index behind "
                    "both, so what differs is the model"
                ),
            },
            "grounding_rule": {
                "rule": (
                    "the span is attached only where the answer carries the value the source "
                    "states, compared as a number, and the cited bytes contain that value"
                ),
                "is_stricter_than_the_frozen_reading": True,
                "what_the_frozen_reading_asks": (
                    "§2.2(d) asks only that the released walk resolve the cited source bytes. A "
                    "runner that stapled the retrieved span onto whatever the model said would "
                    "satisfy that reading exactly and mean nothing — the walk would resolve "
                    "bytes that support no part of the claim. Stricter is allowed and looser is "
                    "not, and saying so here beats a later reader discovering the exit could "
                    "have been passed by stapling"
                ),
            },
        }
    )


async def run_mixed_workload() -> dict[str, Any]:
    """S22D-302. Local inference with the frozen escalation policy in front of the teacher."""
    MALFORMED.pop(MIXED_WORKLOAD, None)
    ESCALATION_LOG.clear()
    RETRIEVAL_LOG.clear()
    RECEIPTS.clear()
    PROVIDER_FAILURES.clear()
    facts, sources = build_retrieval_index()
    service, config = _external_service()
    answerer = mixed_answerer(
        local_model_answerer(facts, sources), external_teacher_answerer(service, config)
    )
    with local_server():
        accounting = await run_arm(MIXED_WORKLOAD, MICROBENCHMARK_TASKS, answerer, sources)
    malformed = sorted(MALFORMED.get(MIXED_WORKLOAD, ()))
    escalated = [item for item in ESCALATION_LOG if item["escalated"]]
    by_kind: dict[str, int] = {}
    for item in escalated:
        by_kind[item["output_kind"]] = by_kind.get(item["output_kind"], 0) + 1
    only_reason_was_grounding = [
        item
        for item in escalated
        if not item["local_abstained"]
        and item["local_answer_form_valid"]
        and item["local_grounded_spans"] == 0
    ]
    return _seal(
        {
            "schema_version": 1,
            "items": ["S22D-302"],
            "workload": MIXED_WORKLOAD,
            "why_this_is_not_a_fifth_arm": (
                "§2.2 freezes `arms` as four and the pre-registration hashes that reading. The "
                "composition is named separately and scored by the same runner: a second runner "
                "would be a second set of accounting, and the whole point of the twenty-five "
                "per cent is that both sides of it were computed by one definition"
            ),
            "tasks": len(MICROBENCHMARK_TASKS),
            "measured_values": len(MICROBENCHMARK_TASKS),
            "accounting": accounting.as_json(),
            "malformed_answers": len(malformed),
            "malformed_task_ids": malformed,
            "runtime": _runtime_of_record(),
            "escalation": {
                "policy": (
                    "escalate(outcome) = outcome.abstained or outcome.grounded_span_count < "
                    "MINIMUM_GROUNDED_SPANS or not outcome.answer_form_valid"
                ),
                "frozen_in": "W0, before any measured number existed",
                "escalated": len(escalated),
                "escalated_by_output_kind": by_kind,
                "escalated_only_because_nothing_was_grounded": len(only_reason_was_grounding),
                "per_task": ESCALATION_LOG,
            },
            "governance": {
                "boundary": "cognitive_os.application.services.governed_teacher",
                "intended_use": "evaluation_evidence",
                "retention_mode": "none",
                "rights_decision": "unknown",
                "teacher": dict(TEACHER_OF_RECORD),
                "receipts": len(RECEIPTS),
                "receipts_digest": _sha256(canonical(RECEIPTS)),
                "attempts_per_task_limit": EXTERNAL_ATTEMPTS,
                "failed_attempts": len(PROVIDER_FAILURES),
                "why_the_same_teacher": (
                    "the reduction is read against W2's external_teacher arm, so the escalated "
                    "half of this workload must be served by the same provider and the same "
                    "prompt. A cheaper teacher here would be a reduction measured on a route "
                    "swap rather than on the local model"
                ),
            },
        }
    )


# ---------------------------------------------------------------------------
# S22D-300. The four measured exits, read once
# ---------------------------------------------------------------------------


def _stored(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ArmRefused(f"{path.name} is absent; the exits are read from sealed records only")
    stored = json.loads(path.read_text(encoding="utf-8"))
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != stored.get("integrity_content_hash"):
        raise ArmRefused(f"{path.name} is not sealed; an unsealed record decides no exit")
    return stored


def _percent_drop(baseline: float, measured: float) -> float:
    if baseline <= 0:
        return 0.0
    return round(100.0 * (baseline - measured) / baseline, 4)


def _divergences(left: Mapping[str, Any], right: Mapping[str, Any], task_ids: Sequence[str]) -> Any:
    divergent = sorted(
        task_id
        for task_id in task_ids
        if left[task_id]["verified"] != right[task_id]["verified"]
        or left[task_id]["abstained"] != right[task_id]["abstained"]
    )
    return {
        "tasks_compared": len(task_ids),
        "divergent_tasks": len(divergent),
        "divergent_task_ids": divergent,
        "verified_here": sum(int(left[task_id]["verified"]) for task_id in task_ids),
        "verified_there": sum(int(right[task_id]["verified"]) for task_id in task_ids),
    }


def read_stability(
    local_record: Mapping[str, Any],
    no_memory_record: Mapping[str, Any],
    mixed_record: Mapping[str, Any],
    teacher_record: Mapping[str, Any],
) -> Any:
    """Whether the same prompt produced the same answer twice — on both sides.

    **Observations, not invariants** (22B S22B-002): nothing recomputes them and no exit reads
    them. They are here because this wave got both for free and because either one, left
    unmeasured, would quietly turn every number above into a single sample.

    *The local side.* For the ninety-six tasks the layer offered nothing for, `local_model`'s
    prompt is **byte-identical** to the one `no_memory` was given in W2 — same weights, same
    quantization, same sampling, same seed. A divergence there could not be the layer, the
    prompt or the model; it would be the serving runtime, and a benchmark that assumed
    determinism would be reporting the scheduler.

    *The external side, and this is the one that matters.* Every escalated task re-asked the
    teacher the prompt W2 already asked it, through the same provider — so the mixed workload is
    an accidental **second run of the baseline** §2.2(c) measures the reduction and the
    non-inferiority margin against. The margin is three points and it is read against one run.
    """
    offered = {
        item["task_id"]
        for item in local_record["retrieval"]["per_task"]
        if item["layer_offered_a_fact"]
    }
    near = local_record["accounting"]["per_task"]
    escalated = sorted(
        item["task_id"] for item in mixed_record["escalation"]["per_task"] if item["escalated"]
    )
    local_side = _divergences(
        near, no_memory_record["accounting"]["per_task"], sorted(set(near) - offered)
    )
    external_side = _divergences(
        mixed_record["accounting"]["per_task"],
        teacher_record["accounting"]["per_task"],
        escalated,
    )
    return {
        "reading": "observation",
        "why_not_an_invariant": (
            "no exit reads either number and nothing recomputes them from a source of truth. "
            "They are recorded because a silent divergence on either side would make every "
            "other number in this wave a single sample rather than a measurement"
        ),
        "the_local_runtime": {
            **local_side,
            "identical_prompts": True,
            "repeated_itself": local_side["divergent_tasks"] == 0,
        },
        "the_external_teacher": {
            **external_side,
            "identical_prompts": True,
            "repeated_itself": external_side["divergent_tasks"] == 0,
            "net_movement_points": external_side["verified_here"] - external_side["verified_there"],
            "why_this_qualifies_the_non_inferiority_reading": (
                "the margin is three absolute points and it is read against a single run of the "
                "baseline. This is what a second run of that same baseline, on the same prompts "
                "through the same provider, did — so a difference the size of the margin is not "
                "distinguishable from the baseline moving. §2.3 forbids amending the margin "
                "after a measured number exists, so the exit is read as frozen and this is "
                "recorded beside it rather than folded into it"
            ),
        },
    }


def read_exits() -> dict[str, Any]:
    """**S22D-300.** Four exits, read once, from records that were sealed before this ran."""
    local_record = _stored(LOCAL_OUTPUT)
    no_memory_record = _stored(ARM_OUTPUTS["no_memory"])
    mixed_record = _stored(MIXED_OUTPUT)
    teacher_record = _stored(ARM_OUTPUTS["external_teacher"])
    local = local_record["accounting"]
    mixed = mixed_record["accounting"]
    teacher = teacher_record["accounting"]
    retrieval = _stored(ARM_OUTPUTS["retrieval_only"])["accounting"]
    no_memory = no_memory_record["accounting"]
    _stored(COVERAGE_OUTPUT)

    # (a) The construction, executed rather than audited.
    refusals = []
    for provider_id in EXTERNAL_PROVIDER_IDS:
        try:
            refuse_external_providers([provider_id])
        except ExternalProviderRefused:
            refusals.append({"provider_id": provider_id, "refused": True})
        else:  # pragma: no cover - the refusal is the point
            refusals.append({"provider_id": provider_id, "refused": False})
    budget = local_benchmark_budget()
    exit_a = {
        "criterion": "no large external LLM is called during the local microbenchmark",
        "read_as": "a construction, never an audit of what happened",
        "external_provider_calls_in_the_local_arm": local["external_provider_calls"],
        "enumerated_external_providers": list(EXTERNAL_PROVIDER_IDS),
        "every_enumerated_provider_refused": all(item["refused"] for item in refusals),
        "refusals": refusals,
        "maximum_provider_calls_in_the_budget": budget.maximum_provider_calls,
        "met": bool(
            local["external_provider_calls"] == 0
            and all(item["refused"] for item in refusals)
            and budget.maximum_provider_calls == 0
        ),
    }

    # (b) The absolute floor and the margin over the comparator.
    margin = round(local["verified_percent"] - retrieval["verified_percent"], 4)
    exit_b = {
        "criterion": "local verified success is at least 70% and at least 10 points above "
        "retrieval-only",
        "local_model_verified_percent": local["verified_percent"],
        "retrieval_only_verified_percent": retrieval["verified_percent"],
        "no_memory_verified_percent": no_memory["verified_percent"],
        "margin_points": margin,
        "minimum_local_success_percent": MINIMUM_LOCAL_SUCCESS_PERCENT,
        "minimum_margin_points": MINIMUM_MARGIN_POINTS,
        "floor_met": local["verified_percent"] >= MINIMUM_LOCAL_SUCCESS_PERCENT,
        "margin_met": margin >= MINIMUM_MARGIN_POINTS,
        "undecidable_tasks": {
            "local_model": local["undecidable"],
            "retrieval_only": retrieval["undecidable"],
            "external_teacher": teacher["undecidable"],
            "mixed_workload": mixed["undecidable"],
        },
        "undecidable_counts_as": "failure for every arm, and the count is reported",
        "what_this_subtraction_is_not": (
            "local_model minus retrieval_only isolates the model, not the layer. The layer's "
            "contribution is local_model minus no_memory, which the allocation never asks for "
            "and which is reported here beside it rather than substituted for it (W2-F3)"
        ),
        "layer_contribution_points": round(
            local["verified_percent"] - no_memory["verified_percent"], 4
        ),
        "met": bool(
            local["verified_percent"] >= MINIMUM_LOCAL_SUCCESS_PERCENT
            and margin >= MINIMUM_MARGIN_POINTS
        ),
    }

    # (c) The reduction, on both quantities separately, and the non-inferiority margin.
    call_drop = _percent_drop(teacher["external_provider_calls"], mixed["external_provider_calls"])
    cost_drop = _percent_drop(teacher["accounted_cost_units"], mixed["accounted_cost_units"])
    success_drop = round(teacher["verified_percent"] - mixed["verified_percent"], 4)
    exit_c = {
        "criterion": "large-LLM calls or equivalent cost fall at least 25% at non-inferior success",
        "baseline": "the external_teacher arm on the same hundred tasks, measured in W2",
        "quantities": list(COST_REDUCTION_QUANTITIES),
        "external_provider_calls": {
            "baseline": teacher["external_provider_calls"],
            "mixed": mixed["external_provider_calls"],
            "reduction_percent": call_drop,
            "met": call_drop >= MINIMUM_COST_REDUCTION_PERCENT,
        },
        "accounted_cost_units": {
            "baseline": teacher["accounted_cost_units"],
            "mixed": mixed["accounted_cost_units"],
            "reduction_percent": cost_drop,
            "met": cost_drop >= MINIMUM_COST_REDUCTION_PERCENT,
        },
        "non_inferiority": {
            "baseline_verified_percent": teacher["verified_percent"],
            "mixed_verified_percent": mixed["verified_percent"],
            "absolute_drop_points": success_drop,
            "margin_points": NON_INFERIORITY_MARGIN_POINTS,
            "met": success_drop <= NON_INFERIORITY_MARGIN_POINTS,
        },
        "why_both_quantities_are_reported": (
            "so a reduction cannot be claimed on whichever moved further. Both must clear the "
            "target, and a workload that beats the cost target while falling outside the "
            "non-inferiority margin is a failed exit rather than a trade-off to narrate"
        ),
        "met": bool(
            call_drop >= MINIMUM_COST_REDUCTION_PERCENT
            and cost_drop >= MINIMUM_COST_REDUCTION_PERCENT
            and success_drop <= NON_INFERIORITY_MARGIN_POINTS
        ),
    }

    # (d) The binary, over every factual output.
    factual = [task for task in MICROBENCHMARK_TASKS if task["output_kind"] in FACTUAL_OUTPUT_KINDS]
    by_arm = {
        "local_model": local,
        "mixed_workload": mixed,
        "external_teacher": teacher,
        "retrieval_only": retrieval,
        "no_memory": no_memory,
    }
    exit_d = {
        "criterion": "factual output is grounded or explicitly uncertain",
        "factual_output_kinds": list(FACTUAL_OUTPUT_KINDS),
        "factual_outputs": len(factual),
        "dispositions": {
            arm: {
                "grounded": row["grounded"],
                "typed_abstention": row["abstained"],
                "ungrounded_assertions": row["ungrounded_assertions"],
            }
            for arm, row in by_arm.items()
        },
        "read_over": ["local_model", "mixed_workload"],
        "why_those_two": (
            "they are the systems this sprint proposes. The three W2 baselines are reported "
            "beside them because a count that only ever appears for the proposal reads as a "
            "property of the proposal rather than of the hundred"
        ),
        "ungrounded_assertions": {
            "local_model": local["ungrounded_assertions"],
            "mixed_workload": mixed["ungrounded_assertions"],
        },
        "met": bool(local["ungrounded_assertions"] == 0 and mixed["ungrounded_assertions"] == 0),
    }

    exits = {"a": exit_a, "b": exit_b, "c": exit_c, "d": exit_d}
    met = [key for key, value in exits.items() if value["met"]]
    return _seal(
        {
            "schema_version": 1,
            "items": ["S22D-300"],
            "read_once": True,
            "sources": [path.name for path in (LOCAL_OUTPUT, MIXED_OUTPUT, *ARM_OUTPUTS.values())],
            "readings_hash": readings_hash(),
            "stability": read_stability(
                local_record, no_memory_record, mixed_record, teacher_record
            ),
            "exits": exits,
            "exits_met": met,
            "exits_read_here": ["a", "b", "c", "d"],
            "exit_e_is_not_read_here": (
                "§2.2(e) re-reads the prior domain, learning and safety gates from their sealed "
                "records against this sprint's head, and §3's wave table gives that to W4"
            ),
            "outcome": "pass" if len(met) == 4 else "typed_negative",
            "what_a_typed_negative_is": (
                "a measured result with the same falsifiability a pass would have had: every "
                "number below was produced by an instrument frozen before it ran, and a failed "
                "exit here is a fact about the system rather than a wave that ran out of time "
                "(22C, whose negative this sprint's §0 carries as precedent)"
            ),
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def check() -> int:
    findings: list[str] = []
    report: dict[str, Any] = {}
    for path in W3_OUTPUTS:
        if not path.exists():
            report[path.name] = {"present": False}
            continue
        stored = json.loads(path.read_text(encoding="utf-8"))
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(canonical(body)) == stored.get("integrity_content_hash")
        report[path.name] = {"present": True, "sealed": sealed}
        if not sealed:
            findings.append(f"{path.name} is not sealed")
    if EXITS_OUTPUT.exists():
        stored = json.loads(EXITS_OUTPUT.read_text(encoding="utf-8"))
        # The exits rebuild from the arm records rather than being restated: a reading that
        # cannot be recomputed is an observation, and §2.2 asks these four to be invariants.
        rebuilt = read_exits()
        identical = rebuilt["integrity_content_hash"] == stored["integrity_content_hash"]
        report["exits_rebuild_identically"] = identical
        if not identical:
            findings.append("the exit readings do not rebuild from the sealed arm records")
    report["findings"] = findings
    print(json.dumps(report, indent=1, sort_keys=True))
    return 1 if findings else 0


def _summary(record: Mapping[str, Any]) -> dict[str, Any]:
    accounting = record["accounting"]
    return {
        "verified": accounting["verified"],
        "abstained": accounting["abstained"],
        "grounded": accounting["grounded"],
        "ungrounded_assertions": accounting["ungrounded_assertions"],
        "undecidable": accounting["undecidable"],
        "escalated": accounting["escalated"],
        "external_provider_calls": accounting["external_provider_calls"],
        "accounted_cost_units": accounting["accounted_cost_units"],
        "malformed_answers": record["malformed_answers"],
        "integrity_content_hash": record["integrity_content_hash"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("local_model",))
    parser.add_argument("--mixed", action="store_true", help="run the mixed workload")
    parser.add_argument("--exits", action="store_true", help="read the four measured exits once")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        return check()
    if arguments.arm:
        record = asyncio.run(run_local_model())
        _write(LOCAL_OUTPUT, record)
        print(json.dumps(_summary(record), indent=1, sort_keys=True))
        return 0
    if arguments.mixed:
        if not LOCAL_OUTPUT.exists():
            raise ArmRefused(
                "the local_model arm has not been sealed. The workload's local half is the arm "
                "§2.2(b) reads, and running the composition first would leave the arm to be "
                "reported from inside it"
            )
        record = asyncio.run(run_mixed_workload())
        _write(MIXED_OUTPUT, record)
        print(json.dumps(_summary(record), indent=1, sort_keys=True))
        return 0
    if arguments.exits:
        record = read_exits()
        _write(EXITS_OUTPUT, record)
        print(
            json.dumps(
                {
                    "outcome": record["outcome"],
                    "exits_met": record["exits_met"],
                    "integrity_content_hash": record["integrity_content_hash"],
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0
    parser.error("choose --arm local_model, --mixed, --exits or --check")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
