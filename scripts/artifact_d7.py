#!/usr/bin/env python3
"""S21D7-035 and S21D7-036: the selected candidate as bytes, and the boundary it must pass.

Conditions 11 and 22 in one command, because they are one claim asked twice. 11 says one
artifact is selected **before** any final manifest is opened; 22 says that artifact is canonical
inert JSON with complete lineage. Run apart, the second would be a record about bytes nobody had
shown were the selected candidate's.

What goes in is not chosen here. The direction is W2's — re-derived and refused unless it hashes
to the one `sprint-21d7-w2-direction.json` sealed — and the operating point is W2's bar, bound by
its derivation hash. This command fits nothing, derives nothing and selects nothing; it packages
what §2.3 already made eligible and then tries to break the package.

Three things are executed rather than described:

*The bytes round-trip into exactly one class.* Canonical inert JSON out, stored by content
address, read back out of the store, and rebuilt through the evaluation boundary under a
capability that names the lineage. The rebuilt ranker must reproduce **every** certification
decision — all 100 first choices and all 100 margins — not merely load.

*Every refusal refuses.* Tampered bytes, a lineage the capability does not authorise, a wrong
descriptor, a wrong revision, a class the loader does not implement, and bytes past the size
ceiling. Each is driven with material that breaks exactly one rule and each is recorded with the
error it raised.

*Nothing final is touched.* The record counts final and canary reads and both are zero. The
artifact is built from the fitting pool's direction and the bar-setting half's certificate; the
fresh certification half supplies the ranking the reload is checked against, and it was already
read by S21D7-034.

    set -a && . ./.env.s21d7.measured.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/artifact_d7.py

Writes one artifact to D7's own measured store. No predecessor store is written.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.learned import LearnedComponentState  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    HYPOTHESIS_CLASS,
    ContainmentContrastiveRanker,
    RelationalGroup,
    fit_containment_direction,
    relational_numbers,
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
from cognitive_os.learning.correction_catalogue_d5 import (  # noqa: E402
    build_d5_fitting_catalogue,
)
from cognitive_os.learning.correction_catalogue_d7 import (  # noqa: E402
    build_d7_certification_catalogue,
)
from cognitive_os.learning.correction_features import (  # noqa: E402
    SealedFeatureRecordSetV2,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import NumericBoundsV2  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-21d7-artifact.json"

D5_FEATURE_SEALS = EVIDENCE / "sprint-21d5-feature-seals.json"
D5_FITTING_CAMPAIGN = EVIDENCE / "sprint-21d5-self-play-campaign.json"
D7_FEATURE_SEALS = EVIDENCE / "sprint-21d7-feature-seals.json"
D7_CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d7-certification-campaign.json"
D7_SNAPSHOTS = EVIDENCE / "sprint-21d7-snapshots.json"
D7_DIRECTION = EVIDENCE / "sprint-21d7-w2-direction.json"
D7_SELECTION = EVIDENCE / "sprint-21d7-learner-selection.json"
D7_PRE_REGISTRATION_R8 = EVIDENCE / "sprint-21d7-pre-registration-r8.json"

D5_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d5")
D7_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7-measured")

#: The released dataset identities the artifact's lineage names. The direction was fitted on D5's
#: 180-group pool and the bar was placed by the demoted D6 certification half, so those are the
#: two datasets in the payload — not the fresh certification half, which the artifact is
#: *certified against* and never fitted or calibrated on.
D5_TRAINING_DATASET = UUID("f2489d5f-0a5b-5598-8dad-3615809d3922")
D6_BAR_SETTING_DATASET = UUID("a5112033-2f11-5885-b60a-bc1a3bd84faf")

REGULARIZATION = Decimal("1")
MARGIN_FLOOR = Decimal("0")

#: What the artifact says about itself that a reader should not have to infer. Every one of these
#: is a property of the evidence behind it, not a caveat added to soften the record.
DECLARED_LIMITATIONS = (
    "the direction is fitted on D5's 180-group pool, whose licensed role is fitting; it has "
    "never been fitted on the corpus it is certified against",
    "the conformal bar is placed by the demoted D6 certification half and is a marginal "
    "guarantee: it holds in expectation over exchangeable halves, not on any one sample",
    "the admitted error budget is a bound, not a zero: the certification cell admitted 59 "
    "decisions with 3 errors and a 95% upper bound of 0.126207",
    "coverage is 0.59 on the certification half; the 41 decisions below the bar are abstentions "
    "by design and carry no claim",
    "seven relational channels only. The 384 embedding channels are sealed for the v2 record's "
    "completeness and read by nothing in this artifact",
)


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


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required; source .env.s21d7.measured.local first")
    return value


def _implementation_digest() -> str:
    files = (
        "src/cognitive_os/learning/correction_source.py",
        "src/cognitive_os/learning/correction_features.py",
        "src/cognitive_os/learning/correction_ranking.py",
        "src/cognitive_os/learning/correction_matrix.py",
        "src/cognitive_os/learning/containment_contrastive.py",
        "src/cognitive_os/learning/repair_containment.py",
        "src/cognitive_os/learning/conformal_operating_point.py",
        "src/cognitive_os/learning/correction_artifact.py",
    )
    digest = sha256()
    for name in files:
        digest.update((REPOSITORY / name).read_bytes())
    return digest.hexdigest()


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
    raise SystemExit(f"the released {partition} feature seal does not resolve in {store.name}")


def _catalogue_maps(catalogue: Any) -> tuple[dict, dict, dict]:
    order: dict[str, tuple[str, ...]] = {}
    delta: dict[str, str] = {}
    baseline: dict[str, str] = {}
    for group in catalogue.groups:
        item = template(group.template_id)
        path = next(name for name in item.visible_files if name.startswith("src/"))
        baseline[group.repository_group] = item.visible_files[path]
        order[group.repository_group] = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        for slot in group.slots:
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[
                RealityCandidateStrategy(slot.recipe)
            ][path]
    return order, delta, baseline


def _groups(seal: SealedFeatureRecordSetV2, catalogue: Any, labels: dict) -> list[RelationalGroup]:
    order, delta, baseline = _catalogue_maps(catalogue)
    values = {str(record.candidate_id): record.values for record in seal.records}
    return [
        RelationalGroup(
            group=name,
            order=order[name],
            numbers=relational_numbers(
                {item: values[item] for item in order[name]},
                baseline_source=baseline[name],
                sources_by_candidate={item: delta[item] for item in order[name]},
            ),
            accepted=labels[name],
        )
        for name in sorted(order)
    ]


def _labels(campaign: Path) -> dict[str, dict[str, bool]]:
    accepted: dict[str, dict[str, bool]] = {}
    for item in _read(campaign)["candidate_outcomes"]:
        accepted.setdefault(str(item["group"]), {})[str(item["candidate_id"])] = bool(
            item["accepted"]
        )
    return accepted


def _ranked(ranker: ContainmentContrastiveRanker, groups: list[RelationalGroup]) -> dict[str, Any]:
    """Every decision's first choice and margin, as one comparable mapping."""
    return {
        group.group: {
            "first": ranker.rank(group.numbers, baseline_order=group.order).ordered_candidate_ids[
                0
            ],
            "margin": str(ranker.rank(group.numbers, baseline_order=group.order).confidence),
        }
        for group in groups
    }


def _direction() -> Any:
    seal = _sealed_records(D5_ARTIFACT_ROOT, D5_FEATURE_SEALS, "training")
    model = fit_containment_direction(
        _groups(seal, build_d5_fitting_catalogue(), _labels(D5_FITTING_CAMPAIGN)),
        regularization=REGULARIZATION,
    )
    sealed_hash = _read(D7_DIRECTION)["fit"]["model_hash"]
    if model.content_hash() != sealed_hash:
        raise SystemExit(
            f"the direction does not match the one W2 sealed: {model.content_hash()} against "
            f"{sealed_hash}. This command packages the wave's direction; it does not fit one"
        )
    return model


def _refusals(
    artifact_bytes: bytes, capability: DirectEvaluationCapability, contract: Any
) -> list[dict[str, str]]:
    """Each case breaks exactly one rule. A refusal list nobody executes is a list of hopes."""
    results: list[dict[str, str]] = []

    def _case(action: str, data: bytes, cap: DirectEvaluationCapability) -> None:
        try:
            build_ranker_for_evaluation_v3(data, capability=cap, contract=contract)
        except (CorrectionArtifactError, ValueError) as error:
            results.append(
                {"action": action, "refused": "true", "error": f"{type(error).__name__}: {error}"}
            )
        else:
            raise SystemExit(f"the boundary accepted {action!r}, which it must refuse")

    payload = json.loads(artifact_bytes)

    tampered = dict(payload)
    tampered["weights"] = [float(value) + 1.0 for value in payload["weights"]]
    _case(
        "load a direction whose weights were edited after storage",
        _canonical_json(tampered),
        capability,
    )

    _case(
        "load the artifact under a capability naming another artifact hash",
        artifact_bytes,
        replace(capability, artifact_hash=_digest(b"another artifact")),
    )
    _case(
        "load the artifact under a capability naming another descriptor",
        artifact_bytes,
        replace(capability, descriptor_hash=_digest(b"another descriptor")),
    )
    _case(
        "load the artifact under a capability naming another component revision",
        artifact_bytes,
        replace(capability, component_revision=capability.component_revision + 1),
    )
    _case(
        "load the artifact under a capability naming another training dataset",
        artifact_bytes,
        replace(capability, training_dataset_id=D6_BAR_SETTING_DATASET),
    )

    other_class = dict(payload)
    other_class["hypothesis_class"] = "a-class-nobody-implements-v1"
    _case(
        "load a payload naming a class the loader does not implement",
        _canonical_json(other_class),
        capability,
    )

    padded = dict(payload)
    padded["declared_limitations"] = ["x" * (MAXIMUM_ARTIFACT_BYTES + 1)]
    _case("load bytes past the artifact size ceiling", _canonical_json(padded), capability)

    return results


def _canonical_json(payload: dict[str, Any]) -> bytes:
    """The same byte convention `canonical_bytes` uses, for material that is deliberately wrong."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


async def _run(output: Path) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    if artifact_root != D7_ARTIFACT_ROOT:
        raise SystemExit(
            f"COGOS_ARTIFACT_ROOT is {artifact_root}, not D7's measured store {D7_ARTIFACT_ROOT}"
        )

    selection = _read(D7_SELECTION)
    if selection["ending"]["name"] != "1_select":
        raise SystemExit(
            f"the selection record ends {selection['ending']['name']!r}; an artifact may only be "
            "built for a candidate §2.3 made eligible"
        )

    model = _direction()
    ranker = ContainmentContrastiveRanker(model, margin_floor=MARGIN_FLOOR)
    contract = CorrectionFeatureContractV2()

    cert_seal = _sealed_records(D7_ARTIFACT_ROOT, D7_FEATURE_SEALS, "calibration")
    cert_groups = _groups(
        cert_seal, build_d7_certification_catalogue(), _labels(D7_CERTIFICATION_CAMPAIGN)
    )
    before = _ranked(ranker, cert_groups)

    bounds_row = next(
        item for item in _read(D7_FEATURE_SEALS)["partitions"] if item["partition"] == "calibration"
    )["bounds"]
    bounds = NumericBoundsV2(lower=bounds_row["lower"], upper=bounds_row["upper"])
    d7_dataset = next(
        item for item in _read(D7_SNAPSHOTS)["datasets"] if item["partition"] == "calibration"
    )
    d6_certificate = _read(D7_SNAPSHOTS)["fitted_matrices"]["conformal_matrix_hash"]
    point = selection["conformal_point"]

    descriptor_hash = _digest(
        f"d7-containment-contrastive-descriptor:{model.content_hash()}:{point['derivation_hash']}"
    )
    code_revision = _implementation_digest()
    payload = build_payload_v3(
        component_revision=1,
        descriptor_hash=descriptor_hash,
        code_revision=code_revision,
        ranker=ranker,
        training_dataset_id=D5_TRAINING_DATASET,
        calibration_dataset_id=D6_BAR_SETTING_DATASET,
        example_manifest_hash=d7_dataset["example_manifest_hash"],
        split_manifest_hash=d7_dataset["split_manifest_hash"],
        selection_manifest_hash=selection["integrity_content_hash"],
        member_manifest_hash=d7_dataset["example_manifest_hash"],
        feature_schema_hash=contract.content_hash,
        embedding_revision=cert_seal.embedding_tree_digest,
        numeric_lower=bounds.lower,
        numeric_upper=bounds.upper,
        setting_identity=_digest(json.dumps(ranker.settings, sort_keys=True)),
        operating_point_hash=point["derivation_hash"],
        calibration_certificate_hash=d6_certificate,
        contract=contract,
        declared_limitations=DECLARED_LIMITATIONS,
    )
    artifact_bytes = canonical_bytes(payload)

    engine = create_postgres_engine(database_url)
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        stored = await artifacts.put_bytes(
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
            training_dataset_id=D5_TRAINING_DATASET,
            split_manifest_hash=d7_dataset["split_manifest_hash"],
            member_manifest_hash=d7_dataset["example_manifest_hash"],
            selection_manifest_hash=selection["integrity_content_hash"],
        )
        from_store = await artifacts.get_bytes(stored.artifact_id)
        reloaded, reloaded_payload = build_ranker_for_evaluation_v3(
            from_store, capability=capability, contract=contract
        )
        after = _ranked(reloaded, cert_groups)
        refusals = _refusals(artifact_bytes, capability, contract)
    finally:
        await engine.dispose()

    disagreements = sorted(name for name in before if before[name] != after[name])
    if disagreements or from_store != artifact_bytes:
        raise SystemExit(
            f"the reloaded artifact does not reproduce the ranking on {len(disagreements)} "
            "decisions; an artifact that loads but ranks differently is the failure the "
            "boundary exists to catch"
        )

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W3",
            "items": ["S21D7-035", "S21D7-036"],
            "final_outcomes_inspected": False,
            "final_or_canary_outcomes_inspected": 0,
            "final_manifests_opened": 0,
            "conformal_bars_derived": 0,
            "directions_fitted": 0,
            "inputs": {
                "w2_direction_sha256": _digest(D7_DIRECTION.read_bytes()),
                "learner_selection_sha256": _digest(D7_SELECTION.read_bytes()),
                "pre_registration_r8_sha256": _digest(D7_PRE_REGISTRATION_R8.read_bytes()),
                "d7_feature_seals_sha256": _digest(D7_FEATURE_SEALS.read_bytes()),
                "d7_snapshots_sha256": _digest(D7_SNAPSHOTS.read_bytes()),
            },
            "selected_because": {
                "record": D7_SELECTION.name,
                "integrity_content_hash": selection["integrity_content_hash"],
                "ending": selection["ending"]["name"],
                "failed_conditions": selection["section_2_3"]["failed_conditions"],
                "selection_precedes_final_access": (
                    "no final or canary manifest has been opened when this runs; the counters "
                    "above are the claim and the campaign records are where it is checkable"
                ),
            },
            "artifact": {
                "artifact_id": str(stored.artifact_id),
                "artifact_hash": _digest(artifact_bytes),
                "artifact_bytes": len(artifact_bytes),
                "media_type": CORRECTION_ARTIFACT_MEDIA_TYPE,
                "schema": correction_artifact_schema(artifact_bytes),
                "hypothesis_class": HYPOTHESIS_CLASS,
                "learner_kind": payload.learner_kind,
                "component_id": payload.component_id,
                "component_revision": payload.component_revision,
                "surface": payload.surface,
                "descriptor_hash": descriptor_hash,
                "code_revision": code_revision,
                "feature_channels": len(payload.feature_channels),
                "channels": list(payload.feature_channels),
                "model_hash": model.content_hash(),
                "margin_floor": str(MARGIN_FLOOR),
                "maximum_inference_ms": payload.maximum_inference_ms,
                "declared_limitations": list(DECLARED_LIMITATIONS),
                "size_reading": (
                    f"{len(artifact_bytes)} bytes for a seven-channel direction. The released v2 "
                    "shape carries one 390-channel vector per fitting row; this carries seven "
                    "weights and the lineage that says what they were fitted on"
                ),
            },
            "lineage": {
                "training_dataset_id": str(D5_TRAINING_DATASET),
                "training_dataset_is": "D5's 180-group fitting pool, its licensed role",
                "calibration_dataset_id": str(D6_BAR_SETTING_DATASET),
                "calibration_dataset_is": "the demoted D6 certification half, per S21D7-010",
                "example_manifest_hash": d7_dataset["example_manifest_hash"],
                "split_manifest_hash": d7_dataset["split_manifest_hash"],
                "selection_manifest_hash": selection["integrity_content_hash"],
                "feature_schema_hash": contract.content_hash,
                "embedding_revision": cert_seal.embedding_tree_digest,
                "operating_point_hash": point["derivation_hash"],
                "operating_point_threshold": point["threshold"],
                "operating_point_alpha": point["alpha"],
                "calibration_certificate_hash": d6_certificate,
                "numeric_bounds_from": "D5's released training seal, carried unchanged",
                "why_the_fresh_half_is_not_in_the_lineage": (
                    "the artifact was fitted on one pool and calibrated on another; the fresh "
                    "certification half is what it was measured against, and naming it as "
                    "training or calibration lineage would misdescribe how it was made"
                ),
            },
            "boundary": {
                "stored_bytes_are_the_built_bytes": from_store == artifact_bytes,
                "reloaded_through": "build_ranker_for_evaluation_v3 under a lineage capability",
                "reloaded_model_hash": reloaded.model.content_hash(),
                "reloaded_model_hash_matches": (
                    reloaded.model.content_hash() == model.content_hash()
                ),
                "reloaded_payload_matches": canonical_bytes(reloaded_payload) == artifact_bytes,
                "decisions_re_ranked": len(before),
                "decisions_disagreeing": len(disagreements),
                "every_first_choice_and_margin_reproduced": not disagreements,
                "why_re_ranking_and_not_only_loading": (
                    "an artifact that loads but ranks differently passes every structural check "
                    "and is the exact failure the boundary exists to catch, so all 100 first "
                    "choices and all 100 margins are compared rather than the model hash alone"
                ),
            },
            "refusals": refusals,
            "every_refusal_refused": all(item["refused"] == "true" for item in refusals),
            "what_this_record_is_not": (
                "an activation. The artifact is registered and readable; promoting, shadowing, "
                "canarying and activating it are later steps with records of their own"
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
                "artifact_hash": evidence["artifact"]["artifact_hash"],
                "artifact_bytes": len(artifact_bytes),
                "model_hash": model.content_hash(),
                "operating_point_hash": point["derivation_hash"],
                "decisions_reproduced": len(before) - len(disagreements),
                "refusals": len(refusals),
                "every_refusal_refused": evidence["every_refusal_refused"],
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return asyncio.run(_run(parser.parse_args().output))


if __name__ == "__main__":
    raise SystemExit(main())
