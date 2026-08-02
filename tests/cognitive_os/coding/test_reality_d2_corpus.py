"""S21D2-022: the corpus properties, locked so a later template cannot quietly break them.

Four of the first ten templates carried a defect, and none was visible by inspection — each
needed the near-clone detector or an executed hidden verifier to surface it. A fifth defect
surfaced only once the cross-corpus check was widened from baselines to every candidate: one
D2 repair was byte-identical to a C3 correction, which is the transfer `reality_leakage`
exists to refuse. These tests are those probes made permanent.

The recipe-oracle check is the one that matters most. C3's recipe names predicted the
verifier's answer on 120 of 120 examples. Renaming them would have changed nothing; binding
recipe to variant per task is what removes it, and this asserts the binding actually did.

Every verdict here is executed, never declared, because a declaration is exactly what the probe
found to be wrong four times out of ten. The executions run once per session in a thread pool —
they are subprocesses, so the GIL is not in the way — and the assertions read that table.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from cognitive_os.coding.reality_leakage import near_clone_pairs
from cognitive_os.coding.reality_task_specs import TASK_SPECS, TaskSpec
from cognitive_os.coding.reality_task_specs_d2 import (
    D2_PROBE_SPECS,
    D2_RECIPES,
    D2_TASK_SPECS,
    D2TaskSpec,
    module_source,
    recipe_binding,
    recipe_is_repair,
)
from cognitive_os.coding.reality_tasks import available_templates, d2_templates, template
from cognitive_os.domain.reality import (
    D2_NEUTRAL_RECIPES,
    LABEL_PREDICTING_STRATEGIES,
    RealityCandidateStrategy,
)
from cognitive_os.learning.correction_catalogue import corpus_entries, seal_corpus
from cognitive_os.learning.correction_protocol import CorrectionPartition

#: The C3 fields that hold a candidate body. A D2 variant may collide with any of them, not
#: only with the baseline: reproducing a C3 *correction* is the more serious collision.
_C3_CANDIDATE_FIELDS = (
    "baseline",
    "incomplete_a",
    "incomplete_b",
    "correct_narrow",
    "correct_robust",
)


def _c3_module(spec: TaskSpec, field: str) -> str:
    """One C3 candidate as a module, built the way `module_source` builds a D2 one."""
    header = f'"""{spec.module_doc}"""\n'
    if spec.imports:
        header += f"\n{spec.imports}\n"
    return f"{header}\n\n{getattr(spec, field).strip()}\n"


def _d2_variant_modules() -> dict[str, str]:
    return {
        f"{spec.template_id}:{index}": module_source(spec, variant)
        for spec in D2_TASK_SPECS
        for index, variant in enumerate(spec.variants)
    }


def _execute(job: tuple[str, str, str, str]) -> tuple[str, bool]:
    """(key, module, module text, test text) -> did the suite pass."""
    key, module, text, test_source = job
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(text, encoding="utf-8")
        (root / f"test_{module}.py").write_text(test_source, encoding="utf-8")
        completed = subprocess.run(  # fixed argv, no shell, throwaway directory
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                f"test_{module}.py",
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        return key, completed.returncode == 0


@pytest.fixture(scope="session")
def verdicts() -> Iterator[dict[str, bool]]:
    """Every candidate of every template, run against both suites, once per session.

    Ninety-five templates at six runs each is 570 pytest invocations. Serially that is minutes;
    in a pool it is under a minute, which is the difference between a check that runs on every
    change and one that gets skipped.
    """
    jobs: list[tuple[str, str, str, str]] = []
    for spec in D2_TASK_SPECS:
        baseline = module_source(spec, spec.baseline)
        jobs.append(
            (
                f"{spec.template_id}|baseline|visible",
                spec.module,
                baseline,
                spec.visible_test,
            )
        )
        jobs.append(
            (
                f"{spec.template_id}|baseline|hidden",
                spec.module,
                baseline,
                spec.hidden_test,
            )
        )
        for index, variant in enumerate(spec.variants):
            text = module_source(spec, variant)
            jobs.append(
                (
                    f"{spec.template_id}|{index}|visible",
                    spec.module,
                    text,
                    spec.visible_test,
                )
            )
            jobs.append(
                (
                    f"{spec.template_id}|{index}|hidden",
                    spec.module,
                    text,
                    spec.hidden_test,
                )
            )

    with ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 4) * 2)) as pool:
        yield dict(pool.map(_execute, jobs))


class TestTheBindingRemovesTheRecipeOracle:
    def test_every_d2_recipe_is_a_neutral_one(self) -> None:
        assert set(D2_RECIPES) == D2_NEUTRAL_RECIPES
        assert not set(D2_RECIPES) & LABEL_PREDICTING_STRATEGIES

    def test_the_binding_is_deterministic(self) -> None:
        assert recipe_binding("d2_boundary.rotate_left") == recipe_binding(
            "d2_boundary.rotate_left"
        )

    def test_the_binding_is_a_permutation(self) -> None:
        for spec in D2_TASK_SPECS:
            assert set(recipe_binding(spec.template_id)) == set(D2_RECIPES)

    def test_the_binding_is_not_the_same_for_every_task(self) -> None:
        """A fixed binding would put the C3 oracle back under new names."""
        assert len({recipe_binding(spec.template_id) for spec in D2_TASK_SPECS}) > 1

    def test_no_recipe_repairs_the_contract_always_or_never(self) -> None:
        """C3 measured 1.0 and 0.0. Anything at either extreme is the oracle again."""
        totals: Counter[str] = Counter()
        repairs: Counter[str] = Counter()
        for spec in D2_TASK_SPECS:
            for recipe, is_repair in recipe_is_repair(spec).items():
                totals[recipe.value] += 1
                repairs[recipe.value] += int(is_repair)

        for recipe, total in totals.items():
            rate = repairs[recipe] / total
            assert 0.3 < rate < 0.7, f"{recipe} repairs the contract {rate:.0%} of the time"


class TestTheCorpusIsBigEnoughForTheContract:
    def test_the_corpus_meets_the_new_group_floor(self) -> None:
        """S21D2-014 raised the final batches to thirty each, which raised this to ninety-five."""
        assert len(D2_TASK_SPECS) >= 95

    def test_the_probe_cohort_is_still_part_of_the_corpus(self) -> None:
        """The P-CLONE evidence reports a defect rate over exactly these ten."""
        assert set(D2_PROBE_SPECS) <= set(D2_TASK_SPECS)

    def test_no_family_carries_the_corpus_on_its_own(self) -> None:
        counts = Counter(spec.family for spec in D2_TASK_SPECS)
        assert min(counts.values()) >= 10


class TestTheCorpusIsStructurallyDistinct:
    def test_no_two_variants_in_the_corpus_are_near_clones(self) -> None:
        """Layout differences are invisible to the normaliser; structure must differ."""
        assert near_clone_pairs(_d2_variant_modules()) == ()

    def test_no_d2_baseline_collides_with_a_c3_baseline(self) -> None:
        d2 = {spec.template_id: module_source(spec, spec.baseline) for spec in D2_TASK_SPECS}
        c3 = {f"c3:{spec.template_id}": _c3_module(spec, "baseline") for spec in TASK_SPECS}
        crossing = [
            pair
            for pair in near_clone_pairs({**d2, **c3})
            if pair.left.startswith("c3:") != pair.right.startswith("c3:")
        ]

        assert crossing == []

    def test_no_d2_variant_reproduces_a_c3_candidate(self) -> None:
        """A D2 repair that is a C3 correction is a solved task, not a new one."""
        c3 = {
            f"c3:{spec.template_id}:{field}": _c3_module(spec, field)
            for spec in TASK_SPECS
            for field in _C3_CANDIDATE_FIELDS
        }
        crossing = [
            pair
            for pair in near_clone_pairs({**_d2_variant_modules(), **c3})
            if pair.left.startswith("c3:") != pair.right.startswith("c3:")
        ]

        assert crossing == []

    def test_every_template_id_group_and_module_is_unique(self) -> None:
        for label, values in (
            ("template ids", [spec.template_id for spec in D2_TASK_SPECS]),
            ("repository groups", [spec.repository_group for spec in D2_TASK_SPECS]),
        ):
            repeated = [name for name, count in Counter(values).items() if count > 1]
            assert repeated == [], f"repeated {label}: {repeated}"

    def test_no_d2_template_id_collides_with_a_c3_one(self) -> None:
        assert not {spec.template_id for spec in D2_TASK_SPECS} & {
            spec.template_id for spec in TASK_SPECS
        }

    def test_every_template_declares_two_edge_cases(self) -> None:
        for spec in D2_TASK_SPECS:
            assert all(spec.edge_cases), f"{spec.template_id} does not name both edge cases"


@pytest.mark.parametrize("spec", D2_TASK_SPECS, ids=lambda item: item.template_id)
class TestTheVerifierAgreesWithTheAuthoredIntent:
    def test_the_baseline_passes_every_visible_test(
        self, spec: D2TaskSpec, verdicts: dict[str, bool]
    ) -> None:
        """The published defect has to be invisible, or the task measures reading comprehension."""
        assert verdicts[f"{spec.template_id}|baseline|visible"]

    def test_the_baseline_fails_the_hidden_tests(
        self, spec: D2TaskSpec, verdicts: dict[str, bool]
    ) -> None:
        assert not verdicts[f"{spec.template_id}|baseline|hidden"]

    def test_each_variant_matches_its_declaration(
        self, spec: D2TaskSpec, verdicts: dict[str, bool]
    ) -> None:
        """A variant that repairs the contract when it said it would not is a corpus defect."""
        for index, declared in enumerate(spec.repairs_contract):
            assert verdicts[f"{spec.template_id}|{index}|hidden"] is declared

    def test_every_variant_passes_the_visible_tests(
        self, spec: D2TaskSpec, verdicts: dict[str, bool]
    ) -> None:
        """A candidate that fails the published suite would be rejected before it was ranked."""
        for index in range(len(spec.variants)):
            assert verdicts[f"{spec.template_id}|{index}|visible"]

    def test_exactly_two_of_four_variants_repair_the_contract(self, spec: D2TaskSpec) -> None:
        """The 2-of-4 balance is what fixes the deterministic baseline at 0.5000."""
        assert sum(spec.repairs_contract) == 2


class TestTheRegistryPlacesTheBodiesTheSealNamed:
    """S21D2-023: what the runner materialises has to be what the catalogue committed to.

    The sealed catalogue records a `variant_index` per slot and the runner asks the template
    registry for a recipe. If those two disagree the campaign executes one body and reports
    another, and every outcome in the corpus is attached to the wrong candidate — a defect
    that no count would reveal, because the counts would all still add up.
    """

    def test_a_d2_template_is_keyed_by_the_neutral_recipes(self) -> None:
        for template_id in d2_templates():
            assert set(template(template_id).candidate_sources) == set(D2_RECIPES)

    def test_a_c3_template_keeps_its_own_keying_and_gains_the_neutral_one(self) -> None:
        """Thirty C3 groups are inherited into D2 training and must not carry C3 recipe names."""
        item = template(TASK_SPECS[0].template_id)

        assert set(item.candidate_sources) == set(LABEL_PREDICTING_STRATEGIES) - {
            RealityCandidateStrategy.PROVIDER_PROPOSED
        }
        assert set(item.neutral_candidate_sources) == set(D2_RECIPES)

    def test_the_two_corpora_stay_separately_addressable(self) -> None:
        assert not set(available_templates()) & set(d2_templates())
        assert len(available_templates()) == len(TASK_SPECS)
        assert len(d2_templates()) == len(D2_TASK_SPECS)

    @pytest.mark.parametrize("partition", list(CorrectionPartition))
    def test_every_sealed_slot_resolves_to_the_body_it_indexed(self, partition) -> None:
        """The catalogue's `variant_index` and the registry's recipe key must agree everywhere."""
        catalogue = seal_corpus().catalogues[partition]
        entries = {entry.template_id: entry for entry in corpus_entries()}

        for group in catalogue.groups:
            item = template(group.template_id)
            for slot in group.slots:
                recipe = RealityCandidateStrategy(slot.recipe)
                materialised = next(iter(item.sources(recipe).values()))
                declared = entries[group.template_id].module_text(slot.variant_index)
                assert materialised == declared, f"{group.template_id} slot {slot.position}"
