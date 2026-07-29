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
from copy import deepcopy
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


#: The contract's own schema, as Pydantic generates it. Correct JSON Schema, and what an
#: OpenAI-compatible `response_format` accepts.
ADVISORY_JSON_SCHEMA: dict[str, Any] = AdvisoryResult.model_json_schema()


def _strict(node: Any) -> Any:
    """Rewrite every object node so `required` lists all properties and no extras are allowed.

    Structured-output backends behind `codex exec --output-schema` and
    `claude --json-schema` enforce OpenAI's *strict* subset. `extra="forbid"` already gives
    us `additionalProperties: false` everywhere; what was missing is that `required` must
    list **every** property. Pydantic omits defaulted fields from it, so `evidence`,
    `findings`, `recommendations`, `risks` and `verification_steps` were all absent and
    Codex refused the whole turn with a 400. `additionalProperties` is set here too so the
    strict guarantee is stated in one place rather than inherited from a model config that
    a later edit could relax.

    Found by the Sprint 21C2 live smoke and not reachable from CI, which never sends the
    schema anywhere. Making every field required costs nothing on the way back: the model
    emits explicit empty arrays, and `AdvisoryResult` validates those identically.
    """
    if isinstance(node, dict):
        rewritten = {key: _strict(value) for key, value in node.items()}
        properties = rewritten.get("properties")
        if isinstance(properties, dict):
            rewritten["required"] = sorted(properties)
            rewritten["additionalProperties"] = False
        return rewritten
    if isinstance(node, list):
        return [_strict(item) for item in node]
    return node


#: The same shape, in the strict subset every CLI structured-output flag demands.
STRICT_ADVISORY_JSON_SCHEMA: dict[str, Any] = _strict(deepcopy(ADVISORY_JSON_SCHEMA))


def advisory_schema_json() -> str:
    """The strict schema as canonical JSON, for a CLI flag or a temporary schema file.

    Strict rather than the Pydantic default because this value is only ever *sent to a
    provider*, and the strict subset is accepted by the permissive consumers too. One
    schema on the wire beats one per adapter.
    """
    return json.dumps(STRICT_ADVISORY_JSON_SCHEMA, sort_keys=True, separators=(",", ":"))
