"""Sprint 21.3: the SQL shape that keeps exact retrieval exact.

Sprint 9 guaranteed exhaustive vector search. Sprint 21.3 adds an approximate mode
beside it, and the guarantee is preserved structurally rather than by a flag: the exact
query compares the undimensioned column, which no pgvector index can serve, while the
approximate query casts to the indexed dimension. These tests assert that difference at
the level of generated SQL, because it is the whole reason the amendment is safe.

The integration suite asserts the resulting query *plans* against a live PostgreSQL —
that is what proves the index is reached. Here the concern is only that the two paths
cannot collapse into one.
"""

from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from cognitive_os.config.memory_config import MemoryConfiguration
from cognitive_os.domain.memory import (
    MemoryQuery,
    MemoryRetrievalMode,
    MemoryVectorQuery,
)
from cognitive_os.infrastructure.memory.postgres.repository import (
    DEFAULT_EF_SEARCH,
    PostgresMemoryRepository,
)
from cognitive_os.infrastructure.memory.postgres.tables import (
    APPROXIMATE_INDEX_DIMENSIONS,
    APPROXIMATE_INDEX_NAMES,
    approximate_index_name,
)
from cognitive_os.memory.repository import InMemoryMemoryRepository

DIMENSION = APPROXIMATE_INDEX_DIMENSIONS[0]


def query(mode: MemoryRetrievalMode, *, dimension: int = DIMENSION) -> MemoryQuery:
    return MemoryQuery(
        query_id=uuid4(),
        mode=mode,
        vector=MemoryVectorQuery(
            provider_id="deterministic-test",
            model_id="deterministic-v1",
            dimension=dimension,
            vector=tuple(0.25 for _ in range(dimension)),
        ),
    )


def rendered(repository: PostgresMemoryRepository, subject: MemoryQuery) -> str:
    expression = repository._vector_distance(subject)
    return str(
        expression.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def repository(*dimensions: int) -> PostgresMemoryRepository:
    # No connection is opened: only SQL construction is under test here.
    return PostgresMemoryRepository(None, approximate_dimensions=frozenset(dimensions))  # type: ignore[arg-type]


class TestDistanceExpressionShape:
    def test_exact_retrieval_compares_the_undimensioned_column(self) -> None:
        """No pgvector index exists on the bare column, so this cannot be indexed."""
        sql = rendered(repository(DIMENSION), query(MemoryRetrievalMode.VECTOR))
        assert "memory_embeddings.embedding <=>" in sql
        assert f"AS vector({DIMENSION})" not in sql

    def test_approximate_retrieval_casts_to_the_indexed_dimension(self) -> None:
        sql = rendered(repository(DIMENSION), query(MemoryRetrievalMode.VECTOR_APPROXIMATE))
        assert f"CAST(cognitive_os.memory_embeddings.embedding AS vector({DIMENSION}))" in sql

    def test_the_two_paths_produce_different_sql(self) -> None:
        """The guarantee is the difference, so a shared expression would erase it."""
        subject = repository(DIMENSION)
        assert rendered(subject, query(MemoryRetrievalMode.VECTOR)) != rendered(
            subject, query(MemoryRetrievalMode.VECTOR_APPROXIMATE)
        )

    def test_the_cast_matches_the_index_definition(self) -> None:
        """Index and query must agree, or the planner silently ignores the index."""
        sql = rendered(repository(DIMENSION), query(MemoryRetrievalMode.VECTOR_APPROXIMATE))
        assert f"vector({DIMENSION})" in sql
        assert approximate_index_name(DIMENSION) in APPROXIMATE_INDEX_NAMES


class TestFailClosedDefaults:
    def test_a_repository_declares_no_approximate_dimension_by_default(self) -> None:
        """An unchanged Sprint 9 call site keeps Sprint 9 behaviour."""
        with pytest.raises(ValueError, match="no approximate index is declared"):
            rendered(repository(), query(MemoryRetrievalMode.VECTOR_APPROXIMATE))

    def test_exact_retrieval_needs_no_declaration(self) -> None:
        assert rendered(repository(), query(MemoryRetrievalMode.VECTOR))

    def test_an_undeclared_dimension_is_refused_even_when_others_are_declared(self) -> None:
        undeclared = next(
            dimension
            for dimension in range(16, 4096)
            if dimension not in APPROXIMATE_INDEX_DIMENSIONS
        )
        with pytest.raises(ValueError, match=f"dimension {undeclared}"):
            rendered(
                repository(DIMENSION),
                query(MemoryRetrievalMode.VECTOR_APPROXIMATE, dimension=undeclared),
            )


class TestSearchEffort:
    def test_search_effort_never_falls_below_the_candidate_limit(self) -> None:
        """pgvector truncates at ef_search, which would read as poor recall."""
        subject = repository(DIMENSION)
        request = query(MemoryRetrievalMode.VECTOR_APPROXIMATE)
        effective = subject._effective_ef_search(request)
        assert effective >= request.budget.maximum_candidates
        assert effective >= DEFAULT_EF_SEARCH


class TestInMemoryDoubleRefusesToPretend:
    @pytest.mark.asyncio
    async def test_the_double_refuses_approximate_retrieval(self) -> None:
        """It holds no index; answering exactly would look like perfect recall."""
        with pytest.raises(ValueError, match="cannot serve approximate retrieval"):
            await InMemoryMemoryRepository().search(query(MemoryRetrievalMode.VECTOR_APPROXIMATE))

    @pytest.mark.asyncio
    async def test_the_double_still_serves_exact_vector_retrieval(self) -> None:
        page = await InMemoryMemoryRepository().search(query(MemoryRetrievalMode.VECTOR))
        assert page.results == ()


class TestConfigurationAmendment:
    def base(self, **overrides: object) -> dict[str, object]:
        fields: dict[str, object] = {
            "allowed_memory_types": frozenset({"episode"}),
            "allowed_scope_types": frozenset({"project"}),
            "maximum_provider_sensitivity": "internal",
            "export_root": "/srv/cognitive-os/archives/memory",
            "embedding_providers": {
                "deterministic-test": {
                    "provider_type": "deterministic",
                    "model_id": "deterministic-v1",
                    "dimension": DIMENSION,
                }
            },
        }
        fields.update(overrides)
        return fields

    def test_approximation_is_off_by_default(self) -> None:
        assert MemoryConfiguration(**self.base()).approximate_vector_index_dimensions == frozenset()

    def test_a_declared_dimension_is_accepted(self) -> None:
        configuration = MemoryConfiguration(
            **self.base(approximate_vector_index_dimensions=frozenset({DIMENSION}))
        )
        assert configuration.approximate_vector_index_dimensions == frozenset({DIMENSION})

    def test_an_unindexable_dimension_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not indexable"):
            MemoryConfiguration(**self.base(approximate_vector_index_dimensions=frozenset({4096})))

    def test_a_dimension_no_provider_produces_is_refused(self) -> None:
        """A permission that no embedding can use is a permission that misleads."""
        with pytest.raises(ValueError, match="no configured embedding provider"):
            MemoryConfiguration(
                **self.base(approximate_vector_index_dimensions=frozenset({DIMENSION + 1}))
            )

    def test_the_other_sprint_nine_seals_are_untouched(self) -> None:
        """Only the ANN prohibition was amended; the rest stay sealed."""
        for sealed in (
            "allow_provider_direct_write",
            "allow_automatic_promotion",
            "allow_network_model_download",
        ):
            with pytest.raises(ValueError, match="are forbidden"):
                MemoryConfiguration(**self.base(**{sealed: True}))


class TestAutogenerateSeesTheApproximateIndexesAsIntended:
    """Sprint 21R: the drift gate must not propose dropping migration 0013's indexes.

    Found by running the CI `migration` job sequence locally against a fresh
    database. `upgrade head; downgrade base; upgrade head` all succeeded, then
    `alembic check` failed with `remove_index` for both approximate indexes:
    they are partial expression indexes created by raw SQL, so autogenerate
    reflects them, finds no `Table` metadata counterpart, and concludes they
    should be dropped. The branch had never had a CI run — `ci.yml` triggers on
    push to `main` and on `pull_request` only — so nothing had surfaced it.
    """

    @staticmethod
    def _include_object() -> Any:
        from pathlib import Path

        path = Path(__file__).resolve().parents[3] / "infra/postgres/alembic/env.py"
        source = path.read_text(encoding="utf-8")
        # env.py runs migrations at import time, so lift the hook out on its own.
        start = source.index("def include_object(")
        end = source.index("def run_migrations_offline(")
        namespace: dict[str, object] = {"APPROXIMATE_INDEX_NAMES": APPROXIMATE_INDEX_NAMES}
        exec(compile(source[start:end], str(path), "exec"), namespace)
        return namespace["include_object"]

    def test_every_approximate_index_is_excluded_from_comparison(self) -> None:
        include_object = self._include_object()
        assert APPROXIMATE_INDEX_NAMES, "the constant must not be empty"
        for name in APPROXIMATE_INDEX_NAMES:
            assert include_object(None, name, "index", True, None) is False, name

    def test_nothing_else_is_excluded(self) -> None:
        """A broad exclusion would hide real drift, which is the opposite of the fix."""
        include_object = self._include_object()
        assert include_object(None, "ix_memory_embeddings_model", "index", True, None) is True
        assert include_object(None, "memory_embeddings", "table", True, None) is True
        # Same name, different object type: still compared.
        for name in APPROXIMATE_INDEX_NAMES:
            assert include_object(None, name, "table", True, None) is True

    def test_the_exclusion_tracks_the_declared_dimensions(self) -> None:
        """The migration, the health check and the hook read one constant."""
        assert (
            frozenset(
                approximate_index_name(dimension) for dimension in APPROXIMATE_INDEX_DIMENSIONS
            )
            == APPROXIMATE_INDEX_NAMES
        )
