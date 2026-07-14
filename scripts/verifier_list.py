"""List deterministic built-in verifier registrations."""

import argparse
import json

from cognitive_os.verification.factory import build_builtin_registry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-unavailable", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--config")
    args = parser.parse_args()
    registry = build_builtin_registry()
    available = {(item.verifier_id, item.version) for item in registry.list_available()}
    descriptors = registry.list_all() if args.include_unavailable else registry.list_available()
    rows = [
        {
            "verifier_id": item.verifier_id,
            "version": item.version,
            "kind": item.kind.value,
            "available": (item.verifier_id, item.version) in available,
            "capabilities": [capability.capability_id for capability in item.capabilities],
            "requires_sandbox": item.requires_sandbox,
        }
        for item in descriptors
    ]
    if args.json:
        print(json.dumps(rows, sort_keys=True))
    else:
        for row in rows:
            print(
                f"{row['verifier_id']}@{row['version']} {row['kind']} "
                f"available={row['available']} sandbox={row['requires_sandbox']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
