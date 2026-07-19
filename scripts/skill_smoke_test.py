"""Run the credential-free deterministic Sprint 12 Skill Engine smoke path."""

import asyncio
import json
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.context.fixtures import sprint11_fixture
from cognitive_os.domain.context import (
    ContextPurpose,
    ContextSourceType,
    HydrationLevel,
    QueryTerm,
    RetrievalMode,
    RetrievalSubquery,
)
from cognitive_os.skills.fixtures import sprint12_verified_skills
from cognitive_os.skills.retrieval import SkillContextRetriever


async def run() -> int:
    repository, registry, artifacts = await sprint12_verified_skills()
    request, _, _, _ = sprint11_fixture()
    request = request.model_copy(
        update={
            "context_purpose": ContextPurpose.SKILL_EXECUTION,
            "query": "repository inspection",
            "allowed_source_types": (ContextSourceType.PROCEDURAL_SKILL,),
        }
    )
    retriever = SkillContextRetriever(
        registry,
        repository,
        artifacts,
        SkillConfiguration(),
    )
    subquery = RetrievalSubquery(
        subquery_id=uuid5(NAMESPACE_URL, "sprint12-skill-smoke"),
        source_type=ContextSourceType.PROCEDURAL_SKILL,
        mode=RetrievalMode.LEXICAL,
        terms=(
            QueryTerm(value="repository", normalized="repository"),
            QueryTerm(value="inspection", normalized="inspection"),
        ),
        maximum_results=8,
    )
    candidates = await retriever.retrieve(subquery, request)
    if not candidates:
        raise RuntimeError("verified skill retrieval returned no candidates")
    hydrated = await retriever.hydrate(candidates[0], HydrationLevel.FULL)
    rows = await repository.query_candidates()
    payload = {
        "verified_skills": len(rows),
        "retrieved": len(candidates),
        "hydrated_hash": hydrated.content_hash,
        "registry_hash": registry.snapshot_hash(),
        "access_records": len(repository.accesses),
    }
    payload["smoke_hash"] = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0 if len(rows) == 8 and hydrated.content else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
