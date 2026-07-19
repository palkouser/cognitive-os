from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.skill_adapter import skill_benchmark_case
from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.context.fixtures import sprint11_fixture
from cognitive_os.domain.benchmarks import BenchmarkCaseStatus
from cognitive_os.domain.context import (
    ContextSourceType,
    HydrationLevel,
    QueryTerm,
    RetrievalMode,
    RetrievalSubquery,
)
from cognitive_os.skills.fixtures import sprint12_verified_skills
from cognitive_os.skills.retrieval import SkillContextRetriever


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,count",
    (
        ("benchmarks/manifests/sprint12-skill-ci.yaml", 8),
        ("benchmarks/manifests/sprint12-skill-seed.yaml", 32),
    ),
)
async def test_skill_benchmark_manifests(path: str, count: int) -> None:
    manifest = load_manifest(Path(path))
    results = tuple([await skill_benchmark_case(case) for case in manifest.cases])
    assert len(results) == count
    assert all(item.status is BenchmarkCaseStatus.PASSED for item in results)
    assert all(item.metrics["permission_expansions"] == 0 for item in results)


@pytest.mark.asyncio
async def test_verified_skill_progressive_context_hydration_records_access() -> None:
    repository, registry, artifacts = await sprint12_verified_skills()
    request = sprint11_fixture()[0].model_copy(
        update={
            "query": "repository inspection",
            "allowed_source_types": (ContextSourceType.PROCEDURAL_SKILL,),
        }
    )
    retriever = SkillContextRetriever(registry, repository, artifacts, SkillConfiguration())
    subquery = RetrievalSubquery(
        subquery_id=uuid5(NAMESPACE_URL, "skill-context-test"),
        source_type=ContextSourceType.PROCEDURAL_SKILL,
        mode=RetrievalMode.LEXICAL,
        terms=(QueryTerm(value="repository", normalized="repository"),),
        maximum_results=8,
    )
    candidates = await retriever.retrieve(subquery, request)
    assert candidates
    assert all(item.trust_class.value == "verified" for item in candidates)
    hydrated = await retriever.hydrate(candidates[0], HydrationLevel.FULL)
    assert hydrated.content
    assert hydrated.source_revision == "3"
    assert len(repository.accesses) == len(candidates) + 1
