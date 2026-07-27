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
import json
import os
import sys
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
    from cognitive_os.infrastructure.learned.postgres.health import PostgresLearnedHealthService

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

    from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
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
                ContentAddressedFilesystem(Path(root)), PostgresArtifactRepository(engine)
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

        from cognitive_os.infrastructure.learned.postgres.tables import learned_artifacts

        async with self._engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        select(learned_artifacts.c.lineage_id, learned_artifacts.c.artifact_id)
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


_ACTIONS = {
    "health": _health,
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
    parser.add_argument(
        "--status", choices=("accepted", "quarantined", "rejected"), help="observation status"
    )
    parser.add_argument("--limit", type=int, default=100, help="maximum rows to return")
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
