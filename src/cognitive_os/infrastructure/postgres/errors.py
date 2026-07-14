"""PostgreSQL error classification without credential disclosure."""

from sqlalchemy.exc import DBAPIError

from cognitive_os.infrastructure.errors import EventStoreUnavailableError


def normalize_postgres_error(error: BaseException) -> EventStoreUnavailableError:
    if isinstance(error, DBAPIError) and error.connection_invalidated:
        return EventStoreUnavailableError("PostgreSQL connection became unavailable")
    return EventStoreUnavailableError("PostgreSQL operation failed")
