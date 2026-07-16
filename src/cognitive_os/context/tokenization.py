"""Dependency-free conservative token estimation."""

from cognitive_os.domain.context import (
    ContextComponentHealth,
    ContextComponentStatus,
    ContextSection,
    TokenEstimatorProfile,
    TokenEstimatorType,
)
from cognitive_os.domain.model_requests import ProviderMessage


class ConservativeUtf8TokenEstimator:
    def __init__(self, *, bytes_per_token: int = 3, per_message_overhead: int = 4) -> None:
        self._profile = TokenEstimatorProfile(
            estimator_type=TokenEstimatorType.CONSERVATIVE_UTF8,
            estimator_id="context.utf8",
            version="1",
            bytes_per_token=bytes_per_token,
            per_message_overhead=per_message_overhead,
        )

    @property
    def profile(self) -> TokenEstimatorProfile:
        return self._profile

    def estimate_text(self, text: str) -> int:
        size = len(text.encode("utf-8"))
        return (size + self.profile.bytes_per_token - 1) // self.profile.bytes_per_token

    def estimate_messages(self, messages: tuple[ProviderMessage, ...]) -> int:
        return sum(
            self.estimate_text(item.content) + self.profile.per_message_overhead
            for item in messages
        )

    def estimate_section(self, section: ContextSection) -> int:
        return self.estimate_text(section.title) + self.estimate_text(section.content) + 4

    async def health_check(self) -> ContextComponentHealth:
        return ContextComponentHealth(status=ContextComponentStatus.AVAILABLE)
