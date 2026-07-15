"""Create the append-only event and artifact store.

Revision ID: 0001
Revises: None
"""

from __future__ import annotations

from alembic import op

from cognitive_os.infrastructure.postgres.tables import (
    artifact_blobs,
    artifacts,
    event_streams,
    events,
)

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CORE_TABLES = (event_streams, events, artifact_blobs, artifacts)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS cognitive_os")
    connection = op.get_bind()
    for table in CORE_TABLES:
        table.create(connection)
    op.execute("REVOKE ALL ON SCHEMA cognitive_os FROM PUBLIC")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA cognitive_os FROM PUBLIC")
    op.execute("GRANT ALL PRIVILEGES ON SCHEMA cognitive_os TO cogos_owner")
    op.execute("GRANT SELECT ON public.alembic_version TO cogos_owner")
    op.execute(
        "GRANT ALL PRIVILEGES ON cognitive_os.events, cognitive_os.event_streams, "
        "cognitive_os.artifact_blobs, cognitive_os.artifacts TO cogos_owner"
    )
    op.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA cognitive_os TO cogos_owner")
    op.execute("GRANT USAGE ON SCHEMA cognitive_os TO cogos_app")
    op.execute("GRANT SELECT ON public.alembic_version TO cogos_app")
    op.execute("GRANT SELECT, INSERT ON cognitive_os.events TO cogos_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON cognitive_os.event_streams TO cogos_app")
    op.execute("GRANT SELECT, INSERT ON cognitive_os.artifact_blobs TO cogos_app")
    op.execute("GRANT SELECT, INSERT ON cognitive_os.artifacts TO cogos_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA cognitive_os TO cogos_app")


def downgrade() -> None:
    connection = op.get_bind()
    for table in reversed(CORE_TABLES):
        table.drop(connection)
    op.execute("DROP SCHEMA IF EXISTS cognitive_os")
