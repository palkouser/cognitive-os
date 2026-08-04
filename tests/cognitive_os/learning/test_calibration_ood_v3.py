from __future__ import annotations

from decimal import Decimal
from itertools import product

import pytest

from cognitive_os.learning.calibration_ood import (
    OodCaseManifestV3,
    OodCaseResultV3,
    OodSubmanifestV3,
    build_ood_precheck_v3,
    rename_identifiers,
    transformation_case_id,
)
from cognitive_os.learning.correction_protocol import CorrectionEvaluationCountsV3


def _manifest() -> OodSubmanifestV3:
    source_hash = "a" * 64
    cases = []
    for group, case in product(range(10), range(5)):
        group_id = f"group-{group:02d}"
        case_name = f"case-{case}"
        seed = 21041 + case
        cases.append(
            OodCaseManifestV3(
                case_id=transformation_case_id(
                    stage="calibration",
                    source_group_id=group_id,
                    case_name=case_name,
                    seed=seed,
                ),
                stage="calibration",
                source_group_id=group_id,
                case_name=case_name,
                transformations=("identifier_rename", "issue_rewrite")[: 1 + case % 2],
                seed=seed,
                candidate_ids=tuple(f"{group_id}-{case_name}-candidate-{i}" for i in range(4)),
                source_manifest_hash=source_hash,
            )
        )
    return OodSubmanifestV3(
        stage="calibration",
        source_manifest_hash=source_hash,
        generator_code_hash="b" * 64,
        hard_coded_oracle_hash="c" * 64,
        cases=tuple(cases),
    )


def test_ten_groups_and_fifty_cases_are_fifty_decisions_and_two_hundred_outcomes() -> None:
    manifest = _manifest()
    results = tuple(
        OodCaseResultV3(
            case_id=case.case_id,
            source_group_id=case.source_group_id,
            clean_answered=True,
            answered=True,
            abstained=False,
            clean_first_choice_correct=index % 10 != 0,
            baseline_first_choice_correct=index % 4 == 0,
            clean_changed_action=index == 0,
            action_preserved=True,
            transformed_changed_action=index == 0,
        )
        for index, case in enumerate(manifest.cases)
    )

    report = build_ood_precheck_v3(manifest, results)

    assert report.counts.task_groups == 10
    assert report.counts.metamorphic_cases == 50
    assert report.counts.ranking_decisions == 50
    assert report.counts.candidate_outcomes == 200
    assert report.counts.answered_decisions == 50
    assert report.confident_error_rate_all_decisions == 0
    assert report.confident_error_rate_answered_decisions == 0
    assert report.selection_eligible


def test_candidate_slots_cannot_be_relabelled_as_decisions() -> None:
    with pytest.raises(ValueError, match="candidate outcomes must equal decisions x four"):
        CorrectionEvaluationCountsV3(
            task_groups=10,
            metamorphic_cases=200,
            ranking_decisions=200,
            candidate_outcomes=200,
            answered_decisions=200,
            abstained_decisions=0,
            changed_actions=0,
            confident_errors=0,
        )


def test_silence_and_confident_error_both_fail_selection_with_named_denominators() -> None:
    manifest = _manifest()
    results = tuple(
        OodCaseResultV3(
            case_id=case.case_id,
            source_group_id=case.source_group_id,
            clean_answered=True,
            answered=index < 39,
            abstained=index >= 39,
            clean_first_choice_correct=True,
            baseline_first_choice_correct=False,
            clean_changed_action=index == 0,
            action_preserved=True if index < 39 else None,
            confident_error=index == 0,
        )
        for index, case in enumerate(manifest.cases)
    )

    report = build_ood_precheck_v3(manifest, results)

    assert report.confident_error_rate_all_decisions == Decimal(1) / Decimal(50)
    assert report.confident_error_rate_answered_decisions == Decimal(1) / Decimal(39)
    assert not report.selection_eligible
    assert "equivalence_coverage_below_floor" in report.ineligible_reasons
    assert "confident_equivalence_error" in report.ineligible_reasons


def test_case_identity_binds_group_composition_seed_candidates_and_manifest() -> None:
    manifest = _manifest()
    case = manifest.cases[0]
    payload = case.model_dump(exclude={"content_hash"})
    payload["source_group_id"] = "other-group"

    with pytest.raises(ValueError, match="case identity"):
        OodCaseManifestV3(**payload)

    payload = case.model_dump(exclude={"content_hash"})
    payload["candidate_ids"] = ("same",) * 4
    with pytest.raises(ValueError, match="distinct candidates"):
        OodCaseManifestV3(**payload)


def test_independent_rename_generator_has_a_hard_coded_golden_pair() -> None:
    source = "def add(left, right):\n    total = left + right\n    return total\n"
    expected = "def q0(q1, q2):\n    q3 = q1 + q2\n    return q3\n"

    assert rename_identifiers(source) == (expected,)
