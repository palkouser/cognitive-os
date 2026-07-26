"""Create approximate vector indexes and widen the recorded retrieval modes.

Sprint 9 shipped vector search as an exhaustive scan and forbade approximate indexes
outright. Sprint 21 needs a measured retrieval capacity envelope, so the prohibition is
narrowed rather than dropped: approximation becomes available, per dimension, and only
to a caller that names it.

`memory_embeddings.embedding` is an undimensioned `vector` so that one table can hold
several embedding models. pgvector cannot build an HNSW index on such a column at all,
so each indexed dimension gets a partial expression index instead. That shape has a
useful consequence: the existing exact query compares the column directly and therefore
*cannot* use these indexes, so Sprint 9's exhaustive guarantee survives as a property of
the SQL rather than of a configuration flag.

Revision ID: 0013
Revises: 0012
"""

from alembic import op

from cognitive_os.infrastructure.memory.postgres.tables import (
    APPROXIMATE_INDEX_DIMENSIONS,
    approximate_index_name,
)

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

#: pgvector's ceiling for an HNSW-indexed column, measured against 0.8.2. Dimensions
#: above it can only be searched exhaustively, which is why they are absent above.
HNSW_MAXIMUM_DIMENSIONS = 2_000


def upgrade() -> None:
    op.execute("ALTER TABLE cognitive_os.memory_accesses DROP CONSTRAINT ck_memory_access_mode")
    op.execute(
        "ALTER TABLE cognitive_os.memory_accesses ADD CONSTRAINT ck_memory_access_mode "
        "CHECK (retrieval_mode IN ('metadata','text','vector','vector_approximate'))"
    )
    for dimension in APPROXIMATE_INDEX_DIMENSIONS:
        if dimension > HNSW_MAXIMUM_DIMENSIONS:
            raise ValueError(f"pgvector cannot index {dimension} dimensions with hnsw")
        # The predicate matches the query's own `dimension = :d` filter, so the planner
        # can prove the partial index applies; the cast matches the query's cast.
        op.execute(
            f"CREATE INDEX {approximate_index_name(dimension)} "
            f"ON cognitive_os.memory_embeddings "
            f"USING hnsw ((embedding::vector({dimension})) vector_cosine_ops) "
            f"WHERE dimension = {dimension}"
        )


def downgrade() -> None:
    for dimension in reversed(APPROXIMATE_INDEX_DIMENSIONS):
        op.execute(f"DROP INDEX IF EXISTS cognitive_os.{approximate_index_name(dimension)}")
    # Any approximate access already recorded would violate the narrower constraint, so
    # the downgrade refuses rather than silently discarding audit rows.
    op.execute("ALTER TABLE cognitive_os.memory_accesses DROP CONSTRAINT ck_memory_access_mode")
    op.execute(
        "ALTER TABLE cognitive_os.memory_accesses ADD CONSTRAINT ck_memory_access_mode "
        "CHECK (retrieval_mode IN ('metadata','text','vector'))"
    )
