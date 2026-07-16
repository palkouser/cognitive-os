"""Provider message composition that keeps retrieved data out of instructions."""

from cognitive_os.domain.context import ContextBuildResult, ContextBuildStatus
from cognitive_os.domain.model_requests import ProviderMessage, ProviderMessageRole


def compose_context_messages(
    task_instruction: str, result: ContextBuildResult
) -> tuple[ProviderMessage, ...]:
    if (
        result.status is not ContextBuildStatus.CREATED
        or result.bundle is None
        or result.bundle_reference is None
        or result.rendered_context is None
    ):
        raise ValueError("a persisted, validated Context Bundle is required")
    return (
        ProviderMessage(role=ProviderMessageRole.USER, content=task_instruction),
        ProviderMessage(
            role=ProviderMessageRole.USER,
            name="retrieved_context_data",
            content=result.rendered_context,
        ),
    )
