"""Read-only health for the durable learned evidence store.

Two categories, kept apart on purpose. An **integrity failure** means the authority is
damaged: a projection row with no history, a replay that disagrees, a hash that does not
verify, two active components on one surface. A **correlation warning** means the audit
stream lags the learned ledger, which is untidy and not wrong — the append-only history
is still complete and replayable, so it cannot make the system unhealthy.

Collapsing the two would be the expensive mistake. If a missing audit event marked the
store unhealthy, an Event Store outage would look identical to learned-state corruption,
and the alarm that matters would be the one nobody trusted. See ADR 0086.

Every query here reads. Nothing in this module writes, so it is safe against a live
database and is the same check the CLI and the release evidence run.
"""

from __future__ import annotations

from pydantic import Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.learned_evidence import (
    LearnedAccessRecord,
    LearnedActivationApproval,
    LearnedActivationReceipt,
    LearnedArtifactLineage,
    LearnedEvidenceRecord,
    LearnedObservationRecord,
)
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.infrastructure.postgres.tables import EXPECTED_MIGRATION_REVISION

from .repository import PostgresLearnedEvidenceRepository
from .tables import (
    LEARNED_APPEND_ONLY_TABLES,
    LEARNED_EVIDENCE_TABLES,
    learned_accesses,
    learned_activation_approvals,
    learned_activation_history,
    learned_artifacts,
    learned_evidence_records,
    learned_observations,
)

EXPECTED_TABLE_COUNT = len(LEARNED_EVIDENCE_TABLES)
EXPECTED_TRIGGER_COUNT = len(LEARNED_APPEND_ONLY_TABLES)

#: Every controlled function migration 0014 creates. Named rather than counted, so a
#: renamed function is reported as the specific one that went missing.
CONTROLLED_FUNCTIONS = (
    "register_learned_component",
    "advance_learned_component",
    "record_learned_evidence",
    "record_learned_observation",
    "record_learned_artifact_lineage",
    "record_learned_activation",
    "record_learned_approval",
    "record_learned_access",
    "record_learned_dataset",
    "learned_transition_is_legal",
)

#: Indexes whose absence changes behaviour rather than only performance. The partial
#: unique index is the database half of "one active component per surface"; without it
#: the rule survives only as long as the service is the only writer.
REQUIRED_INDEXES = (
    "uq_learned_components_active_surface",
    "uq_learned_revision_idempotency",
    "uq_learned_observation_idempotency",
    "uq_learned_activation_idempotency",
)

#: Which contract validates each ledger's canonical payload. Re-validating is how the
#: payload hash is checked: the contract re-seals on load and refuses a mismatch.
#: Bound to the `Table` objects rather than to names, so the query is built by SQLAlchemy
#: instead of by string formatting.
_PAYLOAD_CONTRACTS = (
    (learned_artifacts, LearnedArtifactLineage),
    (learned_evidence_records, LearnedEvidenceRecord),
    (learned_observations, LearnedObservationRecord),
    (learned_activation_approvals, LearnedActivationApproval),
    (learned_activation_history, LearnedActivationReceipt),
    (learned_accesses, LearnedAccessRecord),
)

#: How many rows per ledger the payload check re-validates. Health must stay cheap enough
#: to run often; an unbounded scan would make the check the reason it stopped being run.
PAYLOAD_SAMPLE_LIMIT = 1000


class LearnedHealthReport(ImmutableContractModel):
    """What the learned store looks like right now, and what is wrong with it."""

    healthy: bool
    migration_revision: str | None = None
    table_count: int = Field(ge=0)
    append_only_trigger_count: int = Field(ge=0)
    controlled_function_count: int = Field(ge=0)
    component_count: int = Field(ge=0)
    active_component_count: int = Field(ge=0)
    revision_count: int = Field(ge=0)
    observation_count: int = Field(ge=0)
    quarantined_observation_count: int = Field(ge=0)
    rejected_observation_count: int = Field(ge=0)
    replay_matches: bool = True
    payload_rows_verified: int = Field(default=0, ge=0)
    correlation_checked: bool = False
    #: The store is damaged. These make `healthy` false.
    integrity_failures: tuple[str, ...] = ()
    #: The audit stream lags. These never make `healthy` false.
    correlation_warnings: tuple[str, ...] = ()


class PostgresLearnedHealthService:
    """Read-only integrity inspection of the learned evidence store."""

    def __init__(self, engine: AsyncEngine, *, events: LearnedEventService | None = None) -> None:
        self._engine = engine
        self._events = events
        self._repository = PostgresLearnedEvidenceRepository(engine)

    async def check(self) -> LearnedHealthReport:
        failures: list[str] = []
        warnings: list[str] = []

        async with self._engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            tables = await self._count(
                connection,
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'cognitive_os' AND table_name LIKE 'learned\\_%'",
            )
            triggers = await self._count(
                connection,
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal "
                "AND tgname LIKE 'trg_learned_%_append_only'",
            )
            functions = await self._count(
                connection,
                "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = 'cognitive_os' AND p.proname = ANY(:names)",
                {"names": list(CONTROLLED_FUNCTIONS)},
            )
            missing_indexes = [
                name
                for name in REQUIRED_INDEXES
                if not await connection.scalar(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_indexes "
                        "WHERE schemaname = 'cognitive_os' AND indexname = :name)"
                    ),
                    {"name": name},
                )
            ]

            components = await self._count(
                connection, "SELECT count(*) FROM cognitive_os.learned_components"
            )
            revisions = await self._count(
                connection, "SELECT count(*) FROM cognitive_os.learned_component_revisions"
            )
            active = await self._count(
                connection,
                "SELECT count(*) FROM cognitive_os.learned_components "
                "WHERE current_state = 'active'",
            )
            observations = await self._count(
                connection, "SELECT count(*) FROM cognitive_os.learned_observations"
            )
            quarantined = await self._count(
                connection,
                "SELECT count(*) FROM cognitive_os.learned_observations "
                "WHERE status = 'quarantined'",
            )
            rejected = await self._count(
                connection,
                "SELECT count(*) FROM cognitive_os.learned_observations WHERE status = 'rejected'",
            )

            failures.extend(await self._structural_failures(connection))
            payload_rows = await self._verify_payloads(connection, failures)

        if revision != EXPECTED_MIGRATION_REVISION:
            failures.append(
                f"expected Alembic revision {EXPECTED_MIGRATION_REVISION}, found {revision}"
            )
        if tables != EXPECTED_TABLE_COUNT:
            failures.append(f"expected {EXPECTED_TABLE_COUNT} learned tables, found {tables}")
        if triggers != EXPECTED_TRIGGER_COUNT:
            failures.append(
                f"expected {EXPECTED_TRIGGER_COUNT} append-only triggers, found {triggers}"
            )
        if functions != len(CONTROLLED_FUNCTIONS):
            failures.append(
                f"expected {len(CONTROLLED_FUNCTIONS)} controlled functions, found {functions}"
            )
        if missing_indexes:
            failures.append(f"missing required indexes: {sorted(missing_indexes)}")

        replay = await self._repository.replay()
        if not replay.projection_matches:
            failures.extend(f"replay: {item}" for item in replay.failures)

        if self._events is not None:
            warnings.extend(await self._correlation_warnings(self._events))

        return LearnedHealthReport(
            healthy=not failures,
            migration_revision=str(revision) if revision is not None else None,
            table_count=tables,
            append_only_trigger_count=triggers,
            controlled_function_count=functions,
            component_count=components,
            active_component_count=active,
            revision_count=revisions,
            observation_count=observations,
            quarantined_observation_count=quarantined,
            rejected_observation_count=rejected,
            replay_matches=replay.projection_matches,
            payload_rows_verified=payload_rows,
            correlation_checked=self._events is not None,
            integrity_failures=tuple(failures),
            correlation_warnings=tuple(warnings),
        )

    async def _structural_failures(self, connection: object) -> list[str]:
        """Invariants the schema is supposed to make impossible, checked anyway.

        Every one of these is enforced by a constraint on a live database. They are
        re-checked because a restored dump, a manual repair or a future migration can all
        produce a table whose constraints were never applied to the rows already in it.
        """
        failures: list[str] = []
        for description, query in (
            (
                "projection rows with no lifecycle history",
                "SELECT count(*) FROM cognitive_os.learned_components c "
                "LEFT JOIN cognitive_os.learned_component_revisions r "
                "ON r.component_id = c.component_id WHERE r.component_id IS NULL",
            ),
            (
                "surfaces holding more than one active component",
                "SELECT count(*) FROM (SELECT surface FROM cognitive_os.learned_components "
                "WHERE current_state = 'active' GROUP BY surface HAVING count(*) > 1) AS s",
            ),
            (
                "active revisions without exact promotion and approval evidence",
                "SELECT count(*) FROM cognitive_os.learned_component_revisions "
                "WHERE state_after = 'active' AND (promotion_assessment_hash IS NULL "
                "OR activation_approval_hash IS NULL)",
            ),
            (
                "activation receipts naming an approval that is missing or changed",
                "SELECT count(*) FROM cognitive_os.learned_activation_history h "
                "LEFT JOIN cognitive_os.learned_activation_approvals a "
                "ON a.approval_id = h.approval_id "
                "WHERE h.action = 'activation' AND (a.approval_id IS NULL "
                "OR a.content_hash IS DISTINCT FROM h.approval_hash)",
            ),
            (
                "artifact lineage rows referencing a missing artifact",
                "SELECT count(*) FROM cognitive_os.learned_artifacts l "
                "LEFT JOIN cognitive_os.artifacts a ON a.artifact_id = l.artifact_id "
                "WHERE a.artifact_id IS NULL",
            ),
            (
                "artifact lineage rows whose hash disagrees with the Artifact Store",
                "SELECT count(*) FROM cognitive_os.learned_artifacts l "
                "JOIN cognitive_os.artifacts a ON a.artifact_id = l.artifact_id "
                "WHERE a.content_hash IS DISTINCT FROM l.declared_content_hash",
            ),
            (
                "training datasets containing real governed runs",
                "SELECT count(*) FROM cognitive_os.learned_datasets "
                "WHERE corpus_role = 'training' AND provenance_counts ? 'real_governed_run'",
            ),
            (
                "non-accepted observations marked evaluation-eligible",
                "SELECT count(*) FROM cognitive_os.learned_observations "
                "WHERE evaluation_eligible AND status <> 'accepted'",
            ),
            (
                "revision numbers with a gap in their sequence",
                "SELECT count(*) FROM (SELECT component_id FROM "
                "cognitive_os.learned_component_revisions GROUP BY component_id "
                "HAVING max(revision) <> count(*) OR min(revision) <> 1) AS g",
            ),
        ):
            found = await self._count(connection, query)
            if found:
                failures.append(f"found {found} {description}")
        return failures

    async def _verify_payloads(self, connection: object, failures: list[str]) -> int:
        """Re-validate stored payloads and compare them with their hash columns.

        Two different corruptions are caught here: a payload whose own content no longer
        hashes to its sealed `content_hash`, which the contract refuses on load, and a
        payload that is self-consistent while the indexed column beside it has drifted.
        """
        verified = 0
        for table, contract in _PAYLOAD_CONTRACTS:
            statement = (
                select(table.c.content_hash, table.c.payload_json)
                .order_by(table.c.content_hash)
                .limit(PAYLOAD_SAMPLE_LIMIT)
            )
            result = await connection.execute(statement)  # type: ignore[attr-defined]
            for row in result.mappings().all():
                payload = row["payload_json"]
                try:
                    record = contract.model_validate(payload)
                except ValueError as error:
                    failures.append(f"{table.name}: a stored payload no longer validates: {error}")
                    continue
                if record.content_hash != row["content_hash"]:
                    failures.append(
                        f"{table.name}: the content_hash column disagrees with its payload"
                    )
                verified += 1
        return verified

    async def _correlation_warnings(self, events: LearnedEventService) -> list[str]:
        """Learned records whose audit event is missing, reported as warnings only."""
        components = await self._repository.list_components(limit=500)
        expected: list[tuple[str, str, str]] = []
        for row in components:
            history = await self._repository.component_history(row.component_id, limit=500)
            expected.extend(
                (record.component_id, event_type, record.content_hash)
                for record in history
                if (event_type := _state_event_type(record.state_after.value)) is not None
            )
        gaps = await events.correlation_gaps(tuple(expected))
        return [f"{gap.subject}: {gap.detail}" for gap in gaps]

    @staticmethod
    async def _count(
        connection: object, query: str, parameters: dict[str, object] | None = None
    ) -> int:
        value = await connection.scalar(text(query), parameters or {})  # type: ignore[attr-defined]
        return int(value or 0)


def _state_event_type(state: str) -> str | None:
    """The audit event a lifecycle state should have produced, if one matches exactly.

    Imported lazily through this indirection so the infrastructure layer does not depend
    on the application service; the map itself lives with the service that emits it, so
    there is one definition of which states are deliberately uncorrelated.
    """
    from cognitive_os.application.services.learned_evidence import STATE_EVENT_TYPES
    from cognitive_os.domain.learned import LearnedComponentState

    payload = STATE_EVENT_TYPES.get(LearnedComponentState(state))
    return payload.event_type if payload is not None else None
