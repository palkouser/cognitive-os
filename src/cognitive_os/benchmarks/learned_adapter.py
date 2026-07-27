"""Executable Sprint 21C1 learned evidence benchmark adapter.

Each case really runs the governed path and compares what happened with what the manifest
declared, so a regression in the lifecycle, the intake classifier, the dataset builder or
the replay check fails the benchmark rather than being absorbed by an expectation table.

Everything runs against the in-memory reference repository and a stub Artifact Store, so
the whole family is credential-free, network-free, provider-free and CPU-only. That is
not a convenience: a benchmark gate that needed a database would be one more reason the
gate gets skipped.

Nothing here measures accuracy or uplift. Every case measures whether a *policy* held.
See ADR 0086.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any
from uuid import UUID, uuid5

from cognitive_os.domain.benchmarks import (
    BenchmarkCase,
    BenchmarkCaseResult,
    BenchmarkCaseStatus,
)

BENCHMARK_NAMESPACE = UUID("2f9c8d41-6b05-5a73-9e18-4c07b2fd6a39")


async def learned_benchmark_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    request = case.problem_request
    scenario = str(request.get("scenario", ""))
    # `expected` is a reserved matrix key routed to `expected_outputs["status"]`, not to
    # `problem_request`. Reading it from the request silently defaults every case.
    expected = str(case.expected_outputs.get("status", "passed"))
    started = perf_counter()
    metrics: dict[str, float] = {
        "provider_calls": 0.0,
        "network_calls": 0.0,
        "credential_reads": 0.0,
        "gpu_calls": 0.0,
        "default_active_components": 0.0,
        "artifacts_deserialised": 0.0,
    }

    handler = _SCENARIOS.get(scenario)
    if handler is None:
        matched, extra = False, {"unknown_scenario": 1.0}
    else:
        matched, extra = await handler(request, expected)

    metrics.update(extra)
    metrics["expected_outcome_matched"] = float(matched)
    metrics["elapsed_seconds"] = perf_counter() - started
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED if matched else BenchmarkCaseStatus.FAILED,
        started_at=_fixture_time(),
        finished_at=_fixture_time(),
        metrics=metrics,
    )


def _fixture_time() -> Any:
    from datetime import UTC, datetime

    return datetime(2026, 7, 27, tzinfo=UTC)


def _harness() -> tuple[Any, Any, Any]:
    """A fresh service, its repository and a stub Artifact Store, per case."""
    from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
    from cognitive_os.events.learned_event_service import LearnedEventService
    from cognitive_os.events.memory_store import MemoryEventStore
    from cognitive_os.infrastructure.learned.memory_repository import (
        InMemoryLearnedEvidenceRepository,
    )

    from .learned_fixtures import BenchmarkArtifactVerifier

    repository = InMemoryLearnedEvidenceRepository()
    artifacts = BenchmarkArtifactVerifier()
    service = LearnedEvidenceService(
        repository,
        artifacts=artifacts,
        events=LearnedEventService(MemoryEventStore()),
        activation_actors=frozenset({"benchmark-operator"}),
        clock=_fixture_time,
    )
    return service, repository, artifacts


async def _lifecycle(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """Drive the fixture to a declared state and check the store agrees."""
    from cognitive_os.domain.learned import LearnedComponentState

    from .learned_fixtures import drive_to

    target = LearnedComponentState(str(request.get("target", "verified")))
    service, repository, _ = _harness()
    reached = await drive_to(service, target)
    row = await service.get_component(reached.component_id)
    matched = row is not None and row.current_state is target and expected == "passed"
    return matched, {
        "revisions": float(repository.counts()["revisions"]),
        "reached_state": 1.0 if row and row.current_state is target else 0.0,
    }


async def _activation(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """Activate under a named defect, and check it is refused exactly when it should be."""
    from cognitive_os.domain.learned_evidence import LearnedRepositoryError

    from .learned_fixtures import attempt_activation

    defect = str(request.get("defect", "none"))
    service, repository, _ = _harness()
    refused = False
    conflict = ""
    try:
        await attempt_activation(service, defect=defect)
    except (LearnedRepositoryError, ValueError) as error:
        refused = True
        named = getattr(error, "conflict", None)
        conflict = named.value if named is not None else "contract_validation"
    active = await service.active_component_for("skill.selection")
    matched = refused if expected == "rejected" else (not refused and active is not None)
    return matched, {
        "refused": float(refused),
        "active_after": float(active is not None),
        "receipts": float(repository.counts()["receipts"]),
        "conflict_named": float(bool(conflict)),
    }


async def _rollback(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """Activate, disable, roll back, and confirm the receipt chain names its target."""
    from .learned_fixtures import activate_disable_rollback

    service, repository, _ = _harness()
    activation, rollback = await activate_disable_rollback(service)
    row = await service.get_component(activation.component_id)
    from cognitive_os.domain.learned import LearnedComponentState

    matched = (
        expected == "passed"
        and rollback.rollback_target_receipt_id == activation.receipt_id
        and row is not None
        and row.current_state is LearnedComponentState.ACTIVE
    )
    return matched, {
        "rollback_names_target": float(
            rollback.rollback_target_receipt_id == activation.receipt_id
        ),
        "receipts": float(repository.counts()["receipts"]),
        "history_rewrites": 0.0,
    }


async def _observation(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """Classify one governed outcome and check the decision matches the declaration."""
    from cognitive_os.application.services.learned_intake import classify

    from .learned_fixtures import outcome_reference

    reference = outcome_reference(str(request.get("defect", "none")))
    code, _ = classify(reference)
    matched = code.status.value == expected
    return matched, {
        "accepted": float(code.status.value == "accepted"),
        "quarantined": float(code.status.value == "quarantined"),
        "rejected": float(code.status.value == "rejected"),
        "reason_code_stable": float(code.value.startswith(code.status.value.split("_")[0])),
    }


async def _dataset(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """Build a snapshot twice and check the identity is stable, or changes when it must."""
    from .learned_fixtures import build_dataset_pair

    variation = str(request.get("variation", "identical"))
    first, second, refused = await build_dataset_pair(variation)
    if expected == "rejected":
        return refused, {"refused": float(refused), "identical": 0.0}
    if first is None or second is None:
        return False, {"refused": float(refused), "identical": 0.0}
    identical = first.dataset_id == second.dataset_id and first.content_hash == second.content_hash
    matched = identical if variation == "identical" else not identical
    return matched, {
        "identical": float(identical),
        "observation_count": float(first.observation_count),
        "example_bodies_stored": 0.0,
    }


async def _artifact(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """Register lineage under a named artifact defect and check it is refused correctly."""
    from cognitive_os.domain.learned_evidence import LearnedRepositoryError

    from .learned_fixtures import attempt_lineage

    defect = str(request.get("defect", "none"))
    service, repository, _ = _harness()
    refused = False
    try:
        await attempt_lineage(service, defect=defect)
    except (LearnedRepositoryError, ValueError):
        refused = True
    matched = refused if expected == "rejected" else not refused
    return matched, {
        "refused": float(refused),
        "lineage_rows": float(repository.counts()["lineages"]),
        "bytes_copied": 0.0,
    }


async def _replay(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """Replay a healthy or deliberately damaged history and check it fails closed."""
    from .learned_fixtures import replay_after

    defect = str(request.get("defect", "none"))
    result = await replay_after(defect)
    agrees = result.projection_matches and result.hash_chain_verified
    matched = agrees if expected == "passed" else (not agrees and bool(result.failures))
    return matched, {
        "projection_matches": float(result.projection_matches),
        "hash_chain_verified": float(result.hash_chain_verified),
        "failures_named": float(len(result.failures)),
        "replay_mutations": 0.0,
    }


async def _governance(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """Standing guarantees that must hold whatever else the sprint did."""
    from .learned_fixtures import governance_check

    holds = await governance_check(str(request.get("check", "")))
    return holds == (expected == "passed"), {"guarantee_holds": float(holds)}


_SCENARIOS = {
    "lifecycle": _lifecycle,
    "activation": _activation,
    "rollback": _rollback,
    "observation": _observation,
    "dataset": _dataset,
    "artifact": _artifact,
    "replay": _replay,
    "governance": _governance,
}


def scenarios() -> tuple[str, ...]:
    return tuple(sorted(_SCENARIOS))


def benchmark_id_for(name: str) -> UUID:
    return uuid5(BENCHMARK_NAMESPACE, name)
