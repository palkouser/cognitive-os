from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.config.memory_config import MemoryConfiguration, load_memory_configuration


def test_example_configuration_loads_with_sealed_defaults() -> None:
    configuration = load_memory_configuration(Path("config/memory.example.yaml"))
    assert configuration.default_query_limit == 20
    assert not configuration.allow_provider_direct_write
    assert not configuration.allow_network_model_download
    assert not configuration.allow_approximate_vector_indexes


@pytest.mark.parametrize(
    "field",
    [
        "allow_provider_direct_write",
        "allow_automatic_promotion",
        "allow_network_model_download",
        "allow_approximate_vector_indexes",
    ],
)
def test_forbidden_sprint_nine_switches_cannot_be_enabled(field: str) -> None:
    baseline = load_memory_configuration(Path("config/memory.example.yaml"))
    with pytest.raises(ValidationError, match="forbidden"):
        MemoryConfiguration.model_validate({**baseline.model_dump(mode="python"), field: True})


def test_unknown_configuration_field_fails_closed() -> None:
    baseline = load_memory_configuration(Path("config/memory.example.yaml"))
    with pytest.raises(ValidationError, match="Extra inputs"):
        MemoryConfiguration.model_validate(
            {**baseline.model_dump(mode="python"), "provider_override": True}
        )
