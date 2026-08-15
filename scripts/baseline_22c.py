"""S22C-000 and S22C-001. The 22C starting point, and the two numbers W1 must beat.

Sprint 22C acquires. Its baseline therefore freezes three kinds of thing:

*The authority* — that 22B really released, that `main` is still protected, that the
migration head is `0015`, that neither 22C outcome tag exists yet, and that no predecessor
store is drifting. Each fact is read from the authority that owns it: the release handles
from the remote, the CI conclusion from the API, the fingerprints through the released
`reality_integrity.fingerprint` rather than a second implementation (D4 W7-A1).

*The two inherited repairs, bound by hash rather than retyped* — 22B W3-F1's crash
reproduction and 22B W4-F1's restored-recall measurement. W1 is required to beat both, and
"beat" is only meaningful against the bytes of the record that measured them. A baseline
that restated `0.9410` as a constant would let the comparison drift the moment either
record moved.

*The campaign budget lines* — 22B's sealed throughput numbers. A campaign whose stores are
four orders of magnitude smaller than 22B's does not threaten any of them, but the numbers
are read from 22B's records here so a later wave prices against measurements instead of
rediscovering them.

    UV_CACHE_DIR=.cache/uv uv run python scripts/baseline_22c.py

Read-only. It mutates no remote and writes to no store: 22C's own pair is provisioned after
this record is taken, so the pair's `before` state is genuinely before.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")
SLUG = "palkouser/cognitive-os"

PREDECESSOR_TAG = "sprint-22b-scale-baseline"
SUCCESS_TAG = "sprint-22c-acquisition-baseline"
NEGATIVE_TAG = "sprint-22c-evidence-baseline"
BRANCH = "sprint-22c-groundwork"

#: The fourteen pairs 22C may not write to: the twelve 22B froze, plus 22B's own two roots.
PREDECESSOR_STORES = {
    "development": "artifacts",
    "sprint_21c3": "artifacts-s21c3",
    "sprint_21d1": "artifacts-s21d1",
    "sprint_21d2": "artifacts-s21d2",
    "sprint_21d3": "artifacts-s21d3",
    "sprint_21d4": "artifacts-s21d4",
    "sprint_21d5": "artifacts-s21d5",
    "sprint_21d6": "artifacts-s21d6",
    "sprint_21d6_measured": "artifacts-s21d6-measured",
    "sprint_21d7": "artifacts-s21d7",
    "sprint_21d7_measured": "artifacts-s21d7-measured",
    "sprint_22a": "artifacts-s22a",
    "sprint_22b": "artifacts-s22b",
    "sprint_22b_backups": "backups-s22b",
}

#: The exact-head run 22B's release was closed on. Re-read from the API, never restated.
PREDECESSOR_CI_RUNS = (("22b post-merge main, exact head", 31804585618),)

#: 22B's baseline sealed expectations for the twelve roots it must not write to; its own two
#: roots were not yet among them, exactly as 22A's own root was not among 22A's. The honest
#: handling is the one 22B used on 22A: name it, freeze the current state as a first
#: observation, never edit the predecessor's sealed record.
STALE_EXPECTATIONS = {
    "sprint_22b": (
        "sprint-22b-baseline.json carries no expectation for this root — 22B's baseline listed "
        "the twelve roots it must not write to, and its own was not yet one of them. 22C "
        "freezes the post-release state as a first observation"
    ),
    "sprint_22b_backups": (
        "the backup root 22B created for its restore round trip, never fingerprinted by a "
        "released record. First observation at the 22C baseline"
    ),
}

#: The records 22C reads rather than restates. The first two are what W1 must beat; the rest
#: are the sealed budget lines every campaign estimate is priced against.
PRIOR_ART = {
    "w3_f1_crash_reproduction": EVIDENCE / "sprint-22b-w3-crash.json",
    "w4_f1_restored_recall_clustered": EVIDENCE / "sprint-22b-w4-restored-recall-clustered.json",
    "w4_f1_source_recall_clustered": EVIDENCE / "sprint-22b-w4-source-recall-clustered.json",
    "governed_ingest": EVIDENCE / "sprint-22b-w1-governed-ingest.json",
    "incremental_insert": EVIDENCE / "sprint-22b-w1-incremental.json",
}

COMMANDS: list[str] = []


def _run(*args: str) -> str:
    COMMANDS.append(" ".join(args))
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def _gh_json(path: str) -> Any:
    return json.loads(_run("gh", "api", path))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _remote_ref(pattern: str) -> dict[str, str]:
    out = _run("git", "ls-remote", "origin", pattern)
    return {ref: sha for sha, ref in (line.split("\t") for line in out.splitlines() if line)}


def _fingerprint(directory: Path) -> tuple[str | None, int]:
    """Through the released authority, never a second implementation. D4 W7-A1."""
    from cognitive_os.coding.reality_integrity import fingerprint

    if not directory.exists():
        return None, 0
    digest, files = fingerprint(directory)
    return digest, files


def _released_expectations() -> dict[str, dict[str, Any]]:
    """Every root 22B sealed a fingerprint for, read out of 22B's own baseline record."""
    baseline = _load(EVIDENCE / "sprint-22b-baseline.json")
    return {
        item["path"].rsplit("/", 1)[-1]: item
        for item in baseline["predecessor_artifact_stores"].values()
    }


def _stores() -> dict[str, Any]:
    released = _released_expectations()

    out: dict[str, Any] = {}
    for key, directory in PREDECESSOR_STORES.items():
        digest, files = _fingerprint(DATA_ROOT / directory)
        expected = released.get(directory)
        out[key] = {
            "path": str(DATA_ROOT / directory),
            "files": files,
            "path_and_size_fingerprint_sha256": digest,
            "expected_from": (
                "sprint-22b-baseline.json"
                if expected
                else "first observation at the 22C baseline; no released expectation exists"
            ),
            "matches_expected": (
                None
                if expected is None
                else bool(
                    digest == expected["path_and_size_fingerprint_sha256"]
                    and files == expected["files"]
                )
            ),
            "expectation_is_stale": STALE_EXPECTATIONS.get(key),
            "expected_files": None if expected is None else expected["files"],
        }
    return out


def _predecessor_release() -> dict[str, Any]:
    """22B's release. Absent, or not annotated, means 22C does not start."""
    refs = _remote_ref(f"refs/tags/{PREDECESSOR_TAG}*")
    tag_object = refs.get(f"refs/tags/{PREDECESSOR_TAG}")
    peeled = refs.get(f"refs/tags/{PREDECESSOR_TAG}^{{}}")
    if tag_object is None or peeled is None:
        raise SystemExit(
            f"{PREDECESSOR_TAG} does not resolve remotely as an annotated tag. Sprint 22C W0 is "
            "blocked on the 22B release; see Section 1.1 of the backlog."
        )
    origin_main = _remote_ref("refs/heads/main")["refs/heads/main"]
    return {
        "tag": PREDECESSOR_TAG,
        "remote": f"https://github.com/{SLUG}",
        "remote_tag_object": tag_object,
        "remote_peeled_commit": peeled,
        "local_tag_object": _run("git", "rev-parse", PREDECESSOR_TAG),
        "local_peeled_commit": _run("git", "rev-parse", f"{PREDECESSOR_TAG}^{{}}"),
        "tag_type": _run("git", "cat-file", "-t", tag_object),
        "local_and_remote_agree": (
            tag_object == _run("git", "rev-parse", PREDECESSOR_TAG)
            and peeled == _run("git", "rev-parse", f"{PREDECESSOR_TAG}^{{}}")
        ),
        # 22B's own lesson, checked rather than assumed: the tag must point at the squashed
        # `main` commit, not at a stranded branch head.
        "peels_to_current_origin_main": peeled == origin_main,
        "pull_requests": [233],
    }


def _ci_runs() -> list[dict[str, Any]]:
    runs = []
    for label, run_id in PREDECESSOR_CI_RUNS:
        run = _gh_json(f"repos/{SLUG}/actions/runs/{run_id}")
        jobs = _gh_json(f"repos/{SLUG}/actions/runs/{run_id}/jobs?per_page=100")["jobs"]
        runs.append(
            {
                "label": label,
                "run_id": run_id,
                "head_sha": run["head_sha"],
                "event": run["event"],
                "branch": run["head_branch"],
                "conclusion": run["conclusion"],
                "jobs": len(jobs),
                "jobs_successful": sum(1 for job in jobs if job["conclusion"] == "success"),
            }
        )
    return runs


def _protection() -> dict[str, Any]:
    raw = _run("gh", "api", f"repos/{SLUG}/branches/main/protection")
    document = json.loads(raw)
    contexts = document["required_status_checks"]["contexts"]
    return {
        "allow_deletions": document["allow_deletions"]["enabled"],
        "allow_force_pushes": document["allow_force_pushes"]["enabled"],
        "enforce_admins": document["enforce_admins"]["enabled"],
        "queried_json_sha256": _sha256(raw.encode("utf-8")),
        "required_context_count": len(contexts),
        "required_contexts": sorted(contexts),
        "required_conversation_resolution": document["required_conversation_resolution"]["enabled"],
        "required_pull_request_reviews": document.get("required_pull_request_reviews"),
        "strict": document["required_status_checks"]["strict"],
    }


def _migration_state() -> dict[str, Any]:
    """The head, counted from the files rather than restated from the plan."""
    versions = sorted(
        path.name for path in (REPO / "infra/postgres/alembic/versions").glob("[0-9]*.py")
    )
    return {
        "repository_head": versions[-1].split("_", 1)[0],
        "migration_files": len(versions),
        "planned_22c_migration": None,
        "next_available": "0016 (unallocated)",
        "0016_is_a_refusal": (
            "the campaign pipeline is composition over released storage — memory provenance "
            "bundles, semantic claims, corpus lineage, content-addressed artifacts. A wave that "
            "finds itself needing a migration has found a finding, not a plan item"
        ),
        "the_one_candidate_exception": (
            "§1.4: widening the `domain_pilot_runs` CHECK constraint so a pilot-domain "
            "evaluation run has a persisted path (22A W2-A1). A gate-owner decision taken in W0 "
            "or not at all; the plan's frozen default takes it in neither direction by running "
            "the holdout through `domains.solve`/`domains.checker` and sealing outcomes as 22C "
            "evidence records"
        ),
    }


def _predecessor_exit_state() -> dict[str, Any]:
    """22B's outcome, read out of 22B's own records rather than restated."""
    exit_criteria = _load(EVIDENCE / "sprint-22b-exit-criteria.json")
    return {
        "source": "sprint-22b-exit-criteria.json",
        "source_sha256": _sha256((EVIDENCE / "sprint-22b-exit-criteria.json").read_bytes()),
        "outcome": exit_criteria["outcome"],
        "all_met": exit_criteria["all_met"],
        "criteria_met": exit_criteria["criteria_met"],
        "criteria_total": exit_criteria["criteria_total"],
        "post_restore_all_still_met": exit_criteria.get("post_restore_all_still_met"),
        "thresholds_moved_by_22b": exit_criteria.get("thresholds_moved_by_22b"),
        "carried_forward_by_name": ["22A W2-A1", "22A W3-A1", "22B W2-F2"],
        "why_carried_not_resolved": (
            "W2-A1 needs a migration and §1.4 freezes a default that does not take one; W3-A1 "
            "(a released domain cannot refuse a view) is untouched by any campaign work; 22B "
            "W2-F2 is a filtered-ANN planner choice at 10^6, four orders of magnitude above "
            "campaign scale"
        ),
        "handed_to_22c_for_repair": ["22B W3-F1", "22B W4-F1"],
    }


def _repairs() -> dict[str, Any]:
    """The two numbers W1 must beat, bound to the bytes that measured them.

    Neither threshold is 22C's to choose. W3-F1's is structural — zero items outside their
    own event stream after the same crash — and W4-F1's is the released 0.95 recall floor
    that 22B's restored graph missed. The measured values are read out of the bound records
    so this baseline cannot disagree with them.
    """
    crash = _load(PRIOR_ART["w3_f1_crash_reproduction"])
    restored = _load(PRIOR_ART["w4_f1_restored_recall_clustered"])
    source = _load(PRIOR_ART["w4_f1_source_recall_clustered"])
    return {
        "w3_f1_missing_creation_event": {
            "path": str(PRIOR_ART["w3_f1_crash_reproduction"].relative_to(REPO)),
            "sha256": _sha256(PRIOR_ART["w3_f1_crash_reproduction"].read_bytes()),
            "defect": (
                "MemoryService.create commits the record and appends memory.item_created in two "
                "transactions; a crash between them leaves a governed item permanently outside "
                "its own event stream, because the idempotency key turns the resume into a "
                "lookup that never reaches the event append"
            ),
            "items_missing_an_event": crash["items_missing_an_event"],
            "items_written_before_the_kill": crash["items_written_before_the_kill"],
            "what_was_killed": crash["what_was_killed"],
            "resume_duplicated_nothing": crash["resume_duplicated_nothing"],
            "target": "items_missing_an_event == 0 after the same crash, re-run by W1",
            "why_22c_owns_it": (
                "22C's exits depend on the event stream being the truth: replay, quarantine and "
                "supersession are all read out of it. 22B was forbidden to change released "
                "behaviour mid-measurement; 22C repairs it before the first campaign number "
                "exists"
            ),
        },
        "w4_f1_restored_index_recall": {
            "restored_path": str(PRIOR_ART["w4_f1_restored_recall_clustered"].relative_to(REPO)),
            "restored_sha256": _sha256(PRIOR_ART["w4_f1_restored_recall_clustered"].read_bytes()),
            "source_path": str(PRIOR_ART["w4_f1_source_recall_clustered"].relative_to(REPO)),
            "source_sha256": _sha256(PRIOR_ART["w4_f1_source_recall_clustered"].read_bytes()),
            "defect": (
                "pg_restore rebuilds HNSW indexes rather than copying them, and the rebuilt "
                "graph drops clustered recall below the floor with no released signal that "
                "anything degraded"
            ),
            "restored_recall_at_10": restored["recall_at_k"],
            "source_recall_at_10": source["recall_at_k"],
            "threshold": restored["threshold"],
            "meets_exit_before_repair": restored["meets_exit"],
            "probes": restored["probes"],
            "ground_truth": restored["ground_truth"],
            "target": (
                f"restored clustered recall@10 back over {restored['threshold']}, measured the "
                "way 22B measured it — restore the clustered corpus, apply the pre-registered "
                "procedure, exact-scan ground truth per probe"
            ),
            "why_22c_owns_it": (
                "22B deliberately left it untuned so the number 22C improves is a measured one, "
                "not a number chosen after seeing it"
            ),
        },
    }


def _budget_lines() -> dict[str, Any]:
    """22B's sealed throughput, read rather than retyped. §1.1."""
    ingest = _load(PRIOR_ART["governed_ingest"])
    incremental = _load(PRIOR_ART["incremental_insert"])
    return {
        "governed_ingest_items_per_second": {
            "path": str(PRIOR_ART["governed_ingest"].relative_to(REPO)),
            "sha256": _sha256(PRIOR_ART["governed_ingest"].read_bytes()),
            "items_per_second": ingest["items_per_second"],
        },
        "incremental_insert_rows_per_second": {
            "path": str(PRIOR_ART["incremental_insert"].relative_to(REPO)),
            "sha256": _sha256(PRIOR_ART["incremental_insert"].read_bytes()),
            "rows_per_second": incremental.get("rows_per_second"),
        },
        "why_no_campaign_budget_is_threatened": (
            "one chapter across three cycles is thousands of items, not millions. These are "
            "sealed budget lines a campaign reads rather than rediscovers, and the wave that "
            "grows past fixture scale prices against them"
        ),
    }


def _record() -> dict[str, Any]:
    release = _predecessor_release()
    origin_main = _remote_ref("refs/heads/main")["refs/heads/main"]
    merge_base = _run("git", "merge-base", "HEAD", "origin/main")
    stores = _stores()

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W0",
        "phase": "before",
        "items": ["S22C-000", "S22C-001"],
        "read_policy": "fresh local and remote reads; no remote mutation",
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": {
            "name": BRANCH,
            "local_head": _run("git", "rev-parse", "HEAD"),
            "origin_main": origin_main,
            "merge_base_with_origin_main": merge_base,
            "descends_from_current_origin_main": merge_base == origin_main,
            "commits_ahead_at_baseline": int(
                _run("git", "rev-list", "--count", "origin/main..HEAD")
            ),
            "note": (
                "the backlog commit rides ahead of main on this branch, so the plan the wave "
                "executes travels with the wave that executes it"
            ),
        },
        "predecessor_release": release,
        "outcome_tags_absent": {
            SUCCESS_TAG: not _remote_ref(f"refs/tags/{SUCCESS_TAG}"),
            NEGATIVE_TAG: not _remote_ref(f"refs/tags/{NEGATIVE_TAG}"),
        },
        "ci_runs": _ci_runs(),
        "main_protection": _protection(),
        "migration": _migration_state(),
        "predecessor_artifact_stores": stores,
        "predecessor_stores_match_expectation": all(
            item["matches_expected"] is not False
            for key, item in stores.items()
            if key not in STALE_EXPECTATIONS
        ),
        "stale_expectations": STALE_EXPECTATIONS,
        "unexplained_drift": sorted(
            key
            for key, item in stores.items()
            if item["matches_expected"] is False and key not in STALE_EXPECTATIONS
        ),
        "first_observations": sorted(
            key
            for key, item in stores.items()
            if item["matches_expected"] is None or key in STALE_EXPECTATIONS
        ),
        "stores_written_to_before_this_record": [],
        "why_this_record_precedes_provisioning": (
            "22C's own pair is provisioned by this same wave, after this record exists. A "
            "baseline taken after the store it describes was created would be describing the "
            "sprint's own work"
        ),
        "predecessor_exit_state": _predecessor_exit_state(),
        "inherited_repairs": _repairs(),
        "campaign_budget_lines": _budget_lines(),
    }
    record["commands"] = sorted(set(COMMANDS))
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-22c-baseline.json")
    arguments = parser.parse_args()

    record = _record()
    release = record["predecessor_release"]
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "predecessor_tag_agrees_locally_and_remotely": release["local_and_remote_agree"],
                "predecessor_peeled_commit": release["remote_peeled_commit"],
                "peels_to_current_origin_main": release["peels_to_current_origin_main"],
                "ci": [
                    f"{item['run_id']}: {item['jobs_successful']}/{item['jobs']}"
                    f" {item['conclusion']}"
                    for item in record["ci_runs"]
                ],
                "predecessor_stores": len(record["predecessor_artifact_stores"]),
                "predecessor_stores_match_expectation": record[
                    "predecessor_stores_match_expectation"
                ],
                "unexplained_drift": record["unexplained_drift"],
                "first_observations": record["first_observations"],
                "migration_head": record["migration"]["repository_head"],
                "repairs_bound": sorted(record["inherited_repairs"]),
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
