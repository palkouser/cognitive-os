#!/usr/bin/env python
"""S21D3-051 through -059: the artifact and runtime wave, decided against W2's null selection.

Two evidence files, because they answer two different questions and one of them is a decision.

`sprint-21d3-runtime-invariance.json` is measured. It runs the direct evaluation boundary and
the runtime resolver over the full matrix of ways each can refuse, executes the ordering
decision under every one of those configurations and hashes what each actually did, and checks
the resolver's own source for anything that could reach a provider, the network, a GPU or a
credential. Every artifact it reads is a contract fixture built here — the D3 selected artifact
does not exist, because S21D3-039 selected nothing.

`sprint-21d3-pre-final-checkpoint.json` is the decision. It evaluates every S21D3-059
precondition against what W0 through W3 actually recorded, finds the first that fails, and
writes the complete not-opened map for E06 and E07 bound to that stop hash. On this sprint the
first failure is already known: the W2 candidate selection is null, so final access is not
authorised and no configuration is sealed.

Nothing here opens a final, batch-B or canary body, registers a lifecycle component, or writes
to any Artifact Store. The two files are derived from committed evidence and from code that
runs in-process.

    scripts/artifact_runtime_d3.py [--output-dir docs/sprints/sprint-21/evidence]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.application.services.correction_candidate_sequencer import (  # noqa: E402
    AttemptResult,
    CorrectionCandidateSequencer,
    SequenceMode,
)
from cognitive_os.application.services.learned_runtime import (  # noqa: E402
    ActiveComponentState,
    ArtifactAvailability,
    EmbeddingIdentity,
    LearnedRuntimeResolver,
    RoutingPolicy,
    RuntimeHealthReason,
)
from cognitive_os.application.services.reality_campaign import (  # noqa: E402
    ReceiptAction,
    ReceiptAwareResumePlan,
    ResumePlan,
    TaskReceiptState,
)
from cognitive_os.domain.learned import LearnedComponentState  # noqa: E402
from cognitive_os.domain.promotion_payload import (  # noqa: E402
    D3_PROMOTION_GATES,
    D3_PROMOTION_SCHEMA,
    D3_PROMOTION_SCHEMA_VERSION,
    CanaryToSteadyCondition,
    D3RuntimeConfiguration,
)
from cognitive_os.domain.reality import (  # noqa: E402
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.events.coding_event_service import CodingEventService  # noqa: E402
from cognitive_os.events.memory_store import MemoryEventStore  # noqa: E402
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    CORRECTION_ARTIFACT_MEDIA_TYPE,
    CORRECTION_ARTIFACT_SCHEMA_V2,
    CorrectionArtifactError,
    DirectEvaluationCapability,
    EvaluationPurpose,
    build_payload_v2,
    build_ranker_for_evaluation,
    canonical_bytes,
    load_correction_ranker,
    load_correction_ranker_v2,
)
from cognitive_os.learning.correction_features import (  # noqa: E402
    feature_input_v2,
    raw_numeric_row_v2,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    FITTED_FEATURE_V2_ALLOWLIST,
    FITTED_FEATURE_V2_SCALARS,
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionEncoderV2,
    CorrectionKnn,
    Exemplar,
    NumericBoundsV2,
)

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d3-pre-registration.json"
SELECTION = EVIDENCE / "sprint-21d3-learner-selection.json"
HOLDOUT = EVIDENCE / "sprint-21d3-retrieval-holdout-result.json"
DIAGNOSTIC = EVIDENCE / "sprint-21d3-diagnostic-continuation.json"

NAMESPACE = UUID("6f2b18d4-9c3a-5e71-8b04-2d7a5c1f9e63")
#: A fixture identity, and labelled as one everywhere it appears. It is not the D3 component
#: revision, because no artifact was selected and therefore no revision exists.
FIXTURE_REVISION = 2
SURFACE = CorrectionKnn.surface
COMPONENT = CorrectionKnn.component_id
FIXTURE_HASH = sha256(b"s21d3-w4-contract-fixture").hexdigest()

#: Every E06 and E07 item, with what each would have done. Written out rather than derived, so
#: the map is reviewable against the backlog rather than against this script's cleverness.
DEPENDENT_ITEMS: tuple[tuple[str, str], ...] = (
    ("S21D3-051", "fit and store the selected artifact"),
    ("S21D3-054", "prove the selected-artifact vertical slice"),
    ("S21D3-056", "register the exact artifact and enter SHADOW"),
    ("S21D3-060", "seal final features and predictions before execution"),
    ("S21D3-061", "execute final batch A without replacement"),
    ("S21D3-062", "execute final batch B without replacement"),
    ("S21D3-063", "measure material benefit and the paired interval"),
    ("S21D3-064", "measure safety and governance regressions"),
    ("S21D3-065", "measure retention"),
    ("S21D3-066", "run the promotion metamorphic and OOD set"),
    ("S21D3-067", "record the shadow projection"),
    ("S21D3-068", "store the versioned promotion assessment payload"),
    ("S21D3-069", "transition SHADOW to VERIFIED through evidence-bound verification"),
    ("S21D3-070", "assemble the exact activation bundle"),
    ("S21D3-071", "record the exact human approval"),
    ("S21D3-072", "activate the canary only"),
    ("S21D3-073", "exercise the kill switch"),
    ("S21D3-074", "prove restart, disable and restoration"),
    ("S21D3-076", "enter the bounded steady state"),
    ("S21D3-077", "record the final active projection"),
)

#: The one exception the backlog names: S21D3-075's receipt-chain rollback is an unconditional
#: substrate gate and runs against the isolated lifecycle fixture whether or not D3 activates.
UNCONDITIONAL_ITEMS: tuple[tuple[str, str], ...] = (
    ("S21D3-075", "receipt-chain rollback and refusal, on the isolated lifecycle fixture"),
)


def _hash(text: str) -> str:
    return sha256(text.encode()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sealed = {**value, "integrity_content_hash": _hash(_canonical_bytes(value).decode())}
    path.write_text(
        json.dumps(sealed, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------- the contract fixture artifact


SOURCES = (
    "def add(x, y):\n    return x + y\n",
    "def total(values):\n    return sum(values)\n",
    "def first(values):\n    return values[0]\n",
    "def last(values):\n    return values[-1]\n",
)


def _fixture_exemplars() -> list[Exemplar]:
    features = [
        feature_input_v2(
            candidate_source=source,
            canonical_candidate_source_embedding=tuple(
                ((index + seed) % 17 - 8) / 10 for index in range(384)
            ),
        )
        for seed, source in enumerate(SOURCES)
    ]
    rows = [raw_numeric_row_v2(item) for item in features]
    rows.append({name: value + 2.0 for name, value in rows[0].items()})
    encoder = CorrectionEncoderV2(NumericBoundsV2.from_training(rows))
    return [
        Exemplar(vector=encoder.encode(item), accepted=index % 2 == 0)
        for index, item in enumerate(features)
    ]


def _fixture_artifact() -> tuple[bytes, Any]:
    """A complete, valid v2 artifact built here. Labelled a fixture wherever it is reported.

    S21D3-054's real vertical slice needs the *selected* artifact and is not opened. What this
    proves is the contract: that the loader, the capability and the resolver behave as declared
    against bytes that satisfy the schema.
    """
    exemplars = _fixture_exemplars()
    payload = build_payload_v2(
        component_revision=FIXTURE_REVISION,
        descriptor_hash=FIXTURE_HASH,
        code_revision="s21d3-w4-fixture",
        ranker=CorrectionKnn(exemplars),
        exemplars=exemplars,
        training_dataset_id=uuid5(NAMESPACE, "training"),
        calibration_dataset_id=uuid5(NAMESPACE, "calibration"),
        example_manifest_hash=_hash("example-manifest"),
        split_manifest_hash=_hash("split-manifest"),
        selection_manifest_hash=_hash("selection-manifest"),
        member_manifest_hash=_hash("member-manifest"),
        feature_schema_hash=_hash("feature-schema"),
        embedding_revision=CorrectionFeatureContractV2().embedding_tree_digest,
        numeric_lower=dict.fromkeys(FITTED_FEATURE_V2_SCALARS, 0.0),
        numeric_upper=dict.fromkeys(FITTED_FEATURE_V2_SCALARS, 100.0),
        setting_identity=_hash("setting"),
        declared_limitations=(
            "contract fixture: fitted from four synthetic sources, not from any D3 dataset",
        ),
    )
    return canonical_bytes(payload), payload


def _capability(data: bytes, payload: Any, **overrides: object) -> DirectEvaluationCapability:
    fields: dict[str, object] = {
        "purpose": EvaluationPurpose.SHADOW,
        "component_state": LearnedComponentState.SHADOW,
        "artifact_hash": sha256(data).hexdigest(),
        "component_id": COMPONENT,
        "component_revision": FIXTURE_REVISION,
        "surface": SURFACE,
        "descriptor_hash": FIXTURE_HASH,
        "training_dataset_id": payload.training_dataset_id,
        "split_manifest_hash": payload.split_manifest_hash,
        "member_manifest_hash": payload.member_manifest_hash,
        "selection_manifest_hash": payload.selection_manifest_hash,
    }
    fields.update(overrides)
    return DirectEvaluationCapability(**fields)  # type: ignore[arg-type]


# ----------------------------------------------------- S21D3-052: the direct loader matrix


def _refusal(call) -> str:  # type: ignore[no-untyped-def]
    try:
        call()
    except CorrectionArtifactError as error:
        return str(error)
    return "ACCEPTED"


def _direct_loader_matrix(data: bytes, payload: Any) -> dict[str, Any]:
    """Every way the direct evaluation boundary refuses, and the one way it does not."""
    accepted, loaded = build_ranker_for_evaluation(data, capability=_capability(data, payload))
    v1_document = json.loads(data)
    v1_document["schema_name"] = "correction-ranker-artifact"
    truncated = json.dumps(json.loads(data) | {"exemplars": []}).encode()

    cases = {
        "wrong_artifact_hash": _refusal(
            lambda: build_ranker_for_evaluation(
                data, capability=_capability(data, payload, artifact_hash=_hash("other"))
            )
        ),
        "wrong_media_type": _refusal(
            lambda: build_ranker_for_evaluation(
                data, capability=_capability(data, payload), media_type="application/octet-stream"
            )
        ),
        "oversized": _refusal(
            lambda: build_ranker_for_evaluation(
                data, capability=_capability(data, payload), maximum_bytes=16
            )
        ),
        "corrupt_bytes": _refusal(
            lambda: build_ranker_for_evaluation(
                b"{ not json", capability=_capability(b"{ not json", payload)
            )
        ),
        "empty_exemplars": _refusal(
            lambda: build_ranker_for_evaluation(
                truncated, capability=_capability(truncated, payload)
            )
        ),
        "v1_reader_on_v2_bytes": _refusal(
            lambda: load_correction_ranker(
                data,
                expected_component_id=COMPONENT,
                expected_revision=FIXTURE_REVISION,
                expected_surface=SURFACE,
            )
        ),
        "v2_reader_on_v1_bytes": _refusal(
            lambda: load_correction_ranker_v2(
                json.dumps(v1_document).encode(),
                expected_component_id=COMPONENT,
                expected_revision=FIXTURE_REVISION,
                expected_surface=SURFACE,
                expected_descriptor_hash=FIXTURE_HASH,
            )
        ),
        "wrong_descriptor": _refusal(
            lambda: build_ranker_for_evaluation(
                data, capability=_capability(data, payload, descriptor_hash=_hash("stranger"))
            )
        ),
        "wrong_split_manifest": _refusal(
            lambda: build_ranker_for_evaluation(
                data, capability=_capability(data, payload, split_manifest_hash=_hash("stranger"))
            )
        ),
        "wrong_member_manifest": _refusal(
            lambda: build_ranker_for_evaluation(
                data, capability=_capability(data, payload, member_manifest_hash=_hash("stranger"))
            )
        ),
        "wrong_selection_manifest": _refusal(
            lambda: build_ranker_for_evaluation(
                data,
                capability=_capability(data, payload, selection_manifest_hash=_hash("stranger")),
            )
        ),
    }
    closed_past_shadow = {}
    for state in LearnedComponentState:
        try:
            _capability(data, payload, component_state=state)
        except CorrectionArtifactError as error:
            closed_past_shadow[state.value] = str(error)
        else:
            closed_past_shadow[state.value] = "OPEN"

    return {
        "accepted_exactly_one_artifact": {
            "class": type(accepted).__name__,
            "artifact_hash": sha256(data).hexdigest(),
            "schema": loaded.schema_name,
            "media_type": CORRECTION_ARTIFACT_MEDIA_TYPE,
            "feature_channels": len(loaded.feature_channels),
            "purpose": _capability(data, payload).purpose.value,
            "lifecycle_state": _capability(data, payload).component_state.value,
        },
        "refusals": cases,
        "every_case_refused": all(value != "ACCEPTED" for value in cases.values()),
        "capability_states": closed_past_shadow,
        "open_states": sorted(
            name for name, value in closed_past_shadow.items() if value == "OPEN"
        ),
    }


# --------------------------------------------------- S21D3-055: the resolver health matrix


#: What a resolver would have to name to make a provider, network, GPU or credential call.
#: Checked against the module's own source rather than counted at run time: a counter proves
#: only that these particular fifteen resolutions made no call, and the claim is that no
#: resolution can. The resolver is a frozen dataclass whose every input is passed in.
FORBIDDEN_RESOLVER_REFERENCES = (
    "httpx",
    "requests",
    "aiohttp",
    "socket",
    "openai",
    "anthropic",
    "torch",
    "cuda",
    "os.environ",
    "getenv",
    "api_key",
    "credential",
    "provider",
    "embedding_provider",
)


def _resolver_is_pure() -> dict[str, Any]:
    source = (REPOSITORY / "src/cognitive_os/application/services/learned_runtime.py").read_text(
        encoding="utf-8"
    )
    found = sorted(name for name in FORBIDDEN_RESOLVER_REFERENCES if name in source)
    return {
        "module": "cognitive_os.application.services.learned_runtime",
        "forbidden_references_found": found,
        "provider_network_gpu_or_credential_calls_possible": bool(found),
        "every_input_is_passed_in": True,
    }


def _resolver_matrix(configurations: dict[str, D3RuntimeConfiguration]) -> dict[str, Any]:
    """Resolve under every configuration the acceptance names, and record the reason each gives."""
    embedding = EmbeddingIdentity(
        model_id=CorrectionFeatureContractV2().embedding_model,
        revision=CorrectionFeatureContractV2().embedding_tree_digest,
        available=True,
    )
    resolver = LearnedRuntimeResolver(surface=SURFACE, expected_embedding=embedding)
    canary = configurations["exact_canary"]

    def policy(**overrides: object) -> RoutingPolicy:
        fields: dict[str, object] = {
            "persistence_enabled": True,
            "activation_enabled": True,
            "active_components": (COMPONENT,),
            "routed_groups": canary.routed_group_ids,
            "routing_manifest_hash": canary.routing_manifest_hash,
            "runtime_configuration_hash": canary.content_hash,
        }
        fields.update(overrides)
        return RoutingPolicy(**fields)  # type: ignore[arg-type]

    def state(**overrides: object) -> ActiveComponentState:
        fields: dict[str, object] = {
            "component_id": COMPONENT,
            "surface": SURFACE,
            "revision": FIXTURE_REVISION,
            "model_artifact_id": uuid5(NAMESPACE, "model-artifact"),
            "lineage_verified": True,
            "descriptor_revision": FIXTURE_REVISION,
            "lifecycle_state": LearnedComponentState.ACTIVE,
            "approval_hash": FIXTURE_HASH,
        }
        fields.update(overrides)
        return ActiveComponentState(**fields)  # type: ignore[arg-type]

    def resolve(**overrides: object):  # type: ignore[no-untyped-def]
        fields: dict[str, object] = {
            "policy": policy(),
            "active_states": [state()],
            "group": canary.routed_group_ids[0],
            "artifact": ArtifactAvailability(present=True, bytes_verified=True, size_bytes=4096),
            "local_embedding": embedding,
            "expected_routing_manifest_hash": canary.routing_manifest_hash,
            "expected_configuration_hash": canary.content_hash,
            "expected_approval_hash": FIXTURE_HASH,
        }
        fields.update(overrides)
        return resolver.resolve(**fields)  # type: ignore[arg-type]

    cases: dict[str, dict[str, Any]] = {}
    for name, overrides in (
        ("exact_canary", {}),
        (
            "bounded_steady_state",
            {
                "policy": policy(
                    routed_groups=configurations["bounded_steady_state"].routed_group_ids,
                    routing_manifest_hash=configurations[
                        "bounded_steady_state"
                    ].routing_manifest_hash,
                    runtime_configuration_hash=configurations["bounded_steady_state"].content_hash,
                ),
                "expected_routing_manifest_hash": configurations[
                    "bounded_steady_state"
                ].routing_manifest_hash,
                "expected_configuration_hash": configurations["bounded_steady_state"].content_hash,
            },
        ),
        ("component_absent", {"active_states": []}),
        ("present_but_disabled", {"policy": policy(activation_enabled=False)}),
        (
            "present_in_shadow",
            {"active_states": [state(lifecycle_state=LearnedComponentState.SHADOW)]},
        ),
        (
            "disabled_by_kill_switch",
            {"active_states": [state(lifecycle_state=LearnedComponentState.DISABLED)]},
        ),
        ("unapproved", {"active_states": [state(approval_hash=None)]}),
        ("another_approval", {"active_states": [state(approval_hash=_hash("someone else"))]}),
        ("wrong_configuration", {"policy": policy(runtime_configuration_hash=_hash("other"))}),
        ("loader_refused_missing", {"artifact": ArtifactAvailability(present=False)}),
        (
            "loader_refused_corrupt",
            {"artifact": ArtifactAvailability(present=True, bytes_verified=False)},
        ),
        (
            "loader_refused_oversized",
            {
                "artifact": ArtifactAvailability(
                    present=True, bytes_verified=True, size_bytes=1 << 30
                )
            },
        ),
        ("two_active_revisions", {"active_states": [state(), state(revision=3)]}),
        ("group_not_routed", {"group": "group-never-routed"}),
        (
            "embedding_identity_mismatch",
            {"local_embedding": EmbeddingIdentity("some-other-model", "0", True)},
        ),
        ("persistence_disabled", {"policy": policy(persistence_enabled=False)}),
        ("component_not_allowlisted", {"policy": policy(active_components=())}),
        ("routing_manifest_mismatch", {"expected_routing_manifest_hash": _hash("other")}),
        ("artifact_unverified_lineage", {"active_states": [state(lineage_verified=False)]}),
        (
            "descriptor_revision_mismatch",
            {"active_states": [state(descriptor_revision=FIXTURE_REVISION + 1)]},
        ),
        (
            "embedding_unavailable",
            {"local_embedding": EmbeddingIdentity(embedding.model_id, embedding.revision, False)},
        ),
    ):
        resolved = resolve(**overrides)
        cases[name] = {
            "learned_ordering_permitted": resolved.learned_ordering_permitted,
            "reason": resolved.reason.value,
            "detail": resolved.detail,
        }

    deterministic = sorted(
        name for name, value in cases.items() if not value["learned_ordering_permitted"]
    )
    reached = {value["reason"] for value in cases.values()}
    unreached = sorted(
        reason.value for reason in RuntimeHealthReason if reason.value not in reached
    )
    return {
        "cases": cases,
        "deterministic_fallback_cases": deterministic,
        "permitted_cases": sorted(set(cases) - set(deterministic)),
        "distinct_reasons": sorted(reached),
        "every_reason_code_is_reachable": not unreached,
        "unreached_reason_codes": unreached,
        "purity": _resolver_is_pure(),
    }


def _mandatory_path_hashes(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Execute the decision under every configuration and hash what each one actually did.

    Not asserted — run. Each configuration's resolution decides whether the sequencer receives
    the learned permutation or nothing, the sequencer executes the whole task, and the digest
    is taken over the order it attempted. A resolver that permitted ordering where it should
    have refused would change one of these digests, which is the only way this file can catch
    that at all.
    """
    candidates = tuple(uuid5(NAMESPACE, f"mandatory-{index}") for index in range(4))
    learned = tuple(reversed(candidates))

    async def attempt(candidate_id: UUID) -> AttemptResult:
        return AttemptResult(
            candidate_id=candidate_id,
            accepted=False,
            event_id=uuid5(NAMESPACE, f"mandatory-event-{candidate_id}"),
            verifier_evidence_hash=_hash(f"verifier:{candidate_id}"),
        )

    sequencer = CorrectionCandidateSequencer(CodingEventService(MemoryEventStore()))

    def order_under(permitted: bool) -> str:
        outcome = asyncio.run(
            sequencer.run_task(
                campaign_id=uuid5(NAMESPACE, "mandatory-campaign"),
                task_id=uuid5(NAMESPACE, "mandatory-task"),
                partition="canary",
                mode=SequenceMode.STOP_ON_FIRST_ACCEPTED,
                campaign_manifest_hash=FIXTURE_HASH,
                baseline_order=candidates,
                attempt=attempt,
                resolved_order=learned if permitted else None,
                learned_ordering_used=permitted,
            )
        )
        return _hash(_canonical_bytes([str(item) for item in outcome.attempted_order]).decode())

    executed = {
        name: order_under(value["learned_ordering_permitted"]) for name, value in cases.items()
    }
    mandatory = {
        name: digest
        for name, digest in executed.items()
        if not cases[name]["learned_ordering_permitted"]
    }
    permitted = {
        name: digest
        for name, digest in executed.items()
        if cases[name]["learned_ordering_permitted"]
    }
    return {
        "case_set_hash": _hash(_canonical_bytes([str(item) for item in candidates]).decode()),
        "case_count": len(candidates),
        "decision_hash_by_configuration": executed,
        "identical": len(set(mandatory.values())) == 1,
        "configurations_compared": sorted(mandatory),
        "mandatory_decision_hash": next(iter(set(mandatory.values())), None),
        "only_a_bounded_campaign_may_reorder": bool(permitted)
        and not set(permitted.values()) & set(mandatory.values()),
        "campaign_configurations": sorted(permitted),
    }


# ------------------------------------------------- S21D3-053: the sequencer under a resume


def _sequencer_proof() -> dict[str, Any]:
    """Learned ranking reorders the remainder; it never widens it, and never skips a verifier."""
    campaign = uuid5(NAMESPACE, "campaign")
    task = uuid5(NAMESPACE, "task")
    candidates = tuple(uuid5(NAMESPACE, f"candidate-{index}") for index in range(4))
    verified: list[UUID] = []

    async def attempt(candidate_id: UUID) -> AttemptResult:
        verified.append(candidate_id)
        return AttemptResult(
            candidate_id=candidate_id,
            accepted=candidate_id == candidates[2],
            event_id=uuid5(NAMESPACE, f"event-{candidate_id}"),
            verifier_evidence_hash=_hash(f"verifier:{candidate_id}"),
        )

    remaining = tuple(
        RealityRunIdentity(
            task_id=task,
            task_manifest_hash=FIXTURE_HASH,
            run_kind=RealityRunKind.CANDIDATE,
            candidate_id=candidate_id,
            strategy=RealityCandidateStrategy.CORRECT_NARROW,
            source=RealityCandidateSource.CURATED,
            generator_profile_id="reality.tasks",
            verifier_profile_hash=FIXTURE_HASH,
            campaign_version=1,
        )
        for candidate_id in candidates[1:]
    )
    resume = ReceiptAwareResumePlan(
        plan=ResumePlan(remaining=remaining),
        tasks=(
            TaskReceiptState(
                task_id=task,
                action=ReceiptAction.REPLAY_MISSING_OUTCOME,
                attempted=(candidates[0],),
                intentionally_unattempted=(),
                effective_remaining=remaining,
            ),
        ),
    )

    sequencer = CorrectionCandidateSequencer(CodingEventService(MemoryEventStore()))
    outcome = asyncio.run(
        sequencer.run_task(
            campaign_id=campaign,
            task_id=task,
            partition="canary",
            mode=SequenceMode.STOP_ON_FIRST_ACCEPTED,
            campaign_manifest_hash=FIXTURE_HASH,
            baseline_order=candidates,
            attempt=attempt,
            resolved_order=tuple(reversed(candidates)),
            learned_ordering_used=True,
            resume=resume,
        )
    )
    return {
        "baseline_order": [str(item) for item in candidates],
        "resolved_order": [str(item) for item in outcome.resolved_order],
        "effective_remainder": [str(item) for item in resume.remainder_for(task)],
        "attempted_order": [str(item) for item in outcome.attempted_order],
        "intentionally_unattempted": [str(item) for item in outcome.intentionally_unattempted],
        "every_attempt_ran_the_hidden_verifier": verified
        == [item for item in outcome.attempted_order],
        "learned_order_changed_attempt_order_only": set(outcome.attempted_order)
        <= set(resume.remainder_for(task)),
        "already_recorded_candidate_did_not_re_enter": candidates[0] not in outcome.attempted_order,
        "stopped_at_first_acceptance": outcome.accepted_candidate_id == candidates[2],
        "stop_reason": outcome.stop_reason,
    }


# --------------------------------------------------------- the two canonical configurations


def _configurations() -> dict[str, D3RuntimeConfiguration]:
    """Declared, hashed, and deliberately not sealed: sealing happens at authorised access.

    S21D3-059 seals these before final access is granted. This sprint does not grant it, so
    the two documents exist as contracts with reproducible hashes and the checkpoint records
    them as declared rather than sealed. A sealed configuration bound to evidence nobody read
    would be a claim about a run that never happened.
    """
    common: dict[str, Any] = {
        "component_id": COMPONENT,
        "component_revision": FIXTURE_REVISION,
        "surface": SURFACE,
        "routing_manifest_hash": _hash("s21d3-routing-manifest"),
        "sequence_mode": "stop_on_first_accepted",
        "persistence_enabled": True,
        "activation_enabled": True,
        "kill_switch_enabled": True,
        "maximum_inference_ms": 250,
        "fallback_on_refusal": "frozen deterministic baseline order",
    }
    return {
        "exact_canary": D3RuntimeConfiguration(
            name="exact_canary",
            routed_group_ids=("d3-canary-group-01",),
            maximum_tasks=20,
            declared_limitations=(
                "one routed group and twenty tasks: the smallest set that could show a "
                "safety or verifier regression at all",
            ),
            **common,
        ),
        "bounded_steady_state": D3RuntimeConfiguration(
            name="bounded_steady_state",
            routed_group_ids=("d3-canary-group-01", "d3-steady-group-01", "d3-steady-group-02"),
            maximum_tasks=200,
            declared_limitations=(
                "bounded by task count rather than by time: a steady state with no bound is "
                "an activation nobody has to revisit",
            ),
            **common,
        ),
    }


def _transition_condition() -> CanaryToSteadyCondition:
    return CanaryToSteadyCondition(
        minimum_canary_tasks=20,
        maximum_accepted_safety_regressions=0,
        maximum_verifier_disagreements=0,
        rollback_target_revision=1,
    )


# ------------------------------------------------------------ S21D3-059: the checkpoint


def _preconditions() -> list[dict[str, Any]]:
    """Every S21D3-059 precondition, evaluated against what is actually committed.

    In backlog order, so the first failure the checkpoint reports is the first the plan
    declares — not whichever file happened to be read first.
    """
    selection = _read(SELECTION)["selection"]
    continuation = _read(DIAGNOSTIC)
    holdout = _read(HOLDOUT)

    def item(name: str, passed: bool, detail: str, evidence: Path) -> dict[str, Any]:
        return {
            "name": name,
            "passed": passed,
            "detail": detail,
            "evidence": evidence.name,
            "evidence_sha256": _hash(evidence.read_text(encoding="utf-8")),
        }

    return [
        item(
            "S21D3-039 selected one candidate",
            bool(selection["selected"]),
            selection.get("null_reason") or "one candidate was selected",
            SELECTION,
        ),
        item(
            "the diagnostic continuation permits correction work",
            continuation["outcome"] == "proceed",
            f"{continuation['outcome']}: {continuation['reason']}",
            DIAGNOSTIC,
        ),
        item(
            "S21D3-051 stored one artifact",
            False,
            "not opened: an artifact can only be fitted for a selected candidate",
            SELECTION,
        ),
        item(
            "S21D3-054 proved the selected-artifact vertical slice",
            False,
            "not opened: the slice runs the selected artifact, which does not exist",
            SELECTION,
        ),
        item(
            "S21D3-056 registered the artifact and entered SHADOW",
            False,
            "not opened: registration names an artifact revision that was never fitted",
            SELECTION,
        ),
        item(
            "the independent retrieval branch reached a result",
            holdout["decision"]["winning_arm"] is not None,
            f"first failed floor {holdout['decision'].get('first_failed_floor')}",
            HOLDOUT,
        ),
    ]


def _checkpoint(recorded_at: str, invariance: dict[str, Any]) -> dict[str, Any]:
    preconditions = _preconditions()
    failed = [item for item in preconditions if not item["passed"]]
    first = failed[0] if failed else None
    selection = _read(SELECTION)
    stop_hash = selection["selection"]["content_hash"]

    return {
        "schema_version": 1,
        "sprint": "21D3",
        "wave": "W4",
        "items": [
            "S21D3-048",
            "S21D3-050",
            "S21D3-051",
            "S21D3-054",
            "S21D3-056",
            "S21D3-059",
        ],
        "recorded_at": recorded_at,
        "pre_registration_sha256": _hash(PRE_REGISTRATION.read_text(encoding="utf-8")),
        "final_outcomes_inspected": False,
        "final_or_canary_outcomes_inspected": 0,
        "promotion_contract": {
            "schema": D3_PROMOTION_SCHEMA,
            "schema_version": D3_PROMOTION_SCHEMA_VERSION,
            "gates": list(D3_PROMOTION_GATES),
            "gate_count": len(D3_PROMOTION_GATES),
            "legacy_payloads_readable": True,
        },
        "artifact_contract": {
            "schema": CORRECTION_ARTIFACT_SCHEMA_V2,
            "media_type": CORRECTION_ARTIFACT_MEDIA_TYPE,
            "feature_channels": len(FITTED_FEATURE_V2_ALLOWLIST),
            "feature_contract_hash": CorrectionFeatureContractV2().content_hash,
            "fixture_artifact_sha256": invariance["fixture_artifact_sha256"],
            "selected_artifact_exists": False,
        },
        "runtime_configurations": {
            name: {
                "content_hash": configuration.content_hash,
                "routed_groups": len(configuration.routed_group_ids),
                "maximum_tasks": configuration.maximum_tasks,
                "sealed": False,
                "sealed_reason": (
                    "sealing happens at authorised final access; access was not authorised"
                ),
            }
            for name, configuration in _configurations().items()
        },
        "canary_to_steady_condition": {
            "content_hash": _transition_condition().content_hash,
            "minimum_canary_tasks": _transition_condition().minimum_canary_tasks,
            "maximum_accepted_safety_regressions": 0,
            "rollback_target_revision": _transition_condition().rollback_target_revision,
            "sealed": False,
        },
        "preconditions": preconditions,
        "decision": {
            "authorised": False,
            "first_failed_precondition": None if first is None else first["name"],
            "reason": None if first is None else first["detail"],
            "stop_hash": stop_hash,
            "stop_source": "S21D3-039 candidate selection",
            "opens_no_parametric_rung": True,
            "capability_granted": None,
        },
        "not_opened": [
            {
                "item": item_id,
                "would_have": description,
                "status": "not_opened",
                "stop_hash": stop_hash,
                "stop_source": "S21D3-039 candidate selection",
            }
            for item_id, description in DEPENDENT_ITEMS
        ],
        "unconditional": [
            {"item": item_id, "runs": description, "status": "open"}
            for item_id, description in UNCONDITIONAL_ITEMS
        ],
        "independent_branch": {
            "item": "S21D3-040 through S21D3-047",
            "status": "completed",
            "note": "the retrieval branch reached its own hash-bound negative result in W3",
        },
    }


# ------------------------------------------------------------------------------ entry point


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE)
    arguments = parser.parse_args()

    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    data, payload = _fixture_artifact()
    configurations = _configurations()
    resolver = _resolver_matrix(configurations)

    invariance = {
        "schema_version": 1,
        "sprint": "21D3",
        "wave": "W4",
        "items": ["S21D3-052", "S21D3-053", "S21D3-055"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": _hash(PRE_REGISTRATION.read_text(encoding="utf-8")),
        "final_outcomes_inspected": False,
        "artifact_under_test": "contract_fixture",
        "artifact_under_test_note": (
            "S21D3-039 selected no candidate, so no D3 artifact exists. Every artifact here is "
            "built by this script to satisfy the v2 schema, and proves the contract rather "
            "than the D3 lifecycle projection."
        ),
        "fixture_artifact_sha256": sha256(data).hexdigest(),
        "fixture_artifact_bytes": len(data),
        "direct_loader": _direct_loader_matrix(data, payload),
        "resolver_matrix": resolver,
        "mandatory_path_invariance": _mandatory_path_hashes(resolver["cases"]),
        "sequencer": _sequencer_proof(),
        "configurations": {
            name: {
                "content_hash": configuration.content_hash,
                "document": configuration.model_dump(mode="json"),
            }
            for name, configuration in configurations.items()
        },
        "creates_lifecycle_state": False,
        "writes_to_any_artifact_store": False,
    }
    checkpoint = _checkpoint(recorded_at, invariance)

    _write(arguments.output_dir / "sprint-21d3-runtime-invariance.json", invariance)
    _write(arguments.output_dir / "sprint-21d3-pre-final-checkpoint.json", checkpoint)

    print(
        json.dumps(
            {
                "recorded_at": recorded_at,
                "direct_loader_refusals": len(invariance["direct_loader"]["refusals"]),
                "every_case_refused": invariance["direct_loader"]["every_case_refused"],
                "resolver_cases": len(resolver["cases"]),
                "unreached_reason_codes": resolver["unreached_reason_codes"],
                "mandatory_path_identical": invariance["mandatory_path_invariance"]["identical"],
                "authorised": checkpoint["decision"]["authorised"],
                "first_failed_precondition": checkpoint["decision"]["first_failed_precondition"],
                "stop_hash": checkpoint["decision"]["stop_hash"],
                "not_opened": len(checkpoint["not_opened"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
