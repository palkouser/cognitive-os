"""Sole Coding Agent workspace-write authority boundary."""

from typing import Protocol

from cognitive_os.domain.coding import (
    ChangedFileManifest,
    PatchApplicationResult,
    PatchProposal,
    WorkspaceDescriptor,
)


class PatchPort(Protocol):
    async def apply(
        self, workspace: WorkspaceDescriptor, proposal: PatchProposal
    ) -> PatchApplicationResult: ...

    async def rollback(
        self, workspace: WorkspaceDescriptor, revision: int
    ) -> ChangedFileManifest: ...

    async def changes(self, workspace: WorkspaceDescriptor) -> ChangedFileManifest: ...
