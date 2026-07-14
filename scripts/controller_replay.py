"""Replay a controller task-run stream without repeating side effects."""

import argparse
import asyncio
import json

from controller_common import build_event_store, parse_task_run_id

from cognitive_os.application.services.controller_recovery import ControllerRecoveryService


async def run(task_run_id: str, verify_checkpoints: bool) -> None:
    engine, store = build_event_store()
    try:
        snapshot = await ControllerRecoveryService(store).replay(parse_task_run_id(task_run_id))
        output = snapshot.model_dump(mode="json")
        output["checkpoint_verification_requested"] = verify_checkpoints
        print(json.dumps(output, sort_keys=True))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-run-id", required=True)
    parser.add_argument("--verify-checkpoints", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.task_run_id, args.verify_checkpoints))


if __name__ == "__main__":
    main()
