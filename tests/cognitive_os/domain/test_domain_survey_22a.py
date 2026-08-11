"""S22A-W0: the sealed domain survey reproduces, and its numbers still describe the code.

`sprint-22a-domain-survey.json` is the measured starting state Sprint 22A's negative exit
claim — "without changing the core controller or storage schema" — is diffed against. Three
things have to be true of it, and each is worth more than the prose that introduces it:

*It reproduces.* Re-running the script recomputes every measured field identically. Only
`recorded_at` and the seal over it may differ, so this check does not fail on the passage of
time (W2-F1/F2: a reproduction check that fails because a clock moved proves nothing).

*Its seal is over its own content.* The integrity hash is recomputed here from the record's
own body rather than trusted.

*Its numbers are the fence, not decoration.* The 9 modules and 57 references are the
coupling W1 must show reaching the adapter boundary and stopping, and §3.5 makes the recount
a regression: registering two pilot domains must add **zero** new `DomainKind` references.
This test is where that recount lives from W0 onward, so the fence exists before the wave
that has to stay inside it.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
SURVEY = REPOSITORY / "docs/sprints/sprint-22/evidence/sprint-22a-domain-survey.json"

#: The sealed coupling, restated here so a silent growth fails loudly. A change to these two
#: numbers is a change to what Sprint 22A promised, not a test to update.
SEALED_MODULE_COUNT = 9
SEALED_REFERENCE_COUNT = 57


def _load(name: str) -> Any:
    """`scripts/` is not an importable package, so the released loader pattern is used."""
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / f"scripts/{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


survey_script = _load("domain_survey_22a")


def _sealed() -> dict[str, Any]:
    return json.loads(SURVEY.read_text(encoding="utf-8"))


def _measured_only(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key not in {"recorded_at", "integrity_content_hash"}
    }


def test_the_seal_is_over_the_records_own_content() -> None:
    record = _sealed()
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    assert survey_script._digest(survey_script._canonical(body)) == record["integrity_content_hash"]


def test_the_survey_reproduces_every_measured_field(tmp_path: Path) -> None:
    """Only the timestamp and the seal over it may move between runs."""
    output = tmp_path / "sprint-22a-domain-survey.json"
    assert survey_script._run(output) == 0
    fresh = json.loads(output.read_text(encoding="utf-8"))

    assert _measured_only(fresh) == _measured_only(_sealed())
    assert fresh["recorded_at"] >= _sealed()["recorded_at"]


def test_the_enum_coupling_has_not_grown() -> None:
    """§3.5's silo regression, seated in W0 so W2 and W3 inherit a fence rather than a claim."""
    coupling = survey_script._enum_coupling()
    assert coupling["module_count"] == SEALED_MODULE_COUNT
    assert coupling["reference_count"] == SEALED_REFERENCE_COUNT
    assert coupling == _sealed()["enum_coupling"]


def test_the_coupling_is_counted_over_the_released_source_tree_only() -> None:
    """Tests and scripts may say `DomainKind` freely; the fence is about shipped modules."""
    modules = _sealed()["enum_coupling"]["modules"]
    assert all(name.startswith("src/cognitive_os/") for name in modules)
    assert _sealed()["enum_coupling"]["definition"] in modules


def test_the_derived_descriptors_still_match_the_released_registry() -> None:
    from cognitive_os.domains import registry

    derived = _sealed()["released_domains_as_descriptors"]
    assert derived["registry_snapshot_hash"] == registry.snapshot_hash()
    assert set(derived["descriptors"]) == {"coding", "logic", "mathematics", "physics"}


def test_the_boundary_record_stores_a_diagnosis_for_all_six_refusals() -> None:
    boundary = _sealed()["package_boundary"]
    assert boundary["valid_pilot_shape_accepted"] is True
    assert boundary["every_refusal_refused"] is True
    assert set(boundary["refusals"]) == set(survey_script._refusal_cases())
    assert len(boundary["refusals"]) == 6


def test_the_record_binds_the_predecessor_release_it_was_taken_at() -> None:
    predecessor = _sealed()["predecessor"]
    assert predecessor["tag"] == "sprint-21-learning-baseline"
    assert len(predecessor["commit"]) == 40
