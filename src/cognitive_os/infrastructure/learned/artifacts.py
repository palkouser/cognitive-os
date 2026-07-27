"""Learned artifact lineage over the existing Artifact Store.

The learned plane keeps no bytes of its own. Everything it references already lives in
the content-addressed store, so deduplication, backup coverage and the restore verifier
keep working unchanged, and there is no second copy that can drift from the first.

**Nothing here loads an artifact.** There is no `load`, `open` or `deserialise` method,
and adding one would be a mistake rather than a feature: an artifact is data supplied by
whatever produced it, and a learned plane that executed an object graph supplied as data
would turn every lineage record into a remote-code-execution surface.
`LearnedArtifactFormat.JOBLIB` survives in the enum as a descriptive legacy value; this
module verifies its bytes by hashing them and never interprets them. See ADR 0086.
"""

from __future__ import annotations

from uuid import UUID

from cognitive_os.domain.common import ArtifactRef, utc_now
from cognitive_os.domain.learned import LearnedArtifactFormat
from cognitive_os.domain.learned_evidence import (
    LearnedArtifactLineage,
    LearnedArtifactRole,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.errors import ArtifactIntegrityError, ArtifactNotFoundError

#: Formats whose bytes are an executable object graph rather than inert data. They may be
#: *referenced* — a legacy artifact still has a lineage — and are never loaded. The set is
#: named so a future format that is also unsafe has an obvious place to be added.
UNSAFE_TO_DESERIALISE = frozenset({LearnedArtifactFormat.JOBLIB})


class LearnedArtifactStore:
    """Verified lineage into the existing Artifact Store. Reads and hashes; never loads.

    Satisfies `LearnedArtifactVerifierPort`, so the learned evidence service sees exactly
    two operations: describe an artifact, and confirm its bytes still hash to what was
    recorded.
    """

    def __init__(self, artifacts: ArtifactService) -> None:
        self._artifacts = artifacts

    async def artifact_metadata(self, artifact_id: UUID) -> ArtifactRef | None:
        return await self._artifacts.describe(artifact_id)

    async def verify_artifact(self, artifact_id: UUID) -> bool:
        """Re-read the stored bytes and confirm the recorded hash. Detects bit rot.

        The Artifact Store signals absence and corruption by raising, which is right for
        a caller reading bytes it needs. Here the question is only "do the bytes still
        match", so both become `False`: a lineage check that raised on corruption would
        make an unverifiable artifact indistinguishable from an unavailable database.
        """
        try:
            return await self._artifacts.verify(artifact_id)
        except (ArtifactIntegrityError, ArtifactNotFoundError, FileNotFoundError):
            return False

    async def store(self, data: bytes, *, media_type: str) -> ArtifactRef:
        """Put bytes through the existing store, which deduplicates by content hash.

        Identical bytes stored twice produce one blob on disk, so a learned artifact
        never adds a second copy of something the system already holds.
        """
        return await self._artifacts.put_bytes(data, media_type=media_type)

    async def build_lineage(
        self,
        *,
        lineage_id: UUID,
        artifact_id: UUID,
        role: LearnedArtifactRole,
        declared_format: LearnedArtifactFormat | str,
        component_id: str | None = None,
        dataset_id: UUID | None = None,
        producing_evidence_hash: str | None = None,
        verified_by: str,
    ) -> LearnedArtifactLineage:
        """Verify the referenced bytes, then describe them as lineage.

        The observed hash is what verification actually read, not what the caller says it
        should be. If the two disagree the contract refuses to construct the record at
        all, so an unusable lineage cannot be written and later trusted.
        """
        metadata = await self._artifacts.describe(artifact_id)
        if metadata is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.NOT_FOUND,
                f"artifact {artifact_id} is not in the Artifact Store",
            )
        if not await self.verify_artifact(artifact_id):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.INTEGRITY_FAILURE,
                f"artifact {artifact_id} does not hash to its recorded content hash",
            )
        declared = (
            declared_format.value
            if isinstance(declared_format, LearnedArtifactFormat)
            else declared_format
        )
        return LearnedArtifactLineage(
            lineage_id=lineage_id,
            artifact_id=artifact_id,
            role=role,
            component_id=component_id,
            dataset_id=dataset_id,
            media_type=metadata.media_type,
            declared_format=declared,
            declared_content_hash=metadata.content_hash,
            # Verification passed above, so what was read is what was declared. Naming
            # both makes the record self-describing rather than implying the check.
            observed_content_hash=metadata.content_hash,
            size_bytes=metadata.size_bytes,
            producing_evidence_hash=producing_evidence_hash,
            verified_by=verified_by,
            verified_at=utc_now(),
        )
