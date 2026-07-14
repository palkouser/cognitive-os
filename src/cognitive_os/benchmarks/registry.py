"""Deterministic freezeable benchmark manifest registry."""

import json
from hashlib import sha256

from cognitive_os.domain.benchmarks import BenchmarkManifest

from .errors import BenchmarkNotFoundError, BenchmarkRegistrationError


class BenchmarkRegistry:
    def __init__(self) -> None:
        self._manifests: dict[tuple[str, str], BenchmarkManifest] = {}
        self._frozen = False

    def register_manifest(self, manifest: BenchmarkManifest) -> None:
        if self._frozen:
            raise BenchmarkRegistrationError("benchmark registry is frozen")
        key = (manifest.benchmark_id, manifest.version)
        if key in self._manifests:
            raise BenchmarkRegistrationError(
                f"duplicate benchmark manifest: {manifest.benchmark_id}@{manifest.version}"
            )
        self._manifests[key] = manifest

    def get_manifest(self, benchmark_id: str, version: str) -> BenchmarkManifest:
        try:
            return self._manifests[(benchmark_id, version)]
        except KeyError as error:
            raise BenchmarkNotFoundError(
                f"benchmark is not registered: {benchmark_id}@{version}"
            ) from error

    def list_manifests(self) -> tuple[BenchmarkManifest, ...]:
        return tuple(self._manifests[key] for key in sorted(self._manifests))

    def validate_manifest(self, manifest: BenchmarkManifest) -> None:
        BenchmarkManifest.model_validate(manifest.model_dump(mode="python"))

    def freeze(self) -> None:
        self._frozen = True

    def snapshot(self) -> str:
        records = [
            {
                "benchmark_id": item.benchmark_id,
                "version": item.version,
                "manifest_hash": item.manifest_hash,
            }
            for item in self.list_manifests()
        ]
        return sha256(
            json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
