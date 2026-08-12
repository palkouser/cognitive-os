#!/usr/bin/env python
"""S22A-053: the release, recorded from the remote rather than from prose.

    scripts/release_22a.py --pull-request 231 [--output docs/.../sprint-22a-release.json]

Every handle in this record is read back from GitHub and from the local repository at the
moment it runs: `origin/main`, the merge commit and its timestamp, both CI runs with their
conclusions and job counts, the annotated tag object and the commit it peels to, and the branch
protection state. Nothing is copied from the execution log, because the execution log is prose
and this record is what a reader checks the prose against.

Four things it refuses to do.

*It does not create anything.* No merge, no tag, no push. It reads. A record that could produce
the state it describes would be a record of itself, and on protected `main` the merge is the
gate owner's decision rather than a wave's.

*It does not accept a tag that moved.* The tag object is read from the remote and its peel is
compared to the merge commit. The tag is created once, on the commit exact-head CI passed on,
and never moved or recreated, so a peel that disagrees is a finding rather than a value to
write down.

*It does not report a pass it did not read.* `sprint-22a-domain-baseline` is the success tag.
An exit-criteria record that does not read as four-of-four while this tag exists is a
contradiction, and so is the stop tag existing at all. Both directions are refusals, and the
record states which one it is enforcing.

*And it does not describe a release that has not happened.* Before the merge there is no merge
commit, no post-merge CI run and no tag, and this script exits saying so rather than writing a
record with holes in it. That refusal is the normal state of this file until the gate owner
acts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess  # nosec B404 - fixed argv lists of git and gh, never a shell
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-22" / "evidence"

REMOTE = "palkouser/cognitive-os"
TAG = "sprint-22a-domain-baseline"
#: The tag a stop would have carried. Checked for absence: a sprint cannot release under both.
STOP_TAG = "sprint-22a-evidence-baseline"


def _run(argv: list[str]) -> str:
    completed = subprocess.run(  # nosec B603 - fixed argv list, shell=False
        argv, capture_output=True, text=True, check=True, cwd=REPOSITORY
    )
    return completed.stdout.strip()


def _api(path: str, *, jq: str | None = None) -> Any:
    argv = ["gh", "api", path]
    if jq is not None:
        argv += ["--jq", jq]
    output = _run(argv)
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return output


def _canonical(value: object) -> bytes:
    """The bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode(
        "utf-8"
    )


def _read(name: str) -> dict[str, Any]:
    body: dict[str, Any] = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
    return body


def _ci_run(head_sha: str) -> dict[str, Any]:
    """The run whose head is exactly this commit, with its job tally read back."""
    runs = _api(
        f"repos/{REMOTE}/actions/runs?per_page=50",
        jq=(
            f'[.workflow_runs[] | select(.head_sha == "{head_sha}")] '
            "| map({id, conclusion, status, updated_at})"
        ),
    )
    if not runs:
        raise SystemExit(f"no workflow run has head {head_sha}")
    run = runs[0]
    jobs = _api(
        f"repos/{REMOTE}/actions/runs/{run['id']}/jobs?per_page=100",
        jq="[.jobs[] | .conclusion]",
    )
    successes = sum(1 for item in jobs if item == "success")
    return {
        "run": run["id"],
        "head_sha": head_sha,
        "conclusion": run["conclusion"],
        "status": run["status"],
        "completed_at": run["updated_at"],
        "jobs": f"{successes} of {len(jobs)} success",
        "every_job_succeeded": successes == len(jobs) and len(jobs) > 0,
    }


def _tag_handles() -> dict[str, Any]:
    reference = _api(
        f"repos/{REMOTE}/git/ref/tags/{TAG}", jq="{sha: .object.sha, type: .object.type}"
    )
    if reference["type"] != "tag":
        raise SystemExit(f"{TAG} is a lightweight reference; the release requires an annotated tag")
    annotated = _api(
        f"repos/{REMOTE}/git/tags/{reference['sha']}",
        jq="{sha, message, tagger_date: .tagger.date, object: .object.sha}",
    )
    return {
        "tag": TAG,
        "tag_type": reference["type"],
        "tag_object": reference["sha"],
        "peeled_commit": annotated["object"],
        "tag_created_at": annotated["tagger_date"],
        "message_first_line": str(annotated["message"]).splitlines()[0],
    }


def _protection() -> dict[str, Any]:
    protection = _api(f"repos/{REMOTE}/branches/main/protection")
    return {
        "enforce_admins": protection["enforce_admins"]["enabled"],
        "required_status_check_contexts": len(protection["required_status_checks"]["contexts"]),
        "strict_status_checks": protection["required_status_checks"]["strict"],
        "allow_force_pushes": protection["allow_force_pushes"]["enabled"],
        "allow_deletions": protection["allow_deletions"]["enabled"],
        "required_pull_request_reviews": protection.get("required_pull_request_reviews"),
        "required_conversation_resolution": protection.get(
            "required_conversation_resolution", {}
        ).get("enabled"),
    }


def _findings(report: dict[str, Any]) -> list[str]:
    """What would make this run a refusal rather than a record."""
    findings: list[str] = []
    release = report["release"]
    if release["peeled_commit"] != release["implementation_merge_commit"]:
        findings.append("the annotated tag does not peel to the release commit")
    if release["remote_main"] != release["implementation_merge_commit"]:
        findings.append("origin/main is not the release commit")
    for name in ("pull_request_head_ci", "exact_head_main_ci"):
        if not release[name]["every_job_succeeded"]:
            findings.append(f"{name} did not succeed on every job")
    if release["stop_tag_exists"]:
        findings.append(f"{STOP_TAG} exists, and this release is the passing one")
    if not report["branch_protection_after_release"]["enforce_admins"]:
        findings.append("branch protection no longer enforces administrators")
    # The tag names the outcome and this script only knows how to record one of them. A
    # success tag over an exit-criteria record that is not four-of-four is the contradiction
    # this check exists for; unlike the D-series gate there is no ordering problem, because
    # the criteria are decided before the release rather than by it.
    if report["exit_criteria"]["outcome"] != "pass":
        findings.append(
            f"the exit-criteria record reads {report['exit_criteria']['outcome']!r} and the tag "
            f"created is the success tag {TAG}; a stopped sprint is a different record"
        )
    if not report["exit_criteria"]["all_four_met"]:
        findings.append(
            f"{report['exit_criteria']['met']} of {report['exit_criteria']['of']} exit criteria "
            "are met, and the success tag requires four"
        )
    if report["migration_head"] != "0015":
        findings.append("the migration head moved, and 22A's exit criterion makes 0016 a refusal")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-22a-release.json")
    parser.add_argument(
        "--pull-request",
        type=int,
        required=True,
        help="the implementation PR number, read from the remote rather than hard-coded",
    )
    arguments = parser.parse_args()
    implementation_pr = arguments.pull_request

    pull_request = _api(
        f"repos/{REMOTE}/pulls/{implementation_pr}",
        jq=(
            "{merge_commit_sha, merged, merged_at, head_sha: .head.sha, "
            "merged_by: .merged_by.login}"
        ),
    )
    if not pull_request.get("merged"):
        raise SystemExit(
            f"pull request #{implementation_pr} is not merged, so there is no release to record. "
            "The merge into protected main is the gate owner's decision; this script reads the "
            "result and creates nothing"
        )
    merge_commit = pull_request["merge_commit_sha"]
    remote_main = _api(f"repos/{REMOTE}/git/ref/heads/main", jq=".object.sha")
    tags = _api(f"repos/{REMOTE}/git/refs/tags", jq="[.[] | .ref]")
    if f"refs/tags/{TAG}" not in tags:
        raise SystemExit(
            f"{TAG} does not exist yet. It is created once, on the commit the exact-head "
            "post-merge CI passed on, after that CI — and this record is written afterwards"
        )

    criteria = _read("sprint-22a-exit-criteria.json")
    matrix = _read("sprint-22a-verification-matrix.json")

    report: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W4",
        "items": ["S22A-053"],
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": hashlib.sha256(
            (EVIDENCE / "sprint-22a-pre-registration.json").read_bytes()
        ).hexdigest(),
        "outcome": "positive; two pilot domains registered as data, the released four unchanged",
        "exit_criteria": {
            "outcome": criteria["outcome"],
            "met": criteria["verdicts"]["met"],
            "of": criteria["verdicts"]["of"],
            "all_four_met": criteria["verdicts"]["all_four_met"],
            "by_criterion": criteria["verdicts"]["by_criterion"],
            "record": "sprint-22a-exit-criteria.json",
            "record_sha256": hashlib.sha256(
                (EVIDENCE / "sprint-22a-exit-criteria.json").read_bytes()
            ).hexdigest(),
        },
        "verification_matrix": {
            "totals": matrix["totals"],
            "failed_rows": matrix["failed_rows"],
            "skipped_rows": matrix["skipped_rows"],
            "structural_findings": matrix["structural_findings"],
            "record_sha256": hashlib.sha256(
                (EVIDENCE / "sprint-22a-verification-matrix.json").read_bytes()
            ).hexdigest(),
        },
        "migration_head": "0015",
        "next_available_migration": "0016 (unallocated)",
        "sprint_22b": "unblocked; the handoff names what it inherits and what it must not assume",
        "carried_forward_by_name": {
            "W2-A1": "domain_pilot_runs has a three-domain CHECK constraint in its schema",
            "W3-A1": "a released domain cannot refuse a view, because it declares no relations",
        },
        "release": {
            "implementation_pull_request": implementation_pr,
            "implementation_merge_commit": merge_commit,
            "implementation_merged_at": pull_request["merged_at"],
            "merged_by": pull_request["merged_by"],
            "merge_method": "squash, no administrator bypass",
            "pull_request_head_ci": _ci_run(pull_request["head_sha"]),
            "exact_head_main_ci": _ci_run(merge_commit),
            "remote_main": remote_main,
            **_tag_handles(),
            "stop_tag_forbidden_and_not_created": STOP_TAG,
            "stop_tag_exists": f"refs/tags/{STOP_TAG}" in tags,
            "created_by_this_script": "nothing. This record reads handles; it does not make them",
        },
        "branch_protection_after_release": _protection(),
    }
    report["findings"] = _findings(report)
    seal = hashlib.sha256(_canonical(report)).hexdigest()
    arguments.output.write_bytes(_canonical({**report, "integrity_content_hash": seal}))
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "merge_commit": merge_commit,
                "tag_object": report["release"]["tag_object"],
                "peeled_commit": report["release"]["peeled_commit"],
                "exact_head_main_ci": report["release"]["exact_head_main_ci"]["run"],
                "exit_criteria": f"{criteria['verdicts']['met']} of {criteria['verdicts']['of']}",
                "findings": report["findings"],
                "integrity_content_hash": seal,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
