#!/usr/bin/env python
"""S21D3-086: every check expected before release, run once, with its actual exit status.

    scripts/verification_matrix_d3.py [--output docs/.../sprint-21d3-verification-matrix.json]

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
import tomllib
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
            "git ls-files -z | grep -zv sprint-21d3-verification-matrix.json | "
            "xargs -0 uv run detect-secrets-hook --baseline .secrets.baseline",
        ),
    ),
    Row("dependency_audit", ("uv", "run", "pip-audit")),
    Row("packaging_build", ("uv", "build")),
    Row("wheel_installation", ("bash", "scripts/verify_distribution.sh")),
    Row("editable_installation", ("bash", "scripts/verify_editable_install.sh")),
    Row("pre_registration", ("uv", "run", "python", "scripts/pre_registration_d3.py", "--check")),
    # ------------------------------------------------------------------ D3 evidence
    Row(
        "d3_evidence_report",
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
            "/tmp/s21d3-matrix-ci",
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
            "/tmp/s21d3-matrix-seed",
        ),
    ),  # nosec B108
    # ------------------------------------------------------------------ negative rows
    Row(
        "predecessor_store_refused",
        ("uv", "run", "python", "scripts/learned.py", "d3-integrity"),
        expect="nonzero",
        because="refusing to open",
        env={
            "COGOS_POSTGRES_DATABASE": "cognitive_os_s21d3_test",
            "COGOS_ARTIFACT_ROOT": "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d2",
        },
    ),
    Row(
        "predecessor_database_refused",
        ("uv", "run", "python", "scripts/learned.py", "d3-integrity"),
        expect="nonzero",
        because="require an s21d3 database",
        env={"COGOS_POSTGRES_DATABASE": "cognitive_os_s21d2_test"},
    ),
    Row(
        "smoke_refuses_a_non_test_database",
        ("uv", "run", "python", "scripts/learned.py", "smoke", "--confirm-isolated"),
        expect="nonzero",
        because="isolated *_test database",
        env={"COGOS_DATABASE_ADMIN_URL": "postgresql+asyncpg://u@h/cognitive_os_dev"},
    ),
    # ------------------------------------------------- rows recorded from W7's own evidence
    Row(
        "postgres_backup_restart_restore",
        (),
        evidence=("sprint-21d3-operations.json", "restore.hashed_rows_match"),
    ),
    Row(
        "corruption_and_isolation_matrix",
        (),
        evidence=("sprint-21d3-operations.json", "corruption_matrix"),
    ),
    Row(
        "provisioning_and_migration",
        (),
        evidence=("sprint-21d3-operations.json", "provisioning.migration_is_expected"),
    ),
    Row(
        "pre_final_checkpoint",
        (),
        evidence=("sprint-21d3-pre-final-checkpoint.json", "decision.authorised_is_false"),
    ),
    Row(
        "retrieval_holdout_decision",
        (),
        evidence=("sprint-21d3-retrieval-holdout-result.json", "decision.first_failed_floor"),
    ),
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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

    Kept apart from the rows so neither can quietly become the other. A disclosure never
    turns a failed row green: `failed_rows` still names it, and the exit status still refuses.
    What this adds is the reason a reader would otherwise have to reconstruct.
    """
    runtime = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = runtime["project"]["dependencies"]
    return [
        {
            "row": "dependency_audit",
            "finding": "pip-audit reports five advisories against cryptography and setuptools",
            "packages": ["cryptography", "setuptools"],
            "declared_runtime_dependencies": dependencies,
            "is_a_declared_runtime_dependency": False,
            "arrives_through": "development and test tooling (PyJWT, pytest, mypy, babel)",
            "setuptools": (
                "uv.lock pins 83.0.0, which is the fixed version; the 78.1.0 this matrix "
                "audited is what the installed extra set resolves to, so four of the five "
                "advisories are a property of this environment rather than of the lock"
            ),
            "cryptography": (
                "uv.lock pins 49.0.0 against a fix in 50.0.0. It arrives through PyJWT, is "
                "not a runtime dependency, and is not in the security group's closure, which "
                "is why the CI security lane installs neither and does not see it"
            ),
            "why_the_release_is_not_blocked": (
                "neither package is one of the five declared runtime dependencies, so the "
                "built wheel ships neither"
            ),
            "what_would_clear_it": "cryptography >= 50.0.0 in uv.lock",
            "not_done_here_because": (
                "a lock change alters the environment every earlier wave's evidence was "
                "produced in, and section 10.3 treats that as invalidating the affected "
                "experiment; it is a decision for the release, not for an operations wave"
            ),
        }
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=EVIDENCE / "sprint-21d3-verification-matrix.json"
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
        "sprint": "21D3",
        "wave": "W7",
        "item": "S21D3-086",
        "purpose": (
            "Every check expected before release, run once, with its actual exit status. "
            "Negative rows must refuse for their declared reason; nothing is silently skipped."
        ),
        "started_at": started,
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _digest(
            (EVIDENCE / "sprint-21d3-pre-registration.json").read_text(encoding="utf-8")
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
    report["integrity_content_hash"] = _digest(json.dumps(report, sort_keys=True, default=str))

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "totals": report["totals"],
                "failed_rows": report["failed_rows"],
                "skipped_rows": report["skipped_rows"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not report["failed_rows"] and report["every_row_decided"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
