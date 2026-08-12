"""S22A-W1: the seam's proof stays true, and CI is what keeps it true.

`sprint-22a-w1-seam.json` claims three things about released behaviour — the registry snapshot
hash, the four derived descriptor hashes and the `DomainKind` coupling ceiling. A claim that is
only checked by the wave that made it decays the moment a later wave edits the seam, which is
exactly what W2 and W3 are about to do. So the seam script's own `--check` runs here.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
SEAM = EVIDENCE / "sprint-22a-w1-seam.json"


def _load_script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / f"scripts/{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seam_script = _load_script("seam_22a")


def _record() -> dict[str, Any]:
    return json.loads(SEAM.read_text(encoding="utf-8"))


def test_the_seam_record_still_checks() -> None:
    """Snapshot hash, four compat hashes, the coupling ceiling and the four slice records."""
    seam_script._check()


def test_the_released_domains_cannot_tell_the_seam_exists() -> None:
    record = _record()
    compat = record["backward_compatibility"]
    assert compat["registry_snapshot_unchanged"] is True
    assert len(compat["descriptors"]) == 4
    assert all(item["unchanged"] for item in compat["descriptors"].values())
    assert record["every_released_claim_holds"] is True


def test_the_seam_changed_no_controller_and_no_schema() -> None:
    seam = _record()["seam"]
    assert seam["core_controller_changed"] is False
    assert seam["storage_schema_changed"] is False
    assert seam["migration_head"] == "0015"
    assert seam["migrations_allocated_by_w1"] == 0
    assert seam["storage_route"]["new_tables"] == 0


def test_the_coupling_went_down_rather_than_up() -> None:
    """The seam's purpose, as a number: five `DomainKind` references removed, none added."""
    coupling = _record()["enum_coupling"]
    assert coupling["grew"] is False
    assert coupling["references_removed"] > 0
    assert coupling["at_w1"]["references"] < coupling["at_w0"]["references"]


def test_the_slice_ran_in_separate_processes_and_refused_the_tamper() -> None:
    """The chain is only evidence if the rebuild was a cold start; see the D7 lifecycle lesson."""
    vertical = _record()["vertical_slice"]
    assert vertical["separate_processes"] is True
    assert vertical["fixture_is_not_a_pilot"] is True
    assert vertical["phases"]["rebuild"]["summary"]["fixture_rebuilt"] is True
    assert vertical["phases"]["tamper"]["summary"]["refused"] is True
    assert vertical["phases"]["tamper"]["summary"]["still_parses_as_a_package"] is True
    assert vertical["phases"]["tamper"]["summary"]["named_the_domain"] is True
    assert vertical["phases"]["refusals"]["summary"]["every_case_refused"] is True
    assert vertical["phases"]["refusals"]["summary"]["registrations_after"] == 1
