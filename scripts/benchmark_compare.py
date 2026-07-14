"""Compare two compatible native benchmark reports."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--fail-on-new-required-failure", action="store_true")
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    if (baseline["benchmark_id"], baseline["benchmark_version"]) != (
        candidate["benchmark_id"],
        candidate["benchmark_version"],
    ):
        raise ValueError("benchmark reports are not comparable")
    old = {item["case_id"]: item["status"] for item in baseline["cases"]}
    new = {item["case_id"]: item["status"] for item in candidate["cases"]}
    if set(old) != set(new):
        raise ValueError("benchmark case sets do not match")
    regressions = sorted(key for key in old if old[key] == "passed" and new[key] != "passed")
    print(json.dumps({"newly_failing": regressions}, sort_keys=True))
    return 1 if args.fail_on_new_required_failure and regressions else 0


if __name__ == "__main__":
    raise SystemExit(main())
