"""S21D5-083, -084 and -085: the operations record has to be able to be false about itself.

The command that writes `sprint-21d5-operations.json` decides its own exit status, so a test
that only re-read its `findings` field would agree with it by construction. What is checked
here is the shape a reader depends on: the seal recomputes from the bytes on disk, provisioning
looked at a directory that exists, the restore reproduced something rather than nothing, the
stopped state came back stopped, and every row of the damage table names what it broke.

S21D5-085's clause is the last class here. W7-F2 cost D4 a red lane: the truncation fence lived
behind a SQLAlchemy import, so the one job it had — being collectable in a lane without the
PostgreSQL extra — was the one thing it could not do. Every environment check D5 adds is
therefore asserted to be importable and runnable with `sqlalchemy` blocked on the meta path,
which is the condition `experience-graph-core` actually has.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess  # nosec B404 - a fixed argv list running this interpreter, never a shell
import sys
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
OPERATIONS = EVIDENCE / "sprint-21d5-operations.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"

#: The six pairs D5 must not write to, fingerprinted before and after the whole run.
PREDECESSORS = (
    "artifacts",
    "artifacts-s21c3",
    "artifacts-s21d1",
    "artifacts-s21d2",
    "artifacts-s21d3",
    "artifacts-s21d4",
)

#: The five rows D5 is the first sprint able to run, because D5 is the first to have fitted
#: something. Named so that dropping one is a diff rather than a smaller number.
D5_OWN_CASES = {
    "nudged_direction_320_rows",
    "nudged_direction_720_rows",
    "unimplemented_sealed_hypothesis_class",
    "certificate_names_an_unimplemented_class",
    "operating_point_second_derivation",
}


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
        """The bytes that are hashed are the bytes that are written."""
        document = _load(OPERATIONS)

        assert _reproduces_its_seal(OPERATIONS)
        assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
        assert document["final_outcomes_inspected"] is False

    def test_provisioning_read_a_real_migrations_directory(self) -> None:
        """D4-W7-A2's shape: a glob over a directory that does not exist passes vacuously."""
        provisioning = _load(OPERATIONS)["provisioning"]

        assert provisioning["migration_head"] == "0015"
        assert provisioning["migration_is_expected"] is True
        assert provisioning["no_migration_0016"] is True
        assert provisioning["migration_versions_on_disk"], "no migration was looked at"
        assert provisioning["database_is_isolated"] is True

    def test_the_bootstrap_script_is_hashed_and_was_not_invoked(self) -> None:
        bootstrap = _load(OPERATIONS)["provisioning"]["bootstrap_roles_untouched"]

        assert bootstrap["invoked_by_this_command"] is False
        assert bootstrap["sha256"] == _sha256(
            (REPOSITORY / "scripts/postgres_bootstrap_roles.sh").read_bytes()
        )

    def test_the_backup_was_taken_before_anything_was_damaged(self) -> None:
        """W0-F1 and W7-F1 are what this one line cost; it is asserted, not trusted."""
        backup = _load(OPERATIONS)["backup"]

        assert backup["taken_before_any_damage"] is True
        assert backup["database"] == "cognitive_os_s21d5_test"
        assert backup["alembic_revision"] == "0015"
        assert backup["event_count"] > 0
        assert len(backup["database_dump_sha256"]) == 64

    def test_the_restore_reproduced_something_rather_than_nothing(self) -> None:
        restore = _load(OPERATIONS)["restore"]

        assert restore["counts_match"] and restore["hashed_rows_match"]
        assert all(restore["resume_inputs_match"].values())
        assert restore["source"]["counts"]["events"] > 0
        assert restore["artifact_bytes"]["files_rehashed"] > 0
        assert restore["artifact_bytes"]["content_hash_mismatches"] == []

    def test_the_report_over_the_restored_copy_decided_every_class(self) -> None:
        """Both authorities supplied: nothing may be a warning, and nothing may fail."""
        report = _load(OPERATIONS)["restore"]["evidence_report_on_the_restored_copy"]

        assert report["failed"] == []
        assert report["warnings"] == []
        assert report["not_opened"] == ["lifecycle"]
        assert len(report["clean"]) == 11
        assert len(report["covered"]) == 12

    def test_the_stopped_state_restored_as_a_stopped_state(self) -> None:
        stopped = _load(OPERATIONS)["restore"]["stopped_state"]

        assert stopped["no_correction_component_was_registered"] is True
        assert stopped["components_on_the_correction_surface"] == 0
        assert stopped["checked_surface"] == "experience.correction_ranking"


class TestTheDamageTable:
    def test_every_row_names_what_it_broke_and_every_row_held(self) -> None:
        rows = _load(OPERATIONS)["corruption_matrix"]

        assert rows
        for row in rows:
            assert row["damage"] and row["expected"], f"{row['case']} says nothing"
            assert row["observed"]["failed_closed"] is True, row["case"]

    def test_the_controls_are_counted_apart_from_the_damage(self) -> None:
        """A control that refused nothing must not be counted as a case that did."""
        document = _load(OPERATIONS)
        shape = document["matrix_shape"]
        rows = document["corruption_matrix"]

        assert shape["rows"] == len(rows)
        assert shape["damage_cases"] == len(rows) - len(shape["controls"])
        assert shape["controls"], "a table with no control cannot show its rehash works"
        for name in shape["controls"]:
            row = next(item for item in rows if item["case"] == name)
            assert row["observed"]["is_a_control_not_a_damage_case"] is True

    def test_the_cases_d5_is_the_first_able_to_run_are_all_present(self) -> None:
        cases = {row["case"] for row in _load(OPERATIONS)["corruption_matrix"]}

        assert cases >= D5_OWN_CASES

    def test_the_artifact_cases_say_which_artifact_they_damaged(self) -> None:
        """D5 fitted a direction but never built a v3 artifact; the label says so."""
        document = _load(OPERATIONS)

        assert document["artifact_under_test"] == "d3_contract_fixture"

    def test_six_predecessor_pairs_were_fingerprinted_before_and_after(self) -> None:
        document = _load(OPERATIONS)

        assert set(PREDECESSORS) <= set(document["fingerprints_before"])
        assert document["isolation"]["predecessor_pairs_unchanged"] is True
        assert document["isolation"]["changed"] == []
        for name in PREDECESSORS:
            assert document["fingerprints_before"][name] == document["fingerprints_after"][name], (
                name
            )


class TestTheCredentialFreeClause:
    """S21D5-085. Every new check has to be collectable where the driver is absent."""

    def test_the_report_module_imports_no_database_driver(self) -> None:
        module = REPOSITORY / "src/cognitive_os/learning/integrity_d5.py"
        tree = ast.parse(module.read_text(encoding="utf-8"))

        imported = {
            node.module.split(".")[0] if isinstance(node, ast.ImportFrom) and node.module else name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import | ast.ImportFrom)
            for name in ([alias.name.split(".")[0] for alias in node.names] or [""])
        }

        assert "sqlalchemy" not in imported
        assert "asyncpg" not in imported

    def test_the_report_runs_in_a_process_where_sqlalchemy_cannot_be_imported(self) -> None:
        """The AST says what is written; this says what happens when the driver is gone.

        Checked by blocking the name on the meta path rather than by uninstalling anything,
        because the condition the lane has is "the extra is not installed" and a subprocess
        that refuses the import reproduces it exactly.
        """
        program = (
            "import sys\n"
            "class Block:\n"
            "    def find_module(self, name, path=None):\n"
            "        return self.find_spec(name, path)\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name == 'sqlalchemy' or name.startswith('sqlalchemy.'):\n"
            "            raise ImportError('sqlalchemy is not installed in this lane')\n"
            "        return None\n"
            "sys.meta_path.insert(0, Block())\n"
            "from pathlib import Path\n"
            "from cognitive_os.learning.integrity_d5 import d5_integrity\n"
            f"report = d5_integrity(Path({str(EVIDENCE)!r}))\n"
            "assert report.failed == (), report.failed\n"
            "print(len(report.clean))\n"
        )

        completed = subprocess.run(  # nosec B603 - fixed argv, this interpreter, no shell
            [sys.executable, "-c", program],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPOSITORY,
        )

        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert int(completed.stdout.strip()) == 9

    @pytest.mark.parametrize(
        "surface",
        ["d5_evidence_schemas", "d5_integrity_classes", "d5_cli_boundary", "hypothesis_class"],
    )
    def test_the_recorded_lane_coverage_is_true_of_the_workflow_on_disk(self, surface: str) -> None:
        """The record claims a lane covers something; the workflow is what decides."""
        coverage = _load(OPERATIONS)["ci_coverage"]
        workflow = REPOSITORY / ".github/workflows/ci.yml"

        assert coverage["covered"][surface] is True
        assert coverage["uncovered"] == []
        assert coverage["workflow_sha256"] == _sha256(workflow.read_bytes())
