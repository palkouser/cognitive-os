"""The Sprint 21C3 provider campaign: preflight, then thirty real answers. §S21C3-041/042/032.

Two commands, and the first exists so the second cannot waste thirty live calls on a defect
that a single call would have shown:

    reality_provider_campaign.py preflight --config config/providers.live.local.yaml --live
    reality_provider_campaign.py run       --config config/providers.live.local.yaml --live \
        --output docs/sprints/sprint-21/evidence/...

**Live execution is off unless two independent decisions agree.** The configuration file must
enable the provider *and* set `live_smoke_enabled` — an operator edit, reviewed in Git — and
the caller must pass `--live`. Either alone does nothing, so ordinary CI cannot reach a
provider and a live call is never one arrow-up away in a shell history. Neither gate is a
prompt: §S21C3-041 requires unattended execution after a deliberate configuration, so nothing
here blocks on a terminal, and there is no separate zero-retention waiver — ADR 0088 settled
the data policy for this project's public material in configuration, once, in the open.

What a provider is shown is the task projection, inlined and hash-pinned, re-checked against
the task's control tokens immediately before the call. What it is measured by is the same
hidden suite the offline campaign used, in the same rootless sandbox.

One attempt per task. No retry-until-correct loop exists here, because a campaign that
retried until it liked the answer would be reporting the number of attempts it was willing
to make rather than the provider's accuracy. Resume skips tasks a provider has already
answered, so an interrupted campaign costs calls it has not yet made and no others.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.application.services.learned_intake import LearnedObservationIntake
from cognitive_os.application.services.model_execution import ModelExecutionService
from cognitive_os.application.services.reality_outcome_harvester import RealityOutcomeHarvester
from cognitive_os.coding import reality_leakage, reality_provider
from cognitive_os.coding.hidden_verification import HiddenVerificationRunner, load_bundle
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_provider import ProviderOutcomeClass, RepairPatch
from cognitive_os.coding.reality_tasks import available_templates, template, write_task
from cognitive_os.config.provider_config import load_provider_configuration
from cognitive_os.domain.coding import (
    CodingOutcome,
    CodingOutcomeStatus,
    RepositoryProfile,
    RepositoryProfileStatus,
    WorkspaceDisposition,
)
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ProviderMessage,
    ProviderMessageRole,
    ResponseFormat,
)
from cognitive_os.domain.provider import ProviderKind
from cognitive_os.domain.reality import (
    RealityCandidateManifest,
    RealityCandidateStrategy,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.domain.sandbox import SandboxLimits, SandboxRequest
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.learned.postgres.repository import (
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import PostgresArtifactRepository
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.providers.factory import build_provider
from cognitive_os.providers.openrouter.discovery import parse_catalog
from cognitive_os.providers.registry import ProviderRegistry
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox

REFUSED = 4
NOT_FOUND = 3

CAMPAIGN_NAMESPACE = UUID("b3f7d914-6a28-5e40-9c15-7d2e8b46f0a3")
GENERATION_EPOCH = datetime(2026, 7, 30, tzinfo=UTC)
VERIFIER_PROFILE_HASH = uuid5(CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2

SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

LIMITS = SandboxLimits(
    timeout_seconds=120,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=200_000,
    maximum_stderr_bytes=200_000,
    maximum_artifact_bytes=200_000,
)

#: Ten tasks each, per §S21C3-032. Frozen before execution by `reality_provider.assignment`.
CAMPAIGN_TASK_COUNT = 30


class CampaignRefused(Exception):
    """A policy or structural refusal, carrying the sentence the operator needs to read."""


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True, default=str))


def _config_hash(path: Path) -> str:
    """What was actually loaded. A campaign receipt naming a file proves nothing."""
    return sha256(path.read_bytes()).hexdigest()


def _live_providers(configuration: Any, requested: tuple[str, ...] | None) -> dict[str, Any]:
    """Providers this run may call, or a refusal naming the gate that is closed."""
    names = requested or tuple(configuration.providers)
    live: dict[str, Any] = {}
    for name in names:
        config = configuration.providers.get(name)
        if config is None:
            raise CampaignRefused(f"no provider named {name!r} in this configuration")
        if not (config.enabled and config.live_smoke_enabled):
            continue
        live[name] = config
    if not live:
        raise CampaignRefused(
            "no provider is both enabled and live-enabled in this configuration; live "
            "execution needs a deliberate configuration edit as well as --live"
        )
    return live


# ------------------------------------------------------------------------ S21C3-042


def _client_accepts_extra_body() -> dict[str, Any]:
    """The installed OpenAI client, not a fake transport.

    C2 sent vendor arguments through a stub that accepted anything, so an installed client
    that rejected `extra_body` would have been found only by a live 400. This asks the
    signature directly.
    """
    from openai.resources.chat.completions import AsyncCompletions

    parameters = inspect.signature(AsyncCompletions.create).parameters
    accepted = "extra_body" in parameters
    return {
        "check": "installed_client_accepts_extra_body",
        "passed": accepted,
        "detail": None if accepted else "the installed OpenAI client has no extra_body parameter",
    }


def _variable_price_is_not_free() -> dict[str, Any]:
    """A `-1` price is not a free model. The C2 fixture catalog had no such entry."""
    catalog = parse_catalog(
        {
            "data": [
                {"id": "vendor/auto", "pricing": {"prompt": "-1", "completion": "-1"}},
                {"id": "vendor/model:free", "pricing": {"prompt": "0", "completion": "0"}},
            ]
        },
        provider_id="preflight",
        now=0.0,
    )
    free = set(catalog.free_model_ids)
    passed = free == {"vendor/model:free"}
    return {
        "check": "variable_price_is_not_free",
        "passed": passed,
        "detail": None if passed else f"free set was {sorted(free)}",
    }


def _inline_assembly_carries_no_control_material() -> dict[str, Any]:
    """The prompt is assembled and scanned, not merely typed as safe."""
    from uuid import uuid4 as _uuid4

    from cognitive_os.coding.reality_tasks import build_manifest

    leaks: list[str] = []
    inlined = 0
    for template_id in available_templates():
        item = template(template_id)
        manifest = build_manifest(
            template_id,
            seed=1,
            hidden_bundle_artifact_id=_uuid4(),
            hidden_bundle_hash="0" * 64,
            created_at=GENERATION_EPOCH,
        )
        prompt = reality_provider.build_prompt(manifest.projection, item.visible_files)
        leaks.extend(
            reality_provider.prompt_leaks(prompt, reality_leakage.control_tokens(manifest, item))
        )
        inlined += sum(1 for entry in manifest.projection.files if entry.file_hash in prompt)
    passed = not leaks and inlined > 0
    return {
        "check": "inline_assembly_carries_no_control_material",
        "passed": passed,
        "detail": None if passed else f"{len(leaks)} control tokens reached an assembled prompt",
        "hash_pinned_files": inlined,
    }


async def _tiny_live_call(name: str, config: Any) -> dict[str, Any]:
    """One minimal real call per provider. Structure is judged here; correctness is not."""
    registry = ProviderRegistry()
    registry.register(build_provider(config))
    execution = ModelExecutionService(registry, default_provider_id=config.provider_id)
    request = ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model=getattr(config, "pinned_free_model", None)
        or getattr(config, "default_route", None)
        or config.provider_id,
        system_instructions=reality_provider.PROVIDER_SYSTEM_INSTRUCTIONS,
        messages=(
            ProviderMessage(
                role=ProviderMessageRole.USER,
                content=(
                    "Preflight only. Reply with the JSON object and nothing else: "
                    "set refused to true, refusal_reason to 'preflight', "
                    "unified_diff to an empty string and explanation to 'preflight'."
                ),
            ),
        ),
        response_format=ResponseFormat.JSON_SCHEMA,
        response_schema=reality_provider.STRICT_REPAIR_JSON_SCHEMA,
        max_output_tokens=getattr(config, "maximum_output_tokens", None),
    )
    try:
        response = await execution.execute(request)
    except Exception as error:  # a boundary defect is the finding; the message is the detail
        return {
            "check": "live_call",
            "provider_id": name,
            "passed": False,
            "detail": f"{type(error).__name__}: {error}",
        }
    try:
        RepairPatch.model_validate_json(_json_object(response.content or ""))
        mapped = True
        detail = None
    except Exception as error:
        mapped = False
        detail = f"response did not map to the repair schema: {type(error).__name__}: {error}"
    return {
        "check": "live_call",
        "provider_id": name,
        "passed": mapped,
        "detail": detail,
        "resolved_model": response.resolved_model,
        "finish_reason": response.finish_reason.value,
        "response_hash": sha256((response.content or "").encode()).hexdigest(),
    }


def _json_object(content: str) -> str:
    """The first JSON object in a reply. Providers fence, prefix and apologise."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        text = text.removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in the reply")
    return text[start : end + 1]


async def _preflight(args: argparse.Namespace) -> int:
    if not args.live:
        _emit({"command": "preflight", "refused": True, "reason": "live execution requires --live"})
        return REFUSED
    configuration = load_provider_configuration(args.config)
    try:
        live = _live_providers(configuration, tuple(args.provider) or None)
    except CampaignRefused as refusal:
        _emit({"command": "preflight", "refused": True, "reason": str(refusal)})
        return REFUSED

    checks = [
        _client_accepts_extra_body(),
        _variable_price_is_not_free(),
        _inline_assembly_carries_no_control_material(),
    ]
    for name, config in sorted(live.items()):
        checks.append(await _tiny_live_call(name, config))

    structural = [item for item in checks if not item["passed"]]
    _emit(
        {
            "command": "preflight",
            "config_hash": _config_hash(args.config),
            "providers": sorted(live),
            "checks": checks,
            "structural_failures": len(structural),
            "campaign_may_proceed": not structural,
            "note": "an incorrect model answer is a measured outcome, not a preflight failure",
        }
    )
    return 1 if structural else 0


# ------------------------------------------------------------------------ S21C3-032


async def _ask(config: Any, prompt: str, workspace: Path) -> tuple[Any, RepairPatch | None, str]:
    """One attempt. Returns the response, the parsed answer, and why the answer is absent."""
    if config.kind is ProviderKind.CLI_AGENT:
        # A CLI agent runs where it is pointed. Pointing it at the isolated task workspace
        # is what keeps it away from the repository that holds the answer key.
        config = type(config).model_validate(
            config.model_dump() | {"working_directory": workspace.resolve()}
        )
    registry = ProviderRegistry()
    registry.register(build_provider(config))
    execution = ModelExecutionService(registry, default_provider_id=config.provider_id)
    request = ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model=getattr(config, "pinned_free_model", None)
        or getattr(config, "default_route", None)
        or config.provider_id,
        system_instructions=reality_provider.PROVIDER_SYSTEM_INSTRUCTIONS,
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content=prompt),),
        response_format=ResponseFormat.JSON_SCHEMA,
        response_schema=reality_provider.STRICT_REPAIR_JSON_SCHEMA,
        max_output_tokens=getattr(config, "maximum_output_tokens", None),
    )
    try:
        response = await execution.execute(request)
    except Exception as error:
        return None, None, f"{type(error).__name__}: {error}"
    try:
        answer = RepairPatch.model_validate_json(_json_object(response.content or ""))
    except Exception as error:
        return response, None, f"schema: {type(error).__name__}: {error}"
    return response, answer, ""


async def _run(args: argparse.Namespace) -> int:
    if not args.live:
        _emit({"command": "run", "refused": True, "reason": "live execution requires --live"})
        return REFUSED
    database_url = os.environ.get("COGOS_DATABASE_URL")
    artifact_root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not database_url or not artifact_root:
        _emit(
            {
                "command": "run",
                "refused": True,
                "reason": "COGOS_DATABASE_URL and COGOS_ARTIFACT_ROOT are required; source "
                "the isolated C3 environment first",
            }
        )
        return REFUSED
    if "cognitive_os_dev" in database_url or Path(artifact_root).name == "artifacts":
        _emit(
            {
                "command": "run",
                "refused": True,
                "reason": "refusing the inconsistent development pair; §1.4 forbids C3 writes",
            }
        )
        return REFUSED

    configuration = load_provider_configuration(args.config)
    try:
        live = _live_providers(configuration, tuple(args.provider) or None)
    except CampaignRefused as refusal:
        _emit({"command": "run", "refused": True, "reason": str(refusal)})
        return REFUSED

    templates = tuple(available_templates())[:CAMPAIGN_TASK_COUNT]
    plan = reality_provider.assignment(templates, tuple(sorted(live)))
    already = _completed(args.resume_from)

    engine = create_postgres_engine(database_url)
    report: dict[str, Any] = {
        "command": "run",
        "schema_version": 1,
        "sprint": "21C3",
        "wave": "W4",
        "config_hash": _config_hash(args.config),
        "config_file": args.config.as_posix(),
        "intent": "S21C3-032 provider diversity campaign, one attempt per task, no retries",
        "providers": sorted(live),
        "frozen_assignment": plan,
        "started_at": datetime.now(UTC).isoformat(),
    }
    results: list[dict[str, Any]] = []
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(Path(artifact_root)), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        recorder = CodingOutcomeRecorder(artifacts, CodingEventService(events), events)
        intake = LearnedObservationIntake(
            LearnedEvidenceService(
                PostgresLearnedEvidenceRepository(engine), events=LearnedEventService(events)
            )
        )
        harvester = RealityOutcomeHarvester(artifacts, events, intake)
        sandbox = DockerSandbox(SANDBOX_IMAGE)
        runner = HiddenVerificationRunner(
            sandbox=sandbox, limits=LIMITS, image_digest=SANDBOX_IMAGE
        )
        with tempfile.TemporaryDirectory(prefix="cogos-c3-provider-") as scratch:
            for index, template_id in enumerate(sorted(plan)):
                provider_id = plan[template_id]
                key = f"{template_id}|{provider_id}"
                if key in already:
                    results.append(already[key] | {"resumed": True})
                    continue
                print(f"[{index + 1}/{len(plan)}] {template_id} -> {provider_id}", file=sys.stderr)
                results.append(
                    await _one_task(
                        template_id,
                        provider_id=provider_id,
                        config=live[provider_id],
                        root=Path(scratch) / f"{index:02d}",
                        artifacts=artifacts,
                        recorder=recorder,
                        harvester=harvester,
                        runner=runner,
                        sandbox=sandbox,
                    )
                )
        report["results"] = results
        report["statistics"] = _statistics(results)
        report["finished_at"] = datetime.now(UTC).isoformat()
    finally:
        await engine.dispose()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output.as_posix())
    return 0


def _completed(resume_from: Path | None) -> dict[str, dict[str, Any]]:
    if resume_from is None or not resume_from.exists():
        return {}
    previous = json.loads(resume_from.read_text(encoding="utf-8"))
    return {
        f"{item['template_id']}|{item['provider_id']}": item
        for item in previous.get("results", ())
        if item.get("outcome_class") is not None
    }


async def _one_task(
    template_id: str,
    *,
    provider_id: str,
    config: Any,
    root: Path,
    artifacts: ArtifactService,
    recorder: CodingOutcomeRecorder,
    harvester: RealityOutcomeHarvester,
    runner: HiddenVerificationRunner,
    sandbox: DockerSandbox,
) -> dict[str, Any]:
    """One task, one provider, one attempt, and whatever it produced recorded as an outcome."""
    bundle_artifact = await artifacts.put_bytes(
        f"reality-control:{template_id}:1".encode(), media_type="application/json"
    )
    generated = write_task(
        template_id,
        root=root,
        seed=1,
        hidden_bundle_artifact_id=bundle_artifact.artifact_id,
        hidden_bundle_hash=bundle_artifact.content_hash,
        created_at=GENERATION_EPOCH,
    )
    manifest = generated.manifest
    item = template(template_id)
    prompt = reality_provider.build_prompt(manifest.projection, item.visible_files)
    leaks = reality_provider.prompt_leaks(prompt, reality_leakage.control_tokens(manifest, item))
    if leaks:
        # Never send it. A control token in a request is the answer key on the network.
        raise CampaignRefused(f"{template_id}: assembled prompt carries control tokens {leaks}")

    # `write_task` owns `root/workspace`; the provider's attempt gets its own copy so the
    # pristine tree stays exactly what the hidden suite was built against.
    workspace = root / "attempt"
    shutil.copytree(generated.workspace, workspace)
    response, answer, failure = await _ask(config, prompt, workspace)
    record: dict[str, Any] = {
        "template_id": template_id,
        "provider_id": provider_id,
        "adapter": config.adapter.value,
        "resolved_model": None if response is None else response.resolved_model,
        "prompt_hash": sha256(prompt.encode()).hexdigest(),
        "control_tokens_in_prompt": 0,
        "attempts": 1,
    }
    if answer is None:
        record["outcome_class"] = ProviderOutcomeClass.MALFORMED.value
        record["failure_class"] = "schema_invalid" if failure.startswith("schema:") else "boundary"
        record["reason"] = failure or "no answer"
        record["executed"] = False
        return record

    candidate = reality_provider.classify(
        answer, task=manifest, provider_id=provider_id, sources=item.visible_files
    )
    record["outcome_class"] = candidate.outcome_class.value
    record["reason"] = candidate.reason
    if candidate.outcome_class is ProviderOutcomeClass.MALFORMED:
        record["failure_class"] = "diff_invalid"
    if not candidate.executable:
        record["executed"] = False
        return record

    assert candidate.path is not None and candidate.patched_source is not None
    (workspace / candidate.path).write_text(candidate.patched_source, encoding="utf-8")
    visible = await _visible_exit_code(sandbox, workspace)
    bundle = load_bundle(
        task_id=manifest.task_id,
        host_path=generated.control,
        artifact_id=bundle_artifact.artifact_id,
        artifact_hash=bundle_artifact.content_hash,
    )
    task_run_id = uuid4()
    evidence = await runner.run(
        task_id=manifest.task_id,
        task_run_id=task_run_id,
        workspace=workspace,
        bundle=bundle,
    )
    patch_artifact = await artifacts.put_bytes(
        candidate.unified_diff.encode(),  # type: ignore[union-attr]
        media_type="text/x-diff",
    )
    manifest_record = RealityCandidateManifest(
        candidate_id=candidate.candidate_id,
        task_id=manifest.task_id,
        task_manifest_hash=manifest.content_hash,
        strategy=RealityCandidateStrategy.PROVIDER_PROPOSED,
        source=reality_provider.ADAPTER_SOURCES[config.adapter.value],
        patch_artifact_id=patch_artifact.artifact_id,
        patch_hash=patch_artifact.content_hash,
        generator_profile_id=reality_provider.PROVIDER_PROFILE_ID,
        generator_profile_version=reality_provider.PROVIDER_PROFILE_VERSION,
        provider_id=provider_id,
        resolved_model=None if response is None else response.resolved_model,
        created_at=GENERATION_EPOCH,
    )
    recorded = await recorder.record(
        outcome=CodingOutcome(
            task_run_id=task_run_id,
            status=(
                CodingOutcomeStatus.ACCEPTED if evidence.passed else CodingOutcomeStatus.FAILED
            ),
            repository_profile=RepositoryProfile(
                status=RepositoryProfileStatus.SUPPORTED,
                git_repository=False,
                has_pyproject=True,
                has_pytest=True,
            ),
            base_commit="0" * 40,
            acceptance_decision=_acceptance(task_run_id) if evidence.passed else None,
            workspace_disposition=WorkspaceDisposition.REMOVE,
            policy_denials=(provider_id,),
            completed_at=datetime.now(UTC),
        ),
        task=manifest,
        evidence=evidence,
        candidate=manifest_record,
        correlation_id=task_run_id,
        run_identity=RealityRunIdentity(
            task_id=manifest.task_id,
            task_manifest_hash=manifest.content_hash,
            run_kind=RealityRunKind.CANDIDATE,
            candidate_id=candidate.candidate_id,
            strategy=RealityCandidateStrategy.PROVIDER_PROPOSED,
            source=reality_provider.ADAPTER_SOURCES[config.adapter.value],
            generator_profile_id=reality_provider.PROVIDER_PROFILE_ID,
            verifier_profile_hash=VERIFIER_PROFILE_HASH,
            campaign_version=1,
        ),
    )
    await harvester.harvest(
        event_id=recorded.reference.source_event_id,
        task=manifest,
        correlation_id=task_run_id,
    )
    record.update(
        executed=True,
        published_suite_exit_code=visible,
        hidden_status=evidence.status.value,
        correct=evidence.passed,
        patch_hash=candidate.patch_hash,
        outcome_event_id=str(recorded.reference.source_event_id),
    )
    return record


async def _visible_exit_code(sandbox: DockerSandbox, workspace: Path) -> int:
    sandbox_id = f"cogos-provider-v-{uuid4().hex[:12]}"
    try:
        result = await sandbox.run(
            SandboxRequest(
                sandbox_id=sandbox_id,
                tool_call_id=str(uuid4()),
                task_run_id=str(uuid4()),
                workspace=str(workspace),
                executable="pytest",
                arguments=("-q", "-p", "no:cacheprovider", "tests"),
                limits=LIMITS,
            )
        )
        return int(result.exit_code)
    finally:
        await sandbox.cleanup(sandbox_id)


def _acceptance(task_run_id: UUID) -> Any:
    from uuid import NAMESPACE_URL

    from cognitive_os.domain.acceptance import AcceptanceDecision, AcceptanceDecisionType

    return AcceptanceDecision(
        decision_id=uuid5(NAMESPACE_URL, f"cognitive-os:c3:provider:{task_run_id}"),
        task_run_id=task_run_id,
        policy_id=uuid5(NAMESPACE_URL, "cognitive-os:sprint21c3:python-coding-hidden-acceptance"),
        policy_version="1",
        decision=AcceptanceDecisionType.ACCEPTED,
        criterion_evaluations=(),
        required_passed=True,
        optional_score=1.0,
        reason="every required criterion passed, including hidden verification",
        created_at=datetime.now(UTC),
    )


def _failure_class(item: dict[str, Any]) -> str:
    """Which kind of malformed this was.

    Prefers what the run recorded and falls back to reading the reason, so statistics can be
    recomputed from an evidence file written before the classes were split apart. The reason
    string is what the classifier keyed on in the first place, so the fallback is a re-read
    rather than a guess.
    """
    recorded = item.get("failure_class")
    if recorded:
        return str(recorded)
    reason = str(item.get("reason") or "")
    if reason.startswith("schema:"):
        return "schema_invalid"
    if reason.startswith(("unreadable diff", "the diff", "expected one changed file", "patch")):
        return "diff_invalid"
    return "boundary"


def _statistics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Numerator and denominator for every rate. §S21C3-043 reads this.

    `malformed` is reported as three separate classes because they say different things and
    a single bucket would let one hide behind another. A `boundary` failure is the call
    itself failing — the provider is unavailable, over quota, or returned something the
    adapter could not normalize — and says nothing about repair ability. `schema_invalid` is
    a reply that did not match the shape it was asked for. `diff_invalid` is a well-shaped
    reply whose diff the patch plane cannot read. Only the third is about the model's answer
    to *this* task, and only executed answers say anything about correctness.
    """
    by_provider: dict[str, dict[str, Any]] = {}
    for item in results:
        provider = item["provider_id"]
        bucket = by_provider.setdefault(
            provider,
            {
                "attempted": 0,
                "malformed": 0,
                "boundary_failures": 0,
                "schema_invalid": 0,
                "diff_invalid": 0,
                "refused": 0,
                "executed": 0,
                "correct": 0,
                "resolved_models": Counter(),
            },
        )
        bucket["attempted"] += 1
        outcome = item.get("outcome_class")
        if outcome == ProviderOutcomeClass.MALFORMED.value:
            bucket["malformed"] += 1
            failure = _failure_class(item)
            bucket["boundary_failures" if failure == "boundary" else failure] += 1
        elif outcome == ProviderOutcomeClass.REFUSED.value:
            bucket["refused"] += 1
        if item.get("executed"):
            bucket["executed"] += 1
            bucket["correct"] += int(bool(item.get("correct")))
        if item.get("resolved_model"):
            bucket["resolved_models"][item["resolved_model"]] += 1
    for bucket in by_provider.values():
        bucket["resolved_models"] = dict(sorted(bucket["resolved_models"].items()))
        # Rates carry both terms. A percentage whose denominator is a choice is a claim.
        bucket["correct_over_attempted"] = f"{bucket['correct']}/{bucket['attempted']}"
        bucket["correct_over_executed"] = f"{bucket['correct']}/{bucket['executed']}"
    return {
        "by_provider": by_provider,
        "attempted": len(results),
        "retries_permitted": 0,
        "fallback_results_relabelled_as_success": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    pre = commands.add_parser("preflight", help="bounded structural checks plus one live call")
    pre.add_argument("--config", type=Path, required=True)
    pre.add_argument("--provider", action="append", default=[])
    pre.add_argument("--live", action="store_true", help="explicit opt-in; no prompt follows")

    run = commands.add_parser("run", help="the thirty-outcome provider diversity campaign")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--provider", action="append", default=[])
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--resume-from", type=Path, default=None)
    run.add_argument("--live", action="store_true", help="explicit opt-in; no prompt follows")

    args = parser.parse_args()
    handler = _preflight if args.command == "preflight" else _run
    try:
        return asyncio.run(handler(args))
    except CampaignRefused as refusal:
        _emit({"command": args.command, "refused": True, "reason": str(refusal)})
        return REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
