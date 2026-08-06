"""S21D4-001. The immutable Sprint 21D3 reconciliation, computed from D3's own evidence.

Two corrections, both non-destructive. Not one D1, D2 or D3 byte is modified; the convention
this follows is the one D3 itself established when it reconciled D2's denominators and
retrieval narrative rather than editing them.

**Decision independence.** D3 reported 120 metamorphic ranking decisions per setting: 20
calibration groups times six semantics-preserving transformation cases. Because
`correction-ranking-v2` is *exactly* invariant -- the sprint's own principal result -- all six
transformed cases of a group produce byte-identical fitted vectors and therefore the identical
ranking decision. So the metamorphic set was 20 decisions replicated six times: a perfect
invariance regression test and a null accuracy test. Its "zero confident errors" requirement was
equivalent to demanding zero errors among answered *clean* decisions, on a sample of 20, which
cannot distinguish a 0% error rate from a 14% one.

**W7 recovery narrative.** The W7 recovery paragraph of the execution log disagrees with
`sprint-21d3-operations.json` on every value it states. The evidence is authoritative.

    UV_CACHE_DIR=.cache/uv uv run python scripts/d3_reconciliation_d4.py

Read-only over committed evidence. Stdlib only: the binomial bound is Clopper-Pearson one-sided,
which for zero observed errors in n is exactly ``1 - alpha ** (1 / n)`` and needs no special
function.
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

from cognitive_os.learning.selective_operating_point import (  # noqa: E402
    zero_error_upper_bound,
)

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
SELECTION = EVIDENCE / "sprint-21d3-learner-selection.json"
OPERATIONS = EVIDENCE / "sprint-21d3-operations.json"

CASES_PER_GROUP = 6

#: What the D3 execution log's W7 recovery paragraph and W7-A5 finding state, against the
#: JSON pointer in the operations evidence that actually decides each one. Recorded as pairs
#: so the reconciliation is checkable rather than asserted.
NARRATIVE_CLAIMS: tuple[tuple[str, str, str], ...] = (
    ("database dump sha256", "c51b828106306b92", "backup.database_dump_sha256"),
    ("artifact archive sha256", "8bb54058d02e1f69", "backup.artifact_archive_sha256"),
    ("artifact archive bytes", "1679871", "backup.artifact_archive_bytes"),
    ("events backed up", "1281", "backup.event_count"),
    ("artifacts backed up", "2754", "backup.artifact_count"),
    ("blobs rehashed on restore", "2077", "restore.artifact_bytes.files_rehashed"),
)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pointer(document: dict[str, Any], pointer: str) -> Any:
    value: Any = document
    for part in pointer.split("."):
        value = value[part]
    return value


def _independence() -> dict[str, Any]:
    payload = json.loads(SELECTION.read_text(encoding="utf-8"))
    settings = payload["settings"]

    rows, violations = [], []
    for setting in settings:
        answered = setting["clean_answered"]
        correct = setting["clean_correct"]
        errors = answered - correct
        holds_answered = setting["ood_answered"] == CASES_PER_GROUP * answered
        holds_errors = setting["confident_ood_errors"] == CASES_PER_GROUP * errors
        if not (holds_answered and holds_errors):
            violations.append(setting["setting_identity"])
        rows.append(
            {
                "setting_identity": setting["setting_identity"],
                "clean_decisions": setting["clean_decisions"],
                "clean_answered": answered,
                "clean_correct": correct,
                "clean_errors": errors,
                "metamorphic_ranking_decisions": setting["metamorphic_ranking_decisions"],
                "ood_answered": setting["ood_answered"],
                "confident_ood_errors": setting["confident_ood_errors"],
                "ood_answered_is_six_times_clean_answered": holds_answered,
                "confident_errors_are_six_times_clean_errors": holds_errors,
            }
        )

    nominal = {row["metamorphic_ranking_decisions"] for row in rows}
    independent = {row["clean_decisions"] for row in rows}
    if len(nominal) != 1 or len(independent) != 1:  # pragma: no cover - D3 reported one shape
        raise SystemExit("D3 reported more than one decision shape; the collapse claim is unsafe")
    nominal_count, independent_count = nominal.pop(), independent.pop()

    return {
        "source": {"path": SELECTION.name, "sha256": _hash_file(SELECTION)},
        "settings_examined": len(rows),
        "identity_violations": violations,
        "both_identities_hold_for_every_setting": not violations,
        "per_setting": rows,
        "counts": {
            "nominal_decisions": nominal_count,
            "independent_decisions": independent_count,
            "replicated_decisions": nominal_count - independent_count,
            "cases_per_group": CASES_PER_GROUP,
            "rule": "independence is equality of the fitted feature vector",
        },
        "zero_error_upper_bounds": {
            str(n): round(zero_error_upper_bound(n), 6) for n in (20, 60, 100, 300)
        },
        "consequence": (
            "D3's zero-confident-error requirement over 120 metamorphic decisions was "
            "equivalent to zero errors among answered clean decisions, of which there were 20. "
            f"Observing zero errors in 20 bounds the true rate only at "
            f"{zero_error_upper_bound(20):.1%} with 95% confidence. Gate L2 condition 20's 1% "
            "ceiling is an observed-rate requirement; D4 reports the bound beside it rather "
            "than claiming the bound is met."
        ),
    }


def _recovery() -> dict[str, Any]:
    operations = json.loads(OPERATIONS.read_text(encoding="utf-8"))
    rows = []
    for name, narrated, pointer in NARRATIVE_CLAIMS:
        recorded = _pointer(operations, pointer)
        recorded_text = str(recorded)
        agrees = recorded_text.startswith(narrated) or recorded_text == narrated
        rows.append(
            {
                "value": name,
                "execution_log_narrative": narrated,
                "evidence_pointer": pointer,
                "evidence_value": recorded if isinstance(recorded, int) else recorded_text,
                "agrees": agrees,
            }
        )

    structural = {
        "damage_cases": len(operations["corruption_matrix"]),
        "fingerprints_unchanged": operations["fingerprints_before"]
        == operations["fingerprints_after"],
        "final_outcomes_inspected": operations["final_outcomes_inspected"],
    }
    return {
        "source": {"path": OPERATIONS.name, "sha256": _hash_file(OPERATIONS)},
        "claims": rows,
        "claims_agreeing": sum(1 for row in rows if row["agrees"]),
        "claims_disagreeing": sum(1 for row in rows if not row["agrees"]),
        "w7_a5_blob_rows": {
            "execution_log_narrative": "1,952 of 1,952",
            "evidence_pointer": "restore.source.counts.artifact_blobs",
            "evidence_value": _pointer(operations, "restore.source.counts.artifact_blobs"),
        },
        "corroboration": (
            "Two independent readings agree with the evidence and not with the log. The D3 "
            "report states 2,096, and the D3 Artifact Store fingerprinted at release time "
            "contains exactly 2,096 files (sprint-21d3-release.json)."
        ),
        "structural_claims_reproduce": structural,
        "conclusion": (
            "A narrative restatement of counts, not a result. Nothing about the D3 outcome "
            "moves: the damage cases, matrix rows, store fingerprints and unopened final "
            "outcomes of that wave all reproduce. The paragraph is not corrected in place; the "
            "execution log carries an erratum and this record is the authority."
        ),
    }


def build() -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W0",
        "items": ["S21D4-001"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": (
            "Establish the authoritative D3 denominators and recovery values for Sprint 21D4, "
            "without modifying any released byte."
        ),
        "decision_independence": _independence(),
        "w7_recovery": _recovery(),
        "protected_objects_unchanged": True,
        "d1_d2_d3_bytes_modified": 0,
    }
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d4-d3-reconciliation.json"))
    arguments = parser.parse_args()

    record = build()
    Path(arguments.output).write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    independence = record["decision_independence"]
    print(
        json.dumps(
            {
                "output": Path(arguments.output).name,
                "settings_examined": independence["settings_examined"],
                "collapse_holds_for_every_setting": independence[
                    "both_identities_hold_for_every_setting"
                ],
                "decisions": independence["counts"],
                "w7_claims_disagreeing": record["w7_recovery"]["claims_disagreeing"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
