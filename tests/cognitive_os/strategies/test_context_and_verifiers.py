from uuid import NAMESPACE_URL, uuid5

import pytest

from cognitive_os.context.fixtures import sprint11_fixture
from cognitive_os.domain.context import (
    ContextPurpose,
    ContextSourceType,
    HydrationLevel,
    QueryTerm,
    RetrievalMode,
    RetrievalSubquery,
)
from cognitive_os.domain.verifiers import VerifierKind
from cognitive_os.strategies.fixtures import sprint13_verified_strategies
from cognitive_os.strategies.retrieval import StrategyContextRetriever
from cognitive_os.verification.factory import build_builtin_registry
from cognitive_os.verification.strategies import STRATEGY_CAPABILITIES


@pytest.mark.asyncio
async def test_strategy_context_retrieval_hydration_and_access_audit() -> None:
    repository, registry, _, _, _ = await sprint13_verified_strategies()
    request, _, _, _ = sprint11_fixture()
    request = request.model_copy(
        update={
            "context_purpose": ContextPurpose.STRATEGY_EXECUTION,
            "query": "python bug fix",
            "allowed_source_types": (ContextSourceType.STRATEGY,),
        }
    )
    retriever = StrategyContextRetriever(registry, repository)
    subquery = RetrievalSubquery(
        subquery_id=uuid5(NAMESPACE_URL, "strategy-context-test"),
        source_type=ContextSourceType.STRATEGY,
        mode=RetrievalMode.LEXICAL,
        terms=(
            QueryTerm(value="python", normalized="python"),
            QueryTerm(value="bug", normalized="bug"),
        ),
        maximum_results=7,
    )

    candidates = await retriever.retrieve(subquery, request)
    assert candidates
    assert candidates[0].trust_class.value == "verified"
    summary = await retriever.hydrate(candidates[0], HydrationLevel.SUMMARY)
    full = await retriever.hydrate(candidates[0], HydrationLevel.FULL)
    assert summary.content and "Python Bug Fix" in summary.content
    assert full.content and '"skill_bindings"' in full.content
    assert "SKILL.md" not in full.content
    assert len(repository.accesses) == len(candidates) + 2


def test_mandatory_strategy_verifiers_are_registered() -> None:
    registry = build_builtin_registry()
    descriptors = registry.list_by_kind(VerifierKind.STRATEGY)
    assert {item.verifier_id for item in descriptors} == {
        f"strategy.{capability}" for capability in STRATEGY_CAPABILITIES
    }
