"""Cross-domain solver exposed as a Tool Plane tool.

The pilot never calls a solver directly. Every solve goes through this descriptor
so the Tool Plane authorises it, audits it, and enforces its timeout — the same
path a shell or Git tool takes.

The tool is `R0`, deterministic, and declares no side effects: it computes from
typed inputs with the standard library, touches no filesystem, opens no socket,
and needs no credential.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cognitive_os.domain.tools import (
    ToolDescriptor,
    ToolExecutionContext,
    ToolExecutionMode,
    ToolExecutionResult,
    ToolInvocation,
    ToolRiskLevel,
    ToolSideEffect,
    ToolSource,
)
from cognitive_os.tools.errors import ToolPlaneError

from .base import completed

_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "problem_type": {"type": "string", "minLength": 1, "maxLength": 64},
        "formal_inputs": {"type": "object"},
    },
    "required": ["problem_type", "formal_inputs"],
    "additionalProperties": False,
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer_type": {"type": "string"},
        "exact_value": {"type": ["string", "null"]},
        "approximate_value": {"type": ["string", "null"]},
        "tolerance": {"type": ["string", "null"]},
        "units": {"type": ["string", "null"]},
        "symbolic_form": {"type": ["string", "null"]},
        "logical_status": {"type": ["string", "null"]},
        "structured": {"type": "object"},
        "steps": {"type": "array"},
        "tool_evidence": {"type": "array"},
        "assumptions": {"type": "array"},
        "limitations": {"type": "array"},
    },
    "required": ["answer_type", "structured", "steps"],
    "additionalProperties": False,
}


class DomainSolveTool:
    """Runs one registered problem type and returns a candidate answer with evidence."""

    descriptor = ToolDescriptor(
        tool_id="domains.solve",
        version="1",
        display_name="Cross-domain deterministic solver",
        description=(
            "Solve a registered mathematics, physics, or logic task from typed inputs using "
            "dependency-free deterministic kernels. Produces a candidate answer and a derivation; "
            "grants no acceptance authority."
        ),
        source=ToolSource.BUILT_IN,
        input_schema=_INPUT_SCHEMA,
        output_schema=_OUTPUT_SCHEMA,
        risk_level=ToolRiskLevel.R0,
        side_effects=(ToolSideEffect.NONE,),
        execution_mode=ToolExecutionMode.HOST_READ_ONLY,
        provider_visible=False,
        idempotent=True,
        deterministic=True,
        default_timeout_seconds=30,
        tags=("mathematics", "physics", "logic", "deterministic", "offline"),
    )

    async def execute(
        self, invocation: ToolInvocation, context: ToolExecutionContext
    ) -> ToolExecutionResult:
        from cognitive_os.domains.registry import UnsupportedProblemType, resolve

        started = datetime.now(UTC)
        arguments = dict(invocation.arguments)
        problem_type = str(arguments["problem_type"])
        try:
            entry = resolve(problem_type)
        except UnsupportedProblemType as error:
            raise ToolPlaneError(f"unsupported problem type {problem_type!r}") from error

        from cognitive_os.domains.solvers import SolverError

        try:
            solution = entry.solver(dict(arguments["formal_inputs"]), entry.budget)  # type: ignore[arg-type]
        except SolverError as error:
            raise ToolPlaneError(f"{error.code.value}: {error}") from error
        except (KeyError, TypeError, ValueError) as error:
            raise ToolPlaneError(f"invalid domain inputs: {error}") from error

        return completed(invocation, started, serialise_solution(solution))


def serialise_solution(solution: Any) -> dict[str, Any]:
    """JSON-safe view of a solution; the checker rebuilds a candidate from it."""
    import json

    candidate = solution.candidate
    return {
        "answer_type": candidate.answer_type.value,
        "exact_value": candidate.exact_value,
        "approximate_value": (
            str(candidate.approximate_value) if candidate.approximate_value is not None else None
        ),
        "tolerance": str(candidate.tolerance) if candidate.tolerance is not None else None,
        "units": candidate.units,
        "symbolic_form": candidate.symbolic_form,
        "logical_status": candidate.logical_status,
        "structured": json.loads(json.dumps(candidate.structured, sort_keys=True, default=str)),
        "steps": [
            {
                "operation": item.operation,
                "detail": item.detail,
                "output": item.output,
                "inputs": list(item.inputs),
            }
            for item in solution.steps
        ],
        "tool_evidence": list(solution.tool_evidence),
        "assumptions": list(solution.assumptions),
        "limitations": list(solution.limitations),
    }


def candidate_from(payload: dict[str, Any]) -> Any:
    """Rebuild a typed candidate from the tool's JSON output."""
    from decimal import Decimal

    from cognitive_os.domain.domains import AnswerType
    from cognitive_os.domains.solvers import Candidate

    def decimal(value: Any) -> Decimal | None:
        return Decimal(str(value)) if value is not None else None

    return Candidate(
        answer_type=AnswerType(str(payload["answer_type"])),
        exact_value=payload.get("exact_value"),
        approximate_value=decimal(payload.get("approximate_value")),
        tolerance=decimal(payload.get("tolerance")),
        units=payload.get("units"),
        symbolic_form=payload.get("symbolic_form"),
        logical_status=payload.get("logical_status"),
        structured=dict(payload.get("structured") or {}),
    )
