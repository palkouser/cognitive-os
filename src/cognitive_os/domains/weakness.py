"""Mine real cross-domain harness weaknesses from real recorded evidence.

Nothing here invents a weakness. Each probe is a legitimate input to a task class
the registry already accepts, executed through the same governed Controller and
Tool Plane path every other case uses. The probe is not rigged to fail: it fails
because the harness genuinely cannot solve it, and the evidence mined is the audit
trail the run actually recorded — the failed tool call and the acceptance decision
that rejected it.

The weakness found is a capability gap, not a defect in a component: the
`polynomial-equation` task class accepts any real quadratic, but the solver is
exact-rational only, so a quadratic with irrational roots is admitted at planning
time and then fails at solve time instead of being declined up front.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.config.weakness_config import WeaknessConfiguration
from cognitive_os.domain.domains import DomainBenchmarkCase, DomainProblem
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.routing import TaskComplexityClass
from cognitive_os.domain.weakness import (
    CausalRelationshipType,
    ImpactScore,
    MiningProfile,
    MiningRequest,
    MiningRunResult,
    MiningSourceReference,
    MiningSourceSnapshot,
    SignalSourceType,
    WeaknessComponentType,
    WeaknessConfidenceLevel,
    WeaknessEvidencePackage,
    WeaknessQueueEntry,
    WeaknessReproductionAssessment,
    WeaknessReproductionStatus,
    WeaknessRevision,
    WeaknessSeverity,
    WeaknessSignal,
    WeaknessStatus,
    WeaknessType,
)
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.routing.service import build_task_signature
from cognitive_os.weakness.repository import InMemoryWeaknessRepository
from cognitive_os.weakness.service import (
    ImpactFacts,
    SignalExtractorRegistry,
    SourceResolverRegistry,
    WeaknessMiningService,
    build_candidate,
    build_evidence_package,
    queue_entry_for,
    score_impact,
    transition_revision,
)

from .fixtures import FIXTURE_TIME, build_all_cases
from .runner import run_case_controlled

SCOPE = "repository:cognitive-os"
EXTRACTOR_PROFILE = "domain-capability-gap-extractor-v1"

#: Legitimate `polynomial-equation` inputs whose roots are irrational. Each is a
#: real quadratic the registry admits; none is malformed, out of budget, or
#: adversarial. `x^2 - n = 0` for a non-square `n` is the smallest honest witness.
IRRATIONAL_ROOT_PROBES: tuple[tuple[str, dict[str, int]], ...] = (
    ("domain-weakness-irrational-2", {"a": 1, "b": 0, "c": -2}),
    ("domain-weakness-irrational-3", {"a": 1, "b": 0, "c": -3}),
    ("domain-weakness-irrational-5", {"a": 1, "b": 0, "c": -5}),
)

#: The gap is a missing capability, not a broken component: the tool is routed
#: correctly, authorised correctly, and audited correctly — it simply has no
#: exact-rational answer to give. `MISSING_SKILL` is the honest classification;
#: calling it a tool or verifier failure would blame a component that behaved
#: exactly as specified.
WEAKNESS_TYPE = WeaknessType.MISSING_SKILL
FAILURE_CODE = "invalid_derivation:irrational_roots_outside_exact_rational_scope"


class DomainWeaknessError(RuntimeError):
    """Raised when a probe does not produce the evidence mining requires."""


def probe_case(case_id: str, formal_inputs: dict[str, int]) -> DomainBenchmarkCase:
    """A real `polynomial-equation` case carrying an input with irrational roots.

    Built by substituting coefficients into an existing case rather than through
    `build_case`, which computes its expected answer by calling the solver — the
    very call that cannot succeed here. The problem, plan, budgets, forbidden
    operations, and provenance are the fixture's own and are not weakened.
    """
    base = next(item for item in build_all_cases() if item.problem_type == "polynomial-equation")
    problem = DomainProblem(
        **{
            **base.problem.model_dump(exclude={"content_hash"}),
            "problem_id": uuid5(NAMESPACE_URL, f"domain-problem:{case_id}"),
            "formal_inputs": dict(formal_inputs),
            "knowns": {key: str(value) for key, value in formal_inputs.items()},
        }
    )
    return base.model_copy(
        update={
            "case_id": case_id,
            "problem": problem,
            "plan": base.plan.model_copy(update={"problem_id": problem.problem_id}),
            "expected_answer": base.expected_answer.model_copy(
                update={"problem_id": problem.problem_id}
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class ProbeObservation:
    """What one probe run actually recorded. Nothing here is asserted, only read."""

    case: DomainBenchmarkCase
    task_run_id: UUID
    tool_failed: bool
    accepted: bool
    decision_reason: str
    evidence_hashes: tuple[str, ...]
    event_types: tuple[str, ...]

    @property
    def is_capability_gap(self) -> bool:
        """A gap is evidenced only by a failed tool call *and* a rejected outcome."""
        return self.tool_failed and not self.accepted

    @property
    def observation_hash(self) -> str:
        """Digest of *what was observed about the harness*, not of one execution.

        Deliberately excludes `evidence_hashes`. Those cover real recorded event
        payloads, but a payload carries a fresh acceptance `decision_id` and wall
        clock on every run, so hashing them would make the same weakness mine to a
        different identity each time. A weakness is a property of the harness: the
        same task class, the same failure code, and the same recorded control flow
        must yield the same weakness. The per-run payload digests stay on this
        observation for audit, and every signal still cites its real
        `task_run_id`, which is itself derived from the case rather than the clock.
        """
        return sha256(
            "|".join(
                (
                    self.case.content_hash,
                    str(self.task_run_id),
                    str(self.tool_failed),
                    str(self.accepted),
                    self.decision_reason,
                    ",".join(self.event_types),
                )
            ).encode()
        ).hexdigest()


async def observe_probe(case: DomainBenchmarkCase) -> ProbeObservation:
    """Run one probe through the governed path and read back what it recorded."""
    store = MemoryEventStore()
    run = await run_case_controlled(case, store=store)
    events = store.stored_events()
    task_run_ids = {
        item.envelope.correlation_id
        for item in events
        if item.envelope.event_type == "controller.acceptance_decision_recorded"
    }
    if len(task_run_ids) != 1:
        raise DomainWeaknessError("a probe run must record exactly one task run identity")
    return ProbeObservation(
        case=case,
        task_run_id=task_run_ids.pop(),
        tool_failed=any(item.envelope.event_type == "tool_call.failed" for item in events),
        accepted=run.accepted,
        decision_reason=run.decision_reason,
        evidence_hashes=tuple(
            item.envelope.payload_hash
            for item in events
            if item.envelope.event_type
            in {"tool_call.failed", "controller.acceptance_decision_recorded"}
        ),
        event_types=run.event_types,
    )


async def observe_probes() -> tuple[ProbeObservation, ...]:
    """Every probe, in declared order. A probe that does not fail is not reported."""
    observations = [
        await observe_probe(probe_case(name, inputs)) for name, inputs in IRRATIONAL_ROOT_PROBES
    ]
    gaps = tuple(item for item in observations if item.is_capability_gap)
    if len(gaps) != len(observations):
        raise DomainWeaknessError(
            "a probe solved an input the harness is documented not to support; "
            "the weakness may already be fixed and this miner is now stale"
        )
    return gaps


def _source(
    observation: ProbeObservation,
    source_type: SignalSourceType,
    kind: str,
    *,
    outcome_authority: bool = False,
) -> MiningSourceReference:
    material = f"{kind}:{observation.case.case_id}:{observation.observation_hash}"
    return MiningSourceReference(
        source_type=source_type,
        source_id=f"domain-probe:{observation.case.case_id}:{kind}",
        source_revision=observation.case.content_hash[:16],
        source_content_hash=sha256(material.encode()).hexdigest(),
        scope=SCOPE,
        sensitivity=MemorySensitivity.INTERNAL,
        required=True,
        authoritative=True,
        shadow=False,
        outcome_authority=outcome_authority,
    )


def probe_sources(observations: tuple[ProbeObservation, ...]) -> tuple[MiningSourceReference, ...]:
    """Two sources per probe: the failed tool call, and the deciding authority."""
    sources: list[MiningSourceReference] = []
    for item in observations:
        sources.append(_source(item, SignalSourceType.TOOL, "tool"))
        sources.append(
            _source(item, SignalSourceType.ACCEPTANCE, "acceptance", outcome_authority=True)
        )
    return tuple(sources)


class DomainWeaknessSourceResolver:
    """`WeaknessSourceResolverPort` over frozen probe evidence; read-only."""

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
        return f"domain-{self._source_type.value}-resolver-v1"

    async def discover(self, request: MiningRequest) -> tuple[MiningSourceReference, ...]:
        return self._sources

    async def resolve(self, source: MiningSourceReference) -> MiningSourceReference:
        if source not in self._sources:
            raise LookupError("domain probe source unavailable")
        return source

    async def health_check(self) -> bool:
        return bool(self._sources)


class DomainCapabilityGapExtractor:
    """`WeaknessSignalExtractorPort` that reports the observed capability gap.

    One signal per probe, each carrying its own failed tool call as primary
    evidence and its own acceptance decision as the outcome authority. The
    causal relationship is `OBSERVED_FAILURE` because the run recorded the
    failure directly — not an inference from correlation.
    """

    def __init__(self, observations: tuple[ProbeObservation, ...]) -> None:
        self._by_case = {item.case.case_id: item for item in observations}

    @property
    def descriptor(self) -> str:
        return EXTRACTOR_PROFILE

    @property
    def supported_types(self) -> frozenset[WeaknessType]:
        return frozenset({WEAKNESS_TYPE})

    async def extract(
        self, snapshot: MiningSourceSnapshot, profile: MiningProfile
    ) -> tuple[WeaknessSignal, ...]:
        by_id = {item.source_id: item for item in snapshot.source_refs}
        signals = []
        for case_id, observation in sorted(self._by_case.items()):
            tool = by_id.get(f"domain-probe:{case_id}:tool")
            acceptance = by_id.get(f"domain-probe:{case_id}:acceptance")
            if tool is None or acceptance is None:
                continue
            signals.append(
                WeaknessSignal(
                    signal_id=uuid5(NAMESPACE_URL, f"domain-weakness-signal:{case_id}"),
                    mining_run_id=snapshot.mining_run_id,
                    weakness_type=WEAKNESS_TYPE,
                    task_run_id=observation.task_run_id,
                    source_refs=(tool, acceptance),
                    task_signature=build_task_signature(
                        problem_domain="mathematics",
                        problem_class=observation.case.problem_type,
                        output_type="structured",
                        estimated_complexity=TaskComplexityClass.SMALL,
                        risk_level="standard",
                    ),
                    failure_code=FAILURE_CODE,
                    component_type=WeaknessComponentType.TOOL,
                    component_identity="domains.solve",
                    verifier_reference="domains.checker",
                    # A documented scope limit that fails late rather than
                    # declining early: real, reproducible, and not a safety issue.
                    severity=WeaknessSeverity.MEDIUM,
                    confidence=WeaknessConfidenceLevel.VERIFIED,
                    causal_relationship=CausalRelationshipType.OBSERVED_FAILURE,
                    observed_at=FIXTURE_TIME,
                    extractor_profile=self.descriptor,
                    limitations=(
                        "One task class only; this is not evidence about other domains.",
                        "The gap is a declared scope limit, not an implementation defect.",
                    ),
                )
            )
        return tuple(signals)

    async def health_check(self) -> bool:
        return bool(self._by_case)


def mining_profile(sources: tuple[MiningSourceReference, ...]) -> MiningProfile:
    return MiningProfile(
        profile_id="domain-weakness-profile",
        version=1,
        enabled_source_types=tuple(sorted({item.source_type for item in sources}, key=str)),
        enabled_extractors=(EXTRACTOR_PROFILE,),
        signature_profile="weakness-signature-v1",
        grouping_profile="exact-signature-v1",
        clustering_profile="no-op-v1",
        impact_profile="weakness-impact-default-v1",
        confirmation_policy="explicit-confirmation-v1",
        queue_policy="deterministic-priority-v1",
        resource_limits={"signals": 1_000, "sources": 1_000},
        created_at=FIXTURE_TIME,
    )


def mining_request(profile: MiningProfile) -> MiningRequest:
    return MiningRequest(
        mining_run_id=uuid5(NAMESPACE_URL, "domain-weakness-mining-run:1"),
        scope=SCOPE,
        source_filters=profile.enabled_source_types,
        mining_profile_hash=profile.content_hash,
        requested_by="domain-pilot-operator",
        idempotency_key="sprint20-domain-weakness-1",
        created_at=FIXTURE_TIME,
    )


@dataclass(frozen=True, slots=True)
class DomainMiningOutcome:
    observations: tuple[ProbeObservation, ...]
    result: MiningRunResult
    repository: InMemoryWeaknessRepository

    @property
    def signal_count(self) -> int:
        return self.result.manifest.summary.signal_count if self.result.manifest else 0

    @property
    def weakness_count(self) -> int:
        return self.result.manifest.summary.weakness_count if self.result.manifest else 0


async def mine_domain_weaknesses(
    *, configuration: WeaknessConfiguration | None = None
) -> DomainMiningOutcome:
    """Run the real Weakness Mining Service over real domain probe evidence."""
    observations = await observe_probes()
    sources = probe_sources(observations)
    profile = mining_profile(sources)
    source_registry = SourceResolverRegistry()
    for source_type in profile.enabled_source_types:
        source_registry.register(DomainWeaknessSourceResolver(source_type, sources))
    source_registry.freeze()
    extractor_registry = SignalExtractorRegistry()
    extractor_registry.register(DomainCapabilityGapExtractor(observations))
    extractor_registry.freeze()
    repository = InMemoryWeaknessRepository()
    service = WeaknessMiningService(repository, source_registry, extractor_registry, configuration)
    result = await service.mine(mining_request(profile), profile)
    return DomainMiningOutcome(observations, result, repository)


class DomainWeaknessProposalSource:
    """`WeaknessProposalSourcePort` over one confirmed mined domain weakness."""

    def __init__(
        self,
        revision: WeaknessRevision,
        queue: WeaknessQueueEntry,
        evidence: WeaknessEvidencePackage,
        impact: ImpactScore,
        registry_snapshots: dict[str, str],
    ) -> None:
        self.revision = revision
        self.queue = queue
        self.evidence = evidence
        self.impact = impact
        self._registries = registry_snapshots

    def _matches(self, weakness_id: UUID, revision: int) -> bool:
        return (weakness_id, revision) == (self.revision.weakness_id, self.revision.revision)

    async def get_exact_weakness_revision(
        self, weakness_id: UUID, revision: int
    ) -> WeaknessRevision | None:
        return self.revision if self._matches(weakness_id, revision) else None

    async def get_current_weakness_revision(self, weakness_id: UUID) -> WeaknessRevision | None:
        return self.revision if weakness_id == self.revision.weakness_id else None

    async def get_exact_queue_entry(
        self, weakness_id: UUID, weakness_revision: int
    ) -> WeaknessQueueEntry | None:
        return self.queue if self._matches(weakness_id, weakness_revision) else None

    async def get_exact_evidence_package(
        self, weakness_id: UUID, weakness_revision: int
    ) -> WeaknessEvidencePackage | None:
        return self.evidence if self._matches(weakness_id, weakness_revision) else None

    async def get_exact_impact_score(
        self, weakness_id: UUID, weakness_revision: int
    ) -> ImpactScore | None:
        return self.impact if self._matches(weakness_id, weakness_revision) else None

    async def get_reproduction_assessment(
        self, weakness_id: UUID, weakness_revision: int
    ) -> WeaknessReproductionAssessment | None:
        return self.evidence.reproduction if self._matches(weakness_id, weakness_revision) else None

    async def get_related_benchmark_candidates(
        self, weakness_id: UUID, weakness_revision: int
    ) -> tuple[Any, ...]:
        return ()

    async def get_related_replay_candidates(
        self, weakness_id: UUID, weakness_revision: int
    ) -> tuple[Any, ...]:
        return ()

    async def get_required_registry_snapshots(self) -> dict[str, str]:
        return dict(self._registries)


async def confirm_domain_weakness(
    outcome: DomainMiningOutcome | None = None,
) -> DomainWeaknessProposalSource:
    """Confirm the mined capability gap as an operator would, then expose it.

    Mining leaves a `CANDIDATE`. Confirmation is an operator act with a stated
    reason, so it is performed here explicitly through the real transition
    function rather than being assumed. The queue entry is rebuilt against the
    confirmed revision, because the proposal engine requires the queue entry to
    reference the exact revision it was derived from.
    """
    outcome = outcome or await mine_domain_weaknesses()
    manifest = outcome.result.manifest
    if manifest is None:
        raise DomainWeaknessError("mining produced no manifest")
    repository = outcome.repository
    groups = next(iter(repository.group_snapshots.values()))
    group = max(groups.groups, key=lambda item: item.distinct_task_count)
    if group.distinct_task_count < 2:
        raise DomainWeaknessError("a proposable weakness needs at least two distinct task runs")
    signals = tuple(repository.signals.values())
    impact = score_impact(
        group,
        group_snapshot_hash=groups.content_hash,
        facts=ImpactFacts(
            reproduction_count=group.distinct_task_count,
            evidence_coverage=Decimal("1"),
            correctness_evidence=Decimal("0.5"),
        ),
        reference_time=FIXTURE_TIME,
    )
    reproduction = WeaknessReproductionAssessment(
        status=WeaknessReproductionStatus.REPRODUCIBLE,
        attempts=(),
        required_safety_restrictions=("offline deterministic replay only",),
        limitations=("Reproduced only for the probed task class.",),
        assessed_at=FIXTURE_TIME,
    )
    evidence = build_evidence_package(group, impact, signals, (), reproduction=reproduction)
    verifier_hash = sha256(b"mandatory-weakness-verifier-bundle-v1").hexdigest()
    _identity, candidate = build_candidate(
        group,
        impact,
        evidence,
        actor="domain-pilot-operator",
        created_at=FIXTURE_TIME,
        verifier_bundle_hash=verifier_hash,
    )
    confirmed = transition_revision(
        candidate,
        WeaknessStatus.CONFIRMED,
        group=group,
        score=impact,
        evidence_coverage=Decimal("1"),
        actor="domain-pilot-operator",
        reason="reproduced capability gap: exact-rational solver admits irrational roots",
        verifier_bundle_hash=verifier_hash,
        created_at=FIXTURE_TIME,
        configuration=WeaknessConfiguration(),
    )
    queue = queue_entry_for(
        confirmed,
        impact,
        queue_policy_hash=sha256(b"deterministic-priority-v1").hexdigest(),
        created_at=FIXTURE_TIME,
    )
    if queue is None:
        raise DomainWeaknessError("confirmed domain weakness is not queue eligible")
    return DomainWeaknessProposalSource(
        confirmed,
        queue,
        evidence,
        impact,
        {
            "weakness": confirmed.content_hash,
            "verifiers": verifier_hash,
            "benchmarks": manifest.content_hash,
            "authority": groups.content_hash,
        },
    )
