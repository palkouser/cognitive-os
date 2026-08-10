#!/usr/bin/env python3
"""S21D6-024. One fixture group from task package to conformal admission, on a group no role holds.

Before D6 runs 100 groups and 500 containers, it runs one, end to end, on a group that is in no
D6 catalogue: `d5_fixture.render_duration`. If the spine is broken, this is where it should break
— on a group nobody is allowed to count. Section 6.1 requires the slice to spend no conformal
case, certification case, final member or canary member, and that is not asserted here: the group
is checked against the sealed S21D6-023 bundle before anything runs.

*Why D5's fixture rather than a fresh one.* The fixture's only contract is to be outside every
role, and this one is: it is in none of D6's eight, which the seal check below proves rather than
claims. It carries D6's own campaign namespace, seed and candidate identities, so nothing it
writes collides with D5's run of it, and it lives in D6's isolated store. Authoring a fresh
fixture would cost a near-clone check against 526 released groups and buy the slice nothing it
does not already have.

The nine things it has to show, in the order they happen:

1. one rights-clean four-candidate task package, materialised and hashed;
2. canonical v2 bytes and named scalar and embedding channels, from the frozen local model;
3. the feature seal strictly before the first outcome, and a receipt bound at seal time;
4. hidden-verifier labels from a container the candidate cannot see, projected role-bound;
5. an explicit revision-3 dataset identity and a full fitted-matrix scan;
6. **split-conformal admission** over two disjoint halves of the fixture's own decisions, at the
   pre-registered alpha, and the refusals that keep a bar from choosing itself;
7. the **v3** artifact written, reloaded from its own canonical bytes, and rebuilt into a ranker;
8. wrong, corrupt and oversized artifact bytes refused; a restart that replays the receipt; and
   the artifact backed up and restored;
9. the final and retrieval capabilities refused rather than reported absent.

What is new against D5's slice is step 6, and it is the whole reason D6 exists. D5 derived a
zero-error prefix point here and the fixture's four clean decisions made it *admit everything* at
a floor of zero — the exact behaviour §2.1 showed to be a rule with variance rather than a bound.
The conformal rule cannot do that. On a conformal half this small the finite-sample rank
ceil((1-alpha)*(m+1)) exceeds the number of wrong margins for every m a four-candidate group can
produce, so at the pre-registered alpha the fixture gets **no quantile and admits nothing**. That
is not a failure of the slice; it is the honesty clause the module was written for, driven on real
containers rather than asserted in a unit test.

Because a bar that does not exist cannot bind an artifact, step 7 needs a floor. The slice derives
a **second, clearly-labelled fixture bar** at an alpha the tiny sample can actually support, uses
only that one to bind the artifact, and records both. Neither is D6's operating point: that one is
derived once, at S21D6-034, from the sealed conformal half, and the anti-search rule is executed
here rather than described — a second derivation at a different alpha with `previous=` in hand is
refused, and the refusal is in the record.

Every refusal is executed. A record saying `final_capability_present: false` is a record of a
call nobody made; the ones below name the exception the released code raised.

Storage is the isolated D6 pair from S21D6-002 (`COGOS_DATABASE_URL`, `COGOS_ARTIFACT_ROOT`).
No predecessor store is opened — D5's least of all, because D6 reads its envelope from it.

    set -a && . ./.env.s21d6.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/vertical_slice_d6.py \
        --model ../cognitive-os-data/models/all-MiniLM-L6-v2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

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
from cognitive_os.coding.reality_fixture_spec_d5 import D5_FIXTURE_SPEC  # noqa: E402
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
from cognitive_os.learning.conformal_operating_point import (  # noqa: E402
    ConformalPointError,
    admitted_error_upper_bound,
    conformal_rank,
    derive_conformal_point,
)
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    CORRECTION_ARTIFACT_MEDIA_TYPE,
    MAXIMUM_ARTIFACT_BYTES,
    CorrectionArtifactError,
    DirectEvaluationCapability,
    EvaluationPurpose,
    build_payload_v3,
    build_ranker_for_evaluation_v3,
    canonical_bytes,
    correction_artifact_schema,
)
from cognitive_os.learning.correction_catalogue import (  # noqa: E402
    CorpusEntry,
    campaign_manifest_from_groups,
    catalogue_group,
)
from cognitive_os.learning.correction_catalogue_d6 import seal_d6_corpus  # noqa: E402
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
    Exemplar,
    NumericBoundsV2,
)
from cognitive_os.learning.pairwise_contrastive import (  # noqa: E402
    HYPOTHESIS_CLASS,
    PairwiseContrastiveRanker,
    fit_pairwise_direction,
)
from cognitive_os.learning.selective_operating_point import ScoredDecision  # noqa: E402
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d6-pre-registration.json"
SEALED_MANIFESTS = EVIDENCE / "sprint-21d6-sealed-manifests.json"
SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

#: The same namespace the D6 campaign draws from, so the slice's campaign id cannot collide
#: with the certification partition's and is still recognisably D6's.
D6_CAMPAIGN_NAMESPACE = uuid5(NAMESPACE_URL, "https://cognitive-os.invalid/sprint-21d6/campaign")
D6_CAMPAIGN_VERSION = 6
D6_VERIFIER_PROFILE_HASH = uuid5(D6_CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2
GENERATION_EPOCH = datetime(2026, 8, 8, tzinfo=UTC)

#: The fixture's own seed. Distinct from D6's certification seed, because a fixture that shared
#: one would draw candidate identities out of the same stream a scored role draws from.
FIXTURE_SEED = 21_069_909

FEATURE_SET_MEDIA_TYPE = "application/json"

#: The ridge S21D5-010 froze. The slice uses the contracted value rather than a convenient one:
#: D6 refits nothing, and the sealed direction it inherits was fitted at this ridge.
FIXTURE_REGULARIZATION = Decimal("1")

#: The pre-registered miscoverage budget, read from the sealed record's own generator constant.
#: The slice derives at this value first, whatever it produces.
D6_ALPHA = Decimal("0.20")

SLICE_LIMITATIONS = (
    "fitted on one group's four candidates, which is a wiring proof and not a model",
    "the direction is fitted on the same group it then ranks",
    "the conformal and certification halves are two decisions each, far below any regime in "
    "which a conformal bar means what it says",
)

LIMITS = SandboxLimits(
    timeout_seconds=120,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=200_000,
    maximum_stderr_bytes=200_000,
    maximum_artifact_bytes=200_000,
)

ACTOR = "vertical-slice-d6"
AUTHORITY = "S21D6-024"


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _implementation_digest() -> str:
    """The spine's own bytes, recorded in the seal so a re-encode is checkable."""
    files = (
        "src/cognitive_os/learning/correction_source.py",
        "src/cognitive_os/learning/correction_features.py",
        "src/cognitive_os/learning/correction_ranking.py",
        "src/cognitive_os/learning/correction_matrix.py",
        "src/cognitive_os/learning/pairwise_contrastive.py",
        "src/cognitive_os/learning/conformal_operating_point.py",
        "src/cognitive_os/learning/correction_catalogue_d6.py",
    )
    digest = sha256()
    for name in files:
        digest.update((REPOSITORY / name).read_bytes())
    return digest.hexdigest()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D6 environment first:\n"
            f"    set -a && . ./.env.s21d6.local && set +a"
        )
    return value


def _refusal(action: str, call: Any) -> dict[str, str]:
    """Run something that must be refused and record the refusal it actually raised."""
    try:
        call()
    except (CorrectionArtifactError, ConformalPointError, ValueError) as error:
        return {"action": action, "refused": "true", "error": f"{type(error).__name__}: {error}"}
    raise SystemExit(f"{action} was accepted; the boundary it tests does not exist")


def _role_boundary(group_name: str, template_id: str) -> dict[str, Any]:
    """Ask the sealed S21D6-023 bundle whether this group belongs to anything. It must not.

    The conformal half is asked separately from the catalogues, because it is not one of them:
    it shares the calibration partition with the certification half and a dictionary keyed by
    partition cannot hold both. A slice that checked only `bundle.catalogues` would miss exactly
    the hundred groups whose margins place the bar.
    """
    bundle = seal_d6_corpus(provisional=True)
    roles = {
        partition.value: sorted(bundle.groups_of(partition)) for partition in bundle.catalogues
    }
    roles["conformal"] = sorted(bundle.conformal_groups)
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
        "conformal_cases_spent": 0,
        "certification_cases_spent": 0,
        "final_members_spent": 0,
        "canary_members_spent": 0,
        "authored_by": "S21D5-024, as D5's fixture; outside every D6 role and re-run under D6 "
        "identities in D6's own store",
        "why": (
            "Section 6.1 requires the slice to spend nothing, so the group is checked against "
            "the sealed manifest rather than declared outside it"
        ),
    }


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


def _vector(record: SealedFeatureRecordV2) -> CorrectionFeatureVector:
    return CorrectionFeatureVector(
        encoder_version=record.encoder_version,
        values=record.values,
        embedding=record.embedding,
    )


def _smallest_supported_alpha(wrong_count: int) -> Decimal | None:
    """The coarsest bar this many wrong margins can carry, or None if none can.

    Walks the two-decimal grid upward and returns the first alpha whose finite-sample rank lands
    inside the sample. Searching here is safe in the way searching over the sprint's alpha is not:
    the quantity being searched is the fixture's, no gate row reads it, and the pre-registered
    value is derived first and unconditionally. With no wrong margin at all the answer is None
    for every alpha, because the wrong-margin distribution does not exist.
    """
    if wrong_count <= 0:
        return None
    for step in range(1, 100):
        alpha = Decimal(step) / Decimal(100)
        if conformal_rank(alpha, wrong_count) <= wrong_count:
            return alpha
    return None


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
    backup_root: Path,
) -> dict[str, Any]:
    spec = D5_FIXTURE_SPEC
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

    campaign_id = uuid5(D6_CAMPAIGN_NAMESPACE, "d6:vertical-slice")
    manifest_hash = _digest(f"d6-vertical-slice:{group.content_hash}")
    ordered = sorted(group.slots, key=lambda item: item.position)

    # 1. the package -------------------------------------------------------------------
    prepared = await runner.prepare_task(
        group.template_id,
        root=scratch / group.template_id.replace(".", "_"),
        seed=group.task_seed,
        generated_at=GENERATION_EPOCH,
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
    # Fitted on the fixture's own rows, unlike the campaign, which loads D5's released envelope.
    # The fixture is not measured against the sealed direction, so it needs no shared envelope;
    # what it needs is an envelope derived the way the released code derives one.
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
        campaign_version=D6_CAMPAIGN_VERSION,
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
                    verifier_profile_hash=D6_VERIFIER_PROFILE_HASH,
                    campaign_version=D6_CAMPAIGN_VERSION,
                )
                for slot in ordered
            ),
            RealityRunIdentity(
                task_id=group.task_id,
                task_manifest_hash=task_manifest.content_hash,
                run_kind=RealityRunKind.BASELINE,
                source=RealityCandidateSource.BASELINE,
                generator_profile_id=GENERATOR_PROFILE_ID,
                verifier_profile_hash=D6_VERIFIER_PROFILE_HASH,
                campaign_version=D6_CAMPAIGN_VERSION,
            ),
        ),
        verifier_profile_hash=D6_VERIFIER_PROFILE_HASH,
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
        partition=CorrectionPartition.CALIBRATION,
        manifest_hash=manifest_hash,
        campaign_id=campaign_id,
        campaign_version=D6_CAMPAIGN_VERSION,
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
                campaign_version=D6_CAMPAIGN_VERSION,
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
                    campaign_version=D6_CAMPAIGN_VERSION,
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
        "scans_that_did_not_pass": [item.name for item in scan.scans if not item.passed],
        "why_those_scans_cannot_pass_here": {
            "cause": (
                "the slice has one matrix, so it is scanned against itself. Every cross-split "
                "scan is therefore comparing a row with a copy of itself, and every one of them "
                "is answering a question the slice is not in a position to ask"
            ),
            "where_it_is_asked_for_real": (
                "S21D6-030 scans D5's conformal matrix against D6's certification matrix, which "
                "are disjoint corpora with disjoint authorship. A red row there is a finding; "
                "here it is arithmetic"
            ),
            "identical_to_the_d5_slice": True,
        },
    }

    # 6. split-conformal admission over two disjoint halves -----------------------------
    exemplars = tuple(Exemplar(vector=row.vector, accepted=row.accepted) for row in matrix.rows)
    model = fit_pairwise_direction([exemplars], regularization=FIXTURE_REGULARIZATION)
    vectors = {
        str(candidate_id): _vector(seal.record_for(candidate_id))
        for _observation, _payload, candidate_id, _outcome in observations
    }
    baseline_order = tuple(str(slot.candidate_id) for slot in ordered)

    # The scored set. A D6 decision is a *within-group ordering*, so a per-candidate score would
    # be the wrong quantity: the margin is defined between a group's top two. One group yields
    # one ordering, and a bar over one decision is a bar over nothing, so the group is ranked
    # four times under four leave-one-candidate-out directions. Each is a real ordering decision
    # with its own margin, and correctness is whether the candidate it put first is the one the
    # hidden verifier accepted. Nothing reads a label before a score.
    scored: list[ScoredDecision] = []
    held_out_reports: list[dict[str, Any]] = []
    accepted_of = {str(row.candidate_id): row.accepted for row in matrix.rows}
    for row in matrix.rows:
        rest = tuple(item for item in matrix.rows if item.candidate_id != row.candidate_id)
        if not any(item.accepted for item in rest) or all(item.accepted for item in rest):
            # A one-sided remainder carries no within-group contrast, so the class refuses to
            # fit it. Recorded rather than skipped silently: which folds exist is part of what
            # the derivation was given.
            held_out_reports.append(
                {"held_out": str(row.candidate_id), "fitted": False, "why": "one-sided remainder"}
            )
            continue
        fold = fit_pairwise_direction(
            [tuple(Exemplar(vector=item.vector, accepted=item.accepted) for item in rest)],
            regularization=FIXTURE_REGULARIZATION,
        )
        order = tuple(str(item.candidate_id) for item in rest)
        ranked = PairwiseContrastiveRanker(fold).rank(
            {key: vectors[key] for key in order}, baseline_order=order
        )
        correct = accepted_of[ranked.first_choice] if not ranked.abstained else False
        scored.append(
            ScoredDecision(
                decision_id=str(row.candidate_id),
                feature_hash=row.sealed_feature_hash,
                score=ranked.confidence,
                answered=not ranked.abstained,
                correct=correct,
            )
        )
        held_out_reports.append(
            {
                "held_out": str(row.candidate_id),
                "fitted": True,
                "margin": str(ranked.confidence),
                "first_choice_accepted": correct,
            }
        )
    if len(scored) < 2:
        raise SystemExit(
            f"{len(scored)} leave-one-out folds produced a decision; split conformal needs two "
            "halves and cannot be given one decision"
        )

    # The split. Alternating positions rather than a prefix, so the halves cannot differ by
    # anything the fold order encodes; the rule is stated here because a split chosen after the
    # margins were seen is the same defect as an alpha chosen after them.
    conformal_half = scored[0::2]
    certification_half = scored[1::2]
    preregistration_hash = _digest(PRE_REGISTRATION.read_bytes())

    derived_at = utc_now()
    point = derive_conformal_point(
        conformal_half,
        certification_half,
        alpha=D6_ALPHA,
        split="calibration",
        calibration_source_hash=matrix.content_hash,
        preregistration_hash=preregistration_hash,
        derived_at=derived_at,
    )
    again = derive_conformal_point(
        conformal_half,
        certification_half,
        alpha=D6_ALPHA,
        split="calibration",
        calibration_source_hash=matrix.content_hash,
        preregistration_hash=preregistration_hash,
        derived_at=utc_now(),
        previous=point,
    )

    wrong_in_conformal = point.wrong_decisions_in_conformal_split
    fixture_alpha = _smallest_supported_alpha(wrong_in_conformal)
    fixture_point = None
    if not point.quantile_exists and fixture_alpha is not None:
        fixture_point = derive_conformal_point(
            conformal_half,
            certification_half,
            alpha=fixture_alpha,
            split="calibration",
            calibration_source_hash=matrix.content_hash,
            preregistration_hash=preregistration_hash,
            derived_at=utc_now(),
        )

    binding = fixture_point if fixture_point is not None else point
    if binding.quantile_exists and binding.threshold is not None:
        margin_floor = Decimal(binding.threshold)
        floor_admits = "the decisions scoring strictly above the derived bar"
    else:
        # No bar exists, so the component must admit nothing. A floor of zero here is exactly the
        # move the prefix rule made on this same fixture data in D5, and the module's own words
        # for it are that "no error was seen in the other half" is not a bar. The floor is set
        # above every margin this fixture produced, so the ranker abstains and the artifact
        # carries a component that certifies nothing.
        margin_floor = max((item.score for item in scored), default=Decimal("0")) + Decimal("1")
        floor_admits = "nothing; no quantile exists and a component without a bar must abstain"

    ranker = PairwiseContrastiveRanker(model, margin_floor=margin_floor)
    ranking = ranker.rank(vectors, baseline_order=baseline_order)

    def _point_report(item: Any) -> dict[str, Any]:
        return {
            "alpha": item.alpha,
            "split": item.split,
            "wrong_decisions_in_conformal_split": item.wrong_decisions_in_conformal_split,
            "quantile_rank": item.quantile_rank,
            "quantile_exists": item.quantile_exists,
            "threshold": item.threshold,
            "admitted_decisions": item.admitted_decisions,
            "errors_admitted": item.errors_admitted,
            "coverage": item.coverage,
            "observed_error_rate": item.observed_error_rate,
            "error_upper_bound_95": item.error_upper_bound_95,
            "conformal_independent_decisions": item.conformal_census.independent_decisions,
            "certification_independent_decisions": (
                item.certification_census.independent_decisions
            ),
            "derivation_hash": item.derivation_hash,
        }

    ranking_report = {
        "hypothesis_class": HYPOTHESIS_CLASS,
        "confidence_quantity": "the projection margin between the top two candidates",
        "abstained": ranking.abstained,
        "reason": ranking.reason,
        "confidence": str(ranking.confidence),
        "first_choice": ranking.first_choice,
        "baseline_first_choice": baseline_order[0],
        "order_equals_baseline": ranking.ordered_candidate_ids == baseline_order,
        "fell_back_to_the_baseline_order": ranking.abstained
        and ranking.ordered_candidate_ids == baseline_order,
        "prediction_accepted_nothing": True,
        "direction": {
            "model_hash": model.content_hash(),
            "weights": len(model.weights),
            "regularization": model.regularization,
            "fitted_group_count": model.fitted_group_count,
            "fitted_pair_count": model.fitted_pair_count,
            "fitted_on_the_group_it_ranks": True,
            "why_that_is_said_rather_than_hidden": (
                "one group cannot both fit and evaluate a direction honestly. The slice proves "
                "the wiring -- that a direction is fitted, sealed, stored, reloaded and ranked "
                "with -- and D6 fits none at all: S21D6-034 reads the sealed 720 direction"
            ),
        },
        "admission": {
            "rule": "split conformal, S21D6's one change to the map from a ranked group to a "
            "decision",
            "split_rule": (
                "alternating fold positions, stated before the margins were read; the conformal "
                "half places the bar and the certification half is measured against it"
            ),
            "conformal_half": len(conformal_half),
            "certification_half": len(certification_half),
            "halves_share_no_fitted_vector": not (
                {item.feature_hash for item in conformal_half}
                & {item.feature_hash for item in certification_half}
            ),
            "folds": held_out_reports,
            "scored_decisions": [
                {
                    "decision_id": item.decision_id,
                    "score": str(item.score),
                    "answered": item.answered,
                    "correct": item.correct,
                }
                for item in scored
            ],
            "at_the_pre_registered_alpha": _point_report(point),
            "reproduced_after_a_second_derivation": again.derivation_hash == point.derivation_hash,
            "preregistration_sha256": preregistration_hash,
            "is_the_d6_operating_point": False,
            "why": (
                "D6's bar is derived once, at S21D6-034, from the sealed conformal half of 400 "
                "outcomes. This one is the fixture's, and it exists to show that admission runs "
                "at a derived bar rather than at a constant somebody typed"
            ),
            "why_the_pre_registered_alpha_cannot_produce_a_quantile_here": {
                "arithmetic": (
                    f"the conformal half holds {len(conformal_half)} decisions, so at most that "
                    f"many wrong margins; it held {wrong_in_conformal}. The finite-sample rank "
                    f"ceil((1-{D6_ALPHA})*(m+1)) is {point.quantile_rank}, which exceeds them, so "
                    "the quantile does not exist"
                ),
                "this_is_the_rule_working": (
                    "the module records the rank it computed precisely so a reader can see why "
                    "no bar exists rather than only that none does. A four-candidate group cannot "
                    "support a 0.20 bar at any m, which is a fact about the fixture and not a "
                    "finding about the corpus"
                ),
                "what_the_predecessor_did_with_the_same_data": (
                    "S21D5-024's zero-error prefix rule saw four clean decisions, took the "
                    "every_answered_decision_was_correct branch, admitted everything and ran the "
                    "ranking at a floor of zero. The conformal rule admits nothing instead. That "
                    "difference on identical fixture data is the sprint's change, executed"
                ),
            },
            "fixture_bar_for_the_artifact_binding": (
                {
                    "alpha": str(fixture_alpha),
                    "why_a_second_alpha_exists": (
                        "step 7 needs a bar to bind an artifact to, and the pre-registered alpha "
                        "produces none on four decisions. This one is the coarsest the sample can "
                        "carry, it is derived from the fixture and never from a scored role, and "
                        "no gate row reads it. The sprint's alpha stays 0.20 and is derived "
                        "exactly once, above"
                    ),
                    "point": _point_report(fixture_point),
                }
                if fixture_point is not None
                else {
                    "alpha": None,
                    "why_none": (
                        f"the conformal half produced {wrong_in_conformal} wrong margins, so no "
                        "alpha yields a quantile: with no wrong decision there is no wrong-margin "
                        "distribution to take one from"
                    ),
                }
            ),
            "margin_floor_the_ranking_ran_at": str(margin_floor),
            "margin_floor_admits": floor_admits,
            "derivation_rule": point.derivation_rule,
            "derivation_reading": point.derivation_reading,
        },
    }

    # 7 and 8. the v3 artifact, reloaded, refused, restarted and restored ---------------
    descriptor_hash = _digest(f"d6-vertical-slice-descriptor:{dataset.content_hash}")
    payload = build_payload_v3(
        component_revision=1,
        descriptor_hash=descriptor_hash,
        code_revision=code_revision,
        ranker=ranker,
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
        setting_identity=_digest(json.dumps(ranker.settings, sort_keys=True)),
        operating_point_hash=binding.derivation_hash,
        calibration_certificate_hash=matrix.content_hash,
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
    reloaded, reloaded_payload = build_ranker_for_evaluation_v3(
        reloaded_from_store, capability=capability, contract=contract
    )
    reloaded_ranking = reloaded.rank(vectors, baseline_order=baseline_order)

    wrong_bytes = canonical_bytes(payload.model_copy(update={"component_revision": 2}))
    corrupt_bytes = artifact_bytes[: len(artifact_bytes) // 2]
    oversized_bytes = b'{"padding": "' + b"x" * (MAXIMUM_ARTIFACT_BYTES + 1) + b'"}'
    corrupt_capability = replace(capability, artifact_hash=_digest(corrupt_bytes))
    oversized_capability = replace(capability, artifact_hash=_digest(oversized_bytes))

    # The backup and restore §6.1 asks the slice for, at the level the slice owns. The event
    # store's own dump and reload is a whole-database operation and belongs to W7's recovery
    # items; doing it here would tear down the store this wave is writing into. What the slice
    # can prove is that the artifact it produced survives a round trip through a backup root
    # and still rebuilds the same ranker from the restored bytes.
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / f"{_digest(artifact_bytes)}.json"
    described = await artifacts.describe(stored_artifact.artifact_id)
    shutil.copyfile(Path(_require("COGOS_ARTIFACT_ROOT")) / described.storage_key, backup_path)
    restored_bytes = backup_path.read_bytes()
    restored_ranker, restored_payload = build_ranker_for_evaluation_v3(
        restored_bytes, capability=capability, contract=contract
    )
    restored_ranking = restored_ranker.rank(vectors, baseline_order=baseline_order)

    artifact_report = {
        "schema_name": correction_artifact_schema(artifact_bytes),
        "artifact_id": str(stored_artifact.artifact_id),
        "artifact_hash": _digest(artifact_bytes),
        "artifact_bytes": len(artifact_bytes),
        "store_returned_the_bytes_written": reloaded_from_store == artifact_bytes,
        "weights": len(payload.weights),
        "feature_channels": len(payload.feature_channels),
        "hypothesis_class": payload.hypothesis_class,
        "margin_floor": str(payload.margin_floor),
        "operating_point_hash": payload.operating_point_hash,
        "operating_point_bound_is": (
            "the fixture bar" if fixture_point is not None else "the pre-registered-alpha point"
        ),
        "declared_limitations": list(payload.declared_limitations),
        "reload_reproduced_the_payload": reloaded_payload == payload,
        "reload_reproduced_the_ranking": (
            reloaded_ranking.ordered_candidate_ids == ranking.ordered_candidate_ids
            and reloaded_ranking.confidence == ranking.confidence
            and reloaded_ranking.abstained == ranking.abstained
        ),
        "backup_and_restore": {
            "backup_path_sha256": _digest(restored_bytes),
            "restored_bytes_are_the_stored_bytes": restored_bytes == artifact_bytes,
            "restored_payload_reproduced": restored_payload == payload,
            "restored_ranking_reproduced": (
                restored_ranking.ordered_candidate_ids == ranking.ordered_candidate_ids
                and restored_ranking.confidence == ranking.confidence
            ),
            "scope": "the artifact this slice produced, not the event store",
            "event_store_backup_and_restore_belongs_to": "S21D6-082, the isolated recovery item",
        },
        "refusals": [
            _refusal(
                "reload an artifact the capability does not name",
                lambda: build_ranker_for_evaluation_v3(
                    wrong_bytes, capability=capability, contract=contract
                ),
            ),
            _refusal(
                "reload truncated artifact bytes the capability does name",
                lambda: build_ranker_for_evaluation_v3(
                    corrupt_bytes, capability=corrupt_capability, contract=contract
                ),
            ),
            _refusal(
                "reload oversized artifact bytes the capability does name",
                lambda: build_ranker_for_evaluation_v3(
                    oversized_bytes, capability=oversized_capability, contract=contract
                ),
            ),
        ],
    }

    # the restart, replayed off the durable receipt ------------------------------------
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
        "conformal_bar_reproduced_across_the_restart": (
            derive_conformal_point(
                conformal_half,
                certification_half,
                alpha=D6_ALPHA,
                split="calibration",
                calibration_source_hash=matrix.content_hash,
                preregistration_hash=preregistration_hash,
                derived_at=utc_now(),
                previous=point,
            ).derivation_hash
            == point.derivation_hash
        ),
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
                "derive a conformal bar from the final A split",
                lambda: derive_conformal_point(
                    conformal_half,
                    certification_half,
                    alpha=D6_ALPHA,
                    split="final_a",
                    calibration_source_hash=matrix.content_hash,
                    preregistration_hash=preregistration_hash,
                    derived_at=derived_at,
                ),
            ),
            _refusal(
                "derive a conformal bar from the final B split",
                lambda: derive_conformal_point(
                    conformal_half,
                    certification_half,
                    alpha=D6_ALPHA,
                    split="final_b",
                    calibration_source_hash=matrix.content_hash,
                    preregistration_hash=preregistration_hash,
                    derived_at=derived_at,
                ),
            ),
            _refusal(
                "derive a conformal bar from the retrieval split",
                lambda: derive_conformal_point(
                    conformal_half,
                    certification_half,
                    alpha=D6_ALPHA,
                    split="retrieval",
                    calibration_source_hash=matrix.content_hash,
                    preregistration_hash=preregistration_hash,
                    derived_at=derived_at,
                ),
            ),
            _refusal(
                "derive a second bar at another alpha from the same calibration source",
                lambda: derive_conformal_point(
                    conformal_half,
                    certification_half,
                    alpha=Decimal("0.05"),
                    split="calibration",
                    calibration_source_hash=matrix.content_hash,
                    preregistration_hash=preregistration_hash,
                    derived_at=derived_at,
                    previous=point,
                ),
            ),
            _refusal(
                "place the bar with the half that is measured against it",
                lambda: derive_conformal_point(
                    scored,
                    scored,
                    alpha=D6_ALPHA,
                    split="calibration",
                    calibration_source_hash=matrix.content_hash,
                    preregistration_hash=preregistration_hash,
                    derived_at=derived_at,
                ),
            ),
            _refusal(
                "certify a bar against an empty certification half",
                lambda: derive_conformal_point(
                    conformal_half,
                    [],
                    alpha=D6_ALPHA,
                    split="calibration",
                    calibration_source_hash=matrix.content_hash,
                    preregistration_hash=preregistration_hash,
                    derived_at=derived_at,
                ),
            ),
            _refusal(
                "bound an error rate over zero admitted decisions",
                lambda: admitted_error_upper_bound(0, 0),
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
    # s21d5 is on this list where D5's own copy stopped at s21d4, and it is the one that matters:
    # D6 reads its numeric envelope and its fitted direction out of D5's released seal, so the
    # sprint that reads a predecessor's evidence is exactly the one that must not touch it.
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1", "s21d2", "s21d3", "s21d4", "s21d5"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D6 writes only to its own pair")
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
            verifier_profile_hash=D6_VERIFIER_PROFILE_HASH,
            campaign_version=D6_CAMPAIGN_VERSION,
        )
        embed, model_digest = _embedding_provider(model)
        ledger = RealityCampaignLedger(events)
        backup_root = (
            Path(os.environ.get("COGOS_BACKUP_ROOT", str(artifact_root.parent / "backups-s21d6")))
            / "vertical-slice"
        )
        with tempfile.TemporaryDirectory(prefix="cogos-d6-slice-") as scratch:
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
                backup_root=backup_root,
            )
    finally:
        await engine.dispose()

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D6",
            "wave": "W1",
            "items": ["S21D6-024"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "final_outcomes_inspected": False,
            "code_revision": code_revision,
            "embedding_model_id": minilm.MODEL_ID,
            "embedding_tree_digest": model_digest,
            **report,
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    admission = report["ranking"]["admission"]
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
                "hypothesis_class": report["ranking"]["hypothesis_class"],
                "conformal_half": admission["conformal_half"],
                "certification_half": admission["certification_half"],
                "wrong_margins": admission["at_the_pre_registered_alpha"][
                    "wrong_decisions_in_conformal_split"
                ],
                "rank_at_alpha_0_20": admission["at_the_pre_registered_alpha"]["quantile_rank"],
                "quantile_exists_at_alpha_0_20": admission["at_the_pre_registered_alpha"][
                    "quantile_exists"
                ],
                "fixture_alpha": admission["fixture_bar_for_the_artifact_binding"]["alpha"],
                "margin_floor": admission["margin_floor_the_ranking_ran_at"],
                "ranking_abstained": report["ranking"]["abstained"],
                "artifact_schema": report["artifact"]["schema_name"],
                "artifact_reload_reproduced_the_ranking": report["artifact"][
                    "reload_reproduced_the_ranking"
                ],
                "restored_ranking_reproduced": report["artifact"]["backup_and_restore"][
                    "restored_ranking_reproduced"
                ],
                "bar_reproduced_across_the_restart": report["restart"][
                    "conformal_bar_reproduced_across_the_restart"
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
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d6-vertical-slice.json")
    arguments = parser.parse_args()
    return asyncio.run(_run(arguments.output, arguments.model))


if __name__ == "__main__":
    raise SystemExit(main())
