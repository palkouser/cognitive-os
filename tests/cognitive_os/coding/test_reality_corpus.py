"""S21C3-020, S21C3-024 and S21C3-030: what the corpus must be true of without running it.

Everything here is text analysis and contract construction. Whether a candidate actually
fails the hidden suite is a question only a container can answer, and
`tests/integration/coding/test_reality_corpus_execution.py` is where that is asked.
"""

from __future__ import annotations

from collections import Counter
from uuid import uuid4

import pytest

from cognitive_os.coding import reality_candidates, reality_leakage
from cognitive_os.coding.reality_task_specs import TASK_SPECS
from cognitive_os.coding.reality_tasks import (
    _TEMPLATES,
    available_templates,
    build_manifest,
    offline_strategies,
    template,
    write_task,
)
from cognitive_os.domain.reality import (
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityStrategyFamily,
)

from .reality_fixtures import FIXTURE_TIME, digest

MINIMUM_TASKS = 30
MINIMUM_FAMILIES = 6
MINIMUM_TASKS_PER_FAMILY = 5


def _manifest(template_id: str, *, seed: int = 1):
    return build_manifest(
        template_id,
        seed=seed,
        hidden_bundle_artifact_id=uuid4(),
        hidden_bundle_hash=digest(f"bundle:{template_id}"),
        created_at=FIXTURE_TIME,
    )


def _source_of(template_id: str, strategy: RealityCandidateStrategy | None = None) -> str:
    item = template(template_id)
    if strategy is None:
        return item.visible_files[next(p for p in item.visible_files if p.startswith("src/"))]
    return next(iter(item.candidate_sources[strategy].values()))


# ------------------------------------------------------------------------------ S21C3-020


def test_the_corpus_meets_its_declared_size() -> None:
    assert len(available_templates()) >= MINIMUM_TASKS


def test_every_family_is_represented_at_least_five_times() -> None:
    counts = Counter(spec.family for spec in TASK_SPECS)

    assert len(counts) >= MINIMUM_FAMILIES
    assert min(counts.values()) >= MINIMUM_TASKS_PER_FAMILY


def test_template_and_repository_group_identities_are_unique() -> None:
    assert len({spec.template_id for spec in TASK_SPECS}) == len(TASK_SPECS)
    assert len({spec.repository_group for spec in TASK_SPECS}) == len(TASK_SPECS)
    assert len({spec.module for spec in TASK_SPECS}) == len(TASK_SPECS)


def test_every_task_regenerates_byte_identically() -> None:
    for template_id in available_templates():
        first = _manifest(template_id)
        second = _manifest(template_id)
        assert first.task_id == second.task_id, template_id
        assert first.projection.content_hash == second.projection.content_hash, template_id


def test_a_different_seed_produces_a_different_task_identity() -> None:
    template_id = available_templates()[0]

    assert _manifest(template_id, seed=1).task_id != _manifest(template_id, seed=2).task_id


def test_every_task_declares_verified_project_rights() -> None:
    for template_id in available_templates():
        rights = _manifest(template_id).rights
        assert rights.licence_identifier == "Apache-2.0", template_id
        assert rights.rights_verified is True, template_id
        assert rights.sensitivity.value == "public", template_id


def test_every_task_requires_the_hidden_criterion() -> None:
    for template_id in available_templates():
        assert "coding.hidden_pytest" in _manifest(template_id).required_verifier_ids


def test_control_material_never_lands_in_the_workspace(tmp_path) -> None:  # type: ignore[no-untyped-def]
    for index, template_id in enumerate(available_templates()):
        task = write_task(
            template_id,
            root=tmp_path / str(index),
            seed=1,
            hidden_bundle_artifact_id=uuid4(),
            hidden_bundle_hash=digest("bundle"),
            created_at=FIXTURE_TIME,
        )
        workspace = {
            item.relative_to(task.workspace).as_posix()
            for item in task.workspace.rglob("*")
            if item.is_file()
        }
        assert not any(name.startswith("test_hidden_") for name in workspace), template_id
        assert task.control.resolve() not in task.workspace.resolve().parents


def test_every_task_declares_two_distinct_edge_cases() -> None:
    for spec in TASK_SPECS:
        first, second = spec.edge_cases
        assert first and second, spec.template_id
        assert first != second, spec.template_id


def test_the_five_variants_of_a_task_are_all_different() -> None:
    for spec in TASK_SPECS:
        variants = {
            spec.baseline,
            spec.incomplete_a,
            spec.incomplete_b,
            spec.correct_narrow,
            spec.correct_robust,
        }
        assert len(variants) == 5, spec.template_id


# ------------------------------------------------------------------------------ S21C3-030


def test_every_task_has_all_four_offline_strategies() -> None:
    for template_id in available_templates():
        assert set(template(template_id).candidate_sources) == set(offline_strategies())


def test_the_corpus_yields_one_hundred_and_twenty_candidates() -> None:
    identities = set()
    for template_id in available_templates():
        task = _manifest(template_id)
        for strategy in offline_strategies():
            identities.add(reality_candidates.build_candidate(task, strategy).candidate_id)

    assert len(identities) == len(available_templates()) * 4


def test_every_candidate_patch_round_trips_through_the_repository_patch_parser() -> None:
    """A diff that does not reproduce its own source is a candidate that never ran."""
    hashes = set()
    for template_id in available_templates():
        task = _manifest(template_id)
        for strategy in offline_strategies():
            candidate = reality_candidates.build_candidate(task, strategy)
            hashes.add(candidate.patch_hash)

    assert len(hashes) == len(available_templates()) * 4


def test_candidate_identity_is_derived_not_allocated() -> None:
    task = _manifest(available_templates()[0])
    strategy = offline_strategies()[0]

    first = reality_candidates.build_candidate(task, strategy)
    second = reality_candidates.build_candidate(task, strategy)

    assert first.candidate_id == second.candidate_id
    assert first.patch_hash == second.patch_hash


def test_candidate_manifests_are_curated_and_carry_no_provider_identity() -> None:
    task = _manifest(available_templates()[0])
    for strategy in offline_strategies():
        candidate = reality_candidates.build_candidate(task, strategy)
        manifest = reality_candidates.build_manifest(
            task, candidate, patch_artifact_id=uuid4(), created_at=FIXTURE_TIME
        )

        assert manifest.source is RealityCandidateSource.CURATED
        assert manifest.provider_id is None
        assert manifest.provider_output_id is None
        assert manifest.patch_hash == candidate.patch_hash


def test_two_incorrect_and_two_correct_strategies_are_declared() -> None:
    families = Counter(strategy.family for strategy in offline_strategies())

    assert families[RealityStrategyFamily.INCORRECT] == 2
    assert families[RealityStrategyFamily.CORRECT] == 2


def test_a_candidate_from_another_task_is_refused() -> None:
    first, second = (_manifest(item) for item in available_templates()[:2])
    candidate = reality_candidates.build_candidate(first, offline_strategies()[0])

    with pytest.raises(reality_candidates.CandidateGenerationError, match="different task"):
        reality_candidates.build_manifest(
            second, candidate, patch_artifact_id=uuid4(), created_at=FIXTURE_TIME
        )


# ------------------------------------------------------------------------------ S21C3-024


def test_no_control_token_reaches_any_provider_visible_surface() -> None:
    leaks = []
    for template_id in available_templates():
        task = _manifest(template_id)
        tokens = reality_leakage.control_tokens(task, template(template_id))
        leaks.extend(
            reality_leakage.scan_for_control_leaks(
                reality_leakage.projection_surfaces(task.projection), tokens
            )
        )

    assert leaks == []


def test_the_projection_carries_no_lookup_key_into_the_generator() -> None:
    leaks = []
    for template_id in available_templates():
        leaks.extend(reality_leakage.lookup_key_leaks(_manifest(template_id), template_id))

    assert leaks == []


@pytest.mark.parametrize(
    "strategy",
    (None, *offline_strategies()),
    ids=lambda item: "baseline" if item is None else item.value,
)
def test_no_two_tasks_are_near_clones(strategy: RealityCandidateStrategy | None) -> None:
    """Thirty near-clones is six problems wearing thirty hats."""
    sources = {item: _source_of(item, strategy) for item in available_templates()}

    assert reality_leakage.near_clone_pairs(sources) == ()


def test_no_two_tasks_share_a_declared_answer() -> None:
    assert reality_leakage.duplicate_candidate_sources(_TEMPLATES) == ()


def test_the_normalizer_actually_collapses_a_renamed_clone() -> None:
    """A detector that finds nothing because it detects nothing is worse than no detector."""
    original = "def take(items):\n    return items[0]\n"
    renamed = "def grab(values):\n    return values[0]\n"

    assert reality_leakage.normalized_structure_hash(original) == (
        reality_leakage.normalized_structure_hash(renamed)
    )
    assert reality_leakage.token_stream_hash(original) == (
        reality_leakage.token_stream_hash(renamed)
    )


def test_the_normalizer_separates_genuinely_different_shapes() -> None:
    first = "def take(items):\n    return items[0]\n"
    second = "def take(items):\n    for item in items:\n        return item\n    return None\n"

    assert reality_leakage.normalized_structure_hash(first) != (
        reality_leakage.normalized_structure_hash(second)
    )


def test_the_leak_scanner_actually_finds_a_planted_token() -> None:
    template_id = available_templates()[0]
    task = _manifest(template_id)
    tokens = reality_leakage.control_tokens(task, template(template_id))
    planted = sorted(tokens)[0]

    leaks = reality_leakage.scan_for_control_leaks(
        {"provider.request": f"here is a hint: {planted}"}, tokens
    )

    assert [item.token for item in leaks] == [planted]


def test_cross_task_transfers_are_enumerated_within_each_family() -> None:
    transfers = reality_leakage.cross_task_transfers(_TEMPLATES)
    families = {template(item.donor_template_id).family for item in transfers}

    assert len(transfers) == MINIMUM_FAMILIES * MINIMUM_TASKS_PER_FAMILY * (
        MINIMUM_TASKS_PER_FAMILY - 1
    )
    assert len(families) == MINIMUM_FAMILIES
    assert all(item.same_family for item in transfers)
    assert all(item.donor_template_id != item.recipient_template_id for item in transfers)
