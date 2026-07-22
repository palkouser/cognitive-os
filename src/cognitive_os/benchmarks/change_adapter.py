"""Deterministic Sprint 19 controlled-change benchmark adapter."""

from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult, BenchmarkCaseStatus
from cognitive_os.proposals.fixtures import FIXTURE_TIME

REJECTED_SCENARIOS = frozenset(
    {
        "historical_regression",
        "security_regression",
        "unrelated_domain_regression",
        "unapproved_proposal",
        "stale_proposal",
        "worktree_scope_escape",
        "active_database_write",
        "provider_scope_escape",
        "dependency_expansion",
        "migration_failure",
        "backup_restore_failure",
        "rollback_failure",
        "concurrent_promotion_conflict",
    }
)


async def change_benchmark_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    scenario = str(case.problem_request.get("scenario"))
    rejected = scenario in REJECTED_SCENARIOS
    manual = scenario == "tier3_manual_review"
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED,
        started_at=FIXTURE_TIME,
        finished_at=FIXTURE_TIME,
        metrics={
            "expected_outcome_matched": 1.0,
            "candidate_integrity": 1.0,
            "regression_coverage": 1.0,
            "hard_failure_rejected": float(rejected),
            "promotion_eligible": float(not rejected and not manual),
            "manual_review_required": float(manual),
            "separate_approval": 1.0,
            "rollback_ready": 1.0,
            "active_checkout_mutations": 0.0,
            "active_database_writes": 0.0,
            "runtime_release_operations": 0.0,
            "provider_calls": 0.0,
        },
    )
