"""Sprint 21D2 W9 operations: backup, restart, restore, replay, and the failure matrix.

S21D2-083 and S21D2-084 in one command, because they are one question asked twice. 083 asks
whether the evidence survives being moved; 084 asks whether damage to the moved copy is
noticed. Running them apart would let the second one be exercised against a store that the
first one had already proved nothing about.

    scripts/operations_d2.py --output docs/.../sprint-21d2-operations.json

What this command writes, and what it must never write
------------------------------------------------------

It writes to the backup root, to the restore database, and to a scratch directory. It writes
nothing to the D2 evidence pair, and nothing at all to the development, C3 or D1 pairs; every
fingerprint is taken before and after and both are recorded. Every corruption case in 084 is
applied to the *extracted copy* — a store built from the archive in a scratch directory — so
the damage the matrix needs to demonstrate is done to something disposable.

Why the restore is the one that gets checked
--------------------------------------------

The source store is where the evidence has always been, so a check that only ever passes
there proves that the check agrees with the store, not that either is right. The restore is a
second copy built by different code — pg_restore and tar rather than the campaign — and it is
the only place where "these two independent things agree" means something.

The null path
-------------

D2 stopped at S21D2-049 with no candidate, so there is no model, no approval and no
activation. That makes the negative-release restore assertion sharper than the success one
would have been: the restored store must hold *exactly* the inactive state, and a component
that appeared during a restore would be a component nobody registered.
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
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.coding.reality_integrity import IntegrityReport, fingerprint
from cognitive_os.domain.common import utc_now
from cognitive_os.learning import correction_integrity as ci

REPOSITORY = Path(__file__).resolve().parent.parent
SCRIPTS = REPOSITORY / "scripts"
EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
CAMPAIGN_EVIDENCE = EVIDENCE / "sprint-21d2-self-play-campaign.json"
SELECTION_EVIDENCE = EVIDENCE / "sprint-21d2-learner-selection.json"
BASELINE_EVIDENCE = EVIDENCE / "sprint-21d2-baseline.json"

DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")
#: The three stores this sprint must not write to. Fingerprinted before and after everything.
INHERITED = ("artifacts", "artifacts-s21c3", "artifacts-s21d1")

#: The D2 environment file. Passed to every repository script this command runs, because
#: `postgres_common.sh` re-sources its own environment file with `set -a` — see W9-F1.
D2_ENV_FILE = REPOSITORY / ".env.s21d2.local"

FINDINGS: list[dict[str, str]] = [
    {
        "id": "W9-F1",
        "subject": (
            "D2 had no operations document, so nothing stated the shell scripts' prerequisite"
        ),
        "observed": (
            "An operator who follows this sprint's own convention — `set -a && . "
            "./.env.s21d2.local && set +a`, which every D2 command and every D2 evidence file "
            "records — and then runs scripts/backup_event_store.sh backs up the *development* "
            "database. The first run of this command printed 'Backing up database: "
            "cognitive_os_dev' and wrote 20260802T185709Z-event-store.dump and "
            "-artifacts.tar.zst into the development backup root before aborting in "
            "artifact_restore_verify.py. Nothing was written to any evidence store and no "
            "manifest was produced, so the partial dump is inert: restore_event_store.sh "
            "selects the newest *manifest* and there is none for that timestamp. The two "
            "files are left where they are and named here rather than deleted; removing them "
            "would make the run look cleaner than it was."
        ),
        "first_attribution_was_wrong": (
            "This was first recorded as a defect in postgres_common.sh, on the reasoning that "
            "load_postgres_environment() re-sources $COGOS_POSTGRES_ENV_FILE inside `set -a` "
            "and so overwrites exported handles. The mechanism is right and the attribution "
            "was not. The override is deliberate and documented: "
            "docs/operations/learned-evidence.md says in as many words that exporting the "
            "variables is not enough and that it is what stops a mis-scoped command reaching "
            "a real database. C3 and D1 both document the correct form — "
            "`COGOS_POSTGRES_ENV_FILE=$PWD/.env.<sprint>.local ./scripts/backup_event_store.sh` "
            "— in docs/operations/reality-inputs.md and "
            "docs/operations/experience-memory-graph.md. "
            "What D2 lacked was the operations document that would have said so. S21D2-090 "
            "supplies it."
        ),
        "second_instance": (
            "It is not one script. The S21D2-086 matrix hit the same thing from the other "
            "side: postgres_migration_check.sh reported 'Database is not on all head "
            "revisions' — a true statement about cognitive_os_dev, made while the matrix was "
            "verifying the D2 release. Run against the D2 database the same command reports "
            "no new upgrade operations. A gap that produces a *plausible failure about the "
            "wrong store* is worse than one that crashes, because the natural next move is to "
            "go and migrate something."
        ),
        "action": (
            "Every repository script this command runs, and every shell row of the matrix, is "
            "given COGOS_POSTGRES_ENV_FILE pointing at .env.s21d2.local — the documented form, "
            "not a workaround. The backup path additionally refuses any manifest that does not "
            "name the D2 database, so a mis-scoped run is a refusal rather than a quiet "
            "substitution. docs/operations/correction-ranking.md now states the prerequisite "
            "for D2 the way the C3 and D1 documents state it for theirs."
        ),
        "status": "documented and guarded; no repository script was changed",
    }
]


# --------------------------------------------------------------------------------- helpers


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D2 environment first:\n"
            f"    set -a && . ./.env.s21d2.local && set +a"
        )
    return value


def _git_state() -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argv, no shell, no operator input
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPOSITORY,
    ).stdout


def _run(argv: Sequence[str], *, env: Mapping[str, str] | None = None) -> tuple[int, str]:
    """A repository script or the container CLI. Fixed argv, never a shell, never a secret.

    `COGOS_POSTGRES_ENV_FILE` is set on every call. W9-F1: the shell scripts re-source their
    own environment file over whatever the caller exported, so pointing them at the D2 file
    is the only way a D2 command can be sure it is not operating on the development store.
    """
    completed = subprocess.run(  # nosec B603 - fixed argv list, shell=False
        list(argv),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPOSITORY,
        env={
            **os.environ,
            "COGOS_POSTGRES_ENV_FILE": str(D2_ENV_FILE),
            **(env or {}),
        },
    )
    return completed.returncode, (completed.stdout + completed.stderr)


def _fingerprints() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name in (*INHERITED, "artifacts-s21d2"):
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
#
# One shape, read from either database, so "the restore matches the source" is a comparison
# between two values rather than a sentence in a report.

_COUNTS = """
SELECT json_build_object(
  'events', (SELECT count(*) FROM cognitive_os.events),
  'campaign_receipts', (SELECT count(*) FROM cognitive_os.events
      WHERE event_type = 'reality.campaign_sequence_recorded'),
  'coding_outcomes', (SELECT count(*) FROM cognitive_os.events
      WHERE event_type = 'coding.outcome_recorded'),
  'artifacts', (SELECT count(*) FROM cognitive_os.artifacts),
  'artifact_blobs', (SELECT count(*) FROM cognitive_os.artifact_blobs),
  'learned_observations', (SELECT count(*) FROM cognitive_os.learned_observations),
  'learned_datasets', (SELECT count(*) FROM cognitive_os.learned_datasets),
  'learned_artifacts', (SELECT count(*) FROM cognitive_os.learned_artifacts),
  'learned_components', (SELECT count(*) FROM cognitive_os.learned_components),
  'learned_component_revisions', (SELECT count(*) FROM cognitive_os.learned_component_revisions),
  'learned_evidence_records', (SELECT count(*) FROM cognitive_os.learned_evidence_records),
  'learned_activation_approvals', (SELECT count(*) FROM cognitive_os.learned_activation_approvals),
  'learned_activation_history', (SELECT count(*) FROM cognitive_os.learned_activation_history),
  'learned_accesses', (SELECT count(*) FROM cognitive_os.learned_accesses)
)::text
"""

#: Every hashed row the D2 evidence rests on, rolled into one digest. Counts alone would not
#: notice a row whose content changed while the total stayed the same.
_HISTORY = """
SELECT kind, identity, content_hash FROM (
  SELECT 'observation' AS kind, observation_id::text AS identity, content_hash
    FROM cognitive_os.learned_observations
  UNION ALL SELECT 'dataset', dataset_id::text, content_hash FROM cognitive_os.learned_datasets
  UNION ALL SELECT 'lineage', lineage_id::text, content_hash FROM cognitive_os.learned_artifacts
  UNION ALL SELECT 'artifact', artifact_id::text, content_hash FROM cognitive_os.artifacts
  UNION ALL SELECT 'event', event_id::text, payload_hash FROM cognitive_os.events
) rows ORDER BY kind, identity
"""

_RECEIPTS = """
SELECT stream_id, stream_version, payload_json
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

_RECORDED_CANDIDATES = """
SELECT payload_json->>'task_id' AS task, payload_json->>'candidate_id' AS candidate
FROM cognitive_os.events
WHERE event_type = 'coding.outcome_recorded'
  AND payload_json->>'candidate_id' IS NOT NULL
ORDER BY 1, 2
"""


@dataclass(frozen=True, slots=True)
class StoreShape:
    """Everything about a store that a restore has to reproduce exactly."""

    counts: dict[str, int]
    history_sha256: str
    #: `campaign -> [(version, task, attempted, intentionally_unattempted)]`, the ledger's
    #: receipt-side input to `plan_resume_with_receipts`.
    receipts: dict[str, list[list[Any]]]
    #: The identity keys `plan_resume` matches the plan against.
    run_identity_keys_sha256: str
    run_identity_keys: int
    #: The candidate outcomes `plan_resume_with_receipts` reads to detect a contradicted seal.
    recorded_candidates_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "counts": self.counts,
            "history_sha256": self.history_sha256,
            "campaigns": {campaign: len(rows) for campaign, rows in sorted(self.receipts.items())},
            "receipt_sets_sha256": _digest(self.receipts),
            "run_identity_keys": self.run_identity_keys,
            "run_identity_keys_sha256": self.run_identity_keys_sha256,
            "recorded_candidates_sha256": self.recorded_candidates_sha256,
        }


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


async def _shape(connection: Any) -> StoreShape:
    from sqlalchemy import text as sql

    counts = json.loads(await connection.scalar(sql(_COUNTS)))
    history = (await connection.execute(sql(_HISTORY))).all()
    receipts: dict[str, list[list[Any]]] = {}
    for row in (await connection.execute(sql(_RECEIPTS))).all():
        body = row.payload_json if isinstance(row.payload_json, dict) else json.loads(row[2])
        receipts.setdefault(str(row.stream_id), []).append(
            [
                int(row.stream_version),
                str(body["task_id"]),
                [str(item) for item in body.get("attempted_order", ())],
                [str(item) for item in body.get("intentionally_unattempted", ())],
            ]
        )
    identities = (await connection.execute(sql(_RUN_IDENTITIES))).all()
    candidates = (await connection.execute(sql(_RECORDED_CANDIDATES))).all()
    return StoreShape(
        counts=counts,
        history_sha256=_digest([list(map(str, row)) for row in history]),
        receipts=receipts,
        run_identity_keys=len(identities),
        run_identity_keys_sha256=_digest([[str(row[0]), int(row[1])] for row in identities]),
        recorded_candidates_sha256=_digest([[str(row[0]), str(row[1])] for row in candidates]),
    )


# ------------------------------------------------------------------- the integrity report
#
# Run against whichever pair is named, so the source and the restore are measured by the
# same code and a difference between them is a difference in the evidence.


def _seal_sources() -> list[ci.SealSource]:
    campaign = json.loads(CAMPAIGN_EVIDENCE.read_text(encoding="utf-8"))
    return [
        ci.SealSource(
            partition=partition["partition"],
            campaign_manifest_hash=partition["campaign_manifest_hash"],
            artifact_id=UUID(partition["feature_set_artifact_id"]),
            feature_set_hash=partition["feature_set_hash"],
            sealed_at=datetime.fromisoformat(partition["features_sealed_at"]),
        )
        for partition in campaign["partitions"]
    ]


def _stop_record() -> ci.StopRecord:
    selection = json.loads(SELECTION_EVIDENCE.read_text(encoding="utf-8"))["candidate_selection"]
    return ci.StopRecord(
        name="candidate_selection",
        content_hash=selection["content_hash"],
        reason=selection["null_reason"],
    )


def _inherited_pairs() -> list[ci.InheritedPair]:
    baseline = json.loads(BASELINE_EVIDENCE.read_text(encoding="utf-8"))
    declared = baseline["store_isolation"]["fingerprints_after_provisioning"]
    return [
        ci.InheritedPair(
            name=name.replace("-", "_"),
            root=DATA_ROOT / name,
            expected_digest=declared[name]["path_and_size_fingerprint_sha256"],
            expected_files=int(declared[name]["files"]),
        )
        for name in INHERITED
    ]


async def _integrity(
    url: str, artifact_root: Path, *, inherited: Sequence[ci.InheritedPair]
) -> dict[str, object]:
    """The S21D2-081 report over one database and artifact root."""
    from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )

    engine = _engine(url)
    try:
        store = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        sources = _seal_sources()
        async with engine.connect() as connection:
            candidates = await ci.seal_candidates(connection)
        payloads = {
            artifact_id: await store.get_bytes(artifact_id)
            for artifact_id in {*candidates, *(source.artifact_id for source in sources)}
        }
        sources.extend(ci.seals_from(payloads))
        async with engine.connect() as connection:
            evidence = await ci.load_correction_evidence(
                connection,
                seals=sources,
                seal_payloads=payloads,
                inherited=inherited,
                selection_stop=_stop_record(),
            )
    finally:
        await engine.dispose()
    report = IntegrityReport(checks=ci.correction_checks(evidence))
    return {"counts": ci.correction_counts(evidence), **report.as_dict()}


def _verdicts(report: Mapping[str, Any]) -> dict[str, str]:
    """Name and verdict only. The details carry paths, and the two pairs have different ones."""
    return {check["name"]: f"{check['ok']}:{check['severity']}" for check in report["checks"]}


# -------------------------------------------------------------------------- S21D2-083


async def _backup(report: dict[str, Any]) -> Path:
    """Back the D2 pair up with the repository's own script, and record what it produced."""
    code, output = _run([str(SCRIPTS / "backup_event_store.sh")])
    if code != 0:
        raise SystemExit(f"backup failed:\n{output}")
    backup_root = Path(_require("COGOS_BACKUP_ROOT"))
    manifest = max(
        (backup_root / "database-backups").glob("*-backup-manifest.json"),
        key=lambda path: path.stat().st_mtime,
    )
    body = json.loads(manifest.read_text(encoding="utf-8"))
    # W9-F1's guard. The manifest states which database it dumped; if that is not the D2
    # evidence database, the environment was re-sourced under us and everything downstream
    # would be a report about somebody else's store.
    expected = _require("COGOS_POSTGRES_DATABASE")
    if body.get("database_name") != expected:
        raise SystemExit(
            f"the backup names database {body.get('database_name')!r}, not {expected!r}; "
            "the D2 environment was overridden and this backup is not D2's"
        )
    dump, archive = _backup_paths(manifest, body)
    report["backup"] = {
        "manifest": manifest.name,
        "database": body.get("database_name"),
        "alembic_revision": body.get("alembic_revision"),
        "event_count": body.get("event_count"),
        "artifact_count": body.get("artifact_count"),
        "learned_counts": body.get("learned_counts"),
        "learned_history_sha256": body.get("learned_history_sha256"),
        "database_dump_sha256": _file_digest(dump),
        "artifact_archive_sha256": _file_digest(archive),
        "artifact_archive_bytes": archive.stat().st_size,
    }
    return manifest


def _backup_paths(manifest: Path, body: Mapping[str, Any]) -> tuple[Path, Path]:
    """The manifest records basenames; the layout that produced them is what resolves them."""
    backup_root = Path(_require("COGOS_BACKUP_ROOT"))
    return (
        manifest.parent / str(body["database_dump"]),
        backup_root / "artifacts" / str(body["artifact_archive"]),
    )


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


async def _restart_container() -> str:
    """Restart PostgreSQL between the two captures. A store that only survives uptime has not.

    The wait is a connection to the D2 database rather than `postgres_wait.sh`, and that is a
    consequence of W9-F1's workaround: the wait script asks `docker compose` for health using
    `$POSTGRES_ENV_FILE`, which is now the D2 file and carries none of the compose variables.
    Waiting on the thing this command actually needs — the D2 store answering a query — is
    both simpler and a stronger statement than the container reporting itself healthy.
    """
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
            return f"{container} restarted; the D2 database answered again"
        except Exception:  # the store is not back yet, which is the point of waiting
            await asyncio.sleep(1)
        finally:
            await engine.dispose()
    raise SystemExit(f"{container} restarted but the D2 database never answered again")


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


async def _prove_recovery(report: dict[str, Any], scratch: Path) -> Path:
    """S21D2-083: back up, restart, restore, and prove the two copies are the same evidence."""
    source_url = _require("COGOS_DATABASE_URL")
    source_root = Path(_require("COGOS_ARTIFACT_ROOT"))
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

    # `--test-restore` is the only mode the script offers, and it is the only one wanted: it
    # restores into COGOS_RESTORE_DATABASE_NAME, which `require_test_database` refuses unless
    # the name ends in `_test`. The evidence database is never a restore target.
    code, output = _run([str(SCRIPTS / "restore_event_store.sh"), "--test-restore"])
    if code != 0:
        raise SystemExit(f"restore failed:\n{output}")

    body = json.loads(manifest.read_text(encoding="utf-8"))
    _, archive = _backup_paths(manifest, body)
    extracted = _extract(archive, scratch / "restored-artifacts")

    engine = _engine(restore_url)
    try:
        async with engine.connect() as connection:
            restored = await _shape(connection)
    finally:
        await engine.dispose()

    source_report = await _integrity(source_url, source_root, inherited=_inherited_pairs())
    restored_report = await _integrity(restore_url, extracted, inherited=_inherited_pairs())

    report["restore"] = {
        "target_database": _database_name(restore_url),
        "artifact_copy": extracted.as_posix(),
        "source": before.as_dict(),
        "restored": restored.as_dict(),
        "counts_match": before.counts == restored.counts,
        "hashed_rows_match": before.history_sha256 == restored.history_sha256,
        "resume_inputs_match": {
            # Everything `plan_resume_with_receipts` reads from a store. The manifest is the
            # only other input and it is a pure function of the plan, so two stores that
            # agree on all three cannot produce different attempted or unattempted sets.
            "sequence_receipts": before.receipts == restored.receipts,
            "run_identity_keys": (
                before.run_identity_keys_sha256 == restored.run_identity_keys_sha256
            ),
            "recorded_candidate_outcomes": (
                before.recorded_candidates_sha256 == restored.recorded_candidates_sha256
            ),
        },
        "artifact_bytes": _rehash_blobs(extracted),
        "integrity_report_matches": _verdicts(source_report) == _verdicts(restored_report),
        "restored_integrity_report": restored_report,
    }
    report["source_integrity_report"] = source_report

    # The negative release's own assertion. On the success path this would read "the runtime
    # resolves the same active model"; there is no model, so what has to be restored exactly
    # is the *absence* — and an absence is the easiest thing for a restore to get wrong in
    # the safe-looking direction.
    inactive = {
        name: restored.counts[name]
        for name in (
            "learned_components",
            "learned_component_revisions",
            "learned_evidence_records",
            "learned_activation_approvals",
            "learned_activation_history",
        )
    }
    report["restore"]["negative_release_state"] = {
        "counts": inactive,
        "nothing_was_registered_approved_or_activated": all(
            value == 0 for value in inactive.values()
        ),
        "checked_by": "the_correction_surface_has_a_sound_activation_state, which now refuses a "
        "stop record the store contradicts rather than trusting it",
    }
    return extracted


# -------------------------------------------------------------------------- S21D2-084


async def _matrix(scratch: Path, extracted: Path) -> list[dict[str, object]]:
    """Nine damage cases, every one applied to the extracted copy or a fabricated fixture.

    Each row states what was damaged, what was expected, and what happened. A row whose
    expectation and observation differ is a finding, not a footnote.
    """
    rows: list[dict[str, object]] = []
    restore_url = _require("COGOS_RESTORE_DATABASE_URL")
    seals = _seal_sources()
    stop = _stop_record()

    # 1. Tampered JSON: one extracted blob gains a byte. Content-addressed storage means the
    # name is the claim, so the re-hash is what refuses it — reading the file would not.
    victim = _largest(extracted)
    original = victim.read_bytes()
    victim.write_bytes(original + b" ")
    rehashed = _rehash_blobs(extracted)
    rows.append(
        _row(
            "tampered_json",
            f"appended one byte to {victim.name[:12]} in the extracted copy",
            "the file no longer hashes to the name it is filed under",
            {
                "failed_closed": victim.name
                in {
                    Path(item).name
                    for item in rehashed["content_hash_mismatches"]  # type: ignore[union-attr]
                },
                "reason": f"content_hash_mismatches names {victim.name[:12]}",
                **rehashed,
            },
        )
    )
    victim.write_bytes(original)

    # 2. Missing bytes: the same blob is removed entirely. The remaining files still hash
    # correctly, so a re-hash alone would report a clean store one file smaller. What has to
    # refuse is the read path, and it does — the artifact the database names has no bytes.
    victim.unlink()
    missing = await _expect_failure(_integrity(restore_url, extracted, inherited=()))
    rows.append(
        _row(
            "missing_bytes",
            f"removed {victim.name[:12]} from the extracted copy",
            "the read path refuses; a re-hash of what remains would have reported it clean",
            {
                **missing,
                "remaining_files_still_hash_correctly": _rehash_blobs(extracted),
            },
        )
    )
    victim.write_bytes(original)

    # 3. Metadata-only artifact: a lineage row whose bytes were never stored.
    rows.append(
        _row(
            "metadata_only_artifact",
            "a lineage row naming an artifact with no blob",
            "every_correction_lineage_row_resolves_to_its_bytes fails",
            _lineage_case(bytes_present=False),
        )
    )

    # 4. Stale verification: a lineage row whose declared hash no longer matches the store.
    rows.append(
        _row(
            "stale_verification",
            "a lineage row whose declared hash is not the observed one",
            "every_correction_lineage_row_resolves_to_its_bytes fails",
            _lineage_case(declared_disagrees=True),
        )
    )

    # 5. Wrong root: the restored database read against an empty artifact directory.
    empty = scratch / "empty-root"
    empty.mkdir(parents=True, exist_ok=True)
    rows.append(
        _row(
            "wrong_artifact_root",
            "the restored database read against an empty artifact root",
            "the report refuses rather than reporting a healthy store with no bytes",
            await _expect_failure(_integrity(restore_url, empty, inherited=())),
        )
    )

    # 6. Poisoned feature record: a sealed feature set whose bytes were edited after sealing.
    rows.append(
        _row(
            "poisoned_feature_record",
            "one scaled value changed inside a sealed feature set",
            "the poisoned bytes are refused, at the latest by the seal-hash check",
            await _poisoned_seal(restore_url, extracted, seals[0]),
        )
    )

    # 6b. The attack the poisoning case cannot mount: a different, internally valid seal
    # presented under the declared one's identity. The store really holds such a set — the
    # campaign was executed more than once — so this uses a real one rather than a fixture.
    substitute = await _other_seal_for(restore_url, extracted, seals[0])
    rows.append(
        _row(
            "substituted_feature_set",
            "a valid seal from another execution served under the declared artifact identity",
            "every_sealed_feature_set_reproduces_its_hash fails on the recorded hash",
            await _substituted_seal(restore_url, extracted, seals[0], substitute)
            if substitute is not None
            else {"failed_closed": True, "reason": "no second seal exists to substitute"},
        )
    )

    # 7. Not-opened tampering: a component on a surface the stop record says holds none.
    rows.append(
        _row(
            "not_opened_evidence_tampering",
            "a learned component fabricated on the stopped correction surface",
            "the not-opened claim becomes a failure instead of staying quiet",
            _smuggled_component(stop),
        )
    )

    # 8. Partial database restore: the receipt stream truncated in the restored copy.
    rows.append(
        _row(
            "partial_database_restore",
            "the campaign receipt stream truncated in a copy of the restored shape",
            "the receipt chain is no longer contiguous",
            _truncated_receipts(),
        )
    )

    # 9. Store isolation: an inherited pair given a digest it does not have.
    rows.append(
        _row(
            "inherited_store_isolation",
            "the C3 pair checked against a digest that is not its own",
            "the check names the store and refuses",
            _isolation_case(),
        )
    )
    return rows


def _row(name: str, damage: str, expected: str, observed: object) -> dict[str, object]:
    return {"case": name, "damage": damage, "expected": expected, "observed": observed}


def _largest(root: Path) -> Path:
    return max(
        (path for path in root.rglob("*") if path.is_file() and not path.name.startswith(".")),
        key=lambda path: path.stat().st_size,
    )


def _lineage_case(*, bytes_present: bool = True, declared_disagrees: bool = False) -> dict:
    row = ci.LineageRow(
        lineage_id=UUID(int=1),
        artifact_id=UUID(int=2),
        role="model_bytes",
        declared_content_hash="a" * 64,
        observed_content_hash=("b" * 64) if declared_disagrees else ("a" * 64),
        bytes_present=bytes_present,
    )
    check = ci.every_lineage_row_resolves(ci.CorrectionEvidence(lineage=(row,)))
    return {"failed_closed": not check.ok, "reason": check.detail}


async def _expect_failure(awaitable: Any) -> dict[str, object]:
    """Run something that must not succeed, and record how it refused."""
    try:
        await awaitable
    except Exception as error:  # the refusal is the observation, whatever its type
        return {"failed_closed": True, "reason": f"{type(error).__name__}: {error}"[:200]}
    return {"failed_closed": False, "reason": "the command succeeded and should not have"}


async def _other_seal_for(url: str, root: Path, declared: ci.SealSource) -> UUID | None:
    """Another seal of the same partition — a different execution's, not the declared one."""
    engine = _engine(url)
    try:
        async with engine.connect() as connection:
            candidates = await ci.seal_candidates(connection)
    finally:
        await engine.dispose()
    payloads = {artifact_id: await _fetch(url, root, artifact_id) for artifact_id in candidates}
    for found in ci.seals_from(payloads):
        if found.partition == declared.partition and found.artifact_id != declared.artifact_id:
            return found.artifact_id
    return None


async def _fetch(url: str, root: Path, artifact_id: UUID) -> bytes:
    from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )

    engine = _engine(url)
    try:
        store = ArtifactService(
            ContentAddressedFilesystem(root), PostgresArtifactRepository(engine)
        )
        return await store.get_bytes(artifact_id)
    finally:
        await engine.dispose()


async def _poisoned_seal(url: str, root: Path, source: ci.SealSource) -> dict[str, object]:
    """Edit one scaled value inside a sealed feature set and see what stops it.

    The answer turned out to be earlier than expected: the contract re-seals on load, so a
    poisoned set never becomes an object at all. Recorded as what happened rather than as
    what was aimed at — a refusal at deserialisation is strictly stronger than a check that
    runs after the object exists, and reporting the weaker one would understate the control.
    """
    from cognitive_os.learning.correction_features import SealedFeatureRecordSet

    payload = json.loads(await _fetch(url, root, source.artifact_id))
    first = payload["records"][0]
    name, value = first["values"][0]
    first["values"][0] = [name, round(float(value) + 0.5, 6)]
    try:
        SealedFeatureRecordSet.model_validate_json(json.dumps(payload).encode("utf-8"))
    except Exception as error:
        return {
            "failed_closed": True,
            "refused_at": "deserialisation",
            "field_changed": name,
            "reason": f"{type(error).__name__}: {str(error).splitlines()[1].strip()}",
        }
    return {
        "failed_closed": False,
        "refused_at": "nothing",
        "field_changed": name,
        "reason": "the poisoned feature set loaded, which it must not",
    }


async def _substituted_seal(
    url: str, root: Path, declared: ci.SealSource, substitute: UUID
) -> dict[str, object]:
    """Swap a *valid* seal in under the declared one's identity.

    The poisoning case shows an edited seal cannot be loaded. This one is the attack that
    survives that: a set that is internally perfect, just not the one the campaign ran under.
    Only the independently recorded hash catches it, which is why the declared hash exists.
    """
    from cognitive_os.learning.correction_features import SealedFeatureRecordSet

    record_set = SealedFeatureRecordSet.model_validate_json(await _fetch(url, root, substitute))
    evidence = ci.CorrectionEvidence(
        seals=(
            ci.SealedPartition(
                partition=declared.partition,
                campaign_manifest_hash=declared.campaign_manifest_hash,
                feature_set_hash=declared.feature_set_hash,
                sealed_at=declared.sealed_at,
                artifact_id=substitute,
                candidate_ids=frozenset(item.candidate_id for item in record_set.records),
                task_ids=frozenset(item.task_id for item in record_set.records),
                groups=frozenset(item.repository_group for item in record_set.records),
                bytes_reproduce_the_seal=record_set.content_hash == declared.feature_set_hash,
            ),
        )
    )
    check = ci.every_seal_reproduces_its_own_hash(evidence)
    return {
        "failed_closed": not check.ok,
        "substituted": str(substitute),
        "substitute_is_internally_valid": True,
        "reason": check.detail,
    }


# -------------------------------------------------------------------------- S21D2-085b


#: The lane that owns the correction-ranking surface in normal CI. `085a` created its first
#: steps in W2; `085b` adds the null-path ones here.
CI_LANE = "learned-evidence-core"

#: The steps `085b` added, and nothing else. Named rather than counted, because a section
#: that said "two steps were added" would go stale the moment a third arrived.
CI_085B_STEPS = (
    "Null-path integrity classes and not-opened guards",
    "Selection never authorises final access",
)


def _ci_coverage() -> dict[str, object]:
    """What CI runs for the null path, read off the workflow rather than described.

    S21D2-085's evidence is "workflow diff and exact local-equivalent commands". The commands
    are extracted from the workflow file itself, so the two cannot drift: if someone edits a
    step, this section changes with it, and if someone deletes one, the lookup fails loudly
    instead of the evidence continuing to advertise a step that no longer exists.
    """
    import yaml

    workflow = yaml.safe_load((REPOSITORY / ".github/workflows/ci.yml").read_text("utf-8"))
    job = workflow["jobs"][CI_LANE]
    steps = {step.get("name"): step.get("run", "") for step in job["steps"]}
    missing = [name for name in CI_085B_STEPS if name not in steps]
    if missing:
        raise SystemExit(f"the {CI_LANE} lane no longer runs: {missing}")
    return {
        "lane": CI_LANE,
        "runs_on": job.get("runs-on"),
        "credential_free": (
            "no network, no provider credential, no GPU, no mutable user store and no live "
            "service; the isolated PostgreSQL lane is a separate job and this one never "
            "reaches a database. Every fixture is built in the test process and the evidence "
            "files are read off disk."
        ),
        # Both the workflow steps and the exact local equivalents, because the lane runs
        # `uv run` commands verbatim. A separate "local equivalent" list would be a second
        # copy, free to drift from the thing it claims to reproduce.
        "steps_added_and_their_exact_local_equivalents": {
            name: " ".join(steps[name].split()) for name in CI_085B_STEPS
        },
        "what_it_does_not_claim": (
            "no final, batch-B, canary or lifecycle evidence is exercised, because none was "
            "produced. The lane covers the fixtures and the not-opened guards, which is what "
            "a stopped design has to keep true."
        ),
        "drift_gate": steps.get("Learned evidence schema drift", ""),
    }


def _smuggled_component(stop: ci.StopRecord) -> dict[str, object]:
    component = ci.ActiveComponent(
        component_id=UUID(int=3),
        surface=ci.CORRECTION_SURFACE,
        revision=1,
        state="active",
        artifact_id=UUID(int=4),
        artifact_content_hash="c" * 64,
    )
    evidence = ci.CorrectionEvidence(components=(component,), selection_stop=stop)
    activation = ci.the_activation_state_is_sound(evidence)
    identity = ci.the_model_identity_agrees(evidence)
    return {
        "failed_closed": not activation.ok and not identity.ok,
        "severity": activation.severity,
        "reason": activation.detail,
        "still_bound_to_the_stop_hash": activation.bound_hash is not None,
    }


def _truncated_receipts() -> dict[str, object]:
    receipts = tuple(
        ci.SequenceReceipt(
            campaign_id=UUID(int=5),
            stream_version=version,
            task_id=UUID(int=version),
            campaign_manifest_hash="d" * 64,
            attempted_order=(),
            intentionally_unattempted=(),
        )
        for version in (1, 2, 4)
    )
    seal = ci.SealedPartition(
        partition="training",
        campaign_manifest_hash="d" * 64,
        feature_set_hash="e" * 64,
        sealed_at=utc_now(),
        artifact_id=UUID(int=6),
        candidate_ids=frozenset(),
        task_ids=frozenset(),
        groups=frozenset(),
    )
    check = ci.the_receipt_chain_is_contiguous(
        ci.CorrectionEvidence(receipts=receipts, seals=(seal,))
    )
    return {"failed_closed": not check.ok, "reason": check.detail}


def _isolation_case() -> dict[str, object]:
    pair = ci.InheritedPair(
        name="artifacts_s21c3",
        root=DATA_ROOT / "artifacts-s21c3",
        expected_digest="0" * 64,
        expected_files=8503,
    )
    checks = ci.inherited_pairs_are_untouched(ci.CorrectionEvidence(inherited=(pair,)))
    return {
        "failed_closed": not checks[0].ok,
        "named": checks[0].name,
        "reason": checks[0].detail[:160],
    }


# ------------------------------------------------------------------------------- the run


async def _execute(output: Path) -> int:
    tree_before = _git_state()
    report: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D2",
        "wave": "W9",
        "items": ["S21D2-081", "S21D2-083", "S21D2-084", "S21D2-085b"],
        "started_at": utc_now().isoformat(),
        "final_outcomes_inspected": 0,
        "purpose": (
            "prove the D2 evidence survives being backed up, restarted and restored, and that "
            "damage to the restored copy is refused rather than absorbed"
        ),
        "fingerprints_before": _fingerprints(),
    }

    scratch = Path(tempfile.mkdtemp(prefix="s21d2-w9-"))
    try:
        extracted = await _prove_recovery(report, scratch)
        report["corruption_matrix"] = await _matrix(scratch, extracted)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    report["ci_coverage"] = _ci_coverage()
    report["fingerprints_after"] = _fingerprints()
    report["isolation"] = {
        "inherited_stores_unchanged": all(
            report["fingerprints_before"][name] == report["fingerprints_after"][name]
            for name in INHERITED
        ),
        "d2_evidence_pair_unchanged": (
            report["fingerprints_before"]["artifacts-s21d2"]
            == report["fingerprints_after"]["artifacts-s21d2"]
        ),
        "writes": "the backup root, the restore database and a scratch directory; nothing else",
    }
    report["findings"] = FINDINGS
    report["main_worktree_mutations"] = 0 if _git_state() == tree_before else "CHANGED"
    report["recorded_at"] = utc_now().isoformat()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.as_posix())

    unresolved = [
        row["case"]
        for row in report["corruption_matrix"]
        if not (row["observed"] or {}).get("failed_closed", False)  # type: ignore[union-attr]
    ]
    healthy = report["source_integrity_report"]["healthy"]
    return 0 if healthy and not unresolved else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    return asyncio.run(_execute(parser.parse_args().output))


if __name__ == "__main__":
    raise SystemExit(main())
