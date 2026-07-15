from datetime import UTC, datetime
from uuid import UUID

import pytest

from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
    VerifierKind,
)
from cognitive_os.verification.factory import build_builtin_registry
from cognitive_os.verification.semantic import SEMANTIC_CAPABILITIES


def request(verifier_id: str, value: bool) -> VerificationRequest:
    capability = verifier_id.removeprefix("semantic.")
    return VerificationRequest(
        verification_id=UUID(int=1),
        task_run_id=UUID(int=2),
        criterion_id=UUID(int=3),
        verifier_id=verifier_id,
        verifier_version="1",
        subject=VerificationSubject(
            subject_type=VerificationSubjectType.SEMANTIC_SNAPSHOT,
            inline_value={capability: value},
        ),
        requested_at=datetime(2026, 7, 15, tzinfo=UTC),
        correlation_id=UUID(int=4),
    )


@pytest.mark.asyncio
async def test_semantic_bundle_is_registered_and_fails_closed() -> None:
    registry = build_builtin_registry()
    descriptors = registry.list_by_kind(VerifierKind.SEMANTIC)
    assert {item.verifier_id for item in descriptors} == {
        f"semantic.{item}" for item in SEMANTIC_CAPABILITIES
    }
    verifier = registry.require("semantic.source_grounding", "1")
    passed = await verifier.verify(request("semantic.source_grounding", True))
    failed = await verifier.verify(request("semantic.source_grounding", False))
    assert passed.status is VerifierStatus.PASSED
    assert failed.status is VerifierStatus.FAILED
