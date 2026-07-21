"""Mandatory deterministic verifier bundle for weakness diagnostics."""

from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.weakness import (
    CausalRelationshipType,
    ImpactDimension,
    ImpactScore,
    SignalSourceType,
    WeaknessEvidencePackage,
    WeaknessGroup,
    WeaknessQueueEntry,
    WeaknessRevision,
    WeaknessSignal,
    WeaknessSignature,
)
from cognitive_os.weakness.service import build_signature

MANDATORY_WEAKNESS_VERIFIERS = (
    "weakness.signal_source_integrity",
    "weakness.signal_authority",
    "weakness.signal_evidence_completeness",
    "weakness.signature_determinism",
    "weakness.group_membership_integrity",
    "weakness.impact_score_reproducibility",
    "weakness.evidence_completeness",
    "weakness.sensitivity_safety",
    "weakness.no_unsupported_causal_claim",
    "weakness.lifecycle_integrity",
    "weakness.queue_priority_determinism",
    "weakness.reproduction_integrity",
    "weakness.counterexample_preservation",
    "weakness.no_modification_authority",
    "weakness.no_automatic_proposal",
)

_SENSITIVITY = {
    MemorySensitivity.PUBLIC: 0,
    MemorySensitivity.INTERNAL: 1,
    MemorySensitivity.CONFIDENTIAL: 2,
    MemorySensitivity.RESTRICTED: 3,
}
_MODIFICATION_MARKERS = (
    "diff --git",
    "apply_patch",
    "git commit",
    "git push",
    "create pull request",
    "replace the prompt",
    "modify policy",
    "enable routing policy",
)


def verify_signal(signal: WeaknessSignal) -> tuple[str, ...]:
    failures = []
    if not signal.source_refs or any(
        source.content_hash != source.canonical_hash(exclude={"content_hash"})
        for source in signal.source_refs
    ):
        failures.append("weakness.signal_source_integrity")
    if not any(source.authoritative and not source.shadow for source in signal.source_refs):
        failures.append("weakness.signal_authority")
    if all(source.source_type is SignalSourceType.PROVIDER_RESULT for source in signal.source_refs):
        failures.append("weakness.signal_authority")
    if signal.causal_relationship is CausalRelationshipType.OBSERVED_FAILURE and not any(
        source.source_type
        in {SignalSourceType.ACCEPTANCE, SignalSourceType.VERIFIER, SignalSourceType.BENCHMARK}
        for source in signal.source_refs
    ):
        failures.append("weakness.no_unsupported_causal_claim")
    return tuple(dict.fromkeys(failures))


def verify_signature(signal: WeaknessSignal, signature: WeaknessSignature) -> tuple[str, ...]:
    expected = build_signature(signal)
    return () if expected == signature else ("weakness.signature_determinism",)


def verify_group(group: WeaknessGroup, signals: tuple[WeaknessSignal, ...]) -> tuple[str, ...]:
    by_id = {item.signal_id: item for item in signals}
    for member in group.members:
        signal = by_id.get(member.signal_id)
        if (
            signal is None
            or signal.content_hash != member.signal_hash
            or build_signature(signal) != group.signature
        ):
            return ("weakness.group_membership_integrity",)
    if len({item.signal_id for item in group.members}) != len(group.members):
        return ("weakness.group_membership_integrity",)
    return ()


def verify_impact(score: ImpactScore) -> tuple[str, ...]:
    if {item.dimension for item in score.dimensions} != set(ImpactDimension):
        return ("weakness.impact_score_reproducibility",)
    base = sum((item.weighted_value for item in score.dimensions), start=score.base_score * 0)
    if (
        abs(base * 100 - score.base_score)
        > score.base_score * 0 + score.profile.weights[ImpactDimension.FREQUENCY]
    ):
        return ("weakness.impact_score_reproducibility",)
    if score.final_score != max(score.base_score, score.priority_floor):
        return ("weakness.impact_score_reproducibility",)
    return ()


def verify_evidence(package: WeaknessEvidencePackage) -> tuple[str, ...]:
    failures = []
    if (
        package.complete_source_count != len(package.source_manifest)
        or not package.representative_signal_hashes
        or not package.checksums
    ):
        failures.append("weakness.evidence_completeness")
    strictest = max(package.source_manifest, key=lambda item: _SENSITIVITY[item.sensitivity])
    if _SENSITIVITY[package.sensitivity] < _SENSITIVITY[strictest.sensitivity]:
        failures.append("weakness.sensitivity_safety")
    if package.reproduction.status.value == "reproducible" and not package.reproduction.attempts:
        failures.append("weakness.reproduction_integrity")
    return tuple(failures)


def verify_revision(revision: WeaknessRevision) -> tuple[str, ...]:
    if revision.revision == 1 and revision.previous_revision is not None:
        return ("weakness.lifecycle_integrity",)
    return verify_no_modification(revision)


def verify_queue(entry: WeaknessQueueEntry) -> tuple[str, ...]:
    failures = list(verify_no_modification(entry))
    if not entry.priority_reason or not entry.queue_policy_hash:
        failures.append("weakness.queue_priority_determinism")
    return tuple(failures)


def verify_no_modification(value: object) -> tuple[str, ...]:
    serialized = (
        value.model_dump_json().lower() if hasattr(value, "model_dump_json") else str(value).lower()
    )
    if any(marker in serialized for marker in _MODIFICATION_MARKERS):
        return ("weakness.no_modification_authority",)
    return ()
