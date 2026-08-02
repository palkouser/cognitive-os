"""S21D2-024: the presealed calibration perturbations, resolved into inputs that still run.

Two properties carry the whole set. Every perturbation is deterministic, so the probe set can
be regenerated and therefore checked; and every one of them preserves behaviour, so a probe
still executes. A perturbed package that no longer runs would measure whether the ranker
notices broken Python, which is not the question the OOD precheck asks.

The third property is honesty about absence: a task with no independent statement pair records
that it has none. A perturbation reported as applied when it was not is worse than a missing
one, because only the first kind is invisible.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from cognitive_os.coding.reality_tasks import d2_templates, template
from cognitive_os.learning import calibration_ood
from cognitive_os.learning.calibration_ood import (
    REORDER,
    PerturbationError,
    PerturbedTask,
    ResolvedOodSet,
    perturb,
    rename_identifiers,
    rename_map,
    reorder_independent_statements,
    rewrite_issue_text,
    substitute_literals,
)

MODULE = '''"""A module."""


def rotate(values, offset):
    length = len(values)
    total = 3
    return values[offset % length :] + values[: offset % length]
'''

SUITE = '''"""Published contract."""

from m import rotate


def test_rotate() -> None:
    assert rotate([1, 2, 3], 1) == [2, 3, 1]
'''


class TestTheRenameIsAGenuineRename:
    def test_it_renames_what_the_module_defines(self) -> None:
        mapping = rename_map(MODULE)

        assert set(mapping) == {"rotate", "values", "offset", "length", "total"}

    def test_a_pseudonym_carries_no_trace_of_the_original(self) -> None:
        for original, pseudonym in rename_map(MODULE).items():
            assert original not in pseudonym

    def test_it_leaves_imported_names_alone(self) -> None:
        """Renaming an import produces a module that does not run, not a shifted one."""
        source = '"""D."""\n\nimport re\n\n\ndef f(text):\n    return re.match("a", text)\n'

        assert "re" not in rename_map(source)

    def test_the_suites_are_renamed_with_the_module_they_import(self) -> None:
        module, suite = rename_identifiers(MODULE, SUITE)

        renamed = rename_map(MODULE)["rotate"]

        assert "rotate" not in module
        assert f"from m import {renamed}" in suite
        assert f"{renamed}([1, 2, 3], 1)" in suite

    def test_a_module_defining_nothing_is_refused_rather_than_passed_through(self) -> None:
        with pytest.raises(PerturbationError):
            rename_identifiers('"""D."""\n\nimport re\n')

    def test_it_is_deterministic(self) -> None:
        assert rename_identifiers(MODULE, SUITE) == rename_identifiers(MODULE, SUITE)


class TestTheReorderSaysWhenItHasNothingToSwap:
    def test_it_swaps_an_independent_adjacent_pair(self) -> None:
        rewritten, applied = reorder_independent_statements(MODULE)

        assert applied.applied is True
        assert rewritten != MODULE
        assert rewritten.index("total = 3") < rewritten.index("length = len(values)")

    def test_it_refuses_to_swap_a_dependent_pair(self) -> None:
        source = "def f():\n    a = 1\n    b = a + 1\n    return b\n"

        rewritten, applied = reorder_independent_statements(source)

        assert applied.applied is False
        assert rewritten == source

    def test_an_absent_pair_is_reported_rather_than_invented(self) -> None:
        source = "def f(values):\n    return values[0]\n"

        rewritten, applied = reorder_independent_statements(source)

        assert (applied.name, applied.applied) == (REORDER, False)
        assert rewritten == source


class TestTheIssueRewriteKeepsTheContract:
    def test_it_restates_rather_than_repeats(self) -> None:
        rewritten, applied = rewrite_issue_text("The helper returns the wrong value when empty.")

        assert applied.applied is True
        assert rewritten != "The helper returns the wrong value when empty."
        assert "gives back" in rewritten

    def test_it_is_deterministic(self) -> None:
        assert rewrite_issue_text("returns when")[0] == rewrite_issue_text("returns when")[0]


class TestTheLiteralSubstitutionPreservesValues:
    def test_integers_become_equal_valued_expressions(self) -> None:
        rewritten, applied = substitute_literals("x = 3\n")

        assert applied.applied is True
        assert eval(rewritten.split("=", 1)[1]) == 3

    def test_the_rewritten_suite_still_parses_and_asserts_the_same_thing(self) -> None:
        rewritten, _ = substitute_literals(SUITE)

        assert "rotate" in rewritten
        assert compile(rewritten, "<suite>", "exec")


@pytest.mark.parametrize("template_id", d2_templates()[:8])
def test_a_perturbed_package_still_executes(template_id: str) -> None:
    """The set is a probe only if it runs. This executes it rather than asserting it would."""
    item = template(template_id)
    module_path = next(path for path in item.visible_files if path.startswith("src/"))
    visible_path = next(path for path in item.visible_files if path.startswith("tests/"))
    hidden_path = next(path for path in item.control_files if path.startswith("test_hidden"))
    perturbed = perturb(
        module_source=item.visible_files[module_path],
        visible_test=item.visible_files[visible_path],
        hidden_test=item.control_files[hidden_path],
        issue=item.issue_description,
    )

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / module_path.removeprefix("src/")).write_text(perturbed.module_source)
        (root / "test_visible.py").write_text(perturbed.visible_test)
        completed = subprocess.run(  # fixed argv, no shell, throwaway directory
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_visible.py"],
            cwd=root,
            capture_output=True,
            text=True,
        )

    assert completed.returncode == 0, completed.stdout


class TestTheResolvedSetStaysOutsideFitting:
    def test_a_probe_that_reached_fitting_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a probe"):
            ResolvedOodSet(
                kind="calibration_precheck",
                submanifest_hash="a" * 64,
                perturbation_seed=1,
                tasks=(_task(fitted=True),),
            )

    def test_a_set_that_declares_itself_fitted_is_refused(self) -> None:
        with pytest.raises(ValueError, match="not a probe"):
            ResolvedOodSet(
                kind="calibration_precheck",
                submanifest_hash="a" * 64,
                perturbation_seed=1,
                tasks=(_task(),),
                retained_outside_fitting=False,
            )

    def test_a_clean_set_is_bound_to_the_submanifest_that_declared_it(self) -> None:
        resolved = ResolvedOodSet(
            kind="calibration_precheck",
            submanifest_hash="b" * 64,
            perturbation_seed=21_024_606,
            tasks=(_task(),),
        )

        assert resolved.submanifest_hash == "b" * 64
        assert resolved.content_hash


def _task(*, fitted: bool = False) -> PerturbedTask:
    return PerturbedTask(
        template_id="d2_boundary.rotate_left",
        repository_group="d2-boundary-rotation",
        perturbations_applied=(calibration_ood.RENAME,),
        module_source_hash="c" * 64,
        visible_test_hash="d" * 64,
        issue_text_hash="e" * 64,
        visible_suite_passes=True,
        fitted=fitted,
    )
