"""Governed skill package import and append-only lifecycle service."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.skill_repository import SkillRepositoryPort
from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.skills import (
    SkillActor,
    SkillFailurePolicy,
    SkillIdentity,
    SkillInputSpecification,
    SkillItem,
    SkillOutputSpecification,
    SkillPrecondition,
    SkillProblemSignature,
    SkillPromotionDecision,
    SkillPromotionOutcome,
    SkillRequirement,
    SkillResourceBudget,
    SkillRevision,
    SkillScope,
    SkillScopeType,
    SkillSourceRef,
    SkillSourceType,
    SkillStatus,
    SkillStep,
    SkillVerificationSnapshot,
)
from cognitive_os.events.skill_event_service import SkillEventService
from cognitive_os.events.skill_events import (
    SkillCreated,
    SkillDeprecated,
    SkillRetracted,
    SkillRevisionAppended,
    SkillStaged,
    SkillStatusChanged,
    SkillSuperseded,
    SkillVerified,
)
from cognitive_os.skills.errors import SkillPolicyError
from cognitive_os.skills.packaging import LoadedSkillPackage, load_package, load_zip_package

_TRANSITIONS = {
    SkillStatus.DRAFT: {SkillStatus.DRAFT, SkillStatus.STAGED, SkillStatus.RETRACTED},
    SkillStatus.STAGED: {
        SkillStatus.DRAFT,
        SkillStatus.STAGED,
        SkillStatus.VERIFIED,
        SkillStatus.RETRACTED,
    },
    SkillStatus.VERIFIED: {
        SkillStatus.VERIFIED,
        SkillStatus.DEPRECATED,
        SkillStatus.SUPERSEDED,
        SkillStatus.RETRACTED,
    },
    SkillStatus.DEPRECATED: {
        SkillStatus.VERIFIED,
        SkillStatus.SUPERSEDED,
        SkillStatus.RETRACTED,
    },
    SkillStatus.SUPERSEDED: {SkillStatus.RETRACTED},
    SkillStatus.RETRACTED: set(),
}


def _metadata_list(metadata: dict[str, object], key: str) -> list[object]:
    value = metadata.get(key, [])
    if not isinstance(value, list):
        raise SkillPolicyError(f"skill metadata {key} must be a list")
    return value


class SkillService:
    def __init__(
        self,
        repository: SkillRepositoryPort,
        artifacts: ArtifactStorePort,
        configuration: SkillConfiguration,
        *,
        clock: Callable[[], datetime] = utc_now,
        events: SkillEventService | None = None,
    ) -> None:
        self._repository = repository
        self._artifacts = artifacts
        self._configuration = configuration
        self._clock = clock
        self._events = events

    async def import_package(
        self,
        path: Path,
        *,
        actor: SkillActor,
        reason: str,
    ) -> tuple[SkillItem, SkillRevision, LoadedSkillPackage]:
        package = (
            load_zip_package(path, self._configuration)
            if path.is_file()
            else load_package(path, self._configuration)
        )
        metadata = package.metadata
        if str(metadata.get("status", "draft")) == SkillStatus.VERIFIED.value:
            raise SkillPolicyError("imported packages cannot start verified")
        scope = SkillScope(
            scope_type=SkillScopeType(str(metadata.get("scope_type", "project"))),
            scope_id=str(metadata.get("scope_id", "cognitive-os")),
        )
        if scope.scope_type.value == "global" and not self._configuration.allow_global_scope:
            raise SkillPolicyError("global skill scope is not enabled")
        canonical_name = re.sub(
            r"[^a-z0-9]+", "-", str(metadata["canonical_name"]).strip().casefold()
        ).strip("-")
        skill_id = uuid5(
            NAMESPACE_URL,
            f"cognitive-os-skill:{scope.canonical_hash()}:{canonical_name}",
        )
        package_artifact = await self._artifacts.put_bytes(
            package.artifact_bytes(), media_type="application/vnd.cognitive-os.skill-package+json"
        )
        created_at = self._clock()
        identity = SkillIdentity(
            skill_id=skill_id,
            canonical_name=canonical_name,
            scope=scope,
            created_at=created_at,
            created_by=actor,
        )
        revision = SkillRevision(
            skill_id=skill_id,
            revision=1,
            status=SkillStatus.DRAFT,
            display_name=str(metadata["display_name"]),
            description=str(metadata["description"]),
            purpose=str(metadata["purpose"]),
            domains=tuple(str(item) for item in _metadata_list(metadata, "domains")),
            problem_signatures=tuple(
                SkillProblemSignature.model_validate(item)
                for item in _metadata_list(metadata, "problem_signatures")
            ),
            preconditions=tuple(
                SkillPrecondition.model_validate(item)
                for item in _metadata_list(metadata, "preconditions")
            ),
            input_specification=SkillInputSpecification.model_validate(
                {"fields": _metadata_list(metadata, "inputs")}
            ),
            output_specification=SkillOutputSpecification.model_validate(
                {"fields": _metadata_list(metadata, "outputs")}
            ),
            steps=tuple(
                SkillStep.model_validate(item) for item in _metadata_list(metadata, "steps")
            ),
            requirements=tuple(
                SkillRequirement.model_validate(item)
                for item in _metadata_list(metadata, "requirements")
            ),
            failure_policy=SkillFailurePolicy.model_validate(metadata["failure_policy"]),
            resource_budget=SkillResourceBudget.model_validate(metadata.get("resource_budget", {})),
            package_artifact=package_artifact,
            package_hash=package.manifest.package_hash,
            source_refs=(
                SkillSourceRef(
                    source_type=SkillSourceType.IMPORTED_PACKAGE,
                    source_id=f"package:{package.manifest.package_hash}",
                    source_revision="1",
                    content_hash=package.manifest.package_hash,
                ),
            ),
            sensitivity=MemorySensitivity(str(metadata.get("sensitivity", "internal"))),
            regression_profile=str(metadata["regression_profile"]),
            created_at=created_at,
            created_by=actor,
            reason=reason,
        )
        idempotency_key = sha256(
            f"{identity.canonical_hash()}:{revision.package_hash}".encode()
        ).hexdigest()
        item = SkillItem(
            identity=identity,
            current_revision=1,
            current_status=revision.status,
            idempotency_key=idempotency_key,
        )
        await self._repository.create_skill(item, revision)
        if self._events is not None:
            await self._events.append(
                skill_id,
                SkillCreated(
                    skill_id=skill_id,
                    revision=revision.revision,
                    status=revision.status,
                    package_hash=revision.package_hash,
                    occurred_at=revision.created_at,
                ),
                correlation_id=skill_id,
            )
        return item, revision, package

    async def revise_package(
        self,
        skill_id: UUID,
        path: Path,
        *,
        expected_revision: int,
        actor: SkillActor,
        reason: str,
    ) -> tuple[SkillRevision, LoadedSkillPackage]:
        current = await self._repository.get_current(skill_id)
        if current is None or current[0].current_revision != expected_revision:
            raise SkillPolicyError("skill revision is stale or unavailable")
        item, previous = current
        if previous.status is SkillStatus.RETRACTED:
            raise SkillPolicyError("retracted skills cannot be revised")
        if actor.creator_type.value in {"provider", "import_service"}:
            raise SkillPolicyError("untrusted actor cannot authorize a skill revision")
        package = (
            load_zip_package(path, self._configuration)
            if path.is_file()
            else load_package(path, self._configuration)
        )
        metadata = package.metadata
        canonical_name = re.sub(
            r"[^a-z0-9]+", "-", str(metadata["canonical_name"]).strip().casefold()
        ).strip("-")
        scope = SkillScope(
            scope_type=SkillScopeType(str(metadata.get("scope_type", "project"))),
            scope_id=str(metadata.get("scope_id", "cognitive-os")),
        )
        if canonical_name != item.identity.canonical_name or scope != item.identity.scope:
            raise SkillPolicyError("skill revision cannot change canonical identity or scope")
        package_artifact = await self._artifacts.put_bytes(
            package.artifact_bytes(),
            media_type="application/vnd.cognitive-os.skill-package+json",
        )
        revision = SkillRevision(
            skill_id=skill_id,
            revision=expected_revision + 1,
            previous_revision=expected_revision,
            status=SkillStatus.DRAFT,
            display_name=str(metadata["display_name"]),
            description=str(metadata["description"]),
            purpose=str(metadata["purpose"]),
            domains=tuple(str(value) for value in _metadata_list(metadata, "domains")),
            problem_signatures=tuple(
                SkillProblemSignature.model_validate(value)
                for value in _metadata_list(metadata, "problem_signatures")
            ),
            preconditions=tuple(
                SkillPrecondition.model_validate(value)
                for value in _metadata_list(metadata, "preconditions")
            ),
            input_specification=SkillInputSpecification.model_validate(
                {"fields": _metadata_list(metadata, "inputs")}
            ),
            output_specification=SkillOutputSpecification.model_validate(
                {"fields": _metadata_list(metadata, "outputs")}
            ),
            steps=tuple(
                SkillStep.model_validate(value) for value in _metadata_list(metadata, "steps")
            ),
            requirements=tuple(
                SkillRequirement.model_validate(value)
                for value in _metadata_list(metadata, "requirements")
            ),
            failure_policy=SkillFailurePolicy.model_validate(metadata["failure_policy"]),
            resource_budget=SkillResourceBudget.model_validate(metadata.get("resource_budget", {})),
            package_artifact=package_artifact,
            package_hash=package.manifest.package_hash,
            source_refs=(
                SkillSourceRef(
                    source_type=SkillSourceType.IMPORTED_PACKAGE,
                    source_id=f"package:{package.manifest.package_hash}",
                    source_revision=str(expected_revision + 1),
                    content_hash=package.manifest.package_hash,
                ),
            ),
            sensitivity=MemorySensitivity(str(metadata.get("sensitivity", "internal"))),
            regression_profile=str(metadata["regression_profile"]),
            created_at=self._clock(),
            created_by=actor,
            reason=reason,
        )
        await self._repository.append_revision(revision, expected_revision=expected_revision)
        if self._events is not None:
            await self._events.append(
                skill_id,
                SkillRevisionAppended(
                    skill_id=skill_id,
                    revision=revision.revision,
                    previous_revision=previous.revision,
                    status=revision.status,
                    package_hash=revision.package_hash,
                    occurred_at=revision.created_at,
                ),
                correlation_id=skill_id,
            )
        return revision, package

    async def transition(
        self,
        skill_id: UUID,
        requested_status: SkillStatus,
        *,
        expected_revision: int,
        actor: SkillActor,
        reason: str,
        verification: SkillVerificationSnapshot | None = None,
        promotion: SkillPromotionDecision | None = None,
    ) -> SkillRevision:
        current = await self._repository.get_current(skill_id)
        if current is None or current[0].current_revision != expected_revision:
            raise SkillPolicyError("skill revision is stale or unavailable")
        _, revision = current
        if requested_status not in _TRANSITIONS[revision.status]:
            raise SkillPolicyError("illegal skill lifecycle transition")
        if actor.creator_type.value in {"provider", "import_service"}:
            raise SkillPolicyError("untrusted actor cannot authorize a skill transition")
        if requested_status is SkillStatus.VERIFIED:
            if verification is None or not verification.passed or promotion is None:
                raise SkillPolicyError("verified promotion requires complete verifier evidence")
            if (
                verification.skill_id != skill_id
                or verification.revision != revision.revision
                or verification.package_hash != revision.package_hash
                or promotion.skill_id != skill_id
                or promotion.revision != revision.revision
                or promotion.outcome is not SkillPromotionOutcome.VERIFY
            ):
                raise SkillPolicyError("skill promotion decision targets another revision")
        next_revision = SkillRevision.model_validate(
            {
                **revision.model_dump(mode="python", exclude={"content_hash"}),
                "revision": revision.revision + 1,
                "previous_revision": revision.revision,
                "status": requested_status,
                "created_at": self._clock(),
                "created_by": actor,
                "reason": reason,
            }
        )
        appended = await self._repository.append_revision(
            next_revision, expected_revision=expected_revision
        )
        if self._events is not None:
            await self._events.append(
                skill_id,
                SkillRevisionAppended(
                    skill_id=skill_id,
                    revision=appended.revision,
                    previous_revision=revision.revision,
                    status=appended.status,
                    package_hash=appended.package_hash,
                    occurred_at=appended.created_at,
                ),
                correlation_id=skill_id,
            )
            event_types: dict[SkillStatus, type[SkillStatusChanged]] = {
                SkillStatus.STAGED: SkillStaged,
                SkillStatus.VERIFIED: SkillVerified,
                SkillStatus.DEPRECATED: SkillDeprecated,
                SkillStatus.SUPERSEDED: SkillSuperseded,
                SkillStatus.RETRACTED: SkillRetracted,
            }
            event_model = event_types.get(requested_status)
            if event_model is not None:
                await self._events.append(
                    skill_id,
                    event_model(
                        skill_id=skill_id,
                        revision=appended.revision,
                        previous_status=revision.status,
                        status=appended.status,
                        reason_code=reason,
                        occurred_at=appended.created_at,
                    ),
                    correlation_id=skill_id,
                )
        return appended
