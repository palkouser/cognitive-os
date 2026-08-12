"""S22B-W0: the four W0 seals reproduce, and both validators can fail.

Every later 22B wave binds these records by hash, so what has to be true of them is that they
*are* what they claim and that the checks over them are not decorative:

*Each seal is over its own content.* Recomputed here from the record's body, never trusted.

*The pre-registration measures nothing.* `measured_values: 0` and a chronology of zeros, in a
sprint whose whole risk is a number arriving before the reading that decides it.

*The reference-host check can notice a change.* 22A W4-F2 cost a wave: a claim about what did
not change must be able to see that it did. The host check is fed a tampered copy here and has
to reject it.

*The slice decided no exit criterion.* W0 tested the drivers over a few hundred rows before
the pre-registration was published, which is only honest if that record cannot be read as a
measurement — so it says so in its own body, and this asserts it.

`recorded_at` and the seal over it are excluded from every reproduction comparison, so no test
here fails because a clock moved (W2-F1/F2).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"

BASELINE = EVIDENCE / "sprint-22b-baseline.json"
HOST = EVIDENCE / "sprint-22b-reference-host.json"
SLICE = EVIDENCE / "sprint-22b-w0-slice.json"
CONTRACTS = EVIDENCE / "sprint-22b-contracts.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22b-pre-registration.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal_reproduces(path: Path) -> bool:
    document = _load(path)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    return _sha256(_canonical(body)) == document["integrity_content_hash"]


def test_every_w0_seal_is_over_its_own_content() -> None:
    for path in (BASELINE, HOST, CONTRACTS, PRE_REGISTRATION):
        assert _seal_reproduces(path), path.name


def test_the_baseline_verified_the_predecessor_release_live() -> None:
    baseline = _load(BASELINE)
    release = baseline["predecessor_release"]
    assert release["tag"] == "sprint-22a-domain-baseline"
    assert release["tag_type"] == "tag"
    assert release["local_and_remote_agree"] is True
    assert release["remote_peeled_commit"] == "291482448114ffed95a975c2b6a0d2be47a6a092"
    assert all(run["conclusion"] == "success" for run in baseline["ci_runs"])
    assert all(run["jobs_successful"] == run["jobs"] for run in baseline["ci_runs"])


def test_neither_22b_outcome_tag_existed_at_the_baseline() -> None:
    absent = _load(BASELINE)["outcome_tags_absent"]
    assert absent == {"sprint-22b-scale-baseline": True, "sprint-22b-evidence-baseline": True}


def test_no_predecessor_store_drifted() -> None:
    baseline = _load(BASELINE)
    assert baseline["unexplained_drift"] == []
    assert baseline["predecessor_stores_match_expectation"] is True
    # 22A's own root is a first observation, for the same reason 22A's W0-F1 named D7's.
    assert baseline["first_observations"] == ["sprint_22a"]


def test_the_migration_head_is_counted_from_the_files() -> None:
    migration = _load(BASELINE)["migration"]
    versions = sorted((REPOSITORY / "infra/postgres/alembic/versions").glob("[0-9]*.py"))
    assert migration["repository_head"] == "0015"
    assert migration["migration_files"] == len(versions)
    assert migration["planned_22b_migration"] is None


def test_the_prior_art_is_bound_by_hash_not_retyped() -> None:
    """The 10^5 envelopes and the one graph latency ever measured, bound to their files."""
    prior = _load(BASELINE)["prior_art"]
    for name, entry in prior.items():
        path = REPOSITORY / entry["path"]
        assert _sha256(path.read_bytes()) == entry["sha256"], name
    assert prior["envelope_1e5_clustered"]["read_by_an_exit_criterion"] is True
    assert prior["envelope_1e5_uniform"]["read_by_an_exit_criterion"] is False
    assert prior["graph_arm_d1_w5a"]["p95_ms"] == 1788.9


def test_the_reference_host_sealed_the_extension_every_ann_number_depends_on() -> None:
    """W0-F1: this was `null`, because the record queried the bootstrap database."""
    host = _load(HOST)
    assert host["invariants"]["postgres"]["extensions"]["vector"]
    assert host["invariants"]["postgres"]["settings"]
    assert host["invariants_hash"] == _sha256(_canonical(host["invariants"]))


def _host_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "host_record_22b_under_test", REPOSITORY / "scripts/host_record_22b.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_reference_host_check_recognises_the_sealed_host() -> None:
    """The same invariants must pass, or the drift test below would prove nothing."""
    module = _host_module()
    sealed = _load(HOST)["invariants"]
    module._invariants = lambda _url: sealed
    module._store_url = lambda: "postgresql://unused"
    module._check()


def test_the_reference_host_check_can_notice_a_change() -> None:
    """22A W4-F2, probed rather than asserted: hand it a different host and it must refuse.

    The comparison is driven directly rather than through a subprocess, so the probe runs
    everywhere the suite runs — including CI, which has no 22B store to measure.
    """
    module = _host_module()
    drifted = json.loads(json.dumps(_load(HOST)["invariants"]))
    drifted["cpu"]["logical_cpus"] += 1
    module._invariants = lambda _url: drifted
    module._store_url = lambda: "postgresql://unused"
    with pytest.raises(SystemExit) as raised:
        module._check()
    assert "drifted" in str(raised.value)


def test_the_pre_registration_measures_nothing() -> None:
    pre = _load(PRE_REGISTRATION)
    assert pre["measured_values"] == 0
    assert not any(pre["chronology"].values())
    assert _load(CONTRACTS)["thresholds_changed"] == {
        "count": 0,
        "amendments_made_by_22b": 0,
    }


def test_the_pre_registration_binds_the_drivers_it_freezes() -> None:
    pre = _load(PRE_REGISTRATION)
    drivers = REPOSITORY / "scripts/scale_22b.py"
    assert pre["drivers_module_sha256"] == _sha256(drivers.read_bytes())
    for name, expected in pre["evidence_children_sha256"].items():
        assert _sha256((EVIDENCE / name).read_bytes()) == expected, name


def test_the_five_exit_numbers_are_carried_verbatim() -> None:
    criteria = _load(CONTRACTS)["contracts"]["exit_criteria"]["criteria"]
    assert criteria["recall_at_10"]["threshold"] == 0.95
    assert criteria["warm_filtered_ann_p95_ms"]["threshold"] == 300
    assert criteria["bounded_graph_assisted_p95_ms"]["threshold"] == 500
    assert criteria["governed_ingest_items_per_second"]["threshold"] == 100
    assert set(criteria) == {
        "recall_at_10",
        "warm_filtered_ann_p95_ms",
        "bounded_graph_assisted_p95_ms",
        "governed_ingest_items_per_second",
        "restore_reproduces",
    }


def test_the_w0_slice_decided_no_exit_criterion() -> None:
    """The slice ran before publication, so it must be unreadable as a measurement."""
    record = _load(SLICE)
    assert record["scale"] == "fixture"
    assert record["decides_no_exit_criterion"] is True
    assert record["corpus_rows"] < 1_000
    assert _load(PRE_REGISTRATION)["why_the_w0_slice_is_not_a_measured_value"]


def test_the_w0_slice_exercised_every_driver() -> None:
    record = _load(SLICE)
    for section in (
        "bulk_load",
        "index",
        "vector_probes",
        "recall",
        "governed_ingest",
        "governed_embed",
        "governed_queries",
        "hybrid",
        "temporal",
        "bloat_before",
        "bloat_after",
        "reindex_with_readers",
        "restore_checklist_shape",
        "bounded_graph_configuration",
    ):
        assert section in record, section


def test_the_bloat_driver_can_notice_bloat() -> None:
    """W0-F5: the statistics view reported zero dead tuples after a fifth of the table went."""
    record = _load(SLICE)
    before, after = record["bloat_before"], record["bloat_after"]
    assert before["source"].startswith("pgstattuple")
    assert after["dead_tuples"] > before["dead_tuples"]
    assert after["live_tuples"] < before["live_tuples"]


def test_the_hybrid_recipe_fused_both_legs() -> None:
    """W0-F6: the vector leg returned nothing until governed items carried embeddings."""
    hybrid = _load(SLICE)["hybrid"]
    assert hybrid["text_results"] > 0
    assert hybrid["vector_results"] > 0
    assert hybrid["fused_results"] >= max(hybrid["text_results"], hybrid["vector_results"])
    assert hybrid["rrf_k"] == 60


def test_the_restore_checklist_can_fail() -> None:
    """Run against a store that never held the artifact, it says so rather than passing."""
    checklist = _load(SLICE)["restore_checklist_shape"]
    assert checklist["active_view_was_queried"] is True
    assert checklist["learned_artifact_pointer_resolved"] is False
    assert len(checklist["checklist"]) == 4


def test_the_ingest_driver_reports_a_rate_per_decile() -> None:
    ingest = _load(SLICE)["governed_ingest"]
    assert ingest["reads_the_ingest_exit"] is True
    assert ingest["exit_threshold_items_per_second"] == 100
    assert len(ingest["per_decile"]) >= 4
    assert ingest["slowest_decile_items_per_second"] is not None


def test_embedding_writes_are_measured_outside_the_ingest_rate() -> None:
    """W0-F6's fix, asserted: folding them in would change what the frozen reading measures."""
    record = _load(SLICE)
    assert record["governed_embed"]["reads_an_exit_criterion"] is False
    assert record["governed_ingest"]["path"].endswith("provenance + event + revision")
