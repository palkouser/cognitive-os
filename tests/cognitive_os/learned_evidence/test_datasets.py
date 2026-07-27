"""S21C1-042: immutable dataset selection, and what must change its hash.

A dataset snapshot is only worth having if it is reproducible. The tests below fix the
two halves of that: identical inputs must produce an identical hash, and any change to
membership or split must produce a different one. A builder that satisfied only the first
would let two different corpora share an identity, which is the failure that makes an old
comparison quietly untrustworthy rather than loudly wrong.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4, uuid5

import pytest
import pytest_asyncio
from sqlalchemy import text

from cognitive_os.application.services.learned_datasets import (
    DEFAULT_SPLIT_POLICY,
    LearnedDatasetBuilder,
    dataset_id_for,
)
from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.application.services.learned_intake import LearnedObservationIntake
from cognitive_os.domain.learned import CorpusRole, ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    GovernedOutcomeReference,
    LearnedRepositoryError,
    ObservationAttribution,
)
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import PostgresArtifactRepository
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

from . import fixtures as fx

pytestmark = [pytest.mark.integration, pytest.mark.postgres]

CORRELATION = uuid4()
SCHEMA_HASH = "5" * 64


@pytest_asyncio.fixture
async def builder() -> AsyncIterator[tuple[LearnedDatasetBuilder, LearnedObservationIntake]]:
    """A builder over the real Artifact Store and an in-memory learned repository.

    The Artifact Store must be real: the point of the manifests is that they are stored
    as content-addressed bytes, and a fake store would prove nothing about that.
    """
    admin_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not admin_url or not root:
        pytest.skip("PostgreSQL integration URLs or artifact root are not configured")
    engine = create_postgres_engine(admin_url, pool_size=2, max_overflow=2)
    async with engine.connect() as connection:
        name = await connection.scalar(text("SELECT current_database()"))
        if not str(name).endswith("_test"):
            pytest.fail(f"refusing learned dataset tests against database: {name}")
    artifacts = LearnedArtifactStore(
        ArtifactService(ContentAddressedFilesystem(Path(root)), PostgresArtifactRepository(engine))
    )
    repository = InMemoryLearnedEvidenceRepository()
    service = LearnedEvidenceService(
        repository,
        artifacts=artifacts,
        events=LearnedEventService(MemoryEventStore()),
        clock=lambda: fx.FIXTURE_NOW,
    )
    try:
        yield (
            LearnedDatasetBuilder(repository, artifacts, clock=lambda: fx.FIXTURE_NOW),
            LearnedObservationIntake(service, clock=lambda: fx.FIXTURE_NOW),
        )
    finally:
        await engine.dispose()


def reference(index: int, **overrides: object) -> GovernedOutcomeReference:
    """One governed outcome per index, with a distinct source identity and payload."""
    fields: dict[str, object] = {
        "surface": fx.surface(),
        "source_kind": "governed_task_run",
        "source_run_id": uuid5(fx.FIXTURE_NAMESPACE, f"run-{index}"),
        "source_payload_hash": f"{index:064x}",
        "provenance_class": ProvenanceClass.SELF_PLAY,
        "attribution": ObservationAttribution.DIRECT,
        "usage_rights_verified": True,
        "sensitivity": "internal",
        "verifier_status": "passed",
        "verifier_evidence_hash": "b" * 64,
    }
    fields.update(overrides)
    return GovernedOutcomeReference(**fields)  # type: ignore[arg-type]


async def seed(intake: LearnedObservationIntake, count: int, **overrides: object) -> None:
    for index in range(count):
        await intake.offer(reference(index, **overrides), correlation_id=CORRELATION)


class TestSelectionIsDeterministic:
    @pytest.mark.asyncio
    async def test_the_same_inputs_produce_the_same_dataset_hash(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        maker, intake = builder
        await seed(intake, 8)
        first = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        second = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        assert first.dataset_id == second.dataset_id
        assert first.content_hash == second.content_hash
        assert first.example_manifest_hash == second.example_manifest_hash
        assert first.split_manifest_hash == second.split_manifest_hash

    @pytest.mark.asyncio
    async def test_different_membership_changes_the_hash(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        """Two corpora that are not the same must never share an identity."""
        maker, intake = builder
        await seed(intake, 6)
        before = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        await intake.offer(reference(99), correlation_id=CORRELATION)
        after = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        assert after.example_manifest_hash != before.example_manifest_hash
        assert after.dataset_id != before.dataset_id
        assert after.observation_count == before.observation_count + 1

    @pytest.mark.asyncio
    async def test_a_different_split_policy_changes_the_split_hash(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        maker, intake = builder
        await seed(intake, 6)
        default = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        renamed = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
            split_policy="leave-one-domain-out",
        )
        assert default.split_manifest_hash != renamed.split_manifest_hash
        assert default.dataset_id != renamed.dataset_id, (
            "the same members split a different way are a different corpus"
        )
        assert DEFAULT_SPLIT_POLICY != "leave-one-domain-out"

    @pytest.mark.asyncio
    async def test_the_dataset_identity_is_derived_from_membership(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        maker, intake = builder
        await seed(intake, 4)
        record = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        members = tuple(
            (str(item.observation_id), item.source_payload_hash)
            for item in await maker._repository.list_observations(surface=fx.surface())
        )
        assert record.dataset_id == dataset_id_for(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            revision=1,
            split_policy=DEFAULT_SPLIT_POLICY,
            members=members,
        )


class TestTheTrainingExclusionHolds:
    @pytest.mark.asyncio
    async def test_real_runs_can_form_an_evaluation_snapshot(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        maker, intake = builder
        await seed(intake, 4, provenance_class=ProvenanceClass.REAL_GOVERNED_RUN)
        record = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        assert record.provenance_counts == {"real_governed_run": 4}
        assert record.observation_count == 4

    @pytest.mark.asyncio
    async def test_real_runs_cannot_form_a_training_snapshot(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        """They are filtered out of the candidate set, so the build finds nothing."""
        maker, intake = builder
        await seed(intake, 4, provenance_class=ProvenanceClass.REAL_GOVERNED_RUN)
        with pytest.raises(LearnedRepositoryError, match="eligible for a training dataset"):
            await maker.build(
                surface=fx.surface(),
                corpus_role=CorpusRole.TRAINING,
                feature_schema_hash=SCHEMA_HASH,
            )

    @pytest.mark.asyncio
    async def test_a_mixed_corpus_yields_a_training_snapshot_without_the_real_runs(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        maker, intake = builder
        await seed(intake, 4)
        for index in range(4, 7):
            await intake.offer(
                reference(index, provenance_class=ProvenanceClass.REAL_GOVERNED_RUN),
                correlation_id=CORRELATION,
            )
        training = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=SCHEMA_HASH,
        )
        evaluation = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        assert "real_governed_run" not in training.provenance_counts
        assert training.observation_count == 4
        assert evaluation.observation_count == 7


class TestManifestsStayInTheArtifactStore:
    @pytest.mark.asyncio
    async def test_the_snapshot_holds_references_and_no_example_bodies(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        maker, intake = builder
        await seed(intake, 5)
        record = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        dumped = record.model_dump(mode="json")
        assert record.example_manifest_artifact_id is not None
        assert record.split_manifest_artifact_id is not None
        assert "members" not in dumped
        assert "examples" not in dumped
        assert "splits" not in dumped

    @pytest.mark.asyncio
    async def test_both_manifests_are_recorded_as_verified_lineage(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        maker, intake = builder
        await seed(intake, 5)
        record = await maker.build(
            surface=fx.surface(),
            corpus_role=CorpusRole.EVALUATION,
            feature_schema_hash=SCHEMA_HASH,
        )
        repository = maker._repository
        stored = await repository.get_dataset(record.dataset_id)
        assert stored is not None and stored.content_hash == record.content_hash

    @pytest.mark.asyncio
    async def test_an_empty_selection_is_refused_rather_than_returned(
        self, builder: tuple[LearnedDatasetBuilder, LearnedObservationIntake]
    ) -> None:
        """A snapshot selecting nothing is a selection step that did not happen."""
        maker, _ = builder
        with pytest.raises(LearnedRepositoryError, match="no observation"):
            await maker.build(
                surface="surface.with.nothing",
                corpus_role=CorpusRole.EVALUATION,
                feature_schema_hash=SCHEMA_HASH,
            )
