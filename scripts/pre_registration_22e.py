"""S22E-010 through S22E-016. Revision 1, frozen before any candidate exists.

Every predecessor pre-registered the thing it could otherwise bend. 22B froze readings, 22C
froze a decidable improvement claim, 22D froze an instrument it also authored. 22E's exposure
is different in kind and the plan says so in its own §1.2: **three of Gate M's ten conditions
do not hold or are ambiguous today**, and the sprint that reads the gate is the sprint that
would benefit from reading it generously. So the thing frozen here is not a threshold. It is
*which sealed record each condition is read from*, decided before a single number moved.

What this record publishes, and why each piece could otherwise bend:

* the **gate-owner decisions** (§2.1), both taken in W0 with the ledger in front of them and
  before any candidate was generated — condition 5's reading, and whether a `0016`-shaped
  repair may enter the ranked list;
* the **ten Gate M conditions**, each bound to a record and a dotted field path, with the rule
  that an unresolvable path *raises* rather than rendering false — a condition that quietly
  reads as unmet is indistinguishable from a condition nobody wired up;
* the **five §2.2 readings**, including what "zero active-state mutation" enumerates, which is
  derived from a released contract in `surface_22e` rather than typed out here;
* the **re-measurement licence**: a 22E number replaces a predecessor's sealed number only
  behind a repair that landed through the governed path first. Written down now because after
  W3 it would be a rationalisation.

`measured_values: 0`, and §2.3 forbids touching any of it afterwards.

    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/pre_registration_22e.py
    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/pre_registration_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from ledger_22e import ZERO_ZERO_SIXTEEN_IS_ELIGIBLE  # noqa: E402
from surface_22e import (  # noqa: E402
    ADDITIONAL_SURFACE_MEMBERS,
    SURFACE_CONTRACT,
    active_surface_members,
    contract_surface_members,
)

OUTPUTS = {
    "contracts": EVIDENCE / "sprint-22e-contracts.json",
    "pre_registration": EVIDENCE / "sprint-22e-pre-registration.json",
}

PRE_REGISTRATION_TIME = "2026-08-16T00:00:00Z"

#: The five exit sentences, from `execution-sprint-allocation.md`, verbatim. Retyped nowhere
#: else in this sprint's evidence: every later record points at these strings.
EXIT_CRITERIA = (
    "rejected proposals cause zero active-state mutation",
    "one approved change reaches protected `main` through PR and post-merge CI",
    "failed and successful experience is retained and retrievable",
    "all Gate M conditions pass",
    "`sprint-22-baseline` peels to the verified protected commit",
)

#: Gate M's ten conditions, from `development-plan.md` §11, verbatim.
GATE_M_CONDITIONS = (
    "Gate L2 passes",
    "Domain Registry v2 adds two domains without core branching",
    "the 10^6 capacity, maintenance, backup, and restore envelope passes",
    "three continual-learning cycles pass cross-domain anti-forgetting",
    "a rights-cleared source is acquired, verified, learned, and applied end to end",
    "bounded local English capability passes without a large external LLM",
    "large-LLM dependence falls by at least the declared threshold",
    "one governed self-improvement reaches protected `main`",
    "security, provider, migration, distribution, and repository-language gates pass",
    "post-merge `main` CI and the annotated `sprint-22-baseline` tag are verified",
)

#: §2.1 asks the gate owner for exactly two decisions and nothing else. Both were taken in W0,
#: with the sealed ledger visible and before any candidate existed. Recorded as *decisions*
#: rather than as conclusions, with the alternative each one rejected, because a reading that
#: does not say what it chose against is a reading nobody can audit.
GATE_OWNER_DECISIONS = {
    "condition_5_reading": {
        "question": "which sealed record does 'acquired, verified, learned, and applied end "
        "to end' read?",
        "decision": "22D's grounded holdout answers",
        "reads": "sprint-22d-w1-holdout-read.json",
        "verdict_under_this_reading": "holds",
        "rationale": (
            "the allocation's verb is 'applied' and the word 'improved' appears nowhere in "
            "condition 5; 22C's improvement arithmetic is 22C's own exit 5, a different "
            "sentence. Reading the improvement number into this condition would write a word "
            "into a frozen sentence, which §2.3 forbids in either direction"
        ),
        "rejected_alternatives": [
            {
                "reading": "22C's improvement arithmetic",
                "reads": "sprint-22c-w3-improvement.json",
                "verdict": "fails",
                "measured": "0 of 4 improvement, both arms",
            },
            {
                "reading": "both conjunctively",
                "verdict": "fails",
                "why_rejected": "also writes 'improved' into the frozen sentence, and makes "
                "the condition unreachable by anything §2.3 permits this sprint",
            },
        ],
        "the_risk_this_reading_carries": (
            "it is the reading that moves condition 5 from ambiguous to holding, and both "
            "numbers were already sealed and visible when it was taken. The mitigation is "
            "that the alternative and *its* verdict are published here and re-published in "
            "the W4 assessment, so a reader can apply either without re-deriving anything"
        ),
        "taken": "W0, before any candidate was generated",
    },
    "zero_zero_sixteen_eligibility": {
        "question": "may a repair that needs migration 0016 enter the ranked ledger?",
        "decision": "no — 0016 stays a refusal",
        "eligible": ZERO_ZERO_SIXTEEN_IS_ELIGIBLE,
        "excludes": "22D W2-F1, the LOCAL_API configuration class (ledger entry L5)",
        "rationale": (
            "22D W2-F1 touches no Gate M condition, so spending the one approved change there "
            "licenses no re-measurement; and a schema migration would put a second variable "
            "into the single governed traversal, leaving a failure ambiguous between the loop "
            "and the migration"
        ),
        "taken": "W0, before any candidate was generated",
    },
}

#: §1.2's rule, written before W3 rather than after it.
RE_MEASUREMENT_LICENCE = {
    "rule": (
        "a 22E re-measurement replaces a predecessor's sealed reading **only if** a released "
        "repair affecting that measurement has landed through the governed path first — PR to "
        "protected main, merged by the gate owner, green on post-merge exact-head CI"
    ),
    "what_cannot_change_a_verdict": "rereading a sealed number",
    "instrument": (
        "the frozen 22D hundred-task instrument, re-run per workload, with the landed repair "
        "as the only delta (22B W4-A1: measure the middle)"
    ),
    "each_condition_records": (
        "whether it read a predecessor's seal or a 22E re-measurement, and why"
    ),
}

#: 22E's plan contains no gate-owner amendment path beyond §2.1's two decisions, neither of
#: which moves a threshold. So this is structurally zero rather than merely unused.
AMENDMENTS_MADE_BY_22E = 0


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


class UnresolvableBinding(LookupError):
    """§2.2(d): an unresolvable path **raises** rather than rendering false.

    The distinction is the whole point. A condition that renders false because its record was
    renamed is indistinguishable, in a table of ten, from a condition that was measured and
    did not hold — and only one of those is a result. Raising makes the wiring failure loud
    and keeps `false` meaning "measured, and did not hold".
    """


def resolve_binding(record: str, path: str) -> Any:
    """Resolve `dotted.path` or `list[0].field` into a sealed record. Raises, never defaults.

    Defined here rather than in the W4 driver so that the path syntax the pre-registration
    publishes and the syntax W4 executes are the same code (22B W1-F2: import the recipe, do
    not retype it).
    """
    file = (EVIDENCE / record).resolve()
    if not file.exists():
        raise UnresolvableBinding(f"{record}: record does not exist")
    current: Any = json.loads(file.read_text(encoding="utf-8"))
    for part in path.split("."):
        key, _, index = part.partition("[")
        if key:
            if not isinstance(current, dict) or key not in current:
                raise UnresolvableBinding(f"{record}#{path}: no key {key!r}")
            current = current[key]
        if index:
            position = int(index.rstrip("]"))
            if not isinstance(current, list) or position >= len(current):
                raise UnresolvableBinding(f"{record}#{path}: no index {position}")
            current = current[position]
    return current


def verify_bindings() -> dict[str, Any]:
    """Prove every predecessor binding resolves **now**, in W0, not in W4.

    §3.1's discipline applied to the gate itself: the cheapest place to find a binding that
    points at nothing is the wave that writes it. Two of these did point at nothing when they
    were first drafted — `sprint-22d-preflight.json#gate_l2.conditions_passing`, which was
    never a field, and `sprint-22d-w1-holdout-read.json#holdout.grounded`, whose record keys
    the number as `arm_b_verified`. Both were wrong in the same way: written from what the
    plan's prose calls the number rather than from what the record calls it.
    """
    results = []
    for binding in _gate_m_bindings():
        if binding["source_kind"] == "this_sprint":
            results.append(
                {
                    "condition": binding["condition"],
                    "resolvable": None,
                    "why": "this sprint's record does not exist yet, by construction",
                }
            )
            continue
        paths = [
            binding["reads_path"],
            *([binding["also_reads_path"]] if "also_reads_path" in binding else []),
        ]
        values = {}
        for path in paths:
            values[path] = resolve_binding(binding["reads_record"], path)
        row = {
            "condition": binding["condition"],
            "resolvable": True,
            "record": binding["reads_record"],
            "values": values,
        }
        if "expected_value" in binding:
            row["matches_expected_value"] = (
                values[binding["reads_path"]] == binding["expected_value"]
            )
        results.append(row)
    return {
        "bindings": results,
        "predecessor_bindings_resolvable": all(
            item["resolvable"] for item in results if item["resolvable"] is not None
        ),
        "predecessor_values_as_expected": all(
            item.get("matches_expected_value", True) for item in results
        ),
        "this_sprint_bindings_deferred": sum(1 for item in results if item["resolvable"] is None),
    }


def _gate_m_bindings() -> list[dict[str, Any]]:
    """Each condition bound to the record and dotted path W4 will read it from.

    The binding is published now and executed in W4. Two things make it a binding rather than
    a note: the path is a *dotted field path* into a named record, and §2.2(d) requires an
    unresolvable path to raise. A condition that renders false because its path was renamed
    looks exactly like a condition that failed, and only one of those is a result.
    """
    return [
        {
            "condition": 1,
            "reads_record": "../../sprint-21/evidence/sprint-21d7-gate-l2.json",
            "reads_path": "counts.met",
            "also_reads_path": "counts.failed",
            "expected_value": 29,
            "reading": "D7's sealed close, the same record 22D's exit (e) reads",
            "expected_at_w0": "holds, 29 of 29",
            "source_kind": "predecessor_seal",
        },
        {
            "condition": 2,
            "reads_record": "sprint-22a-exit-criteria.json",
            "reads_path": "outcome",
            # The criterion whose sentence *is* condition 2, carried beside the outcome so the
            # binding names the specific exit rather than only the sprint's verdict. It
            # resolves to the criterion object, not to a boolean — 22A seals a `checks` map
            # and no `met` field, which is why the outcome is the decidable half.
            "also_reads_path": "criteria."
            "registers_without_changing_the_core_controller_or_storage_schema.decided_by",
            "expected_value": "pass",
            "reading": "22A's four exits, and the one that is literally 'without core branching'",
            "expected_at_w0": "holds",
            "source_kind": "predecessor_seal",
        },
        {
            "condition": 3,
            "reads_record": "sprint-22b-exit-criteria.json",
            "reads_path": "all_met",
            "also_reads_path": "outcome",
            "expected_value": True,
            "reading": "22B's five exits",
            "expected_at_w0": "holds, 5 of 5",
            "source_kind": "predecessor_seal",
        },
        {
            "condition": 4,
            "reads_record": "sprint-22c-exit-criteria.json",
            "reads_path": "criteria.every cycle replays all retained domains",
            "reading": "22C's replay exit specifically — *not* its outcome, which is a typed "
            "negative earned on a different exit (improvement) that condition 4 does not read",
            "expected_at_w0": "holds",
            "source_kind": "predecessor_seal",
        },
        {
            "condition": 5,
            "reads_record": "sprint-22d-w1-holdout-read.json",
            "reads_path": "arm_b_verified",
            "also_reads_path": "improvement",
            "expected_value": 4,
            "reading": GATE_OWNER_DECISIONS["condition_5_reading"]["decision"],
            "expected_at_w0": "holds, under the W0 gate-owner reading",
            "source_kind": "predecessor_seal",
            "frozen_by": "gate_owner_decisions.condition_5_reading",
        },
        {
            "condition": 6,
            "reads_record": "sprint-22d-exit-criteria.json",
            "reads_path": "criteria[1].met",
            "expected_value": False,
            "reading": "22D exit (b), local verified success against the 70 % floor",
            "expected_at_w0": "fails as sealed, 66 against 70",
            "source_kind": "predecessor_seal",
            "re_measurement_licensed_by": "a landed repair affecting local verified success "
            "(ledger L1)",
            "measured_ceiling_if_l1_lands": "local_model 66 -> at most 76, computed in W0 "
            "from the sealed per-task records with malformed answers subtracted; a ceiling, "
            "never a forecast",
        },
        {
            "condition": 7,
            "reads_record": "sprint-22d-exit-criteria.json",
            "reads_path": "criteria[2].met",
            "expected_value": False,
            "reading": "22D exit (c), calls or equivalent cost against the 25 % target",
            "expected_at_w0": "fails as sealed, calls -4 %, accounted cost +5.9 %",
            "source_kind": "predecessor_seal",
            "re_measurement_licensed_by": "a landed repair affecting calls or cost (ledger L2)",
        },
        {
            "condition": 8,
            "reads_record": "sprint-22e-w3-promotion.json",
            "reads_path": "post_merge_ci.conclusion",
            "reading": "this sprint's one approved change, merged and green at its exact head",
            "expected_at_w0": "22E's to earn",
            "source_kind": "this_sprint",
        },
        {
            "condition": 9,
            "reads_record": "sprint-22e-w4-gates.json",
            "reads_path": "lanes",
            "reading": "the CI lanes at the release head, re-read rather than quoted",
            "expected_at_w0": "holds, re-read not quoted",
            "source_kind": "this_sprint",
        },
        {
            "condition": 10,
            "reads_record": "sprint-22e-release.json",
            "reads_path": "tag.peels_to",
            "reading": "post-merge main CI, and sprint-22-baseline peeling to the verified "
            "protected commit",
            "expected_at_w0": "22E's to earn",
            "source_kind": "this_sprint",
        },
    ]


def _contracts() -> dict[str, Any]:
    return {
        "S22E-010": {
            "contract": "the five exit criteria, verbatim from the execution sprint allocation",
            "count": len(EXIT_CRITERIA),
            "criteria": list(EXIT_CRITERIA),
            "source": "docs/sprints/sprint-22/execution-sprint-allocation.md",
            "moved_by_22e": AMENDMENTS_MADE_BY_22E,
        },
        "S22E-011": {
            "reading": "(a) what 'zero active-state mutation' reads",
            "surface_contract": SURFACE_CONTRACT,
            "enumeration_derived_from": (
                "ActiveStateProtectionSnapshot.model_fields, not typed out beside it "
                "(22A W4-F1: a coverage word is an enumeration with a test asserting it)"
            ),
            "members": list(active_surface_members()),
            "contract_members": list(contract_surface_members()),
            "additional_members": list(ADDITIONAL_SURFACE_MEMBERS),
            "why_additional_members_exist": (
                "W0-F3 — the domain registry is data rather than a table since 22A, and the "
                "released snapshot contract has no field for it; a candidate that registered "
                "a domain would move none of the contract's five"
            ),
            "compared_by": (
                "surface_22e.compare, which recomputes every member's equality from two "
                "captures and never accepts an `unchanged: true` literal (22A W4-F2)"
            ),
            "at_least_one_rejection_is_real": (
                "a genuine provider-generated candidate refused at a genuine gate, not a "
                "fixture refusing a fixture"
            ),
            "captured_before_and_after": "every rejected proposal, without exception",
        },
        "S22E-012": {
            "reading": "(b) what 'one approved change' is",
            "chain": [
                "a repair drawn from the sealed ledger",
                "a proposal with a rollback plan",
                "a provider-assisted candidate in an isolated worktree",
                "a sandbox evaluation matrix",
                "regression, security, migration, packaging and rollback gates",
                "approval by the named user",
                "a PR to protected main",
                "merge by the gate owner",
                "post-merge exact-head CI",
            ],
            "count": 1,
            "why_not_two": (
                "§2.3 — the exit says one, and a second 'while we are here' is how a governed "
                "loop becomes an ungoverned habit"
            ),
            "no_provider_merges_tags_or_deploys": True,
            "asserted_by": "a test that the provider's authority ends at the proposal",
            "selection_authority": "the gate owner, in W3, from the sealed ledger",
            "the_plan_pre_selects_nothing": True,
        },
        "S22E-013": {
            "reading": "(c) what a dry run is, and what three of them cover",
            "a_dry_run_is": (
                "a complete lifecycle that stops short of merge — every stage entered in "
                "order through the released transitions, stage-skipping refused (22C's "
                "discipline), experience compiled at the end"
            ),
            "count": 3,
            "cover": "distinct weakness classes and distinct outcomes",
            "at_least_one_must_fail_its_own_evaluation": (
                "honestly, and be rejected on the evidence — a loop that has only ever "
                "succeeded has not been tested (22A W4-F2, applied to a process)"
            ),
            "rollback_is": (
                "a rollback executed in isolation, never a manifest that exists (D7 W3-F1)"
            ),
        },
        "S22E-014": {
            "reading": "(d) what 'all Gate M conditions pass' reads",
            "condition_count": len(GATE_M_CONDITIONS),
            "conditions": list(GATE_M_CONDITIONS),
            "source": "docs/sprints/sprint-22/development-plan.md §11, Gate M",
            "read_once": "in W4, at the release head",
            "bindings": _gate_m_bindings(),
            "an_unresolvable_path": "raises, and never renders false",
            "check_rebuilds_from_sources": True,
            "re_measurement_licence": RE_MEASUREMENT_LICENCE,
            "honest_starting_score": {
                "holds": 6,
                "holds_under_a_w0_reading": 1,
                "fails_as_sealed": 2,
                "to_be_earned_by_22e": 3,
                "note": (
                    "conditions 5 and 9 both appear once: 5 holds under the W0 reading, 9 is "
                    "counted as to-be-earned because it is re-read at this sprint's head "
                    "rather than inherited"
                ),
            },
        },
        "S22E-015": {
            "reading": "(e) what 'retained and retrievable' means",
            "both_kinds": ["the failed candidates'", "the approved change's"],
            "compiled_through": "the released Experience Compiler, into the EMG",
            "then": (
                "queried back out — the record shows a retrieval, from the store, whose "
                "content answers what was tried, what failed, and why, for one failure and "
                "one success"
            ),
            "why": "retention without a demonstrated read is a hope (D7 W3-F1)",
            "a_digest_is_not_a_read": True,
        },
        "S22E-016": {
            "reading": "the two gate-owner decisions §2.1 asks for, and nothing else",
            "decisions": GATE_OWNER_DECISIONS,
            "no_threshold_moves": True,
            "no_amendment_path_exists": True,
            "amendments_made_by_22e": AMENDMENTS_MADE_BY_22E,
        },
    }


def _record() -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": 1,
        "revision": 1,
        "items": sorted(_contracts()),
        "sprint": "22E",
        "outcome_tag": "sprint-22-baseline",
        "outcome_tag_is": (
            "the programme-level Sprint 22 tag, not a sprint-local one; annotated **after** "
            "the squash merge on the merged main head, never on the wave branch (22C's "
            "release lesson), and its peeling is itself an exit criterion"
        ),
        "negative_outcome_tag": "sprint-22e-evidence-baseline",
        "exit_criteria": list(EXIT_CRITERIA),
        "gate_m_conditions": list(GATE_M_CONDITIONS),
        "gate_owner_decisions": GATE_OWNER_DECISIONS,
        "re_measurement_licence": RE_MEASUREMENT_LICENCE,
        "amendments_made_by_22e": AMENDMENTS_MADE_BY_22E,
        "measured_values": 0,
        "why_amendments_are_structurally_zero": (
            "§2.1 asks the gate owner for two decisions and neither moves a threshold; §2.3 "
            "forbids rewriting any 22D exit sentence or 22C exit arithmetic, and no other "
            "amendment path exists in this plan"
        ),
        "weakness_ledger": {
            "record": "sprint-22e-weakness-ledger.json",
            "sealed_in": "W0, before any proposal existed",
            "the_plan_pre_selects_nothing": True,
            "one_entry_was_repriced_in_w0": "L4 (22B W3-F1) — W0-F1",
        },
        "migration_head": {
            "expected_revision": "0015",
            "0016_is": "a refusal, kept one by the W0 gate-owner decision",
        },
        "out_of_scope": [
            "any autonomous provider authority — merge, tag, deploy, active-memory write — "
            "anywhere, including 'just for the demo'",
            "rewriting any 22D exit sentence or 22C exit arithmetic",
            "Layer-1 scale-up, new acquisition campaigns, adapter training, any learner refit",
            "more than one approved change",
            "resolving 22C W3-A1 or 22C W2-A1",
            "any schema change beyond an explicitly selected 0016 candidate, which the W0 "
            "decision declined to permit",
            "tuning any pre-registered configuration after its first measured number exists",
        ],
        "recorded_at": PRE_REGISTRATION_TIME,
    }
    record["integrity_content_hash"] = _sha256(
        _canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-bindings", action="store_true")
    arguments = parser.parse_args()

    if arguments.verify_bindings:
        result = verify_bindings()
        print(json.dumps(result, indent=1, sort_keys=True))
        return (
            0
            if result["predecessor_bindings_resolvable"]
            and result["predecessor_values_as_expected"]
            else 1
        )

    built = {"contracts": _contracts(), "pre_registration": _record()}

    if arguments.check:
        results: dict[str, Any] = {}
        for key, path in OUTPUTS.items():
            if not path.exists():
                results[key] = {"present": False}
                continue
            stored = json.loads(path.read_text(encoding="utf-8"))
            results[key] = {"present": True, "rebuild_identical": stored == built[key]}
        stored_record = json.loads(OUTPUTS["pre_registration"].read_text(encoding="utf-8"))
        body = {k: v for k, v in stored_record.items() if k != "integrity_content_hash"}
        results["seal_recomputes"] = (
            _sha256(_canonical(body)) == stored_record["integrity_content_hash"]
        )
        results["measured_values_still_zero"] = stored_record["measured_values"] == 0
        results["amendments_still_zero"] = stored_record["amendments_made_by_22e"] == 0
        print(json.dumps(results, indent=1, sort_keys=True))
        ok = all(
            item.get("rebuild_identical") for item in results.values() if isinstance(item, dict)
        )
        return 0 if ok and results["seal_recomputes"] else 1

    for key, path in OUTPUTS.items():
        _write(path, built[key])
    record = built["pre_registration"]
    print(
        json.dumps(
            {
                "outputs": [path.name for path in OUTPUTS.values()],
                "items": record["items"],
                "exit_criteria": len(EXIT_CRITERIA),
                "gate_m_conditions": len(GATE_M_CONDITIONS),
                "gate_owner_decisions": sorted(GATE_OWNER_DECISIONS),
                "condition_5_reads": GATE_OWNER_DECISIONS["condition_5_reading"]["reads"],
                "zero_zero_sixteen_eligible": ZERO_ZERO_SIXTEEN_IS_ELIGIBLE,
                "surface_members": len(active_surface_members()),
                "measured_values": record["measured_values"],
                "amendments_made_by_22e": AMENDMENTS_MADE_BY_22E,
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
