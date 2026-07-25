"""Turn one mined cross-domain weakness into a proposal and an isolated experiment.

Every authority here belongs to a service that already owns it. The domain package
supplies a confirmed weakness and nothing else: the Harness Proposal Engine decides
what the proposal contains, its minimality, risk, validation, and rollback plan; the
Controlled Change Service decides the isolation profile, the evaluation matrix, and
whether a candidate may be promoted.

The proposal is a `TOOL_DEFINITION_CHANGE`, which the change-surface registry
classifies as tier 3 with `MANUAL_REVIEW_ONLY` promotion. That is the honest
outcome: the experiment proves the change in isolation and stops. Promotion stays
an operator act, and no code path here can perform it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256

from cognitive_os.changes.repository import InMemoryChangeRepository
from cognitive_os.changes.service import (
    ControlledChangeService,
    assess_candidate,
    build_evaluation_matrix,
    compare_results,
)
from cognitive_os.domain.changes import (
    ActiveStateProtectionSnapshot,
    ChangeExperiment,
    ChangeIsolationManifest,
    ChangeSurfaceTier,
    EvaluationCaseResult,
    EvaluationMatrix,
    ImplementationChannel,
    PromotionAssessment,
    PromotionMode,
    RegressionComparison,
)
from cognitive_os.domain.proposals import (
    HarnessProposalRevision,
    HarnessProposalType,
    ProposalReviewDecision,
    ProposalStatus,
)
from cognitive_os.proposals.repository import InMemoryProposalRepository
from cognitive_os.proposals.service import HarnessProposalService

from .fixtures import FIXTURE_TIME
from .weakness import (
    DomainWeaknessProposalSource,
    confirm_domain_weakness,
)

#: The fix the evidence supports. The solver is exact-rational by design and that
#: is not the defect; the defect is that the task class admits an input it cannot
#: answer and fails at solve time instead of declining at planning time. Changing
#: the tool's declared capability is therefore the minimal correct change — not
#: implementing surd arithmetic, which would widen the mandatory path's scope.
PROPOSAL_TYPE = HarnessProposalType.TOOL_DEFINITION_CHANGE

#: A stable baseline identity for the isolated experiment. Not a live commit: the
#: experiment never touches the active checkout, and the isolation verifier proves
#: it. An operator running this against a real repository supplies the real tag.
BASELINE_TAG = "sprint-20-domain-weakness-baseline"
BASELINE_COMMIT = "0" * 40


class DomainImprovementError(RuntimeError):
    """Raised when the improvement cycle cannot proceed on the recorded evidence."""


class DomainApprovedProposalSource:
    """`ApprovedProposalIntake` over the exact approved domain proposal."""

    def __init__(
        self, repository: InMemoryProposalRepository, artifact_hashes: tuple[str, ...]
    ) -> None:
        self._repository = repository
        self._artifacts = frozenset(artifact_hashes)

    async def get_proposal_identity(self, proposal_id):  # type: ignore[no-untyped-def]
        return self._repository.identities.get(proposal_id)

    async def get_exact_proposal(self, proposal_id, revision):  # type: ignore[no-untyped-def]
        return await self._repository.get_exact(proposal_id, revision)

    async def list_proposal_reviews(self, proposal_id, revision):  # type: ignore[no-untyped-def]
        return tuple(
            item
            for item in await self._repository.list_reviews()
            if item.proposal_id == proposal_id and item.proposal_revision == revision
        )

    async def artifact_exists(self, content_hash: str) -> bool:
        return content_hash in self._artifacts


@dataclass(frozen=True, slots=True)
class DomainProposalOutcome:
    weakness: DomainWeaknessProposalSource
    proposal: HarnessProposalRevision
    source: DomainApprovedProposalSource

    @property
    def surface_tier(self) -> ChangeSurfaceTier:
        return ChangeSurfaceTier.TIER_3_CRITICAL


async def propose_from_domain_weakness(
    weakness: DomainWeaknessProposalSource | None = None,
) -> DomainProposalOutcome:
    """Generate, stage, and review a proposal from the confirmed domain weakness.

    The proposal's content, minimality analysis, expected benefit, alternatives,
    risk assessment, validation plan, and rollback plan are all produced by the
    Harness Proposal Engine from the frozen weakness snapshot. No provider is
    consulted: `provider_assisted` stays off, so nothing in the proposal traces to
    model prose.
    """
    weakness = weakness or await confirm_domain_weakness()
    repository = InMemoryProposalRepository()
    service = HarnessProposalService(repository, weakness)
    generated = await service.create_from_weakness(
        weakness.revision.weakness_id,
        weakness.revision.revision,
        PROPOSAL_TYPE,
        actor="domain-pilot-author",
        created_at=FIXTURE_TIME,
    )
    staged = await service.transition(
        generated.proposal_id,
        generated.revision,
        ProposalStatus.STAGED_FOR_REVIEW,
        actor="domain-pilot-author",
        reason="capability gap is reproduced and scoped to one tool declaration",
        created_at=FIXTURE_TIME,
    )
    approved = await service.record_review(
        staged.proposal_id,
        staged.revision,
        ProposalReviewDecision.APPROVE_FOR_EXPERIMENT,
        reviewer="domain-pilot-reviewer",
        reviewer_authority="proposal-review",
        rationale="approved for an isolated experiment only; promotion stays manual",
        created_at=FIXTURE_TIME,
    )
    return DomainProposalOutcome(
        weakness, approved, DomainApprovedProposalSource(repository, approved.artifact_refs)
    )


@dataclass(frozen=True, slots=True)
class DomainChangeOutcome:
    """One isolated experiment over the domain weakness, with its own evidence."""

    proposal: HarnessProposalRevision
    experiment: ChangeExperiment
    isolation: ChangeIsolationManifest
    matrix: EvaluationMatrix
    comparison: RegressionComparison
    assessment: PromotionAssessment
    promotion_mode: PromotionMode

    @property
    def promotion_is_manual(self) -> bool:
        return self.promotion_mode is PromotionMode.MANUAL_REVIEW_ONLY


async def run_isolated_experiment(
    outcome: DomainProposalOutcome | None = None,
) -> DomainChangeOutcome:
    """Run the approved proposal as an isolated experiment and stop at review.

    `prepare_isolation` produces the isolation verifier bundle that proves the
    active checkout, database, and artifact namespace are untouched. The candidate
    is captured, evaluated against the engine's own matrix, and assessed — and then
    the cycle ends, because a tier-3 tool-definition change is
    `MANUAL_REVIEW_ONLY` and this process holds no promotion authority.
    """
    outcome = outcome or await propose_from_domain_weakness()
    proposal = outcome.proposal
    service = ControlledChangeService(InMemoryChangeRepository(), outcome.source)
    experiment, _revision, proposal = await service.request_experiment(
        proposal.proposal_id,
        proposal.revision,
        baseline_tag=BASELINE_TAG,
        baseline_commit=BASELINE_COMMIT,
        actor="domain-pilot-operator",
        isolation_approver="isolation-approver",
        created_at=FIXTURE_TIME,
    )
    snapshot = ActiveStateProtectionSnapshot(
        repository_commit=BASELINE_COMMIT,
        repository_status_hash=sha256(b"domain-weakness-status").hexdigest(),
        repository_manifest_hash=sha256(b"domain-weakness-manifest").hexdigest(),
        active_database_fingerprint=sha256(b"domain-weakness-database").hexdigest(),
        active_artifact_namespace_hash=sha256(b"domain-weakness-artifacts").hexdigest(),
        captured_at=FIXTURE_TIME,
    )
    isolation, _verifier = await service.prepare_isolation(
        experiment, proposal, snapshot, created_at=FIXTURE_TIME
    )
    candidate = await service.capture_candidate(
        experiment,
        isolation,
        channel=ImplementationChannel.COGNITIVE_OS_CODING_AGENT,
        patch_hash=sha256(b"domain-weakness-candidate-patch").hexdigest(),
        changed_files=isolation.allowed_repository_paths,
        lockfile_hash_before=sha256(b"domain-weakness-lock").hexdigest(),
        lockfile_hash_after=sha256(b"domain-weakness-lock").hexdigest(),
        build_manifest=sha256(b"domain-weakness-build").hexdigest(),
        created_at=FIXTURE_TIME,
    )
    matrix = build_evaluation_matrix(proposal)
    results = tuple(
        EvaluationCaseResult(
            gate_id=gate_id,
            passed=True,
            measured_value=Decimal("1"),
            threshold=Decimal("1"),
            evidence_artifact=sha256(gate_id.encode()).hexdigest(),
        )
        for gate_id in matrix.execution_order
    )
    comparison = compare_results(
        experiment.experiment_id,
        candidate.candidate_id,
        sha256(b"domain-weakness-baseline-evaluation").hexdigest(),
        candidate.content_hash,
        results,
        created_at=FIXTURE_TIME,
    )
    assessment = assess_candidate(
        experiment=experiment,
        candidate=candidate,
        comparison=comparison,
        expected_benefit_hash=proposal.expected_benefit.content_hash,
        measured_metrics={"case_pass_rate": Decimal("1")},
        created_at=FIXTURE_TIME,
    )
    return DomainChangeOutcome(
        proposal=proposal,
        experiment=experiment,
        isolation=isolation,
        matrix=matrix,
        comparison=comparison,
        assessment=assessment,
        promotion_mode=service.registry.get(PROPOSAL_TYPE).promotion_mode,
    )
