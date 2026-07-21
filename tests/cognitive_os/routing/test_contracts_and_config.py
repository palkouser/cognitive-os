from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.config.routing_config import RoutingConfiguration, load_routing_configuration
from cognitive_os.domain.routing import ModelIdentity, RoutingControlMode
from cognitive_os.routing.fixtures import build_routing_request
from cognitive_os.routing.service import build_task_signature, cohort_chain


def test_routing_configuration_is_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "routing.yaml"
    path.write_text("routing:\n  shadow_routing_enabled: true\n", encoding="utf-8")
    assert load_routing_configuration(path).shadow_routing_enabled
    with pytest.raises(ValidationError):
        RoutingConfiguration(adaptive_execution_enabled=True)
    with pytest.raises(ValidationError):
        RoutingConfiguration(learned_routing_enabled=True)


def test_identity_and_task_signature_are_immutable_and_deterministic() -> None:
    identity = ModelIdentity(
        provider_id="replay",
        model_id="fixture",
        model_revision="1",
        endpoint_profile="offline",
        execution_mode="replay",
    )
    assert identity.content_hash == ModelIdentity.model_validate(identity.model_dump()).content_hash
    first = build_task_signature(
        problem_domain="coding",
        problem_class="repair",
        output_type="diff",
        required_tool_capabilities=("workspace.patch", "repository.search"),
    )
    second = build_task_signature(
        problem_domain="coding",
        problem_class="repair",
        output_type="diff",
        required_tool_capabilities=("repository.search", "workspace.patch"),
    )
    assert first == second
    assert [item.cohort_level for item in cohort_chain(first)] == [
        "exact",
        "without_skill_revisions",
        "problem_class_output_repository",
        "domain_output_risk",
        "domain",
        "global",
    ]
    request_payload = build_routing_request().model_dump()
    request_payload["prompt"] = "not allowed"
    with pytest.raises(ValidationError):
        type(build_routing_request()).model_validate(request_payload)
    assert RoutingControlMode.STATIC.value == "static"
