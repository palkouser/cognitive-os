"""S22B-W2: the retrieval envelope is complete, traceable, and able to fail.

W2 decides three of the five exit criteria, so the questions this file asks are the ones a
reader of those three numbers would ask if they were suspicious:

*Was every cell actually measured?* Seven shapes over two datasets is fourteen cells at five
hundred probes each. 22A W4-F1 is the rule that a coverage word must be counted, and this
counts it — a shape quietly skipped on one dataset is a failure here.

*Does each exit reading come from where it says it comes from?* Every reading names a record
and a field path. This re-reads that field out of the source record and compares. A summary
that has drifted from its sources is exactly the failure the pre-registration exists to
prevent, and it is invisible unless something recomputes.

*Can the envelope's own check notice a change?* 22A W4-F2. The check is fed a copy whose
sources have been tampered with, and has to refuse it.

*Was the frozen graph recipe still frozen when it was measured?* §2.3's last bullet forbids
tuning a pre-registered configuration once a number exists, and the sprint's hardest number is
the one with the most incentive to be tuned. The measured record's limits hash is compared
against the pre-registration's.

*Does a met number say what answered it?* The filtered-ANN exit is met, and W2-F2 found that
the planner answers it with a sequential scan rather than the index. A record that reported
only the latency would be true and misleading.

`recorded_at` and the seal over it are excluded from every reproduction comparison, so nothing
here fails because a clock moved.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
ASSEMBLER = REPOSITORY / "scripts/envelope_22b.py"

ENVELOPE = EVIDENCE / "sprint-22b-w2-envelope.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22b-pre-registration.json"
#: The frozen contracts live in their own record; the pre-registration binds it by hash, which
#: is asserted below rather than assumed — reading the contracts without checking that the
#: publication still points at them would compare against a file nobody promised.
CONTRACTS = EVIDENCE / "sprint-22b-contracts.json"

DATASETS = ("clustered", "uniform")

#: Written out rather than read from the module, so this compares the record against the plan
#: instead of against the code that wrote it.
W2_SHAPES = {
    "ann",
    "bounded_graph_assisted",
    "exact_vector",
    "filtered_ann",
    "hybrid",
    "stale_item",
    "temporal",
}

MEASURED_PROBES = 500
WARMUP_PROBES = 100


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _assembler() -> Any:
    spec = importlib.util.spec_from_file_location("envelope_22b_under_test", ASSEMBLER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source(kind: str, dataset: str) -> dict[str, Any]:
    return _load(EVIDENCE / f"sprint-22b-w2-{kind}-{dataset}.json")


def test_the_w2_envelope_seal_is_over_its_own_content() -> None:
    document = _load(ENVELOPE)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    assert _sha256(_canonical(body)) == document["integrity_content_hash"]


def test_every_shape_was_measured_on_every_dataset_at_the_pre_registered_count() -> None:
    """22A W4-F1: fourteen cells, five hundred probes each, counted rather than claimed."""
    coverage = _load(ENVELOPE)["coverage"]
    assert set(coverage["shapes_pre_registered"]) == W2_SHAPES
    assert coverage["cells_required"] == len(W2_SHAPES) * len(DATASETS) == 14
    assert coverage["cells_measured"] == coverage["cells_required"]
    assert coverage["missing_cells"] == []
    assert coverage["complete"] is True
    for dataset in DATASETS:
        for shape in W2_SHAPES:
            assert coverage["matrix"][dataset][shape] == MEASURED_PROBES, f"{dataset}/{shape}"
    assert coverage["measured_probes_total"] == 14 * MEASURED_PROBES


@pytest.mark.parametrize("dataset", DATASETS)
def test_the_warm_protocol_restarted_the_database_and_discarded_its_warmup(dataset: str) -> None:
    """§2.2b, taken literally: a restart, then a hundred discarded probes, then the measured."""
    record = _source("envelope", dataset)
    assert record["restart"]["restarted"] is True
    assert record["restart"]["shared_buffers_start_empty"] is True
    # The one thing a container restart does not do, named on the record rather than assumed.
    assert record["restart"]["host_page_cache_dropped"] is False
    assert record["warmup_per_shape"] == WARMUP_PROBES
    for shape, cell in record["measured"].items():
        assert cell["warmup_probes_discarded"] == WARMUP_PROBES, shape
        assert cell["probes"] == MEASURED_PROBES, shape
        cold = cell.get("cold_first_probe_ms") or cell.get("cold_first_probe")
        assert cold is not None, f"{shape} kept no cold probe"


def test_each_exit_reading_traces_to_the_field_it_names() -> None:
    """A reading nobody can trace is a reading that can drift from what was measured."""
    readings = _load(ENVELOPE)["exit_readings"]
    assert set(readings) == {
        "recall_at_10",
        "warm_filtered_ann_p95_ms",
        "bounded_graph_assisted_p95_ms",
    }
    for name, reading in readings.items():
        source, _, field = reading["read_from"].partition("#")
        record = _load(EVIDENCE / source)
        value: Any = record
        for part in field.split("."):
            value = value[part]
        assert value == reading["measured"], name
        if reading["comparison"] == ">=":
            assert reading["met"] is (reading["measured"] >= reading["threshold"])
        else:
            assert reading["met"] is (reading["measured"] <= reading["threshold"])


def test_the_exit_thresholds_are_the_pre_registered_ones() -> None:
    """22B may not move an exit number, so the record's thresholds are compared to the seal."""
    assert _load(PRE_REGISTRATION)["contracts_sha256"] == _sha256(CONTRACTS.read_bytes())
    criteria = _load(CONTRACTS)["contracts"]["exit_criteria"]["criteria"]
    readings = _load(ENVELOPE)["exit_readings"]
    for name, reading in readings.items():
        assert reading["threshold"] == criteria[name]["threshold"], name
        assert reading["comparison"] == criteria[name]["comparison"], name


def test_the_envelope_check_can_notice_a_change(tmp_path: Path, monkeypatch: Any) -> None:
    """22A W4-F2, applied to this wave's summary rather than to the host record."""
    module = _assembler()
    for path in EVIDENCE.glob("sprint-22b-w2-*.json"):
        shutil.copy(path, tmp_path / path.name)
    monkeypatch.setattr(module, "EVIDENCE", tmp_path)
    monkeypatch.setattr(module, "OUTPUT", tmp_path / ENVELOPE.name)

    # Untampered, the copy still reproduces: the probe below fails for the right reason.
    module._check()

    victim = tmp_path / "sprint-22b-w2-envelope-clustered.json"
    tampered = _load(victim)
    tampered["measured"]["bounded_graph_assisted"]["p95_ms"] += 1.0
    victim.write_text(json.dumps(tampered, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit) as raised:
        module._check()
    assert "no longer reproduces" in str(raised.value)


def test_the_bounded_graph_recipe_was_not_tuned_against_its_exit() -> None:
    """§2.3: the configuration is frozen, and the hardest number is the likeliest to be tuned."""
    assert _load(PRE_REGISTRATION)["contracts_sha256"] == _sha256(CONTRACTS.read_bytes())
    sealed = _load(CONTRACTS)["contracts"]["bounded_graph_configuration"]["limits_hash"]
    for dataset in DATASETS:
        graph = _source("envelope", dataset)["measured"]["bounded_graph_assisted"]
        assert graph["configuration"]["limits_hash"] == sealed, dataset
        assert graph["configuration"]["may_be_tuned_after_a_number_exists"] is False
        assert graph["configuration"]["shortlist_width"] == 20
        assert graph["configuration"]["per_pair_timeout_ms"] == 250


@pytest.mark.parametrize("dataset", DATASETS)
def test_the_graph_record_reports_its_cutoffs_beside_its_p95(dataset: str) -> None:
    """`the_cutoff_trap`: a budget cutoff answers less, faster. So the count travels with the p95.

    D1 reached 1 788.9 ms with sixty queries cut off at its budget. A 22B p95 met with a rising
    cutoff count is a miss reported as one, which is only checkable if the number is on the
    record at all.
    """
    graph = _source("envelope", dataset)["measured"]["bounded_graph_assisted"]
    assert "budget_cutoffs" in graph
    assert "per_pair_timeouts" in graph
    assert graph["mean_results_returned"] is not None
    assert graph["measures_quality"] is False
    assert graph["ann_shortlist_leg"]["probes"] == graph["probes"] == MEASURED_PROBES
    assert graph["graph_expansion_leg"]["probes"] == MEASURED_PROBES


def test_the_filtered_ann_reading_says_which_plan_answered_it() -> None:
    """W2-F2. The exit is met; the record still has to say what met it.

    `probe_corpus` reads the plan back rather than trusting it, so `index_scan_confirmed` is a
    fact about the executed statement. When it is false the shape is a filtered scan and the
    record carries a limitation saying so — the diagnostic pass beside it measures what the
    index would have done, and reads no exit.
    """
    for dataset in DATASETS:
        record = _source("envelope", dataset)
        filtered = record["measured"]["filtered_ann"]
        assert "index_scan_confirmed" in filtered
        assert filtered["sequential_scan_disabled"] is False
        if filtered["index_scan_confirmed"] is False:
            assert "not approximate-retrieval numbers" in filtered["limitation"]
            forced = record["diagnostics"]["filtered_ann_index_forced"]
            assert forced["sequential_scan_disabled"] is True
            assert forced["probes"] == MEASURED_PROBES
        assert record["diagnostics_read_no_exit"] is True


def test_the_uniform_dataset_closes_nothing() -> None:
    """§2.2a: measured in full, read by no exit — including when it is the friendlier number."""
    uniform = _source("recall", "uniform")
    assert uniform["reads_the_recall_exit"] is False
    assert uniform["meets_exit"] is False
    readings = _load(ENVELOPE)["exit_readings"]
    assert readings["recall_at_10"]["dataset"] == "clustered"
    assert readings["recall_at_10"]["decided_by_dataset"] == "clustered"
    assert _load(ENVELOPE)["recall"]["uniform"]["recall_at_k"] is not None


def test_a_latency_exit_is_met_only_where_it_is_met_on_both_datasets() -> None:
    """No reading fixed a dataset for the latency exits, so the worse one decides.

    Choosing the friendlier dataset after the numbers exist is precisely what §2.2 freezes
    readings to prevent, and the two latency exits are the place that choice was still open.
    """
    for name in ("warm_filtered_ann_p95_ms", "bounded_graph_assisted_p95_ms"):
        reading = _load(ENVELOPE)["exit_readings"][name]
        assert set(reading["per_dataset"]) == set(DATASETS), name
        assert reading["measured"] == max(reading["per_dataset"].values()), name
        assert reading["met"] is (reading["measured"] <= reading["threshold"]), name


def test_the_recall_ground_truth_was_never_sampled() -> None:
    """§4: an exact scan per probe is the one measurement nobody may shortcut."""
    for dataset in DATASETS:
        recall = _source("recall", dataset)
        assert recall["ground_truth"] == "exact scan per probe, never sampled"
        assert recall["probes"] == MEASURED_PROBES
        assert recall["k"] == 10


def test_the_host_memory_constraint_is_sealed_beside_the_numbers() -> None:
    """§1.4: one host is one host, and the part of it that decides an ANN latency is stated.

    The reference host runs the released compose file's PostgreSQL defaults, so the index is
    many times the buffer pool. 22B seals that arithmetic rather than raising the setting: the
    host record makes a settings change a supersession, and §2.3 forbids tuning after a number.
    """
    for dataset in DATASETS:
        memory = _source("envelope", dataset)["server_memory"]
        assert memory["not_tuned_by_22b"] is True
        assert memory["index_over_shared_buffers"] > 1
        assert memory["index_fits_in_host_memory"] is True
        assert memory["shared_buffers_bytes"] > 0
        # W2-F1: the settings block renders units it can be read back from.
        assert memory["settings"]["shared_buffers"].endswith("8kB")
        assert " " in memory["settings"]["shared_buffers"]


def test_the_envelope_binds_the_authority_it_was_measured_under() -> None:
    document = _load(ENVELOPE)
    binds = document["binds"]
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert binds["host_id"] == "cogos-reference-host-2"
    for kind in ("envelope", "recall"):
        for dataset in DATASETS:
            path = EVIDENCE / f"sprint-22b-w2-{kind}-{dataset}.json"
            assert binds["sources"][kind][dataset] == _sha256(path.read_bytes())


def test_the_record_names_the_modes_driven_inside_the_shapes() -> None:
    """W2's row: name every mode covered — including the two that are not envelope rows."""
    modes = _load(ENVELOPE)["supporting_modes_driven"]
    assert set(modes) == {"metadata", "text"}
    for name, entry in modes.items():
        assert entry["an_envelope_row"] is False, name
        assert set(entry["driven_by"]) <= W2_SHAPES, name
