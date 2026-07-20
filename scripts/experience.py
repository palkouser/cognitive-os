"""Compile and inspect governed experience fixtures."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from cognitive_os.domain.experience import ExperienceCandidateStatus
from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.experience.fixtures import INITIAL_FIXTURES, build_fixture
from cognitive_os.experience.governance import (
    append_candidate_status,
    export_candidate,
    validate_candidate,
)
from cognitive_os.verification.experience import verify_compilation


def _json(value: object) -> str:
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


async def _database_health() -> int:
    from cognitive_os.infrastructure.experience.postgres.health import (
        PostgresExperienceHealthService,
    )
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required for database health")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresExperienceHealthService(engine).check()
    finally:
        await engine.dispose()
    print(report.model_dump_json())
    return 0 if report.healthy else 1


def _run(args: argparse.Namespace) -> int:
    request, sources, profiles = build_fixture(args.fixture)
    compiler = ExperienceCompiler(sources, profiles)
    if args.action == "cancel":
        compiler.cancel(request.compilation_id)
        print(_json({"compilation_id": request.compilation_id, "status": "cancelled"}))
        return 0
    result = compiler.compile(request)
    if args.action in {"compile", "resume", "get", "regenerate"}:
        payload = {
            "decision": result.decision.model_dump(mode="json"),
            "manifest": result.manifest.model_dump(mode="json"),
        }
    elif args.action == "snapshot":
        payload = result.snapshot.model_dump(mode="json")
    elif args.action == "sources":
        payload = [item.model_dump(mode="json") for item in result.snapshot.source_refs]
    elif args.action == "timeline":
        payload = result.trajectory.model_dump(mode="json")
    elif args.action == "segments":
        payload = [item.model_dump(mode="json") for item in result.segments]
    elif args.action == "assessments":
        payload = [item.model_dump(mode="json") for item in result.assessments]
    elif args.action == "paths":
        payload = {
            "successful": (
                result.analysis.successful_path.model_dump(mode="json")
                if result.analysis.successful_path
                else None
            ),
            "failed": [item.model_dump(mode="json") for item in result.analysis.failed_branches],
            "recovery": [item.model_dump(mode="json") for item in result.analysis.recovery_paths],
        }
    elif args.action == "corrections":
        payload = [item.model_dump(mode="json") for item in result.analysis.corrections]
    elif args.action == "contributions":
        payload = [item.model_dump(mode="json") for item in result.analysis.contributions]
    elif args.action == "generalizability":
        payload = result.analysis.generalizability.model_dump(mode="json")
    elif args.action == "candidates":
        payload = [item.model_dump(mode="json") for item in result.candidates]
    elif args.action in {"candidate", "validate-candidate", "reject-candidate", "export-candidate"}:
        candidate = next(
            (item for item in result.candidates if str(item.candidate_id) == args.candidate_id),
            result.candidates[0] if args.candidate_id is None else None,
        )
        if candidate is None:
            raise SystemExit("candidate is unavailable")
        if args.action == "validate-candidate":
            payload = {
                "candidate_id": str(candidate.candidate_id),
                "errors": validate_candidate(candidate, result.snapshot.content_hash),
            }
        elif args.action == "reject-candidate":
            payload = append_candidate_status(
                candidate,
                (),
                ExperienceCandidateStatus.REJECTED,
                actor_id=args.actor_id,
                reason=args.reason,
            ).model_dump(mode="json")
        elif args.action == "export-candidate":
            if args.output is None:
                raise SystemExit("--output is required for candidate export")
            package = export_candidate(candidate)
            args.output.mkdir(parents=True, exist_ok=True)
            for name, data in package.items():
                (args.output / name).write_bytes(data)
            payload = {"candidate_id": str(candidate.candidate_id), "files": sorted(package)}
        else:
            payload = candidate.model_dump(mode="json")
    elif args.action == "manifest":
        payload = result.manifest.model_dump(mode="json")
    elif args.action == "verify":
        payload = {
            "passed": result.verifier_bundle.passed and not verify_compilation(result),
            "bundle": result.verifier_bundle.model_dump(mode="json"),
            "failures": verify_compilation(result),
        }
    elif args.action == "health":
        payload = {
            "healthy": not verify_compilation(result),
            "fixtures": len(INITIAL_FIXTURES),
            "source_registry_hash": sources.snapshot_hash(),
            "profile_registry_hash": profiles.snapshot_hash(),
            "mandatory_verifiers": len(result.verifier_bundle.results),
            "destination_writes": 0,
            "automatic_promotions": 0,
        }
    else:
        raise AssertionError(args.action)
    print(_json(payload))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "compile",
            "resume",
            "cancel",
            "get",
            "snapshot",
            "sources",
            "timeline",
            "segments",
            "assessments",
            "paths",
            "corrections",
            "contributions",
            "generalizability",
            "candidates",
            "candidate",
            "validate-candidate",
            "reject-candidate",
            "export-candidate",
            "manifest",
            "verify",
            "regenerate",
            "health",
        ),
    )
    parser.add_argument("--fixture", choices=INITIAL_FIXTURES, default="direct-success")
    parser.add_argument("--candidate-id")
    parser.add_argument("--actor-id", default="operator")
    parser.add_argument("--reason", default="operator decision")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--database", action="store_true")
    args = parser.parse_args()
    if args.action == "health" and args.database:
        return asyncio.run(_database_health())
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
