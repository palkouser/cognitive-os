"""Deterministic, immutable dataset selection.

A dataset snapshot answers one question precisely: which observations were used, split
which way, under which feature schema. Everything about it is derived — the same inputs
produce the same manifests, the same artifact hashes and the same dataset hash — so a
comparison run months apart is against the same corpus or it is against a different one
that says so.

Two boundaries are structural rather than procedural:

* **manifests live in the Artifact Store, never in a table column.** They grow with the
  corpus, and a manifest inside JSONB invites putting the example bodies in it. Here they
  hold observation IDs and source hashes, so a sensitive outcome is never copied into the
  learning plane's storage;
* **a training snapshot cannot contain a real governed run.** Enforced by
  `LearnedDatasetRecord`, again by a database CHECK, and once more by the selection here
  refusing to put an ineligible observation in the candidate set. Contamination would not
  fail anything; it would only make every later distribution comparison mean less than it
  claims.

See ADR 0086.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID, uuid5

from pydantic import Field

from cognitive_os.application.ports.learned_evidence import LearnedEvidenceRepositoryPort
from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, utc_now
from cognitive_os.domain.learned import CorpusRole, ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    LearnedArtifactRole,
    LearnedDatasetRecord,
    LearnedExampleManifest,
    LearnedObservationRecord,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
    LearnedSplitManifest,
    ObservationStatus,
)
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore

#: Fixed forever: changing it would give an identical selection a second dataset identity.
DATASET_NAMESPACE = UUID("8a4f0b62-1d37-5c98-b0e4-6f2a95d71c48")

MANIFEST_MEDIA_TYPE = "application/json"

#: The one split policy Sprint 21C1 ships. Named in the manifest rather than assumed,
#: because a split whose rule is not recorded cannot be reproduced, and a comparison
#: against an unreproducible split measures nothing.
DEFAULT_SPLIT_POLICY = "group-aware-by-source-hash"

#: How the default policy divides a corpus. Deterministic in the observation ID, so the
#: same member set always lands the same way and re-running never reshuffles a split.
DEFAULT_HOLDOUT_FRACTION = 4  # one in four


def _eligible(
    observations: Sequence[LearnedObservationRecord], corpus_role: CorpusRole
) -> tuple[LearnedObservationRecord, ...]:
    """Accepted observations, minus real governed runs when the corpus is for training."""
    selected = [item for item in observations if item.status is ObservationStatus.ACCEPTED]
    if corpus_role is CorpusRole.TRAINING:
        selected = [item for item in selected if item.training_eligible]
    return tuple(sorted(selected, key=lambda item: str(item.observation_id)))


def _split(members: Sequence[LearnedObservationRecord]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Assign each member to `train` or `holdout` by a stable function of its identity.

    Deterministic rather than random: a seeded shuffle is reproducible only while the
    seed and the library's algorithm both hold still, and neither is recorded anywhere a
    future reader would look.
    """
    train: list[str] = []
    holdout: list[str] = []
    for item in members:
        target = holdout if item.observation_id.int % DEFAULT_HOLDOUT_FRACTION == 0 else train
        target.append(str(item.observation_id))
    return (("holdout", tuple(holdout)), ("train", tuple(train)))


def members_digest(members: Sequence[tuple[str, str]]) -> str:
    """A stable digest of exactly who is in the dataset and what they said."""
    joined = "\n".join(
        f"{observation_id}:{payload_hash}" for observation_id, payload_hash in sorted(members)
    )
    return sha256(joined.encode()).hexdigest()


def split_assignment_digest(splits: Sequence[tuple[str, Sequence[str]]]) -> str:
    """A stable digest of who landed in which split, not merely of who is present.

    S21D2-020. `dataset_id_for` hashed the split *policy name* alongside the members, which
    is enough while one policy produces one assignment from one member set. Explicit mode
    breaks that assumption: two D2 partitions can name the same observations and divide them
    differently, and under the old identity they would collide onto one dataset ID — so the
    second build would return the first one's stored snapshot and every later comparison
    would silently use the wrong split.
    """
    joined = "\n".join(
        f"{name}:{','.join(sorted(members))}"
        for name, members in sorted(splits, key=lambda x: x[0])
    )
    return sha256(joined.encode()).hexdigest()


def dataset_id_for(
    *,
    surface: str,
    corpus_role: CorpusRole,
    revision: int,
    split_policy: str,
    members: Sequence[tuple[str, str]],
    assignment_digest: str | None = None,
    feature_schema_hash: str | None = None,
    selection_partition_digest: str | None = None,
) -> UUID:
    """Identity derived from everything that makes one dataset different from another.

    Membership alone is not enough: the same observations split a different way are a
    different corpus for every purpose that matters, and giving the two one identity
    would let a later comparison silently use the wrong one. Derived from the manifest
    *inputs* rather than the manifest hash, because the manifest embeds this ID.

    `assignment_digest` is absent for the default policy, which keeps every C1 dataset
    identity exactly what it was, and present in explicit mode where the assignment is an
    input rather than a function of the members.
    """
    if (feature_schema_hash is None) != (selection_partition_digest is None):
        raise ValueError(
            "feature schema and selection-partition digest must enter identity together"
        )
    if feature_schema_hash is not None and selection_partition_digest is not None:
        identity = (
            f"v3|{surface}|{corpus_role.value}|{feature_schema_hash}|{selection_partition_digest}"
        )
        return uuid5(DATASET_NAMESPACE, identity)
    identity = f"{surface}|{corpus_role.value}|{revision}|{split_policy}|{members_digest(members)}"
    if assignment_digest is not None:
        identity = f"{identity}|{assignment_digest}"
    return uuid5(DATASET_NAMESPACE, identity)


#: The page the learned plane will serve. `maximum_page_size` is `Field(..., le=500)`, so it
#: cannot be raised by configuration and explicit selection has to page rather than trust one
#: listing to hold everything.
LISTING_PAGE_SIZE = 500

#: The two splits a D2 training dataset has. `train`/`holdout` is the C1 default policy's
#: naming and stays untouched; explicit mode fits and calibrates, which are different jobs.
EXPLICIT_SPLIT_POLICY = "explicit-partition-manifest"
EXPLICIT_SPLIT_POLICY_V3 = "explicit-partition-manifest-v3"


class ExplicitSelectionMemberV3(ImmutableContractModel):
    """One hash-complete member of a revision-3 explicit selection authority."""

    campaign_identity: NonEmptyStr
    partition: NonEmptyStr
    observation_id: NonEmptyStr
    group_id: NonEmptyStr
    feature_record_hash: Sha256Hex
    outcome_hash: Sha256Hex
    member_content_hash: Sha256Hex


class ExplicitSelectionManifestV3(LearnedSplitManifest):
    """Revision-3 selection data stored under the existing split-manifest lineage role."""

    selection_revision: int = Field(default=3, ge=3, le=3)
    surface: NonEmptyStr
    corpus_role: NonEmptyStr
    feature_schema_hash: Sha256Hex
    campaign_identity: NonEmptyStr
    partition: NonEmptyStr
    selection_partition_digest: Sha256Hex
    selected_members: tuple[ExplicitSelectionMemberV3, ...] = Field(min_length=1)


def explicit_selection_partition_digest(
    *,
    campaign_identity: str,
    partition: str,
    members: Sequence[tuple[str, str]],
    groups: Mapping[str, str],
    splits: Mapping[str, Sequence[str]],
    feature_record_hashes: Mapping[str, str],
    outcome_hashes: Mapping[str, str],
    member_content_hashes: Mapping[str, str],
) -> str:
    """Hash exact selection membership and partition assignment, independent of input order."""
    lines = [f"campaign:{campaign_identity}", f"partition:{partition}"]
    for observation_id, payload_hash in sorted(members):
        lines.append(
            ":".join(
                (
                    "member",
                    observation_id,
                    payload_hash,
                    groups[observation_id],
                    feature_record_hashes[observation_id],
                    outcome_hashes[observation_id],
                    member_content_hashes[observation_id],
                )
            )
        )
    lines.extend(
        f"split:{name}:{','.join(sorted(observation_ids))}"
        for name, observation_ids in sorted(splits.items())
    )
    return sha256("\n".join(lines).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ExplicitSelection:
    """Exactly which observations a D2 partition contains, and exactly how they divide.

    S21D2-020. The C1 builder selects every accepted observation on a surface and splits it
    by `observation_id % 4`. Neither is usable for D2: the members are chosen by a sealed
    campaign manifest rather than by whatever the store happens to hold, and the split has to
    respect task groups so a template cannot be memorised in `fit` and scored in
    `calibration`.
    """

    partition: str
    #: `(observation_id, expected_source_payload_hash)`. The hash is checked, not trusted:
    #: a member whose payload changed is a different observation wearing the same ID.
    members: tuple[tuple[str, str], ...]
    #: `observation_id -> group`. Whole groups move together or the split is refused.
    groups: Mapping[str, str]
    #: `split_name -> observation_ids`. The union must equal the members exactly.
    splits: Mapping[str, tuple[str, ...]]
    allowed_provenance: ProvenanceClass
    identity_revision: int = 2
    campaign_identity: str | None = None
    feature_record_hashes: Mapping[str, str] | None = None
    outcome_hashes: Mapping[str, str] | None = None
    member_content_hashes: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        ids = [observation_id for observation_id, _ in self.members]
        if not ids:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.NOT_FOUND,
                f"partition {self.partition!r} selects no observation",
            )
        if len(set(ids)) != len(ids):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"partition {self.partition!r} names an observation twice",
            )
        missing_groups = sorted(set(ids) - set(self.groups))
        if missing_groups:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"partition {self.partition!r} has members with no group: {missing_groups}",
            )
        assigned: list[str] = [item for members in self.splits.values() for item in members]
        if len(set(assigned)) != len(assigned):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"partition {self.partition!r} assigns an observation to two splits",
            )
        if set(assigned) != set(ids):
            extra = sorted(set(assigned) - set(ids))
            absent = sorted(set(ids) - set(assigned))
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"partition {self.partition!r} split union does not equal its members; "
                f"unknown={extra} unassigned={absent}",
            )
        if any(not members for members in self.splits.values()):
            empty = sorted(name for name, members in self.splits.items() if not members)
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"partition {self.partition!r} has empty splits: {empty}",
            )
        owner: dict[str, str] = {}
        for name, members in sorted(self.splits.items()):
            for observation_id in members:
                group = self.groups[observation_id]
                if owner.setdefault(group, name) != name:
                    raise LearnedRepositoryError(
                        LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                        f"group {group!r} crosses splits {owner[group]!r} and {name!r}",
                    )
        if self.identity_revision not in {2, 3}:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"unsupported explicit selection identity revision {self.identity_revision}",
            )
        authorities = (
            self.campaign_identity,
            self.feature_record_hashes,
            self.outcome_hashes,
            self.member_content_hashes,
        )
        if self.identity_revision == 2 and any(item is not None for item in authorities):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "revision-3 selection authorities require identity_revision=3",
            )
        if self.identity_revision == 3:
            _, feature_hashes, outcome_hashes, member_hashes = self._v3_authorities()
            for label, mapping in (
                ("feature record", feature_hashes),
                ("outcome", outcome_hashes),
                ("member content", member_hashes),
            ):
                if set(mapping) != set(ids):
                    raise LearnedRepositoryError(
                        LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                        f"revision-3 {label} hashes do not match selected members",
                    )

    @property
    def assignment_digest(self) -> str:
        return split_assignment_digest([(name, list(m)) for name, m in self.splits.items()])

    @property
    def split_tuples(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple((name, tuple(members)) for name, members in sorted(self.splits.items()))

    def _v3_authorities(
        self,
    ) -> tuple[str, Mapping[str, str], Mapping[str, str], Mapping[str, str]]:
        if (
            self.identity_revision != 3
            or self.campaign_identity is None
            or self.feature_record_hashes is None
            or self.outcome_hashes is None
            or self.member_content_hashes is None
        ):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "revision-3 selection requires campaign, feature, outcome, and member hashes",
            )
        return (
            self.campaign_identity,
            self.feature_record_hashes,
            self.outcome_hashes,
            self.member_content_hashes,
        )

    @property
    def selection_partition_digest(self) -> str:
        if self.identity_revision != 3:
            raise ValueError("the D2 selection has no revision-3 partition digest")
        campaign_identity, feature_hashes, outcome_hashes, member_hashes = self._v3_authorities()
        return explicit_selection_partition_digest(
            campaign_identity=campaign_identity,
            partition=self.partition,
            members=self.members,
            groups=self.groups,
            splits=self.splits,
            feature_record_hashes=feature_hashes,
            outcome_hashes=outcome_hashes,
            member_content_hashes=member_hashes,
        )

    @property
    def selected_members_v3(self) -> tuple[ExplicitSelectionMemberV3, ...]:
        if self.identity_revision != 3:
            raise ValueError("the D2 selection has no revision-3 member manifest")
        campaign_identity, feature_hashes, outcome_hashes, member_hashes = self._v3_authorities()
        return tuple(
            ExplicitSelectionMemberV3(
                campaign_identity=campaign_identity,
                partition=self.partition,
                observation_id=observation_id,
                group_id=self.groups[observation_id],
                feature_record_hash=feature_hashes[observation_id],
                outcome_hash=outcome_hashes[observation_id],
                member_content_hash=member_hashes[observation_id],
            )
            for observation_id, _ in sorted(self.members)
        )


class LearnedDatasetBuilder:
    """Builds immutable evaluation and training snapshots from accepted observations."""

    def __init__(
        self,
        repository: LearnedEvidenceRepositoryPort,
        artifacts: LearnedArtifactStore,
        *,
        actor: str = "learned-dataset-builder",
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._repository = repository
        self._artifacts = artifacts
        self._actor = actor
        self._clock = clock

    async def build(
        self,
        *,
        surface: str,
        corpus_role: CorpusRole,
        feature_schema_hash: str,
        sensitivity: str = "internal",
        revision: int = 1,
        split_policy: str = DEFAULT_SPLIT_POLICY,
        selection: ExplicitSelection | None = None,
    ) -> LearnedDatasetRecord:
        """Select, split, store both manifests, and append the snapshot.

        Raises rather than returning an empty dataset: a snapshot selecting nothing is
        not a small dataset, it is a selection step that silently did not happen.

        With `selection`, membership and split assignment are inputs from a sealed campaign
        manifest instead of being derived from whatever the store holds. Without it, the C1
        behaviour is untouched, down to the dataset identity.
        """
        assignment_digest: str | None = None
        selection_digest: str | None = None
        if selection is None:
            observations = await self._repository.list_observations(
                surface=surface, status=ObservationStatus.ACCEPTED, limit=LISTING_PAGE_SIZE
            )
            members = _eligible(observations, corpus_role)
            splits = _split(members)
        else:
            split_policy = (
                EXPLICIT_SPLIT_POLICY_V3
                if selection.identity_revision == 3
                else EXPLICIT_SPLIT_POLICY
            )
            members = await self._resolve_explicit(surface, corpus_role, selection)
            splits = selection.split_tuples
            if selection.identity_revision == 3:
                selection_digest = selection.selection_partition_digest
            else:
                assignment_digest = selection.assignment_digest
        if not members:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.NOT_FOUND,
                f"no observation on {surface!r} is eligible for a {corpus_role.value} dataset",
            )

        created_at = self._clock()
        member_pairs = tuple(
            (str(item.observation_id), item.source_payload_hash) for item in members
        )
        dataset_id = dataset_id_for(
            surface=surface,
            corpus_role=corpus_role,
            revision=revision,
            split_policy=split_policy,
            members=member_pairs,
            assignment_digest=assignment_digest,
            feature_schema_hash=feature_schema_hash if selection_digest is not None else None,
            selection_partition_digest=selection_digest,
        )
        # Rebuilding an identical selection returns what is already stored. Not merely an
        # optimisation: the manifests would be re-stored under fresh artifact IDs, and
        # the lineage rows — whose identity is derived from the dataset — would then be
        # asked to change, which an append-only ledger rightly refuses.
        existing = await self._repository.get_dataset(dataset_id)
        if existing is not None:
            expected = (
                existing.revision == revision
                and existing.surface == surface
                and existing.corpus_role is corpus_role
                and existing.feature_schema_hash == feature_schema_hash
            )
            if not expected:
                raise LearnedRepositoryError(
                    LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                    "the existing dataset identity resolves to another revision, surface, role, "
                    "or feature schema",
                )
            return existing

        example_manifest = LearnedExampleManifest(
            dataset_id=dataset_id,
            revision=revision,
            surface=surface,
            corpus_role=corpus_role.value,
            members=member_pairs,
            created_at=created_at,
        )
        if selection is not None and selection.identity_revision == 3:
            campaign_identity, _, _, _ = selection._v3_authorities()
            split_manifest: LearnedSplitManifest = ExplicitSelectionManifestV3(
                dataset_id=dataset_id,
                revision=revision,
                policy=split_policy,
                splits=splits,
                created_at=created_at,
                surface=surface,
                corpus_role=corpus_role.value,
                feature_schema_hash=feature_schema_hash,
                campaign_identity=campaign_identity,
                partition=selection.partition,
                selection_partition_digest=selection.selection_partition_digest,
                selected_members=selection.selected_members_v3,
            )
        else:
            split_manifest = LearnedSplitManifest(
                dataset_id=dataset_id,
                revision=revision,
                policy=split_policy,
                splits=splits,
                created_at=created_at,
            )

        example_reference = await self._artifacts.store(
            example_manifest.canonical_json().encode(), media_type=MANIFEST_MEDIA_TYPE
        )
        split_reference = await self._artifacts.store(
            split_manifest.canonical_json().encode(), media_type=MANIFEST_MEDIA_TYPE
        )
        for reference, role in (
            (example_reference, LearnedArtifactRole.EXAMPLE_MANIFEST),
            (split_reference, LearnedArtifactRole.SPLIT_MANIFEST),
        ):
            lineage = await self._artifacts.build_lineage(
                lineage_id=uuid5(DATASET_NAMESPACE, f"{dataset_id}|{role.value}"),
                artifact_id=reference.artifact_id,
                role=role,
                declared_format="json",
                dataset_id=dataset_id,
                verified_by=self._actor,
            )
            await self._repository.record_artifact_lineage(lineage)

        counts: dict[str, int] = {}
        for item in members:
            counts[item.provenance_class.value] = counts.get(item.provenance_class.value, 0) + 1
        if corpus_role is CorpusRole.TRAINING and ProvenanceClass.REAL_GOVERNED_RUN.value in counts:
            # Unreachable while `_eligible` holds. Kept because the day it becomes
            # reachable is the day the selection filter was quietly changed.
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "a training dataset cannot contain real-governed-run evidence",
            )

        record = LearnedDatasetRecord(
            dataset_id=dataset_id,
            revision=revision,
            surface=surface,
            corpus_role=corpus_role,
            feature_schema_hash=feature_schema_hash,
            split_manifest_artifact_id=split_reference.artifact_id,
            split_manifest_hash=split_manifest.content_hash,
            example_manifest_artifact_id=example_reference.artifact_id,
            example_manifest_hash=example_manifest.content_hash,
            provenance_counts=counts,
            observation_count=len(members),
            usage_rights_verified=all(item.usage_rights_verified for item in members),
            sensitivity=sensitivity,
            created_at=created_at,
        )
        return await self._repository.record_dataset(record)

    async def _resolve_explicit(
        self, surface: str, corpus_role: CorpusRole, selection: ExplicitSelection
    ) -> tuple[LearnedObservationRecord, ...]:
        """Resolve exactly the named observations, paging until every one is accounted for.

        Every refusal here is a refusal to build a snapshot that would look complete: a
        missing member, a changed payload, the wrong provenance, evidence from another
        surface. The alternative is a dataset that is quietly smaller or quietly different
        from the manifest that authorised it.
        """
        wanted = dict(selection.members)
        found: dict[str, LearnedObservationRecord] = {}
        offset = 0
        while len(found) < len(wanted):
            page = await self._repository.list_observations(
                surface=surface,
                status=ObservationStatus.ACCEPTED,
                limit=LISTING_PAGE_SIZE,
                offset=offset,
            )
            if not page:
                break
            for item in page:
                key = str(item.observation_id)
                if key in wanted:
                    found[key] = item
            offset += len(page)
            if len(page) < LISTING_PAGE_SIZE:
                break

        absent = sorted(set(wanted) - set(found))
        if absent:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.NOT_FOUND,
                f"partition {selection.partition!r} names observations that are not accepted "
                f"on {surface!r}: {absent}",
            )

        for key, record in sorted(found.items()):
            if record.source_payload_hash != wanted[key]:
                raise LearnedRepositoryError(
                    LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                    f"observation {key} resolves to payload {record.source_payload_hash} "
                    f"but the manifest sealed {wanted[key]}",
                )
            if record.provenance_class is not selection.allowed_provenance:
                raise LearnedRepositoryError(
                    LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                    f"partition {selection.partition!r} accepts only "
                    f"{selection.allowed_provenance.value} evidence, but observation {key} is "
                    f"{record.provenance_class.value}",
                )
            if corpus_role is CorpusRole.TRAINING and not record.training_eligible:
                raise LearnedRepositoryError(
                    LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                    f"observation {key} is not training-eligible and cannot enter a training "
                    f"snapshot",
                )

        # Manifest order, not store order: the members are what the manifest sealed.
        return tuple(found[observation_id] for observation_id, _ in selection.members)
