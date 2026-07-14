"""Environment-only provider secret loading."""

from __future__ import annotations

import os

from pydantic import SecretStr

from cognitive_os.providers.errors import ProviderConfigurationError


def get_required_secret(name: str, *, provider_id: str = "configuration") -> SecretStr:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ProviderConfigurationError(
            provider_id=provider_id,
            error_code="missing_provider_secret",
            message=f"required provider secret environment variable is unavailable: {name}",
        )
    return SecretStr(value)


def get_optional_secret(name: str) -> SecretStr | None:
    value = os.environ.get(name)
    return SecretStr(value) if value is not None and value.strip() else None


def redact_secret(value: str | SecretStr | None) -> str:
    return "<redacted>" if value else "<not configured>"
