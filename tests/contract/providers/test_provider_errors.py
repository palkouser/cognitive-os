import pytest

from cognitive_os.providers.errors import (
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderBudgetExceededError,
    ProviderCancelledError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderContentPolicyError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderInvalidResponseError,
    ProviderPersistenceError,
    ProviderProcessError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnsupportedCapabilityError,
)

ERROR_TYPES = (
    ProviderConfigurationError,
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderUnavailableError,
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderInvalidRequestError,
    ProviderInvalidResponseError,
    ProviderUnsupportedCapabilityError,
    ProviderContentPolicyError,
    ProviderCancelledError,
    ProviderProcessError,
    ProviderBudgetExceededError,
    ProviderPersistenceError,
)


def test_provider_error_is_typed_retry_explicit_and_secret_safe() -> None:
    error = ProviderAuthenticationError(
        provider_id="provider",
        message="authentication failed",
        details={"authorization": "must-not-survive"},
    )
    assert isinstance(error, ProviderError)
    assert error.retryable is False
    assert error.details == {"redacted": True}
    assert "must-not-survive" not in repr(error.to_dict())


@pytest.mark.parametrize("error_type", ERROR_TYPES)
def test_every_provider_error_exposes_the_normalized_contract(error_type) -> None:
    error = error_type(provider_id="provider", message="safe failure")
    assert error.provider_id == "provider"
    assert error.error_code
    assert isinstance(error.retryable, bool)
    assert error.attempt is None
    assert error.provider_request_id is None
    assert error.details == {}
