"""One contract suite for every provider-output governance repository.

The in-memory reference and the PostgreSQL implementation must be indistinguishable through
the port, so the suite lives here and each implementation binds to it. A rule that only one
of them enforces is not a rule, and the one that would quietly disagree is always the one
that writes to disk.

Bind an implementation by subclassing `ProviderOutputRepositoryContract` and providing
`make_repository()` and `link_evidence()` — the latter returns the completed-event ID and
artifact reference the implementation needs a record to point at. The in-memory reference
invents them; PostgreSQL seeds real rows, because its foreign keys are real.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Protocol
from uuid import UUID, uuid4

import pytest

from cognitive_os.application.ports.provider_output import ProviderOutputRepositoryPort
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import ObservationAttribution
from cognitive_os.domain.provider_output import (
    ProviderOutputConflict,
    ProviderOutputIntendedUse,
    ProviderOutputRepositoryError,
    ProviderOutputRetentionMode,
    ProviderOutputVerifierStatus,
    SecretScanStatus,
    UsageRightsDecision,
)

from . import fixtures as fx


class EvidenceLink(Protocol):
    async def __call__(self) -> tuple[UUID, UUID | None, str | None]:
        """Return `(completed_event_id, response_artifact_id, response_artifact_hash)`."""
        ...


class ProviderOutputRepositoryContract:
    """Every semantic the port promises, asserted against whichever store is bound."""

    async def make_repository(self) -> ProviderOutputRepositoryPort:
        raise NotImplementedError

    async def link_evidence(self) -> tuple[UUID, UUID | None, str | None]:
        raise NotImplementedError

    async def _record(self, **overrides: Any) -> Any:
        event_id, _artifact_id, _artifact_hash = await self.link_evidence()
        fields: dict[str, Any] = {"completed_event_id": event_id}
        fields.update(overrides)
        return fx.record(**fields)

    # ------------------------------------------------------------------ appending

    @pytest.mark.asyncio
    async def test_a_first_revision_is_appended_and_readable(self) -> None:
        repository = await self.make_repository()
        record = await self._record()
        stored = await repository.record_output(record)
        assert stored.content_hash == record.content_hash
        assert await repository.get_revision(record.provider_output_revision_id) == stored
        assert await repository.get_latest(record.provider_output_id) == stored
        assert await repository.count_revisions() == 1

    @pytest.mark.asyncio
    async def test_replaying_the_same_record_is_a_free_no_op(self) -> None:
        repository = await self.make_repository()
        record = await self._record()
        first = await repository.record_output(record)
        second = await repository.record_output(record)
        assert first.content_hash == second.content_hash
        assert await repository.count_revisions() == 1

    @pytest.mark.asyncio
    async def test_reusing_an_idempotency_key_with_different_content_fails_closed(self) -> None:
        """A retry must not be able to rewrite a governance decision."""
        repository = await self.make_repository()
        await repository.record_output(await self._record())
        conflicting = await self._record(
            provider_output_revision_id=uuid4(),
            provider_output_id=uuid4(),
            resolved_model="vendor/something-else:free",
        )
        with pytest.raises(ProviderOutputRepositoryError) as failure:
            await repository.record_output(conflicting)
        assert failure.value.conflict is ProviderOutputConflict.IDEMPOTENCY_KEY_REUSED

    @pytest.mark.asyncio
    async def test_a_second_first_revision_for_one_output_is_refused(self) -> None:
        repository = await self.make_repository()
        first = await self._record()
        await repository.record_output(first)
        duplicate = await self._record(
            provider_output_revision_id=uuid4(),
            idempotency_key="provider-output:fixture:duplicate-first",
        )
        with pytest.raises(ProviderOutputRepositoryError) as failure:
            await repository.record_output(duplicate)
        assert failure.value.conflict is ProviderOutputConflict.REVISION_CONFLICT

    # ------------------------------------------------------------------ revisions

    @pytest.mark.asyncio
    async def test_a_correction_appends_a_revision_and_leaves_the_first_untouched(self) -> None:
        repository = await self.make_repository()
        first = await repository.record_output(await self._record())
        second = await repository.record_output(
            fx.superseding_record(first, rights_decision=UsageRightsDecision.PROHIBITED)
        )
        assert (await repository.get_latest(first.provider_output_id)) == second
        # The earlier decision is still exactly what it was: an audit can see what was
        # believed and when, which is the whole reason corrections are revisions.
        preserved = await repository.get_revision(first.provider_output_revision_id)
        assert preserved is not None
        assert preserved.rights_decision is UsageRightsDecision.VERIFIED
        assert preserved.content_hash == first.content_hash

    @pytest.mark.asyncio
    async def test_history_is_returned_in_ascending_revision_order(self) -> None:
        repository = await self.make_repository()
        first = await repository.record_output(await self._record())
        second = await repository.record_output(
            fx.superseding_record(first, verifier_status=ProviderOutputVerifierStatus.FAILED)
        )
        history = await repository.revision_history(first.provider_output_id)
        assert [item.revision for item in history] == [1, 2]
        assert history[1].content_hash == second.content_hash

    @pytest.mark.asyncio
    async def test_a_revision_that_skips_its_predecessor_is_refused(self) -> None:
        repository = await self.make_repository()
        first = await repository.record_output(await self._record())
        gap = fx.superseding_record(first, revision=3, idempotency_key="provider-output:fixture:r3")
        with pytest.raises(ProviderOutputRepositoryError) as failure:
            await repository.record_output(gap)
        assert failure.value.conflict is ProviderOutputConflict.REVISION_CONFLICT

    @pytest.mark.asyncio
    async def test_a_revision_naming_an_unknown_predecessor_is_refused(self) -> None:
        repository = await self.make_repository()
        first = await repository.record_output(await self._record())
        orphan = fx.superseding_record(
            first,
            previous_revision_id=uuid4(),
            idempotency_key="provider-output:fixture:orphan",
        )
        with pytest.raises(ProviderOutputRepositoryError) as failure:
            await repository.record_output(orphan)
        assert failure.value.conflict is ProviderOutputConflict.BROKEN_LINEAGE

    @pytest.mark.asyncio
    async def test_concurrent_writers_cannot_both_append_the_same_revision(self) -> None:
        """One wins, one is refused. Two appended revision 2s would fork the audit chain."""
        repository = await self.make_repository()
        first = await repository.record_output(await self._record())
        contenders = [
            fx.superseding_record(
                first,
                provider_output_revision_id=uuid4(),
                idempotency_key=f"provider-output:race:{index}",
                supersession_reason=f"racing correction {index}",
            )
            for index in range(2)
        ]
        results = await asyncio.gather(
            *(repository.record_output(record) for record in contenders),
            return_exceptions=True,
        )
        successes = [item for item in results if not isinstance(item, BaseException)]
        failures = [item for item in results if isinstance(item, BaseException)]
        assert len(successes) == 1
        assert len(failures) == 1
        assert len(await repository.revision_history(first.provider_output_id)) == 2

    # ---------------------------------------------------------------- eligibility

    @pytest.mark.asyncio
    async def test_a_fully_governed_record_is_eligible(self) -> None:
        repository = await self.make_repository()
        await repository.record_output(await self._record())
        eligible = await repository.list_eligible(
            intended_use=ProviderOutputIntendedUse.CORPUS_CANDIDATE, moment=fx.FIXTURE_NOW
        )
        assert len(eligible) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "overrides",
        [
            {"rights_decision": UsageRightsDecision.UNKNOWN, "rights_evidence_hash": None},
            {"secret_scan_status": SecretScanStatus.FAILED},
            {"verifier_status": ProviderOutputVerifierStatus.INCONCLUSIVE},
            {"physical_deletion_required": True},
            {"intended_use": ProviderOutputIntendedUse.TRANSIENT_ADVICE},
        ],
        ids=["rights", "scan", "verifier", "deletion", "use"],
    )
    async def test_each_missing_condition_removes_eligibility(
        self, overrides: dict[str, Any]
    ) -> None:
        repository = await self.make_repository()
        await repository.record_output(await self._record(**overrides))
        assert (
            await repository.list_eligible(
                intended_use=ProviderOutputIntendedUse.CORPUS_CANDIDATE,
                moment=fx.FIXTURE_NOW,
            )
            == ()
        )

    @pytest.mark.asyncio
    async def test_an_expired_revision_is_excluded_at_the_exact_boundary(self) -> None:
        repository = await self.make_repository()
        expiry = fx.FIXTURE_NOW + timedelta(hours=1)
        await repository.record_output(await self._record(expires_at=expiry))
        use = ProviderOutputIntendedUse.CORPUS_CANDIDATE
        before = await repository.list_eligible(
            intended_use=use, moment=expiry - timedelta(microseconds=1)
        )
        at = await repository.list_eligible(intended_use=use, moment=expiry)
        assert len(before) == 1
        assert at == ()

    @pytest.mark.asyncio
    async def test_a_superseded_revision_is_never_selected(self) -> None:
        """Eligibility changes only through a new immutable revision."""
        repository = await self.make_repository()
        first = await repository.record_output(await self._record())
        await repository.record_output(
            fx.superseding_record(first, rights_decision=UsageRightsDecision.PROHIBITED)
        )
        assert (
            await repository.list_eligible(
                intended_use=ProviderOutputIntendedUse.CORPUS_CANDIDATE,
                moment=fx.FIXTURE_NOW,
            )
            == ()
        )

    @pytest.mark.asyncio
    async def test_a_revision_can_restore_eligibility_it_previously_lost(self) -> None:
        repository = await self.make_repository()
        first = await repository.record_output(
            await self._record(verifier_status=ProviderOutputVerifierStatus.INCONCLUSIVE)
        )
        await repository.record_output(
            fx.superseding_record(first, verifier_status=ProviderOutputVerifierStatus.PASSED)
        )
        eligible = await repository.list_eligible(
            intended_use=ProviderOutputIntendedUse.CORPUS_CANDIDATE, moment=fx.FIXTURE_NOW
        )
        assert len(eligible) == 1
        assert eligible[0].revision == 2

    @pytest.mark.asyncio
    async def test_listing_is_bounded_and_refuses_a_negative_page(self) -> None:
        repository = await self.make_repository()
        with pytest.raises(ValueError):
            await repository.list_eligible(
                intended_use=ProviderOutputIntendedUse.CORPUS_CANDIDATE,
                moment=fx.FIXTURE_NOW,
                limit=-1,
            )

    # ------------------------------------------------------------ source resolution

    @pytest.mark.asyncio
    async def test_a_verified_record_resolves_to_an_intake_reference(self) -> None:
        repository = await self.make_repository()
        record = await repository.record_output(await self._record())
        reference = await repository.resolve_source(
            record.provider_output_id, surface="advisory", moment=fx.FIXTURE_NOW
        )
        assert reference.source_kind == "openrouter_advisory"
        assert reference.source_payload_hash == record.normalized_response_hash
        assert reference.source_event_id == record.completed_event_id
        assert reference.verifier_evidence_hash == record.verifier_evidence_hash

    @pytest.mark.asyncio
    async def test_a_provider_output_is_never_a_real_governed_run(self) -> None:
        repository = await self.make_repository()
        record = await repository.record_output(await self._record())
        reference = await repository.resolve_source(
            record.provider_output_id, surface="advisory", moment=fx.FIXTURE_NOW
        )
        assert reference.provenance_class is ProvenanceClass.OPERATOR_SUPPLIED

    @pytest.mark.asyncio
    async def test_an_unverified_record_resolves_as_unattributable(self) -> None:
        """Quarantine is what 'real but unattributable' is for."""
        repository = await self.make_repository()
        record = await repository.record_output(
            await self._record(verifier_status=ProviderOutputVerifierStatus.INCONCLUSIVE)
        )
        reference = await repository.resolve_source(
            record.provider_output_id, surface="advisory", moment=fx.FIXTURE_NOW
        )
        assert reference.attribution is ObservationAttribution.UNKNOWN

    @pytest.mark.asyncio
    async def test_an_expired_record_resolves_with_rights_no_longer_verified(self) -> None:
        repository = await self.make_repository()
        expiry = fx.FIXTURE_NOW + timedelta(hours=1)
        record = await repository.record_output(await self._record(expires_at=expiry))
        reference = await repository.resolve_source(
            record.provider_output_id, surface="advisory", moment=expiry
        )
        assert reference.usage_rights_verified is False

    @pytest.mark.asyncio
    async def test_a_prohibited_record_refuses_to_resolve_at_all(self) -> None:
        repository = await self.make_repository()
        first = await repository.record_output(await self._record())
        await repository.record_output(
            fx.superseding_record(first, rights_decision=UsageRightsDecision.PROHIBITED)
        )
        with pytest.raises(ProviderOutputRepositoryError) as failure:
            await repository.resolve_source(
                first.provider_output_id, surface="advisory", moment=fx.FIXTURE_NOW
            )
        assert failure.value.conflict is ProviderOutputConflict.RETENTION_REFUSED

    @pytest.mark.asyncio
    async def test_an_unknown_output_refuses_rather_than_returning_nothing(self) -> None:
        repository = await self.make_repository()
        with pytest.raises(ProviderOutputRepositoryError) as failure:
            await repository.resolve_source(uuid4(), surface="advisory", moment=fx.FIXTURE_NOW)
        assert failure.value.conflict is ProviderOutputConflict.NOT_FOUND

    # -------------------------------------------------------------------- reading

    @pytest.mark.asyncio
    async def test_an_unknown_revision_reads_as_absent(self) -> None:
        repository = await self.make_repository()
        assert await repository.get_revision(uuid4()) is None
        assert await repository.get_latest(uuid4()) is None

    @pytest.mark.asyncio
    async def test_a_retained_artifact_reference_survives_the_round_trip(self) -> None:
        repository = await self.make_repository()
        event_id, artifact_id, artifact_hash = await self.link_evidence()
        if artifact_id is None:
            pytest.skip("this binding does not provide a retained artifact")
        record = fx.record(
            completed_event_id=event_id,
            retention_mode=ProviderOutputRetentionMode.NORMALIZED_CONTENT,
            response_artifact_id=artifact_id,
            response_artifact_hash=artifact_hash,
        )
        stored = await repository.record_output(record)
        assert stored.response_artifact_id == artifact_id
        assert stored.response_artifact_hash == artifact_hash
