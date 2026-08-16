"""S22E-300: the one approved change, carried through the whole governed chain.

**What the gate owner selected, and why this driver exists.** S22E-201 decision two selects
ledger entry **L7** — 22E's own W1-F7 — as the sprint's single approved change, because no
selection can fully close Gate M this sprint and L7 is the one that makes §2.2(b)'s chain
walkable for every successor. This driver mines that entry, turns it into a provider-assisted
candidate, evaluates it under the full released matrix in a real worktree, and stops in front
of a human.

**The installing traversal's exception, stated here rather than discovered later.** §2.2(b)
requires the approved change to be a *provider-assisted candidate*. The defect being repaired
is exactly what makes that mark unreachable, so the traversal that installs the repair cannot
be held to the repaired behaviour — it runs against the unrepaired active checkout, where
`merge_provider_draft` still returns an unsealed revision and the caller must reseal. Decision
one names this exception; the record carries it as a field, not as prose. Every *later*
traversal gets the mark for free, which is the point of spending the change here.

**Where the human is, and why the driver cannot move past them.** Without `--approver` the run
stops after `assess_candidate` and records the assessment with the approval withheld. The gate
owner reads that record and re-runs with `--approver`, which is the only way `approve_promotion`
is ever called. The evaluation matrix therefore runs twice, once per invocation, and that is
deliberate: an approval granted against gate results replayed from a file is an approval
granted against a file. 22D W4-F1's rule gets a second, independent execution of every gate for
free.

**What this driver does not do.** It does not merge, tag, push or release. The released
`PromotionBundle` says so in its own required manual steps, and §2.3 forbids it independently.
The bundle is the loop's output; the operator carries it to `main`.

    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/approved_change_22e.py
    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/approved_change_22e.py \
        --approver <named user>
    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/approved_change_22e.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

OUTPUT = EVIDENCE / "sprint-22e-w3-approved-change.json"
ENTRY_ID = "L7"
W3_TIME = "2026-08-16T00:00:00Z"

#: The experiment's isolation approver. `approve_promotion` refuses when the promotion approver
#: is this same actor, which is the released two-actor rule and the reason the gate owner's name
#: has to arrive from the command line rather than from a constant in this file.
ISOLATION_APPROVER = "s22e-isolation-approver"

#: The regression test the candidate carries with the repair. It is part of the change, not part
#: of the sprint's evidence, because the defect survived release precisely by not having one:
#: `test_proposal_engine.py` had two provider tests and both asserted a *failure* path.
TEST_FILE = "tests/cognitive_os/proposals/test_proposal_engine.py"

TEST_STEPS: tuple[tuple[str, str], ...] = (
    (
        "class UnavailableProvider:\n"
        "    async def draft(self, source, *, allowed_source_ids):\n"
        '        raise OSError("provider unavailable")\n',
        "class AdmissibleProvider:\n"
        "    async def draft(self, source, *, allowed_source_ids):\n"
        "        return ProviderProposalDraft(\n"
        "            proposal_type=HarnessProposalType.CONTEXT_PROFILE_CHANGE,\n"
        '            summary="Admissible draft",\n'
        '            proposed_body="Narrow the context profile to the cited sources.",\n'
        '            rationale="the cited evidence supports a bounded profile change",\n'
        "            alternative_drafts=(),\n"
        "            affected_component_hints=(source.weakness_record.affected_components[0],),\n"
        '            validation_rationale="run the registered verifiers on the profile",\n'
        '            rollback_rationale="restore the previous profile revision",\n'
        '            limitations=("provider draft",),\n'
        "            cited_host_source_ref_ids=allowed_source_ids,\n"
        "        )\n"
        "\n"
        "\n"
        "class UnavailableProvider:\n"
        "    async def draft(self, source, *, allowed_source_ids):\n"
        '        raise OSError("provider unavailable")\n',
    ),
    (
        "    assert revision.generation_mode is ProposalGenerationMode.DETERMINISTIC\n"
        "    assert (await service.statistics()).provider_fallback_count == 1\n",
        "    assert revision.generation_mode is ProposalGenerationMode.DETERMINISTIC\n"
        "    assert (await service.statistics()).provider_fallback_count == 1\n"
        "\n"
        "\n"
        "@pytest.mark.asyncio\n"
        "async def test_admitted_provider_draft_becomes_a_sealed_provider_assisted_revision()"
        " -> None:\n"
        '    """The provider-assisted success path, which had no test until 22E W1-F7.\n'
        "\n"
        "    Both existing provider tests assert a failure: the unsafe draft must be refused and\n"
        "    the unavailable provider must fall back. So every assertion about this path was an\n"
        "    assertion about how it fails, and the admitted draft returned a revision whose seal\n"
        "    was blank -- `model_copy(update=...)` does not re-run the sealing validator -- which\n"
        "    made the next released statement refuse it against `^[0-9a-f]{64}$`.\n"
        '    """\n'
        "    source = await fixture_proposal_source()\n"
        "    service = HarnessProposalService(\n"
        "        InMemoryProposalRepository(),\n"
        "        source,\n"
        "        configuration=ProposalConfiguration(\n"
        "            generation=ProposalGenerationConfiguration(provider_assisted_enabled=True)\n"
        "        ),\n"
        "        provider=AdmissibleProvider(),\n"
        "    )\n"
        "    revision = await service.create_from_weakness(\n"
        "        source.revision.weakness_id,\n"
        "        source.revision.revision,\n"
        "        HarnessProposalType.CONTEXT_PROFILE_CHANGE,\n"
        '        actor="operator",\n'
        "        created_at=FIXTURE_TIME,\n"
        "        provider_assisted=True,\n"
        "    )\n"
        "    assert revision.generation_mode is ProposalGenerationMode.PROVIDER_ASSISTED\n"
        '    assert revision.content_hash == revision.canonical_hash(exclude={"content_hash"})\n',
    ),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def read_selection() -> dict[str, Any]:
    """Read the gate owner's sealed selection, and recompute its seal before obeying it.

    A driver that hard-coded `L7` would be a driver that decides which change is approved. This
    one reads the decision record, checks the seal, and refuses to run against anything else.
    """
    stored = json.loads((EVIDENCE / "sprint-22e-decisions.json").read_text(encoding="utf-8"))
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != stored["integrity_content_hash"]:
        raise ValueError("the decision record does not recompute its own seal")
    selection = stored["decision_two"]["selection"]
    if selection != ENTRY_ID:
        raise ValueError(f"the sealed selection is {selection}, not {ENTRY_ID}")
    return {
        "selection": selection,
        "selection_finding": stored["decision_two"]["selection_finding"],
        "decided_by": stored["decided_by"],
        "decision_record_hash": stored["integrity_content_hash"],
        "walkability_ruling": stored["decision_one"]["ruling"],
    }


def apply_repair_with_its_test(worktree: Path) -> dict[str, Any]:
    """Apply the repair *and* the regression test, every step through `deterministic_replace`.

    W1's `apply_repair` takes one file per entry and three sealed records depend on that shape,
    so this is a second, separately declared application rather than a widening of it (22B
    W1-D2: superseded, never edited). The repair itself is still read from `REPAIR_SPECS['L7']`
    — the same bytes W2's ledger revision sealed a reproduction for.
    """
    from dryrun_22e import REPAIR_SPECS

    from cognitive_os.changes.service import deterministic_replace

    applied = []
    for file, steps in (
        (REPAIR_SPECS[ENTRY_ID]["file"], REPAIR_SPECS[ENTRY_ID]["steps"]),
        (TEST_FILE, TEST_STEPS),
    ):
        target = worktree / file
        original = target.read_bytes()
        content = original
        for before, after in steps:
            content = deterministic_replace(
                content, before.encode(), after.encode(), _sha256(content)
            )
        target.write_bytes(content)
        applied.append(
            {
                "file": file,
                "steps": len(steps),
                "before_hash": _sha256(original),
                "after_hash": _sha256(content),
                "bytes_changed": len(content) - len(original),
            }
        )
    return {
        "applied_by": "cognitive_os.changes.service.deterministic_replace",
        "files": applied,
        "changed_files": tuple(item["file"] for item in applied),
        "the_change_carries_its_own_test": True,
        "the_provider_did_not_write_this": (
            "no released provider configuration in this repository can write a file, and "
            "merge_provider_draft refuses a draft carrying a patch; the host applied the "
            "change and the provider advised on the proposal"
        ),
    }


def run_focused_regression(worktree: Path) -> dict[str, Any]:
    """The candidate's own test file, run in the worktree, before the matrix runs anything.

    Separate from the matrix's `focused_target_tests` gate on purpose: this measures the test
    the candidate *adds*, and a candidate whose own new test does not run is not a candidate.
    """
    import subprocess

    from isolation_22e import gate_environment

    completed = subprocess.run(
        ["uv", "run", "--all-groups", "python", "-m", "pytest", TEST_FILE, "-q"],
        cwd=worktree,
        capture_output=True,
        text=True,
        timeout=1200,
        env=gate_environment(),
    )
    tail = completed.stdout.strip().splitlines()[-1:] or completed.stderr.strip().splitlines()[-1:]
    return {
        "command": f"pytest {TEST_FILE}",
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "tail": tail,
    }


def baseline_negative_control() -> dict[str, Any]:
    """Run the candidate's probe against the **unrepaired** active checkout.

    22A W4-F2's rule, one level up: a claim that a repair fixed something must be able to notice
    the thing being broken. The probe is expected to fail here, and the record carries the
    released refusal it fails with. A probe that passed on both trees would measure nothing.
    """
    from dryrun_22e import probe_repair_l7

    result = probe_repair_l7(REPO)
    return {
        "ran_against": "the unrepaired active checkout",
        "probe_holds_without_the_repair": result.get("every_probe_holds", False),
        "refusal_tail": result.get("probe_failed"),
        "why": ("a repair probe that passes on the unrepaired tree is not measuring the repair"),
    }


async def run(approver: str | None) -> dict[str, Any]:
    """Mine, draft, isolate, repair, evaluate, assess — and stop in front of a human."""
    import os

    from dryrun_22e import (
        LedgerProposalSource,
        LiveProviderGenerator,
        _head,
        probe_repair_l7,
    )
    from isolation_22e import (
        RealWorktree,
        assert_the_map_covers_the_matrix,
        matrix_gate_ids,
        run_gate,
    )
    from mining_22e import (
        MINING_TIME,
        LedgerWeaknessProposalSource,
        build_weakness,
        load_entry,
    )
    from sqlalchemy.ext.asyncio import create_async_engine
    from surface_22e import capture, compare

    from cognitive_os.changes.service import (
        ChangeAuthorityError,
        ControlledChangeService,
        assess_candidate,
        build_evaluation_matrix,
        compare_results,
    )
    from cognitive_os.domain.changes import (
        ActiveStateProtectionSnapshot,
        EvaluationCaseResult,
        ImplementationChannel,
        PromotionDecision,
        RollbackManifest,
        TypedPromotionStep,
    )
    from cognitive_os.domain.proposals import (
        HarnessProposalType,
        ProposalGenerationMode,
        ProposalReviewDecision,
        ProposalStatus,
    )
    from cognitive_os.infrastructure.changes.postgres.repository import (
        PostgresChangeRepository,
    )
    from cognitive_os.proposals.repository import InMemoryProposalRepository
    from cognitive_os.proposals.service import (
        HarnessProposalService,
        merge_provider_draft,
    )

    selection = read_selection()
    database_url = os.environ["COGOS_DATABASE_ADMIN_URL"]
    artifact_root = Path(os.environ["COGOS_ARTIFACT_ROOT"])
    before = await capture(database_url=database_url, artifact_root=artifact_root)

    stages: list[str] = []
    entry = load_entry(ENTRY_ID)
    mined = build_weakness(ENTRY_ID)
    stages.append("weakness_mined")

    proposals = HarnessProposalService(
        InMemoryProposalRepository(), LedgerWeaknessProposalSource(mined)
    )
    proposal = await proposals.create_from_weakness(
        mined["revision"].weakness_id,
        mined["revision"].revision,
        HarnessProposalType.SOURCE_CODE_CHANGE,
        actor="s22e-author",
        created_at=MINING_TIME,
    )
    stages.append("proposal_created")

    # **The installing traversal's exception, executed rather than asserted.** This runs against
    # the unrepaired checkout, so `merge_provider_draft` still returns an unsealed revision and
    # the caller reseals through the contract — exactly what W1 did and recorded. Decision one
    # licenses precisely this, for precisely this traversal.
    generator = LiveProviderGenerator(entry)
    draft = await generator.draft(proposal.source_snapshot, allowed_source_ids=())
    merged = merge_provider_draft(proposal, draft, allowed_source_ids=())
    merged_seal_was_blank = merged.content_hash == ""
    proposal = type(merged).model_validate(merged.model_dump(exclude={"content_hash"}))
    if proposal.generation_mode is not ProposalGenerationMode.PROVIDER_ASSISTED:
        raise AssertionError("host verification did not mark the revision provider-assisted")
    stages.append("provider_draft_merged_and_resealed")

    staged = await proposals.transition(
        proposal.proposal_id,
        proposal.revision,
        ProposalStatus.STAGED_FOR_REVIEW,
        actor="s22e-author",
        reason="ready for isolated experiment review",
        created_at=MINING_TIME,
    )
    approved = await proposals.record_review(
        staged.proposal_id,
        staged.revision,
        ProposalReviewDecision.APPROVE_FOR_EXPERIMENT,
        reviewer="s22e-reviewer",
        reviewer_authority="proposal-review",
        rationale="approved only for an exact isolated experiment",
        created_at=MINING_TIME,
    )
    stages.append("proposal_approved_for_experiment")

    baseline = baseline_negative_control()
    stages.append("baseline_negative_control_recorded")

    engine = create_async_engine(database_url)
    promotion: dict[str, Any] = {"attempted": False}
    bundle_record: dict[str, Any] | None = None
    try:
        source = LedgerProposalSource(proposals, approved)
        service = ControlledChangeService(PostgresChangeRepository(engine), source)
        experiment, _revision, approved = await service.request_experiment(
            approved.proposal_id,
            approved.revision,
            baseline_tag="sprint-22d-evidence-baseline",
            baseline_commit=_head(),
            actor="s22e-operator",
            isolation_approver=ISOLATION_APPROVER,
            created_at=MINING_TIME,
        )
        stages.append("experiment_requested")

        snapshot = ActiveStateProtectionSnapshot(
            repository_commit=before["values"]["repository_commit"],
            repository_status_hash=before["values"]["repository_status_hash"],
            repository_manifest_hash=before["values"]["repository_manifest_hash"],
            active_database_fingerprint=before["values"]["active_database_fingerprint"],
            active_artifact_namespace_hash=before["values"]["active_artifact_namespace_hash"],
            captured_at=MINING_TIME,
        )
        async with RealWorktree(f"w3-approved-{ENTRY_ID}") as worktree:
            assert worktree.path is not None
            isolation, _verifier = await service.prepare_isolation(
                experiment, approved, snapshot, created_at=MINING_TIME
            )
            stages.append("isolation_prepared")

            repair = apply_repair_with_its_test(worktree.path)
            stages.append("repair_applied")
            probe = probe_repair_l7(worktree.path)
            stages.append("repair_probed")
            focused = run_focused_regression(worktree.path)
            stages.append("candidate_test_run")

            changed_paths = tuple(repair["changed_files"])
            diff_hash, changed = await worktree.capture(allowed_paths=changed_paths)
            stages.append("candidate_captured_from_the_worktree")

            # **The released scope check, attempted against the real paths.** `capture_candidate`
            # compares `changed_files` against the isolation manifest's allowed paths, which the
            # released proposal engine fills with a synthetic `proposal-scope/...` name. The call
            # is made with the real files and whatever it decides is recorded — substituting the
            # placeholder to make it pass would be the driver certifying its own scope.
            scope: dict[str, Any] = {
                "manifest_allowed_repository_paths": list(isolation.allowed_repository_paths),
                "candidate_changed_files": list(changed_paths),
                "attempted_with_the_real_paths": True,
            }
            candidate = None
            try:
                candidate = await service.capture_candidate(
                    experiment,
                    isolation,
                    channel=ImplementationChannel.COGNITIVE_OS_CODING_AGENT,
                    patch_hash=diff_hash,
                    changed_files=changed_paths,
                    lockfile_hash_before=_sha256((worktree.path / "uv.lock").read_bytes()),
                    lockfile_hash_after=_sha256((worktree.path / "uv.lock").read_bytes()),
                    build_manifest=_sha256(canonical(repair)),
                    created_at=MINING_TIME,
                )
                scope["accepted"] = True
                stages.append("candidate_recorded")
            except ChangeAuthorityError as error:
                scope["accepted"] = False
                scope["refusal"] = str(error)
                stages.append("candidate_scope_refused")

            gate_ids = matrix_gate_ids(approved)
            assert_the_map_covers_the_matrix(gate_ids)
            gates = [run_gate(gate_id, worktree.path) for gate_id in gate_ids]
            stages.append("evaluation_run")
    finally:
        await engine.dispose()

    after = await capture(database_url=database_url, artifact_root=artifact_root)

    matrix = build_evaluation_matrix(approved)
    ran = [item for item in gates if item.get("ran")]
    failed = [item for item in ran if not item.get("passed")]
    results = tuple(
        EvaluationCaseResult(
            gate_id=item["gate_id"],
            passed=bool(item.get("passed")),
            measured_value=Decimal("1") if item.get("passed") else Decimal("0"),
            threshold=Decimal("1"),
            evidence_artifact=_sha256(canonical(item)),
            failure_code=None,
        )
        for item in ran
    )

    assessment_record: dict[str, Any] = {"built": False}
    if candidate is not None and results:
        comparison = compare_results(
            experiment.experiment_id,
            candidate.candidate_id,
            _sha256(b"baseline-evaluation"),
            candidate.content_hash,
            results,
            created_at=MINING_TIME,
        )
        assessment = assess_candidate(
            experiment=experiment,
            candidate=candidate,
            comparison=comparison,
            expected_benefit_hash=approved.expected_benefit.content_hash,
            measured_metrics={
                "case_pass_rate": Decimal(len(results) - len(failed)) / Decimal(len(results))
            },
            created_at=MINING_TIME,
        )
        stages.append("assessed")
        assessment_record = {
            "built": True,
            "decision": assessment.decision.value,
            "reason": assessment.reason,
            "eligible_for_operator_approval": (
                assessment.decision is PromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
            ),
            "hard_failure_codes": [str(item) for item in comparison.hard_failure_codes],
            "assessment_hash": assessment.content_hash,
        }

        if approver is None:
            promotion = {
                "attempted": False,
                "withheld_because": (
                    "no --approver was given; the released approval is a named human act and "
                    "this driver has no authority to supply the name"
                ),
            }
            stages.append("promotion_approval_withheld")
        else:
            engine = create_async_engine(database_url)
            try:
                service = ControlledChangeService(
                    PostgresChangeRepository(engine),
                    LedgerProposalSource(proposals, approved),
                )
                review = await service.approve_promotion(
                    experiment,
                    candidate,
                    assessment,
                    approver=approver,
                    authority="promotion-review",
                    target_authority="protected-repository",
                    rationale=(
                        "the sprint's one approved change, selected in S22E-201 decision two"
                    ),
                    created_at=MINING_TIME,
                )
                stages.append("promotion_approved")
                rollback = RollbackManifest(
                    promotion_reference=assessment.content_hash,
                    pre_promotion_state=repair["files"][0]["before_hash"],
                    post_promotion_state=candidate.content_hash,
                    rollback_operations=(
                        TypedPromotionStep(
                            adapter="operator.repository_bundle",
                            operation="prepare_patch_bundle",
                            target="repository",
                            exact_precondition_hash=candidate.content_hash,
                            artifact_hash=candidate.patch_artifact,
                        ),
                    ),
                    artifact_restore_requirements=(candidate.patch_artifact,),
                    database_restore_requirements=(),
                    verification_plan=matrix.content_hash,
                    maximum_recovery_objective=300,
                    manual_steps=("Operator uses the protected repository revert workflow.",),
                    created_at=MINING_TIME,
                )
                bundle = await service.create_repository_bundle(
                    experiment,
                    candidate,
                    assessment,
                    review,
                    rollback,
                    created_at=MINING_TIME,
                )
                stages.append("promotion_bundle_created")
                promotion = {
                    "attempted": True,
                    "approved": review.approved,
                    "approver": review.approver,
                    "approver_is_not_the_isolation_approver": review.approver
                    != experiment.approved_by,
                    "target_authority": review.target_authority,
                    "review_hash": review.content_hash,
                }
                bundle_record = {
                    "promotion_mode": bundle.promotion_mode.value,
                    "exact_baseline": bundle.exact_baseline,
                    "approved_scope": list(bundle.approved_scope),
                    "required_manual_steps": list(bundle.required_manual_steps),
                    "bundle_hash": bundle.content_hash,
                    "the_bundle_is_the_output_not_the_merge": (
                        "the released contract's own manual steps require the operator to "
                        "perform any merge, tag, publish or release action"
                    ),
                }
            finally:
                await engine.dispose()

    return {
        "entry_id": ENTRY_ID,
        "selection": selection,
        "stages": stages,
        "installing_traversal_exception": {
            "ruling": selection["walkability_ruling"],
            "merged_revision_seal_was_blank": merged_seal_was_blank,
            "caller_resealed_through_the_contract": True,
            "why": (
                "this traversal runs against the unrepaired checkout, where the defect it "
                "installs the repair for is still present; the repaired behaviour cannot be "
                "required of the traversal that installs the repair"
            ),
        },
        "provider": generator.receipt,
        "draft": {
            "prompt_bytes": len(generator.prompt or ""),
            "advisory_fields": sorted(generator.structured or {}),
            "summary": (generator.structured or {}).get("summary"),
            "generation_mode_after_host_verification": merged.generation_mode.value,
            "generation_mode_on_the_approved_revision": approved.generation_mode.value,
        },
        "baseline_negative_control": baseline,
        "repair": repair,
        "repair_probe": probe,
        "candidate_test": focused,
        "worktree_capture": {
            "changed_files": list(changed),
            "diff_hash": diff_hash,
            "only_the_declared_paths_changed": set(changed) <= set(changed_paths),
        },
        "released_scope_check": scope,
        "evaluation": {
            "gates": len(gate_ids),
            "gates_ran": len(ran),
            "gates_passed": len(ran) - len(failed),
            "gates_failed": [item["gate_id"] for item in failed],
            "driver_decided": [item["gate_id"] for item in gates if not item.get("ran")],
            "wall_clock_seconds": round(sum(float(item.get("seconds", 0)) for item in gates), 3),
        },
        "gates": gates,
        "assessment": assessment_record,
        "promotion": promotion,
        "promotion_bundle": bundle_record,
        "zero_active_state_mutation": compare(before, after),
        "surface_before": before["values"],
        "surface_after": after["values"],
        "recorded_at": W3_TIME,
    }


#: What `--check` re-reads instead of recomputing. Gate wall clocks, a live provider receipt and
#: a worktree diff hash are observations of one execution; re-deriving them would mean re-running
#: the matrix and re-billing a provider call, which 22C W1-F1 forbids a validator from doing.
OBSERVED_AT_W3 = (
    "provider",
    "draft",
    "gates",
    "evaluation",
    "repair",
    "repair_probe",
    "candidate_test",
    "baseline_negative_control",
    "worktree_capture",
    "released_scope_check",
    "assessment",
    "promotion",
    "promotion_bundle",
    "stages",
    "surface_before",
    "surface_after",
    "zero_active_state_mutation",
    "installing_traversal_exception",
)


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    """Recompute what can be recomputed without re-running the world.

    The seal, the gate owner's sealed selection, and the ledger entry the run claims to have
    mined are all re-derived from their own records here. Everything in `OBSERVED_AT_W3` is
    re-read and compared against nothing, and the record says which is which.
    """
    from mining_22e import load_entry

    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    entry = load_entry(ENTRY_ID)
    return {
        "seal_recomputes": _sha256(canonical(body)) == record["integrity_content_hash"],
        "selection_still_seals": read_selection()["decision_record_hash"]
        == record["selection"]["decision_record_hash"],
        "ledger_entry_still_seals": entry["entry_id"] == ENTRY_ID,
        "entry_finding_matches": entry["finding"] == record["selection"]["selection_finding"],
        "recorded_not_recomputed": list(OBSERVED_AT_W3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--approver",
        default=None,
        help="the named human granting the released promotion approval",
    )
    parser.add_argument("--output", default=None)
    arguments = parser.parse_args()
    output = Path(arguments.output) if arguments.output else OUTPUT

    if arguments.check:
        stored = json.loads(output.read_text(encoding="utf-8"))
        verdict = check_record(stored)
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return (
            0
            if all(value for key, value in verdict.items() if key != "recorded_not_recomputed")
            else 1
        )

    if arguments.approver == ISOLATION_APPROVER:
        raise SystemExit(
            "the promotion approver must differ from the isolation approver; the released "
            "service refuses this and the driver refuses it earlier"
        )

    record = asyncio.run(run(arguments.approver))
    record["integrity_content_hash"] = _sha256(canonical(record))
    output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "stages": len(record["stages"]),
                "gates_passed": record["evaluation"]["gates_passed"],
                "gates_failed": record["evaluation"]["gates_failed"],
                "scope_accepted": record["released_scope_check"].get("accepted"),
                "assessment": record["assessment"].get("decision"),
                "promotion_attempted": record["promotion"].get("attempted"),
                "zero_active_state_mutation": record["zero_active_state_mutation"][
                    "zero_active_state_mutation"
                ],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
