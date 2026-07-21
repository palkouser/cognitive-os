"""Credential-free deterministic fixtures for Sprint 17."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.application.ports.weakness_miner import (
    WeaknessSignalExtractorPort,
    WeaknessSourceResolverPort,
)
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.routing import TaskComplexityClass
from cognitive_os.domain.weakness import (
    CausalRelationshipType,
    MiningProfile,
    MiningRequest,
    MiningSourceReference,
    MiningSourceSnapshot,
    SignalSourceType,
    WeaknessComponentType,
    WeaknessConfidenceLevel,
    WeaknessSeverity,
    WeaknessSignal,
    WeaknessType,
)
from cognitive_os.routing.service import build_task_signature

FIXTURE_TIME = datetime(2026, 7, 22, 8, 0, tzinfo=UTC)

_SOURCE_BY_TYPE = {
    WeaknessType.MODEL_ROUTING_FAILURE: SignalSourceType.ROUTING_OUTCOME,
    WeaknessType.TOOL_ROUTING_FAILURE: SignalSourceType.TOOL,
    WeaknessType.PROVIDER_STRUCTURED_OUTPUT_FAILURE: SignalSourceType.PROVIDER_RESULT,
    WeaknessType.PROVIDER_AVAILABILITY_FAILURE: SignalSourceType.PROVIDER_RESULT,
    WeaknessType.CONTEXT_REQUIRED_ITEM_MISSING: SignalSourceType.CONTEXT,
    WeaknessType.CONTEXT_IRRELEVANT_CONTENT: SignalSourceType.CONTEXT,
    WeaknessType.CONTEXT_BUDGET_FAILURE: SignalSourceType.CONTEXT,
    WeaknessType.RETRIEVAL_RECALL_FAILURE: SignalSourceType.RETRIEVAL,
    WeaknessType.RETRIEVAL_SCOPE_OR_SENSITIVITY_DENIAL: SignalSourceType.RETRIEVAL,
    WeaknessType.MISSING_SKILL: SignalSourceType.SKILL,
    WeaknessType.SKILL_PRECONDITION_FAILURE: SignalSourceType.SKILL,
    WeaknessType.SKILL_EXECUTION_FAILURE: SignalSourceType.SKILL,
    WeaknessType.STRATEGY_MISMATCH: SignalSourceType.STRATEGY,
    WeaknessType.STRATEGY_FALLBACK_OVERUSE: SignalSourceType.STRATEGY,
    WeaknessType.VERIFIER_GAP: SignalSourceType.VERIFIER,
    WeaknessType.VERIFIER_INSTABILITY: SignalSourceType.VERIFIER,
    WeaknessType.MEMORY_RETRIEVAL_FAILURE: SignalSourceType.MEMORY,
    WeaknessType.SEMANTIC_CONTRADICTION_BLOCK: SignalSourceType.SEMANTIC,
    WeaknessType.CORPUS_COVERAGE_GAP: SignalSourceType.CORPUS,
    WeaknessType.EXCESSIVE_REPAIR: SignalSourceType.CONTROLLER,
    WeaknessType.EXCESSIVE_ITERATION: SignalSourceType.CONTROLLER,
    WeaknessType.UNNECESSARY_PROVIDER_CALL: SignalSourceType.PROVIDER_REQUEST,
    WeaknessType.UNNECESSARY_TOOL_CALL: SignalSourceType.TOOL,
    WeaknessType.COST_REGRESSION: SignalSourceType.BENCHMARK,
    WeaknessType.LATENCY_REGRESSION: SignalSourceType.BENCHMARK,
    WeaknessType.POLICY_DENIAL_PATTERN: SignalSourceType.CONTROLLER,
    WeaknessType.SANDBOX_FAILURE: SignalSourceType.TOOL,
    WeaknessType.USER_CORRECTION_PATTERN: SignalSourceType.USER_CORRECTION,
    WeaknessType.UNKNOWN: SignalSourceType.ACCEPTANCE,
}

_COMPONENT_BY_SOURCE = {
    SignalSourceType.CONTROLLER: WeaknessComponentType.CONTROLLER,
    SignalSourceType.ACCEPTANCE: WeaknessComponentType.VERIFIER,
    SignalSourceType.VERIFIER: WeaknessComponentType.VERIFIER,
    SignalSourceType.USER_CORRECTION: WeaknessComponentType.CONTROLLER,
    SignalSourceType.CONTEXT: WeaknessComponentType.CONTEXT,
    SignalSourceType.RETRIEVAL: WeaknessComponentType.RETRIEVAL,
    SignalSourceType.PROVIDER_REQUEST: WeaknessComponentType.PROVIDER,
    SignalSourceType.PROVIDER_RESULT: WeaknessComponentType.PROVIDER,
    SignalSourceType.TOOL: WeaknessComponentType.TOOL,
    SignalSourceType.MEMORY: WeaknessComponentType.MEMORY,
    SignalSourceType.SEMANTIC: WeaknessComponentType.SEMANTIC_MEMORY,
    SignalSourceType.SKILL: WeaknessComponentType.SKILL,
    SignalSourceType.STRATEGY: WeaknessComponentType.STRATEGY,
    SignalSourceType.EXPERIENCE: WeaknessComponentType.EXPERIENCE,
    SignalSourceType.CORPUS: WeaknessComponentType.CORPUS,
    SignalSourceType.ROUTING_DECISION: WeaknessComponentType.ROUTING,
    SignalSourceType.ROUTING_OUTCOME: WeaknessComponentType.ROUTING,
    SignalSourceType.ROUTING_SHADOW: WeaknessComponentType.ROUTING,
    SignalSourceType.BENCHMARK: WeaknessComponentType.VERIFIER,
    SignalSourceType.ARTIFACT: WeaknessComponentType.UNKNOWN,
}


def fixture_sources(case_count: int = 72) -> tuple[MiningSourceReference, ...]:
    weakness_types = tuple(WeaknessType)
    sources = []
    for index in range(case_count):
        weakness_type = weakness_types[index % len(weakness_types)]
        case_id = f"{weakness_type.value}:{index}"
        source_type = _SOURCE_BY_TYPE[weakness_type]
        sources.append(_source(source_type, f"fixture:{case_id}", weakness_type.value))
        if source_type is not SignalSourceType.ACCEPTANCE:
            sources.append(
                _source(
                    SignalSourceType.ACCEPTANCE,
                    f"authority:{case_id}",
                    "accepted-authoritative-record",
                )
            )
    return tuple(sources)


def _source(source_type: SignalSourceType, source_id: str, revision: str) -> MiningSourceReference:
    return MiningSourceReference(
        source_type=source_type,
        source_id=source_id,
        source_revision=revision,
        event_stream_id=uuid5(NAMESPACE_URL, f"weakness-stream:{source_id}"),
        event_stream_version=1,
        source_content_hash=sha256(
            f"{source_type.value}:{source_id}:{revision}".encode()
        ).hexdigest(),
        scope="repository:cognitive-os",
        sensitivity=MemorySensitivity.INTERNAL,
        required=True,
        authoritative=True,
        outcome_authority=source_type
        in {SignalSourceType.ACCEPTANCE, SignalSourceType.ROUTING_OUTCOME},
    )


class FixtureSourceResolver(WeaknessSourceResolverPort):
    def __init__(
        self, source_type: SignalSourceType, sources: tuple[MiningSourceReference, ...]
    ) -> None:
        self._source_type = source_type
        self._sources = tuple(item for item in sources if item.source_type is source_type)

    @property
    def source_type(self) -> SignalSourceType:
        return self._source_type

    @property
    def descriptor(self) -> str:
        return f"fixture-{self._source_type.value}-resolver-v1"

    async def discover(self, request: MiningRequest) -> tuple[MiningSourceReference, ...]:
        return self._sources

    async def resolve(self, source: MiningSourceReference) -> MiningSourceReference:
        if source not in self._sources:
            raise LookupError("fixture source unavailable")
        return source

    async def health_check(self) -> bool:
        return True


class FixtureSignalExtractor(WeaknessSignalExtractorPort):
    @property
    def descriptor(self) -> str:
        return "authoritative-fixture-extractor-v1"

    @property
    def supported_types(self) -> frozenset[WeaknessType]:
        return frozenset(WeaknessType)

    async def extract(
        self, snapshot: MiningSourceSnapshot, profile: MiningProfile
    ) -> tuple[WeaknessSignal, ...]:
        by_id = {item.source_id: item for item in snapshot.source_refs}
        signals = []
        for source in snapshot.source_refs:
            if not source.source_id.startswith("fixture:"):
                continue
            _, weakness_name, index_text = source.source_id.split(":")
            weakness_type = WeaknessType(weakness_name)
            index = int(index_text)
            authority = by_id.get(f"authority:{weakness_name}:{index}")
            source_refs = (source,) if authority is None else (source, authority)
            component = _COMPONENT_BY_SOURCE[source.source_type]
            critical = weakness_type is WeaknessType.SANDBOX_FAILURE
            signals.append(
                WeaknessSignal(
                    signal_id=uuid5(NAMESPACE_URL, f"weakness-signal:{source.source_id}"),
                    mining_run_id=snapshot.mining_run_id,
                    weakness_type=weakness_type,
                    task_run_id=uuid5(NAMESPACE_URL, f"weakness-task:{index}"),
                    source_refs=source_refs,
                    task_signature=build_task_signature(
                        problem_domain="coding",
                        problem_class=weakness_type.value,
                        output_type="diagnostic",
                        estimated_complexity=TaskComplexityClass.MEDIUM,
                        risk_level="critical" if critical else "standard",
                    ),
                    failure_code=weakness_type.value,
                    component_type=component,
                    component_identity=f"fixture-{component.value}",
                    verifier_reference="fixture-verifier-v1",
                    severity=(WeaknessSeverity.CRITICAL if critical else WeaknessSeverity.HIGH),
                    confidence=WeaknessConfidenceLevel.VERIFIED,
                    causal_relationship=CausalRelationshipType.UNKNOWN_CAUSAL_RELATIONSHIP,
                    observed_at=FIXTURE_TIME,
                    extractor_profile=self.descriptor,
                    limitations=("Fixture correlation does not establish causality.",),
                )
            )
        return tuple(signals)

    async def health_check(self) -> bool:
        return True


def fixture_profile(
    sources: tuple[MiningSourceReference, ...],
) -> MiningProfile:
    return MiningProfile(
        profile_id="weakness-fixture-profile",
        version=1,
        enabled_source_types=tuple(sorted({item.source_type for item in sources}, key=str)),
        enabled_extractors=("authoritative-fixture-extractor-v1",),
        signature_profile="weakness-signature-v1",
        grouping_profile="exact-signature-v1",
        clustering_profile="no-op-v1",
        impact_profile="weakness-impact-default-v1",
        confirmation_policy="explicit-confirmation-v1",
        queue_policy="deterministic-priority-v1",
        resource_limits={"signals": 100_000, "sources": 100_000},
        created_at=FIXTURE_TIME,
    )


def fixture_request(profile: MiningProfile, case_count: int = 72) -> MiningRequest:
    return MiningRequest(
        mining_run_id=uuid5(NAMESPACE_URL, f"weakness-mining-run:{case_count}"),
        scope="repository:cognitive-os",
        source_filters=profile.enabled_source_types,
        mining_profile_hash=profile.content_hash,
        requested_by="fixture-operator",
        idempotency_key=f"sprint17-fixture-{case_count}",
        created_at=FIXTURE_TIME,
    )
