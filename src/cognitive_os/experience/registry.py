"""Frozen source, profile, segmenter, and candidate-generator registries."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256

from cognitive_os.domain.experience import (
    CompilerProfile,
    ExperienceCandidate,
    ExperienceCandidateType,
    TimelineEntry,
    TrajectorySourceRef,
)

from .errors import ExperiencePolicyError, ExperienceSourceError


def canonical_hash(value: object) -> str:
    return sha256(
        json.dumps(value, default=str, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class ResolvedTrajectorySource:
    reference: TrajectorySourceRef
    payload: bytes
    timeline_entries: tuple[TimelineEntry, ...] = ()
    terminal_state: str | None = None


class SourceResolverRegistry:
    """Frozen exact-revision source registry; all reads are immutable and bounded."""

    def __init__(self) -> None:
        self._sources: dict[tuple[str, str, str], ResolvedTrajectorySource] = {}
        self._frozen = False

    def register(self, source: ResolvedTrajectorySource) -> None:
        if self._frozen:
            raise ExperiencePolicyError("source resolver registry is frozen")
        key = (
            source.reference.source_type.value,
            source.reference.source_id,
            source.reference.source_revision,
        )
        if key in self._sources:
            raise ExperienceSourceError("duplicate source resolver identity")
        if sha256(source.payload).hexdigest() != source.reference.source_content_hash:
            raise ExperienceSourceError("source content hash mismatch")
        if any(entry.source_ref != source.reference for entry in source.timeline_entries):
            raise ExperienceSourceError("timeline entry references another source")
        self._sources[key] = source

    def freeze(self) -> None:
        self._frozen = True

    def resolve(self, reference: TrajectorySourceRef) -> ResolvedTrajectorySource:
        key = (reference.source_type.value, reference.source_id, reference.source_revision)
        try:
            source = self._sources[key]
        except KeyError as error:
            raise ExperienceSourceError("trajectory source is unavailable") from error
        if (
            source.reference != reference
            or sha256(source.payload).hexdigest() != reference.source_content_hash
        ):
            raise ExperienceSourceError("trajectory source changed after registration")
        return source

    def snapshot_hash(self) -> str:
        return canonical_hash(
            [self._sources[key].reference.model_dump(mode="json") for key in sorted(self._sources)]
        )


class CompilerProfileRegistry:
    def __init__(self) -> None:
        self._profiles: dict[tuple[str, int], CompilerProfile] = {}
        self._frozen = False

    def register(self, profile: CompilerProfile) -> None:
        if self._frozen:
            raise ExperiencePolicyError("compiler profile registry is frozen")
        key = profile.profile_id, profile.version
        if key in self._profiles:
            raise ExperiencePolicyError("duplicate compiler profile version")
        self._profiles[key] = profile

    def freeze(self) -> None:
        self._frozen = True

    def resolve(self, profile_id: str, version: int) -> CompilerProfile:
        try:
            return self._profiles[(profile_id, version)]
        except KeyError as error:
            raise ExperiencePolicyError("compiler profile version is unavailable") from error

    def snapshot_hash(self) -> str:
        return canonical_hash([self._profiles[key].content_hash for key in sorted(self._profiles)])


CandidateGenerator = Callable[..., ExperienceCandidate | None]


class CandidateGeneratorRegistry:
    def __init__(self) -> None:
        self._generators: dict[ExperienceCandidateType, CandidateGenerator] = {}
        self._frozen = False

    def register(
        self, candidate_type: ExperienceCandidateType, generator: CandidateGenerator
    ) -> None:
        if self._frozen:
            raise ExperiencePolicyError("candidate generator registry is frozen")
        if candidate_type in self._generators:
            raise ExperiencePolicyError("duplicate candidate generator")
        self._generators[candidate_type] = generator

    def freeze(self) -> None:
        self._frozen = True

    def resolve(self, candidate_type: ExperienceCandidateType) -> CandidateGenerator:
        try:
            return self._generators[candidate_type]
        except KeyError as error:
            raise ExperiencePolicyError("candidate generator is unavailable") from error

    def snapshot_hash(self) -> str:
        return canonical_hash(sorted(item.value for item in self._generators))
