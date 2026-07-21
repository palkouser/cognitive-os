"""Append-only Corpus Factory lifecycle evidence."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.corpus import CorpusDestinationType

from .base import EventPayload


class CorpusSourceRegistered(EventPayload):
    event_type = "corpus.source_registered"
    source_manifest_id: UUID
    source_manifest_hash: Sha256Hex
    occurred_at: UtcDatetime


class CorpusItemNormalized(EventPayload):
    event_type = "corpus.item_normalized"
    corpus_item_id: UUID
    item_revision: int
    normalized_content_hash: Sha256Hex
    occurred_at: UtcDatetime


class CorpusItemClassified(EventPayload):
    event_type = "corpus.item_classified"
    corpus_item_id: UUID
    item_revision: int
    classification_hash: Sha256Hex
    occurred_at: UtcDatetime


class CorpusItemQuarantined(EventPayload):
    event_type = "corpus.item_quarantined"
    corpus_item_id: UUID
    item_revision: int
    reason_code: NonEmptyStr
    occurred_at: UtcDatetime


class CorpusItemRejected(EventPayload):
    event_type = "corpus.item_rejected"
    corpus_item_id: UUID
    item_revision: int
    reason_code: NonEmptyStr
    occurred_at: UtcDatetime


class CorpusItemRouted(EventPayload):
    event_type = "corpus.item_routed"
    corpus_item_id: UUID
    item_revision: int
    destination: CorpusDestinationType
    package_hash: Sha256Hex
    occurred_at: UtcDatetime


class CorpusItemExported(EventPayload):
    event_type = "corpus.item_exported"
    corpus_item_id: UUID
    item_revision: int
    export_id: UUID
    occurred_at: UtcDatetime


class CorpusItemSuperseded(EventPayload):
    event_type = "corpus.item_superseded"
    corpus_item_id: UUID
    item_revision: int
    successor_item_id: UUID
    occurred_at: UtcDatetime


class CorpusManifestCreated(EventPayload):
    event_type = "corpus.manifest_created"
    corpus_id: UUID
    corpus_revision: int
    manifest_hash: Sha256Hex
    occurred_at: UtcDatetime


class CorpusExportCompleted(EventPayload):
    event_type = "corpus.export_completed"
    export_id: UUID
    corpus_id: UUID
    corpus_revision: int
    export_hash: Sha256Hex
    occurred_at: UtcDatetime


CORPUS_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    CorpusSourceRegistered,
    CorpusItemNormalized,
    CorpusItemClassified,
    CorpusItemQuarantined,
    CorpusItemRejected,
    CorpusItemRouted,
    CorpusItemExported,
    CorpusItemSuperseded,
    CorpusManifestCreated,
    CorpusExportCompleted,
)
