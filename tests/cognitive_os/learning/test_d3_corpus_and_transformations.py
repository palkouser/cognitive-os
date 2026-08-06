"""W2: the fresh corpora, the independent transformation generator, and the D3 seal.

Every test here pins something a W2 run measured and would otherwise have to trust: that the
rename primitive leaves attributes and module paths alone, that both rename maps are
independent of each other and of the production canonicaliser, that v2 is exactly invariant
across all six frozen cases, and that the seal carries D2's four reused roles by hash rather
than by re-derivation.
"""

from __future__ import annotations

import pytest

from cognitive_os.coding.reality_retrieval_specs_d3 import D3_RETRIEVAL_SPECS
from cognitive_os.coding.reality_task_specs_d2 import module_source
from cognitive_os.coding.reality_task_specs_d3 import (
    D3_CALIBRATION_SPECS,
    D3_FIXTURE_SPEC,
    D3_TASK_SPECS,
)
from cognitive_os.coding.reality_tasks import d2_templates, d3_templates, template
from cognitive_os.learning import transformations_d3
from cognitive_os.learning.calibration_ood import rename_identifiers, rename_map
from cognitive_os.learning.correction_catalogue import seal_corpus
from cognitive_os.learning.correction_catalogue_d3 import (
    NOMINAL_DECISIONS_PER_STAGE,
    build_retrieval_pool,
    eligible_calibration_groups,
    seal_d3_corpus,
)
from cognitive_os.learning.correction_features import (
    CANONICAL_EMBEDDING_WINDOW_CHARACTERS,
    canonical_embedding_windows,
    pool_canonical_embedding,
)
from cognitive_os.learning.correction_ladder import (
    FROZEN_MINILM_COSINE,
    GRAPH_RUNG_INELIGIBLE,
    V2_COSINE_RUNG_INELIGIBLE,
    eligible_rungs,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition
from cognitive_os.learning.correction_ranking import ENCODER_VERSION, ENCODER_VERSION_V2
from cognitive_os.learning.correction_source import (
    canonical_source_bytes,
    canonical_source_hash,
)

_REUSED = (
    CorrectionPartition.TRAINING,
    CorrectionPartition.FINAL_A,
    CorrectionPartition.FINAL_B,
    CorrectionPartition.CANARY,
)


# ------------------------------------------------------------------ the rename primitive


def test_an_attribute_sharing_a_local_name_is_not_renamed() -> None:
    """W2-A5: `counts.items()` reaches a dict method, not the local the map owns."""
    source = "def tally(items):\n    counts = {}\n    return sorted(counts.items())\n"
    mapping = rename_map(source)
    (renamed,) = rename_identifiers(source)

    assert mapping["items"] != "items"
    # The parameter moved; the attribute of the same name did not.
    assert f"def {mapping['tally']}({mapping['items']}):" in renamed
    assert f"{mapping['counts']}.items()" in renamed


def test_a_module_path_sharing_a_function_name_is_not_renamed() -> None:
    """W2-F3: `from step_gaps import step_gaps` names a file and then a function."""
    module = "def step_gaps(values):\n    return list(values)\n"
    suite = "from step_gaps import step_gaps\n\n\ndef test_it():\n    assert step_gaps([]) == []\n"
    _, renamed_suite = rename_identifiers(module, suite)

    assert renamed_suite.startswith("from step_gaps import ")
    assert "from step_gaps import step_gaps" not in renamed_suite


def test_the_two_rename_maps_disagree_on_every_name() -> None:
    source = "def widen(edge, span):\n    total = edge + span\n    return total\n"
    first = transformations_d3.rename_map_a(source)
    second = transformations_d3.rename_map_b(source)

    assert set(first) == set(second)
    assert all(first[name] != second[name] for name in first)


def test_the_hard_coded_oracle_still_holds() -> None:
    transformations_d3.check_golden_pairs()
    assert len(transformations_d3.hard_coded_oracle_hash()) == 64
    assert len(transformations_d3.generator_code_hash()) == 64


def test_a_package_using_a_mapped_name_as_a_call_keyword_is_refused() -> None:
    """A token stream cannot tell `f(key=1)`'s keyword from a binding, so it fails closed."""
    source = "def tally(items, key):\n    return sorted(items, key=key)\n"
    assert transformations_d3.eligible(source) is False


def test_an_unknown_case_name_is_refused() -> None:
    with pytest.raises(transformations_d3.PerturbationError):
        transformations_d3.transform(
            "identifier_rename_c",
            module_source="def f():\n    return 1\n",
            variants=(),
            visible_test="",
            hidden_test="",
            issue="",
        )


# ------------------------------------------------------------------ the fresh corpora


def test_the_calibration_corpus_is_exactly_twenty_eligible_groups() -> None:
    assert len(D3_CALIBRATION_SPECS) == 20
    assert len(eligible_calibration_groups()) == 20
    assert D3_FIXTURE_SPEC not in D3_CALIBRATION_SPECS
    assert len({spec.repository_group for spec in D3_TASK_SPECS}) == len(D3_TASK_SPECS)


def test_the_retrieval_pool_is_overproduced_and_paired() -> None:
    assert len(D3_RETRIEVAL_SPECS) >= 60
    pool = build_retrieval_pool()
    assert len(pool.groups) == len(D3_RETRIEVAL_SPECS)
    assert pool.outcomes_present is False
    assert pool.queries_resolved is False
    assert all(group.failed_source_hash != group.repaired_source_hash for group in pool.groups)


def test_the_d3_registry_neither_shrinks_nor_collides_with_d2() -> None:
    assert len(d3_templates()) == len(D3_TASK_SPECS)
    assert not set(d3_templates()) & set(d2_templates())
    assert template(D3_FIXTURE_SPEC.template_id).repository_group == (
        D3_FIXTURE_SPEC.repository_group
    )


@pytest.mark.parametrize("spec", D3_TASK_SPECS, ids=lambda spec: spec.template_id)
def test_every_case_leaves_the_canonical_candidate_source_byte_identical(spec: object) -> None:
    """The whole intervention: an equivalent package must encode to the same v2 bytes."""
    baseline = module_source(spec, spec.baseline)  # type: ignore[attr-defined]
    variants = tuple(module_source(spec, body) for body in spec.variants)  # type: ignore[attr-defined]
    expected = [canonical_source_hash(body) for body in variants]

    for case_name in transformations_d3.CASES:
        transformed = transformations_d3.transform(
            case_name,
            module_source=baseline,
            variants=variants,
            visible_test=spec.visible_test,  # type: ignore[attr-defined]
            hidden_test=spec.hidden_test,  # type: ignore[attr-defined]
            issue=spec.issue,  # type: ignore[attr-defined]
        )
        assert [canonical_source_hash(body) for body in transformed.variants] == expected


# ------------------------------------------------------------------ the embedding windows


def test_windows_cover_the_canonical_text_without_exceeding_the_model_window() -> None:
    """W2-F1: the frozen model reads 256 word-pieces, so the whole input has to arrive."""
    source = "def widen(edge, span):\n    total = edge + span\n    return total\n"
    windows = canonical_embedding_windows(source)
    canonical = canonical_source_bytes(source).decode()

    assert "".join(windows) == canonical
    assert len(windows) > 1
    assert all(len(window) <= CANONICAL_EMBEDDING_WINDOW_CHARACTERS for window in windows)


def test_pooling_returns_a_unit_vector_and_refuses_an_empty_set() -> None:
    pooled = pool_canonical_embedding([[1.0, 0.0], [0.0, 1.0]])
    assert pytest.approx(sum(value * value for value in pooled), abs=1e-9) == 1.0
    assert all(-1.0 <= value <= 1.0 for value in pooled)
    with pytest.raises(ValueError, match="at least one window"):
        pool_canonical_embedding([])


# ------------------------------------------------------------------ the D3 seal


def test_the_seal_carries_the_four_reused_roles_by_hash() -> None:
    d2 = seal_corpus()
    bundle = seal_d3_corpus()

    for partition in _REUSED:
        assert bundle.catalogues[partition].content_hash == d2.catalogues[partition].content_hash
    assert (
        bundle.catalogues[CorrectionPartition.CALIBRATION].content_hash
        != d2.catalogues[CorrectionPartition.CALIBRATION].content_hash
    )


def test_the_seal_counts_and_disjointness_are_exact() -> None:
    bundle = seal_d3_corpus()
    seal = bundle.seal

    assert (seal.fitting_groups, seal.calibration_groups) == (50, 20)
    assert (seal.final_a_groups, seal.final_b_groups, seal.canary_groups) == (30, 30, 5)
    assert seal.retrieval_source_groups >= 60
    assert seal.calibration_cases == NOMINAL_DECISIONS_PER_STAGE
    assert seal.promotion_cases == 6 * (seal.final_a_groups + seal.final_b_groups)
    assert seal.outcomes_present is False

    roles = [bundle.groups_of(partition) for partition in CorrectionPartition]
    roles.append(bundle.retrieval_groups)
    for index, left in enumerate(roles):
        for right in roles[index + 1 :]:
            assert not left & right


def test_the_seal_is_deterministic() -> None:
    assert seal_d3_corpus().seal.content_hash == seal_d3_corpus().seal.content_hash


def test_every_sealed_case_binds_its_stage_group_name_and_seed() -> None:
    bundle = seal_d3_corpus()
    cases = bundle.calibration_transformations.cases

    assert {case.case_name for case in cases} == set(transformations_d3.CASES)
    assert len({case.case_id for case in cases}) == len(cases)
    assert all(len(case.candidate_ids) == 4 for case in cases)
    assert bundle.calibration_transformations.fitted is False
    assert bundle.promotion_transformations.fitted is False


# ------------------------------------------------------------------ the baseline ladder


def test_the_ladder_dispatches_its_columns_on_the_encoder() -> None:
    """v2 removed the cosine channel, so the rung that ordered by it cannot be scored."""
    v1 = eligible_rungs(ENCODER_VERSION)
    v2 = eligible_rungs(ENCODER_VERSION_V2)

    assert FROZEN_MINILM_COSINE in v1
    assert FROZEN_MINILM_COSINE not in v2
    assert set(v2) < set(v1)
    assert V2_COSINE_RUNG_INELIGIBLE != GRAPH_RUNG_INELIGIBLE
