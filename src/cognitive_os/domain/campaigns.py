"""Campaign manifests — Sprint 22C's primitive, frozen before its first cycle.

Sprint 22A made a domain data. Sprint 22B measured the store domains live in. Sprint 22C
runs *campaigns*: repeated governed passes that turn a rights-cleared source into knowledge
the platform can be held to. A campaign is a long-running, partly nondeterministic process
with a provider in the middle of it, and the only way such a thing produces evidence rather
than anecdote is if everything it may do is written down before it does any of it. That
sealed object is the manifest.

Three rules, each paid for by a predecessor:

**Rights are a gate, not a field.** `CampaignSourceRights` cannot be constructed without a
clearance decision, a clearing authority, and the source's own content hash; and a manifest
cannot be constructed unless its rights record clears the uses the campaign actually makes.
The allocation's §3.5 requires rights evidence to be mandatory, and a mandatory field that
may be left empty is not mandatory. A campaign whose source rights have not cleared cannot
be expressed in this contract at all — which is what "W0 blocks on it" means in code rather
than in prose.

**The holdout is separated by construction, not by promise.** 22B's W1-F6 cost a wave: a
driver mutated the corpus an exit criterion read. Here the curriculum and the holdout are
two disjoint sets of source hashes, the disjointness is a validator rather than a review
note, and the holdout carries its own store URL key so no code path holding the campaign's
connection can reach it.

**A cycle is nine stages or it is not a cycle.** `CampaignStage` is the development plan's
§9.1 pipeline in order, and it is an enumeration rather than a list of strings so that
"three completed cycles" is a countable claim (22A W4-F1: count what a coverage word
covers). A pass that skipped a stage is a pass that skipped a stage; the runner refuses it,
and the record says which stage was missing.

What this module deliberately does not do: it runs nothing, calls no provider, and touches
no store. It is the contract the 22C drivers are held to, and a groundwork module that also
executed would be the sprint pre-empting its own gate.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.corpus import CorpusUsageRight
from cognitive_os.domain.experience import HashedExperienceContract

SCHEMA_VERSION = 1


#: The nine stages of the Knowledge Acquisition Factory, development plan §9.1, in the order
#: the plan states them. The order is load-bearing: quarantine precedes compile so an
#: unresolved contradiction cannot become a candidate, and evaluate precedes promote so
#: nothing activates before the holdout and leakage checks have run.
class CampaignStage(StrEnum):
    REGISTER_SOURCE = "register_source"
    EXTRACT = "extract"
    NORMALIZE = "normalize"
    CROSS_CHECK = "cross_check"
    QUARANTINE = "quarantine"
    COMPILE = "compile"
    EVALUATE = "evaluate"
    PROMOTE = "promote"
    OBSERVE = "observe"


#: The stage order as a tuple, so a runner compares against one authority rather than
#: against the accident of enum declaration order at its call site.
CAMPAIGN_STAGES: tuple[CampaignStage, ...] = tuple(CampaignStage)


class RightsClearanceStatus(StrEnum):
    """Whether the source may be processed at all.

    There is no `PENDING_BUT_PROCEED`. A review that has not concluded is `NOT_CLEARED`, and
    a manifest cannot be built on it.
    """

    CLEARED = "cleared"
    NOT_CLEARED = "not_cleared"


class CampaignStopReason(StrEnum):
    BUDGET_EXHAUSTED = "budget_exhausted"
    STAGE_REFUSED = "stage_refused"
    QUARANTINE_RATE_EXCEEDED = "quarantine_rate_exceeded"
    REPLAY_REGRESSION = "replay_regression"
    SOURCE_LEAKAGE_DETECTED = "source_leakage_detected"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CYCLE_TARGET_REACHED = "cycle_target_reached"


class CampaignSourceRights(HashedExperienceContract):
    """The gate in front of everything. §1.3, and the allocation's §3.5.

    Every field here is something a rights review concludes, and none of them has a default.
    `permitted_uses` is a closed vocabulary — the released `CorpusUsageRight` — so the
    manifest's declared uses can be checked against it mechanically instead of by reading a
    licence name and hoping.
    """

    status: RightsClearanceStatus
    source_content_hash: Sha256Hex
    edition: NonEmptyStr
    author: NonEmptyStr
    location: NonEmptyStr
    license_identifier: NonEmptyStr
    permitted_uses: tuple[CorpusUsageRight, ...] = Field(min_length=1)
    cleared_by: NonEmptyStr
    cleared_at: UtcDatetime
    #: The hash of the evidence the clearance rests on — the licence text, the acquisition
    #: record, whatever the reviewer read. A clearance with no readable basis is an opinion.
    evidence_hash: Sha256Hex
    notes: NonEmptyStr | None = None

    @model_validator(mode="after")
    def a_clearance_names_its_permitted_uses(self) -> CampaignSourceRights:
        if self.status is RightsClearanceStatus.NOT_CLEARED:
            raise ValueError(
                "CampaignSourceRights records a concluded clearance. A review that has not "
                "concluded is the absence of this record, not an instance of it carrying "
                "status=not_cleared — see Sprint 22C §1.3"
            )
        if len(set(self.permitted_uses)) != len(self.permitted_uses):
            raise ValueError("permitted uses must be unique")
        return self


class CampaignBudget(HashedExperienceContract):
    """What the campaign may spend before it stops. Priced against 22B's sealed numbers."""

    maximum_cycles: int = Field(ge=1, le=100)
    maximum_provider_calls_per_cycle: int = Field(ge=0, le=10_000)
    maximum_spend_usd: float = Field(ge=0, allow_inf_nan=False)
    maximum_items_per_cycle: int = Field(ge=1, le=1_000_000)


class CampaignCurriculum(HashedExperienceContract):
    """The source segments a campaign is allowed to learn from, per cycle.

    Segments are named by content hash rather than by offset, so a curriculum cannot drift
    when the source is re-registered and a cycle cannot quietly widen its own diet.
    """

    segment_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    segments_per_cycle: int = Field(ge=1, le=1_000)
    ordering: NonEmptyStr = "declared"


class CampaignHoldout(HashedExperienceContract):
    """The frozen evaluation set, and the store it lives in. §2.2c.

    `measured_values` is zero at freeze and is what a pre-registration checker reads: a
    holdout definition published with a number already in it was not frozen before the
    measurement.
    """

    holdout_id: NonEmptyStr
    #: The evaluation cases, by hash. Never inlined here: the cases live in the holdout store.
    case_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    verifier_id: NonEmptyStr
    seeds: tuple[int, ...] = Field(min_length=1)
    success_definition: NonEmptyStr
    #: The environment variable naming the holdout's own database. Not a URL: a manifest is
    #: sealed into evidence and a credential does not belong in it.
    store_url_env: NonEmptyStr
    measured_values: int = Field(default=0, ge=0)


class CampaignManifestV1(HashedExperienceContract):
    """One campaign, sealed before its first cycle.

    Identity is (`campaign_id`, `revision`), and both are immutable for the same reason a
    descriptor's are: a changed campaign is a new revision with the old one intact, so the
    cycles under one manifest are cycles of one system. §1.4's warning — a persistence path
    that appears between cycle 1 and cycle 3 makes the cycles measurements of different
    systems — generalises to every field here.
    """

    schema_version: int = Field(default=SCHEMA_VERSION, ge=1, le=SCHEMA_VERSION)
    campaign_id: NonEmptyStr
    revision: int = Field(ge=1)
    rights: CampaignSourceRights
    #: The domains the campaign lands content in. Checked against `registry.domain_ids()` by
    #: the runner, not here: a contract that imported the registry would couple a sealed
    #: record to a process's registration state.
    domain_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    goals: tuple[NonEmptyStr, ...] = Field(min_length=1)
    budget: CampaignBudget
    #: Provider ids the campaign may call, or empty for a campaign that calls none. Empty is
    #: a real configuration: the fixture-scale slice replays sealed proposals.
    providers: tuple[NonEmptyStr, ...] = ()
    curriculum: CampaignCurriculum
    holdouts: tuple[CampaignHoldout, ...] = Field(min_length=1)
    stop_conditions: tuple[CampaignStopReason, ...] = Field(min_length=1)
    declared_uses: tuple[CorpusUsageRight, ...] = Field(min_length=1)
    sealed_at: UtcDatetime
    sealed_by: NonEmptyStr

    @model_validator(mode="after")
    def the_manifest_is_within_its_rights_and_its_holdout_is_disjoint(self) -> CampaignManifestV1:
        permitted = set(self.rights.permitted_uses)
        exceeded = sorted(use.value for use in self.declared_uses if use not in permitted)
        if exceeded:
            raise ValueError(
                f"campaign declares uses its rights clearance does not permit: {exceeded}"
            )
        curriculum = set(self.curriculum.segment_hashes)
        if len(curriculum) != len(self.curriculum.segment_hashes):
            raise ValueError("curriculum segments must be unique")
        for holdout in self.holdouts:
            overlap = sorted(curriculum.intersection(holdout.case_hashes))
            if overlap:
                raise ValueError(
                    f"holdout {holdout.holdout_id!r} shares {len(overlap)} case(s) with the "
                    "curriculum; the holdout is never used as curriculum (§2.2c)"
                )
        if len({holdout.holdout_id for holdout in self.holdouts}) != len(self.holdouts):
            raise ValueError("holdout ids must be unique")
        if len(set(self.domain_ids)) != len(self.domain_ids):
            raise ValueError("domain ids must be unique")
        return self


__all__ = [
    "CAMPAIGN_STAGES",
    "SCHEMA_VERSION",
    "CampaignBudget",
    "CampaignCurriculum",
    "CampaignHoldout",
    "CampaignManifestV1",
    "CampaignSourceRights",
    "CampaignStage",
    "CampaignStopReason",
    "RightsClearanceStatus",
]
