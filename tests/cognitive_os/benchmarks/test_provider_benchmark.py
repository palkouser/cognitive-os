"""The Sprint 21C2 provider boundary benchmark.

What is being protected is the benchmark's right to be believed. Three properties do that
work: every declared case really executes (an unknown scenario fails rather than passing by
default), the whole family stays credential-free and process-free, and two runs of the same
manifest produce identical receipts so a changed number means changed behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.provider_adapter import _SCENARIOS, provider_benchmark_case
from cognitive_os.domain.benchmarks import BenchmarkCaseStatus

CI_MANIFEST = Path("benchmarks/manifests/sprint21c2-provider-ci.yaml")
SEED_MANIFEST = Path("benchmarks/manifests/sprint21c2-provider-seed.yaml")

#: The backlog's floor, asserted rather than trusted: a manifest can be edited down.
MINIMUM_CI_CASES = 24
MINIMUM_SEED_CASES = 72


def _cases(path: Path) -> list:
    return list(load_manifest(path).cases)


class TestTheManifestsMeetTheirFloor:
    @pytest.mark.parametrize(
        ("path", "minimum"),
        [(CI_MANIFEST, MINIMUM_CI_CASES), (SEED_MANIFEST, MINIMUM_SEED_CASES)],
    )
    def test_the_case_count_is_at_least_the_declared_floor(self, path: Path, minimum: int) -> None:
        assert len(_cases(path)) >= minimum

    @pytest.mark.parametrize("path", [CI_MANIFEST, SEED_MANIFEST])
    def test_every_case_names_a_scenario_the_adapter_implements(self, path: Path) -> None:
        """An unknown scenario is the way a benchmark silently stops testing anything."""
        for case in _cases(path):
            assert case.problem_request["scenario"] in _SCENARIOS

    @pytest.mark.parametrize("path", [CI_MANIFEST, SEED_MANIFEST])
    def test_case_identifiers_are_unique(self, path: Path) -> None:
        identifiers = [case.case_id for case in _cases(path)]
        assert len(identifiers) == len(set(identifiers))

    def test_the_seed_set_covers_every_scenario_the_adapter_offers(self) -> None:
        covered = {case.problem_request["scenario"] for case in _cases(SEED_MANIFEST)}
        assert covered == set(_SCENARIOS)

    def test_the_backlog_families_are_all_represented(self) -> None:
        """Success, typed failures, retry, retention, rights, scan, verifier, expiry,
        mutation and cleanup — the ten the sprint asked for, by name."""
        cases = _cases(SEED_MANIFEST)
        scenarios = {case.problem_request["scenario"] for case in cases}
        statuses = {str(case.expected_outputs.get("status")) for case in cases}
        variants = {str(case.problem_request.get("variant", "")) for case in cases}
        defects = {str(case.problem_request.get("defect", "")) for case in cases}

        assert {"governance", "selection", "mutation", "cleanup", "scan"} <= scenarios
        assert {"mapped", "invalid", "refused", "conflict", "idempotent"} <= statuses
        assert {"reuse_same_execution", "reuse_different_execution"} <= variants
        assert {
            "expired",
            "scan_failed",
            "verifier_failed",
            "rights_unknown",
        } <= defects


class TestEveryCaseReallyRuns:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", [CI_MANIFEST, SEED_MANIFEST])
    async def test_expected_policy_match_is_total(self, path: Path) -> None:
        results = [await provider_benchmark_case(case) for case in _cases(path)]
        failed = [
            result.case_id for result in results if result.status is not BenchmarkCaseStatus.PASSED
        ]
        assert failed == []
        assert all(result.metrics["expected_policy_matched"] == 1.0 for result in results)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", [CI_MANIFEST, SEED_MANIFEST])
    async def test_nothing_reaches_a_network_a_credential_or_a_process(self, path: Path) -> None:
        """The reason this gate can never acquire a reason to be skipped."""
        for case in _cases(path):
            metrics = (await provider_benchmark_case(case)).metrics
            assert metrics["network_calls"] == 0.0
            assert metrics["credential_reads"] == 0.0
            assert metrics["subprocesses_started"] == 0.0
            assert metrics["gpu_calls"] == 0.0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", [CI_MANIFEST, SEED_MANIFEST])
    async def test_no_case_is_labelled_a_real_governed_outcome(self, path: Path) -> None:
        for case in _cases(path):
            metrics = (await provider_benchmark_case(case)).metrics
            assert metrics["real_governed_outcomes"] == 0.0

    @pytest.mark.asyncio
    async def test_an_unknown_scenario_fails_rather_than_passing_by_default(
        self,
    ) -> None:
        case = _cases(CI_MANIFEST)[0].model_copy(
            update={"problem_request": {"scenario": "not_a_scenario"}}
        )
        result = await provider_benchmark_case(case)
        assert result.status is BenchmarkCaseStatus.FAILED
        assert result.metrics["unknown_scenario"] == 1.0

    @pytest.mark.asyncio
    async def test_a_wrong_expectation_fails_rather_than_being_absorbed(self) -> None:
        """The manifest is checked against behaviour, not the other way round."""
        case = next(
            item
            for item in _cases(CI_MANIFEST)
            if item.problem_request["scenario"] == "advisory_verify"
            and item.problem_request.get("answer") == "empty"
        )
        mislabelled = case.model_copy(update={"expected_outputs": {"status": "correct"}})
        assert (await provider_benchmark_case(mislabelled)).status is BenchmarkCaseStatus.FAILED


class TestDeterminism:
    @pytest.mark.asyncio
    async def test_two_runs_of_the_same_case_agree_on_every_metric_but_time(
        self,
    ) -> None:
        for case in _cases(CI_MANIFEST):
            first = (await provider_benchmark_case(case)).metrics
            second = (await provider_benchmark_case(case)).metrics
            del first["elapsed_seconds"], second["elapsed_seconds"]
            assert first == second, case.case_id

    @pytest.mark.asyncio
    async def test_receipt_timestamps_are_fixed_not_wall_clock(self) -> None:
        """A wall-clock timestamp would make every stored report differ from the last."""
        results = [await provider_benchmark_case(case) for case in _cases(CI_MANIFEST)]
        assert len({result.started_at for result in results}) == 1
