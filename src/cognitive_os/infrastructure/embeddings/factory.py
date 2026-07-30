"""Build the configured embedding provider, or refuse. §S21C3-052.

There is one rule here and the module exists to hold it: a configuration that asks for the
local model and cannot have it raises. It never quietly returns the deterministic provider.

That provider is a hashing vector — it has no semantic content at all — so a fallback would
not degrade retrieval, it would replace it, and the resulting evidence would carry the
production provider's name over numbers a hash produced. §4.15 measures the two against each
other precisely because they are not interchangeable.
"""

from __future__ import annotations

from cognitive_os.application.ports.embedding_provider import EmbeddingProviderPort
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration
from cognitive_os.memory.errors import EmbeddingUnavailableError

from . import minilm
from .deterministic import DeterministicEmbeddingProvider
from .sentence_transformers import LocalSentenceTransformerProvider


def build_embedding_provider(
    config: EmbeddingProviderConfiguration,
    *,
    maximum_batch_size: int = 64,
) -> EmbeddingProviderPort:
    """The configured provider, verified. Raises rather than substituting one."""
    if config.provider_type == "deterministic":
        return DeterministicEmbeddingProvider(
            dimension=config.dimension, maximum_batch_size=maximum_batch_size
        )

    root = config.local_model_path
    if root is None:  # the configuration validator already refuses this
        raise EmbeddingUnavailableError("local embedding provider declares no model path")
    # Declarative checks first. They are what a misconfiguration usually is, and answering
    # them costs a file read rather than loading ~88 MB of weights to reach the same verdict.
    manifest = minilm.read_manifest(root)
    if manifest is None:
        status, reason = minilm.health(root)
        raise EmbeddingUnavailableError(f"local embedding model is {status.value}: {reason}")
    if manifest.get("tree_digest") != config.local_model_digest:
        raise EmbeddingUnavailableError(
            "local embedding model digest does not match the configured identity"
        )
    if config.dimension != minilm.DIMENSION:
        raise EmbeddingUnavailableError(
            f"configuration declares {config.dimension} dimensions, model produces "
            f"{minilm.DIMENSION}"
        )
    status, reason = minilm.health(root)
    if status is not minilm.ModelHealth.HEALTHY:
        raise EmbeddingUnavailableError(f"local embedding model is {status.value}: {reason}")
    return LocalSentenceTransformerProvider(
        root,
        model_id=config.model_id,
        model_digest=manifest["tree_digest"],
        dimension=config.dimension,
        maximum_batch_size=maximum_batch_size,
    )
