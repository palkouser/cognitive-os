"""Replay and inspect a controller task-run projection."""

import argparse
import asyncio
import json

from controller_common import build_event_store, parse_task_run_id

from cognitive_os.application.services.controller_recovery import ControllerRecoveryService


async def run(task_run_id: str, json_output: bool) -> None:
    engine, store = build_event_store()
    try:
        snapshot = await ControllerRecoveryService(store).replay(parse_task_run_id(task_run_id))
        output = snapshot.model_dump(mode="json")
        print(
            json.dumps(output, sort_keys=True)
            if json_output
            else f"{output['task_run_id']}\t{output['state']}\t{output['last_stream_version']}"
        )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-run-id", required=True)
    parser.add_argument("--include-plan", action="store_true")
    parser.add_argument("--include-usage", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.task_run_id, args.json))


if __name__ == "__main__":
    main()
