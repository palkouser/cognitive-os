#!/usr/bin/env python3
"""S22A-020. The first vertical slice: one fixture descriptor through the whole chain.

Sprint 22A's backlog puts this before W1 builds anything, for the reason D4 through D7 each
paid for once — the cheapest defect of a wave is the one the slice finds. The chain is:

    package bytes → fail-closed boundary → event + content-addressed artifact
        → **a different process** → rebuild from stored bytes → problem-type resolution
        → refusal on a tampered byte

**The phases are separate processes on purpose.** `store` writes and exits; `rebuild` starts
cold and knows nothing but the database and the artifact root. This is where "storage without
a schema" would quietly become "state in memory", and D7's lifecycle lesson was that only a
real restart can tell the difference. Running them in one process would prove nothing and
would look exactly like proof.

    COGOS_POSTGRES_ENV_FILE=$PWD/.env.s22a.local uv run python scripts/domain_slice_22a.py store
    COGOS_POSTGRES_ENV_FILE=$PWD/.env.s22a.local uv run python scripts/domain_slice_22a.py rebuild
    COGOS_POSTGRES_ENV_FILE=$PWD/.env.s22a.local uv run python scripts/domain_slice_22a.py tamper
    COGOS_POSTGRES_ENV_FILE=$PWD/.env.s22a.local uv run python scripts/domain_slice_22a.py refusals

The fixture is a slice fixture, not a pilot: `slice.fixture` exists to exercise the chain and
is never one of the two pilot ids the pre-registration froze.
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
    DomainPackageError,
    validate_domain_package,
)
from cognitive_os.domains.descriptor_store import (  # noqa: E402
    DOMAIN_PACKAGE_MEDIA_TYPE,
    DOMAIN_REGISTRY_STREAM_ID,
    DomainRegistrationError,
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

EVIDENCE = REPO / "docs" / "sprints" / "sprint-22" / "evidence"

#: Not a pilot. The pre-registration froze `engineering.mechanics` and `science.chemistry`;
#: burning one of them on a plumbing check would spend a frozen id on a rehearsal.
FIXTURE_DOMAIN_ID = "slice.fixture"


def fixture_package() -> bytes:
    """One honest descriptor: it names capabilities the released registry actually resolves."""
    return json.dumps(
        {
            "domain_id": FIXTURE_DOMAIN_ID,
            "revision": 1,
            "display_name": "vertical slice fixture",
            "lifecycle": "pilot",
            "related_domain_ids": ["physics"],
            "problem_types": ["slice-dimension-check"],
            "concepts": [
                {
                    "concept_id": "slice_quantity",
                    "description": "a unit-carrying quantity the physics verifiers can judge",
                    "shared_with": ["physics"],
                }
            ],
            "capabilities": {
                "verifier_capabilities": ["physics.dimension"],
                "tool_capabilities": ["physics.kernel"],
                "units": ["metre"],
            },
            "provenance": {
                "source": "sprint-22a W1 vertical slice",
                "revision": "none",
                "licence": "internal",
                "redistributable": False,
            },
        },
        sort_keys=True,
    ).encode()


def _environment() -> tuple[str, Path]:
    url = os.environ.get("COGOS_DATABASE_URL")
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not url or not root:
        raise SystemExit(
            "COGOS_DATABASE_URL and COGOS_ARTIFACT_ROOT are required; source the sprint "
            "environment file explicitly rather than exporting (S21D5-W0-F1)"
        )
    return url, Path(root)


def _services(url: str, root: Path) -> tuple[Any, Any, Any, Any]:
    engine = create_postgres_engine(url)
    repository = PostgresArtifactRepository(engine)
    artifacts = ArtifactService(ContentAddressedFilesystem(root), repository)
    events = PostgresEventStore(engine, build_default_event_catalog())
    return engine, repository, artifacts, events


async def _store() -> dict[str, Any]:
    url, root = _environment()
    engine, _repository, artifacts, events = _services(url, root)
    try:
        package = fixture_package()
        registration = await register_domain_package(
            events,
            artifacts,
            package,
            actor="sprint-22a-w1",
            authority="sprint-22a pre-registration revision 1",
            reason="the first vertical slice, before the seam is built",
        )
        return {
            "phase": "store",
            "domain_id": registration.domain_id,
            "revision": registration.revision,
            "descriptor_content_hash": registration.descriptor_content_hash,
            "package_sha256": registration.package_sha256,
            "artifact_id": str(registration.artifact_id),
            "event_id": str(registration.event_id),
            "stream_version": registration.stream_version,
            "stream_id": str(DOMAIN_REGISTRY_STREAM_ID),
            "media_type": DOMAIN_PACKAGE_MEDIA_TYPE,
        }
    finally:
        await dispose_postgres_engine(engine)


async def _rebuild() -> dict[str, Any]:
    """A cold process: nothing is carried over but the database and the artifact root."""
    url, root = _environment()
    engine, _repository, artifacts, events = _services(url, root)
    try:
        registrations = await load_registrations(events)
        descriptors = await rebuild_descriptors(events, artifacts)
        by_id = {item.domain_id: item for item in descriptors}
        fixture = by_id.get(FIXTURE_DOMAIN_ID)
        return {
            "phase": "rebuild",
            "process": os.getpid(),
            "registrations_replayed": len(registrations),
            "descriptors_rebuilt": len(descriptors),
            "fixture_rebuilt": fixture is not None,
            "fixture_content_hash": fixture.content_hash if fixture else None,
            "fixture_problem_types": list(fixture.problem_types) if fixture else [],
            "fixture_shared_concepts": (
                [
                    {"concept_id": item.concept_id, "shared_with": list(item.shared_with)}
                    for item in fixture.concepts
                ]
                if fixture
                else []
            ),
            "rebuilt_from": "artifact bytes, re-validated through the package boundary",
        }
    finally:
        await dispose_postgres_engine(engine)


async def _tamper() -> dict[str, Any]:
    """Flip one byte in the stored blob and confirm the rebuild refuses rather than loads."""
    url, root = _environment()
    engine, repository, artifacts, events = _services(url, root)
    try:
        registrations = await load_registrations(events)
        target = next(item for item in registrations if item.payload.domain_id == FIXTURE_DOMAIN_ID)
        # The event names its artifact, which is the whole point of W1-F2's write order:
        # the bytes exist before anything indexes them, so the index is a payload field and
        # not a foreign key pointing backwards.
        found = await repository.get_artifact(target.payload.artifact_id)
        if found is None or found.media_type != DOMAIN_PACKAGE_MEDIA_TYPE:
            raise SystemExit("the registration does not name a package artifact")
        blob = await repository.get_blob_metadata(found.content_hash)
        if blob is None:  # pragma: no cover - the artifact exists, so its blob does
            raise SystemExit("the package artifact has no blob")
        path = root / blob.storage_key
        original = path.read_bytes()
        # The smallest possible lie: one byte of the display name, so the package still
        # parses, still validates, and still claims to be the same domain at the same
        # revision. A tamper check that only survives corrupt JSON is not a tamper check.
        tampered = original.replace(b"vertical slice fixture", b"vertical slice fixturz")
        if tampered == original:  # pragma: no cover - the fixture text is fixed
            raise SystemExit("the tamper target was not found in the stored bytes")
        path.write_bytes(tampered)
        try:
            await rebuild_descriptors(events, artifacts)
        except DomainRegistrationError as refusal:
            outcome = {"refused": True, "diagnosis": str(refusal)}
        except Exception as leaked:  # W1-F1: an untranslated refusal is itself a finding
            outcome = {
                "refused": True,
                "diagnosis": f"{type(leaked).__name__}: {leaked}",
                "named_the_domain": False,
            }
        else:
            outcome = {"refused": False, "diagnosis": "THE REBUILD ACCEPTED TAMPERED BYTES"}
        finally:
            path.write_bytes(original)
        restored = await rebuild_descriptors(events, artifacts)
        return {
            "phase": "tamper",
            "bytes_changed": 1,
            "still_parses_as_a_package": validate_domain_package(tampered).domain_id
            == FIXTURE_DOMAIN_ID,
            "named_the_domain": FIXTURE_DOMAIN_ID in str(outcome["diagnosis"]),
            **outcome,
            "restored_and_rebuilt": len(restored),
        }
    finally:
        await dispose_postgres_engine(engine)


async def _refusals() -> dict[str, Any]:
    """The two registry-level refusals W0-A1 said belong here rather than at the boundary."""
    url, root = _environment()
    engine, _repository, artifacts, events = _services(url, root)
    cases: dict[str, Any] = {}
    try:
        for name, package in (
            ("re_registration", fixture_package()),
            (
                "released_domain_impersonation",
                json.dumps(
                    dict(json.loads(fixture_package()), domain_id="coding", revision=2),
                    sort_keys=True,
                ).encode(),
            ),
        ):
            try:
                await register_domain_package(
                    events,
                    artifacts,
                    package,
                    actor="sprint-22a-w1",
                    authority="sprint-22a pre-registration revision 1",
                    reason="hostile case, expected to be refused",
                )
            except (DomainRegistrationError, DomainPackageError) as refusal:
                cases[name] = {"refused": True, "diagnosis": str(refusal)}
            else:
                cases[name] = {"refused": False, "diagnosis": "ACCEPTED — this is the finding"}
        registrations = await load_registrations(events)
        return {
            "phase": "refusals",
            "cases": cases,
            "every_case_refused": all(item["refused"] for item in cases.values()),
            "registrations_after": len(registrations),
        }
    finally:
        await dispose_postgres_engine(engine)


PHASES = {"store": _store, "rebuild": _rebuild, "tamper": _tamper, "refusals": _refusals}


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


def digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
