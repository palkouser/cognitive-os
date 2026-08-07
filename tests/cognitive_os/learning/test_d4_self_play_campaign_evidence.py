"""S21D4-035: the fitting campaign is self-play, label_all, and resumable off its receipt.

Four properties, each of which is a way the campaign could look finished and not be:

*Self-play only.* One `REAL_GOVERNED_RUN` row makes the corpus a record of production traffic
that no evaluation may treat as trainable.

*A baseline that passes.* The baseline is the unrepaired body. If the hidden verifier accepts
one, the group's hidden suite does not test what the group says it tests, and the four
candidates were never separable.

*Every candidate labelled.* Under `label_all` nothing may be left unattempted; a stop after the
first acceptance is a different experiment with a different denominator.

*A resume that costs nothing.* Replaying every recorded identity without a container is the
only evidence that a restart mid-campaign would not pay for the work twice.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus
from cognitive_os.learning.correction_protocol import CorrectionPartition

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
CAMPAIGN = EVIDENCE / "sprint-21d4-self-play-campaign.json"
SEALS = EVIDENCE / "sprint-21d4-feature-seals.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"


def _load() -> dict[str, Any]:
    return json.loads(CAMPAIGN.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_integrity_hash() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]


def test_the_campaign_is_bound_to_the_seal_it_executed_against() -> None:
    document = _load()
    sealed = json.loads(SEALS.read_text())
    row = next(item for item in sealed["partitions"] if item["partition"] == "training")
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["feature_seals_sha256"] == _sha256(SEALS.read_bytes())
    assert document["feature_seal_hash"] == row["feature_seal_hash"]
    assert document["feature_seal_reloaded_from_the_artifact_store"] is True
    assert document["campaign_manifest_hash"] == row["campaign_manifest_hash"]
    assert document["final_outcomes_inspected"] is False


def test_the_whole_fitting_partition_ran() -> None:
    document = _load()
    catalogue = seal_d4_corpus().catalogues[CorrectionPartition.TRAINING]
    execution = document["execution"]
    assert document["partition"] == "training"
    assert execution["groups"] == len(catalogue.groups) == 80
    assert execution["candidate_runs"] == catalogue.candidate_slots == 320
    assert execution["baselines"] == 80
    assert execution["containers_started"] == 400
    assert execution["unique_outcomes"] == 320
    assert execution["duplicates_excluded"] == 0


def test_every_candidate_was_labelled_under_label_all() -> None:
    document = _load()
    execution = document["execution"]
    assert document["mode"] == "label_all"
    assert execution["candidates_left_unattempted"] == 0
    assert execution["sequences_recorded"] == 80
    assert execution["stop_reasons"] == {"all_candidates_labelled": 80}
    assert execution["hidden_passed"] + execution["hidden_failed"] == 320


def test_no_baseline_passed_hidden_verification() -> None:
    """A passing baseline means the hidden suite does not test what the group declares."""
    assert _load()["execution"]["baselines_passing_hidden_verification"] == 0


def test_every_outcome_came_after_the_seal() -> None:
    assert _load()["execution"]["every_outcome_follows_the_seal"] is True


def test_the_store_holds_self_play_and_nothing_governed() -> None:
    observations = _load()["observations"]
    assert observations["recorded"] == 320
    assert observations["provenance_counts"] == {"self_play": 320}
    assert observations["real_governed_runs"] == 0
    assert observations["groups"] == 80


def test_no_two_candidates_share_a_fitted_vector() -> None:
    """320 rows collapsing onto fewer vectors would be fewer decisions than the count claims."""
    assert _load()["observations"]["distinct_feature_vector_hashes"] == 320


def test_the_replay_started_no_container_and_left_no_remainder() -> None:
    resume = _load()["resume"]
    assert resume["run_identities_resolved_from_the_receipt"] == 400
    assert resume["runs_replayed"] == 400
    assert resume["containers_started_on_the_replay"] == 0
    assert resume["receipt_is_resumable"] is True
    assert resume["receipt_effective_remainder"] == []


def test_the_member_table_is_complete_enough_to_select_from() -> None:
    """S21D4-037 resolves an explicit selection from this table, not from a store-wide query."""
    document = _load()
    rows = document["candidate_outcomes"]
    assert len(rows) == 320
    assert len({row["observation_id"] for row in rows}) == 320
    assert len({row["candidate_id"] for row in rows}) == 320
    assert len(document["task_run_ids"]) == 400
    for row in rows:
        assert row["provenance_class"]
        assert row["feature_vector_hash"]
        assert row["outcome_hash"]
        assert isinstance(row["accepted"], bool)
