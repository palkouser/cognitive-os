"""S22B-000 and S22B-001. The 22B starting point, and the numbers this sprint extends.

Sprint 22B measures. A measurement sprint's baseline therefore has to freeze two different
kinds of thing, and confusing them is how scale sprints go wrong:

*The authority* — that the predecessor really released, that `main` is still protected, that
the migration head is where the plan says, that neither 22B outcome tag exists yet, and that
no predecessor store is drifting. Read from the authority that owns each fact: the release
handles from the remote, the CI conclusion from the API, the fingerprints through the released
`reality_integrity.fingerprint` rather than a second implementation (D4 W7-A1).

*The prior art the exits will be compared against* — the two sealed 10^5 envelopes and the one
graph-arm latency ever measured. These are bound **by hash** here, so §2.2's frozen readings
point at bytes rather than at numbers retyped into a plan. The 500 ms graph exit is 3.6x
tighter than D1's 1788.9 ms; a baseline that restates that number instead of binding its record
would let the comparison drift silently.

    UV_CACHE_DIR=.cache/uv uv run python scripts/baseline_22b.py

Read-only. It mutates no remote and writes to no store: 22B's own pair is provisioned after
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
D_EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
SPRINT_21 = REPO / "docs/sprints/sprint-21"
DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")
SLUG = "palkouser/cognitive-os"

PREDECESSOR_TAG = "sprint-22a-domain-baseline"
SUCCESS_TAG = "sprint-22b-scale-baseline"
NEGATIVE_TAG = "sprint-22b-evidence-baseline"
BRANCH = "sprint-22b-groundwork"

#: The twelve pairs 22B may not write to: the eleven 22A froze, plus 22A's own root.
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
}

#: The exact-head run 22A's release was closed on. Re-read from the API, never restated.
PREDECESSOR_CI_RUNS = (("22a post-merge main, exact head", 31573794611),)

#: The same class of stale expectation 22A named as its own W0-F1, one sprint on.
#: `sprint-22a-baseline.json` was taken in 22A's W0, before 22A's W1-W4 wrote to
#: `artifacts-s22a`, and no post-release fingerprint of that root was ever sealed. The honest
#: handling is to name it and freeze the current state as a first observation, never to edit
#: 22A's sealed record.
STALE_EXPECTATIONS = {
    "sprint_22a": (
        "sprint-22a-baseline.json carries no expectation for this root at all — 22A's baseline "
        "listed the eleven roots it must not write to, and its own root was not yet one of "
        "them. 22B freezes the post-release state as a first observation"
    )
}

#: The prior art §2.2 reads, bound by hash rather than by retyped number.
PRIOR_ART = {
    "envelope_1e5_uniform": SPRINT_21 / "envelope_1e5.json",
    "envelope_1e5_clustered": SPRINT_21 / "envelope_1e5_clustered.json",
    "graph_arm_d1_w5a": D_EVIDENCE / "sprint-21d1-w5a-retrieval.json",
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
    """Every root 22A sealed a fingerprint for, read out of 22A's own baseline record."""
    baseline = _load(EVIDENCE / "sprint-22a-baseline.json")
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
                "sprint-22a-baseline.json"
                if expected
                else "first observation at the 22B baseline; no released expectation exists"
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
    """22A's release. Absent, or not annotated, means 22B does not start."""
    refs = _remote_ref(f"refs/tags/{PREDECESSOR_TAG}*")
    tag_object = refs.get(f"refs/tags/{PREDECESSOR_TAG}")
    peeled = refs.get(f"refs/tags/{PREDECESSOR_TAG}^{{}}")
    if tag_object is None or peeled is None:
        raise SystemExit(
            f"{PREDECESSOR_TAG} does not resolve remotely as an annotated tag. Sprint 22B W0 is "
            "blocked on the 22A release; see Section 1.1 of the backlog."
        )
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
        "pull_requests": [231, 232],
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
        "planned_22b_migration": None,
        "next_available": "0016 (unallocated)",
        "0016_is_a_refusal": (
            "every scoped mutation 22B drives — supersession, tombstone, bloat, reindex — lives "
            "in the released schema. A wave that finds itself needing a migration has found a "
            "finding, not a plan item"
        ),
    }


def _predecessor_exit_state() -> dict[str, Any]:
    """22A's outcome, read out of 22A's own release record rather than restated."""
    release = _load(EVIDENCE / "sprint-22a-release.json")
    exit_criteria = _load(EVIDENCE / "sprint-22a-exit-criteria.json")
    return {
        "source": "sprint-22a-release.json",
        "source_sha256": _sha256((EVIDENCE / "sprint-22a-release.json").read_bytes()),
        "outcome": release["outcome"],
        "release_findings": len(release["findings"]),
        "exit_criteria_source_sha256": _sha256(
            (EVIDENCE / "sprint-22a-exit-criteria.json").read_bytes()
        ),
        "exit_criteria_met": exit_criteria.get("met"),
        "sprint_22b_status_per_predecessor": release["sprint_22b"],
        "carried_forward_by_name": release["carried_forward_by_name"],
        "why_carried_not_resolved": (
            "22B's objective touches neither. W2-A1 needs a migration and 22B allocates none; "
            "nothing in this sprint persists a pilot run. Both stay named in the handoff chain "
            "until a sprint whose objective touches them"
        ),
    }


def _prior_art() -> dict[str, Any]:
    """The three records the exits are compared against, bound by hash.

    Numbers appear here only where they are read back out of the bound file, so a record that
    changes changes this baseline too instead of leaving a retyped constant behind.
    """
    uniform = _load(PRIOR_ART["envelope_1e5_uniform"])
    clustered = _load(PRIOR_ART["envelope_1e5_clustered"])
    graph = _load(PRIOR_ART["graph_arm_d1_w5a"])
    arm = graph["s21d1_054_results"]["arms"]["minilm_shortlist_plus_bounded_ged"]
    policy = graph["resource_policy_compliance"]

    def _ann(document: dict[str, Any]) -> dict[str, Any]:
        envelope = next(
            item for item in document["envelopes"] if item["retrieval_mode"] == "vector_approximate"
        )
        exact = next(item for item in document["envelopes"] if item["retrieval_mode"] == "vector")
        return {
            "corpus_vector_count": envelope["corpus_vector_count"],
            "embedding_dimension": envelope["embedding_dimension"],
            "queries_measured": envelope["queries_measured"],
            "exact_scan_p95_ms": float(exact["latency_p95_ms"]),
            "ann_p95_ms": float(envelope["latency_p95_ms"]),
            "ann_recall_at_result_limit": float(envelope["recall_at_result_limit"]),
            "result_limit": envelope["result_limit"],
            "ef_search": envelope["ef_search"],
            "index_build_seconds": float(envelope["index_build_seconds"]),
            "index_size_bytes": envelope["index_size_bytes"],
            "limitations": envelope["limitations"],
        }

    return {
        "envelope_1e5_uniform": {
            "path": str(PRIOR_ART["envelope_1e5_uniform"].relative_to(REPO)),
            "sha256": _sha256(PRIOR_ART["envelope_1e5_uniform"].read_bytes()),
            **_ann(uniform),
            "read_by_an_exit_criterion": False,
            "why": (
                "independent gaussians in 768 dimensions have no cluster structure, so recall "
                "collapses on them by construction. §2.2a freezes this dataset as the "
                "adversarial bound: measured and reported in full, read by nothing"
            ),
        },
        "envelope_1e5_clustered": {
            "path": str(PRIOR_ART["envelope_1e5_clustered"].relative_to(REPO)),
            "sha256": _sha256(PRIOR_ART["envelope_1e5_clustered"].read_bytes()),
            **_ann(clustered),
            "read_by_an_exit_criterion": True,
            "why": (
                "§2.2a: the recall floor is met or missed here, on the geometry real "
                "embeddings have. Whether the headroom at 10^5 survives 10x the size is the "
                "sprint's question"
            ),
        },
        "graph_arm_d1_w5a": {
            "path": str(PRIOR_ART["graph_arm_d1_w5a"].relative_to(REPO)),
            "sha256": _sha256(PRIOR_ART["graph_arm_d1_w5a"].read_bytes()),
            "arm": "minilm_shortlist_plus_bounded_ged",
            "p50_ms": arm["p50_ms"],
            "p95_ms": arm["p95_ms"],
            "max_ms": arm["max_ms"],
            "budget_ms": policy["budget_ms"],
            "budget_cutoffs": arm["budget_cutoffs"],
            "per_pair_ged_timeouts": policy["per_pair_ged_timeouts"],
            "read_by_an_exit_criterion": False,
            "why": (
                "this is the lineage the 500 ms exit is measured against, not a threshold. "
                "§2.2d's exit is 3.6x tighter than the only graph-arm latency ever measured, "
                "at 10x the scale — and that 1788.9 ms was itself reached with 60 queries cut "
                "off at the 2 s budget, which the frozen recipe must not repeat silently"
            ),
        },
    }


def _record() -> dict[str, Any]:
    release = _predecessor_release()
    origin_main = _remote_ref("refs/heads/main")["refs/heads/main"]
    merge_base = _run("git", "merge-base", "HEAD", "origin/main")
    stores = _stores()

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22B",
        "wave": "W0",
        "phase": "before",
        "items": ["S22B-000", "S22B-001"],
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
            "22B's own pair is provisioned by this same wave, after this record exists. A "
            "baseline taken after the store it describes was created would be describing the "
            "sprint's own work"
        ),
        "predecessor_exit_state": _predecessor_exit_state(),
        "prior_art": _prior_art(),
    }
    record["commands"] = sorted(set(COMMANDS))
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-22b-baseline.json")
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
                "prior_art_bound": sorted(record["prior_art"]),
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
