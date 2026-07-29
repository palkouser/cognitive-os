"""One operator entry point for the governed provider boundary.

Five of the six commands cannot reach a network, read a credential, or write to any store.
The sixth can, and it is the reason the other five exist: an operator who can inspect
configuration, health, replay, fixture integrity and ledger integrity without touching a
provider has no incentive to reach for the live command to answer an ordinary question.

`live-smoke` is gated twice, by two different people's decisions. The configuration file
must set `live_smoke_enabled` for that provider — an operator edit, reviewed in Git — *and*
the caller must pass `--i-understand-this-calls-a-live-provider` at the terminal. Either
alone does nothing. A single flag would make an accidental live call one shell-history
arrow-up away, and a single config setting would make it invisible at the call site.

Every command prints one line of sorted JSON. Nothing prints a prompt, a response, a
credential, an identity, or raw stderr: receipts carry hashes, versions, model identity,
policy, usage, timing and status, which is enough to prove what happened and not enough to
leak what was said. See ADR 0087.

Exit status:

* `0` — the command succeeded and what it checked is healthy;
* `1` — a check failed, a provider is unhealthy, or a live answer was wrong;
* `2` — invalid usage (argparse);
* `3` — the named provider, fixture or store does not exist;
* `4` — refused on policy: live execution was requested without both opt-ins, or outside an
  isolated fixture root.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

NOT_FOUND = 3
REFUSED = 4

#: The replay corpus and the advisory fixture, both committed and both credential-free.
REPLAY_FIXTURE_ROOT = Path("tests/fixtures/providers/replay")
ADVISORY_FIXTURE_ROOT = Path("tests/fixtures/providers/advisory")


def _emit(payload: object) -> None:
    print(json.dumps(payload, default=str, sort_keys=True, separators=(",", ":")))


# --------------------------------------------------------------------------- list


def _describe(config: Any) -> dict[str, Any]:
    """Configuration as an operator needs to read it: names of things, never values."""
    return {
        "provider_id": config.provider_id,
        "adapter": config.adapter.value,
        "kind": config.kind.value,
        "enabled": config.enabled,
        "live_smoke_enabled": config.live_smoke_enabled,
        "model": getattr(config, "model", None) or getattr(config, "default_route", None),
        # The *name* of the variable a credential would come from. Never its value, and
        # never whether it happens to be set — that is a live question, not a config one.
        "credential_source": getattr(config, "api_key_environment_variable", None),
        "executable": getattr(config, "executable", None),
        "working_directory": str(getattr(config, "working_directory", "") or "") or None,
        "default_retention_mode": config.retention.retention_mode.value,
    }


async def _list(args: argparse.Namespace) -> int:
    from cognitive_os.config.provider_config import load_provider_configuration

    configuration = load_provider_configuration(args.config)
    _emit(
        {
            "configuration_version": configuration.configuration_version,
            "providers": [
                _describe(configuration.providers[key]) for key in sorted(configuration.providers)
            ],
        }
    )
    return 0


# ------------------------------------------------------------------------- health


async def _health(args: argparse.Namespace) -> int:
    from cognitive_os.config.provider_config import load_provider_configuration
    from cognitive_os.domain.common import utc_now
    from cognitive_os.domain.provider import ProviderHealth, ProviderStatus
    from cognitive_os.domain.provider import ProviderKind as Kind
    from cognitive_os.providers.factory import build_provider

    configuration = load_provider_configuration(args.config)
    selected = _select(configuration, args.provider)
    if selected is None:
        _emit({"provider_id": args.provider, "found": False})
        return NOT_FOUND

    reports: list[dict[str, Any]] = []
    for provider_id in selected:
        config = configuration.providers[provider_id]
        needs_network = config.kind is Kind.NETWORK_API
        if not config.enabled:
            health = ProviderHealth(
                provider_id=provider_id,
                status=ProviderStatus.UNAVAILABLE,
                checked_at=utc_now(),
                message="provider is disabled in configuration",
            )
        elif needs_network and not args.allow_network:
            # Not an error and not a failure: the operator asked for an offline check and
            # got an honest answer about what could not be checked offline.
            health = ProviderHealth(
                provider_id=provider_id,
                status=ProviderStatus.UNAVAILABLE,
                checked_at=utc_now(),
                configured_model=getattr(config, "model", None),
                message="network probe not attempted; pass --allow-network to reach the API",
            )
        else:
            health = await _probe(build_provider(config))
        reports.append(health.model_dump(mode="json"))

    _emit({"providers": reports})
    # Misconfiguration is a defect in this repository's control of the boundary and fails.
    # Unavailable and unauthenticated are facts about the outside world on an offline run,
    # and the same two-category split the governance ledger uses applies here: an outage
    # must not be reported with the same severity as a broken configuration.
    failed = [
        report
        for report in reports
        if report["status"] == ProviderStatus.MISCONFIGURED.value
        or (args.require_available and report["status"] != ProviderStatus.AVAILABLE.value)
    ]
    return 1 if failed else 0


async def _probe(provider: Any) -> Any:
    try:
        return await provider.health_check()
    finally:
        closer = getattr(provider, "close", None)
        if closer is not None:
            await closer()


# ------------------------------------------------------------------------- replay


async def _replay(_args: argparse.Namespace) -> int:
    """The deterministic path: reviewed fixtures in, known response out, no process."""
    from cognitive_os.domain.model_requests import (
        ModelProviderRequest,
        ProviderMessage,
        ProviderMessageRole,
    )
    from cognitive_os.providers.replay import ReplayProvider

    provider = ReplayProvider.from_directory(REPLAY_FIXTURE_ROOT)
    request = ModelProviderRequest(
        model_call_id=UUID(int=1),
        task_run_id=UUID(int=2),
        correlation_id=UUID(int=3),
        requested_model="replay-model",
        messages=(
            ProviderMessage(role=ProviderMessageRole.USER, content="Return the exact word ready."),
        ),
    )
    response = await provider.complete(request)
    matched = response.content == "ready"
    _emit(
        {
            "check": "provider-replay",
            "fixture_root": REPLAY_FIXTURE_ROOT.as_posix(),
            "resolved_model": response.resolved_model,
            "finish_reason": response.finish_reason.value,
            "matched_reviewed_fixture": matched,
        }
    )
    return 0 if matched else 1


# ------------------------------------------------------------------------ fixture


async def _fixture(args: argparse.Namespace) -> int:
    """Verify the advisory fixture, and verify that its verifier still discriminates.

    Checking the fixture alone would miss the failure that matters most: a verifier that
    accepts everything makes every live smoke pass. So two canned answers are scored here,
    one right and one confidently wrong, and both verdicts have to come out as expected.
    """
    from cognitive_os.providers.advisory_fixture import (
        FixtureVerdict,
        load_advisory_fixture,
        verify_advisory_answer,
    )
    from cognitive_os.providers.advisory_schema import AdvisoryFinding, AdvisoryResult

    root = args.fixture_root
    if not (root / "manifest.json").is_file():
        _emit({"fixture_root": root.as_posix(), "found": False})
        return NOT_FOUND

    loaded = load_advisory_fixture(root)
    manifest = loaded.manifest

    correct = verify_advisory_answer(
        manifest,
        AdvisoryResult(
            summary="self-check",
            findings=(
                AdvisoryFinding(
                    title="arithmetic_mean divides by zero on empty input",
                    severity="high",
                    description=(
                        "statistics_helper.py: arithmetic_mean divides by len(values) with "
                        "no guard, so an empty sequence raises ZeroDivisionError."
                    ),
                ),
            ),
        ),
    )
    wrong = verify_advisory_answer(
        manifest,
        AdvisoryResult(summary="self-check", findings=()),
    )
    discriminates = correct.correct and not wrong.correct

    _emit(
        {
            "check": "advisory-fixture",
            "fixture_id": manifest.fixture_id,
            "fixture_version": manifest.fixture_version,
            "content_hash": manifest.content_hash,
            "files": len(manifest.content_manifest),
            "is_real_governed_outcome": manifest.provenance.is_real_governed_outcome,
            "license": manifest.provenance.license,
            "verifier_accepts_expected_finding": correct.verdict is FixtureVerdict.CORRECT,
            "verifier_rejects_empty_answer": wrong.verdict is FixtureVerdict.NO_FINDINGS,
            "verifier_discriminates": discriminates,
        }
    )
    return 0 if discriminates else 1


# ------------------------------------------------------------- governance verify


async def _governance_verify(_args: argparse.Namespace) -> int:
    # The URL is checked before the PostgreSQL modules are imported. Not style: the
    # credential-free lanes install no PostgreSQL extra, and importing first would turn
    # "there is no database configured" into an unhandled ModuleNotFoundError.
    url = os.environ.get("COGOS_DATABASE_URL")
    if not url:
        _emit(
            {
                "check": "provider-output-governance",
                "found": False,
                "reason": "no database url",
            }
        )
        return NOT_FOUND

    from cognitive_os.infrastructure.learned.postgres.provider_output_health import (
        PostgresProviderOutputHealthService,
    )
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    engine = create_postgres_engine(url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresProviderOutputHealthService(engine).check()
    finally:
        await engine.dispose()
    _emit(report.model_dump(mode="json"))
    return 0 if report.healthy else 1


# --------------------------------------------------------------------- live smoke


class LiveSmokeRefused(Exception):
    """A policy refusal, carrying the sentence the operator needs to read."""


def _resolve_isolation_root(root: Path) -> Path:
    """A live CLI provider runs here, so it must not be anywhere that matters.

    The repository working tree is refused outright. A CLI agent that ignored its read-only
    sandbox would otherwise be editing the very source that proves it did not.
    """
    resolved = root.resolve()
    if not resolved.is_dir():
        raise LiveSmokeRefused(f"isolation root does not exist: {resolved}")
    repository = Path.cwd().resolve()
    if resolved == repository or repository in resolved.parents or resolved in repository.parents:
        raise LiveSmokeRefused(
            "isolation root must be outside the repository working tree; copy the advisory "
            "fixture to a temporary directory and point --isolation-root at that copy"
        )
    return resolved


async def _live_smoke(args: argparse.Namespace) -> int:
    from cognitive_os.config.provider_config import load_provider_configuration

    if not args.i_understand_this_calls_a_live_provider:
        _emit(
            {
                "check": "live-smoke",
                "refused": True,
                "reason": "live execution requires --i-understand-this-calls-a-live-provider",
            }
        )
        return REFUSED

    configuration = load_provider_configuration(args.config)
    config = configuration.providers.get(args.provider)
    if config is None:
        _emit({"provider_id": args.provider, "found": False})
        return NOT_FOUND
    if not (config.enabled and config.live_smoke_enabled):
        _emit(
            {
                "check": "live-smoke",
                "provider_id": args.provider,
                "refused": True,
                "reason": "configuration does not enable live smokes for this provider",
            }
        )
        return REFUSED

    try:
        return await _run_live_smoke(config, args)
    except LiveSmokeRefused as refusal:
        _emit(
            {
                "check": "live-smoke",
                "provider_id": args.provider,
                "refused": True,
                "reason": str(refusal),
            }
        )
        return REFUSED


async def _run_live_smoke(config: Any, args: argparse.Namespace) -> int:
    from time import perf_counter

    from cognitive_os.application.services.governed_teacher import (
        GovernedTeacherService,
        RightsDecision,
        VerifierOutcome,
    )
    from cognitive_os.application.services.model_execution import ModelExecutionService
    from cognitive_os.domain.model_requests import (
        ModelProviderRequest,
        ProviderMessage,
        ProviderMessageRole,
        ResponseFormat,
    )
    from cognitive_os.domain.provider import ProviderKind as Kind
    from cognitive_os.domain.provider_output import (
        ProviderAdapterKind,
        ProviderOutputIntendedUse,
        ProviderOutputRetentionMode,
        ProviderOutputVerifierStatus,
        ProviderRetentionDirective,
        UsageRightsDecision,
    )
    from cognitive_os.providers.advisory_fixture import (
        load_advisory_fixture,
        verify_advisory_answer,
    )
    from cognitive_os.providers.advisory_schema import (
        ADVISORY_JSON_SCHEMA,
        AdvisoryResult,
    )
    from cognitive_os.providers.factory import build_provider
    from cognitive_os.providers.registry import ProviderRegistry
    from cognitive_os.providers.workspace_snapshot import snapshot_workspace

    is_cli = config.kind is Kind.CLI_AGENT
    root = _resolve_isolation_root(args.isolation_root)
    loaded = load_advisory_fixture(root)
    workspace = loaded.workspace

    if is_cli:
        # The adapter runs in `working_directory`; pointing it anywhere but the verified
        # isolated copy is the whole failure mode this command exists to prevent.
        if config.working_directory.resolve() != workspace.resolve():
            raise LiveSmokeRefused(
                "configured working_directory does not match the isolated fixture workspace"
            )
        before = snapshot_workspace(workspace)

    registry = ProviderRegistry()
    registry.register(build_provider(config))
    service = GovernedTeacherService(
        ModelExecutionService(registry, default_provider_id=config.provider_id),
        # In-memory only. A live smoke proves the boundary works; it is not an occasion to
        # write a governance revision into the durable ledger.
        repository=_memory_repository(),
    )

    request = ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model=_requested_model(config),
        system_instructions=None,
        messages=(
            ProviderMessage(
                role=ProviderMessageRole.USER, content=_task_for(loaded, is_cli=is_cli)
            ),
        ),
        response_format=ResponseFormat.JSON_SCHEMA,
        response_schema=ADVISORY_JSON_SCHEMA,
        max_output_tokens=getattr(config, "maximum_output_tokens", None),
    )

    started = perf_counter()
    receipt = await service.execute_with_receipt(
        request,
        directive=ProviderRetentionDirective(
            intended_use=ProviderOutputIntendedUse.TRANSIENT_ADVICE,
            retention_mode=ProviderOutputRetentionMode.NONE,
        ),
        adapter_kind=ProviderAdapterKind(config.adapter.value),
        rights=RightsDecision(decision=UsageRightsDecision.UNKNOWN),
        verifier=VerifierOutcome(status=ProviderOutputVerifierStatus.NOT_RUN),
    )
    elapsed_ms = (perf_counter() - started) * 1000

    answer = _parse_answer(receipt.execution.response, AdvisoryResult)
    verification = verify_advisory_answer(loaded.manifest, answer)

    changes: tuple[Any, ...] = ()
    if is_cli:
        changes = before.difference(snapshot_workspace(workspace))

    payload: dict[str, Any] = {
        "check": "live-smoke",
        "provider_id": receipt.execution.provider_id,
        "adapter": config.adapter.value,
        "requested_model": receipt.execution.requested_model,
        "resolved_model": receipt.execution.resolved_model,
        "finish_reason": receipt.execution.response.finish_reason.value,
        "request_hash": receipt.execution.request_hash,
        "normalized_response_hash": receipt.execution.normalized_response_hash,
        "retention_mode": receipt.execution.retention_mode.value,
        "governance_recorded": receipt.governance is not None,
        "fixture_id": verification.fixture_id,
        "fixture_content_hash": verification.fixture_content_hash,
        "verifier_verdict": verification.verdict.value,
        "answer_correct": verification.correct,
        "answer_hash": verification.answer_hash,
        "missing_concepts": list(verification.missing_concepts),
        # A provider that reports no usage is not an error; the receipt says so rather
        # than inventing zeros that would look like a free call.
        "usage": (
            receipt.execution.response.usage.model_dump(mode="json")
            if receipt.execution.response.usage is not None
            else None
        ),
        "elapsed_ms": round(elapsed_ms, 1),
        "workspace_unchanged": not changes,
        "workspace_changes": [change.model_dump(mode="json") for change in changes],
    }
    _emit(payload)
    return 0 if verification.correct and not changes else 1


def _task_for(loaded: Any, *, is_cli: bool) -> str:
    """The same task, delivered the only way each kind of provider can receive it.

    A CLI agent is given a workspace and reads the file itself, which is the behaviour the
    mutation guard then checks. A network API has no filesystem at all, so the identical
    task sent verbatim asks it to read something it cannot reach — and a model asked to read
    a file it cannot see will confidently describe one it imagined. The first OpenRouter
    live run diagnosed `calculate_mean` and `calculate_median`, neither of which exists.

    Inlining is safe and stays deterministic because every byte is pinned by the fixture's
    own content manifest, which was verified before this ran.
    """
    task = loaded.task_prompt()
    if is_cli:
        return task
    parts = [task, "", "The file follows in full; you have no filesystem access."]
    for relative in sorted(loaded.manifest.content_manifest):
        if not relative.startswith(f"{loaded.manifest.workspace_path}/"):
            continue
        name = relative.split("/", 1)[1]
        body = (loaded.root / relative).read_text(encoding="utf-8")
        parts.extend(("", f"--- {name} ---", body))
    return "\n".join(parts)


def _requested_model(config: Any) -> str:
    """What the receipt should call the model that was asked for.

    A CLI agent has no model slug unless the operator pinned one; naming the provider is
    honest, where an empty string would make two different receipts look alike.
    """
    return (
        getattr(config, "model", None)
        or getattr(config, "default_route", None)
        or f"{config.adapter.value}:default"
    )


def _memory_repository() -> Any:
    from cognitive_os.infrastructure.learned.memory_provider_output import (
        InMemoryProviderOutputRepository,
    )

    return InMemoryProviderOutputRepository()


def _parse_answer(response: Any, schema: Any) -> Any:
    """Structured output first, then the text body. `None` means unparsable, which the
    verifier treats as a wrong answer rather than an exception."""
    if response.structured_output is not None:
        try:
            return schema.model_validate(response.structured_output)
        except ValueError:
            return None
    try:
        return schema.model_validate_json(response.content)
    except ValueError:
        return None


# --------------------------------------------------------------------------- glue


def _select(configuration: Any, provider: str | None) -> list[str] | None:
    if provider is None:
        return sorted(configuration.providers)
    if provider not in configuration.providers:
        return None
    return [provider]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="provider", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    listing = commands.add_parser("list", help="show configured providers, names only")
    listing.add_argument("--config", type=Path, required=True)
    listing.set_defaults(handler=_list)

    health = commands.add_parser("health", help="typed provider health; offline by default")
    health.add_argument("--config", type=Path, required=True)
    health.add_argument("--provider", default=None)
    health.add_argument(
        "--allow-network",
        action="store_true",
        help="permit network-API health probes; CLI probes are always local",
    )
    health.add_argument(
        "--require-available",
        action="store_true",
        help="exit 1 unless every selected provider reports available",
    )
    health.set_defaults(handler=_health)

    replay = commands.add_parser("replay", help="deterministic replay smoke, no process")
    replay.set_defaults(handler=_replay)

    fixture = commands.add_parser("fixture", help="verify the advisory fixture and its verifier")
    fixture.add_argument("--fixture-root", type=Path, default=ADVISORY_FIXTURE_ROOT)
    fixture.set_defaults(handler=_fixture)

    governance = commands.add_parser(
        "governance-verify", help="read-only provider-output ledger integrity"
    )
    governance.set_defaults(handler=_governance_verify)

    live = commands.add_parser("live-smoke", help="one bounded, operator-approved live call")
    live.add_argument("--config", type=Path, required=True)
    live.add_argument("--provider", required=True)
    live.add_argument(
        "--isolation-root",
        type=Path,
        required=True,
        help="a verified copy of the advisory fixture, outside the repository",
    )
    live.add_argument(
        "--i-understand-this-calls-a-live-provider",
        action="store_true",
        help="the runtime half of the two-part live opt-in",
    )
    live.set_defaults(handler=_live_smoke)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    return asyncio.run(arguments.handler(arguments))


if __name__ == "__main__":
    sys.exit(main())
