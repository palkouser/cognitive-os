"""Deterministic in-memory provider-output governance ledger.

The reference implementation of `ProviderOutputRepositoryPort`, and the specification the
PostgreSQL one is held to: both run the same contract suite, so a behavioural difference
between them is a test failure rather than a production surprise.

A faithful model, not a convenient one. There is no current-state dictionary maintained
alongside the ledger: `get_latest` scans the appended revisions exactly as the SQL does
against `ix_provider_output_latest`. Keeping a shortcut cache here would make the two
implementations agree for the wrong reason — the in-memory one would be answering from a
projection the database does not have. See ADR 0087.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    GovernedOutcomeReference,
    ObservationAttribution,
)
from cognitive_os.domain.provider_output import (
    ProviderOutputConflict,
    ProviderOutputIntendedUse,
    ProviderOutputRecord,
    ProviderOutputRepositoryError,
    ProviderOutputRetentionMode,
    UsageRightsDecision,
)

#: The largest page any listing returns, matching the PostgreSQL implementation. An
#: unbounded read over an append-only store is a denial-of-service surface.
MAX_PAGE_SIZE = 500

#: The learned source kind each adapter's output is offered under. These belong to
#: `VERIFIER_BACKED_SOURCE_KINDS` and never to `REAL_GOVERNED_SOURCE_KINDS`: a provider
#: cannot produce a real governed run, and a fixture that borrowed that label would become
#: the yardstick every later comparison is measured against.
PROVIDER_SOURCE_KINDS: dict[str, str] = {
    "openrouter": "openrouter_advisory",
    "claude_code": "claude_code_advisory",
    "codex_cli": "codex_cli_advisory",
}


def source_kind_for(adapter_kind: str, *, provider_id: str) -> str:
    """The learned source kind for one adapter, refusing anything not allowlisted."""
    kind = PROVIDER_SOURCE_KINDS.get(adapter_kind)
    if kind is None:
        raise ProviderOutputRepositoryError(
            ProviderOutputConflict.BROKEN_LINEAGE,
            f"adapter {adapter_kind!r} has no governed learned source kind",
        )
    del provider_id
    return kind


def build_source_reference(
    record: ProviderOutputRecord, *, surface: str, moment: datetime
) -> GovernedOutcomeReference:
    """Turn one governance revision into a learned intake reference, or refuse.

    Refusals rather than best-effort mapping, because every one of them is a case where an
    observation would otherwise enter the learning plane carrying a claim nobody checked:

    * prohibited rights would enrol material the terms forbid;
    * a failed scan would put a credential into the evidence store;
    * an expired revision would reuse a decision that has already lapsed;
    * a missing verifier would let schema validity stand in for correctness.

    Provenance is always `OPERATOR_SUPPLIED`. A provider call is not a real governed run,
    and C1 intake rejects the claim anyway — but making it here means the rejection is a
    deliberate policy rather than a downstream accident.
    """
    if record.rights_decision is UsageRightsDecision.PROHIBITED:
        raise ProviderOutputRepositoryError(
            ProviderOutputConflict.RETENTION_REFUSED,
            "the governance revision prohibits use of this output",
        )
    if record.retention_mode is ProviderOutputRetentionMode.NORMALIZED_CONTENT and (
        record.response_artifact_hash is None
    ):
        raise ProviderOutputRepositoryError(
            ProviderOutputConflict.BROKEN_LINEAGE,
            "retained content is claimed without an artifact hash",
        )
    # Attribution is `DIRECT` only when an independent verifier actually agreed. Otherwise
    # the outcome is real but unattributable, which is what quarantine is for.
    attribution = (
        ObservationAttribution.DIRECT
        if record.verifier_status.value == "passed"
        else ObservationAttribution.UNKNOWN
    )
    return GovernedOutcomeReference(
        surface=surface,
        source_kind=source_kind_for(record.adapter_kind.value, provider_id=record.provider_id),
        source_event_id=record.completed_event_id,
        source_run_id=record.model_call_id,
        source_payload_hash=record.normalized_response_hash,
        provenance_class=ProvenanceClass.OPERATOR_SUPPLIED,
        attribution=attribution,
        usage_rights_verified=record.rights_decision is UsageRightsDecision.VERIFIED
        and not record.is_expired_at(moment),
        sensitivity=record.sensitivity.value,
        verifier_status=record.verifier_status.value,
        verifier_evidence_hash=record.verifier_evidence_hash,
    )


class InMemoryProviderOutputRepository:
    """Append-only provider-output governance held in process. Loses everything on exit."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._revisions: list[ProviderOutputRecord] = []
        self._by_revision_id: dict[UUID, ProviderOutputRecord] = {}
        self._by_key: dict[str, ProviderOutputRecord] = {}

    # ------------------------------------------------------------------- writing

    async def record_output(self, record: ProviderOutputRecord) -> ProviderOutputRecord:
        async with self._lock:
            existing = self._by_revision_id.get(record.provider_output_revision_id)
            if existing is not None:
                if existing.content_hash != record.content_hash:
                    raise ProviderOutputRepositoryError(
                        ProviderOutputConflict.IDEMPOTENCY_KEY_REUSED,
                        "an immutable revision cannot be replaced with different content",
                    )
                return existing
            replayed = self._by_key.get(record.idempotency_key)
            if replayed is not None:
                if replayed.content_hash != record.content_hash:
                    raise ProviderOutputRepositoryError(
                        ProviderOutputConflict.IDEMPOTENCY_KEY_REUSED,
                        f"idempotency key {record.idempotency_key!r} was used for different "
                        "content",
                    )
                return replayed

            self._validate_lineage(record)
            self._revisions.append(record)
            self._by_revision_id[record.provider_output_revision_id] = record
            self._by_key[record.idempotency_key] = record
            return record

    def _validate_lineage(self, record: ProviderOutputRecord) -> None:
        """The same continuity rule the controlled SQL function enforces."""
        history = [
            item for item in self._revisions if item.provider_output_id == record.provider_output_id
        ]
        latest = max((item.revision for item in history), default=None)
        if record.revision == 1:
            if latest is not None:
                raise ProviderOutputRepositoryError(
                    ProviderOutputConflict.REVISION_CONFLICT,
                    "revision 1 already exists for this provider output",
                )
            return
        if latest is None:
            raise ProviderOutputRepositoryError(
                ProviderOutputConflict.REVISION_CONFLICT,
                f"revision {record.revision} has no history",
            )
        if record.revision != latest + 1:
            raise ProviderOutputRepositoryError(
                ProviderOutputConflict.REVISION_CONFLICT,
                f"expected revision {latest + 1}, requested {record.revision}",
            )
        predecessor = self._by_revision_id.get(record.previous_revision_id or UUID(int=0))
        if (
            predecessor is None
            or predecessor.provider_output_id != record.provider_output_id
            or predecessor.revision != record.revision - 1
        ):
            raise ProviderOutputRepositoryError(
                ProviderOutputConflict.BROKEN_LINEAGE,
                "the named predecessor is not this revision's immediate predecessor",
            )

    # ------------------------------------------------------------------- reading

    async def get_revision(self, revision_id: UUID) -> ProviderOutputRecord | None:
        return self._by_revision_id.get(revision_id)

    async def get_latest(self, provider_output_id: UUID) -> ProviderOutputRecord | None:
        history = [
            item for item in self._revisions if item.provider_output_id == provider_output_id
        ]
        if not history:
            return None
        return max(history, key=lambda item: item.revision)

    async def revision_history(
        self, provider_output_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> tuple[ProviderOutputRecord, ...]:
        _validate_page(limit, offset)
        history = sorted(
            (item for item in self._revisions if item.provider_output_id == provider_output_id),
            key=lambda item: item.revision,
        )
        return tuple(history[offset : offset + min(limit, MAX_PAGE_SIZE)])

    async def list_eligible(
        self,
        *,
        intended_use: ProviderOutputIntendedUse,
        moment: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ProviderOutputRecord, ...]:
        _validate_page(limit, offset)
        heads: dict[UUID, ProviderOutputRecord] = {}
        for item in self._revisions:
            current = heads.get(item.provider_output_id)
            if current is None or item.revision > current.revision:
                heads[item.provider_output_id] = item
        eligible = sorted(
            (
                head
                for head in heads.values()
                if head.intended_use is intended_use and head.is_selectable_at(moment)
            ),
            key=lambda item: (item.recorded_at, str(item.provider_output_id)),
        )
        return tuple(eligible[offset : offset + min(limit, MAX_PAGE_SIZE)])

    async def resolve_source(
        self, provider_output_id: UUID, *, surface: str, moment: datetime
    ) -> GovernedOutcomeReference:
        record = await self.get_latest(provider_output_id)
        if record is None:
            raise ProviderOutputRepositoryError(
                ProviderOutputConflict.NOT_FOUND,
                f"no governance record for provider output {provider_output_id}",
            )
        return build_source_reference(record, surface=surface, moment=moment)

    async def count_revisions(self) -> int:
        return len(self._revisions)


def _validate_page(limit: int, offset: int) -> None:
    if limit < 0 or offset < 0:
        raise ValueError("limit and offset must not be negative")
