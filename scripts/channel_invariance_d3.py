#!/usr/bin/env python3
"""Run the pre-registered, development-only Sprint 21D3 D2 channel diagnostic.

This command reads the spent D2 catalogue, feature seals, and local MiniLM tree. It writes no
database or Artifact Store record and has no calibration or selection authority. Candidate
labels are executed again from the deterministic task packages, so the diagnostic does not
need write access to the D2 PostgreSQL authority.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from math import sqrt
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))
sys.path.insert(0, str(REPOSITORY / "scripts"))

import learner_selection_d2 as d2  # noqa: E402

from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.learning import calibration_ood  # noqa: E402
from cognitive_os.learning.correction_catalogue import seal_corpus  # noqa: E402
from cognitive_os.learning.correction_features import (  # noqa: E402
    SealedFeatureRecordSet,
    feature_input,
    feature_input_v2,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    FITTED_FEATURE_V2_SCALARS,
    CorrectionDiagnosticProtocolV3,
    CorrectionPartition,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionEncoder,
    CorrectionEncoderV2,
    CorrectionKnn,
    Exemplar,
    NumericBounds,
    NumericBoundsV2,
)
from cognitive_os.learning.correction_source import canonical_source_bytes  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
D2_CAMPAIGN = EVIDENCE / "sprint-21d2-self-play-campaign.json"
D2_SELECTION = EVIDENCE / "sprint-21d2-learner-selection.json"
D3_PRE_REGISTRATION = EVIDENCE / "sprint-21d3-pre-registration.json"
D2_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d2")

CASE_CLEAN = "clean"
CASE_RENAME = "identifier_rename_only"
CASE_ISSUE = "issue_rewrite_only"
CASE_REORDER = "baseline_reorder_only"
CASE_TEST = "visible_test_literal_only"
CASE_COMBINED = "combined_identifier_rename_and_issue_rewrite"


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _hash_text(value: str) -> str:
    return _hash_bytes(value.encode())


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _hash_bytes(_canonical_bytes(value))
    return sealed


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _artifact_for_contract_hash(content_hash: str) -> tuple[Path, SealedFeatureRecordSet]:
    for path in (D2_ARTIFACT_ROOT / "sha256").glob("*/*"):
        try:
            if content_hash.encode() not in path.read_bytes():
                continue
            model = SealedFeatureRecordSet.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if model.content_hash == content_hash:
            if _hash_bytes(path.read_bytes()) != path.name:
                raise RuntimeError(f"D2 artifact bytes no longer match {path.name}")
            return path, model
    raise RuntimeError(f"D2 feature seal {content_hash} is absent from the frozen artifact root")


def _bundles(partition: CorrectionPartition) -> dict[str, UUID]:
    catalogue = seal_corpus().catalogues[partition]
    return {group.template_id: UUID(int=index + 1) for index, group in enumerate(catalogue.groups)}


def _source_package(template_id: str) -> tuple[str, str, tuple[str, ...], str, str, str]:
    item = template(template_id)
    module_path = next(path for path in item.visible_files if path.startswith("src/"))
    visible_path = next(path for path in item.visible_files if path.startswith("test"))
    hidden_path = next(path for path in item.control_files if path.startswith("test_hidden"))
    recipes = tuple(sorted(item.neutral_candidate_sources, key=str))
    variants = tuple(item.neutral_candidate_sources[recipe][module_path] for recipe in recipes)
    return (
        module_path.removeprefix("src/"),
        item.visible_files[module_path],
        variants,
        item.visible_files[visible_path],
        item.control_files[hidden_path],
        item.issue_description,
    )


def _original_label_tasks(template_ids: tuple[str, ...]) -> tuple[d2._OodTask, ...]:
    tasks = []
    for template_id in template_ids:
        module_name, baseline, variants, _, hidden, issue = _source_package(template_id)
        tasks.append(
            d2._OodTask(
                template_id=template_id,
                module_name=module_name,
                baseline=baseline,
                variants=variants,
                hidden_test=hidden,
                issue=issue,
                applied=(),
            )
        )
    return tuple(tasks)


def _labels_by_recipe(template_ids: tuple[str, ...]) -> dict[tuple[str, str], bool]:
    tasks = _original_label_tasks(template_ids)
    executed = d2._execute_ood(tasks)
    labels: dict[tuple[str, str], bool] = {}
    for task in tasks:
        recipes = tuple(sorted(template(task.template_id).neutral_candidate_sources, key=str))
        for index, recipe in enumerate(recipes):
            labels[(task.template_id, recipe.value)] = executed[f"{task.template_id}#{index}"]
    return labels


@dataclass(frozen=True, slots=True)
class _Case:
    name: str
    template_id: str
    module_name: str
    baseline: str
    variants: tuple[str, ...]
    visible_test: str
    hidden_test: str
    issue: str
    transformations: tuple[str, ...]
    applicable: bool
    applicability_detail: str


def _case(name: str, template_id: str) -> _Case:
    module_name, baseline, variants, visible, hidden, issue = _source_package(template_id)
    if name == CASE_CLEAN:
        return _Case(
            name,
            template_id,
            module_name,
            baseline,
            variants,
            visible,
            hidden,
            issue,
            (),
            True,
            "clean authority",
        )
    if name == CASE_RENAME:
        renamed = calibration_ood.rename_identifiers(baseline, *variants, visible, hidden)
        return _Case(
            name,
            template_id,
            module_name,
            renamed[0],
            tuple(renamed[1 : 1 + len(variants)]),
            renamed[-2],
            renamed[-1],
            issue,
            (calibration_ood.RENAME,),
            True,
            "one coherent package-wide rename map",
        )
    if name == CASE_ISSUE:
        rewritten, detail = calibration_ood.rewrite_issue_text(issue)
        return _Case(
            name,
            template_id,
            module_name,
            baseline,
            variants,
            visible,
            hidden,
            rewritten,
            (calibration_ood.REWRITE_ISSUE,),
            detail.applied,
            detail.detail,
        )
    if name == CASE_REORDER:
        reordered, detail = calibration_ood.reorder_independent_statements(baseline)
        return _Case(
            name,
            template_id,
            module_name,
            reordered,
            variants,
            visible,
            hidden,
            issue,
            (calibration_ood.REORDER,),
            detail.applied,
            detail.detail,
        )
    if name == CASE_TEST:
        substituted, detail = calibration_ood.substitute_literals(visible)
        return _Case(
            name,
            template_id,
            module_name,
            baseline,
            variants,
            substituted,
            hidden,
            issue,
            (calibration_ood.SUBSTITUTE_LITERALS,),
            detail.applied,
            detail.detail,
        )
    if name == CASE_COMBINED:
        original = d2._perturb_task(template_id)
        renamed_visible = calibration_ood.rename_identifiers(baseline, visible)[1]
        return _Case(
            name,
            template_id,
            original.module_name,
            original.baseline,
            original.variants,
            renamed_visible,
            original.hidden_test,
            original.issue,
            original.applied,
            True,
            "the exact D2 combined package, including registered reorder when applicable",
        )
    raise ValueError(f"unknown diagnostic case {name}")


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = sqrt(sum(a * a for a in left)) * sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


async def _run(output: Path, continuation_output: Path, model_path: Path) -> None:
    protocol = CorrectionDiagnosticProtocolV3()
    campaign = json.loads(D2_CAMPAIGN.read_text(encoding="utf-8"))
    selection = json.loads(D2_SELECTION.read_text(encoding="utf-8"))
    if selection["candidate_selection"]["content_hash"] != protocol.d2_selection_hash:
        raise RuntimeError("the frozen D2 selection hash does not match revision 3")
    partitions = {item["partition"]: item for item in campaign["partitions"]}
    embed, model_tree_digest = d2._embedding(model_path)

    training = d2._rebuild_candidates(
        CorrectionPartition.TRAINING, _bundles(CorrectionPartition.TRAINING)
    )
    calibration = d2._rebuild_candidates(
        CorrectionPartition.CALIBRATION, _bundles(CorrectionPartition.CALIBRATION)
    )
    training_template_ids = tuple(dict.fromkeys(item.template_id for item in training))
    calibration_template_ids = tuple(dict.fromkeys(item.template_id for item in calibration))

    training_texts = {
        **{f"task:{item.template_id}": item.requirement for item in training},
        **{f"cand:{item.candidate_id}": item.diff for item in training},
    }
    training_keys = sorted(training_texts)
    embedded_training = dict(
        zip(
            training_keys,
            await d2._embed_all(embed, tuple(training_texts[key] for key in training_keys)),
            strict=True,
        )
    )
    bounds = NumericBounds.from_training(d2._raw_rows(training, embedded_training))
    training_vectors = await d2._vectors_for(training, embed=embed, bounds=bounds)
    training_labels = _labels_by_recipe(training_template_ids)
    exemplars = tuple(
        Exemplar(
            vector=training_vectors[item.candidate_id],
            accepted=training_labels[(item.template_id, item.recipe.value)],
        )
        for item in training
    )
    ranker = CorrectionKnn(
        exemplars,
        k=3,
        similarity_floor=Decimal("0.30"),
        agreement_floor=Decimal("0.60"),
        confidence_floor=Decimal("0.55"),
        embedding_weight=Decimal("0.7"),
    )

    seal_details: dict[str, object] = {}
    for name, candidates in (("training", training), ("calibration", calibration)):
        entry = partitions[name]
        path, record_set = _artifact_for_contract_hash(entry["feature_set_hash"])
        stored = {record.candidate_id: record.feature_vector_hash for record in record_set.records}
        rebuilt = (
            training_vectors
            if name == "training"
            else await d2._vectors_for(candidates, embed=embed, bounds=bounds)
        )
        mismatches = [
            str(candidate.candidate_id)
            for candidate in candidates
            if rebuilt[candidate.candidate_id].content_hash() != stored[candidate.candidate_id]
        ]
        if mismatches:
            raise RuntimeError(f"{name} v1 vectors no longer reproduce their D2 seals")
        seal_details[name] = {
            "artifact_blob_sha256": path.name,
            "feature_set_hash": record_set.content_hash,
            "records": len(record_set.records),
            "rebuilt_hash_mismatches": mismatches,
            "canonical_json_sha256": _hash_text(record_set.canonical_json()),
        }

    case_names = tuple(protocol.cases)
    cases = tuple(
        _case(case_name, template_id)
        for case_name in case_names
        for template_id in calibration_template_ids
    )
    label_tasks = tuple(
        d2._OodTask(
            template_id=f"{item.name}:{item.template_id}",
            module_name=item.module_name,
            baseline=item.baseline,
            variants=item.variants,
            hidden_test=item.hidden_test,
            issue=item.issue,
            applied=item.transformations,
        )
        for item in cases
    )
    executed_labels = d2._execute_ood(label_tasks)

    texts: dict[str, str] = {}
    diffs: dict[tuple[str, str, int], str] = {}
    for item in cases:
        expected = template(item.template_id).expected_behavior
        texts[f"task:{item.name}:{item.template_id}"] = d2.requirement_text(item.issue, expected)
        for index, variant in enumerate(item.variants):
            key = (item.name, item.template_id, index)
            diffs[key] = d2._diff_of(item.baseline, variant)
            texts[f"candidate:{item.name}:{item.template_id}:{index}"] = diffs[key]
    # Reproduce the D2 harness one case at a time: ten task texts and forty candidate texts in
    # one 50-item batch. Embedding all six cases together would put byte-identical test-only
    # inputs at different batch positions and misclassify floating-point batch noise as a
    # feature response.
    embedded: dict[str, tuple[float, ...]] = {}
    for case_name in case_names:
        case_keys = sorted(key for key in texts if f":{case_name}:" in key)
        embedded.update(
            zip(
                case_keys,
                await d2._embed_all(embed, tuple(texts[key] for key in case_keys)),
                strict=True,
            )
        )
    encoder = CorrectionEncoder(bounds)
    vectors: dict[tuple[str, str, int], Any] = {}
    for item in cases:
        for index, variant in enumerate(item.variants):
            key = (item.name, item.template_id, index)
            vectors[key] = encoder.encode(
                feature_input(
                    candidate_source=variant,
                    unified_diff=diffs[key],
                    task_requirement_embedding=embedded[f"task:{item.name}:{item.template_id}"],
                    candidate_delta_embedding=embedded[
                        f"candidate:{item.name}:{item.template_id}:{index}"
                    ],
                )
            )

    diagnostic_rows: list[dict[str, object]] = []
    aggregates: dict[str, dict[str, int]] = {}
    for item in cases:
        ordered = tuple(f"{item.template_id}#{index}" for index in range(4))
        case_vectors = {
            candidate: vectors[(item.name, item.template_id, index)]
            for index, candidate in enumerate(ordered)
        }
        labels = {
            candidate: executed_labels[f"{item.name}:{item.template_id}#{index}"]
            for index, candidate in enumerate(ordered)
        }
        ranking = ranker.rank(case_vectors, baseline_order=ordered)
        first = ranking.first_choice
        aggregate = aggregates.setdefault(
            item.name,
            {
                "decisions": 0,
                "answered": 0,
                "abstained": 0,
                "confident_errors": 0,
                "accepted_labels": 0,
            },
        )
        aggregate["decisions"] += 1
        aggregate["answered"] += int(not ranking.abstained)
        aggregate["abstained"] += int(ranking.abstained)
        aggregate["confident_errors"] += int(
            not ranking.abstained and first is not None and not labels[first]
        )
        aggregate["accepted_labels"] += sum(labels.values())

        candidates: list[dict[str, object]] = []
        for index, candidate in enumerate(ordered):
            vector = case_vectors[candidate]
            clean = vectors[(CASE_CLEAN, item.template_id, index)]
            nearest = sorted(
                (
                    (
                        ranker._similarity(vector, exemplar.vector),
                        str(training[position].candidate_id),
                        exemplar.accepted,
                    )
                    for position, exemplar in enumerate(exemplars)
                ),
                key=lambda value: (-value[0], value[1]),
            )[:3]
            candidates.append(
                {
                    "candidate_identity": candidate,
                    "raw_inputs": {
                        "candidate_source_sha256": _hash_text(item.variants[index]),
                        "unified_diff_sha256": _hash_text(
                            diffs[(item.name, item.template_id, index)]
                        ),
                        "task_requirement_sha256": _hash_text(
                            texts[f"task:{item.name}:{item.template_id}"]
                        ),
                        "baseline_source_sha256": _hash_text(item.baseline),
                        "visible_test_sha256": _hash_text(item.visible_test),
                        "hidden_test_sha256": _hash_text(item.hidden_test),
                    },
                    "encoded_scalars": dict(vector.values),
                    "named_embedding_channels": {
                        f"candidate_delta_embedding_{dimension:03d}": value
                        for dimension, value in enumerate(vector.embedding)
                    },
                    "embedding_cosine_to_clean": _cosine(vector.embedding, clean.embedding),
                    "feature_hash": vector.content_hash(),
                    "feature_hash_drift": vector.content_hash() != clean.content_hash(),
                    "nearest_neighbours": [
                        {"similarity": similarity, "candidate_id": identity, "accepted": accepted}
                        for similarity, identity, accepted in nearest
                    ],
                    "independent_verifier_label": labels[candidate],
                }
            )
        diagnostic_rows.append(
            {
                "case": item.name,
                "source_group_id": item.template_id,
                "transformations": list(item.transformations),
                "applicable": item.applicable,
                "applicability_detail": item.applicability_detail,
                "ranking": list(ranking.ordered_candidate_ids),
                "first_choice": ranking.first_choice,
                "confidence": str(ranking.confidence),
                "abstained": ranking.abstained,
                "reason": ranking.reason,
                "independent_verifier_labels": labels,
                "candidates": candidates,
            }
        )

    # Reproduce the D2 clean calibration in its original slot order, separately from the
    # recipe-sorted OOD diagnostic order.
    calibration_vectors = await d2._vectors_for(calibration, embed=embed, bounds=bounds)
    calibration_labels = _labels_by_recipe(calibration_template_ids)
    clean_accepted_first = 0
    clean_answered = 0
    for template_id in calibration_template_ids:
        members = tuple(item for item in calibration if item.template_id == template_id)
        ordered_ids = tuple(str(item.candidate_id) for item in members)
        result = ranker.rank(
            {str(item.candidate_id): calibration_vectors[item.candidate_id] for item in members},
            baseline_order=ordered_ids,
        )
        clean_answered += int(not result.abstained)
        chosen = next(item for item in members if str(item.candidate_id) == result.first_choice)
        clean_accepted_first += int(calibration_labels[(template_id, chosen.recipe.value)])

    combined = aggregates[CASE_COMBINED]
    reproduction = {
        "clean_first_choice_rate": str(
            Decimal(clean_accepted_first) / Decimal(len(calibration_template_ids))
        ),
        "clean_answered": clean_answered,
        "clean_abstained": len(calibration_template_ids) - clean_answered,
        "combined_answered": combined["answered"],
        "combined_abstained": combined["abstained"],
        "combined_confident_errors": combined["confident_errors"],
        "combined_accepted_labels": combined["accepted_labels"],
    }
    reproduction["matches_d2"] = reproduction == {
        "clean_first_choice_rate": "0.9",
        "clean_answered": 9,
        "clean_abstained": 1,
        "combined_answered": 8,
        "combined_abstained": 2,
        "combined_confident_errors": 1,
        "combined_accepted_labels": 20,
    }

    # Prove the declared v2 exact invariants using the frozen model, without fitting or
    # selecting on these spent members.
    canonical_texts = sorted(
        {canonical_source_bytes(variant).decode() for item in cases for variant in item.variants}
    )
    canonical_vectors = dict(
        zip(
            canonical_texts,
            await d2._embed_all(embed, tuple(canonical_texts)),
            strict=True,
        )
    )
    embedding_by_key: dict[tuple[str, str, int], tuple[float, ...]] = {}
    for item in cases:
        for index in range(4):
            text = canonical_source_bytes(item.variants[index]).decode()
            embedding_by_key[(item.name, item.template_id, index)] = canonical_vectors[text]
    upper = {name: 1000.0 for name in FITTED_FEATURE_V2_SCALARS}
    upper["declared_verifier_capability_count"] = 10.0
    upper["missing_value_indicators"] = 1.0
    v2_encoder = CorrectionEncoderV2(
        NumericBoundsV2(lower={name: 0.0 for name in FITTED_FEATURE_V2_SCALARS}, upper=upper)
    )
    v2_vectors = {
        key: v2_encoder.encode(
            feature_input_v2(
                candidate_source=next(
                    item.variants[key[2]]
                    for item in cases
                    if item.name == key[0] and item.template_id == key[1]
                ),
                canonical_candidate_source_embedding=embedding,
            )
        )
        for key, embedding in embedding_by_key.items()
    }
    invariant_failures = []
    for item in cases:
        for index in range(4):
            if (
                v2_vectors[(item.name, item.template_id, index)]
                != v2_vectors[(CASE_CLEAN, item.template_id, index)]
            ):
                invariant_failures.append(f"{item.name}:{item.template_id}:{index}")

    structural_names = {
        "ast_node_count",
        "graph_node_count",
        "graph_edge_count",
        "graph_path_length",
    }
    registered_moving = {
        "changed_file_count",
        "hunk_count",
        "added_line_count",
        "removed_line_count",
        "query_to_candidate_cosine",
        "candidate_delta_embedding",
    }
    case_drift: dict[str, dict[str, object]] = {}
    unregistered_action_reversals: list[str] = []
    for case_name in case_names[1:]:
        rows = [row for row in diagnostic_rows if row["case"] == case_name]
        changed_scalars: set[str] = set()
        embedding_moved = False
        action_reversals = 0
        for row in rows:
            clean_row = next(
                item
                for item in diagnostic_rows
                if item["case"] == CASE_CLEAN and item["source_group_id"] == row["source_group_id"]
            )
            action_reversals += int(row["first_choice"] != clean_row["first_choice"])
            for candidate, clean_candidate in zip(
                row["candidates"], clean_row["candidates"], strict=True
            ):
                changed_scalars.update(
                    name
                    for name, value in candidate["encoded_scalars"].items()
                    if value != clean_candidate["encoded_scalars"][name]
                )
                embedding_moved |= candidate["embedding_cosine_to_clean"] < 0.999999999
        moved = set(changed_scalars)
        if embedding_moved:
            moved.add("candidate_delta_embedding")
        if action_reversals and not moved <= registered_moving:
            unregistered_action_reversals.append(case_name)
        case_drift[case_name] = {
            "changed_scalar_channels": sorted(changed_scalars),
            "embedding_moved": embedding_moved,
            "action_reversals": action_reversals,
            "structural_channel_drift": sorted(changed_scalars & structural_names),
            "only_registered_v1_unstable_channels_moved": moved <= registered_moving,
        }

    pre_registration_hash = _hash_bytes(D3_PRE_REGISTRATION.read_bytes())
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    source_hashes = {
        path.relative_to(REPOSITORY).as_posix(): _hash_bytes(path.read_bytes())
        for path in (
            REPOSITORY / "scripts/channel_invariance_d3.py",
            REPOSITORY / "scripts/learner_selection_d2.py",
            REPOSITORY / "src/cognitive_os/learning/calibration_ood.py",
            REPOSITORY / "src/cognitive_os/learning/correction_features.py",
            REPOSITORY / "src/cognitive_os/learning/correction_ranking.py",
            REPOSITORY / "src/cognitive_os/learning/correction_source.py",
        )
    }
    report = _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W1",
            "items": ["S21D3-026"],
            "recorded_at": recorded_at,
            "pre_registration_sha256": pre_registration_hash,
            "development_only": True,
            "selection_authority": False,
            "protocol_hash": protocol.content_hash,
            "setting_identity": protocol.d2_setting_identity,
            "d2_authorities": {
                "resolved_set_hash": protocol.d2_resolved_set_hash,
                "submanifest_hash": protocol.d2_submanifest_hash,
                "selection_hash": protocol.d2_selection_hash,
                "groups": protocol.d2_groups,
                "candidate_outcomes": protocol.d2_candidate_outcomes,
                "ranking_decisions": protocol.d2_ranking_decisions,
            },
            "model": {
                "path": str(model_path),
                "tree_digest": model_tree_digest,
                "dimension": 384,
            },
            "source_hashes": source_hashes,
            "v1_byte_preservation": seal_details,
            "d2_reproduction": reproduction,
            "case_aggregates": aggregates,
            "case_channel_drift": case_drift,
            "per_channel_cases": diagnostic_rows,
            "v2_exact_invariants": {
                "cases_checked": len(cases) * 4,
                "failures": invariant_failures,
                "passed": not invariant_failures,
                "bounds": "fixed diagnostic proof bounds; never fitted or selected",
            },
            "access_accounting": {
                "new_d3_calibration_members": 0,
                "final_or_canary_members": 0,
                "d2_spent_development_groups": len(calibration_template_ids),
                "writes_to_d2_store": 0,
            },
            "thresholds_derived_from_results": False,
        }
    )
    _write(output, report)

    if not reproduction["matches_d2"]:
        outcome = "stop_diagnostic_not_reproducible"
        reason = "the frozen clean or combined D2 result did not reproduce"
    elif (
        any(value["structural_channel_drift"] for value in case_drift.values())
        or case_drift[CASE_TEST]["changed_scalar_channels"]
        or case_drift[CASE_TEST]["embedding_moved"]
    ):
        outcome = "stop_feature_boundary_wrong"
        reason = "a structural rename or test-only input reached a fitted v1 channel"
    elif unregistered_action_reversals:
        outcome = "stop_unregistered_feature_response"
        reason = "an action reversed through a channel outside the registered v2 response"
    elif invariant_failures:
        outcome = "stop_v2_exact_invariant_failure"
        reason = "correction-ranking-v2 did not satisfy every declared exact invariant"
    else:
        outcome = "proceed"
        reason = (
            "only the pre-registered lexical, candidate-delta, query-cosine, and diff-shape "
            "channels moved; v2 is exact across all spent-D2 excluded-input cases"
        )
    decision = _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W1",
            "items": ["S21D3-027"],
            "recorded_at": recorded_at,
            "pre_registration_sha256": pre_registration_hash,
            "diagnostic_sha256": _hash_bytes(output.read_bytes()),
            "diagnostic_integrity_content_hash": report["integrity_content_hash"],
            "outcome": outcome,
            "reason": reason,
            "rule_trace": {
                "d2_reproduced": reproduction["matches_d2"],
                "structural_or_test_boundary_failure": outcome == "stop_feature_boundary_wrong",
                "unregistered_action_reversals": unregistered_action_reversals,
                "v2_invariant_failures": invariant_failures,
                "response": "correction-ranking-v2 only",
            },
            "opened": (
                ["S21D3-028", "S21D3-030", "S21D3-031", "S21D3-032"]
                if outcome == "proceed"
                else ["independent_retrieval", "release_work"]
            ),
            "not_opened": (
                []
                if outcome == "proceed"
                else ["campaign", "fitting", "final", "promotion", "activation"]
            ),
            "improvised_feature_branch": False,
        }
    )
    _write(continuation_output, decision)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=EVIDENCE / "sprint-21d3-channel-invariance-diagnostic.json",
    )
    parser.add_argument(
        "--continuation-output",
        type=Path,
        default=EVIDENCE / "sprint-21d3-diagnostic-continuation.json",
    )
    arguments = parser.parse_args()
    asyncio.run(_run(arguments.output, arguments.continuation_output, arguments.model))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
