"""Controller plan structural and registry validation."""

from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.config.controller_config import ControllerConfiguration
from cognitive_os.domain.controller import ControllerActionType, ControllerBudget
from cognitive_os.domain.identifiers import new_id
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.planning import ControllerExecutionPlan
from cognitive_os.domain.problems import ProblemRepresentation
from cognitive_os.domain.provider import ResponseFormat
from cognitive_os.problem.plan_prompting import plan_instructions
from cognitive_os.providers.registry import ProviderRegistry
from cognitive_os.tools.registry import ToolRegistry


class PlanValidationService:
    def __init__(
        self,
        providers: ProviderRegistry,
        tools: ToolRegistry,
        *,
        verifier_ids: tuple[str, ...] = (
            "minimal.schema",
            "minimal.artifact_exists",
            "minimal.step_completed",
            "minimal.tool_succeeded",
        ),
    ) -> None:
        self._providers = providers
        self._tools = tools
        self._verifier_ids = frozenset(verifier_ids)

    def validate(
        self, plan: ControllerExecutionPlan, budget: ControllerBudget
    ) -> ControllerExecutionPlan:
        if len(plan.plan.steps) > budget.maximum_plan_steps:
            raise ValueError("controller plan exceeds the plan-step budget")
        for action in plan.actions:
            if action.action_type is ControllerActionType.PROVIDER and action.provider_id:
                self._providers.require(action.provider_id)
            elif action.action_type is ControllerActionType.TOOL:
                self._tools.require(action.tool_id or "", action.tool_version or "")
            elif (
                action.action_type is ControllerActionType.VERIFICATION
                and set(action.verifier_ids) - self._verifier_ids
            ):
                raise ValueError("controller plan references an unknown verifier")
        return plan


class PlanService:
    def __init__(
        self,
        model_execution: ModelExecutionService,
        validation: PlanValidationService,
        configuration: ControllerConfiguration,
        *,
        requested_model: str,
    ) -> None:
        self._models = model_execution
        self._validation = validation
        self._configuration = configuration
        self._requested_model = requested_model

    async def create_plan(
        self, problem: ProblemRepresentation, budget: ControllerBudget
    ) -> ControllerExecutionPlan:
        if not problem.is_executable():
            raise ValueError("planning requires an executable problem representation")
        model_call_id = new_id()
        request = ModelProviderRequest(
            model_call_id=model_call_id,
            task_run_id=problem.task_run_id,
            correlation_id=model_call_id,
            requested_model=self._requested_model,
            messages=(
                ProviderMessage(
                    role=ProviderMessageRole.USER,
                    content=plan_instructions(problem, budget),
                ),
            ),
            response_format=ResponseFormat.JSON_SCHEMA,
            response_schema=ControllerExecutionPlan.model_json_schema(),
            max_output_tokens=min(
                self._configuration.budgets.maximum_output_tokens or 32768, 32768
            ),
            metadata={"operation": "controller_plan"},
        )
        response = await self._models.execute(
            request, provider_id=self._configuration.planning_provider_id
        )
        if response.tool_calls:
            raise ValueError("planning response cannot execute tools")
        return self._validation.validate(
            ControllerExecutionPlan.model_validate(response.structured_output), budget
        )

    async def revise_plan(
        self,
        current: ControllerExecutionPlan,
        reason: str,
        budget: ControllerBudget,
    ) -> ControllerExecutionPlan:
        model_call_id = new_id()
        request = ModelProviderRequest(
            model_call_id=model_call_id,
            task_run_id=current.plan.task_run_id,
            correlation_id=model_call_id,
            requested_model=self._requested_model,
            messages=(
                ProviderMessage(
                    role=ProviderMessageRole.USER,
                    content=(
                        "Revise the supplied plan to address the sanitized failure. Preserve "
                        f"permissions and increment version. Failure: {reason}. "
                        f"Plan: {current.model_dump_json()}"
                    ),
                ),
            ),
            response_format=ResponseFormat.JSON_SCHEMA,
            response_schema=ControllerExecutionPlan.model_json_schema(),
            max_output_tokens=min(
                self._configuration.budgets.maximum_output_tokens or 32768, 32768
            ),
            metadata={"operation": "controller_plan_repair"},
        )
        response = await self._models.execute(
            request, provider_id=self._configuration.planning_provider_id
        )
        revised = self._validation.validate(
            ControllerExecutionPlan.model_validate(response.structured_output), budget
        )
        if (
            revised.plan.plan_id != current.plan.plan_id
            or revised.plan.version != current.plan.version + 1
        ):
            raise ValueError("repair plan must preserve identity and increment version")
        old_tools = {(item.tool_id, item.tool_version) for item in current.actions if item.tool_id}
        new_tools = {(item.tool_id, item.tool_version) for item in revised.actions if item.tool_id}
        if not new_tools <= old_tools:
            raise ValueError("repair plan cannot broaden tool permissions")
        return revised
