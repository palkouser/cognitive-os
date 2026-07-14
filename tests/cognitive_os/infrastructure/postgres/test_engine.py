import pytest

pytest.importorskip("sqlalchemy")

from cognitive_os.infrastructure.postgres.engine import create_postgres_engine


def test_engine_creation_is_lazy_and_requires_asyncpg() -> None:
    engine = create_postgres_engine("postgresql+asyncpg://user:password@localhost/database")
    assert engine.url.render_as_string(hide_password=True).endswith("@localhost/database")


@pytest.mark.parametrize(
    "url", ["postgresql://user:password@localhost/database", "sqlite+aiosqlite:///test.db"]
)
def test_engine_rejects_unsupported_urls(url: str) -> None:
    with pytest.raises(ValueError, match="asyncpg"):
        create_postgres_engine(url)
