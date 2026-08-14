"""S22C-W0: the campaign drivers' properties, held where they can fail.

These are fences rather than coverage. Each one holds a rule the sprint's evidence depends
on, and each was written because the rule could plausibly be broken by a later wave without
anyone noticing:

*A cycle is nine stages in order.* The runner is fed an out-of-order stage and has to refuse;
without this, "three completed cycles" could quietly become three partial passes.

*The rights gate refuses.* Four ways, including the one that looks cleared — a clearance
issued against different bytes.

*The holdout is separated by construction.* `campaign_22c` must not import `holdout_22c`, so
a wave that reaches for a holdout case as curriculum breaks the suite instead of the exit
(22B W1-F6).

*The cross-check has two legs, and the second one is load-bearing.* The plant's derivation is
accepted by the released checker; only the assertion comparison refuses it. A test that
asserted merely "the plant is quarantined" would keep passing if that leg were deleted.

*A refused case is data, not an exception.* W0-F5's guard, held directly, because the
holdout's arm A is a refusal by design.

Everything here runs in memory and registers the two committed pilot packages, so it runs in
CI, where no 22C store exists.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
SCRIPTS = REPOSITORY / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


campaign = _module("campaign_22c")
holdout = _module("holdout_22c")

from cognitive_os.domain.campaigns import (  # noqa: E402
    CAMPAIGN_STAGES,
    CampaignManifestV1,
    CampaignSourceRights,
    CampaignStage,
    RightsClearanceStatus,
)
from cognitive_os.domain.corpus import CorpusUsageRight  # noqa: E402

# --- the cycle is nine stages, in order ------------------------------------


def test_the_stage_enumeration_is_the_development_plans_nine() -> None:
    assert [stage.value for stage in CAMPAIGN_STAGES] == [
        "register_source",
        "extract",
        "normalize",
        "cross_check",
        "quarantine",
        "compile",
        "evaluate",
        "promote",
        "observe",
    ]


def test_the_runner_refuses_a_stage_out_of_order() -> None:
    state = campaign.CycleState(manifest=campaign.fixture_manifest())
    runner = campaign.CycleRunner(state)
    with pytest.raises(campaign.StageOutOfOrder):
        runner.enter(CampaignStage.PROMOTE)


def test_the_runner_refuses_a_skipped_stage_midway() -> None:
    state = campaign.CycleState(manifest=campaign.fixture_manifest())
    runner = campaign.CycleRunner(state)
    runner.enter(CampaignStage.REGISTER_SOURCE)
    runner.leave(CampaignStage.REGISTER_SOURCE)
    # Skipping `extract` to reach `normalize` is the failure this fence exists for.
    with pytest.raises(campaign.StageOutOfOrder):
        runner.enter(CampaignStage.NORMALIZE)


def test_a_partial_pass_is_not_a_complete_cycle() -> None:
    state = campaign.CycleState(manifest=campaign.fixture_manifest())
    runner = campaign.CycleRunner(state)
    for stage in CAMPAIGN_STAGES[:-1]:
        runner.enter(stage)
        runner.leave(stage)
    assert runner.complete is False


# --- the rights gate --------------------------------------------------------


def test_the_gate_refuses_a_source_with_no_clearance() -> None:
    with pytest.raises(campaign.RightsNotCleared):
        campaign.rights_gate(None, campaign.fixture_source_hash())


def test_the_gate_refuses_a_clearance_issued_against_different_bytes() -> None:
    # The dangerous case: it looks cleared.
    with pytest.raises(campaign.RightsNotCleared):
        campaign.rights_gate(campaign.fixture_rights(), "0" * 64)


def test_the_gate_admits_a_matching_clearance() -> None:
    campaign.rights_gate(campaign.fixture_rights(), campaign.fixture_source_hash())


def test_the_contract_cannot_hold_an_unconcluded_review() -> None:
    with pytest.raises(ValueError, match="concluded clearance"):
        CampaignSourceRights(
            status=RightsClearanceStatus.NOT_CLEARED,
            source_content_hash="0" * 64,
            edition="1",
            author="unknown",
            location="unknown",
            license_identifier="unknown",
            permitted_uses=(CorpusUsageRight.INTERNAL_USE,),
            cleared_by="nobody",
            cleared_at=campaign.SLICE_TIME,
            evidence_hash="0" * 64,
        )


def test_a_manifest_cannot_declare_a_use_its_clearance_does_not_permit() -> None:
    manifest = campaign.fixture_manifest()
    with pytest.raises(ValueError, match="does not permit"):
        CampaignManifestV1(
            **{
                **manifest.model_dump(exclude={"content_hash"}),
                "declared_uses": (CorpusUsageRight.PUBLIC_RELEASE,),
            }
        )


# --- the holdout is separated by construction -------------------------------


def test_the_campaign_driver_does_not_import_the_holdout() -> None:
    """22B W1-F6 as a structural fence, not a review note."""
    source = (SCRIPTS / "campaign_22c.py").read_text(encoding="utf-8")
    assert "holdout_22c" not in source
    assert "HOLDOUT_CASES" not in source


def test_a_manifest_refuses_a_holdout_case_that_is_also_curriculum() -> None:
    manifest = campaign.fixture_manifest()
    shared = manifest.curriculum.segment_hashes[0]
    body = manifest.model_dump(exclude={"content_hash"})
    # The nested holdout carries its own seal; rebuilding it with a changed field must drop
    # that seal, or the contract refuses for hash mismatch before the disjointness rule runs.
    body["holdouts"][0].pop("content_hash")
    body["holdouts"][0]["case_hashes"] = (shared,)
    with pytest.raises(ValueError, match="shares"):
        CampaignManifestV1(**body)


def test_the_holdout_names_a_store_of_its_own() -> None:
    assert holdout.STORE_URL_ENV == "COGOS_HOLDOUT_DATABASE_URL"
    definition = holdout.holdout_definition()
    assert definition["measured_values"] == 0
    assert definition["case_count"] == len(holdout.HOLDOUT_CASES)
    assert sorted(definition["separation"]) == ["by_hash", "by_module", "by_store", "standing_rule"]


def test_every_holdout_case_withholds_exactly_one_declared_fact() -> None:
    for case in holdout.HOLDOUT_CASES:
        assert case.withheld_key not in case.formal_inputs, case.case_id
        restored = case.arm_b_inputs(case.withheld_value)
        assert restored[case.withheld_key] == case.withheld_value
        assert set(restored) - set(case.formal_inputs) == {case.withheld_key}


def test_holdout_case_hashes_are_unique_and_stable() -> None:
    hashes = holdout.case_hashes()
    assert len(set(hashes)) == len(hashes)
    assert hashes == holdout.case_hashes()


# --- the plant and the two-legged cross-check -------------------------------


def test_the_plant_travels_inside_the_ordinary_intake_stream() -> None:
    segments = campaign.all_segments()
    assert campaign.PLANT in segments
    # Not appended as a distinguishable tail: a stage must not be able to tell it apart by
    # position any more than by shape.
    assert campaign.PLANT.problem_type in {
        item.problem_type for item in segments if item is not campaign.PLANT
    }


def test_the_released_checker_accepts_the_plants_derivation() -> None:
    """W0-F4, held directly: the checker is not what refuses the plant."""
    campaign.register_pilots()
    run = asyncio.run(
        campaign.attempt_case(campaign.PLANT.problem_type, campaign.PLANT.formal_inputs)
    )
    assert run.accepted is True
    assert run.candidate["structured"]["balanced"] is False


def test_the_assertion_leg_is_what_refuses_the_plant() -> None:
    campaign.register_pilots()
    run = asyncio.run(
        campaign.attempt_case(campaign.PLANT.problem_type, campaign.PLANT.formal_inputs)
    )
    agrees, reason = campaign.assertion_agrees(campaign.PLANT.asserted, run.candidate)
    assert agrees is False
    assert "the source asserts" in reason


def test_the_assertion_leg_agrees_with_every_genuine_segment() -> None:
    campaign.register_pilots()
    for segment in campaign.all_segments():
        if segment is campaign.PLANT:
            continue
        run = asyncio.run(campaign.attempt_case(segment.problem_type, segment.formal_inputs))
        agrees, reason = campaign.assertion_agrees(segment.asserted, run.candidate)
        assert agrees is True, f"{segment.segment_id}: {reason}"


def test_the_plant_content_hash_is_stable() -> None:
    assert campaign.PLANT.content_hash == (
        "24da0165a9ed8e13b3af71abbd08b8f2f5f4cff93facf5308348a4f39bb14973"
    )


# --- a refused case is data --------------------------------------------------


def test_a_refused_case_returns_a_refusal_rather_than_raising() -> None:
    """W0-F5. The holdout's arm A depends on this exact behaviour."""
    campaign.register_pilots()
    outcome = asyncio.run(
        campaign.attempt_case(
            "chemistry.molar-conversion",
            {"formula": "O2", "mass": {"magnitude": 96, "unit": "g"}},
        )
    )
    assert outcome.refused_before_solving is True
    assert outcome.accepted is False
    assert "atomic_masses" in outcome.message


def test_an_unregistered_problem_type_is_also_data() -> None:
    outcome = asyncio.run(campaign.attempt_case("nothing.at-all", {}))
    assert outcome.accepted is False
    assert outcome.domain_id == "unregistered"


# --- the recipes -------------------------------------------------------------


def test_the_recipes_hash_covers_the_readings_not_the_modules_bytes() -> None:
    """22B W1-F2: a defect fix in a driver must not be a contract violation."""
    first = campaign.contracts_hash()
    assert first == campaign.contracts_hash()
    assert len(first) == 64


def test_the_replay_enumerates_every_registered_domain() -> None:
    from cognitive_os.domains import registry

    campaign.register_pilots()
    replay = asyncio.run(campaign.replay_all_domains())
    assert replay["enumeration_source"] == "registry.domain_ids()"
    assert set(replay["per_domain"]) == set(registry.domain_ids())
    # A domain with no retained cases is reported, never omitted (22A W4-F1).
    assert any(item["cases"] == 0 for item in replay["per_domain"].values())
    assert replay["all_retained_cases_passed"] is True
