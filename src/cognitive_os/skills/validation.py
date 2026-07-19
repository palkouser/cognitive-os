"""Deterministic package, policy, and regression checks for skill promotion."""

import yaml

from cognitive_os.domain.skills import (
    SkillPreconditionType,
    SkillRequirementType,
    SkillRevision,
    SkillVerificationSnapshot,
)
from cognitive_os.memory.governance import contains_secret

from .packaging import LoadedSkillPackage


def build_skill_verification_snapshot(
    revision: SkillRevision, package: LoadedSkillPackage
) -> SkillVerificationSnapshot:
    files = {item.relative_path: item for item in package.manifest.files}
    package_integrity = package.manifest.package_hash == revision.package_hash and all(
        files[path].size_bytes == len(content) for path, content in package.files.items()
    )
    package_schema = package.metadata.get("format_version", "1") == "1"
    path_safety = all(
        not item.relative_path.startswith(("/", "../")) and "/../" not in item.relative_path
        for item in package.manifest.files
    )
    package_secrets = not any(
        contains_secret(value.decode("utf-8", errors="ignore")) for value in package.files.values()
    )
    precondition_determinism = all(
        item.precondition_type in SkillPreconditionType for item in revision.preconditions
    )
    tool_requirements = all(
        item.capability_id
        for item in revision.requirements
        if item.requirement_type is SkillRequirementType.TOOL
    )
    verifier_requirements = all(
        item.capability_id
        for item in revision.requirements
        if item.requirement_type is SkillRequirementType.VERIFIER
    )
    provider_requirements = all(
        item.capability_id
        for item in revision.requirements
        if item.requirement_type is SkillRequirementType.PROVIDER
    )
    context_requirements = all(
        item.capability_id
        for item in revision.requirements
        if item.requirement_type is SkillRequirementType.CONTEXT
    )
    capabilities = {item.capability_id for item in revision.steps}
    regression_files = [
        (path, content)
        for path, content in package.files.items()
        if path.startswith("tests/") and path.endswith((".yaml", ".yml"))
    ]
    regression_suite = bool(regression_files)
    for _, content in regression_files:
        try:
            value = yaml.safe_load(content)
            cases = value["cases"]
            regression_suite = (
                regression_suite
                and bool(cases)
                and all(
                    set(case.get("expected_capabilities", ())) <= capabilities
                    for case in cases
                    if isinstance(case, dict)
                )
            )
        except (KeyError, TypeError, yaml.YAMLError):
            regression_suite = False
    return SkillVerificationSnapshot(
        skill_id=revision.skill_id,
        revision=revision.revision,
        package_hash=revision.package_hash,
        package_integrity=package_integrity,
        package_schema=package_schema,
        path_safety=path_safety,
        package_secrets=package_secrets,
        precondition_determinism=precondition_determinism,
        tool_requirements=tool_requirements,
        verifier_requirements=verifier_requirements,
        provider_requirements=provider_requirements,
        context_requirements=context_requirements,
        execution_conformance=(
            len(revision.steps) <= revision.resource_budget.maximum_steps
            and len({item.step_id for item in revision.steps}) == len(revision.steps)
        ),
        output_schema=len({item.name for item in revision.output_specification.fields})
        == len(revision.output_specification.fields),
        regression_suite=regression_suite,
        no_permission_expansion=all(
            token not in item.parameters
            for item in revision.steps
            for token in ("shell", "sudo", "credential")
        ),
    )
