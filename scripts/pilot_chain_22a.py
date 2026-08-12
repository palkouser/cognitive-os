#!/usr/bin/env python3
"""The pilot chain: package bytes to a judged answer, one pilot at a time.

Written for the mechanics pilot in W2 (S22A-031…035, as `mechanics_pilot_22a.py`) and
generalised here for the chemistry pilot in W3 (S22A-040…044). The chain is the one W1's
slice proved, continued past the point where the slice stopped:

    committed package bytes → fail-closed boundary → artifact + event
        → **a different process** → rebuild → admitted to the problem-type registry
        → solved by the released Tool Plane tool → judged by the released verifier

**Separate processes, again and for the same reason.** `register` writes and exits; every
later phase starts cold, knowing nothing but the database and the artifact root. A pilot that
"registered" only inside the process that authored it would look exactly like a pilot that
registered.

    COGOS_POSTGRES_ENV_FILE=$PWD/.env.s22a.local \
        uv run python scripts/pilot_chain_22a.py register --pilot chemistry
    ... and likewise for the rebuild, solve, views and rejections phases, each in its own
    process and in that order.

`register`, `rebuild` and `solve` act on the pilot `--pilot` names. `views` and `rejections`
admit **every** pilot the store holds, because both are questions about the catalogue rather
than about one package.

The packages are committed files, not literals in this script. A descriptor package is bytes
that arrive from outside; generating them here would test a serialiser rather than a door.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.domain.descriptors import (  # noqa: E402
    DomainDescriptorV1,
    DomainPackageError,
    concept_owners,
    concept_views,
    released_domain_descriptors,
    validate_domain_package,
)
from cognitive_os.domains import chemistry, mechanics, registry  # noqa: E402
from cognitive_os.domains.descriptor_runner import run_descriptor_case  # noqa: E402
from cognitive_os.domains.descriptor_store import (  # noqa: E402
    DOMAIN_PACKAGE_MEDIA_TYPE,
    DOMAIN_REGISTRY_STREAM_ID,
    load_registrations,
    rebuild_descriptors,
    register_domain_package,
)
from cognitive_os.events.catalog import build_default_event_catalog  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import (  # noqa: E402
    create_postgres_engine,
    dispose_postgres_engine,
)
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402

PACKAGES = REPO / "docs/sprints/sprint-22/packages"

#: The sealed released snapshot: what W0 froze as the backward-compatibility contract, and
#: what S22A-030 re-binds to `released_snapshot_hash()`. No registration may move it.
SEALED_RELEASED_SNAPSHOT = "00187f2bc6e0015529de8388ea33a1e6287939ca4d393875400bc68320997119"

#: Each pilot's package, kernels and tasks. Every task carries a wrong answer that must be
#: refused, and the wrong answers are not noise: each is the specific mistake its checker's
#: independent route exists to catch, so a checker that quietly agreed with its solver fails
#: here rather than in a later sprint.
PILOTS: dict[str, dict[str, Any]] = {
    "mechanics": {
        "package": PACKAGES / "engineering.mechanics.v1.json",
        "domain_id": "engineering.mechanics",
        "kernels": mechanics.MECHANICS_KERNELS,
        "wave": "w2",
        "reason": "the mechanics pilot, the first domain registered from data",
        "tasks": {
            mechanics.STATICS_EQUILIBRIUM: {
                "statement": (
                    "Three cables and a load meet at a joint; is the joint in equilibrium?"
                ),
                "formal_inputs": {
                    "forces": [
                        {"name": "load", "fx": 0, "fy": -30},
                        {"name": "cable_a", "fx": "-40", "fy": 15},
                        {"name": "cable_b", "fx": 40, "fy": 15},
                    ],
                    "force_unit": "N",
                },
                "wrong": {
                    "why": "a dropped force that still sums to a plausible resultant",
                    "mutate": {
                        "structured": {
                            "equilibrium": True,
                            "resultant_x": "0",
                            "resultant_y": "0",
                            "force_count": 2,
                            "forces_summed": ["load", "cable_a"],
                        }
                    },
                },
            },
            mechanics.MOMENT_BALANCE: {
                "statement": "A 50 N load hangs 2 m from a pinned support; what is the moment?",
                "formal_inputs": {
                    "forces": [
                        {"name": "load", "x": 2, "y": 0, "fx": 0, "fy": -50},
                        {"name": "reaction", "x": 0, "y": 0, "fx": 0, "fy": 50},
                    ],
                    "pivot": {"x": 0, "y": 0},
                    "force_unit": "N",
                    "length_unit": "m",
                    "result_unit": "N*m",
                },
                "wrong": {
                    "why": "the sign of the lever arm reversed",
                    "mutate": {"exact_value": "100"},
                },
            },
            mechanics.UNIFORM_MOTION: {
                "statement": (
                    "A trolley moves at a constant 25 m/s for 12 s; how far does it travel?"
                ),
                "formal_inputs": {
                    "speed": {"magnitude": "25", "unit": "m/s"},
                    "time": {"magnitude": 12, "unit": "s"},
                    "result_unit": "m",
                },
                "wrong": {
                    "why": "the right number in the wrong unit",
                    "mutate": {"exact_value": "300", "units": "km"},
                },
            },
        },
    },
    "chemistry": {
        "package": PACKAGES / "science.chemistry.v1.json",
        "domain_id": "science.chemistry",
        "kernels": chemistry.CHEMISTRY_KERNELS,
        "wave": "w3",
        "reason": "the chemistry pilot, the second domain registered from data",
        "tasks": {
            chemistry.MASS_BALANCE: {
                "statement": "Does CH4 + 2 O2 -> CO2 + 2 H2O balance, and what are the masses?",
                "formal_inputs": {
                    "reactants": [
                        {"formula": "CH4", "coefficient": 1},
                        {"formula": "O2", "coefficient": 2},
                    ],
                    "products": [
                        {"formula": "CO2", "coefficient": 1},
                        {"formula": "H2O", "coefficient": 2},
                    ],
                    "atomic_masses": {"C": "12", "H": "1", "O": "16"},
                },
                "wrong": {
                    "why": "an unbalanced equation declared balanced",
                    "mutate": {
                        "structured": {
                            "balanced": True,
                            "unbalanced_elements": [],
                            "reactant_elements": {"C": 1, "H": 4, "O": 4},
                            "product_elements": {"C": 1, "H": 4, "O": 4},
                            "reactant_mass": "80",
                            "product_mass": "80",
                        }
                    },
                    # The wrong answer above is the *correct* answer for the balanced case,
                    # submitted against an equation that does not balance. Nothing about its
                    # shape is suspicious; only recomputation catches it.
                    "against": {
                        "reactants": [
                            {"formula": "CH4", "coefficient": 1},
                            {"formula": "O2", "coefficient": 2},
                        ],
                        "products": [
                            {"formula": "CO2", "coefficient": 1},
                            {"formula": "H2O", "coefficient": 1},
                        ],
                        "atomic_masses": {"C": "12", "H": "1", "O": "16"},
                    },
                },
            },
            chemistry.MOLAR_CONVERSION: {
                "statement": "How many moles of water are there in a 36 g sample?",
                "formal_inputs": {
                    "formula": "H2O",
                    "atomic_masses": {"H": "1", "O": "16"},
                    "mass": {"magnitude": "36", "unit": "g"},
                    "result_unit": "mol",
                },
                "wrong": {
                    "why": "the molar mass of water read as 16 rather than 18",
                    "mutate": {"exact_value": "9/4"},
                },
            },
        },
    },
}

#: Set by `main` from `--pilot`. A module-level selection keeps every phase body identical
#: to the one W2 sealed; threading it through five signatures would buy nothing.
PILOT: dict[str, Any] = PILOTS["mechanics"]


def _environment() -> tuple[str, Path]:
    url = os.environ.get("COGOS_DATABASE_URL")
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not url or not root:
        raise SystemExit(
            "COGOS_DATABASE_URL and COGOS_ARTIFACT_ROOT are required; source the sprint "
            "environment file explicitly rather than exporting (S21D5-W0-F1)"
        )
    return url, Path(root)


def _services(url: str, root: Path) -> tuple[Any, Any, Any]:
    engine = create_postgres_engine(url)
    artifacts = ArtifactService(
        ContentAddressedFilesystem(root), PostgresArtifactRepository(engine)
    )
    events = PostgresEventStore(engine, build_default_event_catalog())
    return engine, artifacts, events


async def _admit(events: Any, artifacts: Any) -> DomainDescriptorV1:
    """Rebuild from stored bytes and admit the selected pilot to the resolution table.

    Nothing in-process is trusted: the descriptor comes back through the artifact bytes and
    the package boundary, exactly as it would on a real cold start.
    """
    for descriptor in await _admit_all(events, artifacts):
        if descriptor.domain_id == PILOT["domain_id"]:
            return descriptor
    raise SystemExit(f"{PILOT['domain_id']} is not in the store; run the register phase first")


async def _admit_all(events: Any, artifacts: Any) -> tuple[DomainDescriptorV1, ...]:
    """Every pilot the store holds, admitted. The store is the authority on which exist."""
    stored = await rebuild_descriptors(events, artifacts)
    by_id = {item["domain_id"]: item for item in PILOTS.values()}
    admitted = []
    for descriptor in stored:
        pilot = by_id.get(descriptor.domain_id)
        if pilot is None:
            continue  # a slice fixture, not a pilot
        registry.register_descriptor_domain(descriptor, pilot["kernels"])
        admitted.append(descriptor)
    return tuple(admitted)


async def _register() -> dict[str, Any]:
    url, root = _environment()
    engine, artifacts, events = _services(url, root)
    package: Path = PILOT["package"]
    try:
        payload = package.read_bytes()
        # The boundary runs here too, before the store's own copy of it. A package that the
        # store would refuse should never reach the store's error path to find that out.
        descriptor = validate_domain_package(payload)
        registration = await register_domain_package(
            events,
            artifacts,
            payload,
            actor=f"sprint-22a-{PILOT['wave']}",
            authority="sprint-22a pre-registration revision 1",
            reason=PILOT["reason"],
        )
        return {
            "phase": "register",
            "process": os.getpid(),
            "package_file": str(package.relative_to(REPO)),
            "package_sha256": sha256(payload).hexdigest(),
            "package_bytes": len(payload),
            "domain_id": registration.domain_id,
            "revision": registration.revision,
            "lifecycle": descriptor.lifecycle.value,
            "descriptor_content_hash": registration.descriptor_content_hash,
            "problem_types": list(descriptor.problem_types),
            "concepts": [item.concept_id for item in descriptor.concepts],
            "artifact_id": str(registration.artifact_id),
            "event_id": str(registration.event_id),
            "stream_id": str(DOMAIN_REGISTRY_STREAM_ID),
            "stream_version": registration.stream_version,
            "media_type": DOMAIN_PACKAGE_MEDIA_TYPE,
            "went_through_the_boundary": True,
        }
    finally:
        await dispose_postgres_engine(engine)


async def _rebuild() -> dict[str, Any]:
    """A cold process admits the pilot and the released four do not notice."""
    url, root = _environment()
    engine, artifacts, events = _services(url, root)
    try:
        before_released = registry.released_snapshot_hash()
        before_all = registry.snapshot_hash()
        entries_before = len(registry.entries())
        registrations = await load_registrations(events)
        pilot = await _admit(events, artifacts)
        resolved = {name: registry.resolve(name).domain_id for name in pilot.problem_types}
        return {
            "phase": "rebuild",
            "process": os.getpid(),
            "pilot": pilot.domain_id,
            "registrations_replayed": len(registrations),
            "pilot_rebuilt": True,
            "pilot_content_hash": pilot.content_hash,
            "problem_types_resolved": resolved,
            "every_problem_type_resolves": set(resolved) == set(pilot.problem_types),
            "resolved_to_the_pilot": all(value == pilot.domain_id for value in resolved.values()),
            "registry_entries_before": entries_before,
            "registry_entries_after": len(registry.entries()),
            "domain_ids_after": list(registry.domain_ids()),
            "released_snapshot_before": before_released,
            "released_snapshot_after": registry.released_snapshot_hash(),
            "released_snapshot_unchanged": (
                registry.released_snapshot_hash() == before_released == SEALED_RELEASED_SNAPSHOT
            ),
            "whole_snapshot_before": before_all,
            "whole_snapshot_after": registry.snapshot_hash(),
            "whole_snapshot_changed": registry.snapshot_hash() != before_all,
            "reading": (
                "S22A-030: the released snapshot is what the sealed compat contract asserts "
                "and no registration may move it; the whole-registry snapshot changed "
                "because the registry really did gain a domain"
            ),
        }
    finally:
        await dispose_postgres_engine(engine)


async def _solve() -> dict[str, Any]:
    """Every problem type solved through the Tool Plane and judged by the released verifier."""
    url, root = _environment()
    engine, artifacts, events = _services(url, root)
    try:
        await _admit(events, artifacts)
        results = {}
        for problem_type, task in PILOT["tasks"].items():
            run = await run_descriptor_case(problem_type, task["formal_inputs"])
            wrong_candidate = dict(run.candidate)
            wrong_candidate.update(task["wrong"]["mutate"])
            # A wrong answer is normally judged against its own case. `against` submits an
            # *honest-looking* answer against a different case, which is the harder shape:
            # nothing about the candidate is malformed, only untrue.
            against = task["wrong"].get("against", task["formal_inputs"])
            refused = await run_descriptor_case(
                problem_type, against, candidate_override=wrong_candidate
            )
            results[problem_type] = {
                "statement": task["statement"],
                "domain_id": run.domain_id,
                "tool_status": run.tool_status,
                "verifier_status": run.verifier_status,
                "accepted": run.accepted,
                "answer": run.candidate.get("exact_value") or run.candidate.get("structured"),
                "units": run.candidate.get("units"),
                "required_capabilities": list(run.required_capabilities),
                "tool_plane_events": list(run.event_types),
                "wrong_answer": {
                    "why": task["wrong"]["why"],
                    "judged_against_a_different_case": "against" in task["wrong"],
                    "verifier_status": refused.verifier_status,
                    "accepted": refused.accepted,
                    "detail": refused.message,
                },
            }
        return {
            "phase": "solve",
            "process": os.getpid(),
            "pilot": PILOT["domain_id"],
            "problem_types": len(results),
            "results": results,
            "every_task_accepted": all(item["accepted"] for item in results.values()),
            "every_wrong_answer_refused": all(
                not item["wrong_answer"]["accepted"] for item in results.values()
            ),
            "solved_through": "domains.solve, under the real Tool Plane policy and audit",
            "judged_by": "domains.checker, through the released VerificationService",
            "core_controller_changed": False,
        }
    finally:
        await dispose_postgres_engine(engine)


async def _views() -> dict[str, Any]:
    """One concept, two governed views: the exit criterion's cross-domain half."""
    url, root = _environment()
    engine, artifacts, events = _services(url, root)
    try:
        pilots = await _admit_all(events, artifacts)
        catalogue = (*pilots, *released_domain_descriptors())
        views = concept_views(catalogue)
        owners = concept_owners(catalogue)
        shared = {
            concept.concept_id: pilot.domain_id
            for pilot in pilots
            for concept in pilot.concepts
            if concept.shared_with
        }
        rendered = {
            domain_id: [
                {
                    "concept_id": view.concept_id,
                    "exposure": view.exposure.value,
                    "owner": view.owner_domain_id,
                    "content_hash": view.content_hash,
                }
                for view in items
            ]
            for domain_id, items in views.items()
            if items
        }
        physics = {item["concept_id"]: item for item in rendered.get("physics", [])}
        owned = {
            name: next(item for item in rendered[owner] if item["concept_id"] == name)
            for name, owner in shared.items()
        }
        return {
            "phase": "views",
            "process": os.getpid(),
            "pilots": [item.domain_id for item in pilots],
            "views": rendered,
            "shared_concepts": shared,
            "owners": owners,
            "every_shared_concept_visible_from_physics": all(name in physics for name in shared),
            "same_content_hash_in_both_views": all(
                owned[name]["content_hash"] == physics[name]["content_hash"] for name in shared
            ),
            "physics_owns_none_of_them": all(
                physics[name]["owner"] == shared[name] for name in shared
            ),
            "physics_sees_two_pilots": len({shared[name] for name in physics}) > 1,
            "stored_once": (
                "the concept lives in exactly one package artifact, the owner's; the second "
                "view is a projection over the same bytes and never a copy"
            ),
        }
    finally:
        await dispose_postgres_engine(engine)


def _sealed_boundary_cases() -> dict[str, bytes]:
    """The six refusal cases W0 sealed, executed rather than restated (W3-F1).

    Loaded out of the survey script that sealed them, so the suite below cannot drift into
    testing a second copy that agrees with itself.
    """
    spec = importlib.util.spec_from_file_location(
        "domain_survey_22a", REPO / "scripts/domain_survey_22a.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases: dict[str, bytes] = module._refusal_cases()
    return cases


async def _rejections() -> dict[str, Any]:
    """The rejection suite (§3.5): the six sealed cases, plus the three this sprint owes.

    Every case names the layer that refused it, because the layer is the finding. A package
    the *boundary* refuses never reaches a store; one the *registry door* refuses never
    reaches a solver; one the *catalogue* refuses never reaches a view. A case that moved
    to a later layer than the suite records would be a real regression.
    """
    url, root = _environment()
    engine, artifacts, events = _services(url, root)
    try:
        pilots = await _admit_all(events, artifacts)
        catalogue = (*pilots, *released_domain_descriptors())
        entries_before = len(registry.entries())
        cases: list[dict[str, Any]] = []

        def attempt(name: str, layer: str, build: Any) -> None:
            before = len(registry.entries())
            try:
                build()
            except (DomainPackageError, registry.DescriptorDomainError) as error:
                cases.append(
                    {
                        "case": name,
                        "layer": layer,
                        "refused": True,
                        "diagnostics": list(error.diagnostics)[:3],
                        "entries_unchanged": len(registry.entries()) == before,
                    }
                )
            else:
                cases.append(
                    {
                        "case": name,
                        "layer": layer,
                        "refused": False,
                        "diagnostics": ["ACCEPTED — this case was not refused"],
                        "entries_unchanged": len(registry.entries()) == before,
                    }
                )

        for name, payload in _sealed_boundary_cases().items():
            attempt(
                f"boundary: {name}",
                "package boundary",
                lambda p=payload: validate_domain_package(p),
            )

        def _variant(pilot: str, **overrides: Any) -> DomainDescriptorV1:
            body = json.loads(PILOTS[pilot]["package"].read_text(encoding="utf-8"))
            body.pop("content_hash", None)
            body.update(overrides)
            return DomainDescriptorV1.model_validate(body)

        # §3.5, one: a released domain id at a new revision. Revision supersession is a
        # governance path with evidence behind it, not something a package upload performs.
        attempt(
            "impersonating a released domain at a new revision",
            "registry door",
            lambda: registry.register_descriptor_domain(
                _variant(
                    "chemistry",
                    domain_id="physics",
                    revision=2,
                    related_domain_ids=[],
                    concepts=[],
                    transfer_links=[],
                ),
                chemistry.CHEMISTRY_KERNELS,
            ),
        )

        # §3.5, two: capabilities naming no verifier that runs. The registry admits it —
        # nothing static can know what a checker will emit — and the released checker
        # refuses at resolution with `missing_required_verifier`, which is the code §3.5
        # names. Run below rather than asserted here.
        # §3.5, three: a concept shared into a domain that never declared it back.
        attempt(
            "sharing a concept into a pilot that never declared it back",
            "catalogue",
            lambda: concept_views(
                (
                    _variant(
                        "chemistry",
                        domain_id="science.materials",
                        related_domain_ids=["engineering.mechanics"],
                        concepts=[
                            {
                                "concept_id": "materials.lattice",
                                "description": "A repeating arrangement of atoms.",
                                "shared_with": ["engineering.mechanics"],
                            }
                        ],
                        transfer_links=[],
                    ),
                    *catalogue,
                )
            ),
        )
        attempt(
            "sharing a concept into a domain that exists nowhere",
            "catalogue",
            lambda: concept_views(
                (
                    _variant(
                        "chemistry",
                        domain_id="science.materials",
                        related_domain_ids=["science.astronomy"],
                        concepts=[
                            {
                                "concept_id": "materials.lattice",
                                "description": "A repeating arrangement of atoms.",
                                "shared_with": ["science.astronomy"],
                            }
                        ],
                        transfer_links=[],
                    ),
                    *catalogue,
                )
            ),
        )

        # The declared-but-unrun verifier, executed rather than described: a task whose plan
        # requires a capability no checker emits must not be accepted.
        problem_type = chemistry.MOLAR_CONVERSION
        task = PILOTS["chemistry"]["tasks"][problem_type]
        entry = registry.resolve(problem_type)
        unrun = await run_descriptor_case(
            problem_type,
            task["formal_inputs"],
            required_capabilities=(*entry.required_verifiers, "chemistry.spectroscopy"),
        )
        cases.append(
            {
                "case": "capabilities naming a verifier that never runs",
                "layer": "resolution",
                "refused": not unrun.accepted,
                "diagnostics": [unrun.message],
                "entries_unchanged": True,
            }
        )

        return {
            "phase": "rejections",
            "process": os.getpid(),
            "pilots": [item.domain_id for item in pilots],
            "cases": cases,
            "case_count": len(cases),
            "layers": sorted({item["layer"] for item in cases}),
            "every_case_refused": all(item["refused"] for item in cases),
            "nothing_registered_halfway": all(item["entries_unchanged"] for item in cases),
            "entries_after": len(registry.entries()),
            "entries_unchanged_overall": len(registry.entries()) == entries_before,
            "released_snapshot_unchanged": (
                registry.released_snapshot_hash() == SEALED_RELEASED_SNAPSHOT
            ),
            "sealed_cases_executed": sorted(_sealed_boundary_cases()),
        }
    finally:
        await dispose_postgres_engine(engine)


PHASES = {
    "register": _register,
    "rebuild": _rebuild,
    "solve": _solve,
    "views": _views,
    "rejections": _rejections,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=sorted(PHASES))
    parser.add_argument("--pilot", choices=sorted(PILOTS), default="mechanics")
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()

    global PILOT
    PILOT = PILOTS[arguments.pilot]

    result = asyncio.run(PHASES[arguments.phase]())
    result["recorded_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    rendered = json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False)
    print(rendered)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
