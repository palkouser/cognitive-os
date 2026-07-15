"""Create temporal semantic memory and deterministic Wiki projections.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

from alembic import op

from cognitive_os.infrastructure.semantic_memory.postgres.tables import (
    SEMANTIC_HISTORY_TABLES,
    SEMANTIC_TABLES,
)

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _advance_function(
    name: str,
    table: str,
    history_table: str,
    id_column: str,
    status_column: str,
) -> None:
    op.execute(
        f"""
        CREATE FUNCTION cognitive_os.{name}(
            requested_id uuid,
            expected_revision integer,
            next_revision integer,
            next_status text
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        BEGIN
            IF next_revision <> expected_revision + 1 THEN
                RETURN false;
            END IF;
            UPDATE cognitive_os.{table}
               SET current_revision = next_revision, {status_column} = next_status
             WHERE {id_column} = requested_id
               AND current_revision = expected_revision
               AND EXISTS (
                   SELECT 1 FROM cognitive_os.{history_table}
                    WHERE {id_column} = requested_id
                      AND revision = next_revision
                      AND {status_column.replace("current_", "")} = next_status
               );
            RETURN FOUND;
        END;
        $$
        """
    )


def upgrade() -> None:
    connection = op.get_bind()
    for table in SEMANTIC_TABLES:
        table.create(connection)

    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_semantic_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Semantic history is append-only';
        END;
        $$
        """
    )
    for table in SEMANTIC_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_semantic_history_mutation()
            """
        )

    _advance_function(
        "advance_semantic_claim",
        "semantic_claims",
        "semantic_claim_revisions",
        "claim_id",
        "current_belief_status",
    )
    _advance_function(
        "advance_semantic_contradiction",
        "semantic_contradictions",
        "semantic_contradiction_revisions",
        "contradiction_id",
        "current_status",
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_wiki_page(
            requested_id uuid,
            expected_revision integer,
            next_revision integer
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        BEGIN
            IF next_revision <> expected_revision + 1 THEN
                RETURN false;
            END IF;
            UPDATE cognitive_os.wiki_pages
               SET current_revision = next_revision
             WHERE page_id = requested_id
               AND current_revision = expected_revision
               AND EXISTS (
                   SELECT 1 FROM cognitive_os.wiki_page_revisions
                    WHERE page_id = requested_id AND revision = next_revision
               );
            RETURN FOUND;
        END;
        $$
        """
    )

    tables = ", ".join(f"cognitive_os.{table.name}" for table in SEMANTIC_TABLES)
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT ON {tables} TO cogos_app")
    insert_tables = ", ".join(f"cognitive_os.{table.name}" for table in SEMANTIC_TABLES)
    op.execute(f"GRANT INSERT ON {insert_tables} TO cogos_app")
    for function in (
        "advance_semantic_claim(uuid, integer, integer, text)",
        "advance_semantic_contradiction(uuid, integer, integer, text)",
        "advance_wiki_page(uuid, integer, integer)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION cognitive_os.{function} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION cognitive_os.{function} TO cogos_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.advance_wiki_page(uuid, integer, integer)")
    op.execute(
        "DROP FUNCTION IF EXISTS "
        "cognitive_os.advance_semantic_contradiction(uuid, integer, integer, text)"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.advance_semantic_claim(uuid, integer, integer, text)"
    )
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_semantic_history_mutation() CASCADE")
    connection = op.get_bind()
    for table in reversed(SEMANTIC_TABLES):
        table.drop(connection)
