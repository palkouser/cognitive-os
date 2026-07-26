"""Create the durable learned evidence store.

Nine tables: one derived projection and eight append-only ledgers, plus the triggers,
constraints and grants that make the authority model of ADR 0086 structural rather than
conventional.

The projection is the only table a controlled function may update. Every ledger rejects
UPDATE and DELETE outright, and `cogos_app` holds SELECT plus EXECUTE on the controlled
functions — never direct write access — so an application-role bug cannot rewrite
evidence.

Revision ID: 0014
Revises: 0013
"""

from alembic import op

from cognitive_os.infrastructure.learned.postgres.tables import (
    LEARNED_APPEND_ONLY_TABLES,
    LEARNED_EVIDENCE_TABLES,
)

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

_SCHEMA = "cognitive_os"


def upgrade() -> None:
    for table in LEARNED_EVIDENCE_TABLES:
        table.create(op.get_bind(), checkfirst=False)

    # Append-only enforcement. The projection is deliberately excluded: it is derived
    # data that a controlled function must be able to update.
    op.execute(
        f"""
        CREATE FUNCTION {_SCHEMA}.reject_learned_evidence_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Learned evidence is append-only';
        END;
        $$
        """
    )
    for table in LEARNED_APPEND_ONLY_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON {_SCHEMA}.{table.name}
            FOR EACH ROW EXECUTE FUNCTION {_SCHEMA}.reject_learned_evidence_mutation()
            """
        )

    # The lifecycle transition policy, in the database as well as in Python.
    #
    # `cogos_app` holds EXECUTE on the controlled functions, so a caller that bypassed
    # the application service could otherwise drive any state change it liked. Keeping
    # the table here closes that. It is a second copy of
    # `cognitive_os.learning.registry`, and the risk of a second copy is drift, so
    # `test_sql_transition_policy_matches_python` compares the two exhaustively.
    #
    # `DISABLED -> ACTIVE` is legal only when a rollback target is named, which is the
    # one deliberate exception ADR 0086 records.
    op.execute(
        f"""
        CREATE FUNCTION {_SCHEMA}.learned_transition_is_legal(
            state_before text, state_after text, rollback_target integer
        )
        RETURNS boolean
        LANGUAGE sql IMMUTABLE AS $$
            SELECT CASE
                WHEN state_before IS NULL THEN state_after = 'registered'
                WHEN state_before = 'disabled' AND state_after = 'active'
                     AND rollback_target IS NOT NULL THEN true
                WHEN state_before = 'registered' THEN state_after IN ('shadow', 'retracted')
                WHEN state_before = 'shadow'
                     THEN state_after IN ('verified', 'disabled', 'retracted')
                WHEN state_before = 'verified'
                     THEN state_after IN ('active', 'disabled', 'retracted')
                WHEN state_before = 'active' THEN state_after IN ('disabled', 'retracted')
                WHEN state_before = 'disabled' THEN state_after IN ('shadow', 'retracted')
                WHEN state_before = 'retracted' THEN false
                ELSE false
            END
        $$
        """
    )

    # Registering a component is one controlled operation: revision 1 is appended and
    # the projection created together, so a projection row can never exist without the
    # history that authorises it. Re-registering identical content is idempotent;
    # reusing the key with different content raises, because a retry must not rewrite
    # history.
    op.execute(
        f"""
        CREATE FUNCTION {_SCHEMA}.register_learned_component(requested jsonb)
        RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, {_SCHEMA} AS $$
        DECLARE
            requested_component text;
            existing_hash text;
        BEGIN
            requested_component := requested->>'component_id';
            IF requested_component IS NULL THEN
                RAISE EXCEPTION 'a learned component registration needs a component_id';
            END IF;
            -- Registration is the entry point, not a shortcut past the lifecycle: a
            -- component cannot be created already active, shadowed or verified.
            IF NOT {_SCHEMA}.learned_transition_is_legal(
                NULL, requested->>'state_after', NULL
            ) THEN
                RAISE EXCEPTION
                    'illegal learned transition for %: registration cannot start in %',
                    requested_component, requested->>'state_after';
            END IF;

            SELECT content_hash INTO existing_hash
            FROM {_SCHEMA}.learned_component_revisions
            WHERE idempotency_key = requested->>'idempotency_key';

            IF existing_hash IS NOT NULL THEN
                IF existing_hash IS DISTINCT FROM requested->>'content_hash' THEN
                    RAISE EXCEPTION
                        'idempotency key reused with different content for %',
                        requested_component;
                END IF;
                RETURN false;
            END IF;

            INSERT INTO {_SCHEMA}.learned_component_revisions (
                component_id, revision, previous_revision, surface, state_before,
                state_after, descriptor_hash, artifact_lineage_id,
                promotion_assessment_hash, activation_approval_hash,
                rollback_target_revision, actor, authority, reason, idempotency_key,
                payload_json, content_hash, recorded_at
            ) VALUES (
                requested_component, 1, NULL, requested->>'surface', NULL,
                requested->>'state_after', requested->>'descriptor_hash',
                (requested->>'artifact_lineage_id')::uuid,
                requested->>'promotion_assessment_hash',
                requested->>'activation_approval_hash',
                (requested->>'rollback_target_revision')::int,
                requested->>'actor', requested->>'authority', requested->>'reason',
                requested->>'idempotency_key',
                -- `descriptor_version` belongs to the projection, not to the revision
                -- contract. Storing it in `payload_json` would make every read of the
                -- authoritative ledger fail contract validation.
                requested - 'descriptor_version', requested->>'content_hash',
                COALESCE((requested->>'recorded_at')::timestamptz, now())
            );

            INSERT INTO {_SCHEMA}.learned_components (
                component_id, surface, descriptor_version, current_revision,
                current_state, descriptor_hash, artifact_lineage_id, content_hash,
                created_at, updated_at
            ) VALUES (
                requested_component, requested->>'surface',
                COALESCE(requested->>'descriptor_version', '1'), 1,
                requested->>'state_after', requested->>'descriptor_hash',
                (requested->>'artifact_lineage_id')::uuid, requested->>'content_hash',
                now(), now()
            );
            RETURN true;
        END;
        $$
        """
    )

    # One lifecycle step under compare-and-swap. The expected revision is checked
    # against the projection under a row lock, so two concurrent callers cannot both
    # believe they advanced from the same state.
    op.execute(
        f"""
        CREATE FUNCTION {_SCHEMA}.advance_learned_component(
            requested jsonb, expected_revision integer
        )
        RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, {_SCHEMA} AS $$
        DECLARE
            requested_component text;
            current_rev integer;
            current_state_value text;
            existing_hash text;
        BEGIN
            requested_component := requested->>'component_id';

            SELECT content_hash INTO existing_hash
            FROM {_SCHEMA}.learned_component_revisions
            WHERE idempotency_key = requested->>'idempotency_key';
            IF existing_hash IS NOT NULL THEN
                IF existing_hash IS DISTINCT FROM requested->>'content_hash' THEN
                    RAISE EXCEPTION
                        'idempotency key reused with different content for %',
                        requested_component;
                END IF;
                RETURN false;
            END IF;

            SELECT current_revision, current_state
              INTO current_rev, current_state_value
            FROM {_SCHEMA}.learned_components
            WHERE component_id = requested_component
            FOR UPDATE;

            IF current_rev IS NULL THEN
                RAISE EXCEPTION 'learned component % is not registered', requested_component;
            END IF;
            IF current_rev <> expected_revision THEN
                RAISE EXCEPTION
                    'stale revision for %: expected %, found %',
                    requested_component, expected_revision, current_rev;
            END IF;
            IF current_state_value IS DISTINCT FROM requested->>'state_before' THEN
                RAISE EXCEPTION
                    'state before mismatch for %: projection holds %, request claims %',
                    requested_component, current_state_value, requested->>'state_before';
            END IF;
            IF NOT {_SCHEMA}.learned_transition_is_legal(
                current_state_value,
                requested->>'state_after',
                (requested->>'rollback_target_revision')::int
            ) THEN
                RAISE EXCEPTION
                    'illegal learned transition for %: % -> %',
                    requested_component, current_state_value, requested->>'state_after';
            END IF;

            INSERT INTO {_SCHEMA}.learned_component_revisions (
                component_id, revision, previous_revision, surface, state_before,
                state_after, descriptor_hash, artifact_lineage_id,
                promotion_assessment_hash, activation_approval_hash,
                rollback_target_revision, actor, authority, reason, idempotency_key,
                payload_json, content_hash, recorded_at
            ) VALUES (
                requested_component, (requested->>'revision')::int, current_rev,
                requested->>'surface', requested->>'state_before',
                requested->>'state_after', requested->>'descriptor_hash',
                (requested->>'artifact_lineage_id')::uuid,
                requested->>'promotion_assessment_hash',
                requested->>'activation_approval_hash',
                (requested->>'rollback_target_revision')::int,
                requested->>'actor', requested->>'authority', requested->>'reason',
                requested->>'idempotency_key', requested, requested->>'content_hash',
                COALESCE((requested->>'recorded_at')::timestamptz, now())
            );

            UPDATE {_SCHEMA}.learned_components
            SET current_revision = (requested->>'revision')::int,
                current_state = requested->>'state_after',
                descriptor_hash = requested->>'descriptor_hash',
                artifact_lineage_id = COALESCE(
                    (requested->>'artifact_lineage_id')::uuid, artifact_lineage_id
                ),
                content_hash = requested->>'content_hash',
                updated_at = now()
            WHERE component_id = requested_component;
            RETURN true;
        END;
        $$
        """
    )

    # Immutable ledger appends. One function per ledger keeps the grant surface exact:
    # `cogos_app` can append evidence without holding INSERT on the tables themselves.
    #
    # `jsonb_populate_record` rather than a built column list: it maps JSON keys onto the
    # table's own row type, so every value lands with the column's declared type instead
    # of as text. Building `($1->>'key')` expressions is the obvious alternative and is
    # wrong — it yields text, and PostgreSQL refuses to assign text to a uuid, integer or
    # timestamptz column, so every append would fail at runtime while the migration
    # itself applied cleanly.
    for name, table, key_column in (
        ("record_learned_evidence", "learned_evidence_records", "evidence_id"),
        ("record_learned_observation", "learned_observations", "observation_id"),
        ("record_learned_artifact_lineage", "learned_artifacts", "lineage_id"),
        ("record_learned_activation", "learned_activation_history", "receipt_id"),
        ("record_learned_approval", "learned_activation_approvals", "approval_id"),
        ("record_learned_access", "learned_accesses", "access_id"),
        ("record_learned_dataset", "learned_datasets", "dataset_id"),
    ):
        op.execute(
            f"""
            CREATE FUNCTION {_SCHEMA}.{name}(requested jsonb)
            RETURNS boolean
            LANGUAGE plpgsql SECURITY DEFINER
            SET search_path = pg_catalog, {_SCHEMA} AS $$
            DECLARE existing_hash text;
            BEGIN
                SELECT content_hash INTO existing_hash
                FROM {_SCHEMA}.{table}
                WHERE {key_column} = (requested->>'{key_column}')::uuid;

                IF existing_hash IS NOT NULL THEN
                    IF existing_hash IS DISTINCT FROM requested->>'content_hash' THEN
                        RAISE EXCEPTION
                            'immutable {table} record % cannot be replaced with '
                            'different content', requested->>'{key_column}';
                    END IF;
                    RETURN false;
                END IF;

                INSERT INTO {_SCHEMA}.{table}
                SELECT * FROM jsonb_populate_record(
                    NULL::{_SCHEMA}.{table},
                    requested || jsonb_build_object('payload_json', requested)
                );
                RETURN true;
            END;
            $$
            """
        )

    tables = ", ".join(f"{_SCHEMA}.{table.name}" for table in LEARNED_EVIDENCE_TABLES)
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT ON {tables} TO cogos_app")
    for signature in (
        f"{_SCHEMA}.register_learned_component(jsonb)",
        f"{_SCHEMA}.advance_learned_component(jsonb, integer)",
        f"{_SCHEMA}.record_learned_evidence(jsonb)",
        f"{_SCHEMA}.record_learned_observation(jsonb)",
        f"{_SCHEMA}.record_learned_artifact_lineage(jsonb)",
        f"{_SCHEMA}.record_learned_activation(jsonb)",
        f"{_SCHEMA}.record_learned_approval(jsonb)",
        f"{_SCHEMA}.record_learned_access(jsonb)",
        f"{_SCHEMA}.record_learned_dataset(jsonb)",
        f"{_SCHEMA}.learned_transition_is_legal(text, text, integer)",
    ):
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO cogos_app")


def downgrade() -> None:
    for signature in (
        "register_learned_component(jsonb)",
        "advance_learned_component(jsonb, integer)",
        "record_learned_evidence(jsonb)",
        "record_learned_observation(jsonb)",
        "record_learned_artifact_lineage(jsonb)",
        "record_learned_activation(jsonb)",
        "record_learned_approval(jsonb)",
        "record_learned_access(jsonb)",
        "record_learned_dataset(jsonb)",
        "learned_transition_is_legal(text, text, integer)",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {_SCHEMA}.{signature}")
    for table in LEARNED_APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table.name}_append_only ON {_SCHEMA}.{table.name}")
    op.execute(f"DROP FUNCTION IF EXISTS {_SCHEMA}.reject_learned_evidence_mutation()")
    for table in reversed(LEARNED_EVIDENCE_TABLES):
        table.drop(op.get_bind(), checkfirst=True)
