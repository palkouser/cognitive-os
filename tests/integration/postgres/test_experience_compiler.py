import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from cognitive_os.application.services.experience_compiler import ExperienceCompilerService
from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.experience.fixtures import build_fixture
from cognitive_os.infrastructure.experience.postgres.health import (
    PostgresExperienceHealthService,
)
from cognitive_os.infrastructure.experience.postgres.repository import (
    PostgresExperienceRepository,
)


@pytest.mark.asyncio
async def test_experience_repository_idempotency_append_only_and_health(engines) -> None:
    app, admin = engines
    request, sources, profiles = build_fixture("repaired-bug-fix")
    repository = PostgresExperienceRepository(app)
    service = ExperienceCompilerService(ExperienceCompiler(sources, profiles), repository)
    first, second = await asyncio.gather(service.compile(request), service.compile(request))
    assert first.manifest == second.manifest
    assert await repository.get_manifest(request.compilation_id) == first.manifest
    assert await repository.list_candidates(request.compilation_id) == first.candidates
    health = await PostgresExperienceHealthService(admin).check()
    assert health.healthy, health.messages
    for statement in (
        "UPDATE cognitive_os.experience_snapshots SET terminal_state='forged'",
        "DELETE FROM cognitive_os.experience_step_assessments",
        "UPDATE cognitive_os.experience_candidate_revisions SET status='routed'",
    ):
        with pytest.raises(DBAPIError):
            async with admin.begin() as connection:
                await connection.execute(text(statement))


@pytest.mark.asyncio
async def test_runtime_role_cannot_mutate_history_or_promote_candidate(engines) -> None:
    app, _ = engines
    request, sources, profiles = build_fixture("direct-success")
    repository = PostgresExperienceRepository(app)
    result = await ExperienceCompilerService(
        ExperienceCompiler(sources, profiles), repository
    ).compile(request)
    candidate_id = result.candidates[0].candidate_id
    for statement in (
        "UPDATE cognitive_os.experience_sources SET source_id='forged'",
        "DELETE FROM cognitive_os.experience_candidates",
        "UPDATE cognitive_os.experience_candidates SET current_status='routed' "
        f"WHERE candidate_id='{candidate_id}'",
    ):
        with pytest.raises(DBAPIError):
            async with app.begin() as connection:
                await connection.execute(text(statement))
    with pytest.raises(DBAPIError):
        async with app.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO cognitive_os.experience_candidates "
                    "SELECT gen_random_uuid(), compilation_id, candidate_type, 2, 'routed', "
                    "target_subsystem, target_schema_version, candidate_hash, payload_json, "
                    "created_at FROM cognitive_os.experience_candidates "
                    "WHERE candidate_id=:candidate_id"
                ),
                {"candidate_id": candidate_id},
            )
