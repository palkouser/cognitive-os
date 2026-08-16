"""S22D-W1: the declarative-fact path, and the claims over it that are not decorative.

W1 turned 22C's acquired-knowledge store from one artifact into eight retained facts and read a
frozen holdout from 0 to 4. What has to be true for those two numbers to mean anything:

*The coverage was priced before the campaign, not after.* 22C W3-F1 is a standing rule in this
sprint's §0 and W0 broke it. The repair is a record published ahead of acquisition, not a
holdout re-cut to fit what the source turned out to hold — so this asserts the holdout's frozen
hashes are the W0 ones, unchanged by anything W1 learned.

*The locators refuse, and the refusals are counted.* A gate that has never refused anything is a
gate nobody has tested (22A W4-F2). Both refusal reasons fire on the real cleared chapters: a
numeral that lost its exponent to the text layer, and a subject that is a sentence fragment.

*The table header is load-bearing.* Chemistry chapter 4 is full of lines shaped exactly like an
element-mass row and they are stoichiometric subscripts. If the header ever stops gating the
locator, `the atomic mass of C is 1` gets retained and every verifier downstream agrees.

*Every candidate left a decision.* `ExtractionDecisionOutcome` was a released contract with no
implementation, and it is what makes a refusal distinguishable from an absence.

*The ladder is the one W0 froze.* Five facts corroborated by the released kernel against the
consequence the source prints beside them, three admitted at the weaker rung — and the split is
read off the frozen ladder rather than restated.

*The holdout read is not circular.* Arm B derives each answer from the value the acquired layer
actually holds, not from the value the case withheld — the expected answer was computed from
that value, so comparing against it would prove only that arithmetic is arithmetic.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPOSITORY / "scripts"))

from facts_22d import (  # noqa: E402
    LADDER_CORROBORATED,
    LADDER_GROUNDED,
    REFUSAL_MANGLED_EXPONENT,
    REFUSAL_SUBJECT_NOT_AN_ENTITY,
    NumeralRefused,
    _entity_id,
    _resolve,
    canonical,
    corroborate,
    locate_all,
    read_numeral,
    read_subject,
)
from holdout_22d import DERIVATIONS, HOLDOUT_CASES, case_hashes  # noqa: E402

COVERAGE = EVIDENCE / "sprint-22d-w1-coverage.json"
ACQUISITION = EVIDENCE / "sprint-22d-w1-acquisition.json"
HOLDOUT_READ = EVIDENCE / "sprint-22d-w1-holdout-read.json"
HOLDOUT_FROZEN = EVIDENCE / "sprint-22d-holdout.json"

#: The cleared PDFs live outside the repository, so every test that reads them skips where they
#: are absent. The records they produced are committed and are asserted unconditionally.
_SOURCES_PRESENT = (Path.home() / "Letöltések" / "chemistry-2e_-_WEB.pdf").exists()
_NEEDS_SOURCES = pytest.mark.skipif(
    not _SOURCES_PRESENT, reason="the rights-cleared sources are not on this host"
)
_NEEDS_PHYSICS = pytest.mark.skipif(
    find_spec("pint") is None, reason="verification-physics extra is absent"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", [COVERAGE, ACQUISITION, HOLDOUT_READ])
def test_every_w1_seal_is_over_its_own_body(path: Path) -> None:
    record = _load(path)
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(canonical(body)).hexdigest() == record["integrity_content_hash"]


def test_the_holdout_was_not_re_cut_after_the_coverage_was_seen() -> None:
    """The whole integrity argument of this wave, in one assertion.

    W1 learned exactly which facts the cleared chapters hold. If that knowledge had been
    allowed to reshape the holdout, arm B's four would be four questions chosen to have
    answers. The frozen case hashes are W0's, and they are what says otherwise.
    """
    frozen = _load(HOLDOUT_FROZEN)
    assert frozen["case_hashes"] == case_hashes()
    assert frozen["measured_values"] == 0, "the frozen record still declares nothing measured"


def test_the_coverage_was_published_before_the_acquisition_that_used_it() -> None:
    coverage, acquisition = _load(COVERAGE), _load(ACQUISITION)
    assert coverage["items"] == ["S22D-100"]
    assert acquisition["items"] == ["S22D-101", "S22D-102"]
    # Same locators, same candidate count: the pricing describes the run that followed it
    # rather than a different configuration that happened to be cheaper to publish.
    assert coverage["candidates_located"] == acquisition["candidates_located"]
    assert coverage["refusals"] == acquisition["locator_refusals"]


def test_a_numeral_that_lost_its_exponent_is_refused_rather_than_repaired() -> None:
    """22C W3-D1: a value that cannot be read is a refusal with a name, never a guess."""
    with pytest.raises(NumeralRefused) as refusal:
        read_numeral("6.022 1023")
    assert refusal.value.reason == REFUSAL_MANGLED_EXPONENT
    assert read_numeral("39.10") == "39.10"


def test_a_sentence_fragment_is_refused_as_a_subject() -> None:
    with pytest.raises(NumeralRefused) as refusal:
        read_subject("chloroform, which")
    assert refusal.value.reason == REFUSAL_SUBJECT_NOT_AN_ENTITY
    assert read_subject("  an aspirin  molecule ") == "an aspirin molecule"


def test_both_refusal_reasons_fired_on_the_real_cleared_chapters() -> None:
    """22A W4-F2: a gate that has never refused anything is a gate nobody has tested."""
    reasons = _load(COVERAGE)["refusals_by_reason"]
    assert reasons[REFUSAL_MANGLED_EXPONENT] > 0
    assert reasons[REFUSAL_SUBJECT_NOT_AN_ENTITY] > 0


def test_every_candidate_and_every_refusal_left_an_extraction_decision() -> None:
    """`ExtractionDecisionOutcome` had no implementation; this is what it buys.

    A fact that is not in the store has to be distinguishable from a fact nobody looked for.
    """
    acquisition = _load(ACQUISITION)
    assert acquisition["every_candidate_left_a_decision"] is True
    assert acquisition["decisions_recorded"] == (
        acquisition["candidates_located"] + acquisition["locator_refusals"]
    )
    for entry in acquisition["decisions"]:
        decision = entry["decision"]
        assert decision["outcome"] in {"accepted", "rejected", "requires_review"}
        assert decision["reason_codes"], "a decision with no reason is not a decision"
        assert decision["decided_by"]["actor_id"]


def test_layer_one_was_materially_filled() -> None:
    acquisition = _load(ACQUISITION)
    assert acquisition["layer_1_before"] == 1
    assert acquisition["layer_1_after"] > acquisition["layer_1_before"]
    assert acquisition["materially_filled"] is True
    assert acquisition["by_ladder_status"][LADDER_CORROBORATED] > 0
    assert acquisition["by_ladder_status"][LADDER_GROUNDED] > 0


def test_the_two_stores_acquired_the_same_layer() -> None:
    """22C W2-F2's standing rule, and the reason it is a rule at all."""
    parity = _load(ACQUISITION)["parity"]
    assert parity["layers_identical"] is True
    assert parity["in_memory_retained"] == parity["postgres_retained"]
    assert _load(ACQUISITION)["store"]["migration_head"] == "0015"
    assert "://" not in _load(ACQUISITION)["store"]["database"], "no credential in evidence"


def test_the_holdout_was_read_once_and_the_arms_differ() -> None:
    read = _load(HOLDOUT_READ)
    assert read["read_once"] is True
    assert read["measured_values"] == len(HOLDOUT_CASES)
    assert read["arm_a_verified"] == 0, "22C's layer holds no declarative facts at all"
    assert read["arm_b_verified"] > read["arm_a_verified"]
    assert read["improvement"] == read["arm_b_verified"] - read["arm_a_verified"]


def test_every_refused_holdout_case_names_the_fact_it_wanted() -> None:
    """A refusal without a name is an absence, which is the thing this wave exists to end."""
    for case in _load(HOLDOUT_READ)["arms"]["arm_b"]["cases"]:
        if not case["answered"]:
            assert case["facts_missing"], case["case_id"]
            assert case["refusal_reason"] == "fact_not_in_acquired_layer"


def test_an_answered_holdout_case_derives_from_the_layer_not_from_the_withheld_value() -> None:
    """The non-circularity argument, asserted rather than described.

    Every answered case reports the facts it used, and each one names the subject *as the
    layer holds it* — `Cl`, not `chlorine`. A reading that had compared against the value the
    case withheld would have no such record to show.
    """
    frozen = {str(case["case_id"]): case for case in HOLDOUT_CASES}
    for case in _load(HOLDOUT_READ)["arms"]["arm_b"]["cases"]:
        if not case["answered"]:
            continue
        assert case["facts_used"], case["case_id"]
        required = {name for name, _ in DERIVATIONS[case["case_id"]][2]}
        assert {item["asked_as"] for item in case["facts_used"]} == required
        for item in case["facts_used"]:
            assert item["ladder_status"] in {LADDER_CORROBORATED, LADDER_GROUNDED}
        assert case["case_id"] in frozen


def test_the_derivation_table_covers_every_frozen_case_and_moves_no_hash() -> None:
    assert {str(case["case_id"]) for case in HOLDOUT_CASES} <= set(DERIVATIONS)
    assert (
        _load(HOLDOUT_FROZEN)["holdout_hash"]
        == hashlib.sha256(canonical(case_hashes())).hexdigest()
    )


def test_entity_ids_are_canonical_identifiers() -> None:
    from cognitive_os.semantic_memory.canonicalization import canonical_identifier

    assert canonical_identifier(_entity_id("average atomic mass", "Cl"))
    assert canonical_identifier(_entity_id("stated constant", "an aspirin molecule"))


def test_the_alias_step_resolves_the_asker_notation_to_the_source_notation() -> None:
    """W1-F3: the layer is keyed as the source writes, and asked as the asker speaks."""
    index = {"cl": {"subject": "Cl", "ladder_status": LADDER_CORROBORATED, "value": "35.45"}}
    assert _resolve("chlorine", index) is not None
    assert _resolve("Cl", index) is not None
    assert _resolve("sulfur", index) is None


@_NEEDS_SOURCES
def test_the_table_header_keeps_stoichiometric_subscripts_out_of_the_layer() -> None:
    """Chemistry chapter 4's `C` then `1` must never be read as an atomic mass."""
    candidates, _ = locate_all()
    from_chapter_four = [
        item for item in candidates if item.source_key == "chemistry" and item.chapter == 4
    ]
    assert from_chapter_four == [], "chapter 4 states no element masses and must yield none"
    masses = {
        item.subject: item.value for item in candidates if item.locator == "element_mass_table"
    }
    assert masses and all(float(value) > 1 for value in masses.values())


@_NEEDS_SOURCES
def test_the_element_mass_table_yields_every_row_it_prints() -> None:
    """A consumed trailing newline reads every other row, and nothing says so."""
    candidates, _ = locate_all()
    rows = {item.subject for item in candidates if item.locator == "element_mass_table"}
    assert rows == {"C", "H", "O", "Na", "Cl"}


@_NEEDS_SOURCES
def test_the_kernel_corroborates_only_where_the_source_prints_a_consequence() -> None:
    """§1.5: the kernel is a consistency oracle, not a recomputation, and never a tolerance."""
    candidates, _ = locate_all()
    for candidate in candidates:
        outcome = corroborate(candidate)
        if candidate.consequence_value is None:
            assert outcome["attempted"] is False
        else:
            assert outcome["kernel"] == "chemistry.molar-conversion"
            assert "never within a tolerance" in outcome["compared"]


@_NEEDS_SOURCES
@_NEEDS_PHYSICS
def test_the_in_memory_acquisition_reproduces_the_sealed_layer() -> None:
    from facts_22d import _layer_fingerprint, acquire, build_fact_composition

    result = asyncio.run(acquire(build_fact_composition()))
    assert _layer_fingerprint(result) == _layer_fingerprint(_load(ACQUISITION))
