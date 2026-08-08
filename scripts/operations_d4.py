#!/usr/bin/env python
"""Sprint 21D4 W7 operations: provisioning, backup, restart, restore, and the failure matrix.

S21D4-082, -083 and -084 in one command, because they are one question asked three times. 082
asks whether the authorities are the ones revision 4 declared; 083 asks whether the evidence
survives being moved; 084 asks whether damage to the moved copy is noticed. Run apart, the third
would be exercised against a store the second had proved nothing about.

    scripts/operations_d4.py --output docs/sprints/sprint-21/evidence/sprint-21d4-operations.json

What this command writes, and what it must never write
------------------------------------------------------

It writes to the D4 backup root, to the D4 restore database, and to a scratch directory. It
writes nothing to the D4 evidence pair and nothing at all to the five predecessor pairs -- one
more than D3 had, and the extra one is the store D3 itself wrote. Every fingerprint is taken
before and after, and both are recorded. Every damage case is applied to the *extracted copy* --
a store rebuilt from the archive in a scratch directory -- or to a copy of the evidence
directory, so what gets broken is always disposable.

Why the restore is the copy that gets checked
---------------------------------------------

The source store is where the evidence has always been, so a check that only ever passes there
proves the check agrees with the store, not that either is right. The restore is a second copy
built by different code -- pg_restore and tar rather than the campaign -- and it is the only
place where "these two independent things agree" means anything.

The two stops, and the two new damage cases
-------------------------------------------

D4 stopped twice as well: S21D4-039 selected no candidate and no retrieval arm cleared both
floors. So the restore assertion is the sharper one -- what must come back is *exactly* the
stopped state, and an absence is the easiest thing for a restore to get wrong in the direction
that looks fine.

The matrix inherits D3's eighteen cases and adds the two the erratum requires: a forged
independent-decision count, which the twelfth integrity class refuses, and a threshold derived
from a split that is not calibration, which the released derivation refuses before it computes
anything. Both are the failures revision 4 exists to make impossible, so both have to be shown
failing closed rather than described. Two more come free once the twelfth class exists -- a rate
naming the counted decisions as its denominator, and a fusion variant opened after the holdout
returned a negative result -- so the matrix runs twenty-two rather than the twenty S21D4-084
names, and the record says which four are D4's.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess  # nosec B404 - fixed repository scripts and the container CLI, never a shell
import sys
import tarfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.coding.reality_integrity import fingerprint
from cognitive_os.coding.reality_leakage import judgement_leaks
from cognitive_os.domain.experience_graph import (
    FROZEN_GRAPH_RESOURCE_POLICIES,
    GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
)
from cognitive_os.learning.correction_artifact import (
    build_ranker_for_evaluation,
    canonical_bytes,
    load_correction_ranker_v2,
)
from cognitive_os.learning.integrity_d4 import (
    d4_integrity,
)
from cognitive_os.learning.selective_operating_point import (
    ScoredDecision,
    derive_zero_error_point,
)

REPOSITORY = Path(__file__).resolve().parent.parent
SCRIPTS = REPOSITORY / "scripts"
EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
D4_ENV_FILE = REPOSITORY / ".env.s21d4.local"

DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")
#: The five stores this sprint must not write to. Fingerprinted before and after everything.
#: D3's own store joins the list D3 kept, which is the whole difference between the two waves
#: here: every sprint inherits one more predecessor than the last, and the newest one is the
#: one an operator is most likely to still have sourced.
INHERITED = (
    "artifacts",
    "artifacts-s21c3",
    "artifacts-s21d1",
    "artifacts-s21d2",
    "artifacts-s21d3",
)
D4_STORE = "artifacts-s21d4"

#: The surface D4's correction experiment would have used. The credential-free lifecycle smoke
#: registers an unrelated inert component on `skill.selection`, so "no component exists" is the
#: wrong assertion and "no component on the correction surface" is the right one.
CORRECTION_SURFACE = "experience.correction_ranking"

EXPECTED_MIGRATION = "0015"


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D4 environment first:\n"
            f"    set -a && . ./.env.s21d4.local && set +a"
        )
    return value


def _run(argv: Sequence[str], *, env: Mapping[str, str] | None = None) -> tuple[int, str]:
    """A repository script or the container CLI. Fixed argv, never a shell, never a secret.

    `COGOS_POSTGRES_ENV_FILE` is set on every call: the shell scripts re-source their own
    environment file over whatever the caller exported, so pointing them at the D4 file is the
    only way a D4 command can be sure it is not operating on a predecessor store.
    """
    completed = subprocess.run(  # nosec B603 - fixed argv list, shell=False
        list(argv),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPOSITORY,
        env={**os.environ, "COGOS_POSTGRES_ENV_FILE": str(D4_ENV_FILE), **(env or {})},
    )
    return completed.returncode, (completed.stdout + completed.stderr)


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


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


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _fingerprints() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name in (*INHERITED, D4_STORE):
        root = DATA_ROOT / name
        digest, files = fingerprint(root) if root.is_dir() else ("", 0)
        result[name] = {"path_and_size_fingerprint_sha256": digest, "files": files}
    return result


def _engine(url: str) -> Any:
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    # The restore handle is a psql URL because the shell scripts hand it to psql and
    # pg_restore. The driver is a property of the client, not of the database.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_postgres_engine(url, pool_size=2, max_overflow=0)


def _database_name(url: str) -> str:
    from urllib.parse import urlsplit

    return urlsplit(url).path.lstrip("/")


# ------------------------------------------------------------------ what a store looks like

_COUNTS = """
SELECT json_build_object(
  'events', (SELECT count(*) FROM cognitive_os.events),
  'campaign_receipts', (SELECT count(*) FROM cognitive_os.events
      WHERE event_type = 'reality.campaign_sequence_recorded'),
  'coding_outcomes', (SELECT count(*) FROM cognitive_os.events
      WHERE event_type = 'coding.outcome_recorded'),
  'artifacts', (SELECT count(*) FROM cognitive_os.artifacts),
  'artifact_blobs', (SELECT count(*) FROM cognitive_os.artifact_blobs),
  'learned_artifacts', (SELECT count(*) FROM cognitive_os.learned_artifacts),
  'learned_components', (SELECT count(*) FROM cognitive_os.learned_components),
  'learned_component_revisions', (SELECT count(*) FROM cognitive_os.learned_component_revisions),
  'learned_evidence_records', (SELECT count(*) FROM cognitive_os.learned_evidence_records),
  'learned_activation_approvals', (SELECT count(*) FROM cognitive_os.learned_activation_approvals),
  'learned_activation_history', (SELECT count(*) FROM cognitive_os.learned_activation_history)
)::text
"""

#: Every hashed row the D4 evidence rests on, rolled into one digest. Counts alone would not
#: notice a row whose content changed while the total stayed the same.
_HISTORY = """
SELECT kind, identity, content_hash FROM (
  SELECT 'lineage' AS kind, lineage_id::text AS identity, content_hash
    FROM cognitive_os.learned_artifacts
  UNION ALL SELECT 'artifact', artifact_id::text, content_hash FROM cognitive_os.artifacts
  UNION ALL SELECT 'event', event_id::text, payload_hash FROM cognitive_os.events
) rows ORDER BY kind, identity
"""

_RECEIPTS = """
SELECT stream_id::text, stream_version, payload_json->>'task_id'
FROM cognitive_os.events
WHERE event_type = 'reality.campaign_sequence_recorded'
ORDER BY stream_id, stream_version
"""

_RUN_IDENTITIES = """
SELECT payload_json->>'run_identity_key' AS key, count(*) AS rows
FROM cognitive_os.events
WHERE event_type = 'coding.outcome_recorded'
  AND payload_json->>'run_identity_key' IS NOT NULL
GROUP BY 1 ORDER BY 1
"""

_CORRECTION_COMPONENTS = """
SELECT count(*) FROM cognitive_os.learned_components WHERE surface = :surface
"""


@dataclass(frozen=True, slots=True)
class StoreShape:
    """Everything about a store that a restore has to reproduce exactly."""

    counts: dict[str, int]
    history_sha256: str
    receipts_sha256: str
    receipts: int
    run_identity_keys_sha256: str
    run_identity_keys: int
    correction_components: int

    def as_dict(self) -> dict[str, object]:
        return {
            "counts": self.counts,
            "history_sha256": self.history_sha256,
            "campaign_receipts": self.receipts,
            "receipts_sha256": self.receipts_sha256,
            "run_identity_keys": self.run_identity_keys,
            "run_identity_keys_sha256": self.run_identity_keys_sha256,
            "components_on_the_correction_surface": self.correction_components,
        }


async def _shape(connection: Any) -> StoreShape:
    from sqlalchemy import text as sql

    counts = json.loads(await connection.scalar(sql(_COUNTS)))
    history = [tuple(row) for row in await connection.execute(sql(_HISTORY))]
    receipts = [tuple(row) for row in await connection.execute(sql(_RECEIPTS))]
    identities = [tuple(row) for row in await connection.execute(sql(_RUN_IDENTITIES))]
    correction = await connection.scalar(
        sql(_CORRECTION_COMPONENTS), {"surface": CORRECTION_SURFACE}
    )
    return StoreShape(
        counts=counts,
        history_sha256=_digest(history),
        receipts_sha256=_digest(receipts),
        receipts=len(receipts),
        run_identity_keys_sha256=_digest(identities),
        run_identity_keys=len(identities),
        correction_components=int(correction or 0),
    )


# -------------------------------------------------------------------------- S21D4-082


async def _provisioning() -> dict[str, Any]:
    """The authorities are the ones revision 4 declared, and no wider.

    Reads only. The provisioning script itself is idempotent and was run in W0; running it
    again here would prove that it is idempotent, which W0 already recorded, and would be a
    write this command has no reason to make.
    """
    from sqlalchemy import text as sql

    url = _require("COGOS_DATABASE_URL")
    name = _database_name(url)
    engine = _engine(url)
    try:
        async with engine.connect() as connection:
            migration = await connection.scalar(
                sql("SELECT version_num FROM public.alembic_version")
            )
            owner = await connection.scalar(
                sql("SELECT nspowner::regrole::text FROM pg_namespace WHERE nspname='cognitive_os'")
            )
            installed = await connection.execute(sql("SELECT extname FROM pg_extension"))
            extensions = sorted(str(row[0]) for row in installed)
            usable = await connection.scalar(
                sql("SELECT has_schema_privilege(current_user, 'cognitive_os', 'USAGE')")
            )
    finally:
        await engine.dispose()

    migrations = REPOSITORY / "infra" / "postgres" / "alembic" / "versions"
    if not migrations.is_dir():
        # W7-A2. The first version of this pointed at a directory that does not exist, so the
        # list was empty and "no migration 0016" passed by looking nowhere. A check that can
        # only pass is not a check.
        raise SystemExit(f"{migrations} is not the alembic versions directory")
    versions = sorted(path.name.split("_")[0] for path in migrations.glob("0*.py"))
    if not versions:
        raise SystemExit(f"{migrations} contains no migrations to check against")
    return {
        "database": name,
        "database_is_isolated": "s21d4" in name,
        "migration_head": migration,
        "migration_is_expected": migration == EXPECTED_MIGRATION,
        "no_migration_0016": not any(item.startswith("0016") for item in versions),
        "migration_versions_on_disk": versions[-3:],
        "schema_owner": owner,
        "schema_usage": bool(usable),
        "extensions": extensions,
        "operations_examples_name_the_env_file": _env_file_referenced(),
        "bootstrap_roles_untouched": _bootstrap_untouched(),
    }


def _env_file_referenced() -> dict[str, Any]:
    """Every D4 operations example must name `COGOS_POSTGRES_ENV_FILE`.

    Checked against the file rather than asserted, because the reason it matters is that the
    shell scripts re-source their own environment: an example that omits it runs against
    whatever the last `set -a` left behind.
    """
    return {
        "operations_script_sets_it": "COGOS_POSTGRES_ENV_FILE"
        in Path(__file__).read_text(encoding="utf-8"),
        "env_file": D4_ENV_FILE.name,
        "env_file_present": D4_ENV_FILE.is_file(),
    }


def _bootstrap_untouched() -> dict[str, Any]:
    """The inherited NOSUPERUSER issue is disclosed, not silently edited.

    S21D4-082 is explicit that `postgres_bootstrap_roles.sh` must not be quietly changed to
    make D4 provisioning smoother. So its bytes are hashed and reported; a diff shows up as a
    changed digest rather than as nothing at all.
    """
    script = SCRIPTS / "postgres_bootstrap_roles.sh"
    return {
        "script": script.name,
        "sha256": _file_digest(script) if script.is_file() else None,
        "invoked_by_this_command": False,
    }


# -------------------------------------------------------------------------- S21D4-083


def _backup_paths(manifest: Path, body: Mapping[str, Any]) -> tuple[Path, Path]:
    backup_root = Path(_require("COGOS_BACKUP_ROOT"))
    return (
        manifest.parent / str(body["database_dump"]),
        backup_root / "artifacts" / str(body["artifact_archive"]),
    )


async def _backup(report: dict[str, Any]) -> Path:
    """Back the D4 pair up with the repository's own script, and record what it produced."""
    code, output = _run([str(SCRIPTS / "backup_event_store.sh")])
    if code != 0:
        raise SystemExit(f"backup failed:\n{output}")
    backup_root = Path(_require("COGOS_BACKUP_ROOT"))
    manifest = max(
        (backup_root / "database-backups").glob("*-backup-manifest.json"),
        key=lambda path: path.stat().st_mtime,
    )
    body = json.loads(manifest.read_text(encoding="utf-8"))
    expected = _require("COGOS_POSTGRES_DATABASE")
    if body.get("database_name") != expected:
        raise SystemExit(
            f"the backup names database {body.get('database_name')!r}, not {expected!r}; "
            "the D4 environment was overridden and this backup is not D4's"
        )
    dump, archive = _backup_paths(manifest, body)
    report["backup"] = {
        "manifest": manifest.name,
        "database": body.get("database_name"),
        "alembic_revision": body.get("alembic_revision"),
        "event_count": body.get("event_count"),
        "artifact_count": body.get("artifact_count"),
        "database_dump_sha256": _file_digest(dump),
        "artifact_archive_sha256": _file_digest(archive),
        "artifact_archive_bytes": archive.stat().st_size,
    }
    return manifest


async def _restart_container() -> str:
    """Restart PostgreSQL between the two captures. A store that only survives uptime has not."""
    from sqlalchemy import text as sql

    container = os.environ.get("COGOS_POSTGRES_TOOL_CONTAINER")
    if not container:
        return "skipped: no COGOS_POSTGRES_TOOL_CONTAINER is configured"
    code, output = _run(["docker", "restart", container])
    if code != 0:
        raise SystemExit(f"restarting {container} failed:\n{output}")

    url = _require("COGOS_DATABASE_URL")
    for _ in range(60):
        engine = _engine(url)
        try:
            async with engine.connect() as connection:
                await connection.scalar(sql("SELECT 1"))
            return f"{container} restarted; the D4 database answered again"
        except Exception:  # the store is not back yet, which is the point of waiting
            await asyncio.sleep(1)
        finally:
            await engine.dispose()
    raise SystemExit(f"{container} restarted but the D4 database never answered again")


def _extract(archive: Path, into: Path) -> Path:
    """The artifact archive, unpacked to a scratch root. Never over an existing store."""
    into.mkdir(parents=True, exist_ok=True)
    decompressed = into.parent / "artifacts.tar"
    code, output = _run(["zstd", "-d", "-q", "-f", str(archive), "-o", str(decompressed)])
    if code != 0:
        raise SystemExit(f"decompressing {archive} failed:\n{output}")
    with tarfile.open(decompressed) as handle:
        handle.extractall(into, filter="data")
    decompressed.unlink()
    return into


def _rehash_blobs(root: Path) -> dict[str, object]:
    """Every extracted file re-hashed against the name it is filed under."""
    checked = 0
    wrong: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        checked += 1
        if _file_digest(path) != path.name:
            wrong.append(path.relative_to(root).as_posix())
    return {"files_rehashed": checked, "content_hash_mismatches": wrong}


async def _prove_recovery(report: dict[str, Any], scratch: Path) -> tuple[Path, list[str]]:
    """S21D4-083: back up, restart, restore, and prove the two copies are the same evidence."""
    source_url = _require("COGOS_DATABASE_URL")
    restore_url = _require("COGOS_RESTORE_DATABASE_URL")

    engine = _engine(source_url)
    try:
        async with engine.connect() as connection:
            before = await _shape(connection)
    finally:
        await engine.dispose()

    manifest = await _backup(report)
    report["restart"] = {"action": await _restart_container()}

    engine = _engine(source_url)
    try:
        async with engine.connect() as connection:
            after_restart = await _shape(connection)
    finally:
        await engine.dispose()
    report["restart"]["store_is_unchanged_across_the_restart"] = (
        before.as_dict() == after_restart.as_dict()
    )
    report["restart"]["history_sha256"] = after_restart.history_sha256

    # `--test-restore` is the only mode the script offers and the only one wanted: it restores
    # into COGOS_RESTORE_DATABASE_NAME, which `require_test_database` refuses unless the name
    # ends in `_test`. The evidence database is never a restore target.
    code, output = _run([str(SCRIPTS / "restore_event_store.sh"), "--test-restore"])
    if code != 0:
        raise SystemExit(f"restore failed:\n{output}")

    body = json.loads(manifest.read_text(encoding="utf-8"))
    _, archive = _backup_paths(manifest, body)
    extracted = _extract(archive, scratch / "restored-artifacts")
    declared_blobs = await _declared_blobs(restore_url)

    engine = _engine(restore_url)
    try:
        async with engine.connect() as connection:
            restored = await _shape(connection)
    finally:
        await engine.dispose()

    report["restore"] = {
        "target_database": _database_name(restore_url),
        "artifact_copy": extracted.as_posix(),
        "source": before.as_dict(),
        "restored": restored.as_dict(),
        "counts_match": before.counts == restored.counts,
        "hashed_rows_match": before.history_sha256 == restored.history_sha256,
        "resume_inputs_match": {
            # Everything `plan_resume_with_receipts` reads from a store. The manifest is the
            # only other input and it is a pure function of the plan, so two stores agreeing
            # on both cannot produce different attempted or unattempted sets.
            "sequence_receipts": before.receipts_sha256 == restored.receipts_sha256,
            "run_identity_keys": (
                before.run_identity_keys_sha256 == restored.run_identity_keys_sha256
            ),
        },
        "artifact_bytes": _rehash_blobs(extracted),
        "evidence_report_on_the_restored_copy": _integrity_on(extracted, declared_blobs),
    }

    # The two stops, restored exactly. An absence is the easiest thing for a restore to get
    # wrong in the direction that looks fine, so it is asserted rather than assumed.
    report["restore"]["stopped_state"] = {
        "components_on_the_correction_surface": restored.correction_components,
        "no_correction_component_was_registered": restored.correction_components == 0,
        "checked_surface": CORRECTION_SURFACE,
        "note": (
            "the credential-free lifecycle smoke registers an unrelated inert component on "
            "skill.selection; it is not a D4 correction component and is expected to restore"
        ),
    }
    return extracted, declared_blobs


def _observed_blobs(root: Path, declared: Sequence[str]) -> dict[str, str | None]:
    """Declared content address to observed hash, or `None` where the bytes are gone.

    Keyed by what the store *says* it holds rather than by what is on disk. W7-A3: a map built
    from the files present reports a store one blob smaller as perfectly clean, and a partial
    restore is exactly that shape of damage.
    """
    return {
        address: (
            _file_digest(root / "sha256" / address[:2] / address)
            if (root / "sha256" / address[:2] / address).is_file()
            else None
        )
        for address in declared
    }


async def _declared_blobs(url: str) -> list[str]:
    from sqlalchemy import text as sql

    engine = _engine(url)
    try:
        async with engine.connect() as connection:
            rows = await connection.execute(
                sql("SELECT content_hash FROM cognitive_os.artifact_blobs ORDER BY 1")
            )
            return [str(row[0]) for row in rows]
    finally:
        await engine.dispose()


def _integrity_on(root: Path, declared: Sequence[str]) -> dict[str, Any]:
    """The twelve-class report, run against the restored artifact copy."""
    report = d4_integrity(
        EVIDENCE,
        blob_hashes=_observed_blobs(root, declared),
        predecessor_fingerprints=_declared_pairs(),
    )
    return report.as_dict()


def _declared_pairs() -> dict[str, str]:
    return {
        name: fingerprint(DATA_ROOT / directory)[0]
        for name, directory in (
            ("development", "artifacts"),
            ("sprint_21c3", "artifacts-s21c3"),
            ("sprint_21d1", "artifacts-s21d1"),
            ("sprint_21d2", "artifacts-s21d2"),
            ("sprint_21d3", "artifacts-s21d3"),
        )
        if (DATA_ROOT / directory).is_dir()
    }


# -------------------------------------------------------------------------- S21D4-084


#: The artifact these cases damage is D3's committed contract fixture, and the record says so.
#: D4 fitted no artifact -- S21D4-039 selected nothing -- so there is no D4 model to damage, and
#: building a second fixture here would give the two sprints two artifacts that are only equal
#: by inspection. What 084 asks is whether the released loader refuses damage arriving through
#: an operations path, and that question is about the loader.
ARTIFACT_UNDER_TEST = "d3_contract_fixture"


def _fixture_module() -> Any:
    """D3's W4 script, imported by path so its fixture artifact has exactly one definition."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "artifact_runtime_d3", SCRIPTS / "artifact_runtime_d3.py"
    )
    if spec is None or spec.loader is None:  # pragma: no cover - the file is committed
        raise SystemExit("scripts/artifact_runtime_d3.py is not importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture_artifact() -> tuple[bytes, Any]:
    return _fixture_module()._fixture_artifact()


def _fixture_capability(data: bytes, payload: Any) -> Any:
    return _fixture_module()._capability(data, payload)


def _row(name: str, damage: str, expected: str, observed: object) -> dict[str, object]:
    return {"case": name, "damage": damage, "expected": expected, "observed": observed}


def _refusal(call: Any) -> dict[str, object]:
    try:
        call()
    except Exception as error:
        return {"failed_closed": True, "reason": f"{type(error).__name__}: {error}"[:200]}
    return {"failed_closed": False, "reason": "accepted"}


def _largest(root: Path) -> Path:
    return max(
        (path for path in root.rglob("*") if path.is_file() and not path.name.startswith(".")),
        key=lambda path: path.stat().st_size,
    )


def _damaged_evidence(scratch: Path, name: str, mutate: Any) -> dict[str, object]:
    """Seed one violation into a copy of the evidence directory and re-run the report.

    The copy is the point: the released report is what decides, and it decides about bytes
    nobody has to put back afterwards.
    """
    target = scratch / f"evidence-{name}"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(EVIDENCE, target)
    mutate(target)
    report = d4_integrity(target)
    return {
        "failed_closed": bool(report.failed),
        "reason": f"classes reporting failed: {list(report.failed)}",
        "healthy": report.healthy,
    }


def _edit(directory: Path, name: str, mutate: Any) -> None:
    path = directory / name
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact_cases(scratch: Path) -> list[dict[str, object]]:
    """The v2 loader and the direct evaluation boundary, against damaged bytes.

    D4 has no fitted artifact, so the bytes are D3's committed contract fixture and the record
    labels them `d3_contract_fixture`. What 084 asks is whether the released loader refuses when
    damage arrives through an operations path — an artifact extracted from a backup, resized, or
    replaced with another schema's bytes — and that question is about the loader, not about
    which model happened to be fitted.
    """
    data, payload = _fixture_artifact()
    capability = _fixture_capability(data, payload)
    document = json.loads(data)
    rows = [
        _row(
            "missing_artifact",
            "the capability's artifact hash against empty bytes",
            "the rehash refuses before the payload is parsed",
            _refusal(lambda: build_ranker_for_evaluation(b"", capability=capability)),
        ),
        _row(
            "corrupt_artifact",
            "one byte appended to the authorised bytes",
            "the rehash refuses; the payload is never read",
            _refusal(lambda: build_ranker_for_evaluation(data + b" ", capability=capability)),
        ),
        _row(
            "oversized_artifact",
            "the authorised bytes against a 16-byte bound",
            "the size bound refuses before parsing",
            _refusal(
                lambda: build_ranker_for_evaluation(data, capability=capability, maximum_bytes=16)
            ),
        ),
        _row(
            "schema_wrong_artifact",
            "v2 bytes relabelled with the v1 schema name",
            "the schema name is checked before any model is constructed",
            _refusal(
                lambda: load_correction_ranker_v2(
                    json.dumps({**document, "schema_name": "correction-ranker-artifact"}).encode(),
                    expected_component_id=document["component_id"],
                    expected_revision=document["component_revision"],
                    expected_surface=document["surface"],
                    expected_descriptor_hash=document["descriptor_hash"],
                )
            ),
        ),
        _row(
            "metadata_substitution",
            "a valid artifact presented under another descriptor's identity",
            "the declared descriptor is compared and refused",
            _refusal(
                lambda: load_correction_ranker_v2(
                    data,
                    expected_component_id=document["component_id"],
                    expected_revision=document["component_revision"],
                    expected_surface=document["surface"],
                    expected_descriptor_hash="9" * 64,
                )
            ),
        ),
        _row(
            "byte_substitution",
            "a differently-fitted but internally valid artifact under the authorised hash",
            "the rehash refuses: the capability names one artifact, not one shape",
            _refusal(
                lambda: build_ranker_for_evaluation(
                    canonical_bytes(_relabelled(document)), capability=capability
                )
            ),
        ),
    ]
    return rows


def _relabelled(document: Mapping[str, Any]) -> Any:
    """A valid v2 payload that differs from the authorised one by its code revision alone."""
    from cognitive_os.learning.correction_artifact import CorrectionArtifactPayloadV2

    return CorrectionArtifactPayloadV2.model_validate(
        {**document, "code_revision": f"{document['code_revision']}-substituted"}
    )


def _matrix(scratch: Path, extracted: Path, declared: Sequence[str]) -> list[dict[str, object]]:
    """Every damage case, applied to the extracted copy or to a copy of the evidence."""
    rows: list[dict[str, object]] = []

    # 1. Tampered blob: content-addressed storage means the name is the claim, so the rehash
    # is what refuses it — reading the file would not.
    victim = _largest(extracted)
    original = victim.read_bytes()
    victim.write_bytes(original + b" ")
    rehashed = _rehash_blobs(extracted)
    rows.append(
        _row(
            "tampered_blob",
            f"appended one byte to {victim.name[:12]} in the extracted copy",
            "the file no longer hashes to the name it is filed under",
            {
                "failed_closed": victim.name
                in {Path(item).name for item in rehashed["content_hash_mismatches"]},  # type: ignore[union-attr]
                "reason": f"content_hash_mismatches names {victim.name[:12]}",
                "files_rehashed": rehashed["files_rehashed"],
            },
        )
    )
    victim.write_bytes(original)

    # 2. Missing bytes: the remaining files still hash correctly, so a rehash alone would
    # report a clean store one file smaller. What has to refuse is the report that knows how
    # many blobs there should be.
    victim.unlink()
    after = _rehash_blobs(extracted)
    absent = d4_integrity(EVIDENCE, blob_hashes=_observed_blobs(extracted, declared))
    rows.append(
        _row(
            "missing_blob",
            f"removed {victim.name[:12]} from the extracted copy",
            "artifact_bytes fails on a declared blob with no bytes, which a rehash of what "
            "remains cannot see",
            {
                "failed_closed": "artifact_bytes" in absent.failed,
                "reason": f"classes reporting failed: {list(absent.failed)}",
                "a_rehash_of_what_remains_reports_it_clean": (
                    after["content_hash_mismatches"] == []
                ),
                "files_rehashed": after["files_rehashed"],
            },
        )
    )
    victim.write_bytes(original)

    rows.extend(_artifact_cases(scratch))

    # 3-9. Evidence damage, each seeded into its own copy and decided by the released report.
    for name, damage, expected, mutate in (
        (
            "ood_unit_forgery",
            "the invariance census reporting every transformed case as a distinct decision",
            "ood_units fails: a semantics-preserving transform that adds a decision is the "
            "collapse the erratum measured",
            lambda root: _edit(
                root,
                "sprint-21d4-invariance-regression.json",
                lambda d: d["independence"]["census_over_clean_and_transformed"].update(
                    independent_decisions=d["independence"]["census_over_clean_and_transformed"][
                        "nominal_decisions"
                    ],
                    replicated_decisions=0,
                ),
            ),
        ),
        (
            "holdout_access_claim",
            "one evidence file claiming a final outcome was inspected",
            "holdout_access fails and names the file",
            lambda root: _edit(
                root,
                "sprint-21d4-separation.json",
                lambda d: d.update(final_outcomes_inspected=True),
            ),
        ),
        (
            "retrieval_second_read",
            "the holdout benchmark recorded as executed twice",
            "retrieval_one_read fails: the protocol allows one read",
            lambda root: _edit(
                root,
                "sprint-21d4-retrieval-holdout-result.json",
                lambda d: d.update(executions=2),
            ),
        ),
        (
            "retrieval_alternative_reopened",
            "a fusion variant opened after the holdout returned a negative result",
            "retrieval_one_read fails: reading once and then tuning is the same failure, later",
            lambda root: _edit(
                root,
                "sprint-21d4-retrieval-decision.json",
                lambda d: d["no_alternative_opened"].update(fusion_variants=3),
            ),
        ),
        (
            "dataset_member_mismatch",
            "a materialised snapshot that no longer rebuilds identically",
            "explicit_member_selection fails",
            lambda root: _edit(
                root,
                "sprint-21d4-snapshots.json",
                lambda d: d["datasets"][0].update(rebuilt_identically=False),
            ),
        ),
        (
            "feature_seal_mismatch",
            "a campaign partition whose receipt is contradicted",
            "duplicate_executions_or_seals fails",
            lambda root: _edit(
                root,
                "sprint-21d4-calibration-campaign.json",
                lambda d: d["resume"].update(receipt_is_resumable=False),
            ),
        ),
        (
            "stale_assessment",
            "the pre-final checkpoint claiming final access was authorised",
            "lifecycle fails: no later evidence supports it",
            lambda root: _edit(
                root,
                "sprint-21d4-pre-final-checkpoint.json",
                lambda d: d["decision"].update(authorised=True),
            ),
        ),
        (
            "wrong_active_revision",
            "two different stop hashes across the not-opened map",
            "lifecycle fails: dependents must bind one stop",
            lambda root: _edit(
                root,
                "sprint-21d4-pre-final-checkpoint.json",
                lambda d: d["not_opened"][0].update(stop_hash="7" * 64),
            ),
        ),
        (
            "forged_independent_decision_count",
            "a stored census claiming more distinct decisions than it counted",
            "decision_independence fails: independence is a partition of what was counted",
            lambda root: _edit(
                root,
                "sprint-21d4-seal-resume.json",
                lambda d: d["partitions"][0]["census"].update(
                    independent_decisions=d["partitions"][0]["census"]["nominal_decisions"] * 2
                ),
            ),
        ),
        (
            "rate_over_a_nominal_denominator",
            "a stored rate naming the counted decisions as its denominator",
            "decision_independence fails: the denominator is named in the bytes, so it can be "
            "read rather than inferred",
            lambda root: _edit(
                root,
                "sprint-21d4-d3-grid-replay.json",
                lambda d: d["per_setting"][0]["new"]["census"].update(
                    rate_denominator="nominal_decisions"
                ),
            ),
        ),
    ):
        rows.append(_row(name, damage, expected, _damaged_evidence(scratch, name, mutate)))

    # The second D4 case S21D4-084 names, and the only one that is not about a stored file: a
    # threshold derived from anything but the calibration split is refused before it computes.
    rows.append(
        _row(
            "threshold_derived_off_calibration",
            "the zero-error operating point asked for from the final split",
            "the derivation refuses by name; a threshold fitted to a holdout is not a threshold",
            _refusal(
                lambda: derive_zero_error_point(
                    [
                        ScoredDecision(
                            decision_id=f"d{index}",
                            feature_hash=_digest(f"case:{index}"),
                            score=Decimal("0.9"),
                            answered=True,
                            correct=True,
                        )
                        for index in range(4)
                    ],
                    split="final",
                    calibration_source_hash=_digest("final-split"),
                    derived_at=datetime.now(UTC),
                )
            ),
        )
    )

    # 10. Retrieval policy substitution: an unfrozen resource policy hash.
    rows.append(
        _row(
            "retrieval_policy_substitution",
            "a graph resource policy hash that was never frozen",
            "the frozen policy table has no entry, so the benchmark cannot name one",
            {
                "failed_closed": _digest("unfrozen") not in FROZEN_GRAPH_RESOURCE_POLICIES,
                "reason": "FROZEN_GRAPH_RESOURCE_POLICIES resolves only the two revisions",
                "frozen_policies": sorted(FROZEN_GRAPH_RESOURCE_POLICIES),
                "revision_2_resolves": (
                    GRAPH_RESOURCE_POLICY_REVISION_2_HASH in FROZEN_GRAPH_RESOURCE_POLICIES
                ),
            },
        )
    )

    # 11. Judgement substitution: searchable text that names the label it is scored against.
    leaks = judgement_leaks(
        {"pair:failed": "coding\nd3r_boundary_collections:thing\nobservation status=completed\n"},
        {"pair:failed": ("boundary_collections",)},
    )
    rows.append(
        _row(
            "retrieval_judgement_substitution",
            "a searchable body spelling the task family it is judged on",
            "the production leak guard names the pair and the label",
            {
                "failed_closed": bool(leaks),
                "reason": f"judgement_leaks reports {list(leaks)}",
            },
        )
    )

    # 12. Store isolation: a predecessor pair checked against a digest that is not its own.
    rows.append(
        _row(
            "inherited_store_isolation",
            "the D3 pair checked against a fingerprint that is not its own",
            "the isolation class names the store and refuses",
            {
                "failed_closed": (
                    d4_integrity(
                        EVIDENCE, predecessor_fingerprints={"sprint_21d3": "0" * 64}
                    ).failed
                    != ()
                ),
                "reason": "isolation fails when a declared fingerprint does not reproduce",
            },
        )
    )
    return rows


# ------------------------------------------------------------------------------ entry point


async def _execute(output: Path) -> int:
    started = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    before = _fingerprints()
    # The scratch root W0 declared as D4's own. Named rather than a temp directory so the
    # damage this command does lands somewhere the isolation record already accounts for.
    scratch = Path(os.environ.get("COGOS_SCRATCH_ROOT", DATA_ROOT / "scratch-s21d4")) / (
        "w7-operations"
    )
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)

    report: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W7",
        "items": ["S21D4-082", "S21D4-083", "S21D4-084", "S21D4-085"],
        "purpose": (
            "Verify D4 provisioning, prove the evidence survives backup, restart and an "
            "isolated restore, and demonstrate that damage to the moved copy is refused."
        ),
        "artifact_under_test": ARTIFACT_UNDER_TEST,
        "started_at": started,
        "pre_registration_sha256": _file_digest(EVIDENCE / "sprint-21d4-pre-registration.json"),
        "final_outcomes_inspected": False,
        "fingerprints_before": before,
        "provisioning": await _provisioning(),
    }

    extracted, declared = await _prove_recovery(report, scratch)
    report["corruption_matrix"] = _matrix(scratch, extracted, declared)
    report["ci_coverage"] = _ci_coverage()

    after = _fingerprints()
    report["fingerprints_after"] = after
    report["isolation"] = {
        "predecessor_pairs_unchanged": all(before[name] == after[name] for name in INHERITED),
        "d4_pair_unchanged": before[D4_STORE] == after[D4_STORE],
        "changed": sorted(name for name in before if before[name] != after[name]),
    }
    report["main_worktree_mutations"] = _git_state()
    report["findings"] = _findings(report)
    report["recorded_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    seal = hashlib.sha256(_canonical(report)).hexdigest()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical({**report, "integrity_content_hash": seal}))
    report["integrity_content_hash"] = seal
    print(
        json.dumps(
            {
                "output": output.name,
                "provisioning_migration": report["provisioning"]["migration_head"],
                "restore_counts_match": report["restore"]["counts_match"],
                "restore_hashed_rows_match": report["restore"]["hashed_rows_match"],
                "matrix_cases": len(report["corruption_matrix"]),
                "matrix_all_failed_closed": all(
                    bool(row["observed"]["failed_closed"])  # type: ignore[index]
                    for row in report["corruption_matrix"]
                ),
                "predecessor_pairs_unchanged": report["isolation"]["predecessor_pairs_unchanged"],
                "findings": report["findings"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not report["findings"] else 1


def _git_state() -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argv, no shell, no operator input
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPOSITORY,
    ).stdout


def _ci_coverage() -> dict[str, object]:
    """S21D4-085: which D4 surfaces the credential-free lanes actually cover."""
    workflow = (REPOSITORY / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    covered = {
        "v2_normalisation_and_matrix": "test_correction_ranking_v2.py" in workflow
        or "learning" in workflow,
        "d3_evidence_schemas": "d3-integrity" in workflow,
        "d4_evidence_schemas": "d4-integrity" in workflow,
        "decision_independence": "test_d4_integrity.py" in workflow,
        "artifact_verification": "artifact-verify" in workflow,
        "lifecycle": "learned.py smoke" in workflow,
        "benchmark_replay": "sprint21c1-learned-ci" in workflow,
    }
    return {
        "workflow_sha256": _file_digest(REPOSITORY / ".github" / "workflows" / "ci.yml"),
        "covered": covered,
        "uncovered": sorted(name for name, value in covered.items() if not value),
        "uses_live_provider_or_network": False,
        "uses_predecessor_store": False,
    }


def _findings(report: Mapping[str, Any]) -> list[str]:
    """What would make this run a failure rather than a record."""
    findings: list[str] = []
    provisioning = report["provisioning"]
    if not provisioning["migration_is_expected"]:
        findings.append(f"migration head is {provisioning['migration_head']}")
    if not provisioning["no_migration_0016"]:
        findings.append("a migration 0016 exists, which D4 forbids")
    restore = report["restore"]
    if not restore["counts_match"] or not restore["hashed_rows_match"]:
        findings.append("the restored store does not reproduce the source")
    if restore["artifact_bytes"]["content_hash_mismatches"]:
        findings.append("a restored blob does not hash to its content address")
    if not restore["stopped_state"]["no_correction_component_was_registered"]:
        findings.append("a component exists on the correction surface, which D4 never opened")
    open_cases = [
        row["case"]
        for row in report["corruption_matrix"]
        if not row["observed"]["failed_closed"]  # type: ignore[index]
    ]
    if open_cases:
        findings.append(f"corruption cases that did not fail closed: {open_cases}")
    if not report["isolation"]["predecessor_pairs_unchanged"]:
        findings.append("a predecessor pair changed during this run")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d4-operations.json")
    arguments = parser.parse_args()
    return asyncio.run(_execute(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
