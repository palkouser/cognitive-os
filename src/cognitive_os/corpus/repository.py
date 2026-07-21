"""Dependency-light append-only Corpus Factory repository."""

from uuid import UUID

from cognitive_os.domain.corpus import (
    CorpusAccessRecord,
    CorpusClassification,
    CorpusExportManifest,
    CorpusItem,
    CorpusManifest,
    CorpusRouteDecision,
    CorpusStatusTransition,
    SourceManifest,
)

from .errors import CorpusConflictError


class InMemoryCorpusRepository:
    def __init__(self) -> None:
        self.sources: dict[UUID, SourceManifest] = {}
        self.source_identities: dict[tuple[str, str], UUID] = {}
        self.items: dict[UUID, CorpusItem] = {}
        self.item_history: dict[UUID, tuple[CorpusItem, ...]] = {}
        self.item_sources: set[tuple[UUID, UUID]] = set()
        self.classifications: dict[UUID, CorpusClassification] = {}
        self.route_decisions: dict[UUID, CorpusRouteDecision] = {}
        self.manifests: dict[tuple[UUID, int], CorpusManifest] = {}
        self.exports: dict[UUID, CorpusExportManifest] = {}
        self.accesses: dict[UUID, CorpusAccessRecord] = {}

    async def register_source(self, source: SourceManifest) -> None:
        key = source.source_identity, source.source_revision
        existing_id = self.source_identities.get(key)
        if existing_id is not None and self.sources[existing_id] != source:
            raise CorpusConflictError("source identity and revision changed")
        existing = self.sources.get(source.source_manifest_id)
        if existing is not None and existing != source:
            raise CorpusConflictError("source manifest identity changed")
        self.sources[source.source_manifest_id] = source
        self.source_identities[key] = source.source_manifest_id

    async def get_source(self, source_manifest_id: UUID) -> SourceManifest | None:
        return self.sources.get(source_manifest_id)

    async def get_source_by_identity(self, identity: str, revision: str) -> SourceManifest | None:
        source_id = self.source_identities.get((identity, revision))
        return self.sources.get(source_id) if source_id is not None else None

    async def create_item(self, item: CorpusItem) -> None:
        existing = self.items.get(item.corpus_item_id)
        if existing is not None and existing != item:
            raise CorpusConflictError("corpus item identity changed")
        self.items[item.corpus_item_id] = item
        self.item_history.setdefault(item.corpus_item_id, (item,))

    async def get_item(self, corpus_item_id: UUID) -> CorpusItem | None:
        return self.items.get(corpus_item_id)

    async def query_by_content_hash(
        self, content_hash: str, *, limit: int = 100
    ) -> tuple[CorpusItem, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self.items.values()
                    if item.canonical_content_hash == content_hash
                ),
                key=lambda item: str(item.corpus_item_id),
            )[:limit]
        )

    async def link_item_source(self, corpus_item_id: UUID, source_manifest_id: UUID) -> None:
        if corpus_item_id not in self.items or source_manifest_id not in self.sources:
            raise CorpusConflictError("corpus source link references an unknown record")
        self.item_sources.add((corpus_item_id, source_manifest_id))

    async def record_classification(self, classification: CorpusClassification) -> None:
        existing = self.classifications.get(classification.classification_id)
        if existing is not None and existing != classification:
            raise CorpusConflictError("classification identity changed")
        self.classifications[classification.classification_id] = classification

    async def record_route_decision(self, decision: CorpusRouteDecision) -> None:
        existing = self.route_decisions.get(decision.route_decision_id)
        if existing is not None and existing != decision:
            raise CorpusConflictError("route decision identity changed")
        self.route_decisions[decision.route_decision_id] = decision

    async def advance_item_status(self, transition: CorpusStatusTransition) -> CorpusItem:
        current = self.items.get(transition.corpus_item_id)
        if current is None:
            raise CorpusConflictError("corpus item is unavailable")
        if (
            current.current_revision != transition.expected_revision
            or current.current_status is not transition.expected_status
        ):
            raise CorpusConflictError("stale corpus item status revision")
        payload = current.model_dump(mode="python", exclude={"content_hash"})
        payload.update(
            current_revision=transition.next_revision,
            current_status=transition.next_status,
        )
        updated = CorpusItem.model_validate(payload)
        self.items[current.corpus_item_id] = updated
        self.item_history[current.corpus_item_id] = (
            *self.item_history[current.corpus_item_id],
            updated,
        )
        return updated

    async def create_manifest(self, manifest: CorpusManifest) -> None:
        key = manifest.corpus_id, manifest.revision
        existing = self.manifests.get(key)
        if existing is not None and existing != manifest:
            raise CorpusConflictError("corpus manifest revision changed")
        if (
            manifest.revision > 1
            and (manifest.corpus_id, manifest.revision - 1) not in self.manifests
        ):
            raise CorpusConflictError("corpus manifest previous revision is unavailable")
        self.manifests[key] = manifest

    async def get_manifest(self, corpus_id: UUID, revision: int) -> CorpusManifest | None:
        return self.manifests.get((corpus_id, revision))

    async def create_export(self, export: CorpusExportManifest) -> None:
        existing = self.exports.get(export.export_id)
        if existing is not None and existing != export:
            raise CorpusConflictError("corpus export identity changed")
        if (export.corpus_id, export.corpus_revision) not in self.manifests:
            raise CorpusConflictError("corpus export references an unknown manifest")
        self.exports[export.export_id] = export

    async def record_access(self, records: tuple[CorpusAccessRecord, ...]) -> None:
        for record in records:
            existing = self.accesses.get(record.access_id)
            if existing is not None and existing != record:
                raise CorpusConflictError("corpus access identity changed")
            self.accesses[record.access_id] = record
