import inspect

from cognitive_os.application.ports import ArtifactStorePort, EventStorePort


def test_ports_are_protocols_without_sqlalchemy_types() -> None:
    source = inspect.getsource(EventStorePort) + inspect.getsource(ArtifactStorePort)
    assert "sqlalchemy" not in source.lower()
    assert "expected_version" in source
    assert "put_bytes" in source
