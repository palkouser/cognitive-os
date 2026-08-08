"""The PostgreSQL implementation bound to the same contract the in-memory one passes.

Deliberately in this package rather than under `tests/integration/postgres`: the binding
belongs beside the suite it binds, and a shared contract that needs a copied import path
tends to acquire a second, divergent copy. The tests skip when the integration URLs are
absent, so the credential-free lane collects them and runs nothing.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.application.ports.learned_evidence import LearnedEvidenceRepositoryPort
from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.domain.learned_evidence import (
    LearnedRepositoryConflict,
    LearnedRepositoryError,
)
from cognitive_os.infrastructure.learned.postgres.repository import (
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.learned.postgres.tables import LEARNED_EVIDENCE_TABLES
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.truncation import (
    TruncationNotNominated,
    TruncationRefused,
    require_nominated_for_truncation,
)
from cognitive_os.learning.registry import durable_transition_is_legal

from . import fixtures as fx
from .repository_contract import (
    LearnedRepositoryContract,
    attempt_stale_activation,
    drive_to_activated,
    drive_to_verified,
    revision,
)

pytestmark = [pytest.mark.integration, pytest.mark.postgres]

#: Only the learned tables. A learned test that truncated the whole database would make
#: its own isolation depend on nothing else running, which is not isolation.
_TRUNCATE = ", ".join(f"cognitive_os.{table.name}" for table in LEARNED_EVIDENCE_TABLES)


def _urls() -> tuple[str, str]:
    app = os.environ.get("COGOS_DATABASE_URL")
    admin = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not app or not admin:
        pytest.skip("PostgreSQL integration URLs are not configured")
    return app, admin


@pytest_asyncio.fixture
async def engines() -> AsyncIterator[tuple[AsyncEngine, AsyncEngine]]:
    app_url, admin_url = _urls()
    app = create_postgres_engine(app_url, pool_size=4, max_overflow=4)
    admin = create_postgres_engine(admin_url, pool_size=2, max_overflow=2)
    async with admin.connect() as connection:
        name = await connection.scalar(text("SELECT current_database()"))
        if not str(name).endswith("_test"):
            pytest.fail(f"refusing learned integration tests against database: {name}")
        # W7-F1. "Ends with `_test`" is a naming convention, not consent: every sprint's
        # evidence database ends in `_test` too, and on 2026-08-07 a release-matrix run with the
        # D4 environment sourced put one in front of this fixture, which truncated 1,076
        # committed observations. The rule is the one W6-F2 and D4-W0-F1 already established,
        # reached through its single implementation rather than copied beside a sixth TRUNCATE.
        try:
            require_nominated_for_truncation(str(name))
        except TruncationNotNominated as reason:
            pytest.skip(str(reason))
        except TruncationRefused as reason:
            pytest.fail(str(reason))
    async with admin.begin() as connection:
        await connection.execute(text(f"TRUNCATE {_TRUNCATE} RESTART IDENTITY CASCADE"))
    try:
        yield app, admin
    finally:
        await app.dispose()
        await admin.dispose()


class TestPostgresLearnedEvidenceRepository(LearnedRepositoryContract):
    """The whole shared suite, unchanged, against the real database."""

    @pytest.fixture(autouse=True)
    def _bind(self, engines: tuple[AsyncEngine, AsyncEngine]) -> None:
        self._app, self._admin = engines

    async def make_repository(self) -> LearnedEvidenceRepositoryPort:
        return PostgresLearnedEvidenceRepository(self._app)

    async def corrupt_projection(
        self, repository: LearnedEvidenceRepositoryPort, component_id: str
    ) -> None:
        """Only the owner can do this, which is itself part of the guarantee."""
        async with self._admin.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE cognitive_os.learned_components SET current_state = 'shadow' "
                    "WHERE component_id = :component_id AND current_state <> 'shadow'"
                ),
                {"component_id": component_id},
            )


class TestTheApplicationRoleCannotRewriteEvidence:
    @pytest.mark.asyncio
    async def test_the_application_role_cannot_insert_into_a_ledger_directly(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """SELECT and EXECUTE, nothing else. A code bug cannot become a data rewrite."""
        app, _ = engines
        with pytest.raises(Exception, match="permission denied"):
            async with app.begin() as connection:
                await connection.execute(
                    text(
                        "INSERT INTO cognitive_os.learned_accesses "
                        "(access_id, actor, authority, target_type, target_id, purpose, "
                        "decision, payload_json, content_hash) VALUES "
                        "(gen_random_uuid(), 'x', 'x', 'x', 'x', 'x', 'x', '{}'::jsonb, :h)"
                    ),
                    {"h": "a" * 64},
                )

    @pytest.mark.asyncio
    async def test_the_application_role_cannot_update_the_projection(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        app, _ = engines
        repository = PostgresLearnedEvidenceRepository(app)
        await repository.register_component(
            revision=revision(number=1, state_after=LearnedComponentState.REGISTERED),
            descriptor_version=fx.descriptor().version,
        )
        with pytest.raises(Exception, match="permission denied"):
            async with app.begin() as connection:
                await connection.execute(
                    text("UPDATE cognitive_os.learned_components SET current_state = 'active'")
                )

    @pytest.mark.asyncio
    async def test_the_owner_cannot_update_a_ledger_either(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """The append-only trigger holds against the owner, not only the app role."""
        _, admin = engines
        repository = PostgresLearnedEvidenceRepository(admin)
        await repository.register_component(
            revision=revision(number=1, state_after=LearnedComponentState.REGISTERED),
            descriptor_version=fx.descriptor().version,
        )
        for statement in (
            "UPDATE cognitive_os.learned_component_revisions SET reason = 'rewritten'",
            "DELETE FROM cognitive_os.learned_component_revisions",
        ):
            with pytest.raises(Exception, match="append-only"):
                async with admin.begin() as connection:
                    await connection.execute(text(statement))


class TestTheSqlTransitionPolicyMatchesPython:
    @pytest.mark.asyncio
    async def test_every_combination_agrees(self, engines: tuple[AsyncEngine, AsyncEngine]) -> None:
        """Two copies of one policy, held identical by exhaustion rather than by care.

        The table lives in Python so the service can refuse early, and in SQL so a caller
        holding only EXECUTE cannot bypass it. Two copies drift; this is what stops them.
        """
        _, admin = engines
        states = list(LearnedComponentState)
        mismatches: list[str] = []
        async with admin.connect() as connection:
            for before in states:
                for after in states:
                    for target in (None, 1):
                        database = await connection.scalar(
                            text(
                                "SELECT cognitive_os.learned_transition_is_legal("
                                ":before, :after, :target)"
                            ),
                            {"before": before.value, "after": after.value, "target": target},
                        )
                        python = durable_transition_is_legal(
                            before, after, rollback_target_revision=target
                        )
                        if bool(database) != python:
                            mismatches.append(
                                f"{before.value} -> {after.value} (rollback={target}): "
                                f"sql={database}, python={python}"
                            )
        assert mismatches == []

    @pytest.mark.asyncio
    async def test_registration_can_only_start_in_registered(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        _, admin = engines
        async with admin.connect() as connection:
            for state in LearnedComponentState:
                legal = await connection.scalar(
                    text("SELECT cognitive_os.learned_transition_is_legal(NULL, :after, NULL)"),
                    {"after": state.value},
                )
                assert bool(legal) is (state is LearnedComponentState.REGISTERED)


class TestActivationConcurrency:
    @pytest.mark.asyncio
    @pytest.mark.concurrency
    async def test_two_sessions_racing_to_activate_leave_one_winner(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """Two real connections, not two coroutines sharing a lock.

        The in-memory reference proves the rule; only the database can prove the rule
        survives two sessions that never see each other's uncommitted work.
        """
        app, _ = engines
        repository = PostgresLearnedEvidenceRepository(app)
        await drive_to_verified(repository)
        assessment = fx.promotion_assessment()

        async def attempt(index: int) -> object:
            own = PostgresLearnedEvidenceRepository(app)
            try:
                return await own.advance_component(
                    revision=revision(
                        number=4,
                        state_before=LearnedComponentState.VERIFIED,
                        state_after=LearnedComponentState.ACTIVE,
                        key=f"race-activate-{index}",
                        reason=f"racing activation {index}",
                        artifact_lineage_id=fx.lineage().lineage_id,
                        promotion_assessment_hash=assessment.content_hash,
                        activation_approval_hash=fx.ARTIFACT_HASH,
                    ),
                    expected_revision=3,
                )
            except LearnedRepositoryError as error:
                return error

        results = await asyncio.gather(attempt(0), attempt(1))
        failures = [item for item in results if isinstance(item, LearnedRepositoryError)]
        assert len(failures) == 1, "exactly one activation may win"
        assert failures[0].conflict in {
            LearnedRepositoryConflict.STALE_REVISION,
            LearnedRepositoryConflict.SURFACE_ALREADY_ACTIVE,
        }
        history = await repository.component_history(fx.INERT.component_id)
        assert len(history) == 4, "the loser must not have appended a revision"

    @pytest.mark.asyncio
    @pytest.mark.concurrency
    async def test_no_committed_state_holds_two_active_components_for_one_surface(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """The partial unique index, exercised rather than assumed."""
        app, admin = engines
        repository = PostgresLearnedEvidenceRepository(app)
        await drive_to_verified(repository)
        await drive_to_activated(repository)
        other = fx.UNPROMOTABLE.component_id
        await repository.register_component(
            revision=revision(
                number=1,
                state_after=LearnedComponentState.REGISTERED,
                component_id=other,
                key="second-component",
            ),
            descriptor_version="1",
        )
        for number, before, after in (
            (2, LearnedComponentState.REGISTERED, LearnedComponentState.SHADOW),
            (3, LearnedComponentState.SHADOW, LearnedComponentState.VERIFIED),
        ):
            await repository.advance_component(
                revision=revision(
                    number=number,
                    state_before=before,
                    state_after=after,
                    component_id=other,
                    key=f"second-{number}",
                ),
                expected_revision=number - 1,
            )
        with pytest.raises(LearnedRepositoryError) as raised:
            await repository.advance_component(
                revision=revision(
                    number=4,
                    state_before=LearnedComponentState.VERIFIED,
                    state_after=LearnedComponentState.ACTIVE,
                    component_id=other,
                    key="second-activate",
                    promotion_assessment_hash=fx.promotion_assessment().content_hash,
                    activation_approval_hash=fx.ARTIFACT_HASH,
                ),
                expected_revision=3,
            )
        assert raised.value.conflict is LearnedRepositoryConflict.SURFACE_ALREADY_ACTIVE
        async with admin.connect() as connection:
            count = await connection.scalar(
                text(
                    "SELECT count(*) FROM cognitive_os.learned_components "
                    "WHERE surface = :surface AND current_state = 'active'"
                ),
                {"surface": fx.surface()},
            )
        assert count == 1
        assert app is not None

    @pytest.mark.asyncio
    async def test_a_refused_activation_step_rolls_back_both_writes(
        self, engines: tuple[AsyncEngine, AsyncEngine]
    ) -> None:
        """Neither partial history nor an orphan receipt survives a refusal."""
        app, admin = engines
        repository = PostgresLearnedEvidenceRepository(app)
        await drive_to_verified(repository)
        with pytest.raises(LearnedRepositoryError):
            await attempt_stale_activation(repository)
        async with admin.connect() as connection:
            receipts = await connection.scalar(
                text("SELECT count(*) FROM cognitive_os.learned_activation_history")
            )
            revisions = await connection.scalar(
                text("SELECT count(*) FROM cognitive_os.learned_component_revisions")
            )
        assert receipts == 0
        assert revisions == 3
