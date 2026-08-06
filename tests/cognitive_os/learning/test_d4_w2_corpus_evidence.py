"""S21D4-030 and S21D4-031: the W2 corpus evidence still says what it said.

Not a second copy of `corpus_d4.py`'s own checks. These are the three things that go wrong
between authoring a corpus and spending it: an evidence file drifting from its sealed hash, a
number in it that no longer satisfies the contract it was produced under, and a source file
changing underneath a record that hashed it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from cognitive_os.coding.reality_retrieval_specs_d4 import D4_RETRIEVAL_SPECS
from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
CORPUS = EVIDENCE / "sprint-21d4-corpus.json"
SEPARATION = EVIDENCE / "sprint-21d4-separation.json"
SEALED = EVIDENCE / "sprint-21d4-sealed-manifests.json"
D3_SEALED = EVIDENCE / "sprint-21d3-sealed-manifests.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


@pytest.mark.parametrize("path", [CORPUS, SEPARATION, SEALED])
def test_each_w2_record_reproduces_its_integrity_hash(path: Path) -> None:
    """One canonicalisation across D4: the bytes hashed are the bytes written."""
    document = _load(path)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    assert _sha256(_canonical(body)) == document["integrity_content_hash"]


@pytest.mark.parametrize("path", [CORPUS, SEPARATION, SEALED])
def test_each_w2_record_is_bound_to_the_pre_registration(path: Path) -> None:
    document = _load(path)
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["final_outcomes_inspected"] is False


def test_the_corpus_is_the_size_the_contracts_demand() -> None:
    corpus = _load(CORPUS)["calibration_corpus"]
    assert corpus["groups"] == corpus["required_groups"] == 100
    assert len(D4_CALIBRATION_SPECS) == 100
    retrieval = _load(CORPUS)["retrieval_pool"]
    assert retrieval["source_groups"] >= retrieval["required_source_groups"] == 60
    assert len(D4_RETRIEVAL_SPECS) == 60


def test_every_body_was_executed_and_none_disagreed_with_its_declaration() -> None:
    executed = _load(CORPUS)["executed_verification"]
    assert executed["calibration_runs"] == 100 * 5 * 2
    assert executed["retrieval_runs"] == 60 * 2 * 2
    assert executed["declaration_mismatches"] == []
    assert executed["baselines_passing_their_visible_tests"] == 100
    assert executed["baselines_failing_their_hidden_tests"] == 100
    assert executed["declared_repairs_passing_both_suites"] == 100 * 2 * 2
    assert executed["partial_fixes_passing_visible_and_failing_hidden"] == 100 * 2 * 2
    assert executed["retrieval_failed_states_rejected_by_the_verifier"] == 60
    assert executed["retrieval_repairs_accepted_by_the_verifier"] == 60


def test_a_hundred_groups_are_not_six_families_with_ninety_four_seeds() -> None:
    families = _load(CORPUS)["calibration_corpus"]["template_families"]
    assert families["required_minimum"] == 15
    assert families["distinct_baseline_structures"] >= families["required_minimum"]
    assert families["satisfied"] is True
    # Every routing family carries real weight; none is a token single group.
    assert min(families["routing_families"].values()) >= 15


def test_the_source_files_still_hash_to_what_the_record_says() -> None:
    """A corpus record that outlives an edit to its corpus is a record of nothing."""
    corpus = _load(CORPUS)
    calibration = REPOSITORY / "src/cognitive_os/coding/reality_task_specs_d4.py"
    retrieval = REPOSITORY / "src/cognitive_os/coding/reality_retrieval_specs_d4.py"
    assert corpus["calibration_corpus"]["source_file_sha256"] == _sha256(
        calibration.read_text(encoding="utf-8").encode("utf-8")
    )
    assert corpus["retrieval_pool"]["source_file_sha256"] == _sha256(
        retrieval.read_text(encoding="utf-8").encode("utf-8")
    )


def test_the_defect_ledger_records_the_scan_that_was_too_narrow() -> None:
    """W2-D6 is the finding this wave must not be able to lose.

    The scan that cleared the hundred calibration groups compared D2 and D3 calibration only.
    A ledger that dropped it would leave the corpus looking as though it had been separated
    correctly the first time.
    """
    ledger = _load(CORPUS)["authoring_defect_ledger"]
    identifiers = {entry["id"] for entry in ledger}
    assert "W2-D6" in identifiers
    narrow = next(entry for entry in ledger if entry["id"] == "W2-D6")
    assert "reality_task_specs.py" in narrow["detail"]
    assert "D3 retrieval" in narrow["detail"]


def test_no_d4_group_crosses_a_role() -> None:
    separation = _load(SEPARATION)["role_separation"]
    assert separation["all_pairwise_disjoint"] is True
    assert separation["groups_crossing_a_role"] == []
    assert separation["group_counts"]["calibration"] == 100
    assert separation["group_counts"]["retrieval"] == 60
    assert separation["group_counts"]["fitting"] == 80


def test_nothing_d4_authored_restates_a_released_task() -> None:
    near_clone = _load(SEPARATION)["near_clone"]
    assert near_clone["cross_group_collisions_touching_d4"] == []
    assert set(near_clone["pool"]) == {"c3", "d2", "d3", "d3_retrieval", "d4", "d4_retrieval"}
    assert near_clone["bodies_compared"] >= 1470
    lineage = _load(SEPARATION)["lineage"]
    assert lineage["template_ids_reused_from_a_predecessor"] == []
    assert lineage["repository_groups_reused_from_a_predecessor"] == []
    assert lineage["task_signatures_reused_from_a_predecessor"] == []
    assert lineage["d4_template_ids"] == lineage["d4_repository_groups"] == 160


def test_the_detector_that_says_so_is_running() -> None:
    """A detector that finds nothing reads the same as a detector that is not running."""
    near_clone = _load(SEPARATION)["near_clone"]
    assert near_clone["seeded_restatement_detected"] is True
    assert near_clone["seeded_restatement_pairs"] >= 1
    # A group's own candidates are meant to be structurally close; that is the edit path.
    assert near_clone["intra_group_structural_matches"] > 0


def test_the_seal_names_every_role_and_no_outcome() -> None:
    sealed = _load(SEALED)
    seal = sealed["seal"]
    assert seal["outcomes_present"] is False
    assert seal["corpus_authoring_capability_revoked"] is True
    assert sealed["capability_revocation"]["revoked"] is True
    counts = {name: row["groups"] for name, row in sealed["catalogues"].items()}
    assert counts == {
        "training": 80,
        "calibration": 100,
        "final_a": 30,
        "final_b": 30,
        "canary": 5,
        "retrieval": 60,
    }
    assert sealed["role_disjointness"]["all_pairwise_disjoint"] is True


def test_the_carried_roles_are_the_bytes_d3_released() -> None:
    """Identical to what S21D3 bound, not merely equal to a fresh derivation of it."""
    carried = _load(SEALED)["carried_roles"]
    released = _load(D3_SEALED)["catalogues"]
    assert carried["all_identical"] is True
    assert carried["d3_evidence_sha256"] == _sha256(D3_SEALED.read_bytes())
    for role, row in carried["roles"].items():
        assert row["identical"] is True
        assert row["d3_released_hash"] == released[role]["content_hash"]
        assert row["s21d4_004_decision"] == "reuse"


def test_the_submanifests_count_replicas_as_replicas() -> None:
    """The W1 erratum reaches the seal, or the hundred-decision floor is met by counting twice."""
    submanifests = _load(SEALED)["transformation_submanifests"]
    invariance = submanifests["calibration_invariance"]
    assert invariance["sample_groups"] == 20
    assert invariance["transformed_decisions"] == 40
    assert invariance["independent_decisions"] == 0
    assert len(invariance["sample_groups_named"]) == 20
    promotion = submanifests["promotion"]
    assert promotion["nominal_decisions"] == 120
    assert promotion["independent_decisions"] == 60
    assert promotion["reported_side_by_side"] is True


def test_the_seal_is_bound_to_the_corpus_it_seals() -> None:
    bound = _load(SEALED)["bound_evidence"]
    assert bound["corpus"]["sha256"] == _sha256(CORPUS.read_bytes())
    assert bound["separation"]["sha256"] == _sha256(SEPARATION.read_bytes())
