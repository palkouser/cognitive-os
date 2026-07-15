"""Python Coding Agent orchestration facade over existing Cognitive OS services."""

from __future__ import annotations

from time import monotonic
from typing import cast
from uuid import UUID, uuid4

from cognitive_os.application.services.tool_execution import ToolExecutionService
from cognitive_os.domain.coding import (
    CodingLimits,
    CodingOutcome,
    CodingOutcomeStatus,
    CodingProblemExtension,
    PatchApplicationResult,
    PatchAttempt,
    PatchAttemptStatus,
    RepositoryProfileStatus,
    RiskRecord,
    WorkspaceDisposition,
    WorkspaceRequest,
)
from cognitive_os.domain.common import JsonValue, utc_now
from cognitive_os.domain.tools import ToolExecutionContext, ToolExecutionStatus, ToolInvocation
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.coding_events import (
    CodingPatchApplied,
    CodingPatchAttemptRecorded,
    CodingPatchPlanCreated,
    CodingPatchRejected,
    CodingRepositoryIndexCreated,
    CodingRepositoryProfileDetected,
    CodingRepositoryProfileRejected,
    CodingResultPackaged,
    CodingWorkspaceArchived,
    CodingWorkspacePrepared,
)
from cognitive_os.infrastructure.repository.git_repository import GitRepositoryService
from cognitive_os.tools.registry import ToolRegistry
from cognitive_os.tools.workspace import build_workspace_tools

from .indexing import RepositoryIndexer
from .patching import PatchService
from .provider import CodingProviderService
from .repository_profile import detect_repository_profile
from .verification import CodingVerifierBundleFactory
from .workspace import WorkspaceManager


class CodingAgentFacade:
    """Domain facade; it deliberately defines no second general controller state machine."""

    def __init__(
        self,
        *,
        repositories: GitRepositoryService,
        workspaces: WorkspaceManager,
        indexer: RepositoryIndexer,
        patches: PatchService,
        provider: CodingProviderService,
        verifier_bundle: CodingVerifierBundleFactory,
        tool_registry: ToolRegistry,
        tool_execution: ToolExecutionService,
        events: CodingEventService,
        limits: CodingLimits,
        rootless_docker: bool,
    ) -> None:
        self.repositories = repositories
        self.workspaces = workspaces
        self.indexer = indexer
        self.patches = patches
        self.provider = provider
        self.verifier_bundle = verifier_bundle
        self.tool_registry = tool_registry
        self.tool_execution = tool_execution
        self.events = events
        self.limits = limits
        self.rootless_docker = rootless_docker

    async def run(self, task_run_id: UUID, problem: CodingProblemExtension) -> CodingOutcome:
        started = monotonic()
        profile = detect_repository_profile(
            problem.repository_path, rootless_docker=self.rootless_docker
        )
        await self.events.append(
            task_run_id,
            CodingRepositoryProfileDetected(task_run_id=task_run_id, profile=profile),
            correlation_id=task_run_id,
        )
        if profile.status is RepositoryProfileStatus.PROFILE_MISMATCH:
            await self.events.append(
                task_run_id,
                CodingRepositoryProfileRejected(
                    task_run_id=task_run_id, profile=profile, rejected_at=utc_now()
                ),
                correlation_id=task_run_id,
            )
            return await self._package(
                task_run_id,
                problem,
                profile,
                CodingOutcomeStatus.REJECTED,
                started,
                policy_denials=tuple(item.reason_code for item in profile.mismatches),
            )

        reference = await self.repositories.validate(problem.repository_path, problem.base_commit)
        main_head = await self.repositories.head(problem.repository_path)
        main_status = await self.repositories.status(problem.repository_path)
        workspace = await self.workspaces.prepare(
            WorkspaceRequest(
                task_run_id=task_run_id,
                repository=reference,
                idempotency_key=problem.canonical_hash(),
            )
        )
        await self.events.append(
            task_run_id,
            CodingWorkspacePrepared(descriptor=workspace),
            correlation_id=task_run_id,
        )
        tools = build_workspace_tools(workspace, self.workspaces, self.patches, self.repositories)
        self.tool_registry.register_many(tools)
        self.tool_registry.freeze()
        patch_attempts: list[PatchAttempt] = []
        policy_denials: list[str] = []
        decision = None
        verification = None
        manifest = None
        outcome_status = CodingOutcomeStatus.FAILED
        risk_records: list[RiskRecord] = []
        try:
            root = self.workspaces.path_for(workspace)
            index = self.indexer.build(root, workspace.base_commit, workspace.workspace_revision)
            await self.events.append(
                task_run_id,
                CodingRepositoryIndexCreated(
                    task_run_id=task_run_id,
                    index_hash=index.canonical_hash(),
                    file_count=len(index.files),
                    truncated=index.truncated,
                ),
                correlation_id=task_run_id,
            )
            context = self.indexer.context(
                index,
                profile.model_dump(mode="json"),
                (),
            )
            plan = await self.provider.plan(
                task_run_id,
                problem,
                profile,
                context,
                tuple(item.descriptor for item in tools),
            )
            await self.events.append(
                task_run_id,
                CodingPatchPlanCreated(
                    task_run_id=task_run_id,
                    plan=plan,
                    plan_hash=plan.canonical_hash(),
                ),
                correlation_id=task_run_id,
            )
            repair_context: dict[str, JsonValue] = {}
            for attempt_number in range(1, self.limits.maximum_patch_attempts + 1):
                repair_cycle = attempt_number - 1
                proposal = await self.provider.propose(
                    task_run_id,
                    problem,
                    profile,
                    context,
                    plan,
                    tuple(item.descriptor for item in tools),
                    workspace_revision=workspace.workspace_revision,
                    repair_context=repair_context,
                )
                proposal_hash = proposal.canonical_hash()
                await self.events.append(
                    task_run_id,
                    CodingPatchAttemptRecorded(
                        task_run_id=task_run_id,
                        attempt_number=attempt_number,
                        proposal_hash=proposal_hash,
                        recorded_at=utc_now(),
                    ),
                    correlation_id=task_run_id,
                )
                result = await self._apply_through_tool_plane(task_run_id, proposal)
                attempt_status = (
                    PatchAttemptStatus.APPLIED if result.applied else PatchAttemptStatus.REJECTED
                )
                patch_attempts.append(
                    PatchAttempt(
                        attempt_number=attempt_number,
                        repair_cycle=repair_cycle,
                        proposal_hash=proposal_hash,
                        status=attempt_status,
                        application_result=result,
                        recorded_at=utc_now(),
                    )
                )
                if not result.applied:
                    reason = result.reason_code or "patch_rejected"
                    policy_denials.append(reason)
                    await self.events.append(
                        task_run_id,
                        CodingPatchRejected(
                            task_run_id=task_run_id,
                            attempt_number=attempt_number,
                            reason_code=reason,
                            rejected_at=utc_now(),
                        ),
                        correlation_id=task_run_id,
                    )
                    outcome_status = CodingOutcomeStatus.REJECTED
                    break
                manifest = result.manifest
                if manifest is None:
                    raise RuntimeError("applied patch result is missing its changed-file manifest")
                workspace = workspace.model_copy(
                    update={"workspace_revision": result.workspace_revision}
                )
                await self.events.append(
                    task_run_id,
                    CodingPatchApplied(
                        task_run_id=task_run_id,
                        workspace_id=workspace.workspace_id,
                        workspace_revision=workspace.workspace_revision,
                        manifest=manifest,
                    ),
                    correlation_id=task_run_id,
                )
                main_unchanged = (
                    await self.repositories.head(problem.repository_path) == main_head
                    and await self.repositories.status(problem.repository_path) == main_status
                )
                if not main_unchanged:
                    outcome_status = CodingOutcomeStatus.SECURITY_FAILURE
                    risk_records.append(
                        RiskRecord(
                            code="main_tree_integrity_failure",
                            message="The main working tree changed during coding execution.",
                            severity="critical",
                        )
                    )
                    break
                evidence = self._evidence(manifest, workspace.base_commit, main_unchanged)
                verified = await self.verifier_bundle.verify(
                    task_run_id=task_run_id,
                    approved_workspace=str(root),
                    changed_file_evidence=evidence[0],
                    diff_evidence=evidence[1],
                    dependency_evidence=evidence[2],
                    integrity_evidence=evidence[3],
                    repair_budget_remaining=(
                        repair_cycle < self.limits.maximum_repair_cycles
                        and attempt_number < self.limits.maximum_patch_attempts
                    ),
                )
                verification, decision = verified.summary, verified.decision
                if decision.decision.value == "accepted":
                    outcome_status = CodingOutcomeStatus.ACCEPTED
                    break
                if (
                    decision.decision.value != "needs_repair"
                    or repair_cycle >= self.limits.maximum_repair_cycles
                ):
                    outcome_status = CodingOutcomeStatus.FAILED
                    break
                current_diff = await self.repositories.diff(root, workspace.base_commit)
                repair_context = {
                    "previous_proposal_hash": proposal_hash,
                    "current_diff": current_diff[:200_000],
                    "acceptance_reason": decision.reason,
                    "remaining_attempts": self.limits.maximum_patch_attempts - attempt_number,
                }
            if len(patch_attempts) >= self.limits.maximum_patch_attempts and decision is None:
                outcome_status = CodingOutcomeStatus.BUDGET_EXHAUSTED
        except Exception as error:
            outcome_status = CodingOutcomeStatus.FAILED
            risk_records.append(
                RiskRecord(
                    code="coding_execution_error",
                    message=(
                        f"Coding execution stopped safely: {type(error).__name__}: "
                        f"{str(error)[:500]}"
                    ),
                    severity="high",
                )
            )
        finally:
            try:
                cleanup = await self.workspaces.cleanup(
                    workspace, disposition=WorkspaceDisposition.ARCHIVE
                )
                await self.events.append(
                    task_run_id,
                    CodingWorkspaceArchived(result=cleanup),
                    correlation_id=task_run_id,
                )
            except Exception as cleanup_error:
                risk_records.append(
                    RiskRecord(
                        code="workspace_cleanup_error",
                        message=(
                            "Workspace cleanup requires operator review: "
                            f"{type(cleanup_error).__name__}"
                        ),
                        severity="high",
                    )
                )
        return await self._package(
            task_run_id,
            problem,
            profile,
            outcome_status,
            started,
            patch_attempts=tuple(patch_attempts),
            manifest=manifest,
            verification=verification,
            decision=decision,
            policy_denials=tuple(policy_denials),
            risks=tuple(risk_records),
        )

    async def _apply_through_tool_plane(
        self, task_run_id: UUID, proposal: object
    ) -> PatchApplicationResult:
        from cognitive_os.domain.coding import PatchProposal

        if not isinstance(proposal, PatchProposal):
            raise TypeError("patch proposal contract is required")
        invocation = ToolInvocation(
            tool_call_id=uuid4(),
            task_run_id=task_run_id,
            correlation_id=task_run_id,
            tool_id="workspace.apply_patch",
            tool_version="1",
            arguments=proposal.model_dump(mode="json"),
            requested_at=utc_now(),
            requested_by="python-coding-agent",
        )
        result = await self.tool_execution.execute(
            invocation,
            ToolExecutionContext(
                workspace="active-coding-workspace",
                timeout_seconds=30,
                maximum_stdout_bytes=1_000_000,
                maximum_stderr_bytes=1_000_000,
                maximum_artifact_bytes=2_000_000,
            ),
        )
        if result.status is not ToolExecutionStatus.COMPLETED or not isinstance(
            result.result, dict
        ):
            raise RuntimeError("workspace patch Tool Plane invocation did not complete")
        return PatchApplicationResult.model_validate(result.result)

    @staticmethod
    def _evidence(
        manifest: object, base_commit: str, main_unchanged: bool
    ) -> tuple[
        dict[str, JsonValue],
        dict[str, JsonValue],
        dict[str, JsonValue],
        dict[str, JsonValue],
    ]:
        from cognitive_os.domain.coding import ChangedFileManifest

        if not isinstance(manifest, ChangedFileManifest):
            raise TypeError("changed-file manifest is required")
        paths = [item.path for item in manifest.files]
        files = [
            {
                "path": item.path,
                "size_bytes": 0,
                "symlink": False,
                "binary": False,
            }
            for item in manifest.files
        ]
        return (
            {"files": cast(JsonValue, files)},
            {
                "paths": cast(JsonValue, paths),
                "line_count": manifest.total_diff_lines,
                "binary_patch": False,
                "mode_change": False,
                "submodule_change": False,
                "deleted_paths": cast(
                    JsonValue,
                    [item.path for item in manifest.files if item.change_type.value == "deleted"],
                ),
            },
            {
                "before_direct": [],
                "after_direct": [],
                "optional_to_core": [],
                "widened_requirements": [],
            },
            {
                "workspace_head": base_commit,
                "base_commit": base_commit,
                "main_head_unchanged": main_unchanged,
                "main_status_unchanged": main_unchanged,
                "git_admin_unchanged": main_unchanged,
            },
        )

    async def _package(
        self,
        task_run_id: UUID,
        problem: CodingProblemExtension,
        profile: object,
        status: CodingOutcomeStatus,
        started: float,
        *,
        patch_attempts: tuple[PatchAttempt, ...] = (),
        manifest: object = None,
        verification: object = None,
        decision: object = None,
        policy_denials: tuple[str, ...] = (),
        risks: tuple[RiskRecord, ...] = (),
    ) -> CodingOutcome:
        from cognitive_os.domain.acceptance import AcceptanceDecision
        from cognitive_os.domain.coding import ChangedFileManifest, CodingVerificationSummary
        from cognitive_os.domain.coding import RepositoryProfile as Profile

        outcome = CodingOutcome(
            task_run_id=task_run_id,
            status=status,
            repository_profile=profile
            if isinstance(profile, Profile)
            else Profile.model_validate(profile),
            base_commit=problem.base_commit,
            patch_attempts=patch_attempts,
            changed_files=manifest if isinstance(manifest, ChangedFileManifest) else None,
            verification=(
                verification if isinstance(verification, CodingVerificationSummary) else None
            ),
            acceptance_decision=decision if isinstance(decision, AcceptanceDecision) else None,
            provider_calls=len(patch_attempts) + (1 if patch_attempts else 0),
            tool_calls=len(patch_attempts),
            elapsed_seconds=monotonic() - started,
            policy_denials=policy_denials,
            risks=risks,
            workspace_disposition=WorkspaceDisposition.ARCHIVE,
            completed_at=utc_now(),
        )
        await self.events.append(
            task_run_id,
            CodingResultPackaged(
                task_run_id=task_run_id,
                outcome_hash=outcome.canonical_hash(),
                status=outcome.status.value,
                packaged_at=outcome.completed_at,
            ),
            correlation_id=task_run_id,
        )
        return outcome
