"""Sprint 21.3: the capacity envelope and the retrieval mode that produces it.

The envelope's job is to stop a flattering number reaching a report. Most of these
tests are therefore refusals, and each one corresponds to a mistake that was actually
made while building the measurement.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cognitive_os.domain.learned import RetrievalCapacityEnvelope
from cognitive_os.domain.memory import (
    HNSW_MAXIMUM_DIMENSIONS,
    MemoryQuery,
    MemoryRetrievalMode,
    MemoryVectorQuery,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME

LIMITATION = "synthetic vectors"


def envelope(**overrides: object) -> RetrievalCapacityEnvelope:
    fields: dict[str, object] = {
        "envelope_id": uuid4(),
        "retrieval_mode": "vector_approximate",
        "embedding_dimension": 768,
        "corpus_vector_count": 100_000,
        "queries_measured": 50,
        "result_limit": 20,
        "candidate_limit": 1_000,
        "latency_p50_ms": Decimal("4.100"),
        "latency_p95_ms": Decimal("9.900"),
        "recall_at_result_limit": Decimal("0.950"),
        "ef_search": 1_000,
        "index_scan_confirmed": True,
        "limitations": (LIMITATION,),
        "created_at": FIXTURE_TIME,
    }
    fields.update(overrides)
    return RetrievalCapacityEnvelope(**fields)  # type: ignore[arg-type]


def vector_query(dimension: int) -> MemoryVectorQuery:
    return MemoryVectorQuery(
        provider_id="deterministic-test",
        model_id="deterministic-v1",
        dimension=dimension,
        vector=tuple(0.5 for _ in range(dimension)),
    )


class TestApproximateMode:
    def test_the_mode_is_recorded_distinctly_from_exact_retrieval(self) -> None:
        """Whether a result came from an index or a full scan must stay answerable."""
        assert MemoryRetrievalMode.VECTOR_APPROXIMATE.value == "vector_approximate"
        assert MemoryRetrievalMode.VECTOR_APPROXIMATE is not MemoryRetrievalMode.VECTOR
        assert MemoryRetrievalMode.VECTOR_APPROXIMATE.is_vector
        assert MemoryRetrievalMode.VECTOR.is_vector
        assert not MemoryRetrievalMode.METADATA.is_vector

    def test_an_approximate_query_still_requires_a_vector(self) -> None:
        with pytest.raises(ValidationError, match="vector retrieval requires"):
            MemoryQuery(query_id=uuid4(), mode=MemoryRetrievalMode.VECTOR_APPROXIMATE)

    def test_an_unindexable_dimension_cannot_be_requested_approximately(self) -> None:
        """pgvector cannot index above its ceiling, so the request is unsatisfiable."""
        with pytest.raises(ValidationError, match="approximate retrieval is impossible"):
            MemoryQuery(
                query_id=uuid4(),
                mode=MemoryRetrievalMode.VECTOR_APPROXIMATE,
                vector=vector_query(HNSW_MAXIMUM_DIMENSIONS + 1),
            )

    def test_the_same_dimension_remains_available_exactly(self) -> None:
        """A dimension no index can cover is still searchable, just not quickly."""
        query = MemoryQuery(
            query_id=uuid4(),
            mode=MemoryRetrievalMode.VECTOR,
            vector=vector_query(HNSW_MAXIMUM_DIMENSIONS + 1),
        )
        assert query.mode is MemoryRetrievalMode.VECTOR


class TestEnvelopeHonesty:
    def test_a_well_formed_approximate_envelope_is_accepted(self) -> None:
        assert envelope().approximate
        assert envelope().recall_at_result_limit == Decimal("0.950")

    def test_an_approximate_envelope_without_recall_is_refused(self) -> None:
        """Latency without recall is the one number an index can always win."""
        with pytest.raises(ValidationError, match="must report the recall"):
            envelope(recall_at_result_limit=None)

    def test_an_exact_envelope_claiming_measured_recall_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="recall 1 by construction"):
            envelope(
                retrieval_mode="vector",
                ef_search=None,
                index_scan_confirmed=None,
                recall_at_result_limit=Decimal(1),
            )

    def test_an_approximate_envelope_without_its_search_effort_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="search effort"):
            envelope(ef_search=None)

    def test_an_approximate_envelope_must_say_whether_the_index_was_used(self) -> None:
        with pytest.raises(ValidationError, match="whether the index was used"):
            envelope(index_scan_confirmed=None)

    def test_an_exact_envelope_has_no_index_scan_to_confirm(self) -> None:
        with pytest.raises(ValidationError, match="no index scan to confirm"):
            envelope(
                retrieval_mode="vector",
                ef_search=None,
                recall_at_result_limit=None,
                index_scan_confirmed=True,
            )

    def test_an_unused_index_reporting_lost_recall_is_a_contradiction(self) -> None:
        """The mistake this validator exists for.

        On a small corpus the planner runs an exhaustive scan instead of the index, and
        recall comes out at 1 for a reason that says nothing about the index. Recording
        that as a *loss* of recall would be incoherent: a full scan cannot miss.
        """
        with pytest.raises(ValidationError, match="cannot miss a neighbour"):
            envelope(index_scan_confirmed=False, recall_at_result_limit=Decimal("0.9"))

    def test_an_unused_index_with_perfect_recall_is_a_valid_finding(self) -> None:
        """Reporting "the planner declined the index" is a result, not an error."""
        measured = envelope(index_scan_confirmed=False, recall_at_result_limit=Decimal(1))
        assert measured.index_scan_confirmed is False

    def test_inverted_percentiles_are_refused(self) -> None:
        with pytest.raises(ValidationError, match="p95 latency cannot be below p50"):
            envelope(latency_p50_ms=Decimal("9.9"), latency_p95_ms=Decimal("4.1"))

    def test_an_envelope_without_limitations_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="state its limitations"):
            envelope(limitations=())

    def test_a_measurement_cannot_be_edited_after_the_fact(self) -> None:
        """The sealed hash is what makes a reported number citable."""
        sealed = envelope()
        tampered = sealed.model_dump() | {"recall_at_result_limit": Decimal("0.5")}
        with pytest.raises(ValidationError, match="hash mismatch"):
            RetrievalCapacityEnvelope.model_validate(tampered)
        assert (
            envelope(recall_at_result_limit=Decimal("0.5")).content_hash != sealed.content_hash
        ), "a different recall is a different measurement"
