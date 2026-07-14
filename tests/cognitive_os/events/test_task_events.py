from cognitive_os.domain import PrivacyClass, StreamType, new_id
from cognitive_os.events import create_event_envelope
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.task_events import TaskCreated, TaskRunStarted


def test_task_payloads_create_and_decode_envelopes(task, task_run, actor, now) -> None:
    catalog = build_default_event_catalog()
    for payload, stream_id, stream_type in (
        (TaskCreated(task=task), task.task_id, StreamType.TASK),
        (TaskRunStarted(task_run=task_run), task_run.task_run_id, StreamType.TASK_RUN),
    ):
        envelope = create_event_envelope(
            payload=payload,
            stream_id=stream_id,
            stream_type=stream_type,
            stream_version=1,
            correlation_id=new_id(),
            causation_event_id=None,
            actor=actor,
            source_component="contract-test",
            privacy_class=PrivacyClass.INTERNAL,
            occurred_at=now,
            recorded_at=now,
        )
        assert catalog.decode_payload(envelope) == payload
