"""The in-memory reference bound to the shared repository contract."""

from __future__ import annotations

import pytest

from cognitive_os.application.ports.learned_evidence import LearnedEvidenceRepositoryPort
from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.domain.learned_evidence import LearnedComponentRevisionRecord
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)

from . import fixtures as fx
from .repository_contract import LearnedRepositoryContract, revision


def _first_revision() -> LearnedComponentRevisionRecord:
    return revision(number=1, state_after=LearnedComponentState.REGISTERED)


class TestInMemoryLearnedEvidenceRepository(LearnedRepositoryContract):
    async def make_repository(self) -> LearnedEvidenceRepositoryPort:
        return InMemoryLearnedEvidenceRepository()

    async def corrupt_projection(
        self, repository: LearnedEvidenceRepositoryPort, component_id: str
    ) -> None:
        assert isinstance(repository, InMemoryLearnedEvidenceRepository)
        row = repository._projection[component_id]  # deliberate: simulating a bug
        repository._projection[component_id] = row.model_construct(
            **{**row.model_dump(), "current_state": LearnedComponentState.ACTIVE}
        )

    @pytest.mark.asyncio
    async def test_the_snapshot_is_stable_and_order_independent(self) -> None:
        repository = InMemoryLearnedEvidenceRepository()
        assert repository.snapshot() == ()
        await repository.register_component(
            revision=_first_revision(), descriptor_version=fx.descriptor().version
        )
        assert repository.snapshot() == ((fx.INERT.component_id, 1, "registered"),)

    @pytest.mark.asyncio
    async def test_counts_show_a_retry_appended_nothing(self) -> None:
        repository = InMemoryLearnedEvidenceRepository()
        await repository.register_component(
            revision=_first_revision(), descriptor_version=fx.descriptor().version
        )
        await repository.register_component(
            revision=_first_revision(), descriptor_version=fx.descriptor().version
        )
        assert repository.counts()["revisions"] == 1

    @pytest.mark.asyncio
    async def test_history_missing_a_revision_is_reported_rather_than_smoothed_over(
        self,
    ) -> None:
        """Replay must notice a hole, not renumber around it."""
        repository = InMemoryLearnedEvidenceRepository()
        await repository.register_component(
            revision=_first_revision(), descriptor_version=fx.descriptor().version
        )
        repository._revisions[fx.INERT.component_id].clear()  # deliberate: simulating loss
        result = await repository.replay()
        assert not result.projection_matches
        assert any("cannot account for" in item for item in result.failures)
