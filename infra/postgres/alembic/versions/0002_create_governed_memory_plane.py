"""Create the governed Memory Plane and exact-vector storage.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

from alembic import op

from cognitive_os.infrastructure.memory.postgres.tables import (
    memory_accesses,
    memory_embeddings,
    memory_items,
    memory_revisions,
    memory_sources,
)

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

HISTORY_TABLES = (memory_revisions, memory_sources, memory_embeddings, memory_accesses)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
    connection = op.get_bind()
    for table in (memory_items, *HISTORY_TABLES):
        table.create(connection)

    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_memory_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Memory Plane history is append-only';
        END;
        $$
        """
    )
    for table in HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_memory_history_mutation()
            """
        )

    op.execute(
        """
        CREATE FUNCTION cognitive_os.validate_memory_embedding_hash()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE revision_hash text;
        BEGIN
            SELECT content_hash INTO revision_hash
              FROM cognitive_os.memory_revisions
             WHERE memory_id = NEW.memory_id AND revision = NEW.revision;
            IF revision_hash IS NULL OR revision_hash <> NEW.content_hash THEN
                RAISE EXCEPTION 'Embedding content hash does not match memory revision';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_memory_embeddings_content_hash
        BEFORE INSERT ON cognitive_os.memory_embeddings
        FOR EACH ROW EXECUTE FUNCTION cognitive_os.validate_memory_embedding_hash()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.require_memory_revision_source()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM cognitive_os.memory_sources
                 WHERE memory_id = NEW.memory_id AND revision = NEW.revision
            ) THEN
                RAISE EXCEPTION 'Durable memory revision requires provenance';
            END IF;
            RETURN NULL;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_memory_revision_requires_source
        AFTER INSERT ON cognitive_os.memory_revisions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION cognitive_os.require_memory_revision_source()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_memory_item(
            requested_memory_id uuid,
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
            UPDATE cognitive_os.memory_items
               SET current_revision = next_revision, status = next_status
             WHERE memory_id = requested_memory_id
               AND current_revision = expected_revision
               AND EXISTS (
                   SELECT 1 FROM cognitive_os.memory_revisions
                    WHERE memory_id = requested_memory_id
                      AND revision = next_revision
                      AND status = next_status
               );
            RETURN FOUND;
        END;
        $$
        """
    )

    op.execute(
        "REVOKE ALL ON cognitive_os.memory_items, cognitive_os.memory_revisions, "
        "cognitive_os.memory_sources, cognitive_os.memory_embeddings, "
        "cognitive_os.memory_accesses FROM cogos_app"
    )
    op.execute(
        "GRANT ALL PRIVILEGES ON cognitive_os.memory_items, "
        "cognitive_os.memory_revisions, cognitive_os.memory_sources, "
        "cognitive_os.memory_embeddings, cognitive_os.memory_accesses TO cogos_owner"
    )
    op.execute(
        "GRANT SELECT ON cognitive_os.memory_items, cognitive_os.memory_revisions, "
        "cognitive_os.memory_sources, cognitive_os.memory_embeddings, "
        "cognitive_os.memory_accesses TO cogos_app"
    )
    op.execute("GRANT INSERT ON cognitive_os.memory_items TO cogos_app")
    op.execute(
        "GRANT INSERT ON cognitive_os.memory_revisions, cognitive_os.memory_sources, "
        "cognitive_os.memory_embeddings, cognitive_os.memory_accesses TO cogos_app"
    )
    op.execute("REVOKE ALL ON FUNCTION cognitive_os.advance_memory_item FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION cognitive_os.advance_memory_item TO cogos_app")


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.advance_memory_item(uuid, integer, integer, text)"
    )
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.require_memory_revision_source() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.validate_memory_embedding_hash() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_memory_history_mutation() CASCADE")
    connection = op.get_bind()
    for table in reversed((memory_items, *HISTORY_TABLES)):
        table.drop(connection)
    op.execute("DROP EXTENSION IF EXISTS vector")
