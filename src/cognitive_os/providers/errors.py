"""Credential-safe provider error taxonomy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognitive_os.domain.common import JsonValue
from cognitive_os.domain.model_requests import reject_secret_keys


class ProviderError(Exception):
    """Base normalized provider failure."""

    default_code = "provider_error"
    default_retryable = False

    def __init__(
        self,
        *,
        provider_id: str,
        message: str,
        error_code: str | None = None,
        retryable: bool | None = None,
        attempt: int | None = None,
        provider_request_id: str | None = None,
        details: Mapping[str, JsonValue] | None = None,
    ) -> None:
        safe_details = dict(details or {})
        try:
            reject_secret_keys(safe_details, path="details")
        except ValueError:
            safe_details = {"redacted": True}
        self.provider_id = provider_id
        self.error_code = error_code or self.default_code
        self.message = message
        self.retryable = self.default_retryable if retryable is None else retryable
        self.attempt = attempt
        self.provider_request_id = provider_request_id
        self.details = safe_details
        super().__init__(message)

    def with_attempt(self, attempt: int) -> ProviderError:
        return type(self)(
            provider_id=self.provider_id,
            message=self.message,
            error_code=self.error_code,
            retryable=self.retryable,
            attempt=attempt,
            provider_request_id=self.provider_request_id,
            details=self.details,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "error_code": self.error_code,
            "message": self.message,
            "retryable": self.retryable,
            "attempt": self.attempt,
            "provider_request_id": self.provider_request_id,
            "details": self.details,
        }


class ProviderConfigurationError(ProviderError):
    default_code = "provider_configuration"


class ProviderAuthenticationError(ProviderError):
    default_code = "provider_authentication"


class ProviderAuthorizationError(ProviderError):
    default_code = "provider_authorization"


class ProviderUnavailableError(ProviderError):
    default_code = "provider_unavailable"
    default_retryable = True


class ProviderConnectionError(ProviderError):
    default_code = "provider_connection"
    default_retryable = True


class ProviderTimeoutError(ProviderError):
    default_code = "provider_timeout"
    default_retryable = True


class ProviderRateLimitError(ProviderError):
    default_code = "provider_rate_limit"
    default_retryable = True


class ProviderInvalidRequestError(ProviderError):
    default_code = "provider_invalid_request"


class ProviderInvalidResponseError(ProviderError):
    default_code = "provider_invalid_response"


class ProviderUnsupportedCapabilityError(ProviderError):
    default_code = "provider_unsupported_capability"


class ProviderContentPolicyError(ProviderError):
    default_code = "provider_content_policy"


class ProviderContextValidationError(ProviderError):
    default_code = "provider_context_validation"


class ProviderCancelledError(ProviderError):
    default_code = "provider_cancelled"


class ProviderProcessError(ProviderError):
    default_code = "provider_process"


class ProviderBudgetExceededError(ProviderError):
    default_code = "provider_budget_exceeded"


class ProviderPersistenceError(ProviderError):
    default_code = "provider_persistence"
