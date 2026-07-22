"""Inspect governed proposal-only Harness Proposal Engine behavior."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from uuid import UUID

from cognitive_os.domain.proposals import (
    HarnessProposalRevision,
    HarnessProposalType,
    ProposalReviewDecision,
    ProposalStatus,
)
from cognitive_os.proposals.fixtures import (
    FIXTURE_TIME,
    FixtureWeaknessProposalSource,
    fixture_proposal_source,
)
from cognitive_os.proposals.repository import InMemoryProposalRepository
from cognitive_os.proposals.service import HarnessProposalService


async def fixture_service() -> tuple[
    HarnessProposalService, InMemoryProposalRepository, FixtureWeaknessProposalSource
]:
    source = await fixture_proposal_source()
    repository = InMemoryProposalRepository()
    return HarnessProposalService(repository, source), repository, source


async def create_fixture(
    service: HarnessProposalService,
    source: FixtureWeaknessProposalSource,
    proposal_type: HarnessProposalType,
) -> HarnessProposalRevision:
    return await service.create_from_weakness(
        source.revision.weakness_id,
        source.revision.revision,
        proposal_type,
        actor="operator",
        created_at=FIXTURE_TIME,
    )


async def _database_health() -> int:
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
    from cognitive_os.infrastructure.proposals.postgres.health import PostgresProposalHealthService

    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required for database health")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresProposalHealthService(engine).check()
    finally:
        await engine.dispose()
    print(report.model_dump_json())
    return 0 if report.healthy else 1


async def _run(args: argparse.Namespace) -> int:
    if args.action == "health" and args.database:
        return await _database_health()
    service, repository, source = await fixture_service()
    proposal_type = HarnessProposalType(args.proposal_type)
    revision = await create_fixture(service, source, proposal_type)
    if args.proposal_id and UUID(args.proposal_id) != revision.proposal_id:
        raise RuntimeError("proposal ID does not match the exact fixture proposal")
    if args.revision and args.revision != revision.revision:
        raise RuntimeError("proposal revision is stale")
    if args.action in {"stage-review", "review", "approve-experiment"}:
        revision = await service.transition(
            revision.proposal_id,
            revision.revision,
            ProposalStatus.STAGED_FOR_REVIEW,
            actor="operator",
            reason="explicit CLI review staging",
            created_at=FIXTURE_TIME,
        )
    if args.action in {"review", "approve-experiment"}:
        decision = (
            ProposalReviewDecision.APPROVE_FOR_EXPERIMENT
            if args.action == "approve-experiment"
            else ProposalReviewDecision.ABSTAIN
        )
        revision = await service.record_review(
            revision.proposal_id,
            revision.revision,
            decision,
            reviewer="operator",
            reviewer_authority="proposal-reviewer",
            rationale="explicit CLI review",
            created_at=FIXTURE_TIME,
        )
    elif args.action == "reject":
        revision = await service.transition(
            revision.proposal_id,
            revision.revision,
            ProposalStatus.REJECTED,
            actor="operator",
            reason="explicit CLI rejection",
            created_at=FIXTURE_TIME,
        )
    elif args.action == "retract":
        revision = await service.transition(
            revision.proposal_id,
            revision.revision,
            ProposalStatus.RETRACTED,
            actor="operator",
            reason="explicit CLI retraction",
            created_at=FIXTURE_TIME,
        )
    if args.action in {"queue-list", "queue-inspect"}:
        identity = repository.identities[revision.proposal_id]
        entry = await service.enqueue(identity, revision.revision, created_at=FIXTURE_TIME)
        print(entry.model_dump_json())
        return 0
    if args.action == "verify-replay":
        replay = await service.verify_replay(
            revision.proposal_id, revision.revision, created_at=FIXTURE_TIME
        )
        print(replay.model_dump_json())
        return 0
    if args.action == "health":
        print(
            json.dumps(
                {
                    "healthy": True,
                    "proposal_types": len(service.registry.list()),
                    "proposal_only": True,
                },
                sort_keys=True,
            )
        )
        return 0
    print(revision.model_dump_json())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Governed proposal-only CLI; it never implements or applies changes."
    )
    parser.add_argument(
        "action",
        choices=(
            "create-from-weakness",
            "inspect",
            "validate",
            "stage-review",
            "review",
            "approve-experiment",
            "reject",
            "retract",
            "queue-list",
            "queue-inspect",
            "verify-replay",
            "health",
            "smoke",
        ),
    )
    parser.add_argument(
        "--proposal-type",
        choices=tuple(item.value for item in HarnessProposalType),
        default=HarnessProposalType.CONTEXT_PROFILE_CHANGE.value,
    )
    parser.add_argument("--proposal-id")
    parser.add_argument("--revision", type=int)
    parser.add_argument("--database", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="confirm an exact review or experiment-approval decision",
    )
    args = parser.parse_args()
    if args.action in {
        "stage-review",
        "review",
        "approve-experiment",
        "reject",
        "retract",
    } and (not args.proposal_id or not args.revision):
        parser.error("consequential actions require --proposal-id and --revision")
    if args.action in {"review", "approve-experiment"} and not args.confirm:
        parser.error("review actions require --confirm")
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
