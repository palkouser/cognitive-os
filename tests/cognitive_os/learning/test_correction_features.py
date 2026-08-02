"""S21D2-023: the pre-outcome feature record is derived from pre-outcome things only.

The feature contract's timing rule is the whole point of this module, and a timing rule is
only checkable if there is one place the numbers come from. These tests pin what that place
reads — the task text, the candidate source and the stored diff — and what the sealed record
carries when it is written, which is before any container has started.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid5

import pytest

from cognitive_os.learning.correction_features import (
    DECLARED_VERIFIER_CAPABILITIES,
    PendingFeature,
    SealedFeatureRecordSet,
    ast_node_count,
    diff_counts,
    feature_input,
    raw_numeric_row,
    requirement_text,
    seal_feature_records,
    statement_graph,
)
from cognitive_os.learning.correction_ranking import (
    NUMERIC_FEATURE_NAMES,
    CorrectionEncoder,
    NumericBounds,
)

NAMESPACE = uuid5(uuid5(__import__("uuid").NAMESPACE_URL, "cogos"), "d2-features-test")
SEALED_AT = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)

DIFF = """diff --git a/src/m.py b/src/m.py
--- a/src/m.py
+++ b/src/m.py
@@ -1,4 +1,5 @@
 def f(values):
-    return values[0]
+    if not values:
+        return None
+    return values[0]
"""

BODY = '''"""A module."""


def f(values):
    if not values:
        return None
    return values[0]
'''


class TestTheCountsComeFromTheDiffThatRan:
    def test_body_lines_are_counted_and_headers_are_not(self) -> None:
        counts = diff_counts(DIFF)

        assert counts.added_line_count == 3
        assert counts.removed_line_count == 1
        assert counts.hunk_count == 1
        assert counts.changed_file_count == 1

    def test_an_empty_diff_counts_nothing_rather_than_guessing(self) -> None:
        counts = diff_counts("")

        assert (counts.hunk_count, counts.added_line_count, counts.removed_line_count) == (0, 0, 0)


class TestTheGraphIsTheStatementGraph:
    def test_nesting_is_visible_in_the_depth(self) -> None:
        flat = statement_graph("a = 1\nb = 2\nc = 3\n")
        nested = statement_graph("def f():\n    if True:\n        for x in ():\n            pass\n")

        assert flat.path_length == 1
        assert nested.path_length == 4

    def test_it_is_not_a_second_copy_of_the_ast_node_count(self) -> None:
        """Two names for one number would give the encoder the same feature twice."""
        assert statement_graph(BODY).node_count != ast_node_count(BODY)

    def test_sequence_and_containment_both_produce_edges(self) -> None:
        one = statement_graph("a = 1\n")
        two = statement_graph("a = 1\nb = 2\n")

        assert one.edge_count == 0
        assert two.edge_count == 1


class TestTheFeatureInputIsPreOutcome:
    def test_every_numeric_name_the_encoder_expects_is_present(self) -> None:
        row = raw_numeric_row(
            feature_input(
                candidate_source=BODY,
                unified_diff=DIFF,
                task_requirement_embedding=(0.1, 0.2),
                candidate_delta_embedding=(0.3, 0.4),
            )
        )

        assert set(row) == set(NUMERIC_FEATURE_NAMES)

    def test_it_declares_the_verifiers_rather_than_their_verdict(self) -> None:
        features = feature_input(
            candidate_source=BODY,
            unified_diff=DIFF,
            task_requirement_embedding=(0.1, 0.2),
            candidate_delta_embedding=(0.3, 0.4),
        )

        assert features.declared_verifier_capabilities == DECLARED_VERIFIER_CAPABILITIES

    def test_the_requirement_text_is_the_task_and_never_a_candidate(self) -> None:
        text = requirement_text("  the issue  ", "  the expectation  ")

        assert text == "the issue\n\nthe expectation"
        assert BODY not in text

    def test_identical_inputs_encode_to_identical_bytes(self) -> None:
        bounds = _bounds()
        encoder = CorrectionEncoder(bounds)
        features = feature_input(
            candidate_source=BODY,
            unified_diff=DIFF,
            task_requirement_embedding=(0.1, 0.2),
            candidate_delta_embedding=(0.3, 0.4),
        )

        assert encoder.encode(features).content_hash() == encoder.encode(features).content_hash()


def _bounds() -> NumericBounds:
    return NumericBounds.from_training(
        [
            dict.fromkeys(NUMERIC_FEATURE_NAMES, 0.0),
            dict.fromkeys(NUMERIC_FEATURE_NAMES, 100.0),
        ]
    )


def _pending(index: int) -> PendingFeature:
    return PendingFeature(
        candidate_id=uuid5(NAMESPACE, f"candidate:{index}"),
        task_id=uuid5(NAMESPACE, "task"),
        repository_group="d2-group",
        features=feature_input(
            candidate_source=BODY,
            unified_diff=DIFF,
            task_requirement_embedding=(0.1, 0.2),
            candidate_delta_embedding=(0.3, 0.4 + index),
        ),
    )


def _sealed(count: int = 3) -> SealedFeatureRecordSet:
    return seal_feature_records(
        [_pending(index) for index in range(count)],
        partition="training",
        campaign_manifest_hash="a" * 64,
        bounds=_bounds(),
        embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
        embedding_revision="1110a243",
        embedding_dimension=384,
        sealed_at=SEALED_AT,
    )


class TestTheSealIsTheChronologyAuthority:
    def test_the_set_records_when_it_was_sealed(self) -> None:
        assert _sealed().sealed_at == SEALED_AT

    def test_it_carries_no_outcome(self) -> None:
        assert _sealed().outcomes_present is False

    def test_the_same_inputs_and_the_same_seal_time_reproduce_the_same_hash(self) -> None:
        """What makes a resume able to prove it is resuming the campaign it says it is."""
        assert _sealed().content_hash == _sealed().content_hash

    def test_a_different_seal_time_is_a_different_set(self) -> None:
        other = seal_feature_records(
            [_pending(index) for index in range(3)],
            partition="training",
            campaign_manifest_hash="a" * 64,
            bounds=_bounds(),
            embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
            embedding_revision="1110a243",
            embedding_dimension=384,
            sealed_at=datetime(2026, 8, 2, 13, 0, tzinfo=UTC),
        )

        assert other.content_hash != _sealed().content_hash

    def test_records_are_ordered_by_candidate_so_the_set_is_stable(self) -> None:
        sealed = _sealed()
        ordered = [str(record.candidate_id) for record in sealed.records]

        assert ordered == sorted(ordered)

    def test_a_record_can_be_found_by_the_candidate_it_describes(self) -> None:
        sealed = _sealed()
        wanted = sealed.records[1].candidate_id

        assert sealed.record_for(wanted).candidate_id == wanted

    def test_an_unknown_candidate_has_no_record_rather_than_an_empty_one(self) -> None:
        with pytest.raises(KeyError):
            _sealed().record_for(uuid5(NAMESPACE, "stranger"))

    def test_the_normalisation_bounds_travel_with_the_set(self) -> None:
        """A scaled value whose bounds are lost cannot be recomputed by anyone."""
        sealed = _sealed()

        assert [name for name, _ in sealed.numeric_lower] == list(NUMERIC_FEATURE_NAMES)
        assert [name for name, _ in sealed.numeric_upper] == list(NUMERIC_FEATURE_NAMES)

    def test_no_record_carries_a_verifier_result(self) -> None:
        for record in _sealed().records:
            names = {name for name, _ in record.values}
            assert "verifier_status" not in names
            assert "hidden_verification_passed" not in names
            assert "candidate_recipe" not in names
