"""Stable string enums used by persisted contracts."""

from enum import Enum


class TaskStatus(str, Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PrivacyClass(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    # This persisted privacy classification is not a credential.
    SECRET = "secret"  # nosec B105


class CallStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class PermissionDecision(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    ALLOWED = "allowed"
    DENIED = "denied"


class VerifierStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    UNVERIFIABLE = "unverifiable"
    ERROR = "error"


class FindingSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActorType(str, Enum):
    USER = "user"
    AGENT = "agent"
    MODEL = "model"
    TOOL = "tool"
    VERIFIER = "verifier"
    SYSTEM = "system"


class StreamType(str, Enum):
    TASK = "task"
    TASK_RUN = "task_run"
    MODEL_CALL = "model_call"
    TOOL_CALL = "tool_call"
    VERIFIER = "verifier"
    SYSTEM = "system"
