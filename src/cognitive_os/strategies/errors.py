"""Strategy Engine errors."""


class StrategyError(RuntimeError):
    """Base Strategy Engine failure."""


class StrategyConcurrencyError(StrategyError):
    """An optimistic strategy revision or identity check failed."""


class StrategyPolicyError(StrategyError):
    """A strategy operation violated host policy."""
