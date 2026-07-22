"""Create controlled change experiments and promotions.

Revision ID: 0011
Revises: 0010
"""

from alembic import op

from cognitive_os.infrastructure.changes.postgres.tables import (
    CHANGE_HISTORY_TABLES,
    CHANGE_TABLES,
)

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

SPRINT19_INVENTORY_SHA256 = "bf48c294063b193c7d3414f84a4688714a9d819c5777bd65916d6b80cff2e3ff"


def upgrade() -> None:
    connection = op.get_bind()
    for table in CHANGE_TABLES:
        table.create(connection)
    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_change_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Controlled change history is append-only';
        END;
        $$
        """
    )
    for table in CHANGE_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_change_history_mutation()
            """
        )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.create_change_experiment(
            requested_experiment jsonb, requested_revision jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid; requested_hash text; requested_signature text;
        BEGIN
            requested_id := (requested_experiment->>'experiment_id')::uuid;
            requested_hash := requested_revision->>'content_hash';
            requested_signature := requested_experiment->>'content_hash';
            IF requested_revision->>'status' <> 'requested'
               OR (requested_revision->>'revision')::integer <> 1
               OR requested_experiment->>'baseline_commit' !~ '^[0-9a-f]{40}$'
               OR lower(requested_experiment->>'requested_by')
                    SIMILAR TO '(provider|model|candidate|experiment)%'
            THEN RETURN false; END IF;
            INSERT INTO cognitive_os.change_experiments(
                experiment_id, proposal_id, proposal_revision, baseline_commit,
                change_surface_tier, request_signature, current_revision, current_status,
                current_content_hash, payload_json, created_at, updated_at
            ) VALUES (
                requested_id, (requested_experiment->>'proposal_id')::uuid,
                (requested_experiment->>'proposal_revision')::integer,
                requested_experiment->>'baseline_commit',
                requested_experiment->>'change_surface_tier', requested_signature,
                1, 'requested', requested_hash, requested_experiment,
                (requested_experiment->>'created_at')::timestamptz,
                (requested_revision->>'created_at')::timestamptz
            ) ON CONFLICT (experiment_id) DO NOTHING;
            INSERT INTO cognitive_os.change_experiment_revisions(
                experiment_id, revision, previous_revision, status,
                content_hash, payload_json, created_at
            ) VALUES (
                requested_id, 1, NULL, 'requested', requested_hash,
                requested_revision, (requested_revision->>'created_at')::timestamptz
            ) ON CONFLICT (experiment_id, revision) DO NOTHING;
            RETURN EXISTS (
                SELECT 1 FROM cognitive_os.change_experiments
                WHERE experiment_id=requested_id AND current_content_hash=requested_hash
            );
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.append_change_experiment_revision(
            requested_id uuid, expected_revision integer, requested_revision jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE current_status text; next_status text; next_revision integer; legal boolean;
        BEGIN
            SELECT p.current_status INTO current_status
            FROM cognitive_os.change_experiments p
            WHERE p.experiment_id=requested_id AND p.current_revision=expected_revision
            FOR UPDATE;
            next_status := requested_revision->>'status';
            next_revision := (requested_revision->>'revision')::integer;
            legal := CASE current_status
                WHEN 'requested' THEN next_status IN
                    ('approved_for_isolation','cancelled','rejected')
                WHEN 'approved_for_isolation' THEN next_status IN ('preparing','cancelled')
                WHEN 'preparing' THEN next_status IN ('implementing','failed','cancelled')
                WHEN 'implementing' THEN next_status IN ('implemented','failed','cancelled')
                WHEN 'implemented' THEN next_status IN ('evaluating','superseded','cancelled')
                WHEN 'evaluating' THEN next_status IN
                    ('eligible_for_promotion','rejected','failed','cancelled')
                WHEN 'eligible_for_promotion' THEN next_status IN
                    ('approved_for_promotion','rejected','superseded')
                WHEN 'approved_for_promotion' THEN next_status IN
                    ('promoted','failed','cancelled')
                WHEN 'promoted' THEN next_status = 'rolled_back'
                ELSE false END;
            IF current_status IS NULL OR NOT legal
               OR next_revision <> expected_revision + 1
               OR (requested_revision->>'previous_revision')::integer <> expected_revision
            THEN RETURN false; END IF;
            INSERT INTO cognitive_os.change_experiment_revisions(
                experiment_id, revision, previous_revision, status,
                content_hash, payload_json, created_at
            ) VALUES (
                requested_id, next_revision, expected_revision, next_status,
                requested_revision->>'content_hash', requested_revision,
                (requested_revision->>'created_at')::timestamptz
            ) ON CONFLICT (experiment_id, revision) DO NOTHING;
            UPDATE cognitive_os.change_experiments SET
                current_revision=next_revision, current_status=next_status,
                current_content_hash=requested_revision->>'content_hash',
                updated_at=(requested_revision->>'created_at')::timestamptz
            WHERE experiment_id=requested_id AND current_revision=expected_revision;
            RETURN FOUND;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.record_change_component(
            requested_kind text, requested_payload jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_experiment uuid; requested_id uuid; requested_hash text;
        BEGIN
            requested_experiment := (requested_payload->>'experiment_id')::uuid;
            requested_hash := requested_payload->>'content_hash';
            IF NOT EXISTS (
                SELECT 1 FROM cognitive_os.change_experiments
                WHERE experiment_id=requested_experiment
            ) THEN RETURN false; END IF;
            CASE requested_kind
                WHEN 'isolation' THEN
                    requested_id := requested_experiment;
                    INSERT INTO cognitive_os.change_isolation_manifests VALUES
                        (requested_id, requested_experiment, requested_kind, requested_hash,
                         requested_payload, (requested_payload->>'created_at')::timestamptz)
                    ON CONFLICT (isolation_record_id) DO NOTHING;
                WHEN 'candidate' THEN
                    requested_id := (requested_payload->>'candidate_id')::uuid;
                    INSERT INTO cognitive_os.change_candidates VALUES
                        (requested_id, requested_experiment, requested_kind, requested_hash,
                         requested_payload, (requested_payload->>'created_at')::timestamptz)
                    ON CONFLICT (candidate_id) DO NOTHING;
                WHEN 'evaluation' THEN
                    requested_id := (requested_payload->>'evaluation_run_id')::uuid;
                    INSERT INTO cognitive_os.change_evaluation_runs VALUES
                        (requested_id, requested_experiment, requested_kind, requested_hash,
                         requested_payload, (requested_payload->>'started_at')::timestamptz)
                    ON CONFLICT (evaluation_run_id) DO NOTHING;
                WHEN 'comparison' THEN
                    requested_id := (requested_payload->>'comparison_id')::uuid;
                    INSERT INTO cognitive_os.change_regression_comparisons VALUES
                        (requested_id, requested_experiment, requested_kind, requested_hash,
                         requested_payload, (requested_payload->>'created_at')::timestamptz)
                    ON CONFLICT (comparison_id) DO NOTHING;
                WHEN 'assessment' THEN
                    requested_id := (requested_payload->>'assessment_id')::uuid;
                    INSERT INTO cognitive_os.change_promotion_assessments VALUES
                        (requested_id, requested_experiment, requested_kind, requested_hash,
                         requested_payload, (requested_payload->>'created_at')::timestamptz)
                    ON CONFLICT (assessment_id) DO NOTHING;
                WHEN 'rollback' THEN
                    requested_id := (requested_payload->>'rollback_id')::uuid;
                    INSERT INTO cognitive_os.change_rollbacks VALUES
                        (requested_id, requested_experiment, requested_kind, requested_hash,
                         requested_payload, (requested_payload->>'completed_at')::timestamptz)
                    ON CONFLICT (rollback_id) DO NOTHING;
                WHEN 'manifest' THEN
                    requested_id := (requested_payload->>'run_manifest_id')::uuid;
                    INSERT INTO cognitive_os.change_candidate_artifacts VALUES
                        (requested_id, requested_experiment, requested_kind, requested_hash,
                         requested_payload, (requested_payload->>'created_at')::timestamptz)
                    ON CONFLICT (candidate_artifact_id) DO NOTHING;
                ELSE RETURN false;
            END CASE;
            RETURN true;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.record_change_promotion(
            requested_kind text, requested_payload jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid; requested_experiment uuid; requested_hash text;
        BEGIN
            requested_experiment := (requested_payload->>'experiment_id')::uuid;
            requested_hash := requested_payload->>'content_hash';
            IF requested_kind = 'review' THEN
                requested_id := (requested_payload->>'review_id')::uuid;
                IF lower(requested_payload->>'approver')
                    SIMILAR TO '(provider|model|candidate|experiment)%'
                   OR NOT (requested_payload->>'approved')::boolean
                THEN RETURN false; END IF;
            ELSIF requested_kind IN ('bundle','promotion') THEN
                requested_id := CASE requested_kind
                    WHEN 'bundle' THEN (requested_payload->>'promotion_bundle_id')::uuid
                    ELSE (requested_payload->>'promotion_id')::uuid END;
                IF requested_kind = 'promotion' AND NOT EXISTS (
                    SELECT 1 FROM cognitive_os.change_promotions
                    WHERE record_kind='review'
                      AND content_hash=requested_payload->>'approval_reference'
                ) THEN RETURN false; END IF;
            ELSE RETURN false; END IF;
            INSERT INTO cognitive_os.change_promotions(
                promotion_record_id, experiment_id, record_kind, content_hash,
                payload_json, created_at
            ) VALUES (
                requested_id, requested_experiment, requested_kind, requested_hash,
                requested_payload, COALESCE(
                    (requested_payload->>'created_at')::timestamptz,
                    (requested_payload->>'performed_at')::timestamptz)
            ) ON CONFLICT (promotion_record_id) DO NOTHING;
            RETURN EXISTS (
                SELECT 1 FROM cognitive_os.change_promotions
                WHERE promotion_record_id=requested_id AND content_hash=requested_hash
            );
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION cognitive_os.record_change_access(requested_payload jsonb)
        RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid;
        BEGIN
            requested_id := (requested_payload->>'access_id')::uuid;
            INSERT INTO cognitive_os.change_accesses(
                access_id, experiment_id, record_kind, content_hash, payload_json, created_at
            ) VALUES (
                requested_id, (requested_payload->>'experiment_id')::uuid,
                requested_payload->>'access_type', requested_payload->>'content_hash',
                requested_payload, (requested_payload->>'created_at')::timestamptz
            ) ON CONFLICT (access_id) DO NOTHING;
            RETURN EXISTS (
                SELECT 1 FROM cognitive_os.change_accesses
                WHERE access_id=requested_id
                  AND content_hash=requested_payload->>'content_hash'
            );
        END;
        $$
        """
    )
    tables = ", ".join(f"cognitive_os.{table.name}" for table in CHANGE_TABLES)
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT ON {tables} TO cogos_app")
    for signature in (
        "cognitive_os.create_change_experiment(jsonb, jsonb)",
        "cognitive_os.append_change_experiment_revision(uuid, integer, jsonb)",
        "cognitive_os.record_change_component(text, jsonb)",
        "cognitive_os.record_change_promotion(text, jsonb)",
        "cognitive_os.record_change_access(jsonb)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    for signature in (
        "cognitive_os.record_change_access(jsonb)",
        "cognitive_os.record_change_promotion(text, jsonb)",
        "cognitive_os.record_change_component(text, jsonb)",
        "cognitive_os.append_change_experiment_revision(uuid, integer, jsonb)",
        "cognitive_os.create_change_experiment(jsonb, jsonb)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {signature}")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_change_history_mutation() CASCADE")
    connection = op.get_bind()
    for table in reversed(CHANGE_TABLES):
        table.drop(connection)
