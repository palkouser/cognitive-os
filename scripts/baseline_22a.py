"""S22A-000 and S22A-002. The 22A starting point, and the predecessor freeze.

Sprint 22A's exit is a *negative* claim — two domains register "without changing the core
controller or storage schema" — and a negative claim needs the live starting state read
rather than restated. One phase, because W0 provisions nothing: 22A's own store is W1's
item, when W1 first has bytes to put in one.

Everything here is read from the authority that owns it: the release handles from the remote,
the CI conclusion from the API, the branch protection from the API, the predecessor
fingerprints through the released `reality_integrity.fingerprint` rather than a second
implementation (D4 W7-A1).

Two D7 roots arrive as **first observations**, which is a finding rather than an oversight —
see the W0 log. `sprint-21d7-authority-isolation-after.json` was written in D7's W0, before
D7's own waves wrote anything, so it carries a zero-file expectation for `artifacts-s21d7`
and none at all for `artifacts-s21d6-measured`'s successor. This record freezes both.

    UV_CACHE_DIR=.cache/uv uv run python scripts/baseline_22a.py

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
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
D7_EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")
SLUG = "palkouser/cognitive-os"

D7_TAG = "sprint-21-learning-baseline"
SUCCESS_TAG = "sprint-22a-domain-baseline"
NEGATIVE_TAG = "sprint-22a-evidence-baseline"
BRANCH = "sprint-22a-groundwork"

#: The eleven pairs 22A may not write to. D7's nine, plus D7's own two roots: the one its
#: isolation record expected to stay empty and the measured one that record never named.
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
}

#: The exact-head run D7's release was closed on. Re-read from the API, never restated.
D7_CI_RUNS = (("d7 post-merge main, exact head", 31476479587),)

#: W0-F1. `sprint-21d7-authority-isolation-after.json` was written in D7's **W0**, at
#: 2026-08-10T13:31Z, and fingerprints D7's own root as empty because at that moment it was.
#: D7's W1 through W3 then wrote to it and no later record re-took the fingerprint, so the only
#: released expectation for `artifacts-s21d7` describes a state its own sprint left behind.
#: The mismatch is therefore a stale expectation, not a 22A write — and the honest handling is
#: to name it here and treat the root as a first observation, never to edit D7's sealed record
#: (W4-F1: an authorised change re-binds, it does not edit).
STALE_EXPECTATIONS = {
    "sprint_21d7": (
        "the expectation was taken in D7's own W0, before D7's W1-W3 wrote to this root, and "
        "no post-release fingerprint of it was ever sealed; 22A freezes the current state as a "
        "first observation instead"
    )
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
    """Every root D7 released a fingerprint for, read out of D7's isolation-after record."""
    isolation = json.loads(
        (D7_EVIDENCE / "sprint-21d7-authority-isolation-after.json").read_text(encoding="utf-8")
    )
    expectations = {
        item["path"].rsplit("/", 1)[-1]: item
        for item in isolation["predecessor_artifact_stores"].values()
    }
    authorities = isolation["d7_authorities"]
    expectations[authorities["artifact_root"].rsplit("/", 1)[-1]] = {
        "path_and_size_fingerprint_sha256": authorities["artifact_root_fingerprint_sha256"],
        "files": authorities["artifact_root_files"],
    }
    return expectations


def _stores() -> dict[str, Any]:
    """Every predecessor root, fingerprinted now and compared to its released expectation."""
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
                "sprint-21d7-authority-isolation-after.json"
                if expected
                else "first observation at the 22A baseline; no released expectation exists"
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


def _d7_release() -> dict[str, Any]:
    """The predecessor release. Absent, or not annotated, means 22A does not start."""
    refs = _remote_ref(f"refs/tags/{D7_TAG}*")
    tag_object = refs.get(f"refs/tags/{D7_TAG}")
    peeled = refs.get(f"refs/tags/{D7_TAG}^{{}}")
    if tag_object is None or peeled is None:
        raise SystemExit(
            f"{D7_TAG} does not resolve remotely as an annotated tag. Sprint 22A W0 is blocked "
            "on the D7 release; see Section 1.1 of the backlog."
        )
    return {
        "tag": D7_TAG,
        "remote": f"https://github.com/{SLUG}",
        "remote_tag_object": tag_object,
        "remote_peeled_commit": peeled,
        "local_tag_object": _run("git", "rev-parse", D7_TAG),
        "local_peeled_commit": _run("git", "rev-parse", f"{D7_TAG}^{{}}"),
        "tag_type": _run("git", "cat-file", "-t", tag_object),
        "local_and_remote_agree": (
            tag_object == _run("git", "rev-parse", D7_TAG)
            and peeled == _run("git", "rev-parse", f"{D7_TAG}^{{}}")
        ),
        "pull_requests": [229, 230],
    }


def _ci_runs() -> list[dict[str, Any]]:
    runs = []
    for label, run_id in D7_CI_RUNS:
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


def _gate_state() -> dict[str, Any]:
    """The dependency 22A was allocated behind, read out of D7's own gate record."""
    gate = json.loads((D7_EVIDENCE / "sprint-21d7-gate-l2.json").read_text(encoding="utf-8"))
    return {
        "gate_l2": gate["verdict"],
        "gate_l2_counts": gate["counts"],
        "gate_d1_conditions_closed": sorted(item["condition"] for item in gate["gate_d1"]),
        "sprint_22a": "unblocked",
        "source": "sprint-21d7-gate-l2.json",
        "source_sha256": _sha256((D7_EVIDENCE / "sprint-21d7-gate-l2.json").read_bytes()),
        "learning_surface_touched_by_22a": (
            "none. The live component keeps routing its five canary groups; 22A replays that "
            "surface green and changes nothing in it"
        ),
    }


def _groundwork() -> dict[str, Any]:
    survey = EVIDENCE / "sprint-22a-domain-survey.json"
    modules = (
        "src/cognitive_os/domain/descriptors.py",
        "scripts/domain_survey_22a.py",
    )
    return {
        "pull_request": None,
        "commit": _run("git", "rev-parse", "HEAD"),
        "modules": list(modules),
        "module_sha256": {name: _sha256((REPO / name).read_bytes()) for name in modules},
        "sealed_record": str(survey.relative_to(REPO)),
        "sealed_record_sha256": _sha256(survey.read_bytes()),
        "tested_by": [
            "tests/cognitive_os/domain/test_domain_descriptors.py",
            "tests/cognitive_os/domain/test_domain_survey_22a.py",
        ],
        "note": (
            "the groundwork registers nothing, routes nothing and changes no released "
            "behaviour; it defines the descriptor, its fail-closed boundary and the adapter "
            "that derives the four released domains. W0 tests it, takes the two §2.2 "
            "decisions and publishes the pre-registration"
        ),
    }


def _record() -> dict[str, Any]:
    release = _d7_release()
    origin_main = _remote_ref("refs/heads/main")["refs/heads/main"]
    merge_base = _run("git", "merge-base", "HEAD", "origin/main")
    stores = _stores()

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W0",
        "phase": "before",
        "items": ["S22A-000", "S22A-002"],
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
        },
        "d7_release": release,
        "outcome_tags_absent": {
            SUCCESS_TAG: not _remote_ref(f"refs/tags/{SUCCESS_TAG}"),
            NEGATIVE_TAG: not _remote_ref(f"refs/tags/{NEGATIVE_TAG}"),
        },
        "ci_runs": _ci_runs(),
        "main_protection": _protection(),
        "migration": {
            "repository_head": "0015",
            "planned_22a_migration": None,
            "next_available": "0016 (unallocated)",
            "0016_is_a_refusal": (
                "the exit criterion forbids a storage-schema change, so a wave that finds "
                "itself allocating a migration has left the sprint's contract and stops"
            ),
        },
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
        "stores_written_to_by_w0": [],
        "why_no_store_is_written_to": (
            "W0 provisions nothing and stores nothing: it tests the groundwork, reads the "
            "release and publishes the pre-registration. 22A's own store is W1's item, when "
            "W1 first has descriptor bytes to persist"
        ),
        "groundwork_on_this_branch": _groundwork(),
        "gate_state_at_baseline": _gate_state(),
    }
    record["commands"] = sorted(set(COMMANDS))
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-22a-baseline.json")
    arguments = parser.parse_args()

    record = _record()
    release = record["d7_release"]
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "d7_tag_agrees_locally_and_remotely": release["local_and_remote_agree"],
                "d7_peeled_commit": release["remote_peeled_commit"],
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
                "gate_l2": record["gate_state_at_baseline"]["gate_l2"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
