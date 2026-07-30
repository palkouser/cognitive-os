"""S21C3-053: what the frozen retrieval benchmark has to be before anyone measures with it.

None of this needs a model. These are the properties that make a *number* from the benchmark
mean something — enough cases, all six families, relevance that never crosses a group, no
control material in a query, and an identity that a later run can cite.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from cognitive_os.coding import reality_leakage
from cognitive_os.coding.reality_retrieval import (
    RELEVANT_KINDS,
    build_benchmark,
    cross_group_leakage,
    kind_counts,
)
from cognitive_os.coding.reality_retrieval_queries import QUERIES, QUERY_KINDS
from cognitive_os.coding.reality_tasks import available_templates, build_manifest, template

FIXTURE_TIME = datetime(2026, 7, 30, tzinfo=UTC)
FIXTURE_ARTIFACT = UUID("00000000-0000-0000-0000-0000000021c3")


def test_the_benchmark_meets_the_declared_size_and_coverage() -> None:
    benchmark = build_benchmark()

    assert len(benchmark.cases) >= 60
    assert len({case.family for case in benchmark.cases}) == 6
    assert len({document.group for document in benchmark.documents}) == 30


def test_every_query_shape_is_represented() -> None:
    """§S21C3-053 names five; a benchmark missing one measures four."""
    counts = kind_counts(build_benchmark())

    assert set(counts) == set(QUERY_KINDS)
    assert min(counts.values()) >= 1


def test_no_relevant_record_lives_outside_its_query_s_group() -> None:
    """§4.15: zero cross-group leakage, asserted rather than hoped for."""
    assert cross_group_leakage(build_benchmark()) == ()


def test_a_query_never_names_the_record_that_answers_it() -> None:
    """Relevance comes from the kind table, so retargeting it is one visible edit."""
    benchmark = build_benchmark()
    identifiers = {document.document_id for document in benchmark.documents}

    for case in benchmark.cases:
        assert set(case.relevant) <= identifiers
        assert not any(document_id in case.text for document_id in identifiers)
        assert len(case.relevant) == len(RELEVANT_KINDS[case.kind])


def test_no_control_token_appears_in_any_query() -> None:
    """A query carrying a hidden test name would be measuring the answer key."""
    queries = "\n".join(case.text for case in build_benchmark().cases)
    leaks = []
    for template_id in available_templates():
        manifest = build_manifest(
            template_id,
            seed=1,
            hidden_bundle_artifact_id=FIXTURE_ARTIFACT,
            hidden_bundle_hash="0" * 64,
            created_at=FIXTURE_TIME,
        )
        tokens = reality_leakage.control_tokens(manifest, template(template_id))
        leaks.extend(token for token in tokens if token in queries)

    assert leaks == []


def test_the_benchmark_is_the_same_benchmark_on_every_build() -> None:
    """The manifest hash is what a measurement cites. A drifting hash cites nothing."""
    assert build_benchmark().manifest_hash == build_benchmark().manifest_hash


def test_each_task_contributes_two_records_that_answer_different_questions() -> None:
    """One record per task would make any query landing in the right group automatically right."""
    benchmark = build_benchmark()
    kinds = {(document.group, document.kind) for document in benchmark.documents}

    assert len(kinds) == len(benchmark.documents)
    assert {kind for _, kind in kinds} == {"task", "correction"}


def test_every_query_targets_a_task_that_exists() -> None:
    known = set(available_templates())

    assert {template_id for template_id, _, _ in QUERIES} <= known
