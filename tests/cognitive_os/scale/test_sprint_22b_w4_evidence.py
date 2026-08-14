"""S22B-W4: five exit criteria read once, and a restore that had to leave them alone.

The release wave adds no measurement of its own except one: the same envelope, re-measured on
the *restored* store. So this file asks the two questions a release record has to survive:

*Is every exit reading traceable to a sealed measurement?* Each of the five names a record and
a field. This re-reads that field and compares. A release record that had drifted from its
sources would be the most expensive kind of wrong.

*Did the restore change the envelope?* §3's W4 row calls that a finding. The restored numbers
are asserted to exist, to have been measured on the restored database rather than the source
one, and to still clear their thresholds — and the record reports the deltas whatever they are.

No threshold may have moved. That is asserted against the frozen contracts, not against this
file's own idea of the numbers.
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
ASSEMBLER = REPOSITORY / "scripts/exit_criteria_22b.py"

EXIT_CRITERIA = EVIDENCE / "sprint-22b-exit-criteria.json"
CONTRACTS = EVIDENCE / "sprint-22b-contracts.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22b-pre-registration.json"

RESTORED_DATABASE = "cognitive_os_s22b_restore_test"
SOURCE_DATABASE = "cognitive_os_s22b_test"

#: The five, written out rather than derived, so this compares the record against the sprint's
#: allocation instead of against the code that assembled it.
FIVE = {
    "governed_ingest_items_per_second",
    "recall_at_10",
    "warm_filtered_ann_p95_ms",
    "bounded_graph_assisted_p95_ms",
    "restore_reproduces",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _assembler() -> Any:
    spec = importlib.util.spec_from_file_location("exit_criteria_22b_under_test", ASSEMBLER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_exit_criteria_seal_is_over_its_own_content() -> None:
    document = _load(EXIT_CRITERIA)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    assert _sha256(_canonical(body)) == document["integrity_content_hash"]


def test_all_five_criteria_are_read_and_all_five_are_met() -> None:
    document = _load(EXIT_CRITERIA)
    assert set(document["criteria"]) == FIVE
    assert document["criteria_total"] == 5
    assert document["criteria_met"] == 5
    assert document["all_met"] is True
    assert document["outcome"] == "pass"


def test_each_criterion_traces_to_the_field_it_names() -> None:
    """A release number nobody can trace is a release number that can drift."""
    for name, reading in _load(EXIT_CRITERIA)["criteria"].items():
        source, _, field = reading["read_from"].partition("#")
        value: Any = _load(EVIDENCE / source)
        for part in field.split("."):
            value = value[part]
        assert value == reading["measured"], name


def test_no_threshold_moved() -> None:
    """22B may not move its own exit numbers, and the frozen contracts are the authority."""
    document = _load(EXIT_CRITERIA)
    assert document["contracts_sha256"] == _sha256(CONTRACTS.read_bytes())
    assert _load(PRE_REGISTRATION)["contracts_sha256"] == _sha256(CONTRACTS.read_bytes())
    frozen = _load(CONTRACTS)["contracts"]["exit_criteria"]["criteria"]
    assert set(frozen) == FIVE
    for name, reading in document["criteria"].items():
        assert reading["threshold"] == frozen[name]["threshold"], name
        assert reading["comparison"] == frozen[name]["comparison"], name
    assert document["thresholds_moved_by_22b"] == 0


def test_the_restore_changed_the_envelope_and_the_record_says_so() -> None:
    """§3's W4 row: a restore that changes the envelope is a finding. It changed it.

    **recall@10 falls from 0.9636 on the source store to 0.9410 on the restored one — below the
    0.95 floor.** The exit criterion itself is decided on the source measurement under the frozen
    reading and is met; this is the separate W4 deliverable, and it came back a finding.

    What the restore is responsible for is decided by `sprint-22b-w4-attribution.json`, not by
    this comparison: two things happened between W2's envelope and W4's, and the latency numbers
    here contain both. See `test_the_latency_deltas_are_not_all_the_restores_doing`.

    Asserted as measured, not as hoped. A future release that made the restored number clear the
    floor would fail this test, which is the correct way for it to fail: the claim being pinned
    here is "the sprint reported this honestly", and it must break when the world changes.
    """
    document = _load(EXIT_CRITERIA)
    post = document["post_restore"]
    assert set(post) == {
        "recall_at_10",
        "warm_filtered_ann_p95_ms",
        "bounded_graph_assisted_p95_ms",
    }
    for name, entry in post.items():
        assert entry["restored_per_dataset"], name
        assert entry["delta"] is not None, name

    # The two latency exits survive the restore; the recall floor does not.
    assert post["warm_filtered_ann_p95_ms"]["restored_still_meets_the_threshold"] is True
    assert post["bounded_graph_assisted_p95_ms"]["restored_still_meets_the_threshold"] is True
    assert post["recall_at_10"]["restored_still_meets_the_threshold"] is False
    assert post["recall_at_10"]["restored"] < post["recall_at_10"]["threshold"]
    assert document["post_restore_all_still_met"] is False


def test_the_finding_did_not_leak_into_the_exit_verdict() -> None:
    """The five criteria are decided on the source measurements, and all five are met.

    Keeping these apart is the whole point. §2.2e defines what a restore must reproduce — exact
    counts, artifact hashes, the queried active view, the live learned artifact's bytes — and W3
    met every item of it. The retrieval envelope is not on that checklist; re-measuring it is a
    separate W4 deliverable whose deviation §3 calls a finding. Reporting the finding as an exit
    miss would be as dishonest as hiding it.
    """
    document = _load(EXIT_CRITERIA)
    assert document["criteria"]["restore_reproduces"]["met"] is True
    assert document["all_met"] is True
    assert document["post_restore_all_still_met"] is False
    assert document["outcome"] == "pass"


def test_the_restored_numbers_were_measured_on_the_restored_store() -> None:
    """Two records that differ only in their numbers cannot be told apart. These say which."""
    for entry in _load(EXIT_CRITERIA)["post_restore"].values():
        assert entry["measured_on"] == [RESTORED_DATABASE]
    for name in ("envelope-clustered", "envelope-uniform", "recall-clustered", "recall-uniform"):
        restored = _load(EVIDENCE / f"sprint-22b-w4-restored-{name}.json")
        assert restored["database"] == RESTORED_DATABASE, name


def test_the_source_and_restored_records_are_different_measurements() -> None:
    """A re-measurement that quietly re-read the source store would prove nothing."""
    source = _load(EVIDENCE / "sprint-22b-w2-envelope-clustered.json")
    restored = _load(EVIDENCE / "sprint-22b-w4-restored-envelope-clustered.json")
    assert source.get("database", SOURCE_DATABASE) != restored["database"]
    assert source["measured"]["ann"]["p95_ms"] != restored["measured"]["ann"]["p95_ms"]


def test_the_latency_deltas_are_not_all_the_restores_doing() -> None:
    """The wave's first reading was wrong, and the attribution record is why.

    Three of the seven shapes read the **governed** store rather than the corpus, and W3 put
    twenty-five thousand transitions through it between the two envelope measurements.
    `stale_item` returned **zero rows** in W2 — nothing was stale yet — and twenty afterwards. A
    shape that starts finding rows gets slower for a reason that is not a restore.

    So the restore owns exactly one shape: `ann` over the clustered corpus, whose HNSW graph
    `pg_restore` rebuilds. The three governed shapes are *faster* on the restored store than on
    the mutated source, because a restore also compacts what mutation left behind.
    """
    attribution = _load(EVIDENCE / "sprint-22b-w4-attribution.json")
    assert attribution["shapes_attributed_to_the_restore"] == ["ann"]
    assert attribution["shapes_attributed_to_w3_mutations"] == ["hybrid", "stale_item", "temporal"]

    stale = attribution["shapes"]["stale_item"]
    assert stale["rows_returned"]["w2_source"] == 0
    assert stale["rows_returned"]["source_now"] > 0
    assert stale["reads_the_governed_store_not_the_corpus"] is True

    for shape in ("hybrid", "stale_item", "temporal"):
        entry = attribution["shapes"][shape]
        assert entry["reads_the_governed_store_not_the_corpus"] is True
        assert entry["restore_effect_ms"] <= 0, shape

    # Every declared shape is accounted for; an unattributed shape is an unexplained number.
    assert set(attribution["shapes"]) == set(
        _load(EVIDENCE / "sprint-22b-w2-envelope-clustered.json")["shapes_in_the_pre_registration"]
    )


def test_the_restores_own_effect_is_the_rebuilt_clustered_graph() -> None:
    """Both halves of the finding are properties of one index, and the control proves it.

    The source store's clustered recall was re-measured with both stores present and came back
    **bit-identical to W2's sealed 0.9636**, so the drop to 0.9410 is not drift, not the probe
    set, and not two 4 GiB stores sharing one page cache. It is the graph `pg_restore` rebuilt.
    """
    attribution = _load(EVIDENCE / "sprint-22b-w4-attribution.json")
    clustered = attribution["recall"]["clustered"]
    assert clustered["source_is_unchanged_since_w2"] is True
    assert clustered["w3_effect"] == 0.0
    assert clustered["restore_effect"] < 0
    assert attribution["shapes"]["ann"]["restore_effect_is_material"] is True
    assert attribution["shapes"]["ann"]["w3_effect_is_material"] is False
    assert attribution["reads_an_exit_criterion"] is False
    assert attribution["pre_registered"] is False


def test_the_attribution_check_can_notice_a_change(tmp_path: Path, monkeypatch: Any) -> None:
    """22A W4-F2, on the record that decides what the wave's finding is about."""
    path = REPOSITORY / "scripts/attribution_22b.py"
    spec = importlib.util.spec_from_file_location("attribution_22b_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for source in EVIDENCE.glob("sprint-22b-*.json"):
        shutil.copy(source, tmp_path / source.name)
    monkeypatch.setattr(module, "EVIDENCE", tmp_path)
    monkeypatch.setattr(module, "OUTPUT", tmp_path / "sprint-22b-w4-attribution.json")

    module._check()

    victim = tmp_path / "sprint-22b-w4-source-recall-clustered.json"
    tampered = _load(victim)
    tampered["recall_at_k"] = 0.9410
    victim.write_text(json.dumps(tampered, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit) as raised:
        module._check()
    assert "no longer reproduces" in str(raised.value)


def test_a_shape_the_control_never_measured_is_refused(tmp_path: Path, monkeypatch: Any) -> None:
    """An attribution that silently skipped a shape would explain six numbers and hide one."""
    path = REPOSITORY / "scripts/attribution_22b.py"
    spec = importlib.util.spec_from_file_location("attribution_22b_refusal", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for source in EVIDENCE.glob("sprint-22b-*.json"):
        shutil.copy(source, tmp_path / source.name)
    monkeypatch.setattr(module, "EVIDENCE", tmp_path)
    monkeypatch.setattr(module, "SOURCE_NOW", ("sprint-22b-w4-source-envelope-clustered.json",))

    with pytest.raises(SystemExit) as raised:
        module._assemble()
    assert "unattributed" in str(raised.value)


def test_the_exit_criteria_check_can_notice_a_change(tmp_path: Path, monkeypatch: Any) -> None:
    """22A W4-F2, on the record that decides whether the sprint passed."""
    module = _assembler()
    for path in EVIDENCE.glob("sprint-22b-*.json"):
        shutil.copy(path, tmp_path / path.name)
    monkeypatch.setattr(module, "EVIDENCE", tmp_path)
    monkeypatch.setattr(module, "OUTPUT", tmp_path / EXIT_CRITERIA.name)
    monkeypatch.setattr(module, "CONTRACTS", tmp_path / CONTRACTS.name)
    monkeypatch.setattr(module, "PRE_REGISTRATION", tmp_path / PRE_REGISTRATION.name)

    module._check()

    victim = tmp_path / "sprint-22b-w1-governed-ingest.json"
    tampered = _load(victim)
    tampered["items_per_second"] += 1.0
    victim.write_text(json.dumps(tampered, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit) as raised:
        module._check()
    assert "no longer reproduces" in str(raised.value)


def test_a_missed_threshold_would_be_reported_as_a_miss(tmp_path: Path, monkeypatch: Any) -> None:
    """The record must be able to say `typed negative`, or `pass` means nothing.

    §5's stop rule is a real branch, not a rhetorical one: a sprint whose release record can only
    print `pass` has not verified anything. So the ingest number is pushed below its floor in a
    copy and the rebuilt record has to come back failed.
    """
    module = _assembler()
    for path in EVIDENCE.glob("sprint-22b-*.json"):
        shutil.copy(path, tmp_path / path.name)
    monkeypatch.setattr(module, "EVIDENCE", tmp_path)
    monkeypatch.setattr(module, "OUTPUT", tmp_path / EXIT_CRITERIA.name)
    monkeypatch.setattr(module, "CONTRACTS", tmp_path / CONTRACTS.name)
    monkeypatch.setattr(module, "PRE_REGISTRATION", tmp_path / PRE_REGISTRATION.name)

    victim = tmp_path / "sprint-22b-w1-governed-ingest.json"
    tampered = _load(victim)
    tampered["items_per_second"] = 42.0
    victim.write_text(json.dumps(tampered, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    rebuilt = module._assemble()
    assert rebuilt["criteria"]["governed_ingest_items_per_second"]["met"] is False
    assert rebuilt["all_met"] is False
    assert rebuilt["criteria_met"] == 4
    assert rebuilt["outcome"] == "typed negative"
