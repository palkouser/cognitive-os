"""S22E-303: the landing — what reached protected `main`, and proof it is what was approved.

The record's *name and read path were pre-registered in W0*: Gate M condition 8 binds
`sprint-22e-w3-promotion.json#post_merge_ci.conclusion`. So this file is not free to be called
anything; W4 resolves that binding against exactly this record, which is what makes the gate a
binding rather than a description.

**The one thing here that is recomputed rather than observed.** A promotion record that only
quoted a PR number and a green tick would prove that *something* merged. This reads the two
approved files back out of the merged commit and hashes them, and compares against the hashes
the evaluation matrix ran over. If the bytes on protected `main` are not the bytes that were
evaluated and approved, this record says so — and `--check` re-derives that comparison from git
every time, because it is the claim most worth being unable to fake.

Everything else — the merge commit, the merge method, the CI conclusion and job counts — is an
observation of one moment, re-read and compared against nothing (22C W1-F1).

    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/promotion_22e.py --pr 237
    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/promotion_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22e-w3-promotion.json"
RECORDED_AT = "2026-08-16T00:00:00Z"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def sealed(name: str) -> dict[str, Any]:
    stored = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != stored["integrity_content_hash"]:
        raise ValueError(f"{name} does not recompute its own seal")
    return stored


def _run(*command: str) -> str:
    return subprocess.run(
        command, cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def landed_file_hashes(commit: str, files: tuple[str, ...]) -> dict[str, str]:
    """Hash each approved file **as it exists in the merged commit**, straight from git."""
    return {
        path: _sha256(
            subprocess.run(
                ("git", "show", f"{commit}:{path}"),
                cwd=REPO,
                capture_output=True,
                check=True,
            ).stdout
        )
        for path in files
    }


def build(pr_number: int) -> dict[str, Any]:
    approval = sealed("sprint-22e-w3-approval.json")
    change = sealed("sprint-22e-w3-approved-change.json")

    pull = json.loads(
        _run(
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,state,mergedAt,mergeCommit,baseRefName,headRefName,title",
        )
    )
    merge_commit = pull["mergeCommit"]["oid"]
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
    exact = next((item for item in runs if item["headSha"] == merge_commit), None)
    if exact is None:
        raise SystemExit(f"no CI run found at the exact merged head {merge_commit[:7]}")
    jobs = json.loads(
        _run("gh", "run", "view", str(exact["databaseId"]), "--json", "conclusion,jobs")
    )
    counts: dict[str, int] = {}
    for job in jobs["jobs"]:
        counts[str(job["conclusion"])] = counts.get(str(job["conclusion"]), 0) + 1

    approved_files = tuple(approval["what_is_approved"]["changed_files"])
    evaluated = {item["file"]: item["after_hash"] for item in change["repair"]["files"]}
    landed = landed_file_hashes(merge_commit, approved_files)

    return {
        "items": ["S22E-303"],
        "sprint": "22E",
        "wave": "W3",
        "schema_version": 1,
        "pull_request": {
            "number": pull["number"],
            "title": pull["title"],
            "state": pull["state"],
            "base": pull["baseRefName"],
            "head": pull["headRefName"],
            "merged_at": pull["mergedAt"],
            "merge_commit": merge_commit,
            "merge_method": "squash",
        },
        "what_landed": {
            "files": list(approved_files),
            "evaluated_hashes": {path: evaluated[path] for path in approved_files},
            "landed_hashes": landed,
            "landed_bytes_are_the_evaluated_bytes": all(
                landed[path] == evaluated[path] for path in approved_files
            ),
            "why_this_is_recomputed": (
                "a promotion record that quoted a PR number and a green tick would prove that "
                "something merged; this hashes the approved files out of the merged commit and "
                "compares them with what the evaluation matrix ran over"
            ),
        },
        "authority": {
            "approver": approval["approver"],
            "approval_record_hash": approval["integrity_content_hash"],
            "approved_change_record_hash": change["integrity_content_hash"],
            "the_merge_was_performed_by": "the gate owner, on explicit instruction",
            "no_provider_merged_anything": (
                "no released provider configuration in this repository can write a file, and "
                "the loop's drivers have no merge, tag or push path"
            ),
        },
        "post_merge_ci": {
            "run_id": exact["databaseId"],
            "head_sha": exact["headSha"],
            "head_is_the_merge_commit": exact["headSha"] == merge_commit,
            "status": exact["status"],
            "conclusion": jobs["conclusion"],
            "job_counts": counts,
        },
        "recorded_at": RECORDED_AT,
    }


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    """The seal and the byte comparison are recomputed; the PR and CI facts are re-read."""
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    landed = landed_file_hashes(
        record["pull_request"]["merge_commit"], tuple(record["what_landed"]["files"])
    )
    approval = sealed("sprint-22e-w3-approval.json")
    return {
        "seal_recomputes": _sha256(canonical(body)) == record["integrity_content_hash"],
        "landed_bytes_still_match_the_evaluated_ones": all(
            landed[path] == record["what_landed"]["evaluated_hashes"][path]
            for path in record["what_landed"]["files"]
        ),
        "approval_record_still_seals": (
            approval["integrity_content_hash"] == record["authority"]["approval_record_hash"]
        ),
        "recorded_not_recomputed": ["pull_request", "post_merge_ci"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--pr", type=int, default=237)
    arguments = parser.parse_args()

    if arguments.check:
        verdict = check_record(json.loads(OUTPUT.read_text(encoding="utf-8")))
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return (
            0
            if all(value for key, value in verdict.items() if key != "recorded_not_recomputed")
            else 1
        )

    record = build(arguments.pr)
    record["integrity_content_hash"] = _sha256(canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "merge_commit": record["pull_request"]["merge_commit"][:7],
                "landed_bytes_are_the_evaluated_bytes": record["what_landed"][
                    "landed_bytes_are_the_evaluated_bytes"
                ],
                "post_merge_ci": record["post_merge_ci"]["conclusion"],
                "job_counts": record["post_merge_ci"]["job_counts"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
