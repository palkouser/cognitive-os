import pytest

from cognitive_os.tools.errors import ToolRegistrationError
from cognitive_os.tools.registry import ToolRegistry


class FakeTool:
    def __init__(self, descriptor):
        self.descriptor = descriptor


def test_registry_is_deterministic_and_freezes(descriptor) -> None:
    registry = ToolRegistry()
    registry.register(FakeTool(descriptor))
    assert registry.list_provider_visible() == (descriptor,)
    assert registry.snapshot() == registry.snapshot()
    with pytest.raises(ToolRegistrationError):
        registry.register(FakeTool(descriptor))
    registry.freeze()
    with pytest.raises(ToolRegistrationError):
        registry.register(FakeTool(descriptor))
