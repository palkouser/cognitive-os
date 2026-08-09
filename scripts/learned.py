"""Inspect the durable learned evidence store. Read-only except the isolated smoke.

Every command prints one line of stable, sorted JSON so output can be diffed between
runs and parsed by a script that does not have to know this file exists.

Nothing here activates, approves or rolls back a learned component. Those are governed
mutations that require evidence a command line cannot supply, and putting them behind a
convenient flag is how a governance control becomes a formality. Sprint 21C1 leaves them
to the application service, which checks the evidence.

Exit status:

* `0` — the command succeeded and what it checked is healthy;
* `1` — the store is unhealthy, or a verification failed;
* `2` — invalid usage (argparse);
* `3` — the requested component, lineage or observation does not exist.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

NOT_FOUND = 3


def _emit(payload: object) -> None:
    print(json.dumps(payload, default=str, sort_keys=True, separators=(",", ":")))


def _database_url() -> str:
    url = os.environ.get("COGOS_DATABASE_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_URL is required")
    return url


def _engine() -> Any:
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    return create_postgres_engine(_database_url(), pool_size=1, max_overflow=0)


async def _with_repository(action: Any) -> int:
    from cognitive_os.infrastructure.learned.postgres.repository import (
        PostgresLearnedEvidenceRepository,
    )

    engine = _engine()
    try:
        return await action(PostgresLearnedEvidenceRepository(engine))
    finally:
        await engine.dispose()


async def _health(_args: argparse.Namespace) -> int:
    from cognitive_os.infrastructure.learned.postgres.health import (
        PostgresLearnedHealthService,
    )

    engine = _engine()
    try:
        report = await PostgresLearnedHealthService(engine).check()
    finally:
        await engine.dispose()
    _emit(report.model_dump(mode="json"))
    return 0 if report.healthy else 1


async def _component_show(args: argparse.Namespace) -> int:
    async def action(repository: Any) -> int:
        row = await repository.get_component(args.component_id)
        if row is None:
            _emit({"component_id": args.component_id, "found": False})
            return NOT_FOUND
        _emit(row.model_dump(mode="json"))
        return 0

    return await _with_repository(action)


async def _component_history(args: argparse.Namespace) -> int:
    async def action(repository: Any) -> int:
        history = await repository.component_history(args.component_id, limit=args.limit)
        if not history:
            _emit({"component_id": args.component_id, "found": False})
            return NOT_FOUND
        _emit(
            {
                "component_id": args.component_id,
                "revisions": [item.model_dump(mode="json") for item in history],
            }
        )
        return 0

    return await _with_repository(action)


async def _evidence_verify(args: argparse.Namespace) -> int:
    """Re-validate stored evidence payloads against their sealed hashes.

    Re-validation *is* the verification: the contract re-seals on load and refuses a
    payload whose content no longer matches the hash it carries.
    """

    async def action(repository: Any) -> int:
        records = await repository.list_evidence(component_id=args.component_id, limit=args.limit)
        failures = [
            str(item.evidence_id)
            for item in records
            if item.content_hash != item.canonical_hash(exclude={"content_hash"})
        ]
        _emit(
            {
                "component_id": args.component_id,
                "verified": len(records),
                "failed": failures,
                "healthy": not failures,
            }
        )
        return 1 if failures else 0

    return await _with_repository(action)


async def _artifact_verify(args: argparse.Namespace) -> int:
    """Re-hash the bytes behind learned lineage. Reads and hashes; never loads."""
    from pathlib import Path

    from cognitive_os.infrastructure.artifacts.filesystem import (
        ContentAddressedFilesystem,
    )
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore
    from cognitive_os.infrastructure.learned.postgres.repository import (
        PostgresLearnedEvidenceRepository,
    )
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )

    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not root:
        raise SystemExit("COGOS_ARTIFACT_ROOT is required for artifact verification")
    engine = _engine()
    try:
        repository = PostgresLearnedEvidenceRepository(engine)
        store = LearnedArtifactStore(
            ArtifactService(
                ContentAddressedFilesystem(Path(root)),
                PostgresArtifactRepository(engine),
            )
        )
        if args.lineage_id is not None:
            lineage = await repository.get_artifact_lineage(UUID(args.lineage_id))
            if lineage is None:
                _emit({"lineage_id": args.lineage_id, "found": False})
                return NOT_FOUND
            verified = await store.verify_artifact(lineage.artifact_id)
            _emit(
                {
                    "lineage_id": args.lineage_id,
                    "artifact_id": str(lineage.artifact_id),
                    "verified": verified,
                    "healthy": verified,
                }
            )
            return 0 if verified else 1
        report = await PostgresLearnedHealthArtifacts(engine, store).check(limit=args.limit)
    finally:
        await engine.dispose()
    _emit(report)
    return 0 if report["healthy"] else 1


class PostgresLearnedHealthArtifacts:
    """Bulk lineage verification, kept out of health so health stays cheap.

    Health re-hashes nothing: re-reading every artifact would make the check expensive
    enough to stop being run, and an expensive check that is skipped is worse than a
    cheap one that is not.
    """

    def __init__(self, engine: Any, store: Any) -> None:
        self._engine = engine
        self._store = store

    async def check(self, *, limit: int) -> dict[str, Any]:
        from sqlalchemy import select

        from cognitive_os.infrastructure.learned.postgres.tables import (
            learned_artifacts,
        )

        async with self._engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        select(
                            learned_artifacts.c.lineage_id,
                            learned_artifacts.c.artifact_id,
                        )
                        .order_by(learned_artifacts.c.lineage_id)
                        .limit(limit)
                    )
                )
                .mappings()
                .all()
            )
        failures = [
            str(row["lineage_id"])
            for row in rows
            if not await self._store.verify_artifact(row["artifact_id"])
        ]
        return {"verified": len(rows), "failed": failures, "healthy": not failures}


async def _observation_list(args: argparse.Namespace) -> int:
    from cognitive_os.domain.learned_evidence import ObservationStatus

    status = ObservationStatus(args.status) if args.status else None

    async def action(repository: Any) -> int:
        records = await repository.list_observations(
            surface=args.surface, status=status, limit=args.limit
        )
        _emit({"count": len(records), "observations": [_redact(item) for item in records]})
        return 0

    return await _with_repository(action)


async def _observation_quarantine(args: argparse.Namespace) -> int:
    """The quarantine queue, redacted, with its reason codes grouped."""
    from cognitive_os.domain.learned_evidence import ObservationStatus

    async def action(repository: Any) -> int:
        records = await repository.list_observations(
            surface=args.surface, status=ObservationStatus.QUARANTINED, limit=args.limit
        )
        by_code: dict[str, int] = {}
        for item in records:
            code = item.decision_reason.split(":", 1)[0].strip()
            by_code[code] = by_code.get(code, 0) + 1
        _emit(
            {
                "count": len(records),
                "by_reason_code": dict(sorted(by_code.items())),
                "observations": [_redact(item) for item in records],
            }
        )
        return 0

    return await _with_repository(action)


def _redact(observation: Any) -> dict[str, Any]:
    """Identity, classification and hashes. Never a body, and never the reason prose.

    The observation record holds no example body to begin with, so this is not filtering
    something more revealing — it is the shape the store keeps, restated as what an
    operator needs from a terminal.
    """
    return {
        "observation_id": str(observation.observation_id),
        "surface": observation.surface,
        "source_kind": observation.source_kind,
        "source_payload_hash": observation.source_payload_hash,
        "provenance_class": observation.provenance_class.value,
        "attribution": observation.attribution.value,
        "status": observation.status.value,
        "sensitivity": observation.sensitivity,
        "decision_code": observation.decision_reason.split(":", 1)[0].strip(),
        "evaluation_eligible": observation.evaluation_eligible,
        "training_eligible": observation.training_eligible,
        "recorded_at": observation.recorded_at.isoformat(),
    }


async def _replay_verify(_args: argparse.Namespace) -> int:
    """Rebuild every projection from history and report whether they agree."""

    async def action(repository: Any) -> int:
        result = await repository.replay()
        _emit(result.model_dump(mode="json"))
        return 0 if result.projection_matches and result.hash_chain_verified else 1

    return await _with_repository(action)


async def _smoke(args: argparse.Namespace) -> int:
    """The one mutating command, and only against an explicitly isolated database.

    It refuses any database whose name does not end in `_test`. A smoke fixture that
    could run against a real store would be a way to write a fabricated component into
    production by typo.
    """
    from cognitive_os.learned_smoke import run_learned_smoke

    if not args.confirm_isolated:
        raise SystemExit("smoke requires --confirm-isolated and an isolated *_test database")
    report = await run_learned_smoke()
    _emit(report)
    return 0 if report["healthy"] else 1


async def _correction_runtime(args: argparse.Namespace) -> int:
    """S21D2-080. Report why the correction surface is or is not using a learned ordering.

    Read-only and offline: it reconciles the *configuration* half against the durable half
    and prints the reason code the resolver would return. It cannot activate, approve or
    change anything — there is no flag here that turns the component on, because turning it
    on is an approval-bound transaction rather than a command-line option.
    """
    from cognitive_os.application.services.learned_runtime import (
        ActiveComponentState,
        ArtifactAvailability,
        EmbeddingIdentity,
        LearnedRuntimeResolver,
        RoutingPolicy,
    )
    from cognitive_os.config.learned_config import load_learned_configuration
    from cognitive_os.learning.correction_ranking import CorrectionKnn

    if not args.config:
        _emit({"error": "correction-runtime needs --config naming a learned configuration"})
        return 2
    configuration = load_learned_configuration(Path(args.config))
    policy = RoutingPolicy(
        persistence_enabled=configuration.persistence_enabled,
        activation_enabled=configuration.activation_enabled,
        active_components=configuration.active_components,
        routed_groups=configuration.correction_ranking_groups,
        routing_manifest_hash=configuration.correction_ranking_manifest_hash,
    )
    expected = EmbeddingIdentity(
        model_id=args.model_id or "", revision=args.model_revision or "", available=True
    )
    resolver = LearnedRuntimeResolver(surface=CorrectionKnn.surface, expected_embedding=expected)

    async def action(repository: Any) -> int:
        row = await repository.active_component_for(CorrectionKnn.surface)
        states = (
            []
            if row is None
            else [
                ActiveComponentState(
                    component_id=row.component_id,
                    surface=CorrectionKnn.surface,
                    revision=row.current_revision,
                    model_artifact_id=UUID(int=0),
                    lineage_verified=False,
                    descriptor_revision=row.current_revision,
                )
            ]
        )
        resolved = resolver.resolve(
            policy=policy,
            active_states=states,
            group=args.group or "",
            artifact=ArtifactAvailability(present=False),
            local_embedding=expected,
        )
        health = resolver.health(resolved, routed_groups=len(policy.routed_groups))
        _emit(health.as_dict())
        return 0

    return await _with_repository(action)


async def _correction_integrity(args: argparse.Namespace) -> int:
    """S21D2-081. The eight-class integrity report over the correction-ranking evidence.

    `--seals` names the campaign evidence file the sprint published, because the sealed
    feature-set artifact ids and their hashes are the authority for every other check and
    this command must not be free to invent them. `--stop-record` names the decision that
    closed a class; without it, a class with nothing in it would be reported as a passing
    zero, which is the one thing S21D2-081 forbids.
    """
    from datetime import datetime

    from cognitive_os.coding.reality_integrity import IntegrityReport
    from cognitive_os.infrastructure.artifacts.filesystem import (
        ContentAddressedFilesystem,
    )
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )
    from cognitive_os.learning import correction_integrity as ci

    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not root:
        raise SystemExit("COGOS_ARTIFACT_ROOT is required for the correction integrity report")
    if not args.seals:
        _emit({"error": "correction-integrity needs --seals naming the campaign evidence file"})
        return 2

    campaign = json.loads(Path(args.seals).read_text())
    sources = [
        ci.SealSource(
            partition=partition["partition"],
            campaign_manifest_hash=partition["campaign_manifest_hash"],
            artifact_id=UUID(partition["feature_set_artifact_id"]),
            feature_set_hash=partition["feature_set_hash"],
            sealed_at=datetime.fromisoformat(partition["features_sealed_at"]),
        )
        for partition in campaign["partitions"]
    ]
    inherited: list[Any] = []
    if args.inherited:
        # `name -> {root, path_and_size_fingerprint_sha256, files}`, exactly the shape the
        # W0 baseline evidence published. Given as a file rather than as flags so that the
        # expected digests come from the record instead of from whoever typed the command.
        declared = json.loads(Path(args.inherited).read_text())
        inherited = [
            ci.InheritedPair(
                name=name,
                root=Path(pair["root"]),
                expected_digest=pair["path_and_size_fingerprint_sha256"],
                expected_files=int(pair["files"]),
            )
            for name, pair in sorted(declared.items())
        ]
    stop = None
    if args.stop_record:
        record = json.loads(Path(args.stop_record).read_text())
        stop = ci.StopRecord(
            name=record["name"],
            content_hash=record["content_hash"],
            reason=record["reason"],
        )

    engine = _engine()
    try:
        store = ArtifactService(
            ContentAddressedFilesystem(Path(root)), PostgresArtifactRepository(engine)
        )
        # Discovery first, because a campaign that was executed more than once sealed once
        # per execution and the evidence file names only the last one. Without the earlier
        # seals the chronology check reports rows written under them as out of order.
        async with engine.connect() as connection:
            candidates = await ci.seal_candidates(connection)
        # Fetched with no connection held, because the store opens one per read and the
        # report holds one for its whole pass.
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
                selection_stop=stop,
            )
    finally:
        await engine.dispose()

    report = IntegrityReport(checks=ci.correction_checks(evidence))
    _emit({"counts": ci.correction_counts(evidence), **report.as_dict()})
    return 0 if report.healthy else 1


#: Every store this sprint must not open. Named as absolute roots, because the boundary a
#: typo crosses is a path rather than a flag: `artifacts` and `artifacts-s21d3` differ by a
#: suffix, and the first is the development store.
_FORBIDDEN_ROOTS = (
    "/home/palkouser/projekt/cognitive-os-data/artifacts",
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21c3",
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d1",
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d2",
)


def _require_d3_environment(*, needs_store: bool) -> Path | None:
    """Refuse a wrong or missing D3 environment before anything is opened.

    S21D3-080. The check is first and it is on the *values*, not on whether they are set: an
    operator who sourced the D2 environment by habit has a complete, valid configuration
    pointing at a store this sprint may not write to, and every later check would pass while
    reading the wrong evidence.
    """
    database = os.environ.get("COGOS_POSTGRES_DATABASE") or os.environ.get("COGOS_DATABASE_URL")
    if database and "s21d3" not in database:
        raise SystemExit(
            f"refusing to run against {database!r}: the D3 commands require an s21d3 database"
        )
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if root is None:
        if needs_store:
            raise SystemExit("COGOS_ARTIFACT_ROOT is required to check artifact bytes")
        return None
    resolved = Path(root).resolve()
    if str(resolved) in _FORBIDDEN_ROOTS:
        raise SystemExit(f"refusing to open the predecessor store at {resolved}")
    if "s21d3" not in resolved.name:
        raise SystemExit(f"refusing to open {resolved}: the D3 commands require the D3 store")
    return resolved


#: D4 inherits one more predecessor than D3 did, and the one it inherits is the store D3 itself
#: wrote. `artifacts-s21d3` is not on D3's own forbidden list for the obvious reason.
_FORBIDDEN_ROOTS_D4 = (
    *_FORBIDDEN_ROOTS,
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d3",
)


def _require_d4_environment(*, needs_store: bool) -> Path | None:
    """S21D4-080. Refuse a wrong or missing D4 environment before anything is opened.

    Same boundary as D3's and for the same reason, over five predecessor roots rather than
    four. It is checked on the *values*: an operator who sourced `.env.s21d3.local` out of habit
    has a complete, valid configuration pointing at a store this sprint may not write to, and
    every later check would pass while reading the wrong evidence. W7-A5 in D3 is what that
    looks like when it happens — a database and an artifact root that belonged to different
    sprints, discovered only because a store survey ran before the backup.
    """
    database = os.environ.get("COGOS_POSTGRES_DATABASE") or os.environ.get("COGOS_DATABASE_URL")
    if database and "s21d4" not in database:
        raise SystemExit(
            f"refusing to run against {database!r}: the D4 commands require an s21d4 database"
        )
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if root is None:
        if needs_store:
            raise SystemExit("COGOS_ARTIFACT_ROOT is required to check artifact bytes")
        return None
    resolved = Path(root).resolve()
    if str(resolved) in _FORBIDDEN_ROOTS_D4:
        raise SystemExit(f"refusing to open the predecessor store at {resolved}")
    if "s21d4" not in resolved.name:
        raise SystemExit(f"refusing to open {resolved}: the D4 commands require the D4 store")
    return resolved


async def _d3_integrity(args: argparse.Namespace) -> int:
    """S21D3-080 and -081. The eleven-class D3 report, read-only and offline by default.

    It reads the committed evidence directory and nothing else unless asked: `--rehash-blobs`
    opens the D3 artifact store, and `--data-root` re-takes the predecessor fingerprints. Both
    are opt-in because the report has to be runnable in a lane that has neither — and both are
    reported as `warning` rather than `clean` when they are not run.
    """
    from cognitive_os.learning.integrity_d3 import d3_integrity, path_and_size_fingerprint

    root = _require_d3_environment(needs_store=args.rehash_blobs)
    evidence = Path(args.evidence or "docs/sprints/sprint-21/evidence")
    if not evidence.is_dir():
        raise SystemExit(f"{evidence} is not an evidence directory")

    blobs: dict[str, str] | None = None
    if args.rehash_blobs and root is not None:
        blobs = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file() and not path.name.startswith(".")
        }
    fingerprints: dict[str, str] | None = None
    if args.data_root:
        data = Path(args.data_root)
        fingerprints = {
            name: path_and_size_fingerprint(data / directory)
            for name, directory in (
                ("development", "artifacts"),
                ("sprint_21c3", "artifacts-s21c3"),
                ("sprint_21d1", "artifacts-s21d1"),
                ("sprint_21d2", "artifacts-s21d2"),
            )
            if (data / directory).is_dir()
        }

    report = d3_integrity(evidence, blob_hashes=blobs, predecessor_fingerprints=fingerprints)
    _emit(report.as_dict())
    return 0 if report.healthy else 1


async def _d4_integrity(args: argparse.Namespace) -> int:
    """S21D4-080 and -081. The twelve-class D4 report, read-only and offline by default.

    The eleven released classes over D4's own evidence plus `decision_independence`, which is
    the one D3 could not have had: it fails when any committed file takes a rate over the
    counted decisions rather than the distinct ones.

    Offline by default and opt-in for both authorities, exactly as the D3 command is, because
    the point of a report that reads files is that a lane with no database, no store and no
    credential can run it — and can never claim a check it did not make.
    """
    from cognitive_os.learning.integrity_d4 import d4_integrity, path_and_size_fingerprint

    root = _require_d4_environment(needs_store=args.rehash_blobs)
    evidence = Path(args.evidence or "docs/sprints/sprint-21/evidence")
    if not evidence.is_dir():
        raise SystemExit(f"{evidence} is not an evidence directory")

    blobs: dict[str, str] | None = None
    if args.rehash_blobs and root is not None:
        blobs = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file() and not path.name.startswith(".")
        }
    fingerprints: dict[str, str] | None = None
    if args.data_root:
        data = Path(args.data_root)
        fingerprints = {
            name: path_and_size_fingerprint(data / directory)
            for name, directory in (
                ("development", "artifacts"),
                ("sprint_21c3", "artifacts-s21c3"),
                ("sprint_21d1", "artifacts-s21d1"),
                ("sprint_21d2", "artifacts-s21d2"),
                ("sprint_21d3", "artifacts-s21d3"),
            )
            if (data / directory).is_dir()
        }

    report = d4_integrity(evidence, blob_hashes=blobs, predecessor_fingerprints=fingerprints)
    _emit(report.as_dict())
    return 0 if report.healthy else 1


#: D5 inherits six, and the sixth is the store D4 wrote. Every sprint's list is the previous
#: one plus the predecessor an operator is most likely to still have exported.
_FORBIDDEN_ROOTS_D5 = (
    *_FORBIDDEN_ROOTS_D4,
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d4",
)

#: The predecessor pairs D5's isolation class re-fingerprints, in the order the baseline
#: declares them.
_D5_PREDECESSORS = (
    ("development", "artifacts"),
    ("sprint_21c3", "artifacts-s21c3"),
    ("sprint_21d1", "artifacts-s21d1"),
    ("sprint_21d2", "artifacts-s21d2"),
    ("sprint_21d3", "artifacts-s21d3"),
    ("sprint_21d4", "artifacts-s21d4"),
)


def _require_d5_environment(*, needs_store: bool) -> Path | None:
    """S21D5-080. Refuse a wrong or missing D5 environment before anything is opened.

    The same boundary as D3's and D4's, over six predecessor roots rather than five, and
    checked on the *values* rather than on whether they are set. An operator who sourced
    `.env.s21d4.local` out of habit has a complete, valid configuration pointing at the store
    the last sprint wrote, and every later check would pass while reading the wrong evidence.
    """
    database = os.environ.get("COGOS_POSTGRES_DATABASE") or os.environ.get("COGOS_DATABASE_URL")
    if database and "s21d5" not in database:
        raise SystemExit(
            f"refusing to run against {database!r}: the D5 commands require an s21d5 database"
        )
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if root is None:
        if needs_store:
            raise SystemExit("COGOS_ARTIFACT_ROOT is required to check artifact bytes")
        return None
    resolved = Path(root).resolve()
    if str(resolved) in _FORBIDDEN_ROOTS_D5:
        raise SystemExit(f"refusing to open the predecessor store at {resolved}")
    if "s21d5" not in resolved.name:
        raise SystemExit(f"refusing to open {resolved}: the D5 commands require the D5 store")
    return resolved


async def _d5_integrity(args: argparse.Namespace) -> int:
    """S21D5-080 and -081. The twelve-class D5 report, read-only and offline by default.

    Nine of the twelve are the released D4 implementations reading D5's prefix; three read
    different bytes and are written in `integrity_d5`. Offline by default and opt-in for both
    authorities, for the reason the D4 command records: a lane with no database, no store and
    no credential must be able to run it, and must never be able to claim a check it did not
    make.
    """
    from cognitive_os.learning.integrity_d5 import d5_integrity, path_and_size_fingerprint

    root = _require_d5_environment(needs_store=args.rehash_blobs)
    evidence = Path(args.evidence or "docs/sprints/sprint-21/evidence")
    if not evidence.is_dir():
        raise SystemExit(f"{evidence} is not an evidence directory")

    blobs: dict[str, str] | None = None
    if args.rehash_blobs and root is not None:
        blobs = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file() and not path.name.startswith(".")
        }
    fingerprints: dict[str, str] | None = None
    if args.data_root:
        data = Path(args.data_root)
        fingerprints = {
            name: path_and_size_fingerprint(data / directory)
            for name, directory in _D5_PREDECESSORS
            if (data / directory).is_dir()
        }

    report = d5_integrity(evidence, blob_hashes=blobs, predecessor_fingerprints=fingerprints)
    _emit(report.as_dict())
    return 0 if report.healthy else 1


_ACTIONS = {
    "health": _health,
    "correction-runtime": _correction_runtime,
    "correction-integrity": _correction_integrity,
    "d3-integrity": _d3_integrity,
    "d4-integrity": _d4_integrity,
    "d5-integrity": _d5_integrity,
    "component-show": _component_show,
    "component-history": _component_history,
    "evidence-verify": _evidence_verify,
    "artifact-verify": _artifact_verify,
    "observation-list": _observation_list,
    "observation-quarantine": _observation_quarantine,
    "replay-verify": _replay_verify,
    "smoke": _smoke,
}

_NEEDS_COMPONENT = {"component-show", "component-history"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=tuple(_ACTIONS))
    parser.add_argument("--component-id", help="exact learned component identifier")
    parser.add_argument("--lineage-id", help="exact artifact lineage identifier")
    parser.add_argument("--surface", help="restrict to one decision surface")
    parser.add_argument("--config", help="learned configuration file to reconcile against")
    parser.add_argument("--group", help="task group to test routing for")
    parser.add_argument("--model-id", help="expected local embedding model identifier")
    parser.add_argument("--model-revision", help="expected local embedding model revision")
    parser.add_argument("--seals", help="campaign evidence file naming the sealed feature sets")
    parser.add_argument("--inherited", help="JSON of inherited artifact roots and their digests")
    parser.add_argument("--stop-record", help="JSON naming the decision that closed a class")
    parser.add_argument(
        "--status",
        choices=("accepted", "quarantined", "rejected"),
        help="observation status",
    )
    parser.add_argument("--limit", type=int, default=100, help="maximum rows to return")
    parser.add_argument("--evidence", help="committed evidence directory to report on")
    parser.add_argument(
        "--rehash-blobs",
        action="store_true",
        help="open the D3 artifact store and rehash every blob against its content address",
    )
    parser.add_argument(
        "--data-root",
        help="data root holding the predecessor stores, to re-take their fingerprints",
    )
    parser.add_argument(
        "--confirm-isolated",
        action="store_true",
        help="required by smoke; asserts the target database is disposable",
    )
    args = parser.parse_args(argv)
    if args.action in _NEEDS_COMPONENT and not args.component_id:
        parser.error(f"{args.action} requires --component-id")
    if args.limit < 1:
        parser.error("--limit must be positive")
    return asyncio.run(_ACTIONS[args.action](args))


if __name__ == "__main__":
    sys.exit(main())
