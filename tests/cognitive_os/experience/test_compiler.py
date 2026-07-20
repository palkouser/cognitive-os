import json
from pathlib import Path

from cognitive_os.domain.experience import (
    CompilationDecisionType,
    ExperienceCandidateType,
    FirstIncorrectType,
    TrajectoryCompleteness,
)
from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.experience.fixtures import INITIAL_FIXTURES, build_fixture
from cognitive_os.verification.experience import verify_compilation


def _compile(name: str):
    request, sources, profiles = build_fixture(name)
    return ExperienceCompiler(sources, profiles).compile(request)


def test_initial_fixture_set_is_deterministic_and_governed() -> None:
    expected = json.loads(
        Path("tests/fixtures/experience/sprint14-expected.json").read_text(encoding="utf-8")
    )
    candidate_types = set()
    for name in INITIAL_FIXTURES:
        request, sources, profiles = build_fixture(name)
        compiler = ExperienceCompiler(sources, profiles)
        first = compiler.compile(request)
        second = compiler.compile(request)
        assert first.manifest == second.manifest
        assert not verify_compilation(first)
        assert all(candidate.status.value == "proposed" for candidate in first.candidates)
        assert all(candidate.target_subsystem for candidate in first.candidates)
        assert first.snapshot.content_hash == expected[name]["snapshot_hash"]
        assert first.trajectory.content_hash == expected[name]["reconstruction_hash"]
        assert first.manifest.content_hash == expected[name]["manifest_hash"]
        assert [item.candidate_type.value for item in first.candidates] == expected[name][
            "candidate_types"
        ]
        candidate_types.update(item.candidate_type for item in first.candidates)
    assert candidate_types == set(ExperienceCandidateType)


def test_repaired_trajectory_preserves_failure_correction_and_recovery() -> None:
    result = _compile("repaired-bug-fix")
    assert result.analysis.successful_path is not None
    assert result.analysis.failed_branches
    assert result.analysis.corrections
    assert result.analysis.recovery_paths[0].resolved
    assert result.analysis.first_incorrect_step.causal_origin.origin_type in {
        FirstIncorrectType.INCORRECT_TOOL_POSTCONDITION,
        FirstIncorrectType.UNKNOWN_CAUSAL_ORIGIN,
    }
    assert not result.analysis.first_incorrect_step.causal_origin.causal_claim_supported


def test_incomplete_and_conflicted_trajectories_fail_closed() -> None:
    incomplete = _compile("incomplete-history")
    conflicted = _compile("conflicting-verifier")
    assert incomplete.trajectory.completeness is TrajectoryCompleteness.INCOMPLETE
    assert conflicted.trajectory.completeness is TrajectoryCompleteness.CONFLICTED
    assert incomplete.decision.decision is CompilationDecisionType.UNVERIFIABLE
    assert conflicted.decision.decision is CompilationDecisionType.UNVERIFIABLE
    restricted = {
        ExperienceCandidateType.FAILURE_PATTERN,
        ExperienceCandidateType.NEGATIVE_EXAMPLE,
    }
    assert {item.candidate_type for item in incomplete.candidates} <= restricted
    assert {item.candidate_type for item in conflicted.candidates} <= restricted


def test_policy_denial_is_not_executed_or_promoted() -> None:
    result = _compile("unsafe-tool-request")
    denial = next(item for item in result.assessments if item.status.value == "denied")
    assert denial.policy_compliance.value == "non_compliant"
    assert result.analysis.first_incorrect_step.causal_origin.causal_claim_supported
    assert result.manifest.usage["provider_calls"] == 0
    assert all(item.status.value == "proposed" for item in result.candidates)
