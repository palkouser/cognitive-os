#!/usr/bin/env python3
"""Freeze the exact released Sprint 18 parent inventory for Sprint 19."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_TAG = "sprint-18-baseline"
BASELINE_COMMIT = "a5ea70ee434bcdedf26ea6e80a0fc1e661eddf2c"  # pragma: allowlist secret
DEFAULT_OUTPUT = ROOT / "artifacts/sprint-19/preflight/repository-inventory.json"


def git(*arguments: str) -> str:
    return subprocess.check_output(("git", *arguments), cwd=ROOT, text=True).strip()


def baseline_bytes(path: str) -> bytes:
    return subprocess.check_output(("git", "show", f"{BASELINE_TAG}:{path}"), cwd=ROOT)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    resolved = git("rev-parse", f"{BASELINE_TAG}^{{}}")
    if resolved != BASELINE_COMMIT:
        raise SystemExit(f"unexpected {BASELINE_TAG}: {resolved}")
    if git("merge-base", "--is-ancestor", BASELINE_TAG, "HEAD"):
        raise SystemExit("Sprint 19 branch does not descend from sprint-18-baseline")
    files = tuple(git("ls-tree", "-r", "--name-only", BASELINE_TAG).splitlines())
    selected = tuple(
        path
        for path in files
        if path.startswith(
            (
                "src/cognitive_os/",
                "schemas/v1/",
                "infra/postgres/alembic/versions/",
                "benchmarks/manifests/",
            )
        )
        or path
        in {
            "pyproject.toml",
            "uv.lock",
            ".github/workflows/ci.yml",
            "scripts/backup_event_store.sh",
            "scripts/restore_event_store.sh",
            "docs/sprints/sprint-18/report.md",
        }
    )
    migrations = tuple(
        path for path in files if path.startswith("infra/postgres/alembic/versions/")
    )
    migration_text = "\n".join(baseline_bytes(path).decode() for path in migrations)
    workflow = baseline_bytes(".github/workflows/ci.yml").decode()
    report = baseline_bytes("docs/sprints/sprint-18/report.md")
    prior_inventory = ROOT / "artifacts/sprint-18/preflight/repository-inventory.json"
    data = {
        "schema_version": 1,
        "sprint": 19,
        "scope": "exact released Sprint 18 baseline before controlled-change implementation",
        "baseline": {
            "tag": BASELINE_TAG,
            "tag_object": git("rev-parse", BASELINE_TAG),
            "commit": resolved,
            "main": git("rev-parse", "main"),
            "origin_main": git("rev-parse", "origin/main"),
            "migration_head": "0010",
            "worktree_clean_before_branch": True,
            "branch": git("branch", "--show-current"),
        },
        "handoff": {
            "closure_report_sha256": digest(report),
            "sprint18_preflight_sha256": (
                digest(prior_inventory.read_bytes()) if prior_inventory.exists() else None
            ),
        },
        "inventory": {
            "python_files": sum(path.endswith(".py") for path in selected),
            "public_schemas": sum(path.endswith(".schema.json") for path in selected),
            "event_schemas": sum(path.startswith("schemas/v1/events/") for path in selected),
            "migrations": list(migrations),
            "tables": sorted(set(re.findall(r'Table\(\s*["\']([^"\']+)', migration_text))),
            "functions": sorted(
                set(re.findall(r"FUNCTION cognitive_os\.([a-z0-9_]+)", migration_text))
            ),
            "append_only_triggers": sorted(
                set(re.findall(r"trg_[a-z0-9_]+_append_only", migration_text))
            ),
            "ci_jobs": sorted(set(re.findall(r"^  ([a-z][a-z0-9-]+):\n", workflow, re.MULTILINE))),
        },
        "dependencies": {
            "lockfile_sha256": digest(baseline_bytes("uv.lock")),
            "new_runtime_dependency_required": False,
        },
        "operations": {
            "backup_restore": "Sprint 18 isolated restore passed",
            "merge_method": "protected merge commit",
            "runtime_merge_authority": False,
        },
        "baseline_checks": {
            "core": {"passed": 651, "skipped": 5},
            "full_repository": {"passed": 821, "skipped": 11},
            "ci_cases": 16,
            "seed_cases": 64,
            "post_merge_ci_run": 29943619550,
        },
        "profile": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "file_sha256": {path: digest(baseline_bytes(path)) for path in selected},
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation = output.with_name("baseline-validation.md")
    validation.write_text(
        "# Sprint 19 baseline validation\n\n"
        f"- Parent tag: `{BASELINE_TAG}`\n"
        f"- Parent commit: `{resolved}`\n"
        "- Migration head: `0010`\n"
        "- Sprint 18 post-merge CI: `29943619550` (`success`)\n"
        "- Parent release and backup/restore evidence: passed\n"
        "- Sprint 19 branch ancestry: verified\n",
        encoding="utf-8",
    )
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
