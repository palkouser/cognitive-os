"""S22A-W2: the pilot's evidence stays true, and CI is what keeps it true.

`sprint-22a-w2-pilot.json` claims that a registry which gained a domain still resolves the
four released domains identically, that the `DomainKind` coupling did not grow, and that the
chain ran across processes. W3 is about to register a second domain through the same door,
so those claims need a check that outlives the wave that made them.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess  # nosec B404 - fixed argument vector, no shell, first-party script
import sys
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
PILOT = EVIDENCE / "sprint-22a-w2-pilot.json"
DECISIONS = EVIDENCE / "sprint-22a-w2-decisions.json"


def _load_script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / f"scripts/{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot_script = _load_script("pilot_22a")


def _record() -> dict[str, Any]:
    return json.loads(PILOT.read_text(encoding="utf-8"))


def test_the_pilot_record_still_checks() -> None:
    """Released snapshot, four compat hashes, the coupling ceiling, five bound phase records."""
    pilot_script._check()


def test_the_snapshot_decision_reproduces_in_a_clean_process() -> None:
    """S22A-030's whole content is *which* hash moves when a pilot registers.

    Run as a subprocess on purpose: the claim is about a registry before and after its first
    descriptor domain, and a pytest session that already registered one has no "before" left
    to measure. Checking it in-process would quietly assert something weaker.
    """
    completed = subprocess.run(  # nosec B603 - fixed vector, no shell
        [sys.executable, str(REPOSITORY / "scripts/decisions_22a_w2.py"), "--check"],
        capture_output=True,
        text=True,
        cwd=REPOSITORY,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    reported = json.loads(completed.stdout)
    assert reported["released_snapshot_unchanged_after_registration"] is True
    assert reported["whole_snapshot_changed_after_registration"] is True


def test_the_released_four_cannot_tell_a_pilot_was_registered() -> None:
    compatibility = _record()["backward_compatibility"]
    assert compatibility["measured_with_the_pilot_registered"] is True
    assert compatibility["released_snapshot_unchanged"] is True
    assert compatibility["whole_registry_snapshot_differs"] is True
    assert len(compatibility["descriptors"]) == 4
    assert all(item["unchanged"] for item in compatibility["descriptors"].values())
    assert compatibility["released_entries"] == 28
    assert _record()["every_released_claim_holds"] is True


def test_the_pilot_registered_without_a_migration_a_table_or_a_branch() -> None:
    boundaries = _record()["boundaries"]
    assert boundaries["core_controller_changed"] is False
    assert boundaries["storage_schema_changed"] is False
    assert boundaries["migration_head"] == "0015"
    assert boundaries["migrations_allocated_by_w2"] == 0
    assert boundaries["new_tables"] == 0
    assert boundaries["new_enum_members"] == 0


def test_registering_a_domain_added_no_domainkind_branch() -> None:
    """§3.5's silo regression, one wave early: a descriptor domain has nothing to branch on."""
    coupling = _record()["enum_coupling"]
    assert coupling["grew_since_w1"] is False
    assert coupling["grew_since_w0"] is False
    assert coupling["added_by_the_pilot"] == 0


def test_the_chain_ran_across_processes_and_refused_what_it_should() -> None:
    chain = _record()["chain"]
    assert chain["separate_processes"] is True
    assert len(chain["processes_observed"]) >= 3
    phases = chain["phases"]
    assert phases["register"]["summary"]["went_through_the_boundary"] is True
    assert phases["rebuild"]["summary"]["pilot_rebuilt"] is True
    assert phases["rebuild"]["summary"]["released_snapshot_unchanged"] is True
    assert phases["rebuild"]["summary"]["whole_snapshot_changed"] is True
    assert phases["solve"]["summary"]["every_task_accepted"] is True
    assert phases["solve"]["summary"]["every_wrong_answer_refused"] is True
    assert phases["views"]["summary"]["same_content_hash_in_both_views"] is True
    assert phases["refusals"]["summary"]["every_case_refused"] is True
    assert phases["refusals"]["summary"]["nothing_registered_halfway"] is True


def test_the_cross_domain_concepts_have_exactly_one_owner_and_two_views() -> None:
    pilot = _record()["pilot"]
    assert pilot["every_shared_concept_has_one_owner"] is True
    assert pilot["every_problem_type_resolves_to_the_pilot"] is True
    assert pilot["capabilities_are_released_ones"] is True
    assert pilot["enum_members_added"] == 0
    for concept in pilot["cross_domain_views"].values():
        assert concept["owner"] == "engineering.mechanics"
        assert concept["visible_from"] == ["engineering.mechanics", "physics"]


def test_the_decision_record_is_sealed_and_names_the_contract_it_re_binds() -> None:
    decision = json.loads(DECISIONS.read_text(encoding="utf-8"))["decisions"][
        "registry_snapshot_scope"
    ]
    assert decision["item"] == "S22A-030"
    assert decision["re_binding"]["reproduces"] is True
    assert decision["re_binding"]["reproduced_by"].endswith("released_snapshot_hash")
    # The premise the wave arrived with was wrong, and the record says so rather than
    # quietly acting on the corrected version (W2-F1).
    assert decision["premise_corrected"]["domains_registry_snapshot_hash_callers_in_src"] == {}
