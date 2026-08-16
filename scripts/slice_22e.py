"""S22E-030. The §3.1 first vertical slice: the released demo, then a proposal to a rejection.

§3.1 says every sprint since D4 found its cheapest defect in the slice, and it is explicit
about what W0's slice is for: drive the released controlled-change demo, then drive **one
fixture proposal through the entire chain to a rejection**, with the zero-mutation comparison
recomputed. W1 then does the same thing against the real repository before any provider is
paid. The point of doing it on a fixture first is that the one change this sprint gets to land
must not be the run that discovers a broken stage.

Three things this slice proves, and one it deliberately does not.

**It proves the chain composes.** Every stage is entered in order through the released
transitions — experiment, isolation, plan, candidate, evaluation matrix, comparison,
assessment — and nothing is skipped.

**It proves the refusal is real.** The candidate fails its own evaluation matrix on a genuine
released failure code, `assess_candidate` maps that to a rejection, and `approve_promotion`
then **raises**. That last step is the one worth having: a loop where rejection is a value
somebody remembered to check is a loop with no gate in it. Here it is a released exception,
and this driver asserts it was raised rather than asserting a field.

**It proves zero active-state mutation, by recomputation.** §2.2(a)'s enumerated surface is
captured before and after and compared by `surface_22e.compare`, which derives every member's
equality from the two captures. Nothing here reports `unchanged: true` about itself
(22A W4-F2).

**What it does not prove**: anything about the real repository. This candidate is a fixture,
its patch hash is a literal, and no worktree exists. §1.3's last sentence lists the seams that
are still unmeasured after this runs, and §3.1 puts them in W1 on purpose.

    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/slice_22e.py
    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/slice_22e.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from surface_22e import capture, compare  # noqa: E402

from cognitive_os.changes.demo import run_demo  # noqa: E402
from cognitive_os.changes.fixtures import fixture_approved_proposal  # noqa: E402
from cognitive_os.changes.repository import InMemoryChangeRepository  # noqa: E402
from cognitive_os.changes.service import (  # noqa: E402
    ChangeAuthorityError,
    ControlledChangeService,
    assess_candidate,
    build_evaluation_matrix,
    compare_results,
)
from cognitive_os.domain.changes import (  # noqa: E402
    ActiveStateProtectionSnapshot,
    EvaluationCaseResult,
    ExperimentFailureCode,
    ImplementationChannel,
    PromotionDecision,
)
from cognitive_os.proposals.fixtures import FIXTURE_TIME  # noqa: E402

OUTPUT = EVIDENCE / "sprint-22e-w0-slice.json"
SLICE_TIME = "2026-08-16T00:00:00Z"

#: The gate the fixture candidate is made to fail, and it is a released code rather than a
#: number chosen to be under a threshold. `SECURITY_REGRESSION` is picked because
#: `FAILURE_DECISIONS` maps it to a *named* promotion decision rather than to the generic
#: `REJECTED`, so the rejection this slice produces has to travel through the released mapping
#: to arrive — a rejection that arrived by default would prove less.
FAILED_GATE_CODE = ExperimentFailureCode.SECURITY_REGRESSION

#: Every stage the lifecycle must enter, in order. Declared once and compared against what the
#: run actually appended, rather than re-typed inside the result dictionary — which is how the
#: first draft of this file claimed `no_stage_skipped: false` on a complete run, having simply
#: forgotten `assessed` in the copy it compared against. A stage list written twice is a stage
#: list that disagrees with itself.
EXPECTED_STAGE_ORDER = (
    "experiment_requested",
    "isolation_prepared",
    "implementation_planned",
    "candidate_captured",
    "evaluation_matrix_built",
    "evaluation_run",
    "assessed",
    "promotion_refused",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


async def _released_demo() -> dict[str, Any]:
    """The released end-to-end demo, driven and *read*, not merely invoked without raising."""
    result = await run_demo()
    assessment = result["assessment"]
    review = result["promotion_review"]
    return {
        "stages": sorted(result),
        "stage_count": len(result),
        "assessment_decision": assessment.decision.value,
        "assessment_reason": assessment.reason,
        "promotion_approved": review.approved,
        "promotion_approver": review.approver,
        "separate_actors_enforced": review.approver != result["experiment"].approved_by,
        "credential_free_and_in_memory": True,
    }


async def _proposal_to_rejection() -> dict[str, Any]:
    """One fixture proposal, every stage in order, refused at a genuine gate."""
    source, proposal = await fixture_approved_proposal()
    service = ControlledChangeService(InMemoryChangeRepository(), source)
    baseline = "a" * 40
    stages: list[str] = []

    experiment, _revision, proposal = await service.request_experiment(
        proposal.proposal_id,
        proposal.revision,
        baseline_tag="sprint-22d-evidence-baseline",
        baseline_commit=baseline,
        actor="operator",
        isolation_approver="isolation-approver",
        created_at=FIXTURE_TIME,
    )
    stages.append("experiment_requested")

    snapshot = ActiveStateProtectionSnapshot(
        repository_commit=baseline,
        repository_status_hash="b" * 64,
        repository_manifest_hash="c" * 64,
        active_database_fingerprint="d" * 64,
        active_artifact_namespace_hash="e" * 64,
        captured_at=FIXTURE_TIME,
    )
    isolation, _verifier = await service.prepare_isolation(
        experiment, proposal, snapshot, created_at=FIXTURE_TIME
    )
    stages.append("isolation_prepared")

    service.build_plan(proposal, isolation)
    stages.append("implementation_planned")

    candidate = await service.capture_candidate(
        experiment,
        isolation,
        channel=ImplementationChannel.COGNITIVE_OS_CODING_AGENT,
        patch_hash="1" * 64,
        changed_files=isolation.allowed_repository_paths,
        lockfile_hash_before="2" * 64,
        lockfile_hash_after="2" * 64,
        build_manifest="3" * 64,
        created_at=FIXTURE_TIME,
    )
    stages.append("candidate_captured")

    matrix = build_evaluation_matrix(proposal)
    stages.append("evaluation_matrix_built")

    # The failure is planted in exactly one cell, and every other cell passes. A candidate
    # that failed everything would be rejected by any reading; one bad gate out of many is
    # what a real refusal looks like, and it is what proves the matrix is read per gate.
    failing_gate = matrix.execution_order[0]
    results = tuple(
        EvaluationCaseResult(
            gate_id=gate_id,
            passed=gate_id != failing_gate,
            measured_value=Decimal("0") if gate_id == failing_gate else Decimal("1"),
            threshold=Decimal("1"),
            evidence_artifact=_sha256(gate_id.encode()),
            failure_code=FAILED_GATE_CODE if gate_id == failing_gate else None,
        )
        for gate_id in matrix.execution_order
    )
    comparison = compare_results(
        experiment.experiment_id,
        candidate.candidate_id,
        _sha256(b"baseline-evaluation"),
        candidate.content_hash,
        results,
        created_at=FIXTURE_TIME,
    )
    stages.append("evaluation_run")

    assessment = assess_candidate(
        experiment=experiment,
        candidate=candidate,
        comparison=comparison,
        expected_benefit_hash=proposal.expected_benefit.content_hash,
        measured_metrics={"case_pass_rate": Decimal(len(results) - 1) / Decimal(len(results))},
        created_at=FIXTURE_TIME,
    )
    stages.append("assessed")

    # The gate, executed. Not "the decision was not eligible, so we did not call it" — the
    # released service is *called* and required to raise, because a refusal nobody attempted
    # is a refusal nobody has evidence of.
    refusal: str | None = None
    try:
        await service.approve_promotion(
            experiment,
            candidate,
            assessment,
            approver="promotion-approver",
            authority="promotion-review",
            target_authority="protected-repository",
            rationale="attempted despite a failed gate, to prove the refusal is executable",
            created_at=FIXTURE_TIME,
        )
    except ChangeAuthorityError as error:
        refusal = str(error)
        stages.append("promotion_refused")
    else:  # pragma: no cover - a pass here is the defect this slice exists to catch
        raise AssertionError(
            "approve_promotion accepted a rejected assessment; the gate does not gate"
        )

    return {
        "stages_entered_in_order": stages,
        "stage_count": len(stages),
        "expected_stage_order": list(EXPECTED_STAGE_ORDER),
        "no_stage_skipped": tuple(stages) == EXPECTED_STAGE_ORDER,
        "evaluation": {
            "gates": len(matrix.execution_order),
            "failing_gate": failing_gate,
            "failing_gate_code": FAILED_GATE_CODE.value,
            "gates_passed": sum(1 for item in results if item.passed),
            "hard_failure_codes": [str(item) for item in comparison.hard_failure_codes],
        },
        "assessment": {
            "decision": assessment.decision.value,
            "reason": assessment.reason,
            "security_result": assessment.security_result,
            "rollback_validation": assessment.rollback_validation,
            "is_a_rejection": assessment.decision
            is not PromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
            "arrived_through_the_released_mapping": (
                assessment.decision is PromotionDecision.SECURITY_REGRESSION
            ),
        },
        "promotion": {
            "attempted": True,
            "refused": refusal is not None,
            "refusal": refusal,
            "refusal_is_an_exception_not_a_field": True,
        },
        "this_is_a_fixture": (
            "the candidate's patch hash is a literal and no worktree exists; §1.3's seams "
            "between this demo and the real repository are still unmeasured, and §3.1 puts "
            "them in W1"
        ),
    }


async def _record() -> dict[str, Any]:
    database_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    artifact_root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not database_url or not artifact_root:
        raise SystemExit("REFUSED: source .env.s22e.local first")

    before = await capture(database_url=database_url, artifact_root=Path(artifact_root))
    demo = await _released_demo()
    rejection = await _proposal_to_rejection()
    after = await capture(database_url=database_url, artifact_root=Path(artifact_root))

    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22E-030"],
        "sprint": "22E",
        "wave": "W0",
        "released_demo": demo,
        "fixture_proposal_to_rejection": rejection,
        "zero_active_state_mutation": compare(before, after),
        "surface_before": before["values"],
        "surface_after": after["values"],
        "reads_an_exit_criterion": False,
        "why_no_exit": (
            "§3.1's slice decides nothing. Exit one wants a *real* rejection — a genuine "
            "provider-generated candidate refused at a genuine gate (§2.2a) — and this is a "
            "fixture refusing a fixture, which the plan names as explicitly not enough"
        ),
        "recorded_at": SLICE_TIME,
    }
    record["integrity_content_hash"] = _sha256(
        _canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    record = asyncio.run(_record())
    if arguments.check:
        if not OUTPUT.exists():
            print(f"MISSING {OUTPUT}")
            return 1
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(_canonical(body)) == stored["integrity_content_hash"]
        # The two surface captures move whenever anything writes to the store or the tree,
        # which is what every later wave does. What must reproduce is the slice's own
        # behaviour and the fact that it mutated nothing *at the time it ran*.
        #
        # **W1-F2.** `integrity_content_hash` joins them, and it has to: the seal is computed
        # over the whole record *including* the two moving captures, so a rebuild that
        # correctly re-reads a moved world can never reproduce it. Left in the comparison,
        # this `--check` was green only while nothing wrote to the governed store between two
        # runs — which held for exactly as long as W0 lasted. The stored seal is still
        # verified, against the stored body, by `sealed` above; that is the question that
        # matters, and it is a different question from whether the rebuild matches.
        moving = {
            "surface_before",
            "surface_after",
            "zero_active_state_mutation",
            "integrity_content_hash",
        }
        identical = {k: v for k, v in stored.items() if k not in moving} == {
            k: v for k, v in record.items() if k not in moving
        }
        print(
            json.dumps(
                {
                    "reproduced": identical and sealed,
                    "rebuild_identical": identical,
                    "stored_seal_intact": sealed,
                    "recorded_not_recomputed": sorted(moving),
                    "rerun_also_mutated_nothing": record["zero_active_state_mutation"][
                        "zero_active_state_mutation"
                    ],
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if identical and sealed else 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "demo_stages": record["released_demo"]["stage_count"],
                "demo_decision": record["released_demo"]["assessment_decision"],
                "rejection_stages": record["fixture_proposal_to_rejection"][
                    "stages_entered_in_order"
                ],
                "no_stage_skipped": record["fixture_proposal_to_rejection"]["no_stage_skipped"],
                "assessment_decision": record["fixture_proposal_to_rejection"]["assessment"][
                    "decision"
                ],
                "promotion_refused": record["fixture_proposal_to_rejection"]["promotion"][
                    "refused"
                ],
                "zero_active_state_mutation": record["zero_active_state_mutation"][
                    "zero_active_state_mutation"
                ],
                "mutated_members": record["zero_active_state_mutation"]["mutated_members"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
