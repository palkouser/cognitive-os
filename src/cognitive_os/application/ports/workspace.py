"""Detached coding workspace lifecycle boundary."""

from typing import Protocol

from cognitive_os.domain.coding import (
    WorkspaceCleanupResult,
    WorkspaceDescriptor,
    WorkspaceIntegritySnapshot,
    WorkspaceRecoveryClassification,
    WorkspaceRequest,
)


class WorkspacePort(Protocol):
    async def prepare(self, request: WorkspaceRequest) -> WorkspaceDescriptor: ...

    async def integrity(self, descriptor: WorkspaceDescriptor) -> WorkspaceIntegritySnapshot: ...

    async def classify_recovery(
        self, descriptor: WorkspaceDescriptor
    ) -> WorkspaceRecoveryClassification: ...

    async def cleanup(
        self, descriptor: WorkspaceDescriptor, *, dry_run: bool = False
    ) -> WorkspaceCleanupResult: ...
