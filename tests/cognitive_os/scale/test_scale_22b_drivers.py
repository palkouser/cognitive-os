"""S22B-W0: the 22B measurement drivers are deterministic, enumerated and able to fail.

Sprint 22B's drivers are not features, so they are not tested like features. What matters
about a measurement driver is narrower and harder:

*It draws the same corpus twice.* A dataset recipe that is reproducible only in prose cannot
be pre-registered. The generators are the released ANN harness's own, so this also asserts
that 22B's corpus is drawn by the function that drew the sealed 10^5 one — the comparison the
whole sprint rests on.

*It is stable across batch boundaries.* W1 generates a million rows in batches, and row `i`
has to be the same row whichever batch produced it, or the corpus depends on a chunk size.

*Its coverage words are counted.* W2 says "seven retrieval shapes"; this asserts the seven by
name (22A W4-F1). The pre-registration's own enumeration check is what caught W0-F8, where
this list had eight entries and was missing the shape the hardest exit reads.

*Its frozen parameters are the plan's.* Shortlist 20 and a 250 ms per-pair budget are §2.2d,
not preferences, and the recall floor reads the clustered dataset and nothing else.

No test here touches a database. The database-facing drivers are exercised by the W0 slice,
whose record `test_sprint_22b_w0_evidence.py` binds.
"""

from __future__ import annotations

import importlib.util
import json
import os
import time
from itertools import islice
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
DRIVERS = REPOSITORY / "scripts/scale_22b.py"

#: The seven shapes W2's row names, written out here rather than derived from the module, so
#: this is a comparison against the plan and not the module agreeing with itself.
W2_SHAPES = {
    "ann",
    "bounded_graph_assisted",
    "exact_vector",
    "filtered_ann",
    "hybrid",
    "stale_item",
    "temporal",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("scale_22b_under_test", DRIVERS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_corpus_rows_are_reproducible() -> None:
    module = _module()
    first = module.corpus_rows("clustered", 32)
    second = module.corpus_rows("clustered", 32)
    assert first == second
    assert len(first) == 32


def test_the_stream_and_the_addressed_rows_are_the_same_corpus() -> None:
    """W1-F1's fix, asserted: one draw order, two entry points, no way to disagree.

    The batched loader streams and the tests address by offset. If those could diverge, a
    million-row corpus would not be the corpus its own reproduction check describes.
    """
    module = _module()
    streamed = list(islice(module.corpus_stream("clustered"), 400))
    assert streamed == module.corpus_rows("clustered", 400)
    assert streamed[350:] == module.corpus_rows("clustered", 50, offset=350)


def test_the_stream_costs_the_same_per_row_wherever_it_is() -> None:
    """W1-F1: the old loader re-drew every prior row, which made a 10^6 load quadratic.

    This asserts the shape of the cost rather than a wall-clock number: pulling the second
    thousand rows from a live stream must not cost meaningfully more than the first, because
    at 10^6 the difference between those two was 46 hours and 6 minutes.
    """
    module = _module()
    stream = module.corpus_stream("clustered")
    first = time.perf_counter()
    list(islice(stream, 1_000))
    first = time.perf_counter() - first
    second = time.perf_counter()
    list(islice(stream, 1_000))
    second = time.perf_counter() - second
    assert second < first * 3


def test_each_dataset_gets_its_own_corpus_table() -> None:
    """W1-F3: one shared table meant the second 10^6 corpus dropped the first."""
    module = _module()
    names = {dataset: module.corpus_table(dataset) for dataset in module.DATASETS}
    assert len(set(names.values())) == len(names)
    assert all(name.startswith(module.CORPUS_TABLE) for name in names.values())


def test_the_artifact_source_is_outside_the_frozen_recipes() -> None:
    """W1-D1: where the bytes are copied from is not part of what a restore must reproduce."""
    module = _module()
    assert "source_path" not in module.LIVE_LEARNED_ARTIFACT
    assert module.LIVE_LEARNED_ARTIFACT_SOURCE["path"].endswith(
        module.LIVE_LEARNED_ARTIFACT["artifact_hash"]
    )
    assert "live_learned_artifact_source" not in module.RECIPES


def test_corpus_rows_are_stable_across_batch_boundaries() -> None:
    """Row `i` is the same row whether it arrived in one batch or three.

    W1 loads a million rows in batches. If the row depended on the batch size, the corpus
    would depend on how the loader was invoked and the recipe would not be a recipe.
    """
    module = _module()
    whole = module.corpus_rows("clustered", 24)
    pieces = (
        module.corpus_rows("clustered", 8, offset=0)
        + module.corpus_rows("clustered", 8, offset=8)
        + module.corpus_rows("clustered", 8, offset=16)
    )
    assert whole == pieces


def test_both_datasets_draw_different_geometries() -> None:
    module = _module()
    clustered = module.corpus_rows("clustered", 8)
    uniform = module.corpus_rows("uniform", 8)
    assert [row[0] for row in clustered] != [row[0] for row in uniform]
    assert module.corpus_centres("clustered") and not module.corpus_centres("uniform")


def test_probes_are_reproducible_and_reuse_the_corpus_centres() -> None:
    module = _module()
    assert module.probe_literals("clustered", 16) == module.probe_literals("clustered", 16)
    # A uniform probe against a clustered corpus lands in empty space, so the probe recipe
    # must be drawn from the corpus distribution rather than from a convenient one.
    assert module.probe_literals("clustered", 4) != module.probe_literals("uniform", 4)


def test_the_corpus_metadata_matches_the_frozen_selectivity() -> None:
    """Ten scopes, one selected: the frozen tenth of the corpus the 300 ms exit reads."""
    module = _module()
    rows = module.corpus_rows("clustered", 1_000)
    scopes = {row[1] for row in rows}
    assert len(scopes) == module.FILTER_PREDICATE["scopes_in_corpus"] == 10
    selected = [row for row in rows if row[1] == "scope-00"]
    assert abs(len(selected) / len(rows) - module.FILTER_PREDICATE["target_selectivity"]) < 0.01


def test_w2_drives_exactly_seven_shapes() -> None:
    """22A W4-F1: count what a coverage word covers, do not read it."""
    module = _module()
    assert set(module.QUERY_SHAPES) == W2_SHAPES
    assert len(module.QUERY_SHAPES) == 7


def test_supporting_modes_are_named_rather_than_hidden() -> None:
    """The released modes the drivers use that are not envelope rows are still enumerated."""
    module = _module()
    assert set(module.SUPPORTING_MODES) == {"metadata", "text"}
    used_by = {shape for entry in module.SUPPORTING_MODES.values() for shape in entry["used_by"]}
    assert used_by <= W2_SHAPES


def test_only_the_clustered_dataset_reads_the_recall_exit() -> None:
    """§2.2a, frozen: the uniform dataset is the adversarial bound and closes nothing."""
    module = _module()
    reading = {name: recipe["reads_the_recall_exit"] for name, recipe in module.DATASETS.items()}
    assert reading == {"clustered": True, "uniform": False}


def test_the_bounded_graph_configuration_is_the_plan_s() -> None:
    """§2.2d's parameters, asserted against the plan rather than against the module."""
    module = _module()
    limits = module.BOUNDED_GRAPH_LIMITS
    assert limits.vector_shortlist == 20
    assert limits.per_pair_ged_timeout_ms == 250
    assert limits.returned_results == 10
    assert limits.path_depth <= 32
    configuration = module.bounded_graph_configuration()
    assert configuration["exit_ms"] == 500
    assert configuration["only_prior_measurement_ms"] == 1788.9
    assert configuration["may_be_tuned_after_a_number_exists"] is False


def test_the_probe_protocol_is_ten_times_the_1e5_envelope() -> None:
    module = _module()
    assert module.PROBE_PROTOCOL["measured_probes"] == 500
    assert module.PROBE_PROTOCOL["warmup_probes"] == 100


def test_the_recipes_hash_is_a_function_of_the_recipes() -> None:
    """A hash that does not move when a recipe moves would bind nothing."""
    module = _module()
    before = module.recipes_hash()
    assert before == module.recipes_hash()
    original = module.DATASETS["clustered"]["cluster_spread"]
    module.DATASETS["clustered"]["cluster_spread"] = original + 0.01
    module.RECIPES["datasets"] = module.DATASETS
    try:
        assert module.recipes_hash() != before
    finally:
        module.DATASETS["clustered"]["cluster_spread"] = original


def test_the_temporal_shape_declares_that_it_leaves_the_governed_path() -> None:
    """W0-F2, kept visible: the one shape that is not a released MemoryQuery says so."""
    module = _module()
    temporal = module.QUERY_SHAPES["temporal"]
    assert "include_historical" in temporal["composition"]
    assert temporal["reads_an_exit"] is False


def test_the_restore_checklist_names_the_live_learned_artifact() -> None:
    module = _module()
    assert len(module.RESTORE_CHECKLIST) == 4
    assert module.LIVE_LEARNED_ARTIFACT["artifact_hash"].startswith("afbdb7c0")


def test_the_envelope_order_covers_every_shape_and_schedules_the_graph_first() -> None:
    """§3.2: "Schedule it first inside W2." An ordering is a schedule, so it is asserted."""
    module = _module()
    assert set(module.ENVELOPE_ORDER) == W2_SHAPES
    assert len(module.ENVELOPE_ORDER) == len(W2_SHAPES)
    assert module.ENVELOPE_ORDER[0] == "bounded_graph_assisted"
    assert (
        set(module.CORPUS_SHAPES) | set(module.GOVERNED_SHAPES) | {"bounded_graph_assisted"}
        == W2_SHAPES
    )


def test_the_graph_pool_is_outside_the_frozen_recipes() -> None:
    """The same rule `LIVE_LEARNED_ARTIFACT_SOURCE` follows: a pointer is not a reading.

    §2.2d freezes the bounded configuration. Which released graph set the pairs are read out
    of is an operational detail, and putting it in `RECIPES` would move the recipes hash the
    pre-registration binds without any reading having changed.
    """
    module = _module()
    assert module.BOUNDED_GRAPH_POOL["pairs"] == 80
    assert "d1" in module.BOUNDED_GRAPH_POOL["graph_set_id"]
    serialised = _canonical(module.RECIPES)
    assert b"BOUNDED_GRAPH_POOL" not in serialised
    assert module.BOUNDED_GRAPH_POOL["artifact_root"].encode() not in serialised


def test_the_warm_protocol_refuses_to_guess_the_container() -> None:
    """§2.2b's restart is a real restart, and the thing it restarts is never inferred."""
    module = _module()
    for name in ("COGOS_POSTGRES_TOOL_CONTAINER", "COGOS_DATABASE_ADMIN_URL"):
        os.environ.pop(name, None)
    with pytest.raises(SystemExit) as raised:
        module.restart_postgres()
    assert "COGOS_POSTGRES_TOOL_CONTAINER" in str(raised.value)
