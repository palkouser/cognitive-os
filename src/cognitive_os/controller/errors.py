"""Controller-specific safe errors."""


class ControllerError(RuntimeError):
    """Base controller failure."""


class IllegalControllerTransition(ControllerError):
    """Raised for an undefined state transition."""


class ControllerBudgetExhausted(ControllerError):
    """Raised when a host-owned budget prevents an action."""


class ContinuationRejected(ControllerError):
    """Raised when a continuation token is invalid or stale."""


class CheckpointValidationError(ControllerError):
    """Raised when checkpoint integrity or scope validation fails."""
