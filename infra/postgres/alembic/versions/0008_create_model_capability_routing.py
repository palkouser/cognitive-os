"""Create governed model capability and routing persistence.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

from cognitive_os.infrastructure.routing.postgres.tables import (
    ROUTING_HISTORY_TABLES,
    ROUTING_TABLES,
)

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    for table in ROUTING_TABLES:
        table.create(connection)
    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_routing_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Routing history is append-only';
        END;
        $$
        """
    )
    for table in ROUTING_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_routing_history_mutation()
            """
        )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.validate_routing_initial_revision()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (to_jsonb(NEW)->>'current_revision')::integer <> 1 THEN
                RAISE EXCEPTION 'Initial routing revision must be 1';
            END IF;
            IF TG_TABLE_NAME = 'routing_policies'
               AND to_jsonb(NEW)->>'control_mode' = 'shadow'
               AND to_jsonb(NEW)->>'current_status' = 'enabled' THEN
                RAISE EXCEPTION 'Shadow routing cannot execute';
            END IF;
            IF TG_TABLE_NAME = 'routing_policies'
               AND to_jsonb(NEW)->>'control_mode' = 'adaptive'
               AND to_jsonb(NEW)->>'current_status' IN ('approved','enabled')
               AND COALESCE(to_jsonb(NEW)->'payload_json'->>'operator_approval_reference','') = '' THEN
                RAISE EXCEPTION 'Adaptive routing requires operator approval';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_model_capability_profiles_initial
        BEFORE INSERT ON cognitive_os.model_capability_profiles
        FOR EACH ROW
        EXECUTE FUNCTION cognitive_os.validate_routing_initial_revision()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_routing_policies_initial
        BEFORE INSERT ON cognitive_os.routing_policies
        FOR EACH ROW
        EXECUTE FUNCTION cognitive_os.validate_routing_initial_revision()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.validate_routing_revision_insert()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_user = 'cogos_app' AND NEW.revision > 1 THEN
                RAISE EXCEPTION 'Routing revisions require a controlled function';
            END IF;
            IF TG_TABLE_NAME = 'routing_policy_revisions'
               AND to_jsonb(NEW)->>'control_mode' = 'shadow'
               AND to_jsonb(NEW)->>'status' = 'enabled' THEN
                RAISE EXCEPTION 'Shadow routing cannot execute';
            END IF;
            IF TG_TABLE_NAME = 'routing_policy_revisions'
               AND to_jsonb(NEW)->>'control_mode' = 'adaptive'
               AND to_jsonb(NEW)->>'status' IN ('approved','enabled')
               AND COALESCE(to_jsonb(NEW)->'payload_json'->>'operator_approval_reference','') = '' THEN
                RAISE EXCEPTION 'Adaptive routing requires operator approval';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    for table_name in ("model_capability_revisions", "routing_policy_revisions"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table_name}_controlled_insert
            BEFORE INSERT ON cognitive_os.{table_name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.validate_routing_revision_insert()
            """
        )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_model_capability_profile(
            requested_hash text, expected_revision integer, next_revision integer,
            next_status text, next_profile_hash text, requested_payload jsonb,
            requested_at timestamptz
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE legal boolean;
        BEGIN
            legal := CASE (
                SELECT current_status FROM cognitive_os.model_capability_profiles
                WHERE model_identity_hash=requested_hash
            )
                WHEN 'draft' THEN next_status IN ('registered','retracted')
                WHEN 'registered' THEN next_status IN (
                    'registered','verified','deprecated','retracted'
                )
                WHEN 'verified' THEN next_status IN ('verified','deprecated','retracted')
                WHEN 'deprecated' THEN next_status IN ('registered','retracted')
                ELSE false END;
            IF NOT legal OR next_revision <> expected_revision + 1 THEN RETURN false; END IF;
            INSERT INTO cognitive_os.model_capability_revisions(
                model_identity_hash, revision, status, profile_hash, payload_json, created_at
            ) VALUES (
                requested_hash, next_revision, next_status, next_profile_hash,
                requested_payload, requested_at
            );
            UPDATE cognitive_os.model_capability_profiles
               SET current_revision=next_revision, current_status=next_status,
                   current_profile_hash=next_profile_hash, payload_json=requested_payload,
                   updated_at=requested_at
             WHERE model_identity_hash=requested_hash AND current_revision=expected_revision;
            RETURN FOUND;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.advance_routing_policy(
            requested_id text, expected_revision integer, next_revision integer,
            next_status text, next_mode text, next_policy_hash text,
            requested_payload jsonb, requested_at timestamptz
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE current_status text; legal boolean;
        BEGIN
            SELECT p.current_status INTO current_status FROM cognitive_os.routing_policies p
             WHERE p.policy_id=requested_id;
            legal := CASE current_status
                WHEN 'draft' THEN next_status IN ('staged','retracted')
                WHEN 'staged' THEN next_status IN ('shadow','retracted')
                WHEN 'shadow' THEN next_status IN ('approved','disabled','deprecated','retracted')
                WHEN 'approved' THEN next_status IN ('enabled','disabled','retracted')
                WHEN 'enabled' THEN next_status IN ('disabled','deprecated','retracted')
                WHEN 'disabled' THEN next_status IN ('shadow','enabled','deprecated','retracted')
                ELSE false END;
            IF NOT legal OR next_revision <> expected_revision + 1 THEN RETURN false; END IF;
            IF next_mode='adaptive' AND next_status IN ('approved','enabled')
               AND COALESCE(requested_payload->>'operator_approval_reference','')='' THEN
                RETURN false;
            END IF;
            IF next_mode='shadow' AND next_status='enabled' THEN RETURN false; END IF;
            INSERT INTO cognitive_os.routing_policy_revisions(
                policy_id, revision, status, control_mode, policy_hash, payload_json, created_at
            ) VALUES (
                requested_id, next_revision, next_status, next_mode,
                next_policy_hash, requested_payload, requested_at
            );
            UPDATE cognitive_os.routing_policies
               SET current_revision=next_revision, current_status=next_status,
                   control_mode=next_mode, current_policy_hash=next_policy_hash,
                   payload_json=requested_payload, updated_at=requested_at
             WHERE policy_id=requested_id AND current_revision=expected_revision;
            RETURN FOUND;
        END;
        $$
        """
    )
    tables = ", ".join(f"cognitive_os.{table.name}" for table in ROUTING_TABLES)
    history = ", ".join(f"cognitive_os.{table.name}" for table in ROUTING_HISTORY_TABLES)
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT ON {tables} TO cogos_app")
    op.execute(f"GRANT INSERT ON {history} TO cogos_app")
    op.execute(
        "GRANT INSERT ON cognitive_os.model_capability_profiles, "
        "cognitive_os.routing_policies TO cogos_app"
    )
    for signature in (
        "cognitive_os.advance_model_capability_profile"
        "(text, integer, integer, text, text, jsonb, timestamptz)",
        "cognitive_os.advance_routing_policy"
        "(text, integer, integer, text, text, text, jsonb, timestamptz)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.advance_routing_policy"
        "(text, integer, integer, text, text, text, jsonb, timestamptz)"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.advance_model_capability_profile"
        "(text, integer, integer, text, text, jsonb, timestamptz)"
    )
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.validate_routing_initial_revision() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.validate_routing_revision_insert() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_routing_history_mutation() CASCADE")
    connection = op.get_bind()
    for table in reversed(ROUTING_TABLES):
        table.drop(connection)
