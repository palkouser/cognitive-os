"""W3: the retrieval source pool as task packages, the repair path, and the leak guard.

Each of these pins something a W3 run measured and would otherwise have to trust: that a
retrieval group expands into a package the released runner can execute, that a two-run repair
path is accepted while a three-run correction path still needs all three of its runs, and
that a searchable text naming its own relevance judgement is refused rather than scored.

The last one is not hypothetical. The first resolution of this holdout put the task family in
the task signature, `search_text()` put the signature in front of every arm, and the vector arm
returned a perfect 1.0000 by reading the label it was being scored against.
"""

from __future__ import annotations

import pytest

from cognitive_os.coding import reality_trajectories
from cognitive_os.coding.reality_retrieval_specs_d3 import D3_RETRIEVAL_SPECS
from cognitive_os.coding.reality_tasks import (
    available_templates,
    d2_templates,
    d3_retrieval_templates,
    d3_templates,
    template,
)
from cognitive_os.coding.reality_trajectories import CorrectionStep, TrajectoryBuildError
from cognitive_os.domain.reality import RealityCandidateStrategy
from scripts.retrieval_holdout_d3 import _judgement_leaks

from .reality_fixtures import task_manifest
from .test_reality_downstream import PATH_A, _path, _Recorded

# ------------------------------------------------------------------ the packages


def test_every_retrieval_group_expands_into_a_runnable_package() -> None:
    assert len(d3_retrieval_templates()) == len(D3_RETRIEVAL_SPECS) == 60

    for spec in D3_RETRIEVAL_SPECS:
        item = template(spec.template_id)
        source = f"src/{spec.module}.py"
        assert item.visible_files[source] == spec.module_text(spec.failed)
        assert item.sources(RealityCandidateStrategy.CORRECT_NARROW) == {
            source: spec.module_text(spec.repaired)
        }
        assert f"tests/test_{spec.module}.py" in item.visible_files
        assert f"test_hidden_{spec.module}.py" in item.control_files


def test_the_retrieval_pool_is_a_fourth_registry_and_collides_with_none() -> None:
    """`d3_templates()` is what the correction catalogue selects from; it must not grow."""
    registries = (
        set(available_templates()),
        set(d2_templates()),
        set(d3_templates()),
        set(d3_retrieval_templates()),
    )
    for index, left in enumerate(registries):
        for right in registries[index + 1 :]:
            assert not left & right
    assert len(d3_templates()) == 21


def test_the_published_suite_cannot_separate_the_two_states() -> None:
    """It sees the module, never the contract. Both states import and expose a callable."""
    spec = D3_RETRIEVAL_SPECS[0]
    assert spec.module in spec.visible_test
    assert "assert" in spec.visible_test
    for body in (spec.failed, spec.repaired):
        namespace: dict[str, object] = {}
        exec(compile(spec.module_text(body), spec.module, "exec"), namespace)
        assert any(callable(value) for key, value in namespace.items() if not key.startswith("_"))


# ------------------------------------------------------------------ the repair path


@pytest.mark.asyncio
async def test_a_two_run_repair_path_is_a_correction_trajectory() -> None:
    recorded = _Recorded()
    baseline = await recorded.run(None, passed=False)
    repair = await recorded.run(RealityCandidateStrategy.CORRECT_NARROW, passed=True)

    plan = reality_trajectories.plan_repair_path(
        task_id=recorded.task.task_id, baseline=baseline, repair=repair
    )
    request, _, _ = await reality_trajectories.build_request(
        plan, task=recorded.task, artifacts=recorded.artifacts, created_at=recorded.task.created_at
    )

    assert plan.incorrect is None
    assert plan.strategy_revision == "correct_narrow"
    assert len(plan.steps) == 2
    assert request.compilation_id == plan.compilation_id


@pytest.mark.asyncio
async def test_a_three_run_path_still_needs_all_three_of_its_runs() -> None:
    """Relaxing the shape for a repair path must not relax it for a correction path."""
    recorded, steps = await _path()
    truncated = reality_trajectories.TrajectoryPlan(
        task_id=recorded.task.task_id,
        incorrect=PATH_A[0],
        correct=PATH_A[1],
        steps=(steps["baseline"], steps["correct"]),
    )

    with pytest.raises(TrajectoryBuildError, match="baseline, incorrect, correct"):
        await reality_trajectories.build_request(
            truncated,
            task=recorded.task,
            artifacts=recorded.artifacts,
            created_at=recorded.task.created_at,
        )


def test_a_repair_path_whose_second_step_is_a_baseline_is_refused() -> None:
    with pytest.raises(TrajectoryBuildError, match="candidate, not a baseline"):
        reality_trajectories.plan_repair_path(
            task_id=task_manifest().task_id,
            baseline=CorrectionStep(reference=None),  # type: ignore[arg-type]
            repair=CorrectionStep(reference=None),  # type: ignore[arg-type]
        )


# ------------------------------------------------------------------ the leak guard


class _Graph:
    """Only what `_judgement_leaks` reads: a searchable text."""

    def __init__(self, text: str) -> None:
        self._text = text

    def search_text(self) -> str:
        return self._text


class _Pair:
    def __init__(self, pair_id: str, group: str, text: str) -> None:
        self.pair_id = pair_id
        self.group = group
        self.failed = _Graph(text)
        self.successful = _Graph(text)


def test_a_signature_that_names_its_own_family_is_caught() -> None:
    spec = D3_RETRIEVAL_SPECS[0]
    family = spec.family.value
    leaky = _Pair(spec.repository_group, spec.repository_group, f"coding\nd3r_{family}:thing\n")

    leaks = _judgement_leaks([leaky], {spec.repository_group: spec})  # type: ignore[arg-type]

    assert leaks
    assert all(spec.repository_group in item for item in leaks)


def test_an_opaque_signature_leaks_nothing() -> None:
    spec = D3_RETRIEVAL_SPECS[0]
    opaque = _Pair(
        spec.repository_group,
        spec.repository_group,
        "coding\n9f1c0a2e-4b6d-5f8a-9c3e-7d2b1a4e6f80\nobservation status=completed\n",
    )

    assert _judgement_leaks([opaque], {spec.repository_group: spec}) == []  # type: ignore[arg-type]
