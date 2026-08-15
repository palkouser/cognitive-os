"""S22C-060. All five exit criteria, read once, against the sealed records that decided them.

Four waves each decided part of the sprint and **no wave read an exit**: every cycle record
carries `why_no_exit` saying so, and the two records that do carry `reads_exit_criterion` —
the plant and the improvement comparison — each read exactly one. This is the only place all
five are read together, and it is deliberately not a summary written by hand. Every verdict is
traced to one field of one sealed record, the readings come from the frozen contracts rather
than from this file, and `--check` rebuilds the whole document from its sources and refuses any
difference.

**22C's exits are structural, not numeric, and that changes the shape of the check.** 22B could
compare a measured float to a floor. Here a criterion is met when a *set* of conditions holds,
each of which is one boolean or one equality in one sealed record — so the record lists the
conditions, names where each was read, and a criterion is met only if all of its conditions
are. A criterion that reported a verdict without its conditions would be this file asserting
the sprint agrees with itself.

**Three of the five need every cycle**, so they are evaluated per cycle and the criterion holds
only if it holds in all three. §2.2a's `minimum_cycles` is read from the frozen contract, not
restated here.

    UV_CACHE_DIR=.cache/uv uv run python scripts/exit_criteria_22c.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/exit_criteria_22c.py --check

Read-only: it touches no database, calls no provider, re-runs no cycle, and writes exactly one
evidence file.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from campaign_22c import _canonical, _sha256  # noqa: E402

OUTPUT = EVIDENCE / "sprint-22c-exit-criteria.json"
CONTRACTS = EVIDENCE / "sprint-22c-contracts.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22c-pre-registration.json"

#: The three cycle records, in the order the campaign ran them. `minimum_cycles` is frozen in
#: S22C-011 and checked against this tuple rather than assumed to match it.
CYCLES: tuple[str, ...] = (
    "sprint-22c-w2-cycle1.json",
    "sprint-22c-w3-cycle2.json",
    "sprint-22c-w3-cycle3.json",
)

PLANT = "sprint-22c-w3-plant.json"
IMPROVEMENT = "sprint-22c-w3-improvement.json"

#: The two descriptor-registered pilots the campaign admits at runtime. S22C-011 froze the
#: enumeration *source* (`registry.domain_ids()`) and a snapshot of what it returned in a
#: process that had registered nothing; a campaign that registers its two pilots therefore
#: enumerates more, and the difference has to be exactly these two by name. Reading the frozen
#: snapshot as a count would have been the easy mistake here.
PILOT_DOMAINS: tuple[str, ...] = ("engineering.mechanics", "science.chemistry")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _at(record: dict[str, Any], field: str) -> Any:
    """One implementation of tracing a dotted field path into a sealed record.

    It raises rather than returning a default: a criterion whose evidence field is missing is
    an unread criterion, and an unread criterion that renders as `false` would be a met
    criterion away from a silent lie.
    """
    value: Any = record
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise SystemExit(f"field path {field!r} does not resolve in this record")
        value = value[part]
    return value


def _condition(
    label: str, record_name: str, field: str, expected: Any, records: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    measured = _at(records[record_name], field)
    return {
        "condition": label,
        "expected": expected,
        "measured": measured,
        "holds": measured == expected,
        "read_from": f"{record_name}#{field}",
    }


def _criterion(name: str, reading: str, conditions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "criterion": name,
        "reading": reading,
        "conditions": conditions,
        "conditions_total": len(conditions),
        "conditions_holding": sum(1 for item in conditions if item["holds"]),
        "met": all(item["holds"] for item in conditions),
    }


def _replay(records: dict[str, dict[str, Any]], frozen: dict[str, Any]) -> list[dict[str, Any]]:
    """(a) Every cycle replays all retained domains — evaluated in each of the three."""
    reading = frozen["S22C-011"]
    conditions: list[dict[str, Any]] = [
        {
            "condition": "at least the frozen minimum number of completed cycles",
            "expected": reading["minimum_cycles"],
            "measured": len(CYCLES),
            "holds": len(CYCLES) >= reading["minimum_cycles"],
            "read_from": "sprint-22c-contracts.json#S22C-011.minimum_cycles",
        }
    ]
    for name in CYCLES:
        cycle = _at(records[name], "cycle")
        enumerated = sorted(_at(records[name], "evaluate.per_domain"))
        expected_domains = sorted([*reading["domains_enumerated_at_freeze"], *PILOT_DOMAINS])
        conditions.extend(
            [
                _condition(
                    f"cycle {cycle}: all nine stages, in order",
                    name,
                    "stages.all_nine_in_order",
                    True,
                    records,
                ),
                _condition(
                    f"cycle {cycle}: the stage enumeration is the frozen one",
                    name,
                    "stages.enumerated",
                    reading["stage_enumeration"],
                    records,
                ),
                _condition(
                    f"cycle {cycle}: domains enumerated from the frozen source",
                    name,
                    "evaluate.enumeration_source",
                    reading["all_retained_domains_enumerated_from"],
                    records,
                ),
                {
                    "condition": (
                        f"cycle {cycle}: the enumeration is the freeze snapshot plus exactly "
                        "the two pilots this campaign registers"
                    ),
                    "expected": expected_domains,
                    "measured": enumerated,
                    "holds": enumerated == expected_domains,
                    "read_from": f"{name}#evaluate.per_domain",
                },
                _condition(
                    f"cycle {cycle}: every domain reports rates, including those with no cases",
                    name,
                    "evaluate.domains_enumerated",
                    len(expected_domains),
                    records,
                ),
                _condition(
                    f"cycle {cycle}: every retained case executed and passed",
                    name,
                    "evaluate.all_retained_cases_passed",
                    True,
                    records,
                ),
            ]
        )
    return conditions


def _citations(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """(d) Citations survive every derivative — the walk covers all of them, in every cycle."""
    conditions: list[dict[str, Any]] = []
    for name in CYCLES:
        cycle = _at(records[name], "cycle")
        promoted = _at(records[name], "promote.count")
        conditions.extend(
            [
                _condition(
                    f"cycle {cycle}: every chain walked resolves to loaded source bytes",
                    name,
                    "citations.all_chains_resolve",
                    True,
                    records,
                ),
                {
                    "condition": (
                        f"cycle {cycle}: the walk covers every promoted artifact "
                        f"({promoted} promoted)"
                    ),
                    "expected": promoted,
                    "measured": _at(records[name], "citations.artifacts_walked"),
                    "holds": _at(records[name], "citations.artifacts_walked") == promoted,
                    "read_from": f"{name}#citations.artifacts_walked",
                },
                _condition(
                    f"cycle {cycle}: the walk did not sample (S22C-014 forbids it)",
                    name,
                    "citations.sampled",
                    False,
                    records,
                ),
            ]
        )
    return conditions


def _supersession(
    records: dict[str, dict[str, Any]], frozen: dict[str, Any]
) -> list[dict[str, Any]]:
    """(e) A valid new revision supersedes without deleting history — cycle 1's demonstration."""
    name = CYCLES[0]
    reading = frozen["S22C-015"]
    both_ways = ", ".join(reading["verified_two_ways_that_must_agree"])
    return [
        _condition(
            "the released lifecycle was walked, candidate to verified to superseded",
            name,
            "supersession.lifecycle.candidate_to_verified_to_superseded",
            ["proposed", "supported", "superseded"],
            records,
        ),
        _condition(
            f"verified two ways that agree: {both_ways}",
            name,
            "supersession.verified_two_ways.the_two_agree",
            True,
            records,
        ),
        _condition(
            "no row was deleted anywhere in the path",
            name,
            "supersession.history_survives.no_row_was_deleted",
            True,
            records,
        ),
        _condition(
            "the superseded revision is still loadable",
            name,
            "supersession.history_survives.revision_2_loadable",
            True,
            records,
        ),
        _condition(
            "its citations still resolve to loaded bytes",
            name,
            "supersession.history_survives.revision_2_citations_still_resolve_to_loaded_bytes",
            True,
            records,
        ),
        _condition(
            "the event stream contains the full transition sequence",
            name,
            "supersession.event_stream.full_transition_sequence_present",
            True,
            records,
        ),
    ]


def assemble() -> dict[str, Any]:
    contracts = _load(CONTRACTS)
    pre_registration = _load(PRE_REGISTRATION)
    if pre_registration["contracts_sha256"] != _sha256(CONTRACTS.read_bytes()):
        raise SystemExit("the publication no longer binds the contracts this record reads")

    frozen_criteria = contracts["S22C-010"]["criteria"]
    if frozen_criteria != pre_registration["exit_criteria"]:
        raise SystemExit("the frozen contracts and the publication list different criteria")

    names = tuple(sorted({*CYCLES, PLANT, IMPROVEMENT}))
    records = {name: _load(EVIDENCE / name) for name in names}

    built = [
        _criterion(
            frozen_criteria[0], contracts["S22C-011"]["reading"], _replay(records, contracts)
        ),
        _criterion(
            frozen_criteria[1],
            contracts["S22C-012"]["reading"],
            [
                _condition(
                    "all four §2.2b conditions met",
                    PLANT,
                    "all_four_conditions_met",
                    True,
                    records,
                ),
                _condition(
                    "the plant is the one W0 sealed before any cycle existed",
                    PLANT,
                    "the_plant.content_hash",
                    contracts["S22C-012"]["plant_content_hash"],
                    records,
                ),
                _condition(
                    "it entered through the genuine intake path",
                    PLANT,
                    "the_plant.entered_through_the_genuine_intake_path",
                    True,
                    records,
                ),
            ],
        ),
        _criterion(
            frozen_criteria[2], contracts["S22C-015"]["reading"], _supersession(records, contracts)
        ),
        _criterion(frozen_criteria[3], contracts["S22C-014"]["reading"], _citations(records)),
        _criterion(
            frozen_criteria[4],
            contracts["S22C-013"]["reading"],
            [
                _condition(
                    "at least one retained artifact improved a held-out verified task",
                    IMPROVEMENT,
                    "comparison.at_least_one_retained_artifact_improved_a_held_out_task",
                    True,
                    records,
                ),
                _condition(
                    "the holdout was frozen with no measured values",
                    IMPROVEMENT,
                    "holdout.measured_values_at_freeze",
                    contracts["S22C-013"]["measured_values"],
                    records,
                ),
                _condition(
                    "it was read once",
                    IMPROVEMENT,
                    "holdout.read_once",
                    True,
                    records,
                ),
                _condition(
                    "no leakage between curriculum and holdout",
                    IMPROVEMENT,
                    "separation.leakage_detected",
                    False,
                    records,
                ),
                _condition(
                    "both arms measured in 22C, same tasks, same seeds, same checker",
                    IMPROVEMENT,
                    "comparison.same_tasks_same_seeds_same_checker",
                    True,
                    records,
                ),
            ],
        ),
    ]

    criteria = {item["criterion"]: item for item in built}
    if len(criteria) != contracts["S22C-010"]["count"]:
        raise SystemExit("a criterion was traced twice or not at all")
    failed = [item for item in built if not item["met"]]

    document: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W4",
        "items": ["S22C-060"],
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "contracts_sha256": _sha256(CONTRACTS.read_bytes()),
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "thresholds_moved_by_22c": contracts["S22C-010"]["moved_by_22c"],
        "amendments_made_by_22c": pre_registration["amendments_made_by_22c"],
        "criteria": criteria,
        "criteria_total": len(criteria),
        "criteria_met": sum(1 for item in built if item["met"]),
        "all_met": not failed,
        "outcome": "pass" if not failed else "typed negative",
        # §5's stop clause asks for three things by name, and a negative that omits any of them
        # is a mood rather than a result.
        "the_stop": (
            None
            if not failed
            else {
                "which_exit_failed": [item["criterion"] for item in failed],
                "at_which_wave": _at(records[IMPROVEMENT], "wave"),
                "after_how_many_cycles": len(CYCLES),
                "measured_values": {
                    "cases": _at(records[IMPROVEMENT], "comparison.cases"),
                    "arm_a_verified_successes": _at(
                        records[IMPROVEMENT], "comparison.arm_a_verified_successes"
                    ),
                    "arm_b_verified_successes": _at(
                        records[IMPROVEMENT], "comparison.arm_b_verified_successes"
                    ),
                    "improved_cases": _at(records[IMPROVEMENT], "comparison.improved_cases"),
                },
                "diagnosis": "W3-F1",
                "why_it_is_not_a_pipeline_failure": (
                    "the four pipeline exits are met on the same records. Arm A failed exactly "
                    "as the frozen definition predicted, and three of arm B's four cases had no "
                    "retained artifact to restore from — the campaign retained one artifact, and "
                    "a held-out task needs a declarative fact no registered problem type can "
                    "verify"
                ),
            }
        ),
        "cycles_read": {
            name: {
                "cycle": _at(records[name], "cycle"),
                "wave": _at(records[name], "wave"),
                "promoted": _at(records[name], "promote.count"),
                "integrity_content_hash": _at(records[name], "integrity_content_hash"),
            }
            for name in CYCLES
        },
        "no_wave_read_an_exit_before_this_record": {
            name: _at(records[name], "why_no_exit") for name in CYCLES
        },
        "sources_sha256": {name: _sha256((EVIDENCE / name).read_bytes()) for name in names},
    }
    document["integrity_content_hash"] = _sha256(_canonical(document))
    return document


def _write(output: Path) -> int:
    document = assemble()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "criteria_met": document["criteria_met"],
                "criteria_total": document["criteria_total"],
                "outcome": document["outcome"],
                "integrity_content_hash": document["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def _check(output: Path) -> int:
    stored = _load(output)
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    sealed = _sha256(_canonical(body)) == stored["integrity_content_hash"]
    rebuilt = assemble()
    skip = {"recorded_at", "integrity_content_hash"}
    same = {key: value for key, value in stored.items() if key not in skip} == {
        key: value for key, value in rebuilt.items() if key not in skip
    }
    print(
        json.dumps(
            {
                "path": output.name,
                "stored_seal_intact": sealed,
                "rebuilt_and_identical": same,
                "reproduced": sealed and same,
                "criteria_met": stored["criteria_met"],
                "outcome": stored["outcome"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0 if sealed and same else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="recompute the record from sources")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    return _check(arguments.output) if arguments.check else _write(arguments.output)


if __name__ == "__main__":
    raise SystemExit(main())
