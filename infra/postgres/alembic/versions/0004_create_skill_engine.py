"""Create governed procedural skill persistence.

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

from alembic import op

from cognitive_os.infrastructure.skills.postgres.tables import (
    SKILL_HISTORY_TABLES,
    SKILL_TABLES,
)

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    for table in SKILL_TABLES:
        table.create(connection)

    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_skill_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Skill history is append-only';
        END;
        $$
        """
    )
    for table in SKILL_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_skill_history_mutation()
            """
        )

    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_skill(
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
            UPDATE cognitive_os.skill_items
               SET current_revision = next_revision, current_status = next_status
             WHERE skill_id = requested_id
               AND current_revision = expected_revision
               AND EXISTS (
                   SELECT 1 FROM cognitive_os.skill_revisions
                    WHERE skill_id = requested_id
                      AND revision = next_revision
                      AND status = next_status
               );
            RETURN FOUND;
        END;
        $$
        """
    )

    tables = ", ".join(f"cognitive_os.{table.name}" for table in SKILL_TABLES)
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT, INSERT ON {tables} TO cogos_app")
    signature = "cognitive_os.advance_skill(uuid, integer, integer, text)"
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.advance_skill(uuid, integer, integer, text)")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_skill_history_mutation() CASCADE")
    connection = op.get_bind()
    for table in reversed(SKILL_TABLES):
        table.drop(connection)
