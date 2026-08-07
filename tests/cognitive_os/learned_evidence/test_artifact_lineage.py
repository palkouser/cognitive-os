"""S21C1-040: learned lineage over the real Artifact Store.

The property under test is that the learned plane adds no second copy of anything and
interprets nothing. Bytes go in through the existing content-addressed store, so they
deduplicate; lineage records a reference and a verified hash; and no code path anywhere
turns those bytes back into an object.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from cognitive_os.domain.learned import LearnedArtifactFormat
from cognitive_os.domain.learned_evidence import (
    LearnedArtifactRole,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
)
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.learned.artifacts import (
    UNSAFE_TO_DESERIALISE,
    LearnedArtifactStore,
)
from cognitive_os.infrastructure.learned.postgres.repository import (
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.learned.postgres.tables import LEARNED_EVIDENCE_TABLES
from cognitive_os.infrastructure.postgres.artifact_repository import PostgresArtifactRepository
from cognitive_os.infrastructure.postgres.engine import (
    TruncationNotNominated,
    TruncationRefused,
    create_postgres_engine,
    require_nominated_for_truncation,
)

from . import fixtures as fx

pytestmark = [pytest.mark.integration, pytest.mark.postgres]

_TRUNCATE = ", ".join(f"cognitive_os.{table.name}" for table in LEARNED_EVIDENCE_TABLES)


@pytest_asyncio.fixture
async def learned_store() -> AsyncIterator[tuple[LearnedArtifactStore, ArtifactService, Path]]:
    admin_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not admin_url or not root:
        pytest.skip("PostgreSQL integration URLs or artifact root are not configured")
    engine = create_postgres_engine(admin_url, pool_size=2, max_overflow=2)
    async with engine.connect() as connection:
        name = await connection.scalar(text("SELECT current_database()"))
        if not str(name).endswith("_test"):
            pytest.fail(f"refusing learned artifact tests against database: {name}")
        # W7-F1. "Ends with `_test`" is a naming convention, not consent: every sprint's
        # evidence database ends in `_test` too, and on 2026-08-07 a release-matrix run with the
        # D4 environment sourced put one in front of this fixture, which truncated 1,076
        # committed observations. The rule is the one W6-F2 and D4-W0-F1 already established,
        # reached through its single implementation rather than copied beside a sixth TRUNCATE.
        try:
            require_nominated_for_truncation(str(name))
        except TruncationNotNominated as reason:
            pytest.skip(str(reason))
        except TruncationRefused as reason:
            pytest.fail(str(reason))
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {_TRUNCATE} RESTART IDENTITY CASCADE"))
    filesystem = ContentAddressedFilesystem(Path(root))
    artifacts = ArtifactService(filesystem, PostgresArtifactRepository(engine))
    try:
        yield LearnedArtifactStore(artifacts), artifacts, filesystem.root
    finally:
        await engine.dispose()


class TestBytesLiveInTheArtifactStoreOnly:
    @pytest.mark.asyncio
    async def test_identical_bytes_deduplicate(
        self, learned_store: tuple[LearnedArtifactStore, ArtifactService, Path]
    ) -> None:
        """Two learned artifacts with the same content share one blob on disk."""
        store, _, root = learned_store
        first = await store.store(fx.ARTIFACT_BYTES, media_type="application/octet-stream")
        second = await store.store(fx.ARTIFACT_BYTES, media_type="application/octet-stream")
        assert first.artifact_id != second.artifact_id, "each reference is its own row"
        assert first.storage_key == second.storage_key, "one blob, referenced twice"
        assert first.content_hash == second.content_hash
        matching = [
            path for path in root.rglob("*") if path.is_file() and path.name == first.content_hash
        ]
        assert len(matching) == 1

    @pytest.mark.asyncio
    async def test_lineage_records_a_reference_and_never_a_copy(
        self, learned_store: tuple[LearnedArtifactStore, ArtifactService, Path]
    ) -> None:
        store, _, _ = learned_store
        reference = await store.store(fx.ARTIFACT_BYTES, media_type="application/octet-stream")
        lineage = await store.build_lineage(
            lineage_id=uuid4(),
            artifact_id=reference.artifact_id,
            role=LearnedArtifactRole.MODEL,
            declared_format=LearnedArtifactFormat.NONE,
            component_id=fx.INERT.component_id,
            verified_by="learned-artifact-test",
        )
        assert lineage.artifact_id == reference.artifact_id
        assert lineage.declared_content_hash == lineage.observed_content_hash
        assert lineage.size_bytes == len(fx.ARTIFACT_BYTES)
        dumped = lineage.model_dump(mode="json")
        assert not any(
            isinstance(value, str) and fx.ARTIFACT_BYTES.decode() in value
            for value in dumped.values()
        ), "lineage must carry a reference, never the content"


class TestCorruptionAndAbsenceAreDetected:
    @pytest.mark.asyncio
    async def test_bit_corruption_is_detected(
        self, learned_store: tuple[LearnedArtifactStore, ArtifactService, Path]
    ) -> None:
        """A flipped byte on disk makes verification fail and lineage impossible."""
        store, _, root = learned_store
        reference = await store.store(fx.ARTIFACT_BYTES, media_type="application/octet-stream")
        blob = root.joinpath(*reference.storage_key.split("/"))
        original = blob.read_bytes()
        blob.chmod(0o640)
        blob.write_bytes(b"X" + original[1:])
        try:
            assert not await store.verify_artifact(reference.artifact_id)
            with pytest.raises(LearnedRepositoryError) as raised:
                await store.build_lineage(
                    lineage_id=uuid4(),
                    artifact_id=reference.artifact_id,
                    role=LearnedArtifactRole.MODEL,
                    declared_format=LearnedArtifactFormat.NONE,
                    component_id=fx.INERT.component_id,
                    verified_by="learned-artifact-test",
                )
            assert raised.value.conflict is LearnedRepositoryConflict.INTEGRITY_FAILURE
        finally:
            blob.write_bytes(original)
            blob.chmod(0o440)

    @pytest.mark.asyncio
    async def test_an_unknown_artifact_cannot_become_lineage(
        self, learned_store: tuple[LearnedArtifactStore, ArtifactService, Path]
    ) -> None:
        store, _, _ = learned_store
        assert await store.artifact_metadata(uuid4()) is None
        with pytest.raises(LearnedRepositoryError) as raised:
            await store.build_lineage(
                lineage_id=uuid4(),
                artifact_id=uuid4(),
                role=LearnedArtifactRole.MODEL,
                declared_format=LearnedArtifactFormat.NONE,
                component_id=fx.INERT.component_id,
                verified_by="learned-artifact-test",
            )
        assert raised.value.conflict is LearnedRepositoryConflict.NOT_FOUND

    @pytest.mark.asyncio
    async def test_missing_content_prevents_activation_evidence(
        self, learned_store: tuple[LearnedArtifactStore, ArtifactService, Path]
    ) -> None:
        """No verified lineage, no activation. The gate is the same one rollback uses."""
        store, _, root = learned_store
        reference = await store.store(fx.ARTIFACT_BYTES, media_type="application/octet-stream")
        blob = root.joinpath(*reference.storage_key.split("/"))
        blob.chmod(0o640)
        removed = blob.read_bytes()
        blob.unlink()
        try:
            assert not await store.verify_artifact(reference.artifact_id)
            with pytest.raises(LearnedRepositoryError):
                await store.build_lineage(
                    lineage_id=uuid4(),
                    artifact_id=reference.artifact_id,
                    role=LearnedArtifactRole.MODEL,
                    declared_format=LearnedArtifactFormat.NONE,
                    component_id=fx.INERT.component_id,
                    verified_by="learned-artifact-test",
                )
        finally:
            blob.write_bytes(removed)
            blob.chmod(0o440)


class TestAnArtifactIsNeverDeserialised:
    def test_the_learned_store_exposes_no_loader(self) -> None:
        """The absence is the guarantee, so it is asserted rather than assumed."""
        for forbidden in ("load", "loads", "open", "deserialise", "deserialize", "get_bytes"):
            assert not hasattr(LearnedArtifactStore, forbidden)

    def test_joblib_is_named_as_unsafe_and_stays_in_the_enum(self) -> None:
        """A legacy value that cannot be represented is a legacy value nobody checks."""
        assert LearnedArtifactFormat.JOBLIB in UNSAFE_TO_DESERIALISE
        assert LearnedArtifactFormat.JOBLIB.value == "joblib"

    @pytest.mark.asyncio
    async def test_a_pickle_like_payload_is_referenced_and_left_inert(
        self, learned_store: tuple[LearnedArtifactStore, ArtifactService, Path]
    ) -> None:
        """Bytes that would execute on load are hashed, referenced, and never opened.

        The payload below is a real pickle opcode stream. Nothing in Sprint 21C1 loads
        it; if something did, this test would be the one that stopped failing.
        """
        store, _, _ = learned_store
        pickled = b"\x80\x04\x95\x05\x00\x00\x00\x00\x00\x00\x00\x8c\x01x\x94."
        reference = await store.store(pickled, media_type="application/octet-stream")
        lineage = await store.build_lineage(
            lineage_id=uuid4(),
            artifact_id=reference.artifact_id,
            role=LearnedArtifactRole.MODEL,
            declared_format=LearnedArtifactFormat.JOBLIB,
            component_id=fx.INERT.component_id,
            verified_by="learned-artifact-test",
        )
        assert lineage.declared_format == "joblib"
        assert lineage.observed_content_hash == reference.content_hash


class TestLineageIsAppendedThroughTheRepository:
    @pytest.mark.asyncio
    async def test_a_verified_lineage_round_trips(
        self, learned_store: tuple[LearnedArtifactStore, ArtifactService, Path]
    ) -> None:
        store, _, _ = learned_store
        admin_url = os.environ["COGOS_DATABASE_ADMIN_URL"]
        engine = create_postgres_engine(admin_url, pool_size=2, max_overflow=1)
        try:
            repository = PostgresLearnedEvidenceRepository(engine)
            reference = await store.store(fx.ARTIFACT_BYTES, media_type="application/octet-stream")
            lineage = await store.build_lineage(
                lineage_id=uuid4(),
                artifact_id=reference.artifact_id,
                role=LearnedArtifactRole.MODEL,
                declared_format=LearnedArtifactFormat.NONE,
                component_id=fx.INERT.component_id,
                verified_by="learned-artifact-test",
            )
            await repository.record_artifact_lineage(lineage)
            stored = await repository.get_artifact_lineage(lineage.lineage_id)
            assert stored is not None
            assert stored.content_hash == lineage.content_hash
        finally:
            await engine.dispose()
