"""S22E-401: the release head's gates — the CI lanes re-read, and the whole matrix re-run.

Gate M condition 9 binds `sprint-22e-w4-gates.json#lanes`, with the reading "the CI lanes at the
release head, **re-read rather than quoted**". So this driver goes and reads them: it resolves
the release head from git, finds the CI run whose head is exactly that commit, and records every
lane's own conclusion. A record that quoted "30 of 30" from a wave log would satisfy the sentence
in appearance and nothing in substance.

**Two independent measurements, deliberately.** The lanes are GitHub's verdict on the release
head; the matrix is this repository's own fifteen-gate evaluation matrix, run locally in a clean
worktree at the same commit. 22D W4-F1's rule is that nothing is green under one command line,
one interpreter or one machine, and the cheapest way to honour it at the release is to have the
two verdicts disagree loudly if they ever do.

    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/w4_gates_22e.py --matrix <file>
    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/w4_gates_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

OUTPUT = EVIDENCE / "sprint-22e-w4-gates.json"
RECORDED_AT = "2026-08-16T00:00:00Z"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _run(*command: str) -> str:
    return subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def read_lanes(head: str) -> tuple[dict[str, str], dict[str, Any]]:
    """Every CI lane's own conclusion at the exact release head, from GitHub."""
    runs = json.loads(
        _run(
            "gh",
            "run",
            "list",
            "--branch",
            "main",
            "--limit",
            "20",
            "--json",
            "databaseId,headSha,status,conclusion",
        )
    )
    exact = next((item for item in runs if item["headSha"] == head), None)
    if exact is None:
        raise SystemExit(f"no CI run found at the exact release head {head[:7]}")
    detail = json.loads(
        _run("gh", "run", "view", str(exact["databaseId"]), "--json", "conclusion,jobs")
    )
    lanes = {str(job["name"]): str(job["conclusion"]) for job in detail["jobs"]}
    return lanes, {
        "run_id": exact["databaseId"],
        "head_sha": exact["headSha"],
        "status": exact["status"],
        "conclusion": detail["conclusion"],
    }


def build(head: str, matrix_path: Path) -> dict[str, Any]:
    from gate_m_22e import CONDITION_9_FAMILIES

    lanes, run = read_lanes(head)
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    ran = [item for item in matrix if item.get("ran")]
    failed = [item["gate_id"] for item in ran if not item.get("passed")]

    return {
        "items": ["S22E-401"],
        "sprint": "22E",
        "wave": "W4",
        "schema_version": 1,
        "release_head": head,
        "lanes": lanes,
        "lane_count": len(lanes),
        "lanes_not_successful": sorted(
            name for name, verdict in lanes.items() if verdict != "success"
        ),
        "ci_run": run,
        "condition_9_families": {
            family: {"lane": lane, "conclusion": lanes.get(lane)}
            for family, lane in CONDITION_9_FAMILIES.items()
        },
        "every_named_family_has_a_passing_lane": all(
            lanes.get(lane) == "success" for lane in CONDITION_9_FAMILIES.values()
        ),
        "local_matrix": {
            "gates": len(matrix),
            "ran": len(ran),
            "passed": len(ran) - len(failed),
            "failed": failed,
            "driver_decided": [item["gate_id"] for item in matrix if not item.get("ran")],
            "wall_clock_seconds": round(sum(float(item.get("seconds", 0)) for item in ran), 3),
            "gate_ids_passed": [item["gate_id"] for item in ran if item.get("passed")],
        },
        "two_independent_verdicts": (
            "GitHub's lanes at the release head, and this repository's own fifteen-gate matrix "
            "run locally in a clean worktree at the same commit; 22D W4-F1's rule is that "
            "nothing is green under one command line"
        ),
        "recorded_at": RECORDED_AT,
    }


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    """The lanes are re-read from GitHub; the local matrix is an observation of one run."""
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    lanes, _run_detail = read_lanes(record["release_head"])
    return {
        "seal_recomputes": _sha256(canonical(body)) == record["integrity_content_hash"],
        "lanes_still_read_the_same": lanes == record["lanes"],
        "every_named_family_still_passes": record["every_named_family_has_a_passing_lane"],
        "recorded_not_recomputed": ["local_matrix"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--head", default=None, help="the release head; defaults to origin/main")
    parser.add_argument("--matrix", default=None, help="the local matrix result, as JSON")
    arguments = parser.parse_args()

    if arguments.check:
        verdict = check_record(json.loads(OUTPUT.read_text(encoding="utf-8")))
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return (
            0
            if all(value for key, value in verdict.items() if key != "recorded_not_recomputed")
            else 1
        )

    if not arguments.matrix:
        raise SystemExit("--matrix is required: the local half of the verdict is not optional")
    head = arguments.head or _run("git", "rev-parse", "origin/main")
    record = build(head, Path(arguments.matrix))
    record["integrity_content_hash"] = _sha256(canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "release_head": head[:7],
                "lane_count": record["lane_count"],
                "lanes_not_successful": record["lanes_not_successful"],
                "every_named_family_has_a_passing_lane": record[
                    "every_named_family_has_a_passing_lane"
                ],
                "local_matrix": {
                    key: record["local_matrix"][key] for key in ("ran", "passed", "failed")
                },
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
