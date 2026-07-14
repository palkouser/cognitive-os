from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cognitive_os.domain.common import TokenUsage
from cognitive_os.domain.provider import (
    ModelCapabilities,
    ProviderHealth,
    ProviderStatus,
    ProviderStreamEvent,
    ProviderStreamEventType,
)


def test_provider_records_are_strict_and_json_serializable() -> None:
    capabilities = ModelCapabilities(model_id="model", provider_id="provider")
    health = ProviderHealth(
        provider_id="provider",
        status=ProviderStatus.AVAILABLE,
        checked_at=datetime.now(UTC),
        message="available",
    )
    assert ModelCapabilities.model_validate_json(capabilities.model_dump_json()) == capabilities
    assert ProviderHealth.model_validate_json(health.model_dump_json()) == health
    with pytest.raises(ValidationError):
        ModelCapabilities(model_id="model", provider_id="provider", unknown=True)


def test_stream_event_requires_event_specific_content() -> None:
    with pytest.raises(ValidationError, match="text_delta"):
        ProviderStreamEvent(sequence=1, event_type=ProviderStreamEventType.TEXT_DELTA)
    event = ProviderStreamEvent(
        sequence=1,
        event_type=ProviderStreamEventType.USAGE,
        usage=TokenUsage(total_tokens=2),
    )
    assert event.usage == TokenUsage(total_tokens=2)
