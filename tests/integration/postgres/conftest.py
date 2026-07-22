from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from cognitive_os.events.base import EventEnvelope
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine


def pytest_collection_modifyitems(items) -> None:
    for item in items:
        item.add_marker(pytest.mark.integration)
        item.add_marker(pytest.mark.postgres)


@pytest.fixture(scope="session")
def database_urls() -> tuple[str, str]:
    app_url = os.environ.get("COGOS_DATABASE_URL")
    admin_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not app_url or not admin_url:
        pytest.skip("PostgreSQL integration URLs are not configured")
    return app_url, admin_url


@pytest_asyncio.fixture
async def engines(database_urls) -> AsyncIterator[tuple[object, object]]:
    app = create_postgres_engine(database_urls[0], pool_size=2, max_overflow=2)
    admin = create_postgres_engine(database_urls[1], pool_size=2, max_overflow=2)
    async with admin.connect() as connection:
        database_name = await connection.scalar(text("SELECT current_database()"))
        if not str(database_name).endswith("_test"):
            pytest.fail(f"refusing integration tests against database: {database_name}")
    async with admin.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE cognitive_os.routing_accesses, cognitive_os.routing_experiments, "
                "cognitive_os.change_accesses, cognitive_os.change_rollbacks, "
                "cognitive_os.change_promotions, cognitive_os.change_promotion_assessments, "
                "cognitive_os.change_regression_comparisons, cognitive_os.change_evaluation_runs, "
                "cognitive_os.change_candidate_artifacts, cognitive_os.change_candidates, "
                "cognitive_os.change_isolation_manifests, "
                "cognitive_os.change_experiment_revisions, cognitive_os.change_experiments, "
                "cognitive_os.harness_proposal_accesses, cognitive_os.harness_proposal_queue, "
                "cognitive_os.harness_proposal_reviews, "
                "cognitive_os.harness_proposal_rollback_plans, "
                "cognitive_os.harness_proposal_validation_plans, "
                "cognitive_os.harness_proposal_risks, cognitive_os.harness_proposal_alternatives, "
                "cognitive_os.harness_proposal_sources, cognitive_os.harness_proposal_revisions, "
                "cognitive_os.harness_proposals, "
                "cognitive_os.weakness_accesses, cognitive_os.weakness_queue, "
                "cognitive_os.weakness_impact_scores, cognitive_os.weakness_sources, "
                "cognitive_os.weakness_revisions, cognitive_os.weakness_items, "
                "cognitive_os.weakness_cluster_members, cognitive_os.weakness_clusters, "
                "cognitive_os.weakness_signals, cognitive_os.weakness_mining_runs, "
                "cognitive_os.routing_statistics, cognitive_os.routing_outcomes, "
                "cognitive_os.routing_decisions, cognitive_os.routing_observations, "
                "cognitive_os.routing_policy_revisions, cognitive_os.routing_policies, "
                "cognitive_os.model_capability_revisions, "
                "cognitive_os.model_capability_profiles, cognitive_os.experience_accesses, "
                "cognitive_os.corpus_accesses, cognitive_os.corpus_exports, "
                "cognitive_os.corpus_manifest_items, cognitive_os.corpus_manifests, "
                "cognitive_os.corpus_route_decisions, cognitive_os.corpus_classifications, "
                "cognitive_os.corpus_item_sources, cognitive_os.corpus_items, "
                "cognitive_os.corpus_sources, "
                "cognitive_os.experience_candidate_sources, "
                "cognitive_os.experience_candidate_revisions, "
                "cognitive_os.experience_decisions, cognitive_os.experience_candidates, "
                "cognitive_os.experience_step_assessments, cognitive_os.experience_snapshots, "
                "cognitive_os.experience_sources, cognitive_os.experience_compilations, "
                "cognitive_os.strategy_accesses, cognitive_os.strategy_statistics, "
                "cognitive_os.strategy_outcomes, cognitive_os.strategy_selections, "
                "cognitive_os.strategy_edges, cognitive_os.strategy_sources, "
                "cognitive_os.strategy_revisions, cognitive_os.strategy_items, "
                "cognitive_os.skill_accesses, cognitive_os.skill_statistics, "
                "cognitive_os.skill_execution_steps, cognitive_os.skill_executions, "
                "cognitive_os.skill_package_artifacts, cognitive_os.skill_requirements, "
                "cognitive_os.skill_sources, cognitive_os.skill_revisions, "
                "cognitive_os.skill_items, cognitive_os.semantic_accesses, "
                "cognitive_os.wiki_page_claims, "
                "cognitive_os.wiki_page_revisions, cognitive_os.wiki_pages, "
                "cognitive_os.semantic_contradiction_claims, "
                "cognitive_os.semantic_contradiction_revisions, "
                "cognitive_os.semantic_contradictions, cognitive_os.semantic_claim_relations, "
                "cognitive_os.semantic_claim_evidence, cognitive_os.semantic_claim_revisions, "
                "cognitive_os.semantic_claims, cognitive_os.semantic_observations, "
                "cognitive_os.memory_accesses, cognitive_os.memory_embeddings, "
                "cognitive_os.memory_sources, cognitive_os.memory_revisions, "
                "cognitive_os.memory_items, cognitive_os.artifacts, cognitive_os.artifact_blobs, "
                "cognitive_os.events, cognitive_os.event_streams RESTART IDENTITY CASCADE"
            )
        )
    try:
        yield app, admin
    finally:
        await app.dispose()
        await admin.dispose()


@pytest.fixture
def make_envelope() -> Callable[..., EventEnvelope]:
    template = EventEnvelope.model_validate_json(
        Path("tests/fixtures/contracts/v1/task-created-envelope.json").read_bytes()
    )

    def factory(
        *,
        stream_id: UUID,
        version: int,
        event_id: UUID | None = None,
        stream_type: str = "task",
    ) -> EventEnvelope:
        values = template.model_dump()
        values.update(
            event_id=event_id or uuid4(),
            stream_id=stream_id,
            stream_version=version,
            stream_type=stream_type,
            correlation_id=stream_id,
        )
        return EventEnvelope.model_validate(values)

    return factory
