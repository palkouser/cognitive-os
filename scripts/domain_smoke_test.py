#!/usr/bin/env python
"""Offline machine-readable smoke test for the cross-domain pilot.

Runs all three domains plus a skill and a strategy transfer experiment and prints
one JSON document. No credentials, no network, no GPU, and no optional extras.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cognitive_os.benchmarks.domain_adapter import _GOVERNANCE, governance_checks  # noqa: E402
from cognitive_os.domain.domains import (  # noqa: E402
    DomainKind,
    TransferDisposition,
    VerificationDisposition,
)
from cognitive_os.domains import kernels  # noqa: E402
from cognitive_os.domains.fixtures import build_all_cases, wrong_answer_for  # noqa: E402
from cognitive_os.domains.registry import entries, problem_types, snapshot_hash  # noqa: E402
from cognitive_os.domains.repository import InMemoryDomainRepository  # noqa: E402
from cognitive_os.domains.service import DomainPilotService  # noqa: E402
from cognitive_os.domains.transfer import (  # noqa: E402
    run_experiment,
    run_negative_transfer_experiment,
)


async def _domain_report() -> dict[str, object]:
    cases = build_all_cases()
    repository = InMemoryDomainRepository()
    service = DomainPilotService(repository)
    per_domain: dict[str, dict[str, int]] = {}
    for domain in DomainKind:
        subset = [item for item in cases if item.domain is domain]
        accepted = rejected = as_declared = fallible = 0
        for case in subset:
            case_accepted = (await service.run_case(case)).accepted
            accepted += case_accepted
            # Sprint 21C.1: the coding domain's baselines are deliberately
            # fallible, so "everything is accepted" stopped being the right
            # question. The right one is whether each case lands where its
            # contract says it will.
            declared_pass = case.expected_disposition is VerificationDisposition.PASS
            as_declared += case_accepted is declared_pass
            fallible += not declared_pass
            if not (await service.run_case(case, candidate=wrong_answer_for(case))).accepted:
                rejected += 1
        per_domain[domain.value] = {
            "cases": len(subset),
            "accepted_correct": accepted,
            "matched_declared_disposition": as_declared,
            "fallible_baselines": fallible,
            "rejected_wrong": rejected,
            "problem_types": len(problem_types(domain)),
        }
    return {"domains": per_domain, "evidence_rows": len(repository.runs)}


async def _governed_report() -> dict[str, object]:
    """Prove the governed path, not just the kernels, over one case per domain."""
    from cognitive_os.domain.skills import SkillExecutionStatus
    from cognitive_os.domains.runner import run_case_controlled
    from cognitive_os.domains.skill_execution import domain_task_signature
    from cognitive_os.domains.skill_runner import run_case_as_skill

    cases = build_all_cases()
    rows: dict[str, object] = {}
    for domain in DomainKind:
        case = next(item for item in cases if item.domain is domain)
        controlled = await run_case_controlled(case)
        rejected = await run_case_controlled(case, candidate_override=wrong_answer_for(case))
        skill = await run_case_as_skill(case)
        rows[domain.value] = {
            "case": case.case_id,
            "controller_state": controlled.state.value,
            "accepted": controlled.accepted,
            "wrong_answer_rejected": not rejected.accepted,
            "tool_calls": controlled.tool_calls,
            "verifier_calls": controlled.verifier_calls,
            "tool_plane_audited": all(
                item in controlled.event_types
                for item in (
                    "tool_call.requested",
                    "tool_call.authorized",
                    "tool_call.started",
                    "tool_call.completed",
                )
            ),
            "skill_execution": skill.result.status.value,
            "task_signature": domain_task_signature(case).content_hash,
        }
    return {
        "per_domain": rows,
        "all_controller_owned": all(
            item["controller_state"] == "completed" and item["accepted"]  # type: ignore[index]
            for item in rows.values()
        ),
        "all_tool_plane_audited": all(
            item["tool_plane_audited"]
            for item in rows.values()  # type: ignore[index]
        ),
        "all_skill_executions_accepted": all(
            item["skill_execution"] == SkillExecutionStatus.ACCEPTED.value  # type: ignore[index]
            for item in rows.values()
        ),
    }


async def _transfer_report() -> dict[str, object]:
    _, skill = await run_experiment(
        source_domain=DomainKind.MATHEMATICS,
        target_domain=DomainKind.PHYSICS,
        unrelated_domain=DomainKind.LOGIC,
        component_kind="skill",
        component_id="verification-driven-arithmetic-repair",
    )
    _, strategy = await run_experiment(
        source_domain=DomainKind.MATHEMATICS,
        target_domain=DomainKind.LOGIC,
        unrelated_domain=DomainKind.PHYSICS,
        component_kind="strategy",
        component_id="decompose-compute-verify",
    )
    _, negative = await run_negative_transfer_experiment()
    return {
        "skill": _transfer_row(skill),
        "strategy": _transfer_row(strategy),
        "negative_control": _transfer_row(negative),
        "positive_skill_transfer": skill.disposition is TransferDisposition.POSITIVE_TRANSFER,
        "positive_strategy_transfer": strategy.disposition is TransferDisposition.POSITIVE_TRANSFER,
        "negative_transfer_rejected": negative.disposition is TransferDisposition.NEGATIVE_TRANSFER,
    }


def _transfer_row(result: object) -> dict[str, object]:
    return {
        "disposition": result.disposition.value,  # type: ignore[attr-defined]
        "target_quality_delta": str(result.target_quality_delta),  # type: ignore[attr-defined]
        "source_quality_delta": str(result.source_quality_delta),  # type: ignore[attr-defined]
        "unrelated_quality_delta": str(result.unrelated_quality_delta),  # type: ignore[attr-defined]
        "hard_gate_failures": list(result.hard_gate_failures),  # type: ignore[attr-defined]
        "control_arms": sorted(item.value for item in result.arms),  # type: ignore[attr-defined]
    }


async def _health() -> dict[str, object]:
    from importlib.util import find_spec

    checks = {name: await _GOVERNANCE[name]() for name in governance_checks()}
    return {
        "registry_snapshot": snapshot_hash(),
        "registered_problem_types": len(entries()),
        "unit_registry_hash": kernels.registry_hash(),
        "governance_checks": checks,
        "governance_all_passed": all(checks.values()),
        "optional_extras": {
            name: find_spec(module) is not None
            for name, module in (
                ("verification-math", "sympy"),
                ("verification-physics", "pint"),
                ("verification-logic", "z3"),
            )
        },
        "mandatory_path_requires_extras": False,
    }


async def _main(output: Path | None) -> int:
    report = {
        "smoke_test": "sprint20-cross-domain-pilot",
        "health": await _health(),
        "pilot": await _domain_report(),
        "governed": await _governed_report(),
        "transfer": await _transfer_report(),
    }
    health = report["health"]
    pilot = report["pilot"]
    transfer = report["transfer"]
    governed = report["governed"]
    report["passed"] = bool(
        health["governance_all_passed"]  # type: ignore[index]
        and governed["all_controller_owned"]  # type: ignore[index]
        and governed["all_tool_plane_audited"]  # type: ignore[index]
        and governed["all_skill_executions_accepted"]  # type: ignore[index]
        and transfer["positive_skill_transfer"]  # type: ignore[index]
        and transfer["positive_strategy_transfer"]  # type: ignore[index]
        and transfer["negative_transfer_rejected"]  # type: ignore[index]
        and all(
            item["matched_declared_disposition"] == item["cases"] == item["rejected_wrong"]
            for item in pilot["domains"].values()  # type: ignore[index,union-attr]
        )
    )
    document = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(document)
    sys.stdout.write(document)
    return 0 if report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None, help="write the JSON report here")
    arguments = parser.parse_args()
    return asyncio.run(_main(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
