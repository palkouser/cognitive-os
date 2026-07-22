"""SQLAlchemy Core metadata for governed harness proposals."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from cognitive_os.infrastructure.postgres.tables import SCHEMA_NAME, metadata

harness_proposals = Table(
    "harness_proposals",
    metadata,
    Column("proposal_id", UUID(as_uuid=True), primary_key=True),
    Column("canonical_name", Text, nullable=False),
    Column("proposal_type", Text, nullable=False),
    Column("scope", Text, nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("current_signature", String(64), nullable=False),
    Column("current_content_hash", String(64), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("current_revision > 0", name="ck_harness_proposals_revision"),
    CheckConstraint(
        "current_status IN ('draft','generated','validated','staged_for_review',"
        "'approved_for_experiment','rejected','superseded','retracted')",
        name="ck_harness_proposals_status",
    ),
)

harness_proposal_revisions = Table(
    "harness_proposal_revisions",
    metadata,
    Column("proposal_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("status", Text, nullable=False),
    Column("proposal_signature", String(64), nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(["proposal_id"], [f"{SCHEMA_NAME}.harness_proposals.proposal_id"]),
    CheckConstraint("revision > 0", name="ck_harness_proposal_revisions_revision"),
    CheckConstraint(
        "(revision = 1 AND previous_revision IS NULL) OR "
        "(revision > 1 AND previous_revision = revision - 1)",
        name="ck_harness_proposal_revision_chain",
    ),
)


def _revision_history_table(name: str, primary_key: str) -> Table:
    return Table(
        name,
        metadata,
        Column(primary_key, UUID(as_uuid=True), primary_key=True),
        Column("proposal_id", UUID(as_uuid=True), nullable=False),
        Column("proposal_revision", Integer, nullable=False),
        Column("content_hash", String(64), nullable=False, unique=True),
        Column("payload_json", JSONB, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        ForeignKeyConstraint(
            ["proposal_id", "proposal_revision"],
            [
                f"{SCHEMA_NAME}.harness_proposal_revisions.proposal_id",
                f"{SCHEMA_NAME}.harness_proposal_revisions.revision",
            ],
        ),
    )


harness_proposal_sources = _revision_history_table("harness_proposal_sources", "source_record_id")
harness_proposal_alternatives = _revision_history_table(
    "harness_proposal_alternatives", "alternative_record_id"
)
harness_proposal_risks = _revision_history_table("harness_proposal_risks", "risk_record_id")
harness_proposal_validation_plans = _revision_history_table(
    "harness_proposal_validation_plans", "validation_plan_record_id"
)
harness_proposal_rollback_plans = _revision_history_table(
    "harness_proposal_rollback_plans", "rollback_plan_record_id"
)

harness_proposal_reviews = Table(
    "harness_proposal_reviews",
    metadata,
    Column("review_id", UUID(as_uuid=True), primary_key=True),
    Column("proposal_id", UUID(as_uuid=True), nullable=False),
    Column("proposal_revision", Integer, nullable=False),
    Column("decision", Text, nullable=False),
    Column("verifier_bundle_hash", String(64), nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["proposal_id", "proposal_revision"],
        [
            f"{SCHEMA_NAME}.harness_proposal_revisions.proposal_id",
            f"{SCHEMA_NAME}.harness_proposal_revisions.revision",
        ],
    ),
    CheckConstraint(
        "decision IN ('approve_for_experiment','reject','abstain')",
        name="ck_harness_proposal_review_decision",
    ),
)

harness_proposal_queue = Table(
    "harness_proposal_queue",
    metadata,
    Column("queue_record_id", UUID(as_uuid=True), primary_key=True),
    Column("record_kind", Text, nullable=False),
    Column("proposal_id", UUID(as_uuid=True), nullable=False),
    Column("proposal_revision", Integer, nullable=False),
    Column("active", Boolean, nullable=False),
    Column("operator_priority", Integer, nullable=False),
    Column("weakness_priority", Integer, nullable=False),
    Column("evidence_confidence", Numeric(5, 4), nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["proposal_id", "proposal_revision"],
        [
            f"{SCHEMA_NAME}.harness_proposal_revisions.proposal_id",
            f"{SCHEMA_NAME}.harness_proposal_revisions.revision",
        ],
    ),
    UniqueConstraint(
        "record_kind",
        "proposal_id",
        "proposal_revision",
        "content_hash",
        name="uq_harness_proposal_queue_record",
    ),
    CheckConstraint("operator_priority BETWEEN 0 AND 100", name="ck_proposal_operator_priority"),
    CheckConstraint("weakness_priority BETWEEN 0 AND 100", name="ck_proposal_weakness_priority"),
    CheckConstraint("evidence_confidence BETWEEN 0 AND 1", name="ck_proposal_evidence_confidence"),
)

harness_proposal_accesses = Table(
    "harness_proposal_accesses",
    metadata,
    Column("access_id", UUID(as_uuid=True), primary_key=True),
    Column("proposal_id", UUID(as_uuid=True), nullable=False),
    Column("proposal_revision", Integer, nullable=False),
    Column("access_type", Text, nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["proposal_id", "proposal_revision"],
        [
            f"{SCHEMA_NAME}.harness_proposal_revisions.proposal_id",
            f"{SCHEMA_NAME}.harness_proposal_revisions.revision",
        ],
    ),
)

Index(
    "ix_harness_proposal_status_type",
    harness_proposals.c.current_status,
    harness_proposals.c.proposal_type,
)
Index("ix_harness_proposal_signature", harness_proposals.c.current_signature)
Index("ix_harness_proposal_revision_signature", harness_proposal_revisions.c.proposal_signature)
Index("ix_harness_proposal_review_created", harness_proposal_reviews.c.created_at)
Index(
    "ix_harness_proposal_queue_priority",
    harness_proposal_queue.c.active,
    harness_proposal_queue.c.operator_priority,
)
Index("ix_harness_proposal_access_created", harness_proposal_accesses.c.created_at)

PROPOSAL_TABLES = (
    harness_proposals,
    harness_proposal_revisions,
    harness_proposal_sources,
    harness_proposal_alternatives,
    harness_proposal_risks,
    harness_proposal_validation_plans,
    harness_proposal_rollback_plans,
    harness_proposal_reviews,
    harness_proposal_queue,
    harness_proposal_accesses,
)

PROPOSAL_HISTORY_TABLES = PROPOSAL_TABLES[1:]
