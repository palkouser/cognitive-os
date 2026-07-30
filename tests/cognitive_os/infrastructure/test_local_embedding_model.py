"""S21C3-050 to S21C3-052: the frozen model's identity, and the refusal to substitute for it.

Loading the real model needs the ~88 MB tree an operator prefetches, so what is asserted here
is everything that must hold *around* the load: an unfetched directory is unusable, tampered
bytes are unusable, and neither one is quietly answered with the hashing provider.

The healthy path is covered by `scripts/retrieval_benchmark.py`, which refuses to run at all
unless `health` returns healthy — a run that produced numbers is a run that passed it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cognitive_os.config.memory_config import EmbeddingProviderConfiguration
from cognitive_os.infrastructure.embeddings import (
    DeterministicEmbeddingProvider,
    build_embedding_provider,
    minilm,
)
from cognitive_os.memory.errors import EmbeddingUnavailableError


def _fetched(root: Path) -> dict:
    """A directory shaped like a prefetched model, with placeholder weights."""
    for name in minilm.MODEL_FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"placeholder for {name}".encode())
    manifest = minilm.build_manifest(root)
    (root / minilm.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def _configuration(root: Path, digest: str, dimension: int = 384) -> EmbeddingProviderConfiguration:
    return EmbeddingProviderConfiguration(
        provider_type="sentence_transformers",
        model_id=minilm.MODEL_ID,
        dimension=dimension,
        local_model_path=root,
        local_model_digest=digest,
    )


# ------------------------------------------------------------------ identity


def test_the_revision_is_a_commit_and_not_a_branch() -> None:
    """§4.14 prohibits `main` and `latest` at runtime; a 40-hex revision is the enforcement."""
    assert len(minilm.REVISION) == 40
    assert minilm.REVISION not in {"main", "latest"}
    assert minilm.DIMENSION == 384
    assert minilm.LICENCE == "apache-2.0"


def test_an_unfetched_directory_is_missing(tmp_path: Path) -> None:
    status, reason = minilm.health(tmp_path)

    assert status is minilm.ModelHealth.MISSING
    assert minilm.MANIFEST_NAME in reason


def test_a_manifest_pinning_another_revision_is_refused(tmp_path: Path) -> None:
    """A directory fetched before the freeze is not this model, whatever its bytes hash to."""
    manifest = _fetched(tmp_path)
    manifest["revision"] = "main"
    (tmp_path / minilm.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")

    status, _ = minilm.health(tmp_path)

    assert status is minilm.ModelHealth.DIGEST_MISMATCH


def test_changed_bytes_are_reported_by_name(tmp_path: Path) -> None:
    _fetched(tmp_path)
    (tmp_path / "config.json").write_bytes(b"tampered")

    status, reason = minilm.health(tmp_path)

    assert status is minilm.ModelHealth.DIGEST_MISMATCH
    assert "config.json" in reason


def test_a_deleted_file_is_missing_not_a_digest_problem(tmp_path: Path) -> None:
    _fetched(tmp_path)
    (tmp_path / "vocab.txt").unlink()

    status, reason = minilm.health(tmp_path)

    assert status is minilm.ModelHealth.MISSING
    assert "vocab.txt" in reason


def test_the_tree_digest_does_not_depend_on_file_order(tmp_path: Path) -> None:
    manifest = _fetched(tmp_path)

    assert manifest["tree_digest"] == minilm.tree_digest(minilm.file_digests(tmp_path))


# ------------------------------------------------------------------ no fallback


def test_a_missing_model_raises_rather_than_returning_the_hashing_provider(tmp_path: Path) -> None:
    """The one rule of §S21C3-052. A substitution here would be a lie in the evidence file."""
    with pytest.raises(EmbeddingUnavailableError, match="missing"):
        build_embedding_provider(_configuration(tmp_path, "0" * 64))


def test_a_digest_the_configuration_did_not_expect_raises(tmp_path: Path) -> None:
    _fetched(tmp_path)

    with pytest.raises(EmbeddingUnavailableError):
        build_embedding_provider(_configuration(tmp_path, "1" * 64))


def test_a_configuration_declaring_the_wrong_dimension_raises(tmp_path: Path) -> None:
    manifest = _fetched(tmp_path)

    with pytest.raises(EmbeddingUnavailableError):
        build_embedding_provider(_configuration(tmp_path, manifest["tree_digest"], dimension=768))


def test_the_deterministic_provider_is_still_available_when_it_is_the_one_asked_for() -> None:
    """Refusing to *substitute* it is not refusing to build it."""
    provider = build_embedding_provider(
        EmbeddingProviderConfiguration(
            provider_type="deterministic", model_id="deterministic-v1", dimension=64
        )
    )

    assert isinstance(provider, DeterministicEmbeddingProvider)
