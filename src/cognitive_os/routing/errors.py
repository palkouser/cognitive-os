"""Typed routing failures."""


class RoutingError(RuntimeError):
    """Base governed routing failure."""


class RoutingConflictError(RoutingError):
    """Raised when immutable routing state conflicts."""


class RoutingPolicyError(RoutingError):
    """Raised when policy authority or lifecycle checks fail."""
