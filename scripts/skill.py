"""Inspect and operate the governed procedural Skill Engine."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.services.skill_service import SkillService
from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.domain.skills import (
    SkillActor,
    SkillCreatorType,
    SkillPromotionDecision,
    SkillPromotionOutcome,
    SkillStatus,
)
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.skills.packaging import (
    export_package,
    load_artifact_package,
    load_package,
    load_zip_package,
)
from cognitive_os.skills.statistics import rebuild_statistics
from cognitive_os.skills.validation import build_skill_verification_snapshot


def _package(path: Path, configuration: SkillConfiguration):
    return (
        load_zip_package(path, configuration)
        if path.is_file()
        else load_package(path, configuration)
    )


def _actor(args: argparse.Namespace) -> SkillActor:
    return SkillActor(
        creator_type=SkillCreatorType.OPERATOR,
        creator_id=args.actor_id,
    )


def _database_url() -> str:
    value = os.environ.get("COGOS_DATABASE_URL")
    if not value:
        raise RuntimeError("COGOS_DATABASE_URL is required")
    return value


def _artifact_root() -> Path:
    value = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not value:
        raise RuntimeError("COGOS_ARTIFACT_ROOT is required")
    return Path(value)


def _runtime():
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
    from cognitive_os.infrastructure.skills.postgres.repository import PostgresSkillRepository

    engine = create_postgres_engine(_database_url())
    repository = PostgresSkillRepository(engine)
    artifacts = ArtifactService(
        ContentAddressedFilesystem(_artifact_root()),
        PostgresArtifactRepository(engine),
    )
    service = SkillService(repository, artifacts, SkillConfiguration())
    return engine, repository, artifacts, service


async def _run(args: argparse.Namespace) -> int:
    configuration = SkillConfiguration()
    if args.action == "inspect-package":
        package = _package(args.path, configuration)
        print(package.manifest.model_dump_json())
        return 0
    if args.action == "list-packages":
        values = [
            {
                "path": path.as_posix(),
                "package_hash": load_package(path, configuration).manifest.package_hash,
            }
            for path in sorted(args.root.glob("*/*"))
        ]
        print(json.dumps(values, sort_keys=True, separators=(",", ":")))
        return 0
    if args.action == "export-package":
        package = _package(args.path, configuration)
        if not args.dry_run:
            export_package(package, args.destination)
        print(package.manifest.model_dump_json())
        return 0
    if args.action in {"execute", "resume", "cancel", "execution"}:
        raise RuntimeError("execution commands require the running application Controller adapter")
    if args.action == "health":
        from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
        from cognitive_os.infrastructure.skills.postgres.health import PostgresSkillHealthService

        engine = create_postgres_engine(_database_url(), pool_size=1, max_overflow=0)
        try:
            report = await PostgresSkillHealthService(engine).check()
        finally:
            await engine.dispose()
        print(report.model_dump_json())
        return 0 if report.healthy else 1
    engine, repository, artifacts, service = _runtime()
    try:
        if args.action in {"import", "create"}:
            if args.dry_run:
                print(_package(args.path, configuration).manifest.model_dump_json())
                return 0
            item, revision, _ = await service.import_package(
                args.path, actor=_actor(args), reason=args.reason
            )
            print(
                json.dumps(
                    {
                        "skill_id": str(item.identity.skill_id),
                        "revision": revision.revision,
                        "status": revision.status.value,
                        "package_hash": revision.package_hash,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if args.action == "revise":
            revision, _ = await service.revise_package(
                args.skill_id,
                args.path,
                expected_revision=args.expected_revision,
                actor=_actor(args),
                reason=args.reason,
            )
            print(revision.model_dump_json())
            return 0
        if args.action == "history":
            values = await repository.list_revisions(args.skill_id, limit=args.limit)
            print(
                json.dumps(
                    [item.model_dump(mode="json") for item in values],
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
            return 0
        if args.action in {"statistics", "rebuild-statistics", "accesses", "usage-report"}:
            if args.action == "rebuild-statistics":
                executions = await repository.list_executions(args.skill_id, args.revision)
                statistics = rebuild_statistics(args.skill_id, args.revision, executions)
                await repository.write_statistics(statistics)
                print(statistics.model_dump_json())
                return 0
            accesses = await repository.list_accesses(
                args.skill_id, args.revision, limit=args.limit
            )
            if args.action == "accesses":
                print(
                    json.dumps(
                        [item.model_dump(mode="json") for item in accesses],
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                return 0
            statistics = await repository.read_statistics(args.skill_id, args.revision)
            payload = (
                statistics.model_dump(mode="json")
                if statistics is not None
                else {"skill_id": str(args.skill_id), "revision": args.revision}
            )
            if args.action == "usage-report":
                payload["access_count"] = len(accesses)
                payload["access_types"] = sorted({item.access_type.value for item in accesses})
            print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
            return 0
        if args.action == "export":
            revision = await repository.get_revision(args.skill_id, args.revision)
            if revision is None:
                raise RuntimeError("skill revision is unavailable")
            package = load_artifact_package(
                await artifacts.get_bytes(revision.package_artifact.artifact_id),
                configuration,
            )
            if not args.dry_run:
                export_package(package, args.destination)
            print(package.manifest.model_dump_json())
            return 0
        if args.action == "verify":
            current = await repository.get_current(args.skill_id)
            if current is None or current[1].revision != args.expected_revision:
                raise RuntimeError("skill revision is stale or unavailable")
            revision = current[1]
            package = load_artifact_package(
                await artifacts.get_bytes(revision.package_artifact.artifact_id),
                configuration,
            )
            snapshot = build_skill_verification_snapshot(revision, package)
            if not snapshot.passed:
                raise RuntimeError("skill verification did not pass")
            verifier_bundle = await artifacts.put_bytes(
                snapshot.model_dump_json().encode(), media_type="application/json"
            )
            regression = await artifacts.put_bytes(
                json.dumps(
                    {
                        "regression_profile": revision.regression_profile,
                        "passed": snapshot.regression_suite,
                    },
                    sort_keys=True,
                ).encode(),
                media_type="application/json",
            )
            promotion = SkillPromotionDecision(
                decision_id=uuid5(NAMESPACE_URL, f"skill-promotion:{snapshot.canonical_hash()}"),
                skill_id=revision.skill_id,
                revision=revision.revision,
                outcome=SkillPromotionOutcome.VERIFY,
                verifier_bundle=verifier_bundle,
                regression_summary=regression,
                decided_by=_actor(args),
                reason_codes=("all_required_verifiers_passed",),
                decided_at=revision.created_at,
            )
            verified = await service.transition(
                args.skill_id,
                SkillStatus.VERIFIED,
                expected_revision=args.expected_revision,
                actor=_actor(args),
                reason=args.reason,
                verification=snapshot,
                promotion=promotion,
            )
            print(verified.model_dump_json())
            return 0
        status = {
            "stage": SkillStatus.STAGED,
            "deprecate": SkillStatus.DEPRECATED,
            "supersede": SkillStatus.SUPERSEDED,
            "retract": SkillStatus.RETRACTED,
        }[args.action]
        revision = await service.transition(
            args.skill_id,
            status,
            expected_revision=args.expected_revision,
            actor=_actor(args),
            reason=args.reason,
        )
        print(revision.model_dump_json())
        return 0
    finally:
        await engine.dispose()


def _common_identity(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("skill_id", type=UUID)
    parser.add_argument("--expected-revision", type=int, required=True)
    parser.add_argument("--actor-id", default="operator")
    parser.add_argument("--reason", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    inspect = subparsers.add_parser("inspect-package")
    inspect.add_argument("path", type=Path)
    listing = subparsers.add_parser("list-packages")
    listing.add_argument("root", type=Path, default=Path("procedural_skills"), nargs="?")
    package_export = subparsers.add_parser("export-package")
    package_export.add_argument("path", type=Path)
    package_export.add_argument("destination", type=Path)
    package_export.add_argument("--dry-run", action="store_true")
    for name in ("import", "create"):
        command = subparsers.add_parser(name)
        command.add_argument("path", type=Path)
        command.add_argument("--actor-id", default="operator")
        command.add_argument("--reason", required=True)
        command.add_argument("--dry-run", action="store_true")
    revise = subparsers.add_parser("revise")
    _common_identity(revise)
    revise.add_argument("path", type=Path)
    for name in ("stage", "verify", "deprecate", "supersede", "retract"):
        _common_identity(subparsers.add_parser(name))
    history = subparsers.add_parser("history")
    history.add_argument("skill_id", type=UUID)
    history.add_argument("--limit", type=int, default=100)
    for name in ("statistics", "rebuild-statistics", "accesses", "usage-report"):
        command = subparsers.add_parser(name)
        command.add_argument("skill_id", type=UUID)
        command.add_argument("revision", type=int)
        command.add_argument("--limit", type=int, default=200)
    export = subparsers.add_parser("export")
    export.add_argument("skill_id", type=UUID)
    export.add_argument("revision", type=int)
    export.add_argument("destination", type=Path)
    export.add_argument("--dry-run", action="store_true")
    subparsers.add_parser("health")
    for name in ("execute", "resume", "cancel", "execution"):
        command = subparsers.add_parser(name)
        command.add_argument("execution_id", type=UUID)
    return parser


def main() -> int:
    return asyncio.run(_run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
