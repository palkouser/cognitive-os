"""Deterministic verification for Corpus Factory results."""

from cognitive_os.corpus.factory import MANDATORY_VERIFIERS
from cognitive_os.domain.corpus import (
    CorpusFactoryResult,
    CorpusItemStatus,
    CorpusQualityDimensionName,
    CorpusRouteStatus,
    CorpusUsageRight,
)


def verify_corpus_result(result: CorpusFactoryResult) -> tuple[str, ...]:
    """Return stable failure codes; an empty tuple means all twenty gates passed."""

    failures: list[str] = []
    source = result.source_manifest
    if tuple(item.content_hash for item in source.content_artifacts) != source.source_hashes:
        failures.append("corpus.source_integrity")
    if not source.source_identity or source.source_identity.startswith("/"):
        failures.append("corpus.archive_safety")
    if any(
        ".." in entry.relative_path.split("/")
        for item in result.normalized
        for entry in item.source_file_refs
    ):
        failures.append("corpus.path_safety")
    if len(result.normalized) != len(result.items):
        failures.append("corpus.normalization_schema")
    if any(
        item.canonical_content_hash != item.normalized_artifact_ref.content_hash
        for item in result.normalized
    ):
        failures.append("corpus.normalization_determinism")
    if any(not item.original_artifact_refs for item in result.normalized):
        failures.append("corpus.original_preservation")
    if len(result.duplicates) != len(result.items):
        failures.append("corpus.deduplication_integrity")
    if any(not item.lineage_ref for item in result.items):
        failures.append("corpus.lineage_integrity")
    if len(result.classifications) != len(result.items):
        failures.append("corpus.classification_schema")
    if any(not item.declarations for item in result.licenses):
        failures.append("corpus.license_policy")
    if any(
        {right.right for right in item.rights} != set(CorpusUsageRight) for item in result.licenses
    ):
        failures.append("corpus.usage_rights")
    if len(result.sensitivity) != len(result.items):
        failures.append("corpus.sensitivity_policy")
    if any(
        item.secret_findings and route.status is CorpusRouteStatus.ALLOWED
        for item, route in zip(result.sensitivity, result.route_decisions, strict=True)
    ):
        failures.append("corpus.secret_policy")
    if any(
        {dimension.dimension for dimension in item.dimensions} != set(CorpusQualityDimensionName)
        for item in result.quality
    ):
        failures.append("corpus.quality_reproducibility")
    if any(
        item.current_status is CorpusItemStatus.ROUTED
        and route.status is not CorpusRouteStatus.ALLOWED
        for item, route in zip(result.items, result.route_decisions, strict=True)
    ):
        failures.append("corpus.route_policy")
    if any(receipt.package.authority_claims for receipt in result.receipts):
        failures.append("corpus.destination_package_schema")
    manifest_hashes = (
        tuple(sorted(item.item_hash for item in result.manifest.items)) if result.manifest else ()
    )
    routed_hashes = tuple(
        sorted(
            item.content_hash
            for item in result.items
            if item.current_status is CorpusItemStatus.ROUTED
        )
    )
    if result.manifest and manifest_hashes != routed_hashes:
        failures.append("corpus.manifest_integrity")
    if result.export and not result.export.reproduced:
        failures.append("corpus.export_reproducibility")
    if any(receipt.promoted for receipt in result.receipts) or result.usage.get(
        "destination_writes"
    ):
        failures.append("corpus.no_destination_promotion")
    if result.usage.get("training_actions"):
        failures.append("corpus.no_model_training")
    return tuple(capability for capability in MANDATORY_VERIFIERS if capability in failures)
