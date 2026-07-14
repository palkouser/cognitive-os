"""Render a concise Markdown view from a native benchmark JSON report."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(args.report.read_text(encoding="utf-8"))
    print(f"# Benchmark report: {value['benchmark_id']} {value['benchmark_version']}\n")
    print("| Case | Status |\n|---|---|")
    for item in value["cases"]:
        print(f"| {item['case_id']} | {item['status']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
