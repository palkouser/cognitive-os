"""Deterministic sensitivity, secret, and instruction-data safety checks."""

import re
from hashlib import sha256

from cognitive_os.domain.context import (
    ContextCandidate,
    ContextExclusion,
    ContextExclusionReason,
    ContextWarning,
    ContextWarningType,
    SuspiciousInstructionSignal,
)
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.memory.governance import contains_secret, sensitivity_allows

from .query import reseal_candidate

_SUSPICIOUS_RULES = (
    (
        "ignore_policy",
        re.compile(r"\bignore\b.{0,40}\b(?:previous|system|policy|instructions?)\b", re.I),
    ),
    (
        "secret_request",
        re.compile(
            r"\b(?:show|reveal|print|send)\b.{0,40}\b(?:secret|token|password|api[_ -]?key)\b", re.I
        ),
    ),
    (
        "tool_authority",
        re.compile(
            r"\b(?:authorize|execute|call|enable)\b.{0,40}\b(?:tool|permission|approval)\b", re.I
        ),
    ),
    ("system_imitation", re.compile(r"(?:^|\n)\s*(?:system|developer)\s*:", re.I)),
    (
        "repository_override",
        re.compile(
            r"\b(?:override|replace|ignore)\b.{0,40}\b(?:AGENTS\.md|repository instructions?)\b",
            re.I,
        ),
    ),
    (
        "budget_override",
        re.compile(r"\b(?:increase|disable|ignore)\b.{0,40}\b(?:budget|limit|quota)\b", re.I),
    ),
    ("encoded_instruction", re.compile(r"\b[A-Za-z0-9+/]{80,}={0,2}\b")),
)


def classify_suspicious_instructions(content: str) -> tuple[SuspiciousInstructionSignal, ...]:
    digest = sha256(content.encode()).hexdigest()
    return tuple(
        SuspiciousInstructionSignal(
            signal_type="suspicious_instruction",
            detected=True,
            content_hash=digest,
            matched_rule=name,
        )
        for name, pattern in _SUSPICIOUS_RULES
        if pattern.search(content)
    )


def filter_unsafe_candidates(
    candidates: tuple[ContextCandidate, ...],
    *,
    sensitivity_limit: MemorySensitivity,
) -> tuple[tuple[ContextCandidate, ...], tuple[ContextExclusion, ...], tuple[ContextWarning, ...]]:
    kept: list[ContextCandidate] = []
    exclusions: list[ContextExclusion] = []
    warnings: list[ContextWarning] = []
    for candidate in candidates:
        identity_hash = sha256(candidate.source_identity.encode()).hexdigest()
        if not sensitivity_allows(candidate.sensitivity, sensitivity_limit):
            exclusions.append(
                ContextExclusion(
                    candidate_id=candidate.candidate_id,
                    source_identity_hash=identity_hash,
                    reason=ContextExclusionReason.SENSITIVITY_EXCEEDED,
                    detail_code="candidate_sensitivity_exceeds_request_ceiling",
                )
            )
            continue
        if candidate.content is not None and contains_secret(candidate.content):
            exclusions.append(
                ContextExclusion(
                    candidate_id=candidate.candidate_id,
                    source_identity_hash=identity_hash,
                    reason=ContextExclusionReason.SECRET_DETECTED,
                    detail_code="candidate_body_failed_secret_scan",
                )
            )
            continue
        signals = (
            classify_suspicious_instructions(candidate.content)
            if candidate.content is not None
            else ()
        )
        candidate_warnings = tuple(
            ContextWarning(
                warning_type=ContextWarningType.SUSPICIOUS_INSTRUCTION,
                code=signal.matched_rule,
                message="Retrieved data resembles an instruction and has no policy authority.",
                candidate_id=candidate.candidate_id,
                source_references=candidate.provenance,
            )
            for signal in signals
        )
        warnings.extend(candidate_warnings)
        kept.append(
            reseal_candidate(
                candidate,
                warnings=tuple((*candidate.warnings, *candidate_warnings)),
            )
        )
    return tuple(kept), tuple(exclusions), tuple(warnings)


def escape_retrieved_data(value: str) -> str:
    """Escape boundary-like syntax while preserving source text as JSON data."""
    import json

    return json.dumps(value, ensure_ascii=False)
