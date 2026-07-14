"""Sprint 6 structural acceptance contracts and pure checks."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

import jsonschema
from pydantic import model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, UtcDatetime


class CriterionOutcome(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    UNVERIFIABLE = "unverifiable"


class MinimalCriterionResult(ImmutableContractModel):
    criterion_id: UUID
    outcome: CriterionOutcome
    reason: NonEmptyStr
    required: bool


class MinimalAcceptanceDecision(ImmutableContractModel):
    accepted: bool
    results: tuple[MinimalCriterionResult, ...]
    required_passed: tuple[UUID, ...]
    failed_criteria: tuple[UUID, ...]
    unverifiable_criteria: tuple[UUID, ...]
    decision_reason: NonEmptyStr
    created_at: UtcDatetime

    @model_validator(mode="after")
    def acceptance_is_evidence_based(self) -> MinimalAcceptanceDecision:
        required_failures = any(
            item.required and item.outcome is not CriterionOutcome.PASSED for item in self.results
        )
        if self.accepted == required_failures:
            raise ValueError("acceptance must match required criterion outcomes")
        return self


def validate_schema(instance: Any, schema: dict[str, Any]) -> tuple[bool, str]:
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError:
        return False, "result does not satisfy the required JSON schema"
    except jsonschema.SchemaError:
        return False, "acceptance criterion contains an invalid JSON schema"
    return True, "result satisfies the required JSON schema"
