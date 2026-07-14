"""Validate controller resume inputs without exposing the continuation token."""

import argparse
import json
from pathlib import Path

from controller_common import parse_task_run_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-run-id", required=True)
    parser.add_argument("--continuation-token", required=True)
    parser.add_argument("--answers-file", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    task_run_id = parse_task_run_id(args.task_run_id)
    answers = json.loads(args.answers_file.read_text(encoding="utf-8"))
    if not isinstance(answers, dict) or not args.continuation_token:
        raise ValueError("resume requires a non-empty token and an answer mapping")
    output = {
        "task_run_id": str(task_run_id),
        "validated_answer_count": len(answers),
        "token_echoed": False,
    }
    print(json.dumps(output, sort_keys=True) if args.json else f"{task_run_id}\tresume-input-valid")


if __name__ == "__main__":
    main()
