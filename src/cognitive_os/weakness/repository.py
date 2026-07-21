"""Dependency-light append-only weakness repository."""

from typing import Any
from uuid import UUID

from cognitive_os.domain.weakness import (
    ImpactScore,
    MiningRequest,
    MiningRunManifest,
    MiningRunStatus,
    MiningSourceSnapshot,
    WeaknessAccessRecord,
    WeaknessClusterSnapshot,
    WeaknessEvidencePackage,
    WeaknessGroupSnapshot,
    WeaknessIdentity,
    WeaknessQueueEntry,
    WeaknessQueueSnapshot,
    WeaknessRevision,
    WeaknessSignal,
)

from .errors import WeaknessConflictError


class InMemoryWeaknessRepository:
    def __init__(self) -> None:
        self.requests: dict[UUID, MiningRequest] = {}
        self.idempotency_keys: dict[str, UUID] = {}
        self.run_statuses: dict[UUID, MiningRunStatus] = {}
        self.source_snapshots: dict[UUID, MiningSourceSnapshot] = {}
        self.signals: dict[UUID, WeaknessSignal] = {}
        self.group_snapshots: dict[UUID, WeaknessGroupSnapshot] = {}
        self.cluster_snapshots: dict[UUID, WeaknessClusterSnapshot] = {}
        self.identities: dict[UUID, WeaknessIdentity] = {}
        self.revisions: dict[tuple[UUID, int], WeaknessRevision] = {}
        self.impact_scores: dict[UUID, ImpactScore] = {}
        self.evidence_packages: dict[UUID, WeaknessEvidencePackage] = {}
        self.queue_entries: dict[UUID, WeaknessQueueEntry] = {}
        self.queue_snapshots: dict[UUID, WeaknessQueueSnapshot] = {}
        self.manifests: dict[UUID, MiningRunManifest] = {}
        self.accesses: dict[UUID, WeaknessAccessRecord] = {}

    async def create_mining_run(self, request: MiningRequest) -> MiningRequest:
        known_id = self.idempotency_keys.get(request.idempotency_key)
        if known_id is not None:
            known = self.requests[known_id]
            if known != request:
                raise WeaknessConflictError("mining idempotency key changed")
            return known
        await self._immutable(self.requests, request.mining_run_id, request)
        self.idempotency_keys[request.idempotency_key] = request.mining_run_id
        self.run_statuses[request.mining_run_id] = MiningRunStatus.REQUESTED
        return request

    async def get_mining_run_by_idempotency_key(self, key: str) -> MiningRequest | None:
        run_id = self.idempotency_keys.get(key)
        return self.requests.get(run_id) if run_id else None

    async def set_mining_status(self, run_id: UUID, status: MiningRunStatus) -> None:
        if run_id not in self.requests:
            raise WeaknessConflictError("unknown mining run")
        self.run_statuses[run_id] = status

    async def record_source_snapshot(self, snapshot: MiningSourceSnapshot) -> None:
        await self._immutable(self.source_snapshots, snapshot.mining_run_id, snapshot)

    async def record_signals(self, signals: tuple[WeaknessSignal, ...]) -> None:
        for signal in signals:
            if signal.mining_run_id not in self.requests:
                raise WeaknessConflictError("signal references an unknown mining run")
            await self._immutable(self.signals, signal.signal_id, signal)

    async def list_signals(self, *, limit: int = 100_000) -> tuple[WeaknessSignal, ...]:
        return tuple(sorted(self.signals.values(), key=lambda item: str(item.signal_id))[:limit])

    async def record_group_snapshot(self, snapshot: WeaknessGroupSnapshot) -> None:
        await self._immutable(self.group_snapshots, snapshot.snapshot_id, snapshot)

    async def record_cluster_snapshot(self, snapshot: WeaknessClusterSnapshot) -> None:
        await self._immutable(self.cluster_snapshots, snapshot.snapshot_id, snapshot)

    async def create_weakness(self, identity: WeaknessIdentity, revision: WeaknessRevision) -> None:
        if revision.weakness_id != identity.weakness_id or revision.revision != 1:
            raise WeaknessConflictError("initial weakness revision is invalid")
        await self._immutable(self.identities, identity.weakness_id, identity)
        await self._immutable(self.revisions, (identity.weakness_id, 1), revision)

    async def append_weakness_revision(
        self, revision: WeaknessRevision, *, expected_revision: int
    ) -> None:
        current = await self.get_weakness_revision(revision.weakness_id)
        if current is None or current.revision != expected_revision:
            raise WeaknessConflictError("weakness revision compare-and-set failed")
        if revision.revision != expected_revision + 1:
            raise WeaknessConflictError("weakness revision is not contiguous")
        await self._immutable(self.revisions, (revision.weakness_id, revision.revision), revision)

    async def get_weakness_revision(
        self, weakness_id: UUID, revision: int | None = None
    ) -> WeaknessRevision | None:
        if revision is not None:
            return self.revisions.get((weakness_id, revision))
        revisions = [
            item for (identity, _), item in self.revisions.items() if identity == weakness_id
        ]
        return max(revisions, key=lambda item: item.revision, default=None)

    async def record_impact_score(self, score: ImpactScore) -> None:
        await self._immutable(self.impact_scores, score.impact_score_id, score)

    async def record_evidence_package(self, package: WeaknessEvidencePackage) -> None:
        await self._immutable(self.evidence_packages, package.evidence_package_id, package)

    async def record_queue_entry(self, entry: WeaknessQueueEntry) -> None:
        await self._immutable(self.queue_entries, entry.queue_entry_id, entry)

    async def record_queue_snapshot(self, snapshot: WeaknessQueueSnapshot) -> None:
        await self._immutable(self.queue_snapshots, snapshot.snapshot_id, snapshot)

    async def record_manifest(self, manifest: MiningRunManifest) -> None:
        await self._immutable(self.manifests, manifest.mining_run_id, manifest)

    async def record_access(self, access: WeaknessAccessRecord) -> None:
        await self._immutable(self.accesses, access.access_id, access)

    @staticmethod
    async def _immutable(store: dict[Any, Any], key: object, value: object) -> None:
        existing = store.get(key)
        if existing is not None and existing != value:
            raise WeaknessConflictError("immutable weakness record changed")
        store[key] = value
