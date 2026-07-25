"""Create cross-domain pilot runs and transfer evidence.

Revision ID: 0012
Revises: 0011
"""

from alembic import op

from cognitive_os.infrastructure.domains.postgres.tables import (
    DOMAIN_HISTORY_TABLES,
    DOMAIN_TABLES,
)

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

# Provenance marker for the preflight inventory this migration was authored against,
# matching the Sprint 19 convention.
SPRINT20_INVENTORY_SHA256 = "c51b4a4f193bb7bcaf8fc41c24bdf084b5761500a8498d0a9075c3c89d79df40"


def upgrade() -> None:
    connection = op.get_bind()
    for table in DOMAIN_TABLES:
        table.create(connection)

    op.execute(
        """
        CREATE FUNCTION cognitive_os.reject_domain_history_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Cross-domain pilot evidence is append-only';
        END;
        $$
        """
    )
    for table in DOMAIN_HISTORY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON cognitive_os.{table.name}
            FOR EACH ROW EXECUTE FUNCTION cognitive_os.reject_domain_history_mutation()
            """
        )

    # Recording a run is a single controlled operation: the caller cannot invent a
    # status, and an existing run may never be silently replaced by different
    # content. Re-recording identical content is idempotent.
    op.execute(
        """
        CREATE FUNCTION cognitive_os.record_domain_pilot_run(requested_run jsonb)
        RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE requested_id uuid; existing_hash text;
        BEGIN
            requested_id := (requested_run->>'run_id')::uuid;
            IF requested_run->>'domain' NOT IN ('mathematics', 'physics', 'logic') THEN
                RAISE EXCEPTION 'unknown domain %', requested_run->>'domain';
            END IF;
            IF requested_run->>'problem_hash' !~ '^[0-9a-f]{64}$' THEN
                RAISE EXCEPTION 'problem hash is not a sha256 digest';
            END IF;
            SELECT problem_hash INTO existing_hash
            FROM cognitive_os.domain_pilot_runs WHERE run_id = requested_id;
            IF existing_hash IS NOT NULL
               AND existing_hash <> requested_run->>'problem_hash' THEN
                RAISE EXCEPTION 'run % already exists with different content', requested_id;
            END IF;
            INSERT INTO cognitive_os.domain_pilot_runs (
                run_id, case_id, domain, status, problem_hash, plan_hash,
                derivation_hash, answer_hash, outcome_hash, failure_code,
                skill_revisions, strategy_revisions, payload_json, created_at
            ) VALUES (
                requested_id,
                requested_run->>'case_id',
                requested_run->>'domain',
                requested_run->>'status',
                requested_run->>'problem_hash',
                requested_run->>'plan_hash',
                requested_run->>'derivation_hash',
                requested_run->>'answer_hash',
                requested_run->>'outcome_hash',
                requested_run->>'failure_code',
                COALESCE(requested_run->'skill_revisions', '[]'::jsonb),
                COALESCE(requested_run->'strategy_revisions', '[]'::jsonb),
                requested_run,
                (requested_run->>'created_at')::timestamptz
            ) ON CONFLICT (run_id) DO NOTHING;
            RETURN TRUE;
        END;
        $$
        """
    )

    # A transfer result that breached a hard gate can never be stored as positive
    # transfer. The check constraint enforces it; this function refuses earlier so
    # the caller gets a clear error instead of a constraint violation.
    op.execute(
        """
        CREATE FUNCTION cognitive_os.record_domain_transfer_result(
            requested_experiment jsonb, requested_result jsonb
        ) RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        DECLARE gate_failed boolean;
        BEGIN
            gate_failed := jsonb_array_length(
                COALESCE(requested_result->'hard_gate_failures', '[]'::jsonb)
            ) > 0;
            IF gate_failed AND requested_result->>'disposition' = 'positive_transfer' THEN
                RAISE EXCEPTION 'positive transfer cannot be recorded with a hard gate failure';
            END IF;
            INSERT INTO cognitive_os.domain_transfer_experiments (
                experiment_id, source_domain, target_domain, unrelated_domain,
                component_kind, component_id, component_revision, case_manifest,
                seed, environment, content_hash, payload_json, created_at
            ) VALUES (
                (requested_experiment->>'experiment_id')::uuid,
                requested_experiment->>'source_domain',
                requested_experiment->>'target_domain',
                requested_experiment->>'unrelated_domain',
                requested_experiment->>'component_kind',
                requested_experiment->>'component_id',
                requested_experiment->>'component_revision',
                requested_experiment->>'case_manifest',
                (requested_experiment->>'seed')::integer,
                requested_experiment->>'environment',
                requested_experiment->>'content_hash',
                requested_experiment,
                (requested_experiment->>'created_at')::timestamptz
            ) ON CONFLICT (experiment_id) DO NOTHING;
            INSERT INTO cognitive_os.domain_transfer_results (
                experiment_id, disposition, target_quality_delta, source_quality_delta,
                unrelated_quality_delta, hard_gate_failed, content_hash,
                payload_json, created_at
            ) VALUES (
                (requested_result->>'experiment_id')::uuid,
                requested_result->>'disposition',
                requested_result->>'target_quality_delta',
                requested_result->>'source_quality_delta',
                requested_result->>'unrelated_quality_delta',
                gate_failed,
                requested_result->>'content_hash',
                requested_result,
                (requested_result->>'created_at')::timestamptz
            ) ON CONFLICT (experiment_id) DO NOTHING;
            RETURN TRUE;
        END;
        $$
        """
    )

    op.execute(
        """
        CREATE FUNCTION cognitive_os.record_domain_access(requested_payload jsonb)
        RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, cognitive_os AS $$
        BEGIN
            INSERT INTO cognitive_os.domain_accesses (
                access_id, run_id, record_kind, content_hash, payload_json, created_at
            ) VALUES (
                (requested_payload->>'access_id')::uuid,
                (requested_payload->>'run_id')::uuid,
                requested_payload->>'record_kind',
                requested_payload->>'content_hash',
                requested_payload,
                (requested_payload->>'created_at')::timestamptz
            ) ON CONFLICT (access_id) DO NOTHING;
            RETURN TRUE;
        END;
        $$
        """
    )

    tables = ", ".join(f"cognitive_os.{table.name}" for table in DOMAIN_TABLES)
    op.execute(f"REVOKE ALL ON {tables} FROM cogos_app")
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT ON {tables} TO cogos_app")
    for signature in (
        "cognitive_os.record_domain_pilot_run(jsonb)",
        "cognitive_os.record_domain_transfer_result(jsonb, jsonb)",
        "cognitive_os.record_domain_access(jsonb)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    for signature in (
        "cognitive_os.record_domain_access(jsonb)",
        "cognitive_os.record_domain_transfer_result(jsonb, jsonb)",
        "cognitive_os.record_domain_pilot_run(jsonb)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {signature}")
    op.execute("DROP FUNCTION IF EXISTS cognitive_os.reject_domain_history_mutation() CASCADE")
    connection = op.get_bind()
    for table in reversed(DOMAIN_TABLES):
        table.drop(connection)
