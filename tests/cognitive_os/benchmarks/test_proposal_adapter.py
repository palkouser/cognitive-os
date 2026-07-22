import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.proposal_adapter import proposal_benchmark_case
from cognitive_os.domain.proposals import HarnessProposalType


@pytest.mark.asyncio
async def test_proposal_manifests_cover_every_type_without_implementation() -> None:
    ci = load_manifest(__import__("pathlib").Path("benchmarks/manifests/sprint18-proposal-ci.yaml"))
    seed = load_manifest(
        __import__("pathlib").Path("benchmarks/manifests/sprint18-proposal-seed.yaml")
    )
    assert len(ci.cases) == 16
    assert len(seed.cases) == 64
    assert {case.problem_request["scenario"] for case in ci.cases} >= {
        item.value for item in HarnessProposalType
    }
    result = await proposal_benchmark_case(ci.cases[0])
    assert result.metrics["implementation_actions"] == 0
    assert result.metrics["destination_writes"] == 0
