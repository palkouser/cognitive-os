"""S21D2-020: a dataset whose membership and split come from a sealed manifest.

The C1 builder answers "everything accepted on this surface, split by observation ID modulo
four". D2 cannot use either half. Membership is decided by a sealed campaign manifest, not by
whatever the store happens to hold when the build runs; and the split has to respect task
groups, because a template memorised in `fit` and scored in `calibration` is a corpus that
grades its own homework.

Every test here is a refusal or an identity check. The identity checks matter most: the C1
`dataset_id_for` hashed the split *policy name* alongside the members, so two D2 partitions
naming the same observations with different assignments would have collided onto one dataset
ID — and the second build would have returned the first one's snapshot without saying so.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from cognitive_os.application.services.learned_datasets import (
    DEFAULT_SPLIT_POLICY,
    EXPLICIT_SPLIT_POLICY,
    LISTING_PAGE_SIZE,
    ExplicitSelection,
    LearnedDatasetBuilder,
    dataset_id_for,
    split_assignment_digest,
)
from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.learned import CorpusRole, ProvenanceClass
from cognitive_os.domain.learned_evidence import LearnedRepositoryError
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)

from . import fixtures as fx

SCHEMA_HASH = "5" * 64


class _MemoryArtifactService:
    """The real content-addressed filesystem, without the PostgreSQL metadata plane.

    The bytes are stored for real — the manifests exist to be content-addressed, and a stub
    that only remembered a hash would prove nothing about that. Only the metadata row, which
    needs PostgreSQL, is replaced.
    """

    def __init__(self, root: Path) -> None:
        self._files = ContentAddressedFilesystem(root)
        self._refs: dict[UUID, ArtifactRef] = {}

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: object = None
    ) -> ArtifactRef:
        del source_event_id
        blob = self._files.put_bytes(data)
        reference = ArtifactRef(
            artifact_id=uuid4(),
            media_type=media_type,
            content_hash=blob.content_hash,
            size_bytes=blob.size_bytes,
            storage_key=blob.storage_key,
            created_at=fx.FIXTURE_NOW,
        )
        self._refs[reference.artifact_id] = reference
        return reference

    async def describe(self, artifact_id: UUID) -> ArtifactRef | None:
        return self._refs.get(artifact_id)

    async def verify(self, artifact_id: UUID) -> bool:
        reference = self._refs.get(artifact_id)
        if reference is None:
            return False
        return self._files.exists(reference.storage_key)


@pytest_asyncio.fixture
async def builder(tmp_path: Path) -> AsyncIterator[tuple[LearnedDatasetBuilder, object]]:
    repository = InMemoryLearnedEvidenceRepository()
    store = LearnedArtifactStore(_MemoryArtifactService(tmp_path / "artifacts"))
    yield LearnedDatasetBuilder(repository, store), repository


async def _seed(repository: object, count: int, **overrides: object) -> list[object]:
    """`count` accepted self-play observations, recorded in the store."""
    records = []
    for index in range(count):
        record = fx.observation(
            source_payload_hash=f"{index:064x}",
            idempotency_key=f"observation-{index}",
            **overrides,
        )
        await repository.record_observation(record)  # type: ignore[attr-defined]
        records.append(record)
    return records


def _selection(records: list[object], *, fit: int, **overrides: object) -> ExplicitSelection:
    ids = [str(item.observation_id) for item in records]  # type: ignore[attr-defined]
    fields: dict[str, object] = {
        "partition": "training",
        "members": tuple(
            (str(item.observation_id), item.source_payload_hash)  # type: ignore[attr-defined]
            for item in records
        ),
        # One group per observation unless a test says otherwise.
        "groups": {observation_id: f"group-{index}" for index, observation_id in enumerate(ids)},
        "splits": {"fit": tuple(ids[:fit]), "calibration": tuple(ids[fit:])},
        "allowed_provenance": ProvenanceClass.SELF_PLAY,
    }
    fields.update(overrides)
    return ExplicitSelection(**fields)  # type: ignore[arg-type]


class TestSplitAssignmentIsPartOfIdentity:
    def test_the_same_members_split_differently_get_different_identities(self) -> None:
        members = (("a", "1" * 64), ("b", "2" * 64), ("c", "3" * 64))
        left = split_assignment_digest([("fit", ["a", "b"]), ("calibration", ["c"])])
        right = split_assignment_digest([("fit", ["a"]), ("calibration", ["b", "c"])])

        assert left != right
        assert dataset_id_for(
            surface="s",
            corpus_role=CorpusRole.TRAINING,
            revision=1,
            split_policy=EXPLICIT_SPLIT_POLICY,
            members=members,
            assignment_digest=left,
        ) != dataset_id_for(
            surface="s",
            corpus_role=CorpusRole.TRAINING,
            revision=1,
            split_policy=EXPLICIT_SPLIT_POLICY,
            members=members,
            assignment_digest=right,
        )

    def test_the_digest_ignores_ordering_within_a_split(self) -> None:
        assert split_assignment_digest([("fit", ["b", "a"])]) == split_assignment_digest(
            [("fit", ["a", "b"])]
        )

    def test_the_c1_identity_is_unchanged_when_no_digest_is_given(self) -> None:
        """The default path must produce byte-identical identities to before this change."""
        members = (("a", "1" * 64),)

        assert dataset_id_for(
            surface="s",
            corpus_role=CorpusRole.TRAINING,
            revision=1,
            split_policy=DEFAULT_SPLIT_POLICY,
            members=members,
        ) == dataset_id_for(
            surface="s",
            corpus_role=CorpusRole.TRAINING,
            revision=1,
            split_policy=DEFAULT_SPLIT_POLICY,
            members=members,
            assignment_digest=None,
        )


class TestTheSelectionRefusesAnIncoherentPlan:
    def test_an_empty_partition_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="selects no observation"):
            ExplicitSelection(
                partition="training",
                members=(),
                groups={},
                splits={"fit": ()},
                allowed_provenance=ProvenanceClass.SELF_PLAY,
            )

    def test_a_duplicated_member_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="names an observation twice"):
            ExplicitSelection(
                partition="training",
                members=(("a", "1" * 64), ("a", "1" * 64)),
                groups={"a": "g"},
                splits={"fit": ("a",)},
                allowed_provenance=ProvenanceClass.SELF_PLAY,
            )

    def test_a_member_without_a_group_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="no group"):
            ExplicitSelection(
                partition="training",
                members=(("a", "1" * 64),),
                groups={},
                splits={"fit": ("a",)},
                allowed_provenance=ProvenanceClass.SELF_PLAY,
            )

    def test_an_unassigned_member_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="unassigned="):
            ExplicitSelection(
                partition="training",
                members=(("a", "1" * 64), ("b", "2" * 64)),
                groups={"a": "g1", "b": "g2"},
                splits={"fit": ("a",)},
                allowed_provenance=ProvenanceClass.SELF_PLAY,
            )

    def test_a_split_naming_an_unknown_observation_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="unknown="):
            ExplicitSelection(
                partition="training",
                members=(("a", "1" * 64),),
                groups={"a": "g1"},
                splits={"fit": ("a",), "calibration": ("z",)},
                allowed_provenance=ProvenanceClass.SELF_PLAY,
            )

    def test_an_observation_in_two_splits_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="two splits"):
            ExplicitSelection(
                partition="training",
                members=(("a", "1" * 64),),
                groups={"a": "g1"},
                splits={"fit": ("a",), "calibration": ("a",)},
                allowed_provenance=ProvenanceClass.SELF_PLAY,
            )

    def test_an_empty_split_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="empty splits"):
            ExplicitSelection(
                partition="training",
                members=(("a", "1" * 64),),
                groups={"a": "g1"},
                splits={"fit": ("a",), "calibration": ()},
                allowed_provenance=ProvenanceClass.SELF_PLAY,
            )

    def test_a_group_crossing_fit_and_calibration_is_refused(self) -> None:
        """The whole reason the split is group-aware rather than row-aware."""
        with pytest.raises(LearnedRepositoryError, match="crosses splits"):
            ExplicitSelection(
                partition="training",
                members=(("a", "1" * 64), ("b", "2" * 64)),
                groups={"a": "shared", "b": "shared"},
                splits={"fit": ("a",), "calibration": ("b",)},
                allowed_provenance=ProvenanceClass.SELF_PLAY,
            )


@pytest.mark.asyncio
class TestExplicitBuildResolvesExactlyWhatWasSealed:
    async def test_it_builds_a_snapshot_over_the_named_members(
        self, builder: tuple[LearnedDatasetBuilder, object]
    ) -> None:
        service, repository = builder
        records = await _seed(repository, 6)

        record = await service.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=SCHEMA_HASH,
            selection=_selection(records, fit=4),
        )

        assert record.observation_count == 6
        assert record.provenance_counts == {ProvenanceClass.SELF_PLAY.value: 6}

    async def test_two_assignments_over_the_same_members_are_two_datasets(
        self, builder: tuple[LearnedDatasetBuilder, object]
    ) -> None:
        """The stale-snapshot collision, stated as the behaviour that must not happen."""
        service, repository = builder
        records = await _seed(repository, 6)

        first = await service.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=SCHEMA_HASH,
            selection=_selection(records, fit=4),
        )
        second = await service.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=SCHEMA_HASH,
            selection=_selection(records, fit=3),
        )

        assert first.dataset_id != second.dataset_id
        assert first.split_manifest_hash != second.split_manifest_hash

    async def test_rebuilding_the_identical_selection_returns_the_same_snapshot(
        self, builder: tuple[LearnedDatasetBuilder, object]
    ) -> None:
        service, repository = builder
        records = await _seed(repository, 6)
        selection = _selection(records, fit=4)

        first = await service.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=SCHEMA_HASH,
            selection=selection,
        )
        second = await service.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=SCHEMA_HASH,
            selection=selection,
        )

        assert first.dataset_id == second.dataset_id

    async def test_a_member_that_is_not_accepted_is_refused(
        self, builder: tuple[LearnedDatasetBuilder, object]
    ) -> None:
        service, repository = builder
        records = await _seed(repository, 3)
        ids = [str(item.observation_id) for item in records]
        phantom = str(uuid4())
        selection = ExplicitSelection(
            partition="training",
            members=(
                *((str(item.observation_id), item.source_payload_hash) for item in records),
                (phantom, "f" * 64),
            ),
            groups={**{item: f"group-{i}" for i, item in enumerate(ids)}, phantom: "group-ghost"},
            splits={"fit": tuple(ids[:2]), "calibration": (*ids[2:], phantom)},
            allowed_provenance=ProvenanceClass.SELF_PLAY,
        )

        with pytest.raises(LearnedRepositoryError, match="not accepted"):
            await service.build(
                surface=fx.surface(),
                corpus_role=CorpusRole.TRAINING,
                feature_schema_hash=SCHEMA_HASH,
                selection=selection,
            )

    async def test_a_changed_payload_hash_is_refused(
        self, builder: tuple[LearnedDatasetBuilder, object]
    ) -> None:
        """A member whose payload moved is a different observation wearing the same ID."""
        service, repository = builder
        records = await _seed(repository, 3)
        members = tuple(
            (str(item.observation_id), "9" * 64 if index == 0 else item.source_payload_hash)
            for index, item in enumerate(records)
        )

        with pytest.raises(LearnedRepositoryError, match="but the manifest sealed"):
            await service.build(
                surface=fx.surface(),
                corpus_role=CorpusRole.TRAINING,
                feature_schema_hash=SCHEMA_HASH,
                selection=_selection(records, fit=2, members=members),
            )

    async def test_real_governed_evidence_cannot_enter_a_training_partition(
        self, builder: tuple[LearnedDatasetBuilder, object]
    ) -> None:
        """The negative membership rule, enforced at selection rather than after the fact."""
        service, repository = builder
        records = await _seed(repository, 3, provenance_class=ProvenanceClass.REAL_GOVERNED_RUN)

        with pytest.raises(LearnedRepositoryError, match="accepts only self_play"):
            await service.build(
                surface=fx.surface(),
                corpus_role=CorpusRole.TRAINING,
                feature_schema_hash=SCHEMA_HASH,
                selection=_selection(records, fit=2),
            )

    async def test_more_than_one_page_of_observations_resolves(
        self, builder: tuple[LearnedDatasetBuilder, object]
    ) -> None:
        """`maximum_page_size` is capped at 500 and cannot be raised, so paging is mandatory."""
        service, repository = builder
        records = await _seed(repository, LISTING_PAGE_SIZE + 20)

        record = await service.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=SCHEMA_HASH,
            selection=_selection(records, fit=LISTING_PAGE_SIZE),
        )

        assert record.observation_count == LISTING_PAGE_SIZE + 20


@pytest.mark.asyncio
async def test_the_default_path_still_builds_without_a_selection(
    builder: tuple[LearnedDatasetBuilder, object],
) -> None:
    """C1 behaviour, untouched: no selection means select everything and split by modulo."""
    service, repository = builder
    await _seed(repository, 8)

    record = await service.build(
        surface=fx.surface(),
        corpus_role=CorpusRole.TRAINING,
        feature_schema_hash=SCHEMA_HASH,
    )

    assert record.observation_count == 8
