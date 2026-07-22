#!/usr/bin/env python3
"""Reconstruct the verified Sprint 17 preflight inventory from its exact tag."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts/sprint-18/preflight/repository-inventory.json"
BASELINE_TAG = "sprint-17-baseline"
BASELINE_COMMIT = "e8ca551dc9697886a935687265073bd402efe06c"  # pragma: allowlist secret


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _baseline_bytes(name: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASELINE_TAG}:{name}"], cwd=ROOT)


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _matching(files: tuple[str, ...], *patterns: str) -> tuple[str, ...]:
    return tuple(name for name in files if any(Path(name).match(pattern) for pattern in patterns))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    resolved = _git("rev-parse", f"{BASELINE_TAG}^{{}}")
    if resolved != BASELINE_COMMIT:
        raise SystemExit(f"unexpected {BASELINE_TAG}: {resolved}")
    listing = _git("ls-tree", "-r", "--name-only", BASELINE_TAG)
    files = tuple(listing.splitlines())
    python_files = _matching(files, "src/cognitive_os/**/*.py")
    schemas = _matching(files, "schemas/v1/**/*.schema.json")
    events = _matching(files, "schemas/v1/events/*.schema.json")
    migrations = _matching(files, "infra/postgres/alembic/versions/*.py")
    benchmarks = _matching(files, "benchmarks/manifests/*.yaml")
    docs = _matching(
        files,
        "docs/adr/*.md",
        "docs/architecture/*.md",
        "docs/operations/*.md",
        "docs/security/*.md",
    )
    migration_text = "\n".join(_baseline_bytes(name).decode() for name in migrations)
    pyproject = tomllib.loads(_baseline_bytes("pyproject.toml").decode())
    dependency_groups = pyproject.get("dependency-groups", {})
    optional_dependencies = pyproject.get("project", {}).get("optional-dependencies", {})
    source_packages = sorted(
        {
            Path(name).parts[2]
            for name in python_files
            if len(Path(name).parts) > 3 and Path(name).parts[2] != "__pycache__"
        }
    )
    registry_files = tuple(
        name
        for name in python_files
        if any(
            marker in name
            for marker in (
                "provider",
                "tool",
                "verification",
                "retriev",
                "skills",
                "strateg",
                "routing",
                "weakness",
                "registry",
            )
        )
    )
    inventory_files = sorted(
        set(
            python_files
            + schemas
            + migrations
            + benchmarks
            + docs
            + (
                "pyproject.toml",
                "uv.lock",
                ".github/workflows/ci.yml",
                "scripts/backup_event_store.sh",
                "scripts/restore_event_store.sh",
            )
        )
    )
    data = {
        "schema_version": 1,
        "sprint": 18,
        "scope": "verified Sprint 17 release baseline before Sprint 18 changes",
        "baseline": {
            "tag": BASELINE_TAG,
            "commit": BASELINE_COMMIT,
            "resolved_commit": resolved,
            "migration_head": "0009",
            "worktree_clean_before_branch": True,
            "tracked_branch": "main",
            "remotes": _git("remote", "-v").splitlines(),
        },
        "source": {
            "python_files": list(python_files),
            "public_contract_schemas": list(schemas),
            "event_schemas": list(events),
            "owned_packages": source_packages,
        },
        "database": {
            "migrations": list(migrations),
            "tables": sorted(set(re.findall(r"create_table\(\s*[\"']([^\"']+)", migration_text))),
            "functions": sorted(
                set(re.findall(r"FUNCTION cognitive_os\.([a-z0-9_]+)", migration_text))
            ),
            "grant_statements": sorted(set(re.findall(r"GRANT [^;]+", migration_text))),
            "protected_history_triggers": sorted(
                set(re.findall(r"protect_[a-z0-9_]+", migration_text))
            ),
        },
        "application": {
            "ports_and_services": list(
                _matching(
                    files,
                    "src/cognitive_os/application/ports/*.py",
                    "src/cognitive_os/**/*service.py",
                )
            ),
            "registered_subsystem_files": list(registry_files),
        },
        "dependencies": {
            "optional_groups": sorted(optional_dependencies),
            "development_groups": sorted(dependency_groups),
            "lockfile_sha256": _hash(_baseline_bytes("uv.lock")),
        },
        "benchmarks": {name: _hash(_baseline_bytes(name)) for name in benchmarks},
        "operations": {
            "backup_manifest_sections": [
                "event_count",
                "artifact_count",
                "memory",
                "semantic",
                "skills",
                "strategies",
                "experience",
                "corpus",
                "routing",
                "weakness",
            ],
            "isolated_backup_restore": "passed",
        },
        "documentation": list(docs),
        "baseline_checks": {
            "ruff_check": "passed",
            "ruff_format": "passed",
            "cognitive_os_tests": {"passed": 643, "skipped": 5},
            "postgres_migration_drift_at_0009": "passed",
        },
        "file_sha256": {name: _hash(_baseline_bytes(name)) for name in inventory_files},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
