from cognitive_os.domain import ActorRef, ActorType
from cognitive_os.events.user_events import UserCorrectionReceived


def test_user_correction_records_provenance_and_time(task_run, now) -> None:
    payload = UserCorrectionReceived(
        task_run_id=task_run.task_run_id,
        correction={"statement": "Use the reviewed value."},
        received_from=ActorRef(actor_type=ActorType.USER, actor_id="reviewer-1"),
        received_at=now,
        source="interactive-review",
    )
    assert payload.source == "interactive-review"
    assert payload.event_type == "user.correction_received"
