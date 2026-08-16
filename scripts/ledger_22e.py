"""S22E-020. The weakness ledger, ranked, priced, and each entry reproduced rather than quoted.

§1.4 names five sealed findings as the mined field and says the plan pre-selects nothing. What
it *does* pre-select, unavoidably, is a price per entry — "roughly a dozen tasks per model arm",
"one line", "the cleanest low-risk candidate" — and a price written into a plan is a price
nobody measured. This driver refuses every one of those phrasings and re-derives the number:

* the notation entry is **probed live** through the released reader and the released verifier,
  one answer string per unit spelling, so "the units a model actually writes" is a pass/error
  pair rather than an assertion;
* the escalation entry is **counted** out of 22D's sealed per-task record, by joining each
  escalated task to its frozen output kind;
* the abstention entry is **summed** over every sealed arm record, and it is careful about
  which arms are model arms, because the model-free arm abstained ninety-six times and an
  unqualified total would read as the opposite of the finding;
* the crash-window entry is **read back out of 22C's sealed repair records**, which is where
  W0-F1 came from: the plan calls it "confirmed still unrepaired in released code", and half of
  it shipped in 22C. An entry whose price is stale is worse than an entry nobody wrote, because
  the ranking it feeds looks measured;
* the `LOCAL_API` entry is **introspected** off the released discriminated union.

The ranking is by measured expected benefit against the Gate M condition each entry touches,
and `eligible` is the W0 gate-owner rule rather than this file's opinion. Nothing here selects
a candidate: W3's selection is the gate owner's, and §2.1 is the reason this file stops at a
sealed, ordered, priced list.

**The live probe needs the `verification-physics` extra, and `--check` must not.** That is 22D
W4-F1, and it was reproduced here before it was fixed: the first version of this sealer raised
`VerifierUnavailableError` under the command line the main CI lane uses, which installs no
physics extra. Whether Pint is importable is a property of the interpreter this command happens
to run under, not a property of the ledger, so `probe_recomputed_when_available` is split off
the way `preflight_22d` splits observations from invariants — recomputed where it can be,
re-read where it cannot, and `--check` says in its own output which of the two it did.

    UV_CACHE_DIR=.cache/uv uv run --extra verification-physics python scripts/ledger_22e.py
    UV_CACHE_DIR=.cache/uv uv run --extra verification-physics python scripts/ledger_22e.py --check
    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/ledger_22e.py --check  # the CI lane
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from benchmark_22d import (  # noqa: E402
    FACTUAL_OUTPUT_KINDS,
    MINIMUM_LOCAL_SUCCESS_PERCENT,
    ArmOutcome,
    canonical,
    verify_answer,
)

OUTPUT = EVIDENCE / "sprint-22e-weakness-ledger.json"

#: Frozen with the ledger, not read from a clock. Every 22E record carries the same stamp so
#: that a rebuild is byte-identical (22B W1-F2, and the reason `--check` can mean anything).
LEDGER_TIME = "2026-08-16T00:00:00Z"

#: The W0 gate-owner decision, §2.1, taken before any candidate was generated. `False` means a
#: repair sitting behind migration `0016` may not enter the ranked list at all.
ZERO_ZERO_SIXTEEN_IS_ELIGIBLE = False

#: Whether the physics verifiers can actually run here. Not a fact about this ledger.
PHYSICS_AVAILABLE = find_spec("pint") is not None

#: The one block `--check` re-reads rather than recomputes when the extra is absent. Everything
#: else in the record is derived from sealed predecessor records and released introspection,
#: both of which are available under every command line.
RECOMPUTED_ONLY_WITH_THE_PHYSICS_EXTRA = "reproduction"

#: The sealed arm records this ledger prices against. The model-free arm is listed here **and**
#: excluded from the abstention denominator below, on purpose: it is an arm, it is not a model
#: arm, and conflating the two inverts the finding.
ARM_RECORDS = {
    "local_model": "sprint-22d-w3-local-model.json",
    "mixed_workload": "sprint-22d-w3-mixed-workload.json",
    "external_teacher": "sprint-22d-w2-external-teacher.json",
    "no_memory": "sprint-22d-w2-no-memory.json",
    "retrieval_only": "sprint-22d-w2-retrieval-only.json",
}
MODEL_ARMS = ("local_model", "mixed_workload", "external_teacher", "no_memory")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sealed(name: str) -> dict[str, Any]:
    """Load a predecessor's sealed record and *recompute its seal* before reading a number.

    A ledger priced off an unsealed record is a ledger priced off whatever was last written to
    that path. The seal is the only thing that makes the number the predecessor's.
    """
    path = EVIDENCE / name
    stored = json.loads(path.read_text(encoding="utf-8"))
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != stored.get("integrity_content_hash"):
        raise ValueError(f"{name}: sealed record does not recompute; refusing to price from it")
    return stored


# ---------------------------------------------------------------------------
# Entry 1. 22D W2-F2 — the notation tax, probed rather than described
# ---------------------------------------------------------------------------

#: One task per unit spelling, each chosen because the frozen hundred actually contains it.
#: `ascii` is the spelling the task's own verifier configuration uses; `written` is the
#: spelling 22D's probe recorded a model producing. Both go through the *released* reader, so
#: a spelling that fails because the reader refuses it is distinguished from one that fails
#: because the sealed unit registry cannot parse it — different defects, different repairs.
NOTATION_PROBES = (
    ("s22d-convert-15", "4700", "ohm", "Ω"),
    ("s22d-dimension-02", "1", "kg*m/s", "kg·m/s"),
    ("s22d-dimension-05", "1", "m/s**2", "m/s²"),
    ("s22d-dimension-08", "1", "kg/m**3", "kg/m³"),
    ("s22d-dimension-09", "1", "N*m", "N·m"),
    ("s22d-dimension-10", "1", "ohm", "Ω"),
)


async def _probe_notation() -> dict[str, Any]:
    if not PHYSICS_AVAILABLE:
        # A named refusal, never a traceback and never a silent empty probe. `--check` reads
        # the stored block in this mode and says so; `main()` refuses to *write* one.
        return {
            "probe_not_run": True,
            "reason": "the verification-physics extra is absent from this interpreter",
            "how_to_recompute": "uv run --extra verification-physics python "
            "scripts/ledger_22e.py --check",
        }

    from arms_22d import read_answer
    from tasks_22d import MICROBENCHMARK_TASKS

    by_id = {task["task_id"]: task for task in MICROBENCHMARK_TASKS}

    async def decide(task: Any, text: str) -> dict[str, Any]:
        answer, abstained, form_valid = read_answer(task, text)
        verified, undecidable = await verify_answer(
            task,
            ArmOutcome(
                task_id=task["task_id"],
                arm="_ledger_probe",
                answer=answer,
                abstained=abstained,
                citations=(),
                answer_form_valid=form_valid,
            ),
        )
        return {
            "answer_text": text,
            "reader_accepted_the_form": form_valid,
            "verified": verified,
            "undecidable": undecidable,
        }

    probes = []
    for task_id, magnitude, ascii_unit, written_unit in NOTATION_PROBES:
        task = by_id[task_id]
        ascii_result = await decide(task, f"{magnitude} {ascii_unit}")
        written_result = await decide(task, f"{magnitude} {written_unit}")
        probes.append(
            {
                "task_id": task_id,
                "verifier_id": str(task["verifier_id"]),
                "ascii_spelling": ascii_result,
                "written_spelling": written_result,
                # The defect in one predicate: the reader takes the answer, and the verifier
                # then cannot decide it. A spelling the reader refused would be a *different*
                # finding (a malformed answer), and 22D counts those apart on purpose.
                "notation_tax_reproduced": (
                    ascii_result["verified"]
                    and written_result["reader_accepted_the_form"]
                    and written_result["undecidable"]
                ),
            }
        )
    return {
        "probe_count": len(probes),
        "probes": probes,
        "every_probe_reproduces": all(item["notation_tax_reproduced"] for item in probes),
        "what_the_probe_shows": (
            "the released reader accepts the spelling a model writes and the sealed unit "
            "registry then errors on it, so the answer arrives at 'undecidable' for a reason "
            "that is not about the answer (22D W2-F2, W0-F1 one layer out)"
        ),
    }


def _notation_ceiling() -> dict[str, Any]:
    """The *upper bound* a notation repair could move each arm, and it is an upper bound.

    22D counts malformed answers apart from undecidable ones, and every malformed answer is
    also undecidable — the verifier is handed a string where it wants a quantity. So the tasks
    a notation repair could possibly recover are `undecidable \\ malformed`, and not one of
    them is guaranteed: 22D's own probe recorded `6 Ω` as *also the wrong answer*, and an
    undecidable verdict hides a wrong answer exactly as well as it hides a right one.

    Reporting it as a ceiling rather than as an expected gain is the whole discipline. A
    ledger that prices a repair at its best case and a gate that then reads the best case as
    a forecast is how a plan meets a threshold on paper.
    """
    arms = {}
    for arm in MODEL_ARMS:
        record = _sealed(ARM_RECORDS[arm])
        per_task = record["accounting"]["per_task"]
        undecidable = {key for key, value in per_task.items() if value["undecidable"]}
        malformed = set(record["malformed_task_ids"])
        verified = sum(1 for value in per_task.values() if value["verified"])
        recoverable = sorted(undecidable - malformed)
        arms[arm] = {
            "verified": verified,
            "undecidable": len(undecidable),
            "malformed": len(malformed),
            "malformed_is_a_subset_of_undecidable": malformed <= undecidable,
            "recoverable_ceiling": len(recoverable),
            "recoverable_task_ids": recoverable,
            "verified_at_the_ceiling": verified + len(recoverable),
        }
    local = arms["local_model"]
    return {
        "arms": arms,
        "floor": MINIMUM_LOCAL_SUCCESS_PERCENT,
        "local_model_reaches_the_floor_at_the_ceiling": (
            local["verified_at_the_ceiling"] >= MINIMUM_LOCAL_SUCCESS_PERCENT
        ),
        "why_a_ceiling_and_not_a_forecast": (
            "an undecidable verdict hides a wrong answer as well as a right one, so every "
            "recoverable task is a task that *might* verify once the notation parses; 22D "
            "recorded `6 Ω` as correct notation over a wrong magnitude"
        ),
    }


# ---------------------------------------------------------------------------
# Entry 2. 22D W3-F1 — escalation blind to output kind, counted
# ---------------------------------------------------------------------------


def _escalation_count() -> dict[str, Any]:
    from tasks_22d import MICROBENCHMARK_TASKS

    kinds = {task["task_id"]: str(task["output_kind"]) for task in MICROBENCHMARK_TASKS}
    factual = set(FACTUAL_OUTPUT_KINDS)
    arms = {}
    for arm in ("local_model", "mixed_workload"):
        per_task = _sealed(ARM_RECORDS[arm])["accounting"]["per_task"]
        escalated = [key for key, value in per_task.items() if value["escalated"]]
        needless = sorted(key for key in escalated if kinds[key] not in factual)
        by_kind: dict[str, int] = {}
        for key in needless:
            by_kind[kinds[key]] = by_kind.get(kinds[key], 0) + 1
        arms[arm] = {
            "tasks": len(per_task),
            "escalated": len(escalated),
            "escalated_without_being_a_factual_output": len(needless),
            "by_output_kind": dict(sorted(by_kind.items())),
        }
    return {
        "arms": arms,
        "factual_output_kinds": list(FACTUAL_OUTPUT_KINDS),
        "the_defect": (
            "escalate() reads grounded_span_count for every output, but the grounding exit "
            "reads only factual outputs; a closed-form computation is escalated for lacking a "
            "citation nothing ever asks it for"
        ),
        "why_it_touches_condition_7": (
            "every needless escalation is a call to the external teacher, and condition 7 is "
            "read off calls and accounted cost"
        ),
    }


# ---------------------------------------------------------------------------
# Entry 3. The abstention observation, summed over model arms only
# ---------------------------------------------------------------------------


def _abstention_count() -> dict[str, Any]:
    per_arm, answers, abstentions = {}, 0, 0
    for arm, name in ARM_RECORDS.items():
        accounting = _sealed(name)["accounting"]
        count = len(accounting["per_task"])
        per_arm[arm] = {
            "answers": count,
            "abstained": accounting["abstained"],
            "is_a_model_arm": arm in MODEL_ARMS,
        }
        if arm in MODEL_ARMS:
            answers += count
            abstentions += accounting["abstained"]
    return {
        "per_arm": per_arm,
        "model_arm_answers": answers,
        "model_arm_abstentions": abstentions,
        "no_model_arm_ever_abstained": abstentions == 0,
        "why_the_denominator_excludes_retrieval_only": (
            "the model-free arm abstained 96 times because it holds almost nothing to answer "
            "from; counting it would turn 'no model arm abstained in four hundred answers' "
            "into a total that reads as the opposite of the finding"
        ),
        "why_it_is_bounded": (
            "§2.3 forbids rewriting exit (d); the candidate is an answer-policy change "
            "that makes the released typed abstention reachable, never a second way to pass"
        ),
    }


# ---------------------------------------------------------------------------
# Entry 4. 22B W3-F1 — W0-F1. The plan's price is stale.
# ---------------------------------------------------------------------------


def _crash_window() -> dict[str, Any]:
    """**W0-F1.** §1.4 calls this "confirmed still unrepaired in released code". Half of it is.

    22C W1 landed and released the half that made the orphan *permanent*: the released service
    now asks the event stream rather than the record, so a resume repairs. What is still open
    is the two-transaction window itself, and 22C's own record says why it stayed open —
    closing it needs a transactional boundary `MemoryRepositoryPort` and `EventStorePort` do
    not share, which is a change to two released ports.

    So the entry is real and the *price* is wrong in both directions at once. The benefit the
    plan claims (`items_missing_an_event == 0`, provable by re-running an existing
    measurement) is **already true today** under a resume, and the residual reading — zero
    orphans after recovery, without a resume — is not reachable by a small change. Ranked as
    what it is rather than struck out: an entry whose repair is a two-port refactor is still a
    candidate, it is simply not the low-risk one the plan reached for.
    """
    crash = _sealed("sprint-22c-w1-crash.json")
    repair = _sealed("sprint-22c-w1-event-repair.json")
    return {
        "finding": "W0-F1",
        "plan_says": "confirmed still unrepaired in released code, the cleanest low-risk candidate",
        "released_code_says": {
            "the_permanence_half_shipped_in_22c": True,
            "released_service": "MemoryEventService.ensure_item_created, asked from "
            "MemoryService.create",
            "resume_repaired_the_orphan": repair["resume_repaired_the_orphan"],
            "resume_is_idempotent": repair["resume_is_idempotent"],
            "repair_closed_every_orphan": crash["repair_closed_every_orphan"],
            "items_missing_an_event_after_resume": crash["items_missing_an_event_after_resume"],
            "items_missing_an_event_after_recovery": crash["items_missing_an_event_after_recovery"],
        },
        "what_is_actually_still_open": (
            "the window: the record and its creation event are still two transactions, so a "
            "crash between them still leaves an orphan until something resumes that range"
        ),
        "why_it_is_not_low_risk": (
            "22C names the closure as needing a transactional boundary MemoryRepositoryPort "
            "and EventStorePort do not share — two released ports, not one released "
            "service; and §1.4 froze 0016 as a refusal, which is why 22C left it owed"
        ),
        "the_priced_benefit_is_therefore": (
            "zero measurable movement on the reading the plan names, because "
            "items_missing_an_event_after_resume is already 0 in 22C's sealed record; the "
            "only movement available is on the after-recovery reading, and that costs a "
            "two-port refactor"
        ),
        "touches_a_gate_m_condition": None,
        "reproduction": "scripts/repairs_22c.py --crash, and --orphan-repair for the "
        "deterministic planted orphan; 22C's crash record refuses a run where the window "
        "never opened",
    }


# ---------------------------------------------------------------------------
# Entry 5. 22D W2-F1 — LOCAL_API, introspected off the released union
# ---------------------------------------------------------------------------


def _local_api() -> dict[str, Any]:
    from cognitive_os.config.provider_config import ProviderAdapterConfig
    from cognitive_os.domain.provider import ProviderKind

    members = ProviderAdapterConfig.__origin__.__args__  # type: ignore[attr-defined]
    return {
        "local_api_is_a_released_provider_kind": ProviderKind.LOCAL_API in set(ProviderKind),
        "union_members": sorted(item.__name__ for item in members),
        "local_api_configuration_classes": sum(
            1 for item in members if item.model_fields["kind"].default is ProviderKind.LOCAL_API
        ),
        "released_adapter_kinds": sorted(
            {item.model_fields["kind"].default.value for item in members}
        ),
        "behind_a_check_constraint": True,
        "therefore_behind_migration": "0016",
        "eligible_under_the_w0_decision": ZERO_ZERO_SIXTEEN_IS_ELIGIBLE,
    }


# ---------------------------------------------------------------------------
# The ranked list
# ---------------------------------------------------------------------------


async def _entries() -> list[dict[str, Any]]:
    notation, ceiling = await _probe_notation(), _notation_ceiling()
    escalation, abstention = _escalation_count(), _abstention_count()
    crash, local_api = _crash_window(), _local_api()
    local = ceiling["arms"]["local_model"]

    return [
        {
            "entry_id": "L1",
            "finding": "22D W2-F2",
            "summary": "the registered physics verifiers error on the unit spellings a model "
            "writes",
            "weakness_class": "verifier_instrument",
            "risk_class": "low",
            "change_surface": "the sealed unit registry's accepted spellings, and the frozen "
            "answer-form contract that admits them",
            "expected_benefit": {
                "measured_from": "22D's sealed per-task records, malformed subtracted",
                "unit": "tasks recovered per model arm",
                "ceiling": {
                    arm: value["recoverable_ceiling"] for arm, value in ceiling["arms"].items()
                },
                "local_model_verified_now": local["verified"],
                "local_model_verified_at_the_ceiling": local["verified_at_the_ceiling"],
                "floor": ceiling["floor"],
                "crosses_the_floor_at_the_ceiling": ceiling[
                    "local_model_reaches_the_floor_at_the_ceiling"
                ],
                "is_a_ceiling_not_a_forecast": True,
            },
            "touches_a_gate_m_condition": 6,
            "reproduction": notation,
            "eligible": True,
        },
        {
            "entry_id": "L2",
            "finding": "22D W3-F1",
            "summary": "the escalation policy is blind to output kind and escalates "
            "computations for lacking a citation the grounding exit never reads",
            "weakness_class": "policy_decision_function",
            "risk_class": "low",
            "change_surface": "benchmark_22d.escalate, one predicate",
            "expected_benefit": {
                "measured_from": "22D's sealed per-task records joined to the frozen output kinds",
                "unit": "needless external escalations removed",
                "value": {
                    arm: value["escalated_without_being_a_factual_output"]
                    for arm, value in escalation["arms"].items()
                },
                "why_it_is_not_a_cost_forecast": (
                    "removing an escalation removes a teacher call, but the local answer then "
                    "stands on its own and condition 7 also reads non-inferior success; the "
                    "two move in opposite directions and only a re-measurement decides"
                ),
            },
            "touches_a_gate_m_condition": 7,
            "reproduction": escalation,
            "eligible": True,
        },
        {
            "entry_id": "L3",
            "finding": "22D abstention observation",
            "summary": "no model arm abstained once in four hundred answers, though exit (d) "
            "offers explicit uncertainty as a second way to pass",
            "weakness_class": "answer_policy",
            "risk_class": "moderate",
            "change_surface": "the answer policy that decides when the released typed "
            "abstention is emitted",
            "expected_benefit": {
                "measured_from": "every sealed arm record, model arms only",
                "unit": "abstentions available where an answer is unsupported",
                "value": abstention["model_arm_abstentions"],
                "out_of": abstention["model_arm_answers"],
                "why_the_benefit_is_unpriced": (
                    "an abstention is a failure for the success reading and a pass for the "
                    "grounding reading; which way condition 6 moves depends on which answers "
                    "abstain, and no sealed record answers that"
                ),
            },
            "touches_a_gate_m_condition": None,
            "reproduction": abstention,
            "eligible": True,
        },
        {
            "entry_id": "L4",
            "finding": "22B W3-F1",
            "summary": "the MemoryService.create two-transaction window is still open, but "
            "the orphan-permanence half shipped in 22C — the plan's price is stale",
            "weakness_class": "transactional_boundary",
            "risk_class": "high",
            "change_surface": "MemoryRepositoryPort and EventStorePort, a shared transactional "
            "boundary across two released ports",
            "expected_benefit": {
                "measured_from": "22C's sealed W1 repair and crash records",
                "unit": "items missing an event",
                "value_on_the_reading_the_plan_names": 0,
                "value_on_the_residual_reading": crash["released_code_says"][
                    "items_missing_an_event_after_recovery"
                ],
                "why_zero": crash["the_priced_benefit_is_therefore"],
            },
            "touches_a_gate_m_condition": None,
            "reproduction": crash,
            "eligible": True,
        },
        {
            "entry_id": "L5",
            "finding": "22D W2-F1",
            "summary": "ProviderKind.LOCAL_API is a released enum member with no configuration "
            "class behind it",
            "weakness_class": "released_contract_without_implementation",
            "risk_class": "moderate",
            "change_surface": "the provider discriminated union, plus a CheckConstraint and "
            "therefore migration 0016",
            "expected_benefit": {
                "measured_from": "introspection of the released discriminated union",
                "unit": "configuration classes behind a released provider kind",
                "value": local_api["local_api_configuration_classes"],
                "why_it_touches_no_condition": (
                    "no Gate M condition reads the provider union; spending the one approved "
                    "change here licenses no re-measurement"
                ),
            },
            "touches_a_gate_m_condition": None,
            "reproduction": local_api,
            "eligible": ZERO_ZERO_SIXTEEN_IS_ELIGIBLE,
            "ineligible_because": None
            if ZERO_ZERO_SIXTEEN_IS_ELIGIBLE
            else "the W0 gate-owner decision (§2.1) keeps 0016 a refusal, so a repair "
            "behind a CheckConstraint may not enter the ranked list",
        },
    ]


def _rank(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Eligible first, then the ones that touch a Gate M condition, then by risk.

    The ranking is published as a *rule* rather than as an order, because an order can be
    rearranged later and a rule cannot be rearranged without showing.
    """
    risk = {"low": 0, "moderate": 1, "high": 2}
    ordered = sorted(
        entries,
        key=lambda item: (
            not item["eligible"],
            item["touches_a_gate_m_condition"] is None,
            item["touches_a_gate_m_condition"] or 99,
            risk[item["risk_class"]],
            item["entry_id"],
        ),
    )
    return [{**item, "rank": index + 1} for index, item in enumerate(ordered)]


async def _record() -> dict[str, Any]:
    entries = _rank(await _entries())
    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22E-020"],
        "sprint": "22E",
        "wave": "W0",
        "ranking_rule": (
            "eligible before ineligible; then entries that touch a Gate M condition, lowest "
            "condition number first; then ascending risk class; then entry id"
        ),
        "zero_zero_sixteen_is_eligible": ZERO_ZERO_SIXTEEN_IS_ELIGIBLE,
        "entries": entries,
        "eligible_count": sum(1 for item in entries if item["eligible"]),
        "the_plan_pre_selects_nothing": (
            "§1.4. This file ranks and prices; W3's selection is the gate owner's, and "
            "the approval authority is the exit's whole point"
        ),
        "one_entry_was_repriced_in_w0": "L4 (22B W3-F1) — W0-F1",
        "measured_values_are_read_from": [
            *sorted(set(ARM_RECORDS.values())),
            "sprint-22c-w1-crash.json",
            "sprint-22c-w1-event-repair.json",
        ],
        "every_source_record_seal_recomputed_before_it_was_read": True,
        "recorded_at": LEDGER_TIME,
    }
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    record = asyncio.run(_record())
    if arguments.check:
        if not OUTPUT.exists():
            print(f"MISSING {OUTPUT}")
            return 1
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(canonical(body)) == stored["integrity_content_hash"]

        def _without_the_probe(payload: dict[str, Any]) -> dict[str, Any]:
            """Everything except the one block that needs the extra to recompute.

            The seal goes too, and only here: it is computed *over* the probe, so a rebuild
            that could not run the probe cannot reproduce it. `stored_seal_intact` above
            still checks the stored seal against the stored body, which is the question that
            matters — that the record on disk is the record that was sealed.
            """
            return {
                **{key: value for key, value in payload.items() if key != "integrity_content_hash"},
                "entries": [
                    {
                        key: value
                        for key, value in entry.items()
                        if key != RECOMPUTED_ONLY_WITH_THE_PHYSICS_EXTRA
                    }
                    for entry in payload["entries"]
                ],
            }

        if PHYSICS_AVAILABLE:
            identical = stored == record
        else:
            identical = _without_the_probe(stored) == _without_the_probe(record)
        print(
            json.dumps(
                {
                    "reproduced": identical and sealed,
                    "rebuild_identical": identical,
                    "stored_seal_intact": sealed,
                    "physics_extra_present": PHYSICS_AVAILABLE,
                    # Named, so a green in the CI lane cannot be read as a green over the
                    # probe. 22D W4-F1: the axis nobody keeps checking is the one that fails.
                    "live_probe_recomputed": PHYSICS_AVAILABLE,
                    "recorded_not_recomputed": []
                    if PHYSICS_AVAILABLE
                    else [f"entries[].{RECOMPUTED_ONLY_WITH_THE_PHYSICS_EXTRA}"],
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if identical and sealed else 1

    if not PHYSICS_AVAILABLE:
        # Writing the ledger is not the same act as checking it. A record whose reproduction
        # block says "probe not run" is not evidence, and sealing one would make the refusal
        # permanent under a hash.
        print(
            "REFUSED: the verification-physics extra is absent, so the live notation probe "
            "cannot run and this ledger would seal a refusal as if it were evidence. Re-run "
            "with: uv run --extra verification-physics python scripts/ledger_22e.py"
        )
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "entries": [
                    {
                        "rank": item["rank"],
                        "entry_id": item["entry_id"],
                        "finding": item["finding"],
                        "risk_class": item["risk_class"],
                        "condition": item["touches_a_gate_m_condition"],
                        "eligible": item["eligible"],
                    }
                    for item in record["entries"]
                ],
                "eligible_count": record["eligible_count"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
