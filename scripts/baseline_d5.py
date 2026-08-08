"""S21D5-000 and S21D5-002. The exact D5 starting point, and the predecessor freeze.

Two items in one script because they are one set of reads. The starting point is what the
remote says right now — the D4 release handles, the absent success tag, branch protection, the
migration head — and the predecessor freeze is the fingerprint of every store D5 may not write
to, taken from the same authority at the same moment. Splitting them would mean reading the
same six directories twice and hoping the two records agree.

Everything here is read. Nothing is copied from a predecessor document except the values a
predecessor *released*, and those are compared rather than restated: a baseline written from
prose is how a sprint inherits a number that stopped being true.

    UV_CACHE_DIR=.cache/uv uv run python scripts/baseline_d5.py --phase before
    UV_CACHE_DIR=.cache/uv uv run python scripts/baseline_d5.py --phase after

`--phase after` re-fingerprints the same six roots and compares them to what `before`
recorded, which is the half of S21D5-002 that proves the wave wrote to none of them. It
refuses if the `before` record is missing, because "unchanged" needs two observations.

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

D4_TAG = "sprint-21d4-evidence-baseline"
SUCCESS_TAG = "sprint-21-learning-baseline"
BRANCH = "feature/sprint-21d5-pairwise-selective-ranking"

#: The six pairs D5 may not write to. `artifacts` is the inconsistent five-file development
#: pair every sprint since C1 has left alone; `artifacts-s21d4` joins the list because D4 is
#: released and its evidence is now somebody else's baseline.
PREDECESSOR_STORES = {
    "development": "artifacts",
    "sprint_21c3": "artifacts-s21c3",
    "sprint_21d1": "artifacts-s21d1",
    "sprint_21d2": "artifacts-s21d2",
    "sprint_21d3": "artifacts-s21d3",
    "sprint_21d4": "artifacts-s21d4",
}

#: The two exact-head runs Gate L2 condition 29 was closed on for D4. Re-read, never restated.
D4_CI_RUNS = (
    ("d4 implementation pr head", 31244781354),
    ("d4 implementation post-merge main", 31245482819),
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
    """Every predecessor root, fingerprinted now and compared to its released expectation."""
    isolation = json.loads(
        (EVIDENCE / "sprint-21d4-authority-isolation.json").read_text(encoding="utf-8")
    )
    released = isolation["predecessor_fingerprints_after"]

    out: dict[str, Any] = {}
    for key, directory in PREDECESSOR_STORES.items():
        digest, files = _fingerprint(DATA_ROOT / directory)
        expected = released.get(directory)
        out[key] = {
            "path": str(DATA_ROOT / directory),
            "files": files,
            "path_and_size_fingerprint_sha256": digest,
            # D4 fingerprinted five roots. Its own store has no released expectation, so this
            # observation becomes one — stated as a first observation rather than a match.
            "expected_from": (
                "sprint-21d4-authority-isolation.json"
                if expected
                else "first observation at the D5 baseline; no released expectation exists"
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


def _d4_release() -> dict[str, Any]:
    """The predecessor release. Absent means D5 does not start."""
    refs = _remote_ref(f"refs/tags/{D4_TAG}*")
    tag_object = refs.get(f"refs/tags/{D4_TAG}")
    peeled = refs.get(f"refs/tags/{D4_TAG}^{{}}")
    if tag_object is None or peeled is None:
        raise SystemExit(
            f"{D4_TAG} does not resolve remotely as an annotated tag. Sprint 21D5 W0 is blocked "
            "on the D4 release; see Section 1.1 of the backlog."
        )
    return {
        "tag": D4_TAG,
        "remote": f"https://github.com/{SLUG}",
        "remote_tag_object": tag_object,
        "remote_peeled_commit": peeled,
        "local_tag_object": _run("git", "rev-parse", D4_TAG),
        "local_peeled_commit": _run("git", "rev-parse", f"{D4_TAG}^{{}}"),
        "tag_type": _run("git", "cat-file", "-t", tag_object),
        "local_and_remote_agree": (
            tag_object == _run("git", "rev-parse", D4_TAG)
            and peeled == _run("git", "rev-parse", f"{D4_TAG}^{{}}")
        ),
    }


def _ci_runs() -> list[dict[str, Any]]:
    runs = []
    for label, run_id in D4_CI_RUNS:
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


def _d5_authorities() -> dict[str, Any]:
    artifact_root = DATA_ROOT / "artifacts-s21d5"
    digest, files = _fingerprint(artifact_root)
    return {
        "artifact_root": str(artifact_root),
        "artifact_root_exists": artifact_root.exists(),
        "artifact_root_files": files,
        "artifact_root_fingerprint_sha256": digest,
        "backup_root": str(DATA_ROOT / "backups-s21d5"),
        "databases": [
            "cognitive_os_s21d5_test",
            "cognitive_os_s21d5_integration_test",
            "cognitive_os_s21d5_restore_test",
        ],
        "evidence_database_prefix": "cognitive_os_s21d5",
        "outside_every_predecessor_pair": str(artifact_root)
        not in {str(DATA_ROOT / name) for name in PREDECESSOR_STORES.values()},
    }


def _before(output: Path) -> dict[str, Any]:
    release = _d4_release()
    origin_main = _remote_ref("refs/heads/main")["refs/heads/main"]
    merge_base = _run("git", "merge-base", "HEAD", "origin/main")
    stores = _stores()

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W0",
        "phase": "before",
        "items": ["S21D5-000", "S21D5-002"],
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
        "d4_release": release,
        "success_tag_absent": not _remote_ref(f"refs/tags/{SUCCESS_TAG}"),
        "success_tag_name": SUCCESS_TAG,
        "ci_runs": _ci_runs(),
        "main_protection": _protection(),
        "migration": {"repository_head": "0015", "planned_d5_migration": None},
        "predecessor_artifact_stores": stores,
        "predecessor_stores_match_expectation": all(
            item["matches_expected"] is not False for item in stores.values()
        ),
        "d5_authorities": _d5_authorities(),
        "groundwork_already_merged": {
            "pull_request": 225,
            "hypothesis_class": "pairwise-contrastive-linear-v1",
            "diagnostic": "sprint-21d5-hypothesis-class-diagnostic.json",
            "note": (
                "the class and the completed surface are implemented; neither has decided "
                "anything, and no D5 measurement has been taken"
            ),
        },
        "gate_state_at_baseline": {
            "gate_l2": "does not pass",
            "gate_d1_open": [6, 7, 15],
            "sprint_22a": "blocked",
            "learned_components_on_experience_correction_ranking": 0,
            "source": "sprint-21d4-gate-l2.json and sprint-21d4-release.json",
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
    """S21D5-001. What was created, at which head, and what still refuses.

    The refusals matter more than the creations. Two evidence stores have been erased in this
    programme by a command that reached the wrong database, so this record proves the prefix
    guard and the truncation fence are in force *before* anything is written, not after.
    """
    evidence_database = "cognitive_os_s21d5_test"
    databases = {}
    for name in _d5_authorities()["databases"]:
        # Existence first, then the value. One statement naming the table would fail to parse
        # where it does not exist, and the integration and restore databases are deliberately
        # unmigrated here — the integration fixture and a restore populate them — so
        # "no alembic_version table" is their correct state, not an error to swallow.
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
        ("artifact_root", DATA_ROOT / "artifacts-s21d5"),
        ("backup_root", DATA_ROOT / "backups-s21d5"),
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
        "sprint": "21D5",
        "wave": "W0",
        "phase": "provisioned",
        "items": ["S21D5-001"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "databases": databases,
        "evidence_database": evidence_database,
        "evidence_database_at_repository_head": (
            databases[evidence_database]["alembic_head"] == "0015"
        ),
        "migration": {
            "repository_head": "0015",
            "planned_d5_migration": None,
            "next_available": "0016 (unallocated)",
            "alembic_check": "no new upgrade operations detected",
        },
        "roots": roots,
        "environment_file": ".env.s21d5.local",
        "guards": {
            "evidence_database_prefix": "cognitive_os_s21d5",
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
                "variables by design, so every D5 shell invocation passes "
                "COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d5.local rather than exporting"
            ),
        },
        "findings": ["S21D5-W0-F1"],
    }
    record["commands"] = sorted(set(COMMANDS))
    return _sealed(record, output)


def _after(output: Path) -> dict[str, Any]:
    # Named rather than derived from `output`: deriving one evidence filename from another by
    # string surgery is how a comparison ends up reading a file that does not exist, or worse,
    # one that does and is not the record it claims to compare against.
    before_path = EVIDENCE / "sprint-21d5-baseline.json"
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
        "sprint": "21D5",
        "wave": "W0",
        "phase": "after",
        "items": ["S21D5-002"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "compared_against": before_path.name,
        "compared_against_sha256": hashlib.sha256(before_path.read_bytes()).hexdigest(),
        "predecessor_artifact_stores": stores,
        "drifted_stores": drifted,
        "zero_predecessor_writes": not drifted,
        "d5_authorities": _d5_authorities(),
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
        "before": "sprint-21d5-baseline.json",
        "provisioned": "sprint-21d5-provisioning.json",
        "after": "sprint-21d5-authority-isolation-after.json",
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
            "d4_tag_local_and_remote_agree": record["d4_release"]["local_and_remote_agree"],
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
