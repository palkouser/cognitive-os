"""Credential-free Sprint 15 corpus fixtures and deterministic artifact storage."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.corpus import (
    CorpusDestinationType,
    CorpusFactoryRequest,
    CorpusSourceType,
    CorpusUsageRight,
)
from cognitive_os.domain.experience import ExperienceCandidate, ExperienceCandidateType
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.experience.fixtures import INITIAL_FIXTURES, build_fixture

from .sources import InspectedSource, SourceMaterial, _build_source, inspect_experience_candidate

FIXTURE_TIME = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
INITIAL_CORPUS_FIXTURES = (
    "experience-candidate",
    "verified-trajectory",
    "memory-export",
    "semantic-export",
    "skill-package",
    "strategy-package",
    "repository-snapshot",
    "document",
    "benchmark-dataset",
    "operator-annotation",
    "provider-dataset",
    "cognitive-os-export",
)


def fixture_id(kind: str, name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"sprint15:{kind}:{name}")


class FixtureArtifactStore:
    """Content-addressed in-memory store with stable identities and timestamps."""

    def __init__(self) -> None:
        self.data: dict[UUID, bytes] = {}

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        del source_event_id
        digest = sha256(data).hexdigest()
        artifact_id = fixture_id("artifact", f"{media_type}:{digest}")
        self.data[artifact_id] = data
        return ArtifactRef(
            artifact_id=artifact_id,
            media_type=media_type,
            content_hash=digest,
            size_bytes=len(data),
            storage_key=f"sha256/{digest[:2]}/{digest}",
            created_at=FIXTURE_TIME,
        )

    async def put_file(
        self, path: Path, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        return await self.put_bytes(
            path.read_bytes(), media_type=media_type, source_event_id=source_event_id
        )

    async def get_bytes(self, artifact_id: UUID) -> bytes:
        return self.data[artifact_id]

    async def open_read(self, artifact_id: UUID) -> io.BytesIO:
        return io.BytesIO(await self.get_bytes(artifact_id))

    async def verify(self, artifact_id: UUID) -> bool:
        data = self.data.get(artifact_id)
        return data is not None

    async def exists(self, artifact_id: UUID) -> bool:
        return artifact_id in self.data

    async def find_orphan_blobs(self) -> tuple[str, ...]:
        return ()


def build_corpus_fixture(
    name: str,
    *,
    secret: bool = False,
    conflicting_license: bool = False,
    destination: CorpusDestinationType | None = None,
) -> tuple[CorpusFactoryRequest, InspectedSource]:
    """Build one of twelve stable source-family fixtures."""

    if name not in INITIAL_CORPUS_FIXTURES and not name.startswith("seed-"):
        raise ValueError(f"unknown corpus fixture: {name}")
    template = (
        INITIAL_CORPUS_FIXTURES[int(name.split("-")[1]) % len(INITIAL_CORPUS_FIXTURES)]
        if name.startswith("seed-")
        else name
    )
    source_type = {
        "experience-candidate": CorpusSourceType.EXPERIENCE_CANDIDATE,
        "verified-trajectory": CorpusSourceType.VERIFIED_TRAJECTORY,
        "memory-export": CorpusSourceType.MEMORY_EXPORT,
        "semantic-export": CorpusSourceType.SEMANTIC_EXPORT,
        "skill-package": CorpusSourceType.SKILL_PACKAGE,
        "strategy-package": CorpusSourceType.STRATEGY_PACKAGE,
        "repository-snapshot": CorpusSourceType.REPOSITORY_SNAPSHOT,
        "document": CorpusSourceType.DOCUMENT,
        "benchmark-dataset": CorpusSourceType.BENCHMARK_DATASET,
        "operator-annotation": CorpusSourceType.OPERATOR_ANNOTATION,
        "provider-dataset": CorpusSourceType.PROVIDER_GENERATED_DATASET,
        "cognitive-os-export": CorpusSourceType.COGNITIVE_OS_EXPORT,
    }[template]
    if template == "experience-candidate":
        compilation, sources, profiles = build_fixture("direct-success")
        candidate = ExperienceCompiler(sources, profiles).compile(compilation).candidates[0]
        source = inspect_experience_candidate(
            candidate, source_revision="1", config=CorpusConfiguration()
        )
    else:
        suffix = "md" if template in {"document", "operator-annotation"} else "json"
        value = (
            f"# {name}\n\nDeterministic local corpus fixture.\n"
            if suffix == "md"
            else f'{{"fixture":"{name}","source_type":"{source_type.value}"}}'
        )
        if secret:
            value += f"\n{'_'.join(('API', 'KEY'))}=fixture-credential-value\n"
        material = SourceMaterial(
            f"{name}.{suffix}",
            value.encode(),
            "text/markdown" if suffix == "md" else "application/json",
            "utf-8",
        )
        source = _build_source(
            source_type,
            f"fixture:{name}",
            "1",
            [material],
            CorpusConfiguration(),
        )
    rights: dict[CorpusUsageRight, bool | None] = {right: True for right in CorpusUsageRight}
    licenses = ("Apache-2.0", "MIT") if conflicting_license else ("Apache-2.0",)
    request = CorpusFactoryRequest(
        request_id=fixture_id("request", name),
        source_type=source_type,
        source_identity=source.source_identity,
        source_revision=source.source_revision,
        scope="project:cognitive-os",
        sensitivity=MemorySensitivity.INTERNAL,
        license_identifiers=licenses,
        usage_rights=rights,
        requested_destination=destination,
        created_at=FIXTURE_TIME,
        created_by="sprint15-fixture",
    )
    return request, source


def sprint14_candidate_fixtures() -> tuple[tuple[CorpusFactoryRequest, InspectedSource], ...]:
    """Expose one exact proposed Sprint 14 candidate of every candidate type."""

    candidates: dict[ExperienceCandidateType, ExperienceCandidate] = {}
    for name in INITIAL_FIXTURES:
        request, sources, profiles = build_fixture(name)
        result = ExperienceCompiler(sources, profiles).compile(request)
        for candidate in result.candidates:
            candidates.setdefault(candidate.candidate_type, candidate)
    fixtures = []
    for _candidate_type, candidate in sorted(candidates.items(), key=lambda item: item[0].value):
        source = inspect_experience_candidate(
            candidate,
            source_revision=str(candidate.candidate_revision),
            config=CorpusConfiguration(),
        )
        rights: dict[CorpusUsageRight, bool | None] = {right: True for right in CorpusUsageRight}
        fixtures.append(
            (
                CorpusFactoryRequest(
                    request_id=fixture_id("experience-request", str(candidate.candidate_id)),
                    source_type=source.source_type,
                    source_identity=source.source_identity,
                    source_revision=source.source_revision,
                    scope=candidate.scope,
                    sensitivity=candidate.sensitivity,
                    license_identifiers=("Apache-2.0",),
                    usage_rights=rights,
                    created_at=FIXTURE_TIME,
                    created_by="sprint15-fixture",
                ),
                source,
            )
        )
    return tuple(fixtures)
