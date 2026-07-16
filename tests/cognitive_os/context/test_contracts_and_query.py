import pytest
from pydantic import ValidationError

from cognitive_os.config.context_config import ContextConfiguration
from cognitive_os.context.query import build_query_plan
from cognitive_os.domain.context import ContextBudget, ContextSourceType

from .helpers import context_request


def test_configuration_is_fail_closed_and_forbids_unknown_fields() -> None:
    configuration = ContextConfiguration()
    assert not configuration.allow_network_retrieval
    assert not configuration.allow_approximate_vector_search
    assert not configuration.allow_learned_ranking
    with pytest.raises(ValidationError):
        ContextConfiguration.model_validate({"unknown": True})
    with pytest.raises(ValidationError):
        ContextConfiguration(allow_provider_retriever_selection=True)


def test_budget_deducts_fixed_content_before_retrieval() -> None:
    budget = ContextBudget(
        provider_context_limit=10_000,
        reserved_output_tokens=2_000,
        system_instruction_tokens=500,
        task_and_plan_tokens=1_000,
        safety_margin_tokens=500,
        maximum_retriever_calls=4,
        maximum_candidates=10,
        maximum_items=4,
        maximum_items_per_source=2,
        minimum_recent_items=0,
        minimum_evidence_items=0,
        maximum_elapsed_seconds=10,
    )
    assert budget.available_tokens == 6_000
    with pytest.raises(ValidationError):
        budget.provider_context_limit = 20_000  # type: ignore[misc]


def test_query_decomposition_is_bounded_and_deterministic() -> None:
    request = context_request(
        ContextSourceType.TASK_STATE,
        ContextSourceType.EXECUTION_PLAN,
        ContextSourceType.MEMORY,
        ContextSourceType.SEMANTIC_GRAPH,
        ContextSourceType.REPOSITORY_INDEX,
    )
    first = build_query_plan(request)
    second = build_query_plan(request)
    assert first == second
    assert first.canonical_hash() == second.canonical_hash()
    assert len(first.subqueries) == 7
    assert [(item.source_type.value, item.mode.value) for item in first.subqueries] == sorted(
        (item.source_type.value, item.mode.value) for item in first.subqueries
    )
