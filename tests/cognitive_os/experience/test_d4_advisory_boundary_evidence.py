"""S21D4-047: the advisory boundary, and the ways this record could have said nothing.

Three of its four claims are "no change" claims, and a no-change claim is the easiest thing in
a repository to assert vacuously. The first version of the script that produced this record
reported `byte-identical: True (0 compared)` -- true over an empty set, and worth nothing. So
these tests check that each claim had something to be false about.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
BOUNDARY = EVIDENCE / "sprint-21d4-advisory-boundary.json"
GRAPH_ROOT = EVIDENCE / "sprint-21d4-retrieval-emg-root.json"
HOLDOUT_RESULT = EVIDENCE / "sprint-21d4-retrieval-holdout-result.json"
DECISION = EVIDENCE / "sprint-21d4-retrieval-decision.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"


def _load() -> dict[str, Any]:
    return json.loads(BOUNDARY.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_integrity_hash_and_its_inputs() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["graph_root_sha256"] == _sha256(GRAPH_ROOT.read_bytes())
    assert document["holdout_result_sha256"] == _sha256(HOLDOUT_RESULT.read_bytes())
    assert document["decision_sha256"] == _sha256(DECISION.read_bytes())


def test_it_ran_on_the_real_holdout_under_the_widened_surface() -> None:
    """Fixtures would prove the contract; the holdout proves the evidence the sprint produced."""
    measured = _load()["measured"]
    assert measured["pairs"] == 60
    assert measured["graphs_carrying_terms"] > 0
    assert measured["widened_surface_reached_the_advisory_path"] is True
    assert measured["candidates_returned"] > 0, "a boundary over zero candidates proves nothing"


def test_the_mandatory_sections_had_something_to_move() -> None:
    """The vacuous-pass guard: an empty comparison is recorded as a failure, not a success."""
    sections = _load()["measured"]["mandatory_sections"]
    assert sections["mandatory_sections_compared"] > 0
    assert len(sections["mandatory_sections"]) == sections["mandatory_sections_compared"]
    assert sections["byte_identical"] == sections["mandatory_sections"]
    assert sections["moved"] == []
    assert sections["every_mandatory_section_is_byte_identical"] is True
    # Retrieval joins existing sections rather than adding new ones, so the two bundles have
    # the same section count. What says the graph contributed at all is this: some section
    # carries a graph reference, and those are exactly the ones excluded from the comparison.
    assert sections["sections_carrying_a_graph_reference"] > 0, (
        "no section carried a graph reference, so 'with and without retrieval' compared one "
        "bundle against itself"
    )
    assert (
        sections["sections_with_graph"]
        == sections["mandatory_sections_compared"] + sections["sections_carrying_a_graph_reference"]
    )


def test_an_advisory_candidate_carries_no_authority_and_no_body() -> None:
    properties = _load()["measured"]["advisory_properties"]
    assert properties["pinned"] == [False]
    assert properties["required"] == [False]
    assert properties["evidence"] == [False]
    assert properties["carries_an_executable_body"] is False
    assert properties["never_pinned_required_or_evidence"] is True
    assert properties["summary_says_advisory"] is True
    assert properties["unsafe_exclusions"] == 0


def test_an_empty_set_degrades_rather_than_failing() -> None:
    empty = _load()["measured"]["empty_set"]
    assert empty["candidates"] == 0
    assert empty["raised"] is False
    assert empty["degraded_rather_than_unavailable"] is True
    assert empty["component_status"] == "degraded"


def test_every_broken_store_lowers_trust_and_none_of_them_raises() -> None:
    """Four distinct ways the evidence can be unusable, each ending at UNVERIFIED."""
    degradation = _load()["measured"]["trust_degradation"]
    assert set(degradation) == {
        "verifier_raises",
        "verifier_says_no",
        "no_artifact_id",
        "no_verifier",
    }
    for name, row in degradation.items():
        assert row["candidates"] > 0, f"{name} returned nothing, so it degraded nothing"
        assert row["trust_classes"] == ["unverified"]
        assert row["only_unverified"] is True
        assert row["raised"] is False


def test_a_non_advisory_purpose_still_gets_nothing() -> None:
    purpose = _load()["measured"]["non_advisory_purpose"]
    assert purpose["candidates"] == 0
    assert purpose["gets_nothing"] is True


def test_the_boundary_was_proved_despite_the_negative_result() -> None:
    """§S21D4-046 records `s21d4_047_runs_on_every_outcome`; this is that promise executed."""
    document = _load()
    assert document["boundary_held"] is True
    assert "negative result" in document["runs_on_every_outcome"]
    assert json.loads(DECISION.read_text())["passed"] is False
    assert document["measured"]["creates_execution_or_correction_authority"] is False
    assert document["measured"]["opened_any_store_for_writing"] is False
