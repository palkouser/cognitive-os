"""S22D-400. All five exit criteria, read once, against the sealed records that decided them.

No wave read an exit. W3 assembled the four *measured* readings into
`sprint-22d-w3-exits.json` from records that were sealed before it ran, and this is the only
place all five are read together — with §2.2(e), the one exit no wave could produce, read here
because it is a re-reading of other sprints rather than a measurement of this one.

**Every verdict traces to one field of one sealed record.** A criterion is met when all of its
conditions hold, each condition is one equality against one dotted field path, and the path is
resolved rather than defaulted: a criterion whose evidence field is missing is an *unread*
criterion, and an unread criterion rendering as `false` would be one edit away from a silent
lie. `--check` rebuilds the whole document from those sources — including re-deriving the four
measured readings through `w3_22d.read_exits`, so a hand-edited exits record fails here.

**This sprint stops.** §5 fixes what a stop owes: a typed negative under
`sprint-22d-evidence-baseline` naming which exit failed, in which wave, with which measured
values. That list is assembled mechanically below rather than written out, so it cannot drift
from the verdicts above it.

    UV_CACHE_DIR=.cache/uv uv run python scripts/exit_criteria_22d.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/exit_criteria_22d.py --check

Read-only: it touches no database, calls no provider, re-runs no arm, and writes one file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
SPRINT_21 = REPO / "docs/sprints/sprint-21/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from benchmark_22d import canonical  # noqa: E402
from w3_22d import _sha256, read_exits  # noqa: E402

OUTPUT = EVIDENCE / "sprint-22d-exit-criteria.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22d-pre-registration.json"
W3_EXITS = EVIDENCE / "sprint-22d-w3-exits.json"

#: §2.2(e)'s enumeration, by file. Gate L2 and Gate D1 share one record — D7 assessed both in
#: one pass — and the four sprint records are each a released sprint's own exit reading.
GATE_L2 = SPRINT_21 / "sprint-21d7-gate-l2.json"
EXITS_22A = EVIDENCE / "sprint-22a-exit-criteria.json"
EXITS_22B = EVIDENCE / "sprint-22b-exit-criteria.json"
EXITS_22C = EVIDENCE / "sprint-22c-exit-criteria.json"

#: Gate D1's three closed conditions, by number. §1.1: 6, 7 and 15 are closed and this exit
#: re-reads that they still are — a condition closed by a later stop would be a gate that
#: reopened without anybody saying so.
GATE_D1_CLOSED = (6, 7, 15)


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"{path.name} is absent; a gate that cannot be re-read is red (§2.2e)")
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed(record: dict[str, Any]) -> bool:
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    return _sha256(canonical(body)) == record.get("integrity_content_hash")


def _at(record: dict[str, Any], field: str) -> Any:
    """Trace a dotted path into a sealed record, raising rather than defaulting.

    22C's reading, reused verbatim in spirit: a criterion whose evidence field does not resolve
    has not been read, and reporting that as `false` is a met criterion away from a lie.
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


def _criterion(
    key: str, statement: str, wave: str, conditions: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "criterion": key,
        "statement": statement,
        "decided_in_wave": wave,
        "conditions": conditions,
        "conditions_total": len(conditions),
        "conditions_holding": sum(1 for item in conditions if item["holds"]),
        "met": all(item["holds"] for item in conditions),
    }


# ---------------------------------------------------------------------------
# §2.2(e). The one exit no wave could produce
# ---------------------------------------------------------------------------


def _prior_gates(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Every prior gate re-read from its own sealed record, at this sprint's head.

    "Re-read, not assumed" is the whole instruction, and the sharp half of it is the sentence
    after: *a gate that cannot be re-read is red*. So the seal is a condition of its own on
    every record — a gate whose evidence no longer rebuilds its own hash has not been re-read,
    it has been quoted.
    """
    l2 = "sprint-21d7-gate-l2.json"
    d1 = {int(item["condition"]): item for item in records[l2]["gate_d1"]}
    conditions = [
        _condition("Gate L2 record seals", l2, "_sealed", True, records),
        _condition("Gate L2 conditions met", l2, "counts.met", 29, records),
        _condition("no Gate L2 condition failed", l2, "counts.failed", 0, records),
        _condition("no Gate L2 condition pending", l2, "counts.pending", 0, records),
        _condition("no Gate L2 condition carried", l2, "counts.carried", 0, records),
    ]
    for number in GATE_D1_CLOSED:
        conditions.append(
            {
                "condition": f"Gate D1 condition {number} still closed",
                "expected": "closed",
                "measured": d1.get(number, {}).get("state"),
                "holds": d1.get(number, {}).get("state") == "closed",
                "read_from": f"{l2}#gate_d1[{number}].state",
            }
        )
    for name, met_field, expected, label in (
        ("sprint-22a-exit-criteria.json", "outcome", "pass", "22A's four exits"),
        ("sprint-22b-exit-criteria.json", "all_met", True, "22B's five exits"),
        ("sprint-22c-exit-criteria.json", "criteria_met", 4, "22C's four met exits"),
    ):
        conditions.append(_condition(f"{label} seal", name, "_sealed", True, records))
        conditions.append(_condition(label, name, met_field, expected, records))
    # 22A's record carries no per-criterion `met` field — each criterion is a bag of named
    # boolean checks — so the four are re-read by their checks rather than by a summary field
    # somebody could have written by hand.
    for key, criterion in sorted(records["sprint-22a-exit-criteria.json"]["criteria"].items()):
        holds = all(criterion["checks"].values())
        conditions.append(
            {
                "condition": f"22A: {key}",
                "expected": True,
                "measured": holds,
                "holds": holds,
                "read_from": f"sprint-22a-exit-criteria.json#criteria.{key}.checks",
            }
        )
    return conditions


# ---------------------------------------------------------------------------
# The document
# ---------------------------------------------------------------------------


def assemble() -> dict[str, Any]:
    measured = read_exits()
    stored_exits = _load(W3_EXITS)
    records: dict[str, dict[str, Any]] = {}
    for path in (GATE_L2, EXITS_22A, EXITS_22B, EXITS_22C, W3_EXITS):
        record = _load(path)
        record["_sealed"] = _sealed(record)
        records[path.name] = record

    skip = {"recorded_at", "integrity_content_hash"}
    w3_rebuilds = {key: value for key, value in stored_exits.items() if key not in skip} == {
        key: value for key, value in measured.items() if key not in skip
    }

    name = W3_EXITS.name
    criteria = [
        _criterion(
            "a",
            "no large external LLM is called during the local microbenchmark",
            "W3 (construction frozen in W0)",
            [
                _condition("W3's exits record seals", name, "_sealed", True, records),
                _condition("the reading holds", name, "exits.a.met", True, records),
                _condition(
                    "zero provider calls in the local arm",
                    name,
                    "exits.a.external_provider_calls_in_the_local_arm",
                    0,
                    records,
                ),
                _condition(
                    "every enumerated provider refused",
                    name,
                    "exits.a.every_enumerated_provider_refused",
                    True,
                    records,
                ),
            ],
        ),
        _criterion(
            "b",
            "local verified success is at least 70% and at least 10 points above retrieval-only",
            "W3",
            [
                _condition("the absolute floor", name, "exits.b.floor_met", True, records),
                _condition("the ten-point margin", name, "exits.b.margin_met", True, records),
            ],
        ),
        _criterion(
            "c",
            "large-LLM calls or equivalent cost fall at least 25% at non-inferior success",
            "W3, against the external-teacher baseline measured in W2",
            [
                _condition(
                    "calls down at least 25%",
                    name,
                    "exits.c.external_provider_calls.met",
                    True,
                    records,
                ),
                _condition(
                    "accounted cost down at least 25%",
                    name,
                    "exits.c.accounted_cost_units.met",
                    True,
                    records,
                ),
                _condition(
                    "inside the non-inferiority margin",
                    name,
                    "exits.c.non_inferiority.met",
                    True,
                    records,
                ),
            ],
        ),
        _criterion(
            "d",
            "factual output is grounded or explicitly uncertain",
            "W3",
            [
                _condition(
                    "no ungrounded assertion from the local arm",
                    name,
                    "exits.d.ungrounded_assertions.local_model",
                    0,
                    records,
                ),
                _condition(
                    "no ungrounded assertion from the mixed workload",
                    name,
                    "exits.d.ungrounded_assertions.mixed_workload",
                    0,
                    records,
                ),
            ],
        ),
        _criterion(
            "e",
            "prior domain, learning and safety gates remain green",
            "W4, re-read from sealed records at this head",
            _prior_gates(records),
        ),
    ]

    met = [item["criterion"] for item in criteria if item["met"]]
    failures = [
        {
            "criterion": item["criterion"],
            "statement": item["statement"],
            "wave": item["decided_in_wave"],
            "conditions_that_did_not_hold": [
                {
                    "condition": condition["condition"],
                    "expected": condition["expected"],
                    "measured": condition["measured"],
                    "read_from": condition["read_from"],
                }
                for condition in item["conditions"]
                if not condition["holds"]
            ],
        }
        for item in criteria
        if not item["met"]
    ]

    pre_registration = _load(PRE_REGISTRATION)
    document = {
        "schema_version": 1,
        "items": ["S22D-400"],
        "sprint": "22D",
        "criteria": criteria,
        "criteria_total": len(criteria),
        "criteria_met": len(met),
        "criteria_met_ids": met,
        "all_met": len(met) == len(criteria),
        "outcome": "pass" if len(met) == len(criteria) else "typed negative",
        "outcome_tag": (
            pre_registration["outcome_tag"]
            if len(met) == len(criteria)
            else pre_registration["negative_outcome_tag"]
        ),
        "failures": failures,
        "what_a_stop_owes": (
            "§5: a typed negative under sprint-22d-evidence-baseline naming which exit failed, "
            "in which wave, with which measured values. `failures` above is assembled from the "
            "conditions rather than written out, so it cannot drift from the verdicts"
        ),
        "no_wave_read_an_exit_before_this_record": (
            "W3 assembled the four measured readings from arm records that were sealed before "
            "it ran, and read no exit as a verdict; the fifth is a re-reading of other sprints "
            "and could not have been produced by any wave of this one"
        ),
        "w3_exits_rebuild_from_the_arm_records": w3_rebuilds,
        "pre_registration_sha256": pre_registration["integrity_content_hash"],
        "readings_hash": measured["readings_hash"],
        "amendments_made_by_22d": pre_registration["amendments_made_by_22d"],
        "the_accounting_source_is_named": {
            "why_this_is_here": (
                "§5 requires 22C W2-F3 repaired or the accounting's source named, and §1.1 said "
                "that finding stops being cosmetic in this sprint because the accounting exit "
                "needs a durable record of what executed where"
            ),
            "repaired": False,
            "source": (
                "the accounting is driver-side and never passed through the Tool Plane: "
                "`run_arm` builds one `ArmAccounting` per workload from each `ArmOutcome`, and "
                "the record it produces is sealed per arm. The external half is additionally "
                "bound by the receipts digest over every governed call's request and normalized "
                "response hash"
            ),
            "why_the_tool_plane_was_not_needed": (
                "no arm executes a tool. The workloads answer, are verified by registered "
                "verifiers and are accounted from their own outcomes, so a Tool Plane store "
                "that discards its events could not have weakened these numbers — and repairing "
                "it here would have been a schema-adjacent change §2.3 excludes, made for a "
                "reading nothing in this sprint takes"
            ),
        },
        "adapter_training_not_taken": (
            "§2.3 makes it optional and conditional on W4 having surplus. It does not: three of "
            "the four measured exits are unmet and no exit needs an adapter, so spending the "
            "release wave on an optional experiment would have added a number nothing reads"
        ),
        "migration_head": pre_registration["migration_head"],
    }
    document["recorded_at"] = _load(W3_EXITS)["recorded_at"]
    document["integrity_content_hash"] = _sha256(canonical(document))
    return document


def _write(output: Path) -> int:
    document = assemble()
    output.write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "criteria_met": document["criteria_met"],
                "criteria_total": document["criteria_total"],
                "criteria_met_ids": document["criteria_met_ids"],
                "outcome": document["outcome"],
                "outcome_tag": document["outcome_tag"],
                "integrity_content_hash": document["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def _check(output: Path) -> int:
    stored = _load(output)
    sealed = _sealed(stored)
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
                "outcome_tag": stored["outcome_tag"],
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
