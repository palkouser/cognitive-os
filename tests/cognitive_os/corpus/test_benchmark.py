import asyncio

from scripts.corpus_benchmark import run_benchmark


def test_ci_corpus_benchmark_has_fourteen_reproducible_cases() -> None:
    report = asyncio.run(run_benchmark(14))
    assert report["cases"] == 14
    assert report["reproducible"]
    assert report["destination_writes"] == 0
    assert report["training_actions"] == 0
