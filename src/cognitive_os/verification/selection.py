"""Deterministic verifier capability matching."""

from cognitive_os.domain.problems import AcceptanceCriterion, ProblemDomain
from cognitive_os.domain.verifiers import VerificationSubjectType, VerifierDescriptor

from .errors import AmbiguousVerifierSelectionError, VerifierSelectionError
from .registry import VerifierRegistry


def select_verifier(
    registry: VerifierRegistry,
    criterion: AcceptanceCriterion,
    *,
    domain: ProblemDomain,
    subject_type: VerificationSubjectType,
    version: str = "1",
    priority: tuple[str, ...] = (),
    allow_network: bool = False,
    sandbox_available: bool = True,
) -> VerifierDescriptor:
    candidates: tuple[VerifierDescriptor, ...]
    if criterion.verifier_id:
        descriptor = registry.require(criterion.verifier_id, version).descriptor
        candidates = (descriptor,)
    else:
        candidates = registry.list_capable(subject_type, domain, criterion.criterion_type)
    candidates = tuple(
        item
        for item in candidates
        if (allow_network or not item.requires_network)
        and (sandbox_available or not item.requires_sandbox)
    )
    if not candidates:
        raise VerifierSelectionError("no available verifier satisfies the requested capability")
    if len(candidates) == 1:
        return candidates[0]
    ranked = [
        item for verifier_id in priority for item in candidates if item.verifier_id == verifier_id
    ]
    if ranked:
        return ranked[0]
    raise AmbiguousVerifierSelectionError("multiple verifiers match without an explicit priority")
