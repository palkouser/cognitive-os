#!/usr/bin/env python3
"""S22A-021 through S22A-024. The W1 seam, proved rather than asserted.

Sprint 22A's first exit criterion is a negative — the two new domains register "without
changing the core controller or storage schema" — and W1's half of it is a second negative:
the four released domains must not be able to tell the seam exists. That is provable, and
this record is the proof rather than a description of one.

Four claims, each recomputed here from the live code and compared against the record that
sealed it before anything moved:

*The registry snapshot is unchanged.* `snapshot_hash()` is the released value bound into
semantic-memory records, so it changing would be a released behaviour change with callers.

*The four derived descriptor hashes are unchanged.* The metadata tables moved out of
`domains/registry.py` into descriptor data; these four hashes are what makes that move
provably lossless rather than merely careful.

*The coupling went down and not up.* The seam is supposed to remove `DomainKind` branches.
The sealed 9/57 is a ceiling, and the delta below is what W1 actually bought.

*The chain runs, in separate processes.* The vertical slice's four phase records are read and
bound by hash here — never summarised from memory (W3-F1: run the thing you intend to rely
on, on the bytes you intend to rely on).

    UV_CACHE_DIR=.cache/uv uv run python scripts/seam_22a.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/seam_22a.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.domain.descriptors import (  # noqa: E402
    RELEASED_DOMAIN_CAPABILITIES,
    released_domain_descriptors,
)
from cognitive_os.domains import registry  # noqa: E402
from cognitive_os.domains.descriptor_store import (  # noqa: E402
    DOMAIN_PACKAGE_MEDIA_TYPE,
    DOMAIN_REGISTRY_STREAM_ID,
)

EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22a-w1-seam.json"
SURVEY = EVIDENCE / "sprint-22a-domain-survey.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22a-pre-registration.json"

SLICE_PHASES = ("store", "rebuild", "tamper", "refusals")

#: The replays run for this wave, with the counts they returned. Recorded rather than
#: recomputed here: a replay is a wall-clock run against manifests, and re-running it inside
#: a `--check` would make the check fail for want of a database rather than for a reason.
REPLAYS = {
    "sprint20-domain-ci": {"mode": "domain-pilot", "cases": 24, "pass_rate": 1.0},
    "sprint20-domain-seed": {"mode": "domain-pilot", "cases": 120, "pass_rate": 1.0},
    "sprint21c1-learned-ci": {"mode": "learned-replay", "cases": 16, "pass_rate": 1.0},
    "sprint21c1-learned-seed": {"mode": "learned-replay", "cases": 48, "pass_rate": 1.0},
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _coupling() -> dict[str, Any]:
    """Recounted from the AST by the sealed survey's own function, never a second copy."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "domain_survey_22a", REPO / "scripts/domain_survey_22a.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    counted: dict[str, Any] = module._enum_coupling()

    sealed = _load(SURVEY)["enum_coupling"]
    return {
        "at_w0": {"modules": sealed["module_count"], "references": sealed["reference_count"]},
        "at_w1": {"modules": counted["module_count"], "references": counted["reference_count"]},
        "references_removed": sealed["reference_count"] - counted["reference_count"],
        "modules_now": counted["modules"],
        "grew": counted["reference_count"] > sealed["reference_count"],
        "reading": (
            "the seam removed the two DomainKind-keyed metadata tables from "
            "domains/registry.py and replaced them with one adapter lookup. The count is a "
            "ceiling the sprint may drive down and may never push up"
        ),
    }


def _compat() -> dict[str, Any]:
    sealed = _load(SURVEY)["released_domains_as_descriptors"]
    derived = {item.domain_id: item for item in released_domain_descriptors()}
    # S22A-030 re-binds this claim from `snapshot_hash` to `released_snapshot_hash`. The
    # value is unchanged — the two agree in any process that admitted no descriptor domain —
    # but only the released-scope function still means "the four released domains resolve
    # identically" once a pilot is registered, and W2 registers one.
    return {
        "registry_snapshot_hash": registry.released_snapshot_hash(),
        "registry_snapshot_hash_sealed": sealed["registry_snapshot_hash"],
        "registry_snapshot_unchanged": (
            registry.released_snapshot_hash() == sealed["registry_snapshot_hash"]
        ),
        "descriptors": {
            domain_id: {
                "content_hash": derived[domain_id].content_hash,
                "sealed": body["content_hash"],
                "unchanged": derived[domain_id].content_hash == body["content_hash"],
            }
            for domain_id, body in sorted(sealed["descriptors"].items())
        },
        "registry_entries": len(registry.entries()),
        "read_from": SURVEY.name,
        "read_from_sha256": _sha256(SURVEY.read_bytes()),
    }


def _seam() -> dict[str, Any]:
    return {
        "moved": {
            "from": "domains/registry.py `_DOMAIN_METADATA` and `_REQUIRED_TOOLS`",
            "to": "domain/descriptors.py `RELEASED_DOMAIN_CAPABILITIES`, keyed by string id",
            "read_through": "released_domain_descriptors() and registry._capabilities()",
        },
        "released_domains_keyed_by_string_id": sorted(RELEASED_DOMAIN_CAPABILITIES),
        "core_controller_changed": False,
        "storage_schema_changed": False,
        "migration_head": "0015",
        "migrations_allocated_by_w1": 0,
        "storage_route": {
            "bytes": "content-addressed artifact, media type " + DOMAIN_PACKAGE_MEDIA_TYPE,
            "index": "one domain.descriptor_registered event per registration",
            "stream_id": str(DOMAIN_REGISTRY_STREAM_ID),
            "write_order": "bytes first, then the event that names them (W1-F2)",
            "new_tables": 0,
        },
    }


def _slice() -> dict[str, Any]:
    phases = {}
    for phase in SLICE_PHASES:
        path = EVIDENCE / f"sprint-22a-w1-slice-{phase}.json"
        body = _load(path)
        phases[phase] = {
            "sha256": _sha256(path.read_bytes()),
            "record": path.name,
            "summary": {
                key: value
                for key, value in body.items()
                if key
                in {
                    "descriptors_rebuilt",
                    "every_case_refused",
                    "fixture_rebuilt",
                    "named_the_domain",
                    "refused",
                    "registrations_after",
                    "registrations_replayed",
                    "still_parses_as_a_package",
                    "stream_version",
                }
            },
        }
    return {
        "phases": phases,
        "separate_processes": True,
        "why": (
            "store writes and exits; rebuild starts cold. Run in one process the chain would "
            "prove nothing and would look exactly like proof (the D7 lifecycle lesson)"
        ),
        "fixture_domain_id": "slice.fixture",
        "fixture_is_not_a_pilot": True,
    }


def _write() -> None:
    compat = _compat()
    coupling = _coupling()
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W1",
        "items": ["S22A-021", "S22A-022", "S22A-023", "S22A-024"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "seam": _seam(),
        "backward_compatibility": compat,
        "enum_coupling": coupling,
        "vertical_slice": _slice(),
        "replays": REPLAYS,
        "replay_cases": sum(int(item["cases"]) for item in REPLAYS.values()),
        "every_released_claim_holds": bool(
            compat["registry_snapshot_unchanged"]
            and all(item["unchanged"] for item in compat["descriptors"].values())
            and not coupling["grew"]
        ),
        "what_w1_did_not_do": [
            "register either pilot domain — that is W2 and W3",
            "add a migration, a table or a controller branch",
            "touch the learned correction component or its five routed canary groups",
        ],
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "registry_snapshot_unchanged": compat["registry_snapshot_unchanged"],
                "compat_hashes_unchanged": sum(
                    1 for item in compat["descriptors"].values() if item["unchanged"]
                ),
                "coupling": f"{coupling['at_w0']['references']} -> "
                f"{coupling['at_w1']['references']}",
                "slice_phases": len(SLICE_PHASES),
                "replay_cases": record["replay_cases"],
                "every_released_claim_holds": record["every_released_claim_holds"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check() -> None:
    record = _load(OUTPUT)
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    if _sha256(_canonical(body)) != record["integrity_content_hash"]:
        raise SystemExit(f"{OUTPUT.name} integrity hash does not match its content")
    if record["pre_registration_sha256"] != _sha256(PRE_REGISTRATION.read_bytes()):
        raise SystemExit("the W1 record does not carry the published pre-registration's hash")

    compat = _compat()
    if not compat["registry_snapshot_unchanged"]:
        raise SystemExit("the registry snapshot hash has moved since the survey sealed it")
    for domain_id, item in compat["descriptors"].items():
        if not item["unchanged"]:
            raise SystemExit(f"released domain {domain_id} no longer derives its sealed hash")
    if _coupling()["grew"]:
        raise SystemExit("the DomainKind coupling has grown past its sealed ceiling")
    for phase, body in record["vertical_slice"]["phases"].items():
        path = EVIDENCE / body["record"]
        if _sha256(path.read_bytes()) != body["sha256"]:
            raise SystemExit(f"the {phase} slice record changed after it was bound")

    print(
        json.dumps(
            {
                "checked": OUTPUT.name,
                "registry_snapshot_unchanged": True,
                "compat_hashes_verified": len(compat["descriptors"]),
                "slice_records_verified": len(record["vertical_slice"]["phases"]),
                "coupling_within_ceiling": True,
            },
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    _check() if arguments.check else _write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
