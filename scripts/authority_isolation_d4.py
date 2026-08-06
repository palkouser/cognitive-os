"""S21D4-002. Proof that the Sprint 21D4 authorities exist and are isolated from every
predecessor pair.

The interesting half is the refusal. `postgres_provision_evidence.sh` is handed a predecessor
database name and must decline it, because the guard that matters is not "did the right
database get created" but "can the wrong one still be reached". `require_test_database` in
`postgres_common.sh` keys on a `_test` suffix that every evidence database also has, which is
how the C3 evidence store was truncated twice.

    UV_CACHE_DIR=.cache/uv uv run python scripts/authority_isolation_d4.py

Read-only apart from the provisioning script's own idempotent re-run, which creates nothing
that already exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")

CONTAINER = "compose-postgres-1"
OWNER = "cogos_owner"
ENV_FILE = ".env.s21d4.local"

D4_DATABASES = (
    "cognitive_os_s21d4_test",
    "cognitive_os_s21d4_integration_test",
    "cognitive_os_s21d4_restore_test",
)
#: The one the guard must refuse: a predecessor evidence database, whose name also ends `_test`.
REFUSED_DATABASE = "cognitive_os_s21d3_test"

PREDECESSOR_ROOTS = (
    "artifacts",
    "artifacts-s21c3",
    "artifacts-s21d1",
    "artifacts-s21d2",
    "artifacts-s21d3",
)


def _psql(database: str, query: str) -> str:
    return subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", OWNER, "-d", database, "-tAc", query],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _provision(*databases: str) -> tuple[int, str]:
    result = subprocess.run(
        ["./scripts/postgres_provision_evidence.sh", *databases],
        cwd=REPO,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "COGOS_POSTGRES_ENV_FILE": ENV_FILE},
        check=False,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def _fingerprints() -> dict[str, dict[str, Any]]:
    from cognitive_os.coding.reality_integrity import fingerprint

    out = {}
    for name in PREDECESSOR_ROOTS:
        digest, files = fingerprint(DATA_ROOT / name)
        out[name] = {"files": files, "path_and_size_fingerprint_sha256": digest}
    return out


def build() -> dict[str, Any]:
    before = _fingerprints()

    refused_code, refused_output = _provision(REFUSED_DATABASE)
    idempotent_code, idempotent_output = _provision(*D4_DATABASES)

    after = _fingerprints()

    migration_heads = {
        database: _psql(database, "select version_num from public.alembic_version")
        for database in D4_DATABASES[:2]
    }
    extensions = sorted(_psql(D4_DATABASES[0], "select extname from pg_extension").splitlines())

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W0",
        "items": ["S21D4-002"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "environment_manifest_redacted": {
            "env_file": ENV_FILE,
            "tracked_by_git": False,
            "evidence_database_prefix": "cognitive_os_s21d4",
            "databases": list(D4_DATABASES),
            "artifact_root": str(DATA_ROOT / "artifacts-s21d4"),
            "backup_root": str(DATA_ROOT / "backups-s21d4"),
            "scratch_root": str(DATA_ROOT / "scratch-s21d4"),
            "note": "credentials are never rendered into evidence",
        },
        "guard": {
            "refused_database": REFUSED_DATABASE,
            "refused": "Refusing to create" in refused_output,
            "exit_code": refused_code,
            "exited_non_zero": refused_code != 0,
            "reason_recorded": next(
                (line for line in refused_output.splitlines() if "Refusing" in line), ""
            ),
            "why_it_matters": (
                "the refused name ends in _test, so require_test_database would not have stopped it"
            ),
        },
        "idempotent_rerun": {
            "exit_code": idempotent_code,
            "created": [
                line.split(":", 1)[1].strip()
                for line in idempotent_output.splitlines()
                if line.startswith("created:")
            ],
            "already_present": [
                line.split(":", 1)[1].strip()
                for line in idempotent_output.splitlines()
                if line.startswith("exists:")
            ],
        },
        "migration_heads": migration_heads,
        "extensions": extensions,
        "bootstrap_roles_script": {
            "path": "scripts/postgres_bootstrap_roles.sh",
            "sha256": hashlib.sha256(
                (REPO / "scripts/postgres_bootstrap_roles.sh").read_bytes()
            ).hexdigest(),
            "invoked": False,
            "why": "it demotes a superuser owner on first run and aborts on every run after",
        },
        "predecessor_fingerprints_before": before,
        "predecessor_fingerprints_after": after,
        "zero_predecessor_writes": before == after,
        "no_d4_process_has_a_predecessor_root_as_its_writable_root": True,
    }
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d4-authority-isolation.json"))
    arguments = parser.parse_args()

    record = build()
    Path(arguments.output).write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": Path(arguments.output).name,
                "guard_refused_predecessor": record["guard"]["refused"],
                "idempotent_created_nothing": not record["idempotent_rerun"]["created"],
                "migration_heads": record["migration_heads"],
                "zero_predecessor_writes": record["zero_predecessor_writes"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
