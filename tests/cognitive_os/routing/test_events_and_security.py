import pytest
from pydantic import ValidationError

from cognitive_os.domain.routing import (
    CapabilityEvidenceType,
    RoutingObservationStatus,
)
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.routing_events import ROUTING_EVENT_MODELS
from cognitive_os.routing.fixtures import build_observations
from cognitive_os.verification.routing import MANDATORY_ROUTING_VERIFIERS, verify_observation


def test_routing_events_and_verifier_bundle_are_registered() -> None:
    registered = build_default_event_catalog().list_event_types()
    assert all((model.event_type, 1) in registered for model in ROUTING_EVENT_MODELS)
    assert len(MANDATORY_ROUTING_VERIFIERS) == 18


def test_provider_self_description_cannot_claim_measured_success() -> None:
    observation = build_observations(1)[0]
    payload = observation.model_dump(exclude={"content_hash"})
    payload.update(
        evidence_type=CapabilityEvidenceType.PROVIDER_SELF_DESCRIPTION,
        status=RoutingObservationStatus.ACCEPTED,
    )
    with pytest.raises(ValidationError):
        type(observation).model_validate(payload)
    assert verify_observation(observation) == ()
