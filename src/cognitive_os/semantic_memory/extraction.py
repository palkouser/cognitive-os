"""Credential-free deterministic extraction from typed Sprint 9 memory revisions."""

import json
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.memory import (
    CodeContextMemoryContent,
    CorrectionMemoryContent,
    EpisodeMemoryContent,
    MemoryRecord,
    MemoryRevision,
    TaskSummaryMemoryContent,
    UserInstructionMemoryContent,
    VerificationSummaryMemoryContent,
)
from cognitive_os.domain.semantic_memory import (
    ClaimProposal,
    ClaimTemporalInterval,
    ExtractionBudget,
    GroundedSourceSpan,
    GroundingMode,
    ObservationProposal,
    SemanticEntityRef,
    SemanticExtractionProposal,
    SemanticLiteral,
    SemanticLiteralKind,
    SemanticSourceRef,
    SemanticSourceType,
)

from .predicates import PredicateRegistry


def extract_typed_memory(
    record: MemoryRecord,
    revision: MemoryRevision,
    registry: PredicateRegistry,
) -> SemanticExtractionProposal:
    source = SemanticSourceRef(
        source_type=SemanticSourceType.MEMORY_REVISION,
        source_id=record.memory_id,
        revision=revision.revision,
        content_hash=revision.content_hash,
    )
    root = f"semantic:{record.memory_id}:{revision.revision}:{revision.content_hash}"
    fields: list[tuple[str, str, str, SemanticLiteralKind, str, str, object]] = []
    content = revision.content
    if isinstance(content, CodeContextMemoryContent):
        fields.extend(
            (
                (
                    "content.base_commit",
                    "repository.base_commit",
                    content.base_commit,
                    SemanticLiteralKind.STRING,
                    "repository",
                    record.scope.scope_id,
                    content.base_commit,
                ),
                (
                    "content.repository_profile",
                    "repository.supported_profile",
                    content.repository_profile,
                    SemanticLiteralKind.STRING,
                    "repository",
                    record.scope.scope_id,
                    content.repository_profile,
                ),
            )
        )
    elif isinstance(content, EpisodeMemoryContent):
        fields.extend(
            (
                (
                    "content.outcome",
                    "task.outcome",
                    content.outcome,
                    SemanticLiteralKind.STRING,
                    "task",
                    str(content.task_run_id),
                    content.outcome,
                ),
                (
                    "content.base_commit",
                    "repository.base_commit",
                    content.base_commit,
                    SemanticLiteralKind.STRING,
                    "repository",
                    content.repository_identity,
                    content.base_commit,
                ),
            ),
        )
    elif isinstance(content, TaskSummaryMemoryContent):
        fields.extend(
            (
                (
                    "content.result",
                    "task.outcome",
                    content.result,
                    SemanticLiteralKind.STRING,
                    "task",
                    str(content.task_run_id),
                    content.result,
                ),
                (
                    "content.review_status",
                    "task.acceptance_status",
                    content.review_status,
                    SemanticLiteralKind.STRING,
                    "task",
                    str(content.task_run_id),
                    content.review_status,
                ),
            ),
        )
    elif isinstance(content, VerificationSummaryMemoryContent):
        result_sets = (
            ("content.required_passed", "passed", content.required_passed),
            ("content.required_failed", "failed", content.required_failed),
            ("content.optional_results", "optional", content.optional_results),
            ("content.verifier_errors", "error", content.verifier_errors),
        )
        fields.extend(
            (
                path,
                "verification.result",
                f"{outcome}:{value}",
                SemanticLiteralKind.STRING,
                "verification",
                str(content.acceptance_decision_id),
                values,
            )
            for path, outcome, values in result_sets
            for value in values
        )
    elif isinstance(content, CorrectionMemoryContent):
        fields.append(
            (
                "content.correction",
                "memory.correction",
                content.correction,
                SemanticLiteralKind.STRING,
                "memory",
                str(content.corrected_memory_id or record.memory_id),
                content.correction,
            )
        )
    elif isinstance(content, UserInstructionMemoryContent):
        fields.append(
            (
                "content.instruction",
                "user.instruction",
                content.instruction,
                SemanticLiteralKind.STRING,
                "user",
                content.instruction_scope,
                content.instruction,
            )
        )
    if not fields:
        raise ValueError("typed memory content has no registered deterministic extractor")
    observations = []
    claims = []
    for index, (path, predicate_id, value, kind, subject_type, subject_id, excerpt) in enumerate(
        fields
    ):
        registry.require(predicate_id)
        observation_id = uuid5(NAMESPACE_URL, root + f":observation:{index}")
        encoded_excerpt = (
            excerpt.encode()
            if isinstance(excerpt, str)
            else json.dumps(excerpt, sort_keys=True, separators=(",", ":")).encode()
        )
        span = GroundedSourceSpan(
            source=source,
            mode=GroundingMode.MEMORY_FIELD,
            path=path,
            excerpt_hash=sha256(encoded_excerpt).hexdigest(),
        )
        observations.append(
            ObservationProposal(
                proposal_id=observation_id,
                content=value,
                source_spans=(span,),
            )
        )
        claims.append(
            ClaimProposal(
                proposal_id=uuid5(NAMESPACE_URL, root + f":claim:{index}"),
                subject=SemanticEntityRef(
                    entity_id=f"{subject_type}:{subject_id}",
                    entity_type=subject_type,
                    display_label=subject_id,
                ),
                predicate_id=predicate_id,
                object=SemanticLiteral(literal_kind=kind, value=value, unit=None),
                valid_interval=ClaimTemporalInterval(valid_from=revision.created_at),
                observation_proposal_ids=(observation_id,),
            )
        )
    return SemanticExtractionProposal(
        extraction_id=uuid5(NAMESPACE_URL, root),
        registry_snapshot_hash=registry.snapshot_hash(),
        observations=tuple(observations),
        claims=tuple(claims),
        budget=ExtractionBudget(
            maximum_observations=100,
            maximum_claims=100,
            maximum_evidence_links=100,
            maximum_relations=0,
        ),
    )
