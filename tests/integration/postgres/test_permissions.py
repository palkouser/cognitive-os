import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


@pytest.mark.asyncio
async def test_runtime_role_cannot_mutate_event_history_or_schema(engines) -> None:
    app, _admin = engines
    statements = [
        "UPDATE cognitive_os.events SET source_component = 'forbidden'",
        "DELETE FROM cognitive_os.events",
        "ALTER TABLE cognitive_os.events ADD COLUMN forbidden text",
    ]
    for statement in statements:
        with pytest.raises(DBAPIError):
            async with app.begin() as connection:
                await connection.execute(text(statement))
