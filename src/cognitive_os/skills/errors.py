"""Typed Skill Engine failures."""


class SkillError(RuntimeError):
    """Base Skill Engine failure."""


class SkillPackageError(SkillError):
    """A skill package is invalid or unsafe."""


class SkillConcurrencyError(SkillError):
    """An exact-revision write lost optimistic concurrency."""


class SkillPolicyError(SkillError):
    """Skill lifecycle or execution policy denied an operation."""


class SkillRequirementError(SkillError):
    """A declared host capability is missing or unauthorized."""
