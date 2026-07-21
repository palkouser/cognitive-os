from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognitive_os.domain.routing import (
    ExecutionRole,
    MultiModelPattern,
    MultiModelPatternType,
    MultiModelRole,
    RoutingBudget,
    RoutingControlMode,
    RoutingPolicyRevision,
    RoutingPolicyStatus,
)
from cognitive_os.routing.errors import RoutingPolicyError
from cognitive_os.routing.fixtures import FIXTURE_TIME
from cognitive_os.routing.service import (
    RoutingService,
    classify_failure,
    fallback_allowed,
    intersect_budgets,
)


def test_adaptive_policy_requires_operator_approval() -> None:
    with pytest.raises(ValidationError):
        RoutingPolicyRevision(
            policy_id="adaptive",
            revision=1,
            status=RoutingPolicyStatus.ENABLED,
            control_mode=RoutingControlMode.ADAPTIVE,
            created_at=FIXTURE_TIME,
            created_by="provider",
            reason="provider cannot enable itself",
        )


def test_budget_intersection_and_uncertain_side_effect_fallback() -> None:
    effective = intersect_budgets(
        RoutingBudget(maximum_calls=8, maximum_tokens=10_000),
        RoutingBudget(maximum_calls=2, maximum_tokens=5_000),
    )
    assert effective.maximum_calls == 2
    assert effective.maximum_tokens == 5_000
    reason = classify_failure("timeout_after_uncertain_side_effect")
    assert not fallback_allowed(reason)


def test_multi_model_plan_cannot_expand_controller_budget() -> None:
    pattern = MultiModelPattern(
        pattern_type=MultiModelPatternType.PLANNER_EXECUTOR,
        roles=(ExecutionRole.PLANNER, ExecutionRole.EXECUTOR),
    )
    roles = tuple(
        MultiModelRole(
            role=role,
            routing_request_id=uuid4(),
            routing_decision_id=uuid4(),
            context_bundle_reference=f"context-{role.value}",
            token_reservation=1_000,
        )
        for role in pattern.roles
    )
    with pytest.raises(RoutingPolicyError):
        RoutingService.build_multi_model_plan(
            plan_id=uuid4(),
            pattern=pattern,
            roles=roles,
            controller_budget=RoutingBudget(maximum_calls=1),
            policy_budget=RoutingBudget(maximum_calls=8),
            strategy_budget=RoutingBudget(maximum_calls=8),
            pattern_budget=RoutingBudget(maximum_calls=8),
            verifier_reference="routing.multi_model_budget",
            controller_plan_reference="controller-plan",
        )
