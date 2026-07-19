"""Credential-free deterministic Sprint 12 fixture construction."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.application.services.skill_service import SkillService
from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.context.fixtures import FixtureArtifactStore
from cognitive_os.domain.skills import (
    SkillActor,
    SkillCreatorType,
    SkillPromotionDecision,
    SkillPromotionOutcome,
    SkillStatus,
)

from .registry import SkillRegistry
from .repository import InMemorySkillRepository
from .validation import build_skill_verification_snapshot

FIXTURE_TIME = datetime(2026, 7, 19, tzinfo=UTC)


async def sprint12_verified_skills(
    root: Path = Path("procedural_skills"),
) -> tuple[InMemorySkillRepository, SkillRegistry, FixtureArtifactStore]:
    repository = InMemorySkillRepository()
    artifacts = FixtureArtifactStore()
    service = SkillService(
        repository,
        artifacts,
        SkillConfiguration(),
        clock=lambda: FIXTURE_TIME,
    )
    actor = SkillActor(creator_type=SkillCreatorType.OPERATOR, creator_id="sprint-12-fixture")
    for path in sorted(root.glob("*/*")):
        item, draft, package = await service.import_package(
            path, actor=actor, reason="Sprint 12 credential-free seed"
        )
        staged = await service.transition(
            item.identity.skill_id,
            SkillStatus.STAGED,
            expected_revision=draft.revision,
            actor=actor,
            reason="Credential-free regression passed",
        )
        verifier_bundle = await artifacts.put_bytes(
            staged.content_hash.encode(), media_type="application/json"
        )
        regression = await artifacts.put_bytes(
            staged.regression_profile.encode(), media_type="application/json"
        )
        verification = build_skill_verification_snapshot(staged, package)
        promotion = SkillPromotionDecision(
            decision_id=uuid5(NAMESPACE_URL, f"skill-promotion:{staged.content_hash}"),
            skill_id=staged.skill_id,
            revision=staged.revision,
            outcome=SkillPromotionOutcome.VERIFY,
            verifier_bundle=verifier_bundle,
            regression_summary=regression,
            decided_by=actor,
            reason_codes=("all_required_verifiers_passed",),
            decided_at=FIXTURE_TIME,
        )
        await service.transition(
            staged.skill_id,
            SkillStatus.VERIFIED,
            expected_revision=staged.revision,
            actor=actor,
            reason="Verified fixture promotion",
            verification=verification,
            promotion=promotion,
        )
    registry = SkillRegistry()
    for item, revision in await repository.query_candidates():
        registry.register(item, revision)
    registry.freeze()
    return repository, registry, artifacts
