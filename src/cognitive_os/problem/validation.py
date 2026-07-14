"""Problem representation security merge and validation."""

from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.problems import (
    ConstraintCategory,
    ConstraintSource,
    ProblemConstraint,
    ProblemRepresentation,
)


def merge_machine_constraints(
    representation: ProblemRepresentation, descriptions: tuple[str, ...]
) -> ProblemRepresentation:
    existing = {item.description for item in representation.constraints}
    added = tuple(
        ProblemConstraint(
            constraint_id=uuid5(NAMESPACE_URL, f"cognitive-os-policy:{description}"),
            category=ConstraintCategory.POLICY,
            description=description,
            hard=True,
            source=ConstraintSource.SYSTEM,
        )
        for description in descriptions
        if description not in existing
    )
    return representation.model_copy(update={"constraints": representation.constraints + added})


def require_executable(representation: ProblemRepresentation) -> None:
    if not representation.is_executable():
        raise ValueError("problem representation requires clarification or has a hard conflict")
