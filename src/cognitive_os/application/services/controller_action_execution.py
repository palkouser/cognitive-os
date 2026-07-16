"""Provider and Tool Plane adapters for planned controller actions."""

from collections.abc import Callable
from datetime import UTC, datetime

from cognitive_os.application.ports.context_builder import ContextBuilderPort
from cognitive_os.application.ports.controller import StartControllerRequest
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
    ) -> None:
        self._models = model_execution
        self._tools = tool_execution
        self._configuration = configuration
        self._workspace = workspace
        if (context_builder is None) != (context_request_factory is None):
            raise ValueError("Context Builder and request factory must be configured together")
        self._context_builder = context_builder
        self._context_request_factory = context_request_factory

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
            context_budget = context_request.budget.provider_context_limit
            reserved_output_tokens = context_request.budget.reserved_output_tokens
        provider_request = ModelProviderRequest(
            model_call_id=model_call_id,
            task_run_id=request.task_run_id,
            step_id=action.step_id,
            correlation_id=request.correlation_id,
            requested_model=action.requested_model or "default",
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
        response = await self._models.execute(provider_request, provider_id=action.provider_id)
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
