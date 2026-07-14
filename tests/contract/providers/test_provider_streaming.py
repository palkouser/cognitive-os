import pytest

from cognitive_os.domain.provider import ProviderStreamEvent, ProviderStreamEventType
from cognitive_os.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_stream_sequence_is_normalized_and_ordered(provider_request) -> None:
    events = (
        ProviderStreamEvent(
            sequence=1,
            event_type=ProviderStreamEventType.RESPONSE_STARTED,
        ),
        ProviderStreamEvent(
            sequence=2,
            event_type=ProviderStreamEventType.TEXT_DELTA,
            text_delta="answer",
        ),
        ProviderStreamEvent(
            sequence=3,
            event_type=ProviderStreamEventType.RESPONSE_COMPLETED,
        ),
    )
    provider = MockProvider(outcomes=(events,))
    received = [event async for event in provider.stream(provider_request)]
    assert [event.sequence for event in received] == [1, 2, 3]
