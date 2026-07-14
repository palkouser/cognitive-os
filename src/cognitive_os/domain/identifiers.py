"""Identifier aliases and factories."""

from typing import TypeAlias
from uuid import UUID, uuid4

AgentId: TypeAlias = UUID
ArtifactId: TypeAlias = UUID
EventId: TypeAlias = UUID
ModelCallId: TypeAlias = UUID
PlanId: TypeAlias = UUID
SessionId: TypeAlias = UUID
StepId: TypeAlias = UUID
TaskId: TypeAlias = UUID
TaskRunId: TypeAlias = UUID
ToolCallId: TypeAlias = UUID
VerifierResultId: TypeAlias = UUID


def new_id() -> UUID:
    """Create a UUID4 identifier."""
    return uuid4()
