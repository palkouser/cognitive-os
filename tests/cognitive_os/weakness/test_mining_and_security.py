import pytest

from cognitive_os.domain.weakness import WeaknessType
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.weakness_events import WEAKNESS_EVENT_MODELS
from cognitive_os.verification.weakness import MANDATORY_WEAKNESS_VERIFIERS
from cognitive_os.weakness.fixtures import (
    FixtureSignalExtractor,
    FixtureSourceResolver,
    fixture_profile,
    fixture_request,
    fixture_sources,
)
from cognitive_os.weakness.repository import InMemoryWeaknessRepository
from cognitive_os.weakness.service import (
    SignalExtractorRegistry,
    SourceResolverRegistry,
    WeaknessMiningService,
)


@pytest.mark.asyncio
async def test_end_to_end_mining_is_idempotent_and_diagnostic_only() -> None:
    sources = fixture_sources(72)
    profile = fixture_profile(sources)
    source_registry = SourceResolverRegistry()
    for source_type in profile.enabled_source_types:
        source_registry.register(FixtureSourceResolver(source_type, sources))
    source_registry.freeze()
    extractor_registry = SignalExtractorRegistry()
    extractor_registry.register(FixtureSignalExtractor())
    extractor_registry.freeze()
    repository = InMemoryWeaknessRepository()
    service = WeaknessMiningService(repository, source_registry, extractor_registry)
    request = fixture_request(profile)
    first = await service.mine(request, profile)
    second = await service.resume_mining(request, profile)
    assert first == second
    assert first.manifest is not None
    assert first.manifest.summary.signal_count == 72
    assert first.manifest.summary.group_count == len(tuple(WeaknessType))
    assert len(repository.accesses) == 9
    assert all("proposal" not in item.description.lower() for item in repository.revisions.values())


def test_events_and_mandatory_verifier_bundle_are_registered() -> None:
    registered = build_default_event_catalog().list_event_types()
    assert all((model.event_type, 1) in registered for model in WEAKNESS_EVENT_MODELS)
    assert len(MANDATORY_WEAKNESS_VERIFIERS) == 15
