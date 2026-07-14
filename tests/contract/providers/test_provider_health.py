import pytest

from cognitive_os.domain.provider import ProviderStatus
from cognitive_os.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_health_result_is_normalized_and_safe() -> None:
    health = await MockProvider().health_check()
    assert health.status is ProviderStatus.AVAILABLE
    assert health.error is None
    assert "key" not in health.message.lower()
