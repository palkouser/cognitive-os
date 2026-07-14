"""Evaluate an acceptance policy and verifier result bundle."""

import argparse
import json
from pathlib import Path
from uuid import UUID

from cognitive_os.application.services.acceptance_service import AcceptancePolicyService
from cognitive_os.domain.acceptance import AcceptancePolicy
from cognitive_os.domain.verification import VerifierResult


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-file", type=Path, required=True)
    parser.add_argument("--results-file", type=Path, required=True)
    parser.add_argument("--task-run-id", type=UUID, required=True)
    args = parser.parse_args()
    policy = AcceptancePolicy.model_validate_json(args.policy_file.read_bytes())
    raw = json.loads(args.results_file.read_text(encoding="utf-8"))
    results = tuple(VerifierResult.model_validate(item) for item in raw)
    decision = AcceptancePolicyService().evaluate(policy, args.task_run_id, results)
    print(decision.model_dump_json(indent=2))
    return 0 if decision.decision.value == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
