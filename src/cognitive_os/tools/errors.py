"""Sanitized Tool Plane failures."""


class ToolPlaneError(RuntimeError):
    """Base Tool Plane failure safe for operational output."""


class ToolRegistrationError(ToolPlaneError):
    pass


class ToolNotFoundError(ToolPlaneError):
    pass


class ToolValidationError(ToolPlaneError):
    pass


class ToolPolicyError(ToolPlaneError):
    pass


class ToolApprovalError(ToolPlaneError):
    pass


class ToolPersistenceError(ToolPlaneError):
    pass


class SandboxExecutionError(ToolPlaneError):
    pass


class McpClientError(ToolPlaneError):
    pass
