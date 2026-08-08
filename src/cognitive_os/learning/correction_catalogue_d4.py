"""S21D4-032: the D4 seal — what each role holds, named before anything it describes ran.

Three of the six correction roles are D2's, byte for byte, and D3 already carried them once.
S21D4-004 audited final A, final B and canary and recorded `reuse` for all three, so this module
calls `seal_d3_corpus()` and carries its catalogue objects across rather than re-deriving them.
Re-deriving would produce hashes that merely *ought* to equal the released ones; carrying the
objects means a drift is a failed comparison rather than a new number.

Two roles are D4's own. The calibration partition is the hundred fresh groups from
`reality_task_specs_d4`, which after the W1 erratum is the smallest corpus §2.3's floor of a
hundred independent calibration decisions can be met from. The fitting partition is eighty
predecessor packages to *re-execute* — ten D2 calibration groups, fifty D2 training groups and
twenty D3 calibration groups — because D4-W0-F1 found the D3 learned store holds no observations
and no datasets, so no predecessor row can be inherited and every one of the eighty has to be
run again to exist at all.

The two submanifests are where the erratum shows most plainly. The invariance sample names forty
transformed decisions over twenty groups and declares that they add **zero** independent
decisions: a transformation of a group does not produce a new fitted feature vector, so the
transformed set is a regression test and never an accuracy sample. The promotion set names a
hundred and twenty nominal decisions over sixty groups and sixty independent ones, for the same
reason and with both numbers reported side by side.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field, model_validator

from cognitive_os.coding.reality_retrieval_specs_d4 import D4_RETRIEVAL_SPECS
from cognitive_os.coding.reality_task_specs_d2 import module_source
from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS
from cognitive_os.domain.common import Sha256Hex
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning import transformations_d3
from cognitive_os.learning.calibration_ood import (
    OodCaseManifestV3,
    OodSubmanifestV3,
    transformation_case_id,
)
from cognitive_os.learning.correction_catalogue import (
    CorpusEntry,
    SealedPartitionCatalogue,
    assign_groups,
    build_catalogue,
)
from cognitive_os.learning.correction_catalogue_d3 import (
    SealedRetrievalPool,
    d3_calibration_entries,
    paired_manifest_hash,
    retrieval_pool_of,
    seal_d3_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition

#: D4's own seeds. Distinct from every D2 and D3 seed, so a D4 candidate identity cannot collide
#: with a predecessor's even for a group both sprints happen to name.
D4_FITTING_SEED = 21_040_202
D4_CALIBRATION_SEED = 21_040_101
INVARIANCE_TRANSFORM_SEED = 21_048_303
PROMOTION_TRANSFORM_SEED = 21_045_404

D4_FITTING_GENERATOR_PATH = "correction_catalogue_d4.seal_d4_corpus:fitting"
D4_CALIBRATION_GENERATOR_PATH = "correction_catalogue_d4.seal_d4_corpus:calibration"

INVARIANCE_STAGE = "calibration_invariance"
PROMOTION_STAGE = "promotion"

#: §S21D4-015 names these two and only these two, for both submanifests. They are a subset of the
#: released `transformations_d3.CASES`, so the generator and its hard-coded oracle are the ones
#: D3 froze rather than a D4 restatement of them.
D4_CASES = ("identifier_rename_a", "issue_rewrite_a")

FITTING_GROUPS = 80
CALIBRATION_GROUPS = 100
INVARIANCE_SAMPLE_GROUPS = 20
PROMOTION_GROUPS = 60

#: What each submanifest names, and what it is allowed to *count*. The gap between the two is the
#: W1 erratum: a transformation repeats a fitted feature vector, so it repeats a decision.
INVARIANCE_TRANSFORMED_DECISIONS = 40
INVARIANCE_INDEPENDENT_DECISIONS = 0
PROMOTION_NOMINAL_DECISIONS = 120
PROMOTION_INDEPENDENT_DECISIONS = 60


def _family_interleaved(entries: tuple[CorpusEntry, ...]) -> tuple[CorpusEntry, ...]:
    """Deal round-robin across families, so a partition is family-balanced by construction."""
    buckets: dict[str, list[CorpusEntry]] = {}
    for entry in sorted(entries, key=lambda item: item.template_id):
        buckets.setdefault(entry.family, []).append(entry)
    ordered: list[CorpusEntry] = []
    for index in range(max(len(bucket) for bucket in buckets.values())):
        for family in sorted(buckets):
            bucket = buckets[family]
            if index < len(bucket):
                ordered.append(bucket[index])
    return tuple(ordered)


def d4_calibration_entries() -> tuple[CorpusEntry, ...]:
    """The hundred fresh groups as the catalogue builder wants them."""
    return _family_interleaved(
        tuple(
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
            for spec in D4_CALIBRATION_SPECS
        )
    )


def d4_fitting_entries() -> tuple[CorpusEntry, ...]:
    """The eighty predecessor packages, carried rather than re-authored.

    The contract's composition — ten D2 calibration, fifty D2 training, twenty D3 calibration —
    is exactly three released partitions, so there is no selection to make here and none is made.
    Every entry keeps `inherited` as the released catalogue set it: these are packages to
    re-execute under D4 run identities, not new tasks.
    """
    d2 = assign_groups()
    carried = (
        tuple(d2[CorrectionPartition.CALIBRATION])
        + tuple(d2[CorrectionPartition.TRAINING])
        + d3_calibration_entries()
    )
    return _family_interleaved(carried)


def build_d4_fitting_catalogue() -> SealedPartitionCatalogue:
    """Seal the fitting partition under D4's own seed and generator path."""
    entries = d4_fitting_entries()
    if len(entries) != FITTING_GROUPS:
        raise ValueError(f"{len(entries)} fitting groups against a frozen target of 80")
    return build_catalogue(
        CorrectionPartition.TRAINING,
        entries,
        seed=D4_FITTING_SEED,
        generator_path=D4_FITTING_GENERATOR_PATH,
    )


def build_d4_calibration_catalogue() -> SealedPartitionCatalogue:
    """Seal the fresh calibration partition under D4's own seed and generator path."""
    entries = d4_calibration_entries()
    if len(entries) != CALIBRATION_GROUPS:
        raise ValueError(f"{len(entries)} calibration groups against a frozen target of 100")
    return build_catalogue(
        CorrectionPartition.CALIBRATION,
        entries,
        seed=D4_CALIBRATION_SEED,
        generator_path=D4_CALIBRATION_GENERATOR_PATH,
    )


def build_d4_retrieval_pool() -> SealedRetrievalPool:
    """Seal D4's sixty authored retrieval groups."""
    return retrieval_pool_of(D4_RETRIEVAL_SPECS)


def _cases_for(
    catalogues: tuple[SealedPartitionCatalogue, ...],
    *,
    stage: str,
    seed: int,
    source_manifest_hash: str,
    cases: tuple[str, ...],
    groups_limit: int | None = None,
) -> tuple[OodCaseManifestV3, ...]:
    """Enumerate exact case identities in manifest order, optionally stopping after N groups."""
    chosen = [group for catalogue in catalogues for group in catalogue.groups]
    if groups_limit is not None:
        chosen = chosen[:groups_limit]
    return tuple(
        OodCaseManifestV3(
            case_id=transformation_case_id(
                stage=stage,
                source_group_id=group.repository_group,
                case_name=case_name,
                seed=seed,
            ),
            stage=stage,
            source_group_id=group.repository_group,
            case_name=case_name,
            transformations=(case_name,),
            seed=seed,
            candidate_ids=tuple(
                str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
            ),
            source_manifest_hash=source_manifest_hash,
        )
        for group in chosen
        for case_name in cases
    )


def invariance_sample_groups(calibration: SealedPartitionCatalogue) -> tuple[str, ...]:
    """The twenty groups the invariance regression runs over, by the frozen manifest order.

    Taking the first twenty of a family-interleaved manifest is a rule that can be checked
    against the sealed catalogue afterwards. Choosing twenty once the bodies were open could
    not be.
    """
    return tuple(group.repository_group for group in calibration.groups[:INVARIANCE_SAMPLE_GROUPS])


def submanifest_of(
    catalogues: tuple[SealedPartitionCatalogue, ...],
    *,
    stage: str,
    seed: int,
    cases: tuple[str, ...],
    groups_limit: int | None = None,
) -> OodSubmanifestV3:
    """One hash-bound transformation set, under the generator and oracle D3 released.

    The set is bound to the catalogue it names, or to the paired hash of both when it spans two:
    a submanifest over two catalogues that named only one of them would look intact after the
    other drifted.
    """
    source_manifest_hash = (
        catalogues[0].content_hash if len(catalogues) == 1 else paired_manifest_hash(*catalogues)
    )
    return OodSubmanifestV3(
        stage=stage,
        source_manifest_hash=source_manifest_hash,
        generator_code_hash=transformations_d3.generator_code_hash(),
        hard_coded_oracle_hash=transformations_d3.hard_coded_oracle_hash(),
        cases=_cases_for(
            catalogues,
            stage=stage,
            seed=seed,
            source_manifest_hash=source_manifest_hash,
            cases=cases,
            groups_limit=groups_limit,
        ),
    )


def invariance_submanifest(calibration: SealedPartitionCatalogue) -> OodSubmanifestV3:
    """Forty transformed decisions over twenty groups, which count as zero independent ones."""
    return submanifest_of(
        (calibration,),
        stage=INVARIANCE_STAGE,
        seed=INVARIANCE_TRANSFORM_SEED,
        cases=D4_CASES,
        groups_limit=INVARIANCE_SAMPLE_GROUPS,
    )


def promotion_submanifest(
    final_a: SealedPartitionCatalogue, final_b: SealedPartitionCatalogue
) -> OodSubmanifestV3:
    """Two cases for every one of the sixty final groups: 120 nominal, 60 independent."""
    return submanifest_of(
        (final_a, final_b), stage=PROMOTION_STAGE, seed=PROMOTION_TRANSFORM_SEED, cases=D4_CASES
    )


class SealedD4Corpus(HashedExperienceContract):
    """Every D4 role in one hash-bound record: carried, fresh, transformed and retrieval."""

    revision: int = 4
    fitting_catalogue_hash: Sha256Hex
    calibration_catalogue_hash: Sha256Hex
    final_a_catalogue_hash: Sha256Hex
    final_b_catalogue_hash: Sha256Hex
    canary_catalogue_hash: Sha256Hex
    invariance_submanifest_hash: Sha256Hex
    promotion_submanifest_hash: Sha256Hex
    retrieval_pool_hash: Sha256Hex
    fitting_groups: int = Field(ge=80)
    calibration_groups: int = Field(ge=100)
    final_a_groups: int = Field(ge=30)
    final_b_groups: int = Field(ge=30)
    canary_groups: int = Field(ge=5)
    retrieval_source_groups: int = Field(ge=60)
    invariance_transformed_decisions: int = Field(ge=40)
    invariance_independent_decisions: int = Field(default=0, ge=0, le=0)
    promotion_nominal_decisions: int = Field(ge=120)
    promotion_independent_decisions: int = Field(ge=60)
    candidate_slots: int = Field(ge=1)
    corpus_authoring_capability_revoked: bool = True
    outcomes_present: bool = False

    @model_validator(mode="after")
    def the_seal_names_no_outcome_and_counts_replicas_as_replicas(self) -> SealedD4Corpus:
        if self.outcomes_present:
            raise ValueError("a sealed corpus that carries an outcome is a result")
        if not self.corpus_authoring_capability_revoked:
            raise ValueError("the seal closes corpus authoring; an open capability is not sealed")
        if self.invariance_independent_decisions:
            raise ValueError(
                "a transformed decision repeats its source group's fitted feature vector, so the "
                "invariance sample adds no independent decision"
            )
        if self.promotion_nominal_decisions != self.promotion_independent_decisions * 2:
            raise ValueError(
                "the promotion set names two cases per group, so its nominal count is exactly "
                "twice its independent one"
            )
        return self


@dataclass(frozen=True, slots=True)
class D4CorpusBundle:
    """Everything S21D4-032 seals, in one value, so a caller cannot hold half of it."""

    catalogues: dict[CorrectionPartition, SealedPartitionCatalogue]
    invariance_transformations: OodSubmanifestV3
    promotion_transformations: OodSubmanifestV3
    retrieval_pool: SealedRetrievalPool
    seal: SealedD4Corpus
    #: The released catalogues these roles were carried from, for the reuse proof.
    reused_from_d3: dict[CorrectionPartition, str]
    #: The D3 seal these objects came out of. What S21D4-032 has to show is not that the three
    #: hashes can be recomputed to the same value -- a re-derivation would do that and would
    #: hide a drift -- but that they arrived here from the released seal, so a caller can check
    #: them against sprint-21d3-sealed-manifests.json and see the same bytes.
    d3_seal_hash: str

    def groups_of(self, partition: CorrectionPartition) -> frozenset[str]:
        return frozenset(group.repository_group for group in self.catalogues[partition].groups)

    @property
    def retrieval_groups(self) -> frozenset[str]:
        return frozenset(group.repository_group for group in self.retrieval_pool.groups)


#: The three roles D4 does not re-derive. Carried objects, so a drift fails a comparison.
CARRIED_ROLES = (
    CorrectionPartition.FINAL_A,
    CorrectionPartition.FINAL_B,
    CorrectionPartition.CANARY,
)


def seal_d4_corpus() -> D4CorpusBundle:
    """Seal every D4 role. Deterministic: same corpora and seeds, same hashes."""
    d3 = seal_d3_corpus()
    carried = {partition: d3.catalogues[partition] for partition in CARRIED_ROLES}
    catalogues = {
        CorrectionPartition.TRAINING: build_d4_fitting_catalogue(),
        CorrectionPartition.CALIBRATION: build_d4_calibration_catalogue(),
        **carried,
    }

    seen: dict[str, CorrectionPartition] = {}
    for partition, catalogue in catalogues.items():
        for group in catalogue.groups:
            previous = seen.setdefault(group.repository_group, partition)
            if previous is not partition:
                raise ValueError(
                    f"group {group.repository_group} is in both {previous.value} and "
                    f"{partition.value}; a group belongs to exactly one D4 role"
                )

    retrieval = build_d4_retrieval_pool()
    shared = seen.keys() & {group.repository_group for group in retrieval.groups}
    if shared:
        raise ValueError(f"correction and retrieval share {sorted(shared)}")

    invariance = invariance_submanifest(catalogues[CorrectionPartition.CALIBRATION])
    promotion = promotion_submanifest(
        catalogues[CorrectionPartition.FINAL_A], catalogues[CorrectionPartition.FINAL_B]
    )
    if len(invariance.cases) != INVARIANCE_TRANSFORMED_DECISIONS:
        raise ValueError(f"{len(invariance.cases)} invariance cases against a frozen 40")
    if len(promotion.cases) != PROMOTION_NOMINAL_DECISIONS:
        raise ValueError(f"{len(promotion.cases)} promotion cases against a frozen 120")

    seal = SealedD4Corpus(
        fitting_catalogue_hash=catalogues[CorrectionPartition.TRAINING].content_hash,
        calibration_catalogue_hash=catalogues[CorrectionPartition.CALIBRATION].content_hash,
        final_a_catalogue_hash=catalogues[CorrectionPartition.FINAL_A].content_hash,
        final_b_catalogue_hash=catalogues[CorrectionPartition.FINAL_B].content_hash,
        canary_catalogue_hash=catalogues[CorrectionPartition.CANARY].content_hash,
        invariance_submanifest_hash=invariance.content_hash,
        promotion_submanifest_hash=promotion.content_hash,
        retrieval_pool_hash=retrieval.content_hash,
        fitting_groups=len(catalogues[CorrectionPartition.TRAINING].groups),
        calibration_groups=len(catalogues[CorrectionPartition.CALIBRATION].groups),
        final_a_groups=len(catalogues[CorrectionPartition.FINAL_A].groups),
        final_b_groups=len(catalogues[CorrectionPartition.FINAL_B].groups),
        canary_groups=len(catalogues[CorrectionPartition.CANARY].groups),
        retrieval_source_groups=len(retrieval.groups),
        invariance_transformed_decisions=len(invariance.cases),
        invariance_independent_decisions=INVARIANCE_INDEPENDENT_DECISIONS,
        promotion_nominal_decisions=len(promotion.cases),
        promotion_independent_decisions=len(promotion.cases) // len(D4_CASES),
        candidate_slots=sum(catalogue.candidate_slots for catalogue in catalogues.values()),
    )
    return D4CorpusBundle(
        catalogues=catalogues,
        invariance_transformations=invariance,
        promotion_transformations=promotion,
        retrieval_pool=retrieval,
        seal=seal,
        reused_from_d3={
            partition: d3.catalogues[partition].content_hash for partition in CARRIED_ROLES
        },
        d3_seal_hash=d3.seal.content_hash,
    )


def calibration_module_sources() -> dict[str, str]:
    """`template_id -> baseline module text` for the fresh groups, for eligibility checks."""
    return {spec.template_id: module_source(spec, spec.baseline) for spec in D4_CALIBRATION_SPECS}


def eligible_calibration_groups() -> tuple[str, ...]:
    """The fresh groups both D4 cases apply to. The floor is checked by the caller."""
    return tuple(
        template_id
        for template_id, source in sorted(calibration_module_sources().items())
        if transformations_d3.eligible(source)
    )
