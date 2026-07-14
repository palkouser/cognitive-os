#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
作者: [weego/WXAI-Team]
最后更新: 2026-02-20
"""

from .version import __version__
from .core import LightAgent, LightSwarm
from .protocol import MemoryAdmissionDecision, MemoryPolicy, MemoryProtocol, MemoryScope
from .tools import ToolRegistry, ToolLoader, AsyncToolDispatcher
from .errors import (
    LightAgentError,
    LightAgentErrorInfo,
    ERROR_TAXONOMY,
    classify_exception,
    format_error_code,
    format_lightagent_error,
)
from .result import RunResult, StreamEvent
from .tracing import TraceEvent, TraceRecorder
from .hooks import HookContext, HookDecision, HookManager
from .guardrails import (
    DEFAULT_PRIVACY_PATTERNS,
    GuardrailDecision,
    GuardrailManager,
    high_risk_parameter_guardrail,
    output_redaction_guardrail,
    privacy_input_guardrail,
    sensitive_tool_confirmation_guardrail,
)
from .flow import JsonLightFlowStore, LightFlow, LightFlowResult, LightFlowStep, LightFlowStepResult
from .shared_memory import SharedMemoryPool, SharedMemoryRecord
from .logger import LoggerManager
from .skills import SkillManager, Skill
from .skill_tools import create_skill_tools
from .builtin_tools.python_executor import (
    execute_python_code,
    execute_python_file,
    execute_python_code_stream
)
from .builtin_tools.nos import upload_file_to_oss


def __getattr__(name):
    """Load optional public integrations only when requested."""
    if name == "MCPClientManager":
        try:
            from .mcp_client_manager import MCPClientManager
        except ImportError as exc:
            raise ImportError(
                "LightAgent MCP support is not installed. "
                "Install the Cognitive OS 'mcp' optional extra to enable it."
            ) from exc
        return MCPClientManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "__version__",
    "LightAgent",
    "LightSwarm",
    "MemoryProtocol",
    "MemoryAdmissionDecision",
    "MemoryPolicy",
    "MemoryScope",
    "ToolRegistry",
    "ToolLoader",
    "AsyncToolDispatcher",
    "LightAgentError",
    "LightAgentErrorInfo",
    "ERROR_TAXONOMY",
    "classify_exception",
    "format_error_code",
    "format_lightagent_error",
    "RunResult",
    "StreamEvent",
    "TraceEvent",
    "TraceRecorder",
    "HookContext",
    "HookDecision",
    "HookManager",
    "DEFAULT_PRIVACY_PATTERNS",
    "GuardrailDecision",
    "GuardrailManager",
    "high_risk_parameter_guardrail",
    "output_redaction_guardrail",
    "privacy_input_guardrail",
    "sensitive_tool_confirmation_guardrail",
    "LightFlow",
    "JsonLightFlowStore",
    "LightFlowResult",
    "LightFlowStep",
    "LightFlowStepResult",
    "SharedMemoryPool",
    "SharedMemoryRecord",
    "LoggerManager",
    "MCPClientManager",
    "SkillManager",
    "Skill",
    "create_skill_tools",
    "execute_python_code",
    "execute_python_file",
    "execute_python_code_stream",
    "upload_file_to_oss",
]
