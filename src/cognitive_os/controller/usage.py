"""Usage reconstruction helpers."""

from cognitive_os.domain.controller import ControllerUsage


def merge_usage(base: ControllerUsage, **increments: int | float) -> ControllerUsage:
    values = base.model_dump()
    for key, value in increments.items():
        if key not in values or key in {"started_at", "last_updated_at"} or value < 0:
            raise ValueError("invalid usage increment")
        values[key] += value
    return ControllerUsage.model_validate(values)
