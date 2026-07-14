import pytest

from cognitive_os.application.services.controller_recovery import (
    ActiveChildClassification,
    classify_child_call,
)


@pytest.mark.parametrize(
    ("events", "expected"),
    [
        ((), ActiveChildClassification.NOT_STARTED),
        (("tool_call.requested",), ActiveChildClassification.SAFE_TO_REEVALUATE),
        (("tool_call.requested", "tool_call.started"), ActiveChildClassification.UNCERTAIN),
        (("tool_call.started", "tool_call.completed"), ActiveChildClassification.TERMINAL),
        (("tool_call.started", "tool_call.denied"), ActiveChildClassification.TERMINAL),
    ],
)
def test_active_child_classification_is_fail_safe(events, expected) -> None:
    assert classify_child_call(events) is expected
