"""Host-owned deterministic skill precondition evaluation."""

import json
from collections.abc import Callable
from hashlib import sha256

from cognitive_os.domain.skills import (
    SkillApplicabilityInput,
    SkillApplicabilityResult,
    SkillApplicabilityStatus,
    SkillPrecondition,
    SkillPreconditionResult,
    SkillPreconditionType,
    SkillRevision,
)

from .errors import SkillError

type Evaluator = Callable[[SkillPrecondition, SkillApplicabilityInput], tuple[bool, str]]


def _allowed(value: object, allowed: object) -> bool:
    values = allowed if isinstance(allowed, list) else [allowed]
    return "*" in values or value in values


def _evaluate(precondition: SkillPrecondition, value: SkillApplicabilityInput) -> tuple[bool, str]:
    kind, parameters = precondition.precondition_type, precondition.parameters
    if kind is SkillPreconditionType.PROBLEM_DOMAIN_MATCH:
        passed = _allowed(value.problem_domain, parameters["allowed"])
    elif kind is SkillPreconditionType.PROBLEM_SIGNATURE_MATCH:
        signature = sha256(
            json.dumps(
                {
                    "problem_domain": value.problem_domain,
                    "task_type": value.task_type,
                    "repository_language": value.repository_language,
                    "repository_profile": value.repository_profile,
                    "requested_output_type": value.requested_output_type,
                    "risk_level": value.risk_level,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        passed = signature == parameters["signature_hash"]
    elif kind is SkillPreconditionType.REPOSITORY_PROFILE_MATCH:
        passed = value.repository_profile is not None and _allowed(
            value.repository_profile, parameters["allowed"]
        )
    elif kind is SkillPreconditionType.ARTIFACT_PRESENCE:
        passed = parameters["artifact_type"] in value.available_artifact_types
    elif kind is SkillPreconditionType.TOOL_CAPABILITY:
        passed = parameters["capability"] in value.tool_capabilities
    elif kind is SkillPreconditionType.VERIFIER_CAPABILITY:
        passed = parameters["capability"] in value.verifier_capabilities
    elif kind is SkillPreconditionType.PROVIDER_CAPABILITY:
        passed = parameters["capability"] in value.provider_capabilities
    elif kind is SkillPreconditionType.SCOPE_MATCH:
        passed = parameters["scope_type"] == value.scope.scope_type.value
    elif kind is SkillPreconditionType.RISK_CEILING:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        passed = order.get(value.risk_level, 99) <= order.get(str(parameters["maximum"]), -1)
    elif kind is SkillPreconditionType.EXPLICIT_PERMISSION:
        passed = parameters["permission"] in value.permissions
    else:
        passed = parameters["flag"] in value.feature_flags
    return passed, "matched" if passed else f"{kind.value}_not_satisfied"


class PreconditionEvaluatorRegistry:
    def __init__(self) -> None:
        self._evaluators: dict[SkillPreconditionType, Evaluator] = {}
        self._frozen = False

    def register(self, kind: SkillPreconditionType, evaluator: Evaluator) -> None:
        if self._frozen or kind in self._evaluators:
            raise SkillError("precondition evaluator registry is frozen or duplicated")
        self._evaluators[kind] = evaluator

    def register_defaults(self) -> None:
        for kind in SkillPreconditionType:
            self.register(kind, _evaluate)

    def freeze(self) -> None:
        self._frozen = True

    def snapshot_hash(self) -> str:
        encoded = ",".join(sorted(item.value for item in self._evaluators)).encode()
        return sha256(encoded).hexdigest()

    def evaluate(
        self, revision: SkillRevision, value: SkillApplicabilityInput
    ) -> SkillApplicabilityResult:
        results = []
        for precondition in sorted(revision.preconditions, key=lambda item: item.precondition_id):
            evaluator = self._evaluators.get(precondition.precondition_type)
            if evaluator is None:
                passed, reason = False, "evaluator_unavailable"
            else:
                passed, reason = evaluator(precondition, value)
            evidence = json.dumps(
                {"input": value.model_dump(mode="json"), "parameters": precondition.parameters},
                sort_keys=True,
                separators=(",", ":"),
            )
            results.append(
                SkillPreconditionResult(
                    precondition_id=precondition.precondition_id,
                    passed=passed,
                    reason_code=reason,
                    evidence_hash=sha256(evidence.encode()).hexdigest(),
                )
            )
        required = {item.precondition_id: item.required for item in revision.preconditions}
        passed = all(item.passed or not required[item.precondition_id] for item in results)
        permission_missing = any(
            item.reason_code.startswith("explicit_permission") for item in results
        )
        status = SkillApplicabilityStatus.APPLICABLE
        if not passed:
            status = (
                SkillApplicabilityStatus.REQUIRES_PERMISSION
                if permission_missing
                else SkillApplicabilityStatus.INAPPLICABLE
            )
        return SkillApplicabilityResult(
            skill_id=revision.skill_id,
            revision=revision.revision,
            status=status,
            results=tuple(results),
        )
