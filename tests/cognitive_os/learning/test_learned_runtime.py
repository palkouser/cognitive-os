"""S21D2-053, -055 and -056: the four authorities, and what happens when any one disagrees.

The resolver's whole job is to say no. There is exactly one path to a learned ordering and
twelve named ways to fall back, and each of the twelve is a test — because a fallback that
happens for the wrong reason looks identical to a fallback that happens for the right one, and
an operator cannot tell them apart without the reason code.

The configuration tests hold the shipped state: empty activation actors, empty active
components, empty routing. A deployment that reads the tracked configuration and changes
nothing runs the deterministic system.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
import yaml

from cognitive_os.application.services.learned_runtime import (
    ActiveComponentState,
    ArtifactAvailability,
    EmbeddingIdentity,
    LearnedRuntimeResolver,
    RoutingPolicy,
    RuntimeHealthReason,
)
from cognitive_os.config.learned_config import (
    LearnedPersistenceConfiguration,
    load_learned_configuration,
)

SURFACE = "experience.correction_ranking"
COMPONENT = "learned.knn.correction_ranking"
ARTIFACT = UUID(int=11)
MODEL = EmbeddingIdentity(model_id="all-MiniLM-L6-v2", revision="1110a24", available=True)
MANIFEST = "c" * 64


def _resolver() -> LearnedRuntimeResolver:
    return LearnedRuntimeResolver(surface=SURFACE, expected_embedding=MODEL)


def _policy(**overrides: object) -> RoutingPolicy:
    fields: dict[str, object] = {
        "persistence_enabled": True,
        "activation_enabled": True,
        "active_components": (COMPONENT,),
        "routed_groups": ("group-a",),
        "routing_manifest_hash": MANIFEST,
    }
    fields.update(overrides)
    return RoutingPolicy(**fields)  # type: ignore[arg-type]


def _state(**overrides: object) -> ActiveComponentState:
    fields: dict[str, object] = {
        "component_id": COMPONENT,
        "surface": SURFACE,
        "revision": 3,
        "model_artifact_id": ARTIFACT,
        "lineage_verified": True,
        "descriptor_revision": 3,
    }
    fields.update(overrides)
    return ActiveComponentState(**fields)  # type: ignore[arg-type]


def _resolve(**overrides: object):
    fields: dict[str, object] = {
        "policy": _policy(),
        "active_states": [_state()],
        "group": "group-a",
        "artifact": ArtifactAvailability(present=True),
        "local_embedding": MODEL,
    }
    fields.update(overrides)
    return _resolver().resolve(**fields)  # type: ignore[arg-type]


class TestTheOnePathToALearnedOrdering:
    def test_all_four_authorities_agreeing_permits_it(self) -> None:
        resolved = _resolve()

        assert resolved.learned_ordering_permitted
        assert resolved.reason is RuntimeHealthReason.ACTIVE
        assert resolved.component_id == COMPONENT
        assert resolved.model_artifact_id == ARTIFACT

    def test_the_routing_manifest_can_be_checked_when_the_caller_knows_it(self) -> None:
        assert _resolve(expected_routing_manifest_hash=MANIFEST).learned_ordering_permitted


class TestEveryDisagreementIsANamedFallback:
    @pytest.mark.parametrize(
        ("overrides", "reason"),
        [
            (
                {"policy": _policy(persistence_enabled=False)},
                RuntimeHealthReason.PERSISTENCE_DISABLED,
            ),
            (
                {"policy": _policy(activation_enabled=False)},
                RuntimeHealthReason.ACTIVATION_DISABLED,
            ),
            ({"active_states": []}, RuntimeHealthReason.NO_ACTIVE_REVISION),
            (
                {"policy": _policy(active_components=())},
                RuntimeHealthReason.COMPONENT_NOT_ALLOWLISTED,
            ),
            ({"group": "group-unrouted"}, RuntimeHealthReason.GROUP_NOT_ROUTED),
            (
                {"artifact": ArtifactAvailability(present=False)},
                RuntimeHealthReason.ARTIFACT_MISSING,
            ),
            (
                {"active_states": [_state(lineage_verified=False)]},
                RuntimeHealthReason.ARTIFACT_UNVERIFIED,
            ),
            (
                {"active_states": [_state(descriptor_revision=2)]},
                RuntimeHealthReason.DESCRIPTOR_REVISION_MISMATCH,
            ),
            (
                {"local_embedding": EmbeddingIdentity("all-MiniLM-L6-v2", "1110a24", False)},
                RuntimeHealthReason.EMBEDDING_UNAVAILABLE,
            ),
            (
                {"local_embedding": EmbeddingIdentity("some-other-model", "1110a24", True)},
                RuntimeHealthReason.EMBEDDING_IDENTITY_MISMATCH,
            ),
        ],
    )
    def test_it_falls_back_with_the_right_reason(
        self, overrides: dict[str, object], reason: RuntimeHealthReason
    ) -> None:
        resolved = _resolve(**overrides)

        assert resolved.uses_deterministic_fallback
        assert resolved.reason is reason

    def test_two_active_revisions_on_one_surface_fail_closed(self) -> None:
        """Guessing which one is current would hide a ledger that disagrees with itself."""
        resolved = _resolve(active_states=[_state(revision=3), _state(revision=4)])

        assert resolved.uses_deterministic_fallback
        assert resolved.reason is RuntimeHealthReason.MULTIPLE_ACTIVE_REVISIONS

    def test_a_routing_manifest_that_does_not_match_falls_back(self) -> None:
        resolved = _resolve(expected_routing_manifest_hash="d" * 64)

        assert resolved.reason is RuntimeHealthReason.ROUTING_MANIFEST_MISMATCH

    def test_another_surfaces_active_component_does_not_count(self) -> None:
        resolved = _resolve(active_states=[_state(surface="skill.selection")])

        assert resolved.reason is RuntimeHealthReason.NO_ACTIVE_REVISION


class TestHealthNeverOverclaims:
    def test_a_fallback_reports_inactive_with_its_reason(self) -> None:
        resolver = _resolver()
        resolved = _resolve(artifact=ArtifactAvailability(present=False))

        health = resolver.health(resolved, routed_groups=1)

        assert health.active is False
        assert health.reason is RuntimeHealthReason.ARTIFACT_MISSING
        assert health.as_dict()["active"] is False

    def test_an_active_resolution_reports_active(self) -> None:
        resolver = _resolver()

        health = resolver.health(_resolve(), routed_groups=5)

        assert health.active is True
        assert health.routed_group_count == 5

    def test_health_discloses_no_model_payload(self) -> None:
        """A health report names components and reasons; it is not a model dump."""
        resolver = _resolver()

        rendered = str(resolver.health(_resolve(), routed_groups=1).as_dict())

        assert "exemplar" not in rendered
        assert "embedding_weight" not in rendered


class TestTheShippedConfigurationChangesNothing:
    def test_the_defaults_are_fail_closed(self) -> None:
        configuration = LearnedPersistenceConfiguration()

        assert configuration.activation_enabled is False
        assert configuration.activation_actors == ()
        assert configuration.active_components == ()
        assert configuration.correction_ranking_groups == ()

    def test_routing_groups_without_a_manifest_hash_are_refused(self) -> None:
        with pytest.raises(ValueError, match="without the manifest hash"):
            LearnedPersistenceConfiguration(correction_ranking_groups=("group-a",))

    def test_a_manifest_hash_routing_nothing_is_refused(self) -> None:
        """It reads as active while changing nothing, which is the worst of both."""
        with pytest.raises(ValueError, match="routes no group"):
            LearnedPersistenceConfiguration(correction_ranking_manifest_hash=MANIFEST)

    def test_a_complete_routing_declaration_validates(self) -> None:
        configuration = LearnedPersistenceConfiguration(
            activation_enabled=True,
            activation_actors=("operator",),
            active_components=(COMPONENT,),
            correction_ranking_groups=("group-a",),
            correction_ranking_manifest_hash=MANIFEST,
        )

        assert configuration.correction_ranking_groups == ("group-a",)

    def test_artifact_deserialisation_is_still_impossible(self) -> None:
        with pytest.raises(ValueError, match="artifact deserialisation cannot be enabled"):
            LearnedPersistenceConfiguration(artifact_deserialisation_enabled=True)

    def test_real_run_training_is_still_impossible(self) -> None:
        with pytest.raises(ValueError, match="evaluation-only"):
            LearnedPersistenceConfiguration(real_run_training_enabled=True)

    def test_a_loaded_file_keeps_the_same_invariants(self, tmp_path: Path) -> None:
        path = tmp_path / "learned.yaml"
        path.write_text(
            yaml.safe_dump({"learned": {"correction_ranking_groups": ["group-a"]}}),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="without the manifest hash"):
            load_learned_configuration(path)
