"""Deterministic pre-provider problem normalization."""

from __future__ import annotations

import hashlib
import re
from uuid import UUID

from pydantic import Field

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import ArtifactRef, NonEmptyStr, Sha256Hex
from cognitive_os.domain.enums import RiskLevel
from cognitive_os.domain.problems import ProblemDomain
from cognitive_os.domain.tools import ToolDescriptor

MACHINE_CONSTRAINTS = (
    "Do not disclose provider secrets.",
    "Do not bypass Tool Plane policy.",
    "Do not modify files outside approved workspaces.",
    "Do not execute unregistered tools.",
    "Do not increase controller budgets.",
)


class NormalizedProblemSeed(ImmutableContractModel):
    task_id: UUID
    task_run_id: UUID
    title: NonEmptyStr
    normalized_request: NonEmptyStr
    request_hash: Sha256Hex
    artifact_ids: tuple[str, ...] = ()
    risk_level: RiskLevel
    domain_hint: ProblemDomain | None = None
    machine_constraints: tuple[NonEmptyStr, ...]
    allowed_provider_ids: tuple[NonEmptyStr, ...]
    available_tools: tuple[NonEmptyStr, ...]
    maximum_output_bytes: int = Field(gt=0)


def normalize_problem(
    *,
    task_id: UUID,
    task_run_id: UUID,
    title: str,
    raw_request: str,
    artifacts: tuple[ArtifactRef, ...] = (),
    risk_level: RiskLevel = RiskLevel.LOW,
    tools: tuple[ToolDescriptor, ...] = (),
    provider_ids: tuple[str, ...] = (),
    domain_hint: ProblemDomain | None = None,
    maximum_output_bytes: int = 1048576,
    repository_language_english: bool = False,
) -> NormalizedProblemSeed:
    normalized = re.sub(r"\s+", " ", raw_request).strip()
    if not normalized:
        raise ValueError("raw request must be non-empty")
    constraints = MACHINE_CONSTRAINTS + (
        ("All tracked repository content must be written in English.",)
        if repository_language_english
        else ()
    )
    return NormalizedProblemSeed(
        task_id=task_id,
        task_run_id=task_run_id,
        title=title,
        normalized_request=normalized,
        request_hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        artifact_ids=tuple(str(item.artifact_id) for item in artifacts),
        risk_level=risk_level,
        domain_hint=domain_hint,
        machine_constraints=constraints,
        allowed_provider_ids=tuple(sorted(set(provider_ids))),
        available_tools=tuple(
            f"{item.tool_id}@{item.version}"
            for item in sorted(tools, key=lambda value: (value.tool_id, value.version))
        ),
        maximum_output_bytes=maximum_output_bytes,
    )
