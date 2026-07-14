from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognitive_os.config.verifier_config import VerificationLimitsConfig
from cognitive_os.domain.acceptance import AcceptancePolicy, VerifierRequirement
from cognitive_os.domain.enums import RiskLevel, VerifierStatus
from cognitive_os.domain.problems import AcceptanceCriterion, CriterionType, ProblemDomain
from cognitive_os.domain.verifiers import (
    VerificationSubject,
    VerificationSubjectType,
    VerifierCapability,
    VerifierDescriptor,
    VerifierDeterminism,
    VerifierKind,
)
from cognitive_os.verification.errors import (
    AmbiguousVerifierSelectionError,
    VerifierRegistrationError,
    VerifierUnavailableError,
)
from cognitive_os.verification.generic import ExactValueVerifier, JsonSchemaVerifier
from cognitive_os.verification.registry import VerifierRegistry
from cognitive_os.verification.selection import select_verifier


def test_descriptor_hash_and_registry_snapshot_are_deterministic() -> None:
    left, right = VerifierRegistry(), VerifierRegistry()
    left.register(ExactValueVerifier())
    right.register(ExactValueVerifier())
    assert left.snapshot() == right.snapshot()
    assert left.list_all()[0].descriptor_hash == left.list_all()[0].computed_hash()


def test_registry_rejects_duplicate_and_mutation_after_freeze() -> None:
    registry = VerifierRegistry()
    registry.register(ExactValueVerifier())
    with pytest.raises(VerifierRegistrationError, match="duplicate"):
        registry.register(ExactValueVerifier())
    registry.freeze()
    with pytest.raises(VerifierRegistrationError, match="frozen"):
        registry.register(JsonSchemaVerifier())


def test_unavailable_optional_verifier_is_reported_safely() -> None:
    descriptor = ExactValueVerifier().descriptor.model_copy(
        update={"verifier_id": "generic.unavailable"}
    )
    registry = VerifierRegistry()
    registry.register_unavailable(descriptor, "optional package missing")
    with pytest.raises(VerifierUnavailableError):
        registry.require("generic.unavailable", "1")
    assert registry.list_available() == ()


def test_selection_is_explicit_and_ambiguous_fallback_fails() -> None:
    registry = VerifierRegistry()
    registry.register_many((ExactValueVerifier(),))
    criterion = AcceptanceCriterion(
        criterion_id=uuid4(),
        description="exact",
        criterion_type=CriterionType.EXACT_MATCH,
        weight=1,
    )
    selected = select_verifier(
        registry,
        criterion,
        domain=ProblemDomain.GENERIC,
        subject_type=VerificationSubjectType.STRUCTURED_VALUE,
    )
    assert selected.verifier_id == "generic.exact"

    class Alias(ExactValueVerifier):
        def __init__(self) -> None:
            super().__init__()
            value = self.descriptor.model_dump(mode="python", exclude={"descriptor_hash"})
            value["verifier_id"] = "generic.exact_alias"
            object.__setattr__(
                self,
                "_descriptor",
                VerifierDescriptor.model_validate(value),
            )

    registry.register(Alias())
    with pytest.raises(AmbiguousVerifierSelectionError):
        select_verifier(
            registry,
            criterion,
            domain=ProblemDomain.GENERIC,
            subject_type=VerificationSubjectType.STRUCTURED_VALUE,
        )


def test_subject_rejects_workspace_escape_and_wrong_type() -> None:
    with pytest.raises(ValidationError):
        VerificationSubject(
            subject_type=VerificationSubjectType.WORKSPACE, workspace_path="../repo"
        )
    with pytest.raises(ValidationError):
        VerificationSubject(
            subject_type=VerificationSubjectType.STRUCTURED_VALUE, workspace_path="repo"
        )


def test_parallel_verifier_execution_is_rejected() -> None:
    with pytest.raises(ValidationError, match="parallel"):
        VerificationLimitsConfig(parallel_execution=True)


def test_policy_hash_is_stable_and_duplicate_criteria_rejected() -> None:
    criterion_id = uuid4()
    requirement = VerifierRequirement(
        requirement_id=uuid4(),
        verifier_id="generic.exact",
        minimum_version="1",
        criterion_ids=(criterion_id,),
        allowed_outcomes=(VerifierStatus.PASSED,),
    )
    policy = AcceptancePolicy(
        policy_id=uuid4(),
        version="1",
        name="exact",
        description="exact policy",
        requirements=(requirement,),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert policy.policy_hash == policy.computed_hash()
    with pytest.raises(ValidationError, match="unique"):
        AcceptancePolicy(
            policy_id=uuid4(),
            version="1",
            name="invalid",
            description="invalid policy",
            requirements=(requirement, requirement.model_copy(update={"requirement_id": uuid4()})),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_capability_rejects_batch_in_sprint7() -> None:
    with pytest.raises(ValidationError, match="batches"):
        VerifierCapability(
            capability_id="batch",
            subject_type=VerificationSubjectType.STRUCTURED_VALUE,
            problem_domains=(ProblemDomain.GENERIC,),
            criterion_types=(CriterionType.EXACT_MATCH,),
            supports_batch=True,
        )


def test_descriptor_rejects_tampered_hash() -> None:
    with pytest.raises(ValidationError, match="hash"):
        VerifierDescriptor(
            verifier_id="generic.test",
            version="1",
            display_name="Test",
            description="Test descriptor",
            kind=VerifierKind.GENERIC,
            capabilities=(
                VerifierCapability(
                    capability_id="generic.test.v1",
                    subject_type=VerificationSubjectType.STRUCTURED_VALUE,
                    problem_domains=(ProblemDomain.GENERIC,),
                    criterion_types=(CriterionType.EXACT_MATCH,),
                ),
            ),
            determinism=VerifierDeterminism.DETERMINISTIC,
            risk_level=RiskLevel.LOW,
            default_timeout_seconds=1,
            maximum_input_bytes=100,
            configuration_schema={"type": "object"},
            descriptor_hash="0" * 64,
        )
