"""Fail-closed host configuration for temporal semantic memory."""

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel


class SemanticMemoryConfiguration(ImmutableContractModel):
    maximum_observations_per_request: int = Field(default=100, ge=1, le=1_000)
    maximum_claims_per_request: int = Field(default=100, ge=1, le=1_000)
    maximum_evidence_links_per_claim: int = Field(default=32, ge=1, le=128)
    maximum_relations_per_request: int = Field(default=200, ge=1, le=2_000)
    maximum_source_spans_per_observation: int = Field(default=16, ge=1, le=64)
    maximum_source_excerpt_bytes: int = Field(default=16_384, ge=1, le=65_536)
    maximum_statement_bytes: int = Field(default=8_192, ge=1, le=65_536)
    maximum_subject_bytes: int = Field(default=1_024, ge=1, le=8_192)
    maximum_object_bytes: int = Field(default=4_096, ge=1, le=65_536)
    maximum_graph_nodes: int = Field(default=5_000, ge=1, le=100_000)
    maximum_graph_edges: int = Field(default=10_000, ge=1, le=200_000)
    maximum_graph_depth: int = Field(default=5, ge=1, le=32)
    maximum_temporal_query_results: int = Field(default=500, ge=1, le=5_000)
    maximum_wiki_claims_per_page: int = Field(default=500, ge=1, le=5_000)
    maximum_wiki_page_bytes: int = Field(default=262_144, ge=1, le=1_048_576)
    maximum_provider_extraction_calls: int = Field(default=2, ge=0, le=10)
    maximum_extraction_elapsed_seconds: int = Field(default=300, ge=1, le=3_600)
    maximum_contradiction_candidates: int = Field(default=200, ge=1, le=2_000)
    supported_confidence_threshold: float = Field(default=0.80, ge=0, le=1)
    disputed_confidence_threshold: float = Field(default=0.40, ge=0, le=1)
    allow_provider_direct_commit: bool = False
    allow_automatic_extraction: bool = False
    allow_automatic_supported_promotion: bool = False
    allow_unknown_predicates: bool = False
    allow_graph_database: bool = False
    allow_generated_wiki_narrative: bool = False
    allow_hybrid_retrieval: bool = False
    fail_closed_on_access_audit_error: bool = True

    @model_validator(mode="after")
    def fail_closed_boundaries(self) -> "SemanticMemoryConfiguration":
        if any(
            (
                self.allow_provider_direct_commit,
                self.allow_automatic_supported_promotion,
                self.allow_unknown_predicates,
                self.allow_graph_database,
                self.allow_generated_wiki_narrative,
                self.allow_hybrid_retrieval,
            )
        ):
            raise ValueError("authoritative provider writes and deferred features are forbidden")
        if self.disputed_confidence_threshold > self.supported_confidence_threshold:
            raise ValueError("disputed confidence threshold exceeds supported threshold")
        return self


def load_semantic_memory_configuration(path: Path) -> SemanticMemoryConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("semantic_memory"), dict):
        raise ValueError("semantic memory configuration requires a semantic_memory mapping")
    return SemanticMemoryConfiguration.model_validate(raw["semantic_memory"])
