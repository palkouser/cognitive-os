import pytest

from cognitive_os.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_capability_contract_is_normalized(provider_request) -> None:
    provider = MockProvider()
    capabilities = await provider.get_model_capabilities(provider_request.requested_model)
    assert capabilities.provider_id == provider.provider_id
    assert capabilities.maximum_context_tokens is not None
    assert type(capabilities).__module__.startswith("cognitive_os.")
