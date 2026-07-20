"""Credential-free Experience Compiler fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.domain.experience import (
    CompilerProfile,
    CompilerResourceLimits,
    ExperienceCandidateType,
    ExperienceCompilationRequest,
    ExperienceStepStatus,
    TimelineEntry,
    TimelineEntryType,
    TrajectorySourceRef,
    TrajectorySourceType,
)
from cognitive_os.domain.memory import MemorySensitivity

from .registry import (
    CompilerProfileRegistry,
    ResolvedTrajectorySource,
    SourceResolverRegistry,
)

FIXTURE_TIME = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)

INITIAL_FIXTURES = (
    "direct-success",
    "repaired-bug-fix",
    "failed-strategy",
    "cancelled",
    "clarification-first",
    "provider-fallback",
    "unsafe-tool-request",
    "context-retrieval-failure",
    "conflicting-verifier",
    "incomplete-history",
)


def _id(kind: str, name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"sprint14:{kind}:{name}")


def _reference(
    name: str,
    source_type: TrajectorySourceType,
    payload: bytes,
    *,
    revision: str = "1",
    required: bool = True,
) -> TrajectorySourceRef:
    event_stream = source_type is TrajectorySourceType.CONTROLLER_EVENT
    return TrajectorySourceRef(
        source_type=source_type,
        source_id=f"{name}:{source_type.value}",
        source_revision=revision,
        event_stream_id=_id("stream", name) if event_stream else None,
        event_stream_version=12 if event_stream else None,
        source_content_hash=sha256(payload).hexdigest(),
        scope="project:cognitive-os",
        sensitivity=MemorySensitivity.INTERNAL,
        required=required,
    )


def _entry(
    name: str,
    reference: TrajectorySourceRef,
    sequence: int,
    entry_type: TimelineEntryType,
    event_type: str,
    status: ExperienceStepStatus,
    summary: str,
) -> TimelineEntry:
    evidence = sha256(f"{name}:{sequence}:{event_type}:{status.value}".encode()).hexdigest()
    return TimelineEntry(
        timeline_entry_id=_id("entry", f"{name}:{sequence}:{event_type}"),
        sequence=sequence,
        source_ref=reference,
        entry_type=entry_type,
        event_type=event_type,
        actor_type="system",
        actor_id=f"fixture-{entry_type.value}",
        step_id=f"step-{sequence}",
        started_at=FIXTURE_TIME + timedelta(seconds=sequence),
        finished_at=FIXTURE_TIME + timedelta(seconds=sequence, milliseconds=100),
        correlation_id=_id("correlation", name),
        status=status,
        payload_summary=summary,
        evidence_refs=(evidence,),
    )


def build_fixture(
    name: str,
) -> tuple[ExperienceCompilationRequest, SourceResolverRegistry, CompilerProfileRegistry]:
    if name not in INITIAL_FIXTURES and not name.startswith("seed-"):
        raise ValueError(f"unknown Experience Compiler fixture: {name}")
    template = (
        INITIAL_FIXTURES[int(name.split("-")[1]) % len(INITIAL_FIXTURES)]
        if name.startswith("seed-")
        else name
    )
    task_payload = f"task:{name}".encode()
    task_ref = _reference(name, TrajectorySourceType.TASK, task_payload)
    controller_payload = f"controller:{name}".encode()
    controller_ref = _reference(name, TrajectorySourceType.CONTROLLER_EVENT, controller_payload)
    verifier_payload = f"verifier:{name}".encode()
    verifier_ref = _reference(name, TrajectorySourceType.VERIFIER, verifier_payload)
    acceptance_payload = f"acceptance:{name}".encode()
    acceptance_ref = _reference(name, TrajectorySourceType.ACCEPTANCE, acceptance_payload)

    entries: list[TimelineEntry] = [
        _entry(
            name,
            controller_ref,
            1,
            TimelineEntryType.PLAN,
            "plan.created",
            ExperienceStepStatus.COMPLETED,
            "Bounded plan created",
        )
    ]
    terminal_state = "accepted"
    sequence = 2
    extra_sources: list[ResolvedTrajectorySource] = []

    if template in {"provider-fallback", "repaired-bug-fix"}:
        provider_payload = f"provider:{name}".encode()
        provider_ref = _reference(name, TrajectorySourceType.PROVIDER_CALL, provider_payload)
        entries.append(
            _entry(
                name,
                provider_ref,
                sequence,
                TimelineEntryType.PROVIDER,
                "provider.call_failed" if template == "provider-fallback" else "provider.proposal",
                (
                    ExperienceStepStatus.FAILED
                    if template == "provider-fallback"
                    else ExperienceStepStatus.COMPLETED
                ),
                "Provider result retained as untrusted evidence",
            )
        )
        sequence += 1
        extra_sources.append(
            ResolvedTrajectorySource(provider_ref, provider_payload, (entries[-1],))
        )

    if template in {"repaired-bug-fix", "unsafe-tool-request"}:
        tool_payload = f"tool:{name}".encode()
        tool_ref = _reference(name, TrajectorySourceType.TOOL_CALL, tool_payload)
        denied = template == "unsafe-tool-request"
        entries.append(
            _entry(
                name,
                tool_ref,
                sequence,
                TimelineEntryType.TOOL,
                "tool.policy_violation" if denied else "tool.postcondition_failed",
                ExperienceStepStatus.DENIED if denied else ExperienceStepStatus.FAILED,
                "Unsafe tool request denied" if denied else "Initial patch failed verification",
            )
        )
        sequence += 1
        extra_sources.append(ResolvedTrajectorySource(tool_ref, tool_payload, (entries[-1],)))

    if template in {"repaired-bug-fix", "clarification-first", "provider-fallback"}:
        correction_payload = f"correction:{name}".encode()
        correction_ref = _reference(
            name, TrajectorySourceType.USER_CORRECTION, correction_payload, required=False
        )
        entries.append(
            _entry(
                name,
                correction_ref,
                sequence,
                TimelineEntryType.CORRECTION,
                "user.correction_received"
                if template != "provider-fallback"
                else "provider.fallback_applied",
                ExperienceStepStatus.COMPLETED,
                "Bounded correction or fallback applied",
            )
        )
        sequence += 1
        extra_sources.append(
            ResolvedTrajectorySource(correction_ref, correction_payload, (entries[-1],))
        )

    if template == "failed-strategy":
        strategy_payload = f"strategy:{name}".encode()
        strategy_ref = _reference(name, TrajectorySourceType.STRATEGY_REVISION, strategy_payload)
        entries.append(
            _entry(
                name,
                strategy_ref,
                sequence,
                TimelineEntryType.STRATEGY,
                "strategy.execution_failed",
                ExperienceStepStatus.FAILED,
                "Exact strategy revision failed",
            )
        )
        sequence += 1
        terminal_state = "failed"
        extra_sources.append(
            ResolvedTrajectorySource(strategy_ref, strategy_payload, (entries[-1],))
        )

    if template == "context-retrieval-failure":
        context_payload = f"context:{name}".encode()
        context_ref = _reference(name, TrajectorySourceType.CONTEXT, context_payload)
        entries.append(
            _entry(
                name,
                context_ref,
                sequence,
                TimelineEntryType.CONTEXT,
                "context.stale_source",
                ExperienceStepStatus.FAILED,
                "Required Context Bundle was stale",
            )
        )
        sequence += 1
        terminal_state = "failed"
        extra_sources.append(ResolvedTrajectorySource(context_ref, context_payload, (entries[-1],)))

    if template == "cancelled":
        terminal_state = "cancelled"
        entries.append(
            _entry(
                name,
                controller_ref,
                sequence,
                TimelineEntryType.CANCELLATION,
                "controller.cancelled",
                ExperienceStepStatus.CANCELLED,
                "Operator cancellation retained partial work",
            )
        )
        sequence += 1

    verifier_status = (
        ExperienceStepStatus.FAILED
        if template in {"failed-strategy", "context-retrieval-failure"}
        else ExperienceStepStatus.COMPLETED
    )
    verifier_sequence = sequence + 1 if template == "incomplete-history" else sequence
    entries.append(
        _entry(
            name,
            verifier_ref,
            verifier_sequence,
            TimelineEntryType.VERIFIER,
            "verifier.failed"
            if verifier_status is ExperienceStepStatus.FAILED
            else "verifier.completed",
            verifier_status,
            "Required verifier result",
        )
    )
    sequence = verifier_sequence + 1
    if template == "conflicting-verifier":
        entries.append(
            _entry(
                name,
                verifier_ref,
                verifier_sequence,
                TimelineEntryType.VERIFIER,
                "verifier.conflicting_result",
                ExperienceStepStatus.FAILED,
                "Conflicting verifier evidence retained",
            )
        )
        terminal_state = "unverifiable"
    entries.append(
        _entry(
            name,
            acceptance_ref,
            sequence,
            TimelineEntryType.ACCEPTANCE,
            f"acceptance.{terminal_state}",
            (
                ExperienceStepStatus.COMPLETED
                if terminal_state == "accepted"
                else ExperienceStepStatus.CANCELLED
                if terminal_state == "cancelled"
                else ExperienceStepStatus.FAILED
            ),
            f"Terminal outcome: {terminal_state}",
        )
    )

    controller_entries = tuple(item for item in entries if item.source_ref == controller_ref)
    verifier_entries = tuple(item for item in entries if item.source_ref == verifier_ref)
    acceptance_entries = tuple(item for item in entries if item.source_ref == acceptance_ref)
    resolved = [
        ResolvedTrajectorySource(task_ref, task_payload),
        ResolvedTrajectorySource(
            controller_ref, controller_payload, controller_entries, terminal_state
        ),
        ResolvedTrajectorySource(verifier_ref, verifier_payload, verifier_entries),
        ResolvedTrajectorySource(acceptance_ref, acceptance_payload, acceptance_entries),
        *extra_sources,
    ]
    sources = SourceResolverRegistry()
    for item in resolved:
        sources.register(item)
    sources.freeze()
    refs = tuple(item.reference for item in resolved)
    source_types = frozenset(item.source_type for item in refs)
    profile = CompilerProfile(
        profile_id="sprint14-default",
        version=1,
        enabled_source_types=source_types,
        required_source_types=frozenset(
            {
                TrajectorySourceType.TASK,
                TrajectorySourceType.CONTROLLER_EVENT,
                TrajectorySourceType.VERIFIER,
                TrajectorySourceType.ACCEPTANCE,
            }
        ),
        candidate_types=frozenset(ExperienceCandidateType),
        assessment_policy="conservative-evidence-v1",
        contribution_policy="no-causal-overclaim-v1",
        generalizability_policy="minimum-specificity-v1",
        resource_limits=CompilerResourceLimits(),
        created_at=FIXTURE_TIME,
    )
    profiles = CompilerProfileRegistry()
    profiles.register(profile)
    profiles.freeze()
    request = ExperienceCompilationRequest(
        compilation_id=_id("compilation", name),
        task_run_id=_id("task-run", name),
        trajectory_sources=refs,
        compiler_profile_id=profile.profile_id,
        compiler_profile_version=profile.version,
        compiler_profile_hash=profile.content_hash,
        candidate_types=frozenset(ExperienceCandidateType),
        budget=CompilerResourceLimits(),
        requested_by="fixture-operator",
        idempotency_key=sha256(f"sprint14:{name}".encode()).hexdigest(),
        created_at=FIXTURE_TIME,
    )
    return request, sources, profiles
