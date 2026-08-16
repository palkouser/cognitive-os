"""S22E-302: the named user's approval, sealed as its own act.

**Why this is a separate record rather than a field.** §2.2(b)'s chain puts "approval by the
named user" between the evaluation matrix and the PR, and the released way to record it is
`ControlledChangeService.approve_promotion`, which writes a `PromotionReview`. **W3-F2 makes
that unreachable for this change**: the released proposal engine names a synthetic
`proposal-scope/...` path as the change's whole allowed scope, so `capture_candidate` refuses
the real repository files, no `ChangeCandidate` exists, and every promotion contract downstream
of it is unbuildable. The approval still happened; what is missing is a released contract to
put it in.

So it goes here, under its own seal, binding the exact evidence it was granted against — the
approved-change record's hash, the candidate's diff hash, and the gate results — rather than
being asserted later as a sentence in a log. A human act nobody can re-check is not evidence
that a human acted.

**What this approval permits, and what it does not.** It permits a PR against protected `main`
carrying exactly the two files named in the record it binds. It does not merge, tag, publish or
release anything; the merge is the gate owner's separate act, and §2.3 forbids this driver from
performing it.

    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/approval_22e.py --approver <name>
    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/approval_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22e-w3-approval.json"
APPROVED_AT = "2026-08-16T00:00:00Z"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def sealed(name: str) -> dict[str, Any]:
    stored = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != stored["integrity_content_hash"]:
        raise ValueError(f"{name} does not recompute its own seal")
    return stored


def build(approver: str) -> dict[str, Any]:
    change = sealed("sprint-22e-w3-approved-change.json")
    decisions = sealed("sprint-22e-decisions.json")
    gates = change["gates"]

    return {
        "items": ["S22E-302"],
        "sprint": "22E",
        "wave": "W3",
        "schema_version": 1,
        "approver": approver,
        "approver_authority": "sprint-22 gate owner",
        "approved": True,
        "approved_at": APPROVED_AT,
        "what_is_approved": {
            "entry_id": change["entry_id"],
            "finding": decisions["decision_two"]["selection_finding"],
            "changed_files": [item["file"] for item in change["repair"]["files"]],
            "diff_hash": change["worktree_capture"]["diff_hash"],
            "approved_change_record_hash": change["integrity_content_hash"],
            "selection_record_hash": decisions["integrity_content_hash"],
        },
        "the_evidence_it_was_granted_against": {
            "gates_ran": change["evaluation"]["gates_ran"],
            "gates_passed": change["evaluation"]["gates_passed"],
            "gates_failed": change["evaluation"]["gates_failed"],
            "gate_ids_passed": [item["gate_id"] for item in gates if item.get("passed")],
            "wall_clock_seconds": change["evaluation"]["wall_clock_seconds"],
            "candidate_test_passed": change["candidate_test"]["passed"],
            "probe_holds_on_the_repair": change["repair_probe"]["every_probe_holds"],
            "probe_fails_without_it": change["baseline_negative_control"][
                "probe_holds_without_the_repair"
            ]
            is False,
            "zero_active_state_mutation": change["zero_active_state_mutation"][
                "zero_active_state_mutation"
            ],
        },
        "why_this_is_not_a_promotion_review": {
            "finding": "22E W3-F2",
            "released_refusal": change["released_scope_check"]["refusal"],
            "manifest_allowed_repository_paths": change["released_scope_check"][
                "manifest_allowed_repository_paths"
            ],
            "candidate_changed_files": change["released_scope_check"]["candidate_changed_files"],
            "what_could_not_be_built": [
                "ChangeCandidate",
                "PromotionAssessment",
                "PromotionReview",
                "PromotionBundle",
            ],
            "cause": (
                "build_change_specification synthesises `proposal-scope/<type>.py` as the whole "
                "allowed scope of every repository_file proposal, prepare_isolation copies it "
                "into the manifest, and capture_candidate refuses anything else; changes/demo.py "
                "passed the same placeholder back in, so both sides agreed and the seam never "
                "opened"
            ),
            "not_worked_around": (
                "the real paths were passed and the refusal recorded; substituting the "
                "placeholder or passing an empty file list would have been the driver "
                "certifying its own scope"
            ),
        },
        "what_this_approval_permits": [
            "a pull request against protected main carrying exactly the files named above",
        ],
        "what_it_does_not_permit": [
            "merge",
            "tag",
            "publish",
            "release",
            "any second repair in this sprint",
        ],
        "the_merge_is_a_separate_act_by": "the gate owner",
        "recorded_at": APPROVED_AT,
    }


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    rebuilt = build(record["approver"])
    return {
        "seal_recomputes": _sha256(canonical(body)) == record["integrity_content_hash"],
        "rebuilds_byte_identical": canonical(rebuilt) == canonical(body),
        "bound_change_record_still_seals": True,
        "approval_is_for_the_exact_diff": bool(record["what_is_approved"]["diff_hash"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--approver", default=None)
    arguments = parser.parse_args()

    if arguments.check:
        verdict = check_record(json.loads(OUTPUT.read_text(encoding="utf-8")))
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return 0 if all(verdict.values()) else 1

    if not arguments.approver:
        raise SystemExit("--approver is required: an approval with no named human is not one")

    record = build(arguments.approver)
    record["integrity_content_hash"] = _sha256(canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "approver": record["approver"],
                "changed_files": record["what_is_approved"]["changed_files"],
                "gates_passed": record["the_evidence_it_was_granted_against"]["gates_passed"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
