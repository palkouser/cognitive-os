"""S21D4-024. The typed decision that either opens W2's correction work or closes it.

Three preconditions, checked against committed evidence rather than against a recollection of
having checked them:

1. **The replay reproduces.** If Sprint 21D3's grid does not come back from Sprint 21D3's own
   primitives, the independence erratum this sprint is built on is not established, and the
   pre-registered stop is `reconciliation_not_reproducible`.
2. **The counting rule is in force.** Not "was written" — in force: the published schema must
   require the triple, and the contract must actually refuse a census that does not add up and a
   payload that names the nominal denominator. Both are exercised here.
3. **The fitting pool audit resolved.** Every protected role reuses, or the whole-role
   replacement contract has been triggered and satisfied.

A stop closes the correction branch and *only* the correction branch. The retrieval branch has
its own evidence, its own holdout and its own gate condition, and a correction failure says
nothing about it — §6's two branches are independent after W0 precisely so that one negative
result cannot quietly cancel the other.

    UV_CACHE_DIR=.cache/uv uv run python scripts/continuation_d4.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.learning.correction_protocol import (  # noqa: E402
    INDEPENDENT_DENOMINATOR,
    DecisionCensusV4,
)

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
SCHEMAS = REPO / "schemas"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
REPLAY = EVIDENCE / "sprint-21d4-d3-grid-replay.json"
SEAL_RESUME = EVIDENCE / "sprint-21d4-seal-resume.json"
REUSE_AUDIT = EVIDENCE / "sprint-21d4-holdout-reuse-audit.json"
CONTRACTS = EVIDENCE / "sprint-21d4-contracts.json"

#: What W2 onward is allowed to start if this decision is `proceed`, and what is bound to the
#: stop hash as `not_opened` if it is not.
DEPENDENT_TASKS = (
    "S21D4-030",
    "S21D4-031",
    "S21D4-032",
    "S21D4-033",
    "S21D4-034",
    "S21D4-035",
    "S21D4-036",
    "S21D4-037",
    "S21D4-038",
    "S21D4-039",
)

#: Untouched by a correction stop. They read their own holdout and close Gate D1 condition 15.
RETRIEVAL_TASKS = ("S21D4-040", "S21D4-041", "S21D4-042", "S21D4-043", "S21D4-044", "S21D4-047")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _replay_reproduces() -> dict[str, Any]:
    document = json.loads(REPLAY.read_text())
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    reproduction = document["reproduction"]
    return {
        "condition": "the D3 grid replays under the corrected denominators",
        "evidence": REPLAY.name,
        "sha256": _sha256(REPLAY.read_bytes()),
        "integrity_hash_matches": _sha256(_canonical(body)) == document["integrity_content_hash"],
        "settings_examined": reproduction["settings_examined"],
        "derived_values_checked": reproduction["derived_values_checked"],
        "settings_that_did_not_reproduce": len(reproduction["settings_that_did_not_reproduce"]),
        "thresholds_derived": document["boundary"]["thresholds_derived"],
        "satisfied": (
            reproduction["reproduced"]
            and not reproduction["settings_that_did_not_reproduce"]
            and document["boundary"]["thresholds_derived"] == 0
            and _sha256(_canonical(body)) == document["integrity_content_hash"]
        ),
        "stop_kind_if_unsatisfied": "reconciliation_not_reproducible",
    }


def _counting_rule_in_force() -> dict[str, Any]:
    """Exercise the refusals rather than assert them, and read the published schema."""
    schema = json.loads((SCHEMAS / "v1/learned/decision-census-v4.schema.json").read_text())
    triple = {"nominal_decisions", "independent_decisions", "replicated_decisions"}
    published = triple <= set(schema["required"])

    refuses_bad_sum = False
    try:
        DecisionCensusV4(nominal_decisions=120, independent_decisions=20, replicated_decisions=99)
    except ValueError:
        refuses_bad_sum = True

    refuses_nominal_denominator = False
    try:
        DecisionCensusV4(
            nominal_decisions=20,
            independent_decisions=20,
            replicated_decisions=0,
            rate_denominator="nominal_decisions",
        )
    except ValueError:
        refuses_nominal_denominator = True

    collapse = DecisionCensusV4.from_feature_hashes(
        [f"group-{group}" for group in range(20) for _ in range(6)]
    )
    contracts = json.loads(CONTRACTS.read_text())
    declared = contracts["contracts"]["decision_independence"]["d3_replay_expectation"]
    reproduces_declaration = (
        collapse.nominal_decisions == declared["nominal"]
        and collapse.independent_decisions == declared["independent"]
        and collapse.replicated_decisions == declared["replicated"]
    )

    return {
        "condition": "the independent counting rule is in force",
        "published_schema_requires_the_triple": published,
        "refuses_a_census_that_does_not_add_up": refuses_bad_sum,
        "refuses_a_nominal_denominator": refuses_nominal_denominator,
        "rate_denominator": INDEPENDENT_DENOMINATOR,
        "six_into_one_collapse_reproduces_the_frozen_expectation": reproduces_declaration,
        "declared_expectation": declared,
        "contract_hash": contracts["contracts"]["decision_independence"]["content_hash"],
        "satisfied": (
            published and refuses_bad_sum and refuses_nominal_denominator and reproduces_declaration
        ),
        "stop_kind_if_unsatisfied": "feature_boundary_wrong",
    }


def _fitting_pool_audit_resolved() -> dict[str, Any]:
    document = json.loads(REUSE_AUDIT.read_text())
    roles = document["roles"]
    decisions = {name: role["decision"] for name, role in roles.items()}
    shapes = all(role["matches_expected_shape"] for role in roles.values())
    contracts = json.loads(CONTRACTS.read_text())
    reallocation = contracts["contracts"]["corpus_reallocation"]
    return {
        "condition": "the fitting pool and protected roles are resolved",
        "evidence": REUSE_AUDIT.name,
        "sha256": _sha256(REUSE_AUDIT.read_bytes()),
        "role_decisions": decisions,
        "every_role_matches_its_expected_shape": shapes,
        "all_pairwise_disjoint": document["group_disjointness"]["all_pairwise_disjoint"],
        "zero_outcomes_predictions_or_receipts": document["access_and_outcome_authority"][
            "zero_outcomes_predictions_or_receipts"
        ],
        "fitting_pool": {
            "groups": reallocation["fitting"]["groups"],
            "outcomes": reallocation["fitting"]["outcomes"],
            "volume_points": reallocation["volume_points"],
            "every_group_is_a_package_to_re_execute": reallocation["fitting"][
                "every_group_is_a_package_to_re_execute"
            ],
        },
        "satisfied": (
            document["eligible_for_reuse"]
            and shapes
            and document["group_disjointness"]["all_pairwise_disjoint"]
            and document["access_and_outcome_authority"]["zero_outcomes_predictions_or_receipts"]
            and set(decisions.values()) == {"reuse"}
        ),
        "stop_kind_if_unsatisfied": "volume_bound",
    }


def _spine_proved() -> dict[str, Any]:
    """Not a precondition the backlog names, but the decision binds its hash either way."""
    document = json.loads(SEAL_RESUME.read_text())
    restarts = [item["restart"] for item in document["partitions"]]
    return {
        "condition": "the seal, receipt and restart spine holds at D4's campaign shape",
        "evidence": SEAL_RESUME.name,
        "sha256": _sha256(SEAL_RESUME.read_bytes()),
        "groups": document["shape"]["groups"],
        "candidate_outcomes": document["shape"]["candidate_outcomes"],
        "every_stored_blob_rehashed": document["artifact_bytes"]["every_stored_blob_rehashed"],
        "datasets_reproduced_after_restart": all(
            item["dataset_record_reproduced"] for item in restarts
        ),
        "effective_remainder": sum(item["receipt_effective_remainder"] for item in restarts),
        "satisfied": (
            all(item["dataset_record_reproduced"] for item in restarts)
            and not any(item["receipt_effective_remainder"] for item in restarts)
            and document["artifact_bytes"]["every_stored_blob_rehashed"]
        ),
        "stop_kind_if_unsatisfied": "reconciliation_not_reproducible",
    }


def build() -> dict[str, Any]:
    conditions = [
        _replay_reproduces(),
        _counting_rule_in_force(),
        _fitting_pool_audit_resolved(),
        _spine_proved(),
    ]
    unsatisfied = [item for item in conditions if not item["satisfied"]]
    proceed = not unsatisfied

    replay = json.loads(REPLAY.read_text())
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W1",
        "items": ["S21D4-024"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "decision": {
            "kind": "proceed" if proceed else "stop",
            "stop_kind": None if proceed else unsatisfied[0]["stop_kind_if_unsatisfied"],
            "reason": (
                "the D3 grid reproduces from D3 evidence, the independent counting rule is in "
                "force and refuses both a broken census and a nominal denominator, the fitting "
                "pool and the three protected roles are resolved, and the seal-receipt-restart "
                "spine holds at 180 groups and 720 candidate outcomes. W2 may author the fresh "
                "corpus."
                if proceed
                else unsatisfied[0]["condition"] + " is not satisfied"
            ),
        },
        "conditions": conditions,
        "bound_hashes": {
            "pre_registration": _sha256(PRE_REGISTRATION.read_bytes()),
            "contracts": _sha256(CONTRACTS.read_bytes()),
            "d3_grid_replay": _sha256(REPLAY.read_bytes()),
            "seal_resume": _sha256(SEAL_RESUME.read_bytes()),
            "holdout_reuse_audit": _sha256(REUSE_AUDIT.read_bytes()),
        },
        "dependent_tasks": {
            "correction_branch": list(DEPENDENT_TASKS),
            "status": "open" if proceed else "not_opened",
        },
        "retrieval_branch": {
            "tasks": list(RETRIEVAL_TASKS),
            "status": "open",
            "why": (
                "a correction stop does not cancel the retrieval branch: it reads its own "
                "holdout, closes Gate D1 condition 15 on its own evidence, and no part of its "
                "verdict depends on the correction result"
            ),
        },
        "what_this_decision_does_not_authorise": [
            "reading any D4 calibration, final, promotion or canary outcome",
            "deriving the selective operating point",
            "selecting a candidate",
        ],
        "measurements_opened": 0,
        "carried_forward": {
            "settings_with_zero_confident_errors_over_independent_decisions": len(
                replay["observations"][
                    "settings_with_zero_confident_errors_over_independent_decisions"
                ]
            ),
            "note": (
                "no D3 setting reached zero confident errors even over its twenty independent "
                "decisions. Proceeding tests the per-decision operating point, which D3 never "
                "had; it does not assume the corrected denominator would have rescued D3."
            ),
        },
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d4-continuation.json"))
    arguments = parser.parse_args()

    record = build()
    Path(arguments.output).write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": Path(arguments.output).name,
                "decision": record["decision"]["kind"],
                "stop_kind": record["decision"]["stop_kind"],
                "conditions_satisfied": sum(item["satisfied"] for item in record["conditions"]),
                "conditions_checked": len(record["conditions"]),
                "correction_branch": record["dependent_tasks"]["status"],
                "retrieval_branch": record["retrieval_branch"]["status"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0 if record["decision"]["kind"] == "proceed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
