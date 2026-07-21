"""Deterministic, package-only Corpus-to-Memory Factory pipeline."""

from __future__ import annotations

import ast
import json
import re
import unicodedata
from collections.abc import Iterable
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

import yaml

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.corpus_repository import CorpusRepositoryPort
from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.domain.corpus import (
    CorpusAccessRecord,
    CorpusAccessType,
    CorpusClassification,
    CorpusContentType,
    CorpusDestinationType,
    CorpusDuplicateType,
    CorpusExportManifest,
    CorpusExportResult,
    CorpusExportType,
    CorpusFactoryRequest,
    CorpusFactoryResult,
    CorpusItem,
    CorpusItemStatus,
    CorpusKnowledgeType,
    CorpusLicenseStatus,
    CorpusLineage,
    CorpusLineageEdge,
    CorpusLineageRelationship,
    CorpusManifest,
    CorpusManifestItem,
    CorpusQualityAssessment,
    CorpusQualityDimension,
    CorpusQualityDimensionName,
    CorpusQualityProfile,
    CorpusQualityTier,
    CorpusRouteDecision,
    CorpusRouteStatus,
    CorpusRoutingReceipt,
    CorpusSecretFinding,
    CorpusSensitivityAssessment,
    CorpusSensitivityStatus,
    CorpusSourceContribution,
    CorpusSourceType,
    CorpusSplit,
    CorpusSplitManifest,
    CorpusStatusTransition,
    CorpusUsageRight,
    DeduplicationProfile,
    DestinationPackageReference,
    DestinationPolicyReference,
    DuplicateDecision,
    DuplicateEvidence,
    LicenseClassification,
    LicenseConflict,
    LicenseDeclaration,
    NormalizationProfile,
    NormalizedContent,
    SourceFileEntry,
    SourceManifest,
    UsageRightAssessment,
)
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.events.base import EventPayload
from cognitive_os.events.corpus_event_service import CorpusEventService
from cognitive_os.events.corpus_events import (
    CorpusExportCompleted,
    CorpusItemClassified,
    CorpusItemNormalized,
    CorpusItemQuarantined,
    CorpusItemRejected,
    CorpusItemRouted,
    CorpusManifestCreated,
    CorpusSourceRegistered,
)
from cognitive_os.experience.registry import canonical_hash

from .errors import CorpusNormalizationError, CorpusPolicyError, CorpusSourceError
from .registry import DestinationPolicyRegistry, NormalizerRegistry
from .sources import InspectedSource, SourceMaterial

SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|password|secret|token|bearer)\s*[:=]\s*['\"]?([A-Za-z0-9._/+\-=]{8,})"
)
APPROVED_LICENSES = frozenset({"Apache-2.0", "MIT", "BSD-3-Clause", "CC0-1.0"})
INTERNAL_LICENSES = frozenset({"LicenseRef-Cognitive-OS-Internal", "LicenseRef-Proprietary"})
MANDATORY_VERIFIERS = (
    "corpus.source_integrity",
    "corpus.archive_safety",
    "corpus.path_safety",
    "corpus.normalization_schema",
    "corpus.normalization_determinism",
    "corpus.original_preservation",
    "corpus.deduplication_integrity",
    "corpus.lineage_integrity",
    "corpus.classification_schema",
    "corpus.license_policy",
    "corpus.usage_rights",
    "corpus.sensitivity_policy",
    "corpus.secret_policy",
    "corpus.quality_reproducibility",
    "corpus.route_policy",
    "corpus.destination_package_schema",
    "corpus.manifest_integrity",
    "corpus.export_reproducibility",
    "corpus.no_destination_promotion",
    "corpus.no_model_training",
)

LEGAL_TRANSITIONS: dict[CorpusItemStatus, frozenset[CorpusItemStatus]] = {
    CorpusItemStatus.RECEIVED: frozenset(
        {CorpusItemStatus.NORMALIZED, CorpusItemStatus.QUARANTINED, CorpusItemStatus.REJECTED}
    ),
    CorpusItemStatus.NORMALIZED: frozenset(
        {CorpusItemStatus.CLASSIFIED, CorpusItemStatus.QUARANTINED, CorpusItemStatus.REJECTED}
    ),
    CorpusItemStatus.CLASSIFIED: frozenset(
        {CorpusItemStatus.STAGED, CorpusItemStatus.QUARANTINED, CorpusItemStatus.REJECTED}
    ),
    CorpusItemStatus.STAGED: frozenset(
        {
            CorpusItemStatus.ROUTED,
            CorpusItemStatus.QUARANTINED,
            CorpusItemStatus.REJECTED,
            CorpusItemStatus.SUPERSEDED,
        }
    ),
    CorpusItemStatus.ROUTED: frozenset(
        {CorpusItemStatus.EXPORTED, CorpusItemStatus.QUARANTINED, CorpusItemStatus.SUPERSEDED}
    ),
    CorpusItemStatus.QUARANTINED: frozenset(
        {
            CorpusItemStatus.NORMALIZED,
            CorpusItemStatus.CLASSIFIED,
            CorpusItemStatus.STAGED,
            CorpusItemStatus.REJECTED,
        }
    ),
    CorpusItemStatus.EXPORTED: frozenset({CorpusItemStatus.SUPERSEDED}),
    CorpusItemStatus.REJECTED: frozenset(),
    CorpusItemStatus.SUPERSEDED: frozenset(),
}


def _uuid(kind: str, value: object) -> UUID:
    return uuid5(NAMESPACE_URL, f"corpus:{kind}:{value}")


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CorpusNormalizationError("duplicate JSON object key")
        result[key] = value
    return result


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> object:
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise CorpusNormalizationError("duplicate YAML mapping key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def _normalize_json(data: bytes, _: str) -> tuple[bytes, tuple[str, ...]]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                CorpusNormalizationError(f"non-finite JSON number: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CorpusNormalizationError("invalid UTF-8 JSON source") from error
    return _canonical_json(value), ()


def _normalize_yaml(data: bytes, _: str) -> tuple[bytes, tuple[str, ...]]:
    try:
        # This loader subclasses SafeLoader only to reject duplicate keys.
        value = yaml.load(data.decode("utf-8"), Loader=_UniqueKeyLoader)  # nosec B506
        normalized = _canonical_json(value)
    except (TypeError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise CorpusNormalizationError("invalid safe YAML source") from error
    return normalized, ("yaml-normalized-to-canonical-json",)


def _normalize_jsonl(data: bytes, _: str) -> tuple[bytes, tuple[str, ...]]:
    try:
        lines = data.decode("utf-8").splitlines()
        values = [
            json.loads(
                line,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    CorpusNormalizationError(f"non-finite JSON number: {value}")
                ),
            )
            for line in lines
            if line.strip()
        ]
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CorpusNormalizationError("invalid UTF-8 JSONL source") from error
    if not values:
        raise CorpusNormalizationError("JSONL source contains no records")
    return b"".join(_canonical_json(value) + b"\n" for value in values), ()


def _normalize_text(data: bytes, path: str) -> tuple[bytes, tuple[str, ...]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CorpusNormalizationError("unsupported non-UTF-8 text source") from error
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    normalized = "\n".join(line.rstrip() for line in text.split("\n")).rstrip("\n") + "\n"
    warnings: tuple[str, ...] = ()
    if path.endswith(".py"):
        try:
            ast.parse(normalized, filename=path)
        except SyntaxError:
            warnings = ("python-syntax-invalid",)
    if path.endswith((".diff", ".patch")):
        for line in normalized.splitlines():
            if line.startswith(("+++ ", "--- ")):
                target = line[4:].split("\t", 1)[0]
                if target != "/dev/null" and (target.startswith("/") or ".." in target.split("/")):
                    raise CorpusNormalizationError("diff path escapes the logical repository")
    return normalized.encode(), warnings


def build_normalizer_registry() -> NormalizerRegistry:
    registry = NormalizerRegistry()
    for suffix in ("json",):
        registry.register(suffix, _normalize_json)
    for suffix in ("yaml", "yml"):
        registry.register(suffix, _normalize_yaml)
    registry.register("jsonl", _normalize_jsonl)
    for suffix in ("md", "markdown", "txt", "py", "diff", "patch"):
        registry.register(suffix, _normalize_text)
    registry.freeze()
    return registry


def build_destination_registry(
    config: CorpusConfiguration | None = None,
) -> DestinationPolicyRegistry:
    config = config or CorpusConfiguration()
    registry = DestinationPolicyRegistry()
    maximums = {
        destination: MemorySensitivity.INTERNAL
        for destination in CorpusDestinationType
        if destination not in {CorpusDestinationType.QUARANTINE, CorpusDestinationType.REJECT}
    }
    maximums[CorpusDestinationType.GOVERNED_MEMORY_CANDIDATE] = MemorySensitivity.CONFIDENTIAL
    maximums[CorpusDestinationType.QUARANTINE] = MemorySensitivity.RESTRICTED
    maximums[CorpusDestinationType.REJECT] = MemorySensitivity.RESTRICTED
    for destination in CorpusDestinationType:
        required_rights = {CorpusUsageRight.INTERNAL_USE}
        if destination is CorpusDestinationType.TRAINING_CORPUS:
            required_rights.add(CorpusUsageRight.MODEL_TRAINING)
        if destination in {
            CorpusDestinationType.BENCHMARK_CASE,
            CorpusDestinationType.REPLAY_FIXTURE,
        }:
            required_rights.add(CorpusUsageRight.BENCHMARK_USE)
        policy = DestinationPolicyReference(
            destination=destination,
            policy_id=f"sprint15-{destination.value}",
            version=1,
            required_content_types=frozenset(CorpusContentType),
            required_quality=(
                config.minimum_training_quality_score
                if destination is CorpusDestinationType.TRAINING_CORPUS
                else config.minimum_benchmark_quality_score
                if destination is CorpusDestinationType.BENCHMARK_CASE
                else config.minimum_reference_quality_score
            ),
            required_rights=frozenset(required_rights),
            maximum_sensitivity=maximums[destination],
            required_verifiers=frozenset(MANDATORY_VERIFIERS),
            package_schema=f"cognitive-os/{destination.value}/v1",
            destination_available=True,
        )
        registry.register(destination.value, policy)
    registry.freeze()
    return registry


def build_normalization_profile(config: CorpusConfiguration) -> NormalizationProfile:
    from cognitive_os.domain.corpus import CorpusResourceLimits

    return NormalizationProfile(
        profile_id="sprint15-core",
        version=1,
        supported_formats=frozenset(
            {"json", "yaml", "yml", "md", "markdown", "txt", "py", "diff", "patch", "jsonl"}
        ),
        resource_limits=CorpusResourceLimits(
            maximum_item_bytes=config.maximum_normalized_item_bytes,
            maximum_files=config.maximum_source_files,
            maximum_archive_depth=config.maximum_archive_depth,
        ),
    )


def build_quality_profile(config: CorpusConfiguration) -> CorpusQualityProfile:
    weight = 1.0 / len(CorpusQualityDimensionName)
    return CorpusQualityProfile(
        profile_id="sprint15-quality",
        version=1,
        weights={dimension: weight for dimension in CorpusQualityDimensionName},
        hard_blockers=frozenset(
            {
                "source-integrity-failed",
                "secret-detected",
                "prohibited-sensitivity",
                "prohibited-usage-right",
                "missing-provenance",
                "unsupported-destination-schema",
            }
        ),
        destination_thresholds={
            destination: config.minimum_training_quality_score
            if destination is CorpusDestinationType.TRAINING_CORPUS
            else config.minimum_benchmark_quality_score
            if destination is CorpusDestinationType.BENCHMARK_CASE
            else config.minimum_reference_quality_score
            for destination in CorpusDestinationType
        },
    )


class CorpusFactory:
    """Fixed-order post-execution pipeline with no destination or training authority."""

    def __init__(
        self,
        repository: CorpusRepositoryPort,
        artifacts: ArtifactStorePort,
        configuration: CorpusConfiguration | None = None,
        events: CorpusEventService | None = None,
    ) -> None:
        self._repository = repository
        self._artifacts = artifacts
        self._config = configuration or CorpusConfiguration()
        self._events = events
        self._normalizers = build_normalizer_registry()
        self._destinations = build_destination_registry(self._config)
        self._normalization_profile = build_normalization_profile(self._config)
        self._deduplication_profile = DeduplicationProfile(
            profile_id="sprint15-exact",
            version=1,
            exact_keys=("canonical_content_hash", "source_identity_revision", "lineage"),
            near_duplicate_advisory=False,
        )
        self._quality_profile = build_quality_profile(self._config)
        self._cancelled: set[UUID] = set()
        self._results: dict[UUID, CorpusFactoryResult] = {}

    def cancel(self, request_id: UUID) -> None:
        self._cancelled.add(request_id)

    async def resume(
        self, request: CorpusFactoryRequest, source: InspectedSource
    ) -> CorpusFactoryResult:
        self._cancelled.discard(request.request_id)
        return await self.ingest(request, source)

    async def ingest(
        self, request: CorpusFactoryRequest, source: InspectedSource
    ) -> CorpusFactoryResult:
        existing = self._results.get(request.request_id)
        if existing is not None:
            return existing
        self._validate_request_source(request, source)
        self._checkpoint(request.request_id)
        source_manifest = await self._register_source(request, source)
        normalized: list[NormalizedContent] = []
        items: list[CorpusItem] = []
        duplicates: list[DuplicateDecision] = []
        classifications: list[CorpusClassification] = []
        licenses: list[LicenseClassification] = []
        sensitivities: list[CorpusSensitivityAssessment] = []
        qualities: list[CorpusQualityAssessment] = []
        decisions: list[CorpusRouteDecision] = []
        receipts: list[CorpusRoutingReceipt] = []
        accesses: list[CorpusAccessRecord] = []
        for index, material in enumerate(source.materials):
            self._checkpoint(request.request_id)
            content = await self._normalize(request, source_manifest, material, index)
            duplicate = await self._deduplicate(request, source_manifest, content, index)
            classification = self._classify(request, source, content, index)
            license_result = self._license(request, source_manifest, content, index)
            sensitivity = self._sensitivity(request, material, content, classification, index)
            quality = self._quality(
                request,
                source,
                content,
                classification,
                duplicate,
                license_result,
                sensitivity,
                index,
            )
            lineage = self._lineage(source_manifest, content)
            destination = request.requested_destination or classification.candidate_destinations[0]
            route = self._route(
                request,
                content,
                classification,
                license_result,
                sensitivity,
                quality,
                destination,
                index,
            )
            item = CorpusItem(
                corpus_item_id=_uuid(
                    "item", f"{request.request_id}:{index}:{content.canonical_content_hash}"
                ),
                current_status=CorpusItemStatus.RECEIVED,
                canonical_content_hash=content.canonical_content_hash,
                normalized_content_artifact=content.normalized_artifact_ref,
                source_manifest_refs=(source_manifest.source_manifest_id,),
                source_refs=source_manifest.source_hashes,
                scope=request.scope,
                sensitivity=sensitivity.effective_sensitivity,
                classification_ref=classification.content_hash,
                quality_ref=quality.content_hash,
                license_ref=license_result.content_hash,
                duplicate_ref=duplicate.content_hash,
                lineage_ref=lineage.content_hash,
                created_at=request.created_at,
                created_by=request.created_by,
            )
            await self._repository.create_item(item)
            await self._repository.link_item_source(
                item.corpus_item_id, source_manifest.source_manifest_id
            )
            await self._repository.record_classification(classification)
            item = await self._advance(
                request, item, CorpusItemStatus.NORMALIZED, content.content_hash
            )
            item = await self._advance(
                request, item, CorpusItemStatus.CLASSIFIED, classification.content_hash
            )
            if route.status is CorpusRouteStatus.ALLOWED:
                item = await self._advance(
                    request, item, CorpusItemStatus.STAGED, quality.content_hash
                )
                package = await self._build_package(
                    request,
                    item,
                    source_manifest,
                    classification,
                    license_result,
                    sensitivity,
                    quality,
                    route,
                )
                await self._repository.record_route_decision(route)
                item = await self._advance(
                    request, item, CorpusItemStatus.ROUTED, route.content_hash
                )
                receipt = CorpusRoutingReceipt(
                    receipt_id=_uuid("receipt", route.route_decision_id),
                    route_decision_hash=route.content_hash,
                    package=package,
                    created_at=request.created_at,
                )
                receipts.append(receipt)
            else:
                target = (
                    CorpusItemStatus.REJECTED
                    if route.status is CorpusRouteStatus.DENIED
                    else CorpusItemStatus.QUARANTINED
                )
                item = await self._advance(request, item, target, route.content_hash)
                await self._repository.record_route_decision(route)
            item_accesses = self._accesses(request, source_manifest, item, index)
            await self._repository.record_access(item_accesses)
            normalized.append(content)
            items.append(item)
            duplicates.append(duplicate)
            classifications.append(classification)
            licenses.append(license_result)
            sensitivities.append(sensitivity)
            qualities.append(quality)
            decisions.append(route)
            accesses.extend(item_accesses)
        manifest, export = await self._manifest_and_export(request, items, licenses, sensitivities)
        result = CorpusFactoryResult(
            request_id=request.request_id,
            source_manifest=source_manifest,
            normalized=tuple(normalized),
            items=tuple(items),
            duplicates=tuple(duplicates),
            classifications=tuple(classifications),
            licenses=tuple(licenses),
            sensitivity=tuple(sensitivities),
            quality=tuple(qualities),
            route_decisions=tuple(decisions),
            receipts=tuple(receipts),
            access_records=tuple(accesses),
            manifest=manifest,
            export=export,
            warnings=tuple(
                sorted({warning for content in normalized for warning in content.warnings})
            ),
            usage={
                "sources": 1,
                "items": len(items),
                "packages": len(receipts),
                "destination_writes": 0,
                "training_actions": 0,
                "network_writes": 0,
            },
        )
        await self._emit_events(request, result)
        self._results[request.request_id] = result
        return result

    async def _emit_events(
        self, request: CorpusFactoryRequest, result: CorpusFactoryResult
    ) -> None:
        if self._events is None:
            return
        await self._events.append(
            request.request_id,
            CorpusSourceRegistered(
                source_manifest_id=result.source_manifest.source_manifest_id,
                source_manifest_hash=result.source_manifest.content_hash,
                occurred_at=request.created_at,
            ),
            correlation_id=request.request_id,
        )
        receipt_by_item = {item.package.corpus_item_id: item for item in result.receipts}
        for normalized, classification, item, decision in zip(
            result.normalized,
            result.classifications,
            result.items,
            result.route_decisions,
            strict=True,
        ):
            await self._events.append(
                request.request_id,
                CorpusItemNormalized(
                    corpus_item_id=item.corpus_item_id,
                    item_revision=2,
                    normalized_content_hash=normalized.content_hash,
                    occurred_at=request.created_at,
                ),
                correlation_id=request.request_id,
            )
            await self._events.append(
                request.request_id,
                CorpusItemClassified(
                    corpus_item_id=item.corpus_item_id,
                    item_revision=3,
                    classification_hash=classification.content_hash,
                    occurred_at=request.created_at,
                ),
                correlation_id=request.request_id,
            )
            terminal: EventPayload
            if decision.status is CorpusRouteStatus.ALLOWED:
                receipt = receipt_by_item[item.corpus_item_id]
                terminal = CorpusItemRouted(
                    corpus_item_id=item.corpus_item_id,
                    item_revision=item.current_revision,
                    destination=decision.destination,
                    package_hash=receipt.package.content_hash,
                    occurred_at=request.created_at,
                )
            elif decision.status is CorpusRouteStatus.DENIED:
                terminal = CorpusItemRejected(
                    corpus_item_id=item.corpus_item_id,
                    item_revision=item.current_revision,
                    reason_code=decision.reason_codes[0],
                    occurred_at=request.created_at,
                )
            else:
                terminal = CorpusItemQuarantined(
                    corpus_item_id=item.corpus_item_id,
                    item_revision=item.current_revision,
                    reason_code=decision.reason_codes[0],
                    occurred_at=request.created_at,
                )
            await self._events.append(
                request.request_id, terminal, correlation_id=request.request_id
            )
        if result.manifest is not None:
            await self._events.append(
                request.request_id,
                CorpusManifestCreated(
                    corpus_id=result.manifest.corpus_id,
                    corpus_revision=result.manifest.revision,
                    manifest_hash=result.manifest.content_hash,
                    occurred_at=request.created_at,
                ),
                correlation_id=request.request_id,
            )
        if result.export is not None:
            export = result.export.export_manifest
            await self._events.append(
                request.request_id,
                CorpusExportCompleted(
                    export_id=export.export_id,
                    corpus_id=export.corpus_id,
                    corpus_revision=export.corpus_revision,
                    export_hash=export.content_hash,
                    occurred_at=request.created_at,
                ),
                correlation_id=request.request_id,
            )

    def _validate_request_source(
        self, request: CorpusFactoryRequest, source: InspectedSource
    ) -> None:
        if request.source_type is not source.source_type:
            raise CorpusSourceError("request and inspected source type differ")
        if (
            request.source_identity != source.source_identity
            or request.source_revision != source.source_revision
        ):
            raise CorpusSourceError("request and inspected source identity differ")
        if not source.report.safe:
            raise CorpusSourceError("source inspection did not pass")
        if self._config.allow_source_execution or self._config.allow_network_sources:
            raise CorpusPolicyError("source execution and network ingestion are forbidden")

    def _checkpoint(self, request_id: UUID) -> None:
        if request_id in self._cancelled:
            raise CorpusPolicyError("corpus request was cancelled")

    async def _register_source(
        self, request: CorpusFactoryRequest, source: InspectedSource
    ) -> SourceManifest:
        existing = await self._repository.get_source_by_identity(
            source.source_identity, source.source_revision
        )
        if existing is not None:
            return existing
        artifacts = tuple(
            [
                await self._artifacts.put_bytes(material.data, media_type=material.media_type)
                for material in source.materials
            ]
        )
        declarations = tuple(
            self._license_declaration(
                request, identifier, tuple(item.content_hash for item in artifacts)
            )
            for identifier in request.license_identifiers
        )
        rights = tuple(
            UsageRightAssessment(
                right=right,
                allowed=request.usage_rights.get(right),
                evidence_refs=tuple(item.content_hash for item in artifacts),
                reason="explicit operator declaration"
                if right in request.usage_rights
                else "right unknown",
            )
            for right in CorpusUsageRight
        )
        manifest = SourceManifest(
            source_manifest_id=_uuid(
                "source",
                f"{source.source_type.value}:{source.source_identity}:{source.source_revision}",
            ),
            source_type=source.source_type,
            source_identity=source.source_identity,
            source_revision=source.source_revision,
            content_artifacts=artifacts,
            source_hashes=tuple(item.content_hash for item in artifacts),
            origin="operator-controlled-local-source",
            license_declarations=declarations,
            usage_right_declarations=rights,
            scope=request.scope,
            sensitivity=request.sensitivity,
            language=None,
            encoding=None,
            created_at=request.created_at,
            created_by=request.created_by,
        )
        await self._repository.register_source(manifest)
        return manifest

    def _license_declaration(
        self, request: CorpusFactoryRequest, identifier: str, evidence: tuple[str, ...]
    ) -> LicenseDeclaration:
        status = (
            CorpusLicenseStatus.APPROVED
            if identifier in APPROVED_LICENSES
            else CorpusLicenseStatus.INTERNAL
            if identifier in INTERNAL_LICENSES
            else CorpusLicenseStatus.UNKNOWN
        )
        if request.source_type is CorpusSourceType.PROVIDER_GENERATED_DATASET:
            status = CorpusLicenseStatus.UNKNOWN
        return LicenseDeclaration(
            identifier=identifier,
            status=status,
            declared_by=request.created_by,
            evidence_refs=evidence,
        )

    async def _normalize(
        self,
        request: CorpusFactoryRequest,
        source: SourceManifest,
        material: SourceMaterial,
        index: int,
    ) -> NormalizedContent:
        suffix = material.relative_path.rsplit(".", 1)[-1].lower()
        if suffix not in self._normalization_profile.supported_formats:
            raise CorpusNormalizationError(f"unsupported source format: {suffix}")
        normalizer = self._normalizers.resolve(suffix)
        normalized, warnings = normalizer(material.data, material.relative_path)
        if len(normalized) > self._config.maximum_normalized_item_bytes:
            raise CorpusNormalizationError("normalized item byte limit exceeded")
        artifact = await self._artifacts.put_bytes(
            normalized,
            media_type="application/json" if suffix in {"json", "yaml", "yml"} else "text/plain",
        )
        source_entry = source.content_artifacts[index]
        return NormalizedContent(
            normalized_content_id=_uuid("normalized", f"{source.source_manifest_id}:{index}"),
            source_manifest_id=source.source_manifest_id,
            source_file_refs=(
                SourceFileEntry(
                    relative_path=material.relative_path,
                    size_bytes=len(material.data),
                    media_type=material.media_type,
                    file_hash=sha256(material.data).hexdigest(),
                    encoding=material.encoding,
                    archive_origin=material.archive_origin,
                ),
            ),
            content_type=self._content_type(
                material.relative_path, source.source_type, material.data
            ),
            original_artifact_refs=(source_entry,),
            normalized_artifact_ref=artifact,
            canonical_content_hash=artifact.content_hash,
            normalization_profile=self._normalization_profile.content_hash,
            language="python"
            if suffix == "py"
            else "markdown"
            if suffix in {"md", "markdown"}
            else None,
            encoding=material.encoding,
            warnings=warnings,
            created_at=request.created_at,
        )

    def _content_type(
        self, path: str, source_type: CorpusSourceType, data: bytes
    ) -> CorpusContentType:
        if source_type is CorpusSourceType.EXPERIENCE_CANDIDATE:
            try:
                candidate_type = json.loads(data).get("candidate_type")
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                return CorpusContentType.UNKNOWN
            mapping = {
                "memory": CorpusContentType.MEMORY,
                "semantic_observation": CorpusContentType.SEMANTIC_OBSERVATION,
                "skill": CorpusContentType.SKILL,
                "strategy": CorpusContentType.STRATEGY,
                "failure_pattern": CorpusContentType.FAILURE_PATTERN,
                "routing_observation": CorpusContentType.ROUTING_OBSERVATION,
                "benchmark_case": CorpusContentType.BENCHMARK_CASE,
                "negative_example": CorpusContentType.NEGATIVE_EXAMPLE,
                "corpus_item": CorpusContentType.DATASET,
            }
            return mapping.get(candidate_type, CorpusContentType.UNKNOWN)
        suffix = path.rsplit(".", 1)[-1].lower()
        return (
            CorpusContentType.SOURCE_CODE
            if suffix == "py"
            else CorpusContentType.DIFF
            if suffix in {"diff", "patch"}
            else CorpusContentType.DOCUMENTATION
            if suffix in {"md", "markdown", "txt"}
            else CorpusContentType.DATASET
            if suffix in {"json", "jsonl", "yaml", "yml"}
            else CorpusContentType.UNKNOWN
        )

    async def _deduplicate(
        self,
        request: CorpusFactoryRequest,
        source: SourceManifest,
        content: NormalizedContent,
        index: int,
    ) -> DuplicateDecision:
        matches = await self._repository.query_by_content_hash(content.canonical_content_hash)
        duplicate_type = (
            CorpusDuplicateType.EXACT_DUPLICATE if matches else CorpusDuplicateType.UNIQUE
        )
        evidence = DuplicateEvidence(
            key_type="canonical_content_hash",
            key_hash=content.canonical_content_hash,
            matched_item_id=matches[0].corpus_item_id if matches else None,
        )
        return DuplicateDecision(
            corpus_item_id=_uuid(
                "item", f"{request.request_id}:{index}:{content.canonical_content_hash}"
            ),
            duplicate_type=duplicate_type,
            evidence=(evidence,),
            provenance_action="append-source-lineage" if matches else "retain-new-source-lineage",
        )

    def _classify(
        self,
        request: CorpusFactoryRequest,
        source: InspectedSource,
        content: NormalizedContent,
        index: int,
    ) -> CorpusClassification:
        destination_map = {
            CorpusContentType.MEMORY: CorpusDestinationType.GOVERNED_MEMORY_CANDIDATE,
            CorpusContentType.SEMANTIC_OBSERVATION: (
                CorpusDestinationType.SEMANTIC_OBSERVATION_CANDIDATE
            ),
            CorpusContentType.SKILL: CorpusDestinationType.SKILL_CANDIDATE,
            CorpusContentType.STRATEGY: CorpusDestinationType.STRATEGY_CANDIDATE,
            CorpusContentType.FAILURE_PATTERN: CorpusDestinationType.WEAKNESS_SIGNAL,
            CorpusContentType.ROUTING_OBSERVATION: CorpusDestinationType.ROUTING_OBSERVATION,
            CorpusContentType.BENCHMARK_CASE: CorpusDestinationType.BENCHMARK_CASE,
            CorpusContentType.NEGATIVE_EXAMPLE: CorpusDestinationType.NEGATIVE_EXAMPLE,
        }
        destination = destination_map.get(
            content.content_type, CorpusDestinationType.REFERENCE_CORPUS
        )
        knowledge_map = {
            CorpusContentType.MEMORY: CorpusKnowledgeType.EPISODIC,
            CorpusContentType.SEMANTIC_OBSERVATION: CorpusKnowledgeType.SEMANTIC,
            CorpusContentType.SKILL: CorpusKnowledgeType.PROCEDURAL,
            CorpusContentType.STRATEGY: CorpusKnowledgeType.STRATEGIC,
            CorpusContentType.FAILURE_PATTERN: CorpusKnowledgeType.FAILURE_EVIDENCE,
            CorpusContentType.ROUTING_OBSERVATION: CorpusKnowledgeType.ROUTING_EVIDENCE,
            CorpusContentType.BENCHMARK_CASE: CorpusKnowledgeType.BENCHMARK_EVIDENCE,
            CorpusContentType.NEGATIVE_EXAMPLE: CorpusKnowledgeType.NEGATIVE_EXAMPLE,
        }
        item_id = _uuid("item", f"{request.request_id}:{index}:{content.canonical_content_hash}")
        return CorpusClassification(
            classification_id=_uuid("classification", item_id),
            corpus_item_id=item_id,
            item_revision=1,
            content_type=content.content_type,
            domain="software-engineering"
            if content.content_type is not CorpusContentType.UNKNOWN
            else "unknown",
            problem_class="experience-transformation"
            if source.source_type is CorpusSourceType.EXPERIENCE_CANDIDATE
            else "local-corpus-ingestion",
            knowledge_type=knowledge_map.get(
                content.content_type, CorpusKnowledgeType.REFERENCE_MATERIAL
            ),
            candidate_destinations=(destination,),
            negative_example_type="incorrect-or-unsafe-output"
            if content.content_type is CorpusContentType.NEGATIVE_EXAMPLE
            else None,
            training_suitability=(
                request.usage_rights.get(CorpusUsageRight.MODEL_TRAINING) is True
            ),
            benchmark_suitability=destination is CorpusDestinationType.BENCHMARK_CASE,
            reference_suitability=True,
            confidence=1.0 if content.content_type is not CorpusContentType.UNKNOWN else 0.0,
            classifier_profile="sprint15-deterministic-v1",
            evidence=(content.content_hash,),
            limitations=()
            if content.content_type is not CorpusContentType.UNKNOWN
            else ("unknown-content",),
            created_at=request.created_at,
        )

    def _license(
        self,
        request: CorpusFactoryRequest,
        source: SourceManifest,
        content: NormalizedContent,
        index: int,
    ) -> LicenseClassification:
        declarations = source.license_declarations
        statuses = {item.status for item in declarations}
        identifiers = {item.identifier for item in declarations}
        status = (
            CorpusLicenseStatus.UNKNOWN
            if not declarations
            else CorpusLicenseStatus.CONFLICTING
            if len(identifiers) > 1
            else next(iter(statuses))
        )
        conflicts = (
            (
                LicenseConflict(
                    identifiers=tuple(sorted(identifiers)),
                    evidence_refs=source.source_hashes,
                ),
            )
            if len(identifiers) > 1
            else ()
        )
        rights = tuple(
            UsageRightAssessment(
                right=right,
                allowed=request.usage_rights.get(right),
                evidence_refs=(content.content_hash,),
                reason="explicit operator declaration"
                if right in request.usage_rights
                else "right unknown",
            )
            for right in CorpusUsageRight
        )
        return LicenseClassification(
            classification_id=_uuid("license", f"{request.request_id}:{index}"),
            corpus_item_id=_uuid(
                "item", f"{request.request_id}:{index}:{content.canonical_content_hash}"
            ),
            item_revision=1,
            status=status,
            declarations=declarations,
            rights=rights,
            conflicts=conflicts,
            profile="sprint15-license-v1",
            created_at=request.created_at,
        )

    def _sensitivity(
        self,
        request: CorpusFactoryRequest,
        material: SourceMaterial,
        content: NormalizedContent,
        classification: CorpusClassification,
        index: int,
    ) -> CorpusSensitivityAssessment:
        findings: list[CorpusSecretFinding] = []
        if material.encoding == "utf-8":
            for line_number, line in enumerate(material.data.decode("utf-8").splitlines(), 1):
                for match in SECRET_PATTERN.finditer(line):
                    findings.append(
                        CorpusSecretFinding(
                            finding_type=match.group(1).lower(),
                            relative_path=material.relative_path,
                            line_number=line_number,
                            fingerprint=sha256(
                                f"{match.group(1).lower()}:{material.relative_path}:{line_number}".encode()
                            ).hexdigest(),
                        )
                    )
        status = (
            CorpusSensitivityStatus.QUARANTINED
            if findings
            else CorpusSensitivityStatus.REQUIRES_REVIEW
            if request.sensitivity in {MemorySensitivity.CONFIDENTIAL, MemorySensitivity.RESTRICTED}
            else CorpusSensitivityStatus.ALLOWED
        )
        compatible = tuple(
            destination
            for destination in CorpusDestinationType
            if list(MemorySensitivity).index(request.sensitivity)
            <= list(MemorySensitivity).index(
                self._destinations.resolve(destination.value).maximum_sensitivity
            )
        )
        return CorpusSensitivityAssessment(
            assessment_id=_uuid("sensitivity", f"{request.request_id}:{index}"),
            corpus_item_id=_uuid(
                "item", f"{request.request_id}:{index}:{content.canonical_content_hash}"
            ),
            item_revision=1,
            inherited_sensitivity=request.sensitivity,
            effective_sensitivity=request.sensitivity,
            status=status,
            secret_findings=tuple(findings),
            compatible_destinations=compatible,
            reason_codes=("secret-detected",) if findings else (),
            created_at=request.created_at,
        )

    def _quality(
        self,
        request: CorpusFactoryRequest,
        source: InspectedSource,
        content: NormalizedContent,
        classification: CorpusClassification,
        duplicate: DuplicateDecision,
        license_result: LicenseClassification,
        sensitivity: CorpusSensitivityAssessment,
        index: int,
    ) -> CorpusQualityAssessment:
        source_score = (
            0.95
            if source.source_type is CorpusSourceType.EXPERIENCE_CANDIDATE
            else 0.8
            if source.source_type is CorpusSourceType.OPERATOR_ANNOTATION
            else 0.3
            if source.source_type is CorpusSourceType.PROVIDER_GENERATED_DATASET
            else 0.7
        )
        values = {
            CorpusQualityDimensionName.SOURCE_AUTHORITY: source_score,
            CorpusQualityDimensionName.VERIFIER_COVERAGE: 0.95
            if source.source_type is CorpusSourceType.EXPERIENCE_CANDIDATE
            else 0.7,
            CorpusQualityDimensionName.ACCEPTANCE_STATUS: 0.9,
            CorpusQualityDimensionName.PROVENANCE_COMPLETENESS: 1.0,
            CorpusQualityDimensionName.REPRODUCIBILITY: 1.0,
            CorpusQualityDimensionName.CONSISTENCY: 0.4
            if duplicate.duplicate_type is CorpusDuplicateType.CONFLICTING_DUPLICATE
            else 1.0,
            CorpusQualityDimensionName.SENSITIVITY_RISK: 0.0
            if sensitivity.secret_findings
            else 1.0,
            CorpusQualityDimensionName.LICENSING_CLARITY: 1.0
            if license_result.status is CorpusLicenseStatus.APPROVED
            else 0.6
            if license_result.status is CorpusLicenseStatus.INTERNAL
            else 0.0,
            CorpusQualityDimensionName.FORMATTING_INTEGRITY: 0.8 if content.warnings else 1.0,
            CorpusQualityDimensionName.GENERALIZABILITY: 0.8,
            CorpusQualityDimensionName.DUPLICATE_STATUS: 0.8
            if duplicate.duplicate_type is not CorpusDuplicateType.CONFLICTING_DUPLICATE
            else 0.2,
            CorpusQualityDimensionName.CONTRADICTION_STATUS: 1.0,
        }
        blockers: list[str] = []
        if sensitivity.secret_findings:
            blockers.append("secret-detected")
        if classification.content_type is CorpusContentType.UNKNOWN:
            blockers.append("unsupported-destination-schema")
        if license_result.status in {
            CorpusLicenseStatus.CONFLICTING,
            CorpusLicenseStatus.RESTRICTED,
        }:
            blockers.append("prohibited-usage-right")
        score = sum(values[item] * self._quality_profile.weights[item] for item in values)
        tier = (
            CorpusQualityTier.BLOCKED
            if blockers
            else CorpusQualityTier.HIGH
            if score >= 0.8
            else CorpusQualityTier.MEDIUM
            if score >= 0.6
            else CorpusQualityTier.LOW
        )
        dimensions = tuple(
            CorpusQualityDimension(
                dimension=dimension,
                score=values[dimension],
                status="passed" if values[dimension] >= 0.6 else "review",
                evidence=(content.content_hash,),
                profile_version=1,
            )
            for dimension in CorpusQualityDimensionName
        )
        return CorpusQualityAssessment(
            assessment_id=_uuid("quality", f"{request.request_id}:{index}"),
            corpus_item_id=_uuid(
                "item", f"{request.request_id}:{index}:{content.canonical_content_hash}"
            ),
            item_revision=1,
            dimensions=dimensions,
            score=score,
            tier=tier,
            hard_blockers=tuple(blockers),
            limitations=("license-review-required",)
            if license_result.status
            in {CorpusLicenseStatus.UNKNOWN, CorpusLicenseStatus.CONFLICTING}
            else (),
            profile_hash=self._quality_profile.content_hash,
            created_at=request.created_at,
        )

    def _lineage(self, source: SourceManifest, content: NormalizedContent) -> CorpusLineage:
        target = str(content.normalized_content_id)
        return CorpusLineage(
            lineage_id=_uuid("lineage", target),
            edges=tuple(
                CorpusLineageEdge(
                    source_identity=str(source.source_manifest_id),
                    target_identity=target,
                    relationship=CorpusLineageRelationship.NORMALIZED_FROM,
                    evidence_refs=(artifact.content_hash,),
                )
                for artifact in source.content_artifacts
            ),
            contributions=tuple(
                CorpusSourceContribution(
                    source_manifest_id=source.source_manifest_id,
                    contribution="original-source",
                    evidence_refs=source.source_hashes,
                )
                for _ in (0,)
            ),
        )

    def _route(
        self,
        request: CorpusFactoryRequest,
        content: NormalizedContent,
        classification: CorpusClassification,
        license_result: LicenseClassification,
        sensitivity: CorpusSensitivityAssessment,
        quality: CorpusQualityAssessment,
        destination: CorpusDestinationType,
        index: int,
    ) -> CorpusRouteDecision:
        policy = self._destinations.resolve(destination.value)
        rights = {item.right: item.allowed for item in license_result.rights}
        reasons: list[str] = []
        status = CorpusRouteStatus.ALLOWED
        if license_result.status in {CorpusLicenseStatus.UNKNOWN, CorpusLicenseStatus.CONFLICTING}:
            status = CorpusRouteStatus.QUARANTINED
            reasons.append("license-review-required")
        elif license_result.status is CorpusLicenseStatus.RESTRICTED:
            status = CorpusRouteStatus.DENIED
            reasons.append("restricted-license")
        if any(rights.get(right) is not True for right in policy.required_rights):
            status = (
                CorpusRouteStatus.DENIED
                if destination is CorpusDestinationType.TRAINING_CORPUS
                else CorpusRouteStatus.QUARANTINED
            )
            reasons.append("required-usage-right-absent")
        if sensitivity.secret_findings:
            status = CorpusRouteStatus.QUARANTINED
            reasons.append("secret-detected")
        if destination not in sensitivity.compatible_destinations:
            status = CorpusRouteStatus.QUARANTINED
            reasons.append("sensitivity-incompatible")
        if quality.hard_blockers:
            status = CorpusRouteStatus.QUARANTINED
            reasons.extend(quality.hard_blockers)
        if quality.score < self._quality_profile.destination_thresholds[destination]:
            status = CorpusRouteStatus.QUARANTINED
            reasons.append("quality-below-threshold")
        if content.content_type not in policy.required_content_types:
            status = CorpusRouteStatus.DENIED
            reasons.append("unsupported-destination-schema")
        item_id = _uuid("item", f"{request.request_id}:{index}:{content.canonical_content_hash}")
        return CorpusRouteDecision(
            route_decision_id=_uuid("route", f"{item_id}:{destination.value}"),
            corpus_item_id=item_id,
            item_revision=4 if status is CorpusRouteStatus.ALLOWED else 3,
            destination=destination,
            destination_policy_hash=policy.content_hash,
            status=status,
            reason_codes=tuple(sorted(set(reasons))),
            required_verifiers=MANDATORY_VERIFIERS,
            required_review=status is CorpusRouteStatus.QUARANTINED,
            created_at=request.created_at,
        )

    async def _advance(
        self,
        request: CorpusFactoryRequest,
        item: CorpusItem,
        next_status: CorpusItemStatus,
        evidence_hash: str,
    ) -> CorpusItem:
        if next_status not in LEGAL_TRANSITIONS[item.current_status]:
            raise CorpusPolicyError("illegal corpus lifecycle transition")
        transition = CorpusStatusTransition(
            corpus_item_id=item.corpus_item_id,
            expected_revision=item.current_revision,
            expected_status=item.current_status,
            next_revision=item.current_revision + 1,
            next_status=next_status,
            actor_id=request.created_by,
            reason=f"corpus-{next_status.value}",
            verifier_bundle_hash=canonical_hash(MANDATORY_VERIFIERS),
            policy_decision_hash=evidence_hash,
            created_at=request.created_at,
        )
        return await self._repository.advance_item_status(transition)

    async def _build_package(
        self,
        request: CorpusFactoryRequest,
        item: CorpusItem,
        source: SourceManifest,
        classification: CorpusClassification,
        license_result: LicenseClassification,
        sensitivity: CorpusSensitivityAssessment,
        quality: CorpusQualityAssessment,
        route: CorpusRouteDecision,
    ) -> DestinationPackageReference:
        policy = self._destinations.resolve(route.destination.value)
        payload = {
            "schema": policy.package_schema,
            "corpus_item": item.model_dump(mode="json"),
            "sources": source.model_dump(mode="json"),
            "classification": classification.model_dump(mode="json"),
            "license_and_rights": license_result.model_dump(mode="json"),
            "sensitivity": sensitivity.model_dump(mode="json"),
            "quality": quality.model_dump(mode="json"),
            "route_decision": route.model_dump(mode="json"),
            "constraints": (
                "proposal-only",
                "no-destination-write",
                "no-promotion",
                "no-training-action",
            ),
        }
        encoded = _canonical_json(payload)
        artifact = await self._artifacts.put_bytes(encoded, media_type="application/json")
        return DestinationPackageReference(
            package_id=_uuid("package", route.route_decision_id),
            corpus_item_id=item.corpus_item_id,
            item_revision=item.current_revision,
            destination=route.destination,
            schema_version=policy.package_schema,
            artifact=artifact,
            checksums=(artifact.content_hash,),
        )

    def _accesses(
        self,
        request: CorpusFactoryRequest,
        source: SourceManifest,
        item: CorpusItem,
        index: int,
    ) -> tuple[CorpusAccessRecord, ...]:
        return tuple(
            CorpusAccessRecord(
                access_id=_uuid("access", f"{request.request_id}:{index}:{access_type.value}"),
                access_type=access_type,
                source_manifest_id=source.source_manifest_id,
                corpus_item_id=item.corpus_item_id,
                item_revision=item.current_revision,
                actor_id="corpus-factory",
                accessed_at=request.created_at,
            )
            for access_type in (
                CorpusAccessType.SOURCE_REGISTRATION,
                CorpusAccessType.SOURCE_READ,
                CorpusAccessType.NORMALIZATION,
                CorpusAccessType.DEDUPLICATION,
                CorpusAccessType.CLASSIFICATION,
                CorpusAccessType.LICENSE_REVIEW,
                CorpusAccessType.QUALITY_SCORING,
                CorpusAccessType.ROUTING,
            )
        )

    async def _manifest_and_export(
        self,
        request: CorpusFactoryRequest,
        items: list[CorpusItem],
        licenses: list[LicenseClassification],
        sensitivities: list[CorpusSensitivityAssessment],
    ) -> tuple[CorpusManifest | None, CorpusExportResult | None]:
        eligible = sorted(
            (
                item
                for item in items
                if item.current_status in {CorpusItemStatus.ROUTED, CorpusItemStatus.STAGED}
            ),
            key=lambda item: str(item.corpus_item_id),
        )
        if not eligible:
            return None, None
        manifest_items = tuple(
            CorpusManifestItem(
                corpus_item_id=item.corpus_item_id,
                item_revision=item.current_revision,
                item_hash=item.content_hash,
                split=self._split(item.lineage_ref),
            )
            for item in eligible
        )
        split = CorpusSplitManifest(
            profile_id="sprint15-lineage-safe-split-v1",
            seed=15,
            assignments=manifest_items,
            lineage_group_hashes=tuple(sorted({item.lineage_ref for item in eligible})),
        )
        purpose = request.requested_destination or CorpusDestinationType.REFERENCE_CORPUS
        corpus_id = _uuid("manifest", f"{request.request_id}:{purpose.value}")
        manifest_payload = {
            "corpus_id": str(corpus_id),
            "revision": 1,
            "purpose": purpose.value,
            "items": [item.model_dump(mode="json") for item in manifest_items],
            "split": split.model_dump(mode="json"),
        }
        manifest_artifact = await self._artifacts.put_bytes(
            _canonical_json(manifest_payload), media_type="application/json"
        )
        manifest = CorpusManifest(
            corpus_id=corpus_id,
            revision=1,
            purpose=purpose,
            items=manifest_items,
            selection_policy="routed-or-staged-v1",
            normalization_profile=self._normalization_profile.content_hash,
            deduplication_profile=self._deduplication_profile.content_hash,
            classification_profile=canonical_hash("sprint15-deterministic-v1"),
            quality_profile=self._quality_profile.content_hash,
            license_summary=self._summary(item.status.value for item in licenses),
            sensitivity_summary=self._summary(item.status.value for item in sensitivities),
            split_manifest=split,
            lineage_hash=canonical_hash([item.lineage_ref for item in eligible]),
            artifact_reference=manifest_artifact,
            created_at=request.created_at,
            created_by=request.created_by,
        )
        await self._repository.create_manifest(manifest)
        lines = b"".join(_canonical_json(item.model_dump(mode="json")) + b"\n" for item in eligible)
        export_artifact = await self._artifacts.put_bytes(lines, media_type="application/x-ndjson")
        export_manifest = CorpusExportManifest(
            export_id=_uuid("export", manifest.content_hash),
            corpus_id=manifest.corpus_id,
            corpus_revision=manifest.revision,
            export_type=CorpusExportType.JSONL,
            artifact=export_artifact,
            item_hashes=tuple(item.content_hash for item in eligible),
            manifest_hash=manifest.content_hash,
            created_at=request.created_at,
        )
        await self._repository.create_export(export_manifest)
        return manifest, CorpusExportResult(export_manifest=export_manifest, reproduced=True)

    @staticmethod
    def _split(lineage_hash: str) -> CorpusSplit:
        bucket = (int(lineage_hash[:8], 16) + 15) % 100
        return (
            CorpusSplit.TRAIN
            if bucket < 80
            else CorpusSplit.VALIDATION
            if bucket < 90
            else CorpusSplit.TEST
            if bucket < 95
            else CorpusSplit.HOLDOUT
        )

    @staticmethod
    def _summary(values: Iterable[object]) -> dict[str, int]:
        result: dict[str, int] = {}
        for value in values:
            key = str(value or "unknown")
            result[key] = result.get(key, 0) + 1
        return result
