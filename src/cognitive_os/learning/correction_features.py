"""S21D2-023: the pre-outcome feature record, and what a feature is derived from.

The feature contract says every fitted field must be derivable from the task and the candidate
patch *before* the sandbox runs. That is a claim about where the numbers come from, and the
only way to keep it a claim rather than a hope is to have one place that produces them and to
seal the result before execution starts.

So this module reads exactly three things: the task's own text, the candidate's module source,
and the unified diff between the baseline and that source. It never sees a verifier result, a
recipe, a variant index or a candidate identity — `CandidateProvenance` exists for identity and
is a different object on purpose.

Two definitions are worth stating because neither is forced by the names.

*The counts come from the diff, not from a comparison of file trees.* `hunk_count`,
`added_line_count` and `removed_line_count` are read off the unified diff the campaign actually
stored and executed, so a feature cannot describe an edit different from the one that ran.

*The graph is the statement graph, not the AST.* `ast_node_count` already counts every AST node;
counting them again under a second name would give the encoder two copies of one number. The
graph features describe the candidate's statement structure — containment and sequence between
statements, and the deepest nesting — which is what the correction's shape actually is.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import Field

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_ranking import (
    NUMERIC_FEATURE_NAMES,
    CorrectionEncoder,
    CorrectionFeatureInput,
    NumericBounds,
)

#: What every generated task declares about itself. Both are corpus-wide constants rather than
#: per-task values, which is why they are stated here instead of being read off a spec.
PROBLEM_DOMAIN = "coding"
DECLARED_PROBLEM_TYPE = "repair"

#: The verifiers a generated task requires, as `build_manifest` records them.
DECLARED_VERIFIER_CAPABILITIES: tuple[str, ...] = ("coding.hidden_pytest", "coding.pytest")


@dataclass(frozen=True, slots=True)
class DiffCounts:
    """What the stored patch changed, counted off the patch itself."""

    hunk_count: int
    added_line_count: int
    removed_line_count: int
    changed_file_count: int


def diff_counts(unified_diff: str) -> DiffCounts:
    """Read the edit size off the diff the campaign stored.

    Counts the `+`/`-` body lines and ignores the `+++`/`---` headers, which are file names
    rather than changes; a counter that includes them reports every single-file edit as one
    line larger than it is.
    """
    hunks = 0
    added = 0
    removed = 0
    files: set[str] = set()
    for line in unified_diff.splitlines():
        if line.startswith("@@"):
            hunks += 1
        elif line.startswith("+++ ") or line.startswith("--- "):
            continue
        elif line.startswith("diff --git "):
            files.add(line.rsplit(" ", 1)[-1])
        elif line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return DiffCounts(
        hunk_count=hunks,
        added_line_count=added,
        removed_line_count=removed,
        changed_file_count=len(files),
    )


@dataclass(frozen=True, slots=True)
class StatementGraph:
    """The candidate's statement structure: how many, how connected, how deep."""

    node_count: int
    edge_count: int
    path_length: int


def statement_graph(source: str) -> StatementGraph:
    """Containment and sequence edges over the statements of one module.

    A statement is an edge to its parent statement and an edge to the sibling before it, so a
    flat function and a deeply nested one with the same statement count are different shapes.
    """
    tree = ast.parse(source)
    nodes = 0
    edges = 0
    deepest = 0

    def walk(body: list[ast.stmt], depth: int, parent: bool) -> None:
        nonlocal nodes, edges, deepest
        deepest = max(deepest, depth)
        previous = False
        for statement in body:
            nodes += 1
            if parent:
                edges += 1
            if previous:
                edges += 1
            previous = True
            for name in ("body", "orelse", "finalbody"):
                nested = getattr(statement, name, None)
                if nested:
                    walk(list(nested), depth + 1, True)
            for handler in getattr(statement, "handlers", ()):
                walk(list(handler.body), depth + 1, True)

    walk(list(tree.body), 1, False)
    return StatementGraph(node_count=nodes, edge_count=edges, path_length=deepest)


def ast_node_count(source: str) -> int:
    return sum(1 for _ in ast.walk(ast.parse(source)))


def requirement_text(issue: str, expected: str) -> str:
    """The task side of the pair, as one text. Never includes a candidate or a result."""
    return f"{issue.strip()}\n\n{expected.strip()}"


def feature_input(
    *,
    candidate_source: str,
    unified_diff: str,
    task_requirement_embedding: tuple[float, ...],
    candidate_delta_embedding: tuple[float, ...],
) -> CorrectionFeatureInput:
    """One candidate's pre-outcome features. Everything here exists before the sandbox runs."""
    counts = diff_counts(unified_diff)
    graph = statement_graph(candidate_source)
    return CorrectionFeatureInput(
        problem_domain=PROBLEM_DOMAIN,
        declared_problem_type=DECLARED_PROBLEM_TYPE,
        task_requirement_embedding=task_requirement_embedding,
        candidate_delta_embedding=candidate_delta_embedding,
        changed_file_count=counts.changed_file_count,
        hunk_count=counts.hunk_count,
        added_line_count=counts.added_line_count,
        removed_line_count=counts.removed_line_count,
        ast_node_count=ast_node_count(candidate_source),
        graph_node_count=graph.node_count,
        graph_edge_count=graph.edge_count,
        graph_path_length=graph.path_length,
        declared_verifier_capabilities=DECLARED_VERIFIER_CAPABILITIES,
    )


def raw_numeric_row(features: CorrectionFeatureInput) -> dict[str, float]:
    """The unscaled numbers `NumericBounds.from_training` is fitted on."""
    return {name: float(getattr(features, name)) for name in NUMERIC_FEATURE_NAMES}


class SealedFeatureRecord(HashedExperienceContract):
    """One candidate's features, sealed before it was executed.

    Carries `candidate_id` because a record has to say who it describes, and the encoded
    vector below carries none: identity is how the record is filed, never a fitted column.
    """

    candidate_id: UUID
    task_id: UUID
    repository_group: NonEmptyStr
    encoder_version: NonEmptyStr
    #: `(name, scaled value)` exactly as the encoder produced them.
    values: tuple[tuple[NonEmptyStr, float], ...] = Field(min_length=1)
    feature_vector_hash: Sha256Hex


class SealedFeatureRecordSet(HashedExperienceContract):
    """Every feature record for one partition, sealed at one moment, before any outcome.

    `sealed_at` is what the projector compares an outcome's own time against, so this contract
    is the authority for the chronology rather than a note about it. The normalisation bounds
    travel with the set because a scaled value whose bounds are lost cannot be recomputed.
    """

    partition: NonEmptyStr
    campaign_manifest_hash: Sha256Hex
    encoder_version: NonEmptyStr
    embedding_model_id: NonEmptyStr
    embedding_revision: NonEmptyStr
    embedding_dimension: int = Field(ge=1)
    numeric_lower: tuple[tuple[NonEmptyStr, float], ...] = Field(min_length=1)
    numeric_upper: tuple[tuple[NonEmptyStr, float], ...] = Field(min_length=1)
    records: tuple[SealedFeatureRecord, ...] = Field(min_length=1)
    sealed_at: UtcDatetime
    outcomes_present: bool = False

    def record_for(self, candidate_id: UUID) -> SealedFeatureRecord:
        for record in self.records:
            if record.candidate_id == candidate_id:
                return record
        raise KeyError(f"candidate {candidate_id} has no sealed feature record")


@dataclass(frozen=True, slots=True)
class PendingFeature:
    """One candidate's inputs, before the bounds that scale them have been fitted."""

    candidate_id: UUID
    task_id: UUID
    repository_group: str
    features: CorrectionFeatureInput


def seal_feature_records(
    pending: list[PendingFeature],
    *,
    partition: str,
    campaign_manifest_hash: str,
    bounds: NumericBounds,
    embedding_model_id: str,
    embedding_revision: str,
    embedding_dimension: int,
    sealed_at: datetime,
) -> SealedFeatureRecordSet:
    """Encode every pending candidate under one set of bounds and seal the result.

    `bounds` is an argument rather than something fitted here: they must come from training
    alone, and a function that fitted them on whatever it was handed would silently fit them
    on calibration the first time it was called with a calibration partition.
    """
    encoder = CorrectionEncoder(bounds)
    records = tuple(
        SealedFeatureRecord(
            candidate_id=item.candidate_id,
            task_id=item.task_id,
            repository_group=item.repository_group,
            encoder_version=encoder.version,
            values=(vector := encoder.encode(item.features)).values,
            feature_vector_hash=vector.content_hash(),
        )
        for item in sorted(pending, key=lambda item: str(item.candidate_id))
    )
    return SealedFeatureRecordSet(
        partition=partition,
        campaign_manifest_hash=campaign_manifest_hash,
        encoder_version=encoder.version,
        embedding_model_id=embedding_model_id,
        embedding_revision=embedding_revision,
        embedding_dimension=embedding_dimension,
        numeric_lower=tuple((name, bounds.lower[name]) for name in NUMERIC_FEATURE_NAMES),
        numeric_upper=tuple((name, bounds.upper[name]) for name in NUMERIC_FEATURE_NAMES),
        records=records,
        sealed_at=sealed_at,
    )
