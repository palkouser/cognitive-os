from cognitive_os.events.catalog import build_default_event_catalog


def test_controller_event_types_are_explicitly_registered() -> None:
    event_types = {name for name, _version in build_default_event_catalog().list_event_types()}
    assert {
        "problem.representation_created",
        "problem.representation_revised",
        "controller.state_changed",
        "controller.decision_recorded",
        "controller.clarification_requested",
        "controller.clarification_provided",
        "controller.checkpoint_created",
        "controller.continuation_issued",
        "controller.continuation_consumed",
        "controller.budget_exhausted",
        "controller.paused",
        "controller.cancelled",
    } <= event_types
