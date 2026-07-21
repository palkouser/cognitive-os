"""Create governed Corpus-to-Memory Factory persistence.

Revision ID: 0007
Revises: 0006
"""

from alembic import op

from cognitive_os.infrastructure.corpus.postgres.tables import (
    CORPUS_HISTORY_TABLES,
    CORPUS_TABLES,
)

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    for table in CORPUS_TABLES:
        table.create(connection)
    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_corpus_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Corpus Factory history is append-only';
        END;
        $$
        """
    )
    for table in CORPUS_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_corpus_history_mutation()
            """
        )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.validate_corpus_item_initial_state()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.current_revision <> 1 OR NEW.current_status <> 'received' THEN
                RAISE EXCEPTION 'Corpus items must begin at revision 1 as received';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_corpus_items_initial_state
        BEFORE INSERT ON cognitive_os.corpus_items
        FOR EACH ROW EXECUTE FUNCTION cognitive_os.validate_corpus_item_initial_state()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.validate_corpus_manifest_revision()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.revision = 1 AND NEW.previous_revision IS NULL THEN
                RETURN NEW;
            END IF;
            IF NEW.previous_revision <> NEW.revision - 1 OR NOT EXISTS (
                SELECT 1 FROM cognitive_os.corpus_manifests
                WHERE corpus_id = NEW.corpus_id AND revision = NEW.previous_revision
            ) THEN
                RAISE EXCEPTION 'Corpus manifest revisions must be contiguous';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_corpus_manifests_revision
        BEFORE INSERT ON cognitive_os.corpus_manifests
        FOR EACH ROW EXECUTE FUNCTION cognitive_os.validate_corpus_manifest_revision()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_corpus_item(
            requested_id uuid, expected_revision integer, expected_status text,
            next_revision integer, next_status text, requested_hash text,
            requested_payload jsonb, requested_actor text, requested_reason text
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE legal boolean;
        BEGIN
            legal := CASE expected_status
                WHEN 'received' THEN next_status IN ('normalized','quarantined','rejected')
                WHEN 'normalized' THEN next_status IN ('classified','quarantined','rejected')
                WHEN 'classified' THEN next_status IN ('staged','quarantined','rejected')
                WHEN 'staged' THEN next_status IN ('routed','quarantined','rejected','superseded')
                WHEN 'routed' THEN next_status IN ('exported','quarantined','superseded')
                WHEN 'quarantined' THEN next_status IN (
                    'normalized','classified','staged','rejected'
                )
                WHEN 'exported' THEN next_status = 'superseded'
                ELSE false END;
            IF NOT legal OR next_revision <> expected_revision + 1 THEN RETURN false; END IF;
            UPDATE cognitive_os.corpus_items
               SET current_revision=next_revision, current_status=next_status,
                   item_hash=requested_hash, payload_json=requested_payload,
                   status_actor=requested_actor, status_reason=requested_reason
             WHERE corpus_item_id=requested_id AND current_revision=expected_revision
               AND current_status=expected_status;
            RETURN FOUND;
        END;
        $$
        """
    )
    tables = ", ".join(f"cognitive_os.{table.name}" for table in CORPUS_TABLES)
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT, INSERT ON {tables} TO cogos_app")
    signature = (
        "cognitive_os.advance_corpus_item"
        "(uuid, integer, text, integer, text, text, jsonb, text, text)"
    )
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.advance_corpus_item"
        "(uuid, integer, text, integer, text, text, jsonb, text, text)"
    )
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.validate_corpus_manifest_revision() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.validate_corpus_item_initial_state() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_corpus_history_mutation() CASCADE")
    connection = op.get_bind()
    for table in reversed(CORPUS_TABLES):
        table.drop(connection)
