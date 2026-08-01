"""S21D2-022, P-CLONE cohort: the corpus properties, locked so a later template cannot break them.

Four of the first ten templates carried a defect, and none was visible by inspection — each
needed the near-clone detector or an executed hidden verifier to surface it. These tests are
that probe made permanent, so template eleven through ninety-five fail here rather than in the
campaign that was supposed to measure something.

The recipe-oracle check is the one that matters most. C3's recipe names predicted the verifier's
answer on 120 of 120 examples. Renaming them would have changed nothing; binding recipe to
variant per task is what removes it, and this asserts the binding actually did.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pytest

from cognitive_os.coding.reality_leakage import near_clone_pairs
from cognitive_os.coding.reality_task_specs import TASK_SPECS
from cognitive_os.coding.reality_task_specs_d2 import (
    D2_PROBE_SPECS,
    D2_RECIPES,
    D2TaskSpec,
    recipe_binding,
    recipe_is_repair,
)
from cognitive_os.domain.reality import D2_NEUTRAL_RECIPES, LABEL_PREDICTING_STRATEGIES


def _module_text(spec: D2TaskSpec, body: str) -> str:
    header = f'"""{spec.module_doc}"""\n\n'
    if spec.imports:
        header += f"{spec.imports}\n"
    return f"{header}\n{body.strip()}\n"


def _run(spec: D2TaskSpec, body: str, test_source: str) -> bool:
    """Execute one variant against one test module. The verifier decides, not a declaration."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / f"{spec.module}.py").write_text(_module_text(spec, body), encoding="utf-8")
        (root / f"test_{spec.module}.py").write_text(test_source, encoding="utf-8")
        return (
            subprocess.run(  # fixed argv, no shell, throwaway directory
                [sys.executable, "-m", "pytest", "-q", f"test_{spec.module}.py"],
                cwd=root,
                capture_output=True,
                text=True,
            ).returncode
            == 0
        )


class TestTheBindingRemovesTheRecipeOracle:
    def test_every_d2_recipe_is_a_neutral_one(self) -> None:
        assert set(D2_RECIPES) == D2_NEUTRAL_RECIPES
        assert not set(D2_RECIPES) & LABEL_PREDICTING_STRATEGIES

    def test_the_binding_is_deterministic(self) -> None:
        assert recipe_binding("d2_boundary.rotate_left") == recipe_binding(
            "d2_boundary.rotate_left"
        )

    def test_the_binding_is_a_permutation(self) -> None:
        for spec in D2_PROBE_SPECS:
            assert set(recipe_binding(spec.template_id)) == set(D2_RECIPES)

    def test_the_binding_is_not_the_same_for_every_task(self) -> None:
        """A fixed binding would put the C3 oracle back under new names."""
        assert len({recipe_binding(spec.template_id) for spec in D2_PROBE_SPECS}) > 1

    def test_no_recipe_repairs_the_contract_always_or_never(self) -> None:
        """C3 measured 1.0 and 0.0. Anything at either extreme is the oracle again."""
        totals: Counter[str] = Counter()
        repairs: Counter[str] = Counter()
        for spec in D2_PROBE_SPECS:
            for recipe, is_repair in recipe_is_repair(spec).items():
                totals[recipe.value] += 1
                repairs[recipe.value] += int(is_repair)

        for recipe, total in totals.items():
            rate = repairs[recipe] / total
            assert 0.0 < rate < 1.0, f"{recipe} repairs the contract {rate:.0%} of the time"


class TestTheCorpusIsStructurallyDistinct:
    def test_no_two_variants_in_the_cohort_are_near_clones(self) -> None:
        """Layout differences are invisible to the normaliser; structure must differ."""
        sources = {
            f"{spec.template_id}:{index}": _module_text(spec, variant)
            for spec in D2_PROBE_SPECS
            for index, variant in enumerate(spec.variants)
        }

        assert near_clone_pairs(sources) == ()

    def test_no_d2_baseline_collides_with_a_c3_baseline(self) -> None:
        d2 = {spec.template_id: _module_text(spec, spec.baseline) for spec in D2_PROBE_SPECS}
        c3 = {
            f"c3:{spec.template_id}": (
                f'"""{spec.module_doc}"""\n\n'
                + (f"{spec.imports}\n" if spec.imports else "")
                + f"\n{spec.baseline.strip()}\n"
            )
            for spec in TASK_SPECS
        }
        crossing = [
            pair
            for pair in near_clone_pairs({**d2, **c3})
            if pair.left.startswith("c3:") != pair.right.startswith("c3:")
        ]

        assert crossing == []

    def test_every_template_id_and_group_is_unique(self) -> None:
        ids = [spec.template_id for spec in D2_PROBE_SPECS]
        groups = [spec.repository_group for spec in D2_PROBE_SPECS]

        assert len(set(ids)) == len(ids)
        assert len(set(groups)) == len(groups)

    def test_no_d2_template_id_collides_with_a_c3_one(self) -> None:
        assert not {spec.template_id for spec in D2_PROBE_SPECS} & {
            spec.template_id for spec in TASK_SPECS
        }

    def test_every_template_declares_two_edge_cases(self) -> None:
        for spec in D2_PROBE_SPECS:
            assert all(spec.edge_cases), f"{spec.template_id} does not name both edge cases"


@pytest.mark.parametrize("spec", D2_PROBE_SPECS, ids=lambda item: item.template_id)
class TestTheVerifierAgreesWithTheAuthoredIntent:
    def test_the_baseline_passes_every_visible_test(self, spec: D2TaskSpec) -> None:
        """The published defect has to be invisible, or the task measures reading comprehension."""
        assert _run(spec, spec.baseline, spec.visible_test)

    def test_the_baseline_fails_the_hidden_tests(self, spec: D2TaskSpec) -> None:
        assert not _run(spec, spec.baseline, spec.hidden_test)

    def test_each_variant_matches_its_declaration(self, spec: D2TaskSpec) -> None:
        """A variant that repairs the contract when it said it would not is a corpus defect."""
        for variant, declared in zip(spec.variants, spec.repairs_contract, strict=True):
            assert _run(spec, variant, spec.hidden_test) is declared

    def test_exactly_two_of_four_variants_repair_the_contract(self, spec: D2TaskSpec) -> None:
        """The 2-of-4 balance is what fixes the deterministic baseline at 0.5000."""
        assert sum(spec.repairs_contract) == 2
