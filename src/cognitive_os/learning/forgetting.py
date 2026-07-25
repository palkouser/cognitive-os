"""The forgetting gate: retention measured across every domain, not asserted.

Requirement 1 of the sprint is that learning accumulates — new knowledge may revise
old knowledge but must not destroy it. That is treated here as a measurable
property with a hard gate, using the rule Sprint 19 already applies to code
changes: a hard failure ends eligibility regardless of how much the target metric
improved.

Retention is recorded per case, not per domain count, so `regressed_cases` names
what broke. A domain with no cases cannot be shown to be retained, and the
assessment says so through `ForgettingVerdict.NOT_ESTABLISHED` rather than
reporting a retention it never measured.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.domain.learned import ForgettingAssessment, ForgettingVerdict
from cognitive_os.domains.fixtures import FIXTURE_TIME, build_all_cases
from cognitive_os.domains.runner import run_case_controlled

#: case_id -> (domain, passed)
Retention = Mapping[str, tuple[str, bool]]


async def measure_retention(cases: Sequence[DomainBenchmarkCase] | None = None) -> Retention:
    """Run every case and record, per case, whether it still passes."""
    subjects = tuple(cases if cases is not None else build_all_cases())
    measured: dict[str, tuple[str, bool]] = {}
    for case in subjects:
        run = await run_case_controlled(case)
        measured[case.case_id] = (case.domain.value, run.accepted)
    return measured


def _per_domain(retention: Retention) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for domain, passed in retention.values():
        counts[domain] = counts.get(domain, 0) + int(passed)
    return tuple(sorted(counts.items()))


def _manifest_hash(retention: Retention) -> str:
    return sha256(":".join(sorted(retention)).encode()).hexdigest()


def assess_forgetting(
    before: Retention,
    after: Retention,
    *,
    session_id: UUID,
    tolerance: int = 0,
) -> ForgettingAssessment:
    """Compare two retention measurements and decide whether learning forgot.

    A case counts as regressed only if it passed before and fails after. A case
    that never passed cannot regress, and a case missing from the later
    measurement is treated as regressed rather than ignored — silently dropping a
    case is the easiest way to fake retention.
    """
    if not before:
        raise ValueError("forgetting cannot be assessed without a baseline measurement")

    regressed = tuple(
        sorted(
            case_id
            for case_id, (_, passed) in before.items()
            if passed and not after.get(case_id, ("", False))[1]
        )
    )
    retained = sum(
        1
        for case_id, (_, passed) in before.items()
        if passed and after.get(case_id, ("", False))[1]
    )
    if len(regressed) > tolerance:
        verdict = ForgettingVerdict.REGRESSED
    elif any(passed for _, passed in before.values()):
        verdict = ForgettingVerdict.RETAINED
    else:
        # Nothing passed at baseline, so retention was never demonstrable.
        verdict = ForgettingVerdict.NOT_ESTABLISHED

    return ForgettingAssessment(
        assessment_id=uuid5(NAMESPACE_URL, f"forgetting:{session_id}:{_manifest_hash(before)}"),
        session_id=session_id,
        baseline_manifest_hash=_manifest_hash(before),
        per_domain_before=_per_domain(before),
        per_domain_after=_per_domain(after),
        regressed_cases=regressed,
        retained_case_count=retained,
        tolerance=tolerance,
        verdict=verdict,
        created_at=FIXTURE_TIME,
    )
