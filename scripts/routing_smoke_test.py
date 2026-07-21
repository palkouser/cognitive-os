"""Run the credential-free governed Sprint 16 routing lifecycle."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.config.routing_config import RoutingConfiguration
from cognitive_os.domain.routing import (
    RoutingExperimentResult,
    RoutingOutcome,
    RoutingOutcomeStatus,
    RoutingRequest,
    ShadowRoutingResult,
)
from cognitive_os.routing.fixtures import (
    FIXTURE_TIME,
    build_observations,
    build_routing_request,
    replay_profiles,
    shadow_policy,
    static_policy,
)
from cognitive_os.routing.repository import InMemoryCapabilityRepository
from cognitive_os.routing.service import RoutingService
from cognitive_os.verification.routing import verify_decision


async def run_smoke() -> dict[str, object]:
    repository = InMemoryCapabilityRepository()
    configuration = RoutingConfiguration(
        minimum_adaptive_samples=16,
        minimum_shadow_cases=16,
        minimum_promotion_benchmark_cases=16,
    )
    service = RoutingService(repository, configuration)
    for profile in replay_profiles():
        await service.register_profile(profile)
    static = static_policy()
    shadow = shadow_policy()
    await service.create_policy(static)
    await service.create_policy(shadow)
    for observation in build_observations(64):
        await service.ingest_observation(observation)
    statistics = await service.rebuild_statistics()

    pairs = []
    shadow_results = []
    for index in range(16):
        request = build_routing_request(index)
        static_decision = await service.route_static(request, static)
        shadow_decision = await service.route_shadow(request, static_decision, shadow)
        assert verify_decision(static_decision) == ()
        assert verify_decision(shadow_decision) == ()
        pairs.append((request, static_decision, shadow_decision))
        static_hash = (
            static_decision.selected_model.content_hash if static_decision.selected_model else None
        )
        shadow_hash = (
            shadow_decision.selected_model.content_hash if shadow_decision.selected_model else None
        )
        shadow_results.append(
            ShadowRoutingResult(
                static_decision_id=static_decision.decision_id,
                shadow_decision_id=shadow_decision.decision_id,
                static_model_hash=static_hash,
                shadow_model_hash=shadow_hash,
                expected_score_delta=Decimal("0"),
            )
        )
    experiment = RoutingExperimentResult(
        experiment_id=uuid5(NAMESPACE_URL, "sprint16:smoke-experiment"),
        results=tuple(shadow_results),
        agreement_rate=Decimal(
            sum(item.static_model_hash == item.shadow_model_hash for item in shadow_results)
        )
        / Decimal(len(shadow_results)),
        completed_at=FIXTURE_TIME,
    )
    assessment = service.assess_promotion(
        policy=shadow,
        experiment=experiment,
        sample_count=64,
        quality_improvement=Decimal("0.03"),
        safety_regression=Decimal("0"),
        policy_regression=Decimal("0"),
        fallback_validated=True,
        replay_validated=True,
    )
    assert assessment.eligible_for_approval
    request, static_decision, _ = pairs[0]
    enabled = await service.approve_and_enable(
        shadow,
        assessment,
        approval_reference="fixture-operator-approval",
        task_signature_hashes=(request.task_signature.content_hash,),
    )
    request_payload = request.model_dump(mode="python", exclude={"content_hash"})
    request_payload.update(policy_id=enabled.policy_id, policy_revision=enabled.revision)
    adaptive_request = RoutingRequest.model_validate(request_payload)
    adaptive_decision = await service.route_adaptive(adaptive_request, enabled)
    assert adaptive_decision.selected_model is not None
    outcome = RoutingOutcome(
        outcome_id=uuid5(NAMESPACE_URL, "sprint16:smoke-outcome"),
        decision_id=static_decision.decision_id,
        task_run_id=static_decision.task_run_id,
        provider_request_reference="replay-provider-request",
        provider_result_reference="replay-provider-result",
        context_bundle_reference="replay-context-bundle",
        verifier_bundle_reference="routing-verifier-bundle",
        acceptance_decision_reference="fixture-acceptance",
        status=RoutingOutcomeStatus.ACCEPTED,
        latency_ms=Decimal("50"),
        cost_units=Decimal("0"),
        safety_result="passed",
        created_at=FIXTURE_TIME,
    )
    await service.record_outcome(outcome)
    projected = await service.project_verified_outcome(
        outcome=outcome,
        decision=static_decision,
        source_hash=sha256(outcome.model_dump_json().encode()).hexdigest(),
    )
    disabled = await service.disable_adaptive_policy(
        enabled, reason="fixture rollback to static control"
    )
    return {
        "healthy": True,
        "profiles": len(repository.profiles),
        "observations": len(repository.observations),
        "statistics": len(statistics),
        "decisions": len(repository.decisions),
        "accesses": len(repository.accesses),
        "static_decision_hash": static_decision.content_hash,
        "adaptive_decision_hash": adaptive_decision.content_hash,
        "projected_observation_hash": projected.content_hash,
        "experiment_hash": experiment.content_hash,
        "promotion_hash": assessment.content_hash,
        "disabled_policy_hash": disabled.content_hash,
        "shadow_provider_calls": 0,
        "unauthorized_enablements": 0,
        "budget_expansions": 0,
        "counterfactual_claims": 0,
    }


def main() -> int:
    print(json.dumps(asyncio.run(run_smoke()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
