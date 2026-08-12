"""S22B-002. The declared reference host, sealed once, before any number exists.

Every latency and throughput exit in Sprint 22B is a claim about *one machine*. §1.4 says so
and §4 says it again: one host is one host. That only means something if the host is written
down before the measuring starts and can be re-read afterwards, so this record is split into
two halves that behave differently on purpose:

*Invariants* are the facts that define the host. CPU, memory, the storage device the database
actually writes to, the kernel, the PostgreSQL and pgvector versions, and the server's memory
settings. `--check` recomputes every one of them and fails on any difference. It compares by
recomputation, never against a stored literal (22A W4-F2), so a claim that the host did not
change is able to notice that it did.

*Observations* are facts about the moment — free disk, load, the container's id, the current
clock speed. They are recorded because a reader wants them and compared by nothing, because a
check that fails when a byte was written proves nothing (W2-F1/F2).

The PostgreSQL memory settings sit in the invariants deliberately, and that is the sharpest
decision in this file. They are near the packaged defaults — `shared_buffers` 128 MB and
`maintenance_work_mem` 64 MB against 46 GiB of RAM — which will cost real wall-clock on a 10^6
HNSW build. They stay exactly as they are: the sealed 10^5 envelope this sprint extends was
measured under these settings, so raising them would buy a faster build at the price of the
only comparison the sprint has. §2.3 forbids tuning a pre-registered configuration after its
first measured number exists; sealing them here makes that fence real rather than rhetorical.

    UV_CACHE_DIR=.cache/uv uv run python scripts/host_record_22b.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/host_record_22b.py --check

Read-only against the database: it runs `SELECT`s and touches no table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22b-reference-host.json"

#: The server settings that decide how a 10^6 index build and a warm probe behave. Sealed as
#: invariants: 22B measures the host it declares, and does not tune its way to an exit.
SEALED_SETTINGS = (
    "effective_cache_size",
    "maintenance_work_mem",
    "max_connections",
    "max_parallel_maintenance_workers",
    "max_parallel_workers",
    "max_parallel_workers_per_gather",
    "max_worker_processes",
    "shared_buffers",
    "work_mem",
)

DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def _psql(url: str, query: str) -> str:
    environment = dict(os.environ)
    return subprocess.run(
        ["psql", url, "-Atqc", query],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
    ).stdout.strip()


def _store_url() -> str:
    """22B's own store, not the bootstrap database.

    W0-F1: this read `COGOS_DATABASE_BOOTSTRAP_URL`, which points at `postgres`, where the
    `vector` extension is not installed — so the pgvector version every ANN number in the
    sprint depends on was sealed as `null`. The host record has to describe the database the
    measurements run against.
    """
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit(
            "COGOS_DATABASE_ADMIN_URL is required. Source .env.s22b.local first: the host "
            "record describes the store 22B measures against, not whichever server is default"
        )
    return url.replace("+asyncpg", "", 1)


def _cpu() -> dict[str, Any]:
    lscpu = dict(
        (key.strip(), value.strip())
        for key, _, value in (line.partition(":") for line in _run("lscpu").splitlines())
        if value
    )
    return {
        "model": lscpu["Model name"],
        "architecture": lscpu["Architecture"],
        "logical_cpus": int(lscpu["CPU(s)"]),
        "cores_per_socket": int(lscpu["Core(s) per socket"]),
        "sockets": int(lscpu["Socket(s)"]),
        "threads_per_core": int(lscpu["Thread(s) per core"]),
        "max_mhz": lscpu.get("CPU max MHz"),
    }


def _memory() -> dict[str, Any]:
    meminfo = dict(
        (key, value.split()[0])
        for key, _, value in (
            line.partition(":") for line in Path("/proc/meminfo").read_text().splitlines()
        )
        if value
    )
    return {"total_kib": int(meminfo["MemTotal"]), "swap_total_kib": int(meminfo["SwapTotal"])}


def _storage(path: Path) -> dict[str, Any]:
    source, fstype = _run("findmnt", "-no", "SOURCE,FSTYPE", "--target", str(path)).split()
    disk = source.rstrip("0123456789").removeprefix("/dev/").rstrip("p")
    rotational = Path(f"/sys/block/{disk}/queue/rotational")
    model = Path(f"/sys/block/{disk}/device/model")
    return {
        "path": str(path),
        "device": source,
        "filesystem": fstype,
        "disk": disk,
        "disk_model": model.read_text().strip() if model.exists() else None,
        "rotational": bool(int(rotational.read_text().strip())) if rotational.exists() else None,
    }


def _postgres(url: str) -> dict[str, Any]:
    settings = dict(
        line.split("=", 1)
        for line in _psql(
            url,
            "SELECT name || '=' || setting || ' ' || COALESCE(unit, '') FROM pg_settings "
            f"WHERE name IN ({', '.join(repr(name) for name in SEALED_SETTINGS)}) ORDER BY name",
        ).splitlines()
    )
    extensions = dict(
        line.split("=", 1)
        for line in _psql(
            url,
            "SELECT extname || '=' || extversion FROM pg_extension "
            "WHERE extname IN ('vector', 'plpgsql') ORDER BY extname",
        ).splitlines()
    )
    return {
        "server_version": _psql(url, "SHOW server_version"),
        "version_string": _psql(url, "SELECT version()"),
        "extensions": extensions,
        "settings": {name: value.strip() for name, value in settings.items()},
        "settings_are_sealed_as_invariants": (
            "shared_buffers 128 MB and maintenance_work_mem 64 MB are close to the packaged "
            "defaults and will cost wall-clock on a 10^6 HNSW build. They stay: the 10^5 "
            "envelope 22B extends was measured under them, and §2.3 forbids tuning a "
            "pre-registered configuration once a number exists. A build that is slow here is a "
            "measured property of the declared host, reported as one"
        ),
    }


def _container(url: str) -> dict[str, Any]:
    """The database runs in a container, so the image is part of the host's identity."""
    name = os.environ.get("COGOS_POSTGRES_TOOL_CONTAINER")
    if not name or not shutil.which("docker"):
        return {"name": name, "available": False}
    image, configured = _run(
        "docker", "inspect", name, "--format", "{{.Image}}|{{.Config.Image}}"
    ).split("|")
    data_directory = _psql(url, "SHOW data_directory")
    return {
        "name": name,
        "available": True,
        "image_reference": configured,
        "image_digest": image,
        "data_directory_in_container": data_directory,
    }


def _invariants(url: str) -> dict[str, Any]:
    """Everything that defines the host. `--check` recomputes every field here."""
    return {
        "cpu": _cpu(),
        "memory": _memory(),
        "kernel_release": platform.release(),
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "postgres": _postgres(url),
        "container": _container(url),
        "storage_data_root": _storage(DATA_ROOT),
        "storage_postgres_data": _storage(DATA_ROOT / "postgres/dev"),
    }


def _observations() -> dict[str, Any]:
    """Facts about the moment. Recorded for the reader, compared by nothing."""
    usage = shutil.disk_usage(DATA_ROOT)
    return {
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_root_free_bytes": usage.free,
        "data_root_total_bytes": usage.total,
        "load_average": list(os.getloadavg()),
        "why_not_invariant": (
            "free disk falls as the sprint writes a million rows and the load average moves "
            "every second. A same-host check that failed on either would fail because the "
            "sprint ran, which proves nothing (W2-F1/F2)"
        ),
    }


def _record() -> dict[str, Any]:
    url = _store_url()
    invariants = _invariants(url)
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22B",
        "wave": "W0",
        "items": ["S22B-002"],
        "host_id": "cogos-reference-host-1",
        "role": (
            "the declared reference host of §1.4: the CPU-first, GPU-free developer machine "
            "the D1 gate already declared. Every 22B latency and throughput number is a claim "
            "about this machine and binds this record's hash. A number measured anywhere else "
            "is reported with its own host record and closes nothing"
        ),
        "invariants": invariants,
        "observations": _observations(),
        "gpu_free": (
            "no accelerator is declared or used. §2.3 puts GPU acceleration out of scope, so "
            "the envelope is a CPU envelope by construction rather than by omission"
        ),
        "capacity_headroom_note": (
            "a 10^6 x 768 corpus is roughly 3 GB of vectors before an index, and the sealed "
            "10^5 index was 410 MB. W1 seals the real numbers; this is the sanity floor a wave "
            "would trip on before it started"
        ),
    }
    record["invariants_hash"] = _sha256(_canonical(invariants))
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def _write() -> None:
    record = _record()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "host_id": record["host_id"],
                "cpu": record["invariants"]["cpu"]["model"],
                "logical_cpus": record["invariants"]["cpu"]["logical_cpus"],
                "memory_total_kib": record["invariants"]["memory"]["total_kib"],
                "postgres": record["invariants"]["postgres"]["server_version"],
                "pgvector": record["invariants"]["postgres"]["extensions"].get("vector"),
                "storage": record["invariants"]["storage_postgres_data"]["device"],
                "invariants_hash": record["invariants_hash"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check() -> None:
    """Is this still the declared host? Recomputed, never read back as a literal (W4-F2)."""
    sealed = json.loads(OUTPUT.read_text(encoding="utf-8"))
    body = {key: value for key, value in sealed.items() if key != "integrity_content_hash"}
    if _sha256(_canonical(body)) != sealed["integrity_content_hash"]:
        raise SystemExit("the reference-host record's seal does not match its content")

    measured = _invariants(_store_url())
    differences = sorted(
        key
        for key in set(measured) | set(sealed["invariants"])
        if measured.get(key) != sealed["invariants"].get(key)
    )
    if differences:
        raise SystemExit(
            "the host has drifted from the record every 22B number binds: "
            + ", ".join(differences)
            + ". A measurement taken here is a measurement on a different machine; re-seal "
            "under a new host id and say so, never edit this record"
        )
    if _sha256(_canonical(measured)) != sealed["invariants_hash"]:
        raise SystemExit("the invariants hash does not reproduce")

    print(
        json.dumps(
            {
                "host_id": sealed["host_id"],
                "invariants_verified": len(measured),
                "invariants_hash": sealed["invariants_hash"],
                "same_host": True,
                "recomputed": True,
            },
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.check:
        _check()
    else:
        _write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
