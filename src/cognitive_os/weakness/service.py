"""Deterministic source validation, grouping, scoring, lifecycle, and queue service."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.weakness_miner import (
    WeaknessSignalExtractorPort,
    WeaknessSourceResolverPort,
)
from cognitive_os.application.ports.weakness_repository import WeaknessRepositoryPort
from cognitive_os.config.weakness_config import WeaknessConfiguration
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.weakness import (
    ImpactDimension,
    ImpactDimensionResult,
    ImpactProfileReference,
    ImpactScore,
    ImpactUncertainty,
    MiningProfile,
    MiningRequest,
    MiningRunManifest,
    MiningRunResult,
    MiningRunStatus,
    MiningRunSummary,
    MiningSourceSnapshot,
    NextAnalysisType,
    QueueBlockerType,
    SignalSourceType,
    WeaknessAccessRecord,
    WeaknessAccessType,
    WeaknessCluster,
    WeaknessClusterComparison,
    WeaknessClusterMember,
    WeaknessClusterMethod,
    WeaknessClusterSnapshot,
    WeaknessCounterexample,
    WeaknessEvidencePackage,
    WeaknessGroup,
    WeaknessGroupMember,
    WeaknessGroupSnapshot,
    WeaknessIdentity,
    WeaknessPriority,
    WeaknessQueueDependency,
    WeaknessQueueEntry,
    WeaknessQueueSnapshot,
    WeaknessQueueStatus,
    WeaknessReproductionAssessment,
    WeaknessReproductionStatus,
    WeaknessRevision,
    WeaknessSeverity,
    WeaknessSignal,
    WeaknessSignature,
    WeaknessStatus,
    WeaknessType,
)

from .errors import (
    WeaknessAuthorityError,
    WeaknessLifecycleError,
    WeaknessSourceError,
)

_Q = Decimal("0.0001")
_PRIORITY_ORDER = {
    WeaknessPriority.CRITICAL: 0,
    WeaknessPriority.HIGH: 1,
    WeaknessPriority.MEDIUM: 2,
    WeaknessPriority.LOW: 3,
    WeaknessPriority.INFORMATIONAL: 4,
}
_SEVERITY = {
    WeaknessSeverity.INFORMATIONAL: Decimal("0.1"),
    WeaknessSeverity.LOW: Decimal("0.25"),
    WeaknessSeverity.MEDIUM: Decimal("0.5"),
    WeaknessSeverity.HIGH: Decimal("0.75"),
    WeaknessSeverity.CRITICAL: Decimal("1"),
}
_LEGAL_TRANSITIONS = {
    WeaknessStatus.CANDIDATE: {
        WeaknessStatus.CANDIDATE,
        WeaknessStatus.CONFIRMED,
        WeaknessStatus.RETRACTED,
        WeaknessStatus.SUPERSEDED,
    },
    WeaknessStatus.CONFIRMED: {
        WeaknessStatus.CONFIRMED,
        WeaknessStatus.MONITORING,
        WeaknessStatus.RESOLVED,
        WeaknessStatus.SUPERSEDED,
        WeaknessStatus.RETRACTED,
    },
    WeaknessStatus.MONITORING: {
        WeaknessStatus.MONITORING,
        WeaknessStatus.CONFIRMED,
        WeaknessStatus.RESOLVED,
        WeaknessStatus.SUPERSEDED,
        WeaknessStatus.RETRACTED,
    },
    WeaknessStatus.RESOLVED: {
        WeaknessStatus.MONITORING,
        WeaknessStatus.SUPERSEDED,
        WeaknessStatus.RETRACTED,
    },
    WeaknessStatus.SUPERSEDED: {WeaknessStatus.RETRACTED},
    WeaknessStatus.RETRACTED: set(),
}


def _hash(values: Iterable[str]) -> str:
    return sha256("\n".join(values).encode()).hexdigest()


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_Q, rounding=ROUND_HALF_EVEN)


class SourceResolverRegistry:
    def __init__(self) -> None:
        self._items: dict[SignalSourceType, WeaknessSourceResolverPort] = {}
        self._frozen = False

    def register(self, resolver: WeaknessSourceResolverPort) -> None:
        if self._frozen:
            raise WeaknessSourceError("source resolver registry is frozen")
        if resolver.source_type in self._items:
            raise WeaknessSourceError("duplicate source resolver")
        self._items[resolver.source_type] = resolver

    def freeze(self) -> None:
        self._frozen = True

    def resolve(self, source_type: SignalSourceType) -> WeaknessSourceResolverPort:
        try:
            return self._items[source_type]
        except KeyError as error:
            raise WeaknessSourceError(f"source resolver unavailable: {source_type}") from error

    @property
    def snapshot_hash(self) -> str:
        return _hash(
            f"{kind.value}:{resolver.descriptor}"
            for kind, resolver in sorted(self._items.items(), key=lambda item: item[0].value)
        )


class SignalExtractorRegistry:
    def __init__(self) -> None:
        self._items: dict[str, WeaknessSignalExtractorPort] = {}
        self._frozen = False

    def register(self, extractor: WeaknessSignalExtractorPort) -> None:
        if self._frozen:
            raise WeaknessAuthorityError("signal extractor registry is frozen")
        if extractor.descriptor in self._items:
            raise WeaknessAuthorityError("duplicate signal extractor")
        self._items[extractor.descriptor] = extractor

    def freeze(self) -> None:
        self._frozen = True

    def enabled(self, names: tuple[str, ...]) -> tuple[WeaknessSignalExtractorPort, ...]:
        missing = set(names) - self._items.keys()
        if missing:
            raise WeaknessAuthorityError(f"signal extractor unavailable: {sorted(missing)}")
        return tuple(self._items[name] for name in sorted(names))

    @property
    def snapshot_hash(self) -> str:
        return _hash(
            f"{name}:{','.join(sorted(item.value for item in extractor.supported_types))}"
            for name, extractor in sorted(self._items.items())
        )


class FailureCodeRegistry:
    def __init__(self) -> None:
        self._codes = {item: frozenset({item.value}) for item in WeaknessType}
        self._frozen = True

    def normalize(self, weakness_type: WeaknessType, code: str) -> str:
        normalized = code.strip().lower().replace("-", "_")
        if normalized not in self._codes[weakness_type]:
            return "unknown"
        return normalized

    @property
    def snapshot_hash(self) -> str:
        return _hash(
            f"{kind.value}:{','.join(sorted(codes))}"
            for kind, codes in sorted(self._codes.items(), key=lambda item: item[0].value)
        )


def default_impact_profile() -> ImpactProfileReference:
    weights = {
        ImpactDimension.FREQUENCY: Decimal("0.08"),
        ImpactDimension.AFFECTED_TASK_COUNT: Decimal("0.08"),
        ImpactDimension.SEVERITY: Decimal("0.12"),
        ImpactDimension.SAFETY_IMPACT: Decimal("0.20"),
        ImpactDimension.CORRECTNESS_IMPACT: Decimal("0.18"),
        ImpactDimension.USER_CORRECTION_COUNT: Decimal("0.06"),
        ImpactDimension.COST_IMPACT: Decimal("0.05"),
        ImpactDimension.LATENCY_IMPACT: Decimal("0.04"),
        ImpactDimension.REPAIR_ITERATION_IMPACT: Decimal("0.05"),
        ImpactDimension.RECENCY: Decimal("0.04"),
        ImpactDimension.REPRODUCIBILITY: Decimal("0.05"),
        ImpactDimension.EVIDENCE_CONFIDENCE: Decimal("0.03"),
        ImpactDimension.STRATEGIC_REACH: Decimal("0.02"),
    }
    return ImpactProfileReference(
        profile_id="weakness-impact-default",
        version=1,
        weights=weights,
        critical_safety_priority_floor=Decimal("90"),
        high_correctness_priority_floor=Decimal("75"),
    )


@dataclass(frozen=True)
class ImpactFacts:
    counterexample_count: int = 0
    user_correction_count: int = 0
    cost_ratio: Decimal | None = None
    latency_ratio: Decimal | None = None
    repair_iteration_ratio: Decimal = Decimal()
    reproduction_count: int = 0
    evidence_coverage: Decimal = Decimal("1")
    strategic_identity_count: int = 1
    safety_evidence: Decimal = Decimal()
    correctness_evidence: Decimal = Decimal("0.5")


def build_signature(
    signal: WeaknessSignal, registry: FailureCodeRegistry | None = None
) -> WeaknessSignature:
    codes = registry or FailureCodeRegistry()
    return WeaknessSignature(
        weakness_type=signal.weakness_type,
        normalized_problem_signature=signal.task_signature.content_hash,
        normalized_failure_code=codes.normalize(signal.weakness_type, signal.failure_code),
        component_type=signal.component_type,
        component_identity=signal.component_identity,
        skill_identity=signal.skill_revision,
        strategy_identity=signal.strategy_revision,
        provider_identity=(
            signal.component_identity
            if signal.component_type.value in {"provider", "model"}
            else None
        ),
        model_identity=(
            signal.component_identity if signal.component_type.value == "model" else None
        ),
        tool_identity=(
            signal.component_identity if signal.component_type.value == "tool" else None
        ),
        verifier_identity=signal.verifier_reference,
        context_source_type=(
            signal.component_identity if signal.component_type.value == "context" else None
        ),
        retrieval_identity=(
            signal.component_identity if signal.component_type.value == "retrieval" else None
        ),
        routing_policy_identity=(
            str(signal.routing_decision) if signal.routing_decision is not None else None
        ),
        risk_class=signal.task_signature.risk_level,
        scope=signal.source_refs[0].scope,
    )


def build_exact_group_snapshot(
    signals: tuple[WeaknessSignal, ...],
    *,
    profile_hash: str,
    created_at: datetime,
    counterexamples: tuple[WeaknessCounterexample, ...] = (),
) -> WeaknessGroupSnapshot:
    signal_hash = _hash(
        item.content_hash for item in sorted(signals, key=lambda item: str(item.signal_id))
    )
    grouped: dict[str, list[tuple[WeaknessSignal, WeaknessSignature]]] = defaultdict(list)
    for signal in sorted(signals, key=lambda item: str(item.signal_id)):
        signature = build_signature(signal)
        grouped[signature.content_hash].append((signal, signature))
    groups = []
    for signature_hash, items in sorted(grouped.items()):
        signature = items[0][1]
        members = tuple(
            WeaknessGroupMember(
                signal_id=signal.signal_id,
                signal_hash=signal.content_hash,
                task_run_id=signal.task_run_id,
                observed_at=signal.observed_at,
            )
            for signal, _ in items
        )
        related_counterexamples = tuple(
            sorted(
                item.content_hash
                for item in counterexamples
                if item.signature_hash == signature_hash
            )
        )
        groups.append(
            WeaknessGroup(
                group_id=uuid5(
                    NAMESPACE_URL,
                    f"weakness-group:{signature_hash}:{signal_hash}:{profile_hash}",
                ),
                revision=1,
                signature=signature,
                members=members,
                distinct_task_count=len({item.task_run_id for item in members}),
                distinct_component_count=len({signal.component_identity for signal, _ in items}),
                first_seen=min(item.observed_at for item in members),
                last_seen=max(item.observed_at for item in members),
                counterexample_refs=related_counterexamples,
            )
        )
    snapshot_id = uuid5(NAMESPACE_URL, f"weakness-groups:{signal_hash}:{profile_hash}")
    return WeaknessGroupSnapshot(
        snapshot_id=snapshot_id,
        groups=tuple(groups),
        source_signal_hash=signal_hash,
        profile_hash=profile_hash,
        created_at=created_at,
    )


def build_noop_cluster_snapshot(
    groups: WeaknessGroupSnapshot, *, created_at: datetime
) -> WeaknessClusterSnapshot:
    method_hash = sha256(b"weakness-clustering:no-op:v1").hexdigest()
    clusters = tuple(
        WeaknessCluster(
            cluster_id=uuid5(NAMESPACE_URL, f"weakness-cluster:{group.content_hash}"),
            revision=1,
            method=WeaknessClusterMethod.NO_OP,
            method_profile_hash=method_hash,
            members=(
                WeaknessClusterMember(
                    group_id=group.group_id,
                    group_revision=group.revision,
                    group_hash=group.content_hash,
                ),
            ),
            created_at=created_at,
        )
        for group in groups.groups
    )
    return WeaknessClusterSnapshot(
        snapshot_id=uuid5(NAMESPACE_URL, f"weakness-clusters:{groups.content_hash}:no-op"),
        group_snapshot_hash=groups.content_hash,
        method=WeaknessClusterMethod.NO_OP,
        clusters=clusters,
        created_at=created_at,
    )


def compare_clusters(
    left: WeaknessClusterSnapshot, right: WeaknessClusterSnapshot
) -> WeaknessClusterComparison:
    left_groups = {member.group_hash for cluster in left.clusters for member in cluster.members}
    right_groups = {member.group_hash for cluster in right.clusters for member in cluster.members}
    return WeaknessClusterComparison(
        left_snapshot_hash=left.content_hash,
        right_snapshot_hash=right.content_hash,
        added_group_hashes=tuple(sorted(right_groups - left_groups)),
        removed_group_hashes=tuple(sorted(left_groups - right_groups)),
        stable_group_count=len(left_groups & right_groups),
        limitations=("Advisory clusters do not alter exact groups or lifecycle state.",),
    )


def score_impact(
    group: WeaknessGroup,
    *,
    group_snapshot_hash: str,
    facts: ImpactFacts,
    reference_time: datetime,
    profile: ImpactProfileReference | None = None,
) -> ImpactScore:
    selected_profile = profile or default_impact_profile()
    severity = max(_SEVERITY[signal_severity] for signal_severity in _group_severities(group))
    age_days = max(0, (reference_time - group.last_seen).days)
    recency = Decimal("1") if age_days <= 7 else Decimal("0.75")
    if age_days > 30:
        recency = Decimal("0.5")
    if age_days > 90:
        recency = Decimal("0.25")
    counterexample_ratio = Decimal(facts.counterexample_count) / Decimal(
        max(1, len(group.members) + facts.counterexample_count)
    )
    confidence = max(Decimal(), facts.evidence_coverage * (Decimal(1) - counterexample_ratio))
    raw: dict[ImpactDimension, Decimal] = {
        ImpactDimension.FREQUENCY: Decimal(len(group.members)),
        ImpactDimension.AFFECTED_TASK_COUNT: Decimal(group.distinct_task_count),
        ImpactDimension.SEVERITY: severity,
        ImpactDimension.SAFETY_IMPACT: facts.safety_evidence,
        ImpactDimension.CORRECTNESS_IMPACT: facts.correctness_evidence,
        ImpactDimension.USER_CORRECTION_COUNT: Decimal(facts.user_correction_count),
        ImpactDimension.COST_IMPACT: facts.cost_ratio
        if facts.cost_ratio is not None
        else Decimal(-1),
        ImpactDimension.LATENCY_IMPACT: (
            facts.latency_ratio if facts.latency_ratio is not None else Decimal(-1)
        ),
        ImpactDimension.REPAIR_ITERATION_IMPACT: facts.repair_iteration_ratio,
        ImpactDimension.RECENCY: recency,
        ImpactDimension.REPRODUCIBILITY: Decimal(facts.reproduction_count),
        ImpactDimension.EVIDENCE_CONFIDENCE: confidence,
        ImpactDimension.STRATEGIC_REACH: Decimal(facts.strategic_identity_count),
    }
    normalized = {
        ImpactDimension.FREQUENCY: min(Decimal(1), raw[ImpactDimension.FREQUENCY] / 10),
        ImpactDimension.AFFECTED_TASK_COUNT: min(
            Decimal(1), raw[ImpactDimension.AFFECTED_TASK_COUNT] / 10
        ),
        ImpactDimension.SEVERITY: severity,
        ImpactDimension.SAFETY_IMPACT: max(Decimal(), min(Decimal(1), facts.safety_evidence)),
        ImpactDimension.CORRECTNESS_IMPACT: max(
            Decimal(), min(Decimal(1), facts.correctness_evidence)
        ),
        ImpactDimension.USER_CORRECTION_COUNT: min(
            Decimal(1), Decimal(facts.user_correction_count) / 5
        ),
        ImpactDimension.COST_IMPACT: (
            Decimal() if facts.cost_ratio is None else min(Decimal(1), facts.cost_ratio)
        ),
        ImpactDimension.LATENCY_IMPACT: (
            Decimal() if facts.latency_ratio is None else min(Decimal(1), facts.latency_ratio)
        ),
        ImpactDimension.REPAIR_ITERATION_IMPACT: min(Decimal(1), facts.repair_iteration_ratio),
        ImpactDimension.RECENCY: recency,
        ImpactDimension.REPRODUCIBILITY: min(Decimal(1), Decimal(facts.reproduction_count) / 2),
        ImpactDimension.EVIDENCE_CONFIDENCE: confidence,
        ImpactDimension.STRATEGIC_REACH: min(
            Decimal(1), Decimal(facts.strategic_identity_count) / 10
        ),
    }
    source_hashes = tuple(sorted({member.signal_hash for member in group.members}))
    dimensions = tuple(
        ImpactDimensionResult(
            dimension=dimension,
            raw_value=raw[dimension],
            normalized_value=_quantize(normalized[dimension]),
            weight=selected_profile.weights[dimension],
            weighted_value=_quantize(normalized[dimension] * selected_profile.weights[dimension]),
            source_refs=source_hashes,
            sample_count=len(group.members),
            uncertainty=_quantize(Decimal(1) - confidence),
            profile_version=selected_profile.version,
        )
        for dimension in ImpactDimension
    )
    base_score = _quantize(sum((item.weighted_value for item in dimensions), Decimal()) * 100)
    floor = Decimal()
    if facts.safety_evidence >= Decimal("1"):
        floor = selected_profile.critical_safety_priority_floor
    elif facts.correctness_evidence >= Decimal("0.75"):
        floor = selected_profile.high_correctness_priority_floor
    final = max(base_score, floor)
    priority = _priority(final)
    missing = int(facts.cost_ratio is None) + int(facts.latency_ratio is None)
    limitations = tuple(
        name
        for name, value in (
            ("cost evidence unavailable", facts.cost_ratio),
            ("latency evidence unavailable", facts.latency_ratio),
        )
        if value is None
    )
    return ImpactScore(
        impact_score_id=uuid5(
            NAMESPACE_URL,
            f"weakness-impact:{group.content_hash}:{selected_profile.content_hash}",
        ),
        group_snapshot_hash=group_snapshot_hash,
        dimensions=dimensions,
        base_score=base_score,
        priority_floor=floor,
        final_score=final,
        priority=priority,
        uncertainty=ImpactUncertainty(
            value=_quantize(Decimal(1) - confidence),
            missing_source_count=missing,
            conflict_count=0,
            counterexample_count=facts.counterexample_count,
            limitations=limitations,
        ),
        profile=selected_profile,
        created_at=reference_time,
        limitations=limitations,
    )


def _group_severities(group: WeaknessGroup) -> tuple[WeaknessSeverity, ...]:
    severity_by_type = {
        WeaknessType.SANDBOX_FAILURE: WeaknessSeverity.CRITICAL,
        WeaknessType.VERIFIER_GAP: WeaknessSeverity.HIGH,
        WeaknessType.USER_CORRECTION_PATTERN: WeaknessSeverity.HIGH,
        WeaknessType.UNKNOWN: WeaknessSeverity.MEDIUM,
    }
    return (severity_by_type.get(group.signature.weakness_type, WeaknessSeverity.MEDIUM),)


def _priority(score: Decimal) -> WeaknessPriority:
    if score >= 90:
        return WeaknessPriority.CRITICAL
    if score >= 75:
        return WeaknessPriority.HIGH
    if score >= 50:
        return WeaknessPriority.MEDIUM
    if score >= 25:
        return WeaknessPriority.LOW
    return WeaknessPriority.INFORMATIONAL


def build_evidence_package(
    group: WeaknessGroup,
    score: ImpactScore,
    signals: tuple[WeaknessSignal, ...],
    counterexamples: tuple[WeaknessCounterexample, ...],
    *,
    reproduction: WeaknessReproductionAssessment,
) -> WeaknessEvidencePackage:
    source_by_hash = {
        source.content_hash: source
        for signal in signals
        if signal.signal_id in {member.signal_id for member in group.members}
        for source in signal.source_refs
    }
    sources = tuple(source_by_hash[key] for key in sorted(source_by_hash))
    signal_hashes = tuple(member.signal_hash for member in group.members[:8])
    sections = {
        "routing": tuple(
            item.content_hash
            for item in sources
            if item.source_type
            in {SignalSourceType.ROUTING_DECISION, SignalSourceType.ROUTING_OUTCOME}
        ),
        "context": tuple(
            item.content_hash
            for item in sources
            if item.source_type in {SignalSourceType.CONTEXT, SignalSourceType.RETRIEVAL}
        ),
        "skill_strategy": tuple(
            item.content_hash
            for item in sources
            if item.source_type in {SignalSourceType.SKILL, SignalSourceType.STRATEGY}
        ),
        "provider_tool_verifier": tuple(
            item.content_hash
            for item in sources
            if item.source_type
            in {
                SignalSourceType.PROVIDER_REQUEST,
                SignalSourceType.PROVIDER_RESULT,
                SignalSourceType.TOOL,
                SignalSourceType.VERIFIER,
            }
        ),
        "memory_semantic_corpus": tuple(
            item.content_hash
            for item in sources
            if item.source_type
            in {SignalSourceType.MEMORY, SignalSourceType.SEMANTIC, SignalSourceType.CORPUS}
        ),
    }
    checksums = {
        "manifest.json": _hash(item.content_hash for item in sources),
        "group-snapshot.json": group.content_hash,
        "impact.json": score.content_hash,
        "representative-signals.json": _hash(signal_hashes),
        "counterexamples.json": _hash(item.content_hash for item in counterexamples),
        "source-lineage.json": _hash(item.source_content_hash for item in sources),
        "limitations.json": sha256(
            b"Correlation is not causality; this package has no modification authority."
        ).hexdigest(),
    }
    package_id = uuid5(
        NAMESPACE_URL, f"weakness-evidence:{group.content_hash}:{score.content_hash}"
    )
    return WeaknessEvidencePackage(
        evidence_package_id=package_id,
        group_snapshot_hash=group.content_hash,
        source_manifest=sources,
        representative_signal_hashes=signal_hashes,
        complete_source_count=len(sources),
        counterexample_hashes=tuple(sorted(item.content_hash for item in counterexamples)),
        task_refs=tuple(sorted({member.task_run_id for member in group.members}, key=str)),
        event_refs=tuple(
            sorted({item.event_stream_id for item in sources if item.event_stream_id}, key=str)
        ),
        artifact_refs=tuple(
            sorted({item.artifact_id for item in sources if item.artifact_id}, key=str)
        ),
        component_sections=sections,
        reproduction=reproduction,
        sensitivity=max((item.sensitivity for item in sources), key=_sensitivity_rank),
        limitations=(
            "Repeated correlation does not establish causality.",
            "This diagnostic package contains no executable change instruction.",
        ),
        artifact_reference=uuid5(NAMESPACE_URL, f"weakness-artifact:{package_id}"),
        checksums=checksums,
        verification_hash=_hash(checksums.values()),
    )


def _sensitivity_rank(value: MemorySensitivity) -> int:
    return {
        MemorySensitivity.PUBLIC: 0,
        MemorySensitivity.INTERNAL: 1,
        MemorySensitivity.CONFIDENTIAL: 2,
        MemorySensitivity.RESTRICTED: 3,
    }[value]


def build_candidate(
    group: WeaknessGroup,
    score: ImpactScore,
    package: WeaknessEvidencePackage,
    *,
    actor: str,
    created_at: datetime,
    verifier_bundle_hash: str,
) -> tuple[WeaknessIdentity, WeaknessRevision]:
    weakness_id = uuid5(NAMESPACE_URL, f"weakness:{group.signature.content_hash}")
    identity = WeaknessIdentity(
        weakness_id=weakness_id,
        canonical_name=f"{group.signature.weakness_type.value}:{group.signature.component_identity}",
        weakness_type=group.signature.weakness_type,
        signature_hash=group.signature.content_hash,
        scope=group.signature.scope,
        created_at=created_at,
        created_by=actor,
    )
    revision = WeaknessRevision(
        weakness_id=weakness_id,
        revision=1,
        status=WeaknessStatus.CANDIDATE,
        title=f"Diagnostic candidate: {group.signature.weakness_type.value}",
        description=(
            "Evidence-backed diagnostic candidate. Correlation is retained without a causal claim."
        ),
        weakness_type=group.signature.weakness_type,
        signature_hash=group.signature.content_hash,
        group_snapshot_hash=group.content_hash,
        cluster_refs=(),
        impact_score_hash=score.content_hash,
        evidence_package_hash=package.content_hash,
        reproduction_status=package.reproduction.status,
        affected_components=(group.signature.component_identity,),
        source_refs=tuple(item.content_hash for item in package.source_manifest),
        counterexample_refs=group.counterexample_refs,
        verifier_bundle_hash=verifier_bundle_hash,
        created_at=created_at,
        created_by=actor,
        reason="deterministic weakness mining candidate",
    )
    return identity, revision


def transition_revision(
    current: WeaknessRevision,
    target: WeaknessStatus,
    *,
    group: WeaknessGroup,
    score: ImpactScore,
    evidence_coverage: Decimal,
    actor: str,
    reason: str,
    verifier_bundle_hash: str,
    created_at: datetime,
    configuration: WeaknessConfiguration,
    operator_approval_reference: str | None = None,
    monitoring_task_count: int = 0,
    successor_weakness_id: UUID | None = None,
) -> WeaknessRevision:
    if actor.lower().startswith(("provider", "model")):
        raise WeaknessAuthorityError("provider actors cannot authorize weakness lifecycle")
    if target not in _LEGAL_TRANSITIONS[current.status]:
        raise WeaknessLifecycleError("illegal weakness status transition")
    if target is WeaknessStatus.CONFIRMED:
        critical = score.priority is WeaknessPriority.CRITICAL
        normal = (
            len(group.members) >= configuration.minimum_signals_for_confirmation
            and group.distinct_task_count >= configuration.minimum_distinct_tasks_for_confirmation
            and evidence_coverage >= Decimal(str(configuration.minimum_evidence_coverage))
        )
        exceptional = (
            critical
            and configuration.allow_single_critical_safety_confirmation
            and operator_approval_reference is not None
        )
        if not normal and not exceptional:
            raise WeaknessLifecycleError("confirmation evidence threshold is not met")
        if (
            critical
            and configuration.critical_safety_confirmation_requires_operator
            and operator_approval_reference is None
        ):
            raise WeaknessLifecycleError("critical safety confirmation requires operator")
    if target is WeaknessStatus.RESOLVED:
        if current.status not in {WeaknessStatus.CONFIRMED, WeaknessStatus.MONITORING}:
            raise WeaknessLifecycleError("resolution requires confirmed or monitoring state")
        if monitoring_task_count < configuration.minimum_resolution_task_count:
            raise WeaknessLifecycleError("resolution monitoring evidence is insufficient")
    return WeaknessRevision(
        **current.model_dump(
            mode="python",
            exclude={
                "content_hash",
                "revision",
                "previous_revision",
                "status",
                "created_at",
                "created_by",
                "reason",
                "operator_approval_reference",
                "successor_weakness_id",
            },
        ),
        revision=current.revision + 1,
        previous_revision=current.revision,
        status=target,
        successor_weakness_id=successor_weakness_id,
        operator_approval_reference=operator_approval_reference,
        created_at=created_at,
        created_by=actor,
        reason=reason,
    )


def queue_entry_for(
    revision: WeaknessRevision,
    score: ImpactScore,
    *,
    queue_policy_hash: str,
    created_at: datetime,
    blockers: tuple[WeaknessQueueDependency, ...] = (),
) -> WeaknessQueueEntry | None:
    if revision.status in {
        WeaknessStatus.RESOLVED,
        WeaknessStatus.SUPERSEDED,
        WeaknessStatus.RETRACTED,
    }:
        return None
    if revision.status is WeaknessStatus.CANDIDATE and score.priority not in {
        WeaknessPriority.CRITICAL,
        WeaknessPriority.HIGH,
    }:
        return None
    recommendation = NextAnalysisType.OPERATOR_REVIEW
    if revision.reproduction_status in {
        WeaknessReproductionStatus.NOT_ATTEMPTED,
        WeaknessReproductionStatus.INSUFFICIENT_EVIDENCE,
    }:
        recommendation = NextAnalysisType.RUN_BOUNDED_REPLAY
    if blockers:
        recommendation = NextAnalysisType.COLLECT_MORE_EVIDENCE
    entry_id = uuid5(
        NAMESPACE_URL,
        f"weakness-queue:{revision.content_hash}:{score.content_hash}:{queue_policy_hash}",
    )
    return WeaknessQueueEntry(
        queue_entry_id=entry_id,
        weakness_id=revision.weakness_id,
        weakness_revision=revision.revision,
        weakness_revision_hash=revision.content_hash,
        weakness_status=revision.status,
        priority=score.priority,
        priority_reason=(
            f"impact={score.final_score}; floor={score.priority_floor}; "
            f"uncertainty={score.uncertainty.value}"
        ),
        blocked_by=blockers,
        recommended_next_analysis=recommendation,
        status=WeaknessQueueStatus.BLOCKED if blockers else WeaknessQueueStatus.QUEUED,
        queue_policy_hash=queue_policy_hash,
        created_at=created_at,
    )


def build_queue_snapshot(
    entries: tuple[WeaknessQueueEntry, ...],
    *,
    queue_policy_hash: str,
    created_at: datetime,
    exclusions: dict[str, str] | None = None,
) -> WeaknessQueueSnapshot:
    _reject_blocker_cycles(entries)
    ordered = tuple(
        sorted(
            entries,
            key=lambda item: (
                _PRIORITY_ORDER[item.priority],
                item.status is WeaknessQueueStatus.BLOCKED,
                str(item.weakness_id),
            ),
        )
    )
    entry_hash = _hash(item.content_hash for item in ordered)
    return WeaknessQueueSnapshot(
        snapshot_id=uuid5(NAMESPACE_URL, f"weakness-queue-snapshot:{entry_hash}"),
        queue_policy_hash=queue_policy_hash,
        entries=ordered,
        exclusions=exclusions or {},
        created_at=created_at,
    )


def _reject_blocker_cycles(entries: tuple[WeaknessQueueEntry, ...]) -> None:
    graph = {
        entry.weakness_id: {
            dependency.blocked_by_weakness_id
            for dependency in entry.blocked_by
            if dependency.blocker_type is QueueBlockerType.DEPENDS_ON_OTHER_WEAKNESS
            and dependency.blocked_by_weakness_id is not None
        }
        for entry in entries
    }

    def visit(node: UUID, path: frozenset[UUID]) -> None:
        if node in path:
            raise WeaknessLifecycleError("weakness queue blocker cycle")
        for child in graph.get(node, set()):
            visit(child, path | {node})

    for node in graph:
        visit(node, frozenset())


class WeaknessMiningService:
    def __init__(
        self,
        repository: WeaknessRepositoryPort,
        source_registry: SourceResolverRegistry,
        extractor_registry: SignalExtractorRegistry,
        configuration: WeaknessConfiguration | None = None,
    ) -> None:
        self.repository = repository
        self.source_registry = source_registry
        self.extractor_registry = extractor_registry
        self.configuration = configuration or WeaknessConfiguration()
        self.failure_codes = FailureCodeRegistry()

    async def prepare_mining(
        self, request: MiningRequest, profile: MiningProfile
    ) -> MiningSourceSnapshot:
        if request.mining_profile_hash != profile.content_hash:
            raise WeaknessAuthorityError("mining request does not reference the exact profile")
        existing = await self.repository.get_mining_run_by_idempotency_key(request.idempotency_key)
        if existing is not None and existing != request:
            raise WeaknessAuthorityError("mining idempotency key references another request")
        await self.repository.create_mining_run(request)
        sources = []
        for source_type in profile.enabled_source_types:
            resolver = self.source_registry.resolve(source_type)
            if not await resolver.health_check():
                raise WeaknessSourceError(f"source resolver unhealthy: {resolver.descriptor}")
            for discovered in await resolver.discover(request):
                resolved = await resolver.resolve(discovered)
                if resolved != discovered:
                    raise WeaknessSourceError("source changed during exact resolution")
                if resolved.scope != request.scope:
                    raise WeaknessSourceError("source scope does not match mining request")
                sources.append(resolved)
        if not sources:
            raise WeaknessSourceError("mining source snapshot would be empty")
        if len(sources) > self.configuration.maximum_source_records_per_run:
            raise WeaknessSourceError("mining source limit exceeded")
        snapshot = MiningSourceSnapshot(
            mining_run_id=request.mining_run_id,
            source_refs=tuple(sources),
            registry_snapshots=(
                self.source_registry.snapshot_hash,
                self.extractor_registry.snapshot_hash,
                self.failure_codes.snapshot_hash,
            ),
            profile_refs=(profile.content_hash,),
            created_at=request.created_at,
        )
        await self.repository.record_source_snapshot(snapshot)
        await self.repository.set_mining_status(
            request.mining_run_id, MiningRunStatus.SNAPSHOT_CREATED
        )
        return snapshot

    async def mine(self, request: MiningRequest, profile: MiningProfile) -> MiningRunResult:
        snapshot = await self.prepare_mining(request, profile)
        await self.repository.set_mining_status(
            request.mining_run_id, MiningRunStatus.EXTRACTING_SIGNALS
        )
        extracted: list[WeaknessSignal] = []
        for extractor in self.extractor_registry.enabled(profile.enabled_extractors):
            extracted.extend(await extractor.extract(snapshot, profile))
        signals = tuple(extracted)
        if len(signals) > self.configuration.maximum_signals_per_run:
            raise WeaknessAuthorityError("weakness signal limit exceeded")
        source_hashes = {item.content_hash for item in snapshot.source_refs}
        for signal in signals:
            if signal.mining_run_id != request.mining_run_id:
                raise WeaknessAuthorityError("extractor returned a signal for another run")
            if not {item.content_hash for item in signal.source_refs} <= source_hashes:
                raise WeaknessAuthorityError("signal references evidence outside the snapshot")
        signals = tuple(
            sorted(
                {item.signal_id: item for item in signals}.values(),
                key=lambda item: str(item.signal_id),
            )
        )
        await self.repository.record_signals(signals)
        await self.repository.set_mining_status(request.mining_run_id, MiningRunStatus.GROUPING)
        groups = build_exact_group_snapshot(
            signals,
            profile_hash=profile.content_hash,
            created_at=request.created_at,
        )
        await self.repository.record_group_snapshot(groups)
        clusters = build_noop_cluster_snapshot(groups, created_at=request.created_at)
        await self.repository.record_cluster_snapshot(clusters)
        await self.repository.set_mining_status(request.mining_run_id, MiningRunStatus.SCORING)
        verifier_hash = sha256(b"mandatory-weakness-verifier-bundle-v1").hexdigest()
        queue_policy_hash = sha256(profile.queue_policy.encode()).hexdigest()
        scores: list[ImpactScore] = []
        revisions: list[WeaknessRevision] = []
        entries: list[WeaknessQueueEntry] = []
        packages: list[WeaknessEvidencePackage] = []
        for group in groups.groups:
            related_signals = tuple(
                item
                for item in signals
                if item.signal_id in {member.signal_id for member in group.members}
            )
            facts = ImpactFacts(
                user_correction_count=sum(
                    item.weakness_type is WeaknessType.USER_CORRECTION_PATTERN
                    for item in related_signals
                ),
                reproduction_count=group.distinct_task_count,
                safety_evidence=(
                    Decimal("1")
                    if any(item.severity is WeaknessSeverity.CRITICAL for item in related_signals)
                    else Decimal()
                ),
                correctness_evidence=max(
                    (_SEVERITY[item.severity] for item in related_signals),
                    default=Decimal(),
                ),
            )
            score = score_impact(
                group,
                group_snapshot_hash=groups.content_hash,
                facts=facts,
                reference_time=request.created_at,
            )
            reproduction = WeaknessReproductionAssessment(
                status=WeaknessReproductionStatus.NOT_ATTEMPTED,
                attempts=(),
                required_safety_restrictions=("bounded replay only",),
                limitations=("No unrestricted source artifact execution is permitted.",),
                assessed_at=request.created_at,
            )
            package = build_evidence_package(group, score, signals, (), reproduction=reproduction)
            identity, revision = build_candidate(
                group,
                score,
                package,
                actor=request.requested_by,
                created_at=request.created_at,
                verifier_bundle_hash=verifier_hash,
            )
            await self.repository.record_impact_score(score)
            await self.repository.record_evidence_package(package)
            await self.repository.create_weakness(identity, revision)
            entry = queue_entry_for(
                revision,
                score,
                queue_policy_hash=queue_policy_hash,
                created_at=request.created_at,
            )
            if entry is not None:
                await self.repository.record_queue_entry(entry)
                entries.append(entry)
            scores.append(score)
            packages.append(package)
            revisions.append(revision)
        queue = build_queue_snapshot(
            tuple(entries),
            queue_policy_hash=queue_policy_hash,
            created_at=request.created_at,
        )
        await self.repository.record_queue_snapshot(queue)
        await self.repository.set_mining_status(request.mining_run_id, MiningRunStatus.PACKAGING)
        summary = MiningRunSummary(
            mining_run_id=request.mining_run_id,
            source_count=len(snapshot.source_refs),
            signal_count=len(signals),
            signature_count=len(groups.groups),
            group_count=len(groups.groups),
            weakness_count=len(revisions),
            queue_entry_count=len(entries),
            warnings=(),
            exclusions=(),
        )
        stage_hashes = {
            "sources": snapshot.content_hash,
            "signals": _hash(item.content_hash for item in signals),
            "groups": groups.content_hash,
            "clusters": clusters.content_hash,
            "impact": _hash(item.content_hash for item in scores),
            "evidence": _hash(item.content_hash for item in packages),
            "queue": queue.content_hash,
        }
        manifest = MiningRunManifest(
            mining_run_id=request.mining_run_id,
            request_hash=request.content_hash,
            source_snapshot_hash=snapshot.content_hash,
            registry_snapshot_hashes=snapshot.registry_snapshots,
            signal_hashes=tuple(item.content_hash for item in signals),
            group_snapshot_hash=groups.content_hash,
            cluster_snapshot_hash=clusters.content_hash,
            impact_hashes=tuple(item.content_hash for item in scores),
            weakness_revision_hashes=tuple(item.content_hash for item in revisions),
            queue_snapshot_hash=queue.content_hash,
            verifier_bundle_hash=verifier_hash,
            stage_hashes=stage_hashes,
            summary=summary,
            created_at=request.created_at,
        )
        await self.repository.record_manifest(manifest)
        await self._record_accesses(request, manifest)
        await self.repository.set_mining_status(request.mining_run_id, MiningRunStatus.COMPLETED)
        return MiningRunResult(
            status=MiningRunStatus.COMPLETED,
            manifest=manifest,
            completed_at=request.created_at,
        )

    async def resume_mining(
        self, request: MiningRequest, profile: MiningProfile
    ) -> MiningRunResult:
        known = await self.repository.get_mining_run_by_idempotency_key(request.idempotency_key)
        if known is not None and known != request:
            raise WeaknessAuthorityError("resume request changed immutable mining input")
        return await self.mine(request, profile)

    async def cancel_mining(self, mining_run_id: UUID) -> None:
        await self.repository.set_mining_status(mining_run_id, MiningRunStatus.CANCELLED)

    async def _record_accesses(self, request: MiningRequest, manifest: MiningRunManifest) -> None:
        for access_type in WeaknessAccessType:
            access = WeaknessAccessRecord(
                access_id=uuid5(
                    NAMESPACE_URL,
                    f"weakness-access:{request.mining_run_id}:{access_type.value}",
                ),
                access_type=access_type,
                actor_id=request.requested_by,
                subject_id=str(request.mining_run_id),
                subject_hash=manifest.content_hash,
                accessed_at=request.created_at,
                reason="deterministic weakness mining lifecycle",
            )
            await self.repository.record_access(access)


def default_mining_profile(*, created_at: datetime | None = None) -> MiningProfile:
    return MiningProfile(
        profile_id="weakness-mining-default",
        version=1,
        enabled_source_types=tuple(SignalSourceType),
        enabled_extractors=("authoritative-fixture-extractor-v1",),
        signature_profile="weakness-signature-v1",
        grouping_profile="exact-signature-v1",
        clustering_profile="no-op-v1",
        impact_profile="weakness-impact-default-v1",
        confirmation_policy="explicit-confirmation-v1",
        queue_policy="deterministic-priority-v1",
        resource_limits={"signals": 100_000, "sources": 100_000},
        created_at=created_at or utc_now(),
    )
