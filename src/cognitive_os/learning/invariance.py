"""Mandatory-path invariance: the sprint's defining guarantee.

The core boundary chosen for Sprint 21 is the deterministic mandatory execution
path. Contracts and ports may be extended when a capability needs it, so "a future
capability needs no core change" cannot be a CI gate. What *is* a gate is the more
useful half:

    With a learned component absent, present but disabled, or present but
    abstaining, the deterministic path produces identical decisions.

That constrains behaviour rather than file layout, which is why it survives the
looser boundary — and it is what protects eleven sprints of deterministic
guarantees from any learned component, including ones not yet written.

The digest covers each case's acceptance decision, not its timing or identifiers,
so a genuine behavioural change fails the gate and an incidental one does not.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.domain.learned import LearnedComponentState, MandatoryPathInvariance
from cognitive_os.domains.fixtures import FIXTURE_TIME, build_all_cases
from cognitive_os.domains.runner import run_case_controlled

from .registry import LearnedComponentRegistry


def _case_set_hash(cases: Sequence[DomainBenchmarkCase]) -> str:
    return sha256(":".join(case.case_id for case in cases).encode()).hexdigest()


async def decision_digest(cases: Sequence[DomainBenchmarkCase]) -> str:
    """Digest of the deterministic path's decision on every case, in order."""
    parts: list[str] = []
    for case in cases:
        run = await run_case_controlled(case)
        parts.append(f"{case.case_id}={run.state.value}:{int(run.accepted)}:{run.decision_reason}")
    return sha256("\n".join(parts).encode()).hexdigest()


async def verify_invariance(
    component_id: str,
    registry: LearnedComponentRegistry,
    *,
    cases: Sequence[DomainBenchmarkCase] | None = None,
    artifact_unavailable: Callable[[], Awaitable[None]] | None = None,
) -> MandatoryPathInvariance:
    """Replay the case set in the configurations the guarantee names.

    The registry is driven through the real lifecycle rather than simulated: the
    component is disabled and re-enabled through `transition`, so a component that
    cannot be disabled fails here instead of passing on a mock.

    `artifact_unavailable` adds Sprint 21D2's fourth configuration. Absent, disabled and
    abstaining are all states the component chose; an unloadable artifact is the one it did
    not, and it is what a corrupt blob or a moved file actually produces in operation. The
    callback makes the artifact unreadable for the duration of the replay, so the digest
    describes a real failure rather than a simulated one. Omitted, the record carries three
    hashes exactly as before, which is what keeps every pre-D2 record loadable.
    """
    subjects = tuple(cases if cases is not None else build_all_cases())
    if not subjects:
        raise ValueError("invariance verification requires at least one case")

    # Absent: the component is registered but has never been shadowed or activated,
    # so no learned code participates.
    absent = await decision_digest(subjects)

    registry.transition(component_id, LearnedComponentState.SHADOW)
    registry.transition(component_id, LearnedComponentState.DISABLED)
    disabled = await decision_digest(subjects)

    # Abstaining: shadow again, where a component may predict but can never change
    # the executed decision.
    registry.transition(component_id, LearnedComponentState.SHADOW)
    abstaining = await decision_digest(subjects)

    unavailable: str | None = None
    if artifact_unavailable is not None:
        await artifact_unavailable()
        unavailable = await decision_digest(subjects)

    return MandatoryPathInvariance(
        record_id=uuid5(NAMESPACE_URL, f"invariance:{component_id}:{_case_set_hash(subjects)}"),
        component_id=component_id,
        case_set_hash=_case_set_hash(subjects),
        case_count=len(subjects),
        decision_hash_absent=absent,
        decision_hash_disabled=disabled,
        decision_hash_abstaining=abstaining,
        decision_hash_artifact_unavailable=unavailable,
        created_at=FIXTURE_TIME,
    )
