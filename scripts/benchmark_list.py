"""Inspect a tracked benchmark manifest."""

import argparse
import json
from pathlib import Path

from cognitive_os.benchmarks.cases import load_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path("benchmarks/manifests/sprint7-seed.yaml")
    )
    args = parser.parse_args()
    manifest = load_manifest(args.manifest)
    print(
        json.dumps(
            {
                "benchmark_id": manifest.benchmark_id,
                "version": manifest.version,
                "manifest_hash": manifest.manifest_hash,
                "cases": [item.case_id for item in manifest.cases],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
