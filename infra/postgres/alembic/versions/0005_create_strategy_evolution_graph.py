"""Create governed Strategy Evolution Graph persistence.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

from alembic import op

from cognitive_os.infrastructure.strategies.postgres.tables import (
    STRATEGY_HISTORY_TABLES,
    STRATEGY_TABLES,
)

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    for table in STRATEGY_TABLES:
        table.create(connection)
    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_strategy_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Strategy history is append-only';
        END;
        $$
        """
    )
    for table in STRATEGY_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_strategy_history_mutation()
            """
        )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_strategy(
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
            UPDATE cognitive_os.strategy_items
               SET current_revision = next_revision, current_status = next_status
             WHERE strategy_id = requested_id
               AND current_revision = expected_revision
               AND EXISTS (
                   SELECT 1 FROM cognitive_os.strategy_revisions
                    WHERE strategy_id = requested_id
                      AND revision = next_revision
                      AND status = next_status
               );
            RETURN FOUND;
        END;
        $$
        """
    )
    tables = ", ".join(f"cognitive_os.{table.name}" for table in STRATEGY_TABLES)
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT, INSERT ON {tables} TO cogos_app")
    signature = "cognitive_os.advance_strategy(uuid, integer, integer, text)"
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.advance_strategy(uuid, integer, integer, text)"
    )
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_strategy_history_mutation() CASCADE")
    connection = op.get_bind()
    for table in reversed(STRATEGY_TABLES):
        table.drop(connection)
