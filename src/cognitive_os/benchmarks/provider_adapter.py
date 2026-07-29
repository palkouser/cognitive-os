"""Executable Sprint 21C2 provider boundary benchmark adapter.

Each case really runs the code it names — the OpenRouter router, the two CLI parsers, the
advisory verifier, the governed teacher, the mutation guard, the secret scanner — and
compares what happened with what the manifest declared. Nothing is looked up in an
expectation table, so a regression in any of those paths fails the benchmark instead of
being absorbed by it.

The whole family is credential-free, network-free, binary-free and CPU-only, and that is a
requirement rather than a convenience: a gate that needed an API key or an installed CLI
would be a gate with a standing reason to be skipped, and it would be skipped on exactly the
day something broke.

Nothing here measures whether a teacher is *useful*. Every case measures whether a **policy**
held: a refusal happened, a retention downgrade was recorded, a mutation was caught, a
reused idempotency key was rejected. Passing the whole set says nothing about Gate L2.
See ADR 0087.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import UUID, uuid5

from cognitive_os.domain.benchmarks import (
    BenchmarkCase,
    BenchmarkCaseResult,
    BenchmarkCaseStatus,
)

#: Fixed, so two runs of the same manifest produce identical receipts and hashes.
BENCHMARK_NAMESPACE = UUID("6d3f0b28-91a7-5c44-8f16-2ad5e79c4b60")
FIXTURE_NOW = datetime(2026, 7, 28, tzinfo=UTC)


async def provider_benchmark_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    request = case.problem_request
    scenario = str(request.get("scenario", ""))
    # `expected` is a reserved matrix key routed to `expected_outputs["status"]`. Reading it
    # from the request would silently default every case to the happy path.
    expected = str(case.expected_outputs.get("status", "passed"))
    started = perf_counter()

    metrics: dict[str, float] = {
        "provider_calls": 0.0,
        "network_calls": 0.0,
        "credential_reads": 0.0,
        "subprocesses_started": 0.0,
        "gpu_calls": 0.0,
        "repository_writes": 0.0,
        "real_governed_outcomes": 0.0,
    }

    handler = _SCENARIOS.get(scenario)
    if handler is None:
        matched, extra = False, {"unknown_scenario": 1.0}
    else:
        matched, extra = await handler(request, expected)

    metrics.update(extra)
    metrics["expected_policy_matched"] = float(matched)
    metrics["expected_outcome_matched"] = float(matched)
    metrics["elapsed_seconds"] = perf_counter() - started
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED if matched else BenchmarkCaseStatus.FAILED,
        started_at=FIXTURE_NOW,
        finished_at=FIXTURE_NOW,
        metrics=metrics,
    )


# ------------------------------------------------------------------- OpenRouter


async def _openrouter_route(
    request: dict[str, Any], expected: str
) -> tuple[bool, dict[str, float]]:
    """Free-only routing, a paid refusal, and a catalog that offers nothing usable."""
    from cognitive_os.providers.errors import (
        ProviderBudgetExceededError,
        ProviderInvalidResponseError,
        ProviderModelUnavailableError,
    )
    from cognitive_os.providers.openrouter.discovery import parse_catalog, resolve_route

    from .provider_fixtures import OPENROUTER_CATALOG, OPENROUTER_PAID_ONLY_CATALOG

    payloads: dict[str, Any] = {
        "free": OPENROUTER_CATALOG,
        "paid_only": OPENROUTER_PAID_ONLY_CATALOG,
        "empty": {"data": []},
        "malformed": {"data": "not-a-list"},
    }
    payload = payloads[str(request.get("catalog", "free"))]
    routes = {
        "default": "openrouter/free",
        "free": "vendor/free-small",
        "paid": "vendor/paid-large",
        "unknown": "vendor/absent",
        "unpriced": "vendor/unpriced",
    }
    route = routes[str(request.get("route", "default"))]

    try:
        catalog = parse_catalog(payload, provider_id="openrouter", now=0.0)
        resolved = resolve_route(
            provider_id="openrouter",
            catalog=catalog,
            requested=route,
            default_route="openrouter/free",
            pinned_free_model=None,
            require_free_model=bool(request.get("require_free", True)),
            maximum_spend_usd=float(request.get("maximum_spend_usd", 0.0)),
        )
    except ProviderInvalidResponseError:
        outcome, free_models = "invalid_catalog", 0
    except ProviderModelUnavailableError:
        outcome, free_models = "unavailable", 0
    except ProviderBudgetExceededError:
        outcome, free_models = "budget_refused", 0
    else:
        outcome = "routed"
        free_models = len(catalog.free_model_ids)
        # A free-only policy that resolved to something is only correct if what it resolved
        # to is actually free or is the router slug OpenRouter resolves server-side.
        if request.get("require_free", True) and resolved != "openrouter/free":
            model = catalog.get(resolved)
            if model is None or not model.is_free:
                outcome = "leaked_paid_route"

    return outcome == expected, {"free_models_in_catalog": float(free_models)}


async def _openrouter_response(
    request: dict[str, Any], expected: str
) -> tuple[bool, dict[str, float]]:
    """Normalizing a chat completion, including the shapes that must fail closed."""
    from cognitive_os.providers.errors import ProviderInvalidResponseError
    from cognitive_os.providers.openai_compatible import map_response

    from .provider_fixtures import advisory_answer, openai_completion

    body = openai_completion(json.dumps(advisory_answer()))
    defect = str(request.get("defect", "none"))
    if defect == "no_choices":
        body["choices"] = []
    elif defect == "missing_model":
        body.pop("model")
    elif defect == "null_content":
        body["choices"][0]["message"]["content"] = None
    elif defect == "length_truncated":
        body["choices"][0]["finish_reason"] = "length"
    elif defect == "unknown_finish_reason":
        body["choices"][0]["finish_reason"] = "something_new"

    try:
        response = map_response(body, _a_request(), provider_id="openrouter", latency_ms=12.0)
    except ProviderInvalidResponseError:
        return expected == "invalid", {"warnings": 0.0}

    outcome = "mapped"
    if response.finish_reason.value == "length":
        outcome = "truncated"
    return outcome == expected, {
        "warnings": float(len(response.warnings)),
        "usage_reported": float(response.usage is not None),
    }


# ------------------------------------------------------------------ Claude Code


async def _claude_envelope(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """The `--output-format json` envelope, and every shape that must not be coerced."""
    from cognitive_os.providers.claude_code.advisory import map_advisory_response
    from cognitive_os.providers.errors import ProviderInvalidResponseError

    from .provider_fixtures import advisory_answer, claude_envelope

    defect = str(request.get("defect", "none"))
    stdout = claude_envelope(advisory_answer())
    if defect == "error_result":
        stdout = claude_envelope(advisory_answer(), is_error=True)
    elif defect == "result_as_string":
        stdout = claude_envelope(json.dumps(advisory_answer()))
    elif defect == "not_json":
        stdout = "Claude is thinking..."
    elif defect == "not_object":
        stdout = "[1, 2, 3]"
    elif defect == "missing_result":
        stdout = json.dumps({"type": "result", "subtype": "success", "is_error": False})
    elif defect == "schema_mismatch":
        stdout = claude_envelope({"verdict": "looks fine"})

    try:
        response = map_advisory_response(
            stdout, _a_request(), provider_id="claude-code", duration_ms=900.0
        )
    except ProviderInvalidResponseError:
        return expected == "invalid", {}

    structured = float(response.structured_output is not None)
    return expected == "mapped", {"structured_output_present": structured}


# ------------------------------------------------------------------- Codex CLI


async def _codex_events(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """JSONL parsing, where an unrecognised event must fail closed rather than be skipped."""
    from cognitive_os.providers.codex_cli.mapping import parse_advisory_result
    from cognitive_os.providers.errors import ProviderInvalidResponseError

    from .provider_fixtures import advisory_answer, codex_stream

    defect = str(request.get("defect", "none"))
    stdout = codex_stream(advisory_answer())
    if defect == "fenced":
        stdout = codex_stream("```json\n" + json.dumps(advisory_answer()) + "\n```")
    elif defect == "malformed_line":
        stdout = codex_stream(advisory_answer()) + '{"type": "item.compl'
    elif defect == "failure_event":
        stdout = codex_stream(advisory_answer(), events=({"type": "turn.failed"},))
    elif defect == "unknown_event":
        stdout = codex_stream(advisory_answer(), events=({"type": "item.exfiltrated"},))
    elif defect == "ignored_event":
        stdout = codex_stream(advisory_answer(), events=({"type": "turn.delta"},))
    elif defect == "no_final_message":
        stdout = json.dumps({"type": "thread.started"}) + "\n"
    elif defect == "schema_mismatch":
        stdout = codex_stream({"verdict": "looks fine"})

    try:
        result = parse_advisory_result(stdout, provider_id="codex-cli")
    except ProviderInvalidResponseError:
        return expected == "invalid", {}
    return expected == "mapped", {"findings": float(len(result.findings))}


# ----------------------------------------------------------- advisory verifier


async def _advisory_verify(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """The independent verifier, including the answers that look right and are not."""
    from cognitive_os.providers.advisory_fixture import (
        DEFAULT_FIXTURE_PATH,
        load_advisory_fixture,
        verify_advisory_answer,
    )
    from cognitive_os.providers.advisory_schema import AdvisoryFinding, AdvisoryResult

    from .provider_fixtures import advisory_answer

    fixture = load_advisory_fixture(DEFAULT_FIXTURE_PATH).manifest
    answer = str(request.get("answer", "correct"))
    result: AdvisoryResult | None
    if answer == "correct":
        result = AdvisoryResult.model_validate(advisory_answer())
    elif answer == "empty":
        result = AdvisoryResult.model_validate(advisory_answer(correct=False))
    elif answer == "wrong_defect":
        result = _finding_result("running_total in statistics_helper.py returns floats")
    elif answer == "shotgun":
        result = AdvisoryResult(
            summary="several notes",
            findings=(
                _one("statistics_helper.py has a problem"),
                _one("something raises ZeroDivisionError"),
            ),
        )
    elif answer == "too_many":
        result = AdvisoryResult(
            summary="everything",
            findings=tuple(
                [AdvisoryFinding.model_validate(advisory_answer()["findings"][0])]
                + [_one(f"style note {index}") for index in range(4)]
            ),
        )
    else:
        result = None

    verification = verify_advisory_answer(fixture, result)
    outcome = "correct" if verification.correct else "rejected"
    return outcome == expected, {
        "matched_concepts": float(len(verification.matched_concepts)),
        "missing_concepts": float(len(verification.missing_concepts)),
    }


def _one(text: str) -> Any:
    from cognitive_os.providers.advisory_schema import AdvisoryFinding

    return AdvisoryFinding(title="note", severity="low", description=text)


def _finding_result(text: str) -> Any:
    from cognitive_os.providers.advisory_schema import AdvisoryResult

    return AdvisoryResult(summary="reviewed", findings=(_one(text),))


# --------------------------------------------------------------- governed path


async def _governance(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """The governed teacher: retention as directive *intersected* with evidence."""
    from pydantic import ValidationError

    from cognitive_os.domain.memory import MemorySensitivity
    from cognitive_os.domain.provider_output import (
        ProviderAdapterKind,
        ProviderOutputIntendedUse,
        ProviderOutputRetentionMode,
        ProviderOutputVerifierStatus,
        ProviderRetentionDirective,
        UsageRightsDecision,
    )
    from cognitive_os.providers.errors import ProviderConfigurationError

    from .provider_harness import (
        RightsDecision,
        VerifierOutcome,
        a_request,
        build_governed_teacher,
    )

    variant = str(request.get("variant", "hash_only"))
    leaky = variant == "scan_failed"
    service, provider, repository = build_governed_teacher(leaky=leaky)

    requested = ProviderOutputRetentionMode(str(request.get("retention", "hash_only")))
    sensitivity = MemorySensitivity(str(request.get("sensitivity", "public")))
    rights = UsageRightsDecision(str(request.get("rights", "verified")))
    deletion = bool(request.get("physical_deletion_required", False))

    try:
        directive = ProviderRetentionDirective(
            intended_use=ProviderOutputIntendedUse.CORPUS_CANDIDATE,
            retention_mode=requested,
            sensitivity=sensitivity,
            physical_deletion_required=deletion,
        )
    except ValidationError:
        # A directive the contract cannot satisfy is refused when it is *written*, not
        # quietly downgraded later. Restricted content and a physical-deletion obligation
        # are both impossible against an immutable Artifact Store, and the caller has to
        # say hash_only or none out loud rather than discover it in a receipt.
        return expected == "directive_refused", {"provider_calls": 0.0}
    # `mock` is the stub provider's own ID, so this asks the service to accept a provider
    # verifying itself. It must refuse: schema validity proves shape, not correctness.
    verifier_identity = "mock" if variant == "self_verification" else "synthetic-verifier"

    async def execute() -> Any:
        return await service.execute_with_receipt(
            a_request(),
            directive=directive,
            adapter_kind=ProviderAdapterKind.OPENROUTER,
            rights=RightsDecision(decision=rights, evidence_hash="a" * 64),
            verifier=VerifierOutcome(
                status=ProviderOutputVerifierStatus.PASSED,
                identity=verifier_identity,
                evidence_hash="c" * 64,
            ),
        )

    try:
        receipt = await execute()
    except ProviderConfigurationError:
        return expected == "refused", {"provider_calls": float(provider.calls)}

    outcome = receipt.execution.retention_mode.value
    metrics = {
        "provider_calls": float(provider.calls),
        "repository_writes": float(await repository.count_revisions()),
        "real_governed_outcomes": 0.0,
    }

    governance = receipt.governance
    if variant == "reuse_same_execution":
        # Re-recording the same execution finds the first record: a genuine retry, and the
        # only one of the two questions "retries cannot duplicate records" is asking.
        if governance is None:
            return False, metrics
        again = await repository.record_output(governance)
        metrics["repository_writes"] = float(await repository.count_revisions())
        same = again.provider_output_revision_id == governance.provider_output_revision_id
        return (expected == "idempotent") == same, metrics

    if variant == "reuse_different_execution":
        # The other question. Re-executing under the same model call ID produces a second
        # answer and a second completed envelope, so the content differs. Accepting it would
        # let a caller with a reused ID overwrite a governance decision.
        from cognitive_os.domain.provider_output import ProviderOutputRepositoryError

        try:
            await execute()
        except ProviderOutputRepositoryError as error:
            return expected == "conflict", metrics | {
                "conflict": float(error.conflict.value == "idempotency_key_reused")
            }
        return expected == "accepted", metrics

    return outcome == expected, metrics


async def _selection(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """Whether a recorded revision may be *newly selected*, which is not the same question
    as whether it was validly recorded."""
    from cognitive_os.domain.provider_output import (
        ProviderOutputVerifierStatus,
        SecretScanStatus,
        UsageRightsDecision,
    )

    from .provider_harness import a_governance_record

    defect = str(request.get("defect", "none"))
    overrides: dict[str, Any] = {}
    moment = FIXTURE_NOW
    if defect == "rights_unknown":
        overrides["rights_decision"] = UsageRightsDecision.UNKNOWN
    elif defect == "scan_failed":
        overrides["secret_scan_status"] = SecretScanStatus.FAILED
    elif defect == "verifier_failed":
        overrides["verifier_status"] = ProviderOutputVerifierStatus.FAILED
    elif defect == "expired":
        overrides["expires_at"] = FIXTURE_NOW + timedelta(hours=1)
        moment = FIXTURE_NOW + timedelta(hours=2)
    elif defect == "deletion_required":
        overrides["physical_deletion_required"] = True

    record = a_governance_record(**overrides)
    selectable = record.is_selectable_at(moment)
    outcome = "selectable" if selectable else "refused"
    return outcome == expected, {"refusal_reasons": float(len(record.selection_refusals(moment)))}


async def _intake(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """A provider answer reaching learned intake is never a real governed run."""
    from cognitive_os.application.services.learned_intake import (
        PROVIDER_ADVISORY_SOURCE_KINDS,
        REAL_GOVERNED_SOURCE_KINDS,
        VERIFIER_BACKED_SOURCE_KINDS,
    )
    from cognitive_os.infrastructure.learned.memory_provider_output import (
        source_kind_for,
    )

    from .provider_harness import a_governance_record

    record = a_governance_record(adapter=str(request.get("adapter", "openrouter")))
    kind = source_kind_for(record.adapter_kind.value, provider_id=record.provider_id)
    real = kind in REAL_GOVERNED_SOURCE_KINDS
    verifier_backed = kind in VERIFIER_BACKED_SOURCE_KINDS
    declared = kind in PROVIDER_ADVISORY_SOURCE_KINDS
    outcome = "advisory" if (declared and verifier_backed and not real) else "misclassified"
    return outcome == expected, {"real_governed_outcomes": float(real)}


# ------------------------------------------------------- mutation and cleanup


async def _mutation(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """The content-based guard, on the four shapes a mutation can take."""
    from tempfile import TemporaryDirectory

    from cognitive_os.providers.workspace_snapshot import snapshot_workspace

    change = str(request.get("change", "none"))
    with TemporaryDirectory(prefix="cogos-benchmark-") as directory:
        from pathlib import Path

        root = Path(directory)
        (root / "kept.py").write_text("value = 1\n", encoding="utf-8")
        (root / "also.py").write_text("value = 2\n", encoding="utf-8")
        before = snapshot_workspace(root)

        if change == "created":
            (root / "new.py").write_text("value = 3\n", encoding="utf-8")
        elif change == "modified":
            (root / "kept.py").write_text("value = 99\n", encoding="utf-8")
        elif change == "deleted":
            (root / "also.py").unlink()
        elif change == "same_size":
            # The case a size or mtime check would miss.
            (root / "kept.py").write_text("value = 2\n", encoding="utf-8")
        elif change == "symlink_swap":
            (root / "also.py").unlink()
            (root / "also.py").symlink_to(root / "kept.py")

        changes = before.difference(snapshot_workspace(root))

    outcome = "clean" if not changes else "detected"
    return outcome == expected, {"workspace_changes": float(len(changes))}


async def _cleanup(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """The runner's temporary directory lives outside the workspace and does not survive."""
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from cognitive_os.config.provider_config import CliProcessLimits
    from cognitive_os.providers.cli_process import BoundedCliRunner
    from cognitive_os.providers.workspace_snapshot import snapshot_workspace

    with TemporaryDirectory(prefix="cogos-benchmark-") as directory:
        workspace = Path(directory) / "workspace"
        workspace.mkdir()
        (workspace / "kept.py").write_text("value = 1\n", encoding="utf-8")
        before = snapshot_workspace(workspace)

        runner = BoundedCliRunner(
            provider_id="benchmark",
            executable="/bin/true",
            working_directory=workspace,
            limits=CliProcessLimits(),
            environment_allowlist=("PATH",),
        )
        async with runner.temporary_directory() as scratch:
            (scratch / "schema.json").write_text("{}", encoding="utf-8")
            outside = workspace.resolve() not in scratch.resolve().parents
            existed = scratch.is_dir()
        removed = not scratch.exists()
        changes = before.difference(snapshot_workspace(workspace))

    clean = outside and existed and removed and not changes
    outcome = "clean" if clean else "leaked"
    return outcome == expected, {
        "temporary_directory_removed": float(removed),
        "temporary_directory_outside_workspace": float(outside),
        "workspace_changes": float(len(changes)),
    }


async def _scan(request: dict[str, Any], expected: str) -> tuple[bool, dict[str, float]]:
    """The secret scanner, run on the unredacted value the way the governed path runs it."""
    from cognitive_os.providers.redaction import redact_value, scan_for_secrets

    payloads: dict[str, Any] = {
        "clean": {"content": "the helper subtracts where it should add"},
        "api_key": {"content": "the key is sk-or-v1-" + "a" * 32},
        "bearer": {"headers": "Authorization: Bearer " + "b" * 40},
        # A harmless value under a secret-shaped key: the scanner must fail this on the
        # field name alone, which is exactly why the scanner also flags it here.
        "secret_named_field": {"api_key": "not-a-key"},  # pragma: allowlist secret
    }
    payload = payloads[str(request.get("payload", "clean"))]

    result = scan_for_secrets(payload, extra_secrets=())
    outcome = result.status.value
    # Redaction must not be what makes a scan pass: scanning the redacted value would
    # always pass, which is the failure mode the ordering exists to prevent.
    redacted_result = scan_for_secrets(redact_value(payload), extra_secrets=())
    hid_it = not result.passed and redacted_result.passed

    return (outcome == expected), {
        "matched_rules": float(sum(result.matched_rules.values())),
        "redaction_would_have_hidden_it": float(hid_it),
        "evidence_hash_present": float(bool(result.evidence_hash)),
    }


# --------------------------------------------------------------------- shared


def _a_request() -> Any:
    from cognitive_os.domain.model_requests import (
        ModelProviderRequest,
        ProviderMessage,
        ProviderMessageRole,
    )

    return ModelProviderRequest(
        model_call_id=uuid5(BENCHMARK_NAMESPACE, "request"),
        task_run_id=uuid5(BENCHMARK_NAMESPACE, "task"),
        correlation_id=uuid5(BENCHMARK_NAMESPACE, "correlation"),
        requested_model="openrouter/free",
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content="review this"),),
    )


_SCENARIOS: dict[str, Any] = {
    "openrouter_route": _openrouter_route,
    "openrouter_response": _openrouter_response,
    "claude_envelope": _claude_envelope,
    "codex_events": _codex_events,
    "advisory_verify": _advisory_verify,
    "governance": _governance,
    "selection": _selection,
    "intake": _intake,
    "mutation": _mutation,
    "cleanup": _cleanup,
    "scan": _scan,
}

__all__ = ["BENCHMARK_NAMESPACE", "FIXTURE_NOW", "provider_benchmark_case"]
