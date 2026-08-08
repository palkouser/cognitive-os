"""S21D4-022, -023, -024: the W1 evidence still says what it said, and still adds up.

These are not a second copy of the scripts' own checks. They are the three things that go wrong
between one wave and the next: an evidence file drifting from its sealed hash, a number in it
that no longer satisfies the contract it was produced under, and a decision whose bound hashes
stop resolving to the files they name.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from cognitive_os.learning.correction_protocol import (
    INDEPENDENT_DENOMINATOR,
    DecisionCensusV4,
)

EVIDENCE = Path(__file__).resolve().parents[3] / "docs/sprints/sprint-21/evidence"
REPLAY = EVIDENCE / "sprint-21d4-d3-grid-replay.json"
SEAL_RESUME = EVIDENCE / "sprint-21d4-seal-resume.json"
CONTINUATION = EVIDENCE / "sprint-21d4-continuation.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("path", [REPLAY, SEAL_RESUME, CONTINUATION])
def test_each_w1_record_reproduces_its_integrity_hash(path: Path) -> None:
    """One canonicalisation across D4: the bytes hashed are the bytes written."""
    document = _load(path)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode()
    assert _sha256(canonical) == document["integrity_content_hash"]


@pytest.mark.parametrize("path", [REPLAY, SEAL_RESUME, CONTINUATION])
def test_each_w1_record_carries_the_pre_registration(path: Path) -> None:
    assert _load(path)["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())


def test_the_replay_reproduced_every_setting_and_derived_no_threshold() -> None:
    replay = _load(REPLAY)
    assert replay["reproduction"]["settings_examined"] == 24
    assert replay["reproduction"]["settings_that_did_not_reproduce"] == []
    assert replay["boundary"]["thresholds_derived"] == 0
    assert replay["boundary"]["predecessor_store_writes"] == 0
    assert replay["boundary"]["database_connections_opened"] == 0


def test_every_replayed_setting_still_validates_as_a_census() -> None:
    """The stored triple is not decoration: it has to survive the contract that produced it."""
    for setting in _load(REPLAY)["per_setting"]:
        census = DecisionCensusV4.model_validate(setting["new"]["census"])
        assert census.nominal_decisions == 120
        assert census.independent_decisions == 20
        assert census.replicated_decisions == 100
        assert census.rate_denominator == INDEPENDENT_DENOMINATOR
        assert setting["new"]["confident_errors"] == (
            setting["new"]["answered_decisions"] - setting["new"]["correct_decisions"]
        )


def test_the_spine_was_proved_at_the_campaign_shape_the_contracts_declare() -> None:
    document = _load(SEAL_RESUME)
    assert document["shape"]["groups"] == 180
    assert document["shape"]["candidate_outcomes"] == 720
    assert {item["partition"] for item in document["partitions"]} == {"training", "calibration"}
    for partition in document["partitions"]:
        assert partition["chronology"]["strictly_pre_outcome"]
        assert partition["chronology"]["stored_seal_time_preserved"]
        assert partition["chronology"]["post_outcome_seal_refusal"]
        assert partition["restart"]["dataset_record_reproduced"]
        assert partition["restart"]["receipt_effective_remainder"] == 0
        # Every fixture candidate must encode distinctly, or the proof is one decision repeated.
        assert (
            partition["members"]["distinct_feature_record_hashes"]
            == partition["candidate_outcomes"]
        )
    assert document["artifact_bytes"]["every_stored_blob_rehashed"]
    assert document["role_boundary"]["d4_final_or_canary_groups_used"] == 0


def test_the_continuation_binds_hashes_that_still_resolve() -> None:
    continuation = _load(CONTINUATION)
    bound = continuation["bound_hashes"]
    for name, path in {
        "pre_registration": PRE_REGISTRATION,
        "contracts": EVIDENCE / "sprint-21d4-contracts.json",
        "d3_grid_replay": REPLAY,
        "seal_resume": SEAL_RESUME,
        "holdout_reuse_audit": EVIDENCE / "sprint-21d4-holdout-reuse-audit.json",
    }.items():
        assert bound[name] == _sha256(path.read_bytes()), name


def test_the_continuation_opened_no_measurement() -> None:
    continuation = _load(CONTINUATION)
    assert continuation["measurements_opened"] == 0
    assert continuation["decision"]["kind"] in {"proceed", "stop"}
    assert all(item["satisfied"] for item in continuation["conditions"]) == (
        continuation["decision"]["kind"] == "proceed"
    )
    assert continuation["retrieval_branch"]["status"] == "open"
