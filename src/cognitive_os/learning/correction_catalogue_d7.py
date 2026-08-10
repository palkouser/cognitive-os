"""S21D7-023: the D7 seal — what each role holds, named before anything it describes ran.

D7 seals nine roles and authors exactly one of them. The interesting thing is again which role
the predecessor's measured partition becomes.

*Fitting is the same 180 groups D5 authored, untouched and unread as a corpus.* Unlike D6, D7
**fits on it** — the containment class is fitted once on its 720 rows in W2 — which is the pool's
licensed role and the reason it was never a selection input. No row of it is re-executed here.

*Conformal is D6's 100 certification groups.* They certified a coverage and an error rate in D6
and are spent by publication; under S21D7-010 they place the bar and measure nothing. That is the
same one-step demotion D5's calibration partition took when it became D6's conformal half, one
sprint further along.

*Certification is fresh: a hundred groups from `reality_task_specs_d7`,* authored at S21D7-020 and
proved separated at S21D7-022 — from the bar-setting half, from the fitting pool, from the three
carried roles and from every released body. It is the only role D7 authors, and the reason it has
to exist is arithmetic: §2.3 requires 100 independent decisions in the *measured* set and D6
produced exactly 100, so one hundred groups cannot be both halves.

*Final A, final B and canary are carried unopened, for the fifth sprint running.* D2's objects,
carried by D3, D4, D5 and D6 before this. Carried, not re-derived: a re-derivation would produce
hashes that merely *ought* to equal the released ones and would hide a drift behind a coincidence.

*Retrieval is inherited, not authored.* The seal names D5's pool hash so a reader can see that D7
holds no retrieval role of its own, which is what the renewed condition-24 ruling bought.

The ninth role is arithmetic rather than growth, the way D6's eighth was: D5's calibration half —
spent twice, as D5's calibration and as D6's bar-setting half — is named here as a **spent** role
so that a reader can see it is neither read nor demoted a third time. S21D7-010 rejected it by
name, and a seal that simply omitted it would leave that rejection invisible.

`provisional=True` builds the same objects out of an unfinished corpus so the chain downstream of
this module can be exercised before the hundredth group exists. Every record it produces says so
in its own bytes, and `outcomes_present` stays False, so nothing provisional can be mistaken for
evidence. A provisional seal is refused the moment the corpus is complete.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field, model_validator

from cognitive_os.coding.reality_task_specs_d2 import module_source
from cognitive_os.coding.reality_task_specs_d7 import D7_CERTIFICATION_SPECS
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
from cognitive_os.learning.correction_catalogue_d4 import (
    CARRIED_ROLES,
    D4_CASES,
    INVARIANCE_STAGE,
    PROMOTION_STAGE,
    invariance_sample_groups,
    submanifest_of,
)
from cognitive_os.learning.correction_catalogue_d5 import (
    build_d5_calibration_catalogue,
    build_d5_fitting_catalogue,
)
from cognitive_os.learning.correction_catalogue_d6 import (
    build_d6_certification_catalogue,
    seal_d6_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition

#: D7's own seed, distinct from every C3, D2, D3, D4, D5 and D6 seed, so a D7 candidate identity
#: cannot collide with a predecessor's.
D7_CERTIFICATION_SEED = 21_070_101
INVARIANCE_TRANSFORM_SEED = 21_078_303
PROMOTION_TRANSFORM_SEED = 21_075_404

D7_CERTIFICATION_GENERATOR_PATH = "correction_catalogue_d7.seal_d7_corpus:certification"

#: The same two cases D4 named and D5 and D6 kept: a subset of the released
#: `transformations_d3.CASES`, so the generator and its hard-coded oracle are the ones D3 froze.
D7_CASES = D4_CASES

FITTING_GROUPS = 180
CONFORMAL_GROUPS = 100
CERTIFICATION_GROUPS = 100
INVARIANCE_SAMPLE_GROUPS = 20
INVARIANCE_TRANSFORMED_DECISIONS = 40
INVARIANCE_INDEPENDENT_DECISIONS = 0
PROMOTION_NOMINAL_DECISIONS = 120
PROMOTION_INDEPENDENT_DECISIONS = 60

#: One point, not a ladder. 720 outcomes over 180 groups: the whole fitting pool, and the volume
#: the containment direction is fitted at — once, in W2.
D7_VOLUME_POINT = 720


def d7_certification_entries() -> tuple[CorpusEntry, ...]:
    """The fresh groups as the catalogue builder wants them."""
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
            for spec in D7_CERTIFICATION_SPECS
        )
    )


def build_d7_certification_catalogue(*, provisional: bool = False) -> SealedPartitionCatalogue:
    """Seal the fresh certification partition under D7's own seed and generator path."""
    entries = d7_certification_entries()
    if len(entries) != CERTIFICATION_GROUPS and not provisional:
        raise ValueError(
            f"{len(entries)} certification groups against a frozen target of {CERTIFICATION_GROUPS}"
        )
    if len(entries) >= CERTIFICATION_GROUPS and provisional:
        raise ValueError(
            "the corpus is complete; a provisional seal over a complete corpus would let an "
            "unfinished-looking record carry finished evidence"
        )
    return build_catalogue(
        CorrectionPartition.CALIBRATION,
        entries,
        seed=D7_CERTIFICATION_SEED,
        generator_path=D7_CERTIFICATION_GENERATOR_PATH,
    )


class SealedD7Corpus(HashedExperienceContract):
    """Every D7 role in one hash-bound record: carried, spent, conformal, fresh and inherited."""

    revision: int = 7
    fitting_catalogue_hash: Sha256Hex
    #: D6's certification catalogue, carried into the bar-setting role under S21D7-010.
    conformal_catalogue_hash: Sha256Hex
    #: D5's calibration catalogue: spent twice, demoted no further, read by nothing in D7. Named
    #: so that its exclusion is visible rather than silent.
    spent_calibration_catalogue_hash: Sha256Hex
    certification_catalogue_hash: Sha256Hex
    final_a_catalogue_hash: Sha256Hex
    final_b_catalogue_hash: Sha256Hex
    canary_catalogue_hash: Sha256Hex
    invariance_submanifest_hash: Sha256Hex
    promotion_submanifest_hash: Sha256Hex
    #: D5's retrieval pool, named so a reader can see D7 holds none of its own. Condition 24 is
    #: inherited under sprint-21d7-condition-24-ruling.json rather than re-measured.
    inherited_retrieval_pool_hash: Sha256Hex
    retrieval_groups_authored: int = Field(default=0, ge=0, le=0)

    fitting_groups: int = Field(ge=180)
    conformal_groups: int = Field(ge=100)
    certification_groups: int = Field(ge=1)
    final_a_groups: int = Field(ge=30)
    final_b_groups: int = Field(ge=30)
    canary_groups: int = Field(ge=5)
    #: Floored by the validator rather than by the field, because a provisional seal reports the
    #: cases its unfinished corpus actually produced. A record that padded this to 40 to satisfy
    #: a constraint would be stating a number nothing measured.
    invariance_transformed_decisions: int = Field(ge=0)
    invariance_independent_decisions: int = Field(default=0, ge=0, le=0)
    promotion_nominal_decisions: int = Field(ge=120)
    promotion_independent_decisions: int = Field(ge=60)
    volume_point: int = Field(ge=1)
    candidate_slots: int = Field(ge=1)
    corpus_authoring_capability_revoked: bool = True
    outcomes_present: bool = False
    #: Set while the certification corpus is unfinished. A provisional seal exists so the chain
    #: below it can be exercised early; it may never carry an outcome or reach a gate row.
    provisional: bool = False

    @model_validator(mode="after")
    def the_seal_names_no_outcome_and_no_half_group_volume(self) -> SealedD7Corpus:
        if self.outcomes_present:
            raise ValueError("a sealed corpus that carries an outcome is a result")
        if not self.corpus_authoring_capability_revoked and not self.provisional:
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
        if self.conformal_catalogue_hash == self.certification_catalogue_hash:
            raise ValueError(
                "the half that places the bar and the half measured against it are the same "
                "catalogue; a decision cannot certify itself"
            )
        # The half S21D7-010 rejected may not arrive through the door it was refused at.
        if self.spent_calibration_catalogue_hash in {
            self.conformal_catalogue_hash,
            self.certification_catalogue_hash,
        }:
            raise ValueError(
                "the twice-spent D5 calibration half is carrying a D7 role; S21D7-010 named it "
                "and declined it, and a third spend is not a demotion step any ruling permits"
            )
        if self.volume_point % CANDIDATES_PER_GROUP:
            raise ValueError(
                f"volume point {self.volume_point} does not land on a whole group; fitting on "
                "part of a group puts the rest of it in the exemplar set"
            )
        if self.volume_point != self.fitting_groups * CANDIDATES_PER_GROUP:
            raise ValueError(
                f"the volume point {self.volume_point} is not the whole fitting pool of "
                f"{self.fitting_groups * CANDIDATES_PER_GROUP} outcomes; D7 fits one direction "
                "on the whole pool and refuses a volume ladder"
            )
        if self.provisional:
            if self.certification_groups >= CERTIFICATION_GROUPS:
                raise ValueError(
                    "a complete certification corpus cannot be sealed provisionally; the flag "
                    "exists for an unfinished one and nothing else"
                )
            return self
        if self.certification_groups < CERTIFICATION_GROUPS:
            raise ValueError(
                f"{self.certification_groups} certification groups against a frozen target of "
                f"{CERTIFICATION_GROUPS}; §2.3 counts 100 independent decisions in the measured "
                "set"
            )
        if self.invariance_transformed_decisions < INVARIANCE_TRANSFORMED_DECISIONS:
            raise ValueError(
                f"{self.invariance_transformed_decisions} invariance cases against a frozen "
                f"{INVARIANCE_TRANSFORMED_DECISIONS}"
            )
        return self


@dataclass(frozen=True, slots=True)
class D7CorpusBundle:
    """Everything S21D7-023 seals, in one value, so a caller cannot hold half of it."""

    catalogues: dict[CorrectionPartition, SealedPartitionCatalogue]
    #: The bar-setting half. Not in `catalogues`: it shares the CALIBRATION partition with the
    #: certification half in the protocol's vocabulary, and a dictionary keyed by partition
    #: cannot hold both. Keeping it beside them is what stops one being read as the other.
    conformal: SealedPartitionCatalogue
    #: The twice-spent D5 calibration half. Held, named, and read by nothing.
    spent_calibration: SealedPartitionCatalogue
    invariance_transformations: OodSubmanifestV3
    promotion_transformations: OodSubmanifestV3
    seal: SealedD7Corpus
    #: The released catalogues the three protected roles were carried from, for the reuse proof.
    reused_from_d6: dict[CorrectionPartition, str]
    #: The D6 seal these objects came out of, so a caller can check them against
    #: sprint-21d6-sealed-manifests.json and see the same bytes rather than the same number.
    d6_seal_hash: str

    def groups_of(self, partition: CorrectionPartition) -> frozenset[str]:
        return frozenset(group.repository_group for group in self.catalogues[partition].groups)

    @property
    def conformal_groups(self) -> frozenset[str]:
        return frozenset(group.repository_group for group in self.conformal.groups)


def seal_d7_corpus(*, provisional: bool = False) -> D7CorpusBundle:
    """Seal every D7 role. Deterministic: same corpora and seeds, same hashes."""
    d6 = seal_d6_corpus()
    carried = {partition: d6.catalogues[partition] for partition in CARRIED_ROLES}
    certification = build_d7_certification_catalogue(provisional=provisional)
    catalogues = {
        CorrectionPartition.TRAINING: build_d5_fitting_catalogue(),
        CorrectionPartition.CALIBRATION: certification,
        **carried,
    }
    conformal = build_d6_certification_catalogue()
    spent_calibration = build_d5_calibration_catalogue()

    seen: dict[str, CorrectionPartition] = {}
    for partition, catalogue in catalogues.items():
        for group in catalogue.groups:
            previous = seen.setdefault(group.repository_group, partition)
            if previous is not partition:
                raise ValueError(
                    f"group {group.repository_group} is in both {previous.value} and "
                    f"{partition.value}; a group belongs to exactly one D7 role"
                )

    # The one separation this seal exists to enforce, and the one the whole experiment rests on:
    # a group that helps place the bar may not also be certified against it.
    both = {group.repository_group for group in conformal.groups} & {
        group.repository_group for group in certification.groups
    }
    if both:
        raise ValueError(
            f"{len(both)} groups are in both the conformal and the certification half: "
            f"{sorted(both)[:3]}"
        )
    # D7 fits on the fitting pool, so the bar may not be placed by margins the direction was
    # fitted on, and the measured half may not be either.
    for role, groups in (
        ("conformal", {group.repository_group for group in conformal.groups}),
        ("certification", {group.repository_group for group in certification.groups}),
    ):
        overlap = groups & {
            group.repository_group for group in catalogues[CorrectionPartition.TRAINING].groups
        }
        if overlap:
            raise ValueError(
                f"{len(overlap)} {role} groups are in the fitting pool; the direction would be "
                "read on the rows it was fitted on"
            )
    if {group.repository_group for group in spent_calibration.groups} & (
        {group.repository_group for group in conformal.groups}
        | {group.repository_group for group in certification.groups}
    ):
        raise ValueError(
            "the twice-spent D5 calibration half overlaps a D7 role; S21D7-010 declined it"
        )

    invariance = submanifest_of(
        (certification,),
        stage=INVARIANCE_STAGE,
        seed=INVARIANCE_TRANSFORM_SEED,
        cases=D7_CASES,
        groups_limit=INVARIANCE_SAMPLE_GROUPS,
    )
    promotion = submanifest_of(
        (
            catalogues[CorrectionPartition.FINAL_A],
            catalogues[CorrectionPartition.FINAL_B],
        ),
        stage=PROMOTION_STAGE,
        seed=PROMOTION_TRANSFORM_SEED,
        cases=D7_CASES,
    )
    if len(invariance.cases) != INVARIANCE_TRANSFORMED_DECISIONS and not provisional:
        raise ValueError(f"{len(invariance.cases)} invariance cases against a frozen 40")
    if len(promotion.cases) != PROMOTION_NOMINAL_DECISIONS:
        raise ValueError(f"{len(promotion.cases)} promotion cases against a frozen 120")

    seal = SealedD7Corpus(
        fitting_catalogue_hash=catalogues[CorrectionPartition.TRAINING].content_hash,
        conformal_catalogue_hash=conformal.content_hash,
        spent_calibration_catalogue_hash=spent_calibration.content_hash,
        certification_catalogue_hash=certification.content_hash,
        final_a_catalogue_hash=catalogues[CorrectionPartition.FINAL_A].content_hash,
        final_b_catalogue_hash=catalogues[CorrectionPartition.FINAL_B].content_hash,
        canary_catalogue_hash=catalogues[CorrectionPartition.CANARY].content_hash,
        invariance_submanifest_hash=invariance.content_hash,
        promotion_submanifest_hash=promotion.content_hash,
        inherited_retrieval_pool_hash=d6.seal.inherited_retrieval_pool_hash,
        fitting_groups=len(catalogues[CorrectionPartition.TRAINING].groups),
        conformal_groups=len(conformal.groups),
        certification_groups=len(certification.groups),
        final_a_groups=len(catalogues[CorrectionPartition.FINAL_A].groups),
        final_b_groups=len(catalogues[CorrectionPartition.FINAL_B].groups),
        canary_groups=len(catalogues[CorrectionPartition.CANARY].groups),
        invariance_transformed_decisions=len(invariance.cases),
        invariance_independent_decisions=INVARIANCE_INDEPENDENT_DECISIONS,
        promotion_nominal_decisions=len(promotion.cases),
        promotion_independent_decisions=len(promotion.cases) // len(D7_CASES),
        volume_point=D7_VOLUME_POINT,
        candidate_slots=sum(catalogue.candidate_slots for catalogue in catalogues.values()),
        # A provisional seal is taken while groups remain to be authored, so the capability that
        # writes them is still open and the record has to say so. Claiming a revocation here
        # would be the one thing a seal cannot get wrong: the field exists to state that no
        # further body can enter the corpus, and under `provisional` more of them will.
        corpus_authoring_capability_revoked=not provisional,
        provisional=provisional,
    )
    return D7CorpusBundle(
        catalogues=catalogues,
        conformal=conformal,
        spent_calibration=spent_calibration,
        invariance_transformations=invariance,
        promotion_transformations=promotion,
        seal=seal,
        reused_from_d6={
            partition: d6.catalogues[partition].content_hash for partition in CARRIED_ROLES
        },
        d6_seal_hash=d6.seal.content_hash,
    )


def certification_module_sources() -> dict[str, str]:
    """`template_id -> baseline module text` for the fresh groups, for eligibility checks."""
    return {spec.template_id: module_source(spec, spec.baseline) for spec in D7_CERTIFICATION_SPECS}


def eligible_certification_groups() -> tuple[str, ...]:
    """The fresh groups both D7 cases apply to. The floor is checked by the caller."""
    return tuple(
        template_id
        for template_id, source in sorted(certification_module_sources().items())
        if transformations_d3.eligible(source)
    )


def d7_invariance_sample_groups(*, provisional: bool = False) -> tuple[str, ...]:
    """The groups the invariance regression runs over, by the frozen manifest order."""
    return invariance_sample_groups(build_d7_certification_catalogue(provisional=provisional))
