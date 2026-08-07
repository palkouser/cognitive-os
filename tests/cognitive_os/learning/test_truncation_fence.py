"""W7-F1: every truncating path asks the same question, in the same place.

D4-W0-F1 found that `learned_smoke` truncated nine tables behind a `_test` suffix check and
erased Sprint 21D3's committed campaign. It fenced two paths — the smoke and the PostgreSQL
integration conftest — and wrote "one rule for both truncating paths, deliberately".

There were eleven. On 2026-08-07 a release-matrix run with `.env.s21d4.local` sourced put
`cognitive_os_s21d4_test` in front of five of the other nine, and they truncated 1,076
committed observations, 9 datasets and 18 artifact lineages. Three of the four the run did not
reach are scale baselines, and one of those truncates `events`, `artifacts` and `artifact_blobs`
-- the append-only store itself. That store had a verified backup from three
minutes earlier and D3's did not, which is the only reason this is a finding rather than a
second irrecoverable loss.

So the rule has one implementation now, and this file is what says so. Two of these tests are
about behaviour and the third is about arithmetic: it counts the `TRUNCATE` statements in the
repository and requires each one's module to reach the fence. A rule with eleven copies is a
rule with eleven chances to be the outdated one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cognitive_os.infrastructure.postgres.engine import (
    TRUNCATABLE_DATABASE,
    TruncationNotNominated,
    TruncationRefused,
    require_nominated_for_truncation,
)

REPOSITORY = Path(__file__).resolve().parents[3]

#: Every module that issues a `TRUNCATE` against the `cognitive_os` schema, and therefore has to
#: reach the fence. Listed rather than globbed so that a twelfth one is a diff in this file.
TRUNCATING_MODULES = (
    "src/cognitive_os/learned_smoke.py",
    "tests/integration/postgres/conftest.py",
    "scripts/semantic_scale_baseline.py",
    "scripts/skill_scale_baseline.py",
    "scripts/strategy_scale_baseline.py",
    "tests/cognitive_os/learned_evidence/test_postgres_repository.py",
    "tests/cognitive_os/learned_evidence/test_postgres_health.py",
    "tests/cognitive_os/learned_evidence/test_artifact_lineage.py",
    "tests/cognitive_os/provider_output/test_postgres_repository.py",
    "tests/cognitive_os/provider_output/test_postgres_controlled_function.py",
    "tests/cognitive_os/provider_output/test_postgres_health.py",
)

#: Paths that name `TRUNCATE` without issuing one: the finding record that describes the
#: mechanism, and this file. Everything else that names it, truncates.
NOT_A_TRUNCATING_PATH = re.compile(
    r"scripts/finding_w0_f1_d4\.py|tests/cognitive_os/learning/test_truncation_fence\.py"
)


class TestTheRuleItself:
    def test_an_unnominated_database_is_refused_as_a_skip_rather_than_a_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nobody asked for this, so a whole-repository run must decline rather than break."""
        monkeypatch.delenv(TRUNCATABLE_DATABASE, raising=False)

        with pytest.raises(TruncationNotNominated, match=TRUNCATABLE_DATABASE):
            require_nominated_for_truncation("cognitive_os_s21d4_test")

    def test_nominating_one_database_and_connecting_to_another_is_loud(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(TRUNCATABLE_DATABASE, "cognitive_os_scratch_test")

        with pytest.raises(TruncationRefused, match="refusing to TRUNCATE cognitive_os_s21d4"):
            require_nominated_for_truncation("cognitive_os_s21d4_test")

    def test_the_test_suffix_alone_consents_to_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The whole finding in one assertion: every sprint's evidence store ends in `_test`."""
        monkeypatch.delenv(TRUNCATABLE_DATABASE, raising=False)

        for evidence_store in (
            "cognitive_os_s21c3_test",
            "cognitive_os_s21d1_test",
            "cognitive_os_s21d2_test",
            "cognitive_os_s21d3_test",
            "cognitive_os_s21d4_test",
        ):
            assert evidence_store.endswith("_test")
            with pytest.raises(TruncationNotNominated):
                require_nominated_for_truncation(evidence_store)

    def test_the_nominated_database_is_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(TRUNCATABLE_DATABASE, "cognitive_os_scratch_test")

        require_nominated_for_truncation("cognitive_os_scratch_test")


class TestEveryTruncatingPathReachesIt:
    @pytest.mark.parametrize("module", TRUNCATING_MODULES)
    def test_each_named_module_calls_the_shared_fence(self, module: str) -> None:
        source = (REPOSITORY / module).read_text(encoding="utf-8")

        assert "TRUNCATE" in source, f"{module} no longer truncates; remove it from the list"
        assert "require_nominated_for_truncation" in source, module

    def test_no_module_reimplements_the_rule_beside_its_own_truncate(self) -> None:
        """A local `os.environ.get(COGOS_TRUNCATABLE_DATABASE)` is the twelfth copy returning."""
        for module in TRUNCATING_MODULES:
            source = (REPOSITORY / module).read_text(encoding="utf-8")
            assert f'environ.get("{TRUNCATABLE_DATABASE}")' not in source, module

    def test_the_list_is_complete_against_the_repository(self) -> None:
        """Globbed rather than trusted: a twelfth truncating module must fail this.

        This is the test that found three of the eleven. The first version of this file listed
        eight and excluded two scale baselines as "scratch schema" on an assumption; the scan
        disagreed, and one of the two truncates `events`, `artifacts` and `artifact_blobs`.
        """
        found = set()
        for path in sorted(REPOSITORY.glob("**/*.py")):
            relative = path.relative_to(REPOSITORY).as_posix()
            if relative.startswith(
                (".venv", "build", ".cache", "dist", "node_modules")
            ) or NOT_A_TRUNCATING_PATH.search(relative):
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r'"TRUNCATE |f"TRUNCATE |TRUNCATE cognitive_os\.', source):
                found.add(relative)

        assert found == set(TRUNCATING_MODULES), (
            f"unfenced or unlisted truncating modules: {sorted(found - set(TRUNCATING_MODULES))}; "
            f"listed but no longer truncating: {sorted(set(TRUNCATING_MODULES) - found)}"
        )
