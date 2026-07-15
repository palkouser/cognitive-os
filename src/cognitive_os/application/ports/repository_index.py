"""Bounded repository index boundary."""

from typing import Protocol

from cognitive_os.domain.coding import (
    RepositoryContextBundle,
    RepositoryIndex,
    RepositorySearchRequest,
    RepositorySearchResult,
    WorkspaceDescriptor,
)


class RepositoryIndexPort(Protocol):
    async def build(self, workspace: WorkspaceDescriptor) -> RepositoryIndex: ...

    async def search(
        self, workspace: WorkspaceDescriptor, request: RepositorySearchRequest
    ) -> tuple[RepositorySearchResult, ...]: ...

    async def context(
        self, index: RepositoryIndex, searches: tuple[RepositorySearchResult, ...]
    ) -> RepositoryContextBundle: ...
