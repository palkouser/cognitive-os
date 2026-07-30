#!/usr/bin/env python3
"""Run the release verification matrix and record what every command actually did. §S21C3-065.

    scripts/verification_matrix.py --output docs/sprints/sprint-21/evidence/…-w6-matrix.json

The point of a matrix is not that the commands pass. It is that the list of commands is
written down once, run in one pass, and recorded with its exit codes — so "we ran the suite"
becomes a claim with a receipt instead of a memory of a terminal.

Three rules the runner enforces, because a release matrix that bends them is decoration:

* **A skipped command is recorded with the reason it was skipped.** A row that is simply
  absent is indistinguishable from a row that was quietly dropped after it failed.
* **Nothing here is retried.** A command that needed a second attempt is a finding.
* **No output is captured into the evidence file.** Command output can contain a database
  URL, a path, or a host name; the file records the command, its exit code, its duration and
  its last non-empty line, and the operator reads the terminal for the rest.

The environment supplies the isolated C3 handles (`COGOS_DATABASE_URL`, `COGOS_ARTIFACT_ROOT`,
normally from `.env.s21c3.local`). Commands whose prerequisites are absent are skipped by
name, never by silently passing.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess  # nosec B404 - a fixed table of repository commands, never a shell
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

REPOSITORY = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

#: Where a test row's artifacts land. Outside the working tree, and never the evidence root.
SCRATCH_ARTIFACT_ROOT = Path(
    os.environ.get("COGOS_SCRATCH_ARTIFACT_ROOT", "/tmp/cognitive-os-matrix-artifacts")  # nosec B108
)


@dataclass(frozen=True, slots=True)
class Command:
    name: str
    argv: tuple[str, ...]
    #: An environment variable that must be set, or a binary that must be on the path.
    requires: str | None = None
    #: Extra environment for this command only.
    environment: tuple[tuple[str, str], ...] = ()
    #: Which store this command may see. `scratch` is a database that exists to be erased;
    #: `evidence` is the isolated C3 pair, which no test suite is ever handed. W6-F2.
    store: str = "evidence"


def _pytest(*targets: str) -> tuple[str, ...]:
    """A test row. Every one of them runs against the scratch store, without exception.

    Not a preference. `tests/integration/postgres` truncates every table it finds, and several
    unit suites write into whatever `COGOS_DATABASE_URL` names — so a matrix that ran the
    suites with the evidence handles loaded would destroy the campaign it was verifying. It
    did, twice, before this field existed.
    """
    return (PYTHON, "-m", "pytest", *targets, "-q")


MATRIX: tuple[Command, ...] = (
    # ---- lint, types, security, contracts
    Command(
        "ruff_check",
        (
            PYTHON,
            "-m",
            "ruff",
            "check",
            "--config",
            "ruff.cognitive-os.toml",
            "src",
            "tests",
            "scripts",
            "infra",
        ),
    ),
    Command(
        "ruff_format",
        (
            PYTHON,
            "-m",
            "ruff",
            "format",
            "--check",
            "--config",
            "ruff.cognitive-os.toml",
            "src",
            "tests",
            "scripts",
            "infra",
        ),
    ),
    Command("mypy", (PYTHON, "-m", "mypy", "src/cognitive_os")),
    Command("bandit", (PYTHON, "-m", "bandit", "-r", "src/cognitive_os", "-q")),
    Command("schema_drift", (PYTHON, "-m", "cognitive_os.schemas.export", "--check")),
    Command("repository_language", ("./scripts/check_repository_language.sh",)),
    # ---- the suites, every one of them against the scratch store
    Command("unit_suite", _pytest("tests/cognitive_os"), store="scratch"),
    Command("contract_suite", _pytest("tests/contract"), store="scratch"),
    Command("full_suite", _pytest(), store="scratch"),
    Command(
        "coding_docker_slice",
        _pytest("tests/integration/coding"),
        requires="docker",
        environment=(("COGOS_RUN_SANDBOX_INTEGRATION", "1"),),
        store="scratch",
    ),
    Command(
        "postgres_integration",
        _pytest("tests/integration/postgres"),
        requires="COGOS_INTEGRATION_DATABASE_URL",
        store="scratch",
    ),
    # ---- the C3 operator surface
    Command("reality_inputs_validate", (PYTHON, "scripts/reality_inputs.py", "validate")),
    Command(
        "reality_inputs_stats",
        (PYTHON, "scripts/reality_inputs.py", "stats"),
        requires="COGOS_DATABASE_URL",
    ),
    Command(
        "reality_inputs_harvest",
        (PYTHON, "scripts/reality_inputs.py", "harvest"),
        requires="COGOS_DATABASE_URL",
    ),
    Command(
        "reality_inputs_verify",
        (PYTHON, "scripts/reality_inputs.py", "verify"),
        requires="COGOS_DATABASE_URL",
    ),
    # ---- storage integrity
    Command(
        "artifact_store_content",
        ("./scripts/verify_artifact_store.sh",),
        requires="COGOS_ARTIFACT_ROOT",
    ),
    Command(
        "development_pair_fingerprint",
        (
            PYTHON,
            "scripts/artifact_store_fingerprint.py",
            "/home/palkouser/projekt/cognitive-os-data/artifacts",
            "--expect",
            "7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf",
            "--expect-files",
            "5",
        ),
    ),
    Command("migration_head", (PYTHON, "scripts/verification_matrix.py", "--print-migration-head")),
    # ---- packaging
    Command("editable_install", ("./scripts/verify_editable_install.sh",)),
)


def _migration_head() -> str:
    versions = REPOSITORY / "infra" / "postgres" / "alembic" / "versions"
    heads = sorted(path.stem for path in versions.glob("*.py"))
    return heads[-1] if heads else "none"


def _available(requirement: str | None) -> bool:
    if requirement is None:
        return True
    if requirement.isupper():
        return bool(os.environ.get(requirement))
    return shutil.which(requirement) is not None


def _database_name(url: str) -> str:
    return url.rpartition("/")[2]


def _scratch_env() -> dict[str, str]:
    """The handles a test row gets. Never the evidence store. W6-F2.

    The Sprint 21C3 evidence store is named `..._test` like everything else, so the integration
    fixture's suffix guard let this matrix erase a whole campaign — twice, before the store
    field existed. The recovery was a restore from the backup this same matrix had just taken,
    which is a fine thing to have and a terrible thing to rely on.

    A collision here is refused rather than worked around: if the scratch handle names the
    evidence database, there is no safe way to run a suite, and continuing would repeat the
    incident this function exists to prevent.
    """
    # The artifact root goes too. A store is a database *and* a content-addressed directory,
    # and redirecting only the first left nineteen test-written blobs in the evidence root
    # before this line existed — harmless bytes, and still not evidence anyone recorded.
    artifacts = {"COGOS_ARTIFACT_ROOT": str(SCRATCH_ARTIFACT_ROOT)}
    SCRATCH_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

    scratch = os.environ.get("COGOS_INTEGRATION_DATABASE_URL")
    evidence = os.environ.get("COGOS_DATABASE_URL", "")
    if scratch is None:
        # Nothing to point the suites at, so the suites get no database at all. Every
        # PostgreSQL-backed test then skips with its own reason, which is a recorded outcome.
        return {"COGOS_DATABASE_URL": "", "COGOS_DATABASE_ADMIN_URL": "", **artifacts}
    if evidence and _database_name(scratch) == _database_name(evidence):
        raise SystemExit(
            f"refused: COGOS_INTEGRATION_DATABASE_URL names {_database_name(evidence)}, which is "
            "the evidence store. The suites truncate and write; give them a database of their own."
        )
    return {
        "COGOS_DATABASE_URL": scratch,
        "COGOS_DATABASE_ADMIN_URL": os.environ.get("COGOS_INTEGRATION_DATABASE_ADMIN_URL", scratch),
        "COGOS_TEST_DATABASE_URL": scratch,
        "COGOS_TRUNCATABLE_DATABASE": _database_name(scratch),
        **artifacts,
    }


def _run(command: Command) -> dict[str, object]:
    if not _available(command.requires):
        return {
            "name": command.name,
            "status": "skipped",
            "reason": f"{command.requires} is not available on this host",
            "exit_code": None,
            "seconds": 0.0,
        }
    overrides = dict(command.environment)
    if command.store == "scratch":
        overrides |= _scratch_env()
    environment = {**os.environ, **overrides}
    started = perf_counter()
    completed = subprocess.run(  # nosec B603
        list(command.argv),
        cwd=REPOSITORY,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    seconds = perf_counter() - started
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    return {
        "name": command.name,
        "status": "passed" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "seconds": round(seconds, 2),
        "last_line": lines[-1][:200] if lines else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--print-migration-head", action="store_true")
    arguments = parser.parse_args()
    if arguments.print_migration_head:
        print(_migration_head())
        return 0
    if arguments.output is None:
        print("refused: --output is required", file=sys.stderr)
        return 2

    results = []
    for command in MATRIX:
        result = _run(command)
        results.append(result)
        marker = {"passed": "ok  ", "failed": "FAIL", "skipped": "skip"}[str(result["status"])]
        print(
            f"{marker} {result['name']:<32} {result['seconds']:>7}s  {result.get('last_line', '')}"
        )

    evidence = {
        "sprint": "21C3",
        "wave": "W6",
        "item": "S21C3-065",
        "recorded_at": datetime.now(UTC).isoformat(),
        "migration_head": _migration_head(),
        # The database *name*, never the URL: this file is meant to be committed.
        "database": os.environ.get("COGOS_DATABASE_URL", "").rpartition("/")[2] or None,
        "commands": results,
        "passed": sum(1 for item in results if item["status"] == "passed"),
        "failed": sorted(str(item["name"]) for item in results if item["status"] == "failed"),
        "skipped": {
            str(item["name"]): item["reason"] for item in results if item["status"] == "skipped"
        },
    }
    arguments.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(
        f"\n{arguments.output}: {evidence['passed']} passed, "
        f"{len(evidence['failed'])} failed, {len(evidence['skipped'])} skipped"
    )
    return 0 if not evidence["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
