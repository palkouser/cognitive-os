"""Typed benchmark failures."""


class BenchmarkError(RuntimeError):
    pass


class BenchmarkRegistrationError(BenchmarkError):
    pass


class BenchmarkNotFoundError(BenchmarkError):
    pass


class BenchmarkComparisonError(BenchmarkError):
    pass


class InspectAdapterUnavailableError(BenchmarkError):
    pass
