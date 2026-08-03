"""S21D2-022 (seal), -026, -027, -028: the five partition catalogues, sealed before any outcome.

This is the sprint's second one-way door. Counts may rise up to the moment of sealing and never
afterwards, so everything here is derived from the corpus and the pre-registration rather than
chosen at seal time: given the same corpus and the same seeds, `seal_corpus()` reproduces the
same hashes, which is what makes a later claim about membership checkable rather than trusted.

Three decisions in here are worth stating plainly, because none of them is forced by the types.

*Where the inherited groups go.* Five partitions need 125 groups and D2 authored 95, so the
thirty C3 groups have to be used. They all go to training, and nowhere else. Final A, final B
and canary must be new relative to D1, and calibration must not carry an inherited group either
(S21D2-024), so training is the only partition that can hold them — which is also the only
placement that keeps a task D1 has already published out of every number D2 will report.

*The inherited groups do not bring their recipes with them.* A C3 task's candidate identity is
`uuid5(namespace, f"{task_id}:{strategy}")`, so holding the task ID lets anyone recompute all
four IDs and read off which is which. Re-using C3 tasks under C3 identity would put the oracle
back into the training partition through the identifier rather than through a feature. So an
inherited task enters the catalogue under D2 identity: opaque positional candidate IDs and the
neutral recipe binding. Its four C3 candidates map onto the D2 authoring convention exactly,
because both corpora are two repairs and two partial fixes.

*The catalogue is control material.* A slot records the authored variant it carries, because
without it the runner cannot materialise the candidate; that is the same category as the hidden
verifier bundle, not a feature. `CorrectionFeatureContract` rejects by absence from its
allowlist, so none of these names can reach a fitted matrix. Nothing here is added to the
denylist: that would change the frozen feature contract's hash and spend the single pre-final
revision section 3.4 permits, to buy a guarantee the allowlist already gives.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID, uuid5

from pydantic import Field, model_validator

from cognitive_os.application.services.correction_ranking_observations import (
    SealedCampaignManifest,
    SealedCampaignMember,
)
from cognitive_os.coding.reality_candidates import opaque_candidate_id, shuffled_recipe_positions
from cognitive_os.coding.reality_task_specs import TASK_SPECS
from cognitive_os.coding.reality_task_specs_d2 import (
    D2_RECIPES,
    D2_TASK_SPECS,
    INHERITED_VARIANT_FIELDS,
    recipe_binding,
)
from cognitive_os.coding.reality_tasks import REALITY_TASK_NAMESPACE
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_protocol import (
    PARTITION_CORPUS_ROLE,
    PARTITION_PROVENANCE,
    CorrectionCampaignMode,
    CorrectionPartition,
)

#: The group floor per partition, as pre-registration revision 2 froze it. S21D2-014 raised the
#: final batches from 25 to 30 each; these may rise before sealing and never after.
PARTITION_GROUP_FLOOR: dict[CorrectionPartition, int] = {
    CorrectionPartition.TRAINING: 50,
    CorrectionPartition.CALIBRATION: 10,
    CorrectionPartition.FINAL_A: 30,
    CorrectionPartition.FINAL_B: 30,
    CorrectionPartition.CANARY: 5,
}

CANDIDATES_PER_GROUP = 4

#: One seed per partition, recorded separately so batch B is generated independently of batch A
#: rather than being a slice of the same draw. The seed reaches candidate identity through
#: `opaque_candidate_id`, so two partitions cannot collide on a slot even by accident.
PARTITION_SEED: dict[CorrectionPartition, int] = {
    CorrectionPartition.TRAINING: 21_022_101,
    CorrectionPartition.CALIBRATION: 21_022_202,
    CorrectionPartition.FINAL_A: 21_026_303,
    CorrectionPartition.FINAL_B: 21_027_404,
    CorrectionPartition.CANARY: 21_028_505,
}

#: The generator path each partition was produced by, recorded because S21D2-027 asks batch B
#: to name a separately recorded path and a path is only evidence if every partition names one.
PARTITION_GENERATOR_PATH: dict[CorrectionPartition, str] = {
    CorrectionPartition.TRAINING: "correction_catalogue.seal_corpus:training",
    CorrectionPartition.CALIBRATION: "correction_catalogue.seal_corpus:calibration",
    CorrectionPartition.FINAL_A: "correction_catalogue.seal_corpus:final_a",
    CorrectionPartition.FINAL_B: "correction_catalogue.seal_corpus:final_b_independent",
    CorrectionPartition.CANARY: "correction_catalogue.seal_corpus:canary",
}

#: The order the deal walks the partitions in. Contiguous slices of a family-interleaved
#: ordering keep every partition family-balanced without a per-family quota table.
_DEAL_ORDER: tuple[CorrectionPartition, ...] = (
    CorrectionPartition.TRAINING,
    CorrectionPartition.CALIBRATION,
    CorrectionPartition.FINAL_A,
    CorrectionPartition.FINAL_B,
    CorrectionPartition.CANARY,
)

#: Everything in both corpora is authored in this repository under its own licence. There is no
#: third-party source to clear, which is why the rights report is a statement rather than a scan.
SOURCE_LICENCE = "Apache-2.0"
SOURCE_ORIGIN = "first_party_authored_in_repository"


@dataclass(frozen=True, slots=True)
class CorpusEntry:
    """One task group as either corpus describes it, before any partition claims it."""

    template_id: str
    repository_group: str
    family: str
    #: The four candidate bodies in authoring order: two repairs, then two partial fixes.
    variants: tuple[str, ...]
    hidden_verifier_source: str
    inherited: bool
    #: Carried so the verifier replay can rebuild the module a slot points at. Without it the
    #: replay could only check that a hash is stable, which is not what "replay" means.
    module: str
    module_doc: str
    imports: str

    @property
    def repairs_contract(self) -> tuple[bool, ...]:
        return (True, True, False, False)

    def module_text(self, variant_index: int) -> str:
        header = f'"""{self.module_doc}"""\n'
        if self.imports:
            header += f"\n{self.imports}\n"
        return f"{header}\n\n{self.variants[variant_index].strip()}\n"


def corpus_entries() -> tuple[CorpusEntry, ...]:
    """Both corpora in one deterministic list: 95 authored for D2 and 30 inherited from C3."""
    authored = tuple(
        CorpusEntry(
            template_id=spec.template_id,
            repository_group=spec.repository_group,
            family=spec.family.value,
            variants=spec.variants,
            hidden_verifier_source=spec.hidden_test,
            inherited=False,
            module=spec.module,
            module_doc=spec.module_doc,
            imports=spec.imports,
        )
        for spec in D2_TASK_SPECS
    )
    # C3 orders its candidates incomplete-first; the D2 convention is repairs-first, and the
    # two corpora agree on the 2-of-4 balance, so the reordering is total and lossless.
    inherited = tuple(
        CorpusEntry(
            template_id=spec.template_id,
            repository_group=spec.repository_group,
            family=spec.family.value,
            variants=tuple(getattr(spec, field) for field in INHERITED_VARIANT_FIELDS),
            hidden_verifier_source=spec.hidden_test,
            inherited=True,
            module=spec.module,
            module_doc=spec.module_doc,
            imports=spec.imports,
        )
        for spec in TASK_SPECS
    )
    return authored + inherited


def task_id_for(template_id: str, *, seed: int) -> UUID:
    """The same derivation C3 uses, so one namespace covers both corpora."""
    return uuid5(REALITY_TASK_NAMESPACE, f"{template_id}:{seed}")


def _family_interleaved(entries: Sequence[CorpusEntry]) -> tuple[CorpusEntry, ...]:
    """Deal the entries round-robin across families, so any contiguous slice stays balanced."""
    by_family: dict[str, list[CorpusEntry]] = {}
    for entry in sorted(entries, key=lambda item: item.template_id):
        by_family.setdefault(entry.family, []).append(entry)
    ordered: list[CorpusEntry] = []
    for index in range(max(len(bucket) for bucket in by_family.values())):
        for family in sorted(by_family):
            bucket = by_family[family]
            if index < len(bucket):
                ordered.append(bucket[index])
    return tuple(ordered)


def assign_groups() -> dict[CorrectionPartition, tuple[CorpusEntry, ...]]:
    """Which group belongs to which partition, permanently.

    Inherited groups are placed first and only into training; the authored groups fill the rest
    in a family-interleaved order, so final A and final B are comparable without being drawn
    from the same shuffle.
    """
    entries = corpus_entries()
    inherited = tuple(entry for entry in entries if entry.inherited)
    authored = _family_interleaved([entry for entry in entries if not entry.inherited])

    assigned: dict[CorrectionPartition, tuple[CorpusEntry, ...]] = {}
    cursor = 0
    for partition in _DEAL_ORDER:
        wanted = PARTITION_GROUP_FLOOR[partition]
        taken = inherited if partition is CorrectionPartition.TRAINING else ()
        needed = wanted - len(taken)
        assigned[partition] = taken + authored[cursor : cursor + needed]
        cursor += needed
    if cursor != len(authored):
        raise ValueError(
            f"the deal consumed {cursor} authored groups of {len(authored)}; the floors and the "
            "corpus no longer agree"
        )
    return assigned


class CatalogueSlot(HashedExperienceContract):
    """One candidate slot: who it will be, never what it did.

    Control material. `variant_index` is what lets the runner materialise the candidate, and it
    is label-adjacent by construction, which is exactly why it lives here and not in a feature.
    """

    candidate_id: UUID
    position: int = Field(ge=0, lt=CANDIDATES_PER_GROUP)
    variant_index: int = Field(ge=0, lt=CANDIDATES_PER_GROUP)
    recipe: NonEmptyStr


class CatalogueGroup(HashedExperienceContract):
    """One task group and its four outcome-free slots."""

    template_id: NonEmptyStr
    repository_group: NonEmptyStr
    family: NonEmptyStr
    task_id: UUID
    task_seed: int
    inherited_from_d1: bool
    verifier_profile_hash: Sha256Hex
    source_licence: NonEmptyStr = SOURCE_LICENCE
    source_origin: NonEmptyStr = SOURCE_ORIGIN
    usage_rights_verified: bool = True
    slots: tuple[CatalogueSlot, ...] = Field(
        min_length=CANDIDATES_PER_GROUP, max_length=CANDIDATES_PER_GROUP
    )

    @model_validator(mode="after")
    def the_slots_are_a_permutation_of_the_positions(self) -> CatalogueGroup:
        positions = sorted(slot.position for slot in self.slots)
        if positions != list(range(CANDIDATES_PER_GROUP)):
            raise ValueError("the slots do not cover each position exactly once")
        variants = sorted(slot.variant_index for slot in self.slots)
        if variants != list(range(CANDIDATES_PER_GROUP)):
            raise ValueError("the slots do not cover each authored variant exactly once")
        if len({slot.candidate_id for slot in self.slots}) != CANDIDATES_PER_GROUP:
            raise ValueError("two slots share a candidate identity")
        return self


class SealedPartitionCatalogue(HashedExperienceContract):
    """One partition, sealed. No outcome may be added to it and none may be read from it."""

    partition: CorrectionPartition
    campaign_seed: int
    generator_path: NonEmptyStr
    provenance: NonEmptyStr
    corpus_role: NonEmptyStr
    mode: CorrectionCampaignMode
    groups: tuple[CatalogueGroup, ...] = Field(min_length=1)

    #: Stated rather than implied. A catalogue that could carry an outcome would be a result.
    outcomes_present: bool = False

    @model_validator(mode="after")
    def the_catalogue_matches_the_partition_it_names(self) -> SealedPartitionCatalogue:
        if self.outcomes_present:
            raise ValueError("a sealed catalogue is outcome-free by definition")
        if self.provenance != PARTITION_PROVENANCE[self.partition]:
            raise ValueError(f"{self.partition.value} does not resolve to {self.provenance}")
        if self.corpus_role != PARTITION_CORPUS_ROLE[self.partition]:
            raise ValueError(f"{self.partition.value} does not sit under {self.corpus_role}")
        stop_first = self.mode is CorrectionCampaignMode.STOP_ON_FIRST_ACCEPTED
        if stop_first is not (self.partition is CorrectionPartition.CANARY):
            raise ValueError(
                "stop_on_first_accepted belongs to the canary partition and to it only"
            )
        if len(self.groups) < PARTITION_GROUP_FLOOR[self.partition]:
            raise ValueError(
                f"{self.partition.value} holds {len(self.groups)} groups against a floor of "
                f"{PARTITION_GROUP_FLOOR[self.partition]}; a floor may rise, never fall"
            )
        if len({group.repository_group for group in self.groups}) != len(self.groups):
            raise ValueError("two groups in one partition share a repository group")
        inherited_outside_training = self.partition is not CorrectionPartition.TRAINING and any(
            group.inherited_from_d1 for group in self.groups
        )
        if inherited_outside_training:
            raise ValueError(
                f"{self.partition.value} carries an inherited group; prior public tasks are "
                "confined to training permanently"
            )
        return self

    @property
    def candidate_slots(self) -> int:
        return len(self.groups) * CANDIDATES_PER_GROUP


class OodSubmanifest(HashedExperienceContract):
    """A hash-bound out-of-distribution set, named before anything it describes was executed."""

    kind: NonEmptyStr
    covers_partitions: tuple[CorrectionPartition, ...] = Field(min_length=1)
    #: The catalogue hashes this submanifest was derived from, so it cannot drift from them.
    source_catalogue_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    repository_groups: tuple[NonEmptyStr, ...] = Field(min_length=1)
    perturbations: tuple[NonEmptyStr, ...] = Field(min_length=1)
    perturbation_seed: int
    minimum_future_decisions: int = Field(ge=0)
    minimum_groups: int = Field(ge=0)

    @model_validator(mode="after")
    def the_submanifest_covers_what_it_claims(self) -> OodSubmanifest:
        if len(set(self.repository_groups)) != len(self.repository_groups):
            raise ValueError("a group is named twice")
        if len(self.repository_groups) < self.minimum_groups:
            raise ValueError(
                f"{len(self.repository_groups)} groups against a declared floor of "
                f"{self.minimum_groups}"
            )
        if len(self.repository_groups) * CANDIDATES_PER_GROUP < self.minimum_future_decisions:
            raise ValueError(
                "the named groups cannot supply the declared number of future decisions"
            )
        return self


class CanaryRoutingPolicy(HashedExperienceContract):
    """What the canary is allowed to touch, and the identity that switches it off."""

    #: Must equal the sealed canary catalogue hash: `learned_config` refuses a routing set that
    #: names groups without the manifest hash they came from, and this is that hash.
    canary_manifest_hash: Sha256Hex
    routed_groups: tuple[NonEmptyStr, ...] = Field(min_length=1)
    component_id: NonEmptyStr = "learned.knn.correction_ranking"
    surface: NonEmptyStr = "experience.correction_ranking"
    mode: CorrectionCampaignMode = CorrectionCampaignMode.STOP_ON_FIRST_ACCEPTED

    #: The kill switch is a configuration identity, not a runtime call: emptying the routed set
    #: is what stops the canary, and it is refused unless the manifest hash is emptied with it.
    kill_switch_setting: NonEmptyStr = "learned.correction_ranking_groups"
    kill_switch_partner_setting: NonEmptyStr = "learned.correction_ranking_manifest_hash"
    kill_switch_default_is_off: bool = True

    #: Never used in fitting, calibration, the final comparison or the promotion decision.
    excluded_from_every_decision: bool = True

    @model_validator(mode="after")
    def the_canary_stays_a_canary(self) -> CanaryRoutingPolicy:
        if not self.kill_switch_default_is_off:
            raise ValueError("an approved component that routes by default is not a canary")
        if not self.excluded_from_every_decision:
            raise ValueError("a canary outcome that reaches a decision is not a canary")
        if self.mode is not CorrectionCampaignMode.STOP_ON_FIRST_ACCEPTED:
            raise ValueError("the canary exists to prove stop-first runtime behaviour")
        return self


class SealedCorpus(HashedExperienceContract):
    """The five catalogues, both OOD submanifests and the canary policy, bound to one hash."""

    pre_registration_revision: int = 2
    catalogue_hashes: tuple[tuple[CorrectionPartition, Sha256Hex], ...] = Field(
        min_length=5, max_length=5
    )
    calibration_ood_hash: Sha256Hex
    promotion_ood_hash: Sha256Hex
    canary_routing_hash: Sha256Hex
    distinct_groups: int = Field(ge=1)
    new_groups_relative_to_d1: int = Field(ge=0)
    candidate_slots: int = Field(ge=1)
    outcomes_present: bool = False

    @model_validator(mode="after")
    def the_seal_meets_the_contract_it_was_sized_for(self) -> SealedCorpus:
        if self.outcomes_present:
            raise ValueError("a sealed corpus is outcome-free by definition")
        partitions = [partition for partition, _ in self.catalogue_hashes]
        if len(set(partitions)) != len(CorrectionPartition):
            raise ValueError("every partition is sealed exactly once")
        if self.distinct_groups < 125:
            raise ValueError(f"{self.distinct_groups} distinct groups against a floor of 125")
        if self.new_groups_relative_to_d1 < 95:
            raise ValueError(f"{self.new_groups_relative_to_d1} new groups against a floor of 95")
        return self


def _slots_for(
    entry: CorpusEntry, task_id: UUID, *, campaign_seed: int
) -> tuple[CatalogueSlot, ...]:
    """Position the four authored variants under the neutral recipe binding.

    `recipe_binding` says which recipe carries which authored variant; `shuffled_recipe_positions`
    says which recipe sits at which execution position. Composing them gives the variant at each
    position without either mapping being the identity.
    """
    binding = recipe_binding(entry.template_id)
    variant_of_recipe = {recipe: index for index, recipe in enumerate(binding)}
    ordered = shuffled_recipe_positions(task_id, D2_RECIPES, campaign_seed=campaign_seed)
    return tuple(
        CatalogueSlot(
            candidate_id=opaque_candidate_id(
                task_id, campaign_seed=campaign_seed, position=position
            ),
            position=position,
            variant_index=variant_of_recipe[recipe],
            recipe=recipe.value,
        )
        for position, recipe in enumerate(ordered)
    )


def build_catalogue(
    partition: CorrectionPartition, entries: Sequence[CorpusEntry]
) -> SealedPartitionCatalogue:
    """Seal one partition from the groups assigned to it."""
    seed = PARTITION_SEED[partition]
    mode = (
        CorrectionCampaignMode.STOP_ON_FIRST_ACCEPTED
        if partition is CorrectionPartition.CANARY
        else CorrectionCampaignMode.LABEL_ALL
    )
    groups = tuple(
        CatalogueGroup(
            template_id=entry.template_id,
            repository_group=entry.repository_group,
            family=entry.family,
            task_id=(task_id := task_id_for(entry.template_id, seed=seed)),
            task_seed=seed,
            inherited_from_d1=entry.inherited,
            verifier_profile_hash=sha256(entry.hidden_verifier_source.encode()).hexdigest(),
            slots=_slots_for(entry, task_id, campaign_seed=seed),
        )
        for entry in entries
    )
    return SealedPartitionCatalogue(
        partition=partition,
        campaign_seed=seed,
        generator_path=PARTITION_GENERATOR_PATH[partition],
        provenance=PARTITION_PROVENANCE[partition],
        corpus_role=PARTITION_CORPUS_ROLE[partition],
        mode=mode,
        groups=groups,
    )


#: What the calibration precheck perturbs. Declared here and hash-bound before S21D2-024 runs
#: it, so the perturbation set cannot be chosen once the calibration numbers are visible.
CALIBRATION_PERTURBATIONS: tuple[str, ...] = (
    "rename_every_identifier_in_the_visible_module",
    "reorder_independent_statements_in_the_baseline",
    "rewrite_the_issue_text_without_changing_the_contract",
    "substitute_equivalent_literals_in_the_visible_tests",
)

#: What the promotion set perturbs. A separate tuple, because the promotion submanifest must
#: stay untouched while the calibration one is being resolved.
PROMOTION_PERTURBATIONS: tuple[str, ...] = (
    "rename_every_identifier_in_the_visible_module",
    "substitute_equivalent_literals_in_the_visible_tests",
    "reorder_the_published_test_functions",
)


def calibration_ood_submanifest(calibration: SealedPartitionCatalogue) -> OodSubmanifest:
    """The precheck set, bound to the calibration catalogue it was derived from."""
    return OodSubmanifest(
        kind="calibration_precheck",
        covers_partitions=(CorrectionPartition.CALIBRATION,),
        source_catalogue_hashes=(calibration.content_hash,),
        repository_groups=tuple(group.repository_group for group in calibration.groups),
        perturbations=CALIBRATION_PERTURBATIONS,
        perturbation_seed=21_024_606,
        minimum_future_decisions=0,
        minimum_groups=PARTITION_GROUP_FLOOR[CorrectionPartition.CALIBRATION],
    )


def promotion_ood_submanifest(
    final_a: SealedPartitionCatalogue, final_b: SealedPartitionCatalogue
) -> OodSubmanifest:
    """The promotion set over both final batches: 100+ decisions over 10+ groups."""
    return OodSubmanifest(
        kind="promotion",
        covers_partitions=(CorrectionPartition.FINAL_A, CorrectionPartition.FINAL_B),
        source_catalogue_hashes=(final_a.content_hash, final_b.content_hash),
        repository_groups=tuple(
            group.repository_group for catalogue in (final_a, final_b) for group in catalogue.groups
        ),
        perturbations=PROMOTION_PERTURBATIONS,
        perturbation_seed=21_022_707,
        minimum_future_decisions=100,
        minimum_groups=10,
    )


def canary_routing_policy(canary: SealedPartitionCatalogue) -> CanaryRoutingPolicy:
    return CanaryRoutingPolicy(
        canary_manifest_hash=canary.content_hash,
        routed_groups=tuple(group.repository_group for group in canary.groups),
    )


@dataclass(frozen=True, slots=True)
class SealedCorpusBundle:
    """Everything W3b produces, in one value, so a caller cannot hold half of it."""

    catalogues: dict[CorrectionPartition, SealedPartitionCatalogue]
    calibration_ood: OodSubmanifest
    promotion_ood: OodSubmanifest
    canary_routing: CanaryRoutingPolicy
    seal: SealedCorpus

    def groups_of(self, partition: CorrectionPartition) -> frozenset[str]:
        return frozenset(group.repository_group for group in self.catalogues[partition].groups)


def campaign_manifest_for(
    catalogue: SealedPartitionCatalogue,
    *,
    campaign_id: UUID,
    campaign_version: int,
    feature_sealed_at: datetime,
) -> SealedCampaignManifest:
    """Turn a sealed catalogue into the manifest the projector reads.

    Deferred out of W3b on purpose: `campaign_id`, `campaign_version` and `feature_sealed_at`
    do not exist until a campaign does, so writing this before one existed would have meant
    inventing three values to satisfy a shape. The projector takes only a manifest and an
    outcome, so this is the single point where a partition becomes a role.
    """
    members = {
        slot.candidate_id: SealedCampaignMember(
            candidate_id=slot.candidate_id,
            task_id=group.task_id,
            group=group.repository_group,
            partition=catalogue.partition,
            campaign_id=campaign_id,
            campaign_manifest_hash=catalogue.content_hash,
            campaign_version=campaign_version,
            verifier_profile_hash=group.verifier_profile_hash,
            feature_sealed_at=feature_sealed_at,
        )
        for group in catalogue.groups
        for slot in group.slots
    }
    return SealedCampaignManifest(
        campaign_id=campaign_id,
        manifest_hash=catalogue.content_hash,
        members=members,
    )


def seal_corpus() -> SealedCorpusBundle:
    """Seal all five partitions. Deterministic: same corpus and seeds, same hashes."""
    assigned = assign_groups()
    catalogues = {
        partition: build_catalogue(partition, entries) for partition, entries in assigned.items()
    }

    seen: dict[str, CorrectionPartition] = {}
    for partition, catalogue in catalogues.items():
        for group in catalogue.groups:
            previous = seen.setdefault(group.repository_group, partition)
            if previous is not partition:
                raise ValueError(
                    f"group {group.repository_group} is in both {previous.value} and "
                    f"{partition.value}; a group belongs to exactly one partition"
                )

    calibration_ood = calibration_ood_submanifest(catalogues[CorrectionPartition.CALIBRATION])
    promotion_ood = promotion_ood_submanifest(
        catalogues[CorrectionPartition.FINAL_A], catalogues[CorrectionPartition.FINAL_B]
    )
    routing = canary_routing_policy(catalogues[CorrectionPartition.CANARY])
    seal = SealedCorpus(
        catalogue_hashes=tuple(
            (partition, catalogues[partition].content_hash) for partition in _DEAL_ORDER
        ),
        calibration_ood_hash=calibration_ood.content_hash,
        promotion_ood_hash=promotion_ood.content_hash,
        canary_routing_hash=routing.content_hash,
        distinct_groups=len(seen),
        new_groups_relative_to_d1=sum(
            1
            for catalogue in catalogues.values()
            for group in catalogue.groups
            if not group.inherited_from_d1
        ),
        candidate_slots=sum(catalogue.candidate_slots for catalogue in catalogues.values()),
    )
    return SealedCorpusBundle(
        catalogues=catalogues,
        calibration_ood=calibration_ood,
        promotion_ood=promotion_ood,
        canary_routing=routing,
        seal=seal,
    )
