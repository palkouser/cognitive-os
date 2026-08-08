"""S21D4-000. The exact Sprint 21D4 starting point, from fresh local and remote reads.

The point of this script is that it reads rather than restates. Every value below comes from
`git`, the GitHub API or the released fingerprint authority at the moment it runs; nothing is
copied from a predecessor document. A baseline written from prose is how a sprint inherits a
number that stopped being true.

It refuses to produce a record if the D3 release does not resolve remotely, which is the one
condition Section 1.0 of the backlog names as blocking.

    UV_CACHE_DIR=.cache/uv uv run python scripts/baseline_d4.py

Read-only. It mutates no remote and writes to no store.
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
EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")
SLUG = "palkouser/cognitive-os"

D3_TAG = "sprint-21d3-evidence-baseline"
SUCCESS_TAG = "sprint-21-learning-baseline"
BRANCH = "feature/sprint-21d4-selective-correction-ranking"

#: The five pairs D4 may not write to. The development pair is the inconsistent five-file one
#: every sprint since C1 has left alone.
PREDECESSOR_STORES = {
    "development": "artifacts",
    "sprint_21c3": "artifacts-s21c3",
    "sprint_21d1": "artifacts-s21d1",
    "sprint_21d2": "artifacts-s21d2",
    "sprint_21d3": "artifacts-s21d3",
}

COMMANDS: list[str] = []


def _run(*args: str) -> str:
    COMMANDS.append(" ".join(args))
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def _gh_json(path: str, *extra: str) -> Any:
    return json.loads(_run("gh", "api", path, *extra))


def _remote_ref(pattern: str) -> dict[str, str]:
    out = _run("git", "ls-remote", "origin", pattern)
    rows = [line.split("\t") for line in out.splitlines() if line]
    return {ref: sha for sha, ref in rows}


def _d3_release() -> dict[str, Any]:
    """The predecessor release. Absent means D4 does not start."""
    refs = _remote_ref(f"refs/tags/{D3_TAG}*")
    tag_object = refs.get(f"refs/tags/{D3_TAG}")
    peeled = refs.get(f"refs/tags/{D3_TAG}^{{}}")
    if tag_object is None or peeled is None:
        raise SystemExit(
            f"{D3_TAG} does not resolve remotely as an annotated tag. Sprint 21D4 W0 is blocked "
            "on S21D3-094 and S21D3-095; see Section 1.0 of the backlog."
        )
    return {
        "tag": D3_TAG,
        "remote": f"https://github.com/{SLUG}",
        "remote_tag_object": tag_object,
        "remote_peeled_commit": peeled,
        "local_tag_object": _run("git", "rev-parse", D3_TAG),
        "local_peeled_commit": _run("git", "rev-parse", f"{D3_TAG}^{{}}"),
        "tag_type": _run("git", "cat-file", "-t", tag_object),
    }


def _ci_runs() -> list[dict[str, Any]]:
    """Every exact-head run the D4 baseline depends on, re-read from the API."""
    runs = []
    for label, run_id in (
        ("d3 implementation pr head", 31031716153),
        ("d3 implementation post-merge main", 31072527026),
        ("d3 gate-close pr head", None),
        ("d3 gate-close post-merge main", 31076102720),
    ):
        if run_id is None:
            continue
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
        "queried_json_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "required_context_count": len(contexts),
        "required_contexts": sorted(contexts),
        "required_conversation_resolution": document["required_conversation_resolution"]["enabled"],
        "required_pull_request_reviews": document.get("required_pull_request_reviews"),
        "strict": document["required_status_checks"]["strict"],
    }


def _stores() -> tuple[dict[str, Any], bool]:
    """Fingerprints through the released authority, never a second implementation. W7-A1."""
    from cognitive_os.coding.reality_integrity import fingerprint

    baseline = json.loads((EVIDENCE / "sprint-21d3-baseline.json").read_text(encoding="utf-8"))
    released = {
        item["absolute_root"].rsplit("/", 1)[-1]: item
        for item in baseline["predecessor_artifact_stores"].values()
    }
    d3_release = json.loads((EVIDENCE / "sprint-21d3-release.json").read_text(encoding="utf-8"))
    released |= {
        name: {
            "files": item["files"],
            "fingerprint_sha256": item["path_and_size_fingerprint_sha256"],
        }
        for name, item in d3_release["store_fingerprints_after_release"].items()
    }

    out: dict[str, Any] = {}
    unchanged = True
    for key, directory in PREDECESSOR_STORES.items():
        digest, files = fingerprint(DATA_ROOT / directory)
        expected = released.get(directory, {})
        want = expected.get("fingerprint_sha256") or expected.get(
            "path_and_size_fingerprint_sha256"
        )
        matches = want is None or (digest == want and files == expected.get("files", files))
        unchanged &= bool(matches)
        out[key] = {
            "path": str(DATA_ROOT / directory),
            "files": files,
            "path_and_size_fingerprint_sha256": digest,
            "expected_from": "sprint-21d3-release.json or sprint-21d3-baseline.json",
            "matches_expected": bool(matches),
        }
    return out, unchanged


def _d4_authorities() -> dict[str, Any]:
    from cognitive_os.coding.reality_integrity import fingerprint

    digest, files = fingerprint(DATA_ROOT / "artifacts-s21d4")
    return {
        "artifact_root": str(DATA_ROOT / "artifacts-s21d4"),
        "artifact_root_files_at_baseline": files,
        "artifact_root_fingerprint_sha256": digest,
        "backup_root": str(DATA_ROOT / "backups-s21d4"),
        "scratch_root": str(DATA_ROOT / "scratch-s21d4"),
        "databases": [
            "cognitive_os_s21d4_test",
            "cognitive_os_s21d4_integration_test",
            "cognitive_os_s21d4_restore_test",
        ],
        "outside_every_predecessor_pair": True,
    }


def build() -> dict[str, Any]:
    release = _d3_release()
    origin_main = _remote_ref("refs/heads/main")["refs/heads/main"]
    local_head = _run("git", "rev-parse", "HEAD")
    stores, unchanged = _stores()

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W0",
        "items": ["S21D4-000"],
        "read_policy": "fresh local and remote reads; no remote mutation",
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": {
            "name": BRANCH,
            "local_head": local_head,
            "origin_main": origin_main,
            "merge_base_with_origin_main": _run("git", "merge-base", "HEAD", "origin/main"),
            "descends_from_current_origin_main": _run("git", "merge-base", "HEAD", "origin/main")
            == origin_main,
            "commits_ahead_at_baseline": int(
                _run("git", "rev-list", "--count", "origin/main..HEAD")
            ),
        },
        "d3_release": release,
        "success_tag_absent": not _remote_ref(f"refs/tags/{SUCCESS_TAG}"),
        "success_tag_name": SUCCESS_TAG,
        "ci_runs": _ci_runs(),
        "main_protection": _protection(),
        "migration": {"repository_head": "0015", "planned_d4_migration": None},
        "predecessor_artifact_stores": stores,
        "zero_predecessor_writes": unchanged,
        "d4_authorities": _d4_authorities(),
        "gate_state_at_baseline": {
            "gate_l2": "does not pass",
            "gate_d1_open": [6, 7, 15],
            "sprint_22a": "blocked",
            "learned_components_on_experience_correction_ranking": 0,
            "source": "sprint-21d3-gate-l2.json and sprint-21d3-release.json",
        },
    }
    record["commands"] = sorted(set(COMMANDS))
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d4-baseline.json"))
    arguments = parser.parse_args()

    record = build()
    body = json.dumps(record, indent=1, sort_keys=True) + "\n"
    Path(arguments.output).write_text(body, encoding="utf-8")
    print(
        json.dumps(
            {
                "output": Path(arguments.output).name,
                "descends_from_current_origin_main": record["branch"][
                    "descends_from_current_origin_main"
                ],
                "zero_predecessor_writes": record["zero_predecessor_writes"],
                "success_tag_absent": record["success_tag_absent"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
