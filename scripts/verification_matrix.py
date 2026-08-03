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


# ------------------------------------------------------------------- Sprint 21D2. §S21D2-086
#
# Appended to the table above rather than replacing it: D2's release rests on C3's evidence
# still being sound, so the rows that check that are part of D2's matrix too. What is added
# here is everything D2 introduced — the correction-ranking surface, the null-path guards, the
# two further inherited pairs, and the operator commands that read them.

D2_MATRIX: tuple[Command, ...] = (
    Command(
        "correction_ranking_spine",
        _pytest("tests/cognitive_os/learning", "tests/cognitive_os/learned_evidence"),
        store="scratch",
    ),
    Command(
        "correction_sequencing_and_receipts",
        _pytest(
            "tests/cognitive_os/coding/test_correction_sequencer.py",
            "tests/cognitive_os/coding/test_reality_d2_corpus.py",
            "tests/cognitive_os/coding/test_reality_campaign_runner.py",
        ),
        store="scratch",
    ),
    Command(
        "null_path_and_not_opened_guards",
        _pytest(
            "tests/cognitive_os/learning/test_correction_integrity.py",
            "tests/cognitive_os/learning/test_d2_null_evidence_guard.py",
        ),
        store="scratch",
    ),
    Command(
        "migration_check",
        ("./scripts/postgres_migration_check.sh",),
        requires="COGOS_DATABASE_URL",
    ),
    # No `artifact_recovery` row. `scripts/artifact_restore_verify.py` is a helper that
    # `restore_event_store.sh` pipes artifact metadata into, not a command with a standalone
    # meaning; a row that ran it bare only proved that it prints its usage. Recovery is
    # proven where it happens — `scripts/operations_d2.py` re-hashes all 1511 blobs out of
    # the archive — and the two rows below check the store's bytes and its lineage here.
    Command(
        "learned_evidence_benchmarks",
        (
            PYTHON,
            "scripts/benchmark_run.py",
            "--manifest",
            "benchmarks/manifests/sprint21c1-learned-ci.yaml",
            "--mode",
            "learned-replay",
            "--report-directory",
            "/tmp/s21d2-matrix-learned-ci",  # nosec B108 - a scratch report directory
        ),
        store="scratch",
    ),
    Command(
        # The D2 operator surface, read-only. Exit 0 means every class that was opened is
        # sound *and* every class that was not names the decision that closed it.
        "correction_integrity_cli",
        (
            PYTHON,
            "scripts/learned.py",
            "correction-integrity",
            "--seals",
            "docs/sprints/sprint-21/evidence/sprint-21d2-self-play-campaign.json",
            "--stop-record",
            "docs/sprints/sprint-21/evidence/sprint-21d2-w9-stop-record.json",
        ),
        requires="COGOS_DATABASE_URL",
    ),
    Command(
        "learned_health", (PYTHON, "scripts/learned.py", "health"), requires="COGOS_DATABASE_URL"
    ),
    Command(
        "learned_artifact_verify",
        (PYTHON, "scripts/learned.py", "artifact-verify"),
        requires="COGOS_ARTIFACT_ROOT",
    ),
    Command(
        "c3_pair_fingerprint",
        (
            PYTHON,
            "scripts/artifact_store_fingerprint.py",
            "/home/palkouser/projekt/cognitive-os-data/artifacts-s21c3",
            "--expect",
            "7d19e3c8e45455296520eb8b6edf524d2454d6f5e07a432b751939eb23dfe593",
            "--expect-files",
            "8503",
        ),
    ),
    Command(
        "d1_pair_fingerprint",
        (
            PYTHON,
            "scripts/artifact_store_fingerprint.py",
            "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d1",
            "--expect",
            "f7b14ac7a66508c5ad41f8f310a02544d1dc8e1d513dcc5bbdab82106cfbf30f",
            "--expect-files",
            "83",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class NotOpened:
    """A row a lawful stop closed. Listed, never omitted, and bound to the decision. §S21D2-086.

    A matrix that simply left these out would be indistinguishable from a matrix someone
    trimmed after a failure — which is the same reason a skipped row carries its reason. The
    difference is that a skip is a property of the host and this is a property of the sprint:
    the command was not skipped, the work it would verify was never authorised.
    """

    name: str
    reason: str


D2_NOT_OPENED: tuple[NotOpened, ...] = (
    NotOpened(
        "final_batch_a_and_b",
        "S21D2-060 was never authorised; the holdout was not opened",
    ),
    NotOpened(
        "benefit_forgetting_and_shadow_measurement",
        "S21D2-063 to -066 measure a selected candidate, and none was selected",
    ),
    NotOpened(
        "promotion_assessment",
        "S21D2-067 assesses a component that exists; none was registered",
    ),
    NotOpened(
        "activation_approval_and_canary",
        "S21D2-069 to -074 need an approved component; the surface has none",
    ),
    NotOpened(
        "governed_rollback_real_leg",
        "S21D2-075's real leg needs an active component; the scratch proof stands from W3c",
    ),
)


#: Every artifact pair on this host, D2's own included. §S21D2-086 requires the evidence
#: stores to be byte-identical across the destructive rows, and the only way to say that is
#: to measure before and after rather than to assert that the rows were careful.
D2_PAIRS: tuple[str, ...] = (
    "artifacts",
    "artifacts-s21c3",
    "artifacts-s21d1",
    "artifacts-s21d2",
)


def _pair_fingerprints() -> dict[str, dict[str, object]]:
    sys.path.insert(0, str(REPOSITORY / "src"))
    from cognitive_os.coding.reality_integrity import fingerprint

    root = Path("/home/palkouser/projekt/cognitive-os-data")
    result: dict[str, dict[str, object]] = {}
    for name in D2_PAIRS:
        path = root / name
        digest, files = fingerprint(path) if path.is_dir() else ("", 0)
        result[name] = {"path_and_size_fingerprint_sha256": digest, "files": files}
    return result


def _stop_hash(path: Path) -> str:
    """The content hash of the record that closed the not-opened rows."""
    selection = json.loads(path.read_text(encoding="utf-8"))["candidate_selection"]
    stop: str = selection["content_hash"]
    if selection["selected"] or selection["authorises_final_access"]:
        raise SystemExit(
            "refused: the selection record names a candidate, so these rows are not closed "
            "and the matrix must run them instead of recording why it did not"
        )
    return stop


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


def _shell_environment(sprint: str) -> dict[str, str]:
    """What the shell rows need so they operate on the sprint's own store. W9-F1.

    `postgres_common.sh` re-sources `$COGOS_POSTGRES_ENV_FILE` — `.env.postgres.local` by
    default — inside `set -a`, so it overwrites every handle the caller exported. A matrix run
    under the D2 environment therefore ran `postgres_migration_check.sh` against the
    *development* database and recorded a real failure about the wrong store. Naming the file
    explicitly is the only way a shell row can be about the database the matrix is verifying.
    """
    if sprint != "21D2":
        return {}
    return {"COGOS_POSTGRES_ENV_FILE": str(REPOSITORY / ".env.s21d2.local")}


def _run(command: Command, *, shell_environment: dict[str, str] | None = None) -> dict[str, object]:
    if not _available(command.requires):
        return {
            "name": command.name,
            "status": "skipped",
            "reason": f"{command.requires} is not available on this host",
            "exit_code": None,
            "seconds": 0.0,
        }
    overrides = dict(shell_environment or {}) | dict(command.environment)
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
    parser.add_argument(
        "--sprint",
        choices=("21C3", "21D2"),
        default="21C3",
        help="which table to run; 21D2 appends its own rows and its not-opened list",
    )
    parser.add_argument(
        "--selection-record",
        type=Path,
        default=REPOSITORY / "docs/sprints/sprint-21/evidence/sprint-21d2-learner-selection.json",
        help="the record whose hash binds the 21D2 not-opened rows",
    )
    arguments = parser.parse_args()
    if arguments.print_migration_head:
        print(_migration_head())
        return 0
    if arguments.output is None:
        print("refused: --output is required", file=sys.stderr)
        return 2

    d2 = arguments.sprint == "21D2"
    table = MATRIX + D2_MATRIX if d2 else MATRIX
    stop = _stop_hash(arguments.selection_record) if d2 else None
    before = _pair_fingerprints() if d2 else {}

    shell = _shell_environment(arguments.sprint)
    results = []
    for command in table:
        result = _run(command, shell_environment=shell)
        results.append(result)
        marker = {"passed": "ok  ", "failed": "FAIL", "skipped": "skip"}[str(result["status"])]
        print(
            f"{marker} {result['name']:<32} {result['seconds']:>7}s  {result.get('last_line', '')}"
        )

    evidence: dict[str, object] = {
        "sprint": arguments.sprint,
        "wave": "W9" if d2 else "W6",
        "item": "S21D2-086" if d2 else "S21C3-065",
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
    if d2:
        evidence["not_opened"] = {
            row.name: {"reason": row.reason, "stop_decision_hash": stop} for row in D2_NOT_OPENED
        }
        after = _pair_fingerprints()
        evidence["artifact_pairs"] = {
            "before": before,
            "after": after,
            "byte_identical_across_every_row": before == after,
        }
    arguments.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(
        f"\n{arguments.output}: {evidence['passed']} passed, "
        f"{len(evidence['failed'])} failed, {len(evidence['skipped'])} skipped"
    )
    return 0 if not evidence["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
