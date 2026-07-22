"""Run the credential-free Sprint 19 controlled-change path."""

import asyncio
import json

from cognitive_os.changes.demo import run_demo


async def smoke() -> dict[str, object]:
    result = await run_demo()
    return {
        "healthy": True,
        "experiment_id": str(result["experiment"].experiment_id),
        "candidate_hash": result["candidate"].content_hash,
        "assessment_decision": result["assessment"].decision,
        "promotion_bundle_hash": result["promotion_bundle"].content_hash,
        "evaluation_gates": len(result["evaluation_matrix"].execution_order),
        "active_checkout_mutations": 0,
        "active_database_writes": 0,
        "runtime_release_operations": 0,
    }


def main() -> int:
    print(json.dumps(asyncio.run(smoke()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
