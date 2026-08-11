#!/usr/bin/env python3
"""S21D7-025 and S21D7-026. Seal every feature before any container, then run one campaign.

The order is the evidence. If the encoder runs after the verifier, the features have seen the
label and every number downstream is a number about a leak. So this command does one thing and
stops: it materialises the certification packages, encodes their candidates under the frozen
local model, and seals one partition-level record — and it refuses to start a container, which is
what makes "before" checkable rather than asserted.

Two things differ from D5, and both follow from what D6 is.

*One partition, not two.* D6 refits nothing. The direction it will score with was fitted on D5's
720 fitting rows and sealed; re-executing that pool would produce new outcomes for a model that
is not going to move. The only campaign here is the certification half.

*The numeric bounds are D5's, loaded rather than fitted.* This is the part that would be easy to
get wrong and impossible to see afterwards. The conformal bar is placed by margins from D5's
sealed calibration matrix and applied to margins encoded here, and two sets of margins are only
comparable if the same clip-and-scale parameters produced them. Fitting bounds on D6's own rows
would silently rescale this half against a different envelope, and every feature name would still
be right. So the bounds come out of D5's released training seal, by artifact identity, read-only,
and the record says where they came from.

Storage is the isolated D6 pair from S21D6-002 (`COGOS_DATABASE_URL`, `COGOS_ARTIFACT_ROOT`).
No predecessor store is written and no learned observation is written by the seal stage: sealing
is not measuring.

    set -a && . ./.env.s21d7.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d7.py \
        --model /home/palkouser/projekt/cognitive-os-data/models/all-MiniLM-L6-v2
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d7.py --stage execute
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d7.py --stage snapshot

`--provisional` seals and executes an unfinished corpus so the chain can be exercised before the
hundredth group exists. Every record it writes carries the flag, and a provisional record may
never reach a gate row.

`--role final` is W3's, added when the selection passed. It seals and executes the two carried
final roles — 30 groups and 120 outcomes each, unopened for five sprints — into records of their
own, so W1's certification seal is never rewritten. It refuses to start unless
`sprint-21d7-learner-selection.json` ends `1_select`, because a flag that spends sixty carried
groups should not be one typo away from spending them on a stopped sprint. The default role
behaves exactly as W1 ran it.

    set -a && . ./.env.s21d7.measured.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d7.py --role final \
        --model /home/palkouser/projekt/cognitive-os-data/models/all-MiniLM-L6-v2
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d7.py --role final \
        --stage execute --partition final_a
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d7.py --role final \
        --stage execute --partition final_b

`--role canary` is W3's second one, and it exists for condition 25 rather than for a measurement.
The canary role is the five groups the runtime routes to a newly activated component, and the
condition asks that every learned-first correction on that subset runs the hidden verifier. That
is only checkable if the subset actually executes, so this role seals and runs it under the same
label-all mechanism every other role uses, and `scripts/lifecycle_d7.py` reads the outcomes back
to derive what the sequencer did. It refuses without the same `1_select` pass the final roles
need: five groups reserved for an activation must not be spent by a sprint that has none.

    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d7.py --role canary \
        --model /home/palkouser/projekt/cognitive-os-data/models/all-MiniLM-L6-v2
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d7.py --role canary \
        --stage execute --partition canary
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
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
    count_outcomes,
)
from cognitive_os.application.services.reality_campaign_runner import (  # noqa: E402
    RealityCampaignRunner,
)
from cognitive_os.coding import reality_candidates  # noqa: E402
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder  # noqa: E402
from cognitive_os.coding.reality_tasks import GENERATOR_PROFILE_ID  # noqa: E402
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.learned import CorpusRole, ProvenanceClass  # noqa: E402
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
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    FITTED_RELATIONAL_CHANNELS,
    HYPOTHESIS_CLASS,
    relational_numbers,
)
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    FITTED_FEATURE_V2_ALLOWLIST,
)
from cognitive_os.learning.correction_catalogue import (  # noqa: E402
    CatalogueGroup,
    campaign_manifest_from_groups,
)
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus  # noqa: E402
from cognitive_os.learning.correction_catalogue_d7 import seal_d7_corpus  # noqa: E402
from cognitive_os.learning.correction_features import (  # noqa: E402
    FITTED_FEATURE_V2_SCALARS,
    PendingFeatureV2,
    SealedFeatureRecordSetV2,
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
    NumericBoundsV2,
)
from cognitive_os.learning.repair_containment import (  # noqa: E402
    REPAIR_CONTAINMENT_CHANNEL,
)
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d7-pre-registration.json"
SEALED_MANIFESTS = EVIDENCE / "sprint-21d7-sealed-manifests.json"
SEPARATION = EVIDENCE / "sprint-21d7-corpus-separation.json"
SEAL_RECORD = EVIDENCE / "sprint-21d7-feature-seals.json"
SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

#: Fixed forever: it is what makes a resumed D5 campaign the same campaign.
D7_CAMPAIGN_NAMESPACE = uuid5(NAMESPACE_URL, "https://cognitive-os.invalid/sprint-21d7/campaign")
D7_CAMPAIGN_VERSION = 6
D7_VERIFIER_PROFILE_HASH = uuid5(D7_CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2

#: Task generation is a pure function of the template, the seed and this constant.
GENERATION_EPOCH = datetime(2026, 8, 8, tzinfo=UTC)

FEATURE_SET_MEDIA_TYPE = "application/json"

#: S21D7-026 names one item for both partitions, and each run writes its own record, or the
#: second would overwrite the first campaign's.
CAMPAIGN_RECORD = {
    CorrectionPartition.CALIBRATION: EVIDENCE / "sprint-21d7-certification-campaign.json",
    CorrectionPartition.FINAL_A: EVIDENCE / "sprint-21d7-final-a-campaign.json",
    CorrectionPartition.FINAL_B: EVIDENCE / "sprint-21d7-final-b-campaign.json",
    CorrectionPartition.CANARY: EVIDENCE / "sprint-21d7-canary-campaign.json",
}

#: W3 only, and only after a pass through §2.3. The final roles have been carried unopened for
#: five sprints; `--role final` is the one switch that opens them, it seals into a record of its
#: own so W1's seal is never rewritten, and it refuses to run unless the selection record says
#: `1_select`. The default role is `certification`, whose behaviour is exactly W1's.
FINAL_SEAL_RECORD = EVIDENCE / "sprint-21d7-final-feature-seals.json"
LEARNER_SELECTION = EVIDENCE / "sprint-21d7-learner-selection.json"
_FINAL_ORDER: tuple[CorrectionPartition, ...] = (
    CorrectionPartition.FINAL_A,
    CorrectionPartition.FINAL_B,
)

#: W3's other opening switch. The canary role is not a measurement half: it is the subset the
#: runtime routes to a component that has just been activated, and condition 25 asks that every
#: learned-first correction on it runs the hidden verifier. A subset that never executes cannot
#: answer that, so this role seals and runs the five groups under the same label-all mechanism,
#: into a record of its own. Gated on the same `1_select` pass the final roles are gated on.
CANARY_SEAL_RECORD = EVIDENCE / "sprint-21d7-canary-feature-seals.json"
_CANARY_ORDER: tuple[CorrectionPartition, ...] = (CorrectionPartition.CANARY,)

#: The roles that spend a carried, once-openable partition, and are therefore refused unless the
#: selection ends `1_select`.
GATED_ROLES = frozenset({"final", "canary"})

ROLES: dict[str, tuple[tuple[CorrectionPartition, ...], Path]] = {}

SNAPSHOT_RECORD = EVIDENCE / "sprint-21d7-snapshots.json"
VERTICAL_SLICE = EVIDENCE / "sprint-21d7-vertical-slice.json"

ACTOR = "reality-campaign-d7"
AUTHORITY = "S21D7-026"

#: The partitions the default role opens, in the order it opens them. Canary stays closed unless
#: `--role canary` is given and final A and B stay closed unless `--role final` is; W3 gives each
#: once, and only after a pass through the amended §2.3.
#: One partition. D6 refits nothing, so there is no fitting campaign to run: the direction was
#: fitted on D5's pool and sealed, and re-executing that pool would produce new outcomes for a
#: model that cannot move.
_ORDER: tuple[CorrectionPartition, ...] = (CorrectionPartition.CALIBRATION,)

ROLES.update(
    {
        "certification": (_ORDER, SEAL_RECORD),
        "final": (_FINAL_ORDER, FINAL_SEAL_RECORD),
        "canary": (_CANARY_ORDER, CANARY_SEAL_RECORD),
    }
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

_EMBED_BATCH = 64


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    """The convention, unchanged since D4: the bytes hashed are the bytes written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _implementation_digest() -> str:
    """The v2 spine's own bytes, recorded in every seal so a re-encode is checkable."""
    files = (
        "src/cognitive_os/learning/correction_source.py",
        "src/cognitive_os/learning/correction_features.py",
        "src/cognitive_os/learning/correction_ranking.py",
        "src/cognitive_os/learning/correction_matrix.py",
        "src/cognitive_os/learning/correction_catalogue_d7.py",
        # The two modules the v3 relational assembly is computed by. A seal that recorded only
        # the v2 spine's bytes would leave the half of the representation D7 fits on unrecorded.
        "src/cognitive_os/learning/repair_containment.py",
        "src/cognitive_os/learning/containment_contrastive.py",
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
            f"    set -a && . ./.env.s21d7.local && set +a"
        )
    return value


#: Every store a predecessor wrote. Two of them are on the list for a reason the others are not:
#: D7 reads its numeric envelope out of D5's released seal and its whole bar-setting half out of
#: D6's, so a D7 run that opened either pair for writing could move the bytes the conformal bar
#: is computed from. The sprint that reads a predecessor's evidence is exactly the sprint that
#: must not be able to touch it. `s21d6` covers both of D6's pairs, the trial one and the
#: `-measured` one W0-F1 found — the second is where D6's certification bytes actually live.
FORBIDDEN_STORES = (
    "cognitive_os_dev",
    "s21c3",
    "s21d1",
    "s21d2",
    "s21d3",
    "s21d4",
    "s21d5",
    "s21d6",
)


def _isolated_pair() -> tuple[str, Path]:
    """The database and artifact root, refused unless both are D6's own."""
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in FORBIDDEN_STORES:
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D6 writes only to its own pair")
    if artifact_root.name == "artifacts":
        raise SystemExit("refusing to run against the inconsistent development pair")
    return database_url, artifact_root


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


async def _embed_all(embed: Any, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
    vectors: list[tuple[float, ...]] = []
    for start in range(0, len(texts), _EMBED_BATCH):
        vectors.extend(await embed.embed_documents(texts[start : start + _EMBED_BATCH]))
    return tuple(vectors)


class _Partition:
    """One role's encoded state, before any outcome exists for it."""

    def __init__(self, partition: CorrectionPartition, groups: tuple[CatalogueGroup, ...]) -> None:
        self.partition = partition
        self.groups = groups
        self.campaign_id = uuid5(D7_CAMPAIGN_NAMESPACE, f"d7:{partition.value}")
        self.manifest_hash: str = ""
        self.bundles: dict[str, str] = {}
        self.task_manifest_hashes: dict[str, str] = {}
        self.pending: list[PendingFeatureV2] = []
        self.rows: list[dict[str, float]] = []
        self.sources: dict[str, str] = {}
        #: The module under repair, per group. The v2 encoder never needs it -- every v2 channel
        #: is a property of one candidate -- but the containment share is a *relation* between a
        #: candidate's repair and its siblings', and a repair is only defined against a baseline.
        self.baselines: dict[str, str] = {}
        self.slot_order: dict[str, tuple[str, ...]] = {}
        self.seal: SealedFeatureRecordSetV2 | None = None
        self.seal_artifact: UUID | None = None
        self.relational: dict[str, Any] | None = None
        self.relational_artifact: UUID | None = None


async def _encode(
    partition: _Partition, *, runner: RealityCampaignRunner, embed: Any, scratch: Path
) -> None:
    """Materialise every package and encode every candidate. No container runs."""
    windows: dict[str, tuple[str, ...]] = {}
    inputs: list[tuple[UUID, UUID, str, str]] = []

    for index, group in enumerate(partition.groups, start=1):
        print(
            f"[encode {partition.partition.value} {index}/{len(partition.groups)}] "
            f"{group.template_id}",
            file=sys.stderr,
        )
        prepared = await runner.prepare_task(
            group.template_id,
            root=scratch / partition.partition.value / group.template_id.replace(".", "_"),
            seed=group.task_seed,
            generated_at=GENERATION_EPOCH,
            bundle_artifact=None,
        )
        if prepared.generated.manifest.task_id != group.task_id:
            raise SystemExit(
                f"{group.template_id} generated task {prepared.generated.manifest.task_id}, but "
                f"the sealed catalogue names {group.task_id}"
            )
        partition.bundles[group.template_id] = str(prepared.bundle_artifact.artifact_id)
        partition.task_manifest_hashes[group.template_id] = prepared.generated.manifest.content_hash
        partition.baselines[group.repository_group] = reality_candidates.baseline_source(
            prepared.generated.manifest
        )
        partition.slot_order[group.repository_group] = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda item: item.position)
        )
        for slot in sorted(group.slots, key=lambda item: item.position):
            body = reality_candidates.candidate_source(
                prepared.generated.manifest, RealityCandidateStrategy(slot.recipe)
            )
            windows[str(slot.candidate_id)] = canonical_embedding_windows(body)
            partition.sources[str(slot.candidate_id)] = body
            inputs.append((slot.candidate_id, group.task_id, group.repository_group, body))

    keys = sorted(windows)
    flat = tuple(text for key in keys for text in windows[key])
    produced = await _embed_all(embed, flat)
    embedded: dict[str, tuple[float, ...]] = {}
    cursor = 0
    for key in keys:
        count = len(windows[key])
        embedded[key] = pool_canonical_embedding(produced[cursor : cursor + count])
        cursor += count

    for candidate_id, task_id, group_name, body in inputs:
        embedding = embedded[str(candidate_id)]
        partition.rows.append(
            raw_numeric_row_v2(
                feature_input_v2(
                    candidate_source=body, canonical_candidate_source_embedding=embedding
                )
            )
        )
        partition.pending.append(
            PendingFeatureV2(
                candidate_id=candidate_id,
                task_id=task_id,
                repository_group=group_name,
                candidate_source=body,
                canonical_candidate_source_embedding=embedding,
            )
        )


# ------------------------------------------------------------- the v3 relational assembly


def _relational_assembly(
    partition: _Partition,
    seal: SealedFeatureRecordSetV2,
    *,
    code_revision: str,
    sealed_at: datetime,
) -> dict[str, Any]:
    """Section 4.2: the seven relational channels, assembled beside the v2 seal.

    This is the one thing D7's campaign does that no predecessor's did, and it is deliberately
    an *assembly* rather than an encoding. Six of the seven channels are the sealed v2 scalars,
    read out of the record above by name and unchanged; the seventh is derived from the group
    package -- the baseline module and the four candidate sources -- and touches no outcome, no
    label and no requirement text.

    Three properties the record has to make checkable, because the fit in W2 rests on all three:

    *The scalars are the sealed ones.* `relational_numbers` takes them by name and refuses a
    record whose names have drifted or been reordered, so a v2 seal that moved underneath this
    assembly fails here rather than feeding a direction numbers under the wrong names.

    *The share is a relation, not a property.* It is computed per group over the frozen slot
    order, so it cannot be assembled at all without the sibling candidates -- which is why the
    assembly lives here, beside the campaign that materialises them, and not in the encoder.

    *The embedding is present and unread.* The v2 seal carries all 384 channels because the
    surface scans and the census read them; not one of them reaches a v3 channel. Both facts are
    recorded, because section 4.2 asks for a seal that makes both checkable.
    """
    groups: list[dict[str, Any]] = []
    for group in sorted(partition.groups, key=lambda item: item.repository_group):
        order = partition.slot_order[group.repository_group]
        numbers = relational_numbers(
            {candidate_id: seal.record_for(UUID(candidate_id)).values for candidate_id in order},
            baseline_source=partition.baselines[group.repository_group],
            sources_by_candidate={
                candidate_id: partition.sources[candidate_id] for candidate_id in order
            },
        )
        groups.append(
            {
                "repository_group": group.repository_group,
                "template_id": group.template_id,
                "baseline_source_sha256": _digest(partition.baselines[group.repository_group]),
                "candidates": [
                    {
                        "candidate_id": candidate_id,
                        "position": position,
                        "channels": [
                            [name, float(value)]
                            for name, value in zip(
                                FITTED_RELATIONAL_CHANNELS, numbers[candidate_id], strict=True
                            )
                        ],
                        "sealed_feature_vector_hash": seal.record_for(
                            UUID(candidate_id)
                        ).feature_vector_hash,
                    }
                    for position, candidate_id in enumerate(order)
                ],
            }
        )

    shares = [row["channels"][-1][1] for group in groups for row in group["candidates"]]
    body = {
        "feature_contract": "CorrectionFeatureContractV3",
        "hypothesis_class_this_is_fitted_by": HYPOTHESIS_CLASS,
        "allowlist": list(FITTED_RELATIONAL_CHANNELS),
        "channels": len(FITTED_RELATIONAL_CHANNELS),
        "scalar_channels_read_from": "the v2 seal below, by name and unchanged",
        "derived_channel": REPAIR_CONTAINMENT_CHANNEL,
        "partition": partition.partition.value,
        "campaign_manifest_hash": partition.manifest_hash,
        "v2_feature_seal_hash": seal.content_hash,
        "code_revision": code_revision,
        "assembled_at": sealed_at.isoformat(),
        "groups": groups,
        "counts": {
            "groups": len(groups),
            "candidates": sum(len(group["candidates"]) for group in groups),
            "distinct_relational_vectors": len(
                {
                    tuple(value for _, value in row["channels"])
                    for group in groups
                    for row in group["candidates"]
                }
            ),
            "shares_outside_the_unit_interval": sum(
                1 for share in shares if share < 0.0 or share > 1.0
            ),
            "groups_where_every_share_is_zero": sum(
                1
                for group in groups
                if all(row["channels"][-1][1] == 0.0 for row in group["candidates"])
            ),
        },
        "embedding": {
            "sealed_channels": len(seal.records[0].embedding) if seal.records else 0,
            "read_by_any_v3_channel": False,
            "reading": (
                "the v2 seal beside this one carries all 384 embedding channels and every scan "
                "and census reads them; not one reaches a channel above. The section 4 "
                "measurement located the non-transferring part of the released class in exactly "
                "those channels, which is why this representation drops them"
            ),
        },
        "no_envelope_on_the_share": (
            "the share is in [0, 1] by construction, so it carries no clip-and-scale parameters "
            "and needs none; the six scalars carry D5's inherited envelope, unchanged"
        ),
        "chronology": {
            "outcomes_present_at_assembly_time": False,
            "containers_started_by_this_command": 0,
            "reading": (
                "the assembly reads the baseline module and the four candidate sources, all "
                "published to the solver before the sandbox runs, and no verifier has judged "
                "anything yet"
            ),
        },
    }
    body["content_hash"] = _digest(_canonical(body))
    return body


#: Two predecessors' released seals, for two different reasons. D5's training artifact carries
#: the clip-and-scale envelope every margin on both sides has to share. D6's certification
#: artifact carries the rows that *are* D7's bar-setting half. Named by identity rather than
#: searched for, so a store that no longer holds them fails loudly instead of falling back to a
#: fit.
D5_FEATURE_SEALS = EVIDENCE / "sprint-21d5-feature-seals.json"
D5_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d5")
D6_FEATURE_SEALS = EVIDENCE / "sprint-21d6-feature-seals.json"
D6_CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d6-certification-campaign.json"
D6_SNAPSHOTS = EVIDENCE / "sprint-21d6-snapshots.json"
#: Both of D6's roots, the `-measured` one first. D6 provisioned a second pair when its seal
#: stage refused a store whose campaign stream already carried events, and the measured campaign
#: -- the one whose rows place D7's bar -- ran in that pair. W0-F1 recorded that no released D6
#: record fingerprints it; looking only in the trial root would resolve the trial's bytes, or
#: nothing at all.
D6_ARTIFACT_ROOTS = (
    Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d6-measured"),
    Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d6"),
)


def _sealed_records(
    record: Path, roots: tuple[Path, ...], partition: str, *, sprint: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """One released feature seal, resolved out of its own artifact store, read-only.

    Resolved by the content hash the predecessor published, never by re-deriving: a
    re-derivation that happened to agree would be a coincidence rather than the same bytes. Two
    callers want this — the envelope the certification half is encoded under, and the
    bar-setting rows themselves — and a second copy of the resolution would be a second place
    for a fallback to creep back in.
    """
    released = json.loads(record.read_text(encoding="utf-8"))
    row = next(item for item in released["partitions"] if item["partition"] == partition)
    for root in roots:
        if not root.exists():
            continue
        matches = list(root.rglob(f"*{row['feature_seal_artifact_id']}*"))
        if not matches:
            # The store is content-addressed, so the artifact id is a database key, not a path.
            needle = (
                f'"partition":"{partition}"'.encode(),
                f'"partition": "{partition}"'.encode(),
            )
            matches = [
                path
                for path in root.rglob("*")
                if path.is_file()
                and len(path.name) == 64
                and any(item in path.read_bytes()[:4096] for item in needle)
            ]
        for path in matches:
            candidate = json.loads(path.read_text(encoding="utf-8"))
            if candidate.get("content_hash") == row["feature_seal_hash"]:
                return candidate, row
    raise SystemExit(
        f"{sprint}'s released {partition} feature seal does not resolve in "
        f"{[str(root) for root in roots]}; the evidence D7 inherits from it cannot be read, and "
        "re-deriving it here would replace a predecessor's sealed bytes with this sprint's "
        "opinion of them"
    )


def _d5_sealed_records(partition: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """D5's released seal, which is where the clip-and-scale envelope comes from."""
    return _sealed_records(D5_FEATURE_SEALS, (D5_ARTIFACT_ROOT,), partition, sprint="D5")


def _d6_sealed_records(partition: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """D6's released seal, whose certification rows are D7's bar-setting half."""
    return _sealed_records(D6_FEATURE_SEALS, D6_ARTIFACT_ROOTS, partition, sprint="D6")


def _inherited_bounds() -> tuple[NumericBoundsV2, dict[str, Any]]:
    """The six clip-and-scale parameters D5 fitted, read out of D5's released seal.

    Read-only, and by content hash rather than by re-deriving: a second fit that happened to
    agree would be a coincidence rather than the same envelope, and one that did not agree would
    rescale this half against a different one with every feature name still correct.
    """
    sealed, training = _d5_sealed_records("training")
    bounds = NumericBoundsV2(
        lower={name: float(value) for name, value in sealed["numeric_lower"]},
        upper={name: float(value) for name, value in sealed["numeric_upper"]},
    )
    return bounds, {
        "fitted_by": "sprint 21D5, on its 720 fitting rows",
        "fitted_here": False,
        "source_record": D5_FEATURE_SEALS.name,
        "source_feature_seal_hash": training["feature_seal_hash"],
        "source_artifact_id": training["feature_seal_artifact_id"],
        "why": (
            "the conformal bar is placed by margins from D5's sealed calibration matrix and "
            "applied to margins encoded here; two sets of margins are comparable only under one "
            "clip-and-scale envelope"
        ),
        "lower": bounds.canonical()["lower"],
        "upper": bounds.canonical()["upper"],
    }


def _envelope_proof(partition: _Partition) -> dict[str, Any]:
    """What the record hashes, and what the vector is allowed to contain.

    The provenance envelope binds candidate, group and partition identity to the canonical
    source and the vector. The vector itself must not: a feature carrying a candidate id would
    let the model recognise a candidate rather than judge it.

    The check is channel equality against the frozen allowlist, in order, and nothing cleverer.
    D4 recorded why a name heuristic is worse than none, and that reading is unchanged: what
    rules a verdict out is `reencodes_identically_from_source_alone`, not a word search.
    """
    seal = partition.seal
    if seal is None:  # pragma: no cover - the caller seals first
        raise SystemExit("an envelope proof needs a seal")
    scalar_names = {tuple(name for name, _ in record.values) for record in seal.records}
    return {
        "records": len(seal.records),
        "fitted_channels": len(FITTED_FEATURE_V2_ALLOWLIST),
        "scalar_channels": list(FITTED_FEATURE_V2_SCALARS),
        "channels_are_the_frozen_allowlist_in_order": (
            tuple(FITTED_FEATURE_V2_SCALARS)
            + tuple(f"canonical_candidate_source_embedding_{index:03d}" for index in range(384))
            == FITTED_FEATURE_V2_ALLOWLIST
        ),
        "every_record_carries_the_same_six_scalars_in_order": scalar_names
        == {tuple(FITTED_FEATURE_V2_SCALARS)},
        "embedding_dimension": seal.embedding_dimension,
        "envelope_binds": [
            "candidate_id",
            "task_id",
            "repository_group",
            "partition",
            "canonical_source_hash",
            "feature_vector_hash",
            "feature_contract_hash",
            "embedding_tree_digest",
            "code_revision",
        ],
        "distinct_feature_vector_hashes": len({r.feature_vector_hash for r in seal.records}),
        "distinct_canonical_source_hashes": len({r.canonical_source_hash for r in seal.records}),
    }


def _reencode_proof(partition: _Partition, bounds: NumericBoundsV2, code_revision: str) -> bool:
    """Re-encode every candidate from its source alone and demand the same vector hashes.

    This is what "no outcome enters the vector" means operationally: the sealed vector is
    reproducible from the candidate source and the bounds, with nothing else in the room.
    """
    seal = partition.seal
    if seal is None:  # pragma: no cover - the caller seals first
        raise SystemExit("a re-encode proof needs a seal")
    replayed = seal_feature_records_v2(
        partition.pending,
        partition=partition.partition.value,
        campaign_manifest_hash=partition.manifest_hash,
        bounds=bounds,
        embedding_model_id=seal.embedding_model_id,
        embedding_revision=seal.embedding_revision,
        embedding_tree_digest=seal.embedding_tree_digest,
        code_revision=code_revision,
        sealed_at=seal.sealed_at,
    )
    return replayed.content_hash == seal.content_hash


def _identity_proof(partitions: dict[CorrectionPartition, _Partition]) -> dict[str, Any]:
    """The 180 re-executed groups must carry D5 identities, not D4's.

    D5's fitting pool is D4's two partitions by *body*, and the contract calls for them to be
    re-executed under new run identities rather than read from a predecessor store. The seed
    reaches candidate identity, so this is checkable: not one of D5's candidate identities may
    equal a D4 one, and not one of D5's task identities may either. Asserting the seeds differ
    would only restate the input.
    """
    d4 = seal_d4_corpus()
    d4_candidates = {
        str(slot.candidate_id)
        for catalogue in d4.catalogues.values()
        for group in catalogue.groups
        for slot in group.slots
    }
    d4_tasks = {
        str(group.task_id) for catalogue in d4.catalogues.values() for group in catalogue.groups
    }
    d6_candidates = {
        str(slot.candidate_id)
        for partition in partitions.values()
        for group in partition.groups
        for slot in group.slots
    }
    d6_tasks = {
        str(group.task_id) for partition in partitions.values() for group in partition.groups
    }
    carried = {
        group.repository_group for partition in partitions.values() for group in partition.groups
    } & {
        group.repository_group for catalogue in d4.catalogues.values() for group in catalogue.groups
    }
    return {
        "groups_carried_by_body_from_d4": len(carried),
        "d6_candidate_identities": len(d6_candidates),
        "candidate_identities_shared_with_d5": sorted(d6_candidates & d4_candidates),
        "task_identities_shared_with_d5": sorted(d6_tasks & d4_tasks),
        "distinct": not (d6_candidates & d4_candidates) and not (d6_tasks & d4_tasks),
        "reading": (
            "the same 180 task packages under 720 identities that have never been run; a shared "
            "identity would let a D4 row be mistaken for a D5 one on resume"
        ),
    }


def _refusal(action: str, call: Any) -> dict[str, str]:
    """Run something that must be refused and record the refusal it actually raised."""
    try:
        call()
    except ValueError as error:
        return {"action": action, "refused": "true", "error": f"{type(error).__name__}: {error}"}
    raise SystemExit(f"{action} was accepted; the boundary it tests does not exist")


async def _stage_seal(
    output: Path,
    model: Path,
    limit: int | None,
    *,
    provisional: bool = False,
    order: tuple[CorrectionPartition, ...] = _ORDER,
) -> int:
    database_url, artifact_root = _isolated_pair()

    engine = create_postgres_engine(database_url)
    code_revision = _implementation_digest()
    contract = CorrectionFeatureContractV2()
    bundle = seal_d7_corpus(provisional=provisional)
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        coding_events = CodingEventService(events)
        runner = RealityCampaignRunner(
            sandbox=DockerSandbox(SANDBOX_IMAGE),
            artifacts=artifacts,
            recorder=CodingOutcomeRecorder(artifacts, coding_events, events),
            harvester=None,
            limits=LIMITS,
            image_digest=SANDBOX_IMAGE,
            verifier_profile_hash=D7_VERIFIER_PROFILE_HASH,
            campaign_version=D7_CAMPAIGN_VERSION,
        )
        embed, model_digest = _embedding_provider(model)

        partitions = {
            name: _Partition(name, bundle.catalogues[name].groups[:limit]) for name in order
        }
        for name in order:
            partitions[name].manifest_hash = bundle.catalogues[name].content_hash

        # Before anything is sealed: the campaign streams these partitions would write to
        # must be empty. A seal is only "pre-outcome" if there is no outcome for it to precede,
        # and an empty stream under the campaign id is what "no outcome" looks like durably.
        # `get_stream_version` answers None for a stream that does not exist yet. None reads
        # as "not looked up"; zero reads as "looked up and empty", which is the claim.
        stream_versions_before = {
            name: (await events.get_stream_version(partitions[name].campaign_id)) or 0
            for name in order
        }
        if any(stream_versions_before.values()):
            raise SystemExit(
                "a D5 campaign stream already carries events; this command seals before the "
                f"first container and cannot run against {stream_versions_before}"
            )

        bounds: NumericBoundsV2 | None = None
        bounds_provenance: dict[str, Any] = {}
        reports: list[dict[str, Any]] = []
        refusals: list[dict[str, str]] = []
        with tempfile.TemporaryDirectory(prefix="cogos-d7-seal-") as scratch:
            for name in order:
                partition = partitions[name]
                await _encode(partition, runner=runner, embed=embed, scratch=Path(scratch))
                # Loaded, never fitted. See the header: the bar is placed by D5's margins and
                # applied to these, and two sets of margins are comparable only under one
                # envelope. `_inherited_bounds` reads D5's released training seal by artifact
                # identity and refuses anything else.
                if bounds is None:
                    bounds, bounds_provenance = _inherited_bounds()
                sealed_at = utc_now()
                partition.seal = seal_feature_records_v2(
                    partition.pending,
                    partition=name.value,
                    campaign_manifest_hash=partition.manifest_hash,
                    bounds=bounds,
                    embedding_model_id=minilm.MODEL_ID,
                    embedding_revision=model_digest,
                    embedding_tree_digest=model_digest,
                    code_revision=code_revision,
                    sealed_at=sealed_at,
                )
                stored = await artifacts.put_bytes(
                    partition.seal.canonical_json().encode(), media_type=FEATURE_SET_MEDIA_TYPE
                )
                partition.seal_artifact = stored.artifact_id

                # Section 4.2: the v3 relational vector is assembled per group *beside* the v2
                # seal, from the sealed scalars and the group package, and sealed with the
                # campaign manifest hash and its own chronology proof.
                relational = _relational_assembly(
                    partition, partition.seal, code_revision=code_revision, sealed_at=sealed_at
                )
                relational_stored = await artifacts.put_bytes(
                    _canonical(relational), media_type=FEATURE_SET_MEDIA_TYPE
                )
                partition.relational = relational
                partition.relational_artifact = relational_stored.artifact_id

                refusals.append(
                    _refusal(
                        f"seal {name.value} again with an outcome already in hand",
                        lambda partition=partition, bounds=bounds: seal_feature_records_v2(
                            partition.pending,
                            partition=partition.partition.value,
                            campaign_manifest_hash=partition.manifest_hash,
                            bounds=bounds,
                            embedding_model_id=minilm.MODEL_ID,
                            embedding_revision=model_digest,
                            embedding_tree_digest=model_digest,
                            code_revision=code_revision,
                            sealed_at=utc_now(),
                            earliest_outcome_at=utc_now(),
                            outcomes_present=True,
                        ),
                    )
                )

                # Section 5.1's named seam, executed rather than asserted: the assembly takes
                # the six scalars by name, so a record whose names drifted must fail here.
                refusals.append(
                    _refusal(
                        "assemble a relational vector from drifted scalar names",
                        lambda partition=partition: relational_numbers(
                            {
                                candidate_id: tuple(
                                    ("drifted_" + name, value)
                                    for name, value in partition.seal.record_for(
                                        UUID(candidate_id)
                                    ).values
                                )
                                for candidate_id in partition.slot_order[
                                    sorted(partition.slot_order)[0]
                                ]
                            },
                            baseline_source=partition.baselines[sorted(partition.baselines)[0]],
                            sources_by_candidate={
                                candidate_id: partition.sources[candidate_id]
                                for candidate_id in partition.slot_order[
                                    sorted(partition.slot_order)[0]
                                ]
                            },
                        ),
                    )
                )

                seal = partition.seal
                replayed = SealedFeatureRecordSetV2.model_validate_json(seal.canonical_json())
                reports.append(
                    {
                        "partition": name.value,
                        "campaign_id": str(partition.campaign_id),
                        "campaign_manifest_hash": partition.manifest_hash,
                        "groups": len(partition.groups),
                        "feature_records": len(seal.records),
                        "feature_seal_hash": seal.content_hash,
                        "feature_seal_artifact_id": str(stored.artifact_id),
                        "feature_contract_hash": seal.feature_contract_hash,
                        "encoder_version": seal.encoder_version,
                        "normalizer_version": seal.normalizer_version,
                        "code_revision": seal.code_revision,
                        "embedding_model_id": seal.embedding_model_id,
                        "embedding_tree_digest": seal.embedding_tree_digest,
                        "chronology": {
                            "sealed_at": seal.sealed_at.isoformat(),
                            "outcomes_present_at_seal_time": seal.outcomes_present,
                            "campaign_stream_version_before_the_seal": stream_versions_before[name],
                            "containers_started_by_this_command": 0,
                            "reading": (
                                "the seal precedes the first container because no container has "
                                "run: the campaign stream is empty and this command starts none"
                            ),
                        },
                        "reserialises_identically": replayed.content_hash == seal.content_hash,
                        "stored_seal_time_preserved": replayed.sealed_at == seal.sealed_at,
                        "reencodes_identically_from_source_alone": _reencode_proof(
                            partition, bounds, code_revision
                        ),
                        "envelope": _envelope_proof(partition),
                        "bounds": bounds_provenance,
                        "bundle_artifacts": dict(sorted(partition.bundles.items())),
                        "task_manifest_hashes": dict(
                            sorted(partition.task_manifest_hashes.items())
                        ),
                        "member_hashes": sorted(
                            record.feature_vector_hash for record in seal.records
                        ),
                        "relational_assembly": {
                            "feature_contract": relational["feature_contract"],
                            "content_hash": relational["content_hash"],
                            "artifact_id": str(relational_stored.artifact_id),
                            "allowlist": relational["allowlist"],
                            "counts": relational["counts"],
                            "embedding_read_by_any_v3_channel": relational["embedding"][
                                "read_by_any_v3_channel"
                            ],
                            "chronology": relational["chronology"],
                        },
                    }
                )
    finally:
        await engine.dispose()

    total = sum(int(item["feature_records"]) for item in reports)
    families = Counter(
        group.family for partition in partitions.values() for group in partition.groups
    )
    identity = _identity_proof(partitions)
    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W1",
            "items": ["S21D7-025"],
            "provisional": provisional,
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "separation_sha256": _digest(SEPARATION.read_bytes()),
            "final_outcomes_inspected": False,
            "code_revision": code_revision,
            "feature_contract_hash": contract.content_hash,
            "relational_contract": {
                "name": "CorrectionFeatureContractV3",
                "frozen_in": "sprint-21d7-contracts.json, revision 7, S21D7-013",
                "channels": len(FITTED_RELATIONAL_CHANNELS),
                "assembled_beside_the_v2_seal": True,
                "reading": (
                    "the v2 seal is unchanged and complete; the assembly is a second, narrower "
                    "record over the same candidates, and the fit in W2 reads only that one"
                ),
            },
            "corpus_seal_hash": bundle.seal.content_hash,
            "counts": {
                "feature_records_sealed": total,
                "partitions_opened": [name.value for name in order],
                "candidate_slots_by_partition": {
                    name.value: len(partitions[name].pending) for name in order
                },
                "reading": (
                    "the certification half holds the candidate slots W1 executes and is the "
                    "only role that wave opens: the fitting pool is read through a sealed "
                    "direction rather than run, the conformal half through a sealed matrix, and "
                    "no final or canary partition is touched -- sealing one's features would be "
                    "the first step of opening it. W3's `--role final` is the one run that does "
                    "open them, after a pass, and it seals into a record of its own"
                )
                if CorrectionPartition.CALIBRATION in order
                else (
                    f"the two carried final roles, opened once by W3 under S21D7-038 with the "
                    f"{total} candidate slots they hold between them. The canary role stays "
                    "closed and no certification row is re-sealed"
                ),
                "slots_not_sealed_by_this_run": {
                    "fitting": 720,
                    "conformal": 400,
                    "canary": 20,
                    "final": 0 if CorrectionPartition.FINAL_A in order else 240,
                    "certification": 0 if CorrectionPartition.CALIBRATION in order else 400,
                },
                "family_distribution": dict(sorted(families.items())),
            },
            "run_identities": identity,
            "partitions": reports,
            "refusals": refusals,
            "containers_started": 0,
            "learned_observations_written": 0,
            "why_no_observation": (
                "sealing is not measuring. An observation exists once a verifier has judged a "
                "candidate, and no candidate has run"
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
                "feature_records_sealed": total,
                "partitions": {str(item["partition"]): item["feature_records"] for item in reports},
                "seals": {
                    str(item["partition"]): str(item["feature_seal_hash"])[:16] for item in reports
                },
                "distinct_vectors": {
                    str(item["partition"]): item["envelope"]["distinct_feature_vector_hashes"]
                    for item in reports
                },
                "relational_assembly": {
                    str(item["partition"]): {
                        "groups": item["relational_assembly"]["counts"]["groups"],
                        "distinct_relational_vectors": item["relational_assembly"]["counts"][
                            "distinct_relational_vectors"
                        ],
                        "content_hash": str(item["relational_assembly"]["content_hash"])[:16],
                    }
                    for item in reports
                },
                "run_identities_distinct_from_d4": identity["distinct"],
                "containers_started": 0,
                "refusals_executed": len(refusals),
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


# ------------------------------------------------------------------------------- S21D7-026


def _receipt_manifest(
    *,
    groups: tuple[CatalogueGroup, ...],
    partition: CorrectionPartition,
    campaign_id: UUID,
    seal: SealedFeatureRecordSetV2,
    manifest_hash: str,
    task_manifest_hashes: dict[str, str],
    bundles: dict[str, str],
) -> RealityCampaignReceiptManifestV3:
    """The durable receipt, bound at the seal's time rather than at execution's.

    `created_at` is the seal time on purpose: a receipt written when the containers start
    records what happened, and what this needs to record is what was planned before they did.
    """
    planned: list[RealityRunIdentity] = []
    for group in groups:
        manifest_hash_of_task = task_manifest_hashes[group.template_id]
        for slot in sorted(group.slots, key=lambda item: item.position):
            planned.append(
                RealityRunIdentity(
                    task_id=group.task_id,
                    task_manifest_hash=manifest_hash_of_task,
                    run_kind=RealityRunKind.CANDIDATE,
                    candidate_id=slot.candidate_id,
                    strategy=RealityCandidateStrategy(slot.recipe),
                    source=RealityCandidateSource.CURATED,
                    generator_profile_id=GENERATOR_PROFILE_ID,
                    verifier_profile_hash=D7_VERIFIER_PROFILE_HASH,
                    campaign_version=D7_CAMPAIGN_VERSION,
                )
            )
        planned.append(
            RealityRunIdentity(
                task_id=group.task_id,
                task_manifest_hash=manifest_hash_of_task,
                run_kind=RealityRunKind.BASELINE,
                source=RealityCandidateSource.BASELINE,
                generator_profile_id=GENERATOR_PROFILE_ID,
                verifier_profile_hash=D7_VERIFIER_PROFILE_HASH,
                campaign_version=D7_CAMPAIGN_VERSION,
            )
        )
    return RealityCampaignReceiptManifestV3(
        campaign_id=campaign_id,
        campaign_version=D7_CAMPAIGN_VERSION,
        planned_runs=tuple(planned),
        verifier_profile_hash=D7_VERIFIER_PROFILE_HASH,
        created_at=seal.sealed_at,
        partition=partition.value,
        mode="label_all",
        selection_manifest_hash=manifest_hash,
        feature_schema_hash=seal.feature_contract_hash,
        feature_seal_root_hash=seal.content_hash,
        receipt_tasks=tuple(
            RealityReceiptTaskV3(
                task_id=group.task_id,
                task_manifest_hash=task_manifest_hashes[group.template_id],
                bundle_id=UUID(bundles[group.template_id]),
                bundle_hash=_digest(bundles[group.template_id]),
                feature_seal_hash=seal.content_hash,
                candidate_order=tuple(
                    slot.candidate_id for slot in sorted(group.slots, key=lambda s: s.position)
                ),
                selected_member_hashes=tuple(
                    seal.record_for(slot.candidate_id).feature_vector_hash
                    for slot in sorted(group.slots, key=lambda s: s.position)
                ),
            )
            for group in groups
        ),
    )


async def _stage_execute(
    output: Path,
    partition: CorrectionPartition,
    limit: int | None,
    *,
    provisional: bool = False,
    seal_record: Path = SEAL_RECORD,
) -> int:
    """Run one partition under `label_all`, project role-bound, then replay off the receipt."""
    database_url, artifact_root = _isolated_pair()

    sealed = json.loads(seal_record.read_text(encoding="utf-8"))
    row = next(item for item in sealed["partitions"] if item["partition"] == partition.value)
    catalogue = seal_d7_corpus(provisional=provisional).catalogues[partition]
    groups = catalogue.groups[: limit or len(catalogue.groups)]

    engine = create_postgres_engine(database_url)
    contract = CorrectionFeatureContractV2()
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        coding_events = CodingEventService(events)
        repository = PostgresLearnedEvidenceRepository(engine)
        learned = LearnedEvidenceService(repository, events=LearnedEventService(events))
        ledger = RealityCampaignLedger(events)
        sequencer = CorrectionCandidateSequencer(coding_events)
        runner = RealityCampaignRunner(
            sandbox=DockerSandbox(SANDBOX_IMAGE),
            artifacts=artifacts,
            recorder=CodingOutcomeRecorder(artifacts, coding_events, events),
            harvester=None,
            limits=LIMITS,
            image_digest=SANDBOX_IMAGE,
            verifier_profile_hash=D7_VERIFIER_PROFILE_HASH,
            campaign_version=D7_CAMPAIGN_VERSION,
        )

        # The seal comes back out of the artifact store rather than being rebuilt. A campaign
        # that re-derives its seal would execute against whatever the encoder produces today.
        seal_bytes = await artifacts.get_bytes(UUID(row["feature_seal_artifact_id"]))
        seal = SealedFeatureRecordSetV2.model_validate_json(seal_bytes.decode())
        if seal.content_hash != row["feature_seal_hash"]:
            raise SystemExit(
                f"the stored feature seal hashes to {seal.content_hash}, not the "
                f"{row['feature_seal_hash']} S21D7-025 recorded"
            )

        campaign_id = uuid5(D7_CAMPAIGN_NAMESPACE, f"d7:{partition.value}")
        prepared_of = {}
        with tempfile.TemporaryDirectory(prefix="cogos-d7-run-") as scratch:
            for index, group in enumerate(groups, start=1):
                print(
                    f"[prepare {partition.value} {index}/{len(groups)}] {group.template_id}",
                    file=sys.stderr,
                )
                prepared = await runner.prepare_task(
                    group.template_id,
                    root=Path(scratch) / group.template_id.replace(".", "_"),
                    seed=group.task_seed,
                    generated_at=GENERATION_EPOCH,
                    bundle_artifact=await artifacts.describe(
                        UUID(row["bundle_artifacts"][group.template_id])
                    ),
                )
                recorded_hash = row["task_manifest_hashes"][group.template_id]
                if prepared.generated.manifest.content_hash != recorded_hash:
                    raise SystemExit(
                        f"{group.template_id}: the task manifest hashes to "
                        f"{prepared.generated.manifest.content_hash}, not the {recorded_hash} the "
                        "seal was bound to; every planned run identity would differ"
                    )
                prepared_of[group.template_id] = prepared

            receipt = _receipt_manifest(
                groups=groups,
                partition=partition,
                campaign_id=campaign_id,
                seal=seal,
                manifest_hash=row["campaign_manifest_hash"],
                task_manifest_hashes=row["task_manifest_hashes"],
                bundles=row["bundle_artifacts"],
            )
            manifest = campaign_manifest_from_groups(
                groups,
                partition=partition,
                manifest_hash=row["campaign_manifest_hash"],
                campaign_id=campaign_id,
                campaign_version=D7_CAMPAIGN_VERSION,
                feature_sealed_at=seal.sealed_at,
            )
            projector = CorrectionRankingObservationProjector(manifest)

            runs: dict[UUID, Any] = {}
            baselines: list[Any] = []
            observations: list[dict[str, Any]] = []
            sequences: list[dict[str, Any]] = []

            def _attempt(prepared: Any, recipe_of: dict[UUID, RealityCandidateStrategy]) -> Any:
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

                return attempt

            for index, group in enumerate(groups, start=1):
                print(
                    f"[run {partition.value} {index}/{len(groups)}] {group.template_id}",
                    file=sys.stderr,
                )
                prepared = prepared_of[group.template_id]
                ordered = sorted(group.slots, key=lambda item: item.position)
                recipe_of = {
                    slot.candidate_id: RealityCandidateStrategy(slot.recipe) for slot in ordered
                }
                baselines.append(await runner.run_baseline(prepared, completed={}))
                sequence = await sequencer.run_task(
                    campaign_id=campaign_id,
                    task_id=group.task_id,
                    partition=partition.value,
                    mode=SequenceMode.LABEL_ALL,
                    campaign_manifest_hash=receipt.content_hash,
                    baseline_order=tuple(slot.candidate_id for slot in ordered),
                    attempt=_attempt(prepared, recipe_of),
                )
                await sequencer.record(sequence, correlation_id=group.task_id)
                sequences.append(
                    {
                        "task_id": str(group.task_id),
                        "attempted": len(sequence.attempted_order),
                        "intentionally_unattempted": len(sequence.intentionally_unattempted),
                        "stop_reason": sequence.stop_reason,
                    }
                )
                for slot in ordered:
                    run = runs[slot.candidate_id]
                    stored = await learned.record_observation(
                        projector.project(
                            run.step.reference,
                            campaign_version=D7_CAMPAIGN_VERSION,
                            verifier_profile_hash=group.verifier_profile_hash,
                            usage_rights_verified=group.usage_rights_verified,
                        ),
                        correlation_id=run.step.reference.task_run_id,
                        actor=ACTOR,
                        authority=AUTHORITY,
                    )
                    observations.append(
                        {
                            "observation_id": str(stored.observation_id),
                            "candidate_id": str(slot.candidate_id),
                            "group": group.repository_group,
                            "task_id": str(group.task_id),
                            "accepted": run.step.reference.hidden_verification_passed,
                            "provenance_class": str(stored.provenance_class),
                            "verifier_status": stored.verifier_status,
                            "outcome_hash": run.step.reference.outcome_hash,
                            "payload_hash": stored.source_payload_hash,
                            "feature_vector_hash": seal.record_for(
                                slot.candidate_id
                            ).feature_vector_hash,
                        }
                    )

            # The replay. A second pass over the same identities that starts no container is
            # what "receipt-aware" means; asserting resumability without re-running proves the
            # ledger can be queried, not that the campaign can be resumed.
            references = [run.step.reference for run in runs.values()]
            task_run_ids = [item.task_run_id for item in references] + [
                run.step.reference.task_run_id for run in baselines
            ]
            recorded = dict(await ledger.completed_by_identity(task_run_ids))
            replayed: list[Any] = []
            for group in groups:
                prepared = prepared_of[group.template_id]
                replayed.append(await runner.run_baseline(prepared, completed=recorded))
                for slot in sorted(group.slots, key=lambda item: item.position):
                    replayed.append(
                        await runner.run_candidate(
                            prepared,
                            RealityCandidateStrategy(slot.recipe),
                            completed=recorded,
                            candidate_id=slot.candidate_id,
                        )
                    )
            resumed = await ledger.plan_resume_with_receipts(
                receipt, task_run_ids=task_run_ids, campaign_id=campaign_id
            )
    finally:
        await engine.dispose()

    count = count_outcomes(references)
    provenance = Counter(str(item["provenance_class"]) for item in observations)
    accepted_by_recipe: Counter[str] = Counter()
    by_recipe: Counter[str] = Counter()
    for reference in references:
        label = "" if reference.strategy is None else reference.strategy.value
        by_recipe[label] += 1
        if reference.hidden_verification_passed:
            accepted_by_recipe[label] += 1

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W1",
            "items": ["S21D7-026"],
            "provisional": provisional,
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "feature_seals_sha256": _digest(seal_record.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "final_outcomes_inspected": False,
            "partition": partition.value,
            "campaign_id": str(campaign_id),
            "campaign_manifest_hash": row["campaign_manifest_hash"],
            "receipt_manifest_hash": receipt.content_hash,
            "feature_seal_hash": seal.content_hash,
            "feature_seal_reloaded_from_the_artifact_store": True,
            "feature_contract_hash": contract.content_hash,
            "mode": "label_all",
            "execution": {
                "groups": len(groups),
                "candidate_runs": len(references),
                "baselines": len(baselines),
                "containers_started": len(references) + len(baselines),
                "unique_outcomes": count.unique,
                "duplicates_excluded": count.duplicates_excluded,
                "hidden_passed": count.passed,
                "hidden_failed": count.failed,
                "baselines_passing_hidden_verification": sum(
                    1 for run in baselines if run.hidden_passed
                ),
                "candidates_left_unattempted": sum(
                    int(item["intentionally_unattempted"]) for item in sequences
                ),
                "sequences_recorded": len(sequences),
                "stop_reasons": dict(Counter(str(item["stop_reason"]) for item in sequences)),
                "acceptance_by_recipe": {
                    name: round(accepted_by_recipe[name] / by_recipe[name], 4)
                    for name in sorted(by_recipe)
                },
                "every_outcome_follows_the_seal": all(
                    item.occurred_at > seal.sealed_at for item in references
                ),
            },
            "observations": {
                "recorded": len(observations),
                "provenance_counts": dict(sorted(provenance.items())),
                "real_governed_runs": provenance.get("ProvenanceClass.REAL_GOVERNED_RUN", 0)
                + provenance.get("real_governed_run", 0),
                "distinct_feature_vector_hashes": len(
                    {str(item["feature_vector_hash"]) for item in observations}
                ),
                "groups": len({str(item["group"]) for item in observations}),
            },
            "resume": {
                "run_identities_resolved_from_the_receipt": len(recorded),
                "runs_replayed": sum(1 for run in replayed if run.replayed),
                "containers_started_on_the_replay": sum(1 for run in replayed if not run.replayed),
                "receipt_is_resumable": resumed.is_resumable,
                "receipt_effective_remainder": [str(item) for item in resumed.effective_remainder],
            },
            "task_run_ids": sorted(str(item) for item in task_run_ids),
            "candidate_outcomes": observations,
            "sequences": sequences,
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
                "partition": partition.value,
                "groups": len(groups),
                "candidate_runs": len(references),
                "hidden_passed": count.passed,
                "baselines_passing_hidden": evidence["execution"][
                    "baselines_passing_hidden_verification"
                ],
                "real_governed_runs": evidence["observations"]["real_governed_runs"],
                "observations": len(observations),
                "containers_on_the_replay": evidence["resume"]["containers_started_on_the_replay"],
                "effective_remainder": len(evidence["resume"]["receipt_effective_remainder"]),
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


# ------------------------------------------------------------------------------- S21D6-030


def _selection(
    partition: CorrectionPartition,
    rows: list[dict[str, Any]],
    *,
    manifest_hash: str,
    split: str,
) -> ExplicitSelection:
    """A revision-3 explicit selection: exact members, exact hashes, one campaign.

    Explicit rather than a store query, and in D5 that is not a precaution. The D5 store holds
    more rows than these two datasets name -- the vertical slice and a smoke test put them
    there -- so "every observation on this surface" would build a dataset nobody can rebuild.
    """
    identifiers = tuple(str(row["observation_id"]) for row in rows)
    return ExplicitSelection(
        partition=partition.value,
        members=tuple((str(row["observation_id"]), str(row["payload_hash"])) for row in rows),
        groups={str(row["observation_id"]): str(row["group"]) for row in rows},
        splits={split: identifiers},
        allowed_provenance=ProvenanceClass.SELF_PLAY,
        identity_revision=3,
        campaign_identity=manifest_hash,
        feature_record_hashes={
            str(row["observation_id"]): str(row["feature_vector_hash"]) for row in rows
        },
        outcome_hashes={str(row["observation_id"]): str(row["outcome_hash"]) for row in rows},
        member_content_hashes={
            str(row["observation_id"]): _digest(
                f"{row['observation_id']}:{row['payload_hash']}:{row['outcome_hash']}"
            )
            for row in rows
        },
    )


def _fitted_matrix(
    *,
    split: str,
    partition: CorrectionPartition,
    rows: list[dict[str, Any]],
    seal: SealedFeatureRecordSetV2,
    outcomes: dict[UUID, Any],
) -> FittedMatrix:
    """The rows the scans read, rebuilt from the sealed records and the recorded outcomes.

    Neither half comes from the campaign report: the vectors come out of the seal the store
    holds and the labels out of the ledger. A matrix assembled from a report is a matrix that
    agrees with the report by construction.
    """
    fitted: list[FittedRow] = []
    for row in rows:
        candidate_id = UUID(str(row["candidate_id"]))
        record = seal.record_for(candidate_id)
        outcome = outcomes[candidate_id]
        fitted.append(
            FittedRow(
                candidate_id=candidate_id,
                task_id=UUID(str(row["task_id"])),
                group=str(row["group"]),
                partition=partition.value,
                vector=CorrectionFeatureVector(
                    encoder_version=record.encoder_version,
                    values=record.values,
                    embedding=record.embedding,
                ),
                accepted=outcome.hidden_verification_passed,
                sealed_at=seal.sealed_at,
                outcome_at=outcome.occurred_at,
                observation_id=UUID(str(row["observation_id"])),
                sealed_feature_hash=record.feature_vector_hash,
            )
        )
    return FittedMatrix(split=split, rows=tuple(fitted))


def _conformal_matrix() -> tuple[FittedMatrix, dict[str, Any]]:
    """D6's certification rows, rebuilt from its released bytes, as the half that places the bar.

    D7 executes one partition, so the pair the scans read cannot be a fitting and a calibration
    matrix out of one store. The pairing is the one the experiment is actually about: the
    bar-setting half against the certification half measured over it. A near-duplicate or a
    shared group across *that* boundary is what would break the exchangeability section 6 names
    as the risk the evidence cannot retire -- and D7's version of that risk is one authoring run
    wider than D6's, because D6's own certification corpus is now the bar-setting half.

    Rebuilt rather than re-executed: the vectors come out of D6's sealed certification record and
    the labels out of D6's released campaign record, both read-only from a pair D7 may not write.
    The reconstruction proves itself -- `canonical_line` serialises the scaled values, the
    embedding and the label and nothing else, so the matrix hash equals D6's published
    `calibration_matrix_hash` exactly when every vector and every label came back intact.

    The two timestamps are the one thing that cannot be rebuilt: D6's per-row outcome times live
    in D6's database, which this sprint does not open. They reach neither the hash nor any scan
    but the chronology one, so both are set to D6's seal time and the chronology of this half is
    *inherited* from D6's released campaign record rather than recomputed here. The record says
    so in as many words, because a scan that passes on substituted data is not a scan.
    """
    sealed, released_row = _d6_sealed_records("calibration")
    seal = SealedFeatureRecordSetV2.model_validate_json(json.dumps(sealed))
    campaign = json.loads(D6_CERTIFICATION_CAMPAIGN.read_text(encoding="utf-8"))
    if campaign["feature_seal_hash"] != released_row["feature_seal_hash"]:
        raise SystemExit(
            "D6's certification campaign ran against a different seal than the one its "
            "feature-seal record publishes; the bar-setting half cannot be rebuilt from two "
            "disagreeing records"
        )
    rows = tuple(
        FittedRow(
            candidate_id=UUID(str(row["candidate_id"])),
            task_id=UUID(str(row["task_id"])),
            group=str(row["group"]),
            partition="conformal",
            vector=CorrectionFeatureVector(
                encoder_version=seal.record_for(UUID(str(row["candidate_id"]))).encoder_version,
                values=seal.record_for(UUID(str(row["candidate_id"]))).values,
                embedding=seal.record_for(UUID(str(row["candidate_id"]))).embedding,
            ),
            accepted=bool(row["accepted"]),
            sealed_at=seal.sealed_at,
            outcome_at=seal.sealed_at,
            observation_id=UUID(str(row["observation_id"])),
            sealed_feature_hash=seal.record_for(UUID(str(row["candidate_id"]))).feature_vector_hash,
        )
        for row in campaign["candidate_outcomes"]
    )
    # The split label is D6's, not "conformal", and it has to be: `canonical_bytes` prefixes the
    # rows with it, so a relabelled matrix hashes differently and could not be checked against
    # the bytes D6 published. It is the only field of the matrix outside the rows themselves, and
    # no scan reads it -- the role this half plays in D7 is stated in the record below instead.
    matrix = FittedMatrix(split="calibration", rows=rows)
    published = json.loads(D6_SNAPSHOTS.read_text(encoding="utf-8"))["fitted_matrices"]
    if matrix.content_hash != published["certification_matrix_hash"]:
        raise SystemExit(
            "the rebuilt conformal matrix is not the one D6 published: "
            f"{matrix.content_hash} against {published['certification_matrix_hash']}. Either a "
            "vector or a label did not survive the round trip, and a bar placed by drifted "
            "margins is not the bar the pre-registration named"
        )
    return matrix, {
        "role": "d6 certification, demoted into the bar-setting role under S21D7-010",
        "rows": len(rows),
        "groups": len(matrix.groups),
        "rebuilt_from": {
            "vectors": (
                "D6's sealed certification feature record set, read-only from its measured store"
            ),
            "labels": D6_CERTIFICATION_CAMPAIGN.name,
            "feature_seal_hash": released_row["feature_seal_hash"],
            "certification_campaign_sha256": _digest(D6_CERTIFICATION_CAMPAIGN.read_bytes()),
            "d6_snapshots_sha256": _digest(D6_SNAPSHOTS.read_bytes()),
        },
        "re_executed": False,
        "matrix_hash": matrix.content_hash,
        "d6_published_matrix_hash": published["certification_matrix_hash"],
        "identical_to_the_published_matrix": True,
        "what_the_hash_proves": (
            "canonical_line serialises the scaled values, the embedding and the label and "
            "nothing else, so an equal hash means every vector and every label came back intact"
        ),
        "chronology_is_inherited_not_recomputed": {
            "why": (
                "D6's per-row outcome times live in D6's database, which D7 does not open. They "
                "reach no scan but the chronology one, so both timestamps here are D6's seal time"
            ),
            "d6_certified": json.loads(D6_CERTIFICATION_CAMPAIGN.read_text(encoding="utf-8"))[
                "execution"
            ]["every_outcome_follows_the_seal"],
            "reading": (
                "the chronology scan's verdict over this half is not independent evidence; the "
                "claim it would test was certified in the bound D6 record above"
            ),
        },
    }


async def _stage_snapshot(output: Path) -> int:
    """S21D6-030: the certification dataset, and the conformal half it is scanned against."""
    database_url, artifact_root = _isolated_pair()

    sealed = json.loads(SEAL_RECORD.read_text(encoding="utf-8"))
    campaigns = {
        name: json.loads(CAMPAIGN_RECORD[name].read_text(encoding="utf-8")) for name in _ORDER
    }
    splits = {CorrectionPartition.TRAINING: "fit", CorrectionPartition.CALIBRATION: "calibration"}
    roles = {
        CorrectionPartition.TRAINING: CorpusRole.TRAINING,
        CorrectionPartition.CALIBRATION: CorpusRole.EVALUATION,
    }

    engine = create_postgres_engine(database_url)
    contract = CorrectionFeatureContractV2()
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        ledger = RealityCampaignLedger(events)
        repository = PostgresLearnedEvidenceRepository(engine)
        builder = LearnedDatasetBuilder(repository, LearnedArtifactStore(artifacts))
        learned = LearnedEvidenceService(repository, events=LearnedEventService(events))

        # How many rows the surface holds, counted rather than assumed. The store is allowed to
        # hold more than any dataset names; a record that never looked cannot say so.
        surface_rows: list[Any] = []
        page = 0
        while True:
            batch = await learned.list_observations(
                surface=CORRECTION_SURFACE, limit=500, offset=page * 500
            )
            surface_rows.extend(batch)
            if len(batch) < 500:
                break
            page += 1
        on_the_surface = len(surface_rows)

        matrices: dict[CorrectionPartition, FittedMatrix] = {}
        reports: list[dict[str, Any]] = []

        for name in _ORDER:
            campaign = campaigns[name]
            row = next(item for item in sealed["partitions"] if item["partition"] == name.value)
            if campaign["feature_seal_hash"] != row["feature_seal_hash"]:
                raise SystemExit(f"{name.value}: the campaign ran against another seal")
            seal_bytes = await artifacts.get_bytes(UUID(row["feature_seal_artifact_id"]))
            seal = SealedFeatureRecordSetV2.model_validate_json(seal_bytes.decode())
            if seal.content_hash != row["feature_seal_hash"]:
                raise SystemExit(f"{name.value}: the stored seal is not the one S21D7-025 recorded")

            recorded = await ledger.completed_by_identity(
                [UUID(item) for item in campaign["task_run_ids"]]
            )
            outcomes = {
                reference.candidate_id: reference
                for reference in recorded.values()
                if reference.candidate_id is not None
            }
            members = list(campaign["candidate_outcomes"])
            missing = [
                item["candidate_id"]
                for item in members
                if UUID(str(item["candidate_id"])) not in outcomes
            ]
            if missing:
                raise SystemExit(
                    f"{name.value}: {len(missing)} candidates have no recorded outcome in the "
                    f"ledger, starting with {missing[0]}"
                )
            # The labels the ledger holds against the labels the campaign reported. S21D6-032
            # fits on these rows; a disagreement here is a disagreement about the training set.
            relabelled = [
                item["candidate_id"]
                for item in members
                if outcomes[UUID(str(item["candidate_id"]))].hidden_verification_passed
                != bool(item["accepted"])
            ]
            if relabelled:
                raise SystemExit(
                    f"{name.value}: {len(relabelled)} ledger labels disagree with the campaign "
                    f"record, starting with {relabelled[0]}"
                )

            selection = _selection(
                name, members, manifest_hash=row["campaign_manifest_hash"], split=splits[name]
            )
            dataset = await builder.build(
                surface=CORRECTION_SURFACE,
                corpus_role=roles[name],
                feature_schema_hash=contract.content_hash,
                revision=3,
                selection=selection,
            )
            # Fresh application services over the same durable authorities. A rebuild that
            # reused the warm builder would prove the builder is deterministic, not the record.
            rebuilt = await LearnedDatasetBuilder(
                PostgresLearnedEvidenceRepository(engine),
                LearnedArtifactStore(
                    ArtifactService(
                        ContentAddressedFilesystem(artifact_root),
                        PostgresArtifactRepository(engine),
                    )
                ),
            ).build(
                surface=CORRECTION_SURFACE,
                corpus_role=roles[name],
                feature_schema_hash=contract.content_hash,
                revision=3,
                selection=selection,
            )
            matrices[name] = _fitted_matrix(
                split=splits[name],
                partition=name,
                rows=members,
                seal=seal,
                outcomes=outcomes,
            )
            reports.append(
                {
                    "partition": name.value,
                    "split": splits[name],
                    "corpus_role": roles[name].value,
                    "dataset_id": str(dataset.dataset_id),
                    "identity_revision": 3,
                    "observation_count": dataset.observation_count,
                    "provenance_counts": dataset.provenance_counts,
                    "real_governed_runs": dataset.provenance_counts.get("real_governed_run", 0),
                    "usage_rights_verified": dataset.usage_rights_verified,
                    "dataset_content_hash": dataset.content_hash,
                    "split_manifest_hash": dataset.split_manifest_hash,
                    "example_manifest_hash": dataset.example_manifest_hash,
                    "selection_partition_digest": selection.selection_partition_digest,
                    "members": len(selection.members),
                    "groups": len(set(selection.groups.values())),
                    "store_wide_selection": False,
                    "latest_seal_selection": False,
                    "rebuilt_identically": str(rebuilt.dataset_id) == str(dataset.dataset_id)
                    and rebuilt.content_hash == dataset.content_hash
                    and rebuilt.split_manifest_hash == dataset.split_manifest_hash
                    and rebuilt.example_manifest_hash == dataset.example_manifest_hash,
                    "immutable": dataset.content_hash == rebuilt.content_hash,
                    "feature_seal_hash": seal.content_hash,
                    "campaign_manifest_hash": row["campaign_manifest_hash"],
                    "labels_read_from": "the durable outcome ledger, not the campaign report",
                    "labels_agree_with_the_campaign_record": True,
                    "vectors_read_from": "the sealed feature record set in the artifact store",
                }
            )
    finally:
        await engine.dispose()

    named = {
        str(row["observation_id"])
        for campaign in campaigns.values()
        for row in campaign["candidate_outcomes"]
    }
    # Which manifest each unreferenced row belongs to, resolved against the manifests this
    # sprint released rather than described. A prefix nobody can name is an unexplained row.
    known_manifests = {
        str(json.loads(VERTICAL_SLICE.read_text(encoding="utf-8"))["fixture_manifest_hash"]): (
            "the S21D6-024 fixture group, outside every role"
        ),
        **{
            str(campaigns[name]["campaign_manifest_hash"]): (
                f"the {name.value} campaign manifest, under a run identity no campaign record names"
            )
            for name in _ORDER
        },
    }
    unreferenced = [row for row in surface_rows if str(row.observation_id) not in named]
    unreferenced_by_campaign = {
        prefix: {
            "rows": count,
            "manifest": next(
                (text for value, text in known_manifests.items() if value.startswith(prefix)),
                "unaccounted for",
            ),
        }
        for prefix, count in sorted(
            Counter(str(row.idempotency_key).split(":")[0][:16] for row in unreferenced).items()
        )
    }

    conformal, conformal_provenance = _conformal_matrix()
    certification = matrices[CorrectionPartition.CALIBRATION]
    report = scan_matrices(conformal, certification, created_at=utc_now(), contract=contract)
    failed = [scan.name for scan in report.scans if not scan.passed]
    channels = len(report.column_names)

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W2",
            "items": ["S21D6-030"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "feature_seals_sha256": _digest(SEAL_RECORD.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "certification_campaign_sha256": _digest(
                CAMPAIGN_RECORD[CorrectionPartition.CALIBRATION].read_bytes()
            ),
            "final_outcomes_inspected": False,
            "feature_contract_hash": contract.content_hash,
            "datasets": reports,
            "store_state": {
                "observations_on_the_correction_surface": on_the_surface,
                "unreferenced_by_campaign_manifest": unreferenced_by_campaign,
                "observations_named_by_the_datasets": sum(int(item["members"]) for item in reports),
                "unreferenced_rows": on_the_surface - sum(int(item["members"]) for item in reports),
                "every_unreferenced_row_is_accounted_for": all(
                    item["manifest"] != "unaccounted for"
                    for item in unreferenced_by_campaign.values()
                ),
                "why_the_store_holds_more_than_the_datasets_name": (
                    "S21D6-024 ran the vertical slice against the fixture group, which is outside "
                    "every role and therefore in no dataset. It was left in place rather than "
                    "deleted: an append-only evidence store that a wave prunes to make a count "
                    "come out is a store nobody can audit"
                ),
                "why_unreferenced_rows_cannot_reach_a_dataset": (
                    "an explicit selection names its members by observation id, so a dataset "
                    "cannot grow because the store did"
                ),
            },
            "conformal_half": conformal_provenance,
            "fitted_matrices": {
                # `fit` and `calibration` are the scan API's names for its two sides, kept so a
                # reader can line this record up against D4's and D5's. What sits on each side is
                # named below, because for D6 they are not a fitting and a calibration split:
                # nothing is fitted here at all.
                "conformal_matrix_hash": report.fit_matrix_hash,
                "certification_matrix_hash": report.calibration_matrix_hash,
                "conformal_rows": report.fit_rows,
                "certification_rows": report.calibration_rows,
                "conformal_groups": report.fit_groups,
                "certification_groups": report.calibration_groups,
                "fitted_dimensions": channels,
                "fitted_dimensions_expected": len(FITTED_FEATURE_V2_ALLOWLIST),
                "channels_are_the_v2_allowlist_in_order": (
                    tuple(report.column_names) == FITTED_FEATURE_V2_ALLOWLIST
                ),
                "encoder_version": report.encoder_version,
                "feature_contract_hash": report.feature_contract_hash,
                "near_duplicate_threshold": report.near_duplicate_threshold,
                "maximum_cross_split_similarity": report.maximum_cross_split_similarity,
                "clean": report.clean,
                "report_hash": report.content_hash,
                "halves_share_no_group": not (conformal.groups & certification.groups),
                "why_this_pair": (
                    "D6 executes one partition, so the pair cannot be a fitting and a calibration "
                    "matrix out of one store. The two halves scanned here are the ones the "
                    "experiment rests on: the conformal half places the bar and the certification "
                    "half is measured against it. A shared group or a near-duplicate across that "
                    "boundary is exactly what would break the exchangeability section 6 names as "
                    "the risk the evidence cannot retire, and it is the only boundary where a "
                    "leak would flatter the result"
                ),
                "the_two_halves_come_from_different_sprints": (
                    "the conformal rows are D5's, rebuilt from its released bytes and unexecuted "
                    "here; the certification rows are D6's own. Their only shared machinery is "
                    "the clip-and-scale envelope, which is deliberate and is what makes the two "
                    "sets of margins comparable at all"
                ),
            },
            "scans": {
                "count": len(report.scans),
                "all_passed": not failed,
                "failed": failed,
                "results": [
                    {"name": scan.name, "passed": scan.passed, "detail": scan.detail}
                    for scan in report.scans
                ],
            },
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
                "datasets": {str(item["partition"]): str(item["dataset_id"]) for item in reports},
                "rebuilt_identically": all(bool(item["rebuilt_identically"]) for item in reports),
                "conformal_rows": report.fit_rows,
                "certification_rows": report.calibration_rows,
                "conformal_matrix_is_d6s_published_one": conformal_provenance[
                    "identical_to_the_published_matrix"
                ],
                "fitted_dimensions": channels,
                "scans": len(report.scans),
                "scans_passed": len(report.scans) - len(failed),
                "failed_scans": failed,
                "maximum_cross_split_similarity": report.maximum_cross_split_similarity,
                "observations_on_the_surface": on_the_surface,
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("seal", "execute", "snapshot"), default="seal")
    parser.add_argument("--model", type=Path)
    parser.add_argument(
        "--role",
        choices=sorted(ROLES),
        default="certification",
        help="which roles this run opens; `final` and `canary` are W3 only and refuse "
        "without a pass through §2.3",
    )
    parser.add_argument(
        "--partition",
        choices=sorted({name.value for order, _ in ROLES.values() for name in order}),
        default=None,
    )
    parser.add_argument("--groups", type=int, default=None, help="smoke-test limit")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--provisional",
        action="store_true",
        help="run against an unfinished corpus; every record written says so",
    )
    arguments = parser.parse_args()
    order, seal_record = ROLES[arguments.role]
    if arguments.role in GATED_ROLES:
        # The carried roles open once, and only for a candidate §2.3 made eligible. Checked
        # here rather than in the caller: a flag that opens 60 unopened groups should not be
        # one typo away from spending them on a stopped sprint.
        selection = json.loads(LEARNER_SELECTION.read_text(encoding="utf-8"))
        if selection["ending"]["name"] != "1_select":
            raise SystemExit(
                f"the selection record ends {selection['ending']['name']!r}; the final roles "
                "are opened only by a pass through the amended §2.3"
            )
    partition_name = arguments.partition or order[0].value
    if CorrectionPartition(partition_name) not in order:
        raise SystemExit(f"--partition {partition_name} is not part of the {arguments.role} role")

    # S21D4-037's first invocation fell through to the execute stage and ran a campaign twice,
    # because `snapshot` was an argparse choice with no branch behind it. Dispatched first here.
    if arguments.stage == "snapshot":
        return asyncio.run(_stage_snapshot(arguments.output or SNAPSHOT_RECORD))

    if arguments.stage == "execute":
        partition = CorrectionPartition(partition_name)
        if arguments.groups is not None and arguments.output is None:
            raise SystemExit("--groups writes a partial record; give it an --output of its own")
        return asyncio.run(
            _stage_execute(
                arguments.output or CAMPAIGN_RECORD[partition],
                partition,
                arguments.groups,
                provisional=arguments.provisional,
                seal_record=seal_record,
            )
        )

    if arguments.model is None:
        raise SystemExit("--stage seal needs --model")
    if arguments.groups is not None and arguments.output is None:
        raise SystemExit("--groups writes a partial record; give it an --output of its own")
    return asyncio.run(
        _stage_seal(
            arguments.output or seal_record,
            arguments.model,
            arguments.groups,
            provisional=arguments.provisional,
            order=order,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
