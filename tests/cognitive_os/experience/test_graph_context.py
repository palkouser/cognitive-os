"""The Experience Graph context source, its retriever, and the advisory path end to end.

S21D1-055, 056 and 057. The properties under test are the ones that keep retrieved
history advisory: never pinned, never required, no execution authority, verified only
when the evidence resolves, and a deterministic fallback when it does not.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest

from cognitive_os.config.context_config import ContextConfiguration
from cognitive_os.context.assembly import assemble_bundle
from cognitive_os.context.fixtures import SPRINT11_SOURCE_TYPES
from cognitive_os.context.ranking import rank_candidates, ranking_profile
from cognitive_os.context.retrieval import _SOURCE_TRUST
from cognitive_os.context.safety import filter_unsafe_candidates
from cognitive_os.context.tokenization import ConservativeUtf8TokenEstimator
from cognitive_os.domain.context import (
    ContextComponentStatus,
    ContextPurpose,
    ContextSourceType,
    ContextTrustClass,
    RetrievalMode,
    RetrievalSubquery,
)
from cognitive_os.domain.experience_graph import (
    ActionDecisionGraph,
    ExperienceGraphEdge,
    ExperienceGraphEdgeKind,
    ExperienceGraphNode,
    ExperienceGraphNodeKind,
    FailedSuccessGraphPair,
    GraphResourceLimits,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME
from cognitive_os.experience import graph_retrieval
from cognitive_os.experience.graph_context import ExperienceGraphContextRetriever
from cognitive_os.experience.graph_projection import derive_edit_path
from tests.cognitive_os.context.helpers import (
    context_candidate,
    context_request,
    provider_profile,
)

HASH = "c" * 64
ARTIFACT = UUID(int=7)


def _graph(count: int, *, accepted: bool, group: str, signature: str) -> ActionDecisionGraph:
    nodes = tuple(
        ExperienceGraphNode(
            logical_id=f"s{index:04d}",
            kind=ExperienceGraphNodeKind.OBSERVATION,
            attributes=(("status", "completed"),),
            source_hash=HASH,
        )
        for index in range(1, count + 1)
    )
    edges = tuple(
        ExperienceGraphEdge(
            source_id=f"s{index:04d}",
            target_id=f"s{index + 1:04d}",
            kind=ExperienceGraphEdgeKind.NEXT,
        )
        for index in range(1, count)
    )
    return ActionDecisionGraph(
        graph_id=f"{signature}:{'ok' if accepted else 'failed'}",
        domain="logic",
        group=group,
        task_signature=signature,
        accepted=accepted,
        nodes=nodes,
        edges=edges,
        source_manifest_hash=HASH,
    )


def _pair(group: str, signature: str) -> FailedSuccessGraphPair:
    failed = _graph(2, accepted=False, group=group, signature=signature)
    successful = _graph(3, accepted=True, group=group, signature=signature)
    return FailedSuccessGraphPair(
        pair_id=signature,
        domain="logic",
        group=group,
        task_signature=signature,
        failed=failed,
        successful=successful,
        edit_path=derive_edit_path(failed, successful, path_id=signature),
        legacy_recompilation_unavailable=False,
        verification_mode="byte_identical_recompilation",
        compiled_at=FIXTURE_TIME,
    )


PAIRS = (_pair("logic.alpha", "logic:alpha"), _pair("logic.beta", "logic:beta"))


def _subquery(mode: RetrievalMode = RetrievalMode.METADATA) -> RetrievalSubquery:
    return RetrievalSubquery(
        subquery_id=UUID(int=42),
        source_type=ContextSourceType.EXPERIENCE_GRAPH,
        mode=mode,
        terms=(),
        maximum_results=10,
    )


def _repair_request(query: str):
    return context_request(ContextSourceType.EXPERIENCE_GRAPH).model_copy(
        update={"context_purpose": ContextPurpose.REPAIR, "query": query}
    )


async def _ok(_: UUID) -> bool:
    return True


async def _corrupt(_: UUID) -> bool:
    raise OSError("artifact bytes are unreadable")


class TestSourceTypeIsAdditive:
    def test_the_new_source_type_exists_and_defaults_to_fail_closed(self) -> None:
        assert _SOURCE_TRUST[ContextSourceType.EXPERIENCE_GRAPH] is ContextTrustClass.UNVERIFIED
        assert set(_SOURCE_TRUST) == set(ContextSourceType), "every source type declares a trust"

    def test_sprint_11_fixtures_do_not_see_the_new_type(self) -> None:
        assert ContextSourceType.EXPERIENCE_GRAPH not in SPRINT11_SOURCE_TYPES


class TestRetriever:
    @pytest.mark.asyncio
    async def test_candidates_are_advisory_never_pinned_and_never_required(self) -> None:
        retriever = ExperienceGraphContextRetriever(PAIRS)
        candidates = await retriever.retrieve(_subquery(), _repair_request("some failure"))
        assert candidates
        for candidate in candidates:
            assert candidate.source_type is ContextSourceType.EXPERIENCE_GRAPH
            assert not candidate.pinned
            assert not candidate.required
            assert not candidate.evidence
            assert candidate.provenance

    @pytest.mark.asyncio
    async def test_the_query_group_is_excluded_from_its_own_pool(self) -> None:
        retriever = ExperienceGraphContextRetriever(PAIRS)
        request = _repair_request("repair for logic:alpha please")
        assert retriever.excluded_groups(request) == frozenset({"logic.alpha"})
        candidates = await retriever.retrieve(_subquery(), request)
        assert [c.source_identity for c in candidates] == ["logic:beta"]

    @pytest.mark.asyncio
    async def test_a_non_advisory_purpose_gets_nothing(self) -> None:
        retriever = ExperienceGraphContextRetriever(PAIRS)
        planning = context_request(ContextSourceType.EXPERIENCE_GRAPH).model_copy(
            update={"context_purpose": ContextPurpose.PLANNING}
        )
        assert await retriever.retrieve(_subquery(), planning) == ()

    @pytest.mark.asyncio
    async def test_verified_requires_a_resolvable_artifact(self) -> None:
        without = ExperienceGraphContextRetriever(PAIRS)
        candidates = await without.retrieve(_subquery(), _repair_request("failure"))
        assert all(c.trust_class is ContextTrustClass.UNVERIFIED for c in candidates)

        with_evidence = ExperienceGraphContextRetriever(
            PAIRS,
            artifact_ids={pair.pair_id: ARTIFACT for pair in PAIRS},
            verifier=_ok,
        )
        verified = await with_evidence.retrieve(_subquery(), _repair_request("failure"))
        assert all(c.trust_class is ContextTrustClass.VERIFIED for c in verified)

    @pytest.mark.asyncio
    async def test_corrupt_evidence_degrades_rather_than_raising(self) -> None:
        retriever = ExperienceGraphContextRetriever(
            PAIRS,
            artifact_ids={pair.pair_id: ARTIFACT for pair in PAIRS},
            verifier=_corrupt,
        )
        candidates = await retriever.retrieve(_subquery(), _repair_request("failure"))
        assert candidates, "a corrupt store must stay visible, not look like an empty corpus"
        assert all(c.trust_class is ContextTrustClass.UNVERIFIED for c in candidates)

    @pytest.mark.asyncio
    async def test_a_foreign_subquery_is_refused(self) -> None:
        retriever = ExperienceGraphContextRetriever(PAIRS)
        foreign = _subquery().model_copy(update={"source_type": ContextSourceType.MEMORY})
        with pytest.raises(ValueError, match="only its own subqueries"):
            await retriever.retrieve(foreign, _repair_request("failure"))

    @pytest.mark.asyncio
    async def test_cancellation_is_honoured(self) -> None:
        retriever = ExperienceGraphContextRetriever(PAIRS)
        cancelled = asyncio.Event()
        cancelled.set()
        with pytest.raises(asyncio.CancelledError):
            await retriever.retrieve(_subquery(), _repair_request("failure"), cancelled)

    @pytest.mark.asyncio
    async def test_an_empty_set_is_degraded_not_unavailable(self) -> None:
        empty = ExperienceGraphContextRetriever(())
        health = await empty.health_check()
        assert health.status is ContextComponentStatus.DEGRADED
        assert await empty.retrieve(_subquery(), _repair_request("failure")) == ()

    @pytest.mark.asyncio
    async def test_results_are_bounded_by_the_resource_policy(self) -> None:
        many = tuple(_pair(f"logic.g{index}", f"logic:t{index}") for index in range(25))
        retriever = ExperienceGraphContextRetriever(many)
        candidates = await retriever.retrieve(_subquery(), _repair_request("failure"))
        assert len(candidates) == 10


class TestAdvisoryContextPath:
    @pytest.mark.asyncio
    async def test_graph_candidates_compete_under_existing_ranking_and_safety(self) -> None:
        retriever = ExperienceGraphContextRetriever(
            PAIRS, artifact_ids={p.pair_id: ARTIFACT for p in PAIRS}, verifier=_ok
        )
        request = _repair_request("a failing logic step")
        candidates = await retriever.retrieve(_subquery(), request)

        safe, exclusions, _ = filter_unsafe_candidates(
            candidates, sensitivity_limit=request.sensitivity_limit
        )
        assert not exclusions, "nothing in a graph candidate is unsafe content"
        assert len(safe) == len(candidates)

        ranked = rank_candidates(safe, request, ranking_profile(ContextConfiguration()))
        assert {c.source_type for c in ranked} == {ContextSourceType.EXPERIENCE_GRAPH}
        assert all(not c.required and not c.pinned for c in ranked)

    @pytest.mark.asyncio
    async def test_the_bundle_carries_a_suggestion_and_never_an_executable_patch(self) -> None:
        retriever = ExperienceGraphContextRetriever(
            PAIRS, artifact_ids={p.pair_id: ARTIFACT for p in PAIRS}, verifier=_ok
        )
        request = _repair_request("a failing logic step")
        candidates = await retriever.retrieve(_subquery(), request)
        bundle = assemble_bundle(
            bundle_id=UUID(int=99),
            revision=1,
            previous_revision=None,
            request=request,
            candidates=candidates,
            exclusions=(),
            warnings=(),
            ranking_profile=ranking_profile(ContextConfiguration()),
            provider_profile=provider_profile(),
            estimator=ConservativeUtf8TokenEstimator(),
        )
        rendered = " ".join(section.content for section in bundle.sections)
        assert "suggested edit operations" in rendered
        assert "Advisory only" in rendered
        for candidate in candidates:
            assert candidate.content is None, "a candidate carries no patch body to execute"


class TestTheAdvisoryBoundarySurvivesTheWidth20Policy:
    """S21D2-036. The shortlist repair must not leak into the advisory path.

    The retriever scores its own pool and truncates on `returned_results`; it never calls
    `minilm_vector` or `bounded_ged`. So widening the internal shortlist is expected to change
    nothing here — and 'expected' is why this is a test rather than a note.
    """

    @pytest.mark.asyncio
    async def test_widening_the_shortlist_changes_no_advisory_candidate(self) -> None:
        width_10 = ExperienceGraphContextRetriever(
            PAIRS, limits=GraphResourceLimits(vector_shortlist=10, returned_results=10)
        )
        width_20 = ExperienceGraphContextRetriever(
            PAIRS, limits=GraphResourceLimits(vector_shortlist=20, returned_results=10)
        )
        request = _repair_request("some failure")

        before = await width_10.retrieve(_subquery(), request)
        after = await width_20.retrieve(_subquery(), request)

        assert [c.candidate_id for c in before] == [c.candidate_id for c in after]
        assert [c.provenance for c in before] == [c.provenance for c in after]

    @pytest.mark.asyncio
    async def test_the_revision_2_policy_keeps_every_advisory_property(self) -> None:
        retriever = ExperienceGraphContextRetriever(
            PAIRS,
            limits=GraphResourceLimits(
                vector_shortlist=20, returned_results=10, per_pair_ged_timeout_ms=90
            ),
        )

        candidates = await retriever.retrieve(_subquery(), _repair_request("some failure"))

        assert candidates
        for candidate in candidates:
            assert not candidate.pinned
            assert not candidate.required
            assert not candidate.evidence

    @pytest.mark.asyncio
    async def test_the_returned_bound_still_governs_what_the_builder_sees(self) -> None:
        """`returned_results` is the advisory bound; `vector_shortlist` is not one here."""
        retriever = ExperienceGraphContextRetriever(
            PAIRS, limits=GraphResourceLimits(vector_shortlist=20, returned_results=1)
        )

        candidates = await retriever.retrieve(_subquery(), _repair_request("some failure"))

        assert len(candidates) <= 1


class TestTheAdvisoryBoundarySurvivesTheFusionArm:
    """S21D3-047. W3 adds a retrieval arm; it must add no authority.

    The properties are the released ones, restated against the new arm rather than assumed
    to carry over: an advisory candidate is never pinned, required or evidence, it never
    carries an executable body, the mandatory part of a bundle is byte-identical whether or
    not retrieval contributed, and an arm that fails leaves the deterministic path intact.
    """

    @pytest.mark.asyncio
    async def test_the_context_retriever_never_calls_the_fusion_arm(self) -> None:
        """It has no embedding provider at all, so it cannot have called a vector arm."""
        retriever = ExperienceGraphContextRetriever(PAIRS)
        candidates = await retriever.retrieve(_subquery(), _repair_request("some failure"))

        assert candidates
        assert {route.retriever_id for c in candidates for route in c.retrieval_routes} == {
            "context.experience_graph"
        }
        assert graph_retrieval.RECIPROCAL_RANK_FUSION not in {
            route.mode.value for c in candidates for route in c.retrieval_routes
        }

    @pytest.mark.asyncio
    async def test_the_mandatory_path_is_byte_identical_with_and_without_retrieval(self) -> None:
        """The hash comparison S21D3-047 asks for: advisory context cannot move it."""
        retriever = ExperienceGraphContextRetriever(
            PAIRS, artifact_ids={p.pair_id: ARTIFACT for p in PAIRS}, verifier=_ok
        )
        request = _repair_request("a failing logic step")
        graph_candidates = await retriever.retrieve(_subquery(), request)
        mandatory = context_candidate(
            ContextSourceType.TASK_STATE, "the step under repair", required=True, pinned=True
        )

        advisory = {candidate.candidate_id for candidate in graph_candidates}

        def mandatory_sections(candidates: tuple) -> dict[str, str]:
            """Sections referencing no advisory candidate. Sectioning is by trust class, not
            by source type, so a graph candidate can share a section heading with a mandatory
            one — the candidate references are what say whose bytes are in there."""
            bundle = assemble_bundle(
                bundle_id=UUID(int=77),
                revision=1,
                previous_revision=None,
                request=request,
                candidates=candidates,
                exclusions=(),
                warnings=(),
                ranking_profile=ranking_profile(ContextConfiguration()),
                provider_profile=provider_profile(),
                estimator=ConservativeUtf8TokenEstimator(),
            )
            return {
                section.section_type: section.content_hash
                for section in bundle.sections
                if not advisory & set(section.candidate_references)
            }

        assert graph_candidates
        without = mandatory_sections((mandatory,))
        with_retrieval = mandatory_sections((mandatory, *graph_candidates))

        assert without, "the mandatory path is not empty"
        assert without == with_retrieval

    @pytest.mark.asyncio
    async def test_an_advisory_candidate_carries_no_authority_whatever_ranked_it(self) -> None:
        retriever = ExperienceGraphContextRetriever(
            PAIRS, artifact_ids={p.pair_id: ARTIFACT for p in PAIRS}, verifier=_ok
        )

        candidates = await retriever.retrieve(_subquery(), _repair_request("a failing step"))

        assert candidates
        for candidate in candidates:
            assert not candidate.pinned
            assert not candidate.required
            assert not candidate.evidence
            assert candidate.content is None
            assert candidate.trust_class is ContextTrustClass.VERIFIED
            assert candidate.provenance, "an advisory suggestion still names where it came from"

    @pytest.mark.asyncio
    async def test_a_failing_arm_leaves_the_deterministic_path_valid(self) -> None:
        """No-memory is a result. A retrieval outage degrades the bundle, never the run."""
        empty = ExperienceGraphContextRetriever(())

        health = await empty.health_check()
        candidates = await empty.retrieve(_subquery(), _repair_request("a failing step"))

        assert health.status is ContextComponentStatus.DEGRADED
        assert candidates == ()

    @pytest.mark.asyncio
    async def test_a_corrupt_store_cannot_promote_a_suggestion(self) -> None:
        """A retrieval failure must not be able to raise trust; it can only lower it."""
        retriever = ExperienceGraphContextRetriever(
            PAIRS, artifact_ids={p.pair_id: ARTIFACT for p in PAIRS}, verifier=_corrupt
        )

        candidates = await retriever.retrieve(_subquery(), _repair_request("a failing step"))

        assert candidates
        assert {c.trust_class for c in candidates} == {ContextTrustClass.UNVERIFIED}
