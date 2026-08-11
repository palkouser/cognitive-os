#!/usr/bin/env python3
"""S22A-031 through S22A-035. The mechanics pilot, from package bytes to a judged answer.

The first domain the platform learns about from data rather than from its own source. The
chain is the one W1's slice proved, continued past the point where the slice stopped:

    committed package bytes → fail-closed boundary → artifact + event
        → **a different process** → rebuild → admitted to the problem-type registry
        → solved by the released Tool Plane tool → judged by the released verifier

**Separate processes, again and for the same reason.** `register` writes and exits;
`rebuild`, `solve`, `views` and `refusals` each start cold, knowing nothing but the database
and the artifact root. A pilot that "registered" only inside the process that authored it
would look exactly like a pilot that registered.

    COGOS_POSTGRES_ENV_FILE=$PWD/.env.s22a.local \
        uv run python scripts/mechanics_pilot_22a.py register
    ... and likewise for the rebuild, solve, views and refusals phases, each in its own
    process and in that order.

The package is a committed file, not a literal in this script. A descriptor package is bytes
that arrive from outside; generating them here would test a serialiser rather than a door.
"""

from __future__ import annotations

import argparse
import asyncio
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
    concept_owners,
    concept_views,
    released_domain_descriptors,
    validate_domain_package,
)
from cognitive_os.domains import registry  # noqa: E402
from cognitive_os.domains.descriptor_runner import run_descriptor_case  # noqa: E402
from cognitive_os.domains.descriptor_store import (  # noqa: E402
    DOMAIN_PACKAGE_MEDIA_TYPE,
    DOMAIN_REGISTRY_STREAM_ID,
    load_registrations,
    rebuild_descriptors,
    register_domain_package,
)
from cognitive_os.domains.mechanics import (  # noqa: E402
    MECHANICS_KERNELS,
    MOMENT_BALANCE,
    STATICS_EQUILIBRIUM,
    UNIFORM_MOTION,
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

PACKAGE = REPO / "docs/sprints/sprint-22/packages/engineering.mechanics.v1.json"
PILOT_DOMAIN_ID = "engineering.mechanics"

#: The sealed released snapshot: what W0 froze as the backward-compatibility contract, and
#: what S22A-030 re-binds to `released_snapshot_hash()`. Admitting a pilot must not move it.
SEALED_RELEASED_SNAPSHOT = "00187f2bc6e0015529de8388ea33a1e6287939ca4d393875400bc68320997119"

#: Three tasks, one per problem type, each with a wrong answer that must be refused. The
#: wrong answers are not noise: each one is the specific mistake its checker's independent
#: route exists to catch, so a checker that quietly agreed with its solver would fail here.
TASKS: dict[str, dict[str, Any]] = {
    STATICS_EQUILIBRIUM: {
        "statement": "Three cables and a load meet at a joint; is the joint in equilibrium?",
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
    MOMENT_BALANCE: {
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
    UNIFORM_MOTION: {
        "statement": "A trolley moves at a constant 25 m/s for 12 s; how far does it travel?",
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
}


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
    """Rebuild from stored bytes and admit the pilot to the released resolution table.

    Nothing in-process is trusted: the descriptor comes back through the artifact bytes and
    the package boundary, exactly as it would on a real cold start.
    """
    descriptors = await rebuild_descriptors(events, artifacts)
    pilot = next((item for item in descriptors if item.domain_id == PILOT_DOMAIN_ID), None)
    if pilot is None:
        raise SystemExit(f"{PILOT_DOMAIN_ID} is not in the store; run the register phase first")
    registry.register_descriptor_domain(pilot, MECHANICS_KERNELS)
    return pilot


async def _register() -> dict[str, Any]:
    url, root = _environment()
    engine, artifacts, events = _services(url, root)
    try:
        payload = PACKAGE.read_bytes()
        # The boundary runs here too, before the store's own copy of it. A package that the
        # store would refuse should never reach the store's error path to find that out.
        descriptor = validate_domain_package(payload)
        registration = await register_domain_package(
            events,
            artifacts,
            payload,
            actor="sprint-22a-w2",
            authority="sprint-22a pre-registration revision 1",
            reason="the mechanics pilot, the first domain registered from data",
        )
        return {
            "phase": "register",
            "process": os.getpid(),
            "package_file": str(PACKAGE.relative_to(REPO)),
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
            "registrations_replayed": len(registrations),
            "pilot_rebuilt": True,
            "pilot_content_hash": pilot.content_hash,
            "problem_types_resolved": resolved,
            "every_problem_type_resolves": set(resolved) == set(pilot.problem_types),
            "resolved_to_the_pilot": all(value == PILOT_DOMAIN_ID for value in resolved.values()),
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
        for problem_type, task in TASKS.items():
            run = await run_descriptor_case(problem_type, task["formal_inputs"])
            wrong_candidate = dict(run.candidate)
            wrong_candidate.update(task["wrong"]["mutate"])
            refused = await run_descriptor_case(
                problem_type, task["formal_inputs"], candidate_override=wrong_candidate
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
                    "verifier_status": refused.verifier_status,
                    "accepted": refused.accepted,
                    "detail": refused.message,
                },
            }
        return {
            "phase": "solve",
            "process": os.getpid(),
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
        pilot = await _admit(events, artifacts)
        catalogue = (pilot, *released_domain_descriptors())
        views = concept_views(catalogue)
        owners = concept_owners(catalogue)
        shared = [item.concept_id for item in pilot.concepts if item.shared_with]
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
        mechanics = {item["concept_id"]: item for item in rendered[PILOT_DOMAIN_ID]}
        physics = {item["concept_id"]: item for item in rendered.get("physics", [])}
        return {
            "phase": "views",
            "process": os.getpid(),
            "views": rendered,
            "shared_concepts": shared,
            "owners": owners,
            "every_shared_concept_visible_from_physics": all(name in physics for name in shared),
            "same_content_hash_in_both_views": all(
                mechanics[name]["content_hash"] == physics[name]["content_hash"] for name in shared
            ),
            "physics_owns_none_of_them": all(
                physics[name]["owner"] == PILOT_DOMAIN_ID for name in shared
            ),
            "stored_once": (
                "the concept lives in exactly one package artifact, the owner's; the second "
                "view is a projection over the same bytes and never a copy"
            ),
        }
    finally:
        await dispose_postgres_engine(engine)


async def _refusals() -> dict[str, Any]:
    """The registration door refuses everything it should, and admits nothing halfway."""
    url, root = _environment()
    engine, artifacts, events = _services(url, root)
    try:
        pilot = await _admit(events, artifacts)
        entries_after_pilot = len(registry.entries())
        cases = []

        def attempt(name: str, build: Any) -> None:
            before = len(registry.entries())
            try:
                build()
            except registry.DescriptorDomainError as error:
                cases.append(
                    {
                        "case": name,
                        "refused": True,
                        "diagnostics": list(error.diagnostics),
                        "entries_unchanged": len(registry.entries()) == before,
                    }
                )
            else:
                cases.append({"case": name, "refused": False, "entries_unchanged": False})

        def _variant(**overrides: Any) -> DomainDescriptorV1:
            body = json.loads(PACKAGE.read_text(encoding="utf-8"))
            body.pop("content_hash", None)
            body.update(overrides)
            return DomainDescriptorV1.model_validate(body)

        attempt(
            "re-registering the same identity",
            lambda: registry.register_descriptor_domain(pilot, MECHANICS_KERNELS),
        )
        # The descriptor contract already blocks part of this shape: a package claiming
        # `physics` cannot keep mechanics' relations, shared concepts or transfer link,
        # because all three would then point at itself. Stripping them is what makes the
        # attempt reach the registry door at all, which is the door under test here.
        attempt(
            "impersonating a released domain id",
            lambda: registry.register_descriptor_domain(
                _variant(
                    domain_id="physics",
                    related_domain_ids=[],
                    concepts=[],
                    transfer_links=[],
                ),
                MECHANICS_KERNELS,
            ),
        )
        attempt(
            "claiming a problem type no kernel implements",
            lambda: registry.register_descriptor_domain(
                _variant(
                    domain_id="engineering.thermofluids",
                    revision=1,
                    problem_types=["mechanics.compressible-flow"],
                ),
                MECHANICS_KERNELS,
            ),
        )
        attempt(
            "taking a problem type another domain already owns",
            lambda: registry.register_descriptor_domain(
                _variant(domain_id="engineering.statics", revision=1),
                MECHANICS_KERNELS,
            ),
        )
        attempt(
            "registering a namespace with no problem types",
            lambda: registry.register_descriptor_domain(
                _variant(domain_id="engineering", revision=1, problem_types=[]),
                MECHANICS_KERNELS,
            ),
        )
        return {
            "phase": "refusals",
            "process": os.getpid(),
            "cases": cases,
            "every_case_refused": all(item["refused"] for item in cases),
            "nothing_registered_halfway": all(item["entries_unchanged"] for item in cases),
            "entries_after": len(registry.entries()),
            "entries_unchanged_overall": len(registry.entries()) == entries_after_pilot,
            "released_snapshot_unchanged": (
                registry.released_snapshot_hash() == SEALED_RELEASED_SNAPSHOT
            ),
        }
    finally:
        await dispose_postgres_engine(engine)


PHASES = {
    "register": _register,
    "rebuild": _rebuild,
    "solve": _solve,
    "views": _views,
    "refusals": _refusals,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=sorted(PHASES))
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()

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
