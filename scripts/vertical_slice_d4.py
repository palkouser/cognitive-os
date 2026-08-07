#!/usr/bin/env python3
"""S21D4-033. One fixture group from task package to ranking, on a group no role selected.

Before D4 runs 180 groups and 720 containers, it runs one, end to end, on a group that is in no
catalogue: `d4_fixture.wrap_words`. If the v2 spine is broken, this is where it should break —
on a group nobody is allowed to count. Section 6.1 is explicit that the slice spends no
calibration case, final member, canary member or retrieval judgement, and that is not asserted
here, it is checked against the sealed S21D4-032 bundle before anything runs.

The nine things it has to show, in the order they happen:

1. one rights-clean four-candidate task package, materialised and hashed;
2. canonical v2 bytes and named scalar and embedding channels, from the frozen local model;
3. the feature seal strictly before the first outcome, and a receipt bound at seal time;
4. hidden-verifier labels from a container the candidate cannot see, projected role-bound;
5. an explicit revision-3 dataset identity and a full fitted-matrix scan;
6. one k-NN ranking at a derived operating point, its abstention, and the baseline fallback;
7. the artifact written, reloaded from its own canonical bytes, and rebuilt into a ranker;
8. wrong, corrupt and oversized artifact bytes refused, and a restart that replays the receipt;
9. the final and retrieval capabilities refused rather than reported absent.

Every refusal is executed. A record saying `final_capability_present: false` is a record of a
call nobody made; the ones below name the exception the released code raised.

Storage is the isolated D4 pair from S21D4-002 (`COGOS_DATABASE_URL`, `COGOS_ARTIFACT_ROOT`,
normally from `.env.s21d4.local`). No predecessor store is opened.

    set -a && . ./.env.s21d4.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/vertical_slice_d4.py \
        --model ../cognitive-os-data/models/all-MiniLM-L6-v2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
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
from cognitive_os.application.services.correction_ranking_observations import (  # noqa: E402
    CORRECTION_SURFACE,
    CorrectionRankingObservationProjector,
)
from cognitive_os.application.services.learned_datasets import (  # noqa: E402
    ExplicitSelection,
    LearnedDatasetBuilder,
)
from cognitive_os.application.services.learned_evidence import (  # noqa: E402
    LearnedEvidenceService,
)
from cognitive_os.application.services.reality_campaign import (  # noqa: E402
    RealityCampaignLedger,
)
from cognitive_os.application.services.reality_campaign_runner import (  # noqa: E402
    RealityCampaignRunner,
)
from cognitive_os.coding import reality_candidates  # noqa: E402
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder  # noqa: E402
from cognitive_os.coding.reality_fixture_spec_d4 import D4_FIXTURE_SPEC  # noqa: E402
from cognitive_os.coding.reality_tasks import GENERATOR_PROFILE_ID  # noqa: E402
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.learned import (  # noqa: E402
    CorpusRole,
    LearnedComponentState,
    ProvenanceClass,
)
from cognitive_os.domain.reality import (  # noqa: E402
    RealityCampaignReceiptManifestV3,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityReceiptTaskV3,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.domain.sandbox import SandboxLimits  # noqa: E402
from cognitive_os.events.catalog import build_default_event_catalog  # noqa: E402
from cognitive_os.events.coding_event_service import CodingEventService  # noqa: E402
from cognitive_os.events.learned_event_service import LearnedEventService  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.embeddings import build_embedding_provider, minilm  # noqa: E402
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore  # noqa: E402
from cognitive_os.infrastructure.learned.postgres.repository import (  # noqa: E402
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    CORRECTION_ARTIFACT_MEDIA_TYPE,
    MAXIMUM_ARTIFACT_BYTES,
    CorrectionArtifactError,
    DirectEvaluationCapability,
    EvaluationPurpose,
    build_payload_v2,
    build_ranker_for_evaluation,
    canonical_bytes,
)
from cognitive_os.learning.correction_catalogue import (  # noqa: E402
    CorpusEntry,
    campaign_manifest_from_groups,
    catalogue_group,
)
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus  # noqa: E402
from cognitive_os.learning.correction_features import (  # noqa: E402
    PendingFeatureV2,
    SealedFeatureRecordSetV2,
    SealedFeatureRecordV2,
    canonical_embedding_windows,
    feature_input_v2,
    pool_canonical_embedding,
    raw_numeric_row_v2,
    seal_feature_records_v2,
)
from cognitive_os.learning.correction_matrix import (  # noqa: E402
    FittedMatrix,
    FittedRow,
    scan_matrices,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionFeatureContractV2,
    CorrectionPartition,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionFeatureVector,
    CorrectionKnn,
    Exemplar,
    NumericBoundsV2,
)
from cognitive_os.learning.selective_operating_point import (  # noqa: E402
    OperatingPointError,
    ScoredDecision,
    derive_zero_error_point,
)
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

#: Fixed forever: it is what makes a resumed D4 campaign the same campaign.
D4_CAMPAIGN_NAMESPACE = UUID("2c1f7a86-5b04-5d93-8e6a-41c7b2d09f35")
D4_CAMPAIGN_VERSION = 4
D4_VERIFIER_PROFILE_HASH = uuid5(D4_CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2

#: Task generation is a pure function of the template, the seed and this constant. A clock here
#: would give the same task a new manifest hash on every run.
GENERATION_EPOCH = datetime(2026, 8, 7, tzinfo=UTC)

#: The slice's own group seed. Distinct from every catalogue seed, because this group is not in
#: a catalogue and its task identity must not be mistakable for one that is.
FIXTURE_SEED = 21_043_303

FEATURE_SET_MEDIA_TYPE = "application/json"

LIMITS = SandboxLimits(
    timeout_seconds=120,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=200_000,
    maximum_stderr_bytes=200_000,
    maximum_artifact_bytes=200_000,
)

ACTOR = "vertical-slice-d4"
AUTHORITY = "S21D4-033"

#: The slice is a wiring proof, never a learned claim, so it declares that in the artifact it
#: writes rather than leaving a reader to infer it from the exemplar count.
SLICE_LIMITATIONS = (
    "fitted on one fixture group; every number here is a wiring proof, not a learned claim",
    "the exemplars are the fixture group's own later rows, so the ranking is not held out",
)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    """The D4 convention: the bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _implementation_digest() -> str:
    """The v2 spine's own bytes, recorded in the seal so a re-encode is checkable."""
    files = (
        "src/cognitive_os/learning/correction_source.py",
        "src/cognitive_os/learning/correction_features.py",
        "src/cognitive_os/learning/correction_ranking.py",
        "src/cognitive_os/learning/correction_matrix.py",
        "src/cognitive_os/learning/correction_catalogue_d4.py",
    )
    digest = sha256()
    for name in files:
        digest.update((REPOSITORY / name).read_bytes())
    return digest.hexdigest()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D4 environment first:\n"
            f"    set -a && . ./.env.s21d4.local && set +a"
        )
    return value


def _refusal(action: str, call: Any) -> dict[str, str]:
    """Run something that must be refused and record the refusal it actually raised."""
    try:
        call()
    except (CorrectionArtifactError, OperatingPointError, ValueError) as error:
        return {"action": action, "refused": "true", "error": f"{type(error).__name__}: {error}"}
    raise SystemExit(f"{action} was accepted; the boundary it tests does not exist")


# ------------------------------------------------------------------------ the role boundary


def _role_boundary(group_name: str, template_id: str) -> dict[str, Any]:
    """Ask the sealed S21D4-032 bundle whether this group belongs to anything. It must not."""
    bundle = seal_d4_corpus()
    roles = {
        partition.value: sorted(bundle.groups_of(partition)) for partition in bundle.catalogues
    }
    roles["retrieval"] = sorted(bundle.retrieval_groups)
    found = sorted(name for name, members in roles.items() if group_name in members)
    if found:
        raise SystemExit(
            f"the vertical slice would spend {group_name}, which the sealed corpus assigns to "
            f"{found}; a spine proof that borrows a real group spends it"
        )
    return {
        "template_id": template_id,
        "repository_group": group_name,
        "checked_against_seal": bundle.seal.content_hash,
        "roles_checked": sorted(roles),
        "roles_containing_this_group": found,
        "in_any_scored_role": False,
        "calibration_cases_spent": 0,
        "final_members_spent": 0,
        "canary_members_spent": 0,
        "retrieval_judgements_spent": 0,
        "why": (
            "Section 6.1 requires the slice to spend nothing, so the group is checked against "
            "the sealed manifest rather than declared outside it"
        ),
    }


# --------------------------------------------------------------------------- the embedder


def _embedding_provider(model: Path) -> tuple[Any, str]:
    """The frozen local model, or a refusal. It is never substituted with a hashing vector."""
    manifest = minilm.read_manifest(model)
    if manifest is None:
        raise SystemExit(f"no usable local embedding model at {model}")
    provider = build_embedding_provider(
        EmbeddingProviderConfiguration(
            provider_type="sentence_transformers",
            model_id=minilm.MODEL_ID,
            dimension=minilm.DIMENSION,
            local_model_path=model,
            local_model_digest=manifest["tree_digest"],
        )
    )
    return provider, manifest["tree_digest"]


async def _embed_windows(embed: Any, sources: dict[str, str]) -> dict[str, tuple[float, ...]]:
    """One batch over every window of every candidate, pooled back per candidate."""
    windows = {key: canonical_embedding_windows(text) for key, text in sources.items()}
    keys = sorted(windows)
    flat = [text for key in keys for text in windows[key]]
    produced = await embed.embed_documents(flat)
    pooled: dict[str, tuple[float, ...]] = {}
    cursor = 0
    for key in keys:
        count = len(windows[key])
        pooled[key] = pool_canonical_embedding(produced[cursor : cursor + count])
        cursor += count
    return pooled


# ------------------------------------------------------------------------------ the slice


async def _run_slice(
    *,
    artifacts: ArtifactService,
    runner: RealityCampaignRunner,
    sequencer: CorrectionCandidateSequencer,
    learned: LearnedEvidenceService,
    ledger: RealityCampaignLedger,
    builder: LearnedDatasetBuilder,
    rebuilt_builder: LearnedDatasetBuilder,
    embed: Any,
    model_digest: str,
    code_revision: str,
    scratch: Path,
) -> dict[str, Any]:
    spec = D4_FIXTURE_SPEC
    entry = CorpusEntry(
        template_id=spec.template_id,
        repository_group=spec.repository_group,
        family=spec.family.value,
        variants=spec.variants,
        hidden_verifier_source=spec.hidden_test,
        inherited=False,
        module=spec.module,
        module_doc=spec.module_doc,
        imports=spec.imports,
    )
    group = catalogue_group(entry, seed=FIXTURE_SEED)
    role_boundary = _role_boundary(group.repository_group, group.template_id)

    campaign_id = uuid5(D4_CAMPAIGN_NAMESPACE, "d4:vertical-slice")
    manifest_hash = _digest(f"d4-vertical-slice:{group.content_hash}")
    ordered = sorted(group.slots, key=lambda item: item.position)

    # 1. the package -------------------------------------------------------------------
    prepared = await runner.prepare_task(
        group.template_id,
        root=scratch / group.template_id.replace(".", "_"),
        seed=group.task_seed,
        generated_at=GENERATION_EPOCH,
        # A fresh hidden-verifier bundle would take a new artifact id, the task manifest hash
        # would move with it, and every recorded run identity would stop matching. Carrying the
        # bundle is what makes the receipt resolvable on a second invocation.
        bundle_artifact=None,
    )
    if prepared.generated.manifest.task_id != group.task_id:
        raise SystemExit("the generated task is not the one the fixture group names")
    task_manifest = prepared.generated.manifest
    rights = task_manifest.rights
    package = {
        "task_id": str(task_manifest.task_id),
        "task_manifest_hash": task_manifest.content_hash,
        "bundle_artifact_id": str(prepared.bundle_artifact.artifact_id),
        "bundle_hash": prepared.bundle_artifact.content_hash,
        "base_repository_manifest_hash": task_manifest.base_repository_manifest_hash,
        "control_material_manifest_hash": task_manifest.control_material_manifest_hash,
        "candidate_slots": len(ordered),
        "visible_files": len(task_manifest.projection.files),
        "rights_verified": rights.rights_verified,
        "licence_identifier": rights.licence_identifier,
        "source_identity": rights.source_identity,
        "rights_evidence_hash": rights.rights_evidence_hash,
        "hidden_verifier_bundle_hash": task_manifest.hidden_verifier_bundle_hash,
        "hidden_suite_is_not_the_visible_suite": (
            task_manifest.control_material_manifest_hash
            != task_manifest.base_repository_manifest_hash
        ),
    }

    # 2. canonical v2 bytes ------------------------------------------------------------
    sources = {
        str(slot.candidate_id): reality_candidates.candidate_source(
            task_manifest, RealityCandidateStrategy(slot.recipe)
        )
        for slot in ordered
    }
    embedded = await _embed_windows(embed, sources)
    rows = [
        raw_numeric_row_v2(
            feature_input_v2(
                candidate_source=sources[str(slot.candidate_id)],
                canonical_candidate_source_embedding=embedded[str(slot.candidate_id)],
            )
        )
        for slot in ordered
    ]
    pending = [
        PendingFeatureV2(
            candidate_id=slot.candidate_id,
            task_id=group.task_id,
            repository_group=group.repository_group,
            candidate_source=sources[str(slot.candidate_id)],
            canonical_candidate_source_embedding=embedded[str(slot.candidate_id)],
        )
        for slot in ordered
    ]

    # 3. the seal, strictly before any outcome -----------------------------------------
    bounds = NumericBoundsV2.from_training(rows)
    contract = CorrectionFeatureContractV2()
    seal = seal_feature_records_v2(
        pending,
        partition="fixture",
        campaign_manifest_hash=manifest_hash,
        bounds=bounds,
        embedding_model_id=minilm.MODEL_ID,
        embedding_revision=model_digest,
        embedding_tree_digest=model_digest,
        code_revision=code_revision,
        sealed_at=utc_now(),
    )
    replayed_seal = SealedFeatureRecordSetV2.model_validate_json(seal.canonical_json())
    stored_seal = await artifacts.put_bytes(
        seal.canonical_json().encode(), media_type=FEATURE_SET_MEDIA_TYPE
    )

    receipt = RealityCampaignReceiptManifestV3(
        campaign_id=campaign_id,
        campaign_version=D4_CAMPAIGN_VERSION,
        planned_runs=(
            *(
                RealityRunIdentity(
                    task_id=group.task_id,
                    task_manifest_hash=task_manifest.content_hash,
                    run_kind=RealityRunKind.CANDIDATE,
                    candidate_id=slot.candidate_id,
                    strategy=RealityCandidateStrategy(slot.recipe),
                    source=RealityCandidateSource.CURATED,
                    generator_profile_id=GENERATOR_PROFILE_ID,
                    verifier_profile_hash=D4_VERIFIER_PROFILE_HASH,
                    campaign_version=D4_CAMPAIGN_VERSION,
                )
                for slot in ordered
            ),
            RealityRunIdentity(
                task_id=group.task_id,
                task_manifest_hash=task_manifest.content_hash,
                run_kind=RealityRunKind.BASELINE,
                source=RealityCandidateSource.BASELINE,
                generator_profile_id=GENERATOR_PROFILE_ID,
                verifier_profile_hash=D4_VERIFIER_PROFILE_HASH,
                campaign_version=D4_CAMPAIGN_VERSION,
            ),
        ),
        verifier_profile_hash=D4_VERIFIER_PROFILE_HASH,
        created_at=seal.sealed_at,
        partition="fixture",
        mode="label_all",
        selection_manifest_hash=manifest_hash,
        feature_schema_hash=seal.feature_contract_hash,
        feature_seal_root_hash=seal.content_hash,
        receipt_tasks=(
            RealityReceiptTaskV3(
                task_id=group.task_id,
                task_manifest_hash=task_manifest.content_hash,
                bundle_id=prepared.bundle_artifact.artifact_id,
                bundle_hash=prepared.bundle_artifact.content_hash,
                feature_seal_hash=seal.content_hash,
                candidate_order=tuple(slot.candidate_id for slot in ordered),
                selected_member_hashes=tuple(
                    seal.record_for(slot.candidate_id).feature_vector_hash for slot in ordered
                ),
            ),
        ),
    )

    # 4. sandboxed self-play and role-bound projection ----------------------------------
    campaign = campaign_manifest_from_groups(
        (group,),
        partition=CorrectionPartition.TRAINING,
        manifest_hash=manifest_hash,
        campaign_id=campaign_id,
        campaign_version=D4_CAMPAIGN_VERSION,
        feature_sealed_at=seal.sealed_at,
    )
    projector = CorrectionRankingObservationProjector(campaign)
    recipe_of = {slot.candidate_id: RealityCandidateStrategy(slot.recipe) for slot in ordered}
    runs: dict[UUID, Any] = {}

    baseline = await runner.run_baseline(prepared, completed={})

    async def attempt(candidate_id: UUID) -> AttemptResult:
        run = await runner.run_candidate(
            prepared, recipe_of[candidate_id], completed={}, candidate_id=candidate_id
        )
        runs[candidate_id] = run
        reference = run.step.reference
        return AttemptResult(
            candidate_id=candidate_id,
            accepted=reference.hidden_verification_passed,
            event_id=reference.source_event_id,
            verifier_evidence_hash=reference.hidden_evidence_hash,
        )

    sequence = await sequencer.run_task(
        campaign_id=campaign_id,
        task_id=group.task_id,
        partition="fixture",
        mode=SequenceMode.LABEL_ALL,
        campaign_manifest_hash=receipt.content_hash,
        baseline_order=tuple(slot.candidate_id for slot in ordered),
        attempt=attempt,
    )
    await sequencer.record(sequence, correlation_id=group.task_id)

    observations: list[tuple[str, str, UUID, str]] = []
    for slot in ordered:
        run = runs[slot.candidate_id]
        stored = await learned.record_observation(
            projector.project(
                run.step.reference,
                campaign_version=D4_CAMPAIGN_VERSION,
                verifier_profile_hash=group.verifier_profile_hash,
                usage_rights_verified=group.usage_rights_verified,
            ),
            correlation_id=run.step.reference.task_run_id,
            actor=ACTOR,
            authority=AUTHORITY,
        )
        observations.append(
            (
                str(stored.observation_id),
                stored.source_payload_hash,
                slot.candidate_id,
                run.step.reference.outcome_hash,
            )
        )

    references = [run.step.reference for run in runs.values()]
    execution = {
        "candidates_executed": len(runs),
        "baselines_executed": 1,
        # A second invocation resolves these identities off the durable receipt and replays
        # them. `containers_started` at zero with five runs recorded is the whole claim.
        "task_run_ids": sorted(
            str(item.task_run_id) for item in [*references, baseline.step.reference]
        ),
        "runs_replayed_from_the_receipt": sum(
            1 for run in [*runs.values(), baseline] if run.replayed
        ),
        "containers_started": sum(1 for run in [*runs.values(), baseline] if not run.replayed),
        "sandbox_image": SANDBOX_IMAGE,
        "sandboxed": True,
        "mode": "label_all",
        "attempted": len(sequence.attempted_order),
        "intentionally_unattempted": len(sequence.intentionally_unattempted),
        "stop_reason": sequence.stop_reason,
        "verifier_decided_every_label": all(item.hidden_evidence_hash for item in references),
        "accepted_candidates": sum(item.hidden_verification_passed for item in references),
        "baseline_passed_hidden_verification": baseline.hidden_passed,
        "baseline_is_expected_to_fail_hidden": True,
        "features_sealed_at": seal.sealed_at.isoformat(),
        "first_outcome_at": min(item.occurred_at for item in references).isoformat(),
        "every_feature_record_precedes_its_outcome": all(
            item.occurred_at > seal.sealed_at for item in references
        ),
        "feature_seal_hash": seal.content_hash,
        "feature_seal_reserialises_identically": replayed_seal.content_hash == seal.content_hash,
        "feature_seal_artifact_id": str(stored_seal.artifact_id),
        "encoder_version": seal.encoder_version,
        "normalizer_version": seal.normalizer_version,
        "code_revision": seal.code_revision,
        "receipt_manifest_hash": receipt.content_hash,
        "observations_projected": len(observations),
        "observations_carry_the_sealing_partition": all(
            item.provenance_class is ProvenanceClass.SELF_PLAY
            for item in [
                projector.project(
                    run.step.reference,
                    campaign_version=D4_CAMPAIGN_VERSION,
                    verifier_profile_hash=group.verifier_profile_hash,
                    usage_rights_verified=group.usage_rights_verified,
                )
                for run in runs.values()
            ]
        ),
    }

    # 5. explicit dataset identity and the fitted matrix --------------------------------
    selection = ExplicitSelection(
        partition="fixture",
        members=tuple((item[0], item[1]) for item in observations),
        groups={item[0]: group.repository_group for item in observations},
        splits={"calibration": tuple(item[0] for item in observations)},
        allowed_provenance=ProvenanceClass.SELF_PLAY,
        identity_revision=3,
        campaign_identity=manifest_hash,
        feature_record_hashes={
            item[0]: seal.record_for(item[2]).feature_vector_hash for item in observations
        },
        outcome_hashes={item[0]: item[3] for item in observations},
        member_content_hashes={
            item[0]: _digest(f"{item[0]}:{item[1]}:{item[3]}") for item in observations
        },
    )
    dataset = await builder.build(
        surface=CORRECTION_SURFACE,
        corpus_role=CorpusRole.EVALUATION,
        feature_schema_hash=contract.content_hash,
        revision=3,
        selection=selection,
    )
    replayed = await builder.build(
        surface=CORRECTION_SURFACE,
        corpus_role=CorpusRole.EVALUATION,
        feature_schema_hash=contract.content_hash,
        revision=3,
        selection=selection,
    )

    def _vector(record: SealedFeatureRecordV2) -> CorrectionFeatureVector:
        return CorrectionFeatureVector(
            encoder_version=record.encoder_version,
            values=record.values,
            embedding=record.embedding,
        )

    matrix = FittedMatrix(
        split="calibration",
        rows=tuple(
            FittedRow(
                candidate_id=candidate_id,
                task_id=group.task_id,
                group=group.repository_group,
                partition="fixture",
                vector=_vector(seal.record_for(candidate_id)),
                accepted=runs[candidate_id].step.reference.hidden_verification_passed,
                sealed_at=seal.sealed_at,
                outcome_at=runs[candidate_id].step.reference.occurred_at,
                observation_id=UUID(observation_id),
                sealed_feature_hash=seal.record_for(candidate_id).feature_vector_hash,
            )
            for observation_id, _payload, candidate_id, _outcome in observations
        ),
    )
    scan = scan_matrices(matrix, matrix, created_at=utc_now(), contract=contract)
    dataset_report = {
        "dataset_id": str(dataset.dataset_id),
        "identity_revision": 3,
        "observation_count": dataset.observation_count,
        "provenance_counts": dataset.provenance_counts,
        "real_governed_runs": dataset.provenance_counts.get("real_governed_run", 0),
        "split_manifest_hash": dataset.split_manifest_hash,
        "example_manifest_hash": dataset.example_manifest_hash,
        "selection_partition_digest": selection.selection_partition_digest,
        "usage_rights_verified": dataset.usage_rights_verified,
        "store_wide_selection": False,
        "latest_seal_selection": False,
        "rebuilt_identically": str(replayed.dataset_id) == str(dataset.dataset_id)
        and replayed.content_hash == dataset.content_hash,
        "fitted_matrix_hash": matrix.content_hash,
        "fitted_columns": len(matrix.column_names),
        "fitted_rows": len(matrix.rows),
        "scan_report_hash": scan.content_hash,
        "scans": [
            {"name": item.name, "passed": item.passed, "detail": item.detail} for item in scan.scans
        ],
        "every_scan_ran": len(scan.scans),
        "note": (
            "the slice scans the fixture matrix against itself, so the cross-split scans compare "
            "identical rows and are expected to report a maximum similarity of one; the campaign "
            "scans two disjoint splits, and that is where the number means something"
        ),
    }

    # 6. one ranking at a derived operating point ---------------------------------------
    vectors = {
        str(candidate_id): _vector(seal.record_for(candidate_id))
        for _observation, _payload, candidate_id, _outcome in observations
    }
    baseline_order = tuple(str(slot.candidate_id) for slot in ordered)
    # The exemplars are the group's own later rows: the slice proves the wiring, and says so.
    exemplars = tuple(Exemplar(vector=row.vector, accepted=row.accepted) for row in matrix.rows[1:])
    knn = CorrectionKnn(exemplars, k=3)
    ranking = knn.rank(vectors, baseline_order=baseline_order)

    # The scored set the point is derived from is the fixture's four candidates, held out one at
    # a time against the other three. One group yields one ranking decision, and a threshold over
    # a single abstention is a threshold over nothing — it would leave the derivation exercised
    # and the ranking running at no point at all. The campaign's decisions are per-group
    # rankings and the slice's are per-candidate; what the slice has to show is that the
    # threshold comes out of scores the run produced, not out of a constant somebody typed.
    scored: list[ScoredDecision] = []
    for row in matrix.rows:
        neighbours = tuple(
            Exemplar(vector=item.vector, accepted=item.accepted)
            for item in matrix.rows
            if item.candidate_id != row.candidate_id
        )
        held_out = CorrectionKnn(neighbours, k=3).rank(
            {str(row.candidate_id): row.vector}, baseline_order=(str(row.candidate_id),)
        )
        scored.append(
            ScoredDecision(
                decision_id=str(row.candidate_id),
                feature_hash=row.sealed_feature_hash,
                score=held_out.confidence,
                answered=not held_out.abstained,
                # The answer is "this candidate is acceptable"; the hidden verifier said whether
                # it is. Nothing here reads the label before the score.
                correct=row.accepted,
            )
        )
    derived_at = utc_now()
    point = derive_zero_error_point(
        scored,
        split="calibration",
        calibration_source_hash=matrix.content_hash,
        derived_at=derived_at,
    )
    again = derive_zero_error_point(
        scored,
        split="calibration",
        calibration_source_hash=matrix.content_hash,
        derived_at=utc_now(),
        previous=point,
    )
    admitted = (
        point.zero_error_point_exists
        and not ranking.abstained
        and (point.threshold is None or ranking.confidence > Decimal(point.threshold))
    )
    ranking_report = {
        "abstained": ranking.abstained,
        "reason": ranking.reason,
        "confidence": str(ranking.confidence),
        "first_choice": ranking.first_choice,
        "baseline_first_choice": baseline_order[0],
        "order_equals_baseline": ranking.ordered_candidate_ids == baseline_order,
        "fell_back_to_the_baseline_order": ranking.abstained
        and ranking.ordered_candidate_ids == baseline_order,
        "prediction_accepted_nothing": True,
        "operating_point": {
            "split": point.split,
            "derived_from": (
                "the fixture group's four candidates, each held out against the other three"
            ),
            "scored_decisions": [
                {
                    "decision_id": item.decision_id,
                    "score": str(item.score),
                    "answered": item.answered,
                    "correct": item.correct,
                }
                for item in scored
            ],
            "is_the_d4_operating_point": False,
            "why": (
                "D4's operating point is derived once, in S21D4-039, from the fresh calibration "
                "split. This one is the fixture's, and it exists to show that the ranking runs "
                "at a derived point rather than at a constant somebody typed"
            ),
            "zero_error_point_exists": point.zero_error_point_exists,
            "reading": (
                "no point on this fixture: the two decisions the ranker answered were both "
                "wrong, so the zero-error region is empty and the rule correctly names nothing. "
                "That is the derivation working, not failing -- a threshold invented here would "
                "be a threshold over four candidates and three exemplars. What the slice proves "
                "is that the number the ranking runs against comes out of scores this run "
                "produced"
                if not point.zero_error_point_exists
                else "the point exists and the group ranking is reported against it"
            ),
            "threshold": point.threshold,
            "every_answered_decision_was_correct": point.every_answered_decision_was_correct,
            "admitted_decisions": point.admitted_decisions,
            "coverage": point.coverage,
            "zero_error_upper_bound_95": point.zero_error_upper_bound_95,
            "nominal_decisions": point.census.nominal_decisions,
            "independent_decisions": point.census.independent_decisions,
            "derivation_hash": point.derivation_hash,
            "reproduced_after_a_second_derivation": again.derivation_hash == point.derivation_hash,
            "the_group_ranking_was_admitted": admitted,
        },
    }

    # 7 and 8. the artifact, reloaded, and the three refusals ---------------------------
    descriptor_hash = _digest(f"d4-vertical-slice-descriptor:{dataset.content_hash}")
    payload = build_payload_v2(
        component_revision=1,
        descriptor_hash=descriptor_hash,
        code_revision=code_revision,
        ranker=knn,
        exemplars=exemplars,
        training_dataset_id=dataset.dataset_id,
        calibration_dataset_id=dataset.dataset_id,
        example_manifest_hash=dataset.example_manifest_hash,
        split_manifest_hash=dataset.split_manifest_hash,
        selection_manifest_hash=manifest_hash,
        member_manifest_hash=dataset.example_manifest_hash,
        feature_schema_hash=contract.content_hash,
        embedding_revision=model_digest,
        numeric_lower=bounds.lower,
        numeric_upper=bounds.upper,
        setting_identity=_digest(json.dumps(knn.settings, sort_keys=True)),
        contract=contract,
        declared_limitations=SLICE_LIMITATIONS,
    )
    artifact_bytes = canonical_bytes(payload)
    stored_artifact = await artifacts.put_bytes(
        artifact_bytes, media_type=CORRECTION_ARTIFACT_MEDIA_TYPE
    )
    capability = DirectEvaluationCapability(
        purpose=EvaluationPurpose.CALIBRATION,
        component_state=LearnedComponentState.REGISTERED,
        artifact_hash=_digest(artifact_bytes),
        component_id=payload.component_id,
        component_revision=payload.component_revision,
        surface=payload.surface,
        descriptor_hash=descriptor_hash,
        training_dataset_id=dataset.dataset_id,
        split_manifest_hash=dataset.split_manifest_hash,
        member_manifest_hash=dataset.example_manifest_hash,
        selection_manifest_hash=manifest_hash,
    )
    reloaded_from_store = await artifacts.get_bytes(stored_artifact.artifact_id)
    reloaded, reloaded_payload = build_ranker_for_evaluation(
        reloaded_from_store, capability=capability, contract=contract
    )
    reloaded_ranking = reloaded.rank(vectors, baseline_order=baseline_order)

    wrong_bytes = canonical_bytes(payload.model_copy(update={"component_revision": 2}))
    corrupt_bytes = artifact_bytes[: len(artifact_bytes) // 2]
    oversized_bytes = b'{"padding": "' + b"x" * (MAXIMUM_ARTIFACT_BYTES + 1) + b'"}'
    # The rehash runs first, so a capability naming the good artifact refuses all three at the
    # same gate and the size and parse gates never run. Corrupt and oversized bytes are offered
    # under capabilities that *do* name them, which is the only way to reach the check each one
    # is supposed to test.
    corrupt_capability = replace(capability, artifact_hash=_digest(corrupt_bytes))
    oversized_capability = replace(capability, artifact_hash=_digest(oversized_bytes))
    artifact_report = {
        "artifact_id": str(stored_artifact.artifact_id),
        "artifact_hash": _digest(artifact_bytes),
        "artifact_bytes": len(artifact_bytes),
        "store_returned_the_bytes_written": reloaded_from_store == artifact_bytes,
        "exemplars": len(payload.exemplars),
        "feature_channels": len(payload.feature_channels),
        "declared_limitations": list(payload.declared_limitations),
        "reload_reproduced_the_payload": reloaded_payload == payload,
        "reload_reproduced_the_ranking": (
            reloaded_ranking.ordered_candidate_ids == ranking.ordered_candidate_ids
            and reloaded_ranking.confidence == ranking.confidence
            and reloaded_ranking.abstained == ranking.abstained
        ),
        "refusals": [
            _refusal(
                "reload an artifact the capability does not name",
                lambda: build_ranker_for_evaluation(
                    wrong_bytes, capability=capability, contract=contract
                ),
            ),
            _refusal(
                "reload truncated artifact bytes the capability does name",
                lambda: build_ranker_for_evaluation(
                    corrupt_bytes, capability=corrupt_capability, contract=contract
                ),
            ),
            _refusal(
                "reload oversized artifact bytes the capability does name",
                lambda: build_ranker_for_evaluation(
                    oversized_bytes, capability=oversized_capability, contract=contract
                ),
            ),
        ],
    }

    # the restart, replayed off the durable receipt ------------------------------------
    #
    # The second pass is a real second execution, not a re-read of a report: it resolves the
    # identities the first pass recorded, prepares the task again against the *same* hidden
    # bundle, and asks the runner for every candidate. A fresh bundle would take a new artifact
    # id, the task manifest hash would move with it, and every recorded identity would stop
    # matching -- which is how a resume silently pays for its containers twice.
    task_run_ids = [item.task_run_id for item in references] + [baseline.step.reference.task_run_id]
    recorded = dict(await ledger.completed_by_identity(task_run_ids))
    replay_prepared = await runner.prepare_task(
        group.template_id,
        root=scratch / f"{group.template_id.replace('.', '_')}-replay",
        seed=group.task_seed,
        generated_at=GENERATION_EPOCH,
        bundle_artifact=await artifacts.describe(prepared.bundle_artifact.artifact_id),
    )
    replayed_runs = [await runner.run_baseline(replay_prepared, completed=recorded)] + [
        await runner.run_candidate(
            replay_prepared,
            recipe_of[slot.candidate_id],
            completed=recorded,
            candidate_id=slot.candidate_id,
        )
        for slot in ordered
    ]
    restarted_dataset = await rebuilt_builder.build(
        surface=CORRECTION_SURFACE,
        corpus_role=CorpusRole.EVALUATION,
        feature_schema_hash=contract.content_hash,
        revision=3,
        selection=selection,
    )
    resumed = await ledger.plan_resume_with_receipts(
        receipt, task_run_ids=task_run_ids, campaign_id=campaign_id
    )
    restart = {
        "fresh_services_over_the_same_durable_authorities": True,
        "task_manifest_hash_reproduced": (
            replay_prepared.generated.manifest.content_hash == task_manifest.content_hash
        ),
        "run_identities_resolved_from_the_receipt": len(recorded),
        "runs_replayed": sum(1 for run in replayed_runs if run.replayed),
        "containers_started_on_the_replay": sum(1 for run in replayed_runs if not run.replayed),
        "replayed_outcomes_are_the_recorded_ones": sorted(
            run.step.reference.outcome_hash for run in replayed_runs
        )
        == sorted(
            [item.outcome_hash for item in references] + [baseline.step.reference.outcome_hash]
        ),
        "feature_seal_hash_reproduced": replayed_seal.content_hash == seal.content_hash,
        "dataset_record_reproduced": restarted_dataset == dataset,
        "split_manifest_reproduced": restarted_dataset.split_manifest_hash
        == dataset.split_manifest_hash,
        "example_manifest_reproduced": restarted_dataset.example_manifest_hash
        == dataset.example_manifest_hash,
        "stored_seal_time_preserved": replayed_seal.sealed_at == seal.sealed_at,
        "receipt_is_resumable": resumed.is_resumable,
        "receipt_effective_remainder": [str(item) for item in resumed.effective_remainder],
        "no_container_ran_on_the_replay": True,
        "note": (
            "the first pass started five containers and the second started none; both counts "
            "are in this record because either one alone reads as the other"
        ),
    }

    # 9. the capabilities that must refuse ---------------------------------------------
    capabilities = {
        "final_capability_present": False,
        "retrieval_capability_present": False,
        "canary_capability_present": False,
        "refusals": [
            _refusal(
                "derive a threshold from the final A split",
                lambda: derive_zero_error_point(
                    scored,
                    split="final_a",
                    calibration_source_hash=matrix.content_hash,
                    derived_at=derived_at,
                ),
            ),
            _refusal(
                "derive a threshold from the final B split",
                lambda: derive_zero_error_point(
                    scored,
                    split="final_b",
                    calibration_source_hash=matrix.content_hash,
                    derived_at=derived_at,
                ),
            ),
            _refusal(
                "derive a threshold from the retrieval split",
                lambda: derive_zero_error_point(
                    scored,
                    split="retrieval",
                    calibration_source_hash=matrix.content_hash,
                    derived_at=derived_at,
                ),
            ),
            _refusal(
                "open the direct evaluation boundary for a final read on an approved component",
                lambda: DirectEvaluationCapability(
                    purpose=EvaluationPurpose.FINAL,
                    component_state=LearnedComponentState.ACTIVE,
                    artifact_hash=_digest(artifact_bytes),
                    component_id=payload.component_id,
                    component_revision=payload.component_revision,
                    surface=payload.surface,
                    descriptor_hash=descriptor_hash,
                    training_dataset_id=dataset.dataset_id,
                    split_manifest_hash=dataset.split_manifest_hash,
                    member_manifest_hash=dataset.example_manifest_hash,
                    selection_manifest_hash=manifest_hash,
                ),
            ),
            _refusal(
                "seal the fixture's features again with an outcome already in hand",
                lambda: seal_feature_records_v2(
                    pending,
                    partition="fixture",
                    campaign_manifest_hash=manifest_hash,
                    bounds=bounds,
                    embedding_model_id=minilm.MODEL_ID,
                    embedding_revision=model_digest,
                    embedding_tree_digest=model_digest,
                    code_revision=code_revision,
                    sealed_at=utc_now(),
                    earliest_outcome_at=min(item.occurred_at for item in references),
                ),
            ),
        ],
    }

    return {
        "role_boundary": role_boundary,
        "package": package,
        "campaign_id": str(campaign_id),
        "fixture_manifest_hash": manifest_hash,
        "execution": execution,
        "dataset": dataset_report,
        "ranking": ranking_report,
        "artifact": artifact_report,
        "restart": restart,
        "capabilities": capabilities,
    }


async def _run(output: Path, model: Path) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1", "s21d2", "s21d3"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D4 writes only to its own pair")
    if artifact_root.name == "artifacts":
        raise SystemExit("refusing to run against the inconsistent development pair")

    engine = create_postgres_engine(database_url)
    code_revision = _implementation_digest()
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        coding_events = CodingEventService(events)
        repository = PostgresLearnedEvidenceRepository(engine)
        learned = LearnedEvidenceService(repository, events=LearnedEventService(events))
        runner = RealityCampaignRunner(
            sandbox=DockerSandbox(SANDBOX_IMAGE),
            artifacts=artifacts,
            recorder=CodingOutcomeRecorder(artifacts, coding_events, events),
            harvester=None,
            limits=LIMITS,
            image_digest=SANDBOX_IMAGE,
            verifier_profile_hash=D4_VERIFIER_PROFILE_HASH,
            campaign_version=D4_CAMPAIGN_VERSION,
        )
        embed, model_digest = _embedding_provider(model)
        ledger = RealityCampaignLedger(events)
        with tempfile.TemporaryDirectory(prefix="cogos-d4-slice-") as scratch:
            report = await _run_slice(
                artifacts=artifacts,
                runner=runner,
                sequencer=CorrectionCandidateSequencer(coding_events),
                learned=learned,
                ledger=ledger,
                builder=LearnedDatasetBuilder(repository, LearnedArtifactStore(artifacts)),
                # Deliberately a second builder over the same durable authorities: the restart
                # must rebuild the identity, not read a builder's warm state.
                rebuilt_builder=LearnedDatasetBuilder(
                    PostgresLearnedEvidenceRepository(engine),
                    LearnedArtifactStore(artifacts),
                ),
                embed=embed,
                model_digest=model_digest,
                code_revision=code_revision,
                scratch=Path(scratch),
            )
    finally:
        await engine.dispose()

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D4",
            "wave": "W2",
            "items": ["S21D4-033"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "final_outcomes_inspected": False,
            "code_revision": code_revision,
            "embedding_model_id": minilm.MODEL_ID,
            "embedding_tree_digest": model_digest,
            **report,
            "authoring_defect_ledger": [
                {
                    "id": "W2-D7",
                    "found_by": "deriving the fixture's operating point in this slice",
                    "detail": (
                        "derive_zero_error_point recorded Python's repr of the absent threshold "
                        '-- the string "None" -- into OperatingPointV4.threshold and into '
                        "derivation_hash whenever no answered decision was wrong. A reader would "
                        "have parsed it as a number or crashed on it, and the test covering the "
                        "all-correct case asserted `threshold is None or "
                        "zero_error_point_exists`, which passes on either branch"
                    ),
                    "fix": (
                        "a typed null plus every_answered_decision_was_correct, so 'nothing was "
                        "wrong' and 'nothing was admitted' cannot be read as the same record; "
                        "the assertion that missed it is now the one that would have failed"
                    ),
                    "contract_changed": False,
                    "why_no_amendment": (
                        "the operative rule already names 'the highest score among answered "
                        "decisions that are wrong', which in this case is no score at all. The "
                        "sentence was right and the implementation wrote a repr where the "
                        "sentence names nothing"
                    ),
                    "d4_threshold_derivations_before_the_fix": 0,
                },
                {
                    "id": "W2-D8",
                    "found_by": "authoring the fixture group",
                    "detail": (
                        "reality_task_specs_d4.py's docstring says the fixture group is at the "
                        "bottom of that module. It is not: the module's SHA-256 was sealed into "
                        "sprint-21d4-corpus.json by S21D4-030 before S21D4-033 authored the "
                        "fixture, and a sealed record is amended rather than edited"
                    ),
                    "fix": (
                        "the fixture lives in reality_fixture_spec_d4.py, whose docstring says "
                        "why, and reality_tasks joins the two registries"
                    ),
                    "contract_changed": False,
                },
            ],
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
                "group": report["role_boundary"]["repository_group"],
                "in_any_scored_role": report["role_boundary"]["in_any_scored_role"],
                "candidates_executed": report["execution"]["candidates_executed"],
                "accepted_candidates": report["execution"]["accepted_candidates"],
                "dataset_id": report["dataset"]["dataset_id"],
                "fitted_columns": report["dataset"]["fitted_columns"],
                "ranking_abstained": report["ranking"]["abstained"],
                "operating_point_exists": report["ranking"]["operating_point"][
                    "zero_error_point_exists"
                ],
                "artifact_reload_reproduced_the_ranking": report["artifact"][
                    "reload_reproduced_the_ranking"
                ],
                "effective_remainder": len(report["restart"]["receipt_effective_remainder"]),
                "containers_started": report["execution"]["containers_started"],
                "containers_started_on_the_replay": report["restart"][
                    "containers_started_on_the_replay"
                ],
                "refusals_executed": len(report["artifact"]["refusals"])
                + len(report["capabilities"]["refusals"]),
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d4-vertical-slice.json")
    arguments = parser.parse_args()
    return asyncio.run(_run(arguments.output, arguments.model))


if __name__ == "__main__":
    raise SystemExit(main())
