"""S22E-001 and S22E-002. The blocking check, the host, the predecessor roots, the surface.

W0 measures nothing about the loop. It settles what every later claim will mean, and it does
four things this file is responsible for.

**The blocking check.** §0's contract is that a wave verifies its predecessor's release from
**live handles**, never from the plan's prose. 22D's release is read off the remote — tag
object, peeled commit, ancestry against `origin/main`, the exact-head CI run, and the branch
protection the merge will have to pass — and the values are then sealed here as observations.
`--check` does not re-read the network: a validator that needs a remote is a validator that
fails on an aeroplane, and 22C W1-F1's rule is that `--check` may not re-derive a world
observation. `--verify-release` is the mode that re-reads it, on purpose and on request.

**The host.** Split the way 22B's S22B-002 and 22C's W1-F1 require: *invariants* are
recomputed by `--check`, *observations* are recorded and compared against nothing.

**The predecessor roots.** 22A through 22D's artifact roots are fingerprinted now, so that
"22E touched nothing that came before it" is a comparison at W4 rather than an assurance. This
is the cheapest possible version of 22A W4-F2, and it costs one path-and-size sweep per root.

**The surface.** §2.2(a)'s active surface, enumerated in `surface_22e` off a released contract
and captured once here as the W0 baseline every rejected proposal is compared against.

    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/preflight_22e.py
    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/preflight_22e.py --check
    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/preflight_22e.py --verify-release
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from surface_22e import capture  # noqa: E402

from cognitive_os.coding.reality_integrity import fingerprint  # noqa: E402

OUTPUT = EVIDENCE / "sprint-22e-preflight.json"

#: Frozen, not read from a clock, so a rebuild is byte-identical.
PREFLIGHT_TIME = "2026-08-16T00:00:00Z"

#: The named owner. §3.2: W0's first act on an unconcluded gate is to surface it with an owner.
GATE_OWNER = "palkouser (Sprint 22 gate owner)"

#: 22D's release, read from the remote at W0 and sealed here. Re-read with `--verify-release`.
PREDECESSOR_RELEASE = {
    "tag": "sprint-22d-evidence-baseline",
    "tag_object": "c546ac8c903cf9a3693c47ac88b7cce04c012a53",
    "peels_to": "cb4d4ada82145ce31033823e2c70a06e308340d8",
    "is_ancestor_of_protected_main": True,
    "equals_protected_main": True,
    "exact_head_ci_run": "31932062537",
    "exact_head_ci_conclusion": "success",
    "exact_head_ci_jobs_not_successful": 0,
    "protection": {"required_checks": 27, "enforce_admins": True},
}

#: The migration head §1.4 froze. `0016` is a refusal, and the W0 gate-owner decision (§2.1)
#: kept it one — so this is the head every 22E store must be at, at W0 and at W4 alike.
EXPECTED_MIGRATION_HEAD = "0015"

#: Every store this sprint provisions, and what it is for. The clone is separate **by
#: construction** (its name is not derivable from `COGOS_DATABASE_URL`), which is 22B W1-F6's
#: rule applied to a clone rather than to a holdout.
STORES = {
    "governed": "COGOS_DATABASE_ADMIN_URL",
    "clone": "COGOS_CLONE_DATABASE_ADMIN_URL",
    "integration": "COGOS_INTEGRATION_DATABASE_ADMIN_URL",
}

#: Fingerprinted now so that "22E touched nothing before it" is a comparison at W4.
PREDECESSOR_ROOTS = (
    "artifacts-s22a",
    "artifacts-s22b",
    "artifacts-s22c",
    "artifacts-s22c-campaign",
    "artifacts-s22c-holdout",
    "artifacts-s22d",
)
DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")

#: What `--check` re-reads instead of recomputing. Free memory moves every minute; the release
#: handles need a network; the surface moves the moment anything writes to the store, which is
#: what the rest of the sprint is *for*.
OBSERVED_AT_W0 = (
    "observations",
    "predecessor_release",
    "active_surface",
    "stores",
    "predecessor_roots",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# The blocking check, from live handles
# ---------------------------------------------------------------------------


def _run(*arguments: str) -> str:
    return subprocess.run(
        arguments, cwd=REPO, capture_output=True, text=True, check=True, timeout=120
    ).stdout.strip()


def verify_release_from_the_remote() -> dict[str, Any]:
    """Re-read 22D's release off the remote and compare it to the sealed values.

    Kept out of `--check` on purpose. This is the mode that answers "is the sealed blocking
    check still true", and it is a different question from "does this record reproduce".
    """
    tag = PREDECESSOR_RELEASE["tag"]
    refs = dict(
        (line.split("\t")[1], line.split("\t")[0])
        for line in _run("git", "ls-remote", "--tags", "origin").splitlines()
        if "\t" in line
    )
    tag_object = refs.get(f"refs/tags/{tag}")
    peeled = refs.get(f"refs/tags/{tag}^{{}}")
    main = _run("git", "ls-remote", "origin", "refs/heads/main").split("\t")[0]
    runs = json.loads(
        _run(
            "gh",
            "api",
            f"repos/:owner/:repo/actions/runs?head_sha={peeled}&per_page=20",
            "--jq",
            "[.workflow_runs[] | {id: (.id|tostring), conclusion}]",
        )
        or "[]"
    )
    protection = json.loads(
        _run(
            "gh",
            "api",
            "repos/:owner/:repo/branches/main/protection",
            "--jq",
            "{required_checks: (.required_status_checks.contexts|length), "
            "enforce_admins: .enforce_admins.enabled}",
        )
    )
    live = {
        "tag_object": tag_object,
        "peels_to": peeled,
        "equals_protected_main": peeled == main,
        "exact_head_ci_runs": runs,
        "protection": protection,
    }
    return {
        "live": live,
        "sealed": PREDECESSOR_RELEASE,
        "still_agrees": (
            tag_object == PREDECESSOR_RELEASE["tag_object"]
            and peeled == PREDECESSOR_RELEASE["peels_to"]
            and peeled == main
            and any(
                item["id"] == PREDECESSOR_RELEASE["exact_head_ci_run"]
                and item["conclusion"] == PREDECESSOR_RELEASE["exact_head_ci_conclusion"]
                for item in runs
            )
            and protection == PREDECESSOR_RELEASE["protection"]
        ),
    }


# ---------------------------------------------------------------------------
# The host
# ---------------------------------------------------------------------------


def _cpu() -> dict[str, Any]:
    text = Path("/proc/cpuinfo").read_text(encoding="utf-8")
    models = {
        line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("model name")
    }
    cores = {
        line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("cpu cores")
    }
    return {
        "model": sorted(models)[0] if models else "unknown",
        "logical_cpus": os.cpu_count() or 0,
        "physical_cores": int(sorted(cores)[0]) if cores else 0,
    }


def _invariants() -> dict[str, Any]:
    return {
        "cpu": _cpu(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "platform": sys.platform,
    }


def _observations() -> dict[str, Any]:
    stats = os.statvfs(REPO)
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            memory = int(line.split()[1])
            break
    else:
        memory = 0
    return {
        "memory_total_kib": memory,
        "free_disk_gib_repo": int(stats.f_bavail * stats.f_frsize / 1024**3),
        "why_not_invariant": (
            "free disk and total memory are states of the world at W0, not properties of the "
            "declared host; `--check` re-reads them and compares them against nothing "
            "(22B S22B-002, 22C W1-F1)"
        ),
    }


# ---------------------------------------------------------------------------
# The stores and the roots
# ---------------------------------------------------------------------------


async def _stores() -> dict[str, Any]:
    from sqlalchemy import text as sql
    from sqlalchemy.ext.asyncio import create_async_engine

    results: dict[str, Any] = {}
    for name, variable in STORES.items():
        url = os.environ.get(variable)
        if not url:
            results[name] = {"provisioned": False, "reason": f"{variable} is unset"}
            continue
        engine = create_async_engine(url)
        try:
            async with engine.connect() as connection:
                # Unqualified: alembic keeps its version table in `public`, not in the
                # `cognitive_os` schema every governed table lives in. Qualifying it with
                # the schema the rest of this file uses raises UndefinedTable, which reads
                # as "the store is not provisioned" rather than as "the query is wrong".
                head = (
                    await connection.execute(sql("SELECT version_num FROM alembic_version"))
                ).scalar_one()
                tables = (
                    await connection.execute(
                        sql(
                            "SELECT count(*) FROM information_schema.tables "
                            "WHERE table_schema = 'cognitive_os' AND table_type = 'BASE TABLE'"
                        )
                    )
                ).scalar_one()
        finally:
            await engine.dispose()
        results[name] = {
            "provisioned": True,
            "migration_head": head,
            "at_the_expected_head": head == EXPECTED_MIGRATION_HEAD,
            "tables": int(tables),
        }
    return {
        "stores": results,
        "expected_migration_head": EXPECTED_MIGRATION_HEAD,
        "every_store_at_the_expected_head": all(
            item.get("at_the_expected_head") for item in results.values()
        ),
        "zero_zero_sixteen_is": (
            "a refusal by default (§ header), and the W0 gate-owner decision (§2.1) kept it "
            "one — so this head is also the head W4 must still read"
        ),
        "the_clone_is_separate_by_construction": (
            "its database name is not derivable from COGOS_DATABASE_URL, so a driver handed "
            "only the governed URL cannot reach it by any code path (22B W1-F6's rule, "
            "applied to a clone)"
        ),
    }


def _predecessor_roots() -> dict[str, Any]:
    roots = {}
    for name in PREDECESSOR_ROOTS:
        path = DATA_ROOT / name
        if not path.is_dir():
            roots[name] = {"present": False}
            continue
        value, files = fingerprint(path)
        roots[name] = {"present": True, "fingerprint": value, "files": files}
    return {
        "roots": roots,
        "why_now": (
            "so that '22E touched nothing that came before it' is a recomputed comparison at "
            "W4 rather than an assurance (22A W4-F2)"
        ),
    }


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


async def _record() -> dict[str, Any]:
    database_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    artifact_root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not database_url or not artifact_root:
        raise SystemExit("REFUSED: source .env.s22e.local first")

    invariants = _invariants()
    stores = await _stores()
    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22E-001", "S22E-002"],
        "sprint": "22E",
        "wave": "W0",
        "owner": GATE_OWNER,
        "predecessor_release": {
            **PREDECESSOR_RELEASE,
            "read_from": "git ls-remote and the GitHub API, at W0",
            "satisfied_rather_than_waived": True,
            "recheck_with": "scripts/preflight_22e.py --verify-release",
            "why_check_does_not_re_read_it": (
                "a validator that needs a network fails for reasons that are not about the "
                "record; 22C W1-F1's rule is that `--check` may not re-derive a world "
                "observation"
            ),
        },
        "invariants": invariants,
        "observations": _observations(),
        "stores": stores,
        "predecessor_roots": _predecessor_roots(),
        "active_surface": await capture(
            database_url=database_url, artifact_root=Path(artifact_root)
        ),
    }
    record["blocking_dependencies"] = [
        item
        for item in (
            None
            if stores["every_store_at_the_expected_head"]
            else {
                "gate": "store_provisioning",
                "owner": GATE_OWNER,
                "blocks": ["W1", "W2", "W3"],
                "detail": stores["stores"],
            },
        )
        if item is not None
    ]
    record["w0_may_proceed"] = not record["blocking_dependencies"]
    record["invariants_hash"] = _sha256(_canonical(invariants))
    record["recorded_at"] = PREFLIGHT_TIME
    record["integrity_content_hash"] = _sha256(
        _canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-release", action="store_true")
    arguments = parser.parse_args()

    if arguments.verify_release:
        result = verify_release_from_the_remote()
        print(json.dumps(result, indent=1, sort_keys=True))
        return 0 if result["still_agrees"] else 1

    record = asyncio.run(_record())
    if arguments.check:
        if not OUTPUT.exists():
            print(f"MISSING {OUTPUT}")
            return 1
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        moving = {"recorded_at", "integrity_content_hash", *OBSERVED_AT_W0}
        invariants_same = {k: v for k, v in stored.items() if k not in moving} == {
            k: v for k, v in record.items() if k not in moving
        }
        body = {k: v for k, v in stored.items() if k != "integrity_content_hash"}
        sealed = _sha256(_canonical(body)) == stored["integrity_content_hash"]
        print(
            json.dumps(
                {
                    "reproduced": invariants_same and sealed,
                    "invariants_recomputed": invariants_same,
                    "stored_seal_intact": sealed,
                    "recorded_not_recomputed": list(OBSERVED_AT_W0),
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if invariants_same and sealed else 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "predecessor_release_peels_to": record["predecessor_release"]["peels_to"],
                "exact_head_ci": record["predecessor_release"]["exact_head_ci_conclusion"],
                "cpu": record["invariants"]["cpu"]["model"],
                "stores_at_head": record["stores"]["every_store_at_the_expected_head"],
                "migration_head": EXPECTED_MIGRATION_HEAD,
                "surface_members": record["active_surface"]["members"],
                "surface_hash": record["active_surface"]["surface_hash"],
                "predecessor_roots": len(record["predecessor_roots"]["roots"]),
                "blocking_dependencies": [item["gate"] for item in record["blocking_dependencies"]],
                "w0_may_proceed": record["w0_may_proceed"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
