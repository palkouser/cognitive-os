"""S21D4-082 through -086: what the two operations records have to be able to be false about.

Both are records of commands that already ran, so the risk here is not that a check is wrong —
it is that a check never happened and the record reads as though it did. Four shapes of that,
and each has a test:

*A damage matrix with no cases.* `all()` over an empty list is `True`, so the case count is
asserted, the released eighteen are named individually, and the two S21D4-084 adds are named
too.

*A restore that reproduced nothing.* Counts matching over zero rows, a blob rehash over zero
files, and both resume inputs agreeing about nothing all look identical to success.

*An isolation claim over stores nobody fingerprinted.* Five predecessor pairs are declared, so
five have to be measured before and after.

The release matrix's own record is checked by the matrix command rather than from here; the
module docstring of `scripts/verification_matrix_d4.py` says why.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
OPERATIONS = EVIDENCE / "sprint-21d4-operations.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"

#: The eighteen cases D3 released, by name. Asserted individually because "eighteen cases ran"
#: is satisfied just as well by eighteen copies of the cheapest one.
RELEASED_CASES = {
    "tampered_blob",
    "missing_blob",
    "missing_artifact",
    "corrupt_artifact",
    "oversized_artifact",
    "schema_wrong_artifact",
    "metadata_substitution",
    "byte_substitution",
    "ood_unit_forgery",
    "holdout_access_claim",
    "retrieval_second_read",
    "dataset_member_mismatch",
    "feature_seal_mismatch",
    "stale_assessment",
    "wrong_active_revision",
    "retrieval_policy_substitution",
    "retrieval_judgement_substitution",
    "inherited_store_isolation",
}

#: The two S21D4-084 names, and the two more the twelfth integrity class made cheap.
D4_CASES = {
    "forged_independent_decision_count",
    "threshold_derived_off_calibration",
    "rate_over_a_nominal_denominator",
    "retrieval_alternative_reopened",
}

PREDECESSORS = (
    "artifacts",
    "artifacts-s21c3",
    "artifacts-s21d1",
    "artifacts-s21d2",
    "artifacts-s21d3",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reproduces_its_seal(path: Path) -> bool:
    document = _load(path)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode(
        "utf-8"
    )
    return _sha256(canonical) == document["integrity_content_hash"]


class TestTheOperationsRecord:
    def test_it_reproduces_its_seal_and_binds_the_pre_registration(self) -> None:
        """The D4 rule: the bytes that are hashed are the bytes that are written."""
        document = _load(OPERATIONS)

        assert _reproduces_its_seal(OPERATIONS)
        assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
        assert document["final_outcomes_inspected"] is False

    def test_provisioning_read_a_real_migrations_directory(self) -> None:
        """W7-A2's shape: a glob over a directory that does not exist passes vacuously."""
        provisioning = _load(OPERATIONS)["provisioning"]

        assert provisioning["migration_head"] == "0015"
        assert provisioning["migration_is_expected"] is True
        assert provisioning["no_migration_0016"] is True
        assert provisioning["migration_versions_on_disk"], "the versions list was empty"
        assert "0015" in provisioning["migration_versions_on_disk"]
        assert provisioning["database_is_isolated"] is True
        assert provisioning["schema_owner"] == "cogos_owner"
        assert set(provisioning["extensions"]) >= {"plpgsql", "vector"}

    def test_the_bootstrap_script_is_hashed_and_was_not_invoked(self) -> None:
        bootstrap = _load(OPERATIONS)["provisioning"]["bootstrap_roles_untouched"]

        assert bootstrap["invoked_by_this_command"] is False
        assert bootstrap["sha256"] == _sha256(
            (REPOSITORY / "scripts/postgres_bootstrap_roles.sh").read_bytes()
        )

    def test_the_restore_reproduced_something_rather_than_nothing(self) -> None:
        restore = _load(OPERATIONS)["restore"]

        assert restore["counts_match"] is True
        assert restore["hashed_rows_match"] is True
        assert all(restore["resume_inputs_match"].values())
        assert restore["source"]["counts"]["events"] > 0, "an empty store matches an empty store"
        assert restore["source"]["counts"]["artifact_blobs"] > 0
        assert restore["artifact_bytes"]["files_rehashed"] > 0
        assert restore["artifact_bytes"]["content_hash_mismatches"] == []
        assert restore["target_database"].endswith("_test")

    def test_the_report_over_the_restored_copy_decided_every_class(self) -> None:
        """Run with both authorities, so nothing may report `warning` there."""
        report = _load(OPERATIONS)["restore"]["evidence_report_on_the_restored_copy"]

        assert report["failed"] == []
        assert report["warnings"] == []
        assert report["not_opened"] == ["lifecycle"]
        assert len(report["covered"]) == 12
        assert len(report["clean"]) == 11

    def test_the_stopped_state_restored_as_a_stopped_state(self) -> None:
        stopped = _load(OPERATIONS)["restore"]["stopped_state"]

        assert stopped["checked_surface"] == "experience.correction_ranking"
        assert stopped["components_on_the_correction_surface"] == 0
        assert stopped["no_correction_component_was_registered"] is True

    def test_every_damage_case_is_named_and_every_one_failed_closed(self) -> None:
        rows = _load(OPERATIONS)["corruption_matrix"]
        names = {row["case"] for row in rows}

        assert len(rows) == len(names), "a case is recorded twice"
        assert names >= RELEASED_CASES, f"missing released cases: {sorted(RELEASED_CASES - names)}"
        assert names >= D4_CASES, f"missing D4 cases: {sorted(D4_CASES - names)}"
        assert len(rows) == 22
        assert all(row["observed"]["failed_closed"] for row in rows)

    def test_the_two_new_cases_were_decided_by_the_class_that_exists_for_them(self) -> None:
        """A case that failed closed for an unrelated reason proves an unrelated thing."""
        rows = {row["case"]: row for row in _load(OPERATIONS)["corruption_matrix"]}

        for case in ("forged_independent_decision_count", "rate_over_a_nominal_denominator"):
            assert "decision_independence" in rows[case]["observed"]["reason"]
        threshold = rows["threshold_derived_off_calibration"]["observed"]
        assert "OperatingPointError" in threshold["reason"]
        assert "calibration" in threshold["reason"]

    def test_five_predecessor_pairs_were_fingerprinted_before_and_after(self) -> None:
        document = _load(OPERATIONS)
        before = document["fingerprints_before"]
        after = document["fingerprints_after"]

        assert set(PREDECESSORS) <= set(before) and set(PREDECESSORS) <= set(after)
        for name in PREDECESSORS:
            assert before[name]["files"] > 0, f"{name} was fingerprinted over nothing"
            assert before[name] == after[name]
        assert document["isolation"]["predecessor_pairs_unchanged"] is True
        assert document["isolation"]["changed"] == []
        assert document["findings"] == []

    def test_the_artifact_cases_say_which_artifact_they_damaged(self) -> None:
        """D4 fitted none, so the bytes are D3's fixture and the record must not imply more."""
        assert _load(OPERATIONS)["artifact_under_test"] == "d3_contract_fixture"


#: The release matrix's own record is deliberately not asserted here. The matrix runs the whole
#: suite as one of its rows, so a test reading that record would see the *previous* run's copy
#: and the command would need two runs to go green — a release command that is not idempotent is
#: a defect in the command. Those checks live in `verification_matrix_d4._structural_findings`,
#: where they contribute to the exit status instead of to the next run.
