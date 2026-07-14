"""Typed, provider-neutral problem representation contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import NonEmptyStr, Sha256Hex, UtcDatetime
from .enums import RiskLevel
from .identifiers import ArtifactId, TaskId, TaskRunId


class ProblemDomain(StrEnum):
    GENERIC = "generic"
    CODING = "coding"
    MATHEMATICS = "mathematics"
    PHYSICS = "physics"
    LOGIC = "logic"


class ConstraintCategory(StrEnum):
    FUNCTIONAL = "functional"
    SECURITY = "security"
    RESOURCE = "resource"
    TIME = "time"
    FORMAT = "format"
    ENVIRONMENT = "environment"
    POLICY = "policy"
    DOMAIN = "domain"


class CriterionType(StrEnum):
    SCHEMA = "schema"
    ARTIFACT_EXISTS = "artifact_exists"
    STEP_COMPLETED = "step_completed"
    TOOL_SUCCEEDED = "tool_succeeded"
    EXACT_MATCH = "exact_match"
    MANUAL = "manual"
    DOMAIN_VERIFIER = "domain_verifier"


class InformationStatus(StrEnum):
    KNOWN = "known"
    ASSUMED = "assumed"
    MISSING = "missing"
    CONFLICTING = "conflicting"


class ConstraintSource(StrEnum):
    USER = "user"
    SYSTEM = "system"
    PROJECT_POLICY = "project_policy"
    TOOL_POLICY = "tool_policy"
    INFERRED = "inferred"


class ProblemGoal(ImmutableContractModel):
    goal_id: UUID
    description: NonEmptyStr
    priority: int = Field(gt=0)
    success_evidence: tuple[NonEmptyStr, ...] = Field(default=(), max_length=32)

    @field_validator("success_evidence")
    @classmethod
    def unique_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("success evidence must be unique")
        return value


class ProblemConstraint(ImmutableContractModel):
    constraint_id: UUID
    category: ConstraintCategory
    description: NonEmptyStr
    hard: bool
    source: ConstraintSource
    status: InformationStatus = InformationStatus.KNOWN


class ProblemAssumption(ImmutableContractModel):
    assumption_id: UUID
    description: NonEmptyStr
    confidence: float = Field(ge=0, le=1)
    requires_validation: bool = True
    source: ConstraintSource = ConstraintSource.INFERRED
    status: InformationStatus = InformationStatus.ASSUMED

    @model_validator(mode="after")
    def inferred_requires_validation(self) -> ProblemAssumption:
        if self.source is ConstraintSource.INFERRED and not self.requires_validation:
            raise ValueError("inferred assumptions require validation")
        return self


class ProblemInputReference(ImmutableContractModel):
    reference_id: UUID
    artifact_id: ArtifactId
    description: NonEmptyStr
    required: bool = True
    media_type: NonEmptyStr


class ProblemOutputRequirement(ImmutableContractModel):
    model_config = ConfigDict(populate_by_name=True)

    requirement_id: UUID
    output_type: NonEmptyStr
    description: NonEmptyStr
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    required: bool = True
    maximum_size_bytes: int | None = Field(default=None, gt=0)


class AcceptanceCriterion(ImmutableContractModel):
    criterion_id: UUID
    description: NonEmptyStr
    criterion_type: CriterionType
    required: bool = True
    weight: float = Field(gt=0)
    verifier_id: NonEmptyStr | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def verifier_is_consistent(self) -> AcceptanceCriterion:
        if self.criterion_type is CriterionType.DOMAIN_VERIFIER and not self.verifier_id:
            raise ValueError("domain verifier criteria require verifier_id")
        return self


class ClarificationQuestion(ImmutableContractModel):
    question_id: UUID
    question: NonEmptyStr
    reason: NonEmptyStr
    required: bool = True
    answer_schema: dict[str, Any]
    related_goal_ids: tuple[UUID, ...] = ()
    related_constraint_ids: tuple[UUID, ...] = ()


class ProblemRepresentation(ImmutableContractModel):
    problem_id: UUID
    task_id: TaskId
    task_run_id: TaskRunId
    domain: ProblemDomain
    title: NonEmptyStr
    summary: NonEmptyStr
    goals: tuple[ProblemGoal, ...] = Field(min_length=1)
    constraints: tuple[ProblemConstraint, ...] = ()
    assumptions: tuple[ProblemAssumption, ...] = ()
    inputs: tuple[ProblemInputReference, ...] = ()
    output_requirements: tuple[ProblemOutputRequirement, ...] = Field(min_length=1)
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = Field(min_length=1)
    clarification_questions: tuple[ClarificationQuestion, ...] = ()
    risk_level: RiskLevel
    confidence: float = Field(ge=0, le=1)
    created_at: UtcDatetime
    revision: int = Field(ge=1)
    source_request_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_collections(self) -> ProblemRepresentation:
        collections = (
            self.goals,
            self.constraints,
            self.assumptions,
            self.inputs,
            self.output_requirements,
            self.acceptance_criteria,
            self.clarification_questions,
        )
        for collection in collections:
            ids = [
                next(value for name, value in item if name.endswith("_id")) for item in collection
            ]
            if len(ids) != len(set(ids)):
                raise ValueError("IDs must be unique within each collection")
        if not any(item.required for item in self.acceptance_criteria):
            raise ValueError("at least one required acceptance criterion is required")
        goal_ids = {goal.goal_id for goal in self.goals}
        constraint_ids = {item.constraint_id for item in self.constraints}
        for question in self.clarification_questions:
            if set(question.related_goal_ids) - goal_ids:
                raise ValueError("clarification references an unknown goal")
            if set(question.related_constraint_ids) - constraint_ids:
                raise ValueError("clarification references an unknown constraint")
        return self

    def requires_clarification(self) -> bool:
        return any(question.required for question in self.clarification_questions)

    def is_executable(self) -> bool:
        hard_conflict = any(
            item.hard and item.status is InformationStatus.CONFLICTING for item in self.constraints
        )
        return not hard_conflict and not self.requires_clarification()

    def required_criteria(self) -> tuple[AcceptanceCriterion, ...]:
        return tuple(item for item in self.acceptance_criteria if item.required)

    def hard_constraints(self) -> tuple[ProblemConstraint, ...]:
        return tuple(item for item in self.constraints if item.hard)
