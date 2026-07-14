"""Import SWE-bench-compatible JSONL metadata without cloning or execution."""

import argparse
from pathlib import Path

import yaml

from cognitive_os.benchmarks.swebench_adapter import import_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--license", required=True)
    args = parser.parse_args()
    cases = import_jsonl(args.input, license_name=args.license, limit=args.limit)
    args.output_manifest.write_text(
        yaml.safe_dump({"cases": [item.model_dump(mode="json") for item in cases]}, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Imported {len(cases)} case records without network or repository cloning.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
