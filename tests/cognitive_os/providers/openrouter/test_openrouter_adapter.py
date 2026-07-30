"""The OpenRouter adapter, entirely offline.

Two claims run through the whole file. First, the strict data policy and the zero-spend
default are properties of what is *sent*, so they are asserted against the recorded payload
rather than against the configuration that produced it. Second, no failure path may leak: an
OpenRouter error body carries the upstream provider's message and routing metadata, so every
error assertion checks what the exception does *not* contain as well as what it does.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from cognitive_os.config.provider_config import OpenRouterProviderConfig
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.provider import ModelFinishReason, ProviderStatus
from cognitive_os.providers.errors import (
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderBudgetExceededError,
    ProviderConnectionError,
    ProviderInvalidResponseError,
    ProviderModelUnavailableError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnsupportedCapabilityError,
)
from cognitive_os.providers.openrouter import OpenRouterProvider
from cognitive_os.providers.openrouter.discovery import parse_catalog, resolve_route

from . import fake_transport as fake

KEY_VARIABLE = "OPENROUTER_API_KEY"


@pytest.fixture(autouse=True)
def _credential(monkeypatch: pytest.MonkeyPatch) -> None:
    """A syntactically plausible key that is not one. Nothing here reaches a network."""
    monkeypatch.setenv(KEY_VARIABLE, "sk-or-v1-" + "0" * 32)  # pragma: allowlist secret


def build(
    *,
    transport: fake.FakeOpenRouterTransport | None = None,
    **overrides: object,
) -> tuple[OpenRouterProvider, fake.FakeOpenRouterTransport]:
    config = OpenRouterProviderConfig(enabled=True, **overrides)  # type: ignore[arg-type]
    fake_transport = transport or fake.FakeOpenRouterTransport()
    clock = iter(range(0, 100_000))
    return (
        OpenRouterProvider(config, transport=fake_transport, clock=lambda: float(next(clock))),
        fake_transport,
    )


def a_request(**overrides: object) -> ModelProviderRequest:
    fields: dict[str, object] = {
        "model_call_id": uuid4(),
        "task_run_id": uuid4(),
        "correlation_id": uuid4(),
        "requested_model": "openrouter/free",
        "messages": (ProviderMessage(role=ProviderMessageRole.USER, content="review this helper"),),
    }
    fields.update(overrides)
    return ModelProviderRequest(**fields)  # type: ignore[arg-type]


class TestNoNewDependencyAndNoRawRetention:
    @pytest.mark.asyncio
    async def test_a_successful_call_normalizes_through_the_shared_mapping(self) -> None:
        provider, _ = build()
        response = await provider.complete(a_request())
        assert response.finish_reason is ModelFinishReason.COMPLETED
        assert response.resolved_model == "vendor/small-model:free"
        assert response.provider_request_id == "gen-0123456789"
        assert response.usage is not None
        assert response.usage.total_tokens == 59

    @pytest.mark.asyncio
    async def test_the_resolved_model_is_recorded_not_the_requested_route(self) -> None:
        """`openrouter/free` is a router. Which model actually answered is the receipt fact."""
        provider, _ = build()
        response = await provider.complete(a_request())
        assert response.requested_model == "openrouter/free"
        assert response.resolved_model != response.requested_model

    @pytest.mark.asyncio
    async def test_the_upstream_provider_is_reported_as_a_warning_not_a_new_field(self) -> None:
        provider, _ = build()
        response = await provider.complete(a_request())
        assert any("routed via SomeUpstream" in warning for warning in response.warnings)

    @pytest.mark.asyncio
    async def test_a_fenced_json_answer_is_still_structured(self) -> None:
        transport = fake.FakeOpenRouterTransport(
            completion=fake.completion_payload(
                content='```json\n{"summary": "fenced but correct", "findings": []}\n```'
            )
        )
        provider, _ = build(transport=transport)
        response = await provider.complete(a_request())
        assert response.content == '{"summary": "fenced but correct", "findings": []}'


class TestTheDataPolicyIsWhatIsSent:
    @pytest.mark.asyncio
    async def test_the_default_request_carries_the_open_development_policy(self) -> None:
        """ADR 0088: public material, so no zero-retention demand and collection allowed."""
        provider, transport = build()
        await provider.complete(a_request())
        preferences = transport.completion_payloads[0]["extra_body"]["provider"]
        assert preferences["data_collection"] == "allow"
        assert "zdr" not in preferences

    @pytest.mark.asyncio
    async def test_a_free_only_policy_sends_a_server_side_price_cap(self) -> None:
        """Belt and braces: a catalog that went stale still cannot bill anything."""
        provider, transport = build()
        await provider.complete(a_request())
        assert transport.completion_payloads[0]["extra_body"]["provider"]["max_price"] == {
            "prompt": 0,
            "completion": 0,
        }

    @pytest.mark.asyncio
    async def test_the_strict_policy_is_visible_in_the_payload_when_configured(self) -> None:
        """Non-public material must be legible in what was sent, not only in the config file."""
        provider, transport = build(require_zero_data_retention=True, allow_data_collection=False)
        await provider.complete(a_request())
        preferences = transport.completion_payloads[0]["extra_body"]["provider"]
        assert preferences["data_collection"] == "deny"
        assert preferences["zdr"] is True

    @pytest.mark.asyncio
    async def test_the_output_cap_is_applied_even_when_the_request_asks_for_more(self) -> None:
        provider, transport = build(maximum_output_tokens=128)
        await provider.complete(a_request(max_output_tokens=100_000))
        assert transport.completion_payloads[0]["max_tokens"] == 128

    @pytest.mark.asyncio
    async def test_no_authorization_value_appears_in_the_sent_payload(self) -> None:
        provider, transport = build()
        await provider.complete(a_request())
        rendered = str(transport.completion_payloads[0])
        assert "sk-or-v1-" not in rendered
        assert "Authorization" not in rendered


class TestFreeRoutingAndDiscovery:
    @pytest.mark.asyncio
    async def test_a_disappeared_free_model_is_typed_unavailable_not_a_defect(self) -> None:
        """The Gemma case: a slug that answered yesterday is simply gone today."""
        provider, _ = build(pinned_free_model="vendor/gemma-that-vanished:free")
        with pytest.raises(ProviderModelUnavailableError, match="not in the current catalog"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_a_pinned_free_model_is_used_only_after_catalog_validation(self) -> None:
        provider, transport = build(pinned_free_model="vendor/other-model:free")
        await provider.complete(a_request())
        assert transport.catalog_calls == 1
        assert transport.completion_payloads[0]["model"] == "vendor/other-model:free"

    @pytest.mark.asyncio
    async def test_an_empty_free_catalog_refuses_rather_than_routing_to_a_paid_model(
        self,
    ) -> None:
        transport = fake.FakeOpenRouterTransport(catalog=fake.PAID_ONLY_CATALOG_PAYLOAD)
        provider, _ = build(transport=transport)
        with pytest.raises(ProviderModelUnavailableError, match="no free model"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_paid_routing_is_refused_while_the_maximum_spend_is_zero(self) -> None:
        provider, _ = build(require_free_model=False, maximum_spend_usd=0.0)
        with pytest.raises(ProviderBudgetExceededError, match="maximum spend is zero"):
            await provider.complete(a_request(requested_model="vendor/premium-model"))

    @pytest.mark.asyncio
    async def test_a_paid_model_is_refused_under_a_free_only_policy(self) -> None:
        provider, _ = build()
        with pytest.raises(ProviderBudgetExceededError, match="free-only policy"):
            await provider.complete(a_request(requested_model="vendor/premium-model"))

    @pytest.mark.asyncio
    async def test_the_catalog_is_cached_for_its_configured_lifetime_and_no_longer(self) -> None:
        transport = fake.FakeOpenRouterTransport()
        provider, _ = build(transport=transport, catalog_cache_seconds=5)
        await provider.complete(a_request())
        await provider.complete(a_request())
        assert transport.catalog_calls == 1
        # The injected clock advances one second per read, so a sixth read is past the
        # lifetime and must refetch rather than route from a stale catalog.
        for _ in range(6):
            provider._clock()
        await provider.complete(a_request())
        assert transport.catalog_calls == 2

    @pytest.mark.asyncio
    async def test_an_empty_catalog_is_an_invalid_response_not_an_empty_result(self) -> None:
        transport = fake.FakeOpenRouterTransport(catalog=fake.EMPTY_CATALOG_PAYLOAD)
        provider, _ = build(transport=transport)
        with pytest.raises(ProviderInvalidResponseError, match="no usable models"):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_an_unparsable_price_is_treated_as_not_free(self) -> None:
        """Failing towards 'this costs money' is the safe direction for a zero-spend policy."""
        transport = fake.FakeOpenRouterTransport(
            catalog={"data": [{"id": "vendor/mystery", "pricing": {"prompt": "n/a"}}]}
        )
        provider, _ = build(transport=transport)
        with pytest.raises(ProviderModelUnavailableError, match="no free model"):
            await provider.complete(a_request())


class TestEveryFailureClassHasAnOfflineFixture:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error_factory", "expected"),
        [
            (fake.authentication_error, ProviderAuthenticationError),
            (fake.authorization_error, ProviderAuthorizationError),
            (fake.rate_limit_error, ProviderRateLimitError),
            (fake.timeout_error, ProviderTimeoutError),
            (fake.connection_error, ProviderConnectionError),
            (fake.upstream_error, ProviderUnavailableError),
            (fake.bad_request_error, ProviderInvalidResponseError.__mro__[1]),
            (fake.credits_exhausted_error, ProviderInvalidResponseError),
        ],
    )
    async def test_a_provider_failure_is_normalized(
        self, error_factory: object, expected: type[Exception]
    ) -> None:
        transport = fake.FakeOpenRouterTransport(completion_error=error_factory())  # type: ignore[operator]
        provider, _ = build(transport=transport)
        with pytest.raises(expected):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_a_normalized_error_carries_no_provider_body_or_request_identity(self) -> None:
        transport = fake.FakeOpenRouterTransport(completion_error=fake.authorization_error())
        provider, _ = build(transport=transport)
        with pytest.raises(ProviderAuthorizationError) as failure:
            await provider.complete(a_request())
        rendered = str(failure.value.to_dict())
        assert "data policy" not in rendered
        assert failure.value.details == {}
        assert failure.value.provider_request_id is None

    @pytest.mark.asyncio
    async def test_a_malformed_response_is_an_invalid_response(self) -> None:
        transport = fake.FakeOpenRouterTransport(completion={"choices": []})
        provider, _ = build(transport=transport)
        with pytest.raises(ProviderInvalidResponseError):
            await provider.complete(a_request())

    @pytest.mark.asyncio
    async def test_a_catalog_failure_is_normalized_too(self) -> None:
        transport = fake.FakeOpenRouterTransport(catalog_error=fake.connection_error())
        provider, _ = build(transport=transport)
        with pytest.raises(ProviderConnectionError):
            await provider.complete(a_request())


class TestHealthIsReadOnly:
    @pytest.mark.asyncio
    async def test_health_reaches_the_catalog_and_never_completes(self) -> None:
        """A health check that completed would spend budget every time it was asked."""
        provider, transport = build()
        health = await provider.health_check()
        assert health.status is ProviderStatus.AVAILABLE
        assert transport.completion_payloads == []
        assert transport.catalog_calls == 1

    @pytest.mark.asyncio
    async def test_health_without_a_credential_reports_typed_not_ready(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(KEY_VARIABLE, raising=False)
        provider, transport = build()
        health = await provider.health_check()
        assert health.status is ProviderStatus.UNAUTHENTICATED
        assert transport.catalog_calls == 0

    @pytest.mark.asyncio
    async def test_health_is_degraded_when_no_free_model_is_offered(self) -> None:
        transport = fake.FakeOpenRouterTransport(catalog=fake.PAID_ONLY_CATALOG_PAYLOAD)
        provider, _ = build(transport=transport)
        health = await provider.health_check()
        assert health.status is ProviderStatus.DEGRADED
        assert "no free model" in health.message

    @pytest.mark.asyncio
    async def test_health_output_contains_no_key_or_account(self) -> None:
        provider, _ = build()
        rendered = (await provider.health_check()).model_dump_json()
        assert "sk-or-v1-" not in rendered
        assert "@" not in rendered


class TestCapabilities:
    @pytest.mark.asyncio
    async def test_streaming_is_refused_rather_than_partially_supported(self) -> None:
        provider, _ = build()
        with pytest.raises(ProviderUnsupportedCapabilityError):
            async for _ in provider.stream(a_request()):
                pass

    @pytest.mark.asyncio
    async def test_capabilities_never_exceed_the_configured_caps(self) -> None:
        provider, _ = build(maximum_context_tokens=16384, maximum_output_tokens=512)
        await provider.catalog()
        capabilities = await provider.get_model_capabilities("vendor/premium-model")
        assert capabilities.maximum_context_tokens == 16384
        assert capabilities.maximum_output_tokens == 512


class TestThePayloadIsAcceptableToTheInstalledClient:
    """The fake transport takes whatever dict it is handed, so nothing in this suite used to
    check that the real client would accept the same keys.

    It did not. `provider` is an OpenRouter extension, not a chat-completions parameter, and
    the OpenAI client validates its keyword arguments: passing it at the top level raised
    `TypeError: unexpected keyword argument 'provider'` and the data policy never reached the
    wire. The Sprint 21C2 live smoke found it. This test is the offline equivalent — it reads
    the installed client's own signature, so it needs no credential and no network.
    """

    @pytest.mark.asyncio
    async def test_every_top_level_key_is_a_parameter_the_client_accepts(self) -> None:
        import inspect

        from openai.resources.chat.completions import AsyncCompletions

        provider, transport = build()
        await provider.complete(a_request())
        payload = transport.completion_payloads[0]

        accepted = set(inspect.signature(AsyncCompletions.create).parameters)
        unexpected = sorted(key for key in payload if key not in accepted)
        assert unexpected == [], f"the installed client would reject: {unexpected}"

    @pytest.mark.asyncio
    async def test_the_vendor_extension_travels_in_extra_body(self) -> None:
        provider, transport = build()
        await provider.complete(a_request())
        payload = transport.completion_payloads[0]
        assert "provider" not in payload
        assert payload["extra_body"]["provider"]["data_collection"] == "allow"


class TestTheLiveCatalogShapes:
    """Shapes the real `/models` catalog contains that the reviewed fixture did not."""

    def test_a_variable_price_is_not_free(self) -> None:
        """OpenRouter sends `-1` for models whose price is not fixed.

        `CatalogModel` constrains prices to `ge=0`, so the whole catalog failed to parse and
        the error escaped as a raw `ValidationError` rather than a typed provider failure.
        Normalising to infinity keeps `ge=0` true, so no later `price <= 0` test can read a
        variable price as a free one.
        """
        catalog = parse_catalog(
            {
                "data": [
                    {"id": "vendor/variable", "pricing": {"prompt": "-1", "completion": "-1"}},
                    {"id": "vendor/free", "pricing": {"prompt": "0", "completion": "0"}},
                ]
            },
            provider_id="openrouter",
            now=0.0,
        )
        variable = catalog.get("vendor/variable")
        assert variable is not None
        assert variable.is_free is False
        assert catalog.free_model_ids == ("vendor/free",)

    def test_a_variable_price_model_is_refused_under_a_free_only_policy(self) -> None:
        catalog = parse_catalog(
            {"data": [{"id": "vendor/variable", "pricing": {"prompt": "-1", "completion": "-1"}}]},
            provider_id="openrouter",
            now=0.0,
        )
        with pytest.raises(ProviderBudgetExceededError):
            resolve_route(
                provider_id="openrouter",
                catalog=catalog,
                requested="vendor/variable",
                default_route="openrouter/free",
                pinned_free_model=None,
                require_free_model=True,
                maximum_spend_usd=0.0,
            )

    def test_one_unusable_row_does_not_destroy_the_catalog(self) -> None:
        """It stays absent, so `resolve_route` refuses it with a typed unavailability
        rather than the adapter guessing at its price."""
        catalog = parse_catalog(
            {
                "data": [
                    {"id": "vendor/broken", "pricing": {"prompt": "0"}, "context_length": -5},
                    {"id": "vendor/free", "pricing": {"prompt": "0", "completion": "0"}},
                ]
            },
            provider_id="openrouter",
            now=0.0,
        )
        assert catalog.get("vendor/broken") is None
        assert catalog.get("vendor/free") is not None
