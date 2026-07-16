"""Fail-closed host configuration for deterministic Context Builder v1."""

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel


class ContextRankingConfiguration(ImmutableContractModel):
    rrf_k: int = Field(default=60, ge=1, le=10_000)
    score_precision: int = Field(default=9, ge=1, le=18)
    trust_weight: float = Field(default=0.20, ge=0, le=1, allow_inf_nan=False)
    scope_weight: float = Field(default=0.10, ge=0, le=1, allow_inf_nan=False)
    verification_weight: float = Field(default=0.15, ge=0, le=1, allow_inf_nan=False)
    recency_weight: float = Field(default=0.10, ge=0, le=1, allow_inf_nan=False)
    salience_weight: float = Field(default=0.10, ge=0, le=1, allow_inf_nan=False)
    graph_weight: float = Field(default=0.05, ge=0, le=1, allow_inf_nan=False)
    contradiction_weight: float = Field(default=0.20, ge=0, le=1, allow_inf_nan=False)


class ContextConfiguration(ImmutableContractModel):
    maximum_context_builds_per_task: int = Field(default=16, ge=1, le=16)
    maximum_retriever_calls_per_build: int = Field(default=24, ge=1, le=24)
    maximum_parallel_retrievers: int = Field(default=4, ge=1, le=4)
    maximum_candidates: int = Field(default=1_000, ge=1, le=1_000)
    maximum_candidates_per_retriever: int = Field(default=200, ge=1, le=200)
    maximum_hydrated_candidates: int = Field(default=128, ge=1, le=128)
    maximum_selected_items: int = Field(default=64, ge=1, le=64)
    maximum_items_per_source_type: int = Field(default=12, ge=1, le=12)
    maximum_source_excerpt_bytes: int = Field(default=32_768, ge=1, le=32_768)
    maximum_total_hydrated_bytes: int = Field(default=1_048_576, ge=1, le=1_048_576)
    maximum_graph_depth: int = Field(default=3, ge=1, le=3)
    maximum_graph_nodes: int = Field(default=500, ge=1, le=500)
    maximum_build_seconds: int = Field(default=30, ge=1, le=30)
    maximum_trace_bytes: int = Field(default=1_048_576, ge=1, le=1_048_576)
    minimum_recent_items: int = Field(default=2, ge=0, le=64)
    minimum_evidence_items: int = Field(default=2, ge=0, le=64)
    minimum_source_types: int = Field(default=2, ge=1, le=16)
    default_reserved_output_tokens: int = Field(default=4_096, ge=1, le=131_072)
    default_context_limit: int = Field(default=32_768, ge=1, le=131_072)
    minimum_safety_margin_tokens: int = Field(default=1_024, ge=1, le=32_768)
    allow_external_sources: bool = False
    allow_unverified_sources: bool = True
    allow_disputed_sources: bool = True
    allow_network_retrieval: bool = False
    allow_approximate_vector_search: bool = False
    allow_learned_ranking: bool = False
    allow_provider_query_expansion: bool = False
    allow_provider_retriever_selection: bool = False
    allow_automatic_memory_write: bool = False
    ranking: ContextRankingConfiguration = ContextRankingConfiguration()

    @model_validator(mode="after")
    def fail_closed_boundaries(self) -> "ContextConfiguration":
        if any(
            (
                self.allow_network_retrieval,
                self.allow_approximate_vector_search,
                self.allow_learned_ranking,
                self.allow_provider_query_expansion,
                self.allow_provider_retriever_selection,
                self.allow_automatic_memory_write,
            )
        ):
            raise ValueError(
                "network, ANN, learned, provider-controlled, and write paths are sealed"
            )
        if self.maximum_candidates_per_retriever > self.maximum_candidates:
            raise ValueError("per-retriever candidates exceed the build maximum")
        if self.maximum_selected_items > self.maximum_candidates:
            raise ValueError("selected items exceed the candidate maximum")
        if (
            self.default_reserved_output_tokens + self.minimum_safety_margin_tokens
            >= self.default_context_limit
        ):
            raise ValueError("fixed token reservations leave no context capacity")
        return self


def load_context_configuration(path: Path) -> ContextConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("context"), dict):
        raise ValueError("context configuration requires a context mapping")
    return ContextConfiguration.model_validate(raw["context"])
