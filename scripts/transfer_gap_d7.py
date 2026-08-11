#!/usr/bin/env python3
"""S21D7 groundwork: the §4 transfer-gap measurement, and the class diagnostic it licenses.

The D7 handoff authorises exactly one successor experiment before anything else varies:
"measure the transfer gap directly" — the released deterministic ladder over both spent
corpora, every rung, reported per family, and the same sealed direction's first-choice rate
on each, with the learned-minus-baseline difference as the pre-registered quantity. §4 prices
it: no authoring, no new contract, every input released and sealed. This script is that
measurement, plus the one continuation the handoff's own decision rule opens: *if the
difference collapses, the class question is the right one* — so the same record carries a
diagnostic of the containment contrastive class on the same spent bytes, under the same
licence D5's groundwork exercised when it fitted its class proposal on D4's spent evidence
("the spent calibration set remain[s] valid *fitting* and *diagnostic* evidence").

What this script never does: it selects nothing, derives no threshold for reuse — the
conformal bar it simulates is reported as a diagnostic and discarded, and the successor's
own W-stage must re-derive one under its pre-registration — opens no final, batch-B or
canary body, writes to no store, and re-decides no released stop. The D6 certification set
stays spent: numbers measured over it here are groundwork for a proposal, and the class it
motivates must certify on a fresh corpus it has never seen.

Read-only against both stores, resolved by published content hashes with no database:

    UV_CACHE_DIR=.cache/uv uv run python scripts/transfer_gap_d7.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_task_specs_d6 import D6_CERTIFICATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.learning import transformations_d3  # noqa: E402
from cognitive_os.learning.conformal_operating_point import (  # noqa: E402
    admitted_error_upper_bound,
    conformal_rank,
)
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    FIT_RULE,
    FITTED_RELATIONAL_CHANNELS,
    HYPOTHESIS_CLASS,
    ContainmentContrastiveRanker,
    RelationalGroup,
    fit_containment_direction,
    relational_numbers,
)
from cognitive_os.learning.correction_catalogue_d5 import (  # noqa: E402
    build_d5_fitting_catalogue,
    seal_d5_corpus,
)
from cognitive_os.learning.correction_catalogue_d6 import seal_d6_corpus  # noqa: E402
from cognitive_os.learning.correction_features import (  # noqa: E402
    SealedFeatureRecordSetV2,
)
from cognitive_os.learning.correction_ladder import (  # noqa: E402
    eligible_rungs,
    group_candidates,
)
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow  # noqa: E402
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionFeatureVector,
)
from cognitive_os.learning.pairwise_contrastive import (  # noqa: E402
    PairwiseContrastiveModel,
)
from cognitive_os.learning.repair_containment import containment_ordering  # noqa: E402
from cognitive_os.learning.transfer_gap import (  # noqa: E402
    CorpusHalf,
    measure_transfer_gap,
)

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
OUTPUT = EVIDENCE / "sprint-21d7-transfer-gap.json"

D5_FEATURE_SEALS = EVIDENCE / "sprint-21d5-feature-seals.json"
D5_CALIBRATION_CAMPAIGN = EVIDENCE / "sprint-21d5-calibration-campaign.json"
D5_FITTING_CAMPAIGN = EVIDENCE / "sprint-21d5-self-play-campaign.json"
D5_SNAPSHOTS = EVIDENCE / "sprint-21d5-snapshots.json"
D6_FEATURE_SEALS = EVIDENCE / "sprint-21d6-feature-seals.json"
D6_CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d6-certification-campaign.json"
D6_SNAPSHOTS = EVIDENCE / "sprint-21d6-snapshots.json"
D6_DIRECTIONS = EVIDENCE / "sprint-21d6-directions.json"

#: The same read-only roots the D6 scripts named. Content-addressed stores; no database.
D5_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d5")
D6_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d6-measured")

#: The pre-registered alpha D6 measured under, reused for the *diagnostic* simulation only.
#: The successor's own bar must be re-derived under its own pre-registration.
DIAGNOSTIC_ALPHA = Decimal("0.20")
REGULARIZATION = Decimal("1")


def _digest(value: bytes | str) -> str:
    return sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _sealed_records(store: Path, seals_path: Path, partition: str) -> SealedFeatureRecordSetV2:
    """One released feature seal, resolved out of its store by the published content hash."""
    released = json.loads(seals_path.read_text(encoding="utf-8"))
    row = next(item for item in released["partitions"] if item["partition"] == partition)
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
            if _digest(path.read_bytes()) != path.name:
                raise SystemExit(f"{path.name} does not hash to its own content address")
            return SealedFeatureRecordSetV2.model_validate_json(path.read_text(encoding="utf-8"))
    raise SystemExit(
        f"the released {partition} feature seal does not resolve in {store.name}; the "
        "evidence this measurement reads cannot be found, and re-deriving it would replace "
        "sealed bytes with this script's opinion of them"
    )


def _matrix(
    seal: SealedFeatureRecordSetV2, campaign_path: Path, *, split: str, published_hash: str
) -> FittedMatrix:
    """A released matrix rebuilt from its sealed vectors and released labels, then proved."""
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    rows = tuple(
        FittedRow(
            candidate_id=UUID(str(item["candidate_id"])),
            task_id=UUID(str(item["task_id"])),
            group=str(item["group"]),
            partition="calibration" if split == "calibration" else "fit",
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
    matrix = FittedMatrix(split=split, rows=rows)
    if matrix.content_hash != published_hash:
        raise SystemExit(
            f"the rebuilt {split} matrix is not the published one: {matrix.content_hash} "
            f"against {published_hash}; a rate over drifted rows is a rate about nothing"
        )
    return matrix


def _direction(model_hash: str) -> PairwiseContrastiveModel:
    """One of D5's sealed directions, out of its content-addressed store, read-only."""
    for path in sorted(D5_ARTIFACT_ROOT.rglob("*")):
        if not path.is_file() or len(path.name) != 64:
            continue
        data = path.read_bytes()
        if b'"hypothesis_class"' not in data:
            continue
        try:
            payload = json.loads(data.decode())
            model = PairwiseContrastiveModel(
                encoder_version=str(payload["encoder_version"]),
                feature_names=tuple(str(name) for name in payload["feature_names"]),
                weights=tuple(float(weight) for weight in payload["weights"]),
                regularization=str(payload["regularization"]),
                fitted_group_count=int(payload["fitted_group_count"]),
                fitted_pair_count=int(payload["fitted_pair_count"]),
            )
        except (KeyError, ValueError):
            continue
        if model.content_hash() == model_hash:
            if _digest(data) != path.name:
                raise SystemExit(f"{path.name} does not hash to its own content address")
            return model
    raise SystemExit(f"direction {model_hash} does not resolve in {D5_ARTIFACT_ROOT.name}")


def _catalogue_maps(catalogue: Any) -> tuple[dict, dict, dict, dict, dict]:
    """Order, requirement text, candidate texts, family and baseline source per group."""
    order: dict[str, tuple[str, ...]] = {}
    requirement: dict[str, str] = {}
    delta: dict[str, str] = {}
    family: dict[str, str] = {}
    baseline: dict[str, str] = {}
    for group in catalogue.groups:
        item = template(group.template_id)
        order[group.repository_group] = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        requirement[group.repository_group] = f"{item.issue_description}\n{item.expected_behavior}"
        family[group.repository_group] = group.family
        module_path = next(path for path in item.visible_files if path.startswith("src/"))
        baseline[group.repository_group] = item.visible_files[module_path]
        for slot in group.slots:
            recipe = RealityCandidateStrategy(slot.recipe)
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[recipe][module_path]
    return order, requirement, delta, family, baseline


def _learned_verdicts(
    matrix: FittedMatrix, order: dict[str, tuple[str, ...]], model: PairwiseContrastiveModel
) -> dict[str, bool]:
    """The sealed direction's first-choice verdict per group, ties on the frozen order."""
    scores: dict[str, dict[str, float]] = {}
    accepted: dict[str, dict[str, bool]] = {}
    for row in matrix.rows:
        scores.setdefault(row.group, {})[str(row.candidate_id)] = model.score(
            row.vector.fitted_numbers
        )
        accepted.setdefault(row.group, {})[str(row.candidate_id)] = row.accepted
    verdicts: dict[str, bool] = {}
    for name, ordered_ids in order.items():
        position = {item: index for index, item in enumerate(ordered_ids)}
        first = min(ordered_ids, key=lambda item: (-scores[name][item], position[item]))
        verdicts[name] = accepted[name][first]
    return verdicts


def _relational_groups(
    matrix: FittedMatrix,
    order: dict[str, tuple[str, ...]],
    delta: dict[str, str],
    baseline: dict[str, str],
) -> list[RelationalGroup]:
    """The seven-channel groups the containment class fits and ranks."""
    values: dict[str, dict[str, Any]] = {}
    accepted: dict[str, dict[str, bool]] = {}
    for row in matrix.rows:
        values.setdefault(row.group, {})[str(row.candidate_id)] = row.vector.values
        accepted.setdefault(row.group, {})[str(row.candidate_id)] = row.accepted
    groups = []
    for name in sorted(order):
        numbers = relational_numbers(
            values[name],
            baseline_source=baseline[name],
            sources_by_candidate={item: delta[item] for item in order[name]},
        )
        groups.append(
            RelationalGroup(group=name, order=order[name], numbers=numbers, accepted=accepted[name])
        )
    return groups


def _score_relational(
    groups: list[RelationalGroup], ranker: ContainmentContrastiveRanker
) -> list[dict[str, Any]]:
    decisions = []
    for group in groups:
        ranking = ranker.rank(group.numbers, baseline_order=group.order)
        first = ranking.ordered_candidate_ids[0]
        decisions.append(
            {
                "group": group.group,
                "first": first,
                "correct": bool(group.accepted[first]),
                "margin": str(ranking.confidence),
            }
        )
    return decisions


def _sweep(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Best Clopper-Pearson bound anywhere and at the 0.40 coverage floor, plus the
    error-free prefix depth — the three feasibility numbers D6's stop turned on."""
    ordered = sorted(decisions, key=lambda item: -Decimal(item["margin"]))
    best_any: tuple | None = None
    best_eligible: tuple | None = None
    prefix = 0
    prefix_open = True
    errors = 0
    for count, decision in enumerate(ordered, start=1):
        if not decision["correct"]:
            errors += 1
            prefix_open = False
        if prefix_open:
            prefix = count
        bound = admitted_error_upper_bound(errors, count)
        coverage = count / len(ordered)
        if best_any is None or bound < best_any[0]:
            best_any = (bound, coverage, count, errors)
        if coverage >= 0.40 and (best_eligible is None or bound < best_eligible[0]):
            best_eligible = (bound, coverage, count, errors)

    def unpack(item: tuple | None) -> dict[str, Any] | None:
        if item is None:
            return None
        return {
            "error_upper_bound_95": round(item[0], 6),
            "coverage": item[1],
            "admitted": item[2],
            "errors": item[3],
        }

    return {
        "deepest_error_free_prefix_by_margin": prefix,
        "best_anywhere": unpack(best_any),
        "best_at_coverage_floor": unpack(best_eligible),
    }


def _diagnostic_bar(
    conformal_decisions: list[dict[str, Any]],
    certification_decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """The D6 admission protocol simulated once: bar from the conformal half's wrong
    margins at the pre-registered alpha, admission strictly above it, measured on the
    certification half. Reported and discarded; nothing downstream may reuse it."""
    wrong = sorted(Decimal(item["margin"]) for item in conformal_decisions if not item["correct"])
    rank = conformal_rank(DIAGNOSTIC_ALPHA, len(wrong))
    if rank > len(wrong):
        return {"quantile_exists": False, "wrong_decisions_in_the_conformal_half": len(wrong)}
    bar = wrong[rank - 1]
    admitted = [item for item in certification_decisions if Decimal(item["margin"]) > bar]
    errors = sum(1 for item in admitted if not item["correct"])
    return {
        "quantile_exists": True,
        "alpha": str(DIAGNOSTIC_ALPHA),
        "wrong_decisions_in_the_conformal_half": len(wrong),
        "quantile_rank": rank,
        "threshold": str(bar),
        "admitted": len(admitted),
        "errors_admitted": errors,
        "coverage": len(admitted) / len(certification_decisions),
        "error_upper_bound_95": round(admitted_error_upper_bound(errors, len(admitted)), 6)
        if admitted
        else None,
        "first_choice_rate_over_admitted": (
            str(Decimal(sum(1 for item in admitted if item["correct"])) / Decimal(len(admitted)))
            if admitted
            else None
        ),
    }


def _invariance(baseline: dict[str, str]) -> dict[str, Any]:
    """The containment ordering under the six frozen cases, on every eligible fresh group.

    The group-wide rename maps every source with one bijection, so the ordering cannot move;
    this measures that claim against the released generator instead of asserting it.
    """
    checked = flips = eligible_groups = ineligible = 0
    for spec in D6_CERTIFICATION_SPECS:
        item = template(spec.template_id)
        module_path = next(path for path in item.visible_files if path.startswith("src/"))
        baseline_source = item.visible_files[module_path]
        if not transformations_d3.eligible(baseline_source):
            ineligible += 1
            continue
        eligible_groups += 1
        recipes = sorted(item.neutral_candidate_sources, key=lambda recipe: recipe.value)
        variants = tuple(item.neutral_candidate_sources[recipe][module_path] for recipe in recipes)
        slots = tuple(str(index) for index in range(len(variants)))
        reference = containment_ordering(
            baseline_source, dict(zip(slots, variants, strict=True)), baseline_order=slots
        )
        visible_path = next(path for path in item.visible_files if path.startswith("tests/"))
        for case in transformations_d3.CASES:
            package = transformations_d3.transform(
                case,
                module_source=baseline_source,
                variants=variants,
                visible_test=item.visible_files[visible_path],
                hidden_test=spec.hidden_test,
                issue=item.issue_description,
            )
            transformed = containment_ordering(
                package.module_source,
                dict(zip(slots, package.variants, strict=True)),
                baseline_order=slots,
            )
            checked += 1
            if transformed != reference:
                flips += 1
    return {
        "cases_evaluated": checked,
        "eligible_groups": eligible_groups,
        "ineligible_groups": ineligible,
        "ordering_changes": flips,
    }


def _run(output: Path) -> int:
    measured_at = datetime.now(UTC)

    d5_calibration_seal = _sealed_records(D5_ARTIFACT_ROOT, D5_FEATURE_SEALS, "calibration")
    d5_training_seal = _sealed_records(D5_ARTIFACT_ROOT, D5_FEATURE_SEALS, "training")
    d6_certification_seal = _sealed_records(D6_ARTIFACT_ROOT, D6_FEATURE_SEALS, "calibration")

    d5_published = json.loads(D5_SNAPSHOTS.read_text(encoding="utf-8"))["fitted_matrices"]
    d6_published = json.loads(D6_SNAPSHOTS.read_text(encoding="utf-8"))["fitted_matrices"]
    d5_calibration = _matrix(
        d5_calibration_seal,
        D5_CALIBRATION_CAMPAIGN,
        split="calibration",
        published_hash=d5_published["calibration_matrix_hash"],
    )
    d5_fitting = _matrix(
        d5_training_seal,
        D5_FITTING_CAMPAIGN,
        split="fit",
        published_hash=d5_published["fit_matrix_hash"],
    )
    d6_certification = _matrix(
        d6_certification_seal,
        D6_CERTIFICATION_CAMPAIGN,
        split="calibration",
        published_hash=d6_published["certification_matrix_hash"],
    )

    directions = json.loads(D6_DIRECTIONS.read_text(encoding="utf-8"))
    selected = next(item for item in directions["directions"] if item["volume_rows"] == 720)
    reported = next(item for item in directions["directions"] if item["volume_rows"] == 320)
    direction_720 = _direction(selected["model_hash"])
    direction_320 = _direction(reported["model_hash"])

    d5_bundle = seal_d5_corpus()
    d6_bundle = seal_d6_corpus()
    d5_order, d5_requirement, d5_delta, d5_family, d5_baseline = _catalogue_maps(
        d5_bundle.catalogues[CorrectionPartition.CALIBRATION]
    )
    d6_order, d6_requirement, d6_delta, d6_family, d6_baseline = _catalogue_maps(
        d6_bundle.catalogues[CorrectionPartition.CALIBRATION]
    )
    fit_order, _, fit_delta, _, fit_baseline = _catalogue_maps(build_d5_fitting_catalogue())

    # --- §4: the transfer-gap record, both sealed directions -----------------------------
    transfer = measure_transfer_gap(
        CorpusHalf(
            name="d5_calibration",
            matrix=d5_calibration,
            order=d5_order,
            requirement_texts=d5_requirement,
            delta_texts=d5_delta,
            family_by_group=d5_family,
            learned_first_choice_correct=_learned_verdicts(d5_calibration, d5_order, direction_720),
        ),
        CorpusHalf(
            name="d6_certification",
            matrix=d6_certification,
            order=d6_order,
            requirement_texts=d6_requirement,
            delta_texts=d6_delta,
            family_by_group=d6_family,
            learned_first_choice_correct=_learned_verdicts(
                d6_certification, d6_order, direction_720
            ),
        ),
        measured_at=measured_at,
    )
    reported_320 = {
        "model_hash": direction_320.content_hash(),
        "d5_calibration_first_choice_rate": str(
            Decimal(sum(_learned_verdicts(d5_calibration, d5_order, direction_320).values()))
            / Decimal(len(d5_order))
        ),
        "d6_certification_first_choice_rate": str(
            Decimal(sum(_learned_verdicts(d6_certification, d6_order, direction_320).values()))
            / Decimal(len(d6_order))
        ),
    }

    # --- the class diagnostic the collapse licenses --------------------------------------
    fit_groups = _relational_groups(d5_fitting, fit_order, fit_delta, fit_baseline)
    model = fit_containment_direction(fit_groups, regularization=REGULARIZATION)
    ranker = ContainmentContrastiveRanker(model, margin_floor=Decimal("0"))
    d5_decisions = _score_relational(
        _relational_groups(d5_calibration, d5_order, d5_delta, d5_baseline), ranker
    )
    d6_decisions = _score_relational(
        _relational_groups(d6_certification, d6_order, d6_delta, d6_baseline), ranker
    )

    strongest = {corpus.corpus: corpus.strongest_rung for corpus in transfer.corpora}
    d6_groups_by_name = {
        item.group: item
        for item in group_candidates(
            d6_certification,
            order=d6_order,
            requirement_texts=d6_requirement,
            delta_texts=d6_delta,
        )
    }
    strongest_ordering = eligible_rungs(d6_certification.rows[0].vector.encoder_version)[
        strongest["d6_certification"]
    ]
    strongest_first = {
        name: strongest_ordering(group)[0] for name, group in d6_groups_by_name.items()
    }
    simulation = _diagnostic_bar(d5_decisions, d6_decisions)
    if simulation.get("quantile_exists"):
        bar = Decimal(simulation["threshold"])
        admitted = [item for item in d6_decisions if Decimal(item["margin"]) > bar]
        changed = sum(1 for item in admitted if item["first"] != strongest_first[item["group"]])
        simulation["changed_against_the_strongest_rung"] = changed
        simulation["projected_changed_final_decisions"] = (
            str(Decimal(changed) / Decimal(len(admitted)) * Decimal(60)) if admitted else None
        )

    containment_rung = {}
    for tag, matrix, order, delta, baseline in (
        ("d5_calibration", d5_calibration, d5_order, d5_delta, d5_baseline),
        ("d6_certification", d6_certification, d6_order, d6_delta, d6_baseline),
    ):
        accepted: dict[str, dict[str, bool]] = {}
        for row in matrix.rows:
            accepted.setdefault(row.group, {})[str(row.candidate_id)] = row.accepted
        correct = 0
        for name in order:
            first = containment_ordering(
                baseline[name],
                {item: delta[item] for item in order[name]},
                baseline_order=order[name],
            )[0]
            correct += int(accepted[name][first])
        containment_rung[tag] = str(Decimal(correct) / Decimal(len(order)))

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "stage": "groundwork",
            "recorded_at": measured_at.isoformat(),
            "final_outcomes_inspected": False,
            "final_or_canary_outcomes_inspected": 0,
            "stores_opened_for_writing": 0,
            "inputs": {
                "d5_feature_seals_sha256": _digest(D5_FEATURE_SEALS.read_bytes()),
                "d5_calibration_campaign_sha256": _digest(D5_CALIBRATION_CAMPAIGN.read_bytes()),
                "d5_fitting_campaign_sha256": _digest(D5_FITTING_CAMPAIGN.read_bytes()),
                "d5_snapshots_sha256": _digest(D5_SNAPSHOTS.read_bytes()),
                "d6_feature_seals_sha256": _digest(D6_FEATURE_SEALS.read_bytes()),
                "d6_certification_campaign_sha256": _digest(D6_CERTIFICATION_CAMPAIGN.read_bytes()),
                "d6_snapshots_sha256": _digest(D6_SNAPSHOTS.read_bytes()),
                "d6_directions_sha256": _digest(D6_DIRECTIONS.read_bytes()),
                "d5_calibration_matrix_hash": d5_calibration.content_hash,
                "d5_fit_matrix_hash": d5_fitting.content_hash,
                "d6_certification_matrix_hash": d6_certification.content_hash,
                "selected_direction_model_hash": direction_720.content_hash(),
            },
            "transfer_gap": json.loads(transfer.model_dump_json()),
            "reported_320_direction": reported_320,
            "class_diagnostic": {
                "hypothesis_class": HYPOTHESIS_CLASS,
                "fit_rule": FIT_RULE,
                "channels": list(FITTED_RELATIONAL_CHANNELS),
                "fitted_on": {
                    "pool": "the released 180-group fitting pool, its licensed role",
                    "groups": model.fitted_group_count,
                    "pairs": model.fitted_pair_count,
                    "regularization": model.regularization,
                },
                "model_hash": model.content_hash(),
                "weights": {
                    name: f"{weight:.12g}"
                    for name, weight in zip(model.channel_names, model.weights, strict=True)
                },
                "containment_rung_alone_first_choice": containment_rung,
                "first_choice_rate": {
                    "d5_calibration": str(
                        Decimal(sum(item["correct"] for item in d5_decisions)) / Decimal(100)
                    ),
                    "d6_certification": str(
                        Decimal(sum(item["correct"] for item in d6_decisions)) / Decimal(100)
                    ),
                },
                "sweep": {
                    "d5_calibration": _sweep(d5_decisions),
                    "d6_certification": _sweep(d6_decisions),
                },
                "diagnostic_admission_simulation": simulation,
                "invariance_of_the_containment_ordering": _invariance(d6_baseline),
                "what_this_is_not": (
                    "a selection. The simulated bar is discarded; the class must be "
                    "pre-registered and certified on a fresh corpus these spent decisions "
                    "cannot stand in for"
                ),
            },
        }
    )
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        "output": output.name,
        "difference_shift": transfer.difference_shift,
        "learned_shift": transfer.learned_shift,
        "class_first_choice_d6": evidence["class_diagnostic"]["first_choice_rate"][
            "d6_certification"
        ],
        "simulation": {
            key: simulation.get(key)
            for key in ("admitted", "errors_admitted", "coverage", "error_upper_bound_95")
        },
        "invariance_ordering_changes": evidence["class_diagnostic"][
            "invariance_of_the_containment_ordering"
        ]["ordering_changes"],
        "integrity_content_hash": evidence["integrity_content_hash"],
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    return _run(arguments.output)


if __name__ == "__main__":
    raise SystemExit(main())
