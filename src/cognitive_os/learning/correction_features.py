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
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite, sqrt
from uuid import UUID

from pydantic import Field, model_validator

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_SCALARS,
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import (
    ENCODER_VERSION_V2,
    NUMERIC_FEATURE_NAMES,
    CorrectionEncoder,
    CorrectionEncoderV2,
    CorrectionFeatureInput,
    CorrectionFeatureInputV2,
    CorrectionFeatureVector,
    NumericBounds,
    NumericBoundsV2,
)
from cognitive_os.learning.correction_source import (
    NORMALIZER_VERSION,
    canonical_source_bytes,
)

#: What every generated task declares about itself. Both are corpus-wide constants rather than
#: per-task values, which is why they are stated here instead of being read off a spec.
PROBLEM_DOMAIN = "coding"
DECLARED_PROBLEM_TYPE = "repair"

#: The verifiers a generated task requires, as `build_manifest` records them.
DECLARED_VERIFIER_CAPABILITIES: tuple[str, ...] = ("coding.hidden_pytest", "coding.pytest")

#: W2-F1. The frozen MiniLM accepts 256 word-pieces and `ast.dump` output is dense: every one
#: of the 280 D3 fitting and calibration candidates tokenises to between 284 and 1549 pieces,
#: median 654. Fed whole, the model would read the module docstring, the function signature and
#: perhaps the first statement, and discard the body — the part that decides whether a candidate
#: repairs the contract. Every candidate in a group then embeds identically, which is exactly
#: what the vertical slice measured.
#:
#: So the canonical bytes are embedded in windows and mean-pooled. The declared input, the model
#: identity and revision, the channel names and the 384 dimensions are all unchanged; what
#: changes is that the encoder now sees the input the contract says it embeds. The window is in
#: characters because that is what can be bounded without a tokenizer at encode time: the densest
#: canonical text measured 0.5437 pieces per character, so 400 characters cannot exceed 218
#: pieces.
CANONICAL_EMBEDDING_WINDOW_CHARACTERS = 400


def canonical_embedding_windows(candidate_source: str) -> tuple[str, ...]:
    """The canonical candidate source split into windows the frozen model reads whole."""
    text = canonical_source_bytes(candidate_source).decode("utf-8")
    width = CANONICAL_EMBEDDING_WINDOW_CHARACTERS
    return tuple(text[start : start + width] for start in range(0, len(text), width)) or (text,)


def pool_canonical_embedding(vectors: Sequence[Sequence[float]]) -> tuple[float, ...]:
    """Mean-pool one candidate's window vectors, renormalised back onto the unit sphere.

    Mean before normalisation, so a long candidate is not dominated by whichever window happens
    to be last; renormalised after, so the pooled vector stays comparable with a single-window
    one under the cosine the ranker uses.
    """
    if not vectors:
        raise ValueError("a pooled embedding needs at least one window vector")
    width = len(vectors[0])
    if any(len(vector) != width for vector in vectors):
        raise ValueError("window vectors must share one dimension")
    mean = [sum(vector[index] for vector in vectors) / len(vectors) for index in range(width)]
    norm = sqrt(sum(value * value for value in mean))
    if not norm:
        return tuple(mean)
    return tuple(value / norm for value in mean)


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


def feature_input_v2(
    *,
    candidate_source: str,
    canonical_candidate_source_embedding: tuple[float, ...],
    missing_value_indicators: int = 0,
) -> CorrectionFeatureInputV2:
    """Build only the source-derived channels declared by correction-ranking-v2."""
    graph = statement_graph(candidate_source)
    return CorrectionFeatureInputV2(
        canonical_candidate_source=canonical_source_bytes(candidate_source),
        canonical_candidate_source_embedding=canonical_candidate_source_embedding,
        candidate_source_ast_node_count=ast_node_count(candidate_source),
        statement_graph_node_count=graph.node_count,
        statement_graph_edge_count=graph.edge_count,
        statement_graph_path_count=graph.path_length,
        declared_verifier_capability_count=len(DECLARED_VERIFIER_CAPABILITIES),
        missing_value_indicators=missing_value_indicators,
    )


def raw_numeric_row_v2(features: CorrectionFeatureInputV2) -> dict[str, float]:
    return {name: float(getattr(features, name)) for name in FITTED_FEATURE_V2_SCALARS}


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


class SealedFeatureRecordV2(HashedExperienceContract):
    """One exact v2 feature member, including the fitted embedding and source authority."""

    candidate_id: UUID
    task_id: UUID
    repository_group: NonEmptyStr
    encoder_version: NonEmptyStr
    canonical_source_hash: Sha256Hex
    values: tuple[tuple[NonEmptyStr, float], ...] = Field(min_length=1)
    embedding: tuple[float, ...] = Field(min_length=384, max_length=384)
    feature_vector_hash: Sha256Hex

    @model_validator(mode="after")
    def fitted_vector_is_self_consistent(self) -> SealedFeatureRecordV2:
        if self.encoder_version != ENCODER_VERSION_V2:
            raise ValueError("a v2 feature record must declare the v2 encoder")
        if tuple(name for name, _ in self.values) != FITTED_FEATURE_V2_SCALARS:
            raise ValueError("a v2 feature record must contain the exact six fitted scalars")
        numbers = tuple(value for _, value in self.values)
        if any(not isfinite(value) or not 0.0 <= value <= 1.0 for value in numbers):
            raise ValueError("v2 fitted scalars must be finite in [0, 1]")
        if any(not isfinite(value) or not -1.0 <= value <= 1.0 for value in self.embedding):
            raise ValueError("v2 fitted embedding values must be finite in [-1, 1]")
        vector = CorrectionFeatureVector(
            encoder_version=self.encoder_version,
            values=self.values,
            embedding=self.embedding,
        )
        if self.feature_vector_hash != vector.content_hash():
            raise ValueError("v2 feature-vector hash does not match its fitted values")
        return self


class SealedFeatureRecordSetV2(HashedExperienceContract):
    """Replay-complete v2 feature seal, immutable and necessarily pre-outcome."""

    partition: NonEmptyStr
    campaign_manifest_hash: Sha256Hex
    feature_contract_hash: Sha256Hex
    encoder_version: NonEmptyStr
    normalizer_version: NonEmptyStr
    code_revision: NonEmptyStr
    embedding_model_id: NonEmptyStr
    embedding_revision: NonEmptyStr
    embedding_tree_digest: Sha256Hex
    embedding_dimension: int = Field(default=384, ge=384, le=384)
    numeric_lower: tuple[tuple[NonEmptyStr, float], ...] = Field(min_length=1)
    numeric_upper: tuple[tuple[NonEmptyStr, float], ...] = Field(min_length=1)
    records: tuple[SealedFeatureRecordV2, ...] = Field(min_length=1)
    sealed_at: UtcDatetime
    outcomes_present: bool = False

    def model_post_init(self, context: object) -> None:
        if self.outcomes_present:
            raise ValueError("a v2 feature seal cannot be created after outcomes exist")
        if len({record.candidate_id for record in self.records}) != len(self.records):
            raise ValueError("a v2 feature seal cannot contain duplicate candidates")
        if self.encoder_version != ENCODER_VERSION_V2 or any(
            record.encoder_version != self.encoder_version for record in self.records
        ):
            raise ValueError("a v2 feature seal must contain only v2 encoder records")
        if self.feature_contract_hash != CorrectionFeatureContractV2().content_hash:
            raise ValueError("a v2 feature seal names another feature contract")
        if self.normalizer_version != NORMALIZER_VERSION:
            raise ValueError("a v2 feature seal names another source normalizer")
        expected = FITTED_FEATURE_V2_SCALARS
        if (
            tuple(name for name, _ in self.numeric_lower) != expected
            or tuple(name for name, _ in self.numeric_upper) != expected
        ):
            raise ValueError("a v2 feature seal must store the exact six numeric bounds")
        for (name, low), (_, high) in zip(self.numeric_lower, self.numeric_upper, strict=True):
            if not isfinite(low) or not isfinite(high) or low > high:
                raise ValueError(f"a v2 feature seal stores invalid bounds for {name!r}")

    def record_for(self, candidate_id: UUID) -> SealedFeatureRecordV2:
        for record in self.records:
            if record.candidate_id == candidate_id:
                return record
        raise KeyError(f"candidate {candidate_id} has no sealed v2 feature record")


@dataclass(frozen=True, slots=True)
class PendingFeatureV2:
    candidate_id: UUID
    task_id: UUID
    repository_group: str
    candidate_source: str
    canonical_candidate_source_embedding: tuple[float, ...]
    missing_value_indicators: int = 0


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


def seal_feature_records_v2(
    pending: list[PendingFeatureV2],
    *,
    partition: str,
    campaign_manifest_hash: str,
    bounds: NumericBoundsV2,
    embedding_model_id: str,
    embedding_revision: str,
    embedding_tree_digest: str,
    code_revision: str,
    sealed_at: datetime,
    earliest_outcome_at: datetime | None = None,
    outcomes_present: bool = False,
) -> SealedFeatureRecordSetV2:
    """Seal replay-complete v2 feature bytes before any candidate outcome can exist."""
    if not pending:
        raise ValueError("a v2 feature seal must contain at least one candidate")
    if outcomes_present or (earliest_outcome_at is not None and sealed_at >= earliest_outcome_at):
        raise ValueError("v2 feature records must be sealed strictly before every outcome")
    contract = CorrectionFeatureContractV2()
    encoder = CorrectionEncoderV2(bounds, contract=contract)
    records: list[SealedFeatureRecordV2] = []
    for item in sorted(pending, key=lambda value: str(value.candidate_id)):
        features = feature_input_v2(
            candidate_source=item.candidate_source,
            canonical_candidate_source_embedding=item.canonical_candidate_source_embedding,
            missing_value_indicators=item.missing_value_indicators,
        )
        vector = encoder.encode(features)
        records.append(
            SealedFeatureRecordV2(
                candidate_id=item.candidate_id,
                task_id=item.task_id,
                repository_group=item.repository_group,
                encoder_version=encoder.version,
                canonical_source_hash=sha256(features.canonical_candidate_source).hexdigest(),
                values=vector.values,
                embedding=vector.embedding,
                feature_vector_hash=vector.content_hash(),
            )
        )
    return SealedFeatureRecordSetV2(
        partition=partition,
        campaign_manifest_hash=campaign_manifest_hash,
        feature_contract_hash=contract.content_hash,
        encoder_version=encoder.version,
        normalizer_version=NORMALIZER_VERSION,
        code_revision=code_revision,
        embedding_model_id=embedding_model_id,
        embedding_revision=embedding_revision,
        embedding_tree_digest=embedding_tree_digest,
        numeric_lower=tuple((name, bounds.lower[name]) for name in FITTED_FEATURE_V2_SCALARS),
        numeric_upper=tuple((name, bounds.upper[name]) for name in FITTED_FEATURE_V2_SCALARS),
        records=tuple(records),
        sealed_at=sealed_at,
    )
