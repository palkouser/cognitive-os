"""Coding command verifiers routed exclusively through ToolExecutionService."""

from __future__ import annotations

import re
from typing import Any, cast
from uuid import uuid4

from cognitive_os.application.services.tool_execution import ToolExecutionService
from cognitive_os.domain.common import ErrorInfo, utc_now
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.tools import ToolExecutionContext, ToolExecutionStatus, ToolInvocation
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import VerificationRequest

from ..base import BaseVerifier
from .common import coding_descriptor

SAFE_PATH = re.compile(r"^[A-Za-z0-9_./-]{1,256}$")
SAFE_K = re.compile(r"^[A-Za-z0-9_ .()andornot-]{1,256}$")


class SandboxCommandVerifier(BaseVerifier):
    tool_id: str
    command: str

    def __init__(self, execution: ToolExecutionService, verifier_id: str, tool_id: str) -> None:
        super().__init__(coding_descriptor(verifier_id, sandbox=True))
        self._execution = execution
        self.tool_id = tool_id

    def arguments(self, request: VerificationRequest) -> tuple[str, ...]:
        raw = request.configuration.get("arguments", [])
        if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
            raise ValueError("coding verifier arguments must be a string list")
        return tuple(cast(list[str], raw))

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        try:
            configuration = cast(Any, request.configuration)
            arguments = self.arguments(request)
            invocation = ToolInvocation(
                tool_call_id=uuid4(),
                task_run_id=request.task_run_id,
                step_id=request.step_id,
                correlation_id=request.correlation_id,
                tool_id=self.tool_id,
                tool_version="1",
                arguments={"arguments": list(arguments)},
                requested_at=utc_now(),
                requested_by=self.descriptor.verifier_id,
            )
            result = await self._execution.execute(
                invocation,
                ToolExecutionContext(
                    workspace=str(
                        configuration.get(
                            "approved_workspace", request.subject.workspace_path or "."
                        )
                    ),
                    timeout_seconds=min(
                        float(
                            configuration.get(
                                "timeout_seconds", self.descriptor.default_timeout_seconds
                            )
                        ),
                        self.descriptor.default_timeout_seconds,
                    ),
                    maximum_stdout_bytes=min(
                        int(configuration.get("maximum_output_bytes", 1_048_576)), 1_048_576
                    ),
                    maximum_stderr_bytes=min(
                        int(configuration.get("maximum_output_bytes", 1_048_576)), 1_048_576
                    ),
                    maximum_artifact_bytes=2_097_152,
                ),
            )
            passed = result.status is ToolExecutionStatus.COMPLETED and result.exit_code == 0
            return self.result(
                request,
                VerifierStatus.PASSED if passed else VerifierStatus.FAILED,
                code=f"{self.descriptor.verifier_id}.failed",
                message=f"{self.command} verification failed in the sandbox",
                score=1 if passed else 0,
            )
        except (KeyError, TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_coding_verifier_configuration", message=str(error)),
            )


class PytestVerifier(SandboxCommandVerifier):
    command = "pytest"

    def __init__(self, execution: ToolExecutionService) -> None:
        super().__init__(execution, "coding.pytest", "sandbox.pytest")

    def arguments(self, request: VerificationRequest) -> tuple[str, ...]:
        arguments = super().arguments(request)
        index = 0
        while index < len(arguments):
            item = arguments[index]
            if item in {"-q", "-x"} or (
                item.startswith("--maxfail=")
                and item.removeprefix("--maxfail=").isdigit()
                and int(item.removeprefix("--maxfail=")) <= 20
            ):
                index += 1
                continue
            if (
                item == "-k"
                and index + 1 < len(arguments)
                and SAFE_K.fullmatch(arguments[index + 1])
            ):
                index += 2
                continue
            if (
                SAFE_PATH.fullmatch(item)
                and ".." not in item.split("/")
                and not item.startswith("/")
            ):
                index += 1
                continue
            raise ValueError("pytest argument is outside the Sprint 7 allowlist")
        return arguments or ("-q",)


class RuffVerifier(SandboxCommandVerifier):
    command = "ruff"

    def __init__(self, execution: ToolExecutionService) -> None:
        super().__init__(execution, "coding.ruff", "sandbox.ruff")

    def arguments(self, request: VerificationRequest) -> tuple[str, ...]:
        arguments = super().arguments(request)
        if not arguments or arguments[0] not in {"check", "format"}:
            raise ValueError("ruff verifier supports check or format only")
        if arguments[0] == "format" and "--check" not in arguments:
            raise ValueError("ruff format verifier requires --check")
        if any(".." in item or ";" in item or item.startswith("/") for item in arguments):
            raise ValueError("unsafe ruff argument")
        return arguments


class MypyVerifier(SandboxCommandVerifier):
    command = "mypy"

    def __init__(self, execution: ToolExecutionService) -> None:
        super().__init__(execution, "coding.mypy", "sandbox.mypy")

    def arguments(self, request: VerificationRequest) -> tuple[str, ...]:
        arguments = super().arguments(request)
        if not arguments or any(
            not SAFE_PATH.fullmatch(item) or ".." in item for item in arguments
        ):
            raise ValueError("mypy verifier accepts workspace-relative module paths only")
        return arguments


class ImportVerifier(SandboxCommandVerifier):
    command = "python import check"

    def __init__(self, execution: ToolExecutionService) -> None:
        super().__init__(execution, "coding.import", "sandbox.python")

    def arguments(self, request: VerificationRequest) -> tuple[str, ...]:
        modules = request.configuration.get("modules", [])
        if (
            not isinstance(modules, list)
            or not modules
            or not all(
                isinstance(item, str) and re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", item)
                for item in modules
            )
        ):
            raise ValueError("import verifier requires valid module names")
        # The sandbox image owns this fixed helper; provider-supplied Python code is never accepted.
        return ("scripts/controlled_import_check.py", *cast(list[str], modules))
