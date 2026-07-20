import asyncio

import pytest

from cognitive_os.application.services.experience_compiler import ExperienceCompilerService
from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.experience.errors import ExperienceConflictError
from cognitive_os.experience.fixtures import build_fixture
from cognitive_os.experience.repository import InMemoryExperienceRepository


def test_service_persists_once_and_recompiles_idempotently() -> None:
    async def run() -> None:
        request, sources, profiles = build_fixture("direct-success")
        repository = InMemoryExperienceRepository()
        service = ExperienceCompilerService(ExperienceCompiler(sources, profiles), repository)
        first = await service.compile(request)
        second = await service.compile(request)
        assert first.manifest == second.manifest
        assert await repository.get_manifest(request.compilation_id) == first.manifest
        assert await repository.list_candidates(request.compilation_id) == first.candidates
        assert len(repository.accesses) == len(first.snapshot.source_refs) + 2

    asyncio.run(run())


def test_append_only_repository_rejects_changed_snapshot() -> None:
    async def run() -> None:
        request, sources, profiles = build_fixture("direct-success")
        result = ExperienceCompiler(sources, profiles).compile(request)
        repository = InMemoryExperienceRepository()
        await repository.create_compilation(request)
        await repository.record_snapshot(request.compilation_id, result.snapshot)
        changed = result.snapshot.model_copy(update={"terminal_state": "failed"})
        with pytest.raises(ExperienceConflictError):
            await repository.record_snapshot(request.compilation_id, changed)

    asyncio.run(run())
