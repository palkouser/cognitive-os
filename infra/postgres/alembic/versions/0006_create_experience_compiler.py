"""Create governed Experience Compiler persistence.

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

from alembic import op

from cognitive_os.infrastructure.experience.postgres.tables import (
    EXPERIENCE_HISTORY_TABLES,
    EXPERIENCE_TABLES,
)

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    for table in EXPERIENCE_TABLES:
        table.create(connection)
    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_experience_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Experience Compiler history is append-only';
        END;
        $$
        """
    )
    for table in EXPERIENCE_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_experience_history_mutation()
            """
        )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.validate_experience_compilation_initial_state()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.current_status <> 'requested'
               OR NEW.manifest_hash IS NOT NULL
               OR NEW.manifest_json IS NOT NULL THEN
                RAISE EXCEPTION 'Experience compilations must begin requested and unfinalized';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.validate_experience_candidate_initial_state()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.current_revision <> 1 OR NEW.current_status <> 'proposed' THEN
                RAISE EXCEPTION 'Experience candidates must begin at revision 1 as proposed';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_experience_compilations_initial_state
        BEFORE INSERT ON cognitive_os.experience_compilations
        FOR EACH ROW EXECUTE FUNCTION cognitive_os.validate_experience_compilation_initial_state()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_experience_candidates_initial_state
        BEFORE INSERT ON cognitive_os.experience_candidates
        FOR EACH ROW EXECUTE FUNCTION cognitive_os.validate_experience_candidate_initial_state()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.finalize_experience_compilation(
            requested_id uuid,
            expected_status text,
            next_status text,
            requested_manifest_hash text,
            requested_manifest jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        BEGIN
            IF next_status NOT IN ('completed', 'failed', 'cancelled') THEN
                RETURN false;
            END IF;
            UPDATE cognitive_os.experience_compilations
               SET current_status = next_status,
                   manifest_hash = requested_manifest_hash,
                   manifest_json = requested_manifest
             WHERE compilation_id = requested_id
               AND current_status = expected_status
               AND manifest_hash IS NULL
               AND EXISTS (
                   SELECT 1 FROM cognitive_os.experience_decisions
                    WHERE compilation_id = requested_id
               );
            RETURN FOUND;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_experience_candidate(
            requested_id uuid,
            expected_revision integer,
            expected_status text,
            next_revision integer,
            next_status text
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        BEGIN
            IF next_revision <> expected_revision + 1 THEN
                RETURN false;
            END IF;
            UPDATE cognitive_os.experience_candidates
               SET current_revision = next_revision,
                   current_status = next_status
             WHERE candidate_id = requested_id
               AND current_revision = expected_revision
               AND current_status = expected_status
               AND EXISTS (
                   SELECT 1 FROM cognitive_os.experience_candidate_revisions
                    WHERE candidate_id = requested_id
                      AND revision = next_revision
                      AND status = next_status
               );
            RETURN FOUND;
        END;
        $$
        """
    )
    tables = ", ".join(f"cognitive_os.{table.name}" for table in EXPERIENCE_TABLES)
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT, INSERT ON {tables} TO cogos_app")
    for signature in (
        "cognitive_os.finalize_experience_compilation(uuid, text, text, text, jsonb)",
        "cognitive_os.advance_experience_candidate(uuid, integer, text, integer, text)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.advance_experience_candidate"
        "(uuid, integer, text, integer, text)"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.finalize_experience_compilation"
        "(uuid, text, text, text, jsonb)"
    )
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_experience_history_mutation() CASCADE")
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.validate_experience_candidate_initial_state() CASCADE"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.validate_experience_compilation_initial_state() "
        "CASCADE"
    )
    connection = op.get_bind()
    for table in reversed(EXPERIENCE_TABLES):
        table.drop(connection)
