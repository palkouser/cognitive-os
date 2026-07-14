from __future__ import annotations

import pytest

from LightAgent import JsonLightFlowStore, LightFlow, RunResult

pytestmark = pytest.mark.contract


class FakeAgent:
    def __init__(self, responses: list[str | RunResult]) -> None:
        self.responses = list(responses)

    def run(self, query: str, **kwargs: object) -> RunResult:
        response = self.responses.pop(0)
        if isinstance(response, RunResult):
            return response
        return RunResult(content=response)


def test_two_step_flow_and_retry_contract() -> None:
    first = FakeAgent(["facts"])
    second = FakeAgent([RunResult(content="failed", error="failed"), "report"])
    flow = (
        LightFlow()
        .step("research", agent=first)
        .step("write", agent=second, depends_on=["research"], max_retry=2)
    )

    result = flow.run("prepare report")

    assert result.success is True
    assert result.content == "report"
    assert result.steps[1].attempts == 2


def test_checkpoint_and_resume_contract(tmp_path) -> None:
    store = JsonLightFlowStore(tmp_path)
    agent = FakeAgent([RunResult(content="failed", error="failed"), "recovered"])
    flow = LightFlow(store=store).step("work", agent=agent)

    failed = flow.run("work", run_id="contract-run")
    resumed = flow.resume("contract-run")

    assert failed.success is False
    assert resumed.success is True
    assert flow.get_run("contract-run")["steps"][0]["status"] == "success"
