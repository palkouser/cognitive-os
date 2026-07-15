"""Canonical, secret-safe Coding Agent outcome reports."""

from __future__ import annotations

import json
import re
from typing import Any

from cognitive_os.domain.coding import CodingOutcome

_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,]+"),
    re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_\-]{12,}\b"),
)


def redact_secrets(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    return value


def render_outcome_json(outcome: CodingOutcome) -> bytes:
    payload = json.dumps(
        _redact_value(outcome.model_dump(mode="json")), sort_keys=True, separators=(",", ":")
    )
    return (payload + "\n").encode()


def render_outcome_markdown(outcome: CodingOutcome) -> str:
    changed = outcome.changed_files.files if outcome.changed_files else ()
    decision = (
        outcome.acceptance_decision.decision.value
        if outcome.acceptance_decision is not None
        else "not-issued"
    )
    lines = [
        "# Python Coding Agent report",
        "",
        f"- Task run: `{outcome.task_run_id}`",
        f"- Status: `{outcome.status.value}`",
        f"- Base commit: `{outcome.base_commit}`",
        f"- Acceptance decision: `{decision}`",
        f"- Patch attempts: `{len(outcome.patch_attempts)}`",
        f"- Changed files: `{len(changed)}`",
        f"- Workspace disposition: `{outcome.workspace_disposition.value}`",
        "- Commit, push, and merge performed: `no`",
        "",
        "## Changed paths",
        "",
        *(f"- `{item.path}` ({item.change_type.value})" for item in changed),
        "",
        "## Policy denials",
        "",
        *(f"- `{item}`" for item in outcome.policy_denials),
        "",
        "## Risks",
        "",
        *(f"- `{item.severity}` `{item.code}`: {item.message}" for item in outcome.risks),
        "",
    ]
    return redact_secrets("\n".join(lines))
