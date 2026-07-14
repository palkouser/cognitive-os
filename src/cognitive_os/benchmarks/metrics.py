"""Deterministic benchmark metric aggregation."""

from cognitive_os.domain.benchmarks import BenchmarkCaseResult, BenchmarkCaseStatus


def aggregate_metrics(results: tuple[BenchmarkCaseResult, ...]) -> dict[str, float]:
    count = len(results)
    if not count:
        zero = float(0)
        return {"case_count": zero, "case_pass_rate": zero}
    passed = sum(item.status is BenchmarkCaseStatus.PASSED for item in results)
    errors = sum(
        item.status in {BenchmarkCaseStatus.ERROR, BenchmarkCaseStatus.TIMED_OUT}
        for item in results
    )
    elapsed = sum((item.finished_at - item.started_at).total_seconds() for item in results)
    metrics = {
        "case_count": float(count),
        "case_pass_rate": passed / count,
        "verification_error_rate": errors / count,
        "elapsed_seconds": elapsed,
    }
    for key in sorted({key for item in results for key in item.metrics}):
        metrics[key] = sum(item.metrics.get(key, 0.0) for item in results)
    return metrics
