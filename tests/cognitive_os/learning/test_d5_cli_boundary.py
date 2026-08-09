"""S21D5-080: the D5 command refuses a wrong environment before it opens anything.

The failure this exists to prevent is not a typo in a flag. It is an operator who sourced the D4
environment out of habit: every variable is set, every value is valid, and every later check
passes while reading the store this sprint is forbidden to touch. So the refusal is on the
*values*, and it happens before a connection, a directory listing or a file read.

D5 inherits six predecessor roots rather than five, and the sixth is `artifacts-s21d4` — the
store the previous sprint wrote, and therefore the one an operator is most likely to still have
exported. That root gets a test of its own for the same reason `artifacts-s21d3` got one in D4.

The output contract is checked here too, because the evidence index quotes this command: one
line of sorted JSON, canonical enough to hash and diff between runs, with no credential in it.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"

#: Values that must never be accepted. `artifacts` and `artifacts-s21d5` differ by a suffix, and
#: the first is the development store.
FORBIDDEN_ROOTS = (
    "/home/palkouser/projekt/cognitive-os-data/artifacts",
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21c3",
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d1",
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d2",
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d3",
    "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d4",
)


def _arguments(evidence: Path | str, **overrides: Any) -> Any:
    fields = {"evidence": str(evidence), "rehash_blobs": False, "data_root": None, **overrides}
    return type("Args", (), fields)()


@pytest.fixture(scope="module")
def cli() -> Any:
    """The released script, imported by path: `scripts/` is not an importable package."""
    spec = importlib.util.spec_from_file_location("learned_cli", REPOSITORY / "scripts/learned.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    for name in ("COGOS_POSTGRES_DATABASE", "COGOS_DATABASE_URL", "COGOS_ARTIFACT_ROOT"):
        monkeypatch.delenv(name, raising=False)
    yield monkeypatch


class TestTheEnvironmentBoundary:
    @pytest.mark.parametrize(
        "database",
        ["cognitive_os_s21d4_test", "cognitive_os_s21d3_test", "cognitive_os_dev"],
    )
    def test_a_predecessor_database_is_refused_by_name(
        self, cli: Any, clean_environment: pytest.MonkeyPatch, database: str
    ) -> None:
        clean_environment.setenv("COGOS_POSTGRES_DATABASE", database)

        with pytest.raises(SystemExit, match="require an s21d5 database"):
            cli._require_d5_environment(needs_store=False)

    def test_a_predecessor_database_inside_a_url_is_refused_too(
        self, cli: Any, clean_environment: pytest.MonkeyPatch
    ) -> None:
        clean_environment.setenv(
            "COGOS_DATABASE_URL", "postgresql+asyncpg://x@h/cognitive_os_s21d4_test"
        )

        with pytest.raises(SystemExit, match="require an s21d5 database"):
            cli._require_d5_environment(needs_store=False)

    @pytest.mark.parametrize("root", FORBIDDEN_ROOTS)
    def test_every_predecessor_store_is_refused_by_path(
        self, cli: Any, clean_environment: pytest.MonkeyPatch, root: str
    ) -> None:
        clean_environment.setenv("COGOS_POSTGRES_DATABASE", "cognitive_os_s21d5_test")
        clean_environment.setenv("COGOS_ARTIFACT_ROOT", root)

        with pytest.raises(SystemExit, match="refusing to open"):
            cli._require_d5_environment(needs_store=False)

    def test_the_d4_store_is_on_the_list_d4_itself_could_not_have_had(self, cli: Any) -> None:
        """The one root that separates the two boundaries, asserted rather than assumed."""
        assert "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d4" in (
            cli._FORBIDDEN_ROOTS_D5
        )
        assert "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d4" not in (
            cli._FORBIDDEN_ROOTS_D4
        )
        assert len(cli._FORBIDDEN_ROOTS_D5) == len(cli._FORBIDDEN_ROOTS_D4) + 1

    def test_the_refused_roots_are_the_pairs_the_isolation_class_re_fingerprints(
        self, cli: Any
    ) -> None:
        """One list, two uses: a store D5 must not open is a store D5 must find unchanged."""
        declared = {directory for _, directory in cli._D5_PREDECESSORS}

        assert {Path(root).name for root in cli._FORBIDDEN_ROOTS_D5} == declared

    def test_a_missing_store_is_refused_only_when_the_command_needs_one(
        self, cli: Any, clean_environment: pytest.MonkeyPatch
    ) -> None:
        clean_environment.setenv("COGOS_POSTGRES_DATABASE", "cognitive_os_s21d5_test")

        assert cli._require_d5_environment(needs_store=False) is None
        with pytest.raises(SystemExit, match="COGOS_ARTIFACT_ROOT is required"):
            cli._require_d5_environment(needs_store=True)

    def test_the_d5_environment_is_accepted(
        self, cli: Any, clean_environment: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        root = tmp_path / "artifacts-s21d5"
        root.mkdir()
        clean_environment.setenv("COGOS_POSTGRES_DATABASE", "cognitive_os_s21d5_test")
        clean_environment.setenv("COGOS_ARTIFACT_ROOT", str(root))

        assert cli._require_d5_environment(needs_store=True) == root

    def test_the_refusal_happens_before_the_evidence_directory_is_read(
        self, cli: Any, clean_environment: pytest.MonkeyPatch
    ) -> None:
        """A nonexistent evidence directory would raise its own error if it were reached."""
        clean_environment.setenv("COGOS_POSTGRES_DATABASE", "cognitive_os_s21d4_test")

        with pytest.raises(SystemExit, match="require an s21d5 database"):
            asyncio.run(cli._d5_integrity(_arguments("/nonexistent")))


class TestTheOutputContract:
    def test_the_report_is_one_line_of_canonical_sorted_json(
        self, cli: Any, clean_environment: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        clean_environment.setenv("COGOS_POSTGRES_DATABASE", "cognitive_os_s21d5_test")

        status = asyncio.run(cli._d5_integrity(_arguments(EVIDENCE)))
        printed = capsys.readouterr().out

        assert status == 0
        assert printed.count("\n") == 1
        document = json.loads(printed)
        assert json.dumps(document, sort_keys=True, separators=(",", ":")) == printed.strip()
        assert len(document["covered"]) == 12

    def test_no_credential_or_connection_string_is_rendered(
        self, cli: Any, clean_environment: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        clean_environment.setenv("COGOS_POSTGRES_DATABASE", "cognitive_os_s21d5_test")
        clean_environment.setenv(
            "COGOS_DATABASE_URL",
            # pragma: allowlist secret - a fabricated URL whose whole purpose is to be a
            # credential the report must not render. A password-free URL would test nothing.
            "postgresql+asyncpg://user:hunter2@host/cognitive_os_s21d5_test",
        )

        asyncio.run(cli._d5_integrity(_arguments(EVIDENCE)))
        printed = capsys.readouterr().out

        assert "hunter2" not in printed
        assert "postgresql" not in printed
        assert "@host" not in printed

    def test_an_unhealthy_report_exits_non_zero(
        self, cli: Any, clean_environment: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        clean_environment.setenv("COGOS_POSTGRES_DATABASE", "cognitive_os_s21d5_test")
        empty = tmp_path / "evidence"
        empty.mkdir()

        assert asyncio.run(cli._d5_integrity(_arguments(empty))) == 1

    def test_the_command_is_registered_and_the_released_ones_are_not_replaced(
        self, cli: Any
    ) -> None:
        assert "d5-integrity" in cli._ACTIONS
        assert "d5-integrity" not in cli._NEEDS_COMPONENT
        assert {"d3-integrity", "d4-integrity"} <= set(cli._ACTIONS)
