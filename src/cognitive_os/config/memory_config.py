"""Fail-closed configuration for Governed Memory Plane v1."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field, field_validator, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.memory import HNSW_MAXIMUM_DIMENSIONS


class MemoryBenchmarkConfiguration(ImmutableContractModel):
    maximum_records: int = Field(default=10_000, ge=1, le=1_000_000)
    maximum_duration_seconds: int = Field(default=600, ge=1, le=86_400)


class EmbeddingProviderConfiguration(ImmutableContractModel):
    provider_type: str = Field(pattern=r"^(deterministic|sentence_transformers)$")
    model_id: str = Field(min_length=1, max_length=256)
    dimension: int = Field(ge=1, le=4096)
    enabled: bool = True
    local_model_path: Path | None = None
    local_model_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def local_provider_is_preconfigured(self) -> EmbeddingProviderConfiguration:
        if self.provider_type == "sentence_transformers":
            if self.local_model_path is None or not self.local_model_path.is_absolute():
                raise ValueError("local embedding model path must be absolute and preconfigured")
            if self.local_model_digest is None:
                raise ValueError("local embedding model digest is required")
        elif self.local_model_path is not None or self.local_model_digest is not None:
            raise ValueError("deterministic provider cannot declare a local model")
        return self


class MemoryConfiguration(ImmutableContractModel):
    maximum_inline_content_bytes: int = Field(default=65_536, ge=1)
    maximum_search_text_bytes: int = Field(default=32_768, ge=1)
    maximum_sources_per_revision: int = Field(default=64, ge=1, le=64)
    maximum_revision_depth: int = Field(default=1_000, ge=1, le=1_000)
    maximum_query_results: int = Field(default=100, ge=1, le=100)
    maximum_query_candidates: int = Field(default=1_000, ge=1, le=1_000)
    maximum_full_text_query_length: int = Field(default=512, ge=1, le=512)
    maximum_vector_query_dimension: int = Field(default=4_096, ge=1, le=4_096)
    maximum_embedding_batch_size: int = Field(default=64, ge=1, le=64)
    maximum_parallel_retrieval_workers: int = Field(default=4, ge=1, le=4)
    default_query_limit: int = Field(default=20, ge=1, le=100)
    allowed_memory_types: frozenset[str] = Field(min_length=1)
    allowed_scope_types: frozenset[str] = Field(min_length=1)
    maximum_provider_sensitivity: str = Field(pattern=r"^(public|internal|confidential)$")
    allow_provider_direct_write: bool = False
    allow_automatic_task_ingestion: bool = False
    allow_automatic_promotion: bool = False
    allow_network_model_download: bool = False
    #: Dimensions that carry an approximate index and may therefore be queried with
    #: `MemoryRetrievalMode.VECTOR_APPROXIMATE` (Sprint 21.3). Empty — the default —
    #: keeps the Sprint 9 behaviour: every vector search is exhaustive. This replaces
    #: the sealed `allow_approximate_vector_indexes` boolean, because a host that
    #: permits approximation has to say *for which embeddings*: an index exists per
    #: dimension, so a blanket yes would have permitted queries no index can serve.
    approximate_vector_index_dimensions: frozenset[int] = frozenset()
    fail_closed_on_access_audit_error: bool = True
    embedding_providers: dict[str, EmbeddingProviderConfiguration] = Field(default_factory=dict)
    export_root: Path
    benchmark: MemoryBenchmarkConfiguration = MemoryBenchmarkConfiguration()

    @field_validator("export_root")
    @classmethod
    def export_root_is_absolute(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("memory export root must be absolute")
        return value

    @model_validator(mode="after")
    def sprint_nine_boundaries_are_sealed(self) -> MemoryConfiguration:
        if (
            self.allow_provider_direct_write
            or self.allow_automatic_promotion
            or self.allow_network_model_download
        ):
            raise ValueError("Sprint 9 direct writes, promotion, and model downloads are forbidden")
        if self.default_query_limit > self.maximum_query_results:
            raise ValueError("default query limit exceeds the host maximum")
        return self

    @model_validator(mode="after")
    def declared_approximate_dimensions_are_indexable(self) -> MemoryConfiguration:
        """The ANN permission is narrowed to dimensions an index can actually cover.

        Sprint 21.3 lifts the blanket prohibition, so this validator carries what is
        left of it: a host cannot declare a dimension pgvector refuses to index, nor
        one its own embedding providers never produce, because either would leave a
        permission that silently degrades to an exhaustive scan.
        """
        for dimension in sorted(self.approximate_vector_index_dimensions):
            if dimension < 1 or dimension > HNSW_MAXIMUM_DIMENSIONS:
                raise ValueError(
                    f"approximate index dimension {dimension} is not indexable "
                    f"(1..{HNSW_MAXIMUM_DIMENSIONS})"
                )
            if dimension > self.maximum_vector_query_dimension:
                raise ValueError(
                    f"approximate index dimension {dimension} exceeds the query maximum"
                )
        declared = {provider.dimension for provider in self.embedding_providers.values()}
        if declared and not self.approximate_vector_index_dimensions <= declared:
            unmatched = sorted(self.approximate_vector_index_dimensions - declared)
            raise ValueError(f"no configured embedding provider produces dimension {unmatched}")
        return self


def load_memory_configuration(path: Path) -> MemoryConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("memory"), dict):
        raise ValueError("memory configuration requires a memory mapping")
    return MemoryConfiguration.model_validate(raw["memory"])
