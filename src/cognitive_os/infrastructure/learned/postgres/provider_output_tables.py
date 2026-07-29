"""SQLAlchemy Core metadata for the provider-output governance ledger.

One append-only table, not a provider platform. It answers exactly one question — may this
provider output be retained, and may it be offered for corpus or training use — and it
answers it in immutable revisions.

No prompt, no response body, no authorization value and no credential has a column here.
Retained bytes live in the existing content-addressed Artifact Store and are referenced by
identity and hash; the model-call lifecycle lives in the existing Event Store and is
referenced by envelope ID. Both references are real foreign keys, so a governance record
cannot outlive the evidence it claims. See ADR 0087.

There is deliberately no materialized current-state table. The latest revision is the
maximum `revision` for one `provider_output_id`, served by `ix_provider_output_latest`; a
projection would be a second authority, and Sprint 21C1 already showed what keeping one
honest costs.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from cognitive_os.infrastructure.postgres.tables import SCHEMA_NAME, metadata

#: Allowlisted values, mirrored from the domain enums as database CHECK constraints.
#: `test_provider_output_tables` asserts that each tuple equals its enum exactly, because
#: two allowlists that must agree are two allowlists that will eventually drift.
PROVIDER_ADAPTER_KINDS = ("minimax", "openrouter", "claude_code", "codex_cli", "replay", "mock")
PROVIDER_OUTPUT_INTENDED_USES = (
    "transient_advice",
    "evaluation_evidence",
    "corpus_candidate",
    "skill_candidate",
    "training_candidate",
)
PROVIDER_OUTPUT_RIGHTS_DECISIONS = ("unknown", "prohibited", "verified")
PROVIDER_OUTPUT_SCAN_STATUSES = ("not_run", "passed", "failed")
PROVIDER_OUTPUT_RETENTION_MODES = ("none", "hash_only", "normalized_content")
PROVIDER_OUTPUT_VERIFIER_STATUSES = ("not_run", "passed", "failed", "inconclusive")
#: `confidential` is absent on purpose: C1 intake does not recognise it. See ADR 0087.
PROVIDER_OUTPUT_SENSITIVITIES = ("public", "internal", "restricted")


#: Assembled outside the table so the secret-scanner allowlist markers sit on their own
#: lines rather than on constraint arguments. Both are SQL predicates, not credentials.
_NORMALIZED_CONTENT_POLICY = (
    "retention_mode <> 'normalized_content' OR ("
    "response_artifact_id IS NOT NULL AND rights_decision = 'verified' "
    "AND secret_scan_status = 'passed' "  # pragma: allowlist secret
    "AND NOT physical_deletion_required "
    "AND sensitivity IN ('public', 'internal'))"
)
_SCAN_EVIDENCE_POLICY = (
    "secret_scan_status = 'not_run' "  # pragma: allowlist secret
    "OR secret_scan_evidence_hash IS NOT NULL"
)


def _in_list(column: str, values: tuple[str, ...]) -> str:
    rendered = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({rendered})"


provider_output_records = Table(
    "provider_output_records",
    metadata,
    # The immutable row identity. `provider_output_id` is stable across revisions and is
    # therefore *not* the primary key.
    Column("provider_output_revision_id", UUID(as_uuid=True), primary_key=True),
    Column("provider_output_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("previous_revision_id", UUID(as_uuid=True), nullable=True),
    Column("schema_version", Text, nullable=False),
    # Provider identity and the call this governs.
    Column("model_call_id", UUID(as_uuid=True), nullable=False),
    Column("provider_id", Text, nullable=False),
    Column("adapter_kind", String(32), nullable=False),
    Column("requested_model", Text, nullable=False),
    Column("resolved_model", Text, nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("normalized_response_hash", String(64), nullable=False),
    # Real foreign keys. RESTRICT rather than CASCADE: a governance record whose lifecycle
    # event was deleted is not a record to clean up quietly, it is an integrity failure.
    Column(
        "completed_event_id",
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_NAME}.events.event_id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "response_artifact_id",
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_NAME}.artifacts.artifact_id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("response_artifact_hash", String(64), nullable=True),
    # Inputs by identity. The prompt body is deliberately absent.
    Column("prompt_template_id", Text, nullable=True),
    Column("prompt_template_version", Text, nullable=True),
    Column("parameter_hash", String(64), nullable=False),
    # The three decisions.
    Column("intended_use", String(32), nullable=False),
    Column("rights_decision", String(32), nullable=False),
    Column("rights_evidence_hash", String(64), nullable=True),
    Column("sensitivity", String(32), nullable=False),
    Column("secret_scan_status", String(32), nullable=False),
    Column("secret_scan_evidence_hash", String(64), nullable=True),
    Column("secret_scan_ruleset_version", Text, nullable=True),
    Column("retention_mode", String(32), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=True),
    Column("physical_deletion_required", Boolean, nullable=False),
    Column("verifier_status", String(32), nullable=False),
    Column("verifier_identity", Text, nullable=True),
    Column("verifier_evidence_hash", String(64), nullable=True),
    Column("human_reviewer", Text, nullable=True),
    # Provenance of the record itself.
    Column("recorded_by", Text, nullable=False),
    Column("idempotency_key", Text, nullable=False),
    Column("supersession_reason", Text, nullable=True),
    Column("payload_json", JSONB, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in_list("adapter_kind", PROVIDER_ADAPTER_KINDS), name="ck_provider_out_kind"),
    CheckConstraint(
        _in_list("intended_use", PROVIDER_OUTPUT_INTENDED_USES), name="ck_provider_out_use"
    ),
    CheckConstraint(
        _in_list("rights_decision", PROVIDER_OUTPUT_RIGHTS_DECISIONS), name="ck_provider_out_rights"
    ),
    CheckConstraint(
        _in_list("secret_scan_status", PROVIDER_OUTPUT_SCAN_STATUSES), name="ck_provider_out_scan"
    ),
    CheckConstraint(
        _in_list("retention_mode", PROVIDER_OUTPUT_RETENTION_MODES),
        name="ck_provider_out_retention",
    ),
    CheckConstraint(
        _in_list("verifier_status", PROVIDER_OUTPUT_VERIFIER_STATUSES),
        name="ck_provider_out_verifier",
    ),
    CheckConstraint(
        _in_list("sensitivity", PROVIDER_OUTPUT_SENSITIVITIES), name="ck_provider_out_sensitivity"
    ),
    CheckConstraint("revision >= 1", name="ck_provider_out_revision_positive"),
    # Revision continuity: the first revision has no predecessor, every later one does.
    CheckConstraint(
        "(revision = 1) = (previous_revision_id IS NULL)",
        name="ck_provider_out_revision_chain",
    ),
    # A retained artifact must carry its hash, and only normalized_content may retain one.
    CheckConstraint(
        "(response_artifact_id IS NULL) = (response_artifact_hash IS NULL)",
        name="ck_provider_out_artifact_hash",
    ),
    CheckConstraint(
        "retention_mode = 'normalized_content' OR response_artifact_id IS NULL",
        name="ck_provider_out_retention_artifact",
    ),
    # The retention policy of ADR 0087, in the database as well as the contract. Retaining
    # bytes without verified rights or a passed scan is not a bug to catch in review.
    CheckConstraint(
        _NORMALIZED_CONTENT_POLICY,
        name="ck_provider_out_normalized_content_policy",
    ),
    CheckConstraint(_SCAN_EVIDENCE_POLICY, name="ck_provider_out_scan_evidence"),
    CheckConstraint(
        "verifier_status = 'not_run' OR verifier_evidence_hash IS NOT NULL",
        name="ck_provider_out_verifier_evidence",
    ),
    # A provider cannot verify its own output.
    CheckConstraint(
        "verifier_identity IS NULL OR verifier_identity <> provider_id",
        name="ck_provider_out_independent_verifier",
    ),
    CheckConstraint(
        "expires_at IS NULL OR expires_at > recorded_at",
        name="ck_provider_out_expiry_after_record",
    ),
    UniqueConstraint("provider_output_id", "revision", name="uq_provider_output_revision"),
    UniqueConstraint("idempotency_key", name="uq_provider_output_idempotency"),
    Index("ix_provider_output_model_call", "model_call_id"),
    Index("ix_provider_output_provider", "provider_id", "adapter_kind"),
    Index("ix_provider_output_intended_use", "intended_use", "verifier_status"),
    Index("ix_provider_output_expiry", "expires_at"),
    # The latest-revision lookup. Descending revision so the head is the first row read.
    Index("ix_provider_output_latest", "provider_output_id", "revision"),
    schema=SCHEMA_NAME,
)

#: Every table migration 0015 creates.
PROVIDER_OUTPUT_TABLES = (provider_output_records,)
