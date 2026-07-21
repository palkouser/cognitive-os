"""Typed weakness-mining failures."""


class WeaknessError(RuntimeError):
    pass


class WeaknessConflictError(WeaknessError):
    pass


class WeaknessAuthorityError(WeaknessError):
    pass


class WeaknessLifecycleError(WeaknessError):
    pass


class WeaknessSourceError(WeaknessError):
    pass
