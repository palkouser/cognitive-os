"""Project a compiled trajectory into an action-decision graph, and diff two of them.

The adapter reads what the Experience Compiler already assessed. Every node comes from a
`StepAssessment`, so a node cannot describe a step the compiler did not see, and its
source hash is the assessment's own authoritative evidence rather than something this
module invents.

The edit path is a deterministic labelled set difference, not a search. NetworkX graph
edit distance is an NP-hard ranking signal used later by the retrieval arm; the *stored*
edit script has to be reproducible, and a set difference over canonically ordered
logical ids is. Applying the script to the failed graph must reconstruct the successful
graph exactly, and `apply_edit_path` is what proves it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from itertools import pairwise
from typing import Any

from cognitive_os.coding.reality_leakage import judgement_leaks
from cognitive_os.domain.experience import ExecutionSegmentType, ExperienceStepStatus
from cognitive_os.domain.experience_graph import (
    SEARCH_TERMS_CHARACTER_BOUND,
    ActionDecisionGraph,
    ExperienceGraphEdge,
    ExperienceGraphEdgeKind,
    ExperienceGraphNode,
    ExperienceGraphNodeKind,
    GraphEditOperation,
    GraphEditOperationKind,
    GraphEditPath,
    GraphResourceLimits,
)
from cognitive_os.experience.compiler import ExperienceCompilationResult
from cognitive_os.learning.correction_source import canonical_source_bytes

#: Segment type to node kind. Anything unmapped is an observation, which is the honest
#: default: the compiler saw a step and this projection does not claim to know more.
_SEGMENT_KIND = {
    ExecutionSegmentType.PLANNING: ExperienceGraphNodeKind.REASONING,
    ExecutionSegmentType.CONTEXT_BUILD: ExperienceGraphNodeKind.OBSERVATION,
    ExecutionSegmentType.PROVIDER_EXECUTION: ExperienceGraphNodeKind.REASONING,
    ExecutionSegmentType.TOOL_EXECUTION: ExperienceGraphNodeKind.TOOL_ACTION,
    ExecutionSegmentType.SKILL_EXECUTION: ExperienceGraphNodeKind.TOOL_ACTION,
    ExecutionSegmentType.STRATEGY_PHASE: ExperienceGraphNodeKind.REASONING,
    ExecutionSegmentType.VERIFICATION: ExperienceGraphNodeKind.VERIFIER,
    ExecutionSegmentType.REPAIR: ExperienceGraphNodeKind.CORRECTION,
    ExecutionSegmentType.FALLBACK: ExperienceGraphNodeKind.CORRECTION,
    ExecutionSegmentType.ACCEPTANCE: ExperienceGraphNodeKind.ACCEPTED_OUTCOME,
}


#: Identifier-bearing fields of the normalised AST dump. Everything else in that dump is
#: either structure the arms already see or a literal the surface deliberately excludes, so
#: the capture is restricted to an identifier shape and string constants can never match.
_CANONICAL_TERM = re.compile(r"(?:id|attr|arg|asname|module|name)='([A-Za-z_][A-Za-z0-9_]*)'")

#: What the released alpha-normaliser rewrites local bindings to. A placeholder is the same
#: token in every task by construction, so it is noise in a retrieval document, not a term.
_PLACEHOLDER_PREFIX = "__cogos_"

#: AST node constructors in the canonical dump: the word immediately before an opening
#: parenthesis. Field names never match — `annotate_fields=True` prints them before `=`.
_STRUCTURE_NODE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\(")

#: Bookkeeping nodes present in essentially every canonical dump. As fallback terms they
#: would say "this is Python", which every document in the pool already is. Operators,
#: control flow, calls and attributes stay in, because those are what distinguish one
#: arithmetic repair from another.
_STRUCTURE_BOOKKEEPING = frozenset(
    {
        "Module",
        "Expr",
        "Load",
        "Store",
        "Del",
        "Name",
        "Constant",
        "arguments",
        "arg",
        "alias",
        "keyword",
    }
)


class SearchSurfaceLeak(ValueError):
    """A projected term names the relevance label the graph will be scored against."""


def search_terms_from_source(
    source: str,
    *,
    judgement_labels: Iterable[str] = (),
    structure_fallback: bool = False,
) -> tuple[str, ...]:
    """The canonical terms of one source, bounded, guarded and deterministic. §S21D4-040.

    The terms are read off `canonical_source_bytes`, the released v2 alpha-normaliser, rather
    than off the raw text: local bindings are already placeholders there while imports,
    attributes, builtins and magic names survive. That is what keeps this from becoming
    lookup — two tasks in a family share preserved names and structure, not spelling.

    `structure_fallback` is the S21D4 residual made operative: ten of D4's sixty holdout
    candidates were repairs in pure arithmetic over their own parameters, the normaliser
    left nothing of them, and an empty document cannot be found by any arm. With the flag
    set, a source whose identifier terms come up empty falls back to its lowercased AST
    node-type names from the same canonical dump — operators, control flow, calls — minus
    the bookkeeping nodes every dump carries. Deterministic, still literal-free, and off by
    default so every released call site keeps producing its exact recorded bytes.

    Fails closed rather than filtering when a term spells a relevance label. A benchmark that
    can read its own judgement out of the document is not a benchmark, and dropping the
    offending term would leave the rest of a leaking projection in place.
    """
    dump = canonical_source_bytes(source).decode()
    terms = sorted(
        {term for term in _CANONICAL_TERM.findall(dump) if not term.startswith(_PLACEHOLDER_PREFIX)}
    )
    if not terms and structure_fallback:
        terms = sorted(
            {
                match.lower()
                for match in _STRUCTURE_NODE.findall(dump)
                if match not in _STRUCTURE_BOOKKEEPING
            }
        )
    bounded: list[str] = []
    for term in terms:
        if len(" ".join([*bounded, term])) > SEARCH_TERMS_CHARACTER_BOUND:
            break
        bounded.append(term)
    labels = tuple(judgement_labels)
    if labels:
        leaks = judgement_leaks({"search_terms": " ".join(bounded)}, {"search_terms": labels})
        if leaks:
            raise SearchSurfaceLeak(f"projected terms name their own judgement: {leaks}")
    return tuple(bounded)


def _segment_for(sequence: int, result: ExperienceCompilationResult) -> ExecutionSegmentType | None:
    for segment in result.segments:
        if segment.first_sequence <= sequence <= segment.last_sequence:
            return segment.segment_type
    return None


def project(
    result: ExperienceCompilationResult,
    *,
    graph_id: str,
    domain: str,
    group: str,
    task_signature: str,
    accepted: bool,
    limits: GraphResourceLimits | None = None,
) -> ActionDecisionGraph:
    """One compiled trajectory as a canonical action-decision graph.

    Logical ids are zero-padded sequence numbers, so canonical sort order and execution
    order agree and a graph does not need a separate ordering field to stay comparable.
    """
    limits = limits or GraphResourceLimits()
    nodes: list[ExperienceGraphNode] = []
    for assessment in sorted(result.assessments, key=lambda a: a.sequence):
        segment = _segment_for(assessment.sequence, result)
        kind = (
            _SEGMENT_KIND.get(segment, ExperienceGraphNodeKind.OBSERVATION)
            if segment
            else (ExperienceGraphNodeKind.OBSERVATION)
        )
        if assessment.status is ExperienceStepStatus.FAILED:
            kind = ExperienceGraphNodeKind.TOOL_RESULT
        nodes.append(
            ExperienceGraphNode(
                logical_id=f"s{assessment.sequence:04d}",
                kind=kind,
                attributes=tuple(
                    sorted(
                        (
                            ("correctness", assessment.correctness.value),
                            ("necessity", assessment.necessity.value),
                            ("segment", segment.value if segment else "unmapped"),
                            ("status", assessment.status.value),
                        )
                    )
                ),
                source_hash=assessment.authoritative_evidence[0],
            )
        )
    edges = tuple(
        ExperienceGraphEdge(
            source_id=left.logical_id, target_id=right.logical_id, kind=ExperienceGraphEdgeKind.NEXT
        )
        for left, right in pairwise(nodes)
    )
    return ActionDecisionGraph(
        graph_id=graph_id,
        domain=domain,
        group=group,
        task_signature=task_signature,
        accepted=accepted,
        nodes=tuple(nodes),
        edges=tuple(sorted(edges, key=lambda e: e.key)),
        limits=limits,
        source_manifest_hash=result.manifest.content_hash,
    )


#: Intent prefix to node kind, for a C3 correction trajectory. The intents are fixed
#: strings the C3 compiler wrote, so matching on them reads recorded evidence rather than
#: guessing at it.
_CORRECTION_INTENT_KIND = (
    ("Ordered correction path", ExperienceGraphNodeKind.OBSERVATION),
    ("Hidden verification", ExperienceGraphNodeKind.VERIFIER),
    ("Applied", ExperienceGraphNodeKind.CORRECTION),
    ("Terminal outcome", ExperienceGraphNodeKind.ACCEPTED_OUTCOME),
)


def _correction_kind(intent: str) -> ExperienceGraphNodeKind:
    for prefix, kind in _CORRECTION_INTENT_KIND:
        if intent.startswith(prefix):
            return kind
    return ExperienceGraphNodeKind.OBSERVATION


def _nodes_from(
    assessments: Sequence[Mapping[str, Any]], *, segment: str
) -> tuple[ExperienceGraphNode, ...]:
    """Nodes from persisted step assessments, in recorded sequence order.

    Reading persisted assessments rather than re-running keeps a projection tied to the
    trajectory that was actually stored. Re-executing a case would produce a different
    trajectory and silently detach the graph from the pair set it belongs to.
    """
    nodes = []
    for assessment in sorted(assessments, key=lambda item: int(item["sequence"])):
        evidence = tuple(assessment.get("authoritative_evidence") or ())
        if not evidence:
            raise ValueError(f"assessment {assessment['step_id']} has no authoritative evidence")
        nodes.append(
            ExperienceGraphNode(
                logical_id=f"s{int(assessment['sequence']):04d}",
                kind=_correction_kind(str(assessment["intent"])),
                attributes=tuple(
                    sorted(
                        (
                            ("correctness", str(assessment["correctness"])),
                            ("necessity", str(assessment["necessity"])),
                            ("segment", segment),
                            ("status", str(assessment["status"])),
                        )
                    )
                ),
                source_hash=evidence[0],
            )
        )
    return tuple(nodes)


def project_persisted_side(
    assessments: Sequence[Mapping[str, Any]],
    *,
    graph_id: str,
    domain: str,
    group: str,
    task_signature: str,
    accepted: bool,
    source_manifest_hash: str,
    limits: GraphResourceLimits | None = None,
) -> ActionDecisionGraph:
    """One side of a fresh pair, projected from its persisted assessments."""
    return _graph(
        _nodes_from(assessments, segment="domain_trajectory"),
        graph_id=graph_id,
        domain=domain,
        group=group,
        task_signature=task_signature,
        accepted=accepted,
        limits=limits or GraphResourceLimits(),
        source_manifest_hash=source_manifest_hash,
    )


def project_correction(
    assessments: Sequence[Mapping[str, Any]],
    *,
    domain: str,
    group: str,
    task_signature: str,
    source_manifest_hash: str,
    limits: GraphResourceLimits | None = None,
    failed_source: str | None = None,
    repaired_source: str | None = None,
    judgement_labels: Iterable[str] = (),
    structure_fallback: bool = False,
) -> tuple[ActionDecisionGraph, ActionDecisionGraph]:
    """Split one historical C3 correction trajectory into a failed and a successful graph.

    A correction trajectory records both sides in one ordered sequence: the failing
    attempts, then the patch that worked, then the terminal acceptance. So the failed
    graph is the prefix through the last step the verifier rejected, and the successful
    graph is the whole trajectory. The split is read from the recorded `correctness`
    field, not from step positions, so a trajectory with a different shape still splits
    where the evidence says it does.

    These graphs are never recompiled. The legacy manifests carry a wall-clock
    `created_at`, so their pairs stay marked `legacy_recompilation_unavailable` and are
    verified by resolving sources instead.

    S21D4-040 adds the two optional sources behind the trajectory. Given them, the failed
    graph carries the failing state's canonical terms and the successful graph the repaired
    state's — which is the retrieval question the widened surface exists to answer: find a
    repair for a bug shaped like mine. Omitted, both graphs keep the empty default and every
    hash this projection produces is the one D3 produced.
    """
    limits = limits or GraphResourceLimits()
    nodes = _nodes_from(assessments, segment="correction_trajectory")
    last_rejected = max(
        (
            index
            for index, node in enumerate(nodes)
            if ("correctness", "incorrect") in node.attributes
        ),
        default=-1,
    )
    if last_rejected < 0:
        raise ValueError("a correction trajectory must record at least one rejected step")

    failed_nodes = tuple(nodes[: last_rejected + 1])
    labels = tuple(judgement_labels)
    return (
        _graph(
            failed_nodes,
            graph_id=f"{task_signature}:failed",
            domain=domain,
            group=group,
            task_signature=task_signature,
            accepted=False,
            limits=limits,
            source_manifest_hash=source_manifest_hash,
            search_terms=(
                search_terms_from_source(
                    failed_source,
                    judgement_labels=labels,
                    structure_fallback=structure_fallback,
                )
                if failed_source is not None
                else ()
            ),
        ),
        _graph(
            tuple(nodes),
            graph_id=f"{task_signature}:successful",
            domain=domain,
            group=group,
            task_signature=task_signature,
            accepted=True,
            limits=limits,
            source_manifest_hash=source_manifest_hash,
            search_terms=(
                search_terms_from_source(
                    repaired_source,
                    judgement_labels=labels,
                    structure_fallback=structure_fallback,
                )
                if repaired_source is not None
                else ()
            ),
        ),
    )


def _graph(
    nodes: tuple[ExperienceGraphNode, ...],
    *,
    graph_id: str,
    domain: str,
    group: str,
    task_signature: str,
    accepted: bool,
    limits: GraphResourceLimits,
    source_manifest_hash: str,
    search_terms: tuple[str, ...] = (),
) -> ActionDecisionGraph:
    edges = tuple(
        ExperienceGraphEdge(
            source_id=left.logical_id, target_id=right.logical_id, kind=ExperienceGraphEdgeKind.NEXT
        )
        for left, right in pairwise(nodes)
    )
    return ActionDecisionGraph(
        graph_id=graph_id,
        domain=domain,
        group=group,
        task_signature=task_signature,
        accepted=accepted,
        nodes=nodes,
        edges=tuple(sorted(edges, key=lambda e: e.key)),
        limits=limits,
        source_manifest_hash=source_manifest_hash,
        search_terms=search_terms,
    )


def derive_edit_path(
    failed: ActionDecisionGraph, successful: ActionDecisionGraph, *, path_id: str
) -> GraphEditPath:
    """The ordered labelled set difference between two graphs."""
    left_nodes = {node.logical_id: node for node in failed.nodes}
    right_nodes = {node.logical_id: node for node in successful.nodes}
    left_edges = {edge.key: edge for edge in failed.edges}
    right_edges = {edge.key: edge for edge in successful.edges}

    operations: list[GraphEditOperation] = []
    for logical_id in sorted(set(left_nodes) - set(right_nodes)):
        operations.append(
            GraphEditOperation(kind=GraphEditOperationKind.DELETE_NODE, target=logical_id)
        )
    for logical_id in sorted(set(right_nodes) - set(left_nodes)):
        operations.append(
            GraphEditOperation(
                kind=GraphEditOperationKind.INSERT_NODE,
                target=logical_id,
                detail=_encode_node(right_nodes[logical_id]),
            )
        )
    for logical_id in sorted(set(left_nodes) & set(right_nodes)):
        if left_nodes[logical_id].label != right_nodes[logical_id].label:
            operations.append(
                GraphEditOperation(
                    kind=GraphEditOperationKind.RELABEL_NODE,
                    target=logical_id,
                    detail=_encode_node(right_nodes[logical_id]),
                )
            )
    for key in sorted(set(left_edges) - set(right_edges)):
        operations.append(
            GraphEditOperation(kind=GraphEditOperationKind.DELETE_EDGE, target="|".join(key))
        )
    for key in sorted(set(right_edges) - set(left_edges)):
        operations.append(
            GraphEditOperation(kind=GraphEditOperationKind.INSERT_EDGE, target="|".join(key))
        )
    return GraphEditPath(
        path_id=path_id,
        from_graph_hash=failed.structural_hash,
        to_graph_hash=successful.structural_hash,
        operations=tuple(sorted(operations, key=lambda op: op.order_key)),
    )


def _encode_node(node: ExperienceGraphNode) -> str:
    attributes = ",".join(f"{key}={value}" for key, value in node.attributes)
    return f"{node.kind.value}|{node.source_hash}|{attributes}"


def _decode_node(logical_id: str, detail: str) -> ExperienceGraphNode:
    kind, source_hash, attributes = detail.split("|", 2)
    pairs = tuple(
        (part.split("=", 1)[0], part.split("=", 1)[1]) for part in attributes.split(",") if part
    )
    return ExperienceGraphNode(
        logical_id=logical_id,
        kind=ExperienceGraphNodeKind(kind),
        attributes=tuple(sorted(pairs)),
        source_hash=source_hash,
    )


def apply_edit_path(failed: ActionDecisionGraph, path: GraphEditPath) -> ActionDecisionGraph:
    """Apply the script and return the reconstructed graph.

    This is the round-trip proof. If the result's canonical hash is not the path's
    declared destination, either the projection or the diff is wrong, and the pair has
    to be rejected rather than the hash recorded as whatever came out.
    """
    if path.from_graph_hash != failed.structural_hash:
        raise ValueError("the edit path does not start at this graph")
    nodes = {node.logical_id: node for node in failed.nodes}
    edges = {edge.key: edge for edge in failed.edges}
    for operation in path.operations:
        if operation.kind is GraphEditOperationKind.DELETE_NODE:
            if operation.target not in nodes:
                raise ValueError(f"delete_node names an absent id: {operation.target}")
            del nodes[operation.target]
        elif operation.kind in {
            GraphEditOperationKind.INSERT_NODE,
            GraphEditOperationKind.RELABEL_NODE,
        }:
            nodes[operation.target] = _decode_node(operation.target, operation.detail)
        elif operation.kind is GraphEditOperationKind.DELETE_EDGE:
            key = tuple(operation.target.split("|"))
            if key not in edges:
                raise ValueError(f"delete_edge names an absent edge: {operation.target}")
            del edges[key]
        elif operation.kind is GraphEditOperationKind.INSERT_EDGE:
            source, target, kind = operation.target.split("|")
            edge = ExperienceGraphEdge(
                source_id=source, target_id=target, kind=ExperienceGraphEdgeKind(kind)
            )
            edges[edge.key] = edge
        else:
            raise ValueError(f"unsupported edit operation: {operation.kind}")
    return ActionDecisionGraph(
        graph_id=failed.graph_id,
        domain=failed.domain,
        group=failed.group,
        task_signature=failed.task_signature,
        accepted=True,
        nodes=tuple(sorted(nodes.values(), key=lambda n: n.logical_id)),
        edges=tuple(sorted(edges.values(), key=lambda e: e.key)),
        limits=failed.limits,
        source_manifest_hash=failed.source_manifest_hash,
    )


def round_trips(
    failed: ActionDecisionGraph, successful: ActionDecisionGraph, path: GraphEditPath
) -> bool:
    """Whether applying the path reproduces the successful graph's canonical structure.

    Structural, not byte-identical, and that is the correct comparison rather than a
    weaker one. `content_hash` includes every node's `source_hash`, the evidence the
    step was projected from, and the two sides of a pair are two different runs whose
    evidence bytes differ at every step. An edit path describes a repair, so what it
    must reproduce is the labelled structure. Provenance is checked separately by
    resolving each source hash.
    """
    rebuilt = apply_edit_path(failed, path)
    return rebuilt.structural_hash == successful.structural_hash
