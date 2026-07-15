"""Bounded in-process projection of authoritative relational claim edges."""

from collections import defaultdict, deque
from importlib import import_module
from typing import Any

from cognitive_os.domain.semantic_memory import (
    ClaimRelation,
    ClaimRelationType,
    ClaimRevisionReference,
)


def bounded_neighbours(
    relations: tuple[ClaimRelation, ...],
    start: ClaimRevisionReference,
    *,
    maximum_depth: int,
    maximum_nodes: int,
    maximum_edges: int,
) -> tuple[ClaimRevisionReference, ...]:
    if maximum_depth < 0 or maximum_nodes < 1 or maximum_edges < 0:
        raise ValueError("graph limits are invalid")
    if len(relations) > maximum_edges:
        raise ValueError("graph edge limit exceeded")
    adjacency: dict[ClaimRevisionReference, list[ClaimRevisionReference]] = defaultdict(list)
    for relation in relations:
        adjacency[relation.source].append(relation.target)
        adjacency[relation.target].append(relation.source)
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        node, depth = queue.popleft()
        if depth == maximum_depth:
            continue
        for neighbour in sorted(
            adjacency[node], key=lambda item: (str(item.claim_id), item.revision)
        ):
            if neighbour in seen:
                continue
            if len(seen) >= maximum_nodes:
                raise ValueError("graph node limit exceeded")
            seen.add(neighbour)
            queue.append((neighbour, depth + 1))
    return tuple(sorted(seen, key=lambda item: (str(item.claim_id), item.revision)))


def has_restricted_cycle(relations: tuple[ClaimRelation, ...]) -> bool:
    restricted = {
        ClaimRelationType.SUPERSEDES,
        ClaimRelationType.DERIVED_FROM,
        ClaimRelationType.SPECIALIZES,
        ClaimRelationType.GENERALIZES,
    }
    adjacency: dict[ClaimRevisionReference, list[ClaimRevisionReference]] = defaultdict(list)
    for relation in relations:
        if relation.relation_type in restricted:
            adjacency[relation.source].append(relation.target)
    visiting: set[ClaimRevisionReference] = set()
    visited: set[ClaimRevisionReference] = set()

    def visit(node: ClaimRevisionReference) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(target) for target in adjacency[node]):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in tuple(adjacency))


def networkx_snapshot(
    relations: tuple[ClaimRelation, ...],
    *,
    maximum_nodes: int,
    maximum_edges: int,
) -> dict[str, Any]:
    """Return an optional, deterministic analytical projection of exact revision edges."""
    if len(relations) > maximum_edges:
        raise ValueError("graph edge limit exceeded")
    nodes = {reference for item in relations for reference in (item.source, item.target)}
    if len(nodes) > maximum_nodes:
        raise ValueError("graph node limit exceeded")
    try:
        networkx = import_module("networkx")
    except ImportError as error:
        raise RuntimeError("install the semantic-graph extra for NetworkX analysis") from error
    graph = networkx.MultiDiGraph()
    for node in sorted(nodes, key=lambda item: (str(item.claim_id), item.revision)):
        graph.add_node(f"{node.claim_id}:{node.revision}")
    duplicates: dict[tuple[str, str, str], int] = defaultdict(int)
    for relation in sorted(relations, key=lambda item: str(item.relation_id)):
        source = f"{relation.source.claim_id}:{relation.source.revision}"
        target = f"{relation.target.claim_id}:{relation.target.revision}"
        graph.add_edge(
            source,
            target,
            key=str(relation.relation_id),
            type=relation.relation_type.value,
        )
        duplicates[(source, target, relation.relation_type.value)] += 1
    components = sorted(
        (sorted(component) for component in networkx.weakly_connected_components(graph)),
        key=lambda component: component[0],
    )
    cycles = sorted(
        (tuple(cycle) for cycle in networkx.simple_cycles(networkx.DiGraph(graph))),
        key=lambda cycle: tuple(cycle),
    )
    return {
        "nodes": sorted(graph.nodes),
        "edges": sorted(
            (source, target, key, data["type"])
            for source, target, key, data in graph.edges(keys=True, data=True)
        ),
        "connected_components": components,
        "cycles": cycles,
        "duplicate_relations": sorted(
            (*key, count) for key, count in duplicates.items() if count > 1
        ),
    }
