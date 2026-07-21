"""Create governed weakness mining and queue persistence.

Revision ID: 0009
Revises: 0008
"""

from alembic import op

from cognitive_os.infrastructure.weakness.postgres.tables import (
    WEAKNESS_HISTORY_TABLES,
    WEAKNESS_TABLES,
)

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    for table in WEAKNESS_TABLES:
        table.create(connection)
    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_weakness_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Weakness history is append-only';
        END;
        $$
        """
    )
    for table in WEAKNESS_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_weakness_history_mutation()
            """
        )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.validate_weakness_initial_revision()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.current_revision <> 1 OR NEW.current_status <> 'candidate' THEN
                RAISE EXCEPTION 'Initial weakness revision must be candidate revision 1';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_weakness_items_initial
        BEFORE INSERT ON cognitive_os.weakness_items
        FOR EACH ROW EXECUTE FUNCTION cognitive_os.validate_weakness_initial_revision()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.validate_weakness_revision_insert()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_user = 'cogos_app' AND NEW.revision > 1 THEN
                RAISE EXCEPTION 'Weakness revisions require a controlled function';
            END IF;
            IF lower(COALESCE(NEW.payload_json->>'created_by',''))
               SIMILAR TO '(provider|model)%' THEN
                RAISE EXCEPTION 'Provider actors cannot authorize weakness revisions';
            END IF;
            IF COALESCE(NEW.payload_json->>'reason','') = '' THEN
                RAISE EXCEPTION 'Weakness revision requires a reason';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_weakness_revisions_controlled_insert
        BEFORE INSERT ON cognitive_os.weakness_revisions
        FOR EACH ROW EXECUTE FUNCTION cognitive_os.validate_weakness_revision_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_weakness_revision(
            requested_id uuid, expected_revision integer, next_revision integer,
            next_status text, next_hash text, requested_payload jsonb,
            requested_at timestamptz
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE existing_status text; legal boolean;
        BEGIN
            SELECT w.current_status INTO existing_status
              FROM cognitive_os.weakness_items w WHERE w.weakness_id=requested_id;
            legal := CASE existing_status
                WHEN 'candidate' THEN next_status IN
                    ('candidate','confirmed','retracted','superseded')
                WHEN 'confirmed' THEN next_status IN
                    ('confirmed','monitoring','resolved','superseded','retracted')
                WHEN 'monitoring' THEN next_status IN
                    ('monitoring','confirmed','resolved','superseded','retracted')
                WHEN 'resolved' THEN next_status IN ('monitoring','superseded','retracted')
                WHEN 'superseded' THEN next_status = 'retracted'
                ELSE false END;
            IF NOT legal OR next_revision <> expected_revision + 1 THEN RETURN false; END IF;
            IF lower(COALESCE(requested_payload->>'created_by','')) SIMILAR TO '(provider|model)%'
               OR COALESCE(requested_payload->>'reason','') = '' THEN RETURN false; END IF;
            IF next_status = 'confirmed'
               AND COALESCE(requested_payload->>'verifier_bundle_hash','') = ''
               THEN RETURN false; END IF;
            IF next_status = 'superseded'
               AND COALESCE(requested_payload->>'successor_weakness_id','')
                   IN ('', requested_id::text)
               THEN RETURN false; END IF;
            INSERT INTO cognitive_os.weakness_revisions(
                weakness_id, revision, status, revision_hash, payload_json, created_at
            ) VALUES (
                requested_id, next_revision, next_status, next_hash,
                requested_payload, requested_at
            );
            UPDATE cognitive_os.weakness_items
               SET current_revision=next_revision, current_status=next_status,
                   current_revision_hash=next_hash, payload_json=requested_payload,
                   updated_at=requested_at
             WHERE weakness_id=requested_id AND current_revision=expected_revision;
            RETURN FOUND;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_weakness_mining_status(
            requested_id uuid, expected_status text, next_status text,
            requested_at timestamptz
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE legal boolean;
        BEGIN
            legal := CASE expected_status
                WHEN 'requested' THEN next_status IN ('snapshot_created','failed','cancelled')
                WHEN 'snapshot_created' THEN next_status IN
                    ('extracting_signals','failed','cancelled')
                WHEN 'extracting_signals' THEN next_status IN ('grouping','failed','cancelled')
                WHEN 'grouping' THEN next_status IN ('scoring','failed','cancelled')
                WHEN 'scoring' THEN next_status IN ('packaging','failed','cancelled')
                WHEN 'packaging' THEN next_status IN
                    ('completed','completed_with_warnings','failed','cancelled')
                ELSE false END;
            IF NOT legal THEN RETURN false; END IF;
            UPDATE cognitive_os.weakness_mining_runs
               SET current_status=next_status, updated_at=requested_at
             WHERE mining_run_id=requested_id AND current_status=expected_status;
            RETURN FOUND;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.queue_weakness(requested_payload jsonb)
        RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid; expected_hash text;
        BEGIN
            requested_id := (requested_payload->>'queue_entry_id')::uuid;
            expected_hash := requested_payload->>'content_hash';
            IF COALESCE(requested_payload->>'priority_reason','') = ''
               OR COALESCE(requested_payload->>'queue_policy_hash','') = '' THEN
                RETURN false;
            END IF;
            INSERT INTO cognitive_os.weakness_queue(
                queue_record_id, record_kind, weakness_id, weakness_revision,
                priority, status, policy_hash, content_hash, payload_json, created_at
            ) VALUES (
                requested_id, 'entry', (requested_payload->>'weakness_id')::uuid,
                (requested_payload->>'weakness_revision')::integer,
                requested_payload->>'priority', requested_payload->>'status',
                requested_payload->>'queue_policy_hash', expected_hash,
                requested_payload, (requested_payload->>'created_at')::timestamptz
            ) ON CONFLICT (queue_record_id) DO NOTHING;
            RETURN EXISTS (
                SELECT 1 FROM cognitive_os.weakness_queue
                 WHERE queue_record_id=requested_id AND content_hash=expected_hash
            );
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.update_queue_status(requested_payload jsonb)
        RETURNS boolean LANGUAGE sql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
            SELECT cognitive_os.queue_weakness(requested_payload)
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.supersede_queue_entry(requested_payload jsonb)
        RETURNS boolean LANGUAGE sql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
            SELECT cognitive_os.queue_weakness(requested_payload)
        $$
        """
    )
    tables = ", ".join(f"cognitive_os.{table.name}" for table in WEAKNESS_TABLES)
    direct_history = ", ".join(
        f"cognitive_os.{table.name}"
        for table in WEAKNESS_HISTORY_TABLES
        if table.name != "weakness_queue"
    )
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT ON {tables} TO cogos_app")
    op.execute(f"GRANT INSERT ON {direct_history} TO cogos_app")
    op.execute(
        "GRANT INSERT ON cognitive_os.weakness_mining_runs, "
        "cognitive_os.weakness_items TO cogos_app"
    )
    for signature in (
        "cognitive_os.advance_weakness_revision"
        "(uuid, integer, integer, text, text, jsonb, timestamptz)",
        "cognitive_os.advance_weakness_mining_status(uuid, text, text, timestamptz)",
        "cognitive_os.queue_weakness(jsonb)",
        "cognitive_os.update_queue_status(jsonb)",
        "cognitive_os.supersede_queue_entry(jsonb)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    for signature in (
        "cognitive_os.supersede_queue_entry(jsonb)",
        "cognitive_os.update_queue_status(jsonb)",
        "cognitive_os.queue_weakness(jsonb)",
        "cognitive_os.advance_weakness_mining_status(uuid, text, text, timestamptz)",
        "cognitive_os.advance_weakness_revision"
        "(uuid, integer, integer, text, text, jsonb, timestamptz)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {signature}")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.validate_weakness_revision_insert() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.validate_weakness_initial_revision() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_weakness_history_mutation() CASCADE")
    connection = op.get_bind()
    for table in reversed(WEAKNESS_TABLES):
        table.drop(connection)
