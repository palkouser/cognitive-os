"""Provider-output governance contracts: hashing, refusals and eligibility.

Every refusal here has a consequence somebody would otherwise have to remember. The tests
are written as "what would have to be true for this to be wrong", not as field-by-field
coverage: a contract that only rejects what its own validator lists is a contract nobody
has tested against.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from cognitive_os.application.services.learned_intake import KNOWN_SENSITIVITIES
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.provider_output import (
    GOVERNED_SENSITIVITIES,
    PROVIDER_OUTPUT_SCHEMA_VERSION,
    ProviderOutputIntendedUse,
    ProviderOutputRetentionMode,
    ProviderOutputVerifierStatus,
    ProviderRetentionDirective,
    SecretScanStatus,
    UsageRightsDecision,
)

from . import fixtures as fx


class TestHashingIsCanonical:
    def test_identical_records_hash_identically(self) -> None:
        assert fx.record().content_hash == fx.record().content_hash

    def test_one_changed_field_changes_the_hash(self) -> None:
        """Every field, not a sampled few: an unhashed field is a field that can be edited."""
        baseline = fx.record()
        variants = {
            "resolved_model": "vendor/other:free",
            "requested_model": "openrouter/paid",
            "provider_id": "codex-cli",
            "normalized_response_hash": fx.HASH_C,
            "request_hash": fx.HASH_B,
            "parameter_hash": fx.HASH_A,
            "intended_use": ProviderOutputIntendedUse.EVALUATION_EVIDENCE,
            "rights_decision": UsageRightsDecision.PROHIBITED,
            "sensitivity": MemorySensitivity.INTERNAL,
            "retention_mode": ProviderOutputRetentionMode.NONE,
            "verifier_status": ProviderOutputVerifierStatus.INCONCLUSIVE,
            "recorded_by": "someone-else",
            "idempotency_key": "provider-output:other",
        }
        for field, value in variants.items():
            changed = fx.record(**{field: value})
            assert changed.content_hash != baseline.content_hash, field

    def test_a_declared_hash_that_disagrees_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="hash mismatch"):
            fx.record(content_hash="f" * 64)

    def test_the_schema_version_is_recorded(self) -> None:
        assert fx.record().schema_version == PROVIDER_OUTPUT_SCHEMA_VERSION


class TestRetentionFailsClosed:
    def test_normalized_content_needs_verified_rights(self) -> None:
        with pytest.raises(ValidationError, match="verified usage rights"):
            fx.record(
                retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
                response_artifact_id=fx.OUTPUT_ID,
                response_artifact_hash=fx.HASH_A,
                rights_decision=UsageRightsDecision.UNKNOWN,
                rights_evidence_hash=None,
            )

    def test_normalized_content_needs_a_passed_scan(self) -> None:
        with pytest.raises(ValidationError, match="passed secret scan"):
            fx.record(
                retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
                response_artifact_id=fx.OUTPUT_ID,
                response_artifact_hash=fx.HASH_A,
                secret_scan_status=SecretScanStatus.FAILED,
            )

    def test_normalized_content_cannot_promise_deletion_it_cannot_perform(self) -> None:
        """The Artifact Store is immutable. A deletion obligation must downgrade retention."""
        with pytest.raises(ValidationError, match="physical-deletion"):
            fx.record(
                retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
                response_artifact_id=fx.OUTPUT_ID,
                response_artifact_hash=fx.HASH_A,
                physical_deletion_required=True,
            )

    def test_restricted_content_is_governable_but_not_storable(self) -> None:
        with pytest.raises(ValidationError, match="may not be written"):
            fx.record(
                retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
                response_artifact_id=fx.OUTPUT_ID,
                response_artifact_hash=fx.HASH_A,
                sensitivity=MemorySensitivity.RESTRICTED,
            )

    def test_hash_only_and_none_must_not_name_an_artifact(self) -> None:
        for mode in (ProviderOutputRetentionMode.HASH_ONLY, ProviderOutputRetentionMode.NONE):
            with pytest.raises(ValidationError, match="must not name a response artifact"):
                fx.record(
                    retention_mode=mode,
                    response_artifact_id=fx.OUTPUT_ID,
                    response_artifact_hash=fx.HASH_A,
                )

    def test_an_artifact_reference_must_carry_its_hash(self) -> None:
        with pytest.raises(ValidationError, match="must carry its content hash"):
            fx.record(
                retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
                response_artifact_id=fx.OUTPUT_ID,
            )

    def test_the_directive_refuses_the_same_combinations_before_a_call_is_made(self) -> None:
        with pytest.raises(ValidationError, match="physical-deletion"):
            fx.directive(
                retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
                physical_deletion_required=True,
            )
        with pytest.raises(ValidationError, match="may not be written"):
            fx.directive(
                retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
                sensitivity=MemorySensitivity.RESTRICTED,
            )

    def test_the_default_directive_retains_nothing(self) -> None:
        default = ProviderRetentionDirective(
            intended_use=ProviderOutputIntendedUse.TRANSIENT_ADVICE
        )
        assert default.retention_mode is ProviderOutputRetentionMode.NONE
        assert default.physical_deletion_required is False


class TestNoProviderIsItsOwnVerifier:
    def test_a_verifier_identity_equal_to_the_provider_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="cannot verify its own output"):
            fx.record(verifier_identity="openrouter")

    def test_a_verifier_that_ran_must_record_evidence(self) -> None:
        with pytest.raises(ValidationError, match="must record its evidence hash"):
            fx.record(verifier_evidence_hash=None)

    def test_evidence_must_name_the_verifier_that_produced_it(self) -> None:
        with pytest.raises(ValidationError, match="must name the verifier"):
            fx.record(
                verifier_status=ProviderOutputVerifierStatus.NOT_RUN,
                verifier_identity=None,
                verifier_evidence_hash=fx.HASH_C,
            )


class TestRevisionLineage:
    def test_the_first_revision_names_no_predecessor(self) -> None:
        with pytest.raises(ValidationError, match="cannot name a predecessor"):
            fx.record(previous_revision_id=fx.REVISION_TWO_ID)

    def test_a_later_revision_must_name_one(self) -> None:
        with pytest.raises(ValidationError, match="must name the revision it supersedes"):
            fx.record(revision=2, previous_revision_id=None)

    def test_a_revision_cannot_supersede_itself(self) -> None:
        with pytest.raises(ValidationError, match="cannot supersede itself"):
            fx.record(revision=2, previous_revision_id=fx.REVISION_ONE_ID)

    def test_a_correction_chains_and_keeps_the_stable_output_identity(self) -> None:
        first = fx.record()
        second = fx.superseding_record(first, rights_decision=UsageRightsDecision.PROHIBITED)
        assert second.provider_output_id == first.provider_output_id
        assert second.previous_revision_id == first.provider_output_revision_id
        assert second.revision == 2
        assert second.content_hash != first.content_hash


class TestEligibilityFailsClosed:
    def test_a_fully_governed_corpus_candidate_is_selectable(self) -> None:
        record = fx.record()
        assert record.selection_refusals(fx.FIXTURE_NOW) == ()
        assert record.is_selectable_at(fx.FIXTURE_NOW)

    @pytest.mark.parametrize(
        ("overrides", "expected"),
        [
            (
                {"rights_decision": UsageRightsDecision.UNKNOWN, "rights_evidence_hash": None},
                "usage rights are unknown",
            ),
            (
                {"rights_decision": UsageRightsDecision.PROHIBITED, "rights_evidence_hash": None},
                "usage rights are prohibited",
            ),
            ({"secret_scan_status": SecretScanStatus.FAILED}, "secret scan is failed"),
            (
                {"secret_scan_status": SecretScanStatus.NOT_RUN, "secret_scan_evidence_hash": None},
                "secret scan is not_run",
            ),
            (
                {"verifier_status": ProviderOutputVerifierStatus.INCONCLUSIVE},
                "verifier status is inconclusive",
            ),
            (
                {
                    "verifier_status": ProviderOutputVerifierStatus.NOT_RUN,
                    "verifier_identity": None,
                    "verifier_evidence_hash": None,
                },
                "verifier status is not_run",
            ),
            ({"physical_deletion_required": True}, "a physical-deletion obligation applies"),
            (
                {"intended_use": ProviderOutputIntendedUse.TRANSIENT_ADVICE},
                "intended use transient_advice is not a material use",
            ),
        ],
    )
    def test_each_missing_condition_refuses_selection(
        self, overrides: dict[str, object], expected: str
    ) -> None:
        record = fx.record(**overrides)
        assert expected in record.selection_refusals(fx.FIXTURE_NOW)
        assert not record.is_selectable_at(fx.FIXTURE_NOW)

    def test_expiry_is_exact_and_governs_selection_only(self) -> None:
        expiry = fx.FIXTURE_NOW + timedelta(hours=1)
        record = fx.record(expires_at=expiry)
        assert record.is_selectable_at(expiry - timedelta(microseconds=1))
        assert not record.is_selectable_at(expiry)
        assert record.is_expired_at(expiry)
        # Expiry says nothing about bytes: this record retains none in the first place, and
        # a normalized-content record would keep its artifact after expiring too.
        assert record.retention_mode is ProviderOutputRetentionMode.HASH_ONLY

    def test_an_expiry_before_the_decision_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="after the moment"):
            fx.record(expires_at=fx.FIXTURE_NOW)


class TestSensitivityReusesTheExistingVocabulary:
    def test_governed_sensitivities_match_what_learned_intake_recognises(self) -> None:
        """One vocabulary. Two allowlists that must agree are two that will drift."""
        assert {item.value for item in GOVERNED_SENSITIVITIES} == set(KNOWN_SENSITIVITIES)

    def test_confidential_is_refused_rather_than_silently_quarantined(self) -> None:
        with pytest.raises(ValidationError, match="not a label learned intake recognises"):
            fx.record(sensitivity=MemorySensitivity.CONFIDENTIAL)


class TestTheRecordCarriesNoPayload:
    def test_a_prompt_or_response_field_cannot_be_added_by_accident(self) -> None:
        for forbidden in ("prompt", "response", "content", "authorization", "api_key"):
            with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
                fx.record(**{forbidden: "secret-value"})

    def test_every_input_source_carries_exactly_one_hash(self) -> None:
        with pytest.raises(ValidationError, match="exactly one hash"):
            fx.record(input_source_ids=("a", "b"), input_source_hashes=(fx.HASH_A,))
