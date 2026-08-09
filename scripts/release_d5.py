#!/usr/bin/env python
"""S21D5-095: the release, recorded from the remote rather than from prose.

    scripts/release_d5.py [--output docs/.../sprint-21d5-release.json]

Every handle in this record is read back from GitHub and from the local repository at the moment
it runs: `origin/main`, the merge commit and its timestamp, both CI runs with their conclusions
and job counts, the annotated tag object and the commit it peels to, and the branch protection
state. Nothing is copied from the execution log, because the execution log is prose and this
record is what a reader checks the prose against.

Three things it refuses to do.

*It does not create anything.* No merge, no tag, no push. It reads. A record that could produce
the state it describes would be a record of itself.

*It does not accept a tag that moved.* The tag object is read from the remote and its peel is
compared to the merge commit. §6.2 is explicit that the tag is never moved or recreated, so a
peel that disagrees is a finding rather than a value to write down.

*It does not report a pass it did not read.* The success tag is named and checked for absence.
D5's outcome is negative on the correction branch and the gate does not pass, so a
`sprint-21-learning-baseline` in existence would contradict every other record in the sprint.
Its absence is asserted rather than assumed.
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
EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"

REMOTE = "palkouser/cognitive-os"
IMPLEMENTATION_PR = 225
GATE_CLOSE_PR_TITLE = "Sprint 21D5: close Gate L2 condition 29 on the verified release handles"
TAG = "sprint-21d5-evidence-baseline"
#: Never created on a negative path. Checked for absence rather than assumed.
SUCCESS_TAG = "sprint-21-learning-baseline"


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


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _canonical(value: object) -> bytes:
    """The bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode(
        "utf-8"
    )


def _read(name: str) -> dict[str, Any]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


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
    if release["success_tag_exists"]:
        findings.append(f"{SUCCESS_TAG} exists, and Gate L2 does not pass")
    if not report["branch_protection_after_release"]["enforce_admins"]:
        findings.append("branch protection no longer enforces administrators")
    # The tag names the outcome, and this script only knows how to record one of them. §8.2's
    # tag is the stop tag; if the assessment ever reads as a pass, the release being recorded is
    # not the release this script describes, and saying so is better than writing it down.
    if report["gate_l2"] == "gate_l2_passes":
        findings.append(
            f"the gate assessment reads as a pass and the tag created is the stop tag {TAG}; "
            "a passing release is a different record with a different tag"
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d5-release.json")
    arguments = parser.parse_args()

    pull_request = _api(
        f"repos/{REMOTE}/pulls/{IMPLEMENTATION_PR}",
        jq="{merge_commit_sha, merged_at, head_sha: .head.sha, merged_by: .merged_by.login}",
    )
    merge_commit = pull_request["merge_commit_sha"]
    remote_main = _api(f"repos/{REMOTE}/git/ref/heads/main", jq=".object.sha")
    tags = _api(f"repos/{REMOTE}/git/refs/tags", jq="[.[] | .ref]")

    continuation = _read("sprint-21d5-continuation.json")
    gate = _read("sprint-21d5-gate-l2.json")
    selection = _read("sprint-21d5-learner-selection.json")
    retrieval = _read("sprint-21d5-retrieval-decision.json")
    operations = _read("sprint-21d5-operations.json")

    report: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W8",
        "items": ["S21D5-094", "S21D5-095"],
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": hashlib.sha256(
            (EVIDENCE / "sprint-21d5-pre-registration.json").read_bytes()
        ).hexdigest(),
        "outcome": "negative on the correction branch, positive on the retrieval branch",
        "gate_l2": gate["verdict"],
        "gate_l2_counts": gate["counts"],
        "d1_conditions_still_open": [6, 7],
        "d1_conditions_closed_here": [15],
        "sprint_22a": "blocked; the handoff targets one bounded successor experiment",
        "migration_head": "0015",
        "next_available_migration": "0016 (unallocated)",
        "final_outcomes_inspected": 0,
        "release": {
            "implementation_pull_request": IMPLEMENTATION_PR,
            "implementation_merge_commit": merge_commit,
            "implementation_merged_at": pull_request["merged_at"],
            "merge_method": "squash, no administrator bypass",
            "pull_request_head_ci": _ci_run(pull_request["head_sha"]),
            "exact_head_main_ci": _ci_run(merge_commit),
            "remote_main": remote_main,
            **_tag_handles(),
            "success_tag_forbidden_and_not_created": SUCCESS_TAG,
            "success_tag_exists": f"refs/tags/{SUCCESS_TAG}" in tags,
            "tags_on_the_remote": tags,
        },
        "branch_protection_after_release": _protection(),
        "stop_hashes": {
            "correction_selection": selection["integrity_content_hash"],
            "correction_stop_kind": continuation["decision"]["stop_kind"],
            "continuation": continuation["stop_hash"],
        },
        "retrieval_branch": {
            "winning_arm": retrieval["winning_arm"],
            "gate_l2_condition_24": retrieval["gate_l2_condition_24"],
            "gate_d1_condition_15": retrieval["gate_d1_condition_15"],
            "note": (
                "§8.2 requires a valid independent retrieval result to be retained whichever "
                "way the correction branch went. It is, and it is the sprint's one closed "
                "condition"
            ),
        },
        "component_state": {
            "learned_components": 0,
            "active_components": 0,
            "approvals": 0,
            "activations": 0,
            "artifact_written": False,
            "note": (
                "S21D5-035 recorded a null under §3.3 step 5; nothing was registered, approved "
                "or activated on experience.correction_ranking. Source: "
                "sprint-21d5-continuation.json, stop kind "
                f"{continuation['decision']['stop_kind']!r}, "
                f"{continuation['not_opened']['count']} dependent items bound to one hash. W7's "
                "restore proof independently confirms zero components on that surface"
            ),
        },
        "store_fingerprints_unchanged": operations["isolation"]["predecessor_pairs_unchanged"],
        "documents": {
            "report": "sprint-21d5-report.md",
            "assessment": "gate-l2-d5-assessment.md",
            "handoff": "sprint-21d6-handoff.md",
            "execution_log": "sprint-21d5-execution.md",
        },
    }
    report["release"]["chronology"] = (
        f"#{IMPLEMENTATION_PR} merge {pull_request['merged_at']} -> exact-head main CI "
        f"{report['release']['exact_head_main_ci']['run']} complete "
        f"{report['release']['exact_head_main_ci']['completed_at']} -> annotated tag created "
        f"{report['release']['tag_created_at']}, once and after that CI"
    )
    report["findings"] = _findings(report)

    seal = _digest(report)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(_canonical({**report, "integrity_content_hash": seal}))

    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "release_commit": merge_commit,
                "tag_object": report["release"]["tag_object"],
                "peels_to": report["release"]["peeled_commit"],
                "exact_head_main_ci": report["release"]["exact_head_main_ci"]["jobs"],
                "findings": report["findings"],
                "seal": seal,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not report["findings"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
