from cognitive_os.events.model_events import ModelCallCompleted


def test_model_event_embeds_typed_result(model_result) -> None:
    payload = ModelCallCompleted(result=model_result)
    assert payload.event_type == "model_call.completed"
    assert payload.result == model_result
