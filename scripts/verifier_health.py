"""Run bounded health checks for available built-in verifiers."""

import argparse
import asyncio
import json

from cognitive_os.verification.factory import build_builtin_registry


async def _run() -> list[dict[str, str]]:
    registry = build_builtin_registry()
    rows = []
    for descriptor in registry.list_available():
        health = await registry.require(descriptor.verifier_id, descriptor.version).health_check()
        rows.append(
            {
                "verifier_id": descriptor.verifier_id,
                "status": health.status.value,
                "reason": health.reason or "",
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.parse_args()
    rows = asyncio.run(_run())
    print(json.dumps(rows, sort_keys=True))
    return 0 if all(item["status"] == "available" for item in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
