"""S21D4-035 and S21D4-036: both campaigns are self-play, label_all, and receipt-resumable.

Four properties, each of which is a way a campaign could look finished and not be:

*Self-play only.* One `REAL_GOVERNED_RUN` row makes the corpus a record of production traffic
that no evaluation may treat as trainable.

*A baseline that passes.* The baseline is the unrepaired body. If the hidden verifier accepts
one, the group's hidden suite does not test what the group says it tests, and the four
candidates were never separable.

*Every candidate labelled.* Under `label_all` nothing may be left unattempted; a stop after the
first acceptance is a different experiment with a different denominator.

*A resume that costs nothing.* Replaying every recorded identity without a container is the
only evidence that a restart mid-campaign would not pay for the work twice.

Both campaigns run the same code over different partitions, so they are checked by the same
assertions over different counts. A second copy of this file with 400 substituted for 320 would
drift the moment one of them changed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus
from cognitive_os.learning.correction_protocol import CorrectionPartition

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
SEALS = EVIDENCE / "sprint-21d4-feature-seals.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"

#: `partition -> (record, groups, candidates)`. The counts are the frozen role sizes, restated
#: here so a campaign that silently ran fewer groups fails rather than passes proportionally.
CAMPAIGNS = {
    "training": (EVIDENCE / "sprint-21d4-self-play-campaign.json", 80, 320),
    "calibration": (EVIDENCE / "sprint-21d4-calibration-campaign.json", 100, 400),
}
PARTITIONS = sorted(CAMPAIGNS)


def _load(partition: str) -> dict[str, Any]:
    return json.loads(CAMPAIGNS[partition][0].read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("partition", PARTITIONS)
def test_the_record_reproduces_its_integrity_hash(partition: str) -> None:
    document = _load(partition)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]


@pytest.mark.parametrize("partition", PARTITIONS)
def test_the_campaign_is_bound_to_the_seal_it_executed_against(partition: str) -> None:
    document = _load(partition)
    sealed = json.loads(SEALS.read_text())
    row = next(item for item in sealed["partitions"] if item["partition"] == partition)
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["feature_seals_sha256"] == _sha256(SEALS.read_bytes())
    assert document["feature_seal_hash"] == row["feature_seal_hash"]
    assert document["feature_seal_reloaded_from_the_artifact_store"] is True
    assert document["campaign_manifest_hash"] == row["campaign_manifest_hash"]
    assert document["final_outcomes_inspected"] is False


@pytest.mark.parametrize("partition", PARTITIONS)
def test_the_whole_partition_ran(partition: str) -> None:
    document = _load(partition)
    _, groups, candidates = CAMPAIGNS[partition]
    catalogue = seal_d4_corpus().catalogues[CorrectionPartition(partition)]
    execution = document["execution"]
    assert document["partition"] == partition
    assert execution["groups"] == len(catalogue.groups) == groups
    assert execution["candidate_runs"] == catalogue.candidate_slots == candidates
    assert execution["baselines"] == groups
    assert execution["containers_started"] == candidates + groups
    assert execution["unique_outcomes"] == candidates
    assert execution["duplicates_excluded"] == 0


@pytest.mark.parametrize("partition", PARTITIONS)
def test_every_candidate_was_labelled_under_label_all(partition: str) -> None:
    document = _load(partition)
    _, groups, candidates = CAMPAIGNS[partition]
    execution = document["execution"]
    assert document["mode"] == "label_all"
    assert execution["candidates_left_unattempted"] == 0
    assert execution["sequences_recorded"] == groups
    assert execution["stop_reasons"] == {"all_candidates_labelled": groups}
    assert execution["hidden_passed"] + execution["hidden_failed"] == candidates


@pytest.mark.parametrize("partition", PARTITIONS)
def test_no_baseline_passed_hidden_verification(partition: str) -> None:
    """A passing baseline means the hidden suite does not test what the group declares."""
    assert _load(partition)["execution"]["baselines_passing_hidden_verification"] == 0


@pytest.mark.parametrize("partition", PARTITIONS)
def test_every_outcome_came_after_the_seal(partition: str) -> None:
    assert _load(partition)["execution"]["every_outcome_follows_the_seal"] is True


@pytest.mark.parametrize("partition", PARTITIONS)
def test_the_store_holds_self_play_and_nothing_governed(partition: str) -> None:
    _, groups, candidates = CAMPAIGNS[partition]
    observations = _load(partition)["observations"]
    assert observations["recorded"] == candidates
    assert observations["provenance_counts"] == {"self_play": candidates}
    assert observations["real_governed_runs"] == 0
    assert observations["groups"] == groups


@pytest.mark.parametrize("partition", PARTITIONS)
def test_no_two_candidates_share_a_fitted_vector(partition: str) -> None:
    """Rows collapsing onto fewer vectors would be fewer decisions than the count claims."""
    _, _, candidates = CAMPAIGNS[partition]
    assert _load(partition)["observations"]["distinct_feature_vector_hashes"] == candidates


@pytest.mark.parametrize("partition", PARTITIONS)
def test_the_replay_started_no_container_and_left_no_remainder(partition: str) -> None:
    _, groups, candidates = CAMPAIGNS[partition]
    resume = _load(partition)["resume"]
    assert resume["run_identities_resolved_from_the_receipt"] == candidates + groups
    assert resume["runs_replayed"] == candidates + groups
    assert resume["containers_started_on_the_replay"] == 0
    assert resume["receipt_is_resumable"] is True
    assert resume["receipt_effective_remainder"] == []


@pytest.mark.parametrize("partition", PARTITIONS)
def test_the_member_table_is_complete_enough_to_select_from(partition: str) -> None:
    """S21D4-037 resolves an explicit selection from this table, not a store-wide query."""
    document = _load(partition)
    _, groups, candidates = CAMPAIGNS[partition]
    rows = document["candidate_outcomes"]
    assert len(rows) == candidates
    assert len({row["observation_id"] for row in rows}) == candidates
    assert len({row["candidate_id"] for row in rows}) == candidates
    assert len(document["task_run_ids"]) == candidates + groups
    for row in rows:
        assert row["provenance_class"]
        assert row["feature_vector_hash"]
        assert row["outcome_hash"]
        assert isinstance(row["accepted"], bool)


def test_the_two_campaigns_share_no_candidate_and_no_group() -> None:
    """One candidate in both roles would fit the ranker on a row it is later scored against."""
    fitting = _load("training")["candidate_outcomes"]
    calibration = _load("calibration")["candidate_outcomes"]
    for key in ("candidate_id", "group", "task_id", "feature_vector_hash", "observation_id"):
        assert not {row[key] for row in fitting} & {row[key] for row in calibration}, key


def test_no_recipe_is_a_giveaway() -> None:
    """If one recipe always carried the repair, a ranker could win by memorising the slot."""
    for partition in PARTITIONS:
        rates = _load(partition)["execution"]["acceptance_by_recipe"]
        assert len(rates) == 4
        assert max(rates.values()) - min(rates.values()) < 0.30, (partition, rates)
