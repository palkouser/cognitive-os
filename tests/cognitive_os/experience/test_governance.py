from hashlib import sha256

import pytest
from pydantic import ValidationError

from cognitive_os.config.experience_config import ExperienceConfiguration
from cognitive_os.domain.experience import ExperienceCandidateStatus, TrajectorySourceRef
from cognitive_os.experience.errors import ExperiencePolicyError
from cognitive_os.experience.fixtures import build_fixture
from cognitive_os.experience.governance import (
    append_candidate_status,
    export_candidate,
    validate_candidate,
)
from cognitive_os.experience.provider_analysis import parse_provider_proposals


def test_configuration_and_source_contracts_fail_closed() -> None:
    with pytest.raises(ValidationError):
        ExperienceConfiguration(allow_automatic_promotion=True)
    with pytest.raises(ValidationError):
        ExperienceConfiguration.model_validate({"unknown": True})
    request, _, _ = build_fixture("direct-success")
    source = request.trajectory_sources[0]
    with pytest.raises(ValidationError):
        TrajectorySourceRef.model_validate(
            {
                **source.model_dump(mode="python", exclude={"content_hash"}),
                "source_id": "/host/private/source",
            }
        )


def test_candidate_validation_lifecycle_and_export_are_destination_safe() -> None:
    request, sources, profiles = build_fixture("repaired-bug-fix")
    from cognitive_os.experience.compiler import ExperienceCompiler

    result = ExperienceCompiler(sources, profiles).compile(request)
    candidate = result.candidates[0]
    assert not validate_candidate(candidate, result.snapshot.content_hash)
    validated = append_candidate_status(
        candidate,
        (),
        ExperienceCandidateStatus.VALIDATED,
        actor_id="operator",
        reason="compiler verification passed",
    )
    with pytest.raises(ExperiencePolicyError):
        append_candidate_status(
            candidate,
            (validated,),
            ExperienceCandidateStatus.PROPOSED,
            actor_id="operator",
            reason="invalid rollback",
        )
    package = export_candidate(candidate)
    assert set(package) == {
        "candidate.json",
        "candidate-body.json",
        "sources.json",
        "evidence.json",
        "generalizability.json",
        "limitations.json",
        "verification.json",
        "manifest.json",
    }
    assert b'"destination_write_performed":false' in package["manifest.json"]


def test_provider_fabrication_causality_and_authority_are_rejected() -> None:
    evidence = sha256(b"evidence").hexdigest()
    allowed = frozenset({evidence})
    valid = [
        {
            "proposal_type": "lesson",
            "summary": "A bounded proposal",
            "evidence_refs": [evidence],
        }
    ]
    assert len(parse_provider_proposals(valid, allowed_evidence=allowed)) == 1
    with pytest.raises(ExperiencePolicyError, match="fabricated"):
        parse_provider_proposals(
            [{**valid[0], "evidence_refs": [sha256(b"fake").hexdigest()]}],
            allowed_evidence=allowed,
        )
    with pytest.raises(ExperiencePolicyError, match="causal"):
        parse_provider_proposals([{**valid[0], "causal_claim": True}], allowed_evidence=allowed)
    with pytest.raises(ValidationError):
        parse_provider_proposals(
            [{**valid[0], "destination_action": "promote"}], allowed_evidence=allowed
        )
