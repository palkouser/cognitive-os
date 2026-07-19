"""Deterministic, host-authorized skill applicability and selection."""

from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.application.ports.skill_repository import SkillRepositoryPort
from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.domain.skills import (
    SkillAccessRecord,
    SkillAccessType,
    SkillApplicabilityStatus,
    SkillExclusionReason,
    SkillItem,
    SkillRequirementType,
    SkillRevision,
    SkillSelectionCandidate,
    SkillSelectionDecision,
    SkillSelectionExclusion,
    SkillSelectionReason,
    SkillSelectionRequest,
)
from cognitive_os.memory.governance import sensitivity_allows

from .errors import SkillPolicyError
from .preconditions import PreconditionEvaluatorRegistry


def _scope_matches(item: SkillItem, request: SkillSelectionRequest) -> bool:
    scope = item.identity.scope
    requested = request.applicability_input.scope
    return scope.scope_type.value == "global" or scope == requested


def _specificity(revision: SkillRevision, request: SkillSelectionRequest) -> int:
    value = request.applicability_input
    score = 0
    for signature in revision.problem_signatures:
        if signature.problem_domain not in {"*", value.problem_domain}:
            continue
        score = max(
            score,
            sum(
                part is not None
                for part in (
                    signature.task_type,
                    signature.repository_language,
                    signature.repository_profile,
                    signature.requested_output_type,
                    signature.risk_level,
                )
            )
            + 1,
        )
    return score


def _requirements_available(revision: SkillRevision, request: SkillSelectionRequest) -> bool:
    available = {
        SkillRequirementType.TOOL: request.applicability_input.tool_capabilities,
        SkillRequirementType.VERIFIER: request.applicability_input.verifier_capabilities,
        SkillRequirementType.PROVIDER: request.applicability_input.provider_capabilities,
        SkillRequirementType.CONTEXT: request.applicability_input.context_capabilities,
        SkillRequirementType.APPROVAL: request.applicability_input.permissions,
        SkillRequirementType.ARTIFACT: request.applicability_input.available_artifact_types,
    }
    return all(
        not requirement.required
        or requirement.capability_id in available[requirement.requirement_type]
        for requirement in revision.requirements
    )


class SkillSelectionService:
    def __init__(
        self,
        repository: SkillRepositoryPort,
        evaluators: PreconditionEvaluatorRegistry,
        configuration: SkillConfiguration,
    ) -> None:
        self._repository = repository
        self._evaluators = evaluators
        self._configuration = configuration

    async def select(self, request: SkillSelectionRequest) -> SkillSelectionDecision:
        rows = await self._repository.query_candidates(limit=request.maximum_candidates)
        candidates: list[SkillSelectionCandidate] = []
        exclusions: list[SkillSelectionExclusion] = []
        for item, revision in rows:
            reason: SkillExclusionReason | None = None
            detail = ""
            if revision.status not in request.allowed_statuses:
                reason, detail = SkillExclusionReason.STATUS, "status_not_authorized"
            elif not _scope_matches(item, request):
                reason, detail = SkillExclusionReason.SCOPE, "scope_mismatch"
            elif not sensitivity_allows(
                revision.sensitivity, request.applicability_input.sensitivity_limit
            ):
                reason, detail = SkillExclusionReason.SENSITIVITY, "sensitivity_exceeded"
            applicability = self._evaluators.evaluate(revision, request.applicability_input)
            if reason is None and applicability.status is not SkillApplicabilityStatus.APPLICABLE:
                reason = (
                    SkillExclusionReason.PERMISSION_REQUIRED
                    if applicability.status is SkillApplicabilityStatus.REQUIRES_PERMISSION
                    else SkillExclusionReason.PRECONDITION
                )
                detail = applicability.status.value
            if reason is None and not _requirements_available(revision, request):
                reason, detail = (
                    SkillExclusionReason.MISSING_REQUIREMENT,
                    "required_capability_unavailable",
                )
            if reason is not None:
                exclusions.append(
                    SkillSelectionExclusion(
                        skill_id=revision.skill_id,
                        revision=revision.revision,
                        reason=reason,
                        detail_code=detail,
                    )
                )
                continue
            statistics = await self._repository.read_statistics(
                revision.skill_id, revision.revision
            )
            statistics_score = (
                statistics.accepted * 100 // max(statistics.executions, 1)
                if statistics is not None
                and statistics.executions
                >= self._configuration.minimum_statistics_sample_for_ranking
                else 0
            )
            candidates.append(
                SkillSelectionCandidate(
                    skill_id=revision.skill_id,
                    revision=revision.revision,
                    applicability=applicability,
                    specificity_score=_specificity(revision, request),
                    scope_score=(
                        2 if item.identity.scope == request.applicability_input.scope else 1
                    ),
                    statistics_score=statistics_score,
                    safety_penalty=0,
                    estimated_context_tokens=max(
                        1, (len(revision.description) + len(revision.purpose)) // 4
                    ),
                )
            )
        candidates.sort(
            key=lambda item: (
                -item.specificity_score,
                -item.scope_score,
                -item.statistics_score,
                item.safety_penalty,
                item.estimated_context_tokens,
                str(item.skill_id),
                item.revision,
            )
        )
        selected = candidates[0] if candidates else None
        profile_hash = sha256(
            b"skill-selection-v1:status,scope,preconditions,requirements,specificity,statistics,cost,id"
        ).hexdigest()
        decision = SkillSelectionDecision(
            request_id=request.request_id,
            selected_skill_id=selected.skill_id if selected else None,
            selected_revision=selected.revision if selected else None,
            reason=(
                SkillSelectionReason.EXACT_SIGNATURE
                if selected and selected.specificity_score
                else SkillSelectionReason.SCOPE_SPECIFICITY
                if selected and selected.scope_score > 1
                else SkillSelectionReason.VERIFIED_STATISTICS
                if selected and selected.statistics_score
                else SkillSelectionReason.CANONICAL_TIE_BREAK
                if selected
                else None
            ),
            candidates=tuple(candidates),
            exclusions=tuple(
                sorted(exclusions, key=lambda item: (str(item.skill_id), item.revision))
            ),
            selection_profile_hash=profile_hash,
            registry_snapshot=request.registry_snapshot,
        )
        if selected is not None:
            await self._repository.record_access(
                (
                    SkillAccessRecord(
                        access_id=uuid5(
                            NAMESPACE_URL,
                            f"skill-selection:{request.request_id}:{selected.skill_id}:{selected.revision}",
                        ),
                        skill_id=selected.skill_id,
                        revision=selected.revision,
                        access_type=SkillAccessType.SELECTION,
                        task_run_id=request.task_run_id,
                        query_hash=decision.decision_hash,
                        scope=request.applicability_input.scope,
                        sensitivity=request.applicability_input.sensitivity_limit,
                        accessed_at=request.created_at,
                    ),
                )
            )
        return decision


def validate_fallback_chain(
    start: SkillRevision,
    revisions: dict[tuple[object, int], SkillRevision],
    *,
    maximum_depth: int,
) -> None:
    seen = {start.skill_id}
    current = start
    for _ in range(maximum_depth):
        fallback = current.failure_policy.fallback
        if fallback is None:
            return
        matches = [
            value
            for (skill_id, _), value in revisions.items()
            if skill_id == fallback.skill_id
            and (fallback.revision is None or value.revision == fallback.revision)
        ]
        if not matches:
            raise SkillPolicyError("fallback skill revision is unavailable")
        current = max(matches, key=lambda item: item.revision)
        if current.skill_id in seen:
            raise SkillPolicyError("skill fallback cycle detected")
        if current.status.value == "retracted":
            raise SkillPolicyError("retracted skill cannot be a fallback")
        seen.add(current.skill_id)
    if current.failure_policy.fallback is not None:
        raise SkillPolicyError("skill fallback depth exceeds the configured limit")
