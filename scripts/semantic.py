"""Operate the governed temporal semantic-memory plane with deterministic JSON I/O."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.config.provider_config import (
    MiniMaxProviderConfig,
    load_provider_configuration,
)
from cognitive_os.config.semantic_memory_config import (
    SemanticMemoryConfiguration,
    load_semantic_memory_configuration,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import MemoryScope, MemoryScopeType, MemorySensitivity
from cognitive_os.domain.semantic_memory import (
    ClaimRelation,
    ClaimRevision,
    ClaimRevisionReference,
    ContradictionResolution,
    ContradictionRevision,
    EvidenceLink,
    ObservationQuery,
    SemanticActor,
    SemanticActorType,
    SemanticExtractionProposal,
    SemanticExtractionRequest,
    SemanticObservation,
    SemanticSourceType,
    TemporalClaimQuery,
    TemporalQueryMode,
    WikiPage,
)
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.provider_event_service import (
    ProviderArtifactService,
    ProviderEventService,
)
from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
from cognitive_os.events.verifier_event_service import VerifierEventService
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.memory.postgres.repository import PostgresMemoryRepository
from cognitive_os.infrastructure.postgres.artifact_repository import PostgresArtifactRepository
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.infrastructure.semantic_memory.postgres.repository import (
    PostgresSemanticMemoryRepository,
)
from cognitive_os.providers.claude_code.advisory import ClaudeCodeAdvisoryProvider
from cognitive_os.providers.minimax.client import MiniMaxProvider
from cognitive_os.providers.registry import ProviderRegistry
from cognitive_os.semantic_memory.compilation import SemanticExtractionService
from cognitive_os.semantic_memory.extraction import extract_typed_memory
from cognitive_os.semantic_memory.graph import bounded_neighbours
from cognitive_os.semantic_memory.grounding import TrustedSourceResolver
from cognitive_os.semantic_memory.predicates import build_default_predicate_registry
from cognitive_os.semantic_memory.promotion import SemanticPromotionGate
from cognitive_os.semantic_memory.provider_extraction import ProviderSemanticExtractionService
from cognitive_os.semantic_memory.service import SemanticMemoryService
from cognitive_os.verification.factory import build_builtin_registry

EVIDENCE = TypeAdapter(tuple[EvidenceLink, ...])


@dataclass(frozen=True)
class Runtime:
    engine: AsyncEngine
    repository: PostgresSemanticMemoryRepository
    memory: PostgresMemoryRepository
    resolver: TrustedSourceResolver
    service: SemanticMemoryService
    events: SemanticMemoryEventService
    promotion: SemanticPromotionGate
    event_store: PostgresEventStore


def _json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(value: Any) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, tuple):
        value = [item.model_dump(mode="json") for item in value]
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _scope(args: argparse.Namespace) -> MemoryScope:
    return MemoryScope(scope_type=MemoryScopeType(args.scope_type), scope_id=args.scope_id)


def _configuration(args: argparse.Namespace) -> SemanticMemoryConfiguration:
    return (
        load_semantic_memory_configuration(args.config)
        if args.config
        else SemanticMemoryConfiguration()
    )


def _runtime(args: argparse.Namespace) -> Runtime:
    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required")
    engine = create_postgres_engine(database_url, pool_size=2, max_overflow=0)
    memory = PostgresMemoryRepository(engine)
    repository = PostgresSemanticMemoryRepository(engine)
    resolver = TrustedSourceResolver(memory)
    event_store = PostgresEventStore(engine, build_default_event_catalog())
    events = SemanticMemoryEventService(event_store)
    service = SemanticMemoryService(
        repository,
        build_default_predicate_registry(),
        _configuration(args),
        event_service=events,
        source_resolver=resolver,
    )
    verifier_registry = build_builtin_registry()
    promotion = SemanticPromotionGate(
        service,
        VerificationService(verifier_registry, VerifierEventService(event_store)),
        verifier_registry,
        events,
    )
    return Runtime(
        engine,
        repository,
        memory,
        resolver,
        service,
        events,
        promotion,
        event_store,
    )


async def _query(runtime: Runtime, args: argparse.Namespace) -> None:
    mode = TemporalQueryMode(args.mode)
    query = TemporalClaimQuery(
        query_id=uuid4(),
        mode=mode,
        scopes=(_scope(args),),
        subject_key=args.subject,
        predicate_id=args.predicate,
        sensitivity_ceiling=MemorySensitivity(args.sensitivity),
        valid_at=datetime.fromisoformat(args.valid_at) if args.valid_at else None,
        known_at=datetime.fromisoformat(args.known_at) if args.known_at else None,
        budget={"maximum_results": args.limit},
    )
    _dump(await runtime.service.query_claims(query))


async def _provider_proposal(runtime: Runtime, args: argparse.Namespace) -> None:
    if not args.enable_provider_extraction:
        raise ValueError("provider extraction requires --enable-provider-extraction")
    artifact_root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not artifact_root:
        raise RuntimeError("COGOS_ARTIFACT_ROOT is required for provider extraction audit")
    provider_configuration = load_provider_configuration(args.provider_config)
    provider_id = args.provider_id or provider_configuration.default_provider_id
    provider_config = provider_configuration.providers.get(provider_id)
    if provider_config is None or not provider_config.enabled:
        raise ValueError("selected semantic extraction provider is not enabled")
    provider = (
        MiniMaxProvider(provider_config)
        if isinstance(provider_config, MiniMaxProviderConfig)
        else ClaudeCodeAdvisoryProvider(provider_config)
    )
    artifacts = ArtifactService(
        ContentAddressedFilesystem(Path(artifact_root)),
        PostgresArtifactRepository(runtime.engine),
    )
    model_execution = ModelExecutionService(
        ProviderRegistry((provider,)),
        default_provider_id=provider_id,
        event_service=ProviderEventService(runtime.event_store),
        artifact_service=ProviderArtifactService(artifacts),
    )
    request = SemanticExtractionRequest.model_validate(_json_file(args.request_input))
    resolver = TrustedSourceResolver(
        runtime.memory,
        artifacts=artifacts,
        events=runtime.event_store,
        maximum_excerpt_bytes=runtime.service.configuration.maximum_source_excerpt_bytes,
    )
    try:
        proposal = await ProviderSemanticExtractionService(
            model_execution,
            runtime.service,
            build_default_predicate_registry(),
            resolver,
            events=runtime.events,
        ).propose(
            request,
            task_run_id=args.task_run_id,
            requested_model=args.model,
            provider_id=provider_id,
        )
    finally:
        if isinstance(provider, MiniMaxProvider):
            await provider.close()
    _dump(proposal)


async def _execute(runtime: Runtime, args: argparse.Namespace) -> None:
    repository = runtime.repository
    command = (args.group, getattr(args, "action", None))
    if command == ("observation", "create"):
        observation = SemanticObservation.model_validate(_json_file(args.input))
        for span in observation.source_spans:
            await runtime.resolver.validate_span(
                span,
                scope=observation.scope,
                sensitivity=observation.sensitivity,
            )
        _dump(
            {"dry_run": True, "observation": observation.model_dump(mode="json")}
            if args.dry_run
            else await runtime.service.record_observation(observation)
        )
    elif command == ("observation", "get"):
        _dump(await repository.get_observation(args.observation_id))
    elif command == ("observation", "list"):
        _dump(
            await runtime.service.query_observations(
                ObservationQuery(
                    query_id=uuid4(),
                    source_type=(
                        SemanticSourceType(args.source_type) if args.source_type else None
                    ),
                    source_id=args.source_id,
                    source_revision=args.source_revision,
                    scopes=(_scope(args),),
                    sensitivity_ceiling=MemorySensitivity(args.sensitivity),
                    maximum_results=args.limit,
                    requested_at=utc_now(),
                    requested_by=SemanticActor(
                        actor_type=SemanticActorType.OPERATOR,
                        actor_id="semantic-cli",
                    ),
                )
            )
        )
    elif command == ("observation", "sources"):
        observation = await repository.get_observation(args.observation_id)
        _dump(observation.source_spans if observation else ())
    elif args.group == "extract-memory":
        record = await runtime.memory.get_current(args.memory_id)
        revision = await runtime.memory.get_revision(args.memory_id, args.revision)
        if record is None or revision is None:
            raise ValueError("memory source revision does not exist")
        registry = build_default_predicate_registry()
        proposal = extract_typed_memory(record[0], revision, registry)
        if not args.commit:
            _dump(proposal)
        else:
            manifest = await SemanticExtractionService(runtime.service, registry).commit(
                proposal,
                scope=record[0].scope,
                sensitivity=record[0].sensitivity,
                actor=SemanticActor(
                    actor_type=SemanticActorType.APPROVED_INTERNAL_SERVICE,
                    actor_id=args.actor,
                ),
                recorded_at=revision.created_at,
            )
            _dump(manifest)
    elif args.group == "extract-provider":
        await _provider_proposal(runtime, args)
    elif args.group == "commit-provider-proposal":
        proposal = SemanticExtractionProposal.model_validate(_json_file(args.proposal_input))
        manifest = await SemanticExtractionService(
            runtime.service,
            build_default_predicate_registry(),
            events=runtime.events,
        ).commit(
            proposal,
            scope=_scope(args),
            sensitivity=MemorySensitivity(args.sensitivity),
            actor=SemanticActor(
                actor_type=SemanticActorType.APPROVED_INTERNAL_SERVICE,
                actor_id=args.actor,
            ),
            recorded_at=datetime.fromisoformat(args.recorded_at),
            provider_origin=True,
        )
        _dump(manifest)
    elif args.group in {"extract-artifact", "extract-trajectory"}:
        raise ValueError(
            "this source has no deterministic extractor; provider extraction is disabled"
        )
    elif args.group == "extraction-report":
        _dump(
            await runtime.service.query_observations(
                ObservationQuery(
                    query_id=uuid4(),
                    source_id=args.source_id,
                    scopes=(_scope(args),),
                    maximum_results=args.limit,
                    requested_at=utc_now(),
                    requested_by=SemanticActor(
                        actor_type=SemanticActorType.OPERATOR,
                        actor_id="semantic-cli",
                    ),
                )
            )
        )
    elif command == ("claim", "get"):
        _dump(await repository.get_claim(args.claim_id))
    elif command == ("claim", "history"):
        _dump(await repository.list_claim_history(args.claim_id, limit=args.limit))
    elif args.group == "timeline":
        claim_history = await repository.list_claim_history(args.claim_id, limit=args.limit)
        contradiction_history = []
        for contradiction in await repository.list_contradictions():
            history = await repository.list_contradiction_history(contradiction.contradiction_id)
            if any(
                reference.claim_id == args.claim_id for item in history for reference in item.claims
            ):
                contradiction_history.extend(history)
        _dump(
            {
                "claim_revisions": [item.model_dump(mode="json") for item in claim_history],
                "evidence": [
                    item.model_dump(mode="json")
                    for revision in claim_history
                    for item in await repository.list_evidence(
                        args.claim_id, revision=revision.revision
                    )
                ],
                "relations": [
                    item.model_dump(mode="json")
                    for item in await repository.list_claim_relations(args.claim_id)
                ],
                "contradictions": [item.model_dump(mode="json") for item in contradiction_history],
            }
        )
    elif args.group == "claim" and args.action in {
        "promote",
        "dispute",
        "supersede",
        "retract",
    }:
        revision = ClaimRevision.model_validate(_json_file(args.revision_input))
        if args.action == "supersede":
            if args.relation_input is None:
                raise ValueError("claim supersede requires --relation-input")
            await runtime.service.add_claim_relation(
                ClaimRelation.model_validate(_json_file(args.relation_input))
            )
        evidence = (
            EVIDENCE.validate_python(_json_file(args.evidence_input)) if args.evidence_input else ()
        )
        decision = None
        if args.action == "promote":
            decision = await runtime.promotion.decide(
                revision,
                evidence,
                task_run_id=args.task_run_id,
                actor=SemanticActor(
                    actor_type=SemanticActorType.OPERATOR,
                    actor_id=args.actor,
                ),
            )
            revision = revision.model_copy(update={"promotion_decision_id": decision.decision_id})
        _dump(
            await runtime.service.transition_claim(
                revision,
                expected_revision=args.expected_revision,
                decision=decision,
                evidence=evidence,
            )
        )
    elif command == ("evidence", "list"):
        _dump(await repository.list_evidence(args.claim_id, revision=args.revision))
    elif command == ("evidence", "validate"):
        _dump(await runtime.service.reevaluate_evidence(args.claim_id, revision=args.revision))
    elif command == ("contradiction", "list"):
        _dump(await repository.list_contradictions())
    elif command == ("contradiction", "inspect"):
        _dump(await repository.list_contradiction_history(args.contradiction_id))
    elif args.group == "contradiction" and args.action in {"resolve", "reopen"}:
        revision = ContradictionRevision.model_validate(_json_file(args.revision_input))
        resolution = (
            ContradictionResolution.model_validate(_json_file(args.resolution_input))
            if args.resolution_input
            else None
        )
        _dump(
            await runtime.service.transition_contradiction(
                revision,
                expected_revision=args.expected_revision,
                resolution=resolution,
            )
        )
    elif args.group in {"query", "query-current", "query-valid-at", "query-known-at"}:
        if args.group != "query":
            args.mode = args.group.removeprefix("query-").replace("-", "_")
        await _query(runtime, args)
    elif args.group == "graph-neighbours":
        relations = await repository.list_claim_relations(args.claim_id)
        start = {"claim_id": args.claim_id, "revision": args.revision}
        _dump(
            bounded_neighbours(
                relations,
                ClaimRevisionReference.model_validate(start),
                maximum_depth=args.depth,
                maximum_nodes=args.nodes,
                maximum_edges=args.edges,
            )
        )
    elif args.group == "wiki":
        await _wiki(runtime, args)
    else:
        raise ValueError("unsupported semantic command")


async def _wiki(runtime: Runtime, args: argparse.Namespace) -> None:
    repository = runtime.repository
    if args.action == "get":
        page = await repository.get_wiki_page(args.page_id)
        _dump(
            await repository.get_wiki_revision(args.page_id, page.current_revision)
            if page
            else None
        )
        return
    if args.action == "history":
        _dump(await repository.list_wiki_history(args.page_id))
        return
    if args.action == "verify":
        _dump(
            {
                "valid": await runtime.service.verify_wiki_revision(args.page_id, args.revision),
                "page_id": str(args.page_id),
                "revision": args.revision,
            }
        )
        return
    page = WikiPage(
        page_id=args.page_id,
        scope=_scope(args),
        canonical_subject_key=args.subject,
        page_type=args.page_type,
        domain=args.domain,
        current_revision=args.expected_revision,
        created_at=datetime.fromisoformat(args.created_at),
    )
    mode = (
        TemporalQueryMode.BITEMPORAL
        if args.valid_at and args.known_at
        else (
            TemporalQueryMode.VALID_AT
            if args.valid_at
            else (TemporalQueryMode.KNOWN_AT if args.known_at else TemporalQueryMode.CURRENT)
        )
    )
    query = TemporalClaimQuery(
        query_id=uuid4(),
        mode=mode,
        scopes=(page.scope,),
        subject_key=page.canonical_subject_key,
        valid_at=datetime.fromisoformat(args.valid_at) if args.valid_at else None,
        known_at=datetime.fromisoformat(args.known_at) if args.known_at else None,
    )
    _dump(await runtime.service.render_wiki(page, query, expected_revision=args.expected_revision))


def _scope_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scope-type", choices=[item.value for item in MemoryScopeType], required=True
    )
    parser.add_argument("--scope-id", required=True)


def _query_arguments(parser: argparse.ArgumentParser) -> None:
    _scope_arguments(parser)
    parser.add_argument("--subject")
    parser.add_argument("--predicate")
    parser.add_argument("--valid-at")
    parser.add_argument("--known-at")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument(
        "--sensitivity",
        choices=[item.value for item in MemorySensitivity],
        default="internal",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    groups = parser.add_subparsers(dest="group", required=True)
    observation = groups.add_parser("observation").add_subparsers(dest="action", required=True)
    create = observation.add_parser("create")
    create.add_argument("--input", type=Path, required=True)
    create.add_argument("--dry-run", action="store_true")
    get = observation.add_parser("get")
    get.add_argument("observation_id", type=UUID)
    listed = observation.add_parser("list")
    listed.add_argument("--source-type", choices=[item.value for item in SemanticSourceType])
    listed.add_argument("--source-id", type=UUID)
    listed.add_argument("--source-revision", type=int)
    listed.add_argument("--limit", type=int, default=100)
    listed.add_argument(
        "--sensitivity",
        choices=[item.value for item in MemorySensitivity],
        default="internal",
    )
    _scope_arguments(listed)
    sources = observation.add_parser("sources")
    sources.add_argument("observation_id", type=UUID)

    extract = groups.add_parser("extract-memory")
    extract.add_argument("memory_id", type=UUID)
    extract.add_argument("--revision", type=int, default=1)
    extract.add_argument("--actor", default="semantic-cli")
    extract.add_argument("--commit", action="store_true")
    provider_extract = groups.add_parser("extract-provider")
    provider_extract.add_argument("--request-input", type=Path, required=True)
    provider_extract.add_argument("--provider-config", type=Path, required=True)
    provider_extract.add_argument("--provider-id")
    provider_extract.add_argument("--model", required=True)
    provider_extract.add_argument("--task-run-id", type=UUID, required=True)
    provider_extract.add_argument("--enable-provider-extraction", action="store_true")
    provider_commit = groups.add_parser("commit-provider-proposal")
    provider_commit.add_argument("--proposal-input", type=Path, required=True)
    provider_commit.add_argument("--recorded-at", required=True)
    provider_commit.add_argument("--actor", default="semantic-cli")
    provider_commit.add_argument(
        "--sensitivity",
        choices=[item.value for item in MemorySensitivity],
        default="internal",
    )
    _scope_arguments(provider_commit)
    groups.add_parser("extract-artifact")
    groups.add_parser("extract-trajectory")
    report = groups.add_parser("extraction-report")
    report.add_argument("--source-id", type=UUID)
    report.add_argument("--limit", type=int, default=100)
    _scope_arguments(report)

    claim = groups.add_parser("claim").add_subparsers(dest="action", required=True)
    for action in ("get", "history"):
        command = claim.add_parser(action)
        command.add_argument("claim_id", type=UUID)
        command.add_argument("--limit", type=int, default=100)
    for action in ("promote", "dispute", "supersede", "retract"):
        command = claim.add_parser(action)
        command.add_argument("--revision-input", type=Path, required=True)
        command.add_argument("--expected-revision", type=int, required=True)
        command.add_argument("--evidence-input", type=Path)
        if action == "promote":
            command.add_argument("--task-run-id", type=UUID, required=True)
            command.add_argument("--actor", default="semantic-cli")
        else:
            command.set_defaults(task_run_id=None, actor=None)
        if action == "supersede":
            command.add_argument("--relation-input", type=Path)
        else:
            command.set_defaults(relation_input=None)

    evidence = groups.add_parser("evidence").add_subparsers(dest="action", required=True)
    for action in ("list", "validate"):
        evidence_command = evidence.add_parser(action)
        evidence_command.add_argument("claim_id", type=UUID)
        evidence_command.add_argument("--revision", type=int)
    contradiction = groups.add_parser("contradiction").add_subparsers(dest="action", required=True)
    contradiction.add_parser("list")
    inspect = contradiction.add_parser("inspect")
    inspect.add_argument("contradiction_id", type=UUID)
    for action in ("resolve", "reopen"):
        command = contradiction.add_parser(action)
        command.add_argument("--revision-input", type=Path, required=True)
        command.add_argument("--expected-revision", type=int, required=True)
        if action == "resolve":
            command.add_argument("--resolution-input", type=Path, required=True)
        else:
            command.set_defaults(resolution_input=None)

    query = groups.add_parser("query")
    query.add_argument("--mode", choices=[item.value for item in TemporalQueryMode], required=True)
    _query_arguments(query)
    for command_name in ("query-current", "query-valid-at", "query-known-at"):
        _query_arguments(groups.add_parser(command_name))
    timeline = groups.add_parser("timeline")
    timeline.add_argument("claim_id", type=UUID)
    timeline.add_argument("--limit", type=int, default=100)
    graph = groups.add_parser("graph-neighbours")
    graph.add_argument("claim_id", type=UUID)
    graph.add_argument("--revision", type=int, required=True)
    graph.add_argument("--depth", type=int, default=2)
    graph.add_argument("--nodes", type=int, default=100)
    graph.add_argument("--edges", type=int, default=200)

    wiki = groups.add_parser("wiki").add_subparsers(dest="action", required=True)
    for action in ("get", "history"):
        command = wiki.add_parser(action)
        command.add_argument("page_id", type=UUID)
    verify = wiki.add_parser("verify")
    verify.add_argument("page_id", type=UUID)
    verify.add_argument("--revision", type=int, required=True)
    for action in ("render", "render-as-of", "regenerate"):
        command = wiki.add_parser(action)
        command.add_argument("page_id", type=UUID)
        command.add_argument("--expected-revision", type=int, required=True)
        command.add_argument("--subject", required=True)
        command.add_argument("--page-type", default="subject")
        command.add_argument("--domain")
        command.add_argument("--created-at", required=True)
        command.add_argument("--valid-at")
        command.add_argument("--known-at")
        _scope_arguments(command)
    return parser


async def _run(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    try:
        await _execute(runtime, args)
        return 0
    finally:
        await runtime.engine.dispose()


def main() -> int:
    return asyncio.run(_run(_build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
