"""S22C-053. The holdout, both arms, read once against the definition W0 froze.

This is the sprint's fifth exit and its hardest sentence: *at least one retained artifact
improves a held-out verified task*. Nothing in the programme has shown that yet, Gate D1's
usefulness floor is open, and §3.2 scheduled this early precisely so that a miss would be a
measured negative with diagnostics rather than a surprise at release.

**What each arm is, and what makes the comparison honest.**

*Arm A* runs each case exactly as W0 froze it, gap and all. The pilot kernels refuse a case
that does not declare what it relies on, so a case with its `atomic_masses` withheld fails
before a verifier is reached. That refusal is the baseline.

*Arm B* runs the same case with the withheld fact **restored from a retained artifact** — an
artifact this campaign acquired, cited to source bytes, promoted through the released gate.
The value comes out of the retained-case records the cycles sealed; it is never taken from
the holdout, and where no retained artifact supplies it the arm reports
`no_retained_artifact_supplies_it` rather than quietly borrowing the case's own answer. That
distinction is the whole integrity of the exit: an arm B that reads the holdout to fill its
own gap measures nothing.

The verdict is the released one. `domains.checker` judges the answer independently, and the
frozen success definition also requires the answer to equal the case's expected answer, so a
plausible-but-wrong artifact fails.

**What this driver may not do.** It may not touch the campaign store, may not re-run a cycle,
and may not change the holdout: `measured_values` was 0 at freeze and this run is the first
and only read. A leakage check runs before any arm, because a curriculum that had seen a
holdout case would make both arms meaningless.

    UV_CACHE_DIR=.cache/uv uv run python scripts/improvement_22c.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/improvement_22c.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from campaign_22c import (  # noqa: E402
    _canonical,
    _sha256,
    assertion_agrees,
    attempt_case,
    register_pilots,
)

HOLDOUT = EVIDENCE / "sprint-22c-holdout.json"
OUTPUT = EVIDENCE / "sprint-22c-w3-improvement.json"

#: Every cycle's retained-case record, in cycle order. Arm B may draw on anything the
#: campaign retained, which is what "a retained artifact" means — but on nothing else.
RETAINED_RECORDS = (
    EVIDENCE / "sprint-22c-w2-retained-cases.json",
    EVIDENCE / "sprint-22c-w3-retained-cases.json",
)

#: Every cycle's record, read only for its curriculum hashes so leakage can be checked
#: against what the campaign actually registered rather than against what it meant to.
CYCLE_RECORDS = (
    EVIDENCE / "sprint-22c-w2-cycle1.json",
    EVIDENCE / "sprint-22c-w3-cycle2.json",
    EVIDENCE / "sprint-22c-w3-cycle3.json",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True, slots=True)
class Retained:
    """One fact this campaign retained, and where it came from."""

    key: str
    value: Any
    case_id: str
    domain_id: str
    claim_id: str
    source_segment_hash: str
    cycle: int


def retained_facts() -> tuple[Retained, ...]:
    """Every declared input the campaign's retained cases carry, by key.

    A retained case is a *promoted* artifact: it survived the cross-check, was compiled with a
    provenance bundle and activated through the released promotion gate. Its `formal_inputs`
    are therefore facts the campaign holds and can cite, and they are the only place arm B is
    allowed to look.
    """
    facts: list[Retained] = []
    for path in RETAINED_RECORDS:
        if not path.exists():
            continue
        record = _load(path)
        for case in record["cases"]:
            for key, value in case["formal_inputs"].items():
                facts.append(
                    Retained(
                        key=key,
                        value=value,
                        case_id=case["case_id"],
                        domain_id=case["domain_id"],
                        claim_id=case["claim_id"],
                        source_segment_hash=case["source_segment_hash"],
                        cycle=case["retained_by_cycle"],
                    )
                )
    return tuple(facts)


def supplier_for(case: dict[str, Any], facts: tuple[Retained, ...]) -> Retained | None:
    """The retained fact that fills this case's gap, if the campaign retained one.

    Matched on the withheld key *and the domain*, because a mechanics artifact cannot supply
    a chemistry case's atomic masses and pretending otherwise would be the same error as
    reading the holdout. The first retained match wins and the record names it, so a reader
    can walk from the arm back to the claim and from the claim back to the source bytes.
    """
    return next(
        (
            fact
            for fact in facts
            if fact.key == case["withheld_key"] and fact.domain_id == case["domain_id"]
        ),
        None,
    )


def leakage() -> dict[str, Any]:
    """No holdout case may appear in any cycle's registered curriculum. §2.2c, 22B W1-F6."""
    holdout = _load(HOLDOUT)
    case_hashes = set(holdout["case_hashes"])
    curricula: dict[str, int] = {}
    overlaps: dict[str, list[str]] = {}
    for path in CYCLE_RECORDS:
        if not path.exists():
            continue
        record = _load(path)
        hashes = {
            item["source_segment_hash"]
            for item in record.get("retained_cases", {}).get("cases", [])
        }
        hashes |= {
            entry["content_hash"]
            for entry in record.get("curriculum_segment_hashes", [])
            if isinstance(entry, dict)
        }
        curricula[path.name] = len(hashes)
        shared = sorted(case_hashes & hashes)
        if shared:
            overlaps[path.name] = shared
    return {
        "holdout_cases": len(case_hashes),
        "cycle_records_read": curricula,
        "overlaps": overlaps,
        "leakage_detected": bool(overlaps),
        "also_enforced_by": (
            "CampaignManifestV1 refuses to seal a manifest whose curriculum shares a hash "
            "with a holdout, so this is the second of two independent checks"
        ),
    }


async def run_arm(case: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    """One case through the released path, judged by the released checker."""
    run = await attempt_case(case["problem_type"], inputs)
    agrees, disagreement = (
        assertion_agrees(case["expected_answer"], run.candidate) if run.accepted else (False, "")
    )
    return {
        "accepted_by_the_checker": run.accepted,
        "verifier_status": run.verifier_status,
        "refused_before_solving": run.refused_before_solving,
        "answer_equals_the_expected_answer": agrees,
        "verified_success": bool(run.accepted and agrees),
        "message": run.message or disagreement,
        "computed": {
            key: value
            for key, value in run.candidate.items()
            if key in {"exact_value", "units", "structured"}
        },
    }


async def read_holdout() -> dict[str, Any]:
    register_pilots()
    holdout = _load(HOLDOUT)
    facts = retained_facts()

    separation = leakage()
    if separation["leakage_detected"]:
        raise SystemExit(
            "a holdout case hash appears in a cycle's curriculum; both arms are void "
            "(§2.2c, 22B W1-F6)"
        )

    cases: list[dict[str, Any]] = []
    for case in holdout["cases"]:
        arm_a = await run_arm(case, dict(case["formal_inputs"]))
        supplier = supplier_for(case, facts)
        if supplier is None:
            arm_b: dict[str, Any] = {
                "verified_success": False,
                "no_retained_artifact_supplies_it": True,
                "why": (
                    f"no artifact this campaign retained for {case['domain_id']} carries "
                    f"{case['withheld_key']!r}. The arm is not run rather than run with a "
                    "value taken from the case itself"
                ),
            }
            restored = None
        else:
            restored = {
                "from_case": supplier.case_id,
                "from_cycle": supplier.cycle,
                "claim_id": supplier.claim_id,
                "source_segment_hash": supplier.source_segment_hash,
                "value": supplier.value,
            }
            arm_b = await run_arm(
                case, {**case["formal_inputs"], case["withheld_key"]: supplier.value}
            )
            arm_b["no_retained_artifact_supplies_it"] = False
        cases.append(
            {
                "case_id": case["case_id"],
                "domain_id": case["domain_id"],
                "problem_type": case["problem_type"],
                "content_hash": case["content_hash"],
                "withheld_key": case["withheld_key"],
                "withheld_description": case["withheld_description"],
                "expected_answer": case["expected_answer"],
                "arm_a_artifact_inactive": arm_a,
                "arm_b_artifact_active": arm_b,
                "restored_from": restored,
                "improved": bool(arm_b.get("verified_success") and not arm_a["verified_success"]),
            }
        )

    arm_a_successes = sum(
        1 for item in cases if item["arm_a_artifact_inactive"]["verified_success"]
    )
    arm_b_successes = sum(
        1 for item in cases if item["arm_b_artifact_active"].get("verified_success")
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W3",
        "items": ["S22C-053"],
        "recorded_at": _now(),
        "reads_exit_criterion": "at least one retained artifact improves a held-out verified task",
        "holdout": {
            "holdout_id": holdout["holdout_id"],
            "frozen_integrity_content_hash": holdout["integrity_content_hash"],
            "case_count": holdout["case_count"],
            "success_definition": holdout["success_definition"],
            "verifier_id": holdout["verifier_id"],
            "seeds": holdout["seeds"],
            "read_once": True,
            "measured_values_at_freeze": 0,
        },
        "separation": separation,
        "retained_facts_available_to_arm_b": [
            {
                "key": fact.key,
                "domain_id": fact.domain_id,
                "from_case": fact.case_id,
                "from_cycle": fact.cycle,
            }
            for fact in facts
        ],
        "cases": cases,
        "comparison": {
            "arm_a_verified_successes": arm_a_successes,
            "arm_b_verified_successes": arm_b_successes,
            "cases": len(cases),
            "improved_cases": sum(1 for item in cases if item["improved"]),
            "at_least_one_retained_artifact_improved_a_held_out_task": any(
                item["improved"] for item in cases
            ),
            "measured_in_22c": True,
            "same_tasks_same_seeds_same_checker": True,
        },
        "what_this_does_not_license": (
            "§4: an existence proof at most, not a learning rate. Nothing here says how fast "
            "the system learns, what a chapter is worth, or whether a fourth cycle would help"
        ),
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    if arguments.check:
        stored = _load(arguments.output)
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(_canonical(body)) == stored["integrity_content_hash"]
        rebuilt = asyncio.run(read_holdout())
        moving = {"recorded_at", "integrity_content_hash"}
        same = {key: value for key, value in stored.items() if key not in moving} == {
            key: value for key, value in rebuilt.items() if key not in moving
        }
        print(
            json.dumps(
                {
                    "path": arguments.output.name,
                    "stored_seal_intact": sealed,
                    "rebuilt_and_identical": same,
                    "reproduced": sealed and same,
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if sealed and same else 1

    record = asyncio.run(read_holdout())
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(record["comparison"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
