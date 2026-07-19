"""Inspect and operate the governed Strategy Evolution Graph."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.services.strategy_service import StrategyService
from cognitive_os.config.strategy_config import StrategyConfiguration
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.skills import SkillProblemSignature
from cognitive_os.domain.strategies import (
    StrategyActor,
    StrategyApplicabilityInput,
    StrategyComparisonRequest,
    StrategyCreatorType,
    StrategyItem,
    StrategyPromotionDecision,
    StrategyPromotionOutcome,
    StrategyRevision,
    StrategySelectionRequest,
    StrategyStatisticsSnapshot,
    StrategyStatus,
)
from cognitive_os.skills.fixtures import sprint12_verified_skills
from cognitive_os.strategies.engine import (
    StrategyGraphService,
    TargetResolverRegistry,
    build_statistics,
    compare_strategies,
    empty_registry_snapshot,
    instantiate_controller_plan,
    render_graph_dot,
    render_graph_mermaid,
    resolve_skill_bindings,
    select_strategy,
)
from cognitive_os.strategies.fixtures import (
    FIXTURE_TIME,
    load_strategy_definition,
    sprint13_verified_strategies,
)
from cognitive_os.strategies.validation import build_strategy_verification_snapshot


def _json(value: object) -> str:
    return json.dumps(value, default=str, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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


def _actor(args: argparse.Namespace) -> StrategyActor:
    return StrategyActor(
        creator_type=StrategyCreatorType.OPERATOR,
        creator_id=args.actor_id,
    )


def _runtime():
    from cognitive_os.events.catalog import build_default_event_catalog
    from cognitive_os.events.strategy_event_service import StrategyEventService
    from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
    from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
    from cognitive_os.infrastructure.strategies.postgres.repository import (
        PostgresStrategyRepository,
    )

    engine = create_postgres_engine(_database_url())
    repository = PostgresStrategyRepository(engine)
    artifacts = ArtifactService(
        ContentAddressedFilesystem(_artifact_root()),
        PostgresArtifactRepository(engine),
    )
    event_service = StrategyEventService(PostgresEventStore(engine, build_default_event_catalog()))
    return engine, repository, artifacts, StrategyService(repository, events=event_service)


async def _definition(path: Path):
    _, skill_registry, _ = await sprint12_verified_skills()
    skills = {item.identity.canonical_name: revision for item, revision in skill_registry.query()}
    return (*load_strategy_definition(path, skills), skill_registry)


async def _database_command(args: argparse.Namespace) -> int:
    if args.action in {"execute", "resume", "cancel", "execution", "outcome"}:
        raise RuntimeError("execution commands require the running application Controller adapter")
    if args.action == "health":
        from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
        from cognitive_os.infrastructure.strategies.postgres.health import (
            PostgresStrategyHealthService,
        )

        engine = create_postgres_engine(_database_url(), pool_size=1, max_overflow=0)
        try:
            report = await PostgresStrategyHealthService(engine).check()
        finally:
            await engine.dispose()
        print(report.model_dump_json())
        return 0 if report.healthy else 1
    engine, repository, artifacts, service = _runtime()
    try:
        if args.action == "create":
            item, draft, edge_set, _, _ = await _definition(args.path)
            actor = _actor(args)
            identity = item.identity.model_copy(update={"created_by": actor})
            draft = StrategyRevision.model_validate(
                {
                    **draft.model_dump(mode="python", exclude={"content_hash"}),
                    "created_by": actor,
                    "reason": args.reason,
                }
            )
            item = StrategyItem(
                identity=identity,
                current_revision=1,
                current_status=StrategyStatus.DRAFT,
                idempotency_key=sha256(
                    f"{identity.canonical_hash()}:{draft.content_hash}".encode()
                ).hexdigest(),
            )
            created = await service.create(item, draft, edge_set)
            print(_json(created.model_dump(mode="json")))
            return 0
        if args.action == "revise":
            _, proposed, edge_set, _, _ = await _definition(args.path)
            revised = await service.revise(
                args.strategy_id,
                proposed,
                edge_set,
                expected_revision=args.expected_revision,
                actor=_actor(args),
                reason=args.reason,
            )
            print(revised.model_dump_json())
            return 0
        if args.action == "history":
            rows = await repository.list_revisions(args.strategy_id, limit=args.limit)
            print(_json([item.model_dump(mode="json") for item in rows]))
            return 0
        if args.action in {"statistics", "rebuild-statistics", "accesses", "usage-report"}:
            accesses = await repository.list_accesses(
                args.strategy_id, args.revision, limit=args.limit
            )
            if args.action == "accesses":
                print(_json([item.model_dump(mode="json") for item in accesses]))
                return 0
            if args.action == "rebuild-statistics":
                outcomes = await repository.list_outcomes(args.strategy_id, args.revision)
                previous = await repository.read_statistics(
                    args.strategy_id, args.revision, args.cohort
                )
                statistics = build_statistics(
                    args.strategy_id,
                    args.revision,
                    outcomes,
                    cohort_id=args.cohort,
                    projection_revision=(previous.projection_revision + 1 if previous else 1),
                )
                await repository.write_statistics(statistics)
                print(statistics.model_dump_json())
                return 0
            statistics = await repository.read_statistics(
                args.strategy_id, args.revision, args.cohort
            )
            payload = (
                statistics.model_dump(mode="json")
                if statistics is not None
                else {
                    "strategy_id": str(args.strategy_id),
                    "revision": args.revision,
                    "cohort_id": args.cohort,
                }
            )
            if args.action == "usage-report":
                payload["access_count"] = len(accesses)
                payload["access_types"] = sorted({item.access_type.value for item in accesses})
            print(_json(payload))
            return 0
        current = await repository.get_current(args.strategy_id)
        if current is None or current[1].revision != args.expected_revision:
            raise RuntimeError("strategy revision is stale or unavailable")
        if args.action == "verify":
            revision = current[1]
            edge_set = await repository.read_edge_set(revision.strategy_id, revision.revision)
            targets = TargetResolverRegistry()
            for edge in edge_set.edges:
                targets.register(edge.target)
            targets.freeze()
            _, skill_registry, _ = await sprint12_verified_skills()
            verification = build_strategy_verification_snapshot(
                revision, edge_set, targets, skill_registry
            )
            if not verification.passed:
                raise RuntimeError("strategy verification did not pass")
            verifier_bundle = await artifacts.put_bytes(
                verification.model_dump_json().encode(), media_type="application/json"
            )
            regression = await artifacts.put_bytes(
                revision.regression_profile.encode(), media_type="application/json"
            )
            promotion = StrategyPromotionDecision(
                decision_id=uuid5(
                    NAMESPACE_URL, f"strategy-promotion:{verification.canonical_hash()}"
                ),
                strategy_id=revision.strategy_id,
                revision=revision.revision,
                outcome=StrategyPromotionOutcome.VERIFY,
                verifier_bundle=verifier_bundle,
                regression_summary=regression,
                decided_by=_actor(args),
                reason_codes=("all_required_verifiers_passed",),
                decided_at=revision.created_at,
            )
            promoted = await service.transition(
                args.strategy_id,
                StrategyStatus.VERIFIED,
                expected_revision=args.expected_revision,
                actor=_actor(args),
                reason=args.reason,
                verification=verification,
                promotion=promotion,
            )
            print(
                _json(
                    {
                        "revision": promoted.model_dump(mode="json"),
                        "verification": verification.model_dump(mode="json"),
                        "promotion": promotion.model_dump(mode="json"),
                    }
                )
            )
            return 0
        status = {
            "stage": StrategyStatus.STAGED,
            "deprecate": StrategyStatus.DEPRECATED,
            "supersede": StrategyStatus.SUPERSEDED,
            "retract": StrategyStatus.RETRACTED,
        }[args.action]
        revision = await service.transition(
            args.strategy_id,
            status,
            expected_revision=args.expected_revision,
            actor=_actor(args),
            reason=args.reason,
        )
        print(revision.model_dump_json())
        return 0
    finally:
        await engine.dispose()


async def _fixture_command(args: argparse.Namespace) -> int:
    _repository, registry, problems, targets, _ = await sprint13_verified_strategies()
    rows = registry.query()
    if args.action == "registry":
        print(
            _json(
                {
                    "healthy": True,
                    "verified_strategies": len(rows),
                    "strategy_registry_hash": registry.snapshot_hash(),
                    "problem_class_registry_hash": problems.snapshot_hash(),
                    "target_resolver_registry_hash": targets.snapshot_hash(),
                    "prohibited_options_enabled": False,
                }
            )
        )
        return 0
    matches = [row for row in rows if row[0].identity.canonical_name == args.strategy]
    if not matches:
        raise SystemExit(f"unknown verified strategy: {args.strategy}")
    item, revision = matches[0]
    if args.action == "inspect":
        print(revision.model_dump_json())
        return 0
    snapshot = empty_registry_snapshot(
        registry.snapshot_hash(), problems.snapshot_hash(), targets.snapshot_hash()
    )
    if args.action in {"graph", "neighbours", "lineage", "export-graph"}:
        graph = StrategyGraphService(registry, targets, StrategyConfiguration()).snapshot(
            revision.strategy_id, revision.revision, snapshot, depth=args.depth
        )
        if args.format == "dot":
            print(render_graph_dot(graph), end="")
        elif args.format == "mermaid":
            print(render_graph_mermaid(graph), end="")
        else:
            print(graph.model_dump_json())
        return 0
    if args.action == "compare":
        right = next(
            (row[1] for row in rows if row[0].identity.canonical_name == args.right_strategy),
            None,
        )
        if right is None:
            raise SystemExit(f"unknown verified strategy: {args.right_strategy}")
        request = StrategyComparisonRequest(
            comparison_id=uuid5(
                NAMESPACE_URL,
                f"strategy-compare:{revision.content_hash}:{right.content_hash}:{args.cohort}",
            ),
            left_strategy_id=revision.strategy_id,
            left_revision=revision.revision,
            right_strategy_id=right.strategy_id,
            right_revision=right.revision,
            cohort_id=args.cohort,
            created_at=FIXTURE_TIME,
        )
        print(compare_strategies(request, revision, right).model_dump_json())
        return 0
    applicability = StrategyApplicabilityInput(
        problem_class_id=item.identity.problem_class_id,
        problem_signature=SkillProblemSignature(
            problem_domain=item.identity.problem_class_id.split(".")[0]
        ),
        repository_profile="cognitive-os",
        scope=item.identity.scope,
        sensitivity_limit=MemorySensitivity.RESTRICTED,
        available_skill_bindings=frozenset(
            binding.binding_id for binding in revision.skill_bindings
        ),
        available_tool_capabilities=frozenset(
            requirement.capability_id
            for phase in revision.phases
            for requirement in phase.tool_requirements
        ),
        available_verifier_capabilities=frozenset(
            requirement.capability_id
            for phase in revision.phases
            for requirement in phase.verifier_requirements
        ),
        available_model_roles=frozenset(
            binding.role_id for binding in revision.model_role_bindings
        ),
        available_context_profiles=frozenset(
            profile.profile_id for profile in revision.context_profiles
        ),
        permissions=frozenset(
            requirement.permission
            for phase in revision.phases
            for requirement in phase.tool_requirements + phase.verifier_requirements
            if requirement.permission
        ),
    )
    request = StrategySelectionRequest(
        selection_id=uuid5(NAMESPACE_URL, f"strategy-cli:{args.strategy}"),
        task_run_id=uuid5(NAMESPACE_URL, f"strategy-cli-task:{args.strategy}"),
        problem_reference=uuid5(NAMESPACE_URL, f"strategy-cli-problem:{args.strategy}"),
        applicability_input=applicability,
        registry_snapshot=snapshot,
        controller_budget=revision.budget_profile,
        approval_granted=args.approve,
        created_at=FIXTURE_TIME,
    )
    decision = select_strategy(
        request, registry, StrategyStatisticsSnapshot(statistics=()), StrategyConfiguration()
    )
    if args.action in {"applicable", "select", "explain-selection"}:
        print(decision.model_dump_json())
        return 0
    _, skills, _ = await sprint12_verified_skills()
    resolved = resolve_skill_bindings(revision, skills)
    plan = instantiate_controller_plan(request, decision, revision, resolved)
    print(plan.model_dump_json())
    return 0


async def _run(args: argparse.Namespace) -> int:
    database_actions = {
        "create",
        "revise",
        "stage",
        "verify",
        "deprecate",
        "supersede",
        "retract",
        "history",
        "statistics",
        "rebuild-statistics",
        "accesses",
        "usage-report",
        "health",
        "execute",
        "resume",
        "cancel",
        "execution",
        "outcome",
    }
    return (
        await _database_command(args)
        if args.action in database_actions
        else await _fixture_command(args)
    )


def _identity(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("strategy_id", type=UUID)
    parser.add_argument("--expected-revision", type=int, required=True)
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--reason", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    create = commands.add_parser("create")
    create.add_argument("path", type=Path)
    create.add_argument("--actor-id", required=True)
    create.add_argument("--reason", required=True)
    revise = commands.add_parser("revise")
    _identity(revise)
    revise.add_argument("path", type=Path)
    for name in ("stage", "verify", "deprecate", "supersede", "retract"):
        _identity(commands.add_parser(name))
    history = commands.add_parser("history")
    history.add_argument("strategy_id", type=UUID)
    history.add_argument("--limit", type=int, default=100)
    for name in ("statistics", "rebuild-statistics", "accesses", "usage-report"):
        command = commands.add_parser(name)
        command.add_argument("strategy_id", type=UUID)
        command.add_argument("revision", type=int)
        command.add_argument("--cohort", default="all")
        command.add_argument("--limit", type=int, default=200)
    commands.add_parser("health")
    for name in ("execute", "resume", "cancel", "execution", "outcome"):
        command = commands.add_parser(name)
        command.add_argument("execution_id", type=UUID)
    for name in (
        "registry",
        "inspect",
        "applicable",
        "select",
        "explain-selection",
        "graph",
        "neighbours",
        "lineage",
        "compare",
        "export-graph",
        "plan",
    ):
        command = commands.add_parser(name)
        command.add_argument("--strategy", default="python-bug-fix")
        command.add_argument("--right-strategy", default="missing-implementation")
        command.add_argument("--depth", type=int, default=3)
        command.add_argument("--cohort", default="all")
        command.add_argument("--format", choices=("json", "dot", "mermaid"), default="json")
        command.add_argument("--approve", action="store_true")
    return parser


def main() -> int:
    return asyncio.run(_run(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
