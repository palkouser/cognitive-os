"""Read-only bridge from provider configuration to declared routing evidence."""

from hashlib import sha256

from cognitive_os.domain.routing import (
    CapabilityEvidenceType,
    CapabilitySourceReference,
    CapabilitySupportStatus,
    DeclaredCapability,
    DeclaredCapabilitySet,
    ModelIdentity,
)
from cognitive_os.providers.registry import ProviderRegistry


async def resolve_declared_model(
    registry: ProviderRegistry,
    *,
    provider_id: str,
    model_id: str,
    model_revision: str,
    endpoint_profile: str,
) -> tuple[ModelIdentity, DeclaredCapabilitySet]:
    """Resolve host configuration without reading or copying credential material."""
    provider = registry.require(provider_id)
    capabilities = await provider.get_model_capabilities(model_id)
    identity = ModelIdentity(
        provider_id=provider_id,
        model_id=model_id,
        model_revision=model_revision,
        endpoint_profile=endpoint_profile,
        execution_mode=provider.identity.provider_kind.value,
    )
    source = CapabilitySourceReference(
        evidence_type=CapabilityEvidenceType.OPERATOR_DECLARATION,
        source_id=f"provider-registry:{provider_id}:{model_id}",
        source_revision=provider.identity.adapter_version,
        source_hash=sha256(
            f"{provider_id}:{model_id}:{provider.identity.adapter_version}".encode()
        ).hexdigest(),
        actor_id="provider-registry",
    )
    declarations = DeclaredCapabilitySet(
        capabilities=(
            DeclaredCapability(
                dimension="structured_output",
                support=(
                    CapabilitySupportStatus.SUPPORTED
                    if capabilities.supports_structured_output
                    else CapabilitySupportStatus.UNSUPPORTED
                ),
                value=capabilities.supports_structured_output,
                source=source,
            ),
            DeclaredCapability(
                dimension="tool_calling",
                support=(
                    CapabilitySupportStatus.SUPPORTED
                    if capabilities.supports_tool_calls
                    else CapabilitySupportStatus.UNSUPPORTED
                ),
                value=capabilities.supports_tool_calls,
                source=source,
            ),
            DeclaredCapability(
                dimension="context_limit",
                support=(
                    CapabilitySupportStatus.SUPPORTED
                    if capabilities.maximum_context_tokens
                    else CapabilitySupportStatus.UNKNOWN
                ),
                value=capabilities.maximum_context_tokens,
                source=source,
            ),
        )
    )
    return identity, declarations
