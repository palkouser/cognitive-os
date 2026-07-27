"""S21C1-062: the learned evidence benchmark manifests, checked as manifests.

The benchmark itself runs in CI. These tests guard the properties a green run cannot
demonstrate: that the required case families are all present, that the volumes the
backlog set are actually met, and that every scenario named in a manifest is one the
adapter implements — a typo would otherwise become a silently unknown scenario.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.learned_adapter import scenarios

CI_MANIFEST = Path("benchmarks/manifests/sprint21c1-learned-ci.yaml")
SEED_MANIFEST = Path("benchmarks/manifests/sprint21c1-learned-seed.yaml")

#: Every family the Sprint 21C1 backlog requires the benchmark to cover.
REQUIRED_FAMILIES = {
    "lifecycle",
    "observation",
    "dataset",
    "artifact",
    "replay",
    "activation",
    "rollback",
}


def _scenarios(path: Path) -> list[str]:
    return [str(case.problem_request.get("scenario", "")) for case in load_manifest(path).cases]


@pytest.mark.parametrize("path", [CI_MANIFEST, SEED_MANIFEST])
def test_every_scenario_is_one_the_adapter_implements(path: Path) -> None:
    """A typo in a manifest must fail here, not become an unknown scenario at runtime."""
    unknown = sorted(set(_scenarios(path)) - set(scenarios()))
    assert unknown == []


@pytest.mark.parametrize("path", [CI_MANIFEST, SEED_MANIFEST])
def test_every_required_case_family_is_present(path: Path) -> None:
    missing = sorted(REQUIRED_FAMILIES - set(_scenarios(path)))
    assert missing == []


def test_the_ci_gate_meets_its_declared_volume() -> None:
    assert len(load_manifest(CI_MANIFEST).cases) >= 12


def test_the_seed_set_meets_its_declared_volume() -> None:
    assert len(load_manifest(SEED_MANIFEST).cases) >= 48


@pytest.mark.parametrize("path", [CI_MANIFEST, SEED_MANIFEST])
def test_case_identifiers_are_unique(path: Path) -> None:
    ids = [case.case_id for case in load_manifest(path).cases]
    assert len(set(ids)) == len(ids)


def test_the_seed_set_exercises_both_outcomes_for_every_family() -> None:
    """A family that only ever passes proves the happy path and nothing else."""
    manifest = load_manifest(SEED_MANIFEST)
    outcomes: dict[str, set[str]] = {}
    for case in manifest.cases:
        scenario = str(case.problem_request.get("scenario", ""))
        outcomes.setdefault(scenario, set()).add(str(case.expected_outputs.get("status", "passed")))
    one_sided = sorted(
        name
        for name, seen in outcomes.items()
        if name in {"activation", "observation", "dataset", "artifact", "replay"} and len(seen) < 2
    )
    assert one_sided == []
