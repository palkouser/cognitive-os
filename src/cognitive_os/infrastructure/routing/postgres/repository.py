"""Transactional PostgreSQL repository for routing metadata."""

from sqlalchemy import Table, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.application.ports.capability_repository import CapabilityRepositoryPort
from cognitive_os.domain.routing import (
    ModelCapabilityProfile,
    RoutingAccessRecord,
    RoutingDecision,
    RoutingExperiment,
    RoutingObservation,
    RoutingOutcome,
    RoutingPolicyRevision,
    RoutingStatistics,
)
from cognitive_os.infrastructure.postgres.engine import postgres_transaction
from cognitive_os.routing.errors import RoutingConflictError

from .tables import (
    model_capability_profiles,
    model_capability_revisions,
    routing_accesses,
    routing_decisions,
    routing_experiments,
    routing_observations,
    routing_outcomes,
    routing_policies,
    routing_policy_revisions,
    routing_statistics,
)


class PostgresCapabilityRepository(CapabilityRepositoryPort):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def register_profile(self, profile: ModelCapabilityProfile) -> None:
        identity_hash = profile.model_identity.content_hash
        existing = await self.get_profile(identity_hash, profile.profile_revision)
        if existing is not None:
            if existing == profile:
                return
            raise RoutingConflictError("capability profile revision changed")
        if profile.profile_revision == 1:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    pg_insert(model_capability_profiles)
                    .values(
                        model_identity_hash=identity_hash,
                        provider_id=profile.model_identity.provider_id,
                        model_id=profile.model_identity.model_id,
                        current_revision=1,
                        current_status=profile.status.value,
                        current_profile_hash=profile.content_hash,
                        payload_json=profile.model_dump(mode="json"),
                        updated_at=profile.created_at,
                    )
                    .on_conflict_do_nothing()
                )
                await connection.execute(
                    pg_insert(model_capability_revisions)
                    .values(
                        model_identity_hash=identity_hash,
                        revision=1,
                        status=profile.status.value,
                        profile_hash=profile.content_hash,
                        payload_json=profile.model_dump(mode="json"),
                        created_at=profile.created_at,
                    )
                    .on_conflict_do_nothing()
                )
        else:
            async with postgres_transaction(self._engine) as connection:
                advanced = await connection.scalar(
                    text(
                        "SELECT cognitive_os.advance_model_capability_profile("
                        ":identity, :expected, :next_revision, :status, :hash, "
                        "CAST(:payload AS jsonb), :created_at)"
                    ),
                    dict(
                        identity=identity_hash,
                        expected=profile.previous_revision,
                        next_revision=profile.profile_revision,
                        status=profile.status.value,
                        hash=profile.content_hash,
                        payload=profile.model_dump_json(),
                        created_at=profile.created_at,
                    ),
                )
            if not advanced:
                raise RoutingConflictError("stale or illegal capability profile revision")
        if await self.get_profile(identity_hash, profile.profile_revision) != profile:
            raise RoutingConflictError("capability profile idempotency conflict")

    async def get_profile(
        self, model_identity_hash: str, revision: int | None = None
    ) -> ModelCapabilityProfile | None:
        table = model_capability_revisions if revision is not None else model_capability_profiles
        statement = select(table.c.payload_json).where(
            table.c.model_identity_hash == model_identity_hash
        )
        if revision is not None:
            statement = statement.where(table.c.revision == revision)
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return ModelCapabilityProfile.model_validate(payload) if payload else None

    async def query_profiles(self, *, limit: int = 256) -> tuple[ModelCapabilityProfile, ...]:
        statement = (
            select(model_capability_profiles.c.payload_json)
            .order_by(model_capability_profiles.c.model_identity_hash)
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(ModelCapabilityProfile.model_validate(payload) for payload in payloads)

    async def create_policy(self, policy: RoutingPolicyRevision) -> None:
        existing = await self.get_policy(policy.policy_id, policy.revision)
        if existing is not None:
            if existing == policy:
                return
            raise RoutingConflictError("routing policy revision changed")
        if policy.revision == 1:
            async with postgres_transaction(self._engine) as connection:
                await connection.execute(
                    pg_insert(routing_policies)
                    .values(
                        policy_id=policy.policy_id,
                        current_revision=1,
                        current_status=policy.status.value,
                        control_mode=policy.control_mode.value,
                        current_policy_hash=policy.content_hash,
                        payload_json=policy.model_dump(mode="json"),
                        updated_at=policy.created_at,
                    )
                    .on_conflict_do_nothing()
                )
                await connection.execute(
                    pg_insert(routing_policy_revisions)
                    .values(
                        policy_id=policy.policy_id,
                        revision=1,
                        status=policy.status.value,
                        control_mode=policy.control_mode.value,
                        policy_hash=policy.content_hash,
                        payload_json=policy.model_dump(mode="json"),
                        created_at=policy.created_at,
                    )
                    .on_conflict_do_nothing()
                )
        else:
            async with postgres_transaction(self._engine) as connection:
                advanced = await connection.scalar(
                    text(
                        "SELECT cognitive_os.advance_routing_policy("
                        ":policy_id, :expected, :next_revision, :status, :mode, :hash, "
                        "CAST(:payload AS jsonb), :created_at)"
                    ),
                    dict(
                        policy_id=policy.policy_id,
                        expected=policy.previous_revision,
                        next_revision=policy.revision,
                        status=policy.status.value,
                        mode=policy.control_mode.value,
                        hash=policy.content_hash,
                        payload=policy.model_dump_json(),
                        created_at=policy.created_at,
                    ),
                )
            if not advanced:
                raise RoutingConflictError("stale or illegal routing policy revision")
        if await self.get_policy(policy.policy_id, policy.revision) != policy:
            raise RoutingConflictError("routing policy idempotency conflict")

    async def get_policy(
        self, policy_id: str, revision: int | None = None
    ) -> RoutingPolicyRevision | None:
        table = routing_policy_revisions if revision is not None else routing_policies
        statement = select(table.c.payload_json).where(table.c.policy_id == policy_id)
        if revision is not None:
            statement = statement.where(table.c.revision == revision)
        async with self._engine.connect() as connection:
            payload = await connection.scalar(statement)
        return RoutingPolicyRevision.model_validate(payload) if payload else None

    async def record_observation(self, observation: RoutingObservation) -> None:
        await self._insert(
            routing_observations,
            dict(
                observation_id=observation.observation_id,
                model_identity_hash=observation.model_identity.content_hash,
                task_signature_hash=observation.task_signature.content_hash,
                evidence_type=observation.evidence_type.value,
                content_hash=observation.content_hash,
                payload_json=observation.model_dump(mode="json"),
                created_at=observation.created_at,
            ),
        )

    async def list_observations(self, *, limit: int = 10_000) -> tuple[RoutingObservation, ...]:
        statement = (
            select(routing_observations.c.payload_json)
            .order_by(routing_observations.c.observation_id)
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(RoutingObservation.model_validate(payload) for payload in payloads)

    async def record_decision(self, decision: RoutingDecision) -> None:
        await self._insert(
            routing_decisions,
            dict(
                decision_id=decision.decision_id,
                task_run_id=decision.task_run_id,
                task_signature_hash=decision.task_signature.content_hash,
                policy_id=decision.policy_id,
                policy_revision=decision.policy_revision,
                control_mode=decision.control_mode.value,
                content_hash=decision.content_hash,
                payload_json=decision.model_dump(mode="json"),
                created_at=decision.created_at,
            ),
        )

    async def record_outcome(self, outcome: RoutingOutcome) -> None:
        await self._insert(
            routing_outcomes,
            dict(
                outcome_id=outcome.outcome_id,
                decision_id=outcome.decision_id,
                status=outcome.status.value,
                content_hash=outcome.content_hash,
                payload_json=outcome.model_dump(mode="json"),
                created_at=outcome.created_at,
            ),
        )

    async def record_statistics(self, statistics: RoutingStatistics) -> None:
        await self._insert(
            routing_statistics,
            dict(
                statistics_id=statistics.statistics_id,
                model_identity_hash=statistics.model_identity_hash,
                cohort_hash=statistics.cohort.content_hash,
                content_hash=statistics.content_hash,
                payload_json=statistics.model_dump(mode="json"),
                created_at=statistics.rebuilt_at,
            ),
        )

    async def list_statistics(self, *, limit: int = 100_000) -> tuple[RoutingStatistics, ...]:
        statement = (
            select(routing_statistics.c.payload_json)
            .order_by(routing_statistics.c.statistics_id)
            .limit(limit)
        )
        async with self._engine.connect() as connection:
            payloads = (await connection.scalars(statement)).all()
        return tuple(RoutingStatistics.model_validate(payload) for payload in payloads)

    async def record_experiment(self, experiment: RoutingExperiment) -> None:
        await self._insert(
            routing_experiments,
            dict(
                experiment_id=experiment.experiment_id,
                status=experiment.status.value,
                content_hash=experiment.content_hash,
                payload_json=experiment.model_dump(mode="json"),
                created_at=experiment.created_at,
            ),
        )

    async def record_access(self, access: RoutingAccessRecord) -> None:
        await self._insert(
            routing_accesses,
            dict(
                access_id=access.access_id,
                access_type=access.access_type.value,
                content_hash=access.content_hash,
                payload_json=access.model_dump(mode="json"),
                created_at=access.accessed_at,
            ),
        )

    async def _insert(self, table: Table, values: dict[str, object]) -> None:
        async with postgres_transaction(self._engine) as connection:
            await connection.execute(pg_insert(table).values(**values).on_conflict_do_nothing())
        conditions = [column == values[column.name] for column in table.primary_key.columns]
        async with self._engine.connect() as connection:
            content_hash = await connection.scalar(select(table.c.content_hash).where(*conditions))
        if content_hash != values["content_hash"]:
            raise RoutingConflictError("routing record idempotency conflict")
