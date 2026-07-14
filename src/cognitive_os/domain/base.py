"""Shared validation policies for Cognitive OS contracts."""

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Base for validated application records."""

    model_config = ConfigDict(
        extra="forbid",
        validate_default=True,
        str_strip_whitespace=True,
        revalidate_instances="always",
    )


class ImmutableContractModel(ContractModel):
    """Base for immutable persisted records and event payloads."""

    model_config = ConfigDict(
        extra="forbid",
        validate_default=True,
        str_strip_whitespace=True,
        revalidate_instances="always",
        frozen=True,
    )
