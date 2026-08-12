"""S22A-W3: the second pilot's evidence stays true, and CI is what keeps it true.

`sprint-22a-w3-pilot.json` closes §3.5's silo regression — two domains registered, zero
`DomainKind` branches added — and seals a rejection suite whose cases each name the layer
that refused them. W4 releases against these numbers, so they need a check that outlives the
wave that made them.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
RECORD = EVIDENCE / "sprint-22a-w3-pilot.json"


def _load_script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / f"scripts/{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chemistry_script = _load_script("chemistry_22a")


def _record() -> dict[str, Any]:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_the_w3_record_still_checks() -> None:
    """Released snapshot with both pilots, compat hashes, the coupling ceiling, five records."""
    chemistry_script._check()


def test_the_released_four_cannot_tell_that_two_pilots_registered() -> None:
    compatibility = _record()["backward_compatibility"]
    assert compatibility["released_snapshot_unchanged"] is True
    assert compatibility["whole_registry_snapshot_differs"] is True
    assert compatibility["released_entries"] == 28
    assert len(compatibility["descriptors"]) == 4
    assert all(item["unchanged"] for item in compatibility["descriptors"].values())
    assert _record()["every_released_claim_holds"] is True


def test_two_domains_added_no_domainkind_branch() -> None:
    """§3.5's silo regression, closed rather than promised."""
    silo = _record()["silo_regression"]
    assert silo["measured_with_both_pilots_registered"] is True
    assert silo["added_by_both_pilots"] == 0
    assert silo["grew"] is False
    assert silo["at_w3"]["references"] <= silo["at_w0"]["references"]


def test_both_pilots_are_registered_and_resolve_to_themselves() -> None:
    pilots = _record()["pilots"]
    assert pilots["pilot_count"] == 2
    assert set(pilots["registered"]) == {"engineering.mechanics", "science.chemistry"}
    assert all(item["lifecycle"] == "pilot" for item in pilots["registered"].values())
    assert all(item["resolves_to_itself"] for item in pilots["registered"].values())
    assert pilots["problem_types_total"] == 5


def test_physics_sees_both_pilots_and_owns_nothing_of_theirs() -> None:
    pilots = _record()["pilots"]
    assert pilots["physics_sees_both_pilots"] is True
    assert pilots["physics_owns_none_of_them"] is True
    assert set(pilots["shared_into_physics"].values()) == {
        "engineering.mechanics",
        "science.chemistry",
    }


def test_the_excluded_candidates_are_named_with_reasons() -> None:
    """§3.4: what could not be deterministically verified is on the record, not dropped."""
    pilots = _record()["pilots"]
    assert set(pilots["excluded_candidates"]) == {
        "chemistry.reaction-prediction",
        "chemistry.equilibrium-constant",
    }
    assert pilots["the_new_capability"]["name"] == "chemistry.stoichiometry"


def test_the_rejection_suite_refuses_at_the_layer_that_owns_each_case() -> None:
    suite = _record()["rejection_suite"]
    assert suite["every_case_refused"] is True
    assert suite["nothing_registered_halfway"] is True
    assert suite["case_count"] == 10
    assert len(suite["sealed_cases_executed"]) == 6
    assert set(suite["by_layer"]) == {
        "package boundary",
        "registry door",
        "catalogue",
        "resolution",
    }
    assert len(suite["by_layer"]["package boundary"]) == 6
    assert suite["the_three_this_sprint_owed"] == {
        "released_id_at_a_new_revision": "registry door",
        "capabilities_naming_a_verifier_that_never_runs": "resolution",
        "shared_into_a_domain_that_never_declared_it_back": "catalogue",
    }


def test_the_second_pilot_registered_without_a_migration_or_a_branch() -> None:
    boundaries = _record()["boundaries"]
    assert boundaries["core_controller_changed"] is False
    assert boundaries["storage_schema_changed"] is False
    assert boundaries["migration_head"] == "0015"
    assert boundaries["migrations_allocated_by_w3"] == 0
    assert boundaries["new_enum_members"] == 0
    # W2-A1's stop travels forward rather than being quietly resolved.
    assert "state machine" in boundaries["not_reached"]["what"]


def test_the_chain_ran_across_processes() -> None:
    chain = _record()["chain"]
    assert chain["separate_processes"] is True
    assert len(chain["processes_observed"]) >= 4
    phases = chain["phases"]
    assert phases["register"]["summary"]["went_through_the_boundary"] is True
    assert phases["rebuild"]["summary"]["released_snapshot_unchanged"] is True
    assert phases["solve"]["summary"]["every_task_accepted"] is True
    assert phases["solve"]["summary"]["every_wrong_answer_refused"] is True
    assert phases["views"]["summary"]["physics_sees_two_pilots"] is True
    assert phases["rejections"]["summary"]["every_case_refused"] is True
