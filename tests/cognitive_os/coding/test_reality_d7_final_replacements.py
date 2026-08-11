"""S21D7-038: the four groups authored to repair the carried final roles.

The defect these replace was invisible for five sprints because nothing ever tried to encode a
final body. So the first test here is the one that would have caught it: every body of every
carried role goes through the canonicaliser the campaign uses. It is deliberately written over
the *roles*, not over the replacements, because a test that only checked the new groups would
miss the next body someone carries in.
"""

from __future__ import annotations

import pytest

from cognitive_os.coding.reality_task_specs_d7_final import (
    D7_FINAL_REPLACEMENT_SPECS,
    D7_FINAL_WITHDRAWN,
)
from cognitive_os.coding.reality_tasks import template
from cognitive_os.domain.reality import RealityCandidateStrategy
from cognitive_os.learning.correction_catalogue_d7 import seal_d7_corpus
from cognitive_os.learning.correction_protocol import CorrectionPartition
from cognitive_os.learning.correction_source import canonical_source_hash

CARRIED = (CorrectionPartition.FINAL_A, CorrectionPartition.FINAL_B, CorrectionPartition.CANARY)


@pytest.fixture(scope="module")
def bundle() -> object:
    return seal_d7_corpus()


@pytest.mark.parametrize("partition", CARRIED)
def test_every_carried_body_canonicalises(bundle: object, partition: CorrectionPartition) -> None:
    """The check five sprints of unchanged digests did not amount to."""
    for group in bundle.catalogues[partition].groups:  # type: ignore[attr-defined]
        item = template(group.template_id)
        path = next(name for name in item.visible_files if name.startswith("src/"))
        canonical_source_hash(item.visible_files[path])
        for slot in group.slots:
            recipe = RealityCandidateStrategy(slot.recipe)
            canonical_source_hash(item.neutral_candidate_sources[recipe][path])


@pytest.mark.parametrize("partition", (CorrectionPartition.FINAL_A, CorrectionPartition.FINAL_B))
def test_a_repaired_role_keeps_its_size_and_drops_its_withdrawn_groups(
    bundle: object, partition: CorrectionPartition
) -> None:
    groups = {
        group.repository_group
        for group in bundle.catalogues[partition].groups  # type: ignore[attr-defined]
    }
    assert len(groups) == 30
    assert not groups & set(D7_FINAL_WITHDRAWN[partition.value])


def test_the_replacements_are_where_the_withdrawn_groups_were(bundle: object) -> None:
    placed = {
        group.repository_group
        for partition in (CorrectionPartition.FINAL_A, CorrectionPartition.FINAL_B)
        for group in bundle.catalogues[partition].groups  # type: ignore[attr-defined]
    }
    assert {spec.repository_group for spec in D7_FINAL_REPLACEMENT_SPECS} <= placed


def test_every_replacement_declares_four_variants_and_two_suites() -> None:
    for spec in D7_FINAL_REPLACEMENT_SPECS:
        assert len(spec.variants) == 4
        assert spec.visible_test != spec.hidden_test
        assert len(spec.edge_cases) == 2


def test_a_replacement_group_is_not_a_clone_of_a_released_one() -> None:
    """Body-level separation, which is the level a rewritten variant can still collide at."""
    from cognitive_os.coding.reality_tasks import _ALL_TEMPLATES

    new = {spec.template_id for spec in D7_FINAL_REPLACEMENT_SPECS}
    seen: dict[str, str] = {}
    for template_id, item in _ALL_TEMPLATES.items():
        path = next(name for name in item.visible_files if name.startswith("src/"))
        bodies = {"baseline": item.visible_files[path]}
        for recipe, sources in item.neutral_candidate_sources.items():
            bodies[str(recipe)] = sources[path]
        for label, source in bodies.items():
            try:
                digest = canonical_source_hash(source)
            except Exception:
                continue
            owner = seen.setdefault(digest, template_id)
            if owner != template_id:
                assert template_id not in new and owner not in new, (
                    f"{template_id}:{label} is a body-level clone of {owner}"
                )
