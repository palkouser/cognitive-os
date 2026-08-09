"""S21D5-023: the D5 seal — what each role holds, named before anything it describes ran.

D5 seals seven roles, and the interesting thing about them is that only two are new.

*Fitting is 180 groups, and every one of them is spent.* The pool is D4's fitting partition and
D4's calibration partition together — the hundred groups D4 already made a selection decision on.
Section 2 of the D5 handoff is the authority for reading them as fitting evidence anyway: a group
that decided a threshold is exhausted *as a calibration sample* and untouched as a task package.
It buys the volume arm a 320-to-720 span against D4's 200-to-320, which is the limitation
S21D4-039 recorded against its own, and it costs no authoring.

*Calibration and retrieval are fresh.* A hundred groups from `reality_task_specs_d5` and sixty
from `reality_retrieval_specs_d5`, authored at S21D5-020 and S21D5-021 and proved separated at
S21D5-022 — from each other, from the five carried roles, and from the spent-for-selection digest
the reuse audit sealed.

*Final A, final B and canary are carried unopened, for the third sprint running.* They are
D2's objects: D3 carried them, D4 carried D3's, and this module carries D4's. Carried, not
re-derived — a re-derivation would produce hashes that merely *ought* to equal the released ones,
and would hide a drift behind a coincidence. §3.2 forbids D5 from authoring into any of the three.

What D5 has that its predecessors did not is a volume arm with two points on it, so this seal
carries the points and refuses one that does not land on a whole group. Fitting three of a
group's four candidates would put the fourth's siblings in the exemplar set and then call the
difference a volume effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field, model_validator

from cognitive_os.coding.reality_retrieval_specs_d5 import D5_RETRIEVAL_SPECS
from cognitive_os.coding.reality_task_specs_d2 import module_source
from cognitive_os.coding.reality_task_specs_d5 import D5_CALIBRATION_SPECS
from cognitive_os.domain.common import Sha256Hex
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning import transformations_d3
from cognitive_os.learning.calibration_ood import OodSubmanifestV3
from cognitive_os.learning.correction_catalogue import (
    CANDIDATES_PER_GROUP,
    CorpusEntry,
    SealedPartitionCatalogue,
    _family_interleaved,
    build_catalogue,
)
from cognitive_os.learning.correction_catalogue_d3 import (
    SealedRetrievalPool,
    retrieval_pool_of,
)
from cognitive_os.learning.correction_catalogue_d4 import (
    CARRIED_ROLES,
    D4_CASES,
    INVARIANCE_STAGE,
    PROMOTION_STAGE,
    d4_calibration_entries,
    d4_fitting_entries,
    invariance_sample_groups,
    seal_d4_corpus,
    submanifest_of,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition

#: D5's own seeds. Distinct from every D2, D3 and D4 seed, so a D5 candidate identity cannot
#: collide with a predecessor's — which matters more here than it did for D4, because 180 of D5's
#: fitting groups are predecessor packages being re-executed rather than new tasks.
D5_FITTING_SEED = 21_050_202
D5_CALIBRATION_SEED = 21_050_101
INVARIANCE_TRANSFORM_SEED = 21_058_303
PROMOTION_TRANSFORM_SEED = 21_055_404

D5_FITTING_GENERATOR_PATH = "correction_catalogue_d5.seal_d5_corpus:fitting"
D5_CALIBRATION_GENERATOR_PATH = "correction_catalogue_d5.seal_d5_corpus:calibration"

#: The same two cases D4 named, and deliberately the same: they are a subset of the released
#: `transformations_d3.CASES`, so the generator and its hard-coded oracle are the ones D3 froze.
#: A D5 restatement of either would be a second oracle wearing the first one's name.
D5_CASES = D4_CASES

FITTING_GROUPS = 180
CALIBRATION_GROUPS = 100
INVARIANCE_SAMPLE_GROUPS = 20
RETRIEVAL_GROUPS = 60

INVARIANCE_TRANSFORMED_DECISIONS = 40
INVARIANCE_INDEPENDENT_DECISIONS = 0
PROMOTION_NOMINAL_DECISIONS = 120
PROMOTION_INDEPENDENT_DECISIONS = 60

#: S21D5-011's two volume points, in outcomes. Both land on whole groups: 80 and 180 of them.
D5_VOLUME_POINTS = (320, 720)


def d5_calibration_entries() -> tuple[CorpusEntry, ...]:
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
            for spec in D5_CALIBRATION_SPECS
        )
    )


def d5_fitting_entries() -> tuple[CorpusEntry, ...]:
    """D4's fitting partition and D4's calibration partition, together and re-interleaved.

    Those are two released partitions, so there is no selection to make here and none is made.
    Re-interleaving matters: the two arrive family-balanced separately, and concatenating them
    would put D4's calibration groups entirely after D4's fitting ones — so the 320-outcome
    volume point would read the first eighty groups and see one sprint's corpus, not a sample.
    """
    return _family_interleaved(d4_fitting_entries() + d4_calibration_entries())


def build_d5_fitting_catalogue() -> SealedPartitionCatalogue:
    """Seal the 180-group fitting partition under D5's own seed and generator path."""
    entries = d5_fitting_entries()
    if len(entries) != FITTING_GROUPS:
        raise ValueError(f"{len(entries)} fitting groups against a frozen target of 180")
    return build_catalogue(
        CorrectionPartition.TRAINING,
        entries,
        seed=D5_FITTING_SEED,
        generator_path=D5_FITTING_GENERATOR_PATH,
    )


def build_d5_calibration_catalogue() -> SealedPartitionCatalogue:
    """Seal the fresh calibration partition under D5's own seed and generator path."""
    entries = d5_calibration_entries()
    if len(entries) != CALIBRATION_GROUPS:
        raise ValueError(f"{len(entries)} calibration groups against a frozen target of 100")
    return build_catalogue(
        CorrectionPartition.CALIBRATION,
        entries,
        seed=D5_CALIBRATION_SEED,
        generator_path=D5_CALIBRATION_GENERATOR_PATH,
    )


def build_d5_retrieval_pool() -> SealedRetrievalPool:
    """Seal the sixty fresh retrieval groups. Content hashes only: no query is chosen here."""
    return retrieval_pool_of(D5_RETRIEVAL_SPECS)


class SealedD5Corpus(HashedExperienceContract):
    """Every D5 role in one hash-bound record: carried, spent, fresh, transformed and retrieval."""

    revision: int = 5
    fitting_catalogue_hash: Sha256Hex
    calibration_catalogue_hash: Sha256Hex
    final_a_catalogue_hash: Sha256Hex
    final_b_catalogue_hash: Sha256Hex
    canary_catalogue_hash: Sha256Hex
    invariance_submanifest_hash: Sha256Hex
    promotion_submanifest_hash: Sha256Hex
    retrieval_pool_hash: Sha256Hex
    #: D4's retrieval pool, named so a reader can see this seal is not carrying it. It was read
    #: once by D4 and is spent; D5's pool is the fresh sixty and the two hashes must differ.
    spent_retrieval_pool_hash: Sha256Hex
    fitting_groups: int = Field(ge=180)
    calibration_groups: int = Field(ge=100)
    final_a_groups: int = Field(ge=30)
    final_b_groups: int = Field(ge=30)
    canary_groups: int = Field(ge=5)
    retrieval_source_groups: int = Field(ge=60)
    invariance_transformed_decisions: int = Field(ge=40)
    invariance_independent_decisions: int = Field(default=0, ge=0, le=0)
    promotion_nominal_decisions: int = Field(ge=120)
    promotion_independent_decisions: int = Field(ge=60)
    volume_points: tuple[int, ...] = Field(min_length=2)
    candidate_slots: int = Field(ge=1)
    corpus_authoring_capability_revoked: bool = True
    outcomes_present: bool = False

    @model_validator(mode="after")
    def the_seal_names_no_outcome_and_no_volume_point_splits_a_group(
        self,
    ) -> SealedD5Corpus:
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
        if self.retrieval_pool_hash == self.spent_retrieval_pool_hash:
            raise ValueError(
                "the D5 retrieval pool is the pool D4 already read; a spent pool measures "
                "retrieval against queries whose answers have been seen"
            )
        split = [point for point in self.volume_points if point % CANDIDATES_PER_GROUP]
        if split:
            raise ValueError(
                f"volume point(s) {split} do not land on a whole group; fitting on part of a "
                "group puts the rest of it in the exemplar set and calls the difference volume"
            )
        if sorted(self.volume_points) != list(self.volume_points):
            raise ValueError("the volume points are a rising ladder, not a set")
        if self.volume_points[-1] != self.fitting_groups * CANDIDATES_PER_GROUP:
            raise ValueError(
                f"the top volume point {self.volume_points[-1]} is not the whole fitting pool of "
                f"{self.fitting_groups * CANDIDATES_PER_GROUP} outcomes"
            )
        return self


@dataclass(frozen=True, slots=True)
class D5CorpusBundle:
    """Everything S21D5-023 seals, in one value, so a caller cannot hold half of it."""

    catalogues: dict[CorrectionPartition, SealedPartitionCatalogue]
    invariance_transformations: OodSubmanifestV3
    promotion_transformations: OodSubmanifestV3
    retrieval_pool: SealedRetrievalPool
    seal: SealedD5Corpus
    #: The released catalogues the three protected roles were carried from, for the reuse proof.
    reused_from_d4: dict[CorrectionPartition, str]
    #: The D4 seal these objects came out of, so a caller can check them against
    #: sprint-21d4-sealed-manifests.json and see the same bytes rather than the same number.
    d4_seal_hash: str

    def groups_of(self, partition: CorrectionPartition) -> frozenset[str]:
        return frozenset(group.repository_group for group in self.catalogues[partition].groups)

    @property
    def retrieval_groups(self) -> frozenset[str]:
        return frozenset(group.repository_group for group in self.retrieval_pool.groups)


def seal_d5_corpus() -> D5CorpusBundle:
    """Seal every D5 role. Deterministic: same corpora and seeds, same hashes."""
    d4 = seal_d4_corpus()
    carried = {partition: d4.catalogues[partition] for partition in CARRIED_ROLES}
    catalogues = {
        CorrectionPartition.TRAINING: build_d5_fitting_catalogue(),
        CorrectionPartition.CALIBRATION: build_d5_calibration_catalogue(),
        **carried,
    }

    seen: dict[str, CorrectionPartition] = {}
    for partition, catalogue in catalogues.items():
        for group in catalogue.groups:
            previous = seen.setdefault(group.repository_group, partition)
            if previous is not partition:
                raise ValueError(
                    f"group {group.repository_group} is in both {previous.value} and "
                    f"{partition.value}; a group belongs to exactly one D5 role"
                )

    retrieval = build_d5_retrieval_pool()
    shared = seen.keys() & {group.repository_group for group in retrieval.groups}
    if shared:
        raise ValueError(f"correction and retrieval share {sorted(shared)}")
    spent = d4.retrieval_groups & {group.repository_group for group in retrieval.groups}
    if spent:
        raise ValueError(f"the D5 retrieval pool re-reads the spent D4 groups {sorted(spent)}")

    calibration = catalogues[CorrectionPartition.CALIBRATION]
    invariance = submanifest_of(
        (calibration,),
        stage=INVARIANCE_STAGE,
        seed=INVARIANCE_TRANSFORM_SEED,
        cases=D5_CASES,
        groups_limit=INVARIANCE_SAMPLE_GROUPS,
    )
    promotion = submanifest_of(
        (
            catalogues[CorrectionPartition.FINAL_A],
            catalogues[CorrectionPartition.FINAL_B],
        ),
        stage=PROMOTION_STAGE,
        seed=PROMOTION_TRANSFORM_SEED,
        cases=D5_CASES,
    )
    if len(invariance.cases) != INVARIANCE_TRANSFORMED_DECISIONS:
        raise ValueError(f"{len(invariance.cases)} invariance cases against a frozen 40")
    if len(promotion.cases) != PROMOTION_NOMINAL_DECISIONS:
        raise ValueError(f"{len(promotion.cases)} promotion cases against a frozen 120")

    seal = SealedD5Corpus(
        fitting_catalogue_hash=catalogues[CorrectionPartition.TRAINING].content_hash,
        calibration_catalogue_hash=calibration.content_hash,
        final_a_catalogue_hash=catalogues[CorrectionPartition.FINAL_A].content_hash,
        final_b_catalogue_hash=catalogues[CorrectionPartition.FINAL_B].content_hash,
        canary_catalogue_hash=catalogues[CorrectionPartition.CANARY].content_hash,
        invariance_submanifest_hash=invariance.content_hash,
        promotion_submanifest_hash=promotion.content_hash,
        retrieval_pool_hash=retrieval.content_hash,
        spent_retrieval_pool_hash=d4.retrieval_pool.content_hash,
        fitting_groups=len(catalogues[CorrectionPartition.TRAINING].groups),
        calibration_groups=len(calibration.groups),
        final_a_groups=len(catalogues[CorrectionPartition.FINAL_A].groups),
        final_b_groups=len(catalogues[CorrectionPartition.FINAL_B].groups),
        canary_groups=len(catalogues[CorrectionPartition.CANARY].groups),
        retrieval_source_groups=len(retrieval.groups),
        invariance_transformed_decisions=len(invariance.cases),
        invariance_independent_decisions=INVARIANCE_INDEPENDENT_DECISIONS,
        promotion_nominal_decisions=len(promotion.cases),
        promotion_independent_decisions=len(promotion.cases) // len(D5_CASES),
        volume_points=D5_VOLUME_POINTS,
        candidate_slots=sum(catalogue.candidate_slots for catalogue in catalogues.values()),
    )
    return D5CorpusBundle(
        catalogues=catalogues,
        invariance_transformations=invariance,
        promotion_transformations=promotion,
        retrieval_pool=retrieval,
        seal=seal,
        reused_from_d4={
            partition: d4.catalogues[partition].content_hash for partition in CARRIED_ROLES
        },
        d4_seal_hash=d4.seal.content_hash,
    )


def calibration_module_sources() -> dict[str, str]:
    """`template_id -> baseline module text` for the fresh groups, for eligibility checks."""
    return {spec.template_id: module_source(spec, spec.baseline) for spec in D5_CALIBRATION_SPECS}


def eligible_calibration_groups() -> tuple[str, ...]:
    """The fresh groups both D5 cases apply to. The floor is checked by the caller."""
    return tuple(
        template_id
        for template_id, source in sorted(calibration_module_sources().items())
        if transformations_d3.eligible(source)
    )


def d5_invariance_sample_groups() -> tuple[str, ...]:
    """The twenty groups the invariance regression runs over, by the frozen manifest order."""
    return invariance_sample_groups(build_d5_calibration_catalogue())
