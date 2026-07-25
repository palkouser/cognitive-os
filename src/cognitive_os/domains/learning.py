"""Feed governed cross-domain runs into the learning plane.

No learning component is re-implemented here. The Experience Compiler, the Memory
Plane, semantic extraction, and the Corpus Factory already exist and already own
their policies; this module only translates the audit trail a governed domain run
leaves behind into the inputs those services accept.

Every timeline entry is derived from a real recorded event — its identity, its
timestamps, its actor, and its payload hash. Nothing is synthesised: if the
Controller never emitted an event, no entry exists for it, and a run whose
evidence is incomplete compiles as incomplete rather than being padded.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.services.experience_compiler import (
    ExperienceCompilerService,
)
from cognitive_os.application.services.memory_service import MemoryService
from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.corpus.factory import CorpusFactory
from cognitive_os.corpus.fixtures import FixtureArtifactStore
from cognitive_os.corpus.repository import InMemoryCorpusRepository
from cognitive_os.corpus.sources import InspectedSource, inspect_experience_candidate
from cognitive_os.domain.common import Sha256Hex
from cognitive_os.domain.corpus import (
    CorpusFactoryRequest,
    CorpusFactoryResult,
    CorpusUsageRight,
)
from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.domain.experience import (
    CompilerProfile,
    CompilerResourceLimits,
    ExperienceCandidate,
    ExperienceCandidateType,
    ExperienceCompilationRequest,
    ExperienceStepStatus,
    TimelineEntry,
    TimelineEntryType,
    TrajectorySourceRef,
    TrajectorySourceType,
)
from cognitive_os.domain.memory import (
    MemoryCreator,
    MemoryCreatorType,
    MemoryProvenanceBundle,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemorySourceIdentity,
    MemorySourceRef,
    MemorySourceType,
    MemoryType,
    MemoryWritePolicy,
    MemoryWriteRequest,
    TaskSummaryMemoryContent,
    VerificationSummaryMemoryContent,
)
from cognitive_os.domain.semantic_memory import (
    SemanticActor,
    SemanticActorType,
    SemanticExtractionManifest,
)
from cognitive_os.events.base import EventEnvelope
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.experience.compiler import (
    ExperienceCompilationResult,
    ExperienceCompiler,
)
from cognitive_os.experience.registry import (
    CompilerProfileRegistry,
    ResolvedTrajectorySource,
    SourceResolverRegistry,
)
from cognitive_os.experience.repository import InMemoryExperienceRepository
from cognitive_os.memory.repository import InMemoryMemoryRepository
from cognitive_os.semantic_memory.compilation import SemanticExtractionService
from cognitive_os.semantic_memory.extraction import extract_typed_memory
from cognitive_os.semantic_memory.grounding import TrustedSourceResolver
from cognitive_os.semantic_memory.predicates import build_default_predicate_registry
from cognitive_os.semantic_memory.repository import InMemorySemanticMemoryRepository
from cognitive_os.semantic_memory.service import SemanticMemoryService

DOMAIN_SCOPE = "project:cognitive-os"
COMPILER_PROFILE_ID = "sprint20-domain"
ACCEPTANCE_EVENT = "controller.acceptance_decision_recorded"

#: Which recorded stream a governed domain run's events belong to. The map is
#: total over what the Controller and Tool Plane actually emit; an event outside
#: it is a real gap in this table, so it raises instead of being filed as
#: `unknown` and quietly averaged into the evidence.
_SOURCE_TYPES: dict[str, TrajectorySourceType] = {
    "controller": TrajectorySourceType.CONTROLLER_EVENT,
    "problem": TrajectorySourceType.CONTROLLER_EVENT,
    "plan": TrajectorySourceType.CONTROLLER_EVENT,
    "execution_step": TrajectorySourceType.CONTROLLER_EVENT,
    "tool_call": TrajectorySourceType.TOOL_CALL,
    "verifier": TrajectorySourceType.VERIFIER,
}

_ENTRY_TYPES: dict[str, TimelineEntryType] = {
    "controller": TimelineEntryType.CONTROLLER,
    "problem": TimelineEntryType.CONTROLLER,
    "plan": TimelineEntryType.PLAN,
    "execution_step": TimelineEntryType.CONTROLLER,
    "tool_call": TimelineEntryType.TOOL,
    "verifier": TimelineEntryType.VERIFIER,
}

_VERIFIER_STATUSES: dict[str, ExperienceStepStatus] = {
    "passed": ExperienceStepStatus.COMPLETED,
    "failed": ExperienceStepStatus.FAILED,
    "unverifiable": ExperienceStepStatus.UNKNOWN,
    "error": ExperienceStepStatus.FAILED,
    "timed_out": ExperienceStepStatus.FAILED,
    "skipped": ExperienceStepStatus.SKIPPED,
}


class DomainLearningError(RuntimeError):
    """Raised when a run's recorded evidence cannot back a learning input."""


def _digest(value: object) -> str:
    return sha256(
        json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _prefix(event_type: str) -> str:
    return event_type.split(".", 1)[0]


def _source_type(envelope: EventEnvelope) -> TrajectorySourceType:
    if envelope.event_type == ACCEPTANCE_EVENT:
        return TrajectorySourceType.ACCEPTANCE
    try:
        return _SOURCE_TYPES[_prefix(envelope.event_type)]
    except KeyError as error:
        raise DomainLearningError(
            f"no trajectory source is declared for event {envelope.event_type}"
        ) from error


def _entry_type(envelope: EventEnvelope) -> TimelineEntryType:
    if envelope.event_type == ACCEPTANCE_EVENT:
        return TimelineEntryType.ACCEPTANCE
    return _ENTRY_TYPES[_prefix(envelope.event_type)]


def _status(envelope: EventEnvelope) -> ExperienceStepStatus:
    """Read the outcome out of the payload, never off the event name alone.

    `verifier.completed` says the verifier ran, not that it passed. Deriving the
    step status from the name would record every failed verification as a
    completed step, which is precisely the evidence the compiler is meant to see.
    """
    event_type = envelope.event_type
    if event_type == ACCEPTANCE_EVENT:
        decision = _mapping(envelope.payload, "decision")
        return (
            ExperienceStepStatus.COMPLETED
            if decision.get("decision") == "accepted"
            else ExperienceStepStatus.FAILED
        )
    if event_type == "verifier.completed":
        status = str(_mapping(envelope.payload, "result").get("status", ""))
        return _VERIFIER_STATUSES.get(status, ExperienceStepStatus.UNKNOWN)
    if "denied" in event_type or "policy_violation" in event_type:
        return ExperienceStepStatus.DENIED
    if "failed" in event_type or "rejected" in event_type:
        return ExperienceStepStatus.FAILED
    if "cancelled" in event_type:
        return ExperienceStepStatus.CANCELLED
    if event_type.endswith(".started"):
        return ExperienceStepStatus.STARTED
    return ExperienceStepStatus.COMPLETED


def _mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise DomainLearningError(f"event payload is missing the {key} record")
    return value


def terminal_acceptance_decision(store: MemoryEventStore) -> dict[str, Any]:
    """The last recorded acceptance decision, read back from the event stream.

    A run that repairs records one decision per cycle. The terminal state is the
    last of them; the earlier ones stay in the timeline as the failed branch that
    justified the repair, which is the part worth learning from.
    """
    decisions = [
        _mapping(item.envelope.payload, "decision")
        for item in store.stored_events()
        if item.envelope.event_type == ACCEPTANCE_EVENT
    ]
    if not decisions:
        raise DomainLearningError("a governed run records at least one acceptance decision")
    return decisions[-1]


@dataclass(frozen=True, slots=True)
class _Group:
    """One trajectory source: the events of one recorded stream slice."""

    source_type: TrajectorySourceType
    ordinal: int
    stream_id: UUID
    events: tuple[tuple[int, EventEnvelope], ...]

    @property
    def source_id(self) -> str:
        return f"{self.source_type.value}:{self.ordinal}"

    @property
    def revision(self) -> str:
        return str(max(envelope.stream_version for _, envelope in self.events))

    @property
    def payload(self) -> bytes:
        return json.dumps(
            [envelope.model_dump(mode="json") for _, envelope in self.events],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()


def _group(store: MemoryEventStore) -> tuple[_Group, ...]:
    """Split the recorded events into per-source groups, in recorded order.

    The acceptance decision is its own source even though it shares the task-run
    stream with the Controller's events: it is the authority the compiler treats
    as terminal, and folding it into the Controller source would hide it. No
    event lands in two groups and none is dropped, so the sequence stays gapless.
    """
    ordered = store.stored_events()
    buckets: dict[tuple[TrajectorySourceType, UUID], list[tuple[int, EventEnvelope]]] = {}
    for item in ordered:
        key = (_source_type(item.envelope), item.envelope.stream_id)
        buckets.setdefault(key, []).append((item.global_position, item.envelope))
    ordinals: dict[TrajectorySourceType, int] = {}
    groups: list[_Group] = []
    for (source_type, stream_id), events in buckets.items():
        ordinals[source_type] = ordinals.get(source_type, 0) + 1
        groups.append(_Group(source_type, ordinals[source_type], stream_id, tuple(events)))
    return tuple(groups)


def _entry(reference: TrajectorySourceRef, sequence: int, envelope: EventEnvelope) -> TimelineEntry:
    return TimelineEntry(
        timeline_entry_id=envelope.event_id,
        sequence=sequence,
        source_ref=reference,
        entry_type=_entry_type(envelope),
        event_type=envelope.event_type,
        actor_type=envelope.actor.actor_type.value,
        actor_id=envelope.actor.actor_id,
        started_at=envelope.occurred_at,
        finished_at=envelope.recorded_at,
        causation_id=envelope.causation_event_id,
        correlation_id=envelope.correlation_id,
        status=_status(envelope),
        payload_summary=f"{envelope.source_component}: {envelope.event_type}",
        evidence_refs=(envelope.payload_hash,),
    )


def build_compilation(
    case: DomainBenchmarkCase, store: MemoryEventStore
) -> tuple[ExperienceCompilationRequest, SourceResolverRegistry, CompilerProfileRegistry]:
    """Turn one governed run's recorded events into a compilation request."""
    groups = _group(store)
    if not groups:
        raise DomainLearningError("a governed run must record events before it can be compiled")
    decision = terminal_acceptance_decision(store)
    terminal_state = str(decision.get("decision"))
    task_run_id = UUID(str(decision["task_run_id"]))

    case_payload = case.canonical_json().encode()
    task_ref = TrajectorySourceRef(
        source_type=TrajectorySourceType.TASK,
        source_id=f"domain-case:{case.case_id}",
        source_revision=case.licence_and_source.revision,
        source_content_hash=sha256(case_payload).hexdigest(),
        scope=DOMAIN_SCOPE,
        sensitivity=MemorySensitivity.INTERNAL,
    )
    resolved: list[ResolvedTrajectorySource] = [ResolvedTrajectorySource(task_ref, case_payload)]
    for group in groups:
        is_stream = group.source_type is not TrajectorySourceType.ACCEPTANCE
        reference = TrajectorySourceRef(
            source_type=group.source_type,
            source_id=group.source_id,
            source_revision=group.revision,
            # A whole recorded stream declares its identity and version; the
            # acceptance projection is one event of a stream another source
            # already declares, so it does not restate the stream identity.
            event_stream_id=group.stream_id if is_stream else None,
            event_stream_version=int(group.revision) if is_stream else None,
            source_content_hash=sha256(group.payload).hexdigest(),
            scope=DOMAIN_SCOPE,
            sensitivity=MemorySensitivity.INTERNAL,
        )
        entries = tuple(
            _entry(reference, sequence, envelope) for sequence, envelope in group.events
        )
        resolved.append(
            ResolvedTrajectorySource(
                reference,
                group.payload,
                entries,
                terminal_state if group.source_type is TrajectorySourceType.ACCEPTANCE else None,
            )
        )

    sources = SourceResolverRegistry()
    for item in resolved:
        sources.register(item)
    sources.freeze()
    refs = tuple(item.reference for item in resolved)
    supplied = frozenset(item.source_type for item in refs)
    created_at = min(envelope.occurred_at for group in groups for _, envelope in group.events)
    profile = CompilerProfile(
        profile_id=COMPILER_PROFILE_ID,
        version=1,
        enabled_source_types=supplied,
        required_source_types=frozenset(
            {
                TrajectorySourceType.TASK,
                TrajectorySourceType.CONTROLLER_EVENT,
                TrajectorySourceType.VERIFIER,
                TrajectorySourceType.ACCEPTANCE,
            }
        ),
        candidate_types=frozenset(ExperienceCandidateType),
        assessment_policy="conservative-evidence-v1",
        contribution_policy="no-causal-overclaim-v1",
        generalizability_policy="minimum-specificity-v1",
        resource_limits=CompilerResourceLimits(),
        created_at=created_at,
    )
    profiles = CompilerProfileRegistry()
    profiles.register(profile)
    profiles.freeze()

    # Compilation identity follows the evidence, not the clock: two runs that
    # recorded the same events compile once, and a run that recorded anything
    # different is a different trajectory and gets its own compilation.
    trajectory_digest = _digest([f"{item.source_content_hash}:{item.source_id}" for item in refs])
    request = ExperienceCompilationRequest(
        compilation_id=uuid5(NAMESPACE_URL, f"domain-compilation:{trajectory_digest}"),
        task_run_id=task_run_id,
        trajectory_sources=refs,
        compiler_profile_id=profile.profile_id,
        compiler_profile_version=profile.version,
        compiler_profile_hash=profile.content_hash,
        candidate_types=frozenset(ExperienceCandidateType),
        budget=CompilerResourceLimits(),
        requested_by="domain-pilot",
        idempotency_key=trajectory_digest,
        created_at=created_at,
    )
    return request, sources, profiles


async def compile_run(
    case: DomainBenchmarkCase,
    store: MemoryEventStore,
    *,
    repository: InMemoryExperienceRepository | None = None,
) -> ExperienceCompilationResult:
    """Compile one governed domain run through the existing Experience Compiler."""
    request, sources, profiles = build_compilation(case, store)
    service = ExperienceCompilerService(
        ExperienceCompiler(sources, profiles),
        repository or InMemoryExperienceRepository(),
    )
    return await service.compile(request)


def _verifier_results(
    store: MemoryEventStore,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Passed, failed, and errored verifier identities as recorded."""
    passed: list[str] = []
    failed: list[str] = []
    errors: list[str] = []
    for item in store.stored_events():
        if item.envelope.event_type != "verifier.completed":
            continue
        result = _mapping(item.envelope.payload, "result")
        identity = f"{result['verifier_id']}@{result['verifier_version']}"
        status = str(result.get("status"))
        if status == "passed":
            passed.append(identity)
        elif status == "failed":
            failed.append(identity)
        else:
            errors.append(identity)
    # Identities, not a call log: a repaired run calls the same verifier once per
    # cycle. A verifier that passed in one cycle and failed in another correctly
    # appears in both lists.
    return (
        tuple(dict.fromkeys(passed)),
        tuple(dict.fromkeys(failed)),
        tuple(dict.fromkeys(errors)),
    )


def project_run(
    case: DomainBenchmarkCase,
    store: MemoryEventStore,
    registry_snapshot_hash: Sha256Hex,
) -> tuple[TaskSummaryMemoryContent, VerificationSummaryMemoryContent]:
    """Project a governed run into the two typed memory contents it evidences.

    Only these two are produced. Both already have a registered deterministic
    semantic extractor, so everything written to the Memory Plane can be grounded
    onward; a content type with no extractor would be a memory that the semantic
    layer can never read, which is worse than not writing it.
    """
    decision = terminal_acceptance_decision(store)
    task_run_id = UUID(str(decision["task_run_id"]))
    passed, failed, errors = _verifier_results(store)
    outcome = str(decision["decision"])
    return (
        TaskSummaryMemoryContent(
            task_run_id=task_run_id,
            goal=case.problem.statement[:8192],
            constraints=tuple(case.problem.constraints + case.forbidden_operations)[:64],
            result=(
                f"{case.domain.value} {case.problem_type} case {case.case_id} "
                f"{outcome} under Controller and Tool Plane authority"
            )[:8192],
            review_status=outcome,
        ),
        VerificationSummaryMemoryContent(
            task_run_id=task_run_id,
            required_passed=passed,
            required_failed=failed,
            verifier_errors=errors,
            acceptance_decision_id=UUID(str(decision["decision_id"])),
            registry_snapshot_hash=registry_snapshot_hash,
        ),
    )


def _provenance(case: DomainBenchmarkCase, decision: dict[str, Any]) -> MemoryProvenanceBundle:
    decision_id = UUID(str(decision["decision_id"]))
    task_run_id = UUID(str(decision["task_run_id"]))
    sources = (
        MemorySourceRef(
            identity=MemorySourceIdentity(
                source_type=MemorySourceType.ACCEPTANCE_DECISION,
                source_id=decision_id,
                content_hash=_digest(decision),
            ),
            source_hash=_digest(decision),
        ),
        MemorySourceRef(
            identity=MemorySourceIdentity(
                source_type=MemorySourceType.TASK_RUN, source_id=task_run_id
            ),
            source_hash=sha256(str(task_run_id).encode()).hexdigest(),
        ),
        MemorySourceRef(
            identity=MemorySourceIdentity(
                source_type=MemorySourceType.VERIFIER_RESULT,
                source_id=uuid5(NAMESPACE_URL, f"domain-case:{case.case_id}"),
                content_hash=case.content_hash,
            ),
            source_hash=case.content_hash,
        ),
    )
    return MemoryProvenanceBundle(
        sources=tuple(sorted(sources, key=lambda source: source.identity.sort_key()))
    )


def domain_memory_policy() -> MemoryWritePolicy:
    """Least privilege: the two projected types, domain and task scopes only."""
    return MemoryWritePolicy(
        allowed_types=frozenset({MemoryType.TASK_SUMMARY, MemoryType.VERIFICATION_SUMMARY}),
        allowed_scopes=frozenset({MemoryScopeType.DOMAIN, MemoryScopeType.TASK}),
        maximum_sensitivity=MemorySensitivity.INTERNAL,
        allow_automatic_request=True,
    )


def corpus_request(
    case: DomainBenchmarkCase, candidate: ExperienceCandidate
) -> tuple[CorpusFactoryRequest, InspectedSource]:
    """Declare one experience candidate to the Corpus Factory.

    The licence and the redistribution right come from the case's own
    `ProvenanceRef` — the declaration made when the fixture was authored — and
    nowhere else. Training and commercial use are left undeclared rather than
    assumed, because nothing in this repository grants them.
    """
    provenance = case.licence_and_source
    rights: dict[CorpusUsageRight, bool | None] = {
        CorpusUsageRight.INTERNAL_USE: True,
        CorpusUsageRight.BENCHMARK_USE: True,
        CorpusUsageRight.MODIFICATION: True,
        CorpusUsageRight.DERIVATIVE_WORK: True,
        CorpusUsageRight.REDISTRIBUTION: provenance.redistributable,
        CorpusUsageRight.PUBLIC_RELEASE: provenance.redistributable,
        CorpusUsageRight.MODEL_TRAINING: None,
        CorpusUsageRight.COMMERCIAL_USE: None,
    }
    source = inspect_experience_candidate(
        candidate,
        source_revision=str(candidate.candidate_revision),
        config=CorpusConfiguration(),
    )
    return (
        CorpusFactoryRequest(
            request_id=uuid5(NAMESPACE_URL, f"domain-corpus:{candidate.candidate_id}"),
            source_type=source.source_type,
            source_identity=source.source_identity,
            source_revision=source.source_revision,
            scope=candidate.scope,
            sensitivity=candidate.sensitivity,
            license_identifiers=(provenance.licence,),
            usage_rights=rights,
            created_at=candidate.created_at,
            created_by="domain-pilot",
        ),
        source,
    )


@dataclass(frozen=True, slots=True)
class DomainLearningResult:
    """What one governed run contributed to each learning-plane component."""

    compilation: ExperienceCompilationResult
    memory_ids: tuple[UUID, ...]
    semantic_manifests: tuple[SemanticExtractionManifest, ...]
    corpus_candidates: tuple[ExperienceCandidate, ...]
    corpus_results: tuple[CorpusFactoryResult, ...] = ()

    @property
    def corpus_item_count(self) -> int:
        return sum(len(item.items) for item in self.corpus_results)

    @property
    def candidate_types(self) -> tuple[ExperienceCandidateType, ...]:
        return tuple(item.candidate_type for item in self.compilation.candidates)

    @property
    def observation_count(self) -> int:
        return sum(len(item.observation_ids) for item in self.semantic_manifests)

    @property
    def claim_count(self) -> int:
        return sum(len(item.claims) for item in self.semantic_manifests)


async def ingest_run(
    case: DomainBenchmarkCase,
    store: MemoryEventStore,
    *,
    registry_snapshot_hash: Sha256Hex,
    memory_repository: InMemoryMemoryRepository | None = None,
    semantic_repository: InMemorySemanticMemoryRepository | None = None,
    recorded_at: datetime | None = None,
) -> DomainLearningResult:
    """Run one governed domain trajectory through the whole learning plane.

    Experience Compiler, then Memory Plane, then semantic extraction, then the
    Corpus Factory. The corpus declaration carries only the rights the case's
    own `ProvenanceRef` grants; training and commercial use stay undeclared, and
    the factory — not this module — decides what those declarations permit.
    """
    from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration

    compilation = await compile_run(case, store)
    decision = terminal_acceptance_decision(store)
    contents = project_run(case, store, registry_snapshot_hash)
    provenance = _provenance(case, decision)
    when = recorded_at or max(item.envelope.recorded_at for item in store.stored_events())

    memory_repository = memory_repository or InMemoryMemoryRepository()
    memory_service = MemoryService(memory_repository, domain_memory_policy())
    scope = MemoryScope(scope_type=MemoryScopeType.DOMAIN, scope_id=case.domain.value)
    written: list[tuple[UUID, Any, Any]] = []
    for content in contents:
        memory_id = uuid5(
            NAMESPACE_URL,
            f"domain-memory:{compilation.snapshot.content_hash}:{content.memory_type.value}",
        )
        request = MemoryWriteRequest(
            request_id=uuid5(NAMESPACE_URL, f"domain-memory-request:{memory_id}"),
            idempotency_key=sha256(
                f"{compilation.manifest.compilation_id}:{memory_id}".encode()
            ).hexdigest(),
            memory_id=memory_id,
            memory_type=content.memory_type,
            scope=scope,
            title=content.render_search_text().splitlines()[0][:1024],
            content=content,
            confidence=1.0,
            salience=0.5,
            sensitivity=MemorySensitivity.INTERNAL,
            provenance=provenance,
            actor=MemoryCreator(
                creator_type=MemoryCreatorType.INGESTION_SERVICE,
                creator_id="domain-pilot-ingestion-v1",
            ),
            automatic=True,
        )
        _, created = await memory_service.create(request)
        if created is None:
            raise DomainLearningError("memory write returned no revision")
        written.append((memory_id, created[0], created[1]))

    predicates = build_default_predicate_registry()
    semantic = SemanticMemoryService(
        semantic_repository or InMemorySemanticMemoryRepository(),
        predicates,
        SemanticMemoryConfiguration(),
        source_resolver=TrustedSourceResolver(memory_repository),
    )
    extraction = SemanticExtractionService(semantic, predicates)
    actor = SemanticActor(
        actor_type=SemanticActorType.APPROVED_INTERNAL_SERVICE,
        actor_id="domain-pilot-extractor",
    )
    manifests = [
        await extraction.commit(
            extract_typed_memory(record, revision, predicates),
            scope=scope,
            sensitivity=MemorySensitivity.INTERNAL,
            actor=actor,
            recorded_at=when,
        )
        for _memory_id, record, revision in written
    ]

    corpus = tuple(
        item for item in compilation.candidates if item.target_subsystem == "corpus-factory"
    )
    factory = CorpusFactory(InMemoryCorpusRepository(), FixtureArtifactStore())
    corpus_results = tuple(
        [await factory.ingest(*corpus_request(case, candidate)) for candidate in corpus]
    )
    return DomainLearningResult(
        compilation=compilation,
        memory_ids=tuple(memory_id for memory_id, _record, _revision in written),
        semantic_manifests=tuple(manifests),
        corpus_candidates=corpus,
        corpus_results=corpus_results,
    )


async def run_case_with_learning(
    case: DomainBenchmarkCase, *, candidate_override: Any | None = None
) -> tuple[Any, DomainLearningResult]:
    """Execute one case under governance, then compile and ingest what it left."""
    from cognitive_os.domains.runner import run_case_controlled
    from cognitive_os.verification.factory import build_builtin_registry

    store = MemoryEventStore()
    run = await run_case_controlled(case, candidate_override=candidate_override, store=store)
    result = await ingest_run(
        case, store, registry_snapshot_hash=build_builtin_registry().snapshot()
    )
    return run, result
