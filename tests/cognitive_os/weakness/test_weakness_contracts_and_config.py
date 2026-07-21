from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from pydantic import ValidationError

from cognitive_os.config.weakness_config import (
    WeaknessConfiguration,
    load_weakness_configuration,
)
from cognitive_os.domain.weakness import (
    CausalRelationshipType,
    MiningSourceSnapshot,
    SignalSourceType,
    WeaknessComponentType,
    WeaknessConfidenceLevel,
    WeaknessSeverity,
    WeaknessSignal,
    WeaknessType,
)
from cognitive_os.weakness.fixtures import (
    FIXTURE_TIME,
    FixtureSignalExtractor,
    fixture_profile,
    fixture_sources,
)


def test_weakness_configuration_is_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "weakness.yaml"
    path.write_text("weakness:\n  optional_clustering_enabled: false\n", encoding="utf-8")
    assert not load_weakness_configuration(path).optional_clustering_enabled
    with pytest.raises(ValidationError):
        WeaknessConfiguration(automatic_proposal_creation_enabled=True)
    with pytest.raises(ValidationError):
        WeaknessConfiguration(clustering_can_mutate_authority=True)


@pytest.mark.asyncio
async def test_signal_requires_authority_and_rejects_unknown_fields() -> None:
    sources = fixture_sources(1)
    profile = fixture_profile(sources)
    snapshot = MiningSourceSnapshot(
        mining_run_id=uuid5(NAMESPACE_URL, "weakness-contract-run"),
        source_refs=sources,
        registry_snapshots=("0" * 64,),
        profile_refs=(profile.content_hash,),
        created_at=FIXTURE_TIME,
    )
    signal = (await FixtureSignalExtractor().extract(snapshot, profile))[0]
    assert signal.causal_relationship is CausalRelationshipType.UNKNOWN_CAUSAL_RELATIONSHIP
    payload = signal.model_dump(mode="python", exclude={"content_hash"})
    payload["source_refs"] = tuple(
        type(item).model_validate(
            {
                **item.model_dump(mode="python", exclude={"content_hash"}),
                "authoritative": False,
            }
        )
        for item in signal.source_refs
    )
    with pytest.raises(ValidationError):
        WeaknessSignal.model_validate(payload)
    payload = signal.model_dump(mode="python")
    payload["prompt"] = "untrusted raw prompt"
    with pytest.raises(ValidationError):
        WeaknessSignal.model_validate(payload)
    assert signal.weakness_type is WeaknessType.MODEL_ROUTING_FAILURE
    assert signal.component_type is WeaknessComponentType.ROUTING
    assert signal.severity is WeaknessSeverity.HIGH
    assert signal.confidence is WeaknessConfidenceLevel.VERIFIED
    assert SignalSourceType.ROUTING_OUTCOME in {item.source_type for item in signal.source_refs}
