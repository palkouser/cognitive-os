from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

import pytest

from cognitive_os.domain.context import ContextBundleReference
from cognitive_os.domain.skills import (
    SkillActor,
    SkillCreatorType,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillExecutionStatus,
    SkillInputBinding,
    SkillRegistrySnapshot,
)
from cognitive_os.skills.execution import SkillExecutionService
from cognitive_os.skills.fixtures import FIXTURE_TIME, sprint12_verified_skills
from cognitive_os.verification.skills import SKILL_CAPABILITIES, build_skill_verifiers


def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


class ContextBuilderStub:
    async def load_bundle(self, *_args):
        return object()

    async def validate_bundle(self, _bundle):
        return True


class ControllerStub:
    async def start(self, request, _revision):
        return SkillExecutionResult(
            execution_id=request.execution_id,
            skill_id=request.skill_id,
            skill_revision=request.skill_revision,
            task_run_id=request.task_run_id,
            status=SkillExecutionStatus.ACCEPTED,
            step_results=(),
            acceptance_decision_id=uuid5(NAMESPACE_URL, "skill-acceptance"),
            started_at=FIXTURE_TIME,
            finished_at=FIXTURE_TIME,
        )

    async def resume(self, _execution_id):
        raise AssertionError("not used")

    async def cancel(self, _execution_id, _reason):
        raise AssertionError("not used")


@pytest.mark.asyncio
async def test_exact_verified_revision_executes_through_controller_adapter() -> None:
    repository, registry, artifacts = await sprint12_verified_skills()
    item, revision = next(
        row
        for row in await repository.query_candidates()
        if row[0].identity.canonical_name == "repository-inspection"
    )
    snapshot = SkillRegistrySnapshot(
        registry_hash=registry.snapshot_hash(),
        precondition_registry_hash=digest("preconditions"),
        context_registry_hash=digest("context"),
        tool_registry_hash=digest("tools"),
        verifier_registry_hash=digest("verifiers"),
        provider_registry_hash=digest("providers"),
    )
    reference = ContextBundleReference(
        context_bundle_id=uuid5(NAMESPACE_URL, "skill-bundle"),
        context_bundle_revision=1,
        bundle_artifact_id=uuid5(NAMESPACE_URL, "skill-bundle-artifact"),
        rendered_context_artifact_id=uuid5(NAMESPACE_URL, "skill-rendered-artifact"),
        content_hash=digest("bundle"),
        source_snapshot_hash=digest("snapshot"),
    )
    request = SkillExecutionRequest(
        execution_id=uuid5(NAMESPACE_URL, "skill-execution"),
        skill_id=item.identity.skill_id,
        skill_revision=revision.revision,
        task_run_id=uuid5(NAMESPACE_URL, "skill-task"),
        problem_reference=uuid5(NAMESPACE_URL, "skill-problem"),
        plan_reference=uuid5(NAMESPACE_URL, "skill-plan"),
        input_bindings=(SkillInputBinding(name="question", value="Inspect contracts"),),
        context_bundle_reference=reference,
        controller_budget=revision.resource_budget,
        expected_registry_snapshots=snapshot,
        requested_by=SkillActor(creator_type=SkillCreatorType.OPERATOR, creator_id="test-operator"),
        package_hash=revision.package_hash,
        created_at=datetime(2026, 7, 19, tzinfo=UTC),
    )
    service = SkillExecutionService(
        repository,
        artifacts,
        ContextBuilderStub(),
        ControllerStub(),
        lambda *_args: (_ for _ in ()).throw(AssertionError("not used")),
        lambda: snapshot,
    )
    result = await service.start_execution(request)
    assert result.status is SkillExecutionStatus.ACCEPTED
    assert await repository.get_execution(request.execution_id) == result
    assert await repository.read_statistics(revision.skill_id, revision.revision)


def test_ten_skill_verifiers_are_deterministic_and_offline() -> None:
    verifiers = build_skill_verifiers()
    assert len(verifiers) == len(SKILL_CAPABILITIES) == 10
    assert all(item.descriptor.kind.value == "skill" for item in verifiers)
    assert all(not item.descriptor.requires_network for item in verifiers)
