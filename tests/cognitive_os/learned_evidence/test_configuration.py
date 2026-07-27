"""S21C1-070: the shipped learned configuration, and what it refuses to become.

The defaults are the safety argument, so they are asserted rather than trusted. Four
settings are permanently false in Sprint 21C1 and the loader refuses to start if any is
true — they exist as named options precisely so the refusal is explicit instead of
implied by their absence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cognitive_os.config.learned_config import (
    LearnedPersistenceConfiguration,
    load_learned_configuration,
)

EXAMPLE = Path("config/learned.example.yaml")


def test_the_shipped_configuration_activates_nothing() -> None:
    """A deployment that changes nothing runs the deterministic system unchanged."""
    config = load_learned_configuration(EXAMPLE)
    assert config.persistence_enabled
    assert not config.activation_enabled
    assert config.activation_actors == ()
    assert config.active_components == ()
    assert config.quarantine_reviewers == ()


def test_the_shipped_configuration_forbids_every_ungoverned_option() -> None:
    config = load_learned_configuration(EXAMPLE)
    assert not config.artifact_deserialisation_enabled
    assert not config.model_approval_enabled
    assert not config.model_review_enabled
    assert not config.real_run_training_enabled


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("artifact_deserialisation_enabled", "artifact deserialisation cannot be enabled"),
        ("model_approval_enabled", "cannot approve an activation"),
        ("model_review_enabled", "cannot approve an activation"),
        ("real_run_training_enabled", "evaluation-only"),
    ],
)
def test_enabling_a_forbidden_option_refuses_to_load(field: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        LearnedPersistenceConfiguration(**{field: True})


def test_active_components_without_activation_is_contradictory() -> None:
    """The configuration would contradict itself, and the safe reading is not obvious."""
    with pytest.raises(ValueError, match="contradicts itself"):
        LearnedPersistenceConfiguration(active_components=("reference.ranker.abstaining",))


def test_activation_without_an_authorised_actor_is_refused() -> None:
    with pytest.raises(ValueError, match="no authorised actor"):
        LearnedPersistenceConfiguration(activation_enabled=True)


def test_a_fully_specified_activation_configuration_is_accepted() -> None:
    """The safe defaults must be a default, not a cage: a real operator can open it."""
    config = LearnedPersistenceConfiguration(
        activation_enabled=True,
        activation_actors=("release-operator",),
        active_components=("reference.ranker.abstaining",),
    )
    assert config.activation_actors == ("release-operator",)


def test_the_loader_requires_a_learned_mapping(tmp_path: Path) -> None:
    path = tmp_path / "wrong.yaml"
    path.write_text("something_else: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="requires a learned mapping"):
        load_learned_configuration(path)
