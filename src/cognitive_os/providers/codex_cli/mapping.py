"""Bounded JSONL parsing for `codex exec --json`.

Codex streams events; the last authoritative one carries the final message. Three rules make
that safe to consume:

* **parse incrementally within the runner's stdout cap.** The runner already refuses to keep
  more than the configured bytes, so the parser's memory is bounded by the same number
  rather than by how talkative the model was;
* **allowlist the event types that carry authority.** An unknown type that looks like a
  result is refused rather than guessed at: a future Codex version adding an event this
  adapter has not reasoned about must fail closed, not be interpreted;
* **require the final structured output.** Truncated JSONL, a missing final message and a
  final message that does not match the advisory schema are three distinct failures and all
  three are refusals.

See ADR 0087.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from cognitive_os.providers.advisory_schema import AdvisoryResult
from cognitive_os.providers.errors import ProviderInvalidResponseError

#: Event types this adapter understands. `item.completed` with an `agent_message` item is
#: where the final answer arrives in codex-cli 0.14x; `thread.started` and `turn.*` frame it.
AUTHORITATIVE_EVENT_TYPES = frozenset(
    {
        "item.completed",
        "turn.completed",
        "thread.started",
        "turn.started",
        "item.started",
        "item.updated",
    }
)

#: Non-authoritative narration. Ignored explicitly rather than by falling through, so the
#: difference between "we chose to ignore this" and "we did not recognise this" stays real.
IGNORED_EVENT_TYPES = frozenset({"turn.delta", "item.delta", "notification", "error.retry"})

#: Event types that mean the run failed, whatever the exit code said.
FAILURE_EVENT_TYPES = frozenset({"turn.failed", "thread.failed", "error"})


def iter_events(stdout: str, *, provider_id: str) -> Iterator[dict[str, Any]]:
    """Decode JSONL line by line, refusing a truncated or malformed stream.

    A trailing partial line is what truncation at the stdout cap looks like, and accepting it
    silently would turn a capped run into a short answer.
    """
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError as error:
            raise ProviderInvalidResponseError(
                provider_id=provider_id,
                message="Codex produced a malformed or truncated JSONL event",
            ) from error
        if not isinstance(event, dict):
            raise ProviderInvalidResponseError(
                provider_id=provider_id,
                message="a Codex JSONL event is not an object",
            )
        yield event


def extract_final_message(stdout: str, *, provider_id: str) -> str:
    """The last agent message text, or a refusal.

    Refuses on an unrecognised event type rather than skipping it: an event this adapter has
    not reasoned about may be the one that carries the real answer, and picking the previous
    message would be a plausible-looking wrong result.
    """
    final: str | None = None
    for event in iter_events(stdout, provider_id=provider_id):
        event_type = event.get("type")
        if not isinstance(event_type, str):
            raise ProviderInvalidResponseError(
                provider_id=provider_id,
                message="a Codex JSONL event has no type",
            )
        if event_type in FAILURE_EVENT_TYPES:
            raise ProviderInvalidResponseError(
                provider_id=provider_id,
                message="Codex reported a failed turn",
            )
        if event_type in IGNORED_EVENT_TYPES:
            continue
        if event_type not in AUTHORITATIVE_EVENT_TYPES:
            raise ProviderInvalidResponseError(
                provider_id=provider_id,
                message=f"Codex emitted an unrecognised event type: {event_type}",
            )
        item = event.get("item")
        if isinstance(item, dict) and item.get("type") == "agent_message":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                final = text
    if final is None:
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="Codex produced no final agent message",
        )
    return final


def parse_advisory_result(stdout: str, *, provider_id: str) -> AdvisoryResult:
    """The final message, validated against the one shared advisory schema."""
    text = extract_final_message(stdout, provider_id=provider_id)
    stripped = text.strip()
    if stripped.startswith("```"):
        # `--output-schema` asks for raw JSON, but a fenced block is a common enough model
        # habit that treating it as malformed would reject a correct answer for formatting.
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:]
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="the Codex final message is not JSON",
        ) from error
    try:
        return AdvisoryResult.model_validate(payload)
    except ValueError as error:
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="Codex output does not match the advisory schema",
        ) from error
