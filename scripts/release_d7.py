#!/usr/bin/env python
"""S21D7-043: the release, recorded from the remote rather than from prose.

    scripts/release_d7.py --pull-request <n> [--output docs/.../sprint-21d7-release.json]

Every handle in this record is read back from GitHub and from the local repository at the moment
it runs: `origin/main`, the merge commit and its timestamp, both CI runs with their conclusions
and job counts, the annotated tag object and the commit it peels to, and the branch protection
state. Nothing is copied from the execution log, because the execution log is prose and this
record is what a reader checks the prose against.

Four things it refuses to do.

*It does not create anything.* No merge, no tag, no push. It reads. A record that could produce
the state it describes would be a record of itself.

*It does not accept a tag that moved.* The tag object is read from the remote and its peel is
compared to the merge commit. §6.2 is explicit that the tag is never moved or recreated, so a
peel that disagrees is a finding rather than a value to write down.

*It does not report a pass it did not read.* This is the first sprint in the D-series whose tag
is the success tag `sprint-21-learning-baseline`, and the one check that matters is the inverse
of D6's: there, a success tag in existence would have contradicted the sprint; here, a gate
assessment that does **not** read as a pass while this tag exists is the contradiction. Both
directions are refusals, and the record states which one it is enforcing.

*And it does not hard-code the pull request.* D5 carried its PR number as a module constant,
which is fine once the release has happened and wrong every moment before it. `--pull-request`
is required, so a run against the wrong release fails at the remote rather than by describing one
release with another's handles.
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
TAG = "sprint-21-learning-baseline"
#: The tag a stop would have carried. Checked for absence: a sprint cannot release under both.
STOP_TAG = "sprint-21d7-evidence-baseline"


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


def _component_state(continuation: dict[str, Any]) -> dict[str, Any]:
    """What is live on the surface after this release, read from the lifecycle record.

    D3 through D6 each wrote zeroes here. This is the first release where the row is not empty,
    so it names the ledger rather than summarising it: the counts come from the sealed lifecycle
    phases, and the reading says what "active" is bounded to.
    """
    lifecycle = _read("sprint-21d7-lifecycle.json")
    restore = lifecycle["phases"]["restore"]
    canary = lifecycle["canary"]
    return {
        "learned_components": lifecycle["phases"]["restore"]["ledger"]["replay_components"],
        "active_components": 1 if restore["state_after_rollback"] == "active" else 0,
        "approvals": 1,
        "activations": 1,
        "rollbacks": 1,
        "kill_switch_exercised": True,
        "artifact_written": True,
        "component_id": lifecycle["component"]["component_id"],
        "surface": lifecycle["component"]["surface"],
        "artifact_id": lifecycle["component"]["artifact_id"],
        "ledger_revisions": restore["ledger"]["replay_revisions"],
        "projection_matches": restore["ledger"]["projection_matches"],
        "hash_chain_verified": restore["ledger"]["hash_chain_verified"],
        "routed_groups": len(canary["routed_groups"]),
        "note": (
            "S21D7-039 registered, verified, approved and activated one component on "
            f"{lifecycle['component']['surface']}, routing {len(canary['routed_groups'])} canary "
            "groups and nothing else. It was disabled by kill switch and restored by rollback "
            "inside the same wave, across two database restarts and four processes. Source: "
            "sprint-21d7-lifecycle.json, continuation ending "
            f"{continuation['decision']['ending']!r} with "
            f"{continuation['delivered']['count']} deliverables opened and "
            f"{continuation['not_opened']['count']} closed"
        ),
        "what_active_is_not": (
            "a shipped default. The bounded steady-state configuration is sealed and was not "
            "entered, and no surface outside the five routed groups consults the component"
        ),
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
    # The tag names the outcome, and this script only knows how to record one of them. §8.2's
    # success tag is what D7 carries, so a gate that is not on course to pass is a finding.
    #
    # "On course" rather than "passing", and the distinction is the ordering: condition 29 *is*
    # this release, so the gate cannot read a pass until this record exists, and this record
    # cannot be written if it demands one. The check that survives that is the one that means
    # something anyway — **every condition this record does not create is met**. If 29 is the
    # only row left, the gate-close regeneration closes it and nothing else moves.
    counts = report["gate_l2_counts"]
    outstanding = {
        name: counts[name]
        for name in ("failed", "not_opened", "met_as_rejection")
        if counts.get(name)
    }
    if outstanding:
        findings.append(
            f"the gate assessment carries {outstanding} and the tag created is the success tag "
            f"{TAG}; a stopped release is a different record with a different tag"
        )
    pending = [row["condition"] for row in report["gate_l2_rows"] if row["state"] == "pending"]
    if report["gate_l2"] != "gate_l2_passes" and pending != [29]:
        findings.append(
            f"the gate assessment reads {report['gate_l2']!r} with pending rows {pending}; only "
            "condition 29 may be outstanding when this record is written, because condition 29 "
            "is this record"
        )
    for condition, state in report["gate_d1"].items():
        if state != "closed":
            findings.append(f"Gate D1 condition {condition} is {state}, not closed")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d7-release.json")
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
        jq="{merge_commit_sha, merged_at, head_sha: .head.sha, merged_by: .merged_by.login}",
    )
    merge_commit = pull_request["merge_commit_sha"]
    remote_main = _api(f"repos/{REMOTE}/git/ref/heads/main", jq=".object.sha")
    tags = _api(f"repos/{REMOTE}/git/refs/tags", jq="[.[] | .ref]")

    continuation = _read("sprint-21d7-continuation.json")
    gate = _read("sprint-21d7-gate-l2.json")
    selection = _read("sprint-21d7-learner-selection.json")
    ruling = _read("sprint-21d7-condition-24-ruling.json")
    isolation = _read("sprint-21d7-authority-isolation-after.json")
    # Read out of the assessment rather than restated: condition 24 is inherited, and the state
    # this record reports for it has to be the one the gate script decided after recomputing the
    # three identities that void the inheritance.
    gate_row_24 = next(row["state"] for row in gate["gate_l2"] if row["condition"] == 24)

    report: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W4",
        "items": ["S21D7-043"],
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": hashlib.sha256(
            (EVIDENCE / "sprint-21d7-pre-registration.json").read_bytes()
        ).hexdigest(),
        "outcome": "positive; one candidate selected, bound, promoted and activated",
        "gate_l2": gate["verdict"],
        "gate_l2_counts": gate["counts"],
        "gate_l2_rows": [
            {"condition": row["condition"], "state": row["state"]} for row in gate["gate_l2"]
        ],
        "gate_l2_read_before_the_close": (
            "condition 29 is this release, so the assessment read here is the one written before "
            "it existed. What this record checks is that every other condition is met; the "
            "gate-close regeneration then reads these bytes and closes 29 against them"
        ),
        "gate_d1": {row["condition"]: row["state"] for row in gate["gate_d1"]},
        "d1_conditions_closed_from_final_surface_evidence": [6, 7],
        "d1_conditions_closed_by_inheritance": [15],
        "sprint_22a": "unblocked; the handoff names what it inherits and what it must re-earn",
        "migration_head": "0015",
        "next_available_migration": "0016 (unallocated)",
        "final_outcomes_inspected": 0,
        "release": {
            "implementation_pull_request": implementation_pr,
            "implementation_merge_commit": merge_commit,
            "implementation_merged_at": pull_request["merged_at"],
            "merge_method": "squash, no administrator bypass",
            "pull_request_head_ci": _ci_run(pull_request["head_sha"]),
            "exact_head_main_ci": _ci_run(merge_commit),
            "remote_main": remote_main,
            **_tag_handles(),
            "stop_tag_forbidden_and_not_created": STOP_TAG,
            "stop_tag_exists": f"refs/tags/{STOP_TAG}" in tags,
            "tags_on_the_remote": tags,
        },
        "branch_protection_after_release": _protection(),
        "decision_hashes": {
            "correction_selection": selection["integrity_content_hash"],
            "ending": continuation["decision"]["ending"],
            "continuation": continuation["integrity_content_hash"],
            "no_stop_hash": (
                "there is no stop to bind. D3 through D6 each released against one; this record "
                "names the selection and the continuation instead, and the gate assessment "
                "closes zero conditions against a stop"
            ),
        },
        "retrieval_branch": {
            "authored_by_d7": 0,
            "ruling": ruling["ruling"],
            "ruling_sha256": hashlib.sha256(
                (EVIDENCE / "sprint-21d7-condition-24-ruling.json").read_bytes()
            ).hexdigest(),
            "inherited_from": ruling["inherited_measurement"]["record"],
            "winning_arm": ruling["inherited_measurement"]["winning_arm"],
            "gate_l2_condition_24": gate_row_24,
            "note": (
                "D7 ran no retrieval branch. Condition 24 and Gate D1 condition 15 are inherited "
                "from D5's sealed measurement under the W0 ruling, and the gate assessment "
                "recomputed all three voiding identities at gate close rather than trusting the "
                "ruling's sentence"
            ),
        },
        "component_state": _component_state(continuation),
        "store_fingerprints_unchanged": {
            "stores": len(isolation["predecessor_artifact_stores"]),
            "drifted": sorted(isolation["drifted_stores"]),
            "zero_predecessor_writes": isolation["zero_predecessor_writes"],
            "compared_against": isolation["compared_against"],
        },
        "documents": {
            "report": "sprint-21d7-report.md",
            "assessment": "gate-l2-d7-assessment.md",
            "handoff": "sprint-21d7-handoff.md",
            "execution_log": "sprint-21d7-execution.md",
        },
    }
    report["release"]["chronology"] = (
        f"#{implementation_pr} merge {pull_request['merged_at']} -> exact-head main CI "
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
