"""Provider-neutral token-estimator boundary."""

from typing import Protocol

from cognitive_os.domain.context import (
    ContextComponentHealth,
    ContextSection,
    TokenEstimatorProfile,
)
from cognitive_os.domain.model_requests import ProviderMessage


class TokenEstimatorPort(Protocol):
    @property
    def profile(self) -> TokenEstimatorProfile: ...

    def estimate_text(self, text: str) -> int: ...

    def estimate_messages(self, messages: tuple[ProviderMessage, ...]) -> int: ...

    def estimate_section(self, section: ContextSection) -> int: ...

    async def health_check(self) -> ContextComponentHealth: ...
