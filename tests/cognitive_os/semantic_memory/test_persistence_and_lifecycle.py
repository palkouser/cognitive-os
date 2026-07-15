from uuid import UUID

import pytest

from cognitive_os.domain.semantic_memory import BeliefStatus
from cognitive_os.events.semantic_memory_events import (
    SemanticClaimBeliefChanged,
    SemanticClaimCreated,
    SemanticClaimRevisionAppended,
)
from cognitive_os.semantic_memory.lifecycle import SemanticClaimStreamReducer


def test_semantic_tables_are_registered_without_graph_extensions() -> None:
    pytest.importorskip("sqlalchemy")
    from cognitive_os.infrastructure.postgres.tables import metadata
    from cognitive_os.infrastructure.semantic_memory.postgres.tables import SEMANTIC_TABLES

    expected = {
        "semantic_observations",
        "semantic_claims",
        "semantic_claim_revisions",
        "semantic_claim_evidence",
        "semantic_claim_relations",
        "semantic_contradictions",
        "semantic_contradiction_revisions",
        "semantic_contradiction_claims",
        "wiki_pages",
        "wiki_page_revisions",
        "wiki_page_claims",
        "semantic_accesses",
    }
    assert {table.name for table in SEMANTIC_TABLES} == expected
    assert {f"cognitive_os.{name}" for name in expected} <= set(metadata.tables)
    assert not any(
        "hnsw" in index.name or "ivfflat" in index.name
        for table in SEMANTIC_TABLES
        for index in table.indexes
    )


def test_claim_replay_rejects_revision_gaps_and_illegal_transitions() -> None:
    claim_id = UUID(int=1)
    created = SemanticClaimCreated(claim_id=claim_id, revision=1, content_hash="a" * 64)
    appended = SemanticClaimRevisionAppended(
        claim_id=claim_id,
        expected_revision=1,
        revision=2,
        content_hash="b" * 64,
    )
    state = SemanticClaimStreamReducer().reduce((created, appended), BeliefStatus.PROPOSED)
    assert state.current_revision == 2
    with pytest.raises(ValueError, match="gap"):
        SemanticClaimStreamReducer().reduce(
            (
                created,
                appended.model_copy(update={"revision": 3}),
            ),
            BeliefStatus.PROPOSED,
        )
    with pytest.raises(ValueError, match="illegal"):
        SemanticClaimStreamReducer().reduce(
            (
                created,
                SemanticClaimBeliefChanged(
                    claim_id=claim_id,
                    expected_revision=1,
                    revision=2,
                    previous_status=BeliefStatus.PROPOSED,
                    status=BeliefStatus.SUPERSEDED,
                ),
            ),
            BeliefStatus.PROPOSED,
        )
