"""SQLAlchemy Core metadata for Model Capability Registry tables."""

from typing import Any

from sqlalchemy import Column, DateTime, ForeignKeyConstraint, Index, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from cognitive_os.infrastructure.postgres.tables import SCHEMA_NAME, metadata

model_capability_profiles = Table(
    "model_capability_profiles",
    metadata,
    Column("model_identity_hash", String(64), primary_key=True),
    Column("provider_id", Text, nullable=False),
    Column("model_id", Text, nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("current_profile_hash", String(64), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

model_capability_revisions = Table(
    "model_capability_revisions",
    metadata,
    Column("model_identity_hash", String(64), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("status", Text, nullable=False),
    Column("profile_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["model_identity_hash"],
        [f"{SCHEMA_NAME}.model_capability_profiles.model_identity_hash"],
    ),
)

routing_policies = Table(
    "routing_policies",
    metadata,
    Column("policy_id", Text, primary_key=True),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("control_mode", Text, nullable=False),
    Column("current_policy_hash", String(64), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

routing_policy_revisions = Table(
    "routing_policy_revisions",
    metadata,
    Column("policy_id", Text, primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("status", Text, nullable=False),
    Column("control_mode", Text, nullable=False),
    Column("policy_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(["policy_id"], [f"{SCHEMA_NAME}.routing_policies.policy_id"]),
)


def _immutable_table(
    name: str,
    id_name: str,
    *,
    extra: tuple[Column[Any], ...] = (),
) -> Table:
    return Table(
        name,
        metadata,
        Column(id_name, UUID(as_uuid=True), primary_key=True),
        *extra,
        Column("content_hash", String(64), nullable=False, unique=True),
        Column("payload_json", JSONB, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )


routing_observations = _immutable_table(
    "routing_observations",
    "observation_id",
    extra=(
        Column("model_identity_hash", String(64), nullable=False),
        Column("task_signature_hash", String(64), nullable=False),
        Column("evidence_type", Text, nullable=False),
    ),
)
routing_decisions = _immutable_table(
    "routing_decisions",
    "decision_id",
    extra=(
        Column("task_run_id", UUID(as_uuid=True), nullable=False),
        Column("task_signature_hash", String(64), nullable=False),
        Column("policy_id", Text, nullable=False),
        Column("policy_revision", Integer, nullable=False),
        Column("control_mode", Text, nullable=False),
    ),
)
routing_outcomes = _immutable_table(
    "routing_outcomes",
    "outcome_id",
    extra=(
        Column("decision_id", UUID(as_uuid=True), nullable=False),
        Column("status", Text, nullable=False),
    ),
)
routing_statistics = _immutable_table(
    "routing_statistics",
    "statistics_id",
    extra=(
        Column("model_identity_hash", String(64), nullable=False),
        Column("cohort_hash", String(64), nullable=False),
    ),
)
routing_experiments = _immutable_table(
    "routing_experiments",
    "experiment_id",
    extra=(Column("status", Text, nullable=False),),
)
routing_accesses = _immutable_table(
    "routing_accesses",
    "access_id",
    extra=(Column("access_type", Text, nullable=False),),
)

routing_observations.append_constraint(
    ForeignKeyConstraint(
        ["model_identity_hash"],
        [f"{SCHEMA_NAME}.model_capability_profiles.model_identity_hash"],
    )
)
routing_decisions.append_constraint(
    ForeignKeyConstraint(
        ["policy_id", "policy_revision"],
        [
            f"{SCHEMA_NAME}.routing_policy_revisions.policy_id",
            f"{SCHEMA_NAME}.routing_policy_revisions.revision",
        ],
    )
)
routing_outcomes.append_constraint(
    ForeignKeyConstraint(["decision_id"], [f"{SCHEMA_NAME}.routing_decisions.decision_id"])
)
routing_statistics.append_constraint(
    ForeignKeyConstraint(
        ["model_identity_hash"],
        [f"{SCHEMA_NAME}.model_capability_profiles.model_identity_hash"],
    )
)

Index(
    "ix_model_capability_provider_model",
    model_capability_profiles.c.provider_id,
    model_capability_profiles.c.model_id,
)
Index("ix_model_capability_status", model_capability_profiles.c.current_status)
Index(
    "ix_routing_policy_status", routing_policies.c.current_status, routing_policies.c.control_mode
)
Index(
    "ix_routing_observation_cohort",
    routing_observations.c.model_identity_hash,
    routing_observations.c.task_signature_hash,
)
Index("ix_routing_decision_task", routing_decisions.c.task_run_id)
Index("ix_routing_outcome_decision", routing_outcomes.c.decision_id)
Index(
    "ix_routing_statistics_cohort",
    routing_statistics.c.model_identity_hash,
    routing_statistics.c.cohort_hash,
)
Index("ix_routing_access_time", routing_accesses.c.created_at)

ROUTING_TABLES = (
    model_capability_profiles,
    model_capability_revisions,
    routing_policies,
    routing_policy_revisions,
    routing_observations,
    routing_decisions,
    routing_outcomes,
    routing_statistics,
    routing_experiments,
    routing_accesses,
)
ROUTING_HISTORY_TABLES = (
    model_capability_revisions,
    routing_policy_revisions,
    routing_observations,
    routing_decisions,
    routing_outcomes,
    routing_statistics,
    routing_experiments,
    routing_accesses,
)
