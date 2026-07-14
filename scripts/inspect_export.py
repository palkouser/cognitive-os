"""Export a tracked native benchmark manifest to an Inspect-compatible directory."""

import argparse
from pathlib import Path

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.inspect_adapter import export_task


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    path = export_task(load_manifest(args.manifest).cases, args.output_directory)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
