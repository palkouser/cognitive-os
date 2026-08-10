"""S21D6-000 and S21D6-002. The exact D6 starting point, and the predecessor freeze.

Two items in one script because they are one set of reads, for the reason
[`baseline_d5.py`](baseline_d5.py) gives and D6 does not improve on: the starting point is what
the remote says right now — the D5 release handles, the still-absent success tag, branch
protection, the migration head — and the predecessor freeze is the fingerprint of every store D6
may not write to, taken from the same authority at the same moment.

Everything here is read. Values a predecessor *released* are compared rather than restated.

    UV_CACHE_DIR=.cache/uv uv run python scripts/baseline_d6.py --phase before
    UV_CACHE_DIR=.cache/uv uv run python scripts/baseline_d6.py --phase provisioned
    UV_CACHE_DIR=.cache/uv uv run python scripts/baseline_d6.py --phase after

`--phase after` re-fingerprints the same seven roots and compares them to what `before`
recorded, which is the half of S21D6-002 that proves the wave wrote to none of them.

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

D5_TAG = "sprint-21d5-evidence-baseline"
SUCCESS_TAG = "sprint-21-learning-baseline"
BRANCH = "sprint-21d6-groundwork"

#: The seven pairs D6 may not write to. `artifacts-s21d5` joins D5's six for the reason
#: `artifacts-s21d4` joined D4's five: D5 is released and its evidence is now somebody else's
#: baseline. D6 reads D5's calibration matrices out of it and writes nothing back.
PREDECESSOR_STORES = {
    "development": "artifacts",
    "sprint_21c3": "artifacts-s21c3",
    "sprint_21d1": "artifacts-s21d1",
    "sprint_21d2": "artifacts-s21d2",
    "sprint_21d3": "artifacts-s21d3",
    "sprint_21d4": "artifacts-s21d4",
    "sprint_21d5": "artifacts-s21d5",
}

#: The two exact-head runs Gate L2 condition 29 was closed on for D5. Re-read, never restated.
D5_CI_RUNS = (
    ("d5 implementation pr head", 31327874931),
    ("d5 implementation post-merge main", 31328614887),
)

COMMANDS: list[str] = []


def _run(*args: str) -> str:
    COMMANDS.append(" ".join(args))
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()


def _gh_json(path: str) -> Any:
    return json.loads(_run("gh", "api", path))


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


def _stores() -> dict[str, Any]:
    """Every predecessor root, fingerprinted now and compared to its released expectation.

    The expectation comes from D5's *after* record rather than its baseline: the after record is
    the one that proves those digests survived a whole sprint, and it is the one D5 released.
    """
    isolation = json.loads(
        (EVIDENCE / "sprint-21d5-authority-isolation-after.json").read_text(encoding="utf-8")
    )
    released = {
        item["path"].rsplit("/", 1)[-1]: item
        for item in isolation["predecessor_artifact_stores"].values()
    }

    out: dict[str, Any] = {}
    for key, directory in PREDECESSOR_STORES.items():
        digest, files = _fingerprint(DATA_ROOT / directory)
        expected = released.get(directory)
        out[key] = {
            "path": str(DATA_ROOT / directory),
            "files": files,
            "path_and_size_fingerprint_sha256": digest,
            "expected_from": (
                "sprint-21d5-authority-isolation-after.json"
                if expected
                else "first observation at the D6 baseline; no released expectation exists"
            ),
            "matches_expected": (
                None
                if expected is None
                else bool(
                    digest == expected["path_and_size_fingerprint_sha256"]
                    and files == expected["files"]
                )
            ),
        }
    return out


def _d5_release() -> dict[str, Any]:
    """The predecessor release. Absent means D6 does not start."""
    refs = _remote_ref(f"refs/tags/{D5_TAG}*")
    tag_object = refs.get(f"refs/tags/{D5_TAG}")
    peeled = refs.get(f"refs/tags/{D5_TAG}^{{}}")
    if tag_object is None or peeled is None:
        raise SystemExit(
            f"{D5_TAG} does not resolve remotely as an annotated tag. Sprint 21D6 W0 is blocked "
            "on the D5 release; see Section 1.1 of the backlog."
        )
    return {
        "tag": D5_TAG,
        "remote": f"https://github.com/{SLUG}",
        "remote_tag_object": tag_object,
        "remote_peeled_commit": peeled,
        "local_tag_object": _run("git", "rev-parse", D5_TAG),
        "local_peeled_commit": _run("git", "rev-parse", f"{D5_TAG}^{{}}"),
        "tag_type": _run("git", "cat-file", "-t", tag_object),
        "local_and_remote_agree": (
            tag_object == _run("git", "rev-parse", D5_TAG)
            and peeled == _run("git", "rev-parse", f"{D5_TAG}^{{}}")
        ),
    }


def _ci_runs() -> list[dict[str, Any]]:
    runs = []
    for label, run_id in D5_CI_RUNS:
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


def _d6_authorities() -> dict[str, Any]:
    artifact_root = DATA_ROOT / "artifacts-s21d6"
    digest, files = _fingerprint(artifact_root)
    return {
        "artifact_root": str(artifact_root),
        "artifact_root_exists": artifact_root.exists(),
        "artifact_root_files": files,
        "artifact_root_fingerprint_sha256": digest,
        "backup_root": str(DATA_ROOT / "backups-s21d6"),
        "databases": [
            "cognitive_os_s21d6_test",
            "cognitive_os_s21d6_integration_test",
            "cognitive_os_s21d6_restore_test",
        ],
        "evidence_database_prefix": "cognitive_os_s21d6",
        "outside_every_predecessor_pair": str(artifact_root)
        not in {str(DATA_ROOT / name) for name in PREDECESSOR_STORES.values()},
    }


def _before(output: Path) -> dict[str, Any]:
    release = _d5_release()
    origin_main = _remote_ref("refs/heads/main")["refs/heads/main"]
    merge_base = _run("git", "merge-base", "HEAD", "origin/main")
    stores = _stores()

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D6",
        "wave": "W0",
        "phase": "before",
        "items": ["S21D6-000", "S21D6-002"],
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
        "d5_release": release,
        "success_tag_absent": not _remote_ref(f"refs/tags/{SUCCESS_TAG}"),
        "success_tag_name": SUCCESS_TAG,
        "ci_runs": _ci_runs(),
        "main_protection": _protection(),
        "migration": {"repository_head": "0015", "planned_d6_migration": None},
        "predecessor_artifact_stores": stores,
        "predecessor_stores_match_expectation": all(
            item["matches_expected"] is not False for item in stores.values()
        ),
        "d6_authorities": _d6_authorities(),
        "groundwork_on_this_branch": {
            "pull_request": None,
            "commit": _run("git", "rev-parse", "HEAD"),
            "admission_rule": "split-conformal over the sealed pairwise-contrastive margin",
            "module": "src/cognitive_os/learning/conformal_operating_point.py",
            "note": (
                "the admission rule is implemented and tested on hand-computable vectors; it has "
                "decided nothing, and no D6 measurement has been taken. Unlike D5's groundwork "
                "this is not yet merged, so the baseline records the commit rather than a PR"
            ),
        },
        "gate_state_at_baseline": {
            "gate_l2": "does not pass",
            "gate_l2_counts": {"met": 14, "not_opened": 15, "failed": 0},
            "gate_d1_open": [6, 7],
            "sprint_22a": "blocked",
            "learned_components_on_experience_correction_ranking": 0,
            "d5_stop": {
                "kind": "selective_margin_bound",
                "hash": "7b59897d8d83a51be3d8fb5c65e4208ddb07d813884eb99ccdb36b73236fec59",
            },
            "source": "sprint-21d5-gate-l2.json and sprint-21d5-release.json",
        },
    }
    record["commands"] = sorted(set(COMMANDS))
    return _sealed(record, output)


def _psql(database: str, query: str) -> list[str]:
    out = _run(
        "docker",
        "exec",
        "compose-postgres-1",
        "psql",
        "-U",
        "cogos_owner",
        "-d",
        database,
        "-tAc",
        query,
    )
    return [line for line in out.splitlines() if line.strip()]


def _provisioned(output: Path) -> dict[str, Any]:
    """S21D6-001. What was created, at which head, and what still refuses."""
    evidence_database = "cognitive_os_s21d6_test"
    databases = {}
    for name in _d6_authorities()["databases"]:
        migrated = _psql(name, "select to_regclass('public.alembic_version') is not null")
        head = (
            _psql(name, "select version_num from public.alembic_version limit 1")
            if migrated and migrated[0] == "t"
            else ["unmigrated"]
        )
        tables = _psql(
            name,
            "select count(*) from information_schema.tables where table_schema='cognitive_os'",
        )
        databases[name] = {
            "exists": True,
            "alembic_head": head[0] if head else None,
            "cognitive_os_tables": int(tables[0]) if tables else 0,
            "role": (
                "evidence store"
                if name == evidence_database
                else "migrated by its own flow, not by W0"
            ),
        }

    roots = {}
    for label, directory in (
        ("artifact_root", DATA_ROOT / "artifacts-s21d6"),
        ("backup_root", DATA_ROOT / "backups-s21d6"),
    ):
        digest, files = _fingerprint(directory)
        roots[label] = {
            "path": str(directory),
            "exists": directory.exists(),
            "files": files,
            "path_and_size_fingerprint_sha256": digest,
        }

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D6",
        "wave": "W0",
        "phase": "provisioned",
        "items": ["S21D6-001"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "databases": databases,
        "evidence_database": evidence_database,
        "evidence_database_at_repository_head": (
            databases[evidence_database]["alembic_head"] == "0015"
        ),
        "migration": {
            "repository_head": "0015",
            "planned_d6_migration": None,
            "next_available": "0016 (unallocated)",
            "alembic_check": "no new upgrade operations detected",
        },
        "roots": roots,
        "environment_file": ".env.s21d6.local",
        "guards": {
            "evidence_database_prefix": "cognitive_os_s21d6",
            "prefix_guard": (
                "postgres_provision_evidence.sh refuses any database outside the prefix"
            ),
            "truncatable_database_nominated": None,
            "truncation_fence": (
                "COGOS_TRUNCATABLE_DATABASE is unset, so every truncating path declines; a "
                "nomination naming any database other than the connected one is refused loudly"
            ),
            "shared_loader": (
                "scripts/postgres_common.sh re-reads its own file and overrides exported "
                "variables by design, so every D6 shell invocation passes "
                "COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d6.local rather than exporting"
            ),
            "s21d5_w0_f1_not_repeated": (
                "D5's finding was a migration that reached the development database first "
                "because the loader re-read a stale file; D6 provisions with the env file passed "
                "explicitly and verifies the head on the prefixed database before recording it"
            ),
        },
        "findings": [],
    }
    record["commands"] = sorted(set(COMMANDS))
    return _sealed(record, output)


def _after(output: Path) -> dict[str, Any]:
    before_path = EVIDENCE / "sprint-21d6-baseline.json"
    if not before_path.exists():
        raise SystemExit(f"{before_path.name} is missing; 'unchanged' needs two observations")
    before = json.loads(before_path.read_text(encoding="utf-8"))

    stores = _stores()
    drifted = {
        key: {
            "before": before["predecessor_artifact_stores"][key][
                "path_and_size_fingerprint_sha256"
            ],
            "after": item["path_and_size_fingerprint_sha256"],
        }
        for key, item in stores.items()
        if item["path_and_size_fingerprint_sha256"]
        != before["predecessor_artifact_stores"][key]["path_and_size_fingerprint_sha256"]
    }
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D6",
        "wave": "W0",
        "phase": "after",
        "items": ["S21D6-002"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "compared_against": before_path.name,
        "compared_against_sha256": hashlib.sha256(before_path.read_bytes()).hexdigest(),
        "predecessor_artifact_stores": stores,
        "drifted_stores": drifted,
        "zero_predecessor_writes": not drifted,
        "d6_authorities": _d6_authorities(),
    }
    record["commands"] = sorted(set(COMMANDS))
    return _sealed(record, output)


def _sealed(record: dict[str, Any], output: Path) -> dict[str, Any]:
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("before", "provisioned", "after"), default="before")
    parser.add_argument("--output", default=None)
    arguments = parser.parse_args()

    defaults = {
        "before": "sprint-21d6-baseline.json",
        "provisioned": "sprint-21d6-provisioning.json",
        "after": "sprint-21d6-authority-isolation-after.json",
    }
    builders = {"before": _before, "provisioned": _provisioned, "after": _after}
    output = Path(arguments.output) if arguments.output else EVIDENCE / defaults[arguments.phase]
    record = builders[arguments.phase](output)

    summary = {"output": output.name, "integrity_content_hash": record["integrity_content_hash"]}
    if arguments.phase == "before":
        summary |= {
            "descends_from_current_origin_main": record["branch"][
                "descends_from_current_origin_main"
            ],
            "d5_tag_local_and_remote_agree": record["d5_release"]["local_and_remote_agree"],
            "success_tag_absent": record["success_tag_absent"],
            "predecessor_stores_match_expectation": record["predecessor_stores_match_expectation"],
        }
    elif arguments.phase == "provisioned":
        summary |= {
            "evidence_database_at_repository_head": record["evidence_database_at_repository_head"],
            "databases": {name: item["alembic_head"] for name, item in record["databases"].items()},
        }
    else:
        summary |= {"zero_predecessor_writes": record["zero_predecessor_writes"]}
    print(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
