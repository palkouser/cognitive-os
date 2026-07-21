import asyncio
import json
from types import SimpleNamespace
from uuid import uuid5

from cognitive_os.corpus.factory import CorpusFactory
from cognitive_os.corpus.fixtures import (
    INITIAL_CORPUS_FIXTURES,
    FixtureArtifactStore,
    build_corpus_fixture,
    sprint14_candidate_fixtures,
)
from cognitive_os.corpus.repository import InMemoryCorpusRepository
from cognitive_os.domain.corpus import (
    CorpusDestinationType,
    CorpusItemStatus,
    CorpusLicenseStatus,
    CorpusRouteStatus,
)
from cognitive_os.events.corpus_event_service import CorpusEventService
from cognitive_os.verification.corpus import verify_corpus_result


def _ingest(name: str, **options):
    request, source = build_corpus_fixture(name, **options)
    artifacts = FixtureArtifactStore()
    repository = InMemoryCorpusRepository()
    result = asyncio.run(CorpusFactory(repository, artifacts).ingest(request, source))
    return result, artifacts, repository


class MemoryEventStore:
    def __init__(self) -> None:
        self.events = []

    async def get_stream_version(self, stream_id):
        del stream_id
        return len(self.events) or None

    async def append(self, events, *, expected_version):
        assert expected_version == len(self.events)
        self.events.extend(events)
        return SimpleNamespace(current_stream_version=len(self.events))


def test_twelve_source_family_fixtures_are_deterministic_and_package_only() -> None:
    assert len(INITIAL_CORPUS_FIXTURES) == 12
    for name in INITIAL_CORPUS_FIXTURES:
        first, artifacts, _ = _ingest(name)
        second, _, _ = _ingest(name)
        assert first == second
        assert not verify_corpus_result(first)
        expected_packages = 0 if name == "provider-dataset" else 1
        assert first.usage == {
            "sources": 1,
            "items": 1,
            "packages": expected_packages,
            "destination_writes": 0,
            "training_actions": 0,
            "network_writes": 0,
        }
        if not first.receipts:
            assert first.route_decisions[0].status is CorpusRouteStatus.QUARANTINED
            assert first.licenses[0].status is CorpusLicenseStatus.UNKNOWN
            continue
        package = first.receipts[0].package
        payload = json.loads(asyncio.run(artifacts.get_bytes(package.artifact.artifact_id)))
        assert "authority" not in payload
        assert payload["constraints"] == [
            "proposal-only",
            "no-destination-write",
            "no-promotion",
            "no-training-action",
        ]
        assert not first.receipts[0].promoted


def test_every_sprint14_candidate_type_is_classified() -> None:
    fixtures = sprint14_candidate_fixtures()
    assert len(fixtures) == 9
    content_types = set()
    for request, source in fixtures:
        result = asyncio.run(
            CorpusFactory(InMemoryCorpusRepository(), FixtureArtifactStore()).ingest(
                request, source
            )
        )
        content_types.add(result.classifications[0].content_type.value)
    assert content_types == {
        "memory",
        "semantic_observation",
        "skill",
        "strategy",
        "failure_pattern",
        "routing_observation",
        "benchmark_case",
        "negative_example",
        "dataset",
    }


def test_exact_duplicate_keeps_distinct_source_lineage() -> None:
    request, source = build_corpus_fixture("document")
    repository = InMemoryCorpusRepository()
    artifacts = FixtureArtifactStore()
    factory = CorpusFactory(repository, artifacts)
    first = asyncio.run(factory.ingest(request, source))
    changed = request.model_copy(update={"request_id": uuid5(request.request_id, "duplicate")})
    second = asyncio.run(factory.ingest(changed, source))
    assert first.items[0].canonical_content_hash == second.items[0].canonical_content_hash
    assert second.duplicates[0].duplicate_type.value == "exact_duplicate"
    assert len(repository.items) == 2


def test_secret_and_conflicting_license_are_quarantined() -> None:
    secret, _, _ = _ingest("document", secret=True)
    conflict, _, _ = _ingest("document", conflicting_license=True)
    assert secret.items[0].current_status is CorpusItemStatus.QUARANTINED
    assert secret.route_decisions[0].status is CorpusRouteStatus.QUARANTINED
    assert secret.sensitivity[0].secret_findings
    assert conflict.licenses[0].status is CorpusLicenseStatus.CONFLICTING
    assert conflict.items[0].current_status is CorpusItemStatus.QUARANTINED


def test_training_destination_requires_explicit_right_but_never_trains() -> None:
    result, _, _ = _ingest("benchmark-dataset", destination=CorpusDestinationType.TRAINING_CORPUS)
    assert result.classifications[0].training_suitability
    assert result.route_decisions[0].status is CorpusRouteStatus.ALLOWED
    assert result.usage["training_actions"] == 0


def test_request_idempotency_and_manifest_export_reproduction() -> None:
    request, source = build_corpus_fixture("cognitive-os-export")
    repository = InMemoryCorpusRepository()
    factory = CorpusFactory(repository, FixtureArtifactStore())
    first = asyncio.run(factory.ingest(request, source))
    second = asyncio.run(factory.ingest(request, source))
    assert first is second
    assert first.manifest is not None
    assert first.export is not None and first.export.reproduced
    assert first.manifest.license_summary == {"approved": 1}


def test_factory_emits_append_only_lifecycle_evidence() -> None:
    request, source = build_corpus_fixture("document")
    store = MemoryEventStore()
    factory = CorpusFactory(
        InMemoryCorpusRepository(),
        FixtureArtifactStore(),
        events=CorpusEventService(store),
    )
    asyncio.run(factory.ingest(request, source))
    assert [item.event_type for item in store.events] == [
        "corpus.source_registered",
        "corpus.item_normalized",
        "corpus.item_classified",
        "corpus.item_routed",
        "corpus.manifest_created",
        "corpus.export_completed",
    ]
