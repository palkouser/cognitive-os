"""S22C-041 and S22C-042. Campaign cycle 1: the cleared chapters into `engineering.mechanics`.

W1 pushed one passage through the nine stages against in-memory repositories. This is the
campaign: every worked example in the three chapters S22C-020 cleared for this domain,
formalised by a governed provider call, recomputed by the domain's own kernel, and — for
whatever survives — compiled, promoted and cited, **against the provisioned 22C PostgreSQL
store**. The nine stage functions are `campaign_22c`'s, unchanged and handed a different
composition, because a second implementation for "the real one" is how the slice and the
campaign would stop being evidence about the same code.

**The number this wave exists to produce is the yield.** How much of a real, rights-cleared
technical source can a governed pipeline actually acquire? Every earlier record in this
sprint measured whether the machinery works. This one measures what it is worth, and the
answer is not the one the plan assumed — see W2-F1.

**What is recorded, and what is recomputed.** W1-F1's rule at campaign scale: the record
separates *invariants* — the manifest, the segment hashes, the sealed provider answers, every
cross-check verdict, the quarantine decisions and the citation chains, all of which `--check`
rebuilds from the same sources — from *observations* of the campaign store, which are read
back out of PostgreSQL rather than recomputed. A validator that rebuilt an observation would
only prove the record was internally consistent.

    UV_CACHE_DIR=.cache/uv uv run python scripts/cycle_22c.py --cycle
    UV_CACHE_DIR=.cache/uv uv run python scripts/cycle_22c.py --check

Both need the 22C environment sourced explicitly (`.env.s22c.local`), never exported —
W0-F1, which cost a wave once already.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from campaign_22c import (  # noqa: E402
    ACTOR,
    CAMPAIGN_PREDICATE_ID,
    CAMPAIGN_STAGES,
    Composition,
    CycleState,
    Segment,
    SourceSpec,
    _canonical,
    _sha256,
    attempt_case,
    build_campaign_predicate_registry,
    observed_event_types,
    run_cycle,
    walk_citations,
)
from chapter_22c import CHAPTERS, SOURCE_PATH, Passage, locate_passages  # noqa: E402
from provider_22c import PROMPT_TEMPLATE_ID, PROMPT_TEMPLATE_VERSION, proposals  # noqa: E402

from cognitive_os.application.services.memory_service import MemoryService  # noqa: E402
from cognitive_os.application.services.verification_service import (  # noqa: E402
    VerificationService,
)
from cognitive_os.config.corpus_config import CorpusConfiguration  # noqa: E402
from cognitive_os.config.semantic_memory_config import (  # noqa: E402
    SemanticMemoryConfiguration,
)
from cognitive_os.corpus.factory import CorpusFactory  # noqa: E402
from cognitive_os.domain.campaigns import (  # noqa: E402
    CampaignBudget,
    CampaignCurriculum,
    CampaignHoldout,
    CampaignManifestV1,
    CampaignSourceRights,
    CampaignStopReason,
    RightsClearanceStatus,
)
from cognitive_os.domain.corpus import (  # noqa: E402
    CorpusQuarantineReason,
    CorpusUsageRight,
)
from cognitive_os.domain.memory import (  # noqa: E402
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemoryType,
    MemoryWritePolicy,
)
from cognitive_os.domain.semantic_memory import (  # noqa: E402
    BeliefStatus,
    Claim,
    ClaimIdentity,
    ClaimPromotionOutcome,
    ClaimRelation,
    ClaimRelationType,
    ClaimRevision,
    ClaimRevisionReference,
    ClaimTemporalInterval,
    SemanticLiteral,
    SemanticLiteralKind,
    SemanticSourceRef,
    SemanticSourceType,
    TemporalClaimQuery,
    claim_revision_hash,
    semantic_hash,
)
from cognitive_os.events.catalog import build_default_event_catalog  # noqa: E402
from cognitive_os.events.memory_event_service import MemoryEventService  # noqa: E402
from cognitive_os.events.memory_store import MemoryEventStore  # noqa: E402
from cognitive_os.events.semantic_memory_event_service import (  # noqa: E402
    SemanticMemoryEventService,
)
from cognitive_os.events.verifier_event_service import VerifierEventService  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.corpus.postgres.repository import (  # noqa: E402
    PostgresCorpusRepository,
)
from cognitive_os.infrastructure.memory.postgres.repository import (  # noqa: E402
    PostgresMemoryRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402
from cognitive_os.infrastructure.semantic_memory.postgres.repository import (  # noqa: E402
    PostgresSemanticMemoryRepository,
)
from cognitive_os.semantic_memory.beliefs import aggregate_confidence  # noqa: E402
from cognitive_os.semantic_memory.canonicalization import canonical_identifier  # noqa: E402
from cognitive_os.semantic_memory.errors import (  # noqa: E402
    SemanticIntegrityError,
    SemanticPolicyError,
)
from cognitive_os.semantic_memory.grounding import TrustedSourceResolver  # noqa: E402
from cognitive_os.semantic_memory.promotion import SemanticPromotionGate  # noqa: E402
from cognitive_os.semantic_memory.service import SemanticMemoryService  # noqa: E402
from cognitive_os.verification.factory import build_builtin_registry  # noqa: E402

OUTPUT = EVIDENCE / "sprint-22c-w2-cycle1.json"
RETAINED = EVIDENCE / "sprint-22c-w2-retained-cases.json"
SOURCE_RIGHTS = EVIDENCE / "sprint-22c-source-rights.json"
HOLDOUT = EVIDENCE / "sprint-22c-holdout.json"

CAMPAIGN_ID = "s22c-physics"
#: Revision 2. Revision 1 is W1's one-segment manifest, sealed in `sprint-22c-w1-slice.json`
#: and its successor; a changed campaign is a new revision with the old one intact.
MANIFEST_REVISION = 2
DOMAIN_ID = "engineering.mechanics"

#: One instant for the whole cycle, and the boundary the supersession turns on. A campaign
#: record whose hashes move with the wall clock cannot be reproduced.
CYCLE_TIME = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
SUPERSESSION_TIME = datetime(2026, 8, 15, 13, 0, tzinfo=UTC)

NAMESPACE = uuid5(NAMESPACE_URL, "cognitive-os:sprint-22c:w2:cycle-1")


def _identifier(label: str) -> UUID:
    return uuid5(NAMESPACE, label)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _seal_intact(path: Path) -> bool:
    stored = _load(path)
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    return _sha256(_canonical(body)) == stored["integrity_content_hash"]


# ---------------------------------------------------------------------------
# The campaign's segments, built from what the provider proposed
# ---------------------------------------------------------------------------


def subject_of(passage_id: str) -> str:
    """**W2-A1.** The claim subject is the *worked example*, not the topic.

    W0's fixture gave one passage per topic, so `mechanics:uniform-motion` was both, and the
    two readings could not be told apart. They are not the same: the campaign predicate is
    functional, so under the fixture's rule two genuine worked examples of one topic would be
    a deterministic contradiction and each would deny the other promotion. Cycle 1 formalised
    one segment and therefore did not exercise the collision, so this is carried as an
    assumption the wave changed rather than a defect it observed — `subject_rule` in the
    record counts what the fixture rule would have collided on, which for this cycle is zero.
    """
    return f"mechanics:{passage_id}"


def topic_subject_of(problem_type: str) -> str:
    """W0's rule, kept so the collision it would cause can be counted rather than described."""
    return f"mechanics:{problem_type.removeprefix('mechanics.')}"


#: **W2-F3.** The released quarantine vocabulary has no reason for "no registered domain can
#: check this", which turned out to be the commonest outcome of a real acquisition campaign
#: by a wide margin. Both provider refusals map onto the nearest honest released reason, and
#: the campaign keeps the distinction in its own record: a campaign may be stricter than the
#: released vocabulary and may never invent a value for it.
REFUSAL_REASON = CorpusQuarantineReason.UNVERIFIABLE_PROVIDER_DATA


def segment_of(passage: Passage, sealed: dict[str, Any]) -> Segment:
    """One campaign segment: the passage's bytes, and what the provider proposed about them.

    `expected_accepted` is **not** an answer key here, and reading it as one would repeat a
    mistake W0's fixture invites: at fixture scale the author knew which passages were sound,
    and in a campaign nobody does. It records what the *provider* proposed, so the cycle's
    `every_outcome_as_expected` count measures provider-and-kernel agreement — the only
    honest thing that field can mean once the content is real.
    """
    answer = sealed["answer"]
    formalisable = bool(answer.get("formalisable"))
    return Segment(
        segment_id=passage.passage_id,
        domain_id=DOMAIN_ID,
        # A passage the provider could not formalise carries no problem type at all rather
        # than a plausible one: the registry then refuses it by name at the cross-check, which
        # puts the refusal on the record instead of dropping the passage from the curriculum.
        problem_type=str(answer.get("problem_type") or ""),
        subject=subject_of(passage.passage_id),
        predicate_id=CAMPAIGN_PREDICATE_ID,
        literal_kind=SemanticLiteralKind.STRING,
        value=str(answer.get("statement") or passage.title),
        unit=None,
        prose=passage.text,
        formal_inputs=dict(answer.get("formal_inputs") or {}),
        asserted=dict(answer.get("asserted") or {}),
        expected_accepted=formalisable,
        quarantine_reason=None if formalisable else REFUSAL_REASON,
        verbatim=passage.text,
    )


def subject_rule(segments: tuple[Segment, ...]) -> dict[str, Any]:
    """What W0's topic-level subject rule would have done to this curriculum. W2-A1."""
    formalised = [item for item in segments if item.expected_accepted]
    by_topic: dict[str, list[str]] = {}
    for segment in formalised:
        by_topic.setdefault(topic_subject_of(segment.problem_type), []).append(segment.segment_id)
    colliding = {key: sorted(value) for key, value in by_topic.items() if len(value) > 1}
    return {
        "rule_used_by_this_cycle": "mechanics:<passage_id> — the worked example is the subject",
        "rule_used_by_the_w0_fixture": "mechanics:<topic> — the topic is the subject",
        "formalised_segments": len(formalised),
        "distinct_subjects_under_this_rule": len({item.subject for item in formalised}),
        "distinct_subjects_under_the_fixture_rule": len(by_topic),
        "topics_with_more_than_one_worked_example": colliding,
        "segments_that_would_have_collided": sum(len(value) for value in colliding.values()),
        "exercised_by_this_cycle": bool(colliding),
        "why_the_rule_changed_anyway": (
            "the campaign predicate is FUNCTIONAL, so two claims on one subject over "
            "overlapping validity are a deterministic contradiction by the released "
            "detector's own rule. Under the fixture's subject every genuine worked example "
            "of a topic would deny promotion to every other one — W0-F3's shape, one layer "
            "on. Cycle 1 formalised one segment, so the collision is latent here and the "
            "record says so rather than claiming a defect it did not observe"
        ),
    }


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------


def cleared_physics() -> tuple[CampaignSourceRights, dict[str, Any]]:
    """The physics clearance, rebuilt through the released contract from the sealed record."""
    record = _load(SOURCE_RIGHTS)
    entry = next(item for item in record["sources"] if item["key"] == "physics")
    rights = CampaignSourceRights(
        status=RightsClearanceStatus.CLEARED,
        source_content_hash=entry["source_content_hash"],
        edition=entry["edition"],
        author=entry["author"],
        location=entry["location"],
        license_identifier=entry["license_identifier"],
        permitted_uses=tuple(CorpusUsageRight(value) for value in sorted(entry["permitted_uses"])),
        cleared_by=record["cleared_by"],
        cleared_at=CYCLE_TIME,
        evidence_hash=entry["evidence_hash"],
        notes=entry["notes"],
    )
    return rights, entry


def frozen_holdout() -> CampaignHoldout:
    """The holdout as W0 froze it, carried in by hash rather than retyped.

    W1's slice named a placeholder. Cycle 1 names the real one, so the leakage check compares
    this curriculum against the cases the improvement exit will actually read — and
    `measured_values` stays 0, because W3 reads that holdout and W2 does not.
    """
    record = _load(HOLDOUT)
    return CampaignHoldout(
        holdout_id=record["holdout_id"],
        case_hashes=tuple(record["case_hashes"]),
        verifier_id=record["verifier_id"],
        seeds=tuple(record["seeds"]),
        success_definition=record["success_definition"],
        store_url_env=record["store_url_env"],
        measured_values=0,
    )


def cycle_manifest(
    rights: CampaignSourceRights, segments: tuple[Segment, ...]
) -> CampaignManifestV1:
    return CampaignManifestV1(
        campaign_id=CAMPAIGN_ID,
        revision=MANIFEST_REVISION,
        rights=rights,
        domain_ids=(DOMAIN_ID,),
        goals=(
            "acquire every worked example the cleared chapters carry for this domain, and "
            "measure how many of them a governed pipeline can actually verify",
            "replay every retained domain and record per-domain rates",
            "supersede an acquired claim through the released lifecycle without deleting history",
            "walk every promoted artifact's citation back to loaded source bytes",
        ),
        budget=CampaignBudget(
            maximum_cycles=3,
            maximum_provider_calls_per_cycle=len(segments),
            maximum_spend_usd=0.0,
            maximum_items_per_cycle=256,
        ),
        providers=("claude-code",),
        curriculum=CampaignCurriculum(
            segment_hashes=tuple(segment.content_hash for segment in segments),
            segments_per_cycle=len(segments),
        ),
        holdouts=(frozen_holdout(),),
        stop_conditions=(
            CampaignStopReason.STAGE_REFUSED,
            CampaignStopReason.SOURCE_LEAKAGE_DETECTED,
            CampaignStopReason.CYCLE_TARGET_REACHED,
        ),
        declared_uses=(CorpusUsageRight.INTERNAL_USE, CorpusUsageRight.DERIVATIVE_WORK),
        sealed_at=CYCLE_TIME,
        sealed_by="sprint-22c-w2",
    )


def cycle_source(rights: CampaignSourceRights, entry: dict[str, Any]) -> SourceSpec:
    return SourceSpec(
        identity=f"openstax:{entry['file_name']}",
        revision=entry["edition"],
        content_hash=rights.source_content_hash,
        media_type="text/plain",
        file_suffix=".txt",
    )


# ---------------------------------------------------------------------------
# The campaign store
# ---------------------------------------------------------------------------


def campaign_environment() -> tuple[str, Path]:
    url = os.environ.get("COGOS_DATABASE_URL")
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not url or not root:
        raise SystemExit(
            "COGOS_DATABASE_URL and COGOS_ARTIFACT_ROOT are required; source "
            ".env.s22c.local explicitly rather than exporting (W0-F1)"
        )
    return url, Path(root)


def postgres_composition(engine: Any, root: Path) -> Composition:
    """The same nine stages, over the provisioned campaign store.

    Everything the cycle writes is durable here except the Tool Plane's solve and verify
    events, which the released `domains.descriptor_runner` can only write to an in-memory
    store — W2-F2, named rather than worked around.
    """
    artifacts = ArtifactService(
        ContentAddressedFilesystem(root), PostgresArtifactRepository(engine)
    )
    events = PostgresEventStore(engine, build_default_event_catalog())
    memory_repository = PostgresMemoryRepository(engine)
    semantic_repository = PostgresSemanticMemoryRepository(engine)
    predicates = build_campaign_predicate_registry()
    semantic_events = SemanticMemoryEventService(events)
    source_resolver = TrustedSourceResolver(memory_repository, artifacts=artifacts)
    return Composition(
        events=events,
        tool_events=MemoryEventStore(),
        corpus=CorpusFactory(PostgresCorpusRepository(engine), artifacts, CorpusConfiguration()),
        artifacts=artifacts,
        memory=MemoryService(
            memory_repository,
            MemoryWritePolicy(
                allowed_types=frozenset(MemoryType),
                allowed_scopes=frozenset(MemoryScopeType),
                maximum_sensitivity=MemorySensitivity.INTERNAL,
            ),
            event_service=MemoryEventService(events),
        ),
        memory_repository=memory_repository,
        semantic=SemanticMemoryService(
            semantic_repository,
            predicates,
            SemanticMemoryConfiguration(),
            event_service=semantic_events,
            source_resolver=source_resolver,
        ),
        semantic_repository=semantic_repository,
        source_resolver=source_resolver,
        semantic_events=semantic_events,
        predicates=predicates,
    )


# ---------------------------------------------------------------------------
# S22C-042. The supersession
# ---------------------------------------------------------------------------


def _revision(
    *,
    claim_id: UUID,
    revision: int,
    previous: int | None,
    template: ClaimRevision,
    belief_status: BeliefStatus,
    valid_interval: ClaimTemporalInterval,
    reason: str,
    object_value: SemanticLiteral | None = None,
    statement: str | None = None,
    evidence_hash: str | None = None,
    confidence: Any = None,
) -> ClaimRevision:
    """One claim revision, with its content hash computed by the released helper."""
    resolved_object = object_value if object_value is not None else template.object
    resolved_statement = statement if statement is not None else template.statement
    resolved_hash = evidence_hash if evidence_hash is not None else template.evidence_snapshot_hash
    resolved_confidence = confidence if confidence is not None else template.confidence
    return ClaimRevision(
        claim_id=claim_id,
        revision=revision,
        previous_revision=previous,
        object=resolved_object,
        statement=resolved_statement,
        belief_status=belief_status,
        confidence=resolved_confidence,
        valid_interval=valid_interval,
        reason=reason,
        recorded_at=SUPERSESSION_TIME,
        created_by=ACTOR,
        evidence_snapshot_hash=resolved_hash,
        content_hash=claim_revision_hash(
            claim_id=claim_id,
            revision=revision,
            object_value=resolved_object,
            statement=resolved_statement,
            belief_status=belief_status,
            confidence=resolved_confidence,
            valid_interval=valid_interval,
            reason=reason,
            evidence_snapshot_hash=resolved_hash,
        ),
    )


async def _promote(
    composition: Composition, claim_id: UUID, *, from_revision: int
) -> dict[str, Any]:
    """The released promotion gate, exactly as `stage_promote` runs it."""
    proposed = await composition.semantic_repository.get_claim_revision(claim_id, from_revision)
    links = await composition.semantic_repository.list_evidence(claim_id, revision=from_revision)
    if proposed is None or not links:
        raise RuntimeError(f"claim {claim_id} has no revision {from_revision} to promote")
    target = from_revision + 1
    evidence = tuple(
        link.model_copy(
            update={
                "evidence_id": _identifier(f"evidence:{claim_id}:{target}"),
                "claim": ClaimRevisionReference(claim_id=claim_id, revision=target),
                "created_by": ACTOR,
            }
        )
        for link in links
    )
    evidence_hash = semantic_hash([link.model_dump(mode="json") for link in evidence])
    confidence = aggregate_confidence(
        extraction=1, source=1, grounding=1, evidence=1, verification=1, consistency=1
    )
    reason = "registered semantic verifier bundle passed on acquired content"
    promoted = _revision(
        claim_id=claim_id,
        revision=target,
        previous=from_revision,
        template=proposed,
        belief_status=BeliefStatus.SUPPORTED,
        valid_interval=proposed.valid_interval,
        reason=reason,
        evidence_hash=evidence_hash,
        confidence=confidence,
    )
    gate_ids = iter(_identifier(f"gate:{claim_id}:{index}") for index in range(64))
    verifier_registry = build_builtin_registry()
    gate = SemanticPromotionGate(
        composition.semantic,
        VerificationService(verifier_registry, VerifierEventService(composition.events)),
        verifier_registry,
        composition.semantic_events,
        clock=lambda: SUPERSESSION_TIME,
        id_factory=lambda: next(gate_ids),
    )
    decision = await gate.decide(
        promoted, evidence, task_run_id=_identifier("task-run"), actor=ACTOR
    )
    if decision.outcome is not ClaimPromotionOutcome.SUPPORTED:
        raise RuntimeError(f"successor promotion rejected: {list(decision.reason_codes)}")
    await composition.semantic.transition_claim(
        promoted.model_copy(update={"promotion_decision_id": decision.decision_id}),
        expected_revision=from_revision,
        decision=decision,
        evidence=evidence,
    )
    return {
        "decision_id": str(decision.decision_id),
        "outcome": decision.outcome.value,
        "reason_codes": list(decision.reason_codes),
        "activated_revision": target,
    }


async def _create_successor(
    composition: Composition,
    state: CycleState,
    segment_id: str,
    *,
    claim_id: UUID,
    statement: str,
    template: ClaimRevision,
    source_links: tuple[Any, ...],
) -> None:
    """The verified restatement, created as a *proposal* like any other claim."""
    segment = next(item for item in state.segments if item.segment_id == segment_id)
    literal = SemanticLiteral(literal_kind=SemanticLiteralKind.STRING, value=statement, unit=None)
    interval = ClaimTemporalInterval(valid_from=SUPERSESSION_TIME)
    scope = MemoryScope(scope_type=MemoryScopeType.DOMAIN, scope_id=segment.domain_id)
    identity = ClaimIdentity(
        claim_id=claim_id,
        scope=scope,
        canonical_subject_key=canonical_identifier(segment.subject),
        predicate_id=CAMPAIGN_PREDICATE_ID,
    )
    evidence = tuple(
        link.model_copy(
            update={
                "evidence_id": _identifier(f"successor-evidence:{segment_id}"),
                "claim": ClaimRevisionReference(claim_id=claim_id, revision=1),
                "created_by": ACTOR,
            }
        )
        for link in source_links
    )
    evidence_hash = semantic_hash([link.model_dump(mode="json") for link in evidence])
    revision = _revision(
        claim_id=claim_id,
        revision=1,
        previous=None,
        template=template,
        belief_status=BeliefStatus.PROPOSED,
        valid_interval=interval,
        reason="restated from the kernel's verification of the same source bytes",
        object_value=literal,
        statement=statement,
        evidence_hash=evidence_hash,
    )
    claim = Claim(
        identity=identity,
        current_revision=1,
        current_belief_status=BeliefStatus.PROPOSED,
        sensitivity=MemorySensitivity.INTERNAL,
        created_at=SUPERSESSION_TIME,
        created_by=ACTOR,
        idempotency_key=semantic_hash(
            {
                "scope": scope.model_dump(mode="json"),
                "subject": identity.canonical_subject_key,
                "predicate": identity.predicate_id,
                "object": literal.model_dump(mode="json"),
                "valid": interval.model_dump(mode="json"),
            }
        ),
    )
    await composition.semantic.create_claim(claim, revision, evidence)


async def supersede(composition: Composition, state: CycleState, segment_id: str) -> dict[str, Any]:
    """A verified restatement supersedes the extracted one, and history survives. §2.2e.

    **What supersedes what, and why it is not staged.** The claim the cycle promoted carries
    the statement a *provider* read out of the passage. The cross-check then computed the same
    quantity with the domain's own kernel, in exact rationals — `552/5` where the textbook
    writes `110.4`. A claim carrying the value a deterministic kernel computed is better
    grounded than one carrying a value a model read, and replacing the second with the first
    is the ordinary business of an acquisition campaign: *the source did not change; what
    changed is that the campaign now holds a number it verified rather than a number it was
    told.* Both cite the same source bytes, and the walk proves it.

    **The temporal boundary is the mechanism, not a workaround.** The campaign predicate is
    functional, and the released contradiction detector compares current revisions and
    ignores belief status (W0-F3) — so a superseded predecessor whose validity was still open
    would go on contradicting its own successor, and the successor could never activate.
    Closing the predecessor at the supersession instant is what supersession *means* for a
    bitemporal functional claim: it was true until the revision, and the successor is true
    from it. Half-open intervals make the two abut without overlapping.
    """
    claim_id = state.claims[segment_id]
    original = await composition.semantic_repository.get_claim_revision(claim_id, 2)
    if original is None:
        raise RuntimeError(f"{segment_id}: no promoted revision to supersede")
    links = await composition.semantic_repository.list_evidence(claim_id, revision=2)
    if not links:
        raise RuntimeError(f"{segment_id}: the promoted revision carries no evidence")

    segment = next(item for item in state.segments if item.segment_id == segment_id)
    run = await attempt_case(
        segment.problem_type, segment.formal_inputs, store=composition.tool_events
    )
    exact = str(run.candidate.get("exact_value"))
    units = str(run.candidate.get("units"))
    statement = (
        f"{segment.value} [verified: the registered {segment.problem_type} kernel computed "
        f"{exact} {units} and domains.checker returned {run.verifier_status}]"
    )

    successor_id = _identifier(f"successor-claim:{segment_id}")
    await _create_successor(
        composition,
        state,
        segment_id,
        claim_id=successor_id,
        statement=statement,
        template=original,
        source_links=links,
    )
    await composition.semantic.add_claim_relation(
        ClaimRelation(
            relation_id=_identifier(f"supersedes:{segment_id}"),
            source=ClaimRevisionReference(claim_id=successor_id, revision=1),
            target=ClaimRevisionReference(claim_id=claim_id, revision=2),
            relation_type=ClaimRelationType.SUPERSEDES,
            valid_interval=ClaimTemporalInterval(valid_from=SUPERSESSION_TIME),
            provenance=SemanticSourceRef(
                source_type=SemanticSourceType.ARTIFACT,
                source_id=UUID(state.corpus_items[segment_id]["normalized_artifact_id"]),
                content_hash=state.corpus_items[segment_id]["normalized_artifact_hash"],
            ),
            created_at=SUPERSESSION_TIME,
        )
    )
    await composition.semantic.transition_claim(
        _revision(
            claim_id=claim_id,
            revision=3,
            previous=2,
            template=original,
            belief_status=BeliefStatus.SUPERSEDED,
            valid_interval=ClaimTemporalInterval(
                valid_from=original.valid_interval.valid_from,
                valid_to=SUPERSESSION_TIME,
            ),
            reason="superseded by a restatement carrying the kernel-verified value",
        ),
        expected_revision=2,
    )
    promotion = await _promote(composition, successor_id, from_revision=1)
    return await _verify_supersession(
        composition,
        segment=segment,
        claim_id=claim_id,
        successor_id=successor_id,
        statement=statement,
        promotion=promotion,
    )


async def _verify_supersession(
    composition: Composition,
    *,
    segment: Segment,
    claim_id: UUID,
    successor_id: UUID,
    statement: str,
    promotion: dict[str, Any],
) -> dict[str, Any]:
    """Two ways that must agree, plus the history and the stream. §2.2e, 22B's discipline."""
    scope = MemoryScope(scope_type=MemoryScopeType.DOMAIN, scope_id=segment.domain_id)

    # Way one: query the active view. The released query's default belief statuses are
    # exactly the active ones — `superseded` and `retracted` are not among them — so this is
    # the store's own answer to "what is believed about this subject now", not a filter this
    # driver invented for the occasion.
    active = await composition.semantic_repository.query_claims(
        TemporalClaimQuery(
            query_id=_identifier("active-view"),
            scopes=(scope,),
            subject_key=canonical_identifier(segment.subject),
            predicate_id=CAMPAIGN_PREDICATE_ID,
        )
    )
    active_ids = {str(item.claim_id) for item in active.claims}

    # Way two: walk the supersession chain from the predecessor.
    relations = await composition.semantic_repository.list_claim_relations(claim_id)
    edges = [
        item
        for item in relations
        if item.relation_type is ClaimRelationType.SUPERSEDES and item.target.claim_id == claim_id
    ]

    predecessor = await composition.semantic_repository.get_claim(claim_id)
    successor = await composition.semantic_repository.get_claim(successor_id)
    history = await composition.semantic_repository.list_claim_history(claim_id)
    first = await composition.semantic_repository.get_claim_revision(claim_id, 1)
    promoted = await composition.semantic_repository.get_claim_revision(claim_id, 2)
    superseded = await composition.semantic_repository.get_claim_revision(claim_id, 3)
    kept_evidence = await composition.semantic_repository.list_evidence(claim_id, revision=2)

    # History survives means the superseded revision is still loadable *with its citations
    # intact*, so the evidence is not merely present — its span is resolved again, which
    # loads the registered bytes and rehashes them.
    citations_intact = True
    for link in kept_evidence:
        try:
            await composition.source_resolver.validate_span(
                link.source_span, scope=scope, sensitivity=MemorySensitivity.INTERNAL
            )
        except (SemanticIntegrityError, SemanticPolicyError):
            citations_intact = False

    stream = await composition.events.read_stream(claim_id, from_version=1)
    successor_stream = await composition.events.read_stream(successor_id, from_version=1)

    two_ways_agree = (
        active_ids == {str(successor_id)}
        and len(edges) == 1
        and str(edges[0].source.claim_id) == str(successor_id)
    )
    return {
        "segment_id": segment.segment_id,
        "what_superseded_what": {
            "predecessor_claim_id": str(claim_id),
            "predecessor_statement": segment.value,
            "predecessor_carried": "the statement the provider read out of the passage",
            "successor_claim_id": str(successor_id),
            "successor_statement": statement,
            "successor_carries": (
                "the same fact restated with the value the domain's own kernel computed and "
                "the released checker verified"
            ),
            "the_source_did_not_change": True,
            "both_cite_the_same_registered_bytes": True,
        },
        "lifecycle": {
            "predecessor_revisions": [item.revision for item in history],
            "predecessor_belief_status": (
                predecessor.current_belief_status.value if predecessor else None
            ),
            "successor_belief_status": (
                successor.current_belief_status.value if successor else None
            ),
            "candidate_to_verified_to_superseded": [
                first.belief_status.value if first else None,
                promoted.belief_status.value if promoted else None,
                superseded.belief_status.value if superseded else None,
            ],
            "promotion": promotion,
        },
        "verified_two_ways": {
            "way_one_active_view_queried": sorted(active_ids),
            "way_two_supersession_chain_walked": [
                {
                    "relation": edge.relation_type.value,
                    "source": str(edge.source.claim_id),
                    "target": f"{edge.target.claim_id}@{edge.target.revision}",
                }
                for edge in edges
            ],
            "the_two_agree": two_ways_agree,
        },
        "history_survives": {
            "revision_1_loadable": first is not None,
            "revision_2_loadable": promoted is not None,
            "revision_3_loadable": superseded is not None,
            "revision_2_evidence_links": len(kept_evidence),
            "revision_2_citations_still_resolve_to_loaded_bytes": citations_intact,
            "revisions_after": len(history),
            "no_row_was_deleted": len(history) == 3,
        },
        "event_stream": {
            "predecessor_events": [item.envelope.event_type for item in stream],
            "successor_events": [item.envelope.event_type for item in successor_stream],
            "full_transition_sequence_present": [item.envelope.event_type for item in stream]
            == [
                "semantic.claim_created",
                "semantic.claim_belief_changed",
                "semantic.claim_belief_changed",
            ],
        },
        "the_temporal_boundary": {
            "predecessor_valid_to": SUPERSESSION_TIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "successor_valid_from": SUPERSESSION_TIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "intervals_are_half_open_so_they_abut_without_overlapping": True,
            "why_it_is_required": (
                "the released functional detector compares current revisions and ignores "
                "belief status, so a superseded claim whose validity stayed open would "
                "contradict its own successor and the successor could never activate"
            ),
        },
    }


# ---------------------------------------------------------------------------
# The retained cases cycles 2 and 3 replay
# ---------------------------------------------------------------------------


def retained_cases(state: CycleState) -> dict[str, Any]:
    """What cycle 1 retains, in the shape a later cycle's replay executes. §2.2a."""
    cases = [
        {
            "case_id": segment_id,
            "domain_id": DOMAIN_ID,
            "problem_type": segment.problem_type,
            "formal_inputs": segment.formal_inputs,
            "asserted": segment.asserted,
            "source_segment_hash": segment.content_hash,
            "claim_id": str(state.claims[segment_id]),
            "retained_by_cycle": 1,
        }
        for segment_id in sorted(state.promoted)
        for segment in [next(item for item in state.segments if item.segment_id == segment_id)]
    ]
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W2",
        "items": ["S22C-041"],
        "campaign_id": CAMPAIGN_ID,
        "manifest_revision": MANIFEST_REVISION,
        "cases": cases,
        "count": len(cases),
        "read_by": "the replay stage of every later cycle (§2.2a); a domain with no retained "
        "case is reported with cases: 0 rather than omitted",
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


# ---------------------------------------------------------------------------
# The cycle
# ---------------------------------------------------------------------------


async def _run(
    *, composition: Composition | None
) -> tuple[CycleState, Composition, dict[str, Any]]:
    passages = locate_passages(SOURCE_PATH)
    sealed = await proposals(passages, live=False)
    segments = tuple(segment_of(passage, sealed[passage.passage_id]) for passage in passages)
    rights, entry = cleared_physics()
    manifest = cycle_manifest(rights, segments)
    state, used = await run_cycle(
        manifest,
        segments=segments,
        source=cycle_source(rights, entry),
        sealed_proposals={key: dict(value) for key, value in sealed.items()},
        composition=composition,
    )
    return state, used, {"passages": passages, "sealed": sealed, "entry": entry}


def _yield_block(
    state: CycleState, passages: tuple[Passage, ...], sealed: dict[str, Any]
) -> dict[str, Any]:
    """The campaign's headline number, per chapter and per refusal reason. W2-F1."""
    by_chapter: dict[str, dict[str, Any]] = {}
    for chapter in CHAPTERS:
        located = [item for item in passages if item.chapter == chapter.number]
        formalised = [
            item for item in located if sealed[item.passage_id]["answer"].get("formalisable")
        ]
        promoted = [item for item in located if item.passage_id in state.promoted]
        by_chapter[str(chapter.number)] = {
            "chosen_for": chapter.chosen_for,
            "worked_examples": len(located),
            "formalised_by_the_provider": len(formalised),
            "promoted": len(promoted),
        }
    reasons: dict[str, int] = {}
    for item in sealed.values():
        answer = item["answer"]
        if not answer.get("formalisable"):
            reasons[str(answer.get("reason"))] = reasons.get(str(answer.get("reason")), 0) + 1
    return {
        "worked_examples_located": len(passages),
        "formalised_by_the_provider": sum(
            1 for item in sealed.values() if item["answer"].get("formalisable")
        ),
        "accepted_by_the_kernel": sum(
            1 for item in state.cross_checks.values() if item["accepted"]
        ),
        "promoted": len(state.promoted),
        "quarantined": len(state.quarantined),
        "refusal_reasons": reasons,
        "per_chapter": by_chapter,
        "acquisition_yield": round(len(state.promoted) / len(passages), 6) if passages else None,
    }


async def cycle_record(*, on_postgres: bool) -> dict[str, Any]:
    engine = None
    composition: Composition | None = None
    store: dict[str, Any] = {
        "kind": "in-memory",
        "why": "a --check rebuild of the invariants",
    }
    if on_postgres:
        url, root = campaign_environment()
        engine = create_postgres_engine(url, pool_size=4, max_overflow=0)
        composition = postgres_composition(engine, root)
        store = {
            "kind": "postgresql",
            # The database name, never the URL: a credential does not belong in evidence.
            "database": url.rsplit("/", 1)[-1],
            "artifact_root_is_configured": True,
            "tool_plane_events": "in-memory only — the released descriptor runner takes a "
            "MemoryEventStore by type (W2-F2)",
        }
    try:
        state, used, context = await _run(composition=composition)
        citations = await walk_citations(used, state)
        supersession = (
            await supersede(used, state, sorted(state.promoted)[0]) if state.promoted else None
        )
        events = await observed_event_types(used.events)
    finally:
        if engine is not None:
            await engine.dispose()

    passages = context["passages"]
    sealed = context["sealed"]
    manifest = state.manifest
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W2",
        "items": ["S22C-041", "S22C-042"],
        "recorded_at": _now(),
        "cycle": 1,
        "decides_an_exit_criterion": False,
        "why_no_exit": (
            "the exits are read once in W4 from every cycle's records. This is cycle 1 of "
            "three, and the replay, supersession and citation exits need all of them"
        ),
        "store": store,
        "manifest": {
            "campaign_id": manifest.campaign_id,
            "revision": manifest.revision,
            "content_hash": manifest.content_hash,
            "rights_content_hash": manifest.rights.content_hash,
            "domain_ids": list(manifest.domain_ids),
            "providers": list(manifest.providers),
            "declared_uses": [use.value for use in manifest.declared_uses],
            "holdout_id": manifest.holdouts[0].holdout_id,
            "holdout_measured_values": manifest.holdouts[0].measured_values,
            "curriculum_segments": len(manifest.curriculum.segment_hashes),
        },
        "extraction": {
            "prompt_template": f"{PROMPT_TEMPLATE_ID}@{PROMPT_TEMPLATE_VERSION}",
            "provider_calls_this_run": 0,
            "every_answer_came_from_a_sealed_proposal": all(
                item["from_a_sealed_proposal"] for item in state.proposals.values()
            ),
            "replayed_through_the_released_provider_path": True,
            "origin_provider": sorted({item["origin_provider_id"] for item in sealed.values()}),
            "receipts": {
                key: {
                    "request_hash": value["request_hash"],
                    "normalized_response_hash": value["normalized_response_hash"],
                    "receipt": value["receipt"],
                    "retention_mode": value["retention_mode"],
                    "rights_decision": value["rights_decision"],
                    "sealed_fixture_sha256": value["sealed_fixture_sha256"],
                }
                for key, value in sorted(sealed.items())
            },
        },
        "stages": {
            "enumerated": [stage.value for stage in CAMPAIGN_STAGES],
            "completed": state.stages_completed,
            "count": len(state.stages_completed),
            "all_nine_in_order": state.stages_completed
            == [stage.value for stage in CAMPAIGN_STAGES],
        },
        "register_source": state.corpus_items["_source_manifest"],
        "yield": _yield_block(state, passages, sealed),
        "subject_rule": subject_rule(state.segments),
        "cross_check": {
            "cases": len(state.cross_checks),
            "accepted": sum(1 for item in state.cross_checks.values() if item["accepted"]),
            "provider_and_kernel_agreed": all(
                item["as_expected"] for item in state.cross_checks.values()
            ),
            "per_segment": state.cross_checks,
        },
        "quarantine": {
            "quarantined": state.quarantined,
            "count": len(state.quarantined),
        },
        "compile": {"records": len(state.compiled)},
        "evaluate": state.replay,
        "promote": {"promoted": sorted(state.promoted), "count": len(state.promoted)},
        "observe": {"event_types": sorted(events), "count": len(events)},
        "citations": citations,
        "supersession": supersession,
        "retained_cases": retained_cases(state),
        "limitations": [
            "one cycle of three. The replay exit reads three, and forgetting is a delta "
            "across them",
            "one domain. Chemistry is a separate campaign with its own lineage, and the "
            "improvement exit runs against chemistry holdout cases this campaign never sees",
            "the Tool Plane's solve and verify events are in-memory, so the cross-check and "
            "replay legs of this cycle left no durable trace (W2-F2)",
            "the yield is this source into this domain. It is not a statement about "
            "textbooks, and §4's 'one source is one source' applies",
        ],
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


#: The facts a rebuild can be held to. Everything here is a function of the source bytes, the
#: sealed proposals and the released rules, so an in-memory rebuild must reproduce it exactly.
#: What is deliberately *outside* it is every identity the store mints — artifact ids, corpus
#: item ids, memory ids, claim ids, decision ids — and the store block itself. Those are
#: observations of one run against one store; recomputing them would prove only that the
#: record agrees with itself (W1-F1).
INVARIANT_KEYS = (
    "manifest",
    "extraction",
    "stages",
    "yield",
    "subject_rule",
    "cross_check",
    "quarantine",
    "compile",
    "promote",
)


def invariants(record: dict[str, Any]) -> dict[str, Any]:
    """The store-independent projection of a cycle record."""
    projected: dict[str, Any] = {key: record[key] for key in INVARIANT_KEYS}
    replay = dict(record["evaluate"])
    projected["evaluate"] = {key: value for key, value in replay.items() if key != "source_leakage"}
    projected["source_leakage"] = {key: value for key, value in replay["source_leakage"].items()}
    citations = record["citations"]
    projected["citations"] = {
        key: value for key, value in citations.items() if key != "per_artifact"
    }
    supersession = record["supersession"]
    projected["supersession"] = {
        "lifecycle_sequence": supersession["lifecycle"]["candidate_to_verified_to_superseded"],
        "predecessor_revisions": supersession["lifecycle"]["predecessor_revisions"],
        "the_two_agree": supersession["verified_two_ways"]["the_two_agree"],
        "history_survives": supersession["history_survives"],
        "event_stream": supersession["event_stream"],
        "temporal_boundary": supersession["the_temporal_boundary"],
    }
    return projected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle", action="store_true", help="run cycle 1 on the campaign store")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--memory", action="store_true", help="run in memory, for a dry pass")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    if arguments.check:
        stored = _load(arguments.output)
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed_ok = _sha256(_canonical(body)) == stored["integrity_content_hash"]
        rebuilt = asyncio.run(cycle_record(on_postgres=False)) if SOURCE_PATH.exists() else None
        same = rebuilt is not None and invariants(stored) == invariants(rebuilt)
        retained_ok = _seal_intact(RETAINED)
        print(
            json.dumps(
                {
                    "path": arguments.output.name,
                    "stored_seal_intact": sealed_ok,
                    "retained_cases_seal_intact": retained_ok,
                    "source_available": SOURCE_PATH.exists(),
                    # The campaign store's own rows are not rebuilt here: they are an
                    # observation of one run, and a validator that recomputed them would only
                    # prove the record agrees with itself.
                    "invariants_rebuilt_in_memory_and_identical": same,
                    "reproduced": sealed_ok and retained_ok and (same or not SOURCE_PATH.exists()),
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if sealed_ok and retained_ok and (same or not SOURCE_PATH.exists()) else 1

    if not (arguments.cycle or arguments.memory):
        parser.error("choose --cycle, --memory or --check")
    record = asyncio.run(cycle_record(on_postgres=arguments.cycle))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if arguments.cycle:
        RETAINED.write_text(
            json.dumps(record["retained_cases"], indent=1, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "store": record["store"]["kind"],
                "stages": record["stages"]["count"],
                "yield": record["yield"],
                "promoted": record["promote"]["count"],
                "citations_resolve": record["citations"]["all_chains_resolve"],
                "supersession_two_ways_agree": (
                    record["supersession"]["verified_two_ways"]["the_two_agree"]
                    if record["supersession"]
                    else None
                ),
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
