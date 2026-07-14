"""Deterministic acceptance-policy contracts."""

from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from pydantic import Field, model_validator

from .base import ImmutableContractModel
from .common import NonEmptyStr, Sha256Hex, UtcDatetime
from .enums import VerifierStatus


class VerifierRequirement(ImmutableContractModel):
    requirement_id: UUID
    verifier_id: NonEmptyStr
    minimum_version: NonEmptyStr
    criterion_ids: tuple[UUID, ...] = Field(min_length=1)
    required: bool = True
    weight: float = Field(default=1, gt=0)
    minimum_score: float = Field(default=1, ge=0, le=1)
    allowed_outcomes: tuple[VerifierStatus, ...] = (VerifierStatus.PASSED,)


class AcceptancePolicy(ImmutableContractModel):
    policy_id: UUID
    version: NonEmptyStr
    name: NonEmptyStr
    description: NonEmptyStr
    requirements: tuple[VerifierRequirement, ...] = Field(min_length=1)
    minimum_optional_score: float = Field(default=0, ge=0, le=1)
    allow_partial: bool = False
    maximum_verifier_errors: int = Field(default=0, ge=0)
    maximum_unverifiable_required: int = Field(default=0, ge=0)
    created_at: UtcDatetime
    policy_hash: str = ""

    @model_validator(mode="after")
    def seal_policy(self) -> AcceptancePolicy:
        ids = [item.requirement_id for item in self.requirements]
        criteria = [criterion for item in self.requirements for criterion in item.criterion_ids]
        if len(set(ids)) != len(ids) or len(set(criteria)) != len(criteria):
            raise ValueError("acceptance policy mappings must be unique")
        expected = self.computed_hash()
        if self.policy_hash and self.policy_hash != expected:
            raise ValueError("policy hash does not match policy content")
        object.__setattr__(self, "policy_hash", expected)
        return self

    def computed_hash(self) -> Sha256Hex:
        payload = self.model_dump(mode="json", exclude={"policy_hash"})
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class CriterionEvaluation(ImmutableContractModel):
    criterion_id: UUID
    verifier_requirement_id: UUID
    result_ids: tuple[UUID, ...] = ()
    outcome: VerifierStatus
    score: float | None = Field(default=None, ge=0, le=1)
    required: bool
    reason: NonEmptyStr


class AcceptanceDecisionType(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REPAIR = "needs_repair"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNVERIFIABLE = "unverifiable"
    VERIFICATION_ERROR = "verification_error"


class AcceptanceDecision(ImmutableContractModel):
    decision_id: UUID
    task_run_id: UUID
    policy_id: UUID
    policy_version: NonEmptyStr
    decision: AcceptanceDecisionType
    criterion_evaluations: tuple[CriterionEvaluation, ...]
    required_passed: bool
    optional_score: float = Field(ge=0, le=1)
    reason: NonEmptyStr
    created_at: UtcDatetime

    @model_validator(mode="after")
    def validate_decision(self) -> AcceptanceDecision:
        ids = [item.criterion_id for item in self.criterion_evaluations]
        if len(ids) != len(set(ids)):
            raise ValueError("criterion evaluations must be unique")
        required_errors = any(
            item.required and item.outcome is VerifierStatus.ERROR
            for item in self.criterion_evaluations
        )
        if self.decision is AcceptanceDecisionType.ACCEPTED and (
            not self.required_passed or required_errors
        ):
            raise ValueError("accepted decision requires all required evidence to pass")
        return self
