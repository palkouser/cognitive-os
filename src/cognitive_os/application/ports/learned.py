"""Optional learned-component boundaries — the extension seam.

A learned component is declared in configuration and reached only through these
protocols. Adding one is additive: a new adapter module, a configuration entry, an
optional dependency group, and a registry entry. The deterministic mandatory path
must produce identical decisions whether a component is absent, disabled, or
abstaining, which `MandatoryPathInvariance` records and CI proves.

`LearnedComponentPort` is deliberately the only mandatory protocol. The two
learned adapters this repository already ships — the local embedding provider and
the local cross-encoder reranker — are inference-only, and a component that never
trains must not be forced to implement a trainer.
"""

from typing import Protocol

from cognitive_os.domain.learned import (
    LearnedComponentDescriptor,
    LearnedDatasetSnapshot,
    LearnedPrediction,
    SituationVector,
)


class LearnedComponentHealth(Protocol):
    @property
    def available(self) -> bool: ...
    @property
    def reason(self) -> str: ...


class LearnedComponentPort(Protocol):
    """Inference boundary. Every component must be able to abstain."""

    @property
    def descriptor(self) -> LearnedComponentDescriptor: ...

    async def health_check(self) -> LearnedComponentHealth: ...

    async def predict(self, situation: SituationVector) -> LearnedPrediction: ...


class LearnedTrainerPort(Protocol):
    """Optional training boundary over an immutable, rights-cleared snapshot."""

    @property
    def descriptor(self) -> LearnedComponentDescriptor: ...

    async def train(self, dataset: LearnedDatasetSnapshot) -> str:
        """Return the digest of the produced model artifact."""
        ...


class LearnedDatasetPort(Protocol):
    """Materialise a hash-identified snapshot from governed sources."""

    async def materialise(
        self, *, surface: str, corpus_role: str, revision: int
    ) -> LearnedDatasetSnapshot: ...


class LearnedArtifactStorePort(Protocol):
    """Content-addressed model-artifact storage. Untrusted pickle is prohibited."""

    async def put(self, payload: bytes, *, media_type: str) -> str: ...

    async def get(self, digest: str) -> bytes: ...
