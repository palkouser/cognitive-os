"""Create governed Harness Proposal Engine persistence.

Revision ID: 0010
Revises: 0009
"""

from alembic import op

from cognitive_os.infrastructure.proposals.postgres.tables import (
    PROPOSAL_HISTORY_TABLES,
    PROPOSAL_TABLES,
)

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

# Verified Sprint 17 preflight inventory used to design and test this migration.
SPRINT18_INVENTORY_SHA256 = "b33d5fe5db7b20ac5df51536821e3295a58b40393559d9879fd056eb341744bc"


def upgrade() -> None:
    connection = op.get_bind()
    for table in PROPOSAL_TABLES:
        table.create(connection)
    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_harness_proposal_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Harness proposal history is append-only';
        END;
        $$
        """
    )
    for table in PROPOSAL_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_harness_proposal_history_mutation()
            """
        )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.create_harness_proposal(
            requested_identity jsonb, requested_revision jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid; requested_signature text; requested_hash text;
        BEGIN
            requested_id := (requested_identity->>'proposal_id')::uuid;
            requested_signature := requested_revision->>'proposal_signature';
            requested_hash := requested_revision->>'content_hash';
            IF (requested_revision->>'revision')::integer <> 1
               OR requested_revision->>'status' NOT IN ('draft','generated')
               OR lower(requested_revision->>'created_by') SIMILAR TO '(provider|model)%'
               OR COALESCE(requested_revision->>'reason','') = ''
               OR EXISTS (
                   SELECT 1 FROM cognitive_os.harness_proposals
                    WHERE current_signature=requested_signature
                      AND current_status NOT IN ('rejected','superseded','retracted')
                      AND proposal_id<>requested_id
               ) THEN RETURN false; END IF;
            INSERT INTO cognitive_os.harness_proposals(
                proposal_id, canonical_name, proposal_type, scope, current_revision,
                current_status, current_signature, current_content_hash, payload_json,
                created_at, updated_at
            ) VALUES (
                requested_id, requested_identity->>'canonical_name',
                requested_identity->>'proposal_type', requested_identity->>'scope', 1,
                requested_revision->>'status', requested_signature, requested_hash,
                requested_revision, (requested_identity->>'created_at')::timestamptz,
                (requested_revision->>'created_at')::timestamptz
            ) ON CONFLICT (proposal_id) DO NOTHING;
            INSERT INTO cognitive_os.harness_proposal_revisions(
                proposal_id, revision, previous_revision, status, proposal_signature,
                content_hash, payload_json, created_at
            ) VALUES (
                requested_id, 1, NULL, requested_revision->>'status', requested_signature,
                requested_hash, requested_revision,
                (requested_revision->>'created_at')::timestamptz
            ) ON CONFLICT (proposal_id, revision) DO NOTHING;
            RETURN EXISTS (
                SELECT 1 FROM cognitive_os.harness_proposals
                 WHERE proposal_id=requested_id AND current_content_hash=requested_hash
            );
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.append_harness_proposal_revision(
            requested_id uuid, expected_revision integer, requested_revision jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE current_status text; next_status text; next_revision integer; legal boolean;
        BEGIN
            SELECT p.current_status INTO current_status FROM cognitive_os.harness_proposals p
             WHERE p.proposal_id=requested_id AND p.current_revision=expected_revision
             FOR UPDATE;
            next_status := requested_revision->>'status';
            next_revision := (requested_revision->>'revision')::integer;
            legal := CASE current_status
                WHEN 'draft' THEN next_status IN ('generated','retracted')
                WHEN 'generated' THEN next_status IN
                    ('validated','rejected','retracted','superseded')
                WHEN 'validated' THEN next_status IN
                    ('staged_for_review','rejected','retracted','superseded')
                WHEN 'staged_for_review' THEN next_status IN
                    ('approved_for_experiment','rejected','retracted','superseded')
                WHEN 'approved_for_experiment' THEN next_status IN ('superseded','retracted')
                ELSE false END;
            IF NOT legal OR next_revision <> expected_revision + 1
               OR (requested_revision->>'previous_revision')::integer <> expected_revision
               OR lower(requested_revision->>'created_by') SIMILAR TO '(provider|model)%'
               OR COALESCE(requested_revision->>'reason','') = '' THEN RETURN false; END IF;
            IF next_status IN ('validated','staged_for_review','approved_for_experiment')
               AND COALESCE(requested_revision->'verifier_bundle'->>'content_hash','') = ''
               THEN RETURN false; END IF;
            INSERT INTO cognitive_os.harness_proposal_revisions(
                proposal_id, revision, previous_revision, status, proposal_signature,
                content_hash, payload_json, created_at
            ) VALUES (
                requested_id, next_revision, expected_revision, next_status,
                requested_revision->>'proposal_signature', requested_revision->>'content_hash',
                requested_revision, (requested_revision->>'created_at')::timestamptz
            );
            UPDATE cognitive_os.harness_proposals SET
                current_revision=next_revision, current_status=next_status,
                current_signature=requested_revision->>'proposal_signature',
                current_content_hash=requested_revision->>'content_hash',
                payload_json=requested_revision,
                updated_at=(requested_revision->>'created_at')::timestamptz
             WHERE proposal_id=requested_id AND current_revision=expected_revision;
            RETURN FOUND;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.transition_harness_proposal(
            requested_id uuid, expected_revision integer, expected_status text,
            requested_revision jsonb
        ) RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM cognitive_os.harness_proposals
                 WHERE proposal_id=requested_id AND current_revision=expected_revision
                   AND current_status=expected_status
            ) THEN RETURN false; END IF;
            RETURN cognitive_os.append_harness_proposal_revision(
                requested_id, expected_revision, requested_revision
            );
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.record_harness_proposal_review(requested_payload jsonb)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid;
        BEGIN
            requested_id := (requested_payload->>'review_id')::uuid;
            IF lower(requested_payload->>'reviewer_identity') SIMILAR TO '(provider|model)%'
               OR NOT EXISTS (
                   SELECT 1 FROM cognitive_os.harness_proposal_revisions r
                    WHERE r.proposal_id=(requested_payload->>'proposal_id')::uuid
                      AND r.revision=(requested_payload->>'proposal_revision')::integer
                      AND r.status='staged_for_review'
                      AND r.content_hash=requested_payload->>'proposal_content_hash'
               ) THEN RETURN false; END IF;
            INSERT INTO cognitive_os.harness_proposal_reviews(
                review_id, proposal_id, proposal_revision, decision,
                verifier_bundle_hash, content_hash, payload_json, created_at
            ) VALUES (
                requested_id, (requested_payload->>'proposal_id')::uuid,
                (requested_payload->>'proposal_revision')::integer,
                requested_payload->>'review_decision',
                requested_payload->>'verifier_bundle_hash', requested_payload->>'content_hash',
                requested_payload, (requested_payload->>'created_at')::timestamptz
            ) ON CONFLICT (review_id) DO NOTHING;
            RETURN EXISTS (
                SELECT 1 FROM cognitive_os.harness_proposal_reviews
                 WHERE review_id=requested_id
                   AND content_hash=requested_payload->>'content_hash'
            );
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.enqueue_harness_proposal(requested_payload jsonb)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid;
        BEGIN
            requested_id := (requested_payload->>'queue_entry_id')::uuid;
            IF NOT EXISTS (
                SELECT 1 FROM cognitive_os.harness_proposal_revisions r
                 WHERE r.proposal_id=(requested_payload->>'proposal_id')::uuid
                   AND r.revision=(requested_payload->>'proposal_revision')::integer
                   AND r.content_hash=requested_payload->>'proposal_content_hash'
                   AND r.status IN
                       ('validated','staged_for_review','approved_for_experiment')
            ) THEN RETURN false; END IF;
            INSERT INTO cognitive_os.harness_proposal_queue(
                queue_record_id, record_kind, proposal_id, proposal_revision, active,
                operator_priority, weakness_priority, evidence_confidence,
                content_hash, payload_json, created_at
            ) VALUES (
                requested_id, 'entry', (requested_payload->>'proposal_id')::uuid,
                (requested_payload->>'proposal_revision')::integer,
                (requested_payload->>'active')::boolean,
                (requested_payload->>'operator_priority')::integer,
                (requested_payload->>'weakness_priority')::integer,
                (requested_payload->>'evidence_confidence')::numeric,
                requested_payload->>'content_hash', requested_payload,
                (requested_payload->>'created_at')::timestamptz
            ) ON CONFLICT (queue_record_id) DO NOTHING;
            RETURN EXISTS (
                SELECT 1 FROM cognitive_os.harness_proposal_queue
                 WHERE queue_record_id=requested_id
                   AND content_hash=requested_payload->>'content_hash'
            );
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.remove_harness_proposal_from_queue(requested_payload jsonb)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid;
        BEGIN
            IF (requested_payload->>'active')::boolean THEN RETURN false; END IF;
            requested_id := (requested_payload->>'queue_entry_id')::uuid;
            IF NOT EXISTS (
                SELECT 1 FROM cognitive_os.harness_proposal_queue
                 WHERE proposal_id=(requested_payload->>'proposal_id')::uuid
                   AND proposal_revision=(requested_payload->>'proposal_revision')::integer
                   AND record_kind='entry' AND active
            ) OR EXISTS (
                SELECT 1 FROM cognitive_os.harness_proposal_queue
                 WHERE proposal_id=(requested_payload->>'proposal_id')::uuid
                   AND proposal_revision=(requested_payload->>'proposal_revision')::integer
                   AND record_kind='removal'
            ) THEN RETURN false; END IF;
            INSERT INTO cognitive_os.harness_proposal_queue(
                queue_record_id, record_kind, proposal_id, proposal_revision, active,
                operator_priority, weakness_priority, evidence_confidence,
                content_hash, payload_json, created_at
            ) VALUES (
                requested_id, 'removal', (requested_payload->>'proposal_id')::uuid,
                (requested_payload->>'proposal_revision')::integer, false,
                (requested_payload->>'operator_priority')::integer,
                (requested_payload->>'weakness_priority')::integer,
                (requested_payload->>'evidence_confidence')::numeric,
                requested_payload->>'content_hash', requested_payload,
                (requested_payload->>'created_at')::timestamptz
            ) ON CONFLICT (queue_record_id) DO NOTHING;
            RETURN EXISTS (
                SELECT 1 FROM cognitive_os.harness_proposal_queue
                 WHERE queue_record_id=requested_id AND record_kind='removal'
                   AND content_hash=requested_payload->>'content_hash'
            );
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.record_harness_proposal_access(requested_payload jsonb)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid;
        BEGIN
            requested_id := (requested_payload->>'access_id')::uuid;
            INSERT INTO cognitive_os.harness_proposal_accesses(
                access_id, proposal_id, proposal_revision, access_type,
                content_hash, payload_json, created_at
            ) VALUES (
                requested_id, (requested_payload->>'proposal_id')::uuid,
                (requested_payload->>'proposal_revision')::integer,
                requested_payload->>'access_type', requested_payload->>'content_hash',
                requested_payload, (requested_payload->>'accessed_at')::timestamptz
            ) ON CONFLICT (access_id) DO NOTHING;
            RETURN EXISTS (
                SELECT 1 FROM cognitive_os.harness_proposal_accesses
                 WHERE access_id=requested_id
                   AND content_hash=requested_payload->>'content_hash'
            );
        END;
        $$
        """
    )
    tables = ", ".join(f"cognitive_os.{table.name}" for table in PROPOSAL_TABLES)
    component_tables = ", ".join(f"cognitive_os.{table.name}" for table in PROPOSAL_TABLES[2:7])
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT ON {tables} TO cogos_app")
    op.execute(f"GRANT INSERT ON {component_tables} TO cogos_app")
    signatures = (
        "cognitive_os.create_harness_proposal(jsonb, jsonb)",
        "cognitive_os.append_harness_proposal_revision(uuid, integer, jsonb)",
        "cognitive_os.transition_harness_proposal(uuid, integer, text, jsonb)",
        "cognitive_os.record_harness_proposal_review(jsonb)",
        "cognitive_os.enqueue_harness_proposal(jsonb)",
        "cognitive_os.remove_harness_proposal_from_queue(jsonb)",
        "cognitive_os.record_harness_proposal_access(jsonb)",
    )
    for signature in signatures:
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    for signature in (
        "cognitive_os.record_harness_proposal_access(jsonb)",
        "cognitive_os.remove_harness_proposal_from_queue(jsonb)",
        "cognitive_os.enqueue_harness_proposal(jsonb)",
        "cognitive_os.record_harness_proposal_review(jsonb)",
        "cognitive_os.transition_harness_proposal(uuid, integer, text, jsonb)",
        "cognitive_os.append_harness_proposal_revision(uuid, integer, jsonb)",
        "cognitive_os.create_harness_proposal(jsonb, jsonb)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {signature}")
    op.execute(
        "DROP FUNCTION IF EXISTS cognitive_os.reject_harness_proposal_history_mutation() CASCADE"
    )
    connection = op.get_bind()
    for table in reversed(PROPOSAL_TABLES):
        table.drop(connection)
