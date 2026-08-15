"""Fail-closed host configuration for the Corpus-to-Memory Factory."""

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel


class CorpusConfiguration(ImmutableContractModel):
    maximum_sources_per_request: int = Field(default=1_000, ge=1, le=1_000)
    maximum_items_per_request: int = Field(default=10_000, ge=1, le=10_000)
    maximum_source_files: int = Field(default=10_000, ge=1, le=10_000)
    maximum_source_bytes: int = Field(default=1_073_741_824, ge=1, le=1_073_741_824)
    maximum_single_file_bytes: int = Field(default=67_108_864, ge=1, le=67_108_864)
    maximum_normalized_item_bytes: int = Field(default=16_777_216, ge=1, le=16_777_216)
    maximum_archive_bytes: int = Field(default=1_073_741_824, ge=1, le=1_073_741_824)
    maximum_archive_files: int = Field(default=10_000, ge=1, le=10_000)
    maximum_archive_depth: int = Field(default=16, ge=1, le=16)
    maximum_archive_expansion_ratio: float = Field(default=20.0, ge=1, le=20)
    maximum_directory_depth: int = Field(default=32, ge=1, le=32)
    maximum_manifest_items: int = Field(default=1_000_000, ge=1, le=1_000_000)
    maximum_lineage_sources: int = Field(default=1_024, ge=1, le=1_024)
    maximum_route_decisions_per_item: int = Field(default=32, ge=1, le=32)
    maximum_export_bytes: int = Field(default=10_737_418_240, ge=1, le=10_737_418_240)
    near_duplicate_threshold: float = Field(default=0.95, ge=0, le=1)
    minimum_training_quality_score: float = Field(default=0.80, ge=0, le=1)
    minimum_benchmark_quality_score: float = Field(default=0.85, ge=0, le=1)
    minimum_reference_quality_score: float = Field(default=0.60, ge=0, le=1)
    unknown_license_action: str = "quarantine"
    conflicting_license_action: str = "quarantine"
    restricted_license_action: str = "reject"
    detected_secret_action: str = "quarantine"
    integrity_failure_action: str = "reject"
    ambiguous_route_action: str = "quarantine"
    allow_network_sources: bool = False
    allow_remote_download: bool = False
    allow_source_execution: bool = False
    allow_automatic_destination_write: bool = False
    allow_automatic_promotion: bool = False
    allow_automatic_duplicate_merge: bool = False
    allow_provider_license_authority: bool = False
    allow_provider_route_authority: bool = False
    allow_model_training: bool = False

    @model_validator(mode="after")
    def prohibit_deferred_authority(self) -> "CorpusConfiguration":
        prohibited = (
            self.allow_network_sources,
            self.allow_remote_download,
            self.allow_source_execution,
            self.allow_automatic_destination_write,
            self.allow_automatic_promotion,
            self.allow_automatic_duplicate_merge,
            self.allow_provider_license_authority,
            self.allow_provider_route_authority,
            self.allow_model_training,
        )
        if any(prohibited):
            raise ValueError(
                "network, execution, promotion, training, and provider authority are forbidden"
            )
        return self

    @model_validator(mode="after")
    def actions_are_refusals(self) -> "CorpusConfiguration":
        """Every `*_action` names a refusal, and none of them can name a permission.

        **Sprint 22C W1-D2.** These six fields were read by nothing until the Corpus Factory
        was taught to consult them, and an unvalidated action string would have reached the
        routing table as a `KeyError` at ingest time — the worst place to discover a typo in
        a configuration file. Validated here, at load, where a bad value is a refusal to
        start rather than a failure mid-run.

        `allow` is deliberately not a legal value. Configuration may choose how strictly to
        refuse material nobody has cleared; it may not choose to permit it. Permission comes
        from an `OperatorLicenseClearance` and from nowhere else, because the legal
        responsibility for using material is a person's and cannot be delegated to a file.
        """
        permitted = {"quarantine", "reject"}
        actions = {
            "unknown_license_action": self.unknown_license_action,
            "conflicting_license_action": self.conflicting_license_action,
            "restricted_license_action": self.restricted_license_action,
            "detected_secret_action": self.detected_secret_action,
            "integrity_failure_action": self.integrity_failure_action,
            "ambiguous_route_action": self.ambiguous_route_action,
        }
        wrong = {name: value for name, value in actions.items() if value not in permitted}
        if wrong:
            raise ValueError(
                f"corpus actions must be one of {sorted(permitted)}; got {sorted(wrong.items())}"
            )
        return self


def load_corpus_configuration(path: Path) -> CorpusConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("corpus"), dict):
        raise ValueError("corpus configuration requires a corpus mapping")
    return CorpusConfiguration.model_validate(raw["corpus"])
