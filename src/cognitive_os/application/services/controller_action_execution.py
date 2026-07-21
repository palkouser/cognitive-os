"""Provider and Tool Plane adapters for planned controller actions."""

from collections.abc import Callable
from datetime import UTC, datetime

from cognitive_os.application.ports.context_builder import ContextBuilderPort
from cognitive_os.application.ports.controller import StartControllerRequest
from cognitive_os.application.ports.model_router import ModelRouterPort
from cognitive_os.application.services.cognitive_controller import ActionOutcome
from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.application.services.tool_execution import ToolExecutionService
from cognitive_os.config.controller_config import ControllerConfiguration
from cognitive_os.context.rendering import compose_context_messages
from cognitive_os.domain.context import ContextRequest
from cognitive_os.domain.controller import ControllerActionType
from cognitive_os.domain.identifiers import new_id
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.planning import ControllerStepAction
from cognitive_os.domain.provider import ResponseFormat
from cognitive_os.domain.routing import RoutingPolicyRevision, RoutingReference, RoutingRequest
from cognitive_os.domain.tools import ToolExecutionContext, ToolExecutionStatus, ToolInvocation


class SequentialActionExecutionService:
    def __init__(
        self,
        model_execution: ModelExecutionService,
        tool_execution: ToolExecutionService,
        configuration: ControllerConfiguration,
        *,
        workspace: str,
        context_builder: ContextBuilderPort | None = None,
        context_request_factory: Callable[
            [ControllerStepAction, StartControllerRequest], ContextRequest
        ]
        | None = None,
        model_router: ModelRouterPort | None = None,
        routing_factory: Callable[
            [ControllerStepAction, StartControllerRequest],
            tuple[RoutingRequest, RoutingPolicyRevision],
        ]
        | None = None,
    ) -> None:
        self._models = model_execution
        self._tools = tool_execution
        self._configuration = configuration
        self._workspace = workspace
        if (context_builder is None) != (context_request_factory is None):
            raise ValueError("Context Builder and request factory must be configured together")
        self._context_builder = context_builder
        self._context_request_factory = context_request_factory
        if (model_router is None) != (routing_factory is None):
            raise ValueError("model router and routing factory must be configured together")
        self._model_router = model_router
        self._routing_factory = routing_factory

    async def execute(
        self, action: ControllerStepAction, request: StartControllerRequest
    ) -> ActionOutcome:
        if action.action_type is ControllerActionType.PROVIDER:
            return await self._provider(action, request)
        if action.action_type is ControllerActionType.TOOL:
            return await self._tool(action, request)
        if action.action_type is ControllerActionType.VERIFICATION:
            return ActionOutcome(succeeded=True)
        return ActionOutcome(succeeded=False, warning="manual action requires a durable pause")

    async def _provider(
        self, action: ControllerStepAction, request: StartControllerRequest
    ) -> ActionOutcome:
        model_call_id = new_id()
        structured = action.response_schema is not None
        instruction = action.provider_instructions or "Execute the bounded plan step."
        context_reference = None
        context_request: ContextRequest | None = None
        context_budget = 32768
        reserved_output_tokens = 32768
        messages: tuple[ProviderMessage, ...] = (
            ProviderMessage(role=ProviderMessageRole.USER, content=instruction),
        )
        requested_model = action.requested_model or "default"
        provider_id = action.provider_id
        routing_reference = None
        routing_decision = None
        routing_request = None
        routing_policy = None
        if self._model_router is not None and self._routing_factory is not None:
            routing_request, routing_policy = self._routing_factory(action, request)
            routing_decision = await self._model_router.route_static(
                routing_request, routing_policy
            )
            if routing_decision.selected_model is None:
                return ActionOutcome(succeeded=False, warning="routing found no eligible model")
            requested_model = routing_decision.selected_model.model_id
            provider_id = routing_decision.selected_model.provider_id
            routing_reference = RoutingReference(
                routing_decision_id=routing_decision.decision_id,
                routing_policy_id=routing_decision.policy_id,
                routing_policy_revision=routing_decision.policy_revision,
                control_mode=routing_decision.control_mode,
                selected_model_identity_hash=routing_decision.selected_model.content_hash,
                role_assignment=routing_decision.task_signature.execution_role,
            )
        if self._context_builder is not None and self._context_request_factory is not None:
            context_request = self._context_request_factory(action, request)
            context_result = await self._context_builder.build_context(context_request)
            if context_result.bundle is None:
                return ActionOutcome(
                    succeeded=False, warning="Context Builder did not create a bundle"
                )
            await self._context_builder.validate_bundle(context_result.bundle)
            messages = compose_context_messages(instruction, context_result)
            context_reference = context_result.bundle_reference
            if routing_decision is not None:
                if self._model_router is None:
                    raise RuntimeError("routing decision has no model router")
                if not await self._model_router.validate_context_fit(
                    routing_decision, context_result.bundle.total_token_estimate
                ):
                    if routing_request is None or routing_policy is None:
                        raise RuntimeError("routing context is unavailable for fallback")
                    routing_decision = await self._model_router.route_context_fallback(
                        routing_request,
                        routing_policy,
                        routing_decision,
                        context_result.bundle.total_token_estimate,
                    )
                    if (
                        routing_decision.selected_model is None
                        or not await self._model_router.validate_context_fit(
                            routing_decision, context_result.bundle.total_token_estimate
                        )
                    ):
                        return ActionOutcome(
                            succeeded=False,
                            warning="no routed model fits the built Context Bundle",
                        )
                    requested_model = routing_decision.selected_model.model_id
                    provider_id = routing_decision.selected_model.provider_id
                    routing_reference = RoutingReference(
                        routing_decision_id=routing_decision.decision_id,
                        routing_policy_id=routing_decision.policy_id,
                        routing_policy_revision=routing_decision.policy_revision,
                        control_mode=routing_decision.control_mode,
                        selected_model_identity_hash=routing_decision.selected_model.content_hash,
                        role_assignment=routing_decision.task_signature.execution_role,
                    )
            context_budget = context_request.budget.provider_context_limit
            reserved_output_tokens = context_request.budget.reserved_output_tokens
        provider_request = ModelProviderRequest(
            model_call_id=model_call_id,
            task_run_id=request.task_run_id,
            step_id=action.step_id,
            correlation_id=request.correlation_id,
            requested_model=requested_model,
            messages=messages,
            response_format=(ResponseFormat.JSON_SCHEMA if structured else ResponseFormat.TEXT),
            response_schema=action.response_schema,
            max_output_tokens=min(
                self._configuration.budgets.maximum_output_tokens or 32768,
                reserved_output_tokens,
                32768,
            ),
            context_budget=context_budget,
            context_bundle_reference=context_reference,
            routing_reference=routing_reference,
            metadata={"operation": "controller_provider_step"},
        )
        if (
            self._context_builder is not None
            and context_reference is not None
            and context_request is not None
        ):
            await self._context_builder.record_attachment(
                context_request, context_reference, model_call_id
            )
        response = await self._models.execute(provider_request, provider_id=provider_id)
        if response.tool_calls:
            return ActionOutcome(
                succeeded=False, warning="unexpected provider tool call was not executed"
            )
        return ActionOutcome(
            succeeded=True,
            output=response.structured_output if structured else response.content,
        )

    async def _tool(
        self, action: ControllerStepAction, request: StartControllerRequest
    ) -> ActionOutcome:
        tool_call_id = new_id()
        result = await self._tools.execute(
            ToolInvocation(
                tool_call_id=tool_call_id,
                task_run_id=request.task_run_id,
                step_id=action.step_id,
                correlation_id=request.correlation_id,
                tool_id=action.tool_id or "",
                tool_version=action.tool_version or "",
                arguments=action.tool_arguments or {},
                requested_at=datetime.now(UTC),
                requested_by="cognitive-controller",
            ),
            ToolExecutionContext(
                workspace=self._workspace,
                timeout_seconds=120,
                maximum_stdout_bytes=1048576,
                maximum_stderr_bytes=1048576,
                maximum_artifact_bytes=self._configuration.execution.maximum_inline_result_bytes,
            ),
        )
        return ActionOutcome(
            succeeded=result.status is ToolExecutionStatus.COMPLETED,
            output=result.result,
            tool_call_id=tool_call_id,
            warning=result.warnings[0] if result.warnings else None,
        )
