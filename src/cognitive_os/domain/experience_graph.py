"""Contracts for the Experience Memory Graph: action-decision graphs and edit paths.

A trajectory becomes a directed acyclic graph of what was observed, reasoned, done,
verified and corrected. A failed graph and the successful graph that replaced it form a
pair, and the ordered edit path between them is the advisory repair suggestion the
Context Builder may later surface.

Three refusals are enforced here rather than in review:

* a graph that is not acyclic is refused, because an action sequence that loops is not a
  trajectory and a graph-edit distance over it has no meaning;
* a node attribute carrying a host path, a credential marker or an unbounded body is
  refused, because everything in a graph is a retrieval surface;
* an edit operation naming a logical id that neither graph contains is refused, so an
  edit path can never be applied to produce something nobody recorded.

Nothing here executes an edit. A `GraphEditPath` is a suggestion with provenance, and
the D1 Context Builder integration surfaces it as advisory, never as an executable patch.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .common import NonEmptyStr, Sha256Hex, UtcDatetime
from .experience import HashedExperienceContract


class ExperienceGraphNodeKind(StrEnum):
    OBSERVATION = "observation"
    REASONING = "reasoning"
    TOOL_ACTION = "tool_action"
    TOOL_RESULT = "tool_result"
    VERIFIER = "verifier"
    CORRECTION = "correction"
    ACCEPTED_OUTCOME = "accepted_outcome"


class ExperienceGraphEdgeKind(StrEnum):
    NEXT = "next"
    BRANCHES_TO = "branches_to"
    CAUSED_BY = "caused_by"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CORRECTED_BY = "corrected_by"
    RECOVERS_TO = "recovers_to"


class GraphEditOperationKind(StrEnum):
    INSERT_NODE = "insert_node"
    DELETE_NODE = "delete_node"
    RELABEL_NODE = "relabel_node"
    INSERT_EDGE = "insert_edge"
    DELETE_EDGE = "delete_edge"
    RELABEL_EDGE = "relabel_edge"


#: Markers that must never reach a graph attribute. Everything in a graph is retrievable.
FORBIDDEN_ATTRIBUTE_MARKERS = (
    "/home/",
    "/root/",
    "/var/tmp/",
    "authorization",
    "api_key",
    "password",
    "secret",
)


class GraphResourceLimits(HashedExperienceContract):
    """The pre-registered bounds. A change must be committed before the next benchmark."""

    nodes_per_graph: int = Field(default=64, ge=1, le=4096)
    edges_per_graph: int = Field(default=128, ge=1, le=8192)
    path_depth: int = Field(default=32, ge=1, le=512)
    vector_shortlist: int = Field(default=10, ge=1, le=100)
    returned_results: int = Field(default=10, ge=1, le=100)
    per_pair_ged_timeout_ms: int = Field(default=250, ge=1, le=60_000)
    query_budget_seconds: int = Field(default=2, ge=1, le=600)
    cross_task_similarity_neighbors: int = Field(default=3, ge=0, le=50)


class ExperienceGraphNode(HashedExperienceContract):
    logical_id: NonEmptyStr
    kind: ExperienceGraphNodeKind
    #: Sorted key/value pairs, so two equivalent nodes hash identically.
    attributes: tuple[tuple[NonEmptyStr, str], ...] = ()
    source_hash: Sha256Hex

    @model_validator(mode="after")
    def attributes_are_canonical_and_safe(self) -> ExperienceGraphNode:
        keys = [key for key, _ in self.attributes]
        if keys != sorted(keys):
            raise ValueError(f"node {self.logical_id} attributes must be sorted by key")
        if len(keys) != len(set(keys)):
            raise ValueError(f"node {self.logical_id} repeats an attribute key")
        for key, value in self.attributes:
            if len(value) > 1024:
                raise ValueError(f"node {self.logical_id} attribute {key} is an unbounded body")
            lowered = value.lower()
            for marker in FORBIDDEN_ATTRIBUTE_MARKERS:
                if marker in lowered:
                    raise ValueError(f"node {self.logical_id} attribute {key} carries {marker!r}")
        return self

    @property
    def label(self) -> tuple[str, tuple[tuple[str, str], ...]]:
        """What labelled graph-edit distance compares. Source hashes are provenance."""
        return self.kind.value, self.attributes


class ExperienceGraphEdge(HashedExperienceContract):
    source_id: NonEmptyStr
    target_id: NonEmptyStr
    kind: ExperienceGraphEdgeKind

    @model_validator(mode="after")
    def no_self_loop(self) -> ExperienceGraphEdge:
        if self.source_id == self.target_id:
            raise ValueError(f"edge {self.source_id} points at itself")
        return self

    @property
    def key(self) -> tuple[str, str, str]:
        return self.source_id, self.target_id, self.kind.value


class ActionDecisionGraph(HashedExperienceContract):
    """One trajectory as a bounded, acyclic, canonically ordered graph."""

    graph_id: NonEmptyStr
    domain: NonEmptyStr
    group: NonEmptyStr
    task_signature: NonEmptyStr
    accepted: bool
    nodes: tuple[ExperienceGraphNode, ...] = Field(min_length=1)
    edges: tuple[ExperienceGraphEdge, ...] = ()
    limits: GraphResourceLimits = GraphResourceLimits()
    source_manifest_hash: Sha256Hex

    @model_validator(mode="after")
    def structure_is_canonical_bounded_and_acyclic(self) -> ActionDecisionGraph:
        ids = [node.logical_id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate logical node identity")
        if ids != sorted(ids):
            raise ValueError("nodes must be in canonical logical-id order")
        if len(self.nodes) > self.limits.nodes_per_graph:
            raise ValueError(f"{len(self.nodes)} nodes exceeds the declared bound")
        if len(self.edges) > self.limits.edges_per_graph:
            raise ValueError(f"{len(self.edges)} edges exceeds the declared bound")
        known = set(ids)
        for edge in self.edges:
            if edge.source_id not in known or edge.target_id not in known:
                raise ValueError(f"edge {edge.key} references an unknown node")
        keys = [edge.key for edge in self.edges]
        if keys != sorted(keys):
            raise ValueError("edges must be in canonical order")
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate edge")
        self._refuse_cycles_and_depth()
        return self

    def _refuse_cycles_and_depth(self) -> None:
        """A DAG check and a longest-path bound, using the already-present networkx."""
        import networkx as nx  # type: ignore[import-untyped]

        graph = nx.DiGraph()
        graph.add_nodes_from(node.logical_id for node in self.nodes)
        graph.add_edges_from((edge.source_id, edge.target_id) for edge in self.edges)
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("an action-decision graph must be acyclic")
        if graph.number_of_edges() and nx.dag_longest_path_length(graph) > self.limits.path_depth:
            raise ValueError("path depth exceeds the declared bound")

    def node(self, logical_id: str) -> ExperienceGraphNode | None:
        return next((n for n in self.nodes if n.logical_id == logical_id), None)

    @property
    def structural_hash(self) -> str:
        """Canonical hash of labelled structure, with provenance deliberately excluded.

        `content_hash` covers everything including each node's `source_hash`, which is
        the evidence the step was projected from. Two runs of the same case produce
        different evidence bytes for the same logical step, so a *repair* edit path can
        never reproduce the successful graph's `content_hash` — and should not try. What
        an edit path claims to transform is the labelled structure, so that is what its
        canonical-hash verification compares. Provenance is verified separately, by
        resolving every source hash.
        """
        from hashlib import sha256

        payload = "\n".join(
            [f"{self.domain}\t{self.task_signature}"]
            + [f"{n.logical_id}\t{n.kind.value}\t{n.attributes}" for n in self.nodes]
            + ["\t".join(e.key) for e in self.edges]
        )
        return sha256(payload.encode()).hexdigest()

    def search_text(self) -> str:
        """The projection a lexical or vector arm ranks. Provenance hashes are excluded."""
        parts = [self.domain, self.task_signature]
        for node in self.nodes:
            rendered = " ".join(f"{k}={v}" for k, v in node.attributes)
            parts.append(f"{node.kind.value} {rendered}")
        parts += [f"{e.kind.value}" for e in self.edges]
        return "\n".join(parts)


class GraphEditOperation(HashedExperienceContract):
    kind: GraphEditOperationKind
    target: NonEmptyStr
    detail: str = Field(default="", max_length=2048)

    @property
    def order_key(self) -> tuple[str, str]:
        return self.kind.value, self.target


class GraphEditPath(HashedExperienceContract):
    """The ordered operations that turn a failed graph into its successful replacement."""

    path_id: NonEmptyStr
    from_graph_hash: Sha256Hex
    to_graph_hash: Sha256Hex
    operations: tuple[GraphEditOperation, ...] = ()

    @model_validator(mode="after")
    def operations_are_canonically_ordered(self) -> GraphEditPath:
        keys = [operation.order_key for operation in self.operations]
        if keys != sorted(keys):
            raise ValueError("edit operations must be in canonical order")
        if self.from_graph_hash == self.to_graph_hash and self.operations:
            raise ValueError("an empty transformation cannot carry operations")
        return self


class FailedSuccessGraphPair(HashedExperienceContract):
    pair_id: NonEmptyStr
    domain: NonEmptyStr
    group: NonEmptyStr
    task_signature: NonEmptyStr
    failed: ActionDecisionGraph
    successful: ActionDecisionGraph
    edit_path: GraphEditPath
    legacy_recompilation_unavailable: bool
    verification_mode: NonEmptyStr
    compiled_at: UtcDatetime

    @model_validator(mode="after")
    def the_pair_is_causal_and_the_path_connects_it(self) -> FailedSuccessGraphPair:
        if self.failed.accepted:
            raise ValueError("the failed side of a pair cannot be an accepted outcome")
        if not self.successful.accepted:
            raise ValueError("the successful side of a pair must be an accepted outcome")
        if self.failed.task_signature != self.successful.task_signature:
            raise ValueError("a pair whose two sides have different task signatures is not causal")
        if self.failed.group != self.successful.group:
            raise ValueError("a pair cannot span two groups")
        if self.edit_path.from_graph_hash != self.failed.structural_hash:
            raise ValueError("the edit path does not start at the failed graph")
        if self.edit_path.to_graph_hash != self.successful.structural_hash:
            raise ValueError("the edit path does not end at the successful graph")
        return self


class ExperienceGraphQuery(HashedExperienceContract):
    query_id: NonEmptyStr
    query_text: NonEmptyStr
    domain: NonEmptyStr
    task_signature: NonEmptyStr
    #: Groups the candidate pool must exclude, always including the query's own.
    excluded_groups: tuple[NonEmptyStr, ...] = Field(min_length=1)


class ExperienceGraphResultEntry(HashedExperienceContract):
    pair_id: NonEmptyStr
    rank: int = Field(ge=1)
    score: str
    arm: NonEmptyStr


class ExperienceGraphResult(HashedExperienceContract):
    query_id: NonEmptyStr
    arm: NonEmptyStr
    entries: tuple[ExperienceGraphResultEntry, ...] = ()
    candidates_considered: int = Field(ge=0)
    timed_out: int = Field(default=0, ge=0)
    limits: GraphResourceLimits = GraphResourceLimits()

    @model_validator(mode="after")
    def results_are_bounded_and_ranked(self) -> ExperienceGraphResult:
        if len(self.entries) > self.limits.returned_results:
            raise ValueError("more results returned than the declared bound")
        ranks = [entry.rank for entry in self.entries]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("result ranks must be dense and start at one")
        return self


PUBLIC_EXPERIENCE_GRAPH_CONTRACTS: tuple[type[HashedExperienceContract], ...] = (
    GraphResourceLimits,
    ExperienceGraphNode,
    ExperienceGraphEdge,
    ActionDecisionGraph,
    GraphEditOperation,
    GraphEditPath,
    FailedSuccessGraphPair,
    ExperienceGraphQuery,
    ExperienceGraphResultEntry,
    ExperienceGraphResult,
)
