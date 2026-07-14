from __future__ import annotations

import pytest

from LightAgent import HookContext, HookDecision, HookManager, TraceRecorder

pytestmark = pytest.mark.contract


def test_hook_can_replace_and_block_runtime_payload() -> None:
    phases: list[str] = []

    def hook(context: HookContext) -> HookDecision:
        phases.append(context.phase)
        if context.phase == "before_model_request":
            return HookDecision.replace({"query": "rewritten"})
        return HookDecision.block("blocked")

    manager = HookManager([hook])
    replaced = manager.run(HookContext(phase="before_model_request", payload={"query": "original"}))
    blocked = manager.run(HookContext(phase="after_model_response", payload={"response": "unsafe"}))

    assert replaced.payload == {"query": "rewritten"}
    assert blocked.action == "block"
    assert blocked.reason == "blocked"
    assert phases == ["before_model_request", "after_model_response"]


def test_trace_export_contract_is_serializable() -> None:
    recorder = TraceRecorder(enabled=True, trace_id="trace-1")
    recorder.record("model_request", {"model": "offline-fake"})
    recorder.record("tool_result", {"name": "add_numbers", "output": "42"})

    exported = recorder.to_list()

    assert [event["type"] for event in exported] == ["model_request", "tool_result"]
    assert all(event["trace_id"] == "trace-1" for event in exported)
    assert set(exported[0]) == {"type", "data", "trace_id", "timestamp"}
