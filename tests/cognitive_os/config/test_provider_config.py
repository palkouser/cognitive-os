from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.config.provider_config import (
    MiniMaxKeyType,
    MiniMaxProviderConfig,
    load_provider_configuration,
)
from cognitive_os.config.secret_loading import get_required_secret, redact_secret
from cognitive_os.providers.errors import ProviderConfigurationError


def test_example_configuration_loads_without_secret() -> None:
    configuration = load_provider_configuration(Path("config/providers.example.yaml"))
    minimax = configuration.providers["minimax"]
    assert minimax.provider_id == "minimax"
    assert "api_key=" not in repr(minimax)


def test_minimax_key_type_is_explicit_and_url_is_safe() -> None:
    config = MiniMaxProviderConfig(key_type=MiniMaxKeyType.PAY_AS_YOU_GO)
    assert config.key_type is MiniMaxKeyType.PAY_AS_YOU_GO
    with pytest.raises(ValidationError, match="credentials"):
        MiniMaxProviderConfig(
            key_type=MiniMaxKeyType.SUBSCRIPTION,
            base_url="https://user:password@example.test/v1",  # pragma: allowlist secret
        )


def test_secret_loading_is_required_and_repr_safe(monkeypatch) -> None:
    monkeypatch.delenv("COGOS_TEST_PROVIDER_KEY", raising=False)
    with pytest.raises(ProviderConfigurationError, match="environment variable"):
        get_required_secret("COGOS_TEST_PROVIDER_KEY")
    monkeypatch.setenv("COGOS_TEST_PROVIDER_KEY", "private-value")
    secret = get_required_secret("COGOS_TEST_PROVIDER_KEY")
    assert "private-value" not in repr(secret)
    assert redact_secret(secret) == "<redacted>"
