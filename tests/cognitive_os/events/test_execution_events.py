from cognitive_os.events.execution_events import ExecutionStepRetried, PlanCreated


def test_plan_and_retry_payload_metadata(plan) -> None:
    assert PlanCreated(plan=plan).event_type == "plan.created"
    retry = ExecutionStepRetried(
        step_id=plan.steps[0].step_id,
        previous_attempt=1,
        next_attempt=2,
    )
    assert retry.event_type == "execution_step.retried"
