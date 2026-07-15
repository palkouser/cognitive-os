"""SQLAlchemy Core metadata for temporal semantic-memory tables."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from cognitive_os.infrastructure.postgres.tables import SCHEMA_NAME, metadata

semantic_observations = Table(
    "semantic_observations",
    metadata,
    Column("observation_id", UUID(as_uuid=True), primary_key=True),
    Column("idempotency_key", String(64), nullable=False, unique=True),
    Column("content", Text, nullable=False),
    Column("normalized_content", Text, nullable=False),
    Column("source_refs_json", JSONB, nullable=False),
    Column("source_spans_json", JSONB, nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("scope_type", Text, nullable=False),
    Column("scope_id", Text, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("created_by_type", Text, nullable=False),
    Column("created_by_id", Text, nullable=False),
    Column("content_hash", String(64), nullable=False),
    CheckConstraint(
        "confidence >= 0 AND confidence <= 1", name="ck_semantic_observation_confidence"
    ),
    CheckConstraint("recorded_at >= observed_at", name="ck_semantic_observation_recorded"),
    CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_semantic_observation_hash"),
)

semantic_claims = Table(
    "semantic_claims",
    metadata,
    Column("claim_id", UUID(as_uuid=True), primary_key=True),
    Column("idempotency_key", String(64), nullable=False, unique=True),
    Column("scope_type", Text, nullable=False),
    Column("scope_id", Text, nullable=False),
    Column("canonical_subject_key", String(1024), nullable=False),
    Column("predicate_id", String(256), nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("current_belief_status", Text, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("created_by_type", Text, nullable=False),
    Column("created_by_id", Text, nullable=False),
    CheckConstraint("current_revision > 0", name="ck_semantic_claim_current_revision"),
    CheckConstraint(
        "current_belief_status IN "
        "('proposed','supported','disputed','superseded','retracted','unknown')",
        name="ck_semantic_claim_status",
    ),
)

semantic_claim_revisions = Table(
    "semantic_claim_revisions",
    metadata,
    Column("claim_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("object_json", JSONB, nullable=False),
    Column("statement", Text, nullable=False),
    Column("belief_status", Text, nullable=False),
    Column("confidence_json", JSONB, nullable=False),
    Column("overall_confidence", Float, nullable=False),
    Column("valid_from", DateTime(timezone=True), nullable=False),
    Column("valid_to", DateTime(timezone=True), nullable=True),
    Column("reason", Text, nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("created_by_type", Text, nullable=False),
    Column("created_by_id", Text, nullable=False),
    Column("evidence_snapshot_hash", String(64), nullable=False),
    Column("promotion_decision_id", UUID(as_uuid=True), nullable=True),
    Column("content_hash", String(64), nullable=False),
    ForeignKeyConstraint(
        ["claim_id"], [f"{SCHEMA_NAME}.semantic_claims.claim_id"], ondelete="RESTRICT"
    ),
    ForeignKeyConstraint(
        ["claim_id", "previous_revision"],
        [
            f"{SCHEMA_NAME}.semantic_claim_revisions.claim_id",
            f"{SCHEMA_NAME}.semantic_claim_revisions.revision",
        ],
        ondelete="RESTRICT",
        name="fk_semantic_claim_revision_previous",
    ),
    CheckConstraint(
        "(revision = 1 AND previous_revision IS NULL) OR previous_revision = revision - 1",
        name="ck_semantic_claim_revision_sequence",
    ),
    CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_semantic_valid_interval"),
    CheckConstraint("octet_length(statement) <= 8192", name="ck_semantic_statement_size"),
    CheckConstraint(
        "overall_confidence >= 0 AND overall_confidence <= 1", name="ck_semantic_confidence"
    ),
)

semantic_claim_evidence = Table(
    "semantic_claim_evidence",
    metadata,
    Column("evidence_id", UUID(as_uuid=True), primary_key=True),
    Column("claim_id", UUID(as_uuid=True), nullable=False),
    Column("claim_revision", Integer, nullable=False),
    Column("source_type", Text, nullable=False),
    Column("source_id", UUID(as_uuid=True), nullable=False),
    Column("source_revision", Integer, nullable=True),
    Column("source_hash", String(64), nullable=False),
    Column("source_span_json", JSONB, nullable=False),
    Column("relation", Text, nullable=False),
    Column("strength", Float, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("created_by_type", Text, nullable=False),
    Column("created_by_id", Text, nullable=False),
    ForeignKeyConstraint(
        ["claim_id", "claim_revision"],
        [
            f"{SCHEMA_NAME}.semantic_claim_revisions.claim_id",
            f"{SCHEMA_NAME}.semantic_claim_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    UniqueConstraint(
        "claim_id",
        "claim_revision",
        "source_type",
        "source_id",
        "source_revision",
        "relation",
        name="uq_semantic_evidence_identity",
        postgresql_nulls_not_distinct=True,
    ),
    CheckConstraint("strength >= 0 AND strength <= 1", name="ck_semantic_evidence_strength"),
)

semantic_claim_relations = Table(
    "semantic_claim_relations",
    metadata,
    Column("relation_id", UUID(as_uuid=True), primary_key=True),
    Column("source_claim_id", UUID(as_uuid=True), nullable=False),
    Column("source_revision", Integer, nullable=False),
    Column("target_claim_id", UUID(as_uuid=True), nullable=False),
    Column("target_revision", Integer, nullable=False),
    Column("relation_type", Text, nullable=False),
    Column("valid_from", DateTime(timezone=True), nullable=False),
    Column("valid_to", DateTime(timezone=True), nullable=True),
    Column("provenance_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["source_claim_id", "source_revision"],
        [
            f"{SCHEMA_NAME}.semantic_claim_revisions.claim_id",
            f"{SCHEMA_NAME}.semantic_claim_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["target_claim_id", "target_revision"],
        [
            f"{SCHEMA_NAME}.semantic_claim_revisions.claim_id",
            f"{SCHEMA_NAME}.semantic_claim_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    UniqueConstraint(
        "source_claim_id",
        "source_revision",
        "target_claim_id",
        "target_revision",
        "relation_type",
        name="uq_semantic_claim_relation",
    ),
)

semantic_contradictions = Table(
    "semantic_contradictions",
    metadata,
    Column("contradiction_id", UUID(as_uuid=True), primary_key=True),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

semantic_contradiction_revisions = Table(
    "semantic_contradiction_revisions",
    metadata,
    Column("contradiction_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("status", Text, nullable=False),
    Column("severity", Text, nullable=False),
    Column("evidence_ids_json", JSONB, nullable=False),
    Column("reason", Text, nullable=False),
    Column("resolver_json", JSONB, nullable=True),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column("content_hash", String(64), nullable=False),
    ForeignKeyConstraint(
        ["contradiction_id"],
        [f"{SCHEMA_NAME}.semantic_contradictions.contradiction_id"],
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["contradiction_id", "previous_revision"],
        [
            f"{SCHEMA_NAME}.semantic_contradiction_revisions.contradiction_id",
            f"{SCHEMA_NAME}.semantic_contradiction_revisions.revision",
        ],
        ondelete="RESTRICT",
        name="fk_semantic_contradiction_previous",
    ),
    CheckConstraint(
        "(revision = 1 AND previous_revision IS NULL) OR previous_revision = revision - 1",
        name="ck_semantic_contradiction_sequence",
    ),
)

semantic_contradiction_claims = Table(
    "semantic_contradiction_claims",
    metadata,
    Column("contradiction_id", UUID(as_uuid=True), primary_key=True),
    Column("contradiction_revision", Integer, primary_key=True),
    Column("claim_id", UUID(as_uuid=True), primary_key=True),
    Column("claim_revision", Integer, primary_key=True),
    ForeignKeyConstraint(
        ["contradiction_id", "contradiction_revision"],
        [
            f"{SCHEMA_NAME}.semantic_contradiction_revisions.contradiction_id",
            f"{SCHEMA_NAME}.semantic_contradiction_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["claim_id", "claim_revision"],
        [
            f"{SCHEMA_NAME}.semantic_claim_revisions.claim_id",
            f"{SCHEMA_NAME}.semantic_claim_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
)

wiki_pages = Table(
    "wiki_pages",
    metadata,
    Column("page_id", UUID(as_uuid=True), primary_key=True),
    Column("scope_type", Text, nullable=False),
    Column("scope_id", Text, nullable=False),
    Column("canonical_subject_key", String(1024), nullable=False),
    Column("page_type", Text, nullable=False),
    Column("domain", Text, nullable=True),
    Column("current_revision", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "scope_type",
        "scope_id",
        "canonical_subject_key",
        "page_type",
        "domain",
        name="uq_wiki_page_identity",
        postgresql_nulls_not_distinct=True,
    ),
    CheckConstraint("current_revision >= 0", name="ck_wiki_current_revision"),
)

wiki_page_revisions = Table(
    "wiki_page_revisions",
    metadata,
    Column("page_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("renderer_version", Text, nullable=False),
    Column("markdown", Text, nullable=False),
    Column("valid_at", DateTime(timezone=True), nullable=True),
    Column("known_at", DateTime(timezone=True), nullable=True),
    Column("rendered_at", DateTime(timezone=True), nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("snapshot_hash", String(64), nullable=False),
    ForeignKeyConstraint(["page_id"], [f"{SCHEMA_NAME}.wiki_pages.page_id"], ondelete="RESTRICT"),
    ForeignKeyConstraint(
        ["page_id", "previous_revision"],
        [
            f"{SCHEMA_NAME}.wiki_page_revisions.page_id",
            f"{SCHEMA_NAME}.wiki_page_revisions.revision",
        ],
        ondelete="RESTRICT",
        name="fk_wiki_revision_previous",
    ),
    CheckConstraint(
        "(revision = 1 AND previous_revision IS NULL) OR previous_revision = revision - 1",
        name="ck_wiki_revision_sequence",
    ),
    CheckConstraint("octet_length(markdown) <= 262144", name="ck_wiki_markdown_size"),
)

wiki_page_claims = Table(
    "wiki_page_claims",
    metadata,
    Column("page_id", UUID(as_uuid=True), primary_key=True),
    Column("page_revision", Integer, primary_key=True),
    Column("claim_id", UUID(as_uuid=True), primary_key=True),
    Column("claim_revision", Integer, primary_key=True),
    Column("section", Text, nullable=False),
    Column("display_order", Integer, nullable=False),
    ForeignKeyConstraint(
        ["page_id", "page_revision"],
        [
            f"{SCHEMA_NAME}.wiki_page_revisions.page_id",
            f"{SCHEMA_NAME}.wiki_page_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["claim_id", "claim_revision"],
        [
            f"{SCHEMA_NAME}.semantic_claim_revisions.claim_id",
            f"{SCHEMA_NAME}.semantic_claim_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    UniqueConstraint(
        "page_id", "page_revision", "section", "display_order", name="uq_wiki_display_order"
    ),
)

semantic_accesses = Table(
    "semantic_accesses",
    metadata,
    Column("access_id", UUID(as_uuid=True), primary_key=True),
    Column("query_id", UUID(as_uuid=True), nullable=False),
    Column("task_run_id", UUID(as_uuid=True), nullable=True),
    Column("claim_id", UUID(as_uuid=True), nullable=False),
    Column("claim_revision", Integer, nullable=False),
    Column("query_mode", Text, nullable=False),
    Column("valid_at", DateTime(timezone=True), nullable=True),
    Column("known_at", DateTime(timezone=True), nullable=True),
    Column("rank", Integer, nullable=False),
    Column("scope_type", Text, nullable=False),
    Column("scope_id", Text, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("query_hash", String(64), nullable=False),
    Column("accessed_at", DateTime(timezone=True), nullable=False),
    Column("used_in_wiki", Boolean, nullable=False, server_default="false"),
    ForeignKeyConstraint(
        ["claim_id", "claim_revision"],
        [
            f"{SCHEMA_NAME}.semantic_claim_revisions.claim_id",
            f"{SCHEMA_NAME}.semantic_claim_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    CheckConstraint("rank > 0", name="ck_semantic_access_rank"),
)

SEMANTIC_TABLES = (
    semantic_observations,
    semantic_claims,
    semantic_claim_revisions,
    semantic_claim_evidence,
    semantic_claim_relations,
    semantic_contradictions,
    semantic_contradiction_revisions,
    semantic_contradiction_claims,
    wiki_pages,
    wiki_page_revisions,
    wiki_page_claims,
    semantic_accesses,
)

SEMANTIC_HISTORY_TABLES = (
    semantic_observations,
    semantic_claim_revisions,
    semantic_claim_evidence,
    semantic_claim_relations,
    semantic_contradiction_revisions,
    semantic_contradiction_claims,
    wiki_page_revisions,
    wiki_page_claims,
    semantic_accesses,
)

Index(
    "ix_semantic_claim_scope_status",
    semantic_claims.c.scope_type,
    semantic_claims.c.scope_id,
    semantic_claims.c.current_belief_status,
)
Index(
    "ix_semantic_claim_subject_predicate",
    semantic_claims.c.canonical_subject_key,
    semantic_claims.c.predicate_id,
)
Index(
    "ix_semantic_revision_valid",
    semantic_claim_revisions.c.valid_from,
    semantic_claim_revisions.c.valid_to,
)
Index("ix_semantic_revision_recorded", semantic_claim_revisions.c.recorded_at)
Index(
    "ix_semantic_evidence_source",
    semantic_claim_evidence.c.source_type,
    semantic_claim_evidence.c.source_id,
    semantic_claim_evidence.c.source_revision,
)
Index(
    "ix_semantic_relation_source",
    semantic_claim_relations.c.source_claim_id,
    semantic_claim_relations.c.source_revision,
)
Index(
    "ix_semantic_relation_target",
    semantic_claim_relations.c.target_claim_id,
    semantic_claim_relations.c.target_revision,
)
Index(
    "ix_semantic_contradiction_status",
    semantic_contradictions.c.current_status,
    semantic_contradictions.c.severity,
)
Index(
    "ix_wiki_subject_scope",
    wiki_pages.c.canonical_subject_key,
    wiki_pages.c.scope_type,
    wiki_pages.c.scope_id,
)
Index("ix_semantic_access_query", semantic_accesses.c.query_id, semantic_accesses.c.accessed_at)
