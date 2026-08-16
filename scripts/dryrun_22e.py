"""S22E-120. Dry run 1: a mined weakness, a live provider draft, and a refusal at a real gate.

§2.2(c) defines a dry run as "a complete lifecycle that stops short of merge — every stage
entered in order through the released transitions, stage-skipping refused, experience compiled
at the end", and W1 owes the first of three: on a real ledger entry, with a real
provider-assisted candidate, carried to a deliberate gate rejection.

**What "provider-assisted" means here is the released answer, not a convenient one.** The plan
says "a provider-assisted candidate in an isolated worktree", and the obvious reading — the
provider writes the patch — is one the released code refuses twice over:

* `ClaudeCodeProviderConfig.tools_and_mode_are_read_only` rejects any mutating tool and any
  permission mode that permits mutation, so **no released provider configuration in this
  repository can write a file**;
* `merge_provider_draft` refuses a draft containing `diff --git`, `apply_patch`, `git commit`
  or `git push` outright — the host verification treats a provider-supplied patch as an
  executable instruction and raises `ProposalAuthorityError`.

So the released architecture is: the provider assists the **proposal**, and the host applies
the **change**. `ProposalGenerationMode.PROVIDER_ASSISTED` is set by `merge_provider_draft`
after host verification has checked that the provider did not change the proposal type, cite an
unknown source, expand the scope, or smuggle in an instruction. The patch is then applied by
`deterministic_replace`, which takes a `before`, an `after` and the hash the result must have.
That is `§2.2(b)`'s "the provider's authority ends at the proposal" implemented rather than
promised, and this driver follows it exactly.

**The rejection is deliberate and the gate is real.** The candidate is a genuine repair of
ledger entry L1 applied in a real worktree, and it is refused at a gate that actually ran.

    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/dryrun_22e.py --entry L1
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

DRY_RUN_TIME = "2026-08-16T00:00:00Z"

#: This sprint's own live provider configuration, untracked like every other. Read-only by
#: released contract; it exists so the draft comes from a real model rather than a fixture.
PROVIDER_CONFIG = REPO / "config/providers.s22e.local.yaml"

#: The provider whose draft this dry run uses. One of W0's four frozen external providers, so
#: nothing about the enumeration widens here.
PROVIDER_ID = "claude-code"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# The prompt, and what the provider is and is not asked for
# ---------------------------------------------------------------------------


def component_identity(subject: Any) -> str:
    """The identity the host will pin the draft's scope to, from a proposal *or* a source.

    `ProposalGeneratorPort.draft` is handed the frozen `ProposalSourceSnapshot`, not the
    revision, so a draft built from the revision's `change_specification` would only work on
    the path that does not use the released port. `build_change_specification` derives the
    identity from the source's first affected component, so this derives it the same way and
    the two paths cannot disagree.
    """
    specification = getattr(subject, "change_specification", None)
    if specification is not None:
        return str(specification.current_identity)
    components = subject.weakness_record.affected_components
    return str(components[0]) if components else "source_code_change"


def proposal_surface(subject: Any) -> str:
    specification = getattr(subject, "change_specification", None)
    if specification is not None:
        return str(specification.change_surface)
    return "source_code_change"


def build_draft_prompt(entry: dict[str, Any], proposal: Any) -> str:
    """Ask for structured advice about a proposal that already exists.

    The provider is *not* asked what to change — the proposal's change specification is
    already fixed by the released `HarnessProposalService`, mined from the weakness. It is
    asked for advice about that fixed specification.

    **W1-F6. The prompt asks for the shape the adapter enforces, not a shape of its own.** The
    first version of this function asked for the eight fields of `ProviderProposalDraft`, while
    `ClaudeCodeAdvisoryProvider.safety_arguments` puts `--json-schema <AdvisoryResult>` on the
    command line unconditionally. The caller and the boundary therefore demanded two different
    JSON objects from one model, and what came back was neither: prose, which arrived at
    `read_draft` as a malformed answer and would have been recorded as a provider failure.
    It was not a provider failure. It was a caller asking for something the boundary had
    already forbidden, and nothing in the released code compares the two — `safety_arguments`
    takes an optional `schema_json`, and a caller that never passes one has no way to learn
    which schema it just silently agreed to.

    So the prompt below names the advisory fields, and `read_draft` maps them onto the draft
    contract. The mapping is the host's work, which is where it belongs: §2.2(b)'s boundary is
    that the provider advises and the host decides what the advice becomes.

    It is told, in the prompt rather than only in the verifier, that a patch will be refused.
    A boundary a caller only enforces after the fact is a boundary the caller pays for on
    every call.
    """
    reproduction = json.dumps(entry["reproduction"], indent=1, sort_keys=True)[:2000]
    identity = component_identity(proposal)
    surface = proposal_surface(proposal)
    return (
        "You are advising on an already-registered software change proposal in a governed "
        "repository. The change specification is fixed; do not propose a different one.\n\n"
        f"Weakness (sealed finding {entry['finding']}): {entry['summary']}\n"
        f"Change surface: {entry['change_surface']}\n"
        f"Risk class: {entry['risk_class']}\n"
        f"Registered proposal type: {surface}\n"
        f"Component identity: {identity}\n\n"
        f"Reproduction evidence:\n{reproduction}\n\n"
        "Answer in the advisory result shape you have been given a schema for:\n"
        "- `summary`: what the repair changes, in one or two sentences;\n"
        "- `findings`: one finding whose `title` is the reason the repair is correct and "
        "whose `description` states the behaviour to change and the behaviour to preserve;\n"
        "- `recommendations`: alternative approaches that were available and not taken;\n"
        "- `risks`: what would have to be undone if this were reverted;\n"
        "- `verification_steps`: how a reviewer would check the repair worked.\n\n"
        "Constraints, which the host enforces and will refuse on:\n"
        "- do NOT include a patch, a diff, `diff --git`, `apply_patch`, or any git command; "
        "the host applies changes itself, and treats a supplied patch as an executable "
        "instruction and refuses the whole draft;\n"
        f"- stay inside the component named above ('{identity}'); a draft that names another "
        "component is refused as a scope expansion;\n"
        "- describe the repair in prose, never as code."
    )


# ---------------------------------------------------------------------------
# The live call, through the governed boundary
# ---------------------------------------------------------------------------


async def request_draft(prompt: str, proposal: Any) -> dict[str, Any]:
    """One live provider call, through the same governed boundary 22D's teacher used.

    `GovernedTeacherService.execute_with_receipt`, so the call leaves a receipt carrying a
    retention directive and a rights decision. Retention is `none` and the rights decision is
    `unknown`: nobody has cleared a model's output for reuse, and this dry run does not reuse
    it — the draft is verified by the host, merged as *advice*, and the receipt keeps the
    request and response hashes so one value survives that a later reader can check.
    """
    from cognitive_os.application.services.governed_teacher import (
        GovernedTeacherService,
        RightsDecision,
        VerifierOutcome,
    )
    from cognitive_os.application.services.model_execution import ModelExecutionService
    from cognitive_os.config.provider_config import load_provider_configuration
    from cognitive_os.domain.model_requests import (
        ModelProviderRequest,
        ProviderMessage,
        ProviderMessageRole,
    )
    from cognitive_os.domain.provider_output import (
        ProviderAdapterKind,
        ProviderOutputIntendedUse,
        ProviderOutputRetentionMode,
        ProviderOutputVerifierStatus,
        ProviderRetentionDirective,
        UsageRightsDecision,
    )
    from cognitive_os.infrastructure.learned.memory_provider_output import (
        InMemoryProviderOutputRepository,
    )
    from cognitive_os.providers.factory import build_provider
    from cognitive_os.providers.registry import ProviderRegistry

    configuration = load_provider_configuration(PROVIDER_CONFIG)
    config = configuration.providers.get(PROVIDER_ID)
    if config is None:
        raise RuntimeError(f"{PROVIDER_ID} is not configured in {PROVIDER_CONFIG.name}")
    # The same two keys `scripts/provider.py` requires. This driver does not get a cheaper
    # door into a live provider than the operator entry point has.
    if not (config.enabled and config.live_smoke_enabled):
        raise RuntimeError(f"{PROVIDER_ID} is configured but live execution is not enabled")

    registry = ProviderRegistry()
    registry.register(build_provider(config))
    service = GovernedTeacherService(
        ModelExecutionService(registry, default_provider_id=config.provider_id),
        repository=InMemoryProviderOutputRepository(),
    )
    request = ModelProviderRequest(
        model_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        requested_model=config.provider_id,
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content=prompt),),
        temperature=0.0,
        # **W1-F5.** Set explicitly, and it has to be. `ModelProviderRequest.timeout_seconds`
        # defaults to 120 while this adapter's own CLI limit is 300, so the *request* expires
        # first and `ModelExecutionService._execute_once` cancels `provider.complete`. The
        # cancellation is then caught inside `BoundedCliRunner._communicate`, which converts it
        # to `ProviderCancelledError` before the outer `except TimeoutError` can see it — so a
        # call that timed out is reported as one somebody cancelled, `events.timed_out` never
        # fires, and the retry policy declines to retry because `ProviderCancelledError` is not
        # in `retryable_error_types` while `ProviderTimeoutError` is.
        #
        # Two live calls were lost to this before the bisection separated the layers: the
        # adapter answers in 34 s on its own, and the same call through the governed service
        # "cancelled" every time. Carried to the ledger as a released-code finding; the repair
        # here is the caller's, which is to stop asking for less time than the adapter is
        # allowed to take.
        timeout_seconds=float(config.limits.timeout_seconds),
    )
    receipt = await service.execute_with_receipt(
        request,
        directive=ProviderRetentionDirective(
            intended_use=ProviderOutputIntendedUse.EVALUATION_EVIDENCE,
            retention_mode=ProviderOutputRetentionMode.NONE,
        ),
        adapter_kind=ProviderAdapterKind(config.adapter.value),
        rights=RightsDecision(decision=UsageRightsDecision.UNKNOWN),
        verifier=VerifierOutcome(status=ProviderOutputVerifierStatus.NOT_RUN),
    )
    response = receipt.execution.response
    return {
        # **`structured_output`, not `content`.** The adapter validates the reply against
        # `AdvisoryResult` and then sets `content = advisory.summary` — one field — while the
        # whole validated object goes to `structured_output`. A caller that reads `content`
        # gets a correct but lossy view: the summary arrives and the findings, recommendations,
        # risks and verification steps are silently gone. That cost two live calls here, both
        # of which looked like the provider answering in prose when it had in fact answered in
        # the schema and the caller had thrown four fifths of it away.
        "structured_output": response.structured_output,
        "content": response.content or "",
        "receipt": {
            "request_hash": receipt.execution.request_hash,
            "normalized_response_hash": receipt.execution.normalized_response_hash,
            "resolved_model": receipt.execution.resolved_model,
            "retention_mode": receipt.execution.retention_mode.value,
            "provider_id": config.provider_id,
            "adapter": config.adapter.value,
        },
    }


def read_draft(structured: Any, proposal: Any) -> Any:
    """Map the provider's reply onto the released draft contract. Refuses; never repairs.

    **The reply arrives in the advisory schema, and that is the adapter's decision rather than
    this driver's.** `ClaudeCodeAdvisoryProvider.safety_arguments` puts
    `--json-schema <AdvisoryResult>` on the command line, so every governed CLI call in this
    repository is answered in the one shape all three providers share — summary, findings,
    recommendations, risks, verification steps. That is the point of the governed boundary
    (ADR 0087): a receipt from one provider is comparable with a receipt from another.

    So the host maps `AdvisoryResult` onto `ProviderProposalDraft` here, field by named field,
    and the mapping is total rather than clever: nothing is inferred, nothing is summarised,
    and a missing advisory field becomes a missing draft field rather than a filled-in one.
    22D's rule is carried — a reader that turns nearly-JSON into a contract is scoring its own
    parser — so the payload must already validate as `AdvisoryResult`.
    """
    from cognitive_os.domain.proposals import HarnessProposalType, ProviderProposalDraft
    from cognitive_os.providers.advisory_schema import AdvisoryResult

    advisory = AdvisoryResult.model_validate(structured)
    identity = component_identity(proposal)
    findings = advisory.findings
    return ProviderProposalDraft(
        proposal_type=HarnessProposalType(proposal_surface(proposal)),
        summary=advisory.summary,
        # The first finding's description is the proposed body; where the provider returned no
        # finding at all, the summary stands in and the limitation below says so. Inventing a
        # body would be the host writing the draft it wanted.
        proposed_body=findings[0].description if findings else advisory.summary,
        rationale=findings[0].title if findings else advisory.summary,
        alternative_drafts=tuple(advisory.recommendations) or ("no alternative was offered",),
        # Scope is the host's, not the provider's: `merge_provider_draft` refuses a draft that
        # names a component outside the registered specification, so this is pinned to the
        # proposal rather than taken from the reply.
        affected_component_hints=(identity,),
        validation_rationale=" ".join(advisory.verification_steps)
        or "no verification step was offered",
        rollback_rationale=" ".join(advisory.risks) or "no rollback risk was offered",
        limitations=(
            "Mapped from the released advisory schema; the provider was not asked for, and "
            "did not supply, a patch.",
            *(() if findings else ("The provider returned no finding.",)),
        ),
        cited_host_source_ref_ids=(),
    )


# ---------------------------------------------------------------------------
# W1-F4. The repair, and the cause 22D misattributed
# ---------------------------------------------------------------------------


#: **The repair, per ledger entry.** Each spec is a file plus an ordered chain of
#: `deterministic_replace` steps, hash-chained so every applied byte is checked rather than
#: trusted. L1 is W1's original; L2 and L6 are W2's dry runs on distinct weakness classes.
#:
#: L2 (`policy_decision_function`): the 22D escalation predicate is blind to output kind, so
#: seventy closed-form tasks escalate for lacking a citation the grounding exit never reads.
#: The repair gates the grounding condition on the factual output kinds, with a defaulted
#: parameter so the frozen pre-registration display's call site keeps its exact behaviour.
#:
#: L6 (`provider_boundary`): `BoundedCliRunner._communicate`'s cancellation catch converts an
#: expired caller deadline into `ProviderCancelledError` below the layer that owns the
#: deadline. The repair cleans up and re-raises the cancellation itself: the caller's own
#: `asyncio.timeout` then surfaces it as `TimeoutError` where the deadline lives, and a real
#: operator cancel stays a cancel.
REPAIR_SPECS: dict[str, dict[str, Any]] = {
    "L1": {
        "file": "src/cognitive_os/verification/physics/quantities.py",
        "steps": (
            (
                'SAFE_UNIT = re.compile(r"^[A-Za-z0-9_/*^ .-]{1,128}$")',
                'SAFE_UNIT = re.compile(r"^[A-Za-z0-9_/*^ .\u00b7\u00b2\u00b3\u03a9-]{1,128}$")',
            ),
        ),
    },
    "L2": {
        "file": "scripts/benchmark_22d.py",
        "steps": (
            (
                "def escalate(outcome: ArmOutcome) -> bool:",
                "def escalate(outcome: ArmOutcome, output_kind: str | None = None) -> bool:",
            ),
            (
                "        or outcome.grounded_span_count < MINIMUM_GROUNDED_SPANS",
                "        or (\n"
                "            (output_kind is None or output_kind in FACTUAL_OUTPUT_KINDS)\n"
                "            and outcome.grounded_span_count < MINIMUM_GROUNDED_SPANS\n"
                "        )",
            ),
            (
                "        accounting.escalated += int(escalate(outcome))",
                '        accounting.escalated += int(escalate(outcome, str(task["output_kind"])))',
            ),
            (
                '            "escalated": escalate(outcome),',
                '            "escalated": escalate(outcome, str(task["output_kind"])),',
            ),
        ),
    },
    "L6": {
        "file": "src/cognitive_os/providers/cli_process.py",
        "steps": (
            (
                "        except asyncio.CancelledError:\n"
                "            # Cleanup before re-raising as a typed error: a cancelled call that left the\n"  # noqa: E501
                "            # provider running would keep spending the operator's subscription unobserved.\n"  # noqa: E501
                "            await self._terminate_tree(process)\n"
                "            raise ProviderCancelledError(\n"
                "                provider_id=self.provider_id,\n"
                '                message="advisory CLI execution was cancelled",\n'
                "            ) from None",
                "        except asyncio.CancelledError:\n"
                "            # Cleanup before re-raising: a cancelled call that left the provider running\n"  # noqa: E501
                "            # would keep spending the operator's subscription unobserved. The\n"
                "            # cancellation itself propagates: converting it to a typed provider error\n"  # noqa: E501
                "            # here made an expired caller deadline read as a cancellation nobody\n"
                "            # requested (22E ledger L6) - the caller's own asyncio.timeout turns this\n"  # noqa: E501
                "            # back into TimeoutError at the layer that owns the deadline, and a real\n"  # noqa: E501
                "            # operator cancel stays a cancel.\n"
                "            await self._terminate_tree(process)\n"
                "            raise",
            ),
        ),
    },
}

#: The file ledger entry L1 actually lives in, and the line that actually rejects the notation.
#:
#: **W1-F4.** 22D W2-F2 reads "the registered physics verifiers ... **error** on `m/s²`,
#: `kg·m/s` and `Ω`", and a reader takes that to mean the sealed Pint registry cannot parse
#: them. It parses all three. What rejects them is this repository's own character-class
#: allowlist in `PhysicalQuantity.safe_unit`:
#:
#:     SAFE_UNIT = re.compile(r"^[A-Za-z0-9_/*^ .-]{1,128}$")
#:
#: measured side by side — `pint.parse_units("Ω")` succeeds, `PhysicalQuantity(unit="Ω")`
#: raises "unit expression is not allowed". So the defect is one regex in one released
#: contract, not a limitation of a dependency, and the repair is correspondingly small. The
#: measured ceiling from W0 (+10 on `local_model`) is unchanged; what changes is the diagnosis,
#: and it changes the repair from "replace the unit library" to "widen an allowlist by four
#: characters, keeping its injection-safety intent".
REPAIR_FILE = "src/cognitive_os/verification/physics/quantities.py"

REPAIR_BEFORE = 'SAFE_UNIT = re.compile(r"^[A-Za-z0-9_/*^ .-]{1,128}$")'

#: The written characters, and only those: Ω (ohm), · (multiplication dot), ² and ³
#: (superscript two and three). Deliberately not `\w` or a Unicode category — a repair that
#: opened the allowlist to "any letter" would trade a false rejection for a real one, and this
#: validator exists to keep a unit expression from being an injection surface.
REPAIR_AFTER = 'SAFE_UNIT = re.compile(r"^[A-Za-z0-9_/*^ .·²³Ω-]{1,128}$")'


def apply_repair(worktree: Path, entry_id: str = "L1") -> dict[str, Any]:
    """Apply the entry's repair chain through the released `deterministic_replace`.

    Each step passes the hash of the bytes it starts from, so every intermediate state is
    checked rather than trusted; the record carries the baseline hash, the final hash and
    the step count. A patch written by string surgery here would be the driver asserting
    its own correctness.
    """
    from cognitive_os.changes.service import deterministic_replace

    spec = REPAIR_SPECS[entry_id]
    target = worktree / spec["file"]
    original = target.read_bytes()
    baseline_hash = _sha256(original)
    content = original
    for before, after in spec["steps"]:
        content = deterministic_replace(content, before.encode(), after.encode(), _sha256(content))
    target.write_bytes(content)
    return {
        "file": spec["file"],
        "applied_by": "cognitive_os.changes.service.deterministic_replace",
        "steps": len(spec["steps"]),
        "before_hash": baseline_hash,
        "after_hash": _sha256(content),
        "expected_hash_is_the_baseline": True,
        "bytes_changed": len(content) - len(original),
        "the_provider_did_not_write_this": (
            "no released provider configuration in this repository can write a file, and "
            "merge_provider_draft refuses a draft carrying a patch; the host applies the "
            "change and the provider advised on the proposal"
        ),
        "finding": "W1-F4" if entry_id == "L1" else f"ledger {entry_id}",
    }


def rollback_repair(worktree: Path, entry_id: str, repair: dict[str, Any]) -> dict[str, Any]:
    """Execute the rollback in isolation, through the same released mechanism, reversed.

    §2.2's rollback evidence must be a rollback *executed*, not a manifest that exists
    (D7 W3-F1). The steps run in reverse with before/after swapped, every intermediate
    hash-checked, and the result must be byte-identical to the baseline the repair recorded
    - verified by hash here and by the released worktree capture reporting an empty diff.
    """
    from cognitive_os.changes.service import deterministic_replace

    spec = REPAIR_SPECS[entry_id]
    target = worktree / spec["file"]
    content = target.read_bytes()
    for before, after in reversed(spec["steps"]):
        content = deterministic_replace(content, after.encode(), before.encode(), _sha256(content))
    target.write_bytes(content)
    return {
        "executed_by": "deterministic_replace, steps reversed",
        "restored_hash": _sha256(content),
        "restored_hash_is_the_baseline": _sha256(content) == repair["before_hash"],
    }


def probe_repair(worktree: Path) -> dict[str, Any]:
    """Does the repaired contract accept the written notation? Run in the worktree, not here.

    Importing the repaired module into this process would measure the *active* checkout, which
    still holds the defect. The probe runs as a subprocess inside the candidate worktree, which
    is the only place the repair exists.
    """
    import subprocess

    from isolation_22e import gate_environment

    program = (
        "from cognitive_os.verification.physics.quantities import PhysicalQuantity\n"
        "import json\n"
        "out={}\n"
        "for u in ('ohm','Ω','kg*m/s','kg·m/s','m/s**2','m/s²','; rm -rf /'):\n"
        "    try:\n"
        "        PhysicalQuantity(magnitude='1', unit=u); out[u]=True\n"
        "    except Exception:\n"
        "        out[u]=False\n"
        "print(json.dumps(out))\n"
    )
    completed = subprocess.run(
        ["uv", "run", "--all-groups", "--extra", "verification-physics", "python", "-c", program],
        cwd=worktree,
        capture_output=True,
        text=True,
        timeout=600,
        env=gate_environment(),
    )
    accepted = json.loads(completed.stdout.strip().splitlines()[-1])
    return {
        "accepted": accepted,
        "written_notation_now_accepted": all(accepted[unit] for unit in ("Ω", "kg·m/s", "m/s²")),
        "ascii_notation_still_accepted": all(
            accepted[unit] for unit in ("ohm", "kg*m/s", "m/s**2")
        ),
        "injection_still_refused": accepted["; rm -rf /"] is False,
        "why_the_injection_case_is_here": (
            "the validator exists to keep a unit expression from being an injection surface; "
            "a repair that widened the allowlist to 'any letter' would trade a false "
            "rejection for a real hole, so the negative case is measured beside the positive"
        ),
    }


def probe_repair_l2(worktree: Path) -> dict[str, Any]:
    """Does the repaired predicate distinguish output kinds - and keep every old behaviour?"""
    import subprocess

    from isolation_22e import gate_environment

    program = (
        "import sys, json\n"
        "sys.path.insert(0, 'scripts')\n"
        "from benchmark_22d import ArmOutcome, escalate\n"
        "computation = ArmOutcome(task_id='t', arm='local_model', answer='4', abstained=False)\n"
        "abstainer = ArmOutcome(task_id='t', arm='local_model', answer=None, abstained=True)\n"
        "print(json.dumps({\n"
        " 'closed_form_no_longer_escalates': not escalate(computation, 'closed_form_computation'),\n"  # noqa: E501
        " 'factual_still_escalates': escalate(computation, 'declarative_fact'),\n"
        " 'abstention_still_escalates': escalate(abstainer, 'closed_form_computation'),\n"
        " 'defaulted_call_keeps_old_behaviour': escalate(computation),\n"
        "}))\n"
    )
    completed = subprocess.run(
        ["uv", "run", "--all-groups", "python", "-c", program],
        cwd=worktree,
        capture_output=True,
        text=True,
        timeout=600,
        env=gate_environment(),
    )
    verdicts = json.loads(completed.stdout.strip().splitlines()[-1])
    return {**verdicts, "every_probe_holds": all(verdicts.values())}


def probe_repair_l6(worktree: Path) -> dict[str, Any]:
    """The conversion is gone, the module still imports, and the timeout path is intact."""
    import subprocess

    from isolation_22e import gate_environment

    source = (worktree / REPAIR_SPECS["L6"]["file"]).read_text(encoding="utf-8")
    completed = subprocess.run(
        ["uv", "run", "--all-groups", "python", "-c", "import cognitive_os.providers.cli_process"],
        cwd=worktree,
        capture_output=True,
        text=True,
        timeout=600,
        env=gate_environment(),
    )
    return {
        "cancellation_no_longer_converted": (
            'message="advisory CLI execution was cancelled"' not in source
        ),
        "timeout_conversion_intact": "advisory CLI execution exceeded its timeout" in source,
        "module_still_imports": completed.returncode == 0,
        "every_probe_holds": (
            'message="advisory CLI execution was cancelled"' not in source
            and "advisory CLI execution exceeded its timeout" in source
            and completed.returncode == 0
        ),
    }


PROBES = {"L1": probe_repair, "L2": probe_repair_l2, "L6": probe_repair_l6}

# ---------------------------------------------------------------------------
# The lifecycle
# ---------------------------------------------------------------------------

OUTPUT = EVIDENCE / "sprint-22e-w1-dryrun1.json"

#: The gates dry run 1 runs against the patched worktree. Not all fifteen: the substrate
#: record already measures the full matrix's wall clock on an unpatched tree, and running the
#: 262-second regression gate again here would measure the same thing twice. These are the
#: gates a *notation* repair can actually move, plus the two that would catch it escaping.
#:
#: §3.2's rule is that a cell economised away is a quiet reading-change, so the reduction is
#: declared here rather than performed silently, and `gates_not_run_here` is carried into the
#: record with the reason. W2's dry runs and W3's approved change run the full matrix.
DRY_RUN_GATES = (
    "candidate_integrity",
    "focused_target_tests",
    "target_benchmark",
    "security",
    "policy",
    "schema",
    "compatibility",
)


async def run_dry_run(
    entry_id: str,
    *,
    label: str | None = None,
    full_matrix: bool = False,
    rollback: bool = False,
) -> dict[str, Any]:
    """Mine, draft, isolate, patch, evaluate, refuse — and compile the experience either way.

    `label` names the worktree and therefore the deterministic experiment id (W1-F8). The
    default is W1's; a continuation run passes its own so the sealed W1 record's worktree
    identity is never reused, and pairs it with `--output` so the sealed record's *file* is
    never overwritten either.
    """
    import os

    from isolation_22e import RealWorktree, matrix_gate_ids, run_gate
    from mining_22e import (
        MINING_TIME,
        LedgerWeaknessProposalSource,
        build_weakness,
        load_entry,
    )
    from sqlalchemy.ext.asyncio import create_async_engine
    from surface_22e import capture, compare

    from cognitive_os.changes.service import (
        ControlledChangeService,
    )
    from cognitive_os.domain.changes import (
        ActiveStateProtectionSnapshot,
    )
    from cognitive_os.domain.proposals import (
        HarnessProposalType,
        ProposalGenerationMode,
        ProposalReviewDecision,
        ProposalStatus,
    )
    from cognitive_os.infrastructure.changes.postgres.repository import PostgresChangeRepository
    from cognitive_os.proposals.repository import InMemoryProposalRepository
    from cognitive_os.proposals.service import HarnessProposalService, merge_provider_draft

    database_url = os.environ["COGOS_DATABASE_ADMIN_URL"]
    artifact_root = Path(os.environ["COGOS_ARTIFACT_ROOT"])
    before = await capture(database_url=database_url, artifact_root=artifact_root)

    stages: list[str] = []
    entry = load_entry(entry_id)
    mined = build_weakness(entry_id)
    stages.append("weakness_mined")

    # **The released provider-assisted path, not a reimplementation of it.**
    # `create_from_weakness(provider_assisted=True)` freezes the source snapshot, builds the
    # host's own specification, asks the injected generator for a draft, and merges it through
    # `merge_provider_draft` — the host verification — all inside one released transition. A
    # driver that merged the draft itself afterwards would be running its own version of the
    # seam the sprint exists to exercise.
    # **W1-F7 forces this shape, and the record says so rather than hiding it.**
    # The released one-call path is `create_from_weakness(provider_assisted=True)`: it freezes
    # the source, builds the host specification, asks the injected generator for a draft and
    # merges it through `merge_provider_draft`, all inside one transition. It cannot succeed.
    # `merge_provider_draft` ends with
    #
    #     return revision.model_copy(update={..., "content_hash": ""})
    #
    # blanking the hash so the contract's `seal_content` validator recomputes it — but
    # `model_copy(update=...)` does not re-run validators in Pydantic v2, so the merged
    # revision keeps `content_hash == ""`, and the next released statement,
    # `ProposalCreated(proposal_content_hash=generated.content_hash)`, refuses it against
    # `^[0-9a-f]{64}$`. **The released provider-assisted path raises on its own success path**,
    # and §1.3 is why nobody had seen it: no candidate had ever been generated by a real
    # provider.
    #
    # So the host verification is still exercised for real — `merge_provider_draft` is called,
    # and it is what decides whether the draft is admissible — and the caller reseals the
    # merged revision through the contract itself. Resealing is not a repair of the defect: it
    # is this driver refusing to pretend the defect is not there. W1-F7 goes to the ledger as a
    # candidate for the governed path, which is where a released repair belongs.
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

    generator = LiveProviderGenerator(entry)
    draft = await generator.draft(proposal.source_snapshot, allowed_source_ids=())
    merged = merge_provider_draft(proposal, draft, allowed_source_ids=())
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

    engine = create_async_engine(database_url)
    try:
        source = LedgerProposalSource(proposals, approved)
        service = ControlledChangeService(PostgresChangeRepository(engine), source)
        experiment, _revision, approved = await service.request_experiment(
            approved.proposal_id,
            approved.revision,
            baseline_tag="sprint-22d-evidence-baseline",
            baseline_commit=_head(),
            actor="s22e-operator",
            isolation_approver="s22e-isolation-approver",
            created_at=MINING_TIME,
        )
        stages.append("experiment_requested")

        # **A real snapshot, not a literal.** `changes/demo.py` fills these five fields with
        # "a"*40 and "b"*64; here they are the surface this sprint actually measured, so the
        # protection snapshot the released service records is about this repository.
        snapshot = ActiveStateProtectionSnapshot(
            repository_commit=before["values"]["repository_commit"],
            repository_status_hash=before["values"]["repository_status_hash"],
            repository_manifest_hash=before["values"]["repository_manifest_hash"],
            active_database_fingerprint=before["values"]["active_database_fingerprint"],
            active_artifact_namespace_hash=before["values"]["active_artifact_namespace_hash"],
            captured_at=MINING_TIME,
        )
        async with RealWorktree(label or f"w1-dryrun-{entry_id}") as worktree:
            assert worktree.path is not None
            _isolation, _verifier = await service.prepare_isolation(
                experiment, approved, snapshot, created_at=MINING_TIME
            )
            stages.append("isolation_prepared")

            repair = apply_repair(worktree.path, entry_id)
            stages.append("repair_applied")
            probe = PROBES[entry_id](worktree.path)
            stages.append("repair_probed")

            allowed_path = REPAIR_SPECS[entry_id]["file"]
            diff_hash, changed = await worktree.capture(allowed_paths=(allowed_path,))
            stages.append("candidate_captured_from_the_worktree")

            gate_ids = matrix_gate_ids(approved)
            gates_to_run = gate_ids if full_matrix else DRY_RUN_GATES
            gates = [run_gate(gate_id, worktree.path) for gate_id in gates_to_run]
            stages.append("evaluation_run")

            rolled_back = None
            if rollback:
                rolled_back = rollback_repair(worktree.path, entry_id, repair)
                back_hash, back_changed = await worktree.capture(allowed_paths=())
                rolled_back["capture_diff_is_empty"] = back_hash == _sha256(b"")
                rolled_back["capture_changed_files"] = list(back_changed)
                stages.append("rollback_executed_in_isolation")
    finally:
        await engine.dispose()

    after = await capture(database_url=database_url, artifact_root=artifact_root)
    return {
        "entry_id": entry_id,
        "stages": stages,
        "provider": generator.receipt,
        "draft": {
            "prompt_bytes": len(generator.prompt or ""),
            "advisory_fields": sorted(generator.structured or {}),
            "findings": len((generator.structured or {}).get("findings", ())),
            "recommendations": len((generator.structured or {}).get("recommendations", ())),
            "risks": len((generator.structured or {}).get("risks", ())),
            "verification_steps": len((generator.structured or {}).get("verification_steps", ())),
            "summary": (generator.structured or {}).get("summary"),
            "generation_mode_after_host_verification": merged.generation_mode.value,
            "generation_mode_on_the_approved_revision": approved.generation_mode.value,
            "host_verification_passed": True,
            # **W1-F7's second consequence, and it must not be papered over.** The merged
            # revision really is `provider_assisted` — `merge_provider_draft` marked it after
            # its own checks passed. But `transition` and `record_review` read the *current*
            # revision back out of the repository, and the only released writer of a merged
            # revision is `create_from_weakness(provider_assisted=True)`, which cannot
            # complete. So the mark cannot survive to the approved revision by any caller's
            # route, and the approved revision reads `deterministic`.
            #
            # The draft was live, host-verified and admitted; what is missing is a released
            # writer for it. Recorded as the gap it is rather than asserted away: this dry run
            # is provider-*advised* end to end and the released `generation_mode` says
            # otherwise, and both halves of that sentence are true.
            "provider_assisted_mark_did_not_survive_because": (
                "the released transitions read the current revision from the repository, and "
                "only create_from_weakness writes a merged one — the path W1-F7 blocks"
            ),
        },
        "repair": repair,
        "repair_probe": probe,
        "worktree_capture": {
            "changed_files": list(changed),
            "diff_hash": diff_hash,
            "only_the_allowed_path_changed": set(changed) <= {allowed_path},
        },
        "gates": gates,
        "gates_not_run_here": [item for item in gate_ids if item not in gates_to_run],
        "rollback": rolled_back,
        "zero_active_state_mutation": compare(before, after),
        "surface_before": before["values"],
        "surface_after": after["values"],
        "recorded_at": DRY_RUN_TIME,
    }


def _head() -> str:
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


class LedgerProposalSource:
    """The `ControlledChangeService` source port over the mined, provider-assisted proposal."""

    def __init__(self, service: Any, approved: Any) -> None:
        self._service = service
        self._approved = approved

    async def get_proposal_identity(self, proposal_id: Any) -> Any:
        return self._service._repository.identities.get(proposal_id)

    async def get_exact_proposal(self, proposal_id: Any, revision: int) -> Any:
        return await self._service._repository.get_exact(proposal_id, revision)

    async def list_proposal_reviews(self, proposal_id: Any, revision: int) -> tuple:
        return tuple(
            item
            for item in await self._service._repository.list_reviews()
            if item.proposal_id == proposal_id and item.proposal_revision == revision
        )

    async def artifact_exists(self, content_hash: str) -> bool:
        return content_hash in set(self._approved.artifact_refs)


class LiveProviderGenerator:
    """The released `ProposalGeneratorPort`, backed by one live governed provider call.

    The port's contract is narrow on purpose: given the frozen source snapshot and the source
    ids the host will accept a citation from, return a `ProviderProposalDraft`. Everything the
    host then does to that draft — type check, citation check, scope check, disallowed-text
    check — happens in `merge_provider_draft`, and this class has no way to skip it.

    The receipt is kept on the instance rather than returned, because the port has no slot for
    one and inventing a return shape would be this driver widening a released interface to suit
    its own record.
    """

    def __init__(self, entry: dict[str, Any]) -> None:
        self.entry = entry
        self.receipt: dict[str, Any] | None = None
        self.structured: Any = None
        self.prompt: str | None = None

    async def draft(self, source: Any, *, allowed_source_ids: tuple[str, ...]) -> Any:
        self.prompt = build_draft_prompt(self.entry, source)
        reply = await request_draft(self.prompt, source)
        self.receipt = reply["receipt"]
        self.structured = reply["structured_output"]
        return read_draft(self.structured, source)


# ---------------------------------------------------------------------------
# W1-F9. The check, split the way the sealers split
# ---------------------------------------------------------------------------


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    """Recompute the invariants; re-read the observations; print which was which.

    **W1-F9.** This script sealed a record that twenty tests read and none could rebuild from
    one flag, and the omission was found in review rather than by a failure. The split is the
    sealers' (22D W4-F1 via W0-F2): a `--check` here must not re-run a billed provider call or
    a gate matrix — 22C W1-F1 forbids a validator that needs the world — so the live halves
    are re-read by name and everything with a derivation is re-derived.
    """
    from surface_22e import compare

    mismatches: list[str] = []

    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != record.get("integrity_content_hash"):
        mismatches.append("integrity_content_hash")

    recorded_gate_ids = [item["gate_id"] for item in record["gates"]]
    reduced_run = bool(record.get("gates_not_run_here"))
    if reduced_run and recorded_gate_ids != list(DRY_RUN_GATES):
        mismatches.append("gates (order or membership differs from DRY_RUN_GATES)")

    matrix_recomputed = False
    matrix_absent_reason = ""
    try:
        import asyncio

        from isolation_22e import assert_the_map_covers_the_matrix, matrix_gate_ids

        from cognitive_os.changes.fixtures import fixture_approved_proposal

        _, proposal = asyncio.run(fixture_approved_proposal())
        gate_ids = matrix_gate_ids(proposal)
        assert_the_map_covers_the_matrix(gate_ids)
        if sorted((*recorded_gate_ids, *record["gates_not_run_here"])) != sorted(gate_ids):
            mismatches.append("gates_not_run_here (union does not cover the released matrix)")
        matrix_recomputed = True
    except ModuleNotFoundError as error:
        matrix_absent_reason = f"{type(error).__name__}: {error}"

    entry_id = record.get("entry_id", "L1")
    spec = REPAIR_SPECS[entry_id]
    repair = record["repair"]
    if repair["file"] != spec["file"]:
        mismatches.append("repair.file")
    replace_recomputed = False
    replace_absent_reason = ""
    active = REPO / spec["file"]
    if active.exists() and _sha256(active.read_bytes()) == repair["before_hash"]:
        from cognitive_os.changes.service import deterministic_replace

        repaired = active.read_bytes()
        for before, after in spec["steps"]:
            repaired = deterministic_replace(
                repaired, before.encode(), after.encode(), _sha256(repaired)
            )
        if _sha256(repaired) != repair["after_hash"]:
            mismatches.append("repair.after_hash")
        replace_recomputed = True
    else:
        # After W3 lands the L1 repair on `main`, the active file legitimately stops matching
        # the recorded baseline; a check that failed on that would fail on the sprint
        # succeeding. Named, not silently skipped.
        replace_absent_reason = "the active tree has moved past the recorded baseline"

    probe = record["repair_probe"]
    if entry_id == "L1":
        accepted = probe["accepted"]
        derived = {
            "written_notation_now_accepted": all(
                accepted[unit] for unit in ("Ω", "kg·m/s", "m/s²")
            ),
            "ascii_notation_still_accepted": all(
                accepted[unit] for unit in ("ohm", "kg*m/s", "m/s**2")
            ),
            "injection_still_refused": accepted["; rm -rf /"] is False,
        }
        for field, value in derived.items():
            if probe[field] != value:
                mismatches.append(f"repair_probe.{field}")
    elif probe.get("every_probe_holds") != all(
        value for key, value in probe.items() if key != "every_probe_holds"
    ):
        mismatches.append("repair_probe.every_probe_holds")

    capture_block = record["worktree_capture"]
    if capture_block["only_the_allowed_path_changed"] != (
        set(capture_block["changed_files"]) <= {spec["file"]}
    ):
        mismatches.append("worktree_capture.only_the_allowed_path_changed")
    rolled = record.get("rollback")
    if rolled is not None:
        if rolled["restored_hash_is_the_baseline"] != (
            rolled["restored_hash"] == repair["before_hash"]
        ):
            mismatches.append("rollback.restored_hash_is_the_baseline")
        if rolled["capture_diff_is_empty"] != (not rolled["capture_changed_files"]):
            mismatches.append("rollback.capture_diff_is_empty")

    stored = record["zero_active_state_mutation"]
    rebuilt = compare(
        {
            "values": record["surface_before"],
            "surface_hash": stored["surface_hash_before"],
            "audit_trail_fingerprint": stored["audit_trail_fingerprint_before"],
        },
        {
            "values": record["surface_after"],
            "surface_hash": stored["surface_hash_after"],
            "audit_trail_fingerprint": stored["audit_trail_fingerprint_after"],
        },
    )
    for field in (
        "per_member_unchanged",
        "mutated_members",
        "zero_active_state_mutation",
        "audit_trail_moved",
    ):
        if rebuilt[field] != stored[field]:
            mismatches.append(f"zero_active_state_mutation.{field}")

    result: dict[str, Any] = {
        "reproduced": not mismatches,
        "mismatches": mismatches,
        "recomputed": [
            "integrity_content_hash",
            "gates (membership against DRY_RUN_GATES)",
            *(["gates_not_run_here (against the released matrix)"] if matrix_recomputed else []),
            *(
                ["repair (deterministic_replace re-executed on the baseline bytes)"]
                if replace_recomputed
                else []
            ),
            "repair_probe verdict booleans (from the probe's own accepted map)",
            "worktree_capture.only_the_allowed_path_changed",
            "zero_active_state_mutation (re-derived from the two stored captures)",
        ],
        "recorded_not_recomputed": [
            "provider receipt and draft (a billed live call; 22C W1-F1)",
            "stage list and gate verdicts and wall clocks (a discarded worktree)",
            "the surface captures themselves (the repository has legitimately moved)",
        ],
        "finding": "W1-F9",
    }
    if not matrix_recomputed:
        result["recorded_not_recomputed"].insert(0, f"released matrix ({matrix_absent_reason})")
    if not replace_recomputed:
        result["recorded_not_recomputed"].insert(0, f"repair bytes ({replace_absent_reason})")
    return result


def main() -> int:
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", default="L1")
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--label", default=None, help="worktree label; a continuation must not reuse W1's"
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--full-matrix", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        stored = json.loads(arguments.output.read_text(encoding="utf-8"))
        verdict = check_record(stored)
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return 0 if verdict["reproduced"] else 1

    record = asyncio.run(
        run_dry_run(
            arguments.entry,
            label=arguments.label,
            full_matrix=arguments.full_matrix,
            rollback=arguments.rollback,
        )
    )
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "entry": record["entry_id"],
                "stages": record["stages"],
                "generation_mode_after_host_verification": record["draft"][
                    "generation_mode_after_host_verification"
                ],
                "generation_mode_on_the_approved_revision": record["draft"][
                    "generation_mode_on_the_approved_revision"
                ],
                "provider": (record["provider"] or {}).get("provider_id"),
                "repair_probe": {
                    key: value for key, value in record["repair_probe"].items() if key != "accepted"
                },
                "changed_files": record["worktree_capture"]["changed_files"],
                "gates": [
                    {
                        "gate_id": item["gate_id"],
                        "passed": item.get("passed"),
                        "seconds": item.get("seconds"),
                    }
                    for item in record["gates"]
                ],
                "zero_active_state_mutation": record["zero_active_state_mutation"][
                    "zero_active_state_mutation"
                ],
                "mutated_members": record["zero_active_state_mutation"]["mutated_members"],
                "audit_trail_moved": record["zero_active_state_mutation"]["audit_trail_moved"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
