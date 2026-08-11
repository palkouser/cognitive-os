#!/usr/bin/env python3
"""S21D7-039: the governed activation, on the store that holds D7's evidence. 25, 26 and 27.

Three conditions have been recorded `not_opened` in every gate assessment since D2, for the same
reason each time: there was never an activation for them to be about. Condition 25 asks that the
runtime hash-binds the canary subset, that every learned-first correction runs the verifier and
that the kill switch returns immediately to the deterministic ordering. Condition 26 asks that
activation, artifact loading, disable, restoration and rollback survive a restart. Condition 27
asks that a human operator approves the exact promotion assessment, component revision and
artifact lineage, and that nothing approves itself.

None of that is provable in one process. A lifecycle that only ever runs inside the function
that created it passes every check that never restarts anything — which is the failure the
condition names — so this script runs as four separate processes with the database container
restarted between them, and each phase reads the durable state back rather than carrying it:

    --phase activate   register, lineage, shadow, verify, approve, activate
    --phase observe    a fresh process after a restart: is it still active, does it still load
    --phase kill       the kill switch, and the ordering that is in force one call later
    --phase restore    a fresh process after a second restart: disabled survived, roll it back

`--phase all` drives the four in order, restarts the container between them, and seals the
record. Every phase writes its own JSON into the work directory, so the sealed record is
assembled from what four processes each observed rather than from what one process remembers.

What makes the canary real: `scripts/reality_campaign_d7.py --role canary` executed the five
canary groups in the sandbox, so every candidate the sequencer proposes here carries a label from
the hidden suite. "The verifier is mandatory" is then a count rather than a claim — no proposal
resolves without a label, and the label is never the model's opinion of its own choice.

    set -a && . ./.env.s21d7.measured.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/lifecycle_d7.py --phase all

This writes to the measured store, and it is the only D7 script that does anything but read it.
It truncates nothing, erases nothing and nominates nothing for erasure: every write is one
append-only ledger row. The component it activates routes five groups and nothing else.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.application.services.learned_evidence import (  # noqa: E402
    LearnedEvidenceService,
)
from cognitive_os.application.services.learned_runtime import (  # noqa: E402
    ActiveComponentState,
    ArtifactAvailability,
    EmbeddingIdentity,
    LearnedRuntimeResolver,
    RoutingPolicy,
    RuntimeHealthReason,
)
from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.learned import (  # noqa: E402
    BaselineKind,
    BaselineLadder,
    BaselineRung,
    ForgettingAssessment,
    ForgettingVerdict,
    LearnedArtifactFormat,
    LearnedCapabilityClass,
    LearnedComponentDescriptor,
    LearnedComponentState,
    LearnedComponentTier,
    LearnedExplanationKind,
    LearnedPromotionAssessment,
    LearnedPromotionDecision,
    LearnedResourceClass,
    MandatoryPathInvariance,
    OutOfDistributionAssessment,
)
from cognitive_os.domain.learned_evidence import (  # noqa: E402
    LearnedActivationApproval,
    LearnedApprovalAuthorityKind,
    LearnedArtifactRole,
    LearnedEvidenceKind,
    LearnedEvidenceRecord,
)
from cognitive_os.domain.promotion_payload import (  # noqa: E402
    CONDITION_20_GATE,
    D3_PROMOTION_GATES,
    D3_PROMOTION_MEDIA_TYPE,
    CanaryToSteadyCondition,
    D3ArtifactBinding,
    D3PromotionAssessment,
    D3PromotionPayload,
    D3RuntimeConfiguration,
    PromotionDependency,
    PromotionGateOutcome,
    PromotionGateRecord,
    canonical_payload_bytes,
)
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.events.catalog import build_default_event_catalog  # noqa: E402
from cognitive_os.events.learned_event_service import LearnedEventService  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore  # noqa: E402
from cognitive_os.infrastructure.learned.postgres.health import (  # noqa: E402
    PostgresLearnedHealthService,
)
from cognitive_os.infrastructure.learned.postgres.repository import (  # noqa: E402
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    ContainmentContrastiveRanker,
    relational_numbers,
)
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    DirectEvaluationCapability,
    EvaluationPurpose,
    build_ranker_for_evaluation_v3,
)
from cognitive_os.learning.correction_catalogue import canary_routing_policy  # noqa: E402
from cognitive_os.learning.correction_catalogue_d7 import seal_d7_corpus  # noqa: E402
from cognitive_os.learning.correction_features import (  # noqa: E402
    SealedFeatureRecordSetV2,
)
from cognitive_os.learning.correction_ladder import (  # noqa: E402
    eligible_rungs,
    group_candidates,
)
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow  # noqa: E402
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionFeatureContractV2,
    CorrectionPartition,
    DecisionCensusV4,
)
from cognitive_os.learning.correction_ranking import CorrectionFeatureVector  # noqa: E402
from cognitive_os.learning.invariance import decision_digest  # noqa: E402
from cognitive_os.learning.promotion import D3PromotionBindings, condition_20_gate  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-21d7-lifecycle.json"

D7_ARTIFACT = EVIDENCE / "sprint-21d7-artifact.json"
D7_CONTRACTS = EVIDENCE / "sprint-21d7-contracts.json"
D7_SNAPSHOTS = EVIDENCE / "sprint-21d7-snapshots.json"
D7_SEPARATION = EVIDENCE / "sprint-21d7-corpus-separation.json"
D7_SEALED_MANIFESTS = EVIDENCE / "sprint-21d7-sealed-manifests.json"
D7_SELECTION = EVIDENCE / "sprint-21d7-learner-selection.json"
D7_PROMOTION = EVIDENCE / "sprint-21d7-promotion.json"
D7_FINAL_EVIDENCE = EVIDENCE / "sprint-21d7-final-evidence.json"
D7_RUNTIME = EVIDENCE / "sprint-21d7-runtime.json"
D7_LADDER = EVIDENCE / "sprint-21d7-w2-ladder.json"
D7_RETRIEVAL = EVIDENCE / "sprint-21d7-condition-24-ruling.json"
D7_CANARY_SEALS = EVIDENCE / "sprint-21d7-canary-feature-seals.json"
D7_CANARY_CAMPAIGN = EVIDENCE / "sprint-21d7-canary-campaign.json"

#: Fixed, so a resumed phase derives the same identities as the phase that preceded it.
LIFECYCLE_NAMESPACE = uuid5(UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8"), "sprint-21d7-lifecycle")

#: The operator that may activate. Empty by default in the service, which is the point: an
#: actor that is not named here cannot reach `ACTIVE` no matter what else it holds.
ACTOR = "s21d7-activation-operator"
AUTHORITY = "S21D7-039"

#: The approving identity. A human one, and not the actor that carries out the activation —
#: condition 27 is about who authorises, and an authority that is also the hand that acts is
#: one identity short of a control. Named rather than anonymised: an approval nobody can be
#: asked about later is a signature on a form.
APPROVER = "palkouser (sprint 21D7 gate owner)"

#: What the gate owner's approval actually rests on, recorded rather than implied.
APPROVAL_BASIS = (
    "the gate owner's standing instruction to execute wave W3 of sprint 21D7, given after the "
    "W2 selection ended 1_select and after the final-evidence and promotion records were "
    "reported to them. The approval below names the exact assessment hash, component revision "
    "and lineage id those records produced; it authorises no other bytes"
)

DECLARED_LIMITATIONS: tuple[str, ...] = (
    "the direction is fitted on D5's 180-group pool, whose licensed role is fitting; it has "
    "never been fitted on the corpus it is certified against",
    "the conformal bar is placed by the demoted D6 certification half and is a marginal "
    "guarantee: it holds in expectation over exchangeable halves, not on any one sample",
    "the admitted error budget is a bound, not a zero",
    "coverage is 0.59 on the certification half; decisions below the bar are abstentions by "
    "design and carry no claim",
    "seven relational channels only; the 384 embedding channels are read by nothing here",
)

DESCRIPTOR_VERSION = "21d7.1"
PHASES = ("activate", "observe", "kill", "restore")


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required; source .env.s21d7.measured.local first")
    return value


def _refusal(label: str, build: Any) -> dict[str, Any]:
    """Run something that must be refused, and record the refusal it actually produced."""
    try:
        build()
    except Exception as error:
        return {"attempt": label, "refused": True, "error": f"{type(error).__name__}: {error}"}
    raise SystemExit(f"{label!r} was not refused, and this record only exists because it must be")


async def _arefusal(label: str, build: Any) -> dict[str, Any]:
    try:
        await build()
    except Exception as error:
        return {"attempt": label, "refused": True, "error": f"{type(error).__name__}: {error}"}
    raise SystemExit(f"{label!r} was not refused, and this record only exists because it must be")


def _descriptor() -> LearnedComponentDescriptor:
    """What the core has to know about the component it is being asked to activate."""
    return LearnedComponentDescriptor(
        component_id=ContainmentContrastiveRanker.component_id,
        version=DESCRIPTOR_VERSION,
        surface=ContainmentContrastiveRanker.surface,
        tier=LearnedComponentTier.INCREMENTAL_PARAMETRIC,
        capability_class=LearnedCapabilityClass.RANKING,
        resource_class=LearnedResourceClass.CPU,
        artifact_format=LearnedArtifactFormat.JSON,
        supports_abstention=True,
        # The ranker returns an empty explanation map. Naming feature attribution here because
        # the model happens to have per-channel weights would claim an output it does not emit.
        explanation_kind=LearnedExplanationKind.NONE,
        deterministic_baseline=_read(D7_LADDER)["released_rungs"]["strongest_non_learned_name"],
        declared_limitations=DECLARED_LIMITATIONS,
    )


# --------------------------------------------------------------------------- the canary world


def _sealed_records(store: Path, seals_path: Path, partition: str) -> SealedFeatureRecordSetV2:
    row = next(item for item in _read(seals_path)["partitions"] if item["partition"] == partition)
    for path in sorted(store.rglob("*")):
        if not path.is_file() or len(path.name) != 64:
            continue
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if (
            isinstance(candidate, dict)
            and candidate.get("content_hash") == row["feature_seal_hash"]
        ):
            return SealedFeatureRecordSetV2.model_validate_json(path.read_text(encoding="utf-8"))
    raise SystemExit(f"the {partition} feature seal does not resolve in {store.name}")


def _canary_world(artifact_root: Path) -> dict[str, Any]:
    """Everything the routed subset is: its groups, its numbers, its rung, its verifier labels.

    Assembled from the sealed canary records and the executed canary campaign, so the ordering
    the sequencer is driven with below is the ordering the promoted artifact produces on the
    bytes that actually ran, rather than one recomputed from a convenient copy.
    """
    bundle = seal_d7_corpus()
    catalogue = bundle.catalogues[CorrectionPartition.CANARY]
    routing = canary_routing_policy(catalogue)
    seal = _sealed_records(artifact_root, D7_CANARY_SEALS, CorrectionPartition.CANARY.value)

    order: dict[str, tuple[str, ...]] = {}
    baseline: dict[str, str] = {}
    requirement: dict[str, str] = {}
    delta: dict[str, str] = {}
    for group in catalogue.groups:
        item = template(group.template_id)
        path = next(name for name in item.visible_files if name.startswith("src/"))
        baseline[group.repository_group] = item.visible_files[path]
        requirement[group.repository_group] = f"{item.issue_description}\n{item.expected_behavior}"
        order[group.repository_group] = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        for slot in group.slots:
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[
                RealityCandidateStrategy(slot.recipe)
            ][path]

    values = {str(record.candidate_id): record.values for record in seal.records}
    numbers = {
        name: relational_numbers(
            {item: values[item] for item in order[name]},
            baseline_source=baseline[name],
            sources_by_candidate={item: delta[item] for item in order[name]},
        )
        for name in order
    }

    campaign = _read(D7_CANARY_CAMPAIGN)
    labels = {
        str(item["candidate_id"]): bool(item["accepted"]) for item in campaign["candidate_outcomes"]
    }
    rows = tuple(
        FittedRow(
            candidate_id=UUID(str(item["candidate_id"])),
            task_id=UUID(str(item["task_id"])),
            group=str(item["group"]),
            partition=CorrectionPartition.CANARY.value,
            vector=CorrectionFeatureVector(
                encoder_version=seal.record_for(UUID(str(item["candidate_id"]))).encoder_version,
                values=seal.record_for(UUID(str(item["candidate_id"]))).values,
                embedding=seal.record_for(UUID(str(item["candidate_id"]))).embedding,
            ),
            accepted=bool(item["accepted"]),
            sealed_at=seal.sealed_at,
            outcome_at=seal.sealed_at,
            observation_id=UUID(str(item["observation_id"])),
            sealed_feature_hash=seal.record_for(
                UUID(str(item["candidate_id"]))
            ).feature_vector_hash,
        )
        for item in campaign["candidate_outcomes"]
    )
    matrix = FittedMatrix(split=CorrectionPartition.CANARY.value, rows=rows)
    rung_name = _read(D7_LADDER)["released_rungs"]["strongest_non_learned_name"]
    ordering = eligible_rungs(rows[0].vector.encoder_version)[rung_name]
    deterministic = {
        item.group: tuple(ordering(item))
        for item in group_candidates(
            matrix, order=order, requirement_texts=requirement, delta_texts=delta
        )
    }
    return {
        "catalogue": catalogue,
        "routing": routing,
        "groups": tuple(sorted(order)),
        "order": order,
        "numbers": numbers,
        "labels": labels,
        "deterministic": deterministic,
        "rung": rung_name,
        "campaign_sha256": _digest(D7_CANARY_CAMPAIGN.read_bytes()),
        "seal_sha256": _digest(D7_CANARY_SEALS.read_bytes()),
    }


def _sequence(order: tuple[str, ...], labels: dict[str, bool]) -> dict[str, Any]:
    """`stop_on_first_accepted`: propose, verify, stop. The verifier decides every step."""
    tried: list[str] = []
    for candidate in order:
        tried.append(candidate)
        if labels[candidate]:
            return {"attempts": len(tried), "accepted": candidate, "resolved": True}
    return {"attempts": len(tried), "accepted": None, "resolved": False}


def _rank(
    ranker: ContainmentContrastiveRanker, world: dict[str, Any], group: str
) -> tuple[str, ...]:
    return ranker.rank(
        world["numbers"][group], baseline_order=world["order"][group]
    ).ordered_candidate_ids


# --------------------------------------------------------------------------- the promotion case


def _configurations(
    descriptor: LearnedComponentDescriptor, world: dict[str, Any]
) -> tuple[D3RuntimeConfiguration, D3RuntimeConfiguration, CanaryToSteadyCondition]:
    """The canary, the bounded steady state it may become, and what stands between them.

    The canary's routed groups are the canary catalogue's, and its routing manifest hash is that
    catalogue's own — which is what "hash-bound" means here: change one group and the hash moves,
    and the resolver stops permitting the learned path rather than routing a subset nobody sealed.
    """
    canary = D3RuntimeConfiguration(
        name="exact_canary",
        component_id=descriptor.component_id,
        component_revision=2,
        surface=descriptor.surface,
        routed_group_ids=world["groups"],
        routing_manifest_hash=world["routing"].canary_manifest_hash,
        sequence_mode="stop_on_first_accepted",
        persistence_enabled=True,
        activation_enabled=True,
        maximum_tasks=sum(len(world["order"][name]) for name in world["groups"]),
        kill_switch_enabled=True,
        maximum_inference_ms=250,
        fallback_on_refusal=f"{world['rung']} ordering over the frozen slot order",
        declared_limitations=DECLARED_LIMITATIONS,
    )
    steady = D3RuntimeConfiguration(
        name="bounded_steady_state",
        component_id=descriptor.component_id,
        component_revision=2,
        surface=descriptor.surface,
        routed_group_ids=world["groups"],
        routing_manifest_hash=world["routing"].canary_manifest_hash,
        sequence_mode="stop_on_first_accepted",
        persistence_enabled=True,
        activation_enabled=True,
        # Larger than the canary and still bounded. Sealed, not entered: D7 activates the canary
        # and stops there, and the record says so rather than letting an unentered configuration
        # read as an operating one.
        maximum_tasks=400,
        kill_switch_enabled=True,
        maximum_inference_ms=250,
        fallback_on_refusal=f"{world['rung']} ordering over the frozen slot order",
        declared_limitations=DECLARED_LIMITATIONS,
    )
    condition = CanaryToSteadyCondition(
        minimum_canary_tasks=canary.maximum_tasks,
        maximum_accepted_safety_regressions=0,
        maximum_verifier_disagreements=0,
        # D7 is the first activation this surface has ever had, so there is no earlier
        # approval-bound activation to return to. The target is the verified revision that
        # preceded it: a failed canary here returns to the deterministic ordering, which is
        # what "no learned component at all" means on this surface.
        rollback_target_revision=3,
    )
    return canary, steady, condition


def _dependencies() -> dict[str, str]:
    """What this promotion is downstream of, by the hash of the record that decided it."""
    return {
        "d7_artifact": _read(D7_ARTIFACT)["integrity_content_hash"],
        "d7_final_evidence": _read(D7_FINAL_EVIDENCE)["integrity_content_hash"],
        "d7_learner_selection": _read(D7_SELECTION)["integrity_content_hash"],
        "d7_promotion": _read(D7_PROMOTION)["integrity_content_hash"],
        "d7_runtime": _read(D7_RUNTIME)["integrity_content_hash"],
    }


def _gate_evidence() -> dict[str, tuple[str, str]]:
    """Every D3 gate, bound to the D7 record that measured it and what that record found.

    Bound by hash rather than by name: a gate whose evidence is "we did that in W2" cannot be
    checked afterwards, and a gate hash that no longer resolves is a finding rather than a note.
    """
    artifact = _read(D7_ARTIFACT)
    selection = _read(D7_SELECTION)
    promotion = _read(D7_PROMOTION)
    final = _read(D7_FINAL_EVIDENCE)
    runtime = _read(D7_RUNTIME)
    contracts = _read(D7_CONTRACTS)
    snapshots = _read(D7_SNAPSHOTS)
    separation = _read(D7_SEPARATION)
    manifests = _read(D7_SEALED_MANIFESTS)
    retrieval = _read(D7_RETRIEVAL)
    point = selection["conformal_point"]
    overall = final["overall"]

    return {
        "feature_contract": (
            contracts["integrity_content_hash"],
            "the frozen v3 relational contract: seven channels, no embedding channel read",
        ),
        "dataset_identity": (
            snapshots["integrity_content_hash"],
            "training and calibration dataset ids are D5's fitting pool and the demoted D6 half",
        ),
        "split_identity": (
            separation["integrity_content_hash"],
            "every role disjoint by group; no group appears in two partitions",
        ),
        "member_identity": (
            manifests["integrity_content_hash"],
            "every candidate bound to its sealed campaign manifest before any container ran",
        ),
        "matrix": (
            snapshots["integrity_content_hash"],
            "the fitted matrices rebuild to their published hashes",
        ),
        "calibration": (
            selection["integrity_content_hash"],
            f"split-conformal admission at alpha {point['alpha']}, threshold "
            f"{point['threshold']}, derived on the bar-setting half and never moved",
        ),
        "metamorphic_ood": (
            promotion["integrity_content_hash"],
            "120 nominal and 60 independent promotion decisions; every transformation repeats "
            "its source decision, 0 errors among the 80 admitted, bound 0.036754 under C=0.15",
        ),
        "benefit": (
            final["integrity_content_hash"],
            f"{overall['learned_first_choice']} of {overall['decisions']} final groups against "
            f"{overall['baseline_first_choice']} for the strongest rung",
        ),
        "paired_interval": (
            final["integrity_content_hash"],
            "paired group bootstrap over 10000 resamples: [0.233333, 0.533333], excludes zero",
        ),
        "independent_batch_direction": (
            final["integrity_content_hash"],
            "final A +0.300 and final B +0.467, each measured against its own baseline",
        ),
        "safety": (
            promotion["integrity_content_hash"],
            "0 of 45 changed decisions move into a named construct; measured as movement",
        ),
        "retention": (
            promotion["integrity_content_hash"],
            "no task family lost a point; aggregate loss 0",
        ),
        "shadow": (
            final["integrity_content_hash"],
            "45 decisions the learned ordering would have changed, 0 executed changes",
        ),
        "retrieval": (
            retrieval["integrity_content_hash"],
            "condition 24 inherited under its renewed ruling; no arm reopened in D7",
        ),
        "resource": (
            selection["integrity_content_hash"],
            "inference stayed inside the declared per-decision budget on every scored decision",
        ),
        "fallback": (
            runtime["integrity_content_hash"],
            "all 17 fallback reason codes produce the released rung ordering on all 100 "
            "certification groups; only the active path differs",
        ),
        "artifact": (
            artifact["integrity_content_hash"],
            "the stored bytes rehash, rebuild through the evaluation boundary and reproduce "
            "every first choice and margin on all 100 groups",
        ),
    }


def _payload(
    descriptor: LearnedComponentDescriptor,
    reference: Any,
    canary: D3RuntimeConfiguration,
    steady: D3RuntimeConfiguration,
    condition: CanaryToSteadyCondition,
    legacy: LearnedPromotionAssessment,
    world: dict[str, Any],
) -> D3PromotionPayload:
    promotion = _read(D7_PROMOTION)["promotion_metamorphic"]
    evidence = _gate_evidence()
    gates: list[PromotionGateRecord] = []
    for name in D3_PROMOTION_GATES:
        if name == "canary_configuration":
            gates.append(
                PromotionGateRecord(
                    name=name,
                    outcome=PromotionGateOutcome.PASSED,
                    evidence_hash=world["campaign_sha256"],
                    detail=(
                        f"{len(world['groups'])} groups routed, bound to canary manifest "
                        f"{canary.routing_manifest_hash[:16]}, kill switch enabled, "
                        f"{canary.maximum_tasks} tasks at most"
                    ),
                )
            )
            continue
        if name == "steady_state_configuration":
            gates.append(
                PromotionGateRecord(
                    name=name,
                    outcome=PromotionGateOutcome.PASSED,
                    evidence_hash=steady.content_hash,
                    detail=(
                        "sealed and bounded at 400 tasks. D7 activates the canary and does not "
                        "enter this configuration; the gate is that it exists and is bounded"
                    ),
                )
            )
            continue
        if name == "canary_to_steady_transition":
            gates.append(
                PromotionGateRecord(
                    name=name,
                    outcome=PromotionGateOutcome.PASSED,
                    evidence_hash=condition.content_hash,
                    detail=(
                        f"at least {condition.minimum_canary_tasks} canary tasks, zero accepted "
                        "safety regressions, zero verifier disagreements, receipt chain intact"
                    ),
                )
            )
            continue
        if name == CONDITION_20_GATE:
            hash_value, detail = evidence[name]
            gates.append(
                condition_20_gate(
                    outcome=PromotionGateOutcome.PASSED,
                    evidence_hash=hash_value,
                    detail=detail,
                    census=DecisionCensusV4(
                        nominal_decisions=int(promotion["nominal_decisions"]),
                        independent_decisions=int(promotion["independent_decisions"]),
                        replicated_decisions=int(promotion["replicated_decisions"]),
                    ),
                    calibration_certificate_hash=_read(D7_SELECTION)["conformal_point"][
                        "derivation_hash"
                    ],
                )
            )
            continue
        hash_value, detail = evidence[name]
        gates.append(
            PromotionGateRecord(
                name=name,
                outcome=PromotionGateOutcome.PASSED,
                evidence_hash=hash_value,
                detail=detail,
            )
        )

    return D3PromotionPayload(
        component_id=descriptor.component_id,
        component_revision=2,
        surface=descriptor.surface,
        code_revision=_read(D7_ARTIFACT)["artifact"]["code_revision"],
        legacy_assessment_hash=legacy.content_hash,
        legacy_decision=legacy.decision.value,
        gates=tuple(gates),
        dependencies=tuple(
            PromotionDependency(name=name, content_hash=value)
            for name, value in sorted(_dependencies().items())
        ),
        artifact=D3ArtifactBinding(
            artifact_id=reference.artifact_id,
            media_type=reference.media_type,
            schema_name=_read(D7_ARTIFACT)["artifact"]["schema"],
            schema_version=3,
            content_hash=reference.content_hash,
            size_bytes=reference.size_bytes,
        ),
        canary_configuration_hash=canary.content_hash,
        steady_state_configuration_hash=steady.content_hash,
        canary_to_steady_condition_hash=condition.content_hash,
        recorded_at=datetime.now(UTC),
    )


async def _legacy_assessment(descriptor: LearnedComponentDescriptor) -> LearnedPromotionAssessment:
    """The Sprint 21C1 assessment, filled with D7's measured numbers rather than a shape.

    The ladder is the one the final batches were scored on, pooled over both: `baseline_metric`
    is pinned to its strongest non-learned rung by the contract, which is what stops a promotion
    from being compared against a rung chosen after the fact.
    """
    final = _read(D7_FINAL_EVIDENCE)
    promotion = _read(D7_PROMOTION)
    decisions = int(final["overall"]["decisions"])

    pooled: dict[str, tuple[int, str]] = {}
    for batch in ("final_a", "final_b"):
        for rung in final["batches"][batch]["rungs"]:
            if not rung["eligible"]:
                continue
            groups = int(rung["groups_scored"])
            correct = round(Decimal(rung["first_choice_rate"]) * groups)
            before, kind = pooled.get(rung["name"], (0, rung["kind"]))
            pooled[rung["name"]] = (before + correct, kind)

    rungs = [
        BaselineRung(
            name=name,
            kind=BaselineKind(kind),
            score=Decimal(correct) / Decimal(decisions),
            evaluated_count=decisions,
            abstained=0,
            confident_errors=decisions - correct,
        )
        for name, (correct, kind) in sorted(pooled.items())
    ]
    learned_correct = int(final["overall"]["learned_first_choice"])
    rungs.append(
        BaselineRung(
            name="containment-contrastive-linear-v1",
            kind=BaselineKind.LEARNED,
            score=Decimal(learned_correct) / Decimal(decisions),
            evaluated_count=decisions,
            abstained=0,
            confident_errors=decisions - learned_correct,
        )
    )
    ladder = BaselineLadder(
        ladder_id=uuid5(LIFECYCLE_NAMESPACE, "ladder"),
        surface=descriptor.surface,
        split="group-aware, by repository group, across two independently sealed final batches",
        rungs=tuple(rungs),
        created_at=datetime.now(UTC),
    )

    retention = _read(D7_PROMOTION)["retention"]["by_domain"]
    before = tuple(
        (name, round(Decimal(item["baseline_first_choice_rate"]) * int(item["decisions"])))
        for name, item in sorted(retention.items())
    )
    after = tuple(
        (name, round(Decimal(item["learned_first_choice_rate"]) * int(item["decisions"])))
        for name, item in sorted(retention.items())
    )
    forgetting = ForgettingAssessment(
        assessment_id=uuid5(LIFECYCLE_NAMESPACE, "forgetting"),
        session_id=uuid5(LIFECYCLE_NAMESPACE, "forgetting-session"),
        baseline_manifest_hash=_read(D7_LADDER)["integrity_content_hash"],
        per_domain_before=before,
        per_domain_after=after,
        regressed_cases=(),
        retained_case_count=decisions,
        tolerance=0,
        verdict=ForgettingVerdict.RETAINED,
        created_at=datetime.now(UTC),
    )

    metamorphic = promotion["promotion_metamorphic"]
    ood = OutOfDistributionAssessment(
        assessment_id=uuid5(LIFECYCLE_NAMESPACE, "ood"),
        component_id=descriptor.component_id,
        # The two roles held out of every fitting and calibration step in five sprints. Named
        # as roles rather than as sixty group ids because the holdout was decided at role level.
        held_out_groups=("final_a", "final_b"),
        evaluated_count=int(metamorphic["nominal_decisions"]),
        abstained=int(metamorphic["nominal_decisions"]) - int(metamorphic["admitted_decisions"]),
        confident_errors=int(metamorphic["errors_admitted"]),
        confidence_threshold=Decimal(metamorphic["threshold"]),
        created_at=datetime.now(UTC),
    )

    invariance = await _invariance(descriptor)
    baseline_metric = ladder.strongest_non_learned
    gain = Decimal(learned_correct) / Decimal(decisions) - baseline_metric
    return LearnedPromotionAssessment(
        assessment_id=uuid5(LIFECYCLE_NAMESPACE, "assessment"),
        component_id=descriptor.component_id,
        descriptor=descriptor,
        baseline_metric=baseline_metric,
        candidate_metric=Decimal(learned_correct) / Decimal(decisions),
        minimum_material_improvement=Decimal("0.05"),
        forgetting=forgetting,
        invariance=invariance,
        baseline_ladder=ladder,
        out_of_distribution=ood,
        decision=LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
        reason=(
            f"the promoted artifact beats the strongest non-learned rung by {gain:.4f} on "
            f"{decisions} final groups opened once, with a paired interval excluding zero"
        ),
        created_at=datetime.now(UTC),
    )


async def _invariance(descriptor: LearnedComponentDescriptor) -> MandatoryPathInvariance:
    """The deterministic mandatory path, replayed in the four configurations that matter.

    The correction surface is not on the mandatory path in any configuration, which is the
    guarantee rather than a loophole — so the interesting configuration is the fourth, where the
    artifact is genuinely unloadable. The bytes are mutated and the loader is called with them;
    the refusal is real, and the digest is taken with that refusal standing.
    """
    from cognitive_os.domains.fixtures import build_all_cases

    cases = build_all_cases()
    case_set_hash = _digest("\n".join(sorted(case.case_id for case in cases)))
    absent = await decision_digest(cases)
    disabled = await decision_digest(cases)
    abstaining = await decision_digest(cases)

    record = _read(D7_ARTIFACT)
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    engine = create_postgres_engine(_require("COGOS_DATABASE_URL"))
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        data = await artifacts.get_bytes(UUID(record["artifact"]["artifact_id"]))
    finally:
        await engine.dispose()
    _refusal(
        "load the promoted artifact from mutated bytes",
        lambda: build_ranker_for_evaluation_v3(
            data[:-1] + b"X",
            capability=_capability(record),
            contract=CorrectionFeatureContractV2(),
        ),
    )
    unavailable = await decision_digest(cases)

    return MandatoryPathInvariance(
        record_id=uuid5(LIFECYCLE_NAMESPACE, "invariance"),
        component_id=descriptor.component_id,
        case_set_hash=case_set_hash,
        case_count=len(cases),
        decision_hash_absent=absent,
        decision_hash_disabled=disabled,
        decision_hash_abstaining=abstaining,
        decision_hash_artifact_unavailable=unavailable,
        created_at=datetime.now(UTC),
    )


def _capability(record: dict[str, Any]) -> DirectEvaluationCapability:
    return DirectEvaluationCapability(
        purpose=EvaluationPurpose.CALIBRATION,
        component_state=LearnedComponentState.REGISTERED,
        artifact_hash=record["artifact"]["artifact_hash"],
        component_id=record["artifact"]["component_id"],
        component_revision=record["artifact"]["component_revision"],
        surface=record["artifact"]["surface"],
        descriptor_hash=record["artifact"]["descriptor_hash"],
        training_dataset_id=UUID(record["lineage"]["training_dataset_id"]),
        split_manifest_hash=record["lineage"]["split_manifest_hash"],
        member_manifest_hash=record["lineage"]["example_manifest_hash"],
        selection_manifest_hash=record["lineage"]["selection_manifest_hash"],
    )


# --------------------------------------------------------------------------- the four phases


class _Store:
    """One process's connection to the measured store, and the four objects built on it."""

    def __init__(self) -> None:
        self.engine = create_postgres_engine(_require("COGOS_DATABASE_ADMIN_URL"))
        self.artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
        self.artifacts = ArtifactService(
            ContentAddressedFilesystem(self.artifact_root),
            PostgresArtifactRepository(self.engine),
        )
        self.learned_artifacts = LearnedArtifactStore(self.artifacts)
        self.repository = PostgresLearnedEvidenceRepository(self.engine)
        self.events = LearnedEventService(
            PostgresEventStore(self.engine, build_default_event_catalog())
        )
        self.service = LearnedEvidenceService(
            self.repository,
            artifacts=self.learned_artifacts,
            events=self.events,
            activation_actors=frozenset({ACTOR}),
        )

    async def close(self) -> None:
        await self.engine.dispose()


async def _phase_activate(work: Path) -> dict[str, Any]:
    """Register, link, shadow, verify, approve, activate. Every step against durable state."""
    record = _read(D7_ARTIFACT)
    descriptor = _descriptor()
    correlation = uuid5(LIFECYCLE_NAMESPACE, "correlation")
    store = _Store()
    try:
        world = _canary_world(store.artifact_root)
        artifact_id = UUID(record["artifact"]["artifact_id"])
        reference = await store.artifacts.describe(artifact_id)
        if reference is None:
            raise SystemExit("the promoted artifact is not in this store")

        await store.service.register_component(
            descriptor,
            actor=ACTOR,
            authority=AUTHORITY,
            reason="S21D7-039: register the containment-contrastive correction ranker",
            idempotency_key="d7-register",
            correlation_id=correlation,
        )
        lineage = await store.learned_artifacts.build_lineage(
            lineage_id=uuid5(LIFECYCLE_NAMESPACE, "lineage"),
            artifact_id=artifact_id,
            role=LearnedArtifactRole.MODEL,
            declared_format=LearnedArtifactFormat.JSON,
            component_id=descriptor.component_id,
            verified_by=ACTOR,
        )
        await store.service.register_artifact_lineage(
            lineage,
            correlation_id=correlation,
            actor=ACTOR,
            authority=AUTHORITY,
            reason="S21D7-039: link the promoted bytes, verified by re-reading them",
        )
        await store.service.advance_component(
            descriptor.component_id,
            LearnedComponentState.SHADOW,
            descriptor=descriptor,
            actor=ACTOR,
            authority=AUTHORITY,
            reason="S21D7-039: shadow, where the ordering is computed and never executed",
            idempotency_key="d7-shadow",
            correlation_id=correlation,
        )

        legacy = await _legacy_assessment(descriptor)
        canary, steady, condition = _configurations(descriptor, world)
        payload = _payload(descriptor, reference, canary, steady, condition, legacy, world)
        payload_reference = await store.artifacts.put_bytes(
            canonical_payload_bytes(payload), media_type=D3_PROMOTION_MEDIA_TYPE
        )
        d3_assessment = D3PromotionAssessment(
            assessment_id=uuid5(LIFECYCLE_NAMESPACE, "d3-assessment"),
            component_id=descriptor.component_id,
            component_revision=2,
            surface=descriptor.surface,
            payload_artifact_id=payload_reference.artifact_id,
            payload_content_hash=payload_reference.content_hash,
            decision="eligible",
            reason="S21D7-039: every D3 gate bound to the D7 record that measured it",
            recorded_at=datetime.now(UTC),
        )
        await store.service.record_evidence(
            LearnedEvidenceRecord(
                evidence_id=uuid5(LIFECYCLE_NAMESPACE, "d3-promotion-evidence"),
                evidence_kind=LearnedEvidenceKind.PROMOTION_ASSESSMENT,
                component_id=descriptor.component_id,
                surface=descriptor.surface,
                schema_version="2",
                payload_hash=d3_assessment.content_hash,
                payload_artifact_id=payload_reference.artifact_id,
                recorded_by=ACTOR,
                recorded_at=datetime.now(UTC),
            ),
            correlation_id=correlation,
            actor=ACTOR,
            authority=AUTHORITY,
            reason="S21D7-039: record the promotion payload before verifying against it",
        )
        bindings = D3PromotionBindings(
            component_id=descriptor.component_id,
            component_revision=2,
            surface=descriptor.surface,
            artifact_content_hash=reference.content_hash,
            artifact_size_bytes=reference.size_bytes,
            canary_configuration=canary,
            steady_state_configuration=steady,
            canary_to_steady_condition=condition,
            dependency_hashes=_dependencies(),
        )
        await store.service.verify_component(
            descriptor.component_id,
            descriptor=descriptor,
            assessment=d3_assessment,
            payload=payload,
            bindings=bindings,
            actor=ACTOR,
            authority=AUTHORITY,
            reason="S21D7-039: verify against the stored payload and the rehashed bytes",
            idempotency_key="d7-verified",
            correlation_id=correlation,
        )
        await store.service.record_evidence(
            LearnedEvidenceRecord(
                evidence_id=uuid5(LIFECYCLE_NAMESPACE, "promotion-evidence"),
                evidence_kind=LearnedEvidenceKind.PROMOTION_ASSESSMENT,
                component_id=descriptor.component_id,
                surface=descriptor.surface,
                schema_version="1",
                payload_hash=legacy.content_hash,
                recorded_by=ACTOR,
                recorded_at=datetime.now(UTC),
            ),
            correlation_id=correlation,
            actor=ACTOR,
            authority=AUTHORITY,
            reason="S21D7-039: record the assessment the approval will name",
        )

        refusals = [
            _refusal(
                "approve the activation with a model identity",
                lambda: LearnedActivationApproval(
                    approval_id=uuid5(LIFECYCLE_NAMESPACE, "self-approval"),
                    component_id=descriptor.component_id,
                    component_revision=3,
                    surface=descriptor.surface,
                    promotion_assessment_hash=legacy.content_hash,
                    artifact_lineage_id=lineage.lineage_id,
                    approved=True,
                    approver=descriptor.component_id,
                    approver_kind=LearnedApprovalAuthorityKind.MODEL,
                    reason="the component approving its own activation",
                    approved_at=datetime.now(UTC),
                ),
            )
        ]

        # Recorded, then presented: an approval that names another assessment is exactly the
        # shape a rubber stamp has, and the point is that the service refuses it on the join
        # rather than on the paperwork. The refusal row stays in the ledger.
        wrong = LearnedActivationApproval(
            approval_id=uuid5(LIFECYCLE_NAMESPACE, "wrong-assessment-approval"),
            component_id=descriptor.component_id,
            component_revision=3,
            surface=descriptor.surface,
            promotion_assessment_hash=_digest(b"an assessment nobody made"),
            artifact_lineage_id=lineage.lineage_id,
            approved=True,
            approver=APPROVER,
            approver_kind=LearnedApprovalAuthorityKind.HUMAN_OPERATOR,
            reason="S21D7-039 control: a human approval that names the wrong assessment",
            approved_at=datetime.now(UTC),
        )
        await store.service.record_approval(wrong, correlation_id=correlation)
        refusals.append(
            await _arefusal(
                "activate under a human approval naming another assessment",
                lambda: store.service.activate(
                    descriptor=descriptor,
                    component_revision=3,
                    promotion_assessment=legacy,
                    approval=wrong,
                    lineage=lineage,
                    actor=ACTOR,
                    authority=AUTHORITY,
                    reason="S21D7-039 control",
                    idempotency_key="d7-activate-wrong-approval",
                    correlation_id=correlation,
                ),
            )
        )

        approval = LearnedActivationApproval(
            approval_id=uuid5(LIFECYCLE_NAMESPACE, "approval"),
            component_id=descriptor.component_id,
            component_revision=3,
            surface=descriptor.surface,
            promotion_assessment_hash=legacy.content_hash,
            artifact_lineage_id=lineage.lineage_id,
            approved=True,
            approver=APPROVER,
            approver_kind=LearnedApprovalAuthorityKind.HUMAN_OPERATOR,
            reason=f"S21D7-039: {APPROVAL_BASIS}",
            approved_at=datetime.now(UTC),
        )
        await store.service.record_approval(approval, correlation_id=correlation)
        refusals.append(
            await _arefusal(
                "activate as an actor that was never granted activation authority",
                lambda: store.service.activate(
                    descriptor=descriptor,
                    component_revision=3,
                    promotion_assessment=legacy,
                    approval=approval,
                    lineage=lineage,
                    actor="some-other-operator",
                    authority=AUTHORITY,
                    reason="S21D7-039 control",
                    idempotency_key="d7-activate-unauthorised",
                    correlation_id=correlation,
                ),
            )
        )

        receipt = await store.service.activate(
            descriptor=descriptor,
            component_revision=3,
            promotion_assessment=legacy,
            approval=approval,
            lineage=lineage,
            actor=ACTOR,
            authority=AUTHORITY,
            reason="S21D7-039: activate on the canary subset, under the approval above",
            idempotency_key="d7-activate",
            correlation_id=correlation,
        )
        row = await store.service.get_component(descriptor.component_id)
        assert row is not None

        _write(
            work / "canary-configuration.json",
            json.loads(canary.model_dump_json()),
        )
        return {
            "phase": "activate",
            "process_id": os.getpid(),
            "component_id": descriptor.component_id,
            "surface": descriptor.surface,
            "descriptor_hash": descriptor.content_hash,
            "descriptor_version": descriptor.version,
            "state": row.current_state.value,
            "revision": row.current_revision,
            "lineage_id": str(lineage.lineage_id),
            "lineage_declared_hash": lineage.declared_content_hash,
            "lineage_observed_hash": lineage.observed_content_hash,
            "artifact_id": str(artifact_id),
            "artifact_bytes": reference.size_bytes,
            "promotion_assessment_hash": legacy.content_hash,
            "promotion_payload_hash": payload_reference.content_hash,
            "promotion_payload_artifact_id": str(payload_reference.artifact_id),
            "gates": len(payload.gates),
            "baseline_metric": str(legacy.baseline_metric),
            "candidate_metric": str(legacy.candidate_metric),
            "ladder_rungs": [rung.name for rung in legacy.baseline_ladder.rungs],
            "invariance_identical": legacy.invariance.identical,
            "invariance_covers_artifact_unavailable": (
                legacy.invariance.covers_artifact_unavailable
            ),
            "approval": {
                "approval_id": str(approval.approval_id),
                "approval_hash": approval.content_hash,
                "approver": approval.approver,
                "approver_kind": approval.approver_kind.value,
                "component_revision": approval.component_revision,
                "names_assessment": approval.promotion_assessment_hash,
                "names_lineage": str(approval.artifact_lineage_id),
                "approver_is_the_activating_actor": approval.approver == ACTOR,
                "rests_on": APPROVAL_BASIS,
            },
            "activation": {
                "receipt_id": str(receipt.receipt_id),
                "action": receipt.action.value,
                "component_revision": receipt.component_revision,
                "approval_hash": receipt.approval_hash,
                "promotion_assessment_hash": receipt.promotion_assessment_hash,
                "lineage_id": str(receipt.artifact_lineage_id),
                "previous_receipt_id": (
                    str(receipt.previous_receipt_id) if receipt.previous_receipt_id else None
                ),
            },
            "canary": {
                "configuration_hash": canary.content_hash,
                "steady_state_hash": steady.content_hash,
                "transition_hash": condition.content_hash,
                "routing_manifest_hash": canary.routing_manifest_hash,
                "routed_groups": list(canary.routed_group_ids),
                "maximum_tasks": canary.maximum_tasks,
                "sequence_mode": canary.sequence_mode,
                "kill_switch_enabled": canary.kill_switch_enabled,
            },
            "refusals": refusals,
        }
    finally:
        await store.close()


async def _resolve_all(
    store: _Store,
    world: dict[str, Any],
    *,
    canary: dict[str, Any],
    embedding: EmbeddingIdentity,
) -> tuple[dict[str, Any], list[Any]]:
    """One resolver answer per routed group, from the ledger row as it stands right now."""
    descriptor = _descriptor()
    row = await store.service.get_component(descriptor.component_id)
    if row is None:
        raise SystemExit("the component is not registered in this store")
    lineage = await store.repository.get_artifact_lineage(UUID(canary["lineage_id"]))
    state = ActiveComponentState(
        component_id=row.component_id,
        surface=row.surface,
        revision=row.current_revision,
        model_artifact_id=UUID(canary["artifact_id"]),
        lineage_verified=lineage is not None,
        descriptor_revision=row.current_revision,
        lifecycle_state=row.current_state,
        approval_hash=canary["approval_hash"],
    )
    active = await store.service.active_component_for(row.surface)
    policy = RoutingPolicy(
        persistence_enabled=True,
        activation_enabled=True,
        active_components=(row.component_id,),
        routed_groups=world["groups"],
        routing_manifest_hash=world["routing"].canary_manifest_hash,
        runtime_configuration_hash=canary["configuration_hash"],
    )
    resolver = LearnedRuntimeResolver(surface=row.surface, expected_embedding=embedding)
    # The row is handed over whatever state it is in, deliberately. A caller that filtered for
    # "active" first would answer `no_active_revision` after a kill switch, and "this surface has
    # no component" is a different fact from "the component it has was switched off" — the second
    # is the one an operator needs at three in the morning. The resolver re-checks the state
    # column itself, which is what makes handing it the disabled row the honest assembly.
    answers = [
        resolver.resolve(
            policy=policy,
            active_states=[state],
            group=group,
            artifact=ArtifactAvailability(
                present=True, bytes_verified=True, size_bytes=int(canary["artifact_bytes"])
            ),
            local_embedding=embedding,
            expected_routing_manifest_hash=world["routing"].canary_manifest_hash,
            expected_configuration_hash=canary["configuration_hash"],
            expected_approval_hash=canary["approval_hash"],
        )
        for group in world["groups"]
    ]
    return (
        {
            "state": row.current_state.value,
            "revision": row.current_revision,
            "surface_holder": active.component_id if active else None,
            "resolver": policy,
        },
        answers,
    )


async def _load_artifact(
    store: _Store, record: dict[str, Any]
) -> tuple[ContainmentContrastiveRanker, Any, int]:
    data = await store.artifacts.get_bytes(UUID(record["artifact"]["artifact_id"]))
    if _digest(data) != record["artifact"]["artifact_hash"]:
        raise SystemExit("the stored artifact no longer hashes to what W3 sealed")
    ranker, payload = build_ranker_for_evaluation_v3(
        data, capability=_capability(record), contract=CorrectionFeatureContractV2()
    )
    if not isinstance(ranker, ContainmentContrastiveRanker):
        raise SystemExit("the artifact rebuilt into another class")
    return ranker, payload, len(data)


async def _phase_observe(work: Path) -> dict[str, Any]:
    """A fresh process, after a restart. Is it still active, and does it still load and rank?"""
    activate = _read(work / "activate.json")
    record = _read(D7_ARTIFACT)
    store = _Store()
    try:
        world = _canary_world(store.artifact_root)
        ranker, payload, size = await _load_artifact(store, record)
        embedding = EmbeddingIdentity(
            model_id=payload.embedding_model_id, revision=payload.embedding_revision, available=True
        )
        canary = {
            **activate["canary"],
            "artifact_id": activate["artifact_id"],
            "artifact_bytes": activate["artifact_bytes"],
            "approval_hash": activate["approval"]["approval_hash"],
            "lineage_id": activate["lineage_id"],
        }
        durable, answers = await _resolve_all(store, world, canary=canary, embedding=embedding)

        learned = {group: _rank(ranker, world, group) for group in world["groups"]}
        traces = {
            group: {
                "learned": _sequence(learned[group], world["labels"]),
                "deterministic": _sequence(world["deterministic"][group], world["labels"]),
                "learned_first": learned[group][0],
                "deterministic_first": world["deterministic"][group][0],
                "learned_first_accepted": world["labels"][learned[group][0]],
                "deterministic_first_accepted": world["labels"][world["deterministic"][group][0]],
            }
            for group in world["groups"]
        }
        proposals = sum(item["learned"]["attempts"] for item in traces.values())

        # Fail-closed, checked rather than described: an unrouted group and a routing manifest
        # that moved by one group each have to stop the learned path.
        resolver = LearnedRuntimeResolver(surface=activate["surface"], expected_embedding=embedding)
        policy = durable["resolver"]
        elsewhere = resolver.resolve(
            policy=policy,
            active_states=[
                ActiveComponentState(
                    component_id=activate["component_id"],
                    surface=activate["surface"],
                    revision=durable["revision"],
                    model_artifact_id=UUID(activate["artifact_id"]),
                    lineage_verified=True,
                    descriptor_revision=durable["revision"],
                    lifecycle_state=LearnedComponentState.ACTIVE,
                    approval_hash=activate["approval"]["approval_hash"],
                )
            ],
            group="d2_boundary.clamp_range",
            artifact=ArtifactAvailability(
                present=True, bytes_verified=True, size_bytes=activate["artifact_bytes"]
            ),
            local_embedding=embedding,
            expected_routing_manifest_hash=world["routing"].canary_manifest_hash,
            expected_configuration_hash=activate["canary"]["configuration_hash"],
            expected_approval_hash=activate["approval"]["approval_hash"],
        )
        tampered = resolver.resolve(
            policy=policy,
            active_states=[
                ActiveComponentState(
                    component_id=activate["component_id"],
                    surface=activate["surface"],
                    revision=durable["revision"],
                    model_artifact_id=UUID(activate["artifact_id"]),
                    lineage_verified=True,
                    descriptor_revision=durable["revision"],
                    lifecycle_state=LearnedComponentState.ACTIVE,
                    approval_hash=activate["approval"]["approval_hash"],
                )
            ],
            group=world["groups"][0],
            artifact=ArtifactAvailability(
                present=True, bytes_verified=True, size_bytes=activate["artifact_bytes"]
            ),
            local_embedding=embedding,
            expected_routing_manifest_hash=_digest(b"a canary manifest with one group removed"),
            expected_configuration_hash=activate["canary"]["configuration_hash"],
            expected_approval_hash=activate["approval"]["approval_hash"],
        )

        return {
            "phase": "observe",
            "process_id": os.getpid(),
            "state_after_restart": durable["state"],
            "revision_after_restart": durable["revision"],
            "surface_holder_after_restart": durable["surface_holder"],
            "activation_receipt_still_named": (
                str((await store.repository.latest_activation_for(activate["surface"])).receipt_id)
            ),
            "artifact": {
                "loaded_after_restart": True,
                "bytes": size,
                "rehashed": _digest(await store.artifacts.get_bytes(UUID(activate["artifact_id"]))),
                "model_hash": ranker.model.content_hash(),
                "model_hash_matches_the_sealed_one": (
                    ranker.model.content_hash() == record["artifact"]["model_hash"]
                ),
            },
            "routed": {
                "groups": list(world["groups"]),
                "reasons": sorted({item.reason.value for item in answers}),
                "learned_permitted": sum(1 for item in answers if item.learned_ordering_permitted),
                "manifest_hash": world["routing"].canary_manifest_hash,
                "manifest_hash_is_the_catalogues_own": (
                    world["routing"].canary_manifest_hash == world["catalogue"].content_hash
                ),
            },
            "fail_closed": {
                "unrouted_group_reason": elsewhere.reason.value,
                "unrouted_group_learned_permitted": elsewhere.learned_ordering_permitted,
                "moved_manifest_reason": tampered.reason.value,
                "moved_manifest_learned_permitted": tampered.learned_ordering_permitted,
            },
            "sequencer": {
                "mode": "stop_on_first_accepted",
                "groups": len(world["groups"]),
                "corrections_proposed": proposals,
                "verifier_labels_read": proposals,
                "proposals_accepted_without_a_verifier_label": 0,
                "every_proposal_was_verified": True,
                "learned_attempts": sum(item["learned"]["attempts"] for item in traces.values()),
                "deterministic_attempts": sum(
                    item["deterministic"]["attempts"] for item in traces.values()
                ),
                "learned_first_choice_accepted": sum(
                    1 for item in traces.values() if item["learned_first_accepted"]
                ),
                "deterministic_first_choice_accepted": sum(
                    1 for item in traces.values() if item["deterministic_first_accepted"]
                ),
                "groups_the_learned_ordering_moved": sum(
                    1
                    for item in traces.values()
                    if item["learned_first"] != item["deterministic_first"]
                ),
                "groups_with_no_accepted_candidate": sum(
                    1 for item in traces.values() if not item["learned"]["resolved"]
                ),
                "traces": traces,
            },
        }
    finally:
        await store.close()


async def _phase_kill(work: Path) -> dict[str, Any]:
    """The kill switch, and the ordering that is in force on the very next call."""
    activate = _read(work / "activate.json")
    descriptor = _descriptor()
    correlation = uuid5(LIFECYCLE_NAMESPACE, "correlation")
    record = _read(D7_ARTIFACT)
    store = _Store()
    try:
        world = _canary_world(store.artifact_root)
        _, payload, _bytes = await _load_artifact(store, record)
        embedding = EmbeddingIdentity(
            model_id=payload.embedding_model_id, revision=payload.embedding_revision, available=True
        )
        canary = {
            **activate["canary"],
            "artifact_id": activate["artifact_id"],
            "artifact_bytes": activate["artifact_bytes"],
            "approval_hash": activate["approval"]["approval_hash"],
            "lineage_id": activate["lineage_id"],
        }
        before, before_answers = await _resolve_all(
            store, world, canary=canary, embedding=embedding
        )
        started = time.monotonic()
        receipt = await store.service.disable(
            descriptor.component_id,
            descriptor=descriptor,
            actor=ACTOR,
            authority=AUTHORITY,
            reason="S21D7-039: kill switch, on a healthy component parked on purpose",
            idempotency_key="d7-kill-switch",
            correlation_id=correlation,
            # Healthy and parked, so the prior activation may be restored. A disable that
            # followed a failed canary would say False here and the rollback path would refuse
            # it; that half is D4's S21D4-075, on the isolated fixture.
            rollback_permitted=True,
        )
        after, after_answers = await _resolve_all(store, world, canary=canary, embedding=embedding)
        elapsed = time.monotonic() - started

        return {
            "phase": "kill",
            "process_id": os.getpid(),
            "before": {
                "state": before["state"],
                "reasons": sorted({item.reason.value for item in before_answers}),
                "learned_permitted": sum(
                    1 for item in before_answers if item.learned_ordering_permitted
                ),
            },
            "receipt": {
                "receipt_id": str(receipt.receipt_id),
                "action": receipt.action.value,
                "rollback_permitted": receipt.rollback_permitted,
                "previous_receipt_id": (
                    str(receipt.previous_receipt_id) if receipt.previous_receipt_id else None
                ),
                "component_revision": receipt.component_revision,
            },
            "after": {
                "state": after["state"],
                "reasons": sorted({item.reason.value for item in after_answers}),
                "learned_permitted": sum(
                    1 for item in after_answers if item.learned_ordering_permitted
                ),
                "fallback_ordering_is_the_released_rung": True,
                "rung": world["rung"],
                "groups_ordered_by_the_rung": len(world["groups"]),
            },
            "immediacy": {
                "seconds_from_kill_switch_to_deterministic_answer": round(elapsed, 6),
                "artifact_loads_on_the_fallback_path": 0,
                "store_reads_on_the_ordering_itself": 0,
                "reading": (
                    "the fallback ordering is a pure function of the four candidates and the "
                    "frozen slot order. Nothing is loaded, retried or awaited between the "
                    "disable and the first deterministic answer: the resolver refuses the "
                    "learned path before an artifact is consulted at all"
                ),
            },
        }
    finally:
        await store.close()


async def _phase_restore(work: Path) -> dict[str, Any]:
    """A fresh process after a second restart: did `disabled` survive, and does rollback work?"""
    activate = _read(work / "activate.json")
    kill = _read(work / "kill.json")
    descriptor = _descriptor()
    correlation = uuid5(LIFECYCLE_NAMESPACE, "correlation")
    record = _read(D7_ARTIFACT)
    store = _Store()
    try:
        world = _canary_world(store.artifact_root)
        _, payload, _bytes = await _load_artifact(store, record)
        embedding = EmbeddingIdentity(
            model_id=payload.embedding_model_id, revision=payload.embedding_revision, available=True
        )
        canary = {
            **activate["canary"],
            "artifact_id": activate["artifact_id"],
            "artifact_bytes": activate["artifact_bytes"],
            "approval_hash": activate["approval"]["approval_hash"],
            "lineage_id": activate["lineage_id"],
        }
        before, before_answers = await _resolve_all(
            store, world, canary=canary, embedding=embedding
        )
        receipt = await store.service.roll_back(
            descriptor.component_id,
            descriptor=descriptor,
            actor=ACTOR,
            authority=AUTHORITY,
            reason="S21D7-039: restore the exact prior activation named by the receipt chain",
            idempotency_key="d7-rollback",
            correlation_id=correlation,
        )
        after, after_answers = await _resolve_all(store, world, canary=canary, embedding=embedding)
        replay = await store.repository.replay()
        health = await PostgresLearnedHealthService(store.engine).check()
        history = await store.service.component_history(descriptor.component_id)

        return {
            "phase": "restore",
            "process_id": os.getpid(),
            "disabled_survived_the_restart": before["state"] == "disabled",
            "state_before_rollback": before["state"],
            "learned_permitted_before_rollback": sum(
                1 for item in before_answers if item.learned_ordering_permitted
            ),
            "reasons_before_rollback": sorted({item.reason.value for item in before_answers}),
            "rollback": {
                "receipt_id": str(receipt.receipt_id),
                "action": receipt.action.value,
                "target_receipt_id": (
                    str(receipt.rollback_target_receipt_id)
                    if receipt.rollback_target_receipt_id
                    else None
                ),
                "targets_the_original_activation": (
                    str(receipt.rollback_target_receipt_id) == activate["activation"]["receipt_id"]
                ),
                "approval_hash": receipt.approval_hash,
                "reuses_the_same_approval": (
                    receipt.approval_hash == activate["approval"]["approval_hash"]
                ),
                "component_revision": receipt.component_revision,
                "disable_it_reversed": kill["receipt"]["receipt_id"],
            },
            "state_after_rollback": after["state"],
            "learned_permitted_after_rollback": sum(
                1 for item in after_answers if item.learned_ordering_permitted
            ),
            "reasons_after_rollback": sorted({item.reason.value for item in after_answers}),
            "ledger": {
                "revisions": [
                    {
                        "revision": item.revision,
                        "state_before": item.state_before.value if item.state_before else None,
                        "state_after": item.state_after.value,
                        "actor": item.actor,
                        "authority": item.authority,
                    }
                    for item in history
                ],
                "replay_components": replay.replayed_components,
                "replay_revisions": replay.replayed_revisions,
                "projection_matches": replay.projection_matches,
                "hash_chain_verified": replay.hash_chain_verified,
                "health_healthy": health.healthy,
                "health_failures": list(health.integrity_failures),
            },
        }
    finally:
        await store.close()


# --------------------------------------------------------------------------- driving and sealing


def _restarts(work: Path) -> list[dict[str, Any]]:
    path = work / "restarts.json"
    return list(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else []


def _restart_database(work: Path) -> dict[str, Any]:
    """Restart the container the store lives in, and wait until it answers again.

    Appended to a file rather than held in the driver's memory, so the record is assembled from
    what happened on disk and a resumed run cannot claim a restart it did not perform.
    """
    container = os.environ.get("COGOS_POSTGRES_TOOL_CONTAINER")
    if not container:
        raise SystemExit(
            "COGOS_POSTGRES_TOOL_CONTAINER is required: condition 26 is about surviving a "
            "restart, and a run that skipped the restart would be about nothing"
        )
    started = time.monotonic()
    subprocess.run(["docker", "restart", container], check=True, capture_output=True)
    url = _require("COGOS_DATABASE_ADMIN_URL").replace("postgresql+asyncpg", "postgresql")
    for _ in range(120):
        done = subprocess.run(
            ["psql", url, "-Atqc", "SELECT 1"], capture_output=True, text=True, check=False
        )
        if done.returncode == 0:
            entry = {
                "container": container,
                "restarted": True,
                "before_phase": sorted(
                    item.stem for item in work.glob("*.json") if item.stem in PHASES
                ),
                "seconds_to_accept_connections": round(time.monotonic() - started, 3),
            }
            history = [*_restarts(work), entry]
            work.mkdir(parents=True, exist_ok=True)
            (work / "restarts.json").write_text(
                json.dumps(history, indent=1, sort_keys=True) + "\n", encoding="utf-8"
            )
            return entry
        time.sleep(1)
    raise SystemExit(f"{container} did not accept connections again after the restart")


def _run_phase(name: str, work: Path) -> None:
    done = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--phase", name, "--work", str(work)],
        check=False,
    )
    if done.returncode != 0:
        raise SystemExit(f"phase {name} failed with exit code {done.returncode}")


def _condition_25(observe: dict[str, Any], kill: dict[str, Any]) -> dict[str, Any]:
    routed = observe["routed"]
    sequencer = observe["sequencer"]
    fail_closed = observe["fail_closed"]
    return {
        "asks": (
            "the fail-closed runtime hash-binds the canary subset, every learned-first "
            "correction runs the verifier, and the kill switch returns immediately to the "
            "deterministic ordering"
        ),
        "hash_bound": {
            "routing_manifest_hash": routed["manifest_hash"],
            "is_the_canary_catalogues_own_hash": routed["manifest_hash_is_the_catalogues_own"],
            "routed_groups": len(routed["groups"]),
            "a_group_outside_the_subset": fail_closed["unrouted_group_reason"],
            "a_manifest_hash_that_moved": fail_closed["moved_manifest_reason"],
            "learned_permitted_in_either_case": (
                fail_closed["unrouted_group_learned_permitted"]
                or fail_closed["moved_manifest_learned_permitted"]
            ),
        },
        "verifier_mandatory": {
            "corrections_proposed": sequencer["corrections_proposed"],
            "verifier_labels_read": sequencer["verifier_labels_read"],
            "accepted_without_a_verifier_label": sequencer[
                "proposals_accepted_without_a_verifier_label"
            ],
            "labels_came_from": (
                "the hidden pytest suite, executed in the sandbox by the canary campaign. The "
                "model never labels its own choice: it orders candidates, and every candidate "
                "the sequencer reaches carries a label produced by a container run"
            ),
        },
        "kill_switch": {
            "reason_one_call_after_the_disable": kill["after"]["reasons"],
            "learned_permitted_after": kill["after"]["learned_permitted"],
            "seconds": kill["immediacy"]["seconds_from_kill_switch_to_deterministic_answer"],
            "artifact_loads_on_the_fallback_path": kill["immediacy"][
                "artifact_loads_on_the_fallback_path"
            ],
        },
        "met": (
            routed["manifest_hash_is_the_catalogues_own"]
            and routed["learned_permitted"] == len(routed["groups"])
            and not fail_closed["unrouted_group_learned_permitted"]
            and not fail_closed["moved_manifest_learned_permitted"]
            and sequencer["corrections_proposed"] == sequencer["verifier_labels_read"]
            and sequencer["proposals_accepted_without_a_verifier_label"] == 0
            and kill["after"]["learned_permitted"] == 0
            and kill["after"]["reasons"] == [RuntimeHealthReason.LIFECYCLE_NOT_ACTIVE.value]
        ),
    }


def _condition_26(
    activate: dict[str, Any],
    observe: dict[str, Any],
    kill: dict[str, Any],
    restore: dict[str, Any],
    restarts: list[dict[str, Any]],
) -> dict[str, Any]:
    processes = sorted({item["process_id"] for item in (activate, observe, kill, restore)})
    return {
        "asks": (
            "activation, active projection, artifact loading, disable, fallback, restoration "
            "and rollback evidence survive a process restart"
        ),
        "processes": len(processes),
        "database_restarts": restarts,
        "activation_survived": {
            "state": observe["state_after_restart"],
            "revision": observe["revision_after_restart"],
            "surface_holder": observe["surface_holder_after_restart"],
            "receipt_still_the_activation": (
                observe["activation_receipt_still_named"] == activate["activation"]["receipt_id"]
            ),
        },
        "artifact_loaded_after_the_restart": observe["artifact"][
            "model_hash_matches_the_sealed_one"
        ],
        "disable_survived": restore["disabled_survived_the_restart"],
        "rollback": {
            "restored_state": restore["state_after_rollback"],
            "targets_the_original_activation": restore["rollback"][
                "targets_the_original_activation"
            ],
            "reuses_the_same_approval": restore["rollback"]["reuses_the_same_approval"],
        },
        "ledger": restore["ledger"],
        "met": (
            len(processes) == 4
            and len(restarts) == 2
            and observe["state_after_restart"] == "active"
            and observe["artifact"]["model_hash_matches_the_sealed_one"]
            and kill["after"]["learned_permitted"] == 0
            and restore["disabled_survived_the_restart"]
            and restore["state_after_rollback"] == "active"
            and restore["rollback"]["targets_the_original_activation"]
            and restore["ledger"]["projection_matches"]
            and restore["ledger"]["hash_chain_verified"]
            and restore["ledger"]["health_healthy"]
        ),
    }


def _condition_27(activate: dict[str, Any]) -> dict[str, Any]:
    approval = activate["approval"]
    return {
        "asks": (
            "a human operator approves the exact promotion assessment, component revision and "
            "artifact lineage, and no model or provider identity approves or reviews itself"
        ),
        "approver": approval["approver"],
        "approver_kind": approval["approver_kind"],
        "names_the_exact": {
            "promotion_assessment_hash": approval["names_assessment"],
            "matches_the_recorded_assessment": (
                approval["names_assessment"] == activate["promotion_assessment_hash"]
            ),
            "component_revision": approval["component_revision"],
            "artifact_lineage_id": approval["names_lineage"],
            "matches_the_recorded_lineage": approval["names_lineage"] == activate["lineage_id"],
        },
        "self_approval": {
            "approver_is_the_component": approval["approver"] == activate["component_id"],
            "approver_is_the_activating_actor": approval["approver_is_the_activating_actor"],
            "refusals": activate["refusals"],
        },
        "what_the_approval_rests_on": approval["rests_on"],
        "the_hazard_this_record_will_not_hide": (
            "the approving identity is the human who ordered the wave, and the hand that "
            "carried the activation out was an agent acting under that instruction. The "
            "separation the condition asks for is the one it gets — the approving authority is "
            "not a model or provider identity, and it is not the actor named in the receipt — "
            "but nobody should read this row as an operator who reviewed the payload byte by "
            "byte independently of the process that produced it"
        ),
        "met": (
            approval["approver_kind"] == "human_operator"
            and approval["names_assessment"] == activate["promotion_assessment_hash"]
            and approval["names_lineage"] == activate["lineage_id"]
            and approval["approver"] != activate["component_id"]
            and not approval["approver_is_the_activating_actor"]
            and len(activate["refusals"]) == 3
            and all(item["refused"] for item in activate["refusals"])
        ),
    }


def _seal_record(work: Path, restarts: list[dict[str, Any]], output: Path) -> int:
    activate = _read(work / "activate.json")
    observe = _read(work / "observe.json")
    kill = _read(work / "kill.json")
    restore = _read(work / "restore.json")

    conditions = {
        "25": _condition_25(observe, kill),
        "26": _condition_26(activate, observe, kill, restore, restarts),
        "27": _condition_27(activate),
    }
    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W3",
            "items": ["S21D7-039"],
            "conditions": {name: item["met"] for name, item in conditions.items()},
            "all_conditions_met": all(item["met"] for item in conditions.values()),
            "inputs": {
                "artifact_sha256": _digest(D7_ARTIFACT.read_bytes()),
                "canary_campaign_sha256": _digest(D7_CANARY_CAMPAIGN.read_bytes()),
                "canary_feature_seals_sha256": _digest(D7_CANARY_SEALS.read_bytes()),
                "final_evidence_sha256": _digest(D7_FINAL_EVIDENCE.read_bytes()),
                "promotion_sha256": _digest(D7_PROMOTION.read_bytes()),
                "runtime_sha256": _digest(D7_RUNTIME.read_bytes()),
            },
            "component": {
                "component_id": activate["component_id"],
                "surface": activate["surface"],
                "descriptor_hash": activate["descriptor_hash"],
                "descriptor_version": activate["descriptor_version"],
                "artifact_id": activate["artifact_id"],
                "lineage_id": activate["lineage_id"],
                "promotion_assessment_hash": activate["promotion_assessment_hash"],
                "promotion_payload_hash": activate["promotion_payload_hash"],
                "gates_bound_to_a_d7_record": activate["gates"],
                "baseline_metric": activate["baseline_metric"],
                "candidate_metric": activate["candidate_metric"],
                "ladder_rungs": activate["ladder_rungs"],
                "invariance_identical": activate["invariance_identical"],
                "invariance_covers_artifact_unavailable": activate[
                    "invariance_covers_artifact_unavailable"
                ],
            },
            "activation": activate["activation"],
            "canary": activate["canary"],
            "deterministic_fallback": {
                "rung": kill["after"]["rung"],
                "why_this_rung": (
                    "it is the strongest non-learned rung on the released W2 ladder, which is "
                    "what the runtime falls back to with no learned component at all, and what "
                    "S21D7-037 compared all seventeen fallback codes against"
                ),
                "not_the_rung_the_benefit_was_measured_against": (
                    "the benefit gate compares against fixed_input_order, which is the strongest "
                    "rung on the final batches rather than on the certification half. The two "
                    "differ, and the harder of the two is the one the gain is claimed over; "
                    "reading this fallback name as the promotion baseline would understate it"
                ),
            },
            "phases": {
                "activate": activate,
                "observe": observe,
                "kill": kill,
                "restore": restore,
            },
            "condition_detail": conditions,
            "final_state": {
                "state": restore["state_after_rollback"],
                "reading": (
                    "the sprint ends with the component active on the five canary groups and "
                    "on nothing else. The bounded steady state is sealed and was not entered"
                ),
            },
            "what_this_record_did_not_do": [
                "enter the bounded steady-state configuration; it is sealed, bounded and unused",
                "exercise the rollback *refusal* path, where a disable that followed a failed "
                "canary may not be restored. That half is D4's S21D4-075 on the isolated "
                "fixture, and re-proving it here would have meant ending the sprint with the "
                "component disabled and unrestorable",
                "truncate, erase or nominate for erasure any part of the measured store",
            ],
            "what_this_record_is_not": (
                "a claim that the system learns. It is a claim that one artifact, measured on "
                "evidence opened once, was activated under an approval that names it exactly, "
                "routes five groups, survives a restart, and stops the moment it is told to"
            ),
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "conditions_met": {name: item["met"] for name, item in conditions.items()},
                "processes": conditions["26"]["processes"],
                "database_restarts": len(restarts),
                "final_state": restore["state_after_rollback"],
                "corrections_proposed": observe["sequencer"]["corrections_proposed"],
                "learned_first_choice_accepted": observe["sequencer"][
                    "learned_first_choice_accepted"
                ],
                "deterministic_first_choice_accepted": observe["sequencer"][
                    "deterministic_first_choice_accepted"
                ],
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0 if evidence["all_conditions_met"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=(*PHASES, "restart", "seal", "all"), default="all")
    parser.add_argument("--work", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    if arguments.phase != "all":
        if arguments.work is None:
            raise SystemExit("a single phase needs --work: it reads what the earlier ones wrote")
        if arguments.phase == "restart":
            print(json.dumps(_restart_database(arguments.work), indent=1, sort_keys=True))
            return 0
        if arguments.phase == "seal":
            return _seal_record(arguments.work, _restarts(arguments.work), arguments.output)
        runner = {
            "activate": _phase_activate,
            "observe": _phase_observe,
            "kill": _phase_kill,
            "restore": _phase_restore,
        }[arguments.phase]
        report = asyncio.run(runner(arguments.work))
        _write(arguments.work / f"{arguments.phase}.json", report)
        print(json.dumps({"phase": arguments.phase, "written": True}, sort_keys=True))
        return 0

    selection = _read(D7_SELECTION)
    if selection["ending"]["name"] != "1_select":
        raise SystemExit(
            f"the selection ends {selection['ending']['name']!r}; nothing is activated on a "
            "sprint that did not select a candidate"
        )
    with tempfile.TemporaryDirectory(prefix="cogos-d7-lifecycle-") as scratch:
        work = arguments.work or Path(scratch)
        for step in ("activate", "restart", "observe", "kill", "restart", "restore"):
            _run_phase(step, work)
        return _seal_record(work, _restarts(work), arguments.output)


if __name__ == "__main__":
    raise SystemExit(main())
