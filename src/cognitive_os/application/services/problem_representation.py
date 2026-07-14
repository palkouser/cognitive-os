"""Structured Problem Representation Engine using the provider service boundary."""

import json

from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.config.controller_config import ControllerConfiguration
from cognitive_os.domain.clarifications import ClarificationResponse
from cognitive_os.domain.identifiers import new_id
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.domain.problems import ConstraintSource, ProblemRepresentation
from cognitive_os.domain.provider import ResponseFormat
from cognitive_os.problem.normalization import NormalizedProblemSeed
from cognitive_os.problem.prompting import representation_instructions
from cognitive_os.problem.representation import decode_representation


class ProblemRepresentationService:
    def __init__(
        self,
        model_execution: ModelExecutionService,
        configuration: ControllerConfiguration,
        *,
        requested_model: str,
    ) -> None:
        self._models = model_execution
        self._configuration = configuration
        self._requested_model = requested_model

    async def represent(self, request: NormalizedProblemSeed) -> ProblemRepresentation:
        task_run_id = getattr(request, "task_run_id", None)
        if task_run_id is None:
            raise ValueError("normalized representation request requires task_run_id context")
        model_call_id = new_id()
        provider_request = ModelProviderRequest(
            model_call_id=model_call_id,
            task_run_id=task_run_id,
            correlation_id=model_call_id,
            requested_model=self._requested_model,
            messages=(
                ProviderMessage(
                    role=ProviderMessageRole.USER,
                    content=representation_instructions(request),
                ),
            ),
            response_format=ResponseFormat.JSON_SCHEMA,
            response_schema=ProblemRepresentation.model_json_schema(by_alias=True),
            max_output_tokens=min(
                self._configuration.budgets.maximum_output_tokens or 32768, 32768
            ),
            metadata={"operation": "problem_representation"},
        )
        response = await self._models.execute(
            provider_request,
            provider_id=self._configuration.problem_representation_provider_id,
        )
        if response.tool_calls:
            raise ValueError("problem representation response cannot request tools")
        return decode_representation(
            response.structured_output,
            request,
            confidence_threshold=self._configuration.confidence_threshold,
        )

    async def revise(
        self,
        current: ProblemRepresentation,
        clarification: ClarificationResponse,
    ) -> ProblemRepresentation:
        model_call_id = new_id()
        content = json.dumps(
            {
                "current": current.model_dump(mode="json", by_alias=True),
                "clarification": clarification.model_dump(mode="json"),
                "required_revision": current.revision + 1,
            },
            sort_keys=True,
        )
        request = ModelProviderRequest(
            model_call_id=model_call_id,
            task_run_id=current.task_run_id,
            correlation_id=model_call_id,
            requested_model=self._requested_model,
            messages=(
                ProviderMessage(
                    role=ProviderMessageRole.USER,
                    content=(
                        "Revise the typed problem representation using only the supplied "
                        f"clarification. Preserve all machine policy constraints. Data: {content}"
                    ),
                ),
            ),
            response_format=ResponseFormat.JSON_SCHEMA,
            response_schema=ProblemRepresentation.model_json_schema(by_alias=True),
            max_output_tokens=min(
                self._configuration.budgets.maximum_output_tokens or 32768, 32768
            ),
            metadata={"operation": "problem_representation_revision"},
        )
        response = await self._models.execute(
            request,
            provider_id=self._configuration.problem_representation_provider_id,
        )
        if response.tool_calls:
            raise ValueError("problem representation revision cannot request tools")
        revised = ProblemRepresentation.model_validate(response.structured_output)
        if (
            revised.problem_id != current.problem_id
            or revised.task_id != current.task_id
            or revised.task_run_id != current.task_run_id
            or revised.source_request_hash != current.source_request_hash
            or revised.revision != current.revision + 1
        ):
            raise ValueError("problem representation revision changed immutable identity")
        machine = tuple(
            item
            for item in current.constraints
            if item.source in {ConstraintSource.SYSTEM, ConstraintSource.PROJECT_POLICY}
        )
        present = {item.constraint_id for item in revised.constraints}
        missing = tuple(item for item in machine if item.constraint_id not in present)
        return revised.model_copy(update={"constraints": revised.constraints + missing})
