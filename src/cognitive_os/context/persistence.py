"""Artifact-backed persistence for immutable context projections."""

import json
from uuid import UUID

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.context import (
    ContextBundleReference,
    ContextBundleRevision,
    ContextRequest,
    ContextRetrievalTrace,
)


def _json_bytes(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


class ContextArtifactService:
    def __init__(self, store: ArtifactStorePort) -> None:
        self._store = store
        self._bundles: dict[tuple[UUID, int], ArtifactRef] = {}

    async def persist(
        self,
        request: ContextRequest,
        trace: ContextRetrievalTrace,
        bundle: ContextBundleRevision,
        rendered_context: str,
    ) -> tuple[ContextBundleRevision, ContextBundleReference, ArtifactRef, ArtifactRef]:
        request_artifact = await self._store.put_bytes(
            _json_bytes(request),
            media_type="application/vnd.cognitive-os.context-request+json",
        )
        trace_artifact = await self._store.put_bytes(
            _json_bytes(trace),
            media_type="application/vnd.cognitive-os.context-trace+json",
        )
        rendered_artifact = await self._store.put_bytes(
            rendered_context.encode(),
            media_type="text/vnd.cognitive-os.context",
        )
        persisted_bundle = ContextBundleRevision.model_validate(
            {
                **bundle.model_dump(mode="python", exclude={"content_hash"}),
                "retrieval_trace_reference": trace_artifact,
                "rendered_context_reference": rendered_artifact,
            }
        )
        bundle_artifact = await self._store.put_bytes(
            _json_bytes(persisted_bundle),
            media_type="application/vnd.cognitive-os.context-bundle+json",
        )
        key = persisted_bundle.context_bundle_id, persisted_bundle.revision
        if key in self._bundles:
            raise ValueError("Context Bundle revision already exists")
        self._bundles[key] = bundle_artifact
        reference = ContextBundleReference(
            context_bundle_id=persisted_bundle.context_bundle_id,
            context_bundle_revision=persisted_bundle.revision,
            bundle_artifact_id=bundle_artifact.artifact_id,
            rendered_context_artifact_id=rendered_artifact.artifact_id,
            content_hash=persisted_bundle.content_hash,
            source_snapshot_hash=persisted_bundle.source_snapshot.snapshot_hash,
        )
        return persisted_bundle, reference, request_artifact, bundle_artifact

    async def load(self, context_bundle_id: UUID, revision: int) -> ContextBundleRevision:
        artifact = self._bundles.get((context_bundle_id, revision))
        if artifact is None or not await self._store.verify(artifact.artifact_id):
            raise ValueError("Context Bundle artifact is missing or invalid")
        return ContextBundleRevision.model_validate_json(
            await self._store.get_bytes(artifact.artifact_id)
        )
