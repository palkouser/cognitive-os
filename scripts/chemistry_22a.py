#!/usr/bin/env python3
"""S22A-040 through S22A-045. The W3 wave record: the second domain, and the fences.

W2 proved one domain could arrive as data. W3 asks the questions only a *second* one can
answer — whether the door generalises, whether two pilots can share a view of the same
released domain without colliding, and whether the `DomainKind` coupling stays flat when the
registry has grown twice. It also owes §3.5 a rejection suite and §3.4 an honest exclusion.

Six claims, recomputed here rather than restated, in the order they would fail:

*The released four still cannot tell*, now measured with **both** pilots registered.

*The second pilot resolves through the released table*, and its problem types resolve to it.

*The coupling did not grow.* Two domains, zero `DomainKind` branches, which is §3.5's silo
regression closed rather than promised.

*The rejection suite refuses at the layer that owns each case*, and the layer is part of the
claim: a case that moved to a later layer than this record names is a regression.

*The chain ran in separate processes.* The five phase records are read and bound by hash.

*What was left out is on the record.* §3.4's excluded candidates, with reasons.

    UV_CACHE_DIR=.cache/uv uv run python scripts/chemistry_22a.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/chemistry_22a.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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
from cognitive_os.domains.chemistry import CHEMISTRY_KERNELS, EXCLUDED_CANDIDATES  # noqa: E402
from cognitive_os.domains.mechanics import MECHANICS_KERNELS  # noqa: E402

EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
PACKAGES = REPO / "docs/sprints/sprint-22/packages"
OUTPUT = EVIDENCE / "sprint-22a-w3-pilot.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22a-pre-registration.json"
W2_RECORD = EVIDENCE / "sprint-22a-w2-pilot.json"

PILOT_DOMAIN_ID = "science.chemistry"
PHASES = ("register", "rebuild", "solve", "views", "rejections")

#: The pilots, in the order they were registered. Both are admitted before anything is
#: measured, because the interesting state is the one no earlier wave could produce.
PILOT_PACKAGES = (
    (PACKAGES / "engineering.mechanics.v1.json", MECHANICS_KERNELS),
    (PACKAGES / "science.chemistry.v1.json", CHEMISTRY_KERNELS),
)

#: The replays run for this wave. Recorded rather than recomputed, for the reason W1 gave:
#: a replay is a wall-clock run against manifests, and re-running one inside a `--check`
#: would make the check fail for want of a database rather than for a reason.
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


def _w2() -> Any:
    """W2's sealer, imported rather than copied: one implementation of the compat claim."""
    spec = importlib.util.spec_from_file_location("pilot_22a", REPO / "scripts/pilot_22a.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _with_both_pilots_registered() -> tuple[Any, ...]:
    """Admit both pilots into this process, so every claim below is measured with both there."""
    descriptors = []
    for package, kernels in PILOT_PACKAGES:
        descriptor = validate_domain_package(package.read_bytes())
        identity = (descriptor.domain_id, descriptor.revision)
        if identity not in registry.registered_descriptor_domains():
            registry.register_descriptor_domain(descriptor, kernels)
        descriptors.append(descriptor)
    return tuple(descriptors)


def _pilots(descriptors: tuple[Any, ...]) -> dict[str, Any]:
    catalogue = (*descriptors, *released_domain_descriptors())
    views = concept_views(catalogue)
    owners = concept_owners(catalogue)
    physics = {view.concept_id: view for view in views["physics"]}
    return {
        "registered": {
            item.domain_id: {
                "revision": item.revision,
                "lifecycle": item.lifecycle.value,
                "descriptor_content_hash": item.content_hash,
                "problem_types": list(item.problem_types),
                "resolves_to_itself": all(
                    registry.resolve(name).domain_id == item.domain_id
                    for name in item.problem_types
                ),
                "verifier_capabilities": list(item.capabilities.verifier_capabilities),
            }
            for item in descriptors
        },
        "pilot_count": len(descriptors),
        "problem_types_total": sum(len(item.problem_types) for item in descriptors),
        "shared_into_physics": {
            concept_id: view.owner_domain_id for concept_id, view in sorted(physics.items())
        },
        "physics_sees_both_pilots": len({view.owner_domain_id for view in physics.values()}) == 2,
        "physics_owns_none_of_them": all(owners[concept_id] != "physics" for concept_id in physics),
        "the_new_capability": {
            "name": "chemistry.stoichiometry",
            "why_it_is_not_a_borrowed_name": (
                "the check counts atoms and compares integers; it is a deterministic kernel, "
                "not a model, a lookup or a heuristic (§3.4)"
            ),
        },
        "excluded_candidates": EXCLUDED_CANDIDATES,
        "excluded_because": (
            "§3.4: a problem type that cannot be deterministically verified is out of the "
            "pilot and recorded as such, rather than admitted with a verifier that is a name"
        ),
    }


def _rejection_suite() -> dict[str, Any]:
    """The suite as sealed by the `rejections` phase, summarised by the layer that refused."""
    body = _load(EVIDENCE / "sprint-22a-w3-pilot-rejections.json")
    by_layer: dict[str, list[str]] = {}
    for case in body["cases"]:
        by_layer.setdefault(case["layer"], []).append(case["case"])
    return {
        "case_count": body["case_count"],
        "by_layer": {layer: sorted(names) for layer, names in sorted(by_layer.items())},
        "every_case_refused": body["every_case_refused"],
        "nothing_registered_halfway": body["nothing_registered_halfway"],
        "sealed_cases_executed": body["sealed_cases_executed"],
        "the_layer_is_part_of_the_claim": (
            "a package the boundary refuses never reaches a store; one the registry door "
            "refuses never reaches a solver; one the catalogue refuses never reaches a view. "
            "A case that moves to a later layer than this record names is a regression"
        ),
        "the_three_this_sprint_owed": {
            "released_id_at_a_new_revision": "registry door",
            "capabilities_naming_a_verifier_that_never_runs": "resolution",
            "shared_into_a_domain_that_never_declared_it_back": "catalogue",
        },
    }


def _silo_regression(coupling: dict[str, Any]) -> dict[str, Any]:
    w2 = _load(W2_RECORD)["enum_coupling"]
    return {
        "at_w0": coupling["at_w0"],
        "at_w1": coupling["at_w1"],
        "at_w2": w2["at_w2"],
        "at_w3": coupling["at_w2"],
        "measured_with_both_pilots_registered": True,
        "added_by_both_pilots": coupling["at_w2"]["references"] - w2["at_w2"]["references"],
        "grew": coupling["grew_since_w0"],
        "reading": (
            "§3.5's silo regression, closed: registering two domains added zero DomainKind "
            "references, because a descriptor-registered domain has no enum member to branch "
            "on. The count is a ceiling the sprint may drive down and may never push up"
        ),
        "read_from_w2": W2_RECORD.name,
        "read_from_w2_sha256": _sha256(W2_RECORD.read_bytes()),
    }


def _chain() -> dict[str, Any]:
    phases = {}
    for phase in PHASES:
        path = EVIDENCE / f"sprint-22a-w3-pilot-{phase}.json"
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
                    "physics_sees_two_pilots",
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
    }


def _write() -> None:
    descriptors = _with_both_pilots_registered()
    w2 = _w2()
    compatibility = w2._compatibility(descriptors[-1])
    coupling = w2._coupling()
    pilots = _pilots(descriptors)
    suite = _rejection_suite()
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W3",
        "items": ["S22A-040", "S22A-041", "S22A-042", "S22A-043", "S22A-044", "S22A-045"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "pilots": pilots,
        "backward_compatibility": compatibility,
        "silo_regression": _silo_regression(coupling),
        "rejection_suite": suite,
        "boundaries": {
            "core_controller_changed": False,
            "storage_schema_changed": False,
            "migration_head": "0015",
            "migrations_allocated_by_w3": 0,
            "new_tables": 0,
            "new_enum_members": 0,
            "not_reached": _load(W2_RECORD)["boundaries"]["not_reached"],
        },
        "chain": _chain(),
        "replays": REPLAYS,
        "replay_cases": sum(int(item["cases"]) for item in REPLAYS.values()),
        "every_released_claim_holds": bool(
            compatibility["released_snapshot_unchanged"]
            and all(item["unchanged"] for item in compatibility["descriptors"].values())
            and not coupling["grew_since_w0"]
            and suite["every_case_refused"]
        ),
        "what_w3_did_not_do": [
            "add a migration, a table, an enum member or a controller branch",
            "give either pilot a persisted-run path — W2-A1's stop still stands",
            "promote either pilot beyond `lifecycle: pilot`",
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
                "pilots": sorted(pilots["registered"]),
                "problem_types": pilots["problem_types_total"],
                "released_snapshot_unchanged": compatibility["released_snapshot_unchanged"],
                "compat_hashes_unchanged": sum(
                    1 for item in compatibility["descriptors"].values() if item["unchanged"]
                ),
                "coupling": f"{coupling['at_w0']['references']} -> "
                f"{coupling['at_w2']['references']}",
                "rejection_cases": suite["case_count"],
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
        raise SystemExit("the W3 record does not carry the published pre-registration's hash")
    if record["silo_regression"]["read_from_w2_sha256"] != _sha256(W2_RECORD.read_bytes()):
        raise SystemExit("the W2 record this wave measures against has changed")

    descriptors = _with_both_pilots_registered()
    w2 = _w2()
    for descriptor in descriptors:
        stated = record["pilots"]["registered"][descriptor.domain_id]
        if stated["descriptor_content_hash"] != descriptor.content_hash:
            raise SystemExit(
                f"the committed {descriptor.domain_id} package no longer produces its descriptor"
            )
    compatibility = w2._compatibility(descriptors[-1])
    if not compatibility["released_snapshot_unchanged"]:
        raise SystemExit("the released snapshot moved once both pilots were registered")
    for domain_id, item in compatibility["descriptors"].items():
        if not item["unchanged"]:
            raise SystemExit(f"released domain {domain_id} no longer derives its sealed hash")
    if w2._coupling()["grew_since_w0"]:
        raise SystemExit("the DomainKind coupling has grown past its sealed ceiling")
    for phase, item in record["chain"]["phases"].items():
        path = EVIDENCE / item["record"]
        if _sha256(path.read_bytes()) != item["sha256"]:
            raise SystemExit(f"the {phase} phase record changed after it was bound")

    print(
        json.dumps(
            {
                "checked": OUTPUT.name,
                "released_snapshot_unchanged_with_both_pilots": True,
                "compat_hashes_verified": len(compatibility["descriptors"]),
                "phase_records_verified": len(record["chain"]["phases"]),
                "rejection_cases": record["rejection_suite"]["case_count"],
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
