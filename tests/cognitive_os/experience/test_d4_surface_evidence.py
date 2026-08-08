"""S21D4-040: the surface record, read against the question it claims to answer.

The dangerous reading of this record is "every number is fine, so the change was free". Two
of its numbers are not fine — seven groups gain no term and four collisions cross a family
boundary — and a test that only checked the reassuring ones would hide exactly the part a
successor needs. So the zeros are checked, and so is the shortfall.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cognitive_os.domain.experience_graph import SEARCH_TERMS_CHARACTER_BOUND

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
SURFACE = EVIDENCE / "sprint-21d4-surface.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d4-contracts.json"


def _load() -> dict[str, Any]:
    return json.loads(SURFACE.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_integrity_hash() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]


def test_the_record_is_bound_to_the_contracts_it_changes() -> None:
    document = _load()
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["contracts_sha256"] == _sha256(CONTRACTS.read_bytes())
    assert document["final_or_canary_outcomes_inspected"] == 0
    assert document["final_outcomes_inspected"] is False


def test_every_stored_graph_kept_the_hash_its_root_declared() -> None:
    """The acceptance condition, and it is checked per root rather than in aggregate."""
    stored = _load()["stored_graphs"]
    assert stored["every_stored_hash_unchanged"] is True
    assert stored["pairs_total"] == 140
    assert stored["graphs_total"] == 280
    for name in ("sprint-21d1", "sprint-21d3"):
        row = stored["roots"][name]
        assert row["all_declared_pairs_loaded"] is True
        assert row["intact"] is True
        assert row["pairs_deserialised"] == row["declared_pairs"]
        assert row["pairs_whose_declared_hashes_moved"] == []
        assert row["graphs_whose_label_or_structure_moved_under_terms"] == []
        assert row["edit_paths_that_stopped_round_tripping"] == []
        assert row["missing_bytes"] == row["corrupt_bytes"] == row["broken_links"] == []


def test_the_d2_gap_is_stated_rather_than_left_implicit() -> None:
    """ "Every D1, D2 and D3 stored graph" has to survive the fact that D2 stored none."""
    stored = _load()["stored_graphs"]
    assert stored["d2_stored_graph_roots"] == 0
    assert "wrote no graph root" in stored["d2_note"]


def test_the_contract_conflict_is_measured_not_argued() -> None:
    """W3-D1 is only a finding if the two hashes it names are different hashes."""
    finding = next(row for row in _load()["findings"] if row["id"] == "W3-D1")
    # Without this anchor the counterfactual is two hashes of nothing in particular: it says
    # the measurement reproduces the hash the released store actually holds.
    assert finding["reproduces_the_stored_content_hash"] is True
    assert finding["hash_as_stored"] != finding["hash_if_the_empty_field_were_included"]
    assert finding["identical"] is False
    assert "not the serializer" in finding["resolution_placed_in"]
    assert finding["stored_pairs_that_would_stop_loading"] == 140
    assert finding["contract_amended_not_edited"] is True
    assert finding["affects_any_published_number"] is False


def test_the_surface_widened_and_the_record_says_by_how_little() -> None:
    """D3 measured one document. The honest successor number is 47, not 60."""
    surface = _load()["document_surface"]
    assert surface["distinct_after_removing_domain_and_signature_before"] == 1
    assert surface["distinct_after_removing_domain_and_signature_after"] > 1
    assert surface["candidates"] == 60
    assert surface["distinct_after_removing_domain_and_signature_after"] < surface["candidates"], (
        "a record claiming sixty distinct documents would be claiming more than was measured"
    )
    assert surface["character_bound"] == SEARCH_TERMS_CHARACTER_BOUND


def test_the_shortfall_is_named_with_its_reason() -> None:
    """W3-F1 states which groups the widened surface still cannot tell apart."""
    finding = next(row for row in _load()["findings"] if row["id"] == "W3-F1")
    surface = _load()["document_surface"]
    assert finding["kind"] == "measured_limitation"
    assert finding["measured"]["groups_with_no_terms"] == len(surface["groups_with_no_terms"])
    assert finding["measured"]["cross_family_collisions"] == len(surface["cross_family_collisions"])
    assert finding["measured"]["groups_with_no_terms"] > 0
    assert finding["not_repaired_here"]
    assert "spent D3 holdout" in finding["measured_on"]


def test_the_bytes_move_exactly_when_a_term_appears() -> None:
    surface = _load()["document_surface"]
    assert surface["every_graph_that_gained_a_term_is_new_bytes"] is True
    assert surface["a_termless_graph_keeps_its_bytes"] is True
    for row in surface["per_pair"]:
        assert row["content_hash_moved"] is bool(row["terms"])
        assert row["characters"] <= SEARCH_TERMS_CHARACTER_BOUND


def test_the_counterfactual_wrote_nothing_and_read_no_holdout() -> None:
    document = _load()
    surface = document["document_surface"]
    assert surface["written_back"] is False
    assert surface["d4_retrieval_pool_read"] is False
    assert document["store_writes"]["unchanged"] is True
    assert (
        document["store_writes"]["fingerprints_before"]
        == (document["store_writes"]["fingerprints_after"])
    )


def test_every_guard_fired_including_the_one_that_could_not() -> None:
    """A leak planted where the normaliser erases it proves nothing; both cases are recorded."""
    guards = _load()["guards"]
    assert guards["all_guards_fired"] is True
    assert guards["judgement_leak_refused"] is True
    assert guards["forbidden_marker_refused"] is True
    assert guards["uncanonical_order_refused"] is True
    assert guards["repeated_term_refused"] is True
    assert guards["over_bound_list_refused"] is True
    assert guards["a_clean_list_is_accepted"] is True
    assert guards["a_module_scope_name_never_reaches_the_surface"] is True
