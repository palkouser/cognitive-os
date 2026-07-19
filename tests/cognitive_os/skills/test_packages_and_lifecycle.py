from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.domain.skills import (
    SkillActor,
    SkillCreatorType,
    SkillStatus,
)
from cognitive_os.skills.errors import SkillPackageError, SkillPolicyError
from cognitive_os.skills.fixtures import sprint12_verified_skills
from cognitive_os.skills.packaging import (
    export_package,
    load_package,
    load_zip_package,
)
from cognitive_os.skills.validation import build_skill_verification_snapshot


def package_paths() -> tuple[Path, ...]:
    return tuple(sorted(Path("procedural_skills").glob("*/*")))


def test_eight_seed_packages_are_bounded_and_have_regressions() -> None:
    packages = [load_package(path, SkillConfiguration()) for path in package_paths()]
    assert len(packages) == 8
    assert len({item.manifest.package_hash for item in packages}) == 8
    assert all(any(path.startswith("tests/") for path in item.files) for item in packages)


def test_zip_export_round_trip_is_exact(tmp_path: Path) -> None:
    package = load_package(package_paths()[0], SkillConfiguration())
    destination = tmp_path / "skill.zip"
    export_package(package, destination)
    restored = load_zip_package(destination, SkillConfiguration())
    assert restored.manifest.package_hash == package.manifest.package_hash
    assert restored.files == package.files


def test_duplicate_yaml_keys_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "bad"
    root.mkdir()
    (root / "SKILL.md").write_text("# Safe\n", encoding="utf-8")
    (root / "metadata.yaml").write_text(
        "canonical_name: one\ncanonical_name: two\n", encoding="utf-8"
    )
    with pytest.raises(SkillPackageError):
        load_package(root, SkillConfiguration())


@pytest.mark.asyncio
async def test_fixture_promotes_only_verified_revision_three() -> None:
    repository, registry, _ = await sprint12_verified_skills()
    rows = await repository.query_candidates()
    assert all(revision.status is SkillStatus.VERIFIED for _, revision in rows)
    assert all(revision.revision == 3 for _, revision in rows)
    assert len(registry.health()) == 8


@pytest.mark.asyncio
async def test_provider_cannot_authorize_lifecycle_transition() -> None:
    repository, _, artifacts = await sprint12_verified_skills()
    item, revision = (await repository.query_candidates())[0]
    from cognitive_os.application.services.skill_service import SkillService

    service = SkillService(repository, artifacts, SkillConfiguration())
    provider = SkillActor(creator_type=SkillCreatorType.PROVIDER, creator_id="advisory")
    with pytest.raises(SkillPolicyError):
        await service.transition(
            item.identity.skill_id,
            SkillStatus.DEPRECATED,
            expected_revision=revision.revision,
            actor=provider,
            reason="Provider suggestion",
        )


@pytest.mark.asyncio
async def test_seed_verification_snapshots_pass_real_package_checks() -> None:
    repository, _, artifacts = await sprint12_verified_skills()
    for _, revision in await repository.query_candidates():
        from cognitive_os.skills.packaging import load_artifact_package

        package = load_artifact_package(
            await artifacts.get_bytes(revision.package_artifact.artifact_id),
            SkillConfiguration(),
        )
        snapshot = build_skill_verification_snapshot(revision, package)
        assert snapshot.passed
        assert snapshot.skill_id == revision.skill_id
        assert uuid5(NAMESPACE_URL, snapshot.package_hash)
