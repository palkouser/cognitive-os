"""Bounded benchmark runner configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BenchmarkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    continue_on_case_error: bool = True
    parallel_execution: bool = False
    maximum_cases: int = Field(default=1000, gt=0, le=10_000)
    maximum_elapsed_seconds: float = Field(default=3600, gt=0, le=86_400)
    random_seed: int = 0

    @model_validator(mode="after")
    def sequential_only(self) -> BenchmarkConfig:
        if self.parallel_execution:
            raise ValueError("parallel benchmark execution is not supported in Sprint 7")
        return self
