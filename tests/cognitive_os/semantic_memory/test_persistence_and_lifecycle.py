from uuid import UUID

import pytest

from cognitive_os.domain.semantic_memory import BeliefStatus, ContradictionStatus
from cognitive_os.events.semantic_memory_events import (
    SemanticClaimBeliefChanged,
    SemanticClaimCreated,
    SemanticClaimRevisionAppended,
    SemanticContradictionCandidateRecorded,
    SemanticContradictionOpened,
    SemanticContradictionResolved,
    SemanticWikiPageRegenerated,
    SemanticWikiPageRendered,
)
from cognitive_os.semantic_memory.lifecycle import (
    SemanticClaimStreamReducer,
    SemanticContradictionStreamReducer,
    SemanticWikiStreamReducer,
)


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


def test_contradiction_replay_handles_candidate_confirmation_and_resolution() -> None:
    contradiction_id = UUID(int=2)
    candidate = SemanticContradictionCandidateRecorded(
        contradiction_id=contradiction_id,
        revision=1,
        claim_ids=(UUID(int=3), UUID(int=4)),
        content_hash="a" * 64,
    )
    opened = SemanticContradictionOpened(
        contradiction_id=contradiction_id,
        revision=2,
        claim_ids=candidate.claim_ids,
        content_hash="b" * 64,
    )
    resolved = SemanticContradictionResolved(
        contradiction_id=contradiction_id,
        expected_revision=2,
        revision=3,
        status=ContradictionStatus.RESOLVED,
        content_hash="c" * 64,
        resolution_id=UUID(int=5),
    )
    state = SemanticContradictionStreamReducer().reduce((candidate, opened, resolved))
    assert state.current_revision == 3
    assert state.status is ContradictionStatus.RESOLVED
    with pytest.raises(ValueError, match="prior creation"):
        SemanticContradictionStreamReducer().reduce((resolved,))
    with pytest.raises(ValueError, match="gap"):
        SemanticContradictionStreamReducer().reduce(
            (candidate, opened.model_copy(update={"revision": 3}))
        )


def test_wiki_replay_rejects_revision_gaps_and_nonidentical_regeneration() -> None:
    page_id = UUID(int=6)
    rendered = SemanticWikiPageRendered(
        page_id=page_id,
        revision=1,
        content_hash="d" * 64,
        snapshot_hash="e" * 64,
    )
    regenerated = SemanticWikiPageRegenerated(
        page_id=page_id,
        revision=1,
        content_hash="d" * 64,
        identical=True,
    )
    assert SemanticWikiStreamReducer().reduce((rendered, regenerated)).current_revision == 1
    with pytest.raises(ValueError, match="does not match"):
        SemanticWikiStreamReducer().reduce(
            (rendered, regenerated.model_copy(update={"identical": False}))
        )
    with pytest.raises(ValueError, match="gap"):
        SemanticWikiStreamReducer().reduce((rendered, rendered.model_copy(update={"revision": 3})))
