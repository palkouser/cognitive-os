"""Render a canonical Coding Agent JSON outcome as Markdown."""

import argparse
from pathlib import Path

from cognitive_os.coding.reporting import render_outcome_markdown
from cognitive_os.domain.coding import CodingOutcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outcome", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    outcome = CodingOutcome.model_validate_json(args.outcome.read_bytes())
    report = render_outcome_markdown(outcome)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
