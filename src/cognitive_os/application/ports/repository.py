"""Trusted repository host-service boundary."""

from pathlib import Path
from typing import Protocol

from cognitive_os.domain.coding import RepositoryReference


class RepositoryPort(Protocol):
    async def validate(self, path: Path, base_commit: str) -> RepositoryReference: ...

    async def head(self, path: Path) -> str: ...

    async def status(self, path: Path) -> str: ...

    async def diff(self, path: Path, base_commit: str) -> str: ...
