"""Fixed synthetic payloads the provider benchmark feeds through the real adapters.

Every value here is invented. There is no credential, no captured provider response, no
repository content and no CLI binary: the benchmark exercises the parsing, routing,
retention and governance code paths, which is where a regression would actually land.

Deliberately not sampled from a live run. A recorded real response would drift out of date
silently, and the day it did the benchmark would still report a pass rate.
"""

from __future__ import annotations

import json
from typing import Any

from cognitive_os.providers.advisory_schema import AdvisoryResult

#: A `/models` page with one free model, one paid model, and one unusable entry.
OPENROUTER_CATALOG: dict[str, Any] = {
    "data": [
        {
            "id": "vendor/free-small",
            "pricing": {"prompt": "0", "completion": "0"},
            "context_length": 32768,
        },
        {
            "id": "vendor/paid-large",
            "pricing": {"prompt": "0.000003", "completion": "0.000009"},
            "context_length": 131072,
        },
        {
            "id": "vendor/unpriced",
            "pricing": {"prompt": "not-a-number", "completion": "0"},
            "context_length": 8192,
        },
    ]
}

#: The same catalog with every free entry removed.
OPENROUTER_PAID_ONLY_CATALOG: dict[str, Any] = {
    "data": [entry for entry in OPENROUTER_CATALOG["data"] if entry["id"] != "vendor/free-small"]
}


def advisory_answer(*, correct: bool = True) -> dict[str, Any]:
    """The structured answer to the committed advisory fixture, right or wrong on demand."""
    if not correct:
        return {"summary": "no issues found", "findings": []}
    return {
        "summary": "one defect found",
        "findings": [
            {
                "title": "arithmetic_mean divides by zero on empty input",
                "severity": "high",
                "description": (
                    "statistics_helper.py: arithmetic_mean divides by len(values) with no "
                    "guard, so an empty sequence raises ZeroDivisionError."
                ),
                "evidence": [],
            }
        ],
    }


def openai_completion(content: str, *, finish_reason: str = "stop") -> dict[str, Any]:
    """An OpenAI-compatible chat completion body, as OpenRouter returns it."""
    return {
        "id": "gen-benchmark",
        "model": "vendor/free-small",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 48, "total_tokens": 168},
    }


def claude_envelope(payload: object, *, is_error: bool = False) -> str:
    """A `claude --print --output-format json` envelope."""
    return json.dumps(
        {
            "type": "result",
            "subtype": "error" if is_error else "success",
            "is_error": is_error,
            "result": payload,
            "num_turns": 1,
            "duration_ms": 900,
        }
    )


def codex_stream(payload: object, *, events: tuple[dict[str, Any], ...] = ()) -> str:
    """A `codex exec --json` JSONL stream ending in one agent message."""
    lines: list[dict[str, Any]] = [{"type": "thread.started", "thread_id": "t-benchmark"}]
    lines.extend(events)
    lines.append(
        {
            "type": "item.completed",
            "item": {
                "type": "agent_message",
                "text": payload if isinstance(payload, str) else json.dumps(payload),
            },
        }
    )
    lines.append({"type": "turn.completed"})
    return "\n".join(json.dumps(line) for line in lines) + "\n"


def parsed(answer: dict[str, Any]) -> AdvisoryResult:
    return AdvisoryResult.model_validate(answer)
