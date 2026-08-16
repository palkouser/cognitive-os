"""S22E-403: the release — which tag was created, what it peels to, and which was not.

Gate M condition 10 binds `sprint-22e-release.json#tag.peels_to`, with the reading "post-merge
main CI, and **`sprint-22-baseline`** peeling to the verified protected commit". That path
therefore has to mean the *programme* tag's peel and nothing else, so on a typed negative it is
`null` — the programme tag is not created, and a record that quietly pointed the path at the
sprint-local negative tag would turn a failed condition into a passing one by renaming a field.

**Tag after the squash merge, never before.** 22C's release lesson, and it is not cosmetic: a
squash merge leaves the wave branch a non-ancestor of `main`, so a tag placed on the branch head
points at a commit protected `main` never contains. The target here is the merge commit, and the
peel is verified by asking git rather than by asserting it.

    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/release_22e.py --pr 236 --create-tag
    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/release_22e.py --check
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
OUTPUT = EVIDENCE / "sprint-22e-release.json"
RECORDED_AT = "2026-08-16T00:00:00Z"

PROGRAMME_TAG = "sprint-22-baseline"
NEGATIVE_TAG = "sprint-22e-evidence-baseline"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _run(*command: str, check: bool = True) -> str:
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=check)
    return result.stdout.strip()


def _tag_exists(name: str) -> bool:
    return bool(
        subprocess.run(
            ("git", "rev-parse", "-q", "--verify", f"refs/tags/{name}"),
            cwd=REPO,
            capture_output=True,
        ).returncode
        == 0
    )


def peels_to(name: str) -> str | None:
    """What the annotated tag actually points at, asked of git rather than asserted."""
    if not _tag_exists(name):
        return None
    return _run("git", "rev-list", "-n", "1", name)


def post_merge_ci(head: str) -> dict[str, Any]:
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
        raise SystemExit(f"no CI run at the exact release head {head[:7]}")
    detail = json.loads(
        _run("gh", "run", "view", str(exact["databaseId"]), "--json", "conclusion,jobs")
    )
    counts: dict[str, int] = {}
    for job in detail["jobs"]:
        counts[str(job["conclusion"])] = counts.get(str(job["conclusion"]), 0) + 1
    return {
        "run_id": exact["databaseId"],
        "head_sha": exact["headSha"],
        "conclusion": detail["conclusion"],
        "job_counts": counts,
    }


def build(pr_number: int, *, outcome: str) -> dict[str, Any]:
    pull = json.loads(
        _run("gh", "pr", "view", str(pr_number), "--json", "number,state,mergedAt,mergeCommit")
    )
    if pull["state"] != "MERGED":
        raise SystemExit(f"PR #{pr_number} is {pull['state']}, not MERGED; there is no release")
    head = pull["mergeCommit"]["oid"]
    ci = post_merge_ci(head)

    programme_peel = peels_to(PROGRAMME_TAG)
    negative_peel = peels_to(NEGATIVE_TAG)

    return {
        "items": ["S22E-403"],
        "sprint": "22E",
        "wave": "W4",
        "schema_version": 1,
        "outcome": outcome,
        "release": {
            "pull_request": pull["number"],
            "merged_at": pull["mergedAt"],
            "merge_commit": head,
            "merge_method": "squash",
            "post_merge_ci": ci,
        },
        "tag": {
            # **What condition 10 reads.** The programme tag's peel, and nothing else. On a
            # typed negative it is null because the programme tag is not created; pointing this
            # path at the sprint-local negative tag would turn a failed condition into a
            # passing one by renaming a field.
            "peels_to": programme_peel,
            "name": PROGRAMME_TAG,
            "created": programme_peel is not None,
            "why_not_created": (
                None
                if programme_peel is not None
                else "the programme tag marks a passing Gate M and five met exits; this sprint "
                "is a typed negative, and the plan names the negative tag for that case"
            ),
        },
        "negative_tag": {
            "name": NEGATIVE_TAG,
            "created": negative_peel is not None,
            "annotated": _tag_exists(NEGATIVE_TAG)
            and _run("git", "cat-file", "-t", NEGATIVE_TAG) == "tag",
            "peels_to": negative_peel,
            "peels_to_the_merge_commit": negative_peel == head,
            "placed_after_the_squash_merge": True,
            "why_that_order": (
                "a squash merge leaves the wave branch a non-ancestor of main, so a tag placed "
                "on the branch head would point at a commit protected main never contains "
                "(22C's release lesson)"
            ),
        },
        "recorded_at": RECORDED_AT,
    }


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    """Both peels are asked of git again; the CI verdict is an observation of one run."""
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    return {
        "seal_recomputes": _sha256(canonical(body)) == record["integrity_content_hash"],
        "programme_tag_peel_unchanged": peels_to(PROGRAMME_TAG) == record["tag"]["peels_to"],
        "negative_tag_still_peels_to_the_merge_commit": (
            peels_to(NEGATIVE_TAG) == record["release"]["merge_commit"]
        ),
        "recorded_not_recomputed": ["release.post_merge_ci"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--pr", type=int, default=236)
    parser.add_argument("--outcome", default="typed_negative")
    parser.add_argument("--create-tag", action="store_true")
    parser.add_argument("--message", default=None)
    arguments = parser.parse_args()

    if arguments.check:
        verdict = check_record(json.loads(OUTPUT.read_text(encoding="utf-8")))
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return (
            0
            if all(value for key, value in verdict.items() if key != "recorded_not_recomputed")
            else 1
        )

    if arguments.create_tag:
        pull = json.loads(_run("gh", "pr", "view", str(arguments.pr), "--json", "mergeCommit"))
        head = pull["mergeCommit"]["oid"]
        if not _tag_exists(NEGATIVE_TAG):
            _run(
                "git",
                "tag",
                "-a",
                NEGATIVE_TAG,
                head,
                "-m",
                arguments.message or f"Sprint 22E typed negative at {head[:7]}",
            )
            _run("git", "push", "origin", NEGATIVE_TAG)

    record = build(arguments.pr, outcome=arguments.outcome)
    record["integrity_content_hash"] = _sha256(canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "outcome": record["outcome"],
                "merge_commit": record["release"]["merge_commit"][:7],
                "post_merge_ci": record["release"]["post_merge_ci"]["conclusion"],
                "programme_tag_peels_to": record["tag"]["peels_to"],
                "negative_tag_peels_to_the_merge_commit": record["negative_tag"][
                    "peels_to_the_merge_commit"
                ],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
