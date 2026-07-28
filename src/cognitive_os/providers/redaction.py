"""Shared provider redaction and secret scanning.

Two related but distinct jobs, kept apart on purpose:

* **redaction** masks values before they reach a log line, an error, an event or an
  artifact. It runs everywhere, it is best-effort, and it must never be the thing that
  decides whether output may be retained;
* **scanning** answers "did we look, and did we find anything". It is tri-state, its result
  is recorded with a rule-set version and an evidence hash, and a `FAILED` or `NOT_RUN`
  scan blocks `normalized_content` retention *even though redaction would have masked the
  value*. A redactor that quietly turned a failed scan into a pass would be a redactor that
  hides the incident it exists to surface.

The evidence hash covers rule identity and match counts, never matched text. See ADR 0087.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from hashlib import sha256

from cognitive_os.domain.provider_output import SecretScanStatus

#: Bumped whenever a rule is added, removed or changed. Stored beside every scan result, so
#: a record scanned by an older rule set is identifiable rather than assumed current.
REDACTION_RULESET_VERSION = "2026.07-c2"

REDACTED = "<redacted>"

#: Names whose *value* is secret whatever it looks like.
_SECRET_NAME = re.compile(
    r"(^|[_\-.])(api[_\-]?key|auth|authorization|bearer|cookie|credential|passwd|password|"
    r"private[_\-]?key|refresh[_\-]?token|secret|session[_\-]?key|token)([_\-.]|$)",
    re.IGNORECASE,
)

#: Values that are secret whatever they are called. Ordered most specific first so a
#: bearer token is reported as a bearer token rather than as a generic long string.
_VALUE_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("authorization_header", re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")),
    ("url_credentials", re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/@:]+:[^\s/@]+@")),
    ("openrouter_key", re.compile(r"\bsk-or-v1-[A-Za-z0-9]{16,}")),
    ("openai_key", re.compile(r"\bsk-(?!or-)[A-Za-z0-9_-]{20,}")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}")),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_-]{20,}")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{12,}")),
    ("slack_token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{8,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("email_identity", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
)


def is_secret_like_name(name: str) -> bool:
    """Whether a key or environment-variable name marks its value as secret."""
    return bool(_SECRET_NAME.search(name))


def environment_secret_values(environment: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """Concrete secret values to mask by literal substitution.

    Short values are skipped: masking every occurrence of a three-character token would
    corrupt unrelated text far more often than it would hide a credential.
    """
    source = os.environ if environment is None else environment
    return tuple(
        value for name, value in source.items() if is_secret_like_name(name) and len(value) >= 8
    )


def redact_text(value: str, *, extra_secrets: tuple[str, ...] = ()) -> str:
    """Mask credential-shaped substrings and any supplied literal secrets."""
    result = value
    for secret in sorted(extra_secrets, key=len, reverse=True):
        if secret:
            result = result.replace(secret, REDACTED)
    for _, pattern in _VALUE_RULES:
        result = pattern.sub(REDACTED, result)
    return result


def redact_value(value: object, *, extra_secrets: tuple[str, ...] = ()) -> object:
    """Recursively redact a JSON-shaped value by key name and by value shape."""
    if isinstance(value, Mapping):
        return {
            str(key): (
                REDACTED
                if is_secret_like_name(str(key))
                else redact_value(nested, extra_secrets=extra_secrets)
            )
            for key, nested in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact_value(nested, extra_secrets=extra_secrets) for nested in value]
    if isinstance(value, str):
        return redact_text(value, extra_secrets=extra_secrets)
    return value


def redact_for_diagnostics(
    value: str, *, limit: int = 512, extra_secrets: tuple[str, ...] = ()
) -> str:
    """A short, redacted excerpt safe to put in an error, a log line or a health message."""
    redacted = redact_text(value, extra_secrets=extra_secrets).strip()
    if len(redacted) <= limit:
        return redacted
    return redacted[:limit] + "…"


class SecretScanResult:
    """What a scan looked at, what it matched, and the hash that proves it ran.

    `matched_rules` names rule identities and counts. The matched text is never stored,
    because an evidence record that copies the secret it found has widened the exposure it
    exists to record.
    """

    __slots__ = ("evidence_hash", "matched_rules", "ruleset_version", "scanned_fields", "status")

    def __init__(
        self,
        *,
        status: SecretScanStatus,
        matched_rules: Mapping[str, int],
        scanned_fields: tuple[str, ...],
        ruleset_version: str = REDACTION_RULESET_VERSION,
    ) -> None:
        self.status = status
        self.matched_rules = dict(sorted(matched_rules.items()))
        self.scanned_fields = scanned_fields
        self.ruleset_version = ruleset_version
        self.evidence_hash = sha256(
            json.dumps(
                {
                    "ruleset_version": ruleset_version,
                    "status": status.value,
                    "matched_rules": self.matched_rules,
                    "scanned_fields": list(scanned_fields),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    @property
    def passed(self) -> bool:
        return self.status is SecretScanStatus.PASSED

    def __repr__(self) -> str:
        return (
            f"SecretScanResult(status={self.status.value}, "
            f"matched_rules={self.matched_rules}, ruleset_version={self.ruleset_version!r})"
        )


def scan_for_secrets(
    value: object,
    *,
    extra_secrets: tuple[str, ...] | None = None,
    ruleset_version: str = REDACTION_RULESET_VERSION,
) -> SecretScanResult:
    """Walk a JSON-shaped value and report whether anything credential-shaped is in it.

    Scans the *unredacted* value. Scanning after redaction would always pass, which is the
    failure mode this separation exists to prevent.
    """
    secrets = environment_secret_values() if extra_secrets is None else extra_secrets
    matched: dict[str, int] = {}
    fields: list[str] = []

    def visit(item: object, path: str) -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                child = f"{path}.{key}" if path else str(key)
                if is_secret_like_name(str(key)):
                    matched["secret_named_field"] = matched.get("secret_named_field", 0) + 1
                    fields.append(child)
                visit(nested, child)
        elif isinstance(item, list | tuple):
            for index, nested in enumerate(item):
                visit(nested, f"{path}[{index}]")
        elif isinstance(item, str):
            for name, pattern in _VALUE_RULES:
                found = len(pattern.findall(item))
                if found:
                    matched[name] = matched.get(name, 0) + found
                    fields.append(path or "<root>")
            for secret in secrets:
                if secret and secret in item:
                    matched["environment_secret_value"] = (
                        matched.get("environment_secret_value", 0) + 1
                    )
                    fields.append(path or "<root>")

    visit(value, "")
    return SecretScanResult(
        status=SecretScanStatus.FAILED if matched else SecretScanStatus.PASSED,
        matched_rules=matched,
        scanned_fields=tuple(sorted(set(fields))),
        ruleset_version=ruleset_version,
    )
