"""S21C3-060 to S21C3-062: the operator surface, and what it refuses.

Every subcommand that needs no store is exercised here, deterministically and without
credentials. The ones that do need a store are represented by the two claims that can be
checked without one: that they exist, and that the CLI refuses to start them without the
opt-in they require.

The integrity report is checked the same way. Whether the C3 store is intact is a question
only the C3 store can answer; whether a *warning* can condemn it is a question about this
module, and it is the one that decides whether the report gets read.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from cognitive_os.coding.reality_integrity import (
    FAILURE,
    WARNING,
    IntegrityCheck,
    IntegrityReport,
    development_pair_is_untouched,
    fingerprint,
    local_embedding_model_is_available,
    task_generation_is_deterministic,
)

REPOSITORY = Path(__file__).resolve().parents[3]
SCRIPTS = REPOSITORY / "scripts"


def _load(name: str):  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reality_inputs = _load("reality_inputs")


# ------------------------------------------------------------------ the CLI


def test_every_delegated_command_points_at_a_script_that_exists() -> None:
    """The forwarding table is the one place this CLI can rot without anyone noticing."""
    for command, script in reality_inputs.DELEGATED.items():
        assert (SCRIPTS / script).is_file(), command


def test_provider_work_is_refused_without_the_explicit_opt_in() -> None:
    """§S21C3-060: explicit `--live`, and no prompt follows. Refusal is exit 2."""
    assert reality_inputs.main(["provider", "--", "run", "--config", "x"]) == 2


def test_resume_without_a_previous_evidence_file_is_refused() -> None:
    assert reality_inputs.main(["resume", "--", "--output", "x.json"]) == 2


def test_generate_refuses_a_relative_destination(tmp_path: Path) -> None:
    assert reality_inputs.main(["generate", "--root", "relative/path"]) == 2


def test_validate_needs_no_store_no_network_and_no_credentials(capsys) -> None:  # type: ignore[no-untyped-def]
    """The default posture. It is the command an operator runs before anything else."""
    code = reality_inputs.main(["validate"])
    receipt = json.loads(capsys.readouterr().out)

    assert code == 0
    assert receipt["ok"] is True
    assert receipt["templates"] == 30
    assert receipt["control_tokens_in_queries"] == []
    assert receipt["cross_group_leakage"] == []


def test_generate_keeps_the_control_bundle_out_of_every_workspace(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    code = reality_inputs.main(["generate", "--root", str(tmp_path), "--tasks", "3"])
    receipt = json.loads(capsys.readouterr().out)

    assert code == 0
    assert len(receipt["tasks"]) == 3
    for task in receipt["tasks"]:
        workspace, control = Path(task["workspace"]), Path(task["control"])
        assert workspace.is_dir() and control.is_dir()
        assert control not in workspace.parents


def test_a_receipt_names_the_database_and_never_the_url(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A receipt has to be safe to paste into a ticket, so it carries no authentication."""
    # A fabricated password, and it has to look like one: the assertion below is that it does
    # not survive into the receipt, which a placeholder without credential shape would not test.
    url = (  # pragma: allowlist secret
        "postgresql+asyncpg://user:hunter2@127.0.0.1:5432/cogos_c3_test"
    )
    monkeypatch.setenv("COGOS_DATABASE_URL", url)

    name = reality_inputs._database_name()

    assert name == "cogos_c3_test"
    assert "hunter2" not in name and "@" not in name


def test_no_database_url_at_all_is_not_a_crash(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("COGOS_DATABASE_URL", raising=False)

    assert reality_inputs._database_name() is None


# ------------------------------------------------------------------ the integrity report


def test_a_warning_does_not_condemn_the_store() -> None:
    """§S21C3-061: an unavailable capability is not corrupted evidence.

    If a missing local model turned the report red, an operator would learn that red is
    normal — and stop reading it on the day it means something.
    """
    report = IntegrityReport(
        checks=(
            IntegrityCheck("bytes_present", True, FAILURE, "0 missing"),
            IntegrityCheck("model_available", False, WARNING, "not fetched on this host"),
        )
    )

    assert report.healthy is True
    assert [check.name for check in report.warnings] == ["model_available"]
    assert report.failures == ()


def test_a_broken_authority_link_is_unhealthy() -> None:
    report = IntegrityReport(
        checks=(IntegrityCheck("bytes_present", False, FAILURE, "3 artifact rows with no blob"),)
    )

    assert report.healthy is False
    assert [check.name for check in report.failures] == ["bytes_present"]


def test_the_missing_local_model_is_reported_as_a_capability(tmp_path: Path) -> None:
    check = local_embedding_model_is_available(tmp_path)

    assert check.severity == WARNING
    assert check.ok is False


def test_no_model_directory_at_all_is_also_only_a_warning() -> None:
    assert local_embedding_model_is_available(None).severity == WARNING


def test_task_generation_is_deterministic_over_every_template() -> None:
    check = task_generation_is_deterministic()

    assert check.ok is True
    assert check.severity == FAILURE


def test_a_write_to_the_development_pair_changes_its_fingerprint(tmp_path: Path) -> None:
    """The claim every wave of this sprint carries, made checkable. §S21C3-003."""
    (tmp_path / "sha256").mkdir()
    (tmp_path / "sha256" / "aa").write_bytes(b"one")
    before, files = fingerprint(tmp_path)

    (tmp_path / "sha256" / "bb").write_bytes(b"two")
    after, more = fingerprint(tmp_path)

    assert (before, files) != (after, more)
    assert (
        development_pair_is_untouched(tmp_path, expected_digest=before, expected_files=files).ok
        is False
    )
    assert (
        development_pair_is_untouched(tmp_path, expected_digest=after, expected_files=more).ok
        is True
    )


def test_an_absent_development_root_is_a_failure_not_a_pass(tmp_path: Path) -> None:
    """ "Nothing to compare" must never read as "nothing was written"."""
    check = development_pair_is_untouched(
        tmp_path / "gone", expected_digest="0" * 64, expected_files=0
    )

    assert check.ok is False
    assert check.severity == FAILURE


# ------------------------------------------------------------------ restore verification


def _verify_restored(root: Path, rows: list[dict[str, object]]) -> int:
    import subprocess  # nosec B404 - a fixed repository script, no shell, no operator input

    return subprocess.run(  # nosec B603
        ["python", str(SCRIPTS / "artifact_restore_verify.py"), str(root)],
        input="\n".join(json.dumps(row) for row in rows),
        capture_output=True,
        text=True,
        check=False,
    ).returncode


@pytest.fixture
def restored(tmp_path: Path) -> tuple[Path, list[dict[str, object]]]:
    from hashlib import sha256

    payload = b"restored artifact bytes"
    digest = sha256(payload).hexdigest()
    (tmp_path / "sha256").mkdir()
    (tmp_path / "sha256" / digest).write_bytes(payload)
    return tmp_path, [
        {
            "content_hash": digest,
            "size_bytes": len(payload),
            "storage_key": f"sha256/{digest}",
        }
    ]


def test_a_complete_restore_verifies(restored: tuple[Path, list[dict[str, object]]]) -> None:
    root, rows = restored

    assert _verify_restored(root, rows) == 0


def test_missing_bytes_fail_restore_verification(
    restored: tuple[Path, list[dict[str, object]]],
) -> None:
    """§S21C3-062: a restore that lost bytes must not report success."""
    root, rows = restored
    (root / "sha256" / str(rows[0]["content_hash"])).unlink()

    assert _verify_restored(root, rows) != 0


def test_tampered_bytes_fail_restore_verification(
    restored: tuple[Path, list[dict[str, object]]],
) -> None:
    root, rows = restored
    (root / "sha256" / str(rows[0]["content_hash"])).write_bytes(b"different bytes entirely")

    assert _verify_restored(root, rows) != 0
