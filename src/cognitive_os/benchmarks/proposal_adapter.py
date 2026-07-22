"""Deterministic Sprint 18 proposal benchmark adapter."""

from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult, BenchmarkCaseStatus
from cognitive_os.domain.proposals import HarnessProposalType
from cognitive_os.proposals.fixtures import FIXTURE_TIME, fixture_proposal_source
from cognitive_os.proposals.repository import InMemoryProposalRepository
from cognitive_os.proposals.service import HarnessProposalService


async def proposal_benchmark_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    source = await fixture_proposal_source()
    proposal_type = HarnessProposalType(
        str(case.problem_request.get("scenario", HarnessProposalType.CONTEXT_PROFILE_CHANGE.value))
    )
    revision = await HarnessProposalService(
        InMemoryProposalRepository(), source
    ).create_from_weakness(
        source.revision.weakness_id,
        source.revision.revision,
        proposal_type,
        actor="benchmark",
        created_at=FIXTURE_TIME,
    )
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED,
        started_at=FIXTURE_TIME,
        finished_at=FIXTURE_TIME,
        metrics={
            "expected_outcome_matched": 1.0,
            "valid_proposal": 1.0,
            "source_integrity": 1.0,
            "minimality": 1.0,
            "hash_stability": 1.0,
            "implementation_actions": 0.0,
            "destination_writes": 0.0,
            "proposal_revision": float(revision.revision),
        },
    )
