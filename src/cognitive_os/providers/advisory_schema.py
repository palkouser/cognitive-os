"""The one structured advisory result shape all three providers are asked for.

One schema, not three. The whole point of the governed boundary is that OpenRouter, Claude
Code and Codex answer the *same* task in the *same* shape, so a deterministic verifier can
check any of them without knowing which one replied — and so a receipt from one is
comparable with a receipt from another.

Schema validity proves shape and nothing else. The verifier that decides whether the finding
is *correct* lives outside this module, because a provider that validated its own answer
would be its own verifier. See ADR 0087.
"""

from __future__ import annotations

import json
from typing import Any

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr


class AdvisoryFinding(ImmutableContractModel):
    title: NonEmptyStr
    severity: NonEmptyStr
    description: NonEmptyStr
    #: Relative paths and short quotations the provider used to justify the finding. Bounded
    #: by the runner's output cap, never by trust.
    evidence: tuple[str, ...] = ()


class AdvisoryResult(ImmutableContractModel):
    summary: NonEmptyStr
    findings: tuple[AdvisoryFinding, ...] = ()
    recommendations: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    verification_steps: tuple[str, ...] = ()


ADVISORY_JSON_SCHEMA: dict[str, Any] = AdvisoryResult.model_json_schema()


def advisory_schema_json() -> str:
    """The schema as canonical JSON, for a CLI flag or a temporary schema file."""
    return json.dumps(ADVISORY_JSON_SCHEMA, sort_keys=True, separators=(",", ":"))
