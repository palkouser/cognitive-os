"""Create the append-only provider-output governance ledger.

One table, one append-only trigger, one controlled write function, and the grants that keep
`cogos_app` on SELECT plus EXECUTE. A governance decision is corrected by appending a
revision, never by updating a row, so UPDATE and DELETE are refused outright.

The controlled function uses `jsonb_populate_record`, and that is not a style preference.
Migration 0014 shipped with generic record functions built from `($1->>'key')` expressions,
which yield `text`; PostgreSQL then refuses to assign text to a uuid, integer, boolean or
timestamptz column, so every append failed at runtime while the migration itself applied
cleanly. `test_record_provider_output_writes_every_declared_type` invokes this function
directly with all of those types, because applying a migration is not evidence that its
functions work. See ADR 0087.

Revision ID: 0015
Revises: 0014
"""

from alembic import op

from cognitive_os.infrastructure.learned.postgres.provider_output_tables import (
    PROVIDER_OUTPUT_TABLES,
)

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

_SCHEMA = "cognitive_os"


def upgrade() -> None:
    for table in PROVIDER_OUTPUT_TABLES:
        table.create(op.get_bind(), checkfirst=False)

    op.execute(
        f"""
        CREATE FUNCTION {_SCHEMA}.reject_provider_output_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Provider output governance is append-only';
        END;
        $$
        """
    )
    for table in PROVIDER_OUTPUT_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table.name}_append_only
            BEFORE UPDATE OR DELETE ON {_SCHEMA}.{table.name}
            FOR EACH ROW EXECUTE FUNCTION {_SCHEMA}.reject_provider_output_mutation()
            """
        )

    # One controlled append. Idempotency, revision continuity and content-hash agreement are
    # all decided here rather than by the caller, because `cogos_app` holds EXECUTE on this
    # function and nothing else — a caller that built the INSERT itself could not reach the
    # table at all.
    #
    # Returns true when a row was appended and false on an idempotent replay, matching the
    # 0014 record functions so the repository layer reads the same either way.
    op.execute(
        f"""
        CREATE FUNCTION {_SCHEMA}.record_provider_output(requested jsonb)
        RETURNS boolean
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, {_SCHEMA} AS $$
        DECLARE
            requested_revision_id uuid;
            requested_output_id uuid;
            requested_revision integer;
            existing_hash text;
            previous_revision integer;
            previous_output_id uuid;
            latest_revision integer;
        BEGIN
            requested_revision_id := (requested->>'provider_output_revision_id')::uuid;
            requested_output_id := (requested->>'provider_output_id')::uuid;
            requested_revision := (requested->>'revision')::int;

            IF requested_revision_id IS NULL OR requested_output_id IS NULL
               OR requested_revision IS NULL THEN
                RAISE EXCEPTION
                    'a provider output revision needs an identity, an output id and a '
                    'revision number';
            END IF;

            -- Idempotent replay by row identity.
            SELECT content_hash INTO existing_hash
            FROM {_SCHEMA}.provider_output_records
            WHERE provider_output_revision_id = requested_revision_id;
            IF existing_hash IS NOT NULL THEN
                IF existing_hash IS DISTINCT FROM requested->>'content_hash' THEN
                    RAISE EXCEPTION
                        'immutable provider_output_records revision % cannot be replaced '
                        'with different content', requested_revision_id;
                END IF;
                RETURN false;
            END IF;

            -- Idempotent replay by key. Same content is a free no-op; different content is
            -- refused, because a retry must not rewrite a governance decision.
            SELECT content_hash INTO existing_hash
            FROM {_SCHEMA}.provider_output_records
            WHERE idempotency_key = requested->>'idempotency_key';
            IF existing_hash IS NOT NULL THEN
                IF existing_hash IS DISTINCT FROM requested->>'content_hash' THEN
                    RAISE EXCEPTION
                        'idempotency key reused with different content for provider '
                        'output %', requested_output_id;
                END IF;
                RETURN false;
            END IF;

            -- Revision continuity, serialized per output ID. A transaction-scoped advisory
            -- lock rather than `FOR UPDATE`: the head is an aggregate, PostgreSQL refuses
            -- `FOR UPDATE` with one, and a row lock could not serialize the case that
            -- actually races — two callers both appending the *first* revision, where there
            -- is no row to lock. `uq_provider_output_revision` is still the backstop.
            PERFORM pg_advisory_xact_lock(
                hashtextextended(requested_output_id::text, 0)
            );

            SELECT max(revision) INTO latest_revision
            FROM {_SCHEMA}.provider_output_records
            WHERE provider_output_id = requested_output_id;

            IF requested_revision = 1 THEN
                IF latest_revision IS NOT NULL THEN
                    RAISE EXCEPTION
                        'revision conflict for provider output %: revision 1 already exists',
                        requested_output_id;
                END IF;
            ELSE
                IF latest_revision IS NULL THEN
                    RAISE EXCEPTION
                        'revision conflict for provider output %: revision % has no history',
                        requested_output_id, requested_revision;
                END IF;
                IF requested_revision <> latest_revision + 1 THEN
                    RAISE EXCEPTION
                        'revision conflict for provider output %: expected revision %, '
                        'requested %',
                        requested_output_id, latest_revision + 1, requested_revision;
                END IF;
                SELECT revision, provider_output_id
                  INTO previous_revision, previous_output_id
                FROM {_SCHEMA}.provider_output_records
                WHERE provider_output_revision_id
                      = (requested->>'previous_revision_id')::uuid;
                IF previous_revision IS NULL THEN
                    RAISE EXCEPTION
                        'broken lineage for provider output %: the named predecessor does '
                        'not exist', requested_output_id;
                END IF;
                IF previous_output_id IS DISTINCT FROM requested_output_id
                   OR previous_revision <> requested_revision - 1 THEN
                    RAISE EXCEPTION
                        'broken lineage for provider output %: the named predecessor is '
                        'not its immediate predecessor', requested_output_id;
                END IF;
            END IF;

            -- `jsonb_populate_record` maps JSON keys onto the table's own row type, so a
            -- uuid lands as a uuid and a timestamptz as a timestamptz. See the module
            -- docstring for what the obvious alternative did in 0014.
            INSERT INTO {_SCHEMA}.provider_output_records
            SELECT * FROM jsonb_populate_record(
                NULL::{_SCHEMA}.provider_output_records,
                requested || jsonb_build_object('payload_json', requested)
            );
            RETURN true;
        END;
        $$
        """
    )

    tables = ", ".join(f"{_SCHEMA}.{table.name}" for table in PROVIDER_OUTPUT_TABLES)
    op.execute(f"GRANT ALL PRIVILEGES ON {tables} TO cogos_owner")
    op.execute(f"GRANT SELECT ON {tables} TO cogos_app")
    op.execute(f"GRANT EXECUTE ON FUNCTION {_SCHEMA}.record_provider_output(jsonb) TO cogos_app")


def downgrade() -> None:
    op.execute(f"DROP FUNCTION IF EXISTS {_SCHEMA}.record_provider_output(jsonb)")
    for table in PROVIDER_OUTPUT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table.name}_append_only ON {_SCHEMA}.{table.name}")
    op.execute(f"DROP FUNCTION IF EXISTS {_SCHEMA}.reject_provider_output_mutation()")
    for table in reversed(PROVIDER_OUTPUT_TABLES):
        table.drop(op.get_bind(), checkfirst=True)
