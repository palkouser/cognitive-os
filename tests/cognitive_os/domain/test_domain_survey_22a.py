"""S22A-W0: the sealed domain survey reproduces, and its numbers still describe the code.

`sprint-22a-domain-survey.json` is the measured starting state Sprint 22A's negative exit
claim — "without changing the core controller or storage schema" — is diffed against. Three
things have to be true of it, and each is worth more than the prose that introduces it:

*The half of it that is a contract reproduces exactly.* The four derived descriptor hashes,
the registry snapshot hash and the package boundary's refusals are what "the released domains
are unchanged" means, and they must recompute identically forever. `recorded_at` and the seal
over it may differ, so this check does not fail on the passage of time (W2-F1/F2: a
reproduction check that fails because a clock moved proves nothing).

*Its seal is over its own content.* The integrity hash is recomputed here from the record's
own body rather than trusted.

*Its coupling numbers are a ceiling, not a target.* 9 modules and 57 references measured the
tree at W0; §3.5 makes the recount a regression in one direction only — a wave may drive the
count down, as W1's seam did, and may never push it up. W1-F3: this test originally demanded
equality, which made the sprint's own progress a failure.
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


def test_the_compat_contract_still_reproduces(tmp_path: Path) -> None:
    """The half of the survey that is a *contract* must reproduce exactly, forever.

    W1-F3. This test used to compare every measured field, which quietly asserted that the
    source tree never changes — so the W1 seam, which legitimately *removed* five enum
    references, failed it. The sealed record is a starting state, and only some of it is a
    promise: the four derived descriptor hashes, the registry snapshot hash and the package
    boundary's refusals are the backward-compatibility contract and reproduce exactly; the
    coupling count is a measurement of the tree at W0 and is fenced below, not frozen here.
    """
    output = tmp_path / "sprint-22a-domain-survey.json"
    assert survey_script._run(output) == 0
    fresh = json.loads(output.read_text(encoding="utf-8"))
    sealed = _sealed()

    assert fresh["released_domains_as_descriptors"] == sealed["released_domains_as_descriptors"]
    assert fresh["package_boundary"]["every_refusal_refused"] is True
    assert set(fresh["package_boundary"]["refusals"]) == set(sealed["package_boundary"]["refusals"])
    assert fresh["predecessor"] == sealed["predecessor"]
    assert fresh["recorded_at"] >= sealed["recorded_at"]


def test_the_enum_coupling_has_not_grown() -> None:
    """§3.5's silo regression, seated in W0 so W2 and W3 inherit a fence rather than a claim.

    A ceiling, not a target: the pre-registration froze `coupling_may_grow: false`, and the
    seam is expected to push the count *down*. A wave that adds a `DomainKind` branch to make
    a pilot register fails here, which is the whole purpose.
    """
    coupling = survey_script._enum_coupling()
    assert coupling["module_count"] <= SEALED_MODULE_COUNT
    assert coupling["reference_count"] <= SEALED_REFERENCE_COUNT
    assert all(name.startswith("src/cognitive_os/") for name in coupling["modules"])


def test_the_coupling_is_counted_over_the_released_source_tree_only() -> None:
    """Tests and scripts may say `DomainKind` freely; the fence is about shipped modules."""
    modules = _sealed()["enum_coupling"]["modules"]
    assert all(name.startswith("src/cognitive_os/") for name in modules)
    assert _sealed()["enum_coupling"]["definition"] in modules


def test_the_derived_descriptors_still_match_the_released_registry() -> None:
    from cognitive_os.domains import registry

    derived = _sealed()["released_domains_as_descriptors"]
    # `released_snapshot_hash`, not `snapshot_hash`: S22A-030 split the two, and only the
    # released-scope one still means what the survey sealed once a pilot can be registered.
    # A test session that admitted a descriptor domain earlier would otherwise fail here on
    # test ordering rather than on a released change.
    assert derived["registry_snapshot_hash"] == registry.released_snapshot_hash()
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
