"""The `0015` table metadata, held to the domain enums it mirrors.

Every CHECK allowlist in the table is a second copy of a domain enum, and the risk of a
second copy is drift: a value added to the enum and not to the constraint is a record the
contract accepts and the database refuses, which surfaces as a runtime failure in whichever
release happens to use it first.

Imports metadata only. No database, so this runs in the credential-free lane.
"""

from __future__ import annotations

from sqlalchemy import Table

from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.provider_output import (
    GOVERNED_SENSITIVITIES,
    ProviderAdapterKind,
    ProviderOutputIntendedUse,
    ProviderOutputRetentionMode,
    ProviderOutputVerifierStatus,
    SecretScanStatus,
    UsageRightsDecision,
)
from cognitive_os.infrastructure.learned.postgres.provider_output_tables import (
    PROVIDER_ADAPTER_KINDS,
    PROVIDER_OUTPUT_INTENDED_USES,
    PROVIDER_OUTPUT_RETENTION_MODES,
    PROVIDER_OUTPUT_RIGHTS_DECISIONS,
    PROVIDER_OUTPUT_SCAN_STATUSES,
    PROVIDER_OUTPUT_SENSITIVITIES,
    PROVIDER_OUTPUT_TABLES,
    PROVIDER_OUTPUT_VERIFIER_STATUSES,
    provider_output_records,
)


def _constraint_names(table: Table) -> set[str]:
    return {constraint.name for constraint in table.constraints if constraint.name}


class TestTheAllowlistsMatchTheEnums:
    def test_every_database_allowlist_equals_its_domain_enum(self) -> None:
        pairs = (
            (PROVIDER_ADAPTER_KINDS, ProviderAdapterKind),
            (PROVIDER_OUTPUT_INTENDED_USES, ProviderOutputIntendedUse),
            (PROVIDER_OUTPUT_RIGHTS_DECISIONS, UsageRightsDecision),
            (PROVIDER_OUTPUT_SCAN_STATUSES, SecretScanStatus),
            (PROVIDER_OUTPUT_RETENTION_MODES, ProviderOutputRetentionMode),
            (PROVIDER_OUTPUT_VERIFIER_STATUSES, ProviderOutputVerifierStatus),
        )
        for allowlist, enum in pairs:
            assert set(allowlist) == {item.value for item in enum}, enum.__name__

    def test_the_sensitivity_allowlist_excludes_confidential(self) -> None:
        assert set(PROVIDER_OUTPUT_SENSITIVITIES) == {item.value for item in GOVERNED_SENSITIVITIES}
        assert MemorySensitivity.CONFIDENTIAL.value not in PROVIDER_OUTPUT_SENSITIVITIES


class TestTheLedgerShape:
    def test_exactly_one_table_is_added(self) -> None:
        """A governance ledger, not a provider platform."""
        assert [table.name for table in PROVIDER_OUTPUT_TABLES] == ["provider_output_records"]

    def test_no_column_can_carry_a_prompt_response_or_credential(self) -> None:
        forbidden = {
            "prompt",
            "prompt_text",
            "response",
            "response_body",
            "raw_response",
            "content",
            "authorization",
            "api_key",
            "token",
            "credential",
        }
        assert forbidden.isdisjoint({column.name for column in provider_output_records.columns})

    def test_the_row_identity_is_the_revision_not_the_output(self) -> None:
        """Two revisions of one decision are two records; the output ID cannot be the key."""
        primary = [column.name for column in provider_output_records.primary_key]
        assert primary == ["provider_output_revision_id"]
        assert "uq_provider_output_revision" in _constraint_names(provider_output_records)

    def test_the_lifecycle_event_and_retained_artifact_are_real_foreign_keys(self) -> None:
        targets = {
            key.parent.name: key.target_fullname for key in provider_output_records.foreign_keys
        }
        assert targets["completed_event_id"] == "cognitive_os.events.event_id"
        assert targets["response_artifact_id"] == "cognitive_os.artifacts.artifact_id"
        for key in provider_output_records.foreign_keys:
            # RESTRICT, not CASCADE: a governance record whose evidence vanished is an
            # integrity failure to surface, not a row to tidy away.
            assert key.ondelete == "RESTRICT"

    def test_the_retention_policy_is_enforced_by_the_database_too(self) -> None:
        names = _constraint_names(provider_output_records)
        for expected in (
            "ck_provider_out_normalized_content_policy",
            "ck_provider_out_retention_artifact",
            "ck_provider_out_artifact_hash",
            "ck_provider_out_independent_verifier",
            "ck_provider_out_revision_chain",
            "ck_provider_out_expiry_after_record",
        ):
            assert expected in names, expected

    def test_the_latest_revision_has_an_index_and_no_projection_table(self) -> None:
        index_names = {index.name for index in provider_output_records.indexes}
        assert "ix_provider_output_latest" in index_names
        assert not any("current" in table.name for table in PROVIDER_OUTPUT_TABLES)
