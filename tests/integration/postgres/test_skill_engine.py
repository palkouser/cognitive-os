from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from cognitive_os.application.services.skill_service import SkillService
from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.domain.skills import (
    SkillActor,
    SkillCreatorType,
    SkillPromotionDecision,
    SkillPromotionOutcome,
    SkillStatus,
)
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.postgres.artifact_repository import PostgresArtifactRepository
from cognitive_os.infrastructure.skills.postgres.health import PostgresSkillHealthService
from cognitive_os.infrastructure.skills.postgres.repository import PostgresSkillRepository
from cognitive_os.skills.errors import SkillConcurrencyError
from cognitive_os.skills.validation import build_skill_verification_snapshot


@pytest.mark.asyncio
async def test_postgres_skill_lifecycle_health_and_append_only_history(
    engines, tmp_path: Path
) -> None:
    app, _admin = engines
    repository = PostgresSkillRepository(app)
    artifacts = ArtifactService(
        ContentAddressedFilesystem(tmp_path / "skill-artifacts", fsync=False),
        PostgresArtifactRepository(app),
    )
    service = SkillService(repository, artifacts, SkillConfiguration())
    actor = SkillActor(creator_type=SkillCreatorType.OPERATOR, creator_id="integration")
    item, draft, package = await service.import_package(
        Path("procedural_skills/coding/repository-inspection"),
        actor=actor,
        reason="PostgreSQL integration import",
    )
    staged = await service.transition(
        item.identity.skill_id,
        SkillStatus.STAGED,
        expected_revision=draft.revision,
        actor=actor,
        reason="Package checks passed",
    )
    snapshot = build_skill_verification_snapshot(staged, package)
    verifier_bundle = await artifacts.put_bytes(
        snapshot.model_dump_json().encode(), media_type="application/json"
    )
    regression = await artifacts.put_bytes(b'{"passed":true}', media_type="application/json")
    promotion = SkillPromotionDecision(
        decision_id=uuid5(NAMESPACE_URL, "postgres-skill-promotion"),
        skill_id=staged.skill_id,
        revision=staged.revision,
        outcome=SkillPromotionOutcome.VERIFY,
        verifier_bundle=verifier_bundle,
        regression_summary=regression,
        decided_by=actor,
        reason_codes=("all_required_verifiers_passed",),
        decided_at=staged.created_at,
    )
    verified = await service.transition(
        staged.skill_id,
        SkillStatus.VERIFIED,
        expected_revision=staged.revision,
        actor=actor,
        reason="Promotion approved",
        verification=snapshot,
        promotion=promotion,
    )
    current = await repository.get_current(staged.skill_id)
    assert current is not None and current[1] == verified
    assert len(await repository.list_revisions(staged.skill_id)) == 3
    with pytest.raises(SkillConcurrencyError):
        await repository.append_revision(verified, expected_revision=1)
    assert (await PostgresSkillHealthService(app).check()).healthy
    for statement in (
        "UPDATE cognitive_os.skill_revisions SET status='draft'",
        "DELETE FROM cognitive_os.skill_revisions",
        "DELETE FROM cognitive_os.skill_accesses",
    ):
        with pytest.raises(DBAPIError):
            async with app.begin() as connection:
                await connection.execute(text(statement))
