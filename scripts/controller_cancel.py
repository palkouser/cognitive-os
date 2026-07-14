"""Expected-version protected controller cancellation."""

import argparse
import asyncio
import json

from controller_common import build_event_store, parse_task_run_id

from cognitive_os.application.services.controller_recovery import ControllerRecoveryService
from cognitive_os.controller.machine import ControllerStateMachine, StateTransition
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.controller import ControllerState
from cognitive_os.domain.identifiers import new_id
from cognitive_os.events.controller_event_service import ControllerEventService
from cognitive_os.events.controller_events import ControllerCancelled, ControllerStateChanged


async def run(task_run_id_text: str, reason: str) -> None:
    task_run_id = parse_task_run_id(task_run_id_text)
    engine, store = build_event_store()
    try:
        snapshot = await ControllerRecoveryService(store).replay(task_run_id)
        decision_id = new_id()
        ControllerStateMachine.require_transition(
            StateTransition(
                snapshot.state,
                ControllerState.CANCELLED,
                reason,
                decision_id,
                snapshot.last_stream_version,
            )
        )
        events = ControllerEventService(store)
        result = await events.append(
            task_run_id=task_run_id,
            payload=ControllerStateChanged(
                previous_state=snapshot.state,
                current_state=ControllerState.CANCELLED,
                reason=reason,
                decision_id=decision_id,
                changed_at=utc_now(),
            ),
            expected_version=snapshot.last_stream_version,
            correlation_id=task_run_id,
        )
        result = await events.append(
            task_run_id=task_run_id,
            payload=ControllerCancelled(
                task_run_id=task_run_id, reason=reason, cancelled_at=utc_now()
            ),
            expected_version=result.current_stream_version,
            correlation_id=task_run_id,
        )
        print(
            json.dumps(
                {
                    "task_run_id": str(task_run_id),
                    "state": "cancelled",
                    "last_stream_version": result.current_stream_version,
                },
                sort_keys=True,
            )
        )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-run-id", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.task_run_id, args.reason))


if __name__ == "__main__":
    main()
