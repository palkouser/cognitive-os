"""Fail-closed host policy for governed memory writes and exposure."""

from __future__ import annotations

import re

from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import (
    MemoryCreatorType,
    MemorySensitivity,
    MemoryStatus,
    MemoryWriteDecision,
    MemoryWriteOutcome,
    MemoryWritePolicy,
    MemoryWriteRequest,
)

_SENSITIVITY_RANK = {
    MemorySensitivity.PUBLIC: 0,
    MemorySensitivity.INTERNAL: 1,
    MemorySensitivity.CONFIDENTIAL: 2,
    MemorySensitivity.RESTRICTED: 3,
}
_SECRET_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]{8,}",
        r"\bgh[opusr]_[A-Za-z0-9]{20,}\b",
    )
)


def sensitivity_allows(actual: MemorySensitivity, ceiling: MemorySensitivity) -> bool:
    return _SENSITIVITY_RANK[actual] <= _SENSITIVITY_RANK[ceiling]


def contains_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)


class MemoryWritePolicyEvaluator:
    def evaluate(
        self, request: MemoryWriteRequest, policy: MemoryWritePolicy
    ) -> MemoryWriteDecision:
        reasons: list[str] = []
        rendered = request.content.render_search_text()
        if request.memory_type not in policy.allowed_types:
            reasons.append("memory_type_denied")
        if request.scope.scope_type not in policy.allowed_scopes:
            reasons.append("scope_denied")
        if not sensitivity_allows(request.sensitivity, policy.maximum_sensitivity):
            reasons.append("sensitivity_denied")
        if contains_secret(rendered):
            reasons.append("secret_detected")
        if request.automatic and not policy.allow_automatic_request:
            reasons.append("automatic_ingestion_denied")
        if request.actor.creator_type is MemoryCreatorType.PROVIDER:
            reasons.append("provider_direct_write_denied")
        if request.status is MemoryStatus.VERIFIED and not policy.allow_verified_creation:
            reasons.append("verified_creation_denied")
        if reasons:
            outcome = MemoryWriteOutcome.DENY
        elif request.status is MemoryStatus.VERIFIED:
            outcome = MemoryWriteOutcome.ALLOW_VERIFIED
            reasons.append("trusted_verified_write_allowed")
        else:
            outcome = MemoryWriteOutcome.ALLOW_CANDIDATE
            reasons.append("candidate_write_allowed")
        return MemoryWriteDecision(
            decision=outcome,
            reason_codes=tuple(reasons),
            policy_hash=policy.canonical_hash(),
            evaluated_at=utc_now(),
        )
