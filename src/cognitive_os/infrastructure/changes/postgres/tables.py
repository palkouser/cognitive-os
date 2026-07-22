"""SQLAlchemy Core metadata for controlled-change persistence."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from cognitive_os.infrastructure.postgres.tables import SCHEMA_NAME, metadata

change_experiments = Table(
    "change_experiments",
    metadata,
    Column("experiment_id", UUID(as_uuid=True), primary_key=True),
    Column("proposal_id", UUID(as_uuid=True), nullable=False),
    Column("proposal_revision", Integer, nullable=False),
    Column("baseline_commit", String(40), nullable=False),
    Column("change_surface_tier", Text, nullable=False),
    Column("request_signature", String(64), nullable=False, unique=True),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("current_content_hash", String(64), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("current_revision > 0", name="ck_change_experiment_revision"),
)

change_experiment_revisions = Table(
    "change_experiment_revisions",
    metadata,
    Column("experiment_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("status", Text, nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(["experiment_id"], [f"{SCHEMA_NAME}.change_experiments.experiment_id"]),
    CheckConstraint(
        "(revision = 1 AND previous_revision IS NULL) OR "
        "(revision > 1 AND previous_revision = revision - 1)",
        name="ck_change_experiment_revision_chain",
    ),
)


def _history(name: str, primary_key: str) -> Table:
    return Table(
        name,
        metadata,
        Column(primary_key, UUID(as_uuid=True), primary_key=True),
        Column("experiment_id", UUID(as_uuid=True), nullable=False),
        Column("record_kind", Text, nullable=False),
        Column("content_hash", String(64), nullable=False, unique=True),
        Column("payload_json", JSONB, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        ForeignKeyConstraint(
            ["experiment_id"], [f"{SCHEMA_NAME}.change_experiments.experiment_id"]
        ),
    )


change_isolation_manifests = _history("change_isolation_manifests", "isolation_record_id")
change_candidates = _history("change_candidates", "candidate_id")
change_candidate_artifacts = _history("change_candidate_artifacts", "candidate_artifact_id")
change_evaluation_runs = _history("change_evaluation_runs", "evaluation_run_id")
change_regression_comparisons = _history("change_regression_comparisons", "comparison_id")
change_promotion_assessments = _history("change_promotion_assessments", "assessment_id")
change_promotions = _history("change_promotions", "promotion_record_id")
change_rollbacks = _history("change_rollbacks", "rollback_id")
change_accesses = _history("change_accesses", "access_id")

Index("ix_change_experiment_status", change_experiments.c.current_status)
Index("ix_change_experiment_proposal", change_experiments.c.proposal_id)
Index("ix_change_candidate_experiment", change_candidates.c.experiment_id)
Index("ix_change_evaluation_experiment", change_evaluation_runs.c.experiment_id)
Index("ix_change_promotion_experiment", change_promotions.c.experiment_id)
Index("ix_change_access_created", change_accesses.c.created_at)

CHANGE_TABLES = (
    change_experiments,
    change_experiment_revisions,
    change_isolation_manifests,
    change_candidates,
    change_candidate_artifacts,
    change_evaluation_runs,
    change_regression_comparisons,
    change_promotion_assessments,
    change_promotions,
    change_rollbacks,
    change_accesses,
)

CHANGE_HISTORY_TABLES = CHANGE_TABLES[1:]
