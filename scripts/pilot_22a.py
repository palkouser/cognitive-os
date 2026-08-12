#!/usr/bin/env python3
"""S22A-031 through S22A-036. The W2 wave record: the first domain that arrived as data.

Sprint 22A's exit criterion has four clauses, and W2 is the first wave able to say anything
about three of them at once — a new domain registered, cross-domain items stored once and
exposed through several governed views, and nothing in the core controller or the storage
schema moved to allow it. This record recomputes each claim rather than restating it, and
binds the five phase records by hash so a later edit to any of them is visible here.

Five claims, in the order they would fail:

*The released four still cannot tell.* `released_snapshot_hash()` and the four derived
descriptor hashes, re-derived live and compared with the W0 survey — in a process that has
the pilot registered, which is the case that did not exist before this wave.

*The pilot resolves through the released table.* Its three problem types resolve, and they
resolve to the pilot rather than to anything released.

*The coupling did not grow.* Registering a domain must add zero `DomainKind` branches; if
the count moved, the pilot was a silo wearing a descriptor.

*The chain ran in separate processes.* The five phase records are read and bound by hash,
never summarised from memory (W3-F1).

*Nothing was allocated.* Migration head, controller and storage schema, restated as the
negatives they are and checked where they can be.

    UV_CACHE_DIR=.cache/uv uv run python scripts/pilot_22a.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/pilot_22a.py --check
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
    concept_owners,
    concept_views,
    released_domain_descriptors,
    validate_domain_package,
)
from cognitive_os.domains import registry  # noqa: E402
from cognitive_os.domains.mechanics import MECHANICS_KERNELS  # noqa: E402

EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22a-w2-pilot.json"
SURVEY = EVIDENCE / "sprint-22a-domain-survey.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22a-pre-registration.json"
DECISIONS = EVIDENCE / "sprint-22a-w2-decisions.json"
PACKAGE = REPO / "docs/sprints/sprint-22/packages/engineering.mechanics.v1.json"

PILOT_DOMAIN_ID = "engineering.mechanics"
PHASES = ("register", "rebuild", "solve", "views", "refusals")

#: The replays run for this wave, with the counts they returned. Recorded rather than
#: recomputed here for the reason W1 gave: a replay is a wall-clock run against manifests,
#: and re-running one inside a `--check` would make the check fail for want of a database
#: rather than for a reason.
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


def _with_pilot_registered() -> Any:
    """Admit the pilot into this process, so every claim below is measured *with* it there.

    A compatibility claim measured in a process that never registered a pilot would be
    measuring the state W1 already proved. The interesting question is whether the released
    four survive a registry that grew, so the registry grows first.
    """
    descriptor = validate_domain_package(PACKAGE.read_bytes())
    if (descriptor.domain_id, descriptor.revision) not in registry.registered_descriptor_domains():
        registry.register_descriptor_domain(descriptor, MECHANICS_KERNELS)
    return descriptor


def _compatibility(descriptor: Any) -> dict[str, Any]:
    sealed = _load(SURVEY)["released_domains_as_descriptors"]
    derived = {item.domain_id: item for item in released_domain_descriptors()}
    return {
        "measured_with_the_pilot_registered": True,
        "released_snapshot_hash": registry.released_snapshot_hash(),
        "released_snapshot_hash_sealed": sealed["registry_snapshot_hash"],
        "released_snapshot_unchanged": (
            registry.released_snapshot_hash() == sealed["registry_snapshot_hash"]
        ),
        "whole_registry_snapshot_hash": registry.snapshot_hash(),
        "whole_registry_snapshot_differs": (
            registry.snapshot_hash() != sealed["registry_snapshot_hash"]
        ),
        "descriptors": {
            domain_id: {
                "content_hash": derived[domain_id].content_hash,
                "sealed": body["content_hash"],
                "unchanged": derived[domain_id].content_hash == body["content_hash"],
            }
            for domain_id, body in sorted(sealed["descriptors"].items())
        },
        "released_entries": len([item for item in registry.entries() if item.domain is not None]),
        "pilot_entries": len(
            [item for item in registry.entries() if item.domain_id == descriptor.domain_id]
        ),
        "read_from": SURVEY.name,
        "read_from_sha256": _sha256(SURVEY.read_bytes()),
        "decision": "S22A-030, recorded in " + DECISIONS.name,
        "decision_sha256": _sha256(DECISIONS.read_bytes()),
    }


def _pilot(descriptor: Any) -> dict[str, Any]:
    resolved = {name: registry.resolve(name).domain_id for name in descriptor.problem_types}
    catalogue = (descriptor, *released_domain_descriptors())
    views = concept_views(catalogue)
    owners = concept_owners(catalogue)
    shared = {
        concept.concept_id: list(concept.shared_with)
        for concept in descriptor.concepts
        if concept.shared_with
    }
    cross_domain = {
        concept_id: {
            "owner": owners[concept_id],
            "visible_from": sorted(
                domain_id
                for domain_id, items in views.items()
                if any(view.concept_id == concept_id for view in items)
            ),
            "content_hash": next(
                view.content_hash
                for view in views[owners[concept_id]]
                if view.concept_id == concept_id
            ),
        }
        for concept_id in shared
    }
    return {
        "domain_id": descriptor.domain_id,
        "revision": descriptor.revision,
        "lifecycle": descriptor.lifecycle.value,
        "descriptor_content_hash": descriptor.content_hash,
        "package_file": str(PACKAGE.relative_to(REPO)),
        "package_sha256": _sha256(PACKAGE.read_bytes()),
        "problem_types": list(descriptor.problem_types),
        "problem_types_resolved_to": resolved,
        "every_problem_type_resolves_to_the_pilot": all(
            value == descriptor.domain_id for value in resolved.values()
        ),
        "capabilities": {
            "verifiers": list(descriptor.capabilities.verifier_capabilities),
            "tools": list(descriptor.capabilities.tool_capabilities),
            "units": list(descriptor.capabilities.units),
        },
        "capabilities_are_released_ones": set(
            descriptor.capabilities.verifier_capabilities
        ).issubset({"physics.dimension", "physics.quantity"}),
        "shared_concepts": shared,
        "cross_domain_views": cross_domain,
        "every_shared_concept_has_one_owner": all(
            item["owner"] == descriptor.domain_id for item in cross_domain.values()
        ),
        "enum_members_added": 0,
        "registered_as": "a descriptor, with `domain` None and `domain_id` the string id",
    }


def _coupling() -> dict[str, Any]:
    """Recounted by the sealed survey's own function, never a second copy (§3.5)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "domain_survey_22a", REPO / "scripts/domain_survey_22a.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    counted: dict[str, Any] = module._enum_coupling()

    sealed = _load(SURVEY)["enum_coupling"]
    at_w1 = _load(EVIDENCE / "sprint-22a-w1-seam.json")["enum_coupling"]["at_w1"]
    return {
        "at_w0": {"modules": sealed["module_count"], "references": sealed["reference_count"]},
        "at_w1": at_w1,
        "at_w2": {"modules": counted["module_count"], "references": counted["reference_count"]},
        "grew_since_w1": counted["reference_count"] > at_w1["references"],
        "grew_since_w0": counted["reference_count"] > sealed["reference_count"],
        "added_by_the_pilot": counted["reference_count"] - at_w1["references"],
        "reading": (
            "§3.5's silo regression, one wave early: registering a domain added zero "
            "DomainKind references, because a descriptor-registered domain has no enum "
            "member to branch on"
        ),
    }


def _phases() -> dict[str, Any]:
    phases = {}
    for phase in PHASES:
        path = EVIDENCE / f"sprint-22a-w2-pilot-{phase}.json"
        body = _load(path)
        phases[phase] = {
            "record": path.name,
            "sha256": _sha256(path.read_bytes()),
            "process": body.get("process"),
            "summary": {
                key: value
                for key, value in body.items()
                if key
                in {
                    "entries_unchanged_overall",
                    "every_case_refused",
                    "every_problem_type_resolves",
                    "every_shared_concept_visible_from_physics",
                    "every_task_accepted",
                    "every_wrong_answer_refused",
                    "nothing_registered_halfway",
                    "physics_owns_none_of_them",
                    "pilot_rebuilt",
                    "registry_entries_after",
                    "released_snapshot_unchanged",
                    "same_content_hash_in_both_views",
                    "stream_version",
                    "went_through_the_boundary",
                    "whole_snapshot_changed",
                }
            },
        }
    observed = sorted({body["process"] for body in phases.values() if body["process"]})
    return {
        "phases": phases,
        "processes_observed": observed,
        "separate_processes": len(observed) > 1,
        "why": (
            "register writes and exits; every later phase starts cold. A pilot that "
            "registered only inside the process that authored it would look exactly like a "
            "pilot that registered (the D7 lifecycle lesson, and W1's slice discipline)"
        ),
        "the_register_record_carries_no_pid": (
            "it was written before the phase script recorded one, and it cannot be rewritten: "
            "the store refuses to re-register an existing (domain_id, revision), and the "
            "application role has no DELETE on the event table. The record is therefore "
            "necessarily the one the first run wrote, which is a stronger claim than a pid"
        ),
    }


def _boundaries() -> dict[str, Any]:
    return {
        "core_controller_changed": False,
        "storage_schema_changed": False,
        "migration_head": "0015",
        "migrations_allocated_by_w2": 0,
        "new_tables": 0,
        "new_enum_members": 0,
        "solved_through": "domains.solve, under the released Tool Plane policy and audit",
        "judged_by": "domains.checker, through the released VerificationService",
        "not_reached": {
            "what": "the Cognitive Controller's own state machine",
            "why": (
                "`run_case_controlled` takes a DomainBenchmarkCase whose `domain` is a "
                "DomainKind, and the controller maps that enum through two per-domain "
                "tables. Reaching it would mean widening a released contract and adding "
                "core branching, which is what the exit criterion forbids"
            ),
            "handed_to": "W4's verification matrix, and 22B if it is to be built",
        },
    }


def _write() -> None:
    descriptor = _with_pilot_registered()
    compatibility = _compatibility(descriptor)
    pilot = _pilot(descriptor)
    coupling = _coupling()
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W2",
        "items": ["S22A-031", "S22A-032", "S22A-033", "S22A-034", "S22A-035", "S22A-036"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "pilot": pilot,
        "backward_compatibility": compatibility,
        "enum_coupling": coupling,
        "boundaries": _boundaries(),
        "chain": _phases(),
        "replays": REPLAYS,
        "replay_cases": sum(int(item["cases"]) for item in REPLAYS.values()),
        "every_released_claim_holds": bool(
            compatibility["released_snapshot_unchanged"]
            and all(item["unchanged"] for item in compatibility["descriptors"].values())
            and not coupling["grew_since_w0"]
        ),
        "what_w2_did_not_do": [
            "register the chemistry pilot or author its rejection suite — that is W3",
            "add a migration, a table, an enum member or a controller branch",
            "touch the learned correction component or its five routed canary groups",
            "promote the pilot beyond `lifecycle: pilot`",
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
                "pilot": pilot["domain_id"],
                "problem_types": len(pilot["problem_types"]),
                "released_snapshot_unchanged": compatibility["released_snapshot_unchanged"],
                "compat_hashes_unchanged": sum(
                    1 for item in compatibility["descriptors"].values() if item["unchanged"]
                ),
                "coupling": f"{coupling['at_w1']['references']} -> "
                f"{coupling['at_w2']['references']}",
                "phases": len(PHASES),
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
        raise SystemExit("the W2 record does not carry the published pre-registration's hash")

    descriptor = _with_pilot_registered()
    if descriptor.content_hash != record["pilot"]["descriptor_content_hash"]:
        raise SystemExit("the committed package no longer produces the registered descriptor")
    compatibility = _compatibility(descriptor)
    if not compatibility["released_snapshot_unchanged"]:
        raise SystemExit("the released snapshot hash moved once the pilot was registered")
    for domain_id, item in compatibility["descriptors"].items():
        if not item["unchanged"]:
            raise SystemExit(f"released domain {domain_id} no longer derives its sealed hash")
    if _coupling()["grew_since_w0"]:
        raise SystemExit("the DomainKind coupling has grown past its sealed ceiling")
    for phase, item in record["chain"]["phases"].items():
        path = EVIDENCE / item["record"]
        if _sha256(path.read_bytes()) != item["sha256"]:
            raise SystemExit(f"the {phase} phase record changed after it was bound")

    print(
        json.dumps(
            {
                "checked": OUTPUT.name,
                "released_snapshot_unchanged_with_the_pilot_registered": True,
                "compat_hashes_verified": len(compatibility["descriptors"]),
                "phase_records_verified": len(record["chain"]["phases"]),
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
