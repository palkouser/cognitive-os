"""Provider-neutral, read-only source and weakness-mining boundaries."""

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.weakness import (
    MiningProfile,
    MiningRequest,
    MiningRunResult,
    MiningSourceReference,
    MiningSourceSnapshot,
    SignalSourceType,
    WeaknessSignal,
    WeaknessType,
)


class WeaknessSourceResolverPort(Protocol):
    @property
    def source_type(self) -> SignalSourceType: ...
    @property
    def descriptor(self) -> str: ...
    async def discover(self, request: MiningRequest) -> tuple[MiningSourceReference, ...]: ...
    async def resolve(self, source: MiningSourceReference) -> MiningSourceReference: ...
    async def health_check(self) -> bool: ...


class WeaknessSignalExtractorPort(Protocol):
    @property
    def descriptor(self) -> str: ...
    @property
    def supported_types(self) -> frozenset[WeaknessType]: ...
    async def extract(
        self, snapshot: MiningSourceSnapshot, profile: MiningProfile
    ) -> tuple[WeaknessSignal, ...]: ...
    async def health_check(self) -> bool: ...


class WeaknessMinerPort(Protocol):
    async def prepare_mining(
        self, request: MiningRequest, profile: MiningProfile
    ) -> MiningSourceSnapshot: ...
    async def mine(self, request: MiningRequest, profile: MiningProfile) -> MiningRunResult: ...
    async def resume_mining(
        self, request: MiningRequest, profile: MiningProfile
    ) -> MiningRunResult: ...
    async def cancel_mining(self, mining_run_id: UUID) -> None: ...
