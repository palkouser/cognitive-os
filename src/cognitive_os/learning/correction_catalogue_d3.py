"""S21D3-032: the D3 seal — what each role holds, named before anything it describes ran.

Four of the six correction roles are D2's, byte for byte. S21D3-004 audited final A, final B and
canary and recorded `reuse` for all three, and §4.2 lets the fifty fitting groups be D2's
training packages re-run under new run identities. Re-deriving those catalogues here would
produce four hashes that merely *ought* to equal the released ones; calling `seal_corpus()` and
carrying its objects across means a drift is a failed comparison rather than a new number.

What is new is the calibration partition — twenty fresh groups from `reality_task_specs_d3` —
and the two revision-3 metamorphic submanifests, which are what D2 did not have: exact case
identities, six per group, sealed before any of them is scored.

The promotion submanifest names six cases for all sixty final groups rather than for the twenty
that will be executed. Which twenty those are is decided at S21D3-060 by the frozen
manifest-order rule, after the protected bodies resolve and before any outcome is read; sealing
only twenty now would mean choosing them while their eligibility could still be argued about.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from pydantic import Field, model_validator

from cognitive_os.coding.reality_retrieval_specs_d3 import D3_RETRIEVAL_SPECS
from cognitive_os.coding.reality_task_specs_d2 import module_source
from cognitive_os.coding.reality_task_specs_d3 import D3_CALIBRATION_SPECS
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning import transformations_d3
from cognitive_os.learning.calibration_ood import (
    OodCaseManifestV3,
    OodSubmanifestV3,
    transformation_case_id,
)
from cognitive_os.learning.correction_catalogue import (
    CANDIDATES_PER_GROUP,
    SOURCE_LICENCE,
    SOURCE_ORIGIN,
    CorpusEntry,
    SealedPartitionCatalogue,
    build_catalogue,
    seal_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition

#: D3's own seeds. Distinct from every D2 partition seed, so a D3 candidate identity cannot
#: collide with a D2 one even for a group that somehow shared a task ID.
D3_CALIBRATION_SEED = 21_034_101
CALIBRATION_TRANSFORM_SEED = 21_038_303
PROMOTION_TRANSFORM_SEED = 21_065_404

D3_CALIBRATION_GENERATOR_PATH = "correction_catalogue_d3.seal_d3_corpus:calibration"

CALIBRATION_STAGE = "fresh_calibration"
PROMOTION_STAGE = "promotion"

#: What each stage must leave standing after ineligible cases are dropped. Nominal is what the
#: manifest names; valid is the floor §2.3 will not go below.
NOMINAL_DECISIONS_PER_STAGE = 120
MINIMUM_VALID_DECISIONS_PER_STAGE = 100
CALIBRATION_GROUPS = 20


def _family_interleaved(entries: tuple[CorpusEntry, ...]) -> tuple[CorpusEntry, ...]:
    """Deal round-robin across families, so the calibration partition is family-balanced."""
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


def d3_calibration_entries() -> tuple[CorpusEntry, ...]:
    """The twenty fresh groups as the catalogue builder wants them."""
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
            for spec in D3_CALIBRATION_SPECS
        )
    )


def build_d3_calibration_catalogue() -> SealedPartitionCatalogue:
    """Seal the fresh calibration partition under D3's own seed and generator path."""
    entries = d3_calibration_entries()
    if len(entries) != CALIBRATION_GROUPS:
        raise ValueError(f"{len(entries)} calibration groups against a frozen target of 20")
    return build_catalogue(
        CorrectionPartition.CALIBRATION,
        entries,
        seed=D3_CALIBRATION_SEED,
        generator_path=D3_CALIBRATION_GENERATOR_PATH,
    )


class RetrievalSourceGroup(HashedExperienceContract):
    """One overproduced retrieval group: two states of one task, and neither is an outcome."""

    template_id: NonEmptyStr
    repository_group: NonEmptyStr
    family: NonEmptyStr
    task_signature: NonEmptyStr
    module: NonEmptyStr
    failed_source_hash: Sha256Hex
    repaired_source_hash: Sha256Hex
    hidden_verifier_hash: Sha256Hex
    source_licence: NonEmptyStr = SOURCE_LICENCE
    source_origin: NonEmptyStr = SOURCE_ORIGIN
    usage_rights_verified: bool = True

    @model_validator(mode="after")
    def the_two_states_differ(self) -> RetrievalSourceGroup:
        if self.failed_source_hash == self.repaired_source_hash:
            raise ValueError("a retrieval pair whose two states are one state is not a pair")
        return self


class SealedRetrievalPool(HashedExperienceContract):
    """The overproduced pool, sealed before any query, judgement or arm exists."""

    revision: int = 3
    minimum_source_groups: int = Field(default=60, ge=60)
    minimum_qualifying_queries: int = Field(default=50, ge=50)
    groups: tuple[RetrievalSourceGroup, ...] = Field(min_length=60)
    outcomes_present: bool = False
    queries_resolved: bool = False

    @model_validator(mode="after")
    def the_pool_is_overproduced_and_unscored(self) -> SealedRetrievalPool:
        if self.outcomes_present or self.queries_resolved:
            raise ValueError("a sealed retrieval pool carries no outcome and no resolved query")
        if len({group.repository_group for group in self.groups}) != len(self.groups):
            raise ValueError("a retrieval group is named twice")
        if len(self.groups) < self.minimum_source_groups:
            raise ValueError(
                f"{len(self.groups)} source groups against a floor of {self.minimum_source_groups}"
            )
        return self


def build_retrieval_pool() -> SealedRetrievalPool:
    """Seal the sixty authored retrieval groups. Content hashes only: no query is chosen here."""
    return SealedRetrievalPool(
        groups=tuple(
            RetrievalSourceGroup(
                template_id=spec.template_id,
                repository_group=spec.repository_group,
                family=spec.family.value,
                task_signature=spec.task_signature,
                module=spec.module,
                failed_source_hash=sha256(spec.module_text(spec.failed).encode()).hexdigest(),
                repaired_source_hash=sha256(spec.module_text(spec.repaired).encode()).hexdigest(),
                hidden_verifier_hash=sha256(spec.hidden_test.encode()).hexdigest(),
            )
            for spec in D3_RETRIEVAL_SPECS
        )
    )


def _cases_for(
    catalogues: tuple[SealedPartitionCatalogue, ...],
    *,
    stage: str,
    seed: int,
    source_manifest_hash: str,
) -> tuple[OodCaseManifestV3, ...]:
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
        for catalogue in catalogues
        for group in catalogue.groups
        for case_name in transformations_d3.CASES
    )


def paired_manifest_hash(left: SealedPartitionCatalogue, right: SealedPartitionCatalogue) -> str:
    """One identity for a submanifest that spans two catalogues, bound to both of them."""
    return sha256(f"{left.content_hash}:{right.content_hash}".encode()).hexdigest()


def calibration_transformation_submanifest(
    calibration: SealedPartitionCatalogue,
) -> OodSubmanifestV3:
    """One hundred and twenty exact case identities over the twenty fresh groups."""
    return OodSubmanifestV3(
        stage=CALIBRATION_STAGE,
        source_manifest_hash=calibration.content_hash,
        generator_code_hash=transformations_d3.generator_code_hash(),
        hard_coded_oracle_hash=transformations_d3.hard_coded_oracle_hash(),
        cases=_cases_for(
            (calibration,),
            stage=CALIBRATION_STAGE,
            seed=CALIBRATION_TRANSFORM_SEED,
            source_manifest_hash=calibration.content_hash,
        ),
    )


def promotion_transformation_submanifest(
    final_a: SealedPartitionCatalogue, final_b: SealedPartitionCatalogue
) -> OodSubmanifestV3:
    """Six candidate cases for every one of the sixty final groups.

    The manifest order is the order the two catalogues were sealed in, and S21D3-060 walks it
    to take the first twenty eligible groups. Enumerating all sixty is what makes that rule
    checkable: the reserve is visible, so a later reader can see that the twenty were not
    picked out of a hat once the bodies were open.
    """
    paired = paired_manifest_hash(final_a, final_b)
    return OodSubmanifestV3(
        stage=PROMOTION_STAGE,
        source_manifest_hash=paired,
        generator_code_hash=transformations_d3.generator_code_hash(),
        hard_coded_oracle_hash=transformations_d3.hard_coded_oracle_hash(),
        cases=_cases_for(
            (final_a, final_b),
            stage=PROMOTION_STAGE,
            seed=PROMOTION_TRANSFORM_SEED,
            source_manifest_hash=paired,
        ),
    )


class SealedD3Corpus(HashedExperienceContract):
    """Every D3 role in one hash-bound record: reused, fresh, transformed and retrieval."""

    revision: int = 3
    fitting_catalogue_hash: Sha256Hex
    calibration_catalogue_hash: Sha256Hex
    final_a_catalogue_hash: Sha256Hex
    final_b_catalogue_hash: Sha256Hex
    canary_catalogue_hash: Sha256Hex
    calibration_transformations_hash: Sha256Hex
    promotion_transformations_hash: Sha256Hex
    retrieval_pool_hash: Sha256Hex
    fitting_groups: int = Field(ge=50)
    calibration_groups: int = Field(ge=20)
    final_a_groups: int = Field(ge=30)
    final_b_groups: int = Field(ge=30)
    canary_groups: int = Field(ge=5)
    retrieval_source_groups: int = Field(ge=60)
    calibration_cases: int = Field(ge=120)
    promotion_cases: int = Field(ge=120)
    candidate_slots: int = Field(ge=1)
    outcomes_present: bool = False

    @model_validator(mode="after")
    def the_seal_names_no_outcome(self) -> SealedD3Corpus:
        if self.outcomes_present:
            raise ValueError("a sealed corpus that carries an outcome is a result")
        return self


@dataclass(frozen=True, slots=True)
class D3CorpusBundle:
    """Everything S21D3-032 seals, in one value, so a caller cannot hold half of it."""

    catalogues: dict[CorrectionPartition, SealedPartitionCatalogue]
    calibration_transformations: OodSubmanifestV3
    promotion_transformations: OodSubmanifestV3
    retrieval_pool: SealedRetrievalPool
    seal: SealedD3Corpus
    #: The released D2 catalogues these roles were carried from, for the reuse proof.
    reused_from_d2: dict[CorrectionPartition, str]

    def groups_of(self, partition: CorrectionPartition) -> frozenset[str]:
        return frozenset(group.repository_group for group in self.catalogues[partition].groups)

    @property
    def retrieval_groups(self) -> frozenset[str]:
        return frozenset(group.repository_group for group in self.retrieval_pool.groups)


def seal_d3_corpus() -> D3CorpusBundle:
    """Seal every D3 role. Deterministic: same corpora and seeds, same hashes."""
    d2 = seal_corpus()
    catalogues = {
        CorrectionPartition.TRAINING: d2.catalogues[CorrectionPartition.TRAINING],
        CorrectionPartition.CALIBRATION: build_d3_calibration_catalogue(),
        CorrectionPartition.FINAL_A: d2.catalogues[CorrectionPartition.FINAL_A],
        CorrectionPartition.FINAL_B: d2.catalogues[CorrectionPartition.FINAL_B],
        CorrectionPartition.CANARY: d2.catalogues[CorrectionPartition.CANARY],
    }

    seen: dict[str, CorrectionPartition] = {}
    for partition, catalogue in catalogues.items():
        for group in catalogue.groups:
            previous = seen.setdefault(group.repository_group, partition)
            if previous is not partition:
                raise ValueError(
                    f"group {group.repository_group} is in both {previous.value} and "
                    f"{partition.value}; a group belongs to exactly one D3 role"
                )

    retrieval = build_retrieval_pool()
    shared = seen.keys() & {group.repository_group for group in retrieval.groups}
    if shared:
        raise ValueError(f"correction and retrieval share {sorted(shared)}")

    calibration_cases = calibration_transformation_submanifest(
        catalogues[CorrectionPartition.CALIBRATION]
    )
    promotion_cases = promotion_transformation_submanifest(
        catalogues[CorrectionPartition.FINAL_A], catalogues[CorrectionPartition.FINAL_B]
    )
    if len(calibration_cases.cases) != NOMINAL_DECISIONS_PER_STAGE:
        raise ValueError(f"{len(calibration_cases.cases)} calibration cases against a nominal 120")

    seal = SealedD3Corpus(
        fitting_catalogue_hash=catalogues[CorrectionPartition.TRAINING].content_hash,
        calibration_catalogue_hash=catalogues[CorrectionPartition.CALIBRATION].content_hash,
        final_a_catalogue_hash=catalogues[CorrectionPartition.FINAL_A].content_hash,
        final_b_catalogue_hash=catalogues[CorrectionPartition.FINAL_B].content_hash,
        canary_catalogue_hash=catalogues[CorrectionPartition.CANARY].content_hash,
        calibration_transformations_hash=calibration_cases.content_hash,
        promotion_transformations_hash=promotion_cases.content_hash,
        retrieval_pool_hash=retrieval.content_hash,
        fitting_groups=len(catalogues[CorrectionPartition.TRAINING].groups),
        calibration_groups=len(catalogues[CorrectionPartition.CALIBRATION].groups),
        final_a_groups=len(catalogues[CorrectionPartition.FINAL_A].groups),
        final_b_groups=len(catalogues[CorrectionPartition.FINAL_B].groups),
        canary_groups=len(catalogues[CorrectionPartition.CANARY].groups),
        retrieval_source_groups=len(retrieval.groups),
        calibration_cases=len(calibration_cases.cases),
        promotion_cases=len(promotion_cases.cases),
        candidate_slots=sum(catalogue.candidate_slots for catalogue in catalogues.values()),
    )
    return D3CorpusBundle(
        catalogues=catalogues,
        calibration_transformations=calibration_cases,
        promotion_transformations=promotion_cases,
        retrieval_pool=retrieval,
        seal=seal,
        reused_from_d2={
            partition: d2.catalogues[partition].content_hash
            for partition in (
                CorrectionPartition.TRAINING,
                CorrectionPartition.FINAL_A,
                CorrectionPartition.FINAL_B,
                CorrectionPartition.CANARY,
            )
        },
    )


def calibration_module_sources() -> dict[str, str]:
    """`template_id -> baseline module text` for the fresh groups, for eligibility checks."""
    return {spec.template_id: module_source(spec, spec.baseline) for spec in D3_CALIBRATION_SPECS}


def eligible_calibration_groups() -> tuple[str, ...]:
    """The fresh groups all six cases apply to. The floor is checked by the caller."""
    return tuple(
        template_id
        for template_id, source in sorted(calibration_module_sources().items())
        if transformations_d3.eligible(source)
    )


__all__ = [
    "CALIBRATION_STAGE",
    "CANDIDATES_PER_GROUP",
    "MINIMUM_VALID_DECISIONS_PER_STAGE",
    "NOMINAL_DECISIONS_PER_STAGE",
    "PROMOTION_STAGE",
    "D3CorpusBundle",
    "RetrievalSourceGroup",
    "SealedD3Corpus",
    "SealedRetrievalPool",
    "build_d3_calibration_catalogue",
    "build_retrieval_pool",
    "calibration_transformation_submanifest",
    "eligible_calibration_groups",
    "paired_manifest_hash",
    "promotion_transformation_submanifest",
    "seal_d3_corpus",
]
