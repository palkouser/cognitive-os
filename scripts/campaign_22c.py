"""S22C-003. The Sprint 22C campaign drivers, in one module.

Everything §1.2 says must be built is here — the cycle runner, the rolling replay harness,
the citation walker, the planted-update fixture, and the fixture-scale source the W0 slice
runs against — because five scripts sharing a manifest, a store composition and a stage
enumeration are one script wearing five hats. 22B learned that at scale; a campaign has the
same shape.

**What is composed rather than rebuilt**, which is the load-bearing half:

| Stage | Composed from |
|---|---|
| register source | `CorpusFactory.ingest` — rights, licence, sensitivity, lineage, routing |
| extract | sealed proposals revalidated on the host; no provider call in the slice |
| normalize | `SemanticExtractionService.commit` — observations, claims, evidence |
| cross-check | the pilots' own deterministic kernels through `run_descriptor_case` |
| quarantine | the released `CorpusQuarantineReason` vocabulary |
| compile | `MemoryService.create` with a `MemoryProvenanceBundle` |
| evaluate | `run_descriptor_case` again, over every domain `registry.domain_ids()` names |
| promote | `SemanticPromotionGate.decide` then `SemanticMemoryService.transition_claim` |
| observe | the event store the other eight stages already wrote to |

Nothing in this module is a second implementation of a released rule. The one thing it adds
is *sequence*: the Corpus Factory's quarantine states, the semantic promotion gate and the
memory lifecycle have never been driven by one runner in one order, and §3.1 predicts the
cheapest defect of the sprint lives in that seam.

    UV_CACHE_DIR=.cache/uv uv run python scripts/campaign_22c.py --slice
    UV_CACHE_DIR=.cache/uv uv run python scripts/campaign_22c.py --check

`--slice` runs all nine stages against the fixture-scale source, including one refused plant
and one citation walk, and decides no exit criterion: every 22C exit is a claim about the
real rights-cleared source, so publishing the pre-registration after this run is not
publishing it after the numbers.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.services.memory_service import MemoryService
from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration
from cognitive_os.corpus.factory import CorpusFactory
from cognitive_os.corpus.fixtures import FixtureArtifactStore
from cognitive_os.corpus.repository import InMemoryCorpusRepository
from cognitive_os.corpus.sources import SourceMaterial, _build_source
from cognitive_os.domain.campaigns import (
    CAMPAIGN_STAGES,
    CampaignBudget,
    CampaignCurriculum,
    CampaignHoldout,
    CampaignManifestV1,
    CampaignSourceRights,
    CampaignStage,
    CampaignStopReason,
    RightsClearanceStatus,
)
from cognitive_os.domain.corpus import (
    CorpusFactoryRequest,
    CorpusQuarantineReason,
    CorpusSourceType,
    CorpusUsageRight,
)
from cognitive_os.domain.descriptors import validate_domain_package
from cognitive_os.domain.memory import (
    MemoryCreator,
    MemoryCreatorType,
    MemoryProvenanceBundle,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemorySourceIdentity,
    MemorySourceRef,
    MemorySourceType,
    MemoryStatus,
    MemoryType,
    MemoryWritePolicy,
    MemoryWriteRequest,
    ObservationMemoryContent,
)
from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    Cardinality,
    ClaimPromotionOutcome,
    ClaimProposal,
    ClaimRevision,
    ClaimRevisionReference,
    ClaimTemporalInterval,
    ExtractionBudget,
    GroundedSourceSpan,
    GroundingMode,
    ObservationProposal,
    PredicateDescriptor,
    SemanticActor,
    SemanticActorType,
    SemanticEntityRef,
    SemanticExtractionProposal,
    SemanticLiteral,
    SemanticLiteralKind,
    SemanticSourceRef,
    SemanticSourceType,
    claim_revision_hash,
    semantic_hash,
)
from cognitive_os.domains import registry
from cognitive_os.domains.chemistry import CHEMISTRY_KERNELS
from cognitive_os.domains.descriptor_runner import run_descriptor_case
from cognitive_os.domains.mechanics import MECHANICS_KERNELS
from cognitive_os.domains.registry import UnsupportedProblemType
from cognitive_os.events.memory_event_service import MemoryEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
from cognitive_os.events.verifier_event_service import VerifierEventService
from cognitive_os.memory.repository import InMemoryMemoryRepository
from cognitive_os.semantic_memory.beliefs import aggregate_confidence
from cognitive_os.semantic_memory.compilation import SemanticExtractionService
from cognitive_os.semantic_memory.errors import SemanticIntegrityError
from cognitive_os.semantic_memory.grounding import TrustedSourceResolver
from cognitive_os.semantic_memory.predicates import (
    PredicateRegistry,
    build_default_predicate_registry,
)
from cognitive_os.semantic_memory.promotion import SemanticPromotionGate
from cognitive_os.semantic_memory.repository import InMemorySemanticMemoryRepository
from cognitive_os.semantic_memory.service import SemanticMemoryService
from cognitive_os.tools.errors import ToolPlaneError
from cognitive_os.verification.factory import build_builtin_registry

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
PACKAGES = REPO / "docs/sprints/sprint-22/packages"

#: The two pilots 22A committed, admitted before any stage resolves a problem type. A
#: campaign that registered its domains half way through its own pipeline would be a
#: campaign whose first stages ran against a different registry than its last (§1.4's
#: warning, one layer down).
PILOT_PACKAGES = (
    (PACKAGES / "engineering.mechanics.v1.json", MECHANICS_KERNELS),
    (PACKAGES / "science.chemistry.v1.json", CHEMISTRY_KERNELS),
)


def register_pilots() -> tuple[str, ...]:
    """Admit both pilot domains into this process, idempotently.

    Re-registering a `(domain_id, revision)` is a refusal by design (22A), never a replace,
    so the guard is a membership test rather than a try/except that would hide a genuine
    duplicate.
    """
    admitted = []
    for path, kernels in PILOT_PACKAGES:
        descriptor = validate_domain_package(path.read_bytes())
        if (
            descriptor.domain_id,
            descriptor.revision,
        ) not in registry.registered_descriptor_domains():
            registry.register_descriptor_domain(descriptor, kernels)
        admitted.append(descriptor.domain_id)
    return tuple(admitted)


#: One instant for the whole slice. A campaign record whose hashes move with the wall clock
#: cannot be reproduced, and §3.2's third risk is exactly that: a cycle nobody can rebuild.
SLICE_TIME = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)

ACTOR = SemanticActor(
    actor_type=SemanticActorType.APPROVED_INTERNAL_SERVICE, actor_id="sprint-22c-campaign"
)
MEMORY_ACTOR = MemoryCreator(
    creator_type=MemoryCreatorType.APPROVED_INTERNAL_SERVICE, creator_id="sprint-22c-campaign"
)


def _identifier(label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"cognitive-os:sprint-22c:{label}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# The fixture-scale source
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Segment:
    """One passage of the fixture chapter, and everything derived from it.

    A segment carries its own evaluation case because that is what makes the citation exit
    testable: the case is a *derivative*, so the walk from the case back to these bytes has
    to resolve like every other derivative's does.
    """

    segment_id: str
    domain_id: str
    problem_type: str
    subject: str
    predicate_id: str
    #: The quantity the passage asserts, as the released semantic literal carries it.
    literal_kind: SemanticLiteralKind
    value: str
    unit: str | None
    prose: str
    formal_inputs: dict[str, Any]
    #: **The conclusion the passage asserts**, in the kernel's own answer vocabulary. This
    #: is what makes the cross-check a check on the *source* rather than on the solver — see
    #: W0-F4 and `stage_cross_check`.
    asserted: dict[str, Any]
    #: Whether the segment is expected to survive the cross-check. A segment whose asserted
    #: conclusion the kernel does not reproduce is quarantined, and that is the door the
    #: plant enters.
    expected_accepted: bool
    quarantine_reason: CorpusQuarantineReason | None = None

    @property
    def markdown(self) -> str:
        return f"## {self.segment_id}\n\n{self.prose}\n"

    @property
    def content_hash(self) -> str:
        return _sha256(self.markdown.encode("utf-8"))


#: Five genuine passages across the two pilot domains, and one plant. The physics is
#: deliberately ordinary: the sprint is not proving mechanics, it is proving that a passage
#: can travel register -> extract -> normalize -> cross-check -> quarantine -> compile ->
#: evaluate -> promote -> observe and keep its citation.
FIXTURE_SEGMENTS: tuple[Segment, ...] = (
    Segment(
        segment_id="mechanics-uniform-motion",
        domain_id="engineering.mechanics",
        problem_type="mechanics.uniform-motion",
        subject="mechanics:uniform-motion",
        predicate_id="domain.worked_example",
        literal_kind=SemanticLiteralKind.STRING,
        value="a body at 5 m/s for 4 s covers 20 m",
        unit=None,
        prose=(
            "A body moving at a constant speed of 5 m/s for 4 s covers a displacement of "
            "20 m. Displacement is the product of speed and elapsed time whenever the speed "
            "does not change over the interval."
        ),
        formal_inputs={
            "speed": {"magnitude": 5, "unit": "m/s"},
            "time": {"magnitude": 4, "unit": "s"},
            "result_unit": "m",
        },
        asserted={"exact_value": "20", "units": "m"},
        expected_accepted=True,
    ),
    Segment(
        segment_id="mechanics-statics-equilibrium",
        domain_id="engineering.mechanics",
        problem_type="mechanics.statics-equilibrium",
        subject="mechanics:statics-equilibrium",
        predicate_id="domain.worked_example",
        literal_kind=SemanticLiteralKind.STRING,
        value="two opposed coplanar forces of equal magnitude balance",
        unit=None,
        prose=(
            "Two coplanar forces of (3, 4) N and (-3, -4) N acting on one rigid body sum to "
            "a zero resultant, so the body is in equilibrium. The vector sum of the forces "
            "on a body at rest vanishes."
        ),
        formal_inputs={
            "forces": [
                {"name": "cable", "fx": 3, "fy": 4},
                {"name": "reaction", "fx": -3, "fy": -4},
            ],
            "force_unit": "N",
        },
        asserted={"structured": {"equilibrium": True}},
        expected_accepted=True,
    ),
    Segment(
        segment_id="mechanics-moment-balance",
        domain_id="engineering.mechanics",
        problem_type="mechanics.moment-balance",
        subject="mechanics:moment-balance",
        predicate_id="domain.worked_example",
        literal_kind=SemanticLiteralKind.STRING,
        value="a 6 N force at a 2 m lever arm produces 12 N*m about the pivot",
        unit=None,
        prose=(
            "A force of 6 N applied perpendicularly at a distance of 2 m from a pivot "
            "produces a moment of 12 N*m about that pivot. The moment is the cross product "
            "of the lever arm and the force."
        ),
        formal_inputs={
            "pivot": {"x": 0, "y": 0},
            "forces": [{"name": "load", "x": 2, "y": 0, "fx": 0, "fy": 6}],
            "force_unit": "N",
            "length_unit": "m",
            "moment_unit": "N*m",
        },
        asserted={"exact_value": "12", "units": "N*m"},
        expected_accepted=True,
    ),
    Segment(
        segment_id="chemistry-molar-conversion",
        domain_id="science.chemistry",
        problem_type="chemistry.molar-conversion",
        subject="chemistry:molar-conversion",
        predicate_id="domain.worked_example",
        literal_kind=SemanticLiteralKind.STRING,
        value="36 g of water is 2 mol",
        unit=None,
        prose=(
            "Water has a molar mass of 18 g/mol when hydrogen is taken as 1 g/mol and oxygen "
            "as 16 g/mol, so a 36 g sample contains 2 mol. The molar mass of a substance is "
            "summed from the atomic masses its formula names."
        ),
        formal_inputs={
            "formula": "H2O",
            "atomic_masses": {"H": 1, "O": 16},
            "mass": {"magnitude": 36, "unit": "g"},
            "molar_mass_unit": "g/mol",
        },
        asserted={"exact_value": "2", "units": "mol"},
        expected_accepted=True,
    ),
    Segment(
        segment_id="chemistry-mass-balance",
        domain_id="science.chemistry",
        problem_type="chemistry.mass-balance",
        subject="chemistry:mass-balance",
        predicate_id="domain.worked_example",
        literal_kind=SemanticLiteralKind.STRING,
        value="2 H2 + O2 -> 2 H2O conserves mass",
        unit=None,
        prose=(
            "The reaction of two moles of hydrogen with one mole of oxygen to give two moles "
            "of water balances: four hydrogen atoms and two oxygen atoms appear on each "
            "side, and the total mass of the reactants equals the total mass of the products."
        ),
        formal_inputs={
            "reactants": [
                {"formula": "H2", "coefficient": 2},
                {"formula": "O2", "coefficient": 1},
            ],
            "products": [{"formula": "H2O", "coefficient": 2}],
            "atomic_masses": {"H": 1, "O": 16},
        },
        asserted={"structured": {"balanced": True}},
        expected_accepted=True,
    ),
)

#: **The planted harmful update (§2.2b), authored and sealed in W0.**
#:
#: It is not malformed and it is not obviously wrong to read: it states a plausible-sounding
#: stoichiometric conclusion with one coefficient altered, so nothing about its *shape*
#: distinguishes it from the five passages above. What distinguishes it is that the derived
#: case fails the pilot's own deterministic checker — a mass balance that does not balance.
#: That is the point: the plant is caught by the same cross-check every genuine segment
#: passes through, entering by the same intake path, and not by a special door.
PLANT = Segment(
    segment_id="chemistry-mass-balance-planted",
    domain_id="science.chemistry",
    problem_type="chemistry.mass-balance",
    subject="chemistry:mass-balance",
    predicate_id="domain.worked_example",
    literal_kind=SemanticLiteralKind.STRING,
    value="2 H2 + O2 -> 3 H2O conserves mass",
    unit=None,
    prose=(
        "The reaction of two moles of hydrogen with one mole of oxygen gives three moles of "
        "water, and the equation as written conserves mass because the same species appear "
        "on both sides."
    ),
    formal_inputs={
        "reactants": [
            {"formula": "H2", "coefficient": 2},
            {"formula": "O2", "coefficient": 1},
        ],
        "products": [{"formula": "H2O", "coefficient": 3}],
        "atomic_masses": {"H": 1, "O": 16},
    },
    asserted={"structured": {"balanced": True}},
    expected_accepted=False,
    quarantine_reason=CorpusQuarantineReason.UNVERIFIABLE_PROVIDER_DATA,
)


def all_segments() -> tuple[Segment, ...]:
    """The intake stream: genuine content and the plant, in one list.

    The plant sits *inside* the ordinary sequence rather than beside it. A fixture that kept
    them in two lists would let a stage tell them apart by which list it was handed.
    """
    return (*FIXTURE_SEGMENTS[:5], PLANT)


def fixture_source_hash() -> str:
    """The whole chapter's content hash — the source identity rights are cleared against."""
    return _sha256("".join(segment.markdown for segment in all_segments()).encode("utf-8"))


# ---------------------------------------------------------------------------
# The rights gate
# ---------------------------------------------------------------------------


class RightsNotCleared(RuntimeError):
    """Raised at the door of stage 1. §1.3: no sealed rights evidence, no source."""


def rights_gate(rights: CampaignSourceRights | None, source_content_hash: str) -> None:
    """The one refusal that runs before anything reads a source byte.

    Two failures, not one. A campaign with no clearance at all is the blocking dependency
    §3.2 names. A campaign whose clearance was issued against *different bytes* is worse: it
    looks cleared. Both are refused here, and the second is why the clearance carries the
    source's content hash rather than its title.
    """
    if rights is None:
        raise RightsNotCleared(
            "no sealed rights record for this source. Sprint 22C W0 blocks on source-rights "
            "clearance; see §1.3 and §3.2 of the technical backlog"
        )
    if rights.status is not RightsClearanceStatus.CLEARED:
        raise RightsNotCleared(f"rights clearance is {rights.status.value}, not cleared")
    if rights.source_content_hash != source_content_hash:
        raise RightsNotCleared(
            "the rights clearance names a different source: cleared "
            f"{rights.source_content_hash[:16]}…, presented {source_content_hash[:16]}…"
        )


def fixture_rights() -> CampaignSourceRights:
    """The fixture chapter's clearance.

    This chapter is authored in this repository for this sprint, so its rights are not a
    review's outcome but a fact about the repository, and clearing it decides nothing about
    the real source. W1's source needs the gate owner's record; this one exists so the gate
    can be *exercised* at fixture scale rather than only described.
    """
    return CampaignSourceRights(
        status=RightsClearanceStatus.CLEARED,
        source_content_hash=fixture_source_hash(),
        edition="1",
        author="cognitive-os/sprint-22c",
        location="scripts/campaign_22c.py#FIXTURE_SEGMENTS",
        license_identifier="Apache-2.0",
        permitted_uses=(
            CorpusUsageRight.INTERNAL_USE,
            CorpusUsageRight.DERIVATIVE_WORK,
            CorpusUsageRight.BENCHMARK_USE,
        ),
        cleared_by="sprint-22c-w0",
        cleared_at=SLICE_TIME,
        evidence_hash=_sha256(b"cognitive-os authored fixture chapter, Apache-2.0, in-repository"),
        notes=(
            "authored in-repository for the W0 slice; clears nothing about the real "
            "rights-cleared chapter W1 registers"
        ),
    )


def fixture_manifest() -> CampaignManifestV1:
    """One sealed manifest for the slice campaign."""
    segments = all_segments()
    return CampaignManifestV1(
        campaign_id="s22c-w0-slice",
        revision=1,
        rights=fixture_rights(),
        domain_ids=("engineering.mechanics", "science.chemistry"),
        goals=(
            "drive all nine §9.1 stages in order against a fixture-scale source",
            "refuse the planted update through the genuine intake path",
            "walk every promoted artifact's citation back to loaded source bytes",
        ),
        budget=CampaignBudget(
            maximum_cycles=1,
            maximum_provider_calls_per_cycle=0,
            maximum_spend_usd=0.0,
            maximum_items_per_cycle=64,
        ),
        providers=(),
        curriculum=CampaignCurriculum(
            segment_hashes=tuple(segment.content_hash for segment in segments),
            segments_per_cycle=len(segments),
        ),
        holdouts=(
            CampaignHoldout(
                holdout_id="s22c-w0-slice-holdout",
                case_hashes=(_sha256(b"s22c-w0-slice-holdout-placeholder"),),
                verifier_id="domains.checker",
                seeds=(22_003,),
                success_definition=(
                    "the case is accepted by domains.checker with every required capability "
                    "exercised"
                ),
                store_url_env="COGOS_HOLDOUT_DATABASE_URL",
            ),
        ),
        stop_conditions=(
            CampaignStopReason.STAGE_REFUSED,
            CampaignStopReason.CYCLE_TARGET_REACHED,
        ),
        declared_uses=(CorpusUsageRight.INTERNAL_USE, CorpusUsageRight.DERIVATIVE_WORK),
        sealed_at=SLICE_TIME,
        sealed_by="sprint-22c-w0",
    )


# ---------------------------------------------------------------------------
# The cycle runner
# ---------------------------------------------------------------------------


@dataclass
class CycleState:
    """Everything one cycle accumulates, and the ledger of which stages actually ran."""

    manifest: CampaignManifestV1
    stages_completed: list[str] = field(default_factory=list)
    corpus_items: dict[str, Any] = field(default_factory=dict)
    proposals: dict[str, dict[str, Any]] = field(default_factory=dict)
    claims: dict[str, UUID] = field(default_factory=dict)
    cross_checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    normalized: dict[str, SemanticExtractionProposal] = field(default_factory=dict)
    quarantined: dict[str, str] = field(default_factory=dict)
    compiled: dict[str, dict[str, Any]] = field(default_factory=dict)
    promoted: list[str] = field(default_factory=list)
    replay: dict[str, Any] = field(default_factory=dict)
    citations: dict[str, Any] = field(default_factory=dict)
    events: tuple[str, ...] = ()


class StageOutOfOrder(RuntimeError):
    """A cycle that skipped a stage is not a cycle (§2.2a)."""


class CycleRunner:
    """Drives the nine §9.1 stages in order and refuses to skip one.

    The refusal is the substance. Every stage below could be called directly, and a driver
    that merely *documented* the order would let a later wave quietly drop `cross_check`
    from a cycle whose numbers looked fine. `enter` is the only way in, and it compares the
    stage against `CAMPAIGN_STAGES` rather than against a list retyped here.
    """

    def __init__(self, state: CycleState) -> None:
        self._state = state

    def enter(self, stage: CampaignStage) -> None:
        expected = CAMPAIGN_STAGES[len(self._state.stages_completed)]
        if stage is not expected:
            raise StageOutOfOrder(
                f"stage {stage.value!r} entered where {expected.value!r} was due; "
                f"completed so far: {self._state.stages_completed}"
            )

    def leave(self, stage: CampaignStage) -> None:
        self._state.stages_completed.append(stage.value)

    @property
    def complete(self) -> bool:
        return tuple(self._state.stages_completed) == tuple(
            stage.value for stage in CAMPAIGN_STAGES
        )


@dataclass(frozen=True, slots=True)
class Composition:
    """The released services one cycle runs against, built once."""

    events: MemoryEventStore
    corpus: CorpusFactory
    artifacts: FixtureArtifactStore
    memory: MemoryService
    memory_repository: InMemoryMemoryRepository
    semantic: SemanticMemoryService
    semantic_repository: InMemorySemanticMemoryRepository
    source_resolver: TrustedSourceResolver
    semantic_events: SemanticMemoryEventService
    predicates: PredicateRegistry


def build_composition() -> Composition:
    """One composition of released services, in memory.

    In-memory is not a shortcut around the store: it is what makes the slice deterministic
    and lets its assertions run in CI, where no 22C database exists. The same stage
    functions run against PostgreSQL repositories unchanged, because every one of them takes
    a service rather than a connection.
    """
    events = MemoryEventStore()
    artifacts = FixtureArtifactStore()
    memory_repository = InMemoryMemoryRepository()
    semantic_repository = InMemorySemanticMemoryRepository()
    predicates = build_campaign_predicate_registry()
    semantic_events = SemanticMemoryEventService(events)
    source_resolver = TrustedSourceResolver(memory_repository, artifacts=artifacts)
    return Composition(
        events=events,
        corpus=CorpusFactory(InMemoryCorpusRepository(), artifacts, CorpusConfiguration()),
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


#: **W0-F2.** The released predicate registry is host-owned, closed and *frozen*: its
#: thirteen predicates describe projects, repositories, tasks and verification, and
#: `build_default_predicate_registry` calls `freeze()` before it returns. A knowledge
#: campaign normalizing a technical passage has nothing to say it under — the seam §3.1
#: predicted, found by running the driver rather than by reading it.
#:
#: The composed answer, and the reason this is not a released-code change: `PredicateRegistry`
#: is publicly constructible and `register` is public before `freeze`, which is exactly how
#: `benchmarks/semantic_adapter.py` already builds a registry of its own. The campaign
#: registry is therefore *the released descriptors plus the campaign's own*, so acquired
#: claims and released claims live under one vocabulary rather than two.
#:
#: The consequence is recorded rather than hidden: `registry_snapshot_hash` on a campaign
#: extraction is not the released snapshot hash, and it cannot be — a registry that gained a
#: predicate is allowed to say so, which is 22A's S22A-030 decision one layer down.
CAMPAIGN_PREDICATE_ID = "domain.worked_example"
CAMPAIGN_SUBJECT_TYPE = "domain_topic"


def build_campaign_predicate_registry() -> PredicateRegistry:
    """The released vocabulary, plus the one predicate a campaign needs, then frozen."""
    registry = PredicateRegistry()
    for descriptor in build_default_predicate_registry().list_all():
        registry.register(descriptor)
    registry.register(
        PredicateDescriptor(
            predicate_id=CAMPAIGN_PREDICATE_ID,
            version="1",
            display_name="Domain worked example",
            description=(
                "A worked example a domain's deterministic kernel can recompute, acquired "
                "from a rights-cleared source."
            ),
            allowed_subject_types=(CAMPAIGN_SUBJECT_TYPE,),
            allowed_object_types=(SemanticLiteralKind.STRING,),
            # Functional on purpose. Two different worked results for one domain topic over
            # overlapping validity is a contradiction, and the released functional detector
            # is what says so — which is how the plant is caught a second time, by a rule
            # this driver did not write.
            cardinality=Cardinality.FUNCTIONAL,
            temporal_behavior="bitemporal",
            default_sensitivity=MemorySensitivity.INTERNAL,
            rendering_label=CAMPAIGN_PREDICATE_ID,
            contradiction_rule="functional_overlap",
        )
    )
    registry.freeze()
    return registry


async def grounding_span(composition: Composition, item: dict[str, Any]) -> GroundedSourceSpan:
    """The span both extract and normalize use, built once.

    It names a real half-open byte range in the registered artifact and carries that
    excerpt's hash, so the released resolver loads the bytes and hash-checks them. Grounding
    the whole normalized passage is the honest range here: the passage *is* the excerpt the
    claim was read from. Two stages building this separately is how the two would drift.
    """
    artifact_id = UUID(item["normalized_artifact_id"])
    registered = await composition.artifacts.get_bytes(artifact_id)
    return GroundedSourceSpan(
        source=SemanticSourceRef(
            source_type=SemanticSourceType.ARTIFACT,
            source_id=artifact_id,
            content_hash=item["normalized_artifact_hash"],
        ),
        mode=GroundingMode.ARTIFACT_BYTES,
        start=0,
        end=len(registered),
        excerpt_hash=_sha256(registered),
    )


# --- stage 1 -----------------------------------------------------------------


async def stage_register_source(
    runner: CycleRunner, composition: Composition, state: CycleState
) -> None:
    """Rights first, then the released Corpus Factory. Nothing reads a byte before the gate."""
    runner.enter(CampaignStage.REGISTER_SOURCE)
    rights_gate(state.manifest.rights, fixture_source_hash())

    segments = all_segments()
    source = _build_source(
        CorpusSourceType.DOCUMENT,
        "s22c:fixture-chapter",
        "1",
        [
            SourceMaterial(
                f"{segment.segment_id}.md",
                segment.markdown.encode("utf-8"),
                "text/markdown",
                "utf-8",
            )
            for segment in segments
        ],
        CorpusConfiguration(),
    )
    request = CorpusFactoryRequest(
        request_id=_identifier("corpus-request:slice"),
        source_type=CorpusSourceType.DOCUMENT,
        source_identity=source.source_identity,
        source_revision=source.source_revision,
        scope="project:cognitive-os",
        sensitivity=MemorySensitivity.INTERNAL,
        license_identifiers=(state.manifest.rights.license_identifier,),
        usage_rights={right: True for right in state.manifest.rights.permitted_uses},
        created_at=SLICE_TIME,
        created_by="sprint-22c-campaign",
    )
    result = await composition.corpus.ingest(request, source)

    # The factory keys items by canonical content hash; the campaign keys everything by
    # segment id. Binding them here, once, is what stops five later stages from each
    # inventing their own correspondence — which is exactly how a provenance hop gets lost.
    by_hash = {item.canonical_content_hash: item for item in result.items}
    for segment in segments:
        normalized = next(
            (
                content
                for content in result.normalized
                if any(
                    entry.relative_path == f"{segment.segment_id}.md"
                    for entry in content.source_file_refs
                )
            ),
            None,
        )
        if normalized is None:
            raise RuntimeError(f"segment {segment.segment_id} produced no normalized content")
        item = by_hash.get(normalized.canonical_content_hash)
        if item is None:
            raise RuntimeError(f"segment {segment.segment_id} produced no corpus item")
        state.corpus_items[segment.segment_id] = {
            "corpus_item_id": str(item.corpus_item_id),
            "status": item.current_status.value,
            "canonical_content_hash": item.canonical_content_hash,
            "normalized_artifact_id": str(item.normalized_content_artifact.artifact_id),
            "normalized_artifact_hash": item.normalized_content_artifact.content_hash,
            "source_manifest_id": str(normalized.source_manifest_id),
            "source_file_hashes": sorted(item.source_refs),
            "lineage_ref": item.lineage_ref,
        }
    state.corpus_items["_source_manifest"] = {
        "source_manifest_id": str(result.source_manifest.source_manifest_id),
        "source_manifest_hash": result.source_manifest.content_hash,
        "license_status": sorted({item.status.value for item in result.licenses}),
        "items": len(result.items),
    }
    runner.leave(CampaignStage.REGISTER_SOURCE)


# --- stage 2 -----------------------------------------------------------------


async def stage_extract(runner: CycleRunner, composition: Composition, state: CycleState) -> None:
    """Sealed proposals, revalidated on the host. No provider call, by manifest.

    §3.3: a cycle that can only be reproduced by re-calling a provider is not replayable
    evidence. Every extraction lands as `(request_hash, response_hash, receipt)` and the
    deterministic half — that the proposed value is the one the passage actually contains —
    is revalidated here. At fixture scale the proposal is authored beside the passage, which
    is the same shape a sealed provider proposal has on replay.
    """
    runner.enter(CampaignStage.EXTRACT)
    if state.manifest.providers:
        raise RuntimeError("the slice manifest declares no providers; a live call is a finding")
    for segment in all_segments():
        item = state.corpus_items[segment.segment_id]
        request_hash = _sha256(
            _canonical(
                {
                    "segment": segment.segment_id,
                    "artifact": item["normalized_artifact_id"],
                    "schema": "s22c-extraction-v1",
                }
            )
        )
        response = {
            "segment": segment.segment_id,
            "subject": segment.subject,
            "predicate_id": segment.predicate_id,
            "value": segment.value,
            "problem_type": segment.problem_type,
            "formal_inputs": segment.formal_inputs,
        }
        # **The host-side revalidation, composed rather than invented.** The released
        # `ProviderSemanticExtractionService` revalidates a proposal by resolving its
        # grounding spans through `TrustedSourceResolver` — which loads the cited bytes and
        # rehashes them — and by checking the proposed predicate, subject type and object
        # type against the host registry. It deliberately does *not* try to confirm that the
        # asserted value is true; that is not decidable from text, and it is what the
        # cross-check stage exists for. This stage runs the same two legs on a sealed
        # proposal, so a campaign replaying from seals is held to the standard a live
        # provider call would have been.
        span = await grounding_span(composition, item)
        try:
            await composition.source_resolver.validate_span(
                span,
                scope=MemoryScope(scope_type=MemoryScopeType.DOMAIN, scope_id=segment.domain_id),
                sensitivity=MemorySensitivity.INTERNAL,
            )
            grounding_resolves = True
            grounding_error = ""
        except SemanticIntegrityError as error:
            grounding_resolves = False
            grounding_error = str(error)
        descriptor = composition.predicates.require(segment.predicate_id)
        types_admitted = (
            CAMPAIGN_SUBJECT_TYPE in descriptor.allowed_subject_types
            and segment.literal_kind in descriptor.allowed_object_types
        )
        state.proposals[segment.segment_id] = {
            "request_hash": request_hash,
            "response_hash": _sha256(_canonical(response)),
            "receipt": f"sealed-proposal:{segment.segment_id}",
            "provider_call": False,
            "grounding_resolves_to_loaded_bytes": grounding_resolves,
            "grounding_error": grounding_error,
            "predicate_and_types_admitted_by_the_host": types_admitted,
            "host_revalidated": bool(grounding_resolves and types_admitted),
            "what_revalidation_does_not_check": (
                "whether the asserted value is true — not decidable from text, and the "
                "cross-check stage's job"
            ),
            "response": response,
        }
    runner.leave(CampaignStage.EXTRACT)


# --- stage 3 -----------------------------------------------------------------


async def stage_normalize(runner: CycleRunner, composition: Composition, state: CycleState) -> None:
    """Content becomes claim *structures* — and nothing is written to the semantic store.

    **W0-F3, and the reason the slice exists.** The first version of this driver committed
    each claim here, at stage 3. Running it proved why the development plan does not: §9.1
    creates "semantic revisions" at **compile**, stage 6, two stages after the cross-check
    that judges them. With the commit at stage 3 the planted passage's claim sat in the
    store as a proposed revision, and the released promotion gate's
    `semantic.critical_contradiction` verifier then refused the *genuine* claim it
    contradicts — so one planted update denied promotion to the very knowledge it falsifies,
    turning a content attack into a denial of acquisition. Normalize now produces the
    proposal and stops; unverified content never reaches the knowledge store at all.

    The grounding span points at the corpus item's own content-addressed artifact, so when
    compile does commit, the released `TrustedSourceResolver` loads and hash-checks the
    registered bytes on the way in. That is the first hop of the citation chain, and it is a
    released check rather than one this driver invented.
    """
    runner.enter(CampaignStage.NORMALIZE)
    composition.predicates.require(CAMPAIGN_PREDICATE_ID)
    for segment in all_segments():
        item = state.corpus_items[segment.segment_id]
        span = await grounding_span(composition, item)
        root = f"slice:{segment.segment_id}"
        observation_id = _identifier(f"{root}:observation")
        proposal = SemanticExtractionProposal(
            extraction_id=_identifier(root),
            registry_snapshot_hash=composition.predicates.snapshot_hash(),
            observations=(
                ObservationProposal(
                    proposal_id=observation_id, content=segment.prose, source_spans=(span,)
                ),
            ),
            claims=(
                ClaimProposal(
                    proposal_id=_identifier(f"{root}:claim"),
                    subject=SemanticEntityRef(
                        entity_id=segment.subject, entity_type=CAMPAIGN_SUBJECT_TYPE
                    ),
                    predicate_id=segment.predicate_id,
                    object=SemanticLiteral(
                        literal_kind=segment.literal_kind, value=segment.value, unit=segment.unit
                    ),
                    valid_interval=ClaimTemporalInterval(valid_from=SLICE_TIME),
                    observation_proposal_ids=(observation_id,),
                ),
            ),
            budget=ExtractionBudget(
                maximum_observations=1,
                maximum_claims=1,
                maximum_evidence_links=1,
                maximum_relations=0,
            ),
        )
        state.normalized[segment.segment_id] = proposal
    runner.leave(CampaignStage.NORMALIZE)


# --- stage 4 -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    """One case attempted, whether or not the platform was willing to attempt it.

    **W0-F5.** `run_descriptor_case` has a branch for a solve that did not complete — and
    for the commonest refusal of all, a kernel declining a case, that branch is unreachable.
    The released Tool Plane records a `failed` event and then **re-raises** `ToolPlaneError`,
    so the exception escapes the runner. Any harness that must *measure* refusals rather
    than merely avoid them — the holdout's arm A, whose whole point is that the case fails
    without acquired knowledge, or a replay over a domain with one malformed case — would
    abort the entire cycle on the first one.

    The guard lives here, in the one helper every 22C caller routes through, rather than in
    each of them: cross-check, replay and both holdout arms need identical semantics, and
    three copies of a try/except is how two of them drift.
    """

    problem_type: str
    domain_id: str
    accepted: bool
    verifier_status: str
    message: str
    candidate: dict[str, Any]
    refused_before_solving: bool


async def attempt_case(
    problem_type: str,
    formal_inputs: dict[str, Any],
    *,
    store: MemoryEventStore | None = None,
) -> CaseOutcome:
    """Run one case through the released path, returning a refusal instead of raising."""
    try:
        run = await run_descriptor_case(problem_type, formal_inputs, store=store)
    except (ToolPlaneError, UnsupportedProblemType) as error:
        # Two refusals, one shape. `UnsupportedProblemType` is raised by the registry before
        # the Tool Plane is reached and is a LookupError rather than a ToolPlaneError, so a
        # manifest naming a problem type nobody registered would otherwise abort a cycle
        # somewhere quite different from where the mistake is.
        try:
            domain_id = registry.resolve(problem_type).domain_id
        except UnsupportedProblemType:
            domain_id = "unregistered"
        return CaseOutcome(
            problem_type=problem_type,
            domain_id=domain_id,
            accepted=False,
            verifier_status="not_reached",
            message=f"{type(error).__name__}: {error}",
            candidate={},
            refused_before_solving=True,
        )
    return CaseOutcome(
        problem_type=run.problem_type,
        domain_id=run.domain_id,
        accepted=run.accepted,
        verifier_status=run.verifier_status,
        message=run.message,
        candidate=run.candidate,
        refused_before_solving=False,
    )


def assertion_agrees(asserted: dict[str, Any], candidate: dict[str, Any]) -> tuple[bool, str]:
    """Does the kernel's answer reproduce what the passage claimed?

    A subset comparison, one level into `structured`, because the passage asserts a
    conclusion and the kernel returns a conclusion plus its whole derivation. Comparing the
    whole candidate would fail on the steps; comparing nothing would be the bug below.
    """
    for key, expected in asserted.items():
        actual = candidate.get(key)
        if isinstance(expected, dict):
            for inner, value in expected.items():
                if not isinstance(actual, dict) or actual.get(inner) != value:
                    return False, (
                        f"the source asserts {key}.{inner}={value!r}; the kernel computed "
                        f"{None if not isinstance(actual, dict) else actual.get(inner)!r}"
                    )
        elif actual != expected:
            return False, (f"the source asserts {key}={expected!r}; the kernel computed {actual!r}")
    return True, ""


async def stage_cross_check(
    runner: CycleRunner, composition: Composition, state: CycleState
) -> None:
    """Two legs, and **W0-F4 is why there are two.**

    The obvious cross-check is to run the derived case through `run_descriptor_case` — the
    released `domains.solve` tool and `domains.checker` verifier, the same path §1.4's
    holdout evaluation takes — and quarantine whatever the checker refuses. Running the
    slice showed that check passing the plant. It is not a defect in the checker: the
    checker judges whether the *derivation* is sound, and the plant's derivation is
    impeccable. Asked whether `2 H2 + O2 -> 3 H2O` balances, the kernel correctly answers
    "no", the checker correctly accepts that answer, and the passage's assertion that it
    *does* balance is never examined by anyone.

    So the second leg compares the conclusion the **source asserts** against the conclusion
    the kernel **computes**. A checker that accepts a case has verified an arithmetic; only
    this comparison verifies the literature. Both legs must pass, and the record keeps them
    apart so a future failure says which one refused.
    """
    runner.enter(CampaignStage.CROSS_CHECK)
    for segment in all_segments():
        run = await attempt_case(
            segment.problem_type, segment.formal_inputs, store=composition.events
        )
        agrees, disagreement = (
            assertion_agrees(segment.asserted, run.candidate) if run.accepted else (False, "")
        )
        state.cross_checks[segment.segment_id] = {
            "problem_type": run.problem_type,
            "domain_id": run.domain_id,
            "refused_before_solving": run.refused_before_solving,
            "verifier_status": run.verifier_status,
            "derivation_accepted": run.accepted,
            "assertion_agrees_with_kernel": agrees,
            "accepted": bool(run.accepted and agrees),
            "message": run.message or disagreement,
            "asserted": segment.asserted,
            "expected_accepted": segment.expected_accepted,
            "as_expected": bool(run.accepted and agrees) == segment.expected_accepted,
        }
    runner.leave(CampaignStage.CROSS_CHECK)


# --- stage 5 -----------------------------------------------------------------


async def stage_quarantine(
    runner: CycleRunner, composition: Composition, state: CycleState
) -> None:
    """Whatever failed the cross-check is quarantined with a named released reason.

    §2.2b: quarantined means the item reaches a quarantine state with a named reason through
    the released vocabulary and never reaches an active state. The quarantine set is
    computed from the cross-check *outcomes*, never from the fixture's own
    `expected_accepted` — a quarantine pass that consulted the answer key would quarantine
    the plant on a technicality of authorship rather than on evidence.

    Because W0-F3 moved the semantic write to compile, quarantining is a decision recorded
    here and enforced by the two stages that follow: a quarantined segment is never
    committed as a claim and never compiled as a memory record, so "never reaches an active
    state" holds at the store rather than only in the ledger.
    """
    runner.enter(CampaignStage.QUARANTINE)
    del composition
    for segment in all_segments():
        if state.cross_checks[segment.segment_id]["accepted"]:
            continue
        reason = segment.quarantine_reason or CorpusQuarantineReason.CONFLICTING_PROVENANCE
        state.quarantined[segment.segment_id] = reason.value
    runner.leave(CampaignStage.QUARANTINE)


# --- stage 6 -----------------------------------------------------------------


async def stage_compile(runner: CycleRunner, composition: Composition, state: CycleState) -> None:
    """Candidates only, and only for what survived quarantine.

    The compiled memory record's provenance bundle cites the corpus item's content-addressed
    artifact — the same artifact the claim's grounding span named — so one identity carries
    the citation across the corpus → semantic → memory seam instead of three dialects each
    holding half of it.
    """
    runner.enter(CampaignStage.COMPILE)
    extraction = SemanticExtractionService(
        composition.semantic, composition.predicates, events=composition.semantic_events
    )
    for segment in all_segments():
        if segment.segment_id in state.quarantined:
            continue
        item = state.corpus_items[segment.segment_id]
        # §9.1 stage 6 creates the semantic revision, and it is the first moment the content
        # has earned one: it has been registered, extracted, structured, recomputed by the
        # domain's own kernel and cleared by quarantine.
        committed = await extraction.commit(
            state.normalized[segment.segment_id],
            scope=MemoryScope(scope_type=MemoryScopeType.DOMAIN, scope_id=segment.domain_id),
            sensitivity=MemorySensitivity.INTERNAL,
            actor=ACTOR,
            recorded_at=SLICE_TIME,
        )
        state.claims[segment.segment_id] = committed.claims[0].claim_id
        memory_id = _identifier(f"memory:{segment.segment_id}")
        content = ObservationMemoryContent(
            observation=segment.prose,
            evidence_summary=(
                f"{segment.problem_type} recomputed by the registered checker; "
                f"claim {state.claims[segment.segment_id]}"
            ),
        )
        request = MemoryWriteRequest(
            request_id=_identifier(f"memory-request:{segment.segment_id}"),
            idempotency_key=_sha256(f"s22c:{segment.segment_id}".encode()),
            memory_id=memory_id,
            memory_type=MemoryType.OBSERVATION,
            scope=MemoryScope(scope_type=MemoryScopeType.DOMAIN, scope_id=segment.domain_id),
            title=f"{segment.domain_id}: {segment.segment_id}",
            content=content,
            status=MemoryStatus.CANDIDATE,
            confidence=0.9,
            salience=0.5,
            sensitivity=MemorySensitivity.INTERNAL,
            provenance=MemoryProvenanceBundle(
                sources=(
                    MemorySourceRef(
                        identity=MemorySourceIdentity(
                            source_type=MemorySourceType.ARTIFACT,
                            source_id=UUID(item["normalized_artifact_id"]),
                            content_hash=item["normalized_artifact_hash"],
                        ),
                        source_hash=item["normalized_artifact_hash"],
                        relationship="derived_from",
                    ),
                )
            ),
            actor=MEMORY_ACTOR,
        )
        _decision, created = await composition.memory.create(request)
        if created is None:
            raise RuntimeError(f"compiling {segment.segment_id} produced no memory record")
        state.compiled[segment.segment_id] = {
            "memory_id": str(memory_id),
            "revision": created[1].revision,
            "status": created[0].status.value,
            "cited_artifact_id": item["normalized_artifact_id"],
            "cited_artifact_hash": item["normalized_artifact_hash"],
        }
    runner.leave(CampaignStage.COMPILE)


# --- stage 7 -----------------------------------------------------------------


async def replay_all_domains(store: MemoryEventStore | None = None) -> dict[str, Any]:
    """Execute every retained domain's retained evaluation cases. §2.2a.

    The enumeration is `registry.domain_ids()` — released and pilot alike — and the rate is
    per domain, so forgetting is a measured delta rather than an alert that fired or did
    not. D7 W3-F1 is why this *executes*: a hash comparison replays nothing.

    A domain the registry names but for which no retained case exists is reported with
    `cases: 0` rather than silently omitted, because "all retained domains" is an
    enumeration the record has to be able to be wrong about (22A W4-F1).
    """
    cases: dict[str, list[Segment]] = {}
    for segment in all_segments():
        if segment.expected_accepted:
            cases.setdefault(segment.domain_id, []).append(segment)

    per_domain: dict[str, Any] = {}
    for domain_id in registry.domain_ids():
        retained = cases.get(domain_id, [])
        passed = 0
        for segment in retained:
            run = await attempt_case(segment.problem_type, segment.formal_inputs, store=store)
            passed += int(run.accepted)
        per_domain[domain_id] = {
            "cases": len(retained),
            "passed": passed,
            "rate": None if not retained else round(passed / len(retained), 6),
        }
    with_cases = [item for item in per_domain.values() if item["cases"]]
    return {
        "domains_enumerated": len(per_domain),
        "enumeration_source": "registry.domain_ids()",
        "domains_with_retained_cases": len(with_cases),
        "cases_executed": sum(item["cases"] for item in per_domain.values()),
        "cases_passed": sum(item["passed"] for item in per_domain.values()),
        "per_domain": per_domain,
        "all_retained_cases_passed": all(
            item["passed"] == item["cases"] for item in per_domain.values()
        ),
    }


def source_leakage_check(state: CycleState) -> dict[str, Any]:
    """No holdout case hash may appear in the curriculum. §2.2c, 22B W1-F6.

    Cheap and structural on purpose: the holdout lives in another database, and this is the
    check that the *definition* did not overlap even before the stores are consulted.
    """
    curriculum = set(state.manifest.curriculum.segment_hashes)
    overlaps = {
        holdout.holdout_id: sorted(curriculum.intersection(holdout.case_hashes))
        for holdout in state.manifest.holdouts
    }
    return {
        "curriculum_segments": len(curriculum),
        "holdouts": len(state.manifest.holdouts),
        "overlaps": {key: value for key, value in overlaps.items() if value},
        "leakage_detected": any(overlaps.values()),
        "holdout_store_env": sorted({holdout.store_url_env for holdout in state.manifest.holdouts}),
    }


async def stage_evaluate(runner: CycleRunner, composition: Composition, state: CycleState) -> None:
    """Replay every retained domain, then check for leakage. Before anything is promoted."""
    runner.enter(CampaignStage.EVALUATE)
    state.replay = await replay_all_domains(composition.events)
    state.replay["source_leakage"] = source_leakage_check(state)
    runner.leave(CampaignStage.EVALUATE)


# --- stage 8 -----------------------------------------------------------------


async def stage_promote(runner: CycleRunner, composition: Composition, state: CycleState) -> None:
    """Only what survived every earlier stage reaches the released promotion gate.

    The gate runs the required verifier capabilities before any claim activates; this driver
    adds no promotion rule of its own. A quarantined segment is not offered to it at all,
    which is what §2.2b's "never reaches an active state" means in sequence.
    """
    runner.enter(CampaignStage.PROMOTE)
    gate_ids = iter(_identifier(f"promotion-gate:{index}") for index in range(1000))
    verifier_registry = build_builtin_registry()
    gate = SemanticPromotionGate(
        composition.semantic,
        VerificationService(verifier_registry, VerifierEventService(composition.events)),
        verifier_registry,
        composition.semantic_events,
        clock=lambda: SLICE_TIME,
        id_factory=lambda: next(gate_ids),
    )
    for segment in all_segments():
        if segment.segment_id in state.quarantined:
            continue
        claim_id = state.claims[segment.segment_id]
        proposed = await composition.semantic_repository.get_claim_revision(claim_id, 1)
        first_evidence = await composition.semantic_repository.list_evidence(claim_id, revision=1)
        if proposed is None or not first_evidence:
            raise RuntimeError(f"claim {claim_id} has no proposed revision to promote")

        # The released lifecycle promotes a *successor*: revision 1 is the candidate the
        # extraction proposed, revision 2 is what the gate decides on. `decide` refuses a
        # revision with no predecessor, which is the rule that stops a campaign from
        # extracting straight into an active view.
        evidence = tuple(
            link.model_copy(
                update={
                    "evidence_id": _identifier(f"evidence:{claim_id}:2"),
                    "claim": ClaimRevisionReference(claim_id=claim_id, revision=2),
                    "created_by": ACTOR,
                }
            )
            for link in first_evidence
        )
        evidence_hash = semantic_hash([link.model_dump(mode="json") for link in evidence])
        confidence = aggregate_confidence(
            extraction=1, source=1, grounding=1, evidence=1, verification=1, consistency=1
        )
        reason = "registered semantic verifier bundle passed on acquired content"
        promoted = ClaimRevision(
            claim_id=claim_id,
            revision=2,
            previous_revision=1,
            object=proposed.object,
            statement=proposed.statement,
            belief_status=BeliefStatus.SUPPORTED,
            confidence=confidence,
            valid_interval=proposed.valid_interval,
            reason=reason,
            recorded_at=SLICE_TIME,
            created_by=ACTOR,
            evidence_snapshot_hash=evidence_hash,
            content_hash=claim_revision_hash(
                claim_id=claim_id,
                revision=2,
                object_value=proposed.object,
                statement=proposed.statement,
                belief_status=BeliefStatus.SUPPORTED,
                confidence=confidence,
                valid_interval=proposed.valid_interval,
                reason=reason,
                evidence_snapshot_hash=evidence_hash,
            ),
        )
        decision = await gate.decide(
            promoted, evidence, task_run_id=_identifier("task-run"), actor=ACTOR
        )
        if decision.outcome is not ClaimPromotionOutcome.SUPPORTED:
            raise RuntimeError(
                f"{segment.segment_id}: promotion rejected {list(decision.reason_codes)}"
            )
        await composition.semantic.transition_claim(
            promoted.model_copy(update={"promotion_decision_id": decision.decision_id}),
            expected_revision=1,
            decision=decision,
            evidence=evidence,
        )
        state.promoted.append(segment.segment_id)
        state.compiled[segment.segment_id]["promotion_decision"] = {
            "decision_id": str(decision.decision_id),
            "outcome": decision.outcome.value,
            "reason_codes": list(decision.reason_codes),
            "claim_id": str(claim_id),
            "activated_revision": 2,
        }
    runner.leave(CampaignStage.PROMOTE)


# --- stage 9 -----------------------------------------------------------------


async def stage_observe(runner: CycleRunner, composition: Composition, state: CycleState) -> None:
    """Outcomes return to the evidence store. The cycle's own event types are the record."""
    runner.enter(CampaignStage.OBSERVE)
    state.events = composition.events.event_types()
    runner.leave(CampaignStage.OBSERVE)


# ---------------------------------------------------------------------------
# The citation walker
# ---------------------------------------------------------------------------


async def walk_citations(composition: Composition, state: CycleState) -> dict[str, Any]:
    """From every promoted artifact back to the registered source bytes, loading them. §2.2d.

    Four hops, each one *resolved* rather than asserted non-empty:

    1. the memory record's provenance bundle names an artifact and a hash;
    2. the artifact store yields those bytes and they hash to that value;
    3. the corpus item registered under the same canonical hash names its source manifest;
    4. the source manifest's own file hashes contain the segment's registered bytes.

    A check that sampled would have verified the sample, so the walk covers every promoted
    artifact and the count is asserted against the enumeration (22A W4-F1).
    """
    walked: dict[str, Any] = {}
    for segment_id in state.promoted:
        compiled = state.compiled[segment_id]
        item = state.corpus_items[segment_id]
        record = await composition.memory_repository.get_current(UUID(compiled["memory_id"]))
        if record is None:
            raise RuntimeError(f"promoted memory {compiled['memory_id']} is not loadable")
        # Provenance is not a field on the revision: the released read path is
        # `list_sources(memory_id, revision)`. The walk reads it back out of the repository
        # rather than out of the write request it was handed, because a citation nobody can
        # re-read is not a citation (D7 W3-F1).
        sources = await composition.memory_repository.list_sources(
            record[0].memory_id, record[1].revision
        )
        if not sources:
            raise RuntimeError(f"{segment_id}: promoted memory has no readable provenance")
        hops: list[dict[str, Any]] = []
        for source in sources:
            artifact_id = source.identity.source_id
            if artifact_id is None:
                raise RuntimeError(f"{segment_id}: provenance source names no artifact")
            data = await composition.artifacts.get_bytes(artifact_id)
            loaded_hash = _sha256(data)
            hops.append(
                {
                    "hop": "memory_provenance -> artifact_bytes",
                    "artifact_id": str(artifact_id),
                    "declared_hash": source.source_hash,
                    "loaded_bytes": len(data),
                    "loaded_hash": loaded_hash,
                    "resolves": loaded_hash == source.source_hash,
                }
            )
        hops.append(
            {
                "hop": "artifact -> corpus_item",
                "corpus_item_id": item["corpus_item_id"],
                "canonical_content_hash": item["canonical_content_hash"],
                "resolves": item["normalized_artifact_hash"] == item["canonical_content_hash"],
            }
        )
        hops.append(
            {
                "hop": "corpus_item -> source_manifest",
                "source_manifest_id": item["source_manifest_id"],
                "resolves": item["source_manifest_id"]
                == state.corpus_items["_source_manifest"]["source_manifest_id"],
            }
        )
        segment = next(item for item in all_segments() if item.segment_id == segment_id)
        hops.append(
            {
                "hop": "source_manifest -> registered_source_bytes",
                "segment_content_hash": segment.content_hash,
                "resolves": segment.content_hash in item["source_file_hashes"],
            }
        )
        walked[segment_id] = {
            "hops": hops,
            "chain_resolves": all(hop["resolves"] for hop in hops),
        }
    return {
        "promoted_artifacts": len(state.promoted),
        "artifacts_walked": len(walked),
        "walk_covers_every_promoted_artifact": len(walked) == len(state.promoted),
        "all_chains_resolve": bool(walked)
        and all(entry["chain_resolves"] for entry in walked.values()),
        "sampled": False,
        "per_artifact": walked,
    }


# ---------------------------------------------------------------------------
# The slice
# ---------------------------------------------------------------------------


async def run_cycle(manifest: CampaignManifestV1) -> tuple[CycleState, Composition]:
    """One complete nine-stage pass. The only way to run a cycle."""
    register_pilots()
    state = CycleState(manifest=manifest)
    composition = build_composition()
    runner = CycleRunner(state)
    for stage in (
        stage_register_source,
        stage_extract,
        stage_normalize,
        stage_cross_check,
        stage_quarantine,
        stage_compile,
        stage_evaluate,
        stage_promote,
        stage_observe,
    ):
        await stage(runner, composition, state)
    if not runner.complete:
        raise StageOutOfOrder(f"cycle completed only {state.stages_completed}")
    return state, composition


async def slice_record() -> dict[str, Any]:
    manifest = fixture_manifest()
    state, composition = await run_cycle(manifest)
    citations = await walk_citations(composition, state)

    plant = state.cross_checks[PLANT.segment_id]
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W0",
        "items": ["S22C-003"],
        "recorded_at": SLICE_TIME.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decides_an_exit_criterion": False,
        "why_no_exit": (
            "every 22C exit is a claim about the real rights-cleared source across three "
            "cycles. This runs one cycle against a fixture chapter authored in-repository, "
            "so publishing the pre-registration after it is not publishing it after the "
            "numbers"
        ),
        "manifest": {
            "campaign_id": manifest.campaign_id,
            "revision": manifest.revision,
            "content_hash": manifest.content_hash,
            "rights_content_hash": manifest.rights.content_hash,
            "source_content_hash": fixture_source_hash(),
            "domain_ids": list(manifest.domain_ids),
            "providers": list(manifest.providers),
        },
        "stages": {
            "enumerated": [stage.value for stage in CAMPAIGN_STAGES],
            "completed": state.stages_completed,
            "count": len(state.stages_completed),
            "all_nine_in_order": state.stages_completed
            == [stage.value for stage in CAMPAIGN_STAGES],
        },
        "register_source": state.corpus_items["_source_manifest"],
        "extract": {
            "proposals": len(state.proposals),
            "provider_calls": 0,
            "host_revalidated": sum(
                1 for item in state.proposals.values() if item["host_revalidated"]
            ),
            "grounding_resolves_to_loaded_bytes": sum(
                1 for item in state.proposals.values() if item["grounding_resolves_to_loaded_bytes"]
            ),
            "what_revalidation_does_not_check": next(iter(state.proposals.values()))[
                "what_revalidation_does_not_check"
            ],
            "replayable_without_the_network": all(
                not item["provider_call"] for item in state.proposals.values()
            ),
        },
        "normalize": {"claims": len(state.claims)},
        "cross_check": {
            "cases": len(state.cross_checks),
            "accepted": sum(1 for item in state.cross_checks.values() if item["accepted"]),
            "every_outcome_as_expected": all(
                item["as_expected"] for item in state.cross_checks.values()
            ),
            "per_segment": state.cross_checks,
        },
        "quarantine": {
            "quarantined": state.quarantined,
            "count": len(state.quarantined),
            "the_plant": {
                "segment_id": PLANT.segment_id,
                "content_hash": PLANT.content_hash,
                "entered_through_the_genuine_intake_path": True,
                # Named precisely, because W0-F4 is exactly this distinction: the released
                # checker *passed* the plant's derivation. What refused it is the second
                # cross-check leg, comparing the source's assertion to the kernel's answer.
                "refused_by": "cross_check.assertion_agrees_with_kernel",
                "derivation_accepted_by_domains_checker": plant["derivation_accepted"],
                "verifier_status": plant["verifier_status"],
                "message": plant["message"],
                "quarantined": PLANT.segment_id in state.quarantined,
                "reason": state.quarantined.get(PLANT.segment_id),
                "reached_an_active_state": PLANT.segment_id in state.promoted,
                "compiled": PLANT.segment_id in state.compiled,
            },
        },
        "compile": {"records": len(state.compiled)},
        "evaluate": state.replay,
        "promote": {"promoted": sorted(state.promoted), "count": len(state.promoted)},
        "observe": {"event_types": sorted(state.events), "count": len(state.events)},
        "citations": citations,
        "limitations": [
            "one cycle, not three: the cycle-count exit is a W2/W3 claim",
            "the fixture chapter is authored in this repository, so its rights clearance "
            "decides nothing about the real source W1 registers",
            "in-memory repositories, so this run says nothing about PostgreSQL behaviour "
            "under the campaign store",
            "four of the six enumerated domains retain no evaluation cases of their own, so "
            "their replay executes nothing — reported as cases: 0 rather than omitted, and "
            "carried as W0-A1 for the wave that reads the replay exit",
        ],
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def contracts_hash() -> str:
    """The frozen recipe, hashed from the module rather than retyped (22B S22B-010).

    A `--check` that recomputed a number written into the record would only prove the record
    was internally consistent. This hashes the *inputs* — the stage enumeration, the segment
    contents, the plant, and the manifest — so a drifted fixture fails the check.
    """
    return _sha256(
        _canonical(
            {
                "stages": [stage.value for stage in CAMPAIGN_STAGES],
                "segments": [
                    {
                        "segment_id": segment.segment_id,
                        "domain_id": segment.domain_id,
                        "problem_type": segment.problem_type,
                        "content_hash": segment.content_hash,
                        "formal_inputs": segment.formal_inputs,
                        "expected_accepted": segment.expected_accepted,
                    }
                    for segment in all_segments()
                ],
                "plant_content_hash": PLANT.content_hash,
                "source_content_hash": fixture_source_hash(),
                "manifest_content_hash": fixture_manifest().content_hash,
            }
        )
    )


async def _check(path: Path) -> int:
    stored = json.loads(path.read_text(encoding="utf-8"))
    rebuilt = await slice_record()
    same = stored == rebuilt
    print(
        json.dumps(
            {
                "path": path.name,
                "reproduced": same,
                "stored_integrity": stored.get("integrity_content_hash"),
                "rebuilt_integrity": rebuilt["integrity_content_hash"],
                "contracts_hash": contracts_hash(),
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0 if same else 1


async def _write(path: Path) -> int:
    record = await slice_record()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": path.name,
                "stages_completed": record["stages"]["count"],
                "all_nine_in_order": record["stages"]["all_nine_in_order"],
                "cross_check_as_expected": record["cross_check"]["every_outcome_as_expected"],
                "plant_quarantined": record["quarantine"]["the_plant"]["quarantined"],
                "plant_reached_active_state": record["quarantine"]["the_plant"][
                    "reached_an_active_state"
                ],
                "domains_enumerated": record["evaluate"]["domains_enumerated"],
                "cases_executed": record["evaluate"]["cases_executed"],
                "promoted": record["promote"]["count"],
                "citation_chains_resolve": record["citations"]["all_chains_resolve"],
                "contracts_hash": contracts_hash(),
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", action="store_true", help="run the nine stages and seal")
    parser.add_argument("--check", action="store_true", help="rebuild and compare")
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-22c-w0-slice.json")
    arguments = parser.parse_args()
    if arguments.check:
        return asyncio.run(_check(arguments.output))
    if arguments.slice:
        return asyncio.run(_write(arguments.output))
    parser.error("choose --slice or --check")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
