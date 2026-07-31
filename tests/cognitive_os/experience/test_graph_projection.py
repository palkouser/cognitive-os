"""Fail-closed behaviour of the action-decision graph contracts and the edit path.

S21D1-043 asks for adversarial coverage: cycles, duplicate ids, unknown kinds, oversized
graphs, excessive depth, secret patterns and unresolved edges must all be refused rather
than stored and discovered later. Each test names one refusal.
"""

from __future__ import annotations

import pytest

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
from cognitive_os.experience.graph_projection import derive_edit_path, round_trips

HASH = "a" * 64


def node(logical_id: str, *, kind: str = "observation", status: str = "completed"):
    return ExperienceGraphNode(
        logical_id=logical_id,
        kind=ExperienceGraphNodeKind(kind),
        attributes=(("status", status),),
        source_hash=HASH,
    )


def edge(source: str, target: str) -> ExperienceGraphEdge:
    return ExperienceGraphEdge(
        source_id=source, target_id=target, kind=ExperienceGraphEdgeKind.NEXT
    )


def graph(nodes, edges=(), *, accepted: bool = False, limits=None, signature="t:1", group="g1"):
    return ActionDecisionGraph(
        graph_id="g",
        domain="logic",
        group=group,
        task_signature=signature,
        accepted=accepted,
        nodes=tuple(nodes),
        edges=tuple(edges),
        limits=limits or GraphResourceLimits(),
        source_manifest_hash=HASH,
    )


def test_a_valid_chain_is_accepted_and_hashes_structurally() -> None:
    built = graph([node("s0001"), node("s0002")], [edge("s0001", "s0002")])
    assert len(built.structural_hash) == 64
    assert built.structural_hash != built.content_hash


def test_a_cycle_is_refused() -> None:
    with pytest.raises(ValueError, match="acyclic"):
        graph([node("s0001"), node("s0002")], [edge("s0001", "s0002"), edge("s0002", "s0001")])


def test_a_duplicate_logical_id_is_refused() -> None:
    with pytest.raises(ValueError, match="duplicate logical node identity"):
        graph([node("s0001"), node("s0001")])


def test_an_edge_to_an_unknown_node_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown node"):
        graph([node("s0001")], [edge("s0001", "s0999")])


def test_a_self_loop_is_refused() -> None:
    with pytest.raises(ValueError, match="points at itself"):
        edge("s0001", "s0001")


def test_an_oversized_graph_is_refused() -> None:
    limits = GraphResourceLimits(nodes_per_graph=2)
    with pytest.raises(ValueError, match="exceeds the declared bound"):
        graph([node(f"s{index:04d}") for index in range(3)], limits=limits)


def test_excessive_depth_is_refused() -> None:
    limits = GraphResourceLimits(path_depth=1)
    nodes = [node(f"s{index:04d}") for index in range(1, 4)]
    edges = [edge("s0001", "s0002"), edge("s0002", "s0003")]
    with pytest.raises(ValueError, match="path depth"):
        graph(nodes, edges, limits=limits)


@pytest.mark.parametrize(
    "value", ["/home/palkouser/secret.txt", "authorization: Bearer abc", "my-password-here"]
)
def test_a_secret_or_host_path_in_an_attribute_is_refused(value: str) -> None:
    with pytest.raises(ValueError, match="carries"):
        ExperienceGraphNode(
            logical_id="s0001",
            kind=ExperienceGraphNodeKind.OBSERVATION,
            attributes=(("detail", value),),
            source_hash=HASH,
        )


def test_an_unbounded_attribute_body_is_refused() -> None:
    with pytest.raises(ValueError, match="unbounded body"):
        ExperienceGraphNode(
            logical_id="s0001",
            kind=ExperienceGraphNodeKind.OBSERVATION,
            attributes=(("detail", "x" * 1025),),
            source_hash=HASH,
        )


def test_an_unsorted_node_order_is_refused() -> None:
    with pytest.raises(ValueError, match="canonical logical-id order"):
        graph([node("s0002"), node("s0001")])


def test_edit_path_round_trips_and_is_canonically_ordered() -> None:
    failed = graph([node("s0001"), node("s0002")], [edge("s0001", "s0002")])
    successful = graph(
        [node("s0001"), node("s0002"), node("s0003", kind="accepted_outcome")],
        [edge("s0001", "s0002"), edge("s0002", "s0003")],
        accepted=True,
    )
    path = derive_edit_path(failed, successful, path_id="p")
    assert round_trips(failed, successful, path)
    keys = [operation.order_key for operation in path.operations]
    assert keys == sorted(keys)


def test_a_pair_whose_sides_disagree_on_the_task_is_refused() -> None:
    failed = graph([node("s0001")], signature="t:1")
    successful = graph([node("s0001")], accepted=True, signature="t:2")
    path = derive_edit_path(failed, successful, path_id="p")
    with pytest.raises(ValueError, match="not causal"):
        FailedSuccessGraphPair(
            pair_id="p",
            domain="logic",
            group="g1",
            task_signature="t:1",
            failed=failed,
            successful=successful,
            edit_path=path,
            legacy_recompilation_unavailable=False,
            verification_mode="byte_identical_recompilation",
            compiled_at=FIXTURE_TIME,
        )


def test_a_pair_whose_failed_side_was_accepted_is_refused() -> None:
    failed = graph([node("s0001")], accepted=True)
    successful = graph([node("s0001"), node("s0002")], accepted=True)
    path = derive_edit_path(failed, successful, path_id="p")
    with pytest.raises(ValueError, match="failed side"):
        FailedSuccessGraphPair(
            pair_id="p",
            domain="logic",
            group="g1",
            task_signature="t:1",
            failed=failed,
            successful=successful,
            edit_path=path,
            legacy_recompilation_unavailable=False,
            verification_mode="byte_identical_recompilation",
            compiled_at=FIXTURE_TIME,
        )


def test_an_edit_path_from_a_different_graph_is_refused() -> None:
    failed = graph([node("s0001")])
    other = graph([node("s0001"), node("s0002")])
    successful = graph([node("s0001"), node("s0002"), node("s0003")], accepted=True)
    path = derive_edit_path(other, successful, path_id="p")
    with pytest.raises(ValueError, match="does not start at this graph"):
        round_trips(failed, successful, path)
