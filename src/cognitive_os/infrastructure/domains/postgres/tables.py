"""SQLAlchemy Core metadata for cross-domain pilot and transfer evidence.

Only metadata and hashes live here. Statements, derivations, solver traces, and
transfer reports stay in the Artifact Store and are referenced by hash, so the
tables cannot grow into a second evidence store.
"""

from sqlalchemy import (
    Boolean,
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

domain_pilot_runs = Table(
    "domain_pilot_runs",
    metadata,
    Column("run_id", UUID(as_uuid=True), primary_key=True),
    Column("case_id", Text, nullable=False),
    Column("domain", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("problem_hash", String(64), nullable=False),
    Column("plan_hash", String(64), nullable=False),
    Column("derivation_hash", String(64), nullable=True),
    Column("answer_hash", String(64), nullable=True),
    Column("outcome_hash", String(64), nullable=True),
    Column("failure_code", Text, nullable=True),
    Column("skill_revisions", JSONB, nullable=False),
    Column("strategy_revisions", JSONB, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "domain IN ('mathematics', 'physics', 'logic')", name="ck_domain_pilot_run_domain"
    ),
    CheckConstraint(
        "status IN ('requested', 'planned', 'executing', 'verifying', 'accepted', "
        "'partially_accepted', 'rejected', 'failed', 'cancelled')",
        name="ck_domain_pilot_run_status",
    ),
    CheckConstraint("problem_hash ~ '^[0-9a-f]{64}$'", name="ck_domain_pilot_run_problem_hash"),
)


def _reference(name: str, primary_key: str) -> Table:
    """Immutable, hash-addressed evidence row bound to exactly one run."""
    return Table(
        name,
        metadata,
        Column(primary_key, UUID(as_uuid=True), primary_key=True),
        Column("run_id", UUID(as_uuid=True), nullable=False),
        Column("record_kind", Text, nullable=False),
        Column("content_hash", String(64), nullable=False, unique=True),
        Column("artifact_id", UUID(as_uuid=True), nullable=True),
        Column("payload_json", JSONB, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        ForeignKeyConstraint(["run_id"], [f"{SCHEMA_NAME}.domain_pilot_runs.run_id"]),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name=f"ck_{name}_content_hash"),
    )


domain_problem_references = _reference("domain_problem_references", "problem_reference_id")
domain_derivation_references = _reference("domain_derivation_references", "derivation_reference_id")
domain_verification_results = _reference("domain_verification_results", "verification_result_id")
domain_accesses = _reference("domain_accesses", "access_id")

domain_transfer_experiments = Table(
    "domain_transfer_experiments",
    metadata,
    Column("experiment_id", UUID(as_uuid=True), primary_key=True),
    Column("source_domain", Text, nullable=False),
    Column("target_domain", Text, nullable=False),
    Column("unrelated_domain", Text, nullable=False),
    Column("component_kind", Text, nullable=False),
    Column("component_id", Text, nullable=False),
    Column("component_revision", Text, nullable=False),
    Column("case_manifest", Text, nullable=False),
    Column("seed", Integer, nullable=False),
    Column("environment", Text, nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "component_kind IN ('skill', 'strategy')", name="ck_domain_transfer_component_kind"
    ),
    CheckConstraint(
        "source_domain <> target_domain AND target_domain <> unrelated_domain "
        "AND source_domain <> unrelated_domain",
        name="ck_domain_transfer_distinct_domains",
    ),
    CheckConstraint("seed >= 0", name="ck_domain_transfer_seed"),
)

domain_transfer_results = Table(
    "domain_transfer_results",
    metadata,
    Column("experiment_id", UUID(as_uuid=True), primary_key=True),
    Column("disposition", Text, nullable=False),
    Column("target_quality_delta", Text, nullable=False),
    Column("source_quality_delta", Text, nullable=False),
    Column("unrelated_quality_delta", Text, nullable=False),
    Column("hard_gate_failed", Boolean, nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["experiment_id"], [f"{SCHEMA_NAME}.domain_transfer_experiments.experiment_id"]
    ),
    CheckConstraint(
        "disposition IN ('positive_transfer', 'neutral_transfer', 'negative_transfer', "
        "'inconclusive', 'invalid_experiment')",
        name="ck_domain_transfer_result_disposition",
    ),
    # A hard gate failure and a positive result are mutually exclusive in the
    # database as well as in the contract, so no writer can record both.
    CheckConstraint(
        "NOT (hard_gate_failed AND disposition = 'positive_transfer')",
        name="ck_domain_transfer_result_gate",
    ),
)

Index("ix_domain_pilot_run_domain", domain_pilot_runs.c.domain)
Index("ix_domain_pilot_run_status", domain_pilot_runs.c.status)
Index("ix_domain_pilot_run_case", domain_pilot_runs.c.case_id)
Index("ix_domain_derivation_run", domain_derivation_references.c.run_id)
Index("ix_domain_verification_run", domain_verification_results.c.run_id)
Index("ix_domain_access_created", domain_accesses.c.created_at)
Index("ix_domain_transfer_component", domain_transfer_experiments.c.component_id)

DOMAIN_TABLES = (
    domain_pilot_runs,
    domain_problem_references,
    domain_derivation_references,
    domain_verification_results,
    domain_transfer_experiments,
    domain_transfer_results,
    domain_accesses,
)

#: Everything except the run header is append-only evidence.
DOMAIN_HISTORY_TABLES = tuple(item for item in DOMAIN_TABLES if item is not domain_pilot_runs)
