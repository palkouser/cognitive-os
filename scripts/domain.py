"""Operate the Sprint 20 cross-domain pilot: run cases, mine weaknesses, and check health.

Every action runs offline, on CPU, with no credentials, unless `--database` selects a
read-only Postgres health check.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.domains.fixtures import build_all_cases, wrong_answer_for


def _json(value: object) -> str:
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


def _case(case_id: str | None) -> DomainBenchmarkCase:
    cases = build_all_cases()
    if case_id is None:
        return cases[0]
    case = next((item for item in cases if item.case_id == case_id), None)
    if case is None:
        raise SystemExit(f"unknown case: {case_id}")
    return case


async def _database_health() -> int:
    from cognitive_os.infrastructure.domains.postgres.health import PostgresDomainHealthService
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required for database health")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresDomainHealthService(engine).check()
    finally:
        await engine.dispose()
    print(report.model_dump_json())
    return 0 if report.healthy else 1


async def _run(args: argparse.Namespace) -> int:
    from cognitive_os.domains.runner import run_case_controlled

    case = _case(args.case)
    candidate = wrong_answer_for(case) if args.wrong else None
    run = await run_case_controlled(case, candidate_override=candidate)
    payload = {
        "case_id": case.case_id,
        "state": run.state.value,
        "accepted": run.accepted,
        "tool_calls": run.tool_calls,
        "verifier_calls": run.verifier_calls,
        "decision_reason": run.decision_reason,
        "event_types": run.event_types,
    }
    print(_json(payload))
    return int(run.accepted == bool(args.wrong))


async def _run_skill(args: argparse.Namespace) -> int:
    from cognitive_os.domains.skill_runner import run_case_as_skill

    case = _case(args.case)
    run = await run_case_as_skill(case)
    payload = {
        "case_id": case.case_id,
        "status": run.result.status.value,
        "accepted": run.accepted,
    }
    print(_json(payload))
    return int(not run.accepted)


async def _learn(args: argparse.Namespace) -> int:
    from cognitive_os.domains.learning import run_case_with_learning

    case = _case(args.case)
    candidate = wrong_answer_for(case) if args.wrong else None
    run, result = await run_case_with_learning(case, candidate_override=candidate)
    payload = {
        "case_id": case.case_id,
        "accepted": run.accepted,
        "compilation_decision": result.compilation.decision.decision.value,
        "terminal_state": result.compilation.snapshot.terminal_state,
        "candidate_types": [item.value for item in result.candidate_types],
        "memory_ids": [str(item) for item in result.memory_ids],
        "observation_count": result.observation_count,
        "claim_count": result.claim_count,
        "corpus_item_count": result.corpus_item_count,
    }
    print(_json(payload))
    return 0


async def _mine(_args: argparse.Namespace) -> int:
    from cognitive_os.domains.weakness import mine_domain_weaknesses

    outcome = await mine_domain_weaknesses()
    payload = {
        "status": outcome.result.status.value,
        "signal_count": outcome.signal_count,
        "weakness_count": outcome.weakness_count,
        "probes": [
            {"case_id": item.case.case_id, "is_capability_gap": item.is_capability_gap}
            for item in outcome.observations
        ],
    }
    print(_json(payload))
    return int(outcome.result.manifest is None)


async def _propose(_args: argparse.Namespace) -> int:
    from cognitive_os.domains.improvement import propose_from_domain_weakness

    outcome = await propose_from_domain_weakness()
    print(outcome.proposal.model_dump_json())
    return int(outcome.proposal.status.value != "approved_for_experiment")


async def _experiment(_args: argparse.Namespace) -> int:
    from cognitive_os.domains.improvement import run_isolated_experiment

    outcome = await run_isolated_experiment()
    payload = {
        "experiment_id": str(outcome.experiment.experiment_id),
        "promotion_mode": outcome.promotion_mode.value,
        "promotion_is_manual": outcome.promotion_is_manual,
        "assessment_decision": outcome.assessment.decision.value,
        "approval_requirements": outcome.assessment.approval_requirements,
        "hard_failures": outcome.comparison.hard_failure_codes,
    }
    print(_json(payload))
    return int(not outcome.promotion_is_manual)


async def _health(args: argparse.Namespace) -> int:
    if args.database:
        return await _database_health()
    from cognitive_os.benchmarks.domain_adapter import _GOVERNANCE, governance_checks

    checks = {name: await _GOVERNANCE[name]() for name in governance_checks()}
    payload = {"healthy": all(checks.values()), "governance_checks": checks}
    print(_json(payload))
    return int(not payload["healthy"])


_ACTIONS = {
    "run": _run,
    "run-skill": _run_skill,
    "learn": _learn,
    "mine": _mine,
    "propose": _propose,
    "experiment": _experiment,
    "health": _health,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=tuple(_ACTIONS))
    parser.add_argument("--case", help="exact case_id; defaults to the first fixture case")
    parser.add_argument(
        "--wrong", action="store_true", help="inject a deliberately wrong answer (run, learn)"
    )
    parser.add_argument("--database", action="store_true", help="run the Postgres health check")
    args = parser.parse_args()
    return asyncio.run(_ACTIONS[args.action](args))


if __name__ == "__main__":
    raise SystemExit(main())
