"""S21D2-081: the correction-ranking half of the one integrity report.

Every guarantee D2 rests on was enforced at the moment a row was written — the projector
refused a role the sealed partition did not give, an outcome that preceded its own feature
record, a candidate outside the manifest. That is the right place to enforce them, and it is
the wrong place to *prove* them: a rule that only ever runs on the write path cannot answer
whether what is in the store today still satisfies it. A store can be restored from a backup
taken mid-campaign, partially migrated, or restored into the wrong database, and none of those
go back through the projector.

So these checks re-derive the same eight guarantees from the store and the sealed artifacts,
with the seal as the authority in every case. Nothing here trusts a column the campaign wrote
about itself: partition membership comes from the sealed feature-set artifact, group placement
comes from the same artifact, and the campaign manifest hash is the join between them.

Reported in the vocabulary of `coding.reality_integrity` rather than a second report of its
own, for the reason S21D1-064 gave: an operator asking whether the store is sound should not
have to know which sprint added which check.

The third state matters here more than anywhere else. D2 stopped at the learner-selection
door with a null, so *there is no model*, and two of the eight classes — activation state and
model identity — have nothing to check. A report that answered "0 wrongly-active components"
would be true and misleading in the same breath. They are reported as `not_opened`, bound to
the hash of the record that closed them.

Every check is a read. This module writes nothing, anywhere.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from cognitive_os.coding.reality_integrity import (
    FAILURE,
    NOT_OPENED,
    WARNING,
    IntegrityCheck,
)

#: The surface every D2 observation belongs to. A row on another surface is not this report's
#: business and is deliberately not counted into these totals.
CORRECTION_SURFACE = "experience.correction_ranking"

#: `partition -> the source kind the projector binds to it`. Restated here rather than
#: imported so that a change to the projector's table is a *disagreement* this report can
#: detect, instead of a change both sides make together and neither notices.
PARTITION_SOURCE_KIND: Mapping[str, str] = {
    "training": "correction_self_play_task_run",
    "calibration": "correction_self_play_task_run",
    "final_a": "governed_task_run",
    "final_b": "governed_task_run",
    "canary": "governed_task_run",
}

#: `partition -> provenance class`. Same reasoning.
PARTITION_PROVENANCE: Mapping[str, str] = {
    "training": "self_play",
    "calibration": "self_play",
    "final_a": "real_governed_run",
    "final_b": "real_governed_run",
    "canary": "real_governed_run",
}

#: Partitions whose rows may be fitted on. The others are evaluation-only for the life of the
#: sprint, which is the one inherited constraint that has no expiry.
FITTABLE_PARTITIONS = frozenset({"training", "calibration"})

_SAMPLE = 5


def _sample(items: Sequence[str]) -> str:
    shown = ", ".join(sorted(items)[:_SAMPLE])
    return shown if len(items) <= _SAMPLE else f"{shown}, +{len(items) - _SAMPLE} more"


# --------------------------------------------------------------------------- what is read


@dataclass(frozen=True, slots=True)
class ObservedCorrection:
    """One `learned_observations` row, as the store holds it."""

    observation_id: UUID
    source_task_id: UUID
    source_run_id: UUID
    source_kind: str
    provenance_class: str
    status: str
    evaluation_eligible: bool
    #: The prefix of `idempotency_key`, which the projector sets to the sealed manifest hash.
    campaign_manifest_hash: str
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class SealedPartition:
    """One sealed feature-set artifact, verified against its own recorded hash before use.

    This is the authority. Everything a check asks about an observation — which partition it
    belongs to, which group, whether it existed before its outcome — is answered from here.

    There can be more than one per campaign manifest. A campaign that was executed, resumed
    and executed again seals once per execution, and every one of those seals is real: the
    rows written under it were pre-outcome relative to *it*. Only the last one is what the
    sprint's evidence names, so a report that knew about only the named seal would call the
    earlier rows out of order when they were nothing of the kind. `declared` marks the seal
    the evidence file names; the rest were found in the store.
    """

    partition: str
    campaign_manifest_hash: str
    feature_set_hash: str
    sealed_at: datetime
    artifact_id: UUID
    candidate_ids: frozenset[UUID]
    task_ids: frozenset[UUID]
    groups: frozenset[str]
    #: False when the stored bytes did not reproduce `feature_set_hash`.
    bytes_reproduce_the_seal: bool = True
    #: True when the campaign evidence names this seal as the one it ran under.
    declared: bool = True


@dataclass(frozen=True, slots=True)
class LineageRow:
    """One `learned_artifacts` row and whether its bytes are really there."""

    lineage_id: UUID
    artifact_id: UUID
    role: str
    declared_content_hash: str
    observed_content_hash: str
    bytes_present: bool


@dataclass(frozen=True, slots=True)
class SequenceReceipt:
    """One `reality.campaign_sequence_recorded` event, with its position in the stream."""

    campaign_id: UUID
    stream_version: int
    task_id: UUID
    campaign_manifest_hash: str
    attempted_order: tuple[UUID, ...]
    intentionally_unattempted: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ActiveComponent:
    """A learned component the runtime could resolve. On the D2 null path there are none."""

    component_id: UUID
    surface: str
    revision: int
    state: str
    artifact_id: UUID | None
    artifact_content_hash: str | None


@dataclass(frozen=True, slots=True)
class StopRecord:
    """The immutable record that closed a class of evidence, and its hash.

    `reason` is carried so the report can say *why* a class is absent without the reader
    having to open the evidence file, and `content_hash` is carried so that saying so is
    checkable.
    """

    name: str
    content_hash: str
    reason: str


@dataclass(frozen=True, slots=True)
class InheritedPair:
    """A store this sprint must not have written to."""

    name: str
    root: Path
    expected_digest: str
    expected_files: int


@dataclass(frozen=True, slots=True)
class CorrectionEvidence:
    """Everything the eight classes are derived from, read once."""

    observations: tuple[ObservedCorrection, ...] = ()
    seals: tuple[SealedPartition, ...] = ()
    lineage: tuple[LineageRow, ...] = ()
    receipts: tuple[SequenceReceipt, ...] = ()
    components: tuple[ActiveComponent, ...] = ()
    inherited: tuple[InheritedPair, ...] = ()
    #: Set when the selection produced no candidate. Closes activation and model identity.
    selection_stop: StopRecord | None = None

    @property
    def seals_by_manifest(self) -> Mapping[str, tuple[SealedPartition, ...]]:
        """Every seal a campaign manifest was executed under, earliest first."""
        grouped: dict[str, list[SealedPartition]] = defaultdict(list)
        for seal in self.seals:
            grouped[seal.campaign_manifest_hash].append(seal)
        return {
            manifest: tuple(sorted(items, key=lambda seal: seal.sealed_at))
            for manifest, items in grouped.items()
        }

    def partition_of(self, manifest_hash: str) -> str | None:
        """The partition a manifest belongs to. Every seal of one manifest agrees on it."""
        seals = self.seals_by_manifest.get(manifest_hash)
        return None if not seals else seals[0].partition


# ------------------------------------------------------------------ 1. role and group


def every_observation_carries_its_sealed_role(
    evidence: CorrectionEvidence,
) -> IntegrityCheck:
    """The partition decides the role, so a row whose role disagrees with its seal is damage.

    Checked in both directions on purpose. A self-play row wearing a governed role would let
    real governed evidence be mistaken for training-eligible material; a governed row wearing
    a self-play role would do the reverse, which is the one that ends a sprint.
    """
    wrong: list[str] = []
    unknown: list[str] = []
    for row in evidence.observations:
        partition = evidence.partition_of(row.campaign_manifest_hash)
        if partition is None:
            unknown.append(str(row.observation_id))
            continue
        expected_kind = PARTITION_SOURCE_KIND.get(partition)
        expected_provenance = PARTITION_PROVENANCE.get(partition)
        if row.source_kind != expected_kind or row.provenance_class != expected_provenance:
            wrong.append(str(row.observation_id))
    broken = wrong + unknown
    return IntegrityCheck(
        name="every_correction_observation_carries_its_sealed_role",
        ok=not broken,
        severity=FAILURE,
        detail=(
            f"{len(evidence.observations)} observations across "
            f"{len({row.campaign_manifest_hash for row in evidence.observations})} sealed "
            f"campaigns carry the role their partition gives them"
            if not broken
            else f"{len(wrong)} observations whose role disagrees with their seal and "
            f"{len(unknown)} whose campaign manifest no seal names: {_sample(broken)}"
        ),
    )


def no_group_crosses_a_partition(evidence: CorrectionEvidence) -> IntegrityCheck:
    """A repository group in two partitions makes the split a formality. §S21D2-020."""
    seen: dict[str, list[str]] = defaultdict(list)
    for seal in evidence.seals:
        for group in seal.groups:
            seen[group].append(seal.partition)
    crossing = {group: parts for group, parts in seen.items() if len(set(parts)) > 1}
    total = len(seen)
    partitions = {seal.partition for seal in evidence.seals}
    return IntegrityCheck(
        name="no_correction_group_crosses_a_partition",
        ok=not crossing,
        severity=FAILURE,
        detail=(
            f"{total} repository groups over {len(partitions)} sealed partitions, each in "
            f"exactly one"
            if not crossing
            else f"{len(crossing)} groups in more than one partition: "
            f"{_sample([f'{g} in {sorted(set(p))}' for g, p in crossing.items()])}"
        ),
    )


# ---------------------------------------------------------------------- 2. chronology


def every_observation_follows_its_seal(evidence: CorrectionEvidence) -> IntegrityCheck:
    """Features were sealed before the first container started, and a clock cannot be argued with.

    The projector already refuses an outcome that precedes its own feature record. This asks
    the same question of the rows that are in the store now, because a restore, a partial
    migration or a hand-edited row never passes through the projector.

    Measured against the *earliest* seal a campaign manifest carries, not the one the sprint
    evidence names. A campaign executed more than once seals once per execution, and a row
    written under the first seal is genuinely pre-outcome even though a later seal postdates
    it. Comparing every row against the last seal would report sound evidence as damage —
    which is exactly what this check did on its first run over the D2 store.
    """
    first_seal = {
        manifest: seals[0].sealed_at for manifest, seals in evidence.seals_by_manifest.items()
    }
    early: list[str] = []
    for row in evidence.observations:
        sealed_at = first_seal.get(row.campaign_manifest_hash)
        if sealed_at is None:
            continue  # named by the role check; one defect should not fail two classes
        if row.recorded_at < sealed_at:
            early.append(str(row.observation_id))
    earliest = min((row.recorded_at for row in evidence.observations), default=None)
    first = min(first_seal.values(), default=None)
    return IntegrityCheck(
        name="every_correction_observation_follows_its_feature_seal",
        ok=not early,
        severity=FAILURE,
        detail=(
            f"earliest seal {first.isoformat() if first else 'none'} against the earliest "
            f"outcome {earliest.isoformat() if earliest else 'none'}; "
            f"{len(evidence.observations)} observations, none earlier than the first seal of "
            f"the campaign that produced it"
            if not early
            else f"{len(early)} observations recorded before the features that describe them "
            f"were sealed: {_sample(early)}"
        ),
    )


def each_campaign_manifest_was_sealed_once(evidence: CorrectionEvidence) -> IntegrityCheck:
    """More than one seal means the campaign was executed more than once. Not damage — news.

    A warning rather than a failure, and the distinction is the whole point. Nothing is
    inconsistent: every row resolves to bytes, to an event and to the seal it ran under. But
    the store then holds more rows than any one execution produced, and a dataset built from
    "every row on this surface" would silently be a dataset over two executions. That is
    something an operator has to know before using the store, which is what a warning is for.
    """
    repeated = {
        manifest: len(seals)
        for manifest, seals in evidence.seals_by_manifest.items()
        if len(seals) > 1
    }
    return IntegrityCheck(
        name="each_campaign_manifest_was_sealed_once",
        ok=not repeated,
        severity=WARNING,
        detail=(
            f"{len(evidence.seals_by_manifest)} campaign manifests, one seal each"
            if not repeated
            else f"{len(repeated)} campaign manifests were sealed more than once, so the store "
            f"holds rows from more than one execution and a dataset over it must select an "
            f"explicit member list: "
            + _sample([f"{manifest[:12]} x{count}" for manifest, count in repeated.items()])
        ),
    )


# ------------------------------------------------------------- 3. manifest membership


def every_observation_is_a_sealed_member(
    evidence: CorrectionEvidence,
) -> IntegrityCheck:
    """A row for work no manifest planned is a row the corpus never authorised."""
    tasks: dict[str, set[UUID]] = {
        manifest: {task for seal in seals for task in seal.task_ids}
        for manifest, seals in evidence.seals_by_manifest.items()
    }
    outside: list[str] = []
    for row in evidence.observations:
        held = tasks.get(row.campaign_manifest_hash)
        if held is None or row.source_task_id not in held:
            outside.append(str(row.observation_id))
    members = sum(len(seals[0].candidate_ids) for seals in evidence.seals_by_manifest.values())
    return IntegrityCheck(
        name="every_correction_observation_is_a_sealed_member",
        ok=not outside,
        severity=FAILURE,
        detail=(
            f"{len(evidence.observations)} observations resolve to tasks inside "
            f"{len(tasks)} sealed manifests holding {members} candidate slots"
            if not outside
            else f"{len(outside)} observations naming a task no sealed manifest holds: "
            f"{_sample(outside)}"
        ),
    )


# ----------------------------------------------------------------- 4. artifact lineage


def every_lineage_row_resolves(evidence: CorrectionEvidence) -> IntegrityCheck:
    """A lineage row is a claim about bytes; unverified, it is a claim about nothing."""
    missing = [str(row.artifact_id) for row in evidence.lineage if not row.bytes_present]
    disagreeing = [
        str(row.artifact_id)
        for row in evidence.lineage
        if row.declared_content_hash != row.observed_content_hash
    ]
    broken = missing + disagreeing
    roles = sorted({row.role for row in evidence.lineage})
    return IntegrityCheck(
        name="every_correction_lineage_row_resolves_to_its_bytes",
        ok=not broken,
        severity=FAILURE,
        detail=(
            f"{len(evidence.lineage)} lineage rows over roles {roles}; declared and observed "
            f"content hashes agree and every row has bytes"
            if not broken
            else f"{len(missing)} rows with no bytes and {len(disagreeing)} whose declared hash "
            f"is not what the store holds: {_sample(broken)}"
        ),
    )


def every_seal_reproduces_its_own_hash(evidence: CorrectionEvidence) -> IntegrityCheck:
    """The seal is the authority for every other check, so it is verified before it is used.

    Only the declared seals can be checked this way: a seal found in the store carries no
    independently recorded hash to be compared against, so "it hashes to itself" would be a
    tautology dressed as a verification. They are counted in the detail instead.
    """
    declared = [seal for seal in evidence.seals if seal.declared]
    found = len(evidence.seals) - len(declared)
    broken = [seal.partition for seal in declared if not seal.bytes_reproduce_the_seal]
    return IntegrityCheck(
        name="every_sealed_feature_set_reproduces_its_hash",
        ok=not broken,
        severity=FAILURE,
        detail=(
            (
                "; ".join(
                    f"{seal.partition} {seal.feature_set_hash[:12]} over "
                    f"{len(seal.candidate_ids)} slots"
                    for seal in sorted(declared, key=lambda item: item.partition)
                )
                or "no declared feature set was given to verify"
            )
            + f"; {found} further seals found in the store and not hash-checked"
            if not broken
            else f"{len(broken)} sealed feature sets whose stored bytes do not hash to the name "
            f"the campaign recorded: {_sample(broken)}"
        ),
    )


# ------------------------------------------------------------------- 5. receipt chain


def the_receipt_chain_is_contiguous(evidence: CorrectionEvidence) -> IntegrityCheck:
    """Compare-and-set on the campaign stream means the versions run 1..N with no gap.

    A gap is the interesting failure: it means a receipt existed and no longer does, which is
    exactly the state in which a resume re-runs work the campaign deliberately chose not to
    do — the failure mode S21D2-054 exists to prevent.
    """
    by_campaign: dict[UUID, list[int]] = defaultdict(list)
    for receipt in evidence.receipts:
        by_campaign[receipt.campaign_id].append(receipt.stream_version)
    broken: list[str] = []
    for campaign, versions in by_campaign.items():
        ordered = sorted(versions)
        if ordered != list(range(1, len(ordered) + 1)):
            broken.append(str(campaign))
    seals = evidence.seals_by_manifest
    unsealed = [
        str(receipt.task_id)
        for receipt in evidence.receipts
        if receipt.campaign_manifest_hash not in seals
    ]
    failures = broken + unsealed
    return IntegrityCheck(
        name="every_campaign_receipt_chains_to_its_predecessor",
        ok=not failures,
        severity=FAILURE,
        detail=(
            "; ".join(
                f"{campaign} 1..{len(versions)}"
                for campaign, versions in sorted(by_campaign.items(), key=lambda kv: str(kv[0]))
            )
            or "no campaign receipt was given to verify"
            if not failures
            else f"{len(broken)} campaigns whose receipt versions are not contiguous and "
            f"{len(unsealed)} receipts naming an unsealed manifest: {_sample(failures)}"
        ),
    )


# -------------------------------------------------- 6 and 7. activation and model identity


def _stop_contradicted(evidence: CorrectionEvidence) -> tuple[str, ...]:
    """Components on the stopped surface. A stop record says there are none, so any is damage.

    Without this, `not_opened` would be a way to *stop looking*: a report given a stop record
    would answer "nothing was registered" no matter what the store held, and a fabricated
    component would be the one thing the report could not see. The stop record says the store
    is empty on this surface; that is a claim, and a claim gets checked.
    """
    return tuple(
        str(component.component_id)
        for component in evidence.components
        if component.surface == CORRECTION_SURFACE
    )


def the_activation_state_is_sound(evidence: CorrectionEvidence) -> IntegrityCheck:
    """At most one active revision per surface — or nothing, if selection produced no candidate."""
    if evidence.selection_stop is not None:
        contradicted = _stop_contradicted(evidence)
        if contradicted:
            return IntegrityCheck(
                name="the_correction_surface_has_a_sound_activation_state",
                ok=False,
                severity=FAILURE,
                detail=(
                    f"the selection record {evidence.selection_stop.content_hash[:12]} says no "
                    f"component was registered for {CORRECTION_SURFACE}, and the store holds "
                    f"{len(contradicted)}: {_sample(contradicted)}"
                ),
            )
        return IntegrityCheck(
            name="the_correction_surface_has_a_sound_activation_state",
            ok=True,
            severity=NOT_OPENED,
            detail=(
                f"no component was ever registered for {CORRECTION_SURFACE}, and the store "
                f"holds none: {evidence.selection_stop.reason}"
            ),
            bound_hash=evidence.selection_stop.content_hash,
        )
    active: dict[str, list[str]] = defaultdict(list)
    for component in evidence.components:
        if component.state == "active":
            active[component.surface].append(str(component.component_id))
    contested = {surface: ids for surface, ids in active.items() if len(ids) > 1}
    return IntegrityCheck(
        name="the_correction_surface_has_a_sound_activation_state",
        ok=not contested,
        severity=FAILURE,
        detail=(
            f"{len(evidence.components)} components, "
            f"{sum(len(ids) for ids in active.values())} active, at most one per surface"
            if not contested
            else f"{len(contested)} surfaces with more than one active revision: "
            f"{_sample([f'{s}: {len(i)}' for s, i in contested.items()])}"
        ),
    )


def the_model_identity_agrees(evidence: CorrectionEvidence) -> IntegrityCheck:
    """An active component's artifact hash must be the one the component declares."""
    if evidence.selection_stop is not None:
        contradicted = _stop_contradicted(evidence)
        if contradicted:
            return IntegrityCheck(
                name="every_active_component_resolves_to_the_model_it_declares",
                ok=False,
                severity=FAILURE,
                detail=(
                    f"the selection record {evidence.selection_stop.content_hash[:12]} says no "
                    f"model was ever built, and the store holds {len(contradicted)} components "
                    f"on {CORRECTION_SURFACE}: {_sample(contradicted)}"
                ),
            )
        return IntegrityCheck(
            name="every_active_component_resolves_to_the_model_it_declares",
            ok=True,
            severity=NOT_OPENED,
            detail=(
                f"no model artifact exists for {CORRECTION_SURFACE}, and the store holds no "
                f"component that could name one: {evidence.selection_stop.reason}"
            ),
            bound_hash=evidence.selection_stop.content_hash,
        )
    stored = {row.artifact_id: row.observed_content_hash for row in evidence.lineage}
    wrong: list[str] = []
    for component in evidence.components:
        if component.state != "active":
            continue
        if component.artifact_id is None or component.artifact_content_hash is None:
            wrong.append(str(component.component_id))
            continue
        if stored.get(component.artifact_id) != component.artifact_content_hash:
            wrong.append(str(component.component_id))
    return IntegrityCheck(
        name="every_active_component_resolves_to_the_model_it_declares",
        ok=not wrong,
        severity=FAILURE,
        detail=(
            f"{len([c for c in evidence.components if c.state == 'active'])} active components "
            f"resolve to the artifact hash they declare"
            if not wrong
            else f"{len(wrong)} active components whose artifact is absent or hashes to "
            f"something else: {_sample(wrong)}"
        ),
    )


# ------------------------------------------------------------------ 8. store isolation


def inherited_pairs_are_untouched(
    evidence: CorrectionEvidence,
) -> tuple[IntegrityCheck, ...]:
    """One check per inherited store, named for the store, so a failure says which one."""
    from cognitive_os.coding.reality_integrity import artifact_pair_is_untouched

    return tuple(
        artifact_pair_is_untouched(
            f"{pair.name}_is_untouched",
            pair.root,
            expected_digest=pair.expected_digest,
            expected_files=pair.expected_files,
        )
        for pair in evidence.inherited
    )


# ------------------------------------------------------------------------- the report


def correction_checks(evidence: CorrectionEvidence) -> tuple[IntegrityCheck, ...]:
    """The eight classes S21D2-081 names, in the order an operator would read them."""
    return (
        every_seal_reproduces_its_own_hash(evidence),
        every_observation_carries_its_sealed_role(evidence),
        no_group_crosses_a_partition(evidence),
        every_observation_follows_its_seal(evidence),
        each_campaign_manifest_was_sealed_once(evidence),
        every_observation_is_a_sealed_member(evidence),
        every_lineage_row_resolves(evidence),
        the_receipt_chain_is_contiguous(evidence),
        the_activation_state_is_sound(evidence),
        the_model_identity_agrees(evidence),
        *inherited_pairs_are_untouched(evidence),
    )


def correction_counts(evidence: CorrectionEvidence) -> dict[str, Any]:
    """Exact numbers alongside the verdicts. `ok` on its own is not a report."""
    fittable = sum(
        1
        for row in evidence.observations
        if evidence.partition_of(row.campaign_manifest_hash) in FITTABLE_PARTITIONS
    )
    return {
        "observations": len(evidence.observations),
        "observations_in_a_fittable_partition": fittable,
        "real_governed_run_observations": sum(
            1 for row in evidence.observations if row.provenance_class == "real_governed_run"
        ),
        "sealed_partitions": {
            seals[0].partition: {
                "campaign_manifest_hash": manifest,
                "seals": [
                    {
                        "feature_set_hash": seal.feature_set_hash,
                        "artifact_id": str(seal.artifact_id),
                        "sealed_at": seal.sealed_at.isoformat(),
                        "declared_by_the_campaign_evidence": seal.declared,
                    }
                    for seal in seals
                ],
                "candidate_slots": len(seals[0].candidate_ids),
                "repository_groups": len(seals[0].groups),
                "observations": sum(
                    1 for row in evidence.observations if row.campaign_manifest_hash == manifest
                ),
            }
            for manifest, seals in sorted(
                evidence.seals_by_manifest.items(), key=lambda kv: kv[1][0].partition
            )
        },
        "lineage_rows": len(evidence.lineage),
        "campaign_receipts": len(evidence.receipts),
        "learned_components": len(evidence.components),
    }


# ----------------------------------------------------------------------- reading a store
#
# Kept apart from the checks above so that every check is a pure function of data a test can
# construct. A check that could only be exercised against a live PostgreSQL instance is a
# check whose seeded-violation test does not get written.


@dataclass(frozen=True, slots=True)
class SealSource:
    """Where one partition's sealed feature set lives, as the campaign evidence recorded it."""

    partition: str
    campaign_manifest_hash: str
    artifact_id: UUID
    feature_set_hash: str
    sealed_at: datetime
    #: False for a seal discovered in the store rather than named by the evidence file.
    declared: bool = True


#: Everything a sealed feature set could be filed under. The campaign stores them as plain
#: JSON, so discovery cannot select on the media type alone and has to try to parse.
_SEAL_MEDIA_TYPES: tuple[str, ...] = ("application/json",)

_SEAL_CANDIDATE_QUERY = """
SELECT a.artifact_id
FROM cognitive_os.artifacts a
JOIN cognitive_os.artifact_blobs b ON b.content_hash = a.content_hash
WHERE a.media_type = ANY(:media_types) AND b.size_bytes >= :minimum_bytes
ORDER BY a.created_at
"""


async def seal_candidates(connection: Any, *, minimum_bytes: int = 4096) -> tuple[UUID, ...]:
    """Artifacts large enough and of the right media type to *possibly* be a feature set.

    Deliberately only the query half: the caller fetches the bytes with the connection
    released, because the Artifact Store opens one of its own per read and would otherwise
    wait forever on a single-connection pool. The size floor keeps the scan off the six
    hundred small outcome payloads; it decides nothing, as parsing is what selects.
    """
    from sqlalchemy import text as sql

    rows = (
        await connection.execute(
            sql(_SEAL_CANDIDATE_QUERY),
            {"media_types": list(_SEAL_MEDIA_TYPES), "minimum_bytes": minimum_bytes},
        )
    ).all()
    return tuple(row.artifact_id for row in rows)


def seals_from(payloads: Mapping[UUID, bytes]) -> tuple[SealSource, ...]:
    """Every sealed feature set among `payloads`, including ones no evidence file names.

    A campaign that was executed more than once left a seal per execution, and the chronology
    check needs all of them to attribute rows written under a superseded one.

    Only `ValidationError` is skipped, and the narrowness is the point: an artifact that is
    not a feature set is expected and uninteresting, while an unreadable one is a fault this
    function has no business absorbing. A bare `except` here would turn a broken store into a
    store with fewer seals, and fewer seals is exactly the state in which the chronology
    check starts reporting sound rows as out of order.
    """
    from pydantic import ValidationError

    from cognitive_os.learning.correction_features import SealedFeatureRecordSet

    found: list[SealSource] = []
    for artifact_id, payload in payloads.items():
        try:
            record_set = SealedFeatureRecordSet.model_validate_json(payload)
        except ValidationError:
            continue
        found.append(
            SealSource(
                partition=record_set.partition,
                campaign_manifest_hash=record_set.campaign_manifest_hash,
                artifact_id=artifact_id,
                feature_set_hash=record_set.content_hash,
                sealed_at=record_set.sealed_at,
                declared=False,
            )
        )
    return tuple(found)


_OBSERVATION_QUERY = """
SELECT observation_id, source_task_id, source_run_id, source_kind, provenance_class,
       status, evaluation_eligible, split_part(idempotency_key, ':', 1) AS manifest_hash,
       recorded_at
FROM cognitive_os.learned_observations
WHERE surface = :surface
"""

_LINEAGE_QUERY = """
SELECT l.lineage_id, l.artifact_id, l.role, l.declared_content_hash, l.observed_content_hash,
       (b.content_hash IS NOT NULL) AS bytes_present
FROM cognitive_os.learned_artifacts l
LEFT JOIN cognitive_os.artifacts a ON a.artifact_id = l.artifact_id
LEFT JOIN cognitive_os.artifact_blobs b ON b.content_hash = a.content_hash
"""

_RECEIPT_QUERY = """
SELECT stream_id, stream_version, payload_json
FROM cognitive_os.events
WHERE event_type = 'reality.campaign_sequence_recorded'
ORDER BY stream_id, stream_version
"""

_COMPONENT_QUERY = """
SELECT c.component_id, c.surface, c.current_revision AS revision,
       c.current_state AS state, l.artifact_id, l.observed_content_hash
FROM cognitive_os.learned_components c
LEFT JOIN cognitive_os.learned_artifacts l ON l.lineage_id = c.artifact_lineage_id
"""


async def load_correction_evidence(
    connection: Any,
    *,
    seals: Sequence[SealSource],
    seal_payloads: Mapping[UUID, bytes],
    inherited: Sequence[InheritedPair] = (),
    selection_stop: StopRecord | None = None,
    surface: str = CORRECTION_SURFACE,
) -> CorrectionEvidence:
    """Read every input once, over one open connection. Opens nothing of its own.

    The sealed feature-set bytes arrive already fetched, rather than this function reaching
    for an Artifact Store: the store opens its own connection per read, and a loader that
    both holds a connection and asks for more deadlocks against a single-connection pool.
    Taking the bytes as an argument also means every check can be exercised without one.
    """
    import json

    from sqlalchemy import text as sql

    from cognitive_os.learning.correction_features import SealedFeatureRecordSet

    observations = tuple(
        ObservedCorrection(
            observation_id=row.observation_id,
            source_task_id=row.source_task_id,
            source_run_id=row.source_run_id,
            source_kind=row.source_kind,
            provenance_class=row.provenance_class,
            status=row.status,
            evaluation_eligible=bool(row.evaluation_eligible),
            campaign_manifest_hash=row.manifest_hash,
            recorded_at=row.recorded_at,
        )
        for row in (await connection.execute(sql(_OBSERVATION_QUERY), {"surface": surface})).all()
    )

    resolved: list[SealedPartition] = []
    # A discovered seal that the evidence also names is one seal, not two: the declared entry
    # wins, because only it carries an independently recorded hash to check against.
    declared_ids = {source.artifact_id for source in seals if source.declared}
    for source in seals:
        if not source.declared and source.artifact_id in declared_ids:
            continue
        record_set = SealedFeatureRecordSet.model_validate_json(seal_payloads[source.artifact_id])
        resolved.append(
            SealedPartition(
                partition=source.partition,
                campaign_manifest_hash=source.campaign_manifest_hash,
                feature_set_hash=source.feature_set_hash,
                sealed_at=source.sealed_at,
                artifact_id=source.artifact_id,
                candidate_ids=frozenset(item.candidate_id for item in record_set.records),
                task_ids=frozenset(item.task_id for item in record_set.records),
                groups=frozenset(item.repository_group for item in record_set.records),
                bytes_reproduce_the_seal=record_set.content_hash == source.feature_set_hash,
                declared=source.declared,
            )
        )

    lineage = tuple(
        LineageRow(
            lineage_id=row.lineage_id,
            artifact_id=row.artifact_id,
            role=row.role,
            declared_content_hash=row.declared_content_hash,
            observed_content_hash=row.observed_content_hash,
            bytes_present=bool(row.bytes_present),
        )
        for row in (await connection.execute(sql(_LINEAGE_QUERY))).all()
    )

    receipts: list[SequenceReceipt] = []
    for row in (await connection.execute(sql(_RECEIPT_QUERY))).all():
        body = row.payload_json if isinstance(row.payload_json, dict) else json.loads(row[2])
        receipts.append(
            SequenceReceipt(
                campaign_id=row.stream_id,
                stream_version=int(row.stream_version),
                task_id=UUID(str(body["task_id"])),
                campaign_manifest_hash=str(body["campaign_manifest_hash"]),
                attempted_order=tuple(UUID(str(item)) for item in body.get("attempted_order", ())),
                intentionally_unattempted=tuple(
                    UUID(str(item)) for item in body.get("intentionally_unattempted", ())
                ),
            )
        )

    components = tuple(
        ActiveComponent(
            component_id=row.component_id,
            surface=row.surface,
            revision=int(row.revision),
            state=row.state,
            artifact_id=row.artifact_id,
            artifact_content_hash=row.observed_content_hash,
        )
        for row in (await connection.execute(sql(_COMPONENT_QUERY))).all()
    )

    return CorrectionEvidence(
        observations=observations,
        seals=tuple(resolved),
        lineage=lineage,
        receipts=tuple(receipts),
        components=components,
        inherited=tuple(inherited),
        selection_stop=selection_stop,
    )


#: Exported for the operator command, which needs the field order to build its own payload.
__all__ = [
    "CORRECTION_SURFACE",
    "ActiveComponent",
    "CorrectionEvidence",
    "InheritedPair",
    "LineageRow",
    "ObservedCorrection",
    "SealSource",
    "SealedPartition",
    "SequenceReceipt",
    "StopRecord",
    "correction_checks",
    "correction_counts",
    "load_correction_evidence",
]
