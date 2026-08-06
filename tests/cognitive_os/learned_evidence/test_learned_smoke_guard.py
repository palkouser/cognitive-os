"""The learned smoke must refuse a store it did not create. D4-W0-F1.

The smoke truncates every learned evidence table before it runs. Its original fence was the
database name ending in `_test`, which every sprint's evidence database also does -- so the
fence passed and the truncate erased Sprint 21D3's committed campaign: 280 self-play
observations and both materialised revision-3 datasets, two minutes before the backup meant to
preserve them.

These cases pin the two fences that replaced it: the nomination the integration fixture has
required since W6-F2, and a content check that catches a nomination given by mistake. No
database and no fixtures -- `_require_erasable` takes a connection and asks it three questions,
so a stub that answers them is the whole harness, and a regression shows up as a failing
assertion rather than as a lost campaign.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cognitive_os.infrastructure.learned.reference import AlwaysAbstainingRanker
from cognitive_os.learned_smoke import SmokeRefused, _require_erasable, _require_nomination


def test_nomination_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """No nomination is not consent. This is the state D3 ran in."""
    monkeypatch.delenv("COGOS_TRUNCATABLE_DATABASE", raising=False)
    with pytest.raises(SmokeRefused) as refusal:
        _require_nomination("cognitive_os_s21d3_test")
    assert "COGOS_TRUNCATABLE_DATABASE" in str(refusal.value)


def test_nomination_must_name_the_connected_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nominating one database and connecting to another is the loud case, not the quiet one."""
    monkeypatch.setenv("COGOS_TRUNCATABLE_DATABASE", "cognitive_os_scratch_test")
    with pytest.raises(SmokeRefused) as refusal:
        _require_nomination("cognitive_os_s21d3_test")
    message = str(refusal.value)
    assert "cognitive_os_s21d3_test" in message
    assert "cognitive_os_scratch_test" in message


def test_a_matching_nomination_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGOS_TRUNCATABLE_DATABASE", "cognitive_os_test")
    _require_nomination("cognitive_os_test")


def test_the_smoke_uses_the_same_nomination_variable_as_the_integration_fixture() -> None:
    """One rule for both truncating paths. Two names would teach an operator only one of them."""
    fixture = Path("tests/integration/postgres/conftest.py").read_text(encoding="utf-8")
    assert "COGOS_TRUNCATABLE_DATABASE" in fixture


class _StubConnection:
    """Answers the three counts `_require_erasable` asks for, and records what it was asked."""

    def __init__(self, *, observations: int = 0, datasets: int = 0, foreign_components: int = 0):
        self._answers = {
            "learned_observations": observations,
            "learned_datasets": datasets,
            "learned_components": foreign_components,
        }
        self.asked: list[str] = []
        self.parameters: list[Any] = []

    async def scalar(self, statement: Any, parameters: Any = None) -> int:
        sql = str(statement)
        self.asked.append(sql)
        self.parameters.append(parameters)
        for table, answer in self._answers.items():
            if table in sql:
                return answer
        raise AssertionError(f"unexpected query: {sql}")


@pytest.mark.asyncio
async def test_empty_store_is_erasable() -> None:
    """The ordinary case: a scratch database the smoke may have."""
    await _require_erasable(_StubConnection())


@pytest.mark.asyncio
async def test_store_holding_only_the_reference_component_is_erasable() -> None:
    """Repeated runs stay idempotent -- the smoke's own rows are not somebody else's evidence."""
    await _require_erasable(_StubConnection(foreign_components=0))


@pytest.mark.asyncio
async def test_refuses_a_store_holding_observations() -> None:
    """The Sprint 21D3 case. One observation is enough; it is the record of an executed run."""
    with pytest.raises(SmokeRefused) as refusal:
        await _require_erasable(_StubConnection(observations=280))
    message = str(refusal.value)
    assert "280 row(s) in learned_observations" in message
    assert "did not create" in message


@pytest.mark.asyncio
async def test_refuses_a_store_holding_datasets() -> None:
    with pytest.raises(SmokeRefused) as refusal:
        await _require_erasable(_StubConnection(datasets=2))
    assert "2 row(s) in learned_datasets" in str(refusal.value)


@pytest.mark.asyncio
async def test_refuses_a_store_holding_a_foreign_component() -> None:
    with pytest.raises(SmokeRefused) as refusal:
        await _require_erasable(_StubConnection(foreign_components=1))
    assert "other than the reference one" in str(refusal.value)


@pytest.mark.asyncio
async def test_refusal_names_every_finding_not_just_the_first() -> None:
    """An operator who pointed at the wrong store should see all of what is there."""
    with pytest.raises(SmokeRefused) as refusal:
        await _require_erasable(_StubConnection(observations=280, datasets=2, foreign_components=1))
    message = str(refusal.value)
    assert "learned_observations" in message
    assert "learned_datasets" in message
    assert "other than the reference one" in message


@pytest.mark.asyncio
async def test_the_foreign_component_query_excludes_the_reference_component_by_id() -> None:
    """The exclusion is bound as a parameter from the released descriptor, not spelled inline."""
    connection = _StubConnection()
    await _require_erasable(connection)
    bound = [item for item in connection.parameters if item]
    assert bound == [{"own": AlwaysAbstainingRanker.component_id}]
    assert AlwaysAbstainingRanker.component_id == "reference.ranker.abstaining"


@pytest.mark.asyncio
async def test_the_guard_asks_before_anything_is_truncated() -> None:
    """Every question is a SELECT. A guard that wrote would be a guard that already lost."""
    connection = _StubConnection()
    await _require_erasable(connection)
    assert connection.asked
    assert all(sql.strip().upper().startswith("SELECT") for sql in connection.asked)
