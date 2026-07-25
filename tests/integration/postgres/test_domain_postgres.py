"""Migration 0012 enforces the Gate K persistence invariants in the database itself."""

import importlib

import pytest
from sqlalchemy import text

RUN_ID = "11111111-1111-1111-1111-111111111111"
HASH_A = "a" * 64
HASH_B = "b" * 64


def _run(run_id: str, domain: str = "mathematics", problem_hash: str = HASH_A) -> str:
    return (
        "jsonb_build_object("
        f"'run_id','{run_id}','case_id','case-1','domain','{domain}',"
        f"'status','accepted','problem_hash','{problem_hash}','plan_hash','{HASH_B}',"
        "'created_at','2026-07-24T00:00:00Z')"
    )


def _digest(value: str) -> str:
    """Distinct per-record hash; `content_hash` is unique by constraint."""
    from hashlib import sha256

    return sha256(value.encode()).hexdigest()


def _experiment(experiment_id: str, source: str = "mathematics", target: str = "physics") -> str:
    return (
        "jsonb_build_object("
        f"'experiment_id','{experiment_id}','source_domain','{source}',"
        f"'target_domain','{target}','unrelated_domain','logic',"
        "'component_kind','skill','component_id','repair','component_revision','3',"
        f"'case_manifest','sprint20-domain-ci','seed',0,'environment','cpu-only',"
        f"'content_hash','{_digest('experiment:' + experiment_id)}',"
        "'created_at','2026-07-24T00:00:00Z')"
    )


def _result(experiment_id: str, disposition: str, gates: str) -> str:
    return (
        "jsonb_build_object("
        f"'experiment_id','{experiment_id}','disposition','{disposition}',"
        "'target_quality_delta','0.4','source_quality_delta','-0.9',"
        f"'unrelated_quality_delta','0','hard_gate_failures',{gates},"
        f"'content_hash','{_digest('result:' + experiment_id + disposition)}',"
        "'created_at','2026-07-24T00:00:00Z')"
    )


@pytest.mark.asyncio
async def test_migration_0012_is_present_and_not_empty() -> None:
    module = importlib.import_module("infra.postgres.alembic.versions.0012_create_domain_pilots")
    assert module.revision == "0012"
    assert module.down_revision == "0011"
    from cognitive_os.infrastructure.domains.postgres.tables import DOMAIN_TABLES

    assert len(DOMAIN_TABLES) == 7


@pytest.mark.asyncio
async def test_domain_tables_functions_and_triggers_exist(engines) -> None:
    _, admin = engines
    async with admin.connect() as connection:
        tables = set(
            await connection.scalars(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname='cognitive_os' AND tablename LIKE 'domain\\_%'"
                )
            )
        )
        assert {
            "domain_pilot_runs",
            "domain_problem_references",
            "domain_derivation_references",
            "domain_verification_results",
            "domain_transfer_experiments",
            "domain_transfer_results",
            "domain_accesses",
        } <= tables
        functions = set(
            await connection.scalars(
                text(
                    "SELECT proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                    "WHERE n.nspname='cognitive_os' AND proname LIKE '%domain%'"
                )
            )
        )
        assert {
            "record_domain_pilot_run",
            "record_domain_transfer_result",
            "record_domain_access",
            "reject_domain_history_mutation",
        } <= functions


@pytest.mark.asyncio
async def test_run_recording_rejects_unknown_domains_and_bad_hashes(engines) -> None:
    _, admin = engines
    async with admin.begin() as connection:
        assert await connection.scalar(
            text(f"SELECT cognitive_os.record_domain_pilot_run({_run(RUN_ID)})")
        )
    async with admin.begin() as connection:
        with pytest.raises(Exception, match="unknown domain"):
            await connection.execute(
                text(
                    "SELECT cognitive_os.record_domain_pilot_run("
                    + _run("22222222-2222-2222-2222-222222222222", domain="astrology")
                    + ")"
                )
            )
    async with admin.begin() as connection:
        with pytest.raises(Exception, match="sha256"):
            await connection.execute(
                text(
                    "SELECT cognitive_os.record_domain_pilot_run("
                    + _run("33333333-3333-3333-3333-333333333333", problem_hash="deadbeef")
                    + ")"
                )
            )


@pytest.mark.asyncio
async def test_run_cannot_be_rewritten_with_different_content(engines) -> None:
    _, admin = engines
    async with admin.begin() as connection:
        await connection.execute(
            text(f"SELECT cognitive_os.record_domain_pilot_run({_run(RUN_ID)})")
        )
    async with admin.begin() as connection:
        with pytest.raises(Exception, match="different content"):
            await connection.execute(
                text(
                    "SELECT cognitive_os.record_domain_pilot_run("
                    + _run(RUN_ID, problem_hash="c" * 64)
                    + ")"
                )
            )


@pytest.mark.asyncio
async def test_positive_transfer_cannot_be_stored_with_a_hard_gate_failure(engines) -> None:
    _, admin = engines
    experiment_id = "44444444-4444-4444-4444-444444444444"
    async with admin.begin() as connection:
        with pytest.raises(Exception, match="hard gate"):
            await connection.execute(
                text(
                    "SELECT cognitive_os.record_domain_transfer_result("
                    + _experiment(experiment_id)
                    + ", "
                    + _result(
                        experiment_id,
                        "positive_transfer",
                        "jsonb_build_array('source retention regressed')",
                    )
                    + ")"
                )
            )
    # The same measurement recorded honestly as negative transfer is accepted.
    honest_id = "55555555-5555-5555-5555-555555555555"
    async with admin.begin() as connection:
        assert await connection.scalar(
            text(
                "SELECT cognitive_os.record_domain_transfer_result("
                + _experiment(honest_id)
                + ", "
                + _result(
                    honest_id,
                    "negative_transfer",
                    "jsonb_build_array('source retention regressed')",
                )
                + ")"
            )
        )


@pytest.mark.asyncio
async def test_transfer_experiment_requires_three_distinct_domains(engines) -> None:
    _, admin = engines
    experiment_id = "66666666-6666-6666-6666-666666666666"
    async with admin.begin() as connection:
        with pytest.raises(Exception, match="ck_domain_transfer_distinct_domains"):
            await connection.execute(
                text(
                    "SELECT cognitive_os.record_domain_transfer_result("
                    + _experiment(experiment_id, source="physics", target="physics")
                    + ", "
                    + _result(experiment_id, "neutral_transfer", "jsonb_build_array()")
                    + ")"
                )
            )


@pytest.mark.asyncio
async def test_recorded_evidence_is_append_only(engines) -> None:
    _, admin = engines
    experiment_id = "77777777-7777-7777-7777-777777777777"
    async with admin.begin() as connection:
        await connection.execute(
            text(
                "SELECT cognitive_os.record_domain_transfer_result("
                + _experiment(experiment_id)
                + ", "
                + _result(experiment_id, "neutral_transfer", "jsonb_build_array()")
                + ")"
            )
        )
    for statement in (
        "UPDATE cognitive_os.domain_transfer_results SET disposition='positive_transfer' "
        f"WHERE experiment_id='{experiment_id}'",
        f"DELETE FROM cognitive_os.domain_transfer_results WHERE experiment_id='{experiment_id}'",
    ):
        async with admin.begin() as connection:
            with pytest.raises(Exception, match="append-only"):
                await connection.execute(text(statement))


@pytest.mark.asyncio
async def test_domain_health_reports_healthy_after_recording_evidence(engines) -> None:
    from cognitive_os.infrastructure.domains.postgres.health import PostgresDomainHealthService

    _, admin = engines
    run_id = "88888888-8888-8888-8888-888888888888"
    experiment_id = "99999999-9999-9999-9999-999999999999"
    async with admin.begin() as connection:
        await connection.execute(
            text(f"SELECT cognitive_os.record_domain_pilot_run({_run(run_id)})")
        )
        await connection.execute(
            text(
                "SELECT cognitive_os.record_domain_transfer_result("
                + _experiment(experiment_id)
                + ", "
                + _result(experiment_id, "neutral_transfer", "jsonb_build_array()")
                + ")"
            )
        )
    health = await PostgresDomainHealthService(admin).check()
    assert health.healthy, health.messages
    assert health.table_count == 7
    assert health.append_only_trigger_count == 6
    assert health.controlled_function_count == 3
    assert health.orphan_evidence_count == 0
    assert health.orphan_transfer_result_count == 0
    assert health.hard_gate_violation_count == 0


@pytest.mark.asyncio
async def test_application_role_has_read_only_table_access(engines) -> None:
    _, admin = engines
    async with admin.connect() as connection:
        privileges = set(
            await connection.scalars(
                text(
                    "SELECT privilege_type FROM information_schema.table_privileges "
                    "WHERE grantee='cogos_app' AND table_schema='cognitive_os' "
                    "AND table_name='domain_pilot_runs'"
                )
            )
        )
    assert privileges == {"SELECT"}, privileges
