#!/usr/bin/env python
"""S21D4-086: every check expected before release, run once, with its actual exit status.

    scripts/verification_matrix_d4.py [--output docs/.../sprint-21d4-verification-matrix.json]

One row per command. Each records what was run, what it was expected to do, what it actually
did, how long it took, and the SHA-256 of its combined output — so a row that passes today and
fails tomorrow can be compared without anyone having kept the log.

Two rules make this a matrix rather than a list.

*Negative rows must fail for their expected reason.* A row declared `expect: nonzero` is a
finding when it succeeds, and a row that fails with a message other than the one it names is
also a finding. A destructive check that passes because it never ran is the failure mode this
exists to prevent.

*Nothing is silently skipped.* A row whose preconditions are absent is recorded as `skipped`
with the reason, and the totals count it — an evidence file reporting sixteen passes out of
sixteen rows when four never ran would be a report about the host, not about the release.

*The record checks itself, here.* `_structural_findings` asserts what the record has to be able
to be false about — every command row measured a cost, every negative row exists and refused,
every recorded row binds the bytes it read — and folds the result into the exit status. Those
checks began as a test module, which could not work: this command runs the whole suite as one of
its rows, so a test reading this record saw the previous run's copy and the command needed two
runs to go green. A release command that is not idempotent is a defect in the command.

The command is read-only with respect to every store: rows that would write are the ones the
W7 operations command already ran, and this matrix records their evidence rather than running
them again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess  # nosec B404 - fixed argv lists of repository commands, never a shell
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
RUFF_CONFIG = "ruff.cognitive-os.toml"


@dataclass(frozen=True, slots=True)
class Row:
    """One check: what it is, how to run it, and what counts as the right answer."""

    name: str
    argv: tuple[str, ...]
    #: `zero` for a check that must succeed, `nonzero` for one that must refuse.
    expect: str = "zero"
    #: For a negative row, a fragment its output must contain. A refusal for the wrong reason
    #: is not the refusal the row claims to demonstrate.
    because: str = ""
    #: Environment overrides. Used only by the negative rows, which exist to prove that a
    #: wrong environment is refused.
    env: dict[str, str] = field(default_factory=dict)
    #: An evidence file this row records rather than re-runs, with the key that decides it.
    evidence: tuple[str, str] | None = None


ROWS: tuple[Row, ...] = (
    # ------------------------------------------------------------------ formatting and lint
    Row(
        "ruff_check",
        ("uv", "run", "ruff", "check", "--config", RUFF_CONFIG, "src", "tests", "scripts", "infra"),
    ),
    Row(
        "ruff_format",
        (
            "uv",
            "run",
            "ruff",
            "format",
            "--check",
            "--config",
            RUFF_CONFIG,
            "src",
            "tests",
            "scripts",
            "infra",
        ),
    ),
    Row("mypy", ("uv", "run", "mypy", "src/cognitive_os")),
    Row("bandit", ("uv", "run", "bandit", "-q", "-r", "src/cognitive_os")),
    # ------------------------------------------------------------------ suites
    Row("full_suite", ("uv", "run", "pytest", "-q", "--timeout=600")),
    Row("correction_slice", ("uv", "run", "pytest", "-q", "tests/cognitive_os/learning")),
    Row(
        "retrieval_slice",
        (
            "uv",
            "run",
            "pytest",
            "-q",
            "tests/cognitive_os/experience",
            "tests/cognitive_os/coding/test_d3_retrieval_holdout.py",
        ),
    ),
    Row(
        "lifecycle_slice",
        ("uv", "run", "pytest", "-q", "tests/cognitive_os/learned_evidence"),
    ),
    # ------------------------------------------------------------------ contracts and policy
    Row("schema_export", ("uv", "run", "python", "-m", "cognitive_os.schemas.export", "--check")),
    Row("repository_language", ("bash", "scripts/check_repository_language.sh")),
    # W7-A4. These four are the released commands from `.github/workflows/ci.yml`, not
    # approximations of them. The first version of this matrix invented `pip-audit --strict`,
    # `python -m build` and a bare `detect-secrets scan`, and three rows failed for reasons
    # that said nothing about the release: a matrix that runs its own checks measures itself.
    # This matrix's own output is excluded, and only this matrix's own output: a file whose
    # hashes are written at the end of a run cannot be scanned by the run that writes it. The
    # release workflow regenerates the baseline and re-scans afterwards, which is what covers
    # it — recorded here rather than left as folklore.
    Row(
        "secrets_scan",
        (
            "bash",
            "-c",
            "git ls-files -z | grep -zv sprint-21d4-verification-matrix.json | "
            "xargs -0 uv run detect-secrets-hook --baseline .secrets.baseline",
        ),
    ),
    Row("dependency_audit", ("uv", "run", "pip-audit")),
    Row("packaging_build", ("uv", "build")),
    Row("wheel_installation", ("bash", "scripts/verify_distribution.sh")),
    Row("editable_installation", ("bash", "scripts/verify_editable_install.sh")),
    Row("pre_registration", ("uv", "run", "python", "scripts/pre_registration_d4.py", "--check")),
    # ------------------------------------------------------------------ D4 evidence
    Row(
        "d4_evidence_report",
        ("uv", "run", "python", "scripts/learned.py", "d4-integrity"),
        env={"COGOS_POSTGRES_DATABASE": "cognitive_os_s21d4_test"},
    ),
    # The released D3 command, still green over its own evidence. D4 changed the shared
    # `experience.py` canonical form and the promotion payload, so "D3's report still reports"
    # is a claim about this release rather than about the last one.
    Row(
        "d3_evidence_report_still_green",
        ("uv", "run", "python", "scripts/learned.py", "d3-integrity"),
        env={"COGOS_POSTGRES_DATABASE": "cognitive_os_s21d3_test"},
    ),
    Row(
        "benchmark_replay_ci",
        (
            "uv",
            "run",
            "python",
            "scripts/benchmark_run.py",
            "--manifest",
            "benchmarks/manifests/sprint21c1-learned-ci.yaml",
            "--mode",
            "learned-replay",
            "--report-directory",
            "/tmp/s21d4-matrix-ci",
        ),
    ),  # nosec B108
    Row(
        "benchmark_replay_seed",
        (
            "uv",
            "run",
            "python",
            "scripts/benchmark_run.py",
            "--manifest",
            "benchmarks/manifests/sprint21c1-learned-seed.yaml",
            "--mode",
            "learned-replay",
            "--report-directory",
            "/tmp/s21d4-matrix-seed",
        ),
    ),  # nosec B108
    # ------------------------------------------------------------------ negative rows
    Row(
        "predecessor_store_refused",
        ("uv", "run", "python", "scripts/learned.py", "d4-integrity"),
        expect="nonzero",
        because="refusing to open",
        env={
            "COGOS_POSTGRES_DATABASE": "cognitive_os_s21d4_test",
            "COGOS_ARTIFACT_ROOT": "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d2",
        },
    ),
    # The root D3 could not have refused, because D3 wrote it. It is the one an operator is
    # most likely to still have exported, which is why it gets a row of its own.
    Row(
        "d3_store_refused",
        ("uv", "run", "python", "scripts/learned.py", "d4-integrity"),
        expect="nonzero",
        because="refusing to open the predecessor store",
        env={
            "COGOS_POSTGRES_DATABASE": "cognitive_os_s21d4_test",
            "COGOS_ARTIFACT_ROOT": "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d3",
        },
    ),
    Row(
        "predecessor_database_refused",
        ("uv", "run", "python", "scripts/learned.py", "d4-integrity"),
        expect="nonzero",
        because="require an s21d4 database",
        env={"COGOS_POSTGRES_DATABASE": "cognitive_os_s21d3_test"},
    ),
    # The artifact root is supplied so the refusal under test is the *database name*. This
    # matrix runs with no sourced environment, and without a root the smoke refuses for a
    # missing root instead — a refusal for the wrong reason, which this matrix treats as a
    # failure rather than as a pass.
    Row(
        "smoke_refuses_a_non_test_database",
        ("uv", "run", "python", "scripts/learned.py", "smoke", "--confirm-isolated"),
        expect="nonzero",
        because="isolated *_test database",
        env={
            "COGOS_DATABASE_ADMIN_URL": "postgresql+asyncpg://u@h/cognitive_os_dev",
            "COGOS_ARTIFACT_ROOT": "/tmp/s21d4-matrix-never-opened",  # nosec B108
        },
    ),
    # ------------------------------------------------- rows recorded from W7's own evidence
    Row(
        "postgres_backup_restart_restore",
        (),
        evidence=("sprint-21d4-operations.json", "restore.hashed_rows_match"),
    ),
    Row(
        "corruption_and_isolation_matrix",
        (),
        evidence=("sprint-21d4-operations.json", "corruption_matrix"),
    ),
    Row(
        "provisioning_and_migration",
        (),
        evidence=("sprint-21d4-operations.json", "provisioning.migration_is_expected"),
    ),
    Row(
        "pre_final_checkpoint",
        (),
        evidence=("sprint-21d4-pre-final-checkpoint.json", "decision.authorised_is_false"),
    ),
    Row(
        "learner_selection_null",
        (),
        evidence=("sprint-21d4-learner-selection.json", "selection.stop_kind"),
    ),
    Row(
        "retrieval_holdout_decision",
        (),
        evidence=("sprint-21d4-retrieval-decision.json", "first_failed_floor"),
    ),
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(value: object) -> bytes:
    """The D4 convention: the bytes that are hashed are the bytes that are written.

    D3's originals hashed a compact serialisation and wrote an indented one, so recomputing the
    seal from the file gave a different number. Every other D4 record uses this rule, and two
    records that verified differently from the other twenty would be a trap rather than a
    difference.
    """
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode(
        "utf-8"
    )


def _dig(document: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(document, dict) or part not in document:
            return None
        document = document[part]
    return document


def _from_evidence(row: Row) -> dict[str, Any]:
    """A row this command records rather than re-runs, decided by the evidence file itself."""
    assert row.evidence is not None
    name, key = row.evidence
    path = EVIDENCE / name
    if not path.is_file():
        return {
            "status": "skipped",
            "reason": f"{name} is not present, so this row was not decided",
            "evidence": name,
        }
    document = json.loads(path.read_text(encoding="utf-8"))
    if key == "corruption_matrix":
        rows = document.get("corruption_matrix", [])
        passed = bool(rows) and all(item["observed"]["failed_closed"] for item in rows)
        detail: Any = f"{len(rows)} cases, all failed closed" if passed else "a case stayed open"
    elif key == "decision.authorised_is_false":
        passed = document["decision"]["authorised"] is False
        detail = f"authorised={document['decision']['authorised']}"
    else:
        value = _dig(document, key)
        passed = bool(value) if not isinstance(value, str) else True
        detail = f"{key}={value}"
    return {
        "status": "passed" if passed else "failed",
        "evidence": name,
        "evidence_sha256": _digest(path.read_text(encoding="utf-8")),
        "detail": detail,
    }


def _execute(row: Row) -> dict[str, Any]:
    if row.evidence is not None:
        return {"name": row.name, "kind": "recorded", **_from_evidence(row)}

    started = time.monotonic()
    completed = subprocess.run(  # nosec B603 - fixed argv list, shell=False
        list(row.argv),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPOSITORY,
        env={**os.environ, **row.env},
    )
    elapsed = round(time.monotonic() - started, 2)
    output = completed.stdout + completed.stderr
    refused = completed.returncode != 0
    if row.expect == "zero":
        passed = not refused
        reason = "" if passed else output.strip().splitlines()[-1][:200] if output else ""
    else:
        passed = refused and row.because in output
        reason = (
            ""
            if passed
            else f"expected a refusal naming {row.because!r}, got exit {completed.returncode}"
        )
    return {
        "name": row.name,
        "kind": "command",
        "command": " ".join(row.argv),
        "environment_overrides": sorted(row.env),
        "expect": row.expect,
        "expected_reason": row.because,
        "exit_status": completed.returncode,
        "duration_seconds": elapsed,
        "output_sha256": _digest(output),
        "status": "passed" if passed else "failed",
        "detail": reason,
    }


def _disclosures() -> list[dict[str, Any]]:
    """Findings a row records that the release is nonetheless not blocked by, and why.

    Kept apart from the rows so neither can quietly become the other. A disclosure never turns
    a failed row green: `failed_rows` still names it, and the exit status still refuses. What
    this adds is the reason a reader would otherwise have to reconstruct.

    The list is empty on a clean run, and that is the honest shape: a disclosure that outlived
    the finding it explains is a claim about a state the repository has left. D3's dependency
    disclosure is exactly that: the bump it describes is in the lock this sprint inherited, so
    repeating it here would be D4 claiming a finding it did not make.
    """
    return []


def _structural_findings(report: dict[str, Any]) -> list[str]:
    """What the record has to be able to be false about, checked where it is written.

    These used to be a test class, and a test that reads this record cannot pass during the run
    that writes it: the matrix runs the whole suite as one of its own rows, so the suite saw the
    *previous* record and the command needed two runs to go green. A release command that is not
    idempotent is a defect in the command, so the checks moved here, where they contribute to
    the exit status instead of to the next run.
    """
    rows = {row["name"]: row for row in report["rows"]}
    findings: list[str] = []

    commands = [row for row in report["rows"] if row["kind"] == "command"]
    if not commands:
        findings.append("no row ran a command, so this matrix measured nothing")
    for row in commands:
        if not row["command"] or row["duration_seconds"] <= 0 or len(row["output_sha256"]) != 64:
            findings.append(f"{row['name']} recorded no measured cost")

    negatives = {name for name, row in rows.items() if row.get("expect") == "nonzero"}
    required = {
        "predecessor_store_refused",
        "d3_store_refused",
        "predecessor_database_refused",
        "smoke_refuses_a_non_test_database",
    }
    if not required <= negatives:
        findings.append(f"negative rows missing: {sorted(required - negatives)}")
    for name in sorted(negatives):
        if rows[name]["exit_status"] == 0:
            findings.append(f"{name} was expected to refuse and did not")

    recorded = [row for row in report["rows"] if row["kind"] == "recorded"]
    if not recorded:
        findings.append("no row was decided from committed evidence")
    for row in recorded:
        path = EVIDENCE / str(row.get("evidence", ""))
        if not path.is_file():
            findings.append(f"{row['name']} names evidence that is not committed")
        elif row.get("evidence_sha256") != _digest(path.read_text(encoding="utf-8")):
            findings.append(f"{row['name']} does not bind the bytes it read")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=EVIDENCE / "sprint-21d4-verification-matrix.json"
    )
    parser.add_argument("--only", help="run one row by name, for iterating on it")
    arguments = parser.parse_args()

    selected = [row for row in ROWS if not arguments.only or row.name == arguments.only]
    started = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    results = [_execute(row) for row in selected]
    totals = {
        state: sum(1 for item in results if item["status"] == state)
        for state in ("passed", "failed", "skipped")
    }

    report = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W7",
        "item": "S21D4-086",
        "purpose": (
            "Every check expected before release, run once, with its actual exit status. "
            "Negative rows must refuse for their declared reason; nothing is silently skipped."
        ),
        "started_at": started,
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _digest(
            (EVIDENCE / "sprint-21d4-pre-registration.json").read_text(encoding="utf-8")
        ),
        "final_outcomes_inspected": False,
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "database": os.environ.get("COGOS_POSTGRES_DATABASE", "not set"),
            "artifact_root": os.environ.get("COGOS_ARTIFACT_ROOT", "not set"),
        },
        "rows": results,
        "totals": {**totals, "rows": len(results)},
        "every_row_decided": totals["skipped"] == 0,
        "failed_rows": [item["name"] for item in results if item["status"] == "failed"],
        "disclosures": _disclosures(),
        "skipped_rows": [item["name"] for item in results if item["status"] == "skipped"],
    }
    report["structural_findings"] = _structural_findings(report)
    seal = hashlib.sha256(_canonical(report)).hexdigest()

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(_canonical({**report, "integrity_content_hash": seal}))
    report["integrity_content_hash"] = seal
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "totals": report["totals"],
                "failed_rows": report["failed_rows"],
                "skipped_rows": report["skipped_rows"],
                "structural_findings": report["structural_findings"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return (
        0
        if not report["failed_rows"]
        and report["every_row_decided"]
        and not report["structural_findings"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
