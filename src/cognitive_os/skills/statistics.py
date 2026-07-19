"""Rebuildable statistics derived only from immutable execution results."""

from uuid import UUID

from cognitive_os.domain.skills import SkillExecutionResult, SkillExecutionStatus, SkillStatistics


def rebuild_statistics(
    skill_id: UUID,
    revision: int,
    executions: tuple[SkillExecutionResult, ...],
) -> SkillStatistics:
    ordered = tuple(sorted(executions, key=lambda item: str(item.execution_id)))
    return SkillStatistics(
        skill_id=skill_id,
        revision=revision,
        projection_revision=max(len(ordered), 1),
        executions=len(ordered),
        accepted=sum(item.status is SkillExecutionStatus.ACCEPTED for item in ordered),
        rejected=sum(item.status is SkillExecutionStatus.REJECTED for item in ordered),
        unverifiable=sum(item.status is SkillExecutionStatus.UNVERIFIABLE for item in ordered),
        failed=sum(item.status is SkillExecutionStatus.FAILED for item in ordered),
        repairs=0,
        provider_calls=sum(
            len(step.provider_call_ids) for item in ordered for step in item.step_results
        ),
        tool_calls=sum(len(step.tool_call_ids) for item in ordered for step in item.step_results),
        token_usage=sum(item.usage.total_tokens or 0 for item in ordered),
        policy_denials=sum(item.failure == "policy_denied" for item in ordered),
        safety_failures=sum(item.failure == "safety_failure" for item in ordered),
        fallback_uses=sum(item.fallback_execution_id is not None for item in ordered),
        elapsed_ms=sum(
            int((item.finished_at - item.started_at).total_seconds() * 1000) for item in ordered
        ),
        source_execution_ids=tuple(item.execution_id for item in ordered),
    )
