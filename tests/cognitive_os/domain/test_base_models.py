from __future__ import annotations

import pytest
from pydantic import Field, ValidationError

from cognitive_os.domain.base import ContractModel, ImmutableContractModel


class MutableExample(ContractModel):
    name: str = " valid "
    values: list[int] = Field(default_factory=list)


class FrozenExample(ImmutableContractModel):
    child: MutableExample


def test_base_policy_rejects_unknown_fields_and_validates_defaults() -> None:
    assert MutableExample().name == "valid"
    with pytest.raises(ValidationError):
        MutableExample(extra_field=True)


def test_mutable_defaults_are_not_shared() -> None:
    first = MutableExample()
    second = MutableExample()
    first.values.append(1)
    assert second.values == []


def test_frozen_model_rejects_assignment_and_revalidates_nested_input() -> None:
    model = FrozenExample(child={"name": " nested "})
    assert model.child.name == "nested"
    with pytest.raises(ValidationError):
        model.child = MutableExample(name="changed")
