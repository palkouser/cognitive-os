import pytest

from cognitive_os.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_provider_identity_and_normalized_completion(
    provider_request, provider_response
) -> None:
    provider = MockProvider(outcomes=(provider_response,))
    response = await provider.complete(provider_request)
    assert provider.identity.provider_id == provider.provider_id
    assert response.model_call_id == provider_request.model_call_id
    assert type(response).__module__.startswith("cognitive_os.")
