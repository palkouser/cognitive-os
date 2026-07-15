from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from cognitive_os.domain.memory import MemoryScope, MemoryScopeType, MemorySensitivity
from cognitive_os.domain.semantic_memory import (
    ClaimProposal,
    ClaimTemporalInterval,
    ContradictionProposal,
    ContradictionSeverity,
    ExtractionBudget,
    ObservationProposal,
    RelationProposal,
    SemanticEntityRef,
    SemanticExtractionProposal,
    SemanticLiteral,
    SemanticLiteralKind,
    SemanticSourceRef,
    SemanticSourceType,
)
from cognitive_os.semantic_memory.predicates import build_default_predicate_registry

NOW = datetime(2026, 7, 15, tzinfo=UTC)


def test_checked_in_canonical_proposal_round_trip_preserves_hash_and_identities() -> None:
    path = Path("tests/fixtures/contracts/v1/semantic-extraction-proposal.json")
    proposal = SemanticExtractionProposal.model_validate_json(path.read_bytes())
    restored = SemanticExtractionProposal.model_validate_json(proposal.model_dump_json())

    assert restored == proposal
    assert restored.extraction_id == UUID(int=4)
    assert restored.observations[0].proposal_id == UUID(int=1)
    assert restored.claims[0].proposal_id == UUID(int=2)
    assert restored.canonical_hash() == (
        "91938eba6535de4489d231019cfaa1e663bdd8c2ff6a3969bc55ee9add5eadc1"
    )


@given(
    start=st.integers(min_value=-365, max_value=365),
    length=st.integers(min_value=1, max_value=365),
)
def test_half_open_interval_contains_start_and_excludes_end(start: int, length: int) -> None:
    valid_from = NOW + timedelta(days=start)
    valid_to = valid_from + timedelta(days=length)
    interval = ClaimTemporalInterval(valid_from=valid_from, valid_to=valid_to)
    assert interval.contains(valid_from)
    assert interval.contains(valid_to - timedelta(microseconds=1))
    assert not interval.contains(valid_to)


@given(
    left=st.integers(min_value=-100, max_value=100),
    right=st.integers(min_value=-100, max_value=100),
)
def test_interval_overlap_is_symmetric(left: int, right: int) -> None:
    first = ClaimTemporalInterval(
        valid_from=NOW + timedelta(days=left),
        valid_to=NOW + timedelta(days=left + 10),
    )
    second = ClaimTemporalInterval(
        valid_from=NOW + timedelta(days=right),
        valid_to=NOW + timedelta(days=right + 10),
    )
    assert first.overlaps(second) == second.overlaps(first)


def test_extraction_proposal_references_are_bounded_and_closed() -> None:
    registry = build_default_predicate_registry()
    observation_id, claim_id = UUID(int=1), UUID(int=2)
    source = SemanticSourceRef(
        source_type=SemanticSourceType.MEMORY_REVISION,
        source_id=UUID(int=3),
        revision=1,
        content_hash="a" * 64,
    )
    observation = ObservationProposal(
        proposal_id=observation_id,
        content="Python 3.12",
        source_spans=(
            {
                "source": source,
                "mode": "memory_field",
                "path": "content.observation",
                "excerpt_hash": "b" * 64,
            },
        ),
    )
    claim = ClaimProposal(
        proposal_id=claim_id,
        subject=SemanticEntityRef(
            entity_id="project:cognitive-os",
            entity_type="project",
            display_label="Cognitive OS",
        ),
        predicate_id="project.python_version",
        object=SemanticLiteral(literal_kind=SemanticLiteralKind.VERSION, value="3.12", unit=None),
        valid_interval=ClaimTemporalInterval(valid_from=NOW),
        observation_proposal_ids=(observation_id,),
    )
    second_claim = claim.model_copy(
        update={
            "proposal_id": UUID(int=8),
            "object": SemanticLiteral(
                literal_kind=SemanticLiteralKind.VERSION, value="3.13", unit=None
            ),
        }
    )
    budget = ExtractionBudget(
        maximum_observations=1,
        maximum_claims=2,
        maximum_evidence_links=1,
        maximum_relations=1,
    )
    proposal = SemanticExtractionProposal(
        extraction_id=UUID(int=4),
        registry_snapshot_hash=registry.snapshot_hash(),
        observations=(observation,),
        claims=(claim, second_claim),
        contradictions=(
            ContradictionProposal(
                proposal_id=UUID(int=5),
                claim_proposal_ids=(claim_id, second_claim.proposal_id),
                rule_id="provider-candidate-only",
                severity=ContradictionSeverity.LOW,
            ),
        ),
        budget=budget,
    )
    assert proposal.claims[0].observation_proposal_ids == (observation_id,)
    with pytest.raises(ValidationError, match="unknown claim proposal"):
        SemanticExtractionProposal(
            extraction_id=UUID(int=6),
            registry_snapshot_hash=registry.snapshot_hash(),
            observations=(observation,),
            claims=(claim, second_claim),
            relations=(
                RelationProposal(
                    proposal_id=UUID(int=7),
                    source_claim_proposal_id=claim_id,
                    target_claim_proposal_id=UUID(int=99),
                    relation_type="supersedes",
                    valid_interval=ClaimTemporalInterval(valid_from=NOW),
                ),
            ),
            budget=budget,
        )


def test_proposals_do_not_accept_scope_or_sensitivity_authority_fields() -> None:
    scope = MemoryScope(scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os")
    with pytest.raises(ValidationError):
        ClaimProposal.model_validate(
            {
                "proposal_id": UUID(int=20),
                "subject": {
                    "entity_id": "project:cognitive-os",
                    "entity_type": "project",
                    "display_label": "Cognitive OS",
                },
                "predicate_id": "project.python_version",
                "object": {"literal_kind": "version", "value": "3.12"},
                "valid_interval": {"valid_from": NOW},
                "observation_proposal_ids": [UUID(int=21)],
                "scope": scope,
                "sensitivity": MemorySensitivity.RESTRICTED,
            }
        )
