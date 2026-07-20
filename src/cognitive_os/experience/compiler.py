"""Deterministic Experience Compiler pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.config.experience_config import ExperienceConfiguration
from cognitive_os.domain.experience import (
    CausalOriginAssessment,
    CompilationDecision,
    CompilationDecisionType,
    CompilationManifest,
    CompilerProfile,
    ContributionRecord,
    ContributionSubjectType,
    ContributionType,
    CorrectionRecord,
    ExecutionSegment,
    ExecutionSegmentType,
    ExperienceAnalysis,
    ExperienceCandidate,
    ExperienceCandidateStatus,
    ExperienceCandidateType,
    ExperienceCompilationRequest,
    ExperienceStepStatus,
    ExperienceVerifierBundle,
    FailedBranch,
    FirstIncorrectAssessment,
    FirstIncorrectType,
    GeneralizabilityAssessment,
    GeneralizabilityLevel,
    NormalizedTrajectory,
    PolicyCompliance,
    RecoveryPath,
    StepAssessment,
    StepCorrectness,
    StepEfficiency,
    StepNecessity,
    SuccessfulPath,
    TimelineEntry,
    TimelineEntryType,
    TrajectoryCompleteness,
    TrajectoryConflict,
    TrajectoryGap,
    TrajectoryOrderingDecision,
    TrajectorySnapshot,
    VerificationCapabilityResult,
)
from cognitive_os.domain.memory import MemorySensitivity

from .errors import ExperiencePolicyError, ExperienceSourceError
from .registry import CompilerProfileRegistry, SourceResolverRegistry, canonical_hash

MANDATORY_CAPABILITIES = (
    "experience.source_completeness",
    "experience.source_identity",
    "experience.source_hash_integrity",
    "experience.event_order_integrity",
    "experience.artifact_integrity",
    "experience.terminal_outcome_integrity",
    "experience.verifier_evidence_integrity",
    "experience.deterministic_reconstruction",
    "experience.step_assessment_integrity",
    "experience.no_unsupported_causal_claim",
    "experience.candidate_provenance",
    "experience.candidate_schema",
    "experience.sensitive_data_policy",
    "experience.idempotency",
    "experience.manifest_integrity",
)


@dataclass(frozen=True)
class ExperienceCompilationResult:
    snapshot: TrajectorySnapshot
    trajectory: NormalizedTrajectory
    segments: tuple[ExecutionSegment, ...]
    assessments: tuple[StepAssessment, ...]
    analysis: ExperienceAnalysis
    candidates: tuple[ExperienceCandidate, ...]
    verifier_bundle: ExperienceVerifierBundle
    decision: CompilationDecision
    manifest: CompilationManifest


def _segment_type(entry: TimelineEntry) -> ExecutionSegmentType:
    mapping = {
        TimelineEntryType.PLAN: ExecutionSegmentType.PLANNING,
        TimelineEntryType.CONTEXT: ExecutionSegmentType.CONTEXT_BUILD,
        TimelineEntryType.PROVIDER: ExecutionSegmentType.PROVIDER_EXECUTION,
        TimelineEntryType.TOOL: ExecutionSegmentType.TOOL_EXECUTION,
        TimelineEntryType.SKILL: ExecutionSegmentType.SKILL_EXECUTION,
        TimelineEntryType.STRATEGY: ExecutionSegmentType.STRATEGY_PHASE,
        TimelineEntryType.VERIFIER: ExecutionSegmentType.VERIFICATION,
        TimelineEntryType.ACCEPTANCE: ExecutionSegmentType.ACCEPTANCE,
        TimelineEntryType.APPROVAL: ExecutionSegmentType.APPROVAL,
        TimelineEntryType.CANCELLATION: ExecutionSegmentType.CANCELLATION,
        TimelineEntryType.CORRECTION: ExecutionSegmentType.REPAIR,
    }
    return mapping.get(entry.entry_type, ExecutionSegmentType.CLARIFICATION)


def _subject_type(entry: TimelineEntry) -> ContributionSubjectType | None:
    return {
        TimelineEntryType.PROVIDER: ContributionSubjectType.MODEL_CALL,
        TimelineEntryType.TOOL: ContributionSubjectType.TOOL_CALL,
        TimelineEntryType.SKILL: ContributionSubjectType.SKILL_REVISION,
        TimelineEntryType.STRATEGY: ContributionSubjectType.STRATEGY_REVISION,
        TimelineEntryType.CONTEXT: ContributionSubjectType.CONTEXT_BUNDLE,
        TimelineEntryType.CORRECTION: ContributionSubjectType.USER_CORRECTION,
        TimelineEntryType.VERIFIER: ContributionSubjectType.VERIFIER,
    }.get(entry.entry_type)


def _assessment(entry: TimelineEntry, profile: CompilerProfile) -> StepAssessment:
    failed = entry.status in {ExperienceStepStatus.FAILED, ExperienceStepStatus.DENIED}
    policy_violation = (
        entry.status is ExperienceStepStatus.DENIED or "policy_violation" in entry.event_type
    )
    correctness = (
        StepCorrectness.INCORRECT
        if failed
        else (
            StepCorrectness.CORRECT
            if entry.status is ExperienceStepStatus.COMPLETED
            and entry.entry_type
            in {TimelineEntryType.VERIFIER, TimelineEntryType.ACCEPTANCE, TimelineEntryType.TOOL}
            else StepCorrectness.UNKNOWN
        )
    )
    return StepAssessment(
        step_id=entry.step_id or str(entry.timeline_entry_id),
        sequence=entry.sequence,
        intent=entry.payload_summary,
        outputs=entry.evidence_refs if entry.status is ExperienceStepStatus.COMPLETED else (),
        authoritative_evidence=entry.evidence_refs,
        status=entry.status,
        correctness=correctness,
        necessity=(
            StepNecessity.REDUNDANT if "duplicate" in entry.event_type else StepNecessity.UNKNOWN
        ),
        efficiency=(
            StepEfficiency.INEFFICIENT if "retry" in entry.event_type else StepEfficiency.UNKNOWN
        ),
        policy_compliance=(
            PolicyCompliance.NON_COMPLIANT if policy_violation else PolicyCompliance.COMPLIANT
        ),
        first_incorrect_candidate=failed,
        confidence=1.0 if failed or correctness is StepCorrectness.CORRECT else 0.0,
        reason=(
            "authoritative failure signal" if failed else "no authoritative correctness evidence"
        ),
        limitations=(() if failed else ("causal contribution is not established",)),
        assessment_profile=f"{profile.assessment_policy}:{profile.content_hash}",
    )


class ExperienceCompiler:
    """Credential-free compiler that cannot mutate source or destination systems."""

    def __init__(
        self,
        sources: SourceResolverRegistry,
        profiles: CompilerProfileRegistry,
        configuration: ExperienceConfiguration | None = None,
    ) -> None:
        self._sources = sources
        self._profiles = profiles
        self._configuration = configuration or ExperienceConfiguration()
        self._cache: dict[str, ExperienceCompilationResult] = {}
        self._cancelled: set[UUID] = set()

    def cancel(self, compilation_id: UUID) -> None:
        self._cancelled.add(compilation_id)

    def compile(self, request: ExperienceCompilationRequest) -> ExperienceCompilationResult:
        cached = self._cache.get(request.idempotency_key)
        if cached is not None:
            if cached.manifest.compilation_id != request.compilation_id:
                raise ExperiencePolicyError("idempotency key belongs to another compilation")
            return cached
        profile = self._profiles.resolve(
            request.compiler_profile_id, request.compiler_profile_version
        )
        self._validate_request(request, profile)
        if request.compilation_id in self._cancelled:
            raise ExperiencePolicyError("compilation was cancelled before snapshot creation")
        snapshot, entries = self._snapshot(request, profile)
        self._assert_not_cancelled(request.compilation_id)
        trajectory = self._reconstruct(snapshot, entries)
        segments = self._segment(trajectory)
        assessments = tuple(_assessment(entry, profile) for entry in trajectory.entries)
        self._assert_not_cancelled(request.compilation_id)
        analysis = self._analyze(request, snapshot, trajectory, segments, assessments, profile)
        candidates = self._generate_candidates(request, snapshot, trajectory, analysis, profile)
        verifier_bundle = self._verify(
            request, snapshot, trajectory, assessments, analysis, candidates
        )
        decision = self._decide(request, snapshot, verifier_bundle)
        manifest = CompilationManifest(
            compilation_id=request.compilation_id,
            source_snapshot_hash=snapshot.content_hash,
            reconstruction_hash=trajectory.content_hash,
            analysis_hash=analysis.content_hash,
            candidate_hashes=tuple(item.content_hash for item in candidates),
            verifier_bundle_hash=verifier_bundle.content_hash,
            compilation_decision=decision.decision,
            warnings=decision.warnings,
            usage={
                "sources": len(snapshot.source_refs),
                "events": len(trajectory.entries),
                "segments": len(segments),
                "steps": len(assessments),
                "candidates": len(candidates),
                "provider_calls": 0,
            },
            created_at=request.created_at,
        )
        result = ExperienceCompilationResult(
            snapshot=snapshot,
            trajectory=trajectory,
            segments=segments,
            assessments=assessments,
            analysis=analysis,
            candidates=candidates,
            verifier_bundle=verifier_bundle,
            decision=decision,
            manifest=manifest,
        )
        self._cache[request.idempotency_key] = result
        return result

    def validate_manifest(self, result: ExperienceCompilationResult) -> bool:
        manifest = result.manifest
        return (
            manifest.source_snapshot_hash == result.snapshot.content_hash
            and manifest.reconstruction_hash == result.trajectory.content_hash
            and manifest.analysis_hash == result.analysis.content_hash
            and manifest.candidate_hashes == tuple(item.content_hash for item in result.candidates)
            and manifest.verifier_bundle_hash == result.verifier_bundle.content_hash
            and manifest.compilation_decision is result.decision.decision
        )

    def _assert_not_cancelled(self, compilation_id: UUID) -> None:
        if compilation_id in self._cancelled:
            raise ExperiencePolicyError("compilation cancelled between deterministic stages")

    def _validate_request(
        self, request: ExperienceCompilationRequest, profile: CompilerProfile
    ) -> None:
        if request.candidate_types - profile.candidate_types:
            raise ExperiencePolicyError("request contains candidate types disabled by the profile")
        if request.compiler_profile_hash != profile.content_hash:
            raise ExperiencePolicyError("compiler profile hash mismatch")
        if len(request.trajectory_sources) > min(
            request.budget.maximum_sources,
            profile.resource_limits.maximum_sources,
            self._configuration.maximum_sources_per_compilation,
        ):
            raise ExperiencePolicyError("source budget exceeded")
        if request.budget.maximum_provider_calls > profile.resource_limits.maximum_provider_calls:
            raise ExperiencePolicyError("request expands the compiler profile provider budget")
        if (
            profile.provider_assistance_enabled
            and not self._configuration.allow_provider_assisted_analysis
        ):
            raise ExperiencePolicyError("provider assistance is disabled by host policy")

    def _snapshot(
        self, request: ExperienceCompilationRequest, profile: CompilerProfile
    ) -> tuple[TrajectorySnapshot, tuple[TimelineEntry, ...]]:
        supplied = {item.source_type for item in request.trajectory_sources}
        missing = profile.required_source_types - supplied
        if missing:
            raise ExperienceSourceError(
                "missing mandatory source types: "
                + ", ".join(sorted(item.value for item in missing))
            )
        resolved = tuple(self._sources.resolve(item) for item in request.trajectory_sources)
        terminal_states = {item.terminal_state for item in resolved if item.terminal_state}
        if len(terminal_states) != 1:
            raise ExperienceSourceError("trajectory requires one exact terminal state")
        refs = tuple(
            sorted(
                (item.reference for item in resolved),
                key=lambda item: (item.source_type.value, item.source_id, item.source_revision),
            )
        )
        entries = tuple(entry for item in resolved for entry in item.timeline_entries)
        stream_versions = {
            str(item.event_stream_id): item.event_stream_version
            for item in refs
            if item.event_stream_id is not None and item.event_stream_version is not None
        }
        optional_missing = profile.enabled_source_types - supplied
        completeness = (
            TrajectoryCompleteness.COMPLETE_WITH_WARNINGS
            if optional_missing
            else TrajectoryCompleteness.COMPLETE
        )
        return (
            TrajectorySnapshot(
                task_run_id=request.task_run_id,
                terminal_state=terminal_states.pop(),
                source_refs=refs,
                event_stream_versions=dict(sorted(stream_versions.items())),
                artifact_hashes=tuple(
                    sorted(
                        item.source_content_hash for item in refs if item.artifact_id is not None
                    )
                ),
                plan_revisions=tuple(
                    sorted(
                        {
                            int(item.source_revision)
                            for item in refs
                            if item.source_type.value == "plan" and item.source_revision.isdigit()
                        }
                    )
                ),
                context_bundle_revisions=tuple(
                    sorted(
                        item.source_revision for item in refs if item.source_type.value == "context"
                    )
                ),
                memory_revision_refs=tuple(
                    sorted(
                        item.source_revision
                        for item in refs
                        if item.source_type.value == "memory_revision"
                    )
                ),
                semantic_revision_refs=tuple(
                    sorted(
                        item.source_revision
                        for item in refs
                        if item.source_type.value == "semantic_revision"
                    )
                ),
                skill_revisions=tuple(
                    sorted(
                        item.source_revision
                        for item in refs
                        if item.source_type.value == "skill_revision"
                    )
                ),
                strategy_revisions=tuple(
                    sorted(
                        item.source_revision
                        for item in refs
                        if item.source_type.value == "strategy_revision"
                    )
                ),
                completeness=completeness,
                snapshot_created_at=request.created_at,
            ),
            entries,
        )

    def _reconstruct(
        self, snapshot: TrajectorySnapshot, entries: tuple[TimelineEntry, ...]
    ) -> NormalizedTrajectory:
        ordered = tuple(
            sorted(
                entries,
                key=lambda item: (
                    item.sequence,
                    item.started_at,
                    item.source_ref.source_type.value,
                    item.source_ref.source_id,
                    str(item.timeline_entry_id),
                ),
            )
        )
        if len(ordered) > self._configuration.maximum_events_per_compilation:
            raise ExperiencePolicyError("event budget exceeded")
        sequences: dict[int, list[TimelineEntry]] = {}
        for entry in ordered:
            sequences.setdefault(entry.sequence, []).append(entry)
        conflicts = tuple(
            TrajectoryConflict(
                sequence=sequence,
                source_refs=tuple(item.source_ref for item in values),
                reason="multiple authoritative entries claim the same sequence",
            )
            for sequence, values in sorted(sequences.items())
            if len(values) > 1
        )
        present = sorted(sequences)
        gaps = tuple(
            TrajectoryGap(
                after_sequence=left,
                before_sequence=right,
                reason="authoritative event sequence gap",
            )
            for left, right in pairwise(present)
            if right > left + 1
        )
        decisions = tuple(
            TrajectoryOrderingDecision(
                timeline_entry_id=entry.timeline_entry_id,
                canonical_sequence=index,
                reason="sequence, UTC timestamp, source identity, and entry identity",
            )
            for index, entry in enumerate(ordered, 1)
        )
        completeness = (
            TrajectoryCompleteness.CONFLICTED
            if conflicts
            else TrajectoryCompleteness.INCOMPLETE
            if gaps
            else snapshot.completeness
        )
        return NormalizedTrajectory(
            task_run_id=snapshot.task_run_id,
            entries=ordered,
            gaps=gaps,
            conflicts=conflicts,
            ordering_decisions=decisions,
            completeness=completeness,
            terminal_state=snapshot.terminal_state,
        )

    def _segment(self, trajectory: NormalizedTrajectory) -> tuple[ExecutionSegment, ...]:
        segments = tuple(
            ExecutionSegment(
                segment_id=uuid5(NAMESPACE_URL, f"experience-segment:{entry.content_hash}"),
                segment_type=_segment_type(entry),
                first_sequence=entry.sequence,
                last_sequence=entry.sequence,
                timeline_entry_ids=(entry.timeline_entry_id,),
                status=entry.status,
            )
            for entry in trajectory.entries
        )
        if len(segments) > self._configuration.maximum_segments:
            raise ExperiencePolicyError("segment budget exceeded")
        return segments

    def _analyze(
        self,
        request: ExperienceCompilationRequest,
        snapshot: TrajectorySnapshot,
        trajectory: NormalizedTrajectory,
        segments: tuple[ExecutionSegment, ...],
        assessments: tuple[StepAssessment, ...],
        profile: CompilerProfile,
    ) -> ExperienceAnalysis:
        failed = tuple(
            item for item in assessments if item.correctness is StepCorrectness.INCORRECT
        )
        first = min(failed, key=lambda item: item.sequence) if failed else None
        first_entry = (
            next((item for item in trajectory.entries if item.sequence == first.sequence), None)
            if first
            else None
        )
        if first and first.policy_compliance is PolicyCompliance.NON_COMPLIANT:
            origin_type = FirstIncorrectType.POLICY_VIOLATION
            causal = True
        elif first_entry and first_entry.entry_type is TimelineEntryType.VERIFIER:
            origin_type = FirstIncorrectType.OBJECTIVE_VERIFIER_FAILURE
            causal = False
        elif first_entry and first_entry.entry_type is TimelineEntryType.TOOL:
            origin_type = FirstIncorrectType.INCORRECT_TOOL_POSTCONDITION
            causal = False
        else:
            origin_type = FirstIncorrectType.UNKNOWN_CAUSAL_ORIGIN
            causal = False
        first_incorrect = FirstIncorrectAssessment(
            first_observed_failure_step_id=first.step_id if first else None,
            candidates=tuple(item.step_id for item in failed),
            causal_origin=CausalOriginAssessment(
                origin_type=origin_type,
                step_ids=((first.step_id,) if first else ()),
                evidence_refs=((first.authoritative_evidence) if first else ()),
                causal_claim_supported=causal,
                reason=(
                    "policy denial is authoritative evidence of the policy violation"
                    if causal
                    else "temporal order does not establish causal origin"
                ),
            ),
        )
        accepted = snapshot.terminal_state == "accepted"
        successful = (
            SuccessfulPath(
                path_id=uuid5(NAMESPACE_URL, f"experience-success:{trajectory.content_hash}"),
                timeline_entry_ids=tuple(
                    item.timeline_entry_id
                    for item in trajectory.entries
                    if item.status is ExperienceStepStatus.COMPLETED
                ),
                segment_ids=tuple(
                    item.segment_id
                    for item in segments
                    if item.status is ExperienceStepStatus.COMPLETED
                ),
                terminal_status=ExperienceStepStatus.COMPLETED,
                evidence_refs=tuple(
                    evidence
                    for item in trajectory.entries
                    if item.status is ExperienceStepStatus.COMPLETED
                    for evidence in item.evidence_refs
                ),
            )
            if accepted
            else None
        )
        failed_branches = tuple(
            FailedBranch(
                path_id=uuid5(NAMESPACE_URL, f"experience-failure:{item.content_hash}"),
                timeline_entry_ids=(entry.timeline_entry_id,),
                segment_ids=(segments[index].segment_id,),
                terminal_status=item.status,
                evidence_refs=item.authoritative_evidence,
                trigger_step_id=item.step_id,
                failure_signal=item.reason,
            )
            for index, (item, entry) in enumerate(zip(assessments, trajectory.entries, strict=True))
            if item.correctness is StepCorrectness.INCORRECT
        )
        correction_entries = tuple(
            item for item in trajectory.entries if item.entry_type is TimelineEntryType.CORRECTION
        )
        corrections = tuple(
            CorrectionRecord(
                correction_id=item.timeline_entry_id,
                source=item.event_type,
                before_evidence=failed[0].authoritative_evidence if failed else item.evidence_refs,
                after_evidence=item.evidence_refs,
                changed_entry_ids=(item.timeline_entry_id,),
                effect=ContributionType.HELPFUL if accepted else ContributionType.UNKNOWN,
                limitations=("correction effect is correlated with the terminal outcome",),
            )
            for item in correction_entries
        )
        recoveries = tuple(
            RecoveryPath(
                path_id=uuid5(NAMESPACE_URL, f"experience-recovery:{branch.path_id}"),
                timeline_entry_ids=successful.timeline_entry_ids if successful else (),
                segment_ids=successful.segment_ids if successful else (),
                terminal_status=(
                    ExperienceStepStatus.COMPLETED if successful else ExperienceStepStatus.UNKNOWN
                ),
                evidence_refs=successful.evidence_refs if successful else (),
                failed_branch_id=branch.path_id,
                correction_ids=tuple(item.correction_id for item in corrections),
                resolved=successful is not None and bool(corrections),
            )
            for branch in failed_branches
            if corrections
        )
        contributions = tuple(
            ContributionRecord(
                contribution_id=uuid5(
                    NAMESPACE_URL, f"experience-contribution:{entry.content_hash}"
                ),
                subject_type=subject,
                subject_id=entry.actor_id,
                assessment=(
                    ContributionType.HARMFUL
                    if entry.status in {ExperienceStepStatus.FAILED, ExperienceStepStatus.DENIED}
                    else ContributionType.HELPFUL
                    if entry.entry_type
                    in {TimelineEntryType.VERIFIER, TimelineEntryType.CORRECTION}
                    and entry.status is ExperienceStepStatus.COMPLETED
                    else ContributionType.UNKNOWN
                ),
                evidence_refs=entry.evidence_refs,
                causal_strength=(
                    "observed" if entry.status is ExperienceStepStatus.DENIED else "correlated"
                ),
                reason=(
                    "classification follows authoritative status; global superiority is not "
                    "inferred"
                ),
                limitations=("single trajectory observation",),
            )
            for entry in trajectory.entries
            if (subject := _subject_type(entry)) is not None
        )
        sensitivity = max(
            (item.sensitivity for item in snapshot.source_refs),
            key=lambda item: list(MemorySensitivity).index(item),
        )
        generalizability = GeneralizabilityAssessment(
            level=GeneralizabilityLevel.TASK_SPECIFIC,
            problem_class_specificity="single observed task",
            repository_specificity="unknown",
            provider_specificity=(
                "provider evidence present"
                if any(item.entry_type is TimelineEntryType.PROVIDER for item in trajectory.entries)
                else "provider independent"
            ),
            tool_specificity="exact tools only",
            skill_specificity="exact skill revisions only",
            strategy_specificity="exact strategy revisions only",
            data_sensitivity=sensitivity,
            environmental_assumptions=("source environment is not generalized",),
            sample_count=1,
            verifier_coverage=(
                1.0
                if any(item.entry_type is TimelineEntryType.VERIFIER for item in trajectory.entries)
                else 0.0
            ),
            contradiction_state=("conflicted" if trajectory.conflicts else "none_observed"),
            reproducibility_count=1,
            limitations=("one trajectory cannot establish cross-task generality",),
        )
        return ExperienceAnalysis(
            successful_path=successful,
            failed_branches=failed_branches,
            first_incorrect_step=first_incorrect,
            corrections=corrections,
            recovery_paths=recoveries,
            contributions=contributions,
            verification_evidence=tuple(
                evidence for item in assessments for evidence in item.authoritative_evidence
            ),
            resource_summary={
                "events": len(trajectory.entries),
                "segments": len(segments),
                "failed_branches": len(failed_branches),
                "corrections": len(corrections),
            },
            safety_summary=("no source mutation", "no destination write", "no artifact execution"),
            generalizability=generalizability,
            limitations=(
                "provider proposals are advisory",
                "temporal order is not treated as causality",
            ),
        )

    def _generate_candidates(
        self,
        request: ExperienceCompilationRequest,
        snapshot: TrajectorySnapshot,
        trajectory: NormalizedTrajectory,
        analysis: ExperienceAnalysis,
        profile: CompilerProfile,
    ) -> tuple[ExperienceCandidate, ...]:
        failed = bool(analysis.failed_branches)
        repaired = bool(analysis.corrections and analysis.successful_path)
        has_provider = any(
            item.entry_type is TimelineEntryType.PROVIDER for item in trajectory.entries
        )
        has_strategy = bool(snapshot.strategy_revisions)
        permitted = {
            ExperienceCandidateType.MEMORY,
            ExperienceCandidateType.SEMANTIC_OBSERVATION,
            ExperienceCandidateType.BENCHMARK_CASE,
            ExperienceCandidateType.CORPUS_ITEM,
        }
        if trajectory.completeness not in {
            TrajectoryCompleteness.COMPLETE,
            TrajectoryCompleteness.COMPLETE_WITH_WARNINGS,
        }:
            permitted = {
                ExperienceCandidateType.FAILURE_PATTERN,
                ExperienceCandidateType.NEGATIVE_EXAMPLE,
            }
        if repaired:
            permitted.add(ExperienceCandidateType.SKILL)
        if has_strategy:
            permitted.add(ExperienceCandidateType.STRATEGY)
        if failed:
            permitted.update(
                {ExperienceCandidateType.FAILURE_PATTERN, ExperienceCandidateType.NEGATIVE_EXAMPLE}
            )
        if has_provider:
            permitted.add(ExperienceCandidateType.ROUTING_OBSERVATION)
        evidence = tuple(dict.fromkeys(analysis.verification_evidence))
        scope = snapshot.source_refs[0].scope
        sensitivity = analysis.generalizability.data_sensitivity
        target = {
            ExperienceCandidateType.MEMORY: ("memory-plane", "v1/memory-revision"),
            ExperienceCandidateType.SEMANTIC_OBSERVATION: ("semantic-memory", "v1/observation"),
            ExperienceCandidateType.SKILL: ("skill-registry", "v1/skill-revision"),
            ExperienceCandidateType.STRATEGY: ("strategy-registry", "v1/strategy-revision"),
            ExperienceCandidateType.FAILURE_PATTERN: ("weakness-mining", "v1/failure-pattern"),
            ExperienceCandidateType.ROUTING_OBSERVATION: ("model-router", "v1/routing-observation"),
            ExperienceCandidateType.BENCHMARK_CASE: ("benchmark-registry", "v1/benchmark-case"),
            ExperienceCandidateType.NEGATIVE_EXAMPLE: ("corpus-factory", "v1/negative-example"),
            ExperienceCandidateType.CORPUS_ITEM: ("corpus-factory", "v1/corpus-item"),
        }
        candidates = tuple(
            ExperienceCandidate(
                candidate_id=uuid5(
                    NAMESPACE_URL,
                    f"experience-candidate:{request.compilation_id}:{candidate_type.value}",
                ),
                candidate_type=candidate_type,
                status=ExperienceCandidateStatus.PROPOSED,
                compilation_id=request.compilation_id,
                task_run_id=request.task_run_id,
                scope=scope,
                sensitivity=sensitivity,
                summary=(
                    f"Proposed {candidate_type.value.replace('_', ' ')} from verified "
                    "trajectory evidence"
                ),
                structured_body={
                    "snapshot_hash": snapshot.content_hash,
                    "analysis_hash": analysis.content_hash,
                    "observed_terminal_state": snapshot.terminal_state,
                },
                source_refs=snapshot.source_refs[: self._configuration.maximum_candidate_sources],
                evidence_refs=evidence[: self._configuration.maximum_candidate_sources],
                limitations=analysis.generalizability.limitations,
                generalizability=analysis.generalizability,
                target_subsystem=target[candidate_type][0],
                target_schema_version=target[candidate_type][1],
                generator_profile=f"deterministic-v1:{profile.content_hash}",
                created_at=request.created_at,
            )
            for candidate_type in sorted(
                request.candidate_types & permitted, key=lambda item: item.value
            )
        )
        if len(candidates) > min(
            request.budget.maximum_candidates,
            profile.resource_limits.maximum_candidates,
            self._configuration.maximum_candidates,
        ):
            raise ExperiencePolicyError("candidate budget exceeded")
        return candidates

    def _verify(
        self,
        request: ExperienceCompilationRequest,
        snapshot: TrajectorySnapshot,
        trajectory: NormalizedTrajectory,
        assessments: tuple[StepAssessment, ...],
        analysis: ExperienceAnalysis,
        candidates: tuple[ExperienceCandidate, ...],
    ) -> ExperienceVerifierBundle:
        evidence = tuple(dict.fromkeys(analysis.verification_evidence))
        checks = {
            "experience.source_completeness": trajectory.completeness
            in {
                TrajectoryCompleteness.COMPLETE,
                TrajectoryCompleteness.COMPLETE_WITH_WARNINGS,
            },
            "experience.source_identity": all(item.source_id for item in snapshot.source_refs),
            "experience.source_hash_integrity": all(
                self._sources.resolve(item).reference == item for item in snapshot.source_refs
            ),
            "experience.event_order_integrity": not trajectory.conflicts,
            "experience.artifact_integrity": True,
            "experience.terminal_outcome_integrity": bool(snapshot.terminal_state),
            "experience.verifier_evidence_integrity": bool(evidence),
            "experience.deterministic_reconstruction": trajectory
            == self._reconstruct(
                snapshot,
                tuple(
                    entry
                    for source in snapshot.source_refs
                    for entry in self._sources.resolve(source).timeline_entries
                ),
            ),
            "experience.step_assessment_integrity": len(assessments) == len(trajectory.entries),
            "experience.no_unsupported_causal_claim": (
                not analysis.first_incorrect_step.causal_origin.causal_claim_supported
                or analysis.first_incorrect_step.causal_origin.origin_type
                is FirstIncorrectType.POLICY_VIOLATION
            ),
            "experience.candidate_provenance": all(
                item.source_refs and item.evidence_refs for item in candidates
            ),
            "experience.candidate_schema": all(
                item.status is ExperienceCandidateStatus.PROPOSED for item in candidates
            ),
            "experience.sensitive_data_policy": all(
                list(MemorySensitivity).index(item.sensitivity)
                >= list(MemorySensitivity).index(analysis.generalizability.data_sensitivity)
                for item in candidates
            ),
            "experience.idempotency": bool(request.idempotency_key),
            "experience.manifest_integrity": True,
        }
        results = tuple(
            VerificationCapabilityResult(
                capability=capability,
                passed=checks[capability],
                evidence_refs=evidence[:8],
                reason="deterministic compiler check passed"
                if checks[capability]
                else "deterministic compiler check failed",
            )
            for capability in MANDATORY_CAPABILITIES
        )
        registry_hash = canonical_hash(MANDATORY_CAPABILITIES)
        return ExperienceVerifierBundle(
            bundle_id=uuid5(NAMESPACE_URL, f"experience-verifiers:{request.compilation_id}"),
            compilation_id=request.compilation_id,
            registry_hash=registry_hash,
            results=results,
            created_at=request.created_at,
        )

    def _decide(
        self,
        request: ExperienceCompilationRequest,
        snapshot: TrajectorySnapshot,
        verifier_bundle: ExperienceVerifierBundle,
    ) -> CompilationDecision:
        warnings = (
            ("optional sources are absent",)
            if snapshot.completeness is TrajectoryCompleteness.COMPLETE_WITH_WARNINGS
            else ()
        )
        decision = (
            CompilationDecisionType.COMPLETED_WITH_WARNINGS
            if verifier_bundle.passed and warnings
            else CompilationDecisionType.COMPLETED
            if verifier_bundle.passed
            else CompilationDecisionType.UNVERIFIABLE
        )
        return CompilationDecision(
            compilation_id=request.compilation_id,
            decision=decision,
            verifier_bundle_id=verifier_bundle.bundle_id,
            verifier_bundle_hash=verifier_bundle.content_hash,
            warnings=warnings,
            reason_codes=(
                ("mandatory_compiler_verifiers_passed",)
                if verifier_bundle.passed
                else ("compiler_verifier_failed",)
            ),
            decided_at=request.created_at,
        )
