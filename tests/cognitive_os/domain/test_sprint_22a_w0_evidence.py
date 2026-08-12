"""S22A-W0: the wave's four sealed records stay sealed, and the frozen contracts stay frozen.

The `--check` paths of `decisions_22a.py` and `pre_registration_22a.py` are the validators that
make W0's publication mean something for the rest of the sprint: the descriptor schema cannot
be widened to admit a pilot, a compatibility hash cannot be edited into agreement, and a pilot
id cannot be substituted after a registration goes badly. Validators that only ever run by hand
rot, so they run here — every wave of this sprint executes them without choosing to.

Every assertion below names the record it reads (W4-F1) and none re-globs a directory or reads
a clock (W2-F1/F2), so a failure here means something moved rather than that time passed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"

W0_RECORDS = (
    "sprint-22a-domain-survey.json",
    "sprint-22a-baseline.json",
    "sprint-22a-decisions.json",
    "sprint-22a-contracts.json",
    "sprint-22a-pre-registration.json",
)


def _load_script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / f"scripts/{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


baseline = _load_script("baseline_22a")
decisions_script = _load_script("decisions_22a")
pre_registration = _load_script("pre_registration_22a")


def _record(name: str) -> dict[str, Any]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", W0_RECORDS)
def test_every_w0_record_is_present(name: str) -> None:
    assert (EVIDENCE / name).is_file()


def test_the_baseline_seal_is_over_its_own_content() -> None:
    """Verified offline: the record is read, never the remote it was taken from."""
    record = _record("sprint-22a-baseline.json")
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    assert baseline._sha256(baseline._canonical(body)) == record["integrity_content_hash"]


def test_the_baseline_froze_every_predecessor_store_and_found_no_unexplained_drift() -> None:
    record = _record("sprint-22a-baseline.json")
    assert len(record["predecessor_artifact_stores"]) == len(baseline.PREDECESSOR_STORES)
    assert record["unexplained_drift"] == []
    assert record["predecessor_stores_match_expectation"] is True
    assert record["stores_written_to_by_w0"] == []
    assert set(record["stale_expectations"]) <= set(record["first_observations"])


def test_the_baseline_verified_the_predecessor_release_from_live_handles() -> None:
    release = _record("sprint-22a-baseline.json")["d7_release"]
    assert release["tag"] == "sprint-21-learning-baseline"
    assert release["tag_type"] == "tag"
    assert release["local_and_remote_agree"] is True
    assert release["remote_peeled_commit"] == "3f5d7379caf85290da45885e22138506211bee2e"


def test_the_decisions_record_still_checks() -> None:
    decisions_script._check()


def test_both_governance_decisions_were_taken_and_neither_moved_a_threshold() -> None:
    record = _record("sprint-22a-decisions.json")
    assert set(record["decisions"]) == {"rung_as_product", "steady_state_door"}
    assert record["thresholds_changed"]["count"] == 0
    assert record["measured_values"] == 0
    rung = record["decisions"]["rung_as_product"]
    assert rung["released_runtime_changed_by_this_decision"] is False
    assert rung["blocks_no_item_in_this_plan"] is True
    assert record["decisions"]["steady_state_door"]["canary_routing_changed_by_22a"] is False


def test_the_rung_decision_is_priced_from_the_sealed_d7_records() -> None:
    """Both branches priced by recomputation from sealed evidence, not by adjective."""
    prices = _record("sprint-22a-decisions.json")["decisions"]["rung_as_product"]["prices"]
    assert prices["released_runtime_fallback_rung"] == "lexical_similarity"
    assert prices["fallback_codes"] == 17
    for corpus, body in prices["per_corpus"].items():
        assert float(body["containment_rung_rate"]) > float(body["released_fallback_rate"]), corpus


def test_the_pre_registration_still_checks() -> None:
    """The frozen schema, the compat hashes and the W0 children, all re-verified."""
    pre_registration._check()


def test_the_publication_carries_no_measured_value() -> None:
    record = _record("sprint-22a-pre-registration.json")
    assert record["measured_values"] == 0
    assert not any(record["chronology"].values())
    assert record["outcome_tags"] == {
        "pass": "sprint-22a-domain-baseline",
        "stop": "sprint-22a-evidence-baseline",
    }


def test_the_frozen_pilot_ids_are_the_two_the_backlog_named() -> None:
    contracts = _record("sprint-22a-contracts.json")["contracts"]
    assert contracts["pilot_domains"]["domain_ids"] == [
        "engineering.mechanics",
        "science.chemistry",
    ]
    assert contracts["pilot_domains"]["may_be_substituted_after_a_failure"] is False


def test_the_enum_reading_forbids_a_fifth_member_and_a_grown_coupling() -> None:
    reading = _record("sprint-22a-contracts.json")["contracts"]["enum_reading"]
    assert reading["new_enum_member_may_be_added"] is False
    assert reading["coupling_may_grow"] is False
    assert reading["coupling_at_publication"] == {
        "modules": 9,
        "references": 57,
        "counted_from": reading["coupling_at_publication"]["counted_from"],
    }


def test_migration_0016_is_recorded_as_a_refusal() -> None:
    storage = _record("sprint-22a-contracts.json")["contracts"]["storage_without_a_schema"]
    assert storage["migration_head"] == "0015"
    assert storage["planned_22a_migration"] is None
    assert storage["core_controller_changed"] is False
