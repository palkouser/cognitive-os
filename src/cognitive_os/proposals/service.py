"""Deterministic proposal generation, verification, lifecycle, review, and queue."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.proposals import (
    ProposalGeneratorPort,
    ProposalRepositoryPort,
    WeaknessProposalSourcePort,
)
from cognitive_os.config.proposal_config import ProposalConfiguration
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.proposals import (
    ArtifactRevisionOperation,
    ChangeSpecification,
    ChangeSurfaceTier,
    ConfigurationValueOperation,
    EligibilityReason,
    ExpectedBenefit,
    ExpectedDirection,
    HarnessProposalIdentity,
    HarnessProposalRevision,
    HarnessProposalType,
    MinimalityAssessment,
    ProposalAccessRecord,
    ProposalAccessType,
    ProposalAlternative,
    ProposalEligibilityResult,
    ProposalGenerationMode,
    ProposalQueueEntry,
    ProposalQueueSnapshot,
    ProposalReview,
    ProposalReviewDecision,
    ProposalRiskAssessment,
    ProposalRiskLevel,
    ProposalRollbackPlan,
    ProposalRunManifest,
    ProposalSourceSnapshot,
    ProposalStatistics,
    ProposalStatus,
    ProposalTypeRegistration,
    ProposalValidationPlan,
    ProposalVerifierBundle,
    ProposalVerifierFinding,
    ProposalVerifierStatus,
    ProviderProposalDraft,
    RepositoryFileOperation,
    RollbackOperation,
    RollbackType,
    TypedProposalOperation,
)
from cognitive_os.domain.weakness import WeaknessPriority, WeaknessStatus
from cognitive_os.events.base import EventPayload
from cognitive_os.events.proposal_event_service import ProposalEventService
from cognitive_os.events.proposal_events import (
    ProposalApprovedForExperiment,
    ProposalCreated,
    ProposalQueued,
    ProposalQueueRemoved,
    ProposalRejected,
    ProposalRetracted,
    ProposalRevisionAppended,
    ProposalStagedForReview,
    ProposalSuperseded,
    ProposalValidated,
)


class ProposalError(RuntimeError):
    """Base error for governed proposal processing."""


class ProposalSourceError(ProposalError):
    """Raised when exact weakness evidence cannot be resolved."""


class ProposalAuthorityError(ProposalError):
    """Raised when a caller or provider attempts to gain authority."""


class ProposalConflictError(ProposalError):
    """Raised for stale revisions or duplicate active proposals."""


class ProposalValidationError(ProposalError):
    """Raised when the mandatory verifier bundle fails closed."""


MANDATORY_PROPOSAL_VERIFIERS = (
    "proposal.source_integrity",
    "proposal.weakness_revision_integrity",
    "proposal.weakness_eligibility",
    "proposal.schema_integrity",
    "proposal.change_surface_allowlist",
    "proposal.typed_operation_integrity",
    "proposal.minimality",
    "proposal.blast_radius_completeness",
    "proposal.expected_benefit_hypothesis",
    "proposal.risk_completeness",
    "proposal.alternatives_completeness",
    "proposal.validation_plan_completeness",
    "proposal.rollback_plan_completeness",
    "proposal.no_unsupported_causal_claim",
    "proposal.no_source_mutation",
    "proposal.no_destination_mutation",
    "proposal.no_permission_expansion",
    "proposal.no_automatic_approval",
    "proposal.no_unrestricted_instruction",
    "proposal.artifact_hash_integrity",
    "proposal.lifecycle_integrity",
    "proposal.queue_determinism",
)

_TERMINAL = {ProposalStatus.REJECTED, ProposalStatus.SUPERSEDED, ProposalStatus.RETRACTED}
_LEGAL_TRANSITIONS = {
    ProposalStatus.DRAFT: {ProposalStatus.GENERATED, ProposalStatus.RETRACTED},
    ProposalStatus.GENERATED: {
        ProposalStatus.VALIDATED,
        ProposalStatus.REJECTED,
        ProposalStatus.RETRACTED,
        ProposalStatus.SUPERSEDED,
    },
    ProposalStatus.VALIDATED: {
        ProposalStatus.STAGED_FOR_REVIEW,
        ProposalStatus.REJECTED,
        ProposalStatus.RETRACTED,
        ProposalStatus.SUPERSEDED,
    },
    ProposalStatus.STAGED_FOR_REVIEW: {
        ProposalStatus.APPROVED_FOR_EXPERIMENT,
        ProposalStatus.REJECTED,
        ProposalStatus.RETRACTED,
        ProposalStatus.SUPERSEDED,
    },
    ProposalStatus.APPROVED_FOR_EXPERIMENT: {
        ProposalStatus.SUPERSEDED,
        ProposalStatus.RETRACTED,
    },
    ProposalStatus.REJECTED: set(),
    ProposalStatus.SUPERSEDED: set(),
    ProposalStatus.RETRACTED: set(),
}
_RISK_RANK = {
    ProposalRiskLevel.LOW: 0,
    ProposalRiskLevel.MODERATE: 1,
    ProposalRiskLevel.HIGH: 2,
    ProposalRiskLevel.CRITICAL: 3,
}
_WEAKNESS_PRIORITY = {
    WeaknessPriority.INFORMATIONAL: 10,
    WeaknessPriority.LOW: 25,
    WeaknessPriority.MEDIUM: 50,
    WeaknessPriority.HIGH: 75,
    WeaknessPriority.CRITICAL: 100,
}
_DISALLOWED_TEXT = (
    "diff --git",
    "apply_patch",
    "git commit",
    "git push",
    "rm -rf",
    "sudo ",
    "curl ",
    "wget ",
    "password=",
    "api_key=",
    "secret=",
    "disable verifier",
    "automatic approval",
)


def _hash(values: Iterable[str]) -> str:
    return sha256("\n".join(values).encode()).hexdigest()


def _stable_hash(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class ProposalTypeRegistry:
    def __init__(self, records: tuple[ProposalTypeRegistration, ...] | None = None) -> None:
        values = records or default_type_registrations()
        self._items = {item.proposal_type: item for item in values}
        if len(self._items) != len(values) or set(self._items) != set(HarnessProposalType):
            raise ProposalValidationError("proposal registry must contain every type exactly once")

    def resolve(self, proposal_type: HarnessProposalType) -> ProposalTypeRegistration:
        try:
            return self._items[proposal_type]
        except KeyError as error:
            raise ProposalValidationError(f"unsupported proposal type: {proposal_type}") from error

    @property
    def snapshot_hash(self) -> str:
        return _hash(item.content_hash for item in self.list())

    def list(self) -> tuple[ProposalTypeRegistration, ...]:
        return tuple(self._items[item] for item in sorted(self._items, key=str))


def default_type_registrations() -> tuple[ProposalTypeRegistration, ...]:
    tier_zero = {HarnessProposalType.BENCHMARK_CHANGE, HarnessProposalType.DOCUMENTATION_CHANGE}
    tier_two = {
        HarnessProposalType.CONFIGURATION_CHANGE,
        HarnessProposalType.SOURCE_CODE_CHANGE,
        HarnessProposalType.TOOL_DEFINITION_CHANGE,
    }
    tier_three = {HarnessProposalType.VERIFIER_CHANGE}
    repository_types = tier_zero | {
        HarnessProposalType.SOURCE_CODE_CHANGE,
        HarnessProposalType.TOOL_DEFINITION_CHANGE,
        HarnessProposalType.VERIFIER_CHANGE,
    }
    records = []
    for proposal_type in HarnessProposalType:
        tier = (
            ChangeSurfaceTier.TIER_3
            if proposal_type in tier_three
            else ChangeSurfaceTier.TIER_2
            if proposal_type in tier_two
            else ChangeSurfaceTier.TIER_0
            if proposal_type in tier_zero
            else ChangeSurfaceTier.TIER_1
        )
        operation_type: Literal["artifact_revision", "configuration_value", "repository_file"] = (
            "repository_file"
            if proposal_type in repository_types
            else "configuration_value"
            if proposal_type is HarnessProposalType.CONFIGURATION_CHANGE
            else "artifact_revision"
        )
        records.append(
            ProposalTypeRegistration(
                proposal_type=proposal_type,
                supported_weakness_types=("*",),
                change_surface_tier=tier,
                template_id=f"proposal-template-{proposal_type.value}",
                template_version=1,
                operation_type=operation_type,
                allowed_target_identity_kinds=(proposal_type.value.removesuffix("_change"),),
                mandatory_verifier_capabilities=MANDATORY_PROPOSAL_VERIFIERS,
                mandatory_validation_sections=(
                    "target",
                    "historical_regression",
                    "unrelated_domain",
                    "security",
                    "recovery",
                ),
                mandatory_rollback_sections=("baseline", "operations", "verification"),
                provider_assistance_permitted=True,
                dependency_requirements=(),
                license_requirements=("Apache-2.0 compatible",),
            )
        )
    return tuple(records)


def proposal_signature(
    source: ProposalSourceSnapshot,
    proposal_type: HarnessProposalType,
    change: ChangeSpecification,
    template_version: int,
) -> str:
    return _stable_hash(
        {
            "schema_version": 1,
            "weakness_id": str(source.weakness_id),
            "weakness_revision": source.weakness_revision,
            "weakness_signature": source.weakness_record.signature_hash,
            "proposal_type": proposal_type.value,
            "change_surface": change.change_surface,
            "current_identity": change.current_identity,
            "current_revision": change.current_revision,
            "scope": {
                "files": sorted(change.allowed_files),
                "configuration_keys": sorted(change.allowed_configuration_keys),
                "registry_targets": sorted(change.allowed_registry_targets),
            },
            "template_version": template_version,
        }
    )


async def assess_eligibility(
    source: WeaknessProposalSourcePort,
    weakness_id: UUID,
    revision: int,
    *,
    configuration: ProposalConfiguration,
    policy_hash: str,
) -> ProposalEligibilityResult:
    exact = await source.get_exact_weakness_revision(weakness_id, revision)
    current = await source.get_current_weakness_revision(weakness_id)
    queue = await source.get_exact_queue_entry(weakness_id, revision)
    evidence = await source.get_exact_evidence_package(weakness_id, revision)
    impact = await source.get_exact_impact_score(weakness_id, revision)
    source_hashes = tuple(
        item
        for item in (
            exact.content_hash if exact else None,
            queue.content_hash if queue else None,
            evidence.content_hash if evidence else None,
            impact.content_hash if impact else None,
        )
        if item is not None
    )
    reason = EligibilityReason.ELIGIBLE_CONFIRMED
    eligible = True
    if exact is None or current is None or queue is None:
        eligible, reason = False, EligibilityReason.SOURCE_INTEGRITY
    elif configuration.eligibility.require_current_revision and current.revision != revision:
        eligible, reason = False, EligibilityReason.STALE_REVISION
    elif evidence is None or exact.evidence_package_hash != evidence.content_hash:
        eligible, reason = False, EligibilityReason.MISSING_EVIDENCE
    elif impact is None or exact.impact_score_hash != impact.content_hash:
        eligible, reason = False, EligibilityReason.MISSING_IMPACT
    elif queue.weakness_revision_hash != exact.content_hash:
        eligible, reason = False, EligibilityReason.SOURCE_INTEGRITY
    elif exact.status is WeaknessStatus.CANDIDATE:
        eligible = configuration.eligibility.high_impact_candidates and impact.priority in {
            WeaknessPriority.HIGH,
            WeaknessPriority.CRITICAL,
        }
        reason = (
            EligibilityReason.ELIGIBLE_POLICY_CANDIDATE
            if eligible
            else EligibilityReason.CANDIDATE_DISABLED
        )
    elif exact.status is not WeaknessStatus.CONFIRMED:
        eligible, reason = False, EligibilityReason.STATUS_INELIGIBLE
    return ProposalEligibilityResult(
        eligible=eligible,
        reason=reason,
        policy_snapshot_hash=policy_hash,
        source_hashes=source_hashes,
    )


async def freeze_source_snapshot(
    source: WeaknessProposalSourcePort,
    weakness_id: UUID,
    revision: int,
    proposal_id: UUID,
    *,
    configuration: ProposalConfiguration,
    policy_hash: str,
    created_at: datetime,
) -> ProposalSourceSnapshot:
    eligibility = await assess_eligibility(
        source,
        weakness_id,
        revision,
        configuration=configuration,
        policy_hash=policy_hash,
    )
    if not eligibility.eligible:
        raise ProposalSourceError(eligibility.reason.value)
    weakness = await source.get_exact_weakness_revision(weakness_id, revision)
    queue = await source.get_exact_queue_entry(weakness_id, revision)
    evidence = await source.get_exact_evidence_package(weakness_id, revision)
    impact = await source.get_exact_impact_score(weakness_id, revision)
    reproduction = await source.get_reproduction_assessment(weakness_id, revision)
    if (
        weakness is None
        or queue is None
        or evidence is None
        or impact is None
        or reproduction is None
    ):
        raise ProposalSourceError("incomplete exact weakness source")
    benchmarks = await source.get_related_benchmark_candidates(weakness_id, revision)
    replays = await source.get_related_replay_candidates(weakness_id, revision)
    registries = await source.get_required_registry_snapshots()
    source_hashes = tuple(
        sorted(
            {
                *eligibility.source_hashes,
                reproduction.content_hash,
                *(item.content_hash for item in benchmarks),
                *(item.content_hash for item in replays),
                *registries.values(),
            }
        )
    )
    return ProposalSourceSnapshot(
        proposal_id=proposal_id,
        weakness_id=weakness_id,
        weakness_revision=revision,
        weakness_status=weakness.status,
        weakness_record=weakness,
        weakness_queue_entry=queue,
        weakness_evidence_package=evidence,
        impact_score=impact,
        reproduction_assessment=reproduction,
        related_benchmark_candidates=benchmarks,
        related_replay_candidates=replays,
        source_hashes=source_hashes,
        registry_snapshots=registries,
        policy_snapshot=policy_hash,
        created_at=created_at,
    )


def build_change_specification(
    source: ProposalSourceSnapshot,
    registration: ProposalTypeRegistration,
) -> ChangeSpecification:
    proposal_type = registration.proposal_type
    current_identity = (
        source.weakness_record.affected_components[0]
        if source.weakness_record.affected_components
        else proposal_type.value
    )
    current_revision = source.weakness_record.signature_hash
    artifact_hash = _stable_hash(
        {
            "template": registration.template_id,
            "source": source.snapshot_hash,
            "proposal_type": proposal_type.value,
        }
    )
    allowed_files: tuple[str, ...] = ()
    allowed_keys: tuple[str, ...] = ()
    allowed_targets: tuple[str, ...] = ()
    if registration.operation_type == "repository_file":
        suffix = "md" if proposal_type is HarnessProposalType.DOCUMENTATION_CHANGE else "py"
        allowed_files = (f"proposal-scope/{proposal_type.value}.{suffix}",)
        operation: TypedProposalOperation = RepositoryFileOperation(
            target_identity=current_identity,
            target_revision=current_revision,
            allowed_files=allowed_files,
            description_artifact_hash=artifact_hash,
        )
    elif registration.operation_type == "configuration_value":
        allowed_keys = (f"harness_proposals.{proposal_type.value}",)
        operation = ConfigurationValueOperation(
            target_identity=current_identity,
            target_revision=current_revision,
            configuration_key=allowed_keys[0],
            proposed_value_artifact_hash=artifact_hash,
        )
    else:
        allowed_targets = (current_identity,)
        operation = ArtifactRevisionOperation(
            target_identity=current_identity,
            target_revision=current_revision,
            proposed_artifact_hash=artifact_hash,
        )
    return ChangeSpecification(
        change_surface=proposal_type.value,
        change_surface_tier=registration.change_surface_tier,
        current_identity=current_identity,
        current_revision=current_revision,
        proposed_operation=operation,
        proposed_schema=registration.content_hash,
        proposed_body_artifact=artifact_hash,
        allowed_files=allowed_files,
        allowed_configuration_keys=allowed_keys,
        allowed_registry_targets=allowed_targets,
        forbidden_surfaces=(
            "active destination state",
            "credentials and permissions",
            "approval policy",
            "active repository checkout",
        ),
        expected_artifacts=("proposal body", "future validation evidence"),
        compatibility_requirements=("preserve existing public contracts",),
    )


def analyze_minimality(
    source: ProposalSourceSnapshot, change: ChangeSpecification
) -> MinimalityAssessment:
    included = (change.change_surface,)
    omnibus = () if len(included) == 1 else ("multiple unrelated change surfaces",)
    return MinimalityAssessment(
        primary_weakness_signature=source.weakness_record.signature_hash,
        included_surfaces=included,
        excluded_surfaces=change.forbidden_surfaces,
        required_compatibility_changes=change.compatibility_requirements,
        optional_changes_split_out=("unrelated enhancements",),
        is_effect_isolatable=True,
        is_exact_rollback_possible=True,
        omnibus_reasons=omnibus,
        result="passed" if not omnibus else "failed",
    )


def build_expected_benefit(source: ProposalSourceSnapshot) -> ExpectedBenefit:
    return ExpectedBenefit(
        target_metrics=("weakness_reproduction_rate",),
        baseline_values={"weakness_impact_score": source.impact_score.final_score},
        expected_direction=ExpectedDirection.ELIMINATE_FAILURE,
        minimum_material_improvement=Decimal("0.05"),
        applicable_task_signatures=(source.weakness_record.signature_hash,),
        limitations=("Expected benefit is unverified until a Sprint 19 experiment.",),
        source_refs=source.source_hashes,
        hypothesis_only=True,
    )


def build_alternatives(
    source: ProposalSourceSnapshot, change: ChangeSpecification
) -> tuple[ProposalAlternative, ...]:
    values = (
        ("no_change", "Retain the exact baseline and continue monitoring."),
        ("more_evidence", "Collect more bounded evidence before implementation."),
        ("dependency_free", "Use the existing Cognitive OS implementation surface."),
    )
    return tuple(
        ProposalAlternative(
            alternative_id=uuid5(
                NAMESPACE_URL,
                f"proposal-alternative:{source.proposal_id}:{kind}:{change.content_hash}",
            ),
            kind=kind,
            summary=summary,
            change_surface=change.change_surface,
            expected_tradeoffs=("May reduce expected benefit or increase evidence latency.",),
            required_dependencies=(),
            validation_delta=("Recalculate the future experiment matrix.",),
            rollback_delta=("Exact baseline remains the rollback target.",),
            risk_delta=("No authority expansion.",),
            source_refs=source.source_hashes,
        )
        for kind, summary in values
    )


def build_risk_assessment(change: ChangeSpecification) -> ProposalRiskAssessment:
    tier_risk = {
        ChangeSurfaceTier.TIER_0: ProposalRiskLevel.LOW,
        ChangeSurfaceTier.TIER_1: ProposalRiskLevel.MODERATE,
        ChangeSurfaceTier.TIER_2: ProposalRiskLevel.HIGH,
        ChangeSurfaceTier.TIER_3: ProposalRiskLevel.CRITICAL,
    }
    return ProposalRiskAssessment(
        risk_level=tier_risk[change.change_surface_tier],
        blast_radius=(change.current_identity, *change.compatibility_requirements),
        affected_authorities=("destination subsystem owner",),
        affected_tasks=("tasks matching the exact weakness signature",),
        affected_data=("future isolated experiment data only",),
        security_risks=("scope or authority expansion",),
        privacy_risks=("proposal artifact disclosure",),
        compatibility_risks=("public contract regression",),
        performance_risks=("latency or resource regression",),
        recovery_risks=("incomplete baseline restoration",),
        unknowns=("actual candidate effect remains unmeasured",),
        required_approvals=("explicit proposal reviewer", "future promotion reviewer"),
        change_surface_tier=change.change_surface_tier,
    )


def build_validation_plan(change: ChangeSpecification) -> ProposalValidationPlan:
    migration = (
        ("migration upgrade downgrade re-upgrade",)
        if change.change_surface_tier is ChangeSurfaceTier.TIER_3
        else ("confirm no migration change",)
    )
    return ProposalValidationPlan(
        target_benchmarks=("sprint18-proposal-target",),
        historical_regression_manifests=("sprint17-weakness-ci",),
        unrelated_domain_manifests=("sprint7-ci",),
        security_gates=("bandit", "secret scan", "authority invariant"),
        policy_gates=("explicit approval", "destination ownership"),
        migration_gates=migration,
        dependency_gates=("locked dependency audit",),
        performance_gates=("bounded CPU and memory",),
        cost_latency_gates=("no material cost or latency regression",),
        backup_restore_gates=("isolated backup and restore",),
        acceptance_thresholds={"case_pass_rate": Decimal("1")},
        failure_conditions=("security, policy, source, or destination authority failure",),
        required_verifiers=MANDATORY_PROPOSAL_VERIFIERS,
        required_artifacts=("candidate report", "regression report", "rollback evidence"),
    )


def build_rollback_plan(
    source: ProposalSourceSnapshot, change: ChangeSpecification
) -> ProposalRollbackPlan:
    rollback_type = (
        RollbackType.REPOSITORY_REVERT_PLAN
        if isinstance(change.proposed_operation, RepositoryFileOperation)
        else RollbackType.CONFIGURATION_RESTORE
        if isinstance(change.proposed_operation, ConfigurationValueOperation)
        else RollbackType.DECLARATIVE_REVISION
    )
    return ProposalRollbackPlan(
        rollback_type=rollback_type,
        baseline_references=(change.current_revision, source.snapshot_hash),
        state_snapshot_requirements=("exact destination baseline",),
        artifact_requirements=(change.proposed_body_artifact,),
        rollback_commands_as_typed_operations=(
            RollbackOperation(
                operation_type=(
                    "restore_configuration"
                    if rollback_type is RollbackType.CONFIGURATION_RESTORE
                    else "restore_revision"
                ),
                target_identity=change.current_identity,
                baseline_reference=change.current_revision,
            ),
        ),
        verification_steps=("compare exact baseline hashes", "run future recovery gate"),
        maximum_rollback_time=900,
        manual_steps=("Operator confirms restoration evidence.",),
        limitations=("Sprint 18 describes rollback but does not execute it.",),
    )


def build_generated_revision(
    identity: HarnessProposalIdentity,
    source: ProposalSourceSnapshot,
    registration: ProposalTypeRegistration,
    *,
    actor: str,
    created_at: datetime,
    artifact_hashes: tuple[str, ...],
    generation_mode: ProposalGenerationMode = ProposalGenerationMode.DETERMINISTIC,
) -> HarnessProposalRevision:
    change = build_change_specification(source, registration)
    return HarnessProposalRevision(
        proposal_id=identity.proposal_id,
        revision=1,
        status=ProposalStatus.GENERATED,
        generation_mode=generation_mode,
        proposal_signature=proposal_signature(
            source, identity.proposal_type, change, registration.template_version
        ),
        source_snapshot=source,
        change_specification=change,
        expected_benefit=build_expected_benefit(source),
        risk_assessment=build_risk_assessment(change),
        validation_plan=build_validation_plan(change),
        rollback_plan=build_rollback_plan(source, change),
        alternatives=build_alternatives(source, change),
        minimality_assessment=analyze_minimality(source, change),
        limitations=("Proposal-only; no implementation or destination write occurred.",),
        artifact_refs=artifact_hashes,
        created_at=created_at,
        created_by=actor,
        reason="deterministic proposal generation",
    )


def merge_provider_draft(
    revision: HarnessProposalRevision,
    draft: ProviderProposalDraft,
    *,
    allowed_source_ids: tuple[str, ...],
) -> HarnessProposalRevision:
    expected_type = HarnessProposalType(revision.change_specification.change_surface)
    if draft.proposal_type is not expected_type:
        raise ProposalAuthorityError("provider changed the registered proposal type")
    if set(draft.cited_host_source_ref_ids) - set(allowed_source_ids):
        raise ProposalAuthorityError("provider cited an unknown source")
    serialized = draft.model_dump_json().lower()
    if any(marker in serialized for marker in _DISALLOWED_TEXT):
        raise ProposalAuthorityError(
            "provider draft contains an executable or privileged instruction"
        )
    if set(draft.affected_component_hints) - {
        revision.change_specification.current_identity,
        *revision.change_specification.allowed_registry_targets,
    }:
        raise ProposalAuthorityError("provider expanded proposal scope")
    return revision.model_copy(
        update={
            "generation_mode": ProposalGenerationMode.PROVIDER_ASSISTED,
            "limitations": tuple(sorted({*revision.limitations, *draft.limitations})),
            "content_hash": "",
        }
    )


def verify_proposal(
    revision: HarnessProposalRevision,
    *,
    registry: ProposalTypeRegistry,
    created_at: datetime,
    proposal_revision: int | None = None,
) -> ProposalVerifierBundle:
    serialized = revision.model_dump_json().lower()
    failures: dict[str, str] = {}
    source = revision.source_snapshot
    if source.snapshot_hash != source.canonical_hash(exclude={"snapshot_hash"}):
        failures["proposal.source_integrity"] = "source_hash_mismatch"
    if source.weakness_revision != source.weakness_record.revision:
        failures["proposal.weakness_revision_integrity"] = "weakness_revision_mismatch"
    if source.weakness_status not in {WeaknessStatus.CONFIRMED, WeaknessStatus.CANDIDATE}:
        failures["proposal.weakness_eligibility"] = "weakness_status_ineligible"
    registration = registry.resolve(
        HarnessProposalType(revision.change_specification.change_surface)
    )
    if registration.change_surface_tier is not revision.change_specification.change_surface_tier:
        failures["proposal.change_surface_allowlist"] = "change_surface_tier_mismatch"
    if not isinstance(
        revision.change_specification.proposed_operation,
        (ArtifactRevisionOperation, ConfigurationValueOperation, RepositoryFileOperation),
    ):
        failures["proposal.typed_operation_integrity"] = "untyped_operation"
    if revision.minimality_assessment.result != "passed":
        failures["proposal.minimality"] = "omnibus_or_nonisolatable"
    if not revision.risk_assessment.blast_radius:
        failures["proposal.blast_radius_completeness"] = "missing_blast_radius"
    if not revision.expected_benefit.hypothesis_only:
        failures["proposal.expected_benefit_hypothesis"] = "benefit_claimed_verified"
    if len(revision.risk_assessment.unknowns) == 0:
        failures["proposal.risk_completeness"] = "missing_unknowns"
    if {item.kind for item in revision.alternatives}.isdisjoint({"no_change"}) or {
        item.kind for item in revision.alternatives
    }.isdisjoint({"more_evidence"}):
        failures["proposal.alternatives_completeness"] = "required_alternative_missing"
    if not revision.validation_plan.failure_conditions:
        failures["proposal.validation_plan_completeness"] = "failure_conditions_missing"
    if not revision.rollback_plan.rollback_commands_as_typed_operations:
        failures["proposal.rollback_plan_completeness"] = "rollback_operations_missing"
    if any(marker in serialized for marker in ("caused by model", "proves that")):
        failures["proposal.no_unsupported_causal_claim"] = "unsupported_causal_claim"
    if any(marker in serialized for marker in _DISALLOWED_TEXT):
        failures["proposal.no_unrestricted_instruction"] = "unrestricted_instruction"
    if "permission expansion" in serialized or "grant permission" in serialized:
        failures["proposal.no_permission_expansion"] = "permission_expansion"
    if not revision.artifact_refs or any(len(item) != 64 for item in revision.artifact_refs):
        failures["proposal.artifact_hash_integrity"] = "artifact_hash_invalid"
    findings = tuple(
        ProposalVerifierFinding(
            capability_id=capability,
            status=(
                ProposalVerifierStatus.FAILED
                if capability in failures
                else ProposalVerifierStatus.PASSED
            ),
            severity="error" if capability in failures else "info",
            reason_code=failures.get(capability, "verified"),
            input_hash=revision.content_hash,
        )
        for capability in MANDATORY_PROPOSAL_VERIFIERS
    )
    return ProposalVerifierBundle(
        proposal_id=revision.proposal_id,
        proposal_revision=proposal_revision or revision.revision,
        input_hash=revision.content_hash,
        findings=findings,
        status=(ProposalVerifierStatus.FAILED if failures else ProposalVerifierStatus.PASSED),
        verifier_registry_hash=_hash(MANDATORY_PROPOSAL_VERIFIERS),
        created_at=created_at,
    )


def transition_revision(
    current: HarnessProposalRevision,
    status: ProposalStatus,
    *,
    actor: str,
    reason: str,
    created_at: datetime,
    verifier_bundle: ProposalVerifierBundle | None = None,
) -> HarnessProposalRevision:
    if actor.lower().startswith(("provider", "model")):
        raise ProposalAuthorityError("provider actors cannot advance proposal lifecycle")
    if status not in _LEGAL_TRANSITIONS[current.status]:
        raise ProposalConflictError(f"illegal proposal transition: {current.status} -> {status}")
    bundle = verifier_bundle or current.verifier_bundle
    if status in {
        ProposalStatus.VALIDATED,
        ProposalStatus.STAGED_FOR_REVIEW,
        ProposalStatus.APPROVED_FOR_EXPERIMENT,
    } and (bundle is None or bundle.status is not ProposalVerifierStatus.PASSED):
        raise ProposalValidationError("proposal transition requires a passing verifier bundle")
    values = current.model_dump(mode="python", exclude={"content_hash"})
    values.update(
        revision=current.revision + 1,
        previous_revision=current.revision,
        status=status,
        verifier_bundle=bundle,
        created_at=created_at,
        created_by=actor,
        reason=reason,
    )
    return HarnessProposalRevision.model_validate(values)


def queue_sort_key(entry: ProposalQueueEntry) -> tuple[object, ...]:
    return (
        entry.blocked_by_dependency,
        -entry.operator_priority,
        -entry.weakness_priority,
        -entry.evidence_confidence,
        entry.risk_rank,
        -entry.expected_value_rank,
        entry.experiment_cost_rank,
        entry.blast_radius_rank,
        -entry.rollback_readiness_rank,
        entry.dependency_count,
        entry.canonical_name,
        str(entry.proposal_id),
        entry.proposal_revision,
    )


def build_queue_entry(
    identity: HarnessProposalIdentity,
    revision: HarnessProposalRevision,
    *,
    operator_priority: int,
    created_at: datetime,
) -> ProposalQueueEntry:
    if revision.status not in {
        ProposalStatus.VALIDATED,
        ProposalStatus.STAGED_FOR_REVIEW,
        ProposalStatus.APPROVED_FOR_EXPERIMENT,
    }:
        raise ProposalValidationError("proposal revision is not queue-eligible")
    return ProposalQueueEntry(
        queue_entry_id=uuid5(
            NAMESPACE_URL,
            f"proposal-queue:{revision.proposal_id}:{revision.revision}:{revision.content_hash}",
        ),
        proposal_id=revision.proposal_id,
        proposal_revision=revision.revision,
        proposal_content_hash=revision.content_hash,
        proposal_status=revision.status,
        blocked_by_dependency=False,
        operator_priority=operator_priority,
        weakness_priority=_WEAKNESS_PRIORITY[
            revision.source_snapshot.weakness_queue_entry.priority
        ],
        evidence_confidence=Decimal("1") - revision.source_snapshot.impact_score.uncertainty.value,
        risk_rank=_RISK_RANK[revision.risk_assessment.risk_level],
        expected_value_rank=int(revision.source_snapshot.impact_score.final_score),
        experiment_cost_rank=50,
        blast_radius_rank=25 * (_RISK_RANK[revision.risk_assessment.risk_level] + 1),
        rollback_readiness_rank=100,
        dependency_count=0,
        canonical_name=identity.canonical_name,
        created_at=created_at,
    )


def build_queue_snapshot(
    entries: tuple[ProposalQueueEntry, ...], *, policy_hash: str, created_at: datetime
) -> ProposalQueueSnapshot:
    removed = {(item.proposal_id, item.proposal_revision) for item in entries if not item.active}
    active = tuple(
        item
        for item in entries
        if item.active
        and item.proposal_status not in _TERMINAL
        and (item.proposal_id, item.proposal_revision) not in removed
    )
    ordered = tuple(sorted(active, key=queue_sort_key))
    return ProposalQueueSnapshot(
        snapshot_id=uuid5(
            NAMESPACE_URL,
            f"proposal-queue-snapshot:{policy_hash}:{_hash(item.content_hash for item in ordered)}",
        ),
        entries=ordered,
        policy_hash=policy_hash,
        created_at=created_at,
    )


class HarnessProposalService:
    def __init__(
        self,
        repository: ProposalRepositoryPort,
        source: WeaknessProposalSourcePort,
        *,
        registry: ProposalTypeRegistry | None = None,
        configuration: ProposalConfiguration | None = None,
        artifacts: ArtifactStorePort | None = None,
        provider: ProposalGeneratorPort | None = None,
        event_service: ProposalEventService | None = None,
    ) -> None:
        self._repository = repository
        self._source = source
        self.registry = registry or ProposalTypeRegistry()
        self.configuration = configuration or ProposalConfiguration()
        self._artifacts = artifacts
        self._provider = provider
        self._event_service = event_service
        self._provider_fallback_count = 0

    async def _emit(self, payload: EventPayload, proposal_id: UUID) -> None:
        if self._event_service is not None:
            await self._event_service.append(
                proposal_id,
                payload,
                correlation_id=proposal_id,
            )

    async def _record_access(
        self,
        revision: HarnessProposalRevision,
        access_type: ProposalAccessType,
        *,
        actor: str,
        reason: str,
        accessed_at: datetime,
    ) -> None:
        await self._repository.record_access(
            ProposalAccessRecord(
                access_id=uuid5(
                    NAMESPACE_URL,
                    f"proposal-access:{revision.proposal_id}:{revision.revision}:"
                    f"{access_type.value}:{actor}:{reason}:{accessed_at.isoformat()}",
                ),
                access_type=access_type,
                actor_id=actor,
                proposal_id=revision.proposal_id,
                proposal_revision=revision.revision,
                proposal_content_hash=revision.content_hash,
                reason=reason,
                accessed_at=accessed_at,
            )
        )

    async def create_from_weakness(
        self,
        weakness_id: UUID,
        weakness_revision: int,
        proposal_type: HarnessProposalType,
        *,
        actor: str,
        created_at: datetime | None = None,
        provider_assisted: bool = False,
    ) -> HarnessProposalRevision:
        now = created_at or utc_now()
        registration = self.registry.resolve(proposal_type)
        proposal_id = uuid5(
            NAMESPACE_URL,
            f"harness-proposal:{weakness_id}:{weakness_revision}:{proposal_type.value}",
        )
        policy_hash = _stable_hash(self.configuration.model_dump(mode="json"))
        source = await freeze_source_snapshot(
            self._source,
            weakness_id,
            weakness_revision,
            proposal_id,
            configuration=self.configuration,
            policy_hash=policy_hash,
            created_at=now,
        )
        identity = HarnessProposalIdentity(
            proposal_id=proposal_id,
            canonical_name=f"{proposal_type.value}:{source.weakness_record.signature_hash[:12]}",
            proposal_type=proposal_type,
            scope=(
                source.weakness_record.affected_components[0]
                if source.weakness_record.affected_components
                else proposal_type.value
            ),
            created_at=now,
            created_by=actor,
        )
        artifact_hashes = (source.snapshot_hash,)
        if self._artifacts is not None:
            artifact = await self._artifacts.put_bytes(
                source.canonical_json().encode(), media_type="application/json"
            )
            artifact_hashes = (artifact.content_hash,)
        generated = build_generated_revision(
            identity,
            source,
            registration,
            actor=actor,
            created_at=now,
            artifact_hashes=artifact_hashes,
        )
        duplicate = await self._repository.find_active_signature(generated.proposal_signature)
        if duplicate is not None:
            if duplicate.proposal_id == generated.proposal_id:
                return duplicate
            raise ProposalConflictError("duplicate active proposal signature")
        active_for_weakness = [
            item
            for item in await self._repository.list_current()
            if item.source_snapshot.weakness_id == weakness_id and item.status not in _TERMINAL
        ]
        if len(active_for_weakness) >= self.configuration.generation.max_proposals_per_weakness:
            raise ProposalConflictError("maximum active proposals for weakness reached")
        if provider_assisted:
            if (
                not self.configuration.generation.provider_assisted_enabled
                or self._provider is None
            ):
                raise ProposalAuthorityError("provider-assisted generation is disabled")
            source_ids = tuple(str(item) for item in source.source_hashes)
            try:
                draft = await self._provider.draft(source, allowed_source_ids=source_ids)
                generated = merge_provider_draft(generated, draft, allowed_source_ids=source_ids)
            except ProposalAuthorityError:
                raise
            except (OSError, TimeoutError):
                self._provider_fallback_count += 1
        await self._repository.create(identity, generated)
        await self._repository.record_source(source)
        await self._emit(
            ProposalCreated(
                proposal_id=proposal_id,
                proposal_revision=generated.revision,
                source_snapshot_hash=source.snapshot_hash,
                proposal_content_hash=generated.content_hash,
                actor_identity=actor,
                actor_authority="proposal-operator",
                summary="Deterministic proposal created without destination writes.",
                occurred_at=now,
            ),
            proposal_id,
        )
        bundle = verify_proposal(
            generated,
            registry=self.registry,
            created_at=now,
            proposal_revision=2,
        )
        if bundle.status is not ProposalVerifierStatus.PASSED:
            raise ProposalValidationError("mandatory proposal verifier bundle failed")
        validated = transition_revision(
            generated,
            ProposalStatus.VALIDATED,
            actor=actor,
            reason="mandatory verifier bundle passed",
            created_at=now,
            verifier_bundle=bundle,
        )
        await self._repository.append(validated, expected_revision=1)
        await self._emit(
            ProposalRevisionAppended(
                proposal_id=proposal_id,
                proposal_revision=validated.revision,
                source_snapshot_hash=source.snapshot_hash,
                proposal_content_hash=validated.content_hash,
                actor_identity=actor,
                actor_authority="proposal-operator",
                summary="Immutable proposal revision appended.",
                occurred_at=now,
            ),
            proposal_id,
        )
        await self._emit(
            ProposalValidated(
                proposal_id=proposal_id,
                proposal_revision=validated.revision,
                source_snapshot_hash=source.snapshot_hash,
                proposal_content_hash=validated.content_hash,
                actor_identity=actor,
                actor_authority="proposal-operator",
                summary="All mandatory proposal verifiers passed.",
                occurred_at=now,
                verifier_bundle_hash=bundle.content_hash,
            ),
            proposal_id,
        )
        await self._repository.record_manifest(
            ProposalRunManifest(
                proposal_id=proposal_id,
                proposal_revision=validated.revision,
                source_snapshot_hash=source.snapshot_hash,
                registry_hash=self.registry.snapshot_hash,
                policy_hash=policy_hash,
                proposal_hash=validated.content_hash,
                verifier_bundle_hash=bundle.content_hash,
                artifact_hashes=validated.artifact_refs,
                no_destination_writes=True,
                created_at=now,
            )
        )
        return validated

    async def get_exact(
        self,
        proposal_id: UUID,
        revision: int,
        *,
        actor: str = "system",
        reason: str = "exact proposal read",
        accessed_at: datetime | None = None,
    ) -> HarnessProposalRevision | None:
        exact = await self._repository.get_exact(proposal_id, revision)
        if exact is not None:
            await self._record_access(
                exact,
                ProposalAccessType.READ,
                actor=actor,
                reason=reason,
                accessed_at=accessed_at or utc_now(),
            )
        return exact

    async def get_current(
        self,
        proposal_id: UUID,
        *,
        actor: str = "system",
        reason: str = "current proposal read",
        accessed_at: datetime | None = None,
    ) -> HarnessProposalRevision | None:
        current = await self._repository.get_current(proposal_id)
        if current is not None:
            await self._record_access(
                current,
                ProposalAccessType.READ,
                actor=actor,
                reason=reason,
                accessed_at=accessed_at or utc_now(),
            )
        return current

    async def verify_replay(
        self,
        proposal_id: UUID,
        revision: int,
        *,
        created_at: datetime | None = None,
    ) -> ProposalVerifierBundle:
        exact = await self._repository.get_exact(proposal_id, revision)
        if exact is None:
            raise ProposalSourceError("exact proposal revision not found")
        now = created_at or utc_now()
        await self._record_access(
            exact,
            ProposalAccessType.READ,
            actor="verifier-replay",
            reason="deterministic verifier replay",
            accessed_at=now,
        )
        return verify_proposal(
            exact,
            registry=self.registry,
            created_at=now,
            proposal_revision=revision,
        )

    async def transition(
        self,
        proposal_id: UUID,
        expected_revision: int,
        status: ProposalStatus,
        *,
        actor: str,
        reason: str,
        created_at: datetime | None = None,
    ) -> HarnessProposalRevision:
        current = await self._repository.get_current(proposal_id)
        if current is None or current.revision != expected_revision:
            raise ProposalConflictError("proposal revision compare-and-set failed")
        if status is ProposalStatus.APPROVED_FOR_EXPERIMENT:
            raise ProposalAuthorityError("experiment approval requires an exact review record")
        now = created_at or utc_now()
        revision = transition_revision(
            current,
            status,
            actor=actor,
            reason=reason,
            created_at=now,
        )
        await self._repository.append(revision, expected_revision=expected_revision)
        await self._emit(
            ProposalRevisionAppended(
                proposal_id=proposal_id,
                proposal_revision=revision.revision,
                source_snapshot_hash=revision.source_snapshot.snapshot_hash,
                proposal_content_hash=revision.content_hash,
                actor_identity=actor,
                actor_authority="proposal-operator",
                summary=f"Proposal lifecycle advanced to {status.value}.",
                occurred_at=now,
            ),
            proposal_id,
        )
        event_types = {
            ProposalStatus.STAGED_FOR_REVIEW: ProposalStagedForReview,
            ProposalStatus.REJECTED: ProposalRejected,
            ProposalStatus.SUPERSEDED: ProposalSuperseded,
            ProposalStatus.RETRACTED: ProposalRetracted,
        }
        event_type = event_types.get(status)
        if event_type is not None:
            await self._emit(
                event_type(
                    proposal_id=proposal_id,
                    proposal_revision=revision.revision,
                    source_snapshot_hash=revision.source_snapshot.snapshot_hash,
                    proposal_content_hash=revision.content_hash,
                    actor_identity=actor,
                    actor_authority="proposal-operator",
                    summary=f"Proposal transitioned to {status.value}.",
                    occurred_at=now,
                ),
                proposal_id,
            )
        return revision

    async def record_review(
        self,
        proposal_id: UUID,
        expected_revision: int,
        decision: ProposalReviewDecision,
        *,
        reviewer: str,
        reviewer_authority: str,
        rationale: str,
        created_at: datetime | None = None,
    ) -> HarnessProposalRevision:
        now = created_at or utc_now()
        current = await self._repository.get_current(proposal_id)
        if current is None or current.revision != expected_revision:
            raise ProposalConflictError("stale proposal review")
        if (
            current.status is not ProposalStatus.STAGED_FOR_REVIEW
            or current.verifier_bundle is None
        ):
            raise ProposalValidationError("only staged exact revisions may be reviewed")
        review = ProposalReview(
            review_id=uuid5(
                NAMESPACE_URL,
                f"proposal-review:{proposal_id}:{expected_revision}:{reviewer}:{decision.value}",
            ),
            proposal_id=proposal_id,
            proposal_revision=expected_revision,
            reviewer_identity=reviewer,
            reviewer_authority=reviewer_authority,
            review_decision=decision,
            rationale=rationale,
            required_changes=(),
            policy_snapshot_hash=current.source_snapshot.policy_snapshot,
            verifier_bundle_hash=current.verifier_bundle.content_hash,
            proposal_content_hash=current.content_hash,
            created_at=now,
        )
        await self._repository.record_review(review)
        status = (
            ProposalStatus.APPROVED_FOR_EXPERIMENT
            if decision is ProposalReviewDecision.APPROVE_FOR_EXPERIMENT
            else ProposalStatus.REJECTED
            if decision is ProposalReviewDecision.REJECT
            else None
        )
        if status is None:
            return current
        if status is ProposalStatus.APPROVED_FOR_EXPERIMENT:
            approved = transition_revision(
                current,
                status,
                actor=reviewer,
                reason=f"explicit review: {decision.value}",
                created_at=now,
            )
            await self._repository.append(approved, expected_revision=expected_revision)
            await self._emit(
                ProposalRevisionAppended(
                    proposal_id=proposal_id,
                    proposal_revision=approved.revision,
                    source_snapshot_hash=approved.source_snapshot.snapshot_hash,
                    proposal_content_hash=approved.content_hash,
                    actor_identity=reviewer,
                    actor_authority=reviewer_authority,
                    summary="Immutable reviewed proposal revision appended.",
                    occurred_at=now,
                ),
                proposal_id,
            )
            await self._emit(
                ProposalApprovedForExperiment(
                    proposal_id=proposal_id,
                    proposal_revision=approved.revision,
                    source_snapshot_hash=approved.source_snapshot.snapshot_hash,
                    proposal_content_hash=approved.content_hash,
                    actor_identity=reviewer,
                    actor_authority=reviewer_authority,
                    summary="Exact proposal revision approved for an isolated experiment only.",
                    occurred_at=now,
                    review_hash=review.content_hash,
                ),
                proposal_id,
            )
            return approved
        return await self.transition(
            proposal_id,
            expected_revision,
            status,
            actor=reviewer,
            reason=f"explicit review: {decision.value}",
            created_at=now,
        )

    async def enqueue(
        self,
        identity: HarnessProposalIdentity,
        expected_revision: int,
        *,
        operator_priority: int = 0,
        created_at: datetime | None = None,
    ) -> ProposalQueueEntry:
        revision = await self._repository.get_current(identity.proposal_id)
        if revision is None or revision.revision != expected_revision:
            raise ProposalConflictError("stale proposal queue request")
        entry = build_queue_entry(
            identity,
            revision,
            operator_priority=operator_priority,
            created_at=created_at or utc_now(),
        )
        await self._repository.record_queue(entry)
        await self._emit(
            ProposalQueued(
                proposal_id=revision.proposal_id,
                proposal_revision=revision.revision,
                source_snapshot_hash=revision.source_snapshot.snapshot_hash,
                proposal_content_hash=revision.content_hash,
                actor_identity="operator",
                actor_authority="proposal-queue-operator",
                summary="Exact proposal revision added to the deterministic review queue.",
                occurred_at=entry.created_at,
                queue_entry_hash=entry.content_hash,
            ),
            revision.proposal_id,
        )
        return entry

    async def remove_from_queue(
        self,
        proposal_id: UUID,
        expected_revision: int,
        *,
        actor: str,
        created_at: datetime | None = None,
    ) -> ProposalQueueEntry:
        if actor.lower().startswith(("provider", "model")):
            raise ProposalAuthorityError("provider actors cannot change proposal queue state")
        records = await self._repository.list_queue()
        if any(
            item.proposal_id == proposal_id
            and item.proposal_revision == expected_revision
            and not item.active
            for item in records
        ):
            raise ProposalConflictError("exact proposal queue entry is already inactive")
        matches = [
            item
            for item in records
            if item.proposal_id == proposal_id
            and item.proposal_revision == expected_revision
            and item.active
        ]
        if len(matches) != 1:
            raise ProposalConflictError("active exact proposal queue entry not found")
        current = matches[0]
        values = current.model_dump(mode="python", exclude={"content_hash"})
        values.update(
            queue_entry_id=uuid5(
                NAMESPACE_URL,
                f"proposal-queue-remove:{current.queue_entry_id}:{actor}",
            ),
            active=False,
            created_at=created_at or utc_now(),
        )
        removed = ProposalQueueEntry.model_validate(values)
        await self._repository.record_queue(removed)
        revision = await self._repository.get_exact(proposal_id, expected_revision)
        if revision is None:
            raise ProposalSourceError("exact queued proposal revision not found")
        await self._emit(
            ProposalQueueRemoved(
                proposal_id=proposal_id,
                proposal_revision=expected_revision,
                source_snapshot_hash=revision.source_snapshot.snapshot_hash,
                proposal_content_hash=revision.content_hash,
                actor_identity=actor,
                actor_authority="proposal-queue-operator",
                summary="Exact proposal revision removed from the active review queue.",
                occurred_at=removed.created_at,
                queue_entry_hash=removed.content_hash,
            ),
            proposal_id,
        )
        return removed

    async def statistics(self) -> ProposalStatistics:
        revisions = await self._repository.list_current()
        reviews = await self._repository.list_reviews()
        return ProposalStatistics(
            proposals_by_type=dict(
                Counter(
                    HarnessProposalType(item.change_specification.change_surface)
                    for item in revisions
                )
            ),
            proposals_by_status=dict(Counter(item.status for item in revisions)),
            proposals_by_risk=dict(Counter(item.risk_assessment.risk_level for item in revisions)),
            proposals_by_tier=dict(
                Counter(item.change_specification.change_surface_tier for item in revisions)
            ),
            review_outcomes=dict(Counter(item.review_decision for item in reviews)),
            verifier_failure_reasons=dict(
                Counter(
                    finding.reason_code
                    for item in revisions
                    if item.verifier_bundle
                    for finding in item.verifier_bundle.findings
                    if finding.status is ProposalVerifierStatus.FAILED
                )
            ),
            provider_fallback_count=self._provider_fallback_count,
        )
