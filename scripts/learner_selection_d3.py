#!/usr/bin/env python
"""S21D3-038 and -039: the fresh metamorphic set, the ladder, the grid, and one selection.

Two items, one command, because the second may not read a number the first has not finished
producing. The order is:

1. resolve the 120 sealed calibration transformation cases — six per fresh group — by
   *executing* every transformed candidate against its own hidden suite, so each case carries
   four independently verified labels rather than four labels carried over from the clean task;
2. derive the strongest deterministic baseline from the ladder;
3. measure all 24 frozen k-NN settings on the clean calibration groups and on the resolved
   metamorphic set;
4. apply the frozen selection rule and the revision-3 non-silence rules, and record one
   candidate or one null.

Every transformed feature record is sealed before its transformed candidate runs, exactly as the
clean campaign seals before execution. The metamorphic executions are prechecks: they run in a
throwaway directory, produce no learned observation, enter no dataset, and count towards no
outcome floor — what they do count towards is condition 20's *ranking-decision* denominator,
which is one decision per case and never four.

    scripts/learner_selection_d3.py --campaign <campaign.json> --model <minilm> --output <json>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.application.ports.embedding_provider import (  # noqa: E402
    EmbeddingProviderPort,
)
from cognitive_os.coding.reality_task_specs_d2 import module_source  # noqa: E402
from cognitive_os.coding.reality_task_specs_d3 import D3_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.infrastructure.embeddings import build_embedding_provider, minilm  # noqa: E402
from cognitive_os.learning import transformations_d3  # noqa: E402
from cognitive_os.learning.calibration_ood import (  # noqa: E402
    OodCaseResultV3,
    OodSubmanifestV3,
    build_ood_precheck_v3,
)
from cognitive_os.learning.correction_catalogue_d3 import (  # noqa: E402
    CALIBRATION_STAGE,
    MINIMUM_VALID_DECISIONS_PER_STAGE,
    seal_d3_corpus,
)
from cognitive_os.learning.correction_features import (  # noqa: E402
    canonical_embedding_windows,
    feature_input_v2,
    pool_canonical_embedding,
)
from cognitive_os.learning.correction_ladder import (  # noqa: E402
    build_ladder,
    eligible_rungs,
    group_candidates,
)
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow  # noqa: E402
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionEvaluatorManifest,
    CorrectionFeatureContractV2,
    CorrectionPartition,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionEncoderV2,
    CorrectionFeatureVector,
    CorrectionKnn,
    Exemplar,
    NumericBoundsV2,
)
from cognitive_os.learning.knn_calibration import (  # noqa: E402
    CandidateSelection,
    CorrectionCalibration,
    MeasuredSetting,
    OodPrecheck,
    apply_selection_rule,
    decide_continuation,
    declared_grid,
    grid_hash,
    settings_hash_for,
)

from cognitive_os.coding.reality_tasks import template  # noqa: E402  isort:skip
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402  isort:skip

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d3-pre-registration.json"

#: Fifty of the corpus's inference calls per task is nowhere near the 250 ms budget, but the
#: budget is a gate condition and a number nobody measures is a number nobody honours.
_INFERENCE_SAMPLE = 4


def _hash(text: str) -> str:
    return sha256(text.encode()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _write(path: Path, value: dict[str, Any]) -> None:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _hash(_canonical_bytes(value).decode())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sealed, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _embedding(model: Path):  # type: ignore[no-untyped-def]
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


async def _embed_windows(
    embed: EmbeddingProviderPort, sources: Sequence[str]
) -> tuple[tuple[float, ...], ...]:
    """One pooled vector per source, batched over every window of every source."""
    windows = [canonical_embedding_windows(source) for source in sources]
    flat = tuple(text for group in windows for text in group)
    produced: list[tuple[float, ...]] = []
    for start in range(0, len(flat), 64):
        produced.extend(await embed.embed_documents(flat[start : start + 64]))
    pooled: list[tuple[float, ...]] = []
    cursor = 0
    for group in windows:
        pooled.append(pool_canonical_embedding(produced[cursor : cursor + len(group)]))
        cursor += len(group)
    return tuple(pooled)


# --------------------------------------------------------------- S21D3-038: metamorphic set


@dataclass(frozen=True, slots=True)
class _Case:
    """One sealed transformation case, resolved into executable text.

    `bodies` is keyed by the *sealed candidate id*, not by authoring index, so a transformed
    decision and its clean decision are comparable candidate by candidate. Without that,
    "the first action was preserved" could only be checked positionally, and the position is
    exactly what a ranker is allowed to change.
    """

    case_id: str
    case_name: str
    group: str
    template_id: str
    module: str
    bodies: dict[str, str]
    order: tuple[str, ...]
    hidden_test: str


def _resolve_cases(
    submanifest: OodSubmanifestV3, *, slots: dict[str, dict[str, int]]
) -> tuple[tuple[_Case, ...], list[str]]:
    """Turn every sealed case identity into a transformed package. No score is read here."""
    by_group = {spec.repository_group: spec for spec in D3_CALIBRATION_SPECS}
    cases: list[_Case] = []
    inapplicable: list[str] = []
    for case in submanifest.cases:
        spec = by_group[case.source_group_id]
        try:
            transformed = transformations_d3.transform(
                case.case_name,
                module_source=module_source(spec, spec.baseline),
                variants=tuple(module_source(spec, body) for body in spec.variants),
                visible_test=spec.visible_test,
                hidden_test=spec.hidden_test,
                issue=spec.issue,
            )
        except transformations_d3.PerturbationError as error:  # pragma: no cover - eligibility
            inapplicable.append(f"{case.case_id}:{error}")
            continue
        variant_of = slots[case.source_group_id]
        cases.append(
            _Case(
                case_id=case.case_id,
                case_name=case.case_name,
                group=case.source_group_id,
                template_id=spec.template_id,
                module=spec.module,
                bodies={
                    candidate_id: transformed.variants[variant_of[candidate_id]]
                    for candidate_id in case.candidate_ids
                },
                order=case.candidate_ids,
                hidden_test=transformed.hidden_test,
            )
        )
    return tuple(cases), inapplicable


def _execute_case(job: tuple[str, str, str, str]) -> tuple[str, bool]:
    """Run one transformed candidate's hidden suite. A precheck, never a governed outcome."""
    key, module, body, hidden = job
    with tempfile.TemporaryDirectory(prefix="cogos-d3-meta-") as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(body, encoding="utf-8")
        (root / "test_hidden.py").write_text(hidden, encoding="utf-8")
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_hidden.py"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        return key, done.returncode == 0


def _execute_cases(cases: Sequence[_Case]) -> dict[str, bool]:
    jobs = [
        (f"{case.case_id}#{candidate_id}", case.module, case.bodies[candidate_id], case.hidden_test)
        for case in cases
        for candidate_id in case.order
    ]
    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4) * 2)) as pool:
        return dict(pool.map(_execute_case, jobs))


@dataclass(frozen=True, slots=True)
class _ResolvedCase:
    """One case with its sealed transformed vectors and its four executed labels."""

    case: _Case
    vectors: dict[str, CorrectionFeatureVector]
    accepted: dict[str, bool]
    #: The clean group's labels, so a transformed package whose verifier changed its mind is
    #: reported as a label change rather than counted against the ranker.
    clean_accepted: dict[str, bool]
    feature_hashes: tuple[str, ...]
    sealed_at: datetime
    executed_at: datetime


async def _resolve_metamorphic(
    submanifest: OodSubmanifestV3,
    *,
    embed: EmbeddingProviderPort,
    bounds: NumericBoundsV2,
    slots: dict[str, dict[str, int]],
    clean_accepted: dict[str, dict[str, bool]],
) -> tuple[tuple[_ResolvedCase, ...], list[str], dict[str, Any]]:
    cases, inapplicable = _resolve_cases(submanifest, slots=slots)

    # Seal first. Every transformed feature record is encoded and hashed before the transformed
    # candidate that it describes is executed, so the chronology holds for the metamorphic set
    # exactly as it holds for the clean campaign.
    sources = [case.bodies[candidate_id] for case in cases for candidate_id in case.order]
    vectors = await _embed_windows(embed, sources)
    encoder = CorrectionEncoderV2(bounds)
    sealed_at = utc_now()
    resolved_vectors: list[dict[str, CorrectionFeatureVector]] = []
    hashes: list[tuple[str, ...]] = []
    cursor = 0
    for case in cases:
        per_case: dict[str, CorrectionFeatureVector] = {}
        for candidate_id in case.order:
            per_case[candidate_id] = encoder.encode(
                feature_input_v2(
                    candidate_source=case.bodies[candidate_id],
                    canonical_candidate_source_embedding=vectors[cursor],
                )
            )
            cursor += 1
        resolved_vectors.append(per_case)
        hashes.append(tuple(per_case[key].content_hash() for key in case.order))

    labels = _execute_cases(cases)
    executed_at = utc_now()
    if executed_at <= sealed_at:  # pragma: no cover - the clock only moves forward
        raise SystemExit("the transformed features were not sealed before their execution")

    resolved = tuple(
        _ResolvedCase(
            case=case,
            vectors=per_case,
            accepted={
                candidate_id: labels[f"{case.case_id}#{candidate_id}"]
                for candidate_id in case.order
            },
            clean_accepted=clean_accepted[case.group],
            feature_hashes=case_hashes,
            sealed_at=sealed_at,
            executed_at=executed_at,
        )
        for case, per_case, case_hashes in zip(cases, resolved_vectors, hashes, strict=True)
    )
    report = {
        "submanifest_hash": submanifest.content_hash,
        "stage": submanifest.stage,
        "generator_code_hash": submanifest.generator_code_hash,
        "hard_coded_oracle_hash": submanifest.hard_coded_oracle_hash,
        "nominal_cases": len(submanifest.cases),
        "applicable_cases": len(resolved),
        "not_applicable": inapplicable,
        "source_groups": len({case.group for case in cases}),
        "candidate_outcomes_executed": len(labels),
        "features_sealed_at": sealed_at.isoformat(),
        "first_transformed_execution_at": executed_at.isoformat(),
        "every_transformed_seal_precedes_its_execution": True,
        "cases_by_name": {
            name: sum(1 for case in cases if case.case_name == name)
            for name in transformations_d3.CASES
        },
        "optional_probes_excluded_from_the_floor": list(transformations_d3.OPTIONAL_PROBES),
        "verifier_label_changes": sum(
            1
            for item in resolved
            for candidate_id in item.case.order
            if item.accepted[candidate_id] != item.clean_accepted[candidate_id]
        ),
        "entered_any_dataset": False,
        "fitted": False,
        "final_or_canary_access": 0,
        "resolved_set_hash": _hash(
            "\n".join(
                f"{item.case.case_id}:{':'.join(item.feature_hashes)}:"
                f"{''.join(str(int(item.accepted[key])) for key in sorted(item.accepted))}"
                for item in resolved
            )
        ),
    }
    return resolved, inapplicable, report


# ------------------------------------------------------------- S21D3-039: ladder and grid


def _clean_groups(campaign: dict[str, Any]) -> dict[str, Any]:
    calibration = next(
        item for item in campaign["partitions"] if item["partition"] == "calibration"
    )
    return calibration


def _matrix_from(
    outcomes: Sequence[dict[str, Any]],
    seal_records: dict[str, Any],
    *,
    split: str,
    partition: str,
    sealed_at: datetime,
) -> FittedMatrix:
    rows = []
    for item in outcomes:
        record = seal_records[item["candidate_id"]]
        rows.append(
            FittedRow(
                candidate_id=UUID(item["candidate_id"]),
                task_id=UUID(record["task_id"]),
                group=item["group"],
                partition=partition,
                vector=CorrectionFeatureVector(
                    encoder_version=record["encoder_version"],
                    values=tuple((name, value) for name, value in record["values"]),
                    embedding=tuple(record["embedding"]),
                ),
                accepted=item["accepted"],
                sealed_at=sealed_at,
                outcome_at=sealed_at,
                observation_id=UUID(item["observation_id"]),
                sealed_feature_hash=record["feature_vector_hash"],
            )
        )
    return FittedMatrix(split=split, rows=tuple(rows))


@dataclass(frozen=True, slots=True)
class _CleanGroup:
    """One fresh calibration group as both stages see it: one order, four vectors, four labels."""

    group: str
    order: tuple[str, ...]
    vectors: dict[str, CorrectionFeatureVector]
    accepted: dict[str, bool]
    baseline_first_choice: str


def _measure(
    setting: Any,
    *,
    fit_rows: Sequence[FittedRow],
    clean: Sequence[_CleanGroup],
    resolved: Sequence[_ResolvedCase],
) -> tuple[MeasuredSetting, tuple[OodCaseResultV3, ...], dict[str, Any]]:
    """One grid point, on the clean groups and on every resolved metamorphic case."""
    knn = CorrectionKnn(
        tuple(Exemplar(vector=row.vector, accepted=row.accepted) for row in fit_rows),
        k=setting.k,
        similarity_floor=setting.similarity_floor,
        agreement_floor=setting.agreement_floor,
        confidence_floor=setting.confidence_floor,
        embedding_weight=setting.embedding_weight,
    )

    states: dict[str, dict[str, Any]] = {}
    answered = 0
    correct = 0
    changed = 0
    slowest = Decimal("0")
    for item in clean:
        started = datetime.now(UTC)
        ranking = knn.rank(item.vectors, baseline_order=item.order)
        elapsed = Decimal(str(round((datetime.now(UTC) - started).total_seconds() * 1000, 3)))
        slowest = max(slowest, elapsed)
        first = ranking.first_choice
        states[item.group] = {
            "answered": not ranking.abstained,
            "first_choice": first,
            "correct": bool(first and item.accepted[first]),
            "changed": (not ranking.abstained) and first != item.baseline_first_choice,
            "baseline_correct": item.accepted[item.baseline_first_choice],
        }
        if not ranking.abstained:
            answered += 1
            correct += bool(first and item.accepted[first])
            changed += first != item.baseline_first_choice

    results: list[OodCaseResultV3] = []
    for item in resolved:
        state = states[item.case.group]
        ranking = knn.rank(item.vectors, baseline_order=item.case.order)
        first = ranking.first_choice
        covered = bool(state["answered"]) and not ranking.abstained
        results.append(
            OodCaseResultV3(
                case_id=item.case.case_id,
                source_group_id=item.case.group,
                clean_answered=bool(state["answered"]),
                answered=not ranking.abstained,
                abstained=ranking.abstained,
                clean_first_choice_correct=bool(state["correct"]),
                baseline_first_choice_correct=bool(state["baseline_correct"]),
                clean_changed_action=bool(state["changed"]),
                # The whole point of a metamorphic case: the transformed package states the
                # same contract in different words, so the ranker must reach the same first
                # action. Comparison is by candidate identity, which the transformation does
                # not move.
                action_preserved=(first == state["first_choice"]) if covered else None,
                transformed_changed_action=(
                    (not ranking.abstained) and first != item.case.order[0]
                ),
                confident_error=(not ranking.abstained)
                and not bool(first and item.accepted[first]),
                verifier_failures=0,
                label_changes=sum(
                    1
                    for candidate_id in item.case.order
                    if item.accepted[candidate_id] != item.clean_accepted[candidate_id]
                ),
            )
        )

    decisions = Decimal(len(clean))
    measured = MeasuredSetting(
        setting=setting,
        first_choice_rate=Decimal(correct) / decisions,
        coverage=Decimal(answered) / decisions,
        changed_decisions=changed,
        confident_ood_errors=sum(item.confident_error for item in results),
        ood_answered=sum(item.answered for item in results),
        maximum_inference_ms=slowest,
    )
    detail = {
        "clean_decisions": len(clean),
        "clean_answered": answered,
        "clean_correct": correct,
        "clean_changed": changed,
        "metamorphic_ranking_decisions": len(results),
        "metamorphic_answered": measured.ood_answered,
        "metamorphic_candidate_outcomes": len(results) * 4,
    }
    return measured, tuple(results), detail


async def _run(campaign_path: Path, model: Path, output: Path, metamorphic_output: Path) -> int:
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    if campaign.get("final_outcomes_inspected"):  # pragma: no cover - defensive
        raise SystemExit("the campaign evidence claims final access; refusing to calibrate")

    bundle = seal_d3_corpus()
    submanifest = bundle.calibration_transformations
    if submanifest.stage != CALIBRATION_STAGE:  # pragma: no cover - defensive
        raise SystemExit("the calibration submanifest names another stage")
    transformations_d3.check_golden_pairs()

    seals = _load_seals(campaign)
    fitting = next(item for item in campaign["partitions"] if item["partition"] == "training")
    calibration = next(
        item for item in campaign["partitions"] if item["partition"] == "calibration"
    )
    fit_records = {record["candidate_id"]: record for record in seals["training"]["records"]}
    calibration_records = {
        record["candidate_id"]: record for record in seals["calibration"]["records"]
    }
    fit_matrix = _matrix_from(
        fitting["candidate_outcomes"],
        fit_records,
        split="fit",
        partition="training",
        sealed_at=datetime.fromisoformat(fitting["features_sealed_at"]),
    )
    calibration_matrix = _matrix_from(
        calibration["candidate_outcomes"],
        calibration_records,
        split="calibration",
        partition="calibration",
        sealed_at=datetime.fromisoformat(calibration["features_sealed_at"]),
    )

    # The frozen order, the slot-to-variant binding and the deterministic baseline material,
    # all read off the sealed catalogue rather than off the campaign's output.
    order_by_group: dict[str, tuple[str, ...]] = {}
    variant_of: dict[str, dict[str, int]] = {}
    requirement_texts: dict[str, str] = {}
    delta_texts: dict[str, str] = {}
    for group in bundle.catalogues[CorrectionPartition.CALIBRATION].groups:
        ordered = sorted(group.slots, key=lambda slot: slot.position)
        order_by_group[group.repository_group] = tuple(str(slot.candidate_id) for slot in ordered)
        variant_of[group.repository_group] = {
            str(slot.candidate_id): slot.variant_index for slot in ordered
        }
        item = template(group.template_id)
        requirement_texts[group.repository_group] = (
            f"{item.issue_description}\n{item.expected_behavior}"
        )
        module_path = next(path for path in item.visible_files if path.startswith("src/"))
        for slot in ordered:
            recipe = RealityCandidateStrategy(slot.recipe)
            delta_texts[str(slot.candidate_id)] = item.neutral_candidate_sources[recipe][
                module_path
            ]

    accepted_by_candidate = {
        item["candidate_id"]: item["accepted"] for item in calibration["candidate_outcomes"]
    }
    vectors_by_group: dict[str, dict[str, CorrectionFeatureVector]] = {}
    for row in calibration_matrix.rows:
        vectors_by_group.setdefault(row.group, {})[str(row.candidate_id)] = row.vector

    ladder = build_ladder(
        calibration_matrix,
        order=order_by_group,
        requirement_texts=requirement_texts,
        delta_texts=delta_texts,
        created_at=utc_now(),
    )
    baseline_order = _baseline_orderings(
        calibration_matrix,
        ladder=ladder,
        order=order_by_group,
        requirement_texts=requirement_texts,
        delta_texts=delta_texts,
    )

    clean = tuple(
        _CleanGroup(
            group=group,
            order=order,
            vectors=vectors_by_group[group],
            accepted={item: accepted_by_candidate[item] for item in order},
            baseline_first_choice=baseline_order[group][0],
        )
        for group, order in sorted(order_by_group.items())
    )

    embed, model_digest = _embedding(model)
    resolved, inapplicable, metamorphic = await _resolve_metamorphic(
        submanifest,
        embed=embed,
        bounds=_bounds_from(seals["training"]),
        slots=variant_of,
        clean_accepted={item.group: item.accepted for item in clean},
    )
    valid = len(resolved)
    if valid < MINIMUM_VALID_DECISIONS_PER_STAGE:
        raise SystemExit(
            f"{valid} valid metamorphic decisions against a floor of "
            f"{MINIMUM_VALID_DECISIONS_PER_STAGE}; substituting groups after the seal is not "
            "an option"
        )
    resolved_manifest = submanifest_with(submanifest, resolved)

    manifest = CorrectionEvaluatorManifest()
    measurements = []
    prechecks = {}
    details: dict[str, dict[str, Any]] = {}
    for setting in declared_grid():
        measured, results, detail = _measure(
            setting, fit_rows=fit_matrix.rows, clean=clean, resolved=resolved
        )
        measurements.append(measured)
        prechecks[setting.identity] = build_ood_precheck_v3(resolved_manifest, results)
        details[setting.identity] = detail

    results, selected = apply_selection_rule(measurements, manifest=manifest)

    # The revision-3 non-silence rules sit on top of the released filter: a setting that
    # survives it still has to clear coverage, action preservation and the changed-clean floor
    # before it may be selected. §2.3 calls this a supplement, never a relaxation.
    non_silence_failures = {
        identity: list(precheck.ineligible_reasons)
        for identity, precheck in prechecks.items()
        if not precheck.selection_eligible
    }
    non_silence_filtered = None
    if selected is not None and not prechecks[selected.identity].selection_eligible:
        non_silence_filtered = selected.identity
        selected = None

    reference = selected.identity if selected is not None else declared_grid()[0].identity
    precheck = prechecks[reference]
    calibration_record = CorrectionCalibration(
        grid_identity=grid_hash(),
        settings_attempted=len(results),
        calibration_matrix_hash=calibration_matrix.content_hash,
        ladder_hash=ladder.content_hash,
        baseline_rung=ladder.strongest_non_learned_name,
        baseline_rate=ladder.strongest_non_learned_rate,
        results=results,
        ood=OodPrecheck(
            submanifest_hash=resolved_manifest.content_hash,
            resolved_set_hash=metamorphic["resolved_set_hash"],
            groups=precheck.counts.task_groups,
            decisions=precheck.counts.ranking_decisions,
            abstained=precheck.counts.abstained_decisions,
            confident_errors=precheck.counts.confident_errors,
        ),
        selected_setting_identity=None if selected is None else selected.identity,
        selected_settings_hash=None if selected is None else settings_hash_for(selected),
        created_at=utc_now(),
    )
    continuation = decide_continuation(
        calibration_record, manifest=manifest, baseline=ladder.baseline, created_at=utc_now()
    )
    contract = CorrectionFeatureContractV2()
    datasets = campaign["snapshot"]["datasets"]
    selection = CandidateSelection(
        selected=selected is not None,
        learner_kind=None if selected is None else "bounded_cosine_knn",
        settings_identity=None if selected is None else selected.identity,
        settings_hash=None if selected is None else settings_hash_for(selected),
        feature_contract_hash=contract.content_hash,
        fitted_feature_report_hash=campaign["snapshot"]["fitted_matrix"]["report_hash"],
        training_dataset_id=None if selected is None else datasets["fitting"]["dataset_id"],
        calibration_dataset_id=None if selected is None else datasets["calibration"]["dataset_id"],
        example_manifest_hash=datasets["fitting"]["example_manifest_hash"],
        split_manifest_hash=datasets["fitting"]["split_manifest_hash"],
        baseline_rung=ladder.strongest_non_learned_name,
        baseline_rate=ladder.strongest_non_learned_rate,
        continuation_hash=continuation.content_hash,
        null_reason=(
            None
            if selected is not None
            else "no frozen k-NN setting cleared both the released selection rule and the "
            "revision-3 non-silence rules on the fresh calibration and metamorphic evidence"
        ),
        created_at=utc_now(),
    )

    pre_hash = _hash(PRE_REGISTRATION.read_text())
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    _write(
        metamorphic_output,
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W2",
            "items": ["S21D3-038"],
            "recorded_at": recorded_at,
            "pre_registration_sha256": pre_hash,
            "final_outcomes_inspected": False,
            "purpose": (
                "Resolve the sealed fresh-calibration transformation cases by executing every "
                "transformed candidate, so each case is one ranking decision backed by four "
                "independently verified candidate outcomes."
            ),
            "valid_decisions": valid,
            "minimum_valid_decisions": MINIMUM_VALID_DECISIONS_PER_STAGE,
            "candidate_outcomes": valid * 4,
            "minimum_candidate_outcomes": MINIMUM_VALID_DECISIONS_PER_STAGE * 4,
            "decision_ids": [item.case.case_id for item in resolved],
            "embedding_tree_digest": model_digest,
            "applicability_ledger": {
                "nominal": len(submanifest.cases),
                "applicable": valid,
                "not_applicable": inapplicable,
            },
            **metamorphic,
        },
    )
    _write(
        output,
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W2",
            "items": ["S21D3-039"],
            "recorded_at": recorded_at,
            "pre_registration_sha256": pre_hash,
            "final_outcomes_inspected": False,
            "purpose": (
                "Derive the strongest deterministic baseline, measure all twenty-four frozen "
                "k-NN settings on fresh evidence, and record one candidate or one null."
            ),
            "baseline_ladder": {
                "hash": ladder.content_hash,
                "groups": ladder.groups,
                "strongest_non_learned_rung": ladder.strongest_non_learned_name,
                "strongest_non_learned_rate": ladder.strongest_non_learned_rate,
                "rungs": [
                    {
                        "name": rung.name,
                        "kind": rung.kind,
                        "eligible": rung.eligible,
                        "first_choice_rate": rung.first_choice_rate,
                        "ineligible_reason": rung.ineligible_reason,
                    }
                    for rung in ladder.rungs
                ],
            },
            "grid": {
                "identity": grid_hash(),
                "settings_attempted": len(results),
                "embedding_weight": "0.7",
                "parametric_rungs_opened": [],
                "non_silence_filtered_the_released_winner": non_silence_filtered,
            },
            "settings": [
                {
                    **json.loads(item.model_dump_json(exclude={"content_hash"})),
                    **details[item.setting_identity],
                    "non_silence_failures": non_silence_failures.get(item.setting_identity, []),
                    "metamorphic": json.loads(
                        prechecks[item.setting_identity].model_dump_json(exclude={"content_hash"})
                    ),
                }
                for item in results
            ],
            "calibration_record_hash": calibration_record.content_hash,
            "continuation": json.loads(continuation.model_dump_json()),
            "selection": json.loads(selection.model_dump_json()),
            "selection_before_final_access": True,
            "final_or_canary_outcomes_inspected": 0,
            "retrieval_holdout_opened": False,
            "dependent_not_opened": (
                []
                if selection.selected
                else [
                    "S21D3-051 fit and store the selected artifact",
                    "S21D3-054 selected-artifact vertical slice",
                    "S21D3-056 REGISTERED to SHADOW",
                    "S21D3-059 pre-final checkpoint",
                    "S21D3-060 through S21D3-069 final evaluation and promotion",
                    "S21D3-070 through S21D3-077 approval, canary, activation and rollback",
                ]
            ),
        },
    )
    print(
        json.dumps(
            {
                "selected": selection.selected,
                "baseline": ladder.strongest_non_learned_rate,
                "valid_metamorphic_decisions": valid,
                "output": output.as_posix(),
            },
            indent=2,
        )
    )
    return 0


def _baseline_orderings(
    matrix: FittedMatrix,
    *,
    ladder: Any,
    order: dict[str, tuple[str, ...]],
    requirement_texts: dict[str, str],
    delta_texts: dict[str, str],
) -> dict[str, tuple[str, ...]]:
    """The strongest deterministic rung's ordering per group.

    "Changed decision" and "the baseline was right" both mean *against the strongest rung*, not
    against the sealed input order, so the ordering the ladder derived is the one to compare to.
    """
    ordering = eligible_rungs(matrix.rows[0].vector.encoder_version)[
        ladder.strongest_non_learned_name
    ]
    groups = group_candidates(
        matrix, order=order, requirement_texts=requirement_texts, delta_texts=delta_texts
    )
    return {item.group: ordering(item) for item in groups}


def submanifest_with(
    submanifest: OodSubmanifestV3, resolved: Sequence[_ResolvedCase]
) -> OodSubmanifestV3:
    """The submanifest narrowed to the cases that actually resolved.

    `build_ood_precheck_v3` requires results for every case it names. An inapplicable case is
    reported in the applicability ledger and excluded here rather than counted as an abstention,
    because an abstention is a decision the ranker made and this is one it never saw. Rebuilt
    rather than copied, so the validators run on the narrowed set too.
    """
    keep = {item.case.case_id for item in resolved}
    if keep == {case.case_id for case in submanifest.cases}:
        return submanifest
    return OodSubmanifestV3(
        stage=submanifest.stage,
        source_manifest_hash=submanifest.source_manifest_hash,
        generator_code_hash=submanifest.generator_code_hash,
        hard_coded_oracle_hash=submanifest.hard_coded_oracle_hash,
        cases=tuple(case for case in submanifest.cases if case.case_id in keep),
    )


def _load_seals(campaign: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The sealed v2 feature records, read back from the artifact the campaign stored."""
    root = Path(os.environ["COGOS_ARTIFACT_ROOT"])
    seals: dict[str, dict[str, Any]] = {}
    for entry in campaign["partitions"]:
        wanted = entry["feature_set_hash"]
        found = None
        for path in (root / "sha256").glob("*/*"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if payload.get("content_hash") == wanted:
                found = payload
                break
        if found is None:
            raise SystemExit(f"no stored feature seal reproduces {wanted}")
        seals[entry["partition"]] = found
    return seals


def _bounds_from(seal: dict[str, Any]) -> NumericBoundsV2:
    """The bounds the fitting seal recorded, read back rather than refitted.

    Refitting them here would fit the encoder on whatever this command was handed, and the
    transformed packages would then be scaled by a different ruler than the clean ones.
    """
    return NumericBoundsV2(
        lower={name: float(value) for name, value in seal["numeric_lower"]},
        upper={name: float(value) for name, value in seal["numeric_upper"]},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(os.environ.get("COGOS_LOCAL_EMBEDDING_MODEL_PATH", "models/all-MiniLM-L6-v2")),
    )
    parser.add_argument(
        "--output", type=Path, default=EVIDENCE / "sprint-21d3-learner-selection.json"
    )
    parser.add_argument(
        "--metamorphic-output",
        type=Path,
        default=EVIDENCE / "sprint-21d3-calibration-metamorphic.json",
    )
    arguments = parser.parse_args()
    return asyncio.run(
        _run(arguments.campaign, arguments.model, arguments.output, arguments.metamorphic_output)
    )


if __name__ == "__main__":  # pragma: no cover - operator entry point
    raise SystemExit(main())
