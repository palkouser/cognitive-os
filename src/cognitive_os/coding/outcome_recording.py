"""Authoritative recording of one executed coding run, §4.7.

Sprint 21C3 counts outcomes. `CodingResultPackaged` cannot support that count: it carries an
outcome hash and nothing that resolves it, so an outcome recorded under it is a claim about
bytes that may never have been written. A corpus built on those is a corpus of labels, and
labels are exactly what this sprint exists to stop accepting.

So the order here is fixed and the failures are all in the same direction:

1. serialize the complete `CodingOutcome` canonically;
2. write the bytes through `ArtifactService`;
3. verify the returned hash *and* read the blob back, because a metadata row whose file is
   missing is the C1 Artifact Store defect, and it is still on disk today;
4. do the same for the hidden-verifier evidence;
5. only then append `coding.outcome_recorded`.

An event appended before its bytes exist would be an event that claims bytes nobody wrote.
Every step above raises rather than degrading, and the campaign treats a raise as a run that
did not happen rather than as an outcome to count.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.coding import CodingOutcome
from cognitive_os.domain.common import ArtifactRef, utc_now
from cognitive_os.domain.reality import (
    RealityCandidateManifest,
    RealityOutcomeReference,
    RealityRunIdentity,
    RealityRunKind,
    RealityTaskManifest,
)
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.coding_events import CodingOutcomeRecorded

from .hidden_verification import HiddenVerificationEvidence

OUTCOME_MEDIA_TYPE = "application/vnd.cognitive-os.coding-outcome+json"
HIDDEN_EVIDENCE_MEDIA_TYPE = "application/vnd.cognitive-os.hidden-verification-evidence+json"


class OutcomeRecordingError(RuntimeError):
    """The outcome could not be made resolvable, so it is not an outcome."""


@dataclass(frozen=True, slots=True)
class RecordedOutcome:
    """One authoritative identity. `replayed` is true when this run was already recorded."""

    reference: RealityOutcomeReference
    replayed: bool


class CodingOutcomeRecorder:
    def __init__(
        self,
        artifacts: ArtifactStorePort,
        events: CodingEventService,
        event_store: EventStorePort,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._artifacts = artifacts
        self._events = events
        self._store = event_store
        self._clock = clock

    async def record(
        self,
        *,
        outcome: CodingOutcome,
        task: RealityTaskManifest,
        evidence: HiddenVerificationEvidence,
        candidate: RealityCandidateManifest | None,
        correlation_id: UUID,
        run_identity: RealityRunIdentity | None = None,
    ) -> RecordedOutcome:
        run_kind = RealityRunKind.BASELINE if candidate is None else RealityRunKind.CANDIDATE
        if candidate is not None and candidate.task_id != task.task_id:
            raise OutcomeRecordingError("candidate belongs to a different task")
        if evidence.task_run_id != outcome.task_run_id:
            raise OutcomeRecordingError("hidden evidence belongs to a different task run")
        if run_identity is not None:
            self._require_identity_describes_this_run(run_identity, task, candidate, run_kind)

        outcome_hash = outcome.canonical_hash()
        existing = await self._find_recorded(outcome.task_run_id, outcome_hash)
        if existing is not None:
            return RecordedOutcome(reference=existing, replayed=True)

        outcome_artifact = await self._store_canonical(
            outcome.canonical_json().encode(), OUTCOME_MEDIA_TYPE
        )
        evidence_artifact = await self._store_canonical(
            evidence.canonical_json().encode(), HIDDEN_EVIDENCE_MEDIA_TYPE
        )

        occurred_at = self._clock()
        payload = CodingOutcomeRecorded(
            task_run_id=outcome.task_run_id,
            run_kind=run_kind,
            task_id=task.task_id,
            task_manifest_hash=task.content_hash,
            candidate_id=None if candidate is None else candidate.candidate_id,
            candidate_strategy=None if candidate is None else candidate.strategy,
            outcome_hash=outcome_hash,
            outcome_artifact_id=outcome_artifact.artifact_id,
            outcome_artifact_hash=outcome_artifact.content_hash,
            hidden_evidence_artifact_id=evidence_artifact.artifact_id,
            hidden_evidence_hash=evidence_artifact.content_hash,
            final_status=outcome.status,
            hidden_verification_passed=evidence.passed,
            provider_output_id=None if candidate is None else candidate.provider_output_id,
            run_identity_key=None if run_identity is None else run_identity.key,
            occurred_at=occurred_at,
        )
        event_id = await self._events.append(
            outcome.task_run_id, payload, correlation_id=correlation_id
        )
        return RecordedOutcome(reference=self._reference(payload, event_id), replayed=False)

    @staticmethod
    def _require_identity_describes_this_run(
        identity: RealityRunIdentity,
        task: RealityTaskManifest,
        candidate: RealityCandidateManifest | None,
        run_kind: RealityRunKind,
    ) -> None:
        """Refuse to stamp a campaign identity onto a run it does not describe.

        The identity key is what resume trusts, so a mismatched one is worse than a missing
        one: resume would skip a planned run on the strength of a different run's evidence.
        """
        if identity.task_id != task.task_id or identity.task_manifest_hash != task.content_hash:
            raise OutcomeRecordingError("run identity describes a different task revision")
        if identity.run_kind is not run_kind:
            raise OutcomeRecordingError("run identity describes a different kind of run")
        expected_candidate = None if candidate is None else candidate.candidate_id
        if identity.candidate_id != expected_candidate:
            raise OutcomeRecordingError("run identity describes a different candidate")

    async def _store_canonical(self, data: bytes, media_type: str) -> ArtifactRef:
        """Write, then prove the write. A hash the caller computed is not evidence of bytes."""
        expected = sha256(data).hexdigest()
        artifact = await self._artifacts.put_bytes(data, media_type=media_type)
        if artifact.content_hash != expected or artifact.size_bytes != len(data):
            raise OutcomeRecordingError(
                "artifact metadata does not describe the bytes that were submitted"
            )
        if not await self._artifacts.verify(artifact.artifact_id):
            raise OutcomeRecordingError(
                "artifact bytes could not be read back and verified after writing"
            )
        return artifact

    async def _find_recorded(
        self, task_run_id: UUID, outcome_hash: str
    ) -> RealityOutcomeReference | None:
        """Return the already-recorded identity for this run, if there is one.

        Matching on the outcome hash, not on the task-run ID alone: a task run legitimately
        holds several events, and re-recording the *same* outcome is a free no-op while a
        *different* outcome under the same run is a second execution the campaign has to see.
        """
        version = await self._store.get_stream_version(task_run_id)
        if not version:
            return None
        for stored in await self._store.read_stream(task_run_id):
            envelope = stored.envelope
            if envelope.event_type != CodingOutcomeRecorded.event_type:
                continue
            if envelope.payload.get("outcome_hash") != outcome_hash:
                continue
            payload = CodingOutcomeRecorded.model_validate(envelope.payload)
            return self._reference(payload, envelope.event_id)
        return None

    @staticmethod
    def _reference(payload: CodingOutcomeRecorded, event_id: UUID) -> RealityOutcomeReference:
        return RealityOutcomeReference(
            task_run_id=payload.task_run_id,
            run_kind=payload.run_kind,
            task_id=payload.task_id,
            task_manifest_hash=payload.task_manifest_hash,
            candidate_id=payload.candidate_id,
            strategy=payload.candidate_strategy,
            outcome_hash=payload.outcome_hash,
            outcome_artifact_id=payload.outcome_artifact_id,
            outcome_artifact_hash=payload.outcome_artifact_hash,
            hidden_evidence_artifact_id=payload.hidden_evidence_artifact_id,
            hidden_evidence_hash=payload.hidden_evidence_hash,
            final_status=payload.final_status,
            hidden_verification_passed=payload.hidden_verification_passed,
            provider_output_id=payload.provider_output_id,
            source_event_id=event_id,
            occurred_at=payload.occurred_at,
        )
