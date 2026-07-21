"""Transactional PostgreSQL repository for weakness diagnostics."""

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import Table, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.application.ports.weakness_repository import WeaknessRepositoryPort
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
from cognitive_os.infrastructure.postgres.engine import postgres_transaction
from cognitive_os.weakness.errors import WeaknessConflictError

from .tables import (
    weakness_accesses,
    weakness_cluster_members,
    weakness_clusters,
    weakness_impact_scores,
    weakness_items,
    weakness_mining_runs,
    weakness_revisions,
    weakness_signals,
    weakness_sources,
)


class PostgresWeaknessRepository(WeaknessRepositoryPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create_mining_run(self, request: MiningRequest) -> MiningRequest:
        existing = await self.get_mining_run_by_idempotency_key(request.idempotency_key)
        if existing is not None:
            if existing == request:
                return existing
            raise WeaknessConflictError("mining idempotency key changed")
        await self._insert(
            weakness_mining_runs,
            dict(
                mining_run_id=request.mining_run_id,
                idempotency_key=request.idempotency_key,
                scope=request.scope,
                current_status=MiningRunStatus.REQUESTED.value,
                request_hash=request.content_hash,
                payload_json=request.model_dump(mode="json"),
                created_at=request.created_at,
                updated_at=request.created_at,
            ),
            hash_column="request_hash",
        )
        return request

    async def get_mining_run_by_idempotency_key(self, key: str) -> MiningRequest | None:
        statement = select(weakness_mining_runs.c.payload_json).where(
            weakness_mining_runs.c.idempotency_key == key
        )
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return MiningRequest.model_validate(payload) if payload else None

    async def set_mining_status(self, run_id: UUID, status: MiningRunStatus) -> None:
        async with self._engine.connect() as connection:
            current = await connection.scalar(
                select(weakness_mining_runs.c.current_status).where(
                    weakness_mining_runs.c.mining_run_id == run_id
                )
            )
        if current == status.value:
            return
        if current is None:
            raise WeaknessConflictError("unknown mining run")
        async with postgres_transaction(self._engine) as connection:
            advanced = await connection.scalar(
                text(
                    "SELECT cognitive_os.advance_weakness_mining_status("
                    ":run_id, :expected, :next, now())"
                ),
                dict(run_id=run_id, expected=current, next=status.value),
            )
        if not advanced:
            raise WeaknessConflictError("illegal or stale mining status transition")

    async def record_source_snapshot(self, snapshot: MiningSourceSnapshot) -> None:
        for source in snapshot.source_refs:
            await self._insert(
                weakness_sources,
                dict(
                    source_record_id=uuid5(NAMESPACE_URL, f"weakness-source:{source.content_hash}"),
                    mining_run_id=snapshot.mining_run_id,
                    record_kind="source",
                    source_type=source.source_type.value,
                    source_identity=source.source_id,
                    source_revision=source.source_revision,
                    source_hash=source.source_content_hash,
                    content_hash=source.content_hash,
                    payload_json=source.model_dump(mode="json"),
                    created_at=snapshot.created_at,
                ),
            )

    async def record_signals(self, signals: tuple[WeaknessSignal, ...]) -> None:
        for signal in signals:
            await self._insert(
                weakness_signals,
                dict(
                    signal_id=signal.signal_id,
                    mining_run_id=signal.mining_run_id,
                    weakness_type=signal.weakness_type.value,
                    task_run_id=signal.task_run_id,
                    signature_hash=signal.task_signature.content_hash,
                    component_identity=signal.component_identity,
                    content_hash=signal.content_hash,
                    payload_json=signal.model_dump(mode="json"),
                    created_at=signal.observed_at,
                ),
            )

    async def list_signals(self, *, limit: int = 100_000) -> tuple[WeaknessSignal, ...]:
        statement = (
            select(weakness_signals.c.payload_json)
            .order_by(weakness_signals.c.signal_id)
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(WeaknessSignal.model_validate(payload) for payload in payloads)

    async def record_group_snapshot(self, snapshot: WeaknessGroupSnapshot) -> None:
        for group in snapshot.groups:
            await self._insert(
                weakness_clusters,
                dict(
                    cluster_id=group.group_id,
                    revision=group.revision,
                    snapshot_hash=snapshot.content_hash,
                    signature_hash=group.signature.content_hash,
                    cluster_method="exact_signature",
                    authoritative=True,
                    content_hash=group.content_hash,
                    payload_json=group.model_dump(mode="json"),
                    created_at=snapshot.created_at,
                ),
            )
            for member in group.members:
                await self._insert(
                    weakness_cluster_members,
                    dict(
                        member_id=uuid5(
                            NAMESPACE_URL,
                            f"weakness-group-member:{group.group_id}:{member.signal_id}",
                        ),
                        cluster_id=group.group_id,
                        cluster_revision=group.revision,
                        signal_id=member.signal_id,
                        group_hash=group.content_hash,
                        content_hash=member.content_hash,
                        payload_json=member.model_dump(mode="json"),
                        created_at=snapshot.created_at,
                    ),
                )

    async def record_cluster_snapshot(self, snapshot: WeaknessClusterSnapshot) -> None:
        for cluster in snapshot.clusters:
            await self._insert(
                weakness_clusters,
                dict(
                    cluster_id=cluster.cluster_id,
                    revision=cluster.revision,
                    snapshot_hash=snapshot.content_hash,
                    signature_hash=None,
                    cluster_method=cluster.method.value,
                    authoritative=False,
                    content_hash=cluster.content_hash,
                    payload_json=cluster.model_dump(mode="json"),
                    created_at=cluster.created_at,
                ),
            )
            for member in cluster.members:
                await self._insert(
                    weakness_cluster_members,
                    dict(
                        member_id=uuid5(
                            NAMESPACE_URL,
                            f"weakness-cluster-member:{cluster.cluster_id}:{member.group_hash}",
                        ),
                        cluster_id=cluster.cluster_id,
                        cluster_revision=cluster.revision,
                        signal_id=None,
                        group_hash=member.group_hash,
                        content_hash=member.content_hash,
                        payload_json=member.model_dump(mode="json"),
                        created_at=cluster.created_at,
                    ),
                )

    async def create_weakness(self, identity: WeaknessIdentity, revision: WeaknessRevision) -> None:
        existing = await self.get_weakness_revision(identity.weakness_id, 1)
        if existing is not None:
            if existing == revision:
                return
            raise WeaknessConflictError("initial weakness revision changed")
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(
                pg_insert(weakness_items)
                .values(
                    weakness_id=identity.weakness_id,
                    canonical_name=identity.canonical_name,
                    weakness_type=identity.weakness_type.value,
                    signature_hash=identity.signature_hash,
                    scope=identity.scope,
                    current_revision=1,
                    current_status=revision.status.value,
                    current_revision_hash=revision.content_hash,
                    payload_json=revision.model_dump(mode="json"),
                    created_at=identity.created_at,
                    updated_at=identity.created_at,
                )
                .on_conflict_do_nothing()
            )
            await connection.execute(
                pg_insert(weakness_revisions)
                .values(
                    weakness_id=revision.weakness_id,
                    revision=revision.revision,
                    status=revision.status.value,
                    revision_hash=revision.content_hash,
                    payload_json=revision.model_dump(mode="json"),
                    created_at=revision.created_at,
                )
                .on_conflict_do_nothing()
            )
        if await self.get_weakness_revision(identity.weakness_id, 1) != revision:
            raise WeaknessConflictError("weakness creation idempotency conflict")

    async def append_weakness_revision(
        self, revision: WeaknessRevision, *, expected_revision: int
    ) -> None:
        async with postgres_transaction(self._engine) as connection:
            advanced = await connection.scalar(
                text(
                    "SELECT cognitive_os.advance_weakness_revision("
                    ":weakness_id, :expected, :revision, :status, :hash, "
                    "CAST(:payload AS jsonb), :created_at)"
                ),
                dict(
                    weakness_id=revision.weakness_id,
                    expected=expected_revision,
                    revision=revision.revision,
                    status=revision.status.value,
                    hash=revision.content_hash,
                    payload=revision.model_dump_json(),
                    created_at=revision.created_at,
                ),
            )
        if not advanced:
            raise WeaknessConflictError("stale or illegal weakness revision")

    async def get_weakness_revision(
        self, weakness_id: UUID, revision: int | None = None
    ) -> WeaknessRevision | None:
        table = weakness_revisions if revision is not None else weakness_items
        statement = select(table.c.payload_json).where(table.c.weakness_id == weakness_id)
        if revision is not None:
            statement = statement.where(table.c.revision == revision)
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return WeaknessRevision.model_validate(payload) if payload else None

    async def record_impact_score(self, score: ImpactScore) -> None:
        await self._insert(
            weakness_impact_scores,
            dict(
                impact_score_id=score.impact_score_id,
                weakness_id=score.weakness_id,
                weakness_revision=score.weakness_revision,
                group_snapshot_hash=score.group_snapshot_hash,
                priority=score.priority.value,
                final_score=score.final_score,
                content_hash=score.content_hash,
                payload_json=score.model_dump(mode="json"),
                created_at=score.created_at,
            ),
        )

    async def record_evidence_package(self, package: WeaknessEvidencePackage) -> None:
        await self._record_artifact_metadata(
            identity=str(package.evidence_package_id),
            kind="evidence_package",
            content_hash=package.content_hash,
            source_hash=package.verification_hash,
            payload=package.model_dump(mode="json"),
            created_at=package.reproduction.assessed_at,
        )

    async def record_queue_entry(self, entry: WeaknessQueueEntry) -> None:
        async with postgres_transaction(self._engine) as connection:
            inserted = await connection.scalar(
                text("SELECT cognitive_os.queue_weakness(CAST(:payload AS jsonb))"),
                dict(payload=entry.model_dump_json()),
            )
        if not inserted:
            raise WeaknessConflictError("queue entry idempotency conflict")

    async def record_queue_snapshot(self, snapshot: WeaknessQueueSnapshot) -> None:
        await self._record_artifact_metadata(
            identity=str(snapshot.snapshot_id),
            kind="queue_snapshot",
            content_hash=snapshot.content_hash,
            source_hash=snapshot.queue_policy_hash,
            payload=snapshot.model_dump(mode="json"),
            created_at=snapshot.created_at,
        )

    async def record_manifest(self, manifest: MiningRunManifest) -> None:
        await self._record_artifact_metadata(
            identity=str(manifest.mining_run_id),
            kind="mining_manifest",
            content_hash=manifest.content_hash,
            source_hash=manifest.source_snapshot_hash,
            payload=manifest.model_dump(mode="json"),
            created_at=manifest.created_at,
            mining_run_id=manifest.mining_run_id,
        )

    async def record_access(self, access: WeaknessAccessRecord) -> None:
        await self._insert(
            weakness_accesses,
            dict(
                access_id=access.access_id,
                access_type=access.access_type.value,
                subject_id=access.subject_id,
                subject_revision=access.subject_revision,
                content_hash=access.content_hash,
                payload_json=access.model_dump(mode="json"),
                created_at=access.accessed_at,
            ),
        )

    async def _record_artifact_metadata(
        self,
        *,
        identity: str,
        kind: str,
        content_hash: str,
        source_hash: str,
        payload: dict[str, object],
        created_at: datetime,
        mining_run_id: UUID | None = None,
    ) -> None:
        await self._insert(
            weakness_sources,
            dict(
                source_record_id=uuid5(NAMESPACE_URL, f"weakness-{kind}:{identity}"),
                mining_run_id=mining_run_id,
                record_kind=kind,
                source_type=kind,
                source_identity=identity,
                source_revision="1",
                source_hash=source_hash,
                content_hash=content_hash,
                payload_json=payload,
                created_at=created_at,
            ),
        )

    async def _insert(
        self, table: Table, values: dict[str, object], *, hash_column: str = "content_hash"
    ) -> None:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(pg_insert(table).values(**values).on_conflict_do_nothing())
        conditions = [column == values[column.name] for column in table.primary_key.columns]
        async with self._engine.connect() as connection:
            stored_hash = await connection.scalar(
                select(getattr(table.c, hash_column)).where(*conditions)
            )
        if stored_hash != values[hash_column]:
            raise WeaknessConflictError("weakness record idempotency conflict")
