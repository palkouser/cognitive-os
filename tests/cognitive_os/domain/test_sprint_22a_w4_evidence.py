"""S22A-W4: the release wave's claims, checked by the suite the release wave runs.

`sprint-22a-exit-criteria.json` is where the sprint's four exit criteria are decided, and it
is the record the tag will be created against. These tests re-derive it rather than read it:
`_check()` recomputes the frozen-file comparison, the coupling census, the released registry
hashes and all six benchmark replays in this process.

**No test here reads `sprint-22a-verification-matrix.json`, on purpose.** The matrix runs this
suite as one of its own rows, so a test asserting over the matrix record would be reading the
*previous* run's copy and the release command would need two runs to go green. That is D5's
defect and D7's lesson; the matrix checks itself in `_structural_findings`, where the result
reaches the exit status instead of the next run.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
RECORD = EVIDENCE / "sprint-22a-exit-criteria.json"


def _load_script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / f"scripts/{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exit_criteria = _load_script("exit_criteria_22a")


def _record() -> dict[str, Any]:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_the_exit_criteria_record_still_checks() -> None:
    """Seal, frozen files, coupling, released hashes, and six replays actually run."""
    exit_criteria._check()


def test_all_four_criteria_are_met_and_the_outcome_follows_from_them() -> None:
    record = _record()
    assert record["verdicts"] == exit_criteria._verdicts(record["criteria"])
    assert record["verdicts"]["met"] == 4
    assert record["verdicts"]["all_four_met"] is True
    assert record["outcome"] == "pass"
    assert record["outcome_tag"] == "sprint-22a-domain-baseline"


def test_every_check_that_decides_a_criterion_is_a_boolean() -> None:
    """Counts live in `counts`: a release decided on `!= 0` is decided by truthiness."""
    for criterion in _record()["criteria"].values():
        assert criterion["checks"]
        assert all(isinstance(value, bool) for value in criterion["checks"].values())


def test_the_core_controller_and_the_storage_schema_are_the_predecessors_bytes() -> None:
    """W2 and W3 wrote this as a literal; here it is eleven files and fifteen migrations."""
    assert exit_criteria._check_frozen_files(_record()) == []
    frozen = _record()["unchanged_since_the_predecessor"]
    assert frozen["core_controller"]["file_count"] == 11
    assert frozen["core_controller"]["every_file_identical_to_the_predecessor"] is True
    assert frozen["storage_schema"]["file_count"] == 15
    assert frozen["storage_schema"]["every_file_identical_to_the_predecessor"] is True


def test_the_controller_module_set_is_sealed_rather_than_globbed_afresh() -> None:
    """A twelfth controller module has to be a refusal, not a row nobody wrote."""
    sealed = _record()["unchanged_since_the_predecessor"]["core_controller"]["files"]
    assert sorted(sealed) == exit_criteria._controller_modules()
    assert "src/cognitive_os/domains/controller.py" in sealed
    assert "src/cognitive_os/application/services/cognitive_controller.py" in sealed


def test_every_released_domain_is_replayed_including_coding() -> None:
    """W4-F1: for three waves, "per-domain replay" covered three of the four released domains."""
    replay = _record()["replay"]
    assert replay["every_released_domain_replayed"] is True
    assert replay["released_domains_replayed"] == ["coding", "logic", "mathematics", "physics"]
    assert replay["manifest_count"] == 6
    assert replay["every_manifest_green"] is True
    assert set(replay["manifests"]) >= {"sprint22-coding-ci", "sprint22-coding-seed"}


def test_the_recorded_criteria_bind_the_records_they_were_read_from() -> None:
    record = _record()
    for group in ("governed_views", "fail_closed", "pilots"):
        bound = record[group]["bound"]
        assert bound
        for item in bound:
            assert (EVIDENCE / item["record"]).is_file()
            assert len(item["sha256"]) == 64


def test_the_pass_names_what_it_does_not_mean() -> None:
    """The two stops travel forward by name rather than being closed by a green record."""
    disclaimers = " ".join(_record()["what_a_pass_here_does_not_mean"])
    assert "state machine" in disclaimers
    assert "persisted-run path" in disclaimers
    assert "deterministic verification" in disclaimers
