"""Persistence-neutral Context Builder boundary."""

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.context import (
    ContextBuildResult,
    ContextBundleReference,
    ContextBundleRevision,
    ContextRequest,
)


class ContextBuilderPort(Protocol):
    async def build_context(self, request: ContextRequest) -> ContextBuildResult: ...

    async def rebuild_context(
        self, request: ContextRequest, previous: ContextBundleRevision
    ) -> ContextBuildResult: ...

    async def validate_bundle(self, bundle: ContextBundleRevision) -> bool: ...

    async def load_bundle(
        self, context_bundle_id: UUID, revision: int
    ) -> ContextBundleRevision: ...

    async def record_attachment(
        self,
        request: ContextRequest,
        reference: ContextBundleReference,
        model_call_id: UUID,
    ) -> None: ...
