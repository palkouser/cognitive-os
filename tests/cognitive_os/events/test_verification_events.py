from cognitive_os.events.verification_events import VerifierCompleted


def test_verifier_event_embeds_typed_snapshot(verifier_result) -> None:
    payload = VerifierCompleted(result=verifier_result)
    assert payload.event_type == "verifier.completed"
    assert payload.result == verifier_result
