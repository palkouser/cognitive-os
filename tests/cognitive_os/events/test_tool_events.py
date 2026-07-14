from cognitive_os.events.tool_events import ToolCallCompleted, ToolCallDenied


def test_permission_denial_is_distinct_from_completion(tool_result, now) -> None:
    denied = ToolCallDenied(
        tool_call_id=tool_result.tool_call_id,
        denied_at=now,
        denied_by="policy-engine",
        reason="Approval required",
    )
    completed = ToolCallCompleted(result=tool_result)
    assert denied.event_type == "tool_call.denied"
    assert completed.event_type == "tool_call.completed"
