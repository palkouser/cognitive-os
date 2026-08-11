#!/usr/bin/env python3
"""S21D7-032: the deterministic ladder on the fresh certification corpus, under S21D7-027.

W0 seated the containment rung as a sixth. W2's step 0 superseded that ruling and unseated it,
so what this script measures is the **five released rungs** — the ladder D2 through D6 were all
measured against — and it reports the containment ordering *beside* them as an unseated
measurement that sets no baseline and can win nothing.

That distinction is mechanical here, not editorial. `build_ladder` derives
`strongest_non_learned_*` from the rungs it is given; the containment ordering is never given to
it, so it cannot become the baseline by being measured. Its rate is computed separately and
carried in its own block, labelled for what it is.

Two of the five released rungs are ineligible on this surface and say so in their own words: the
frozen-MiniLM cosine has no columns under the v2 encoder, and a twenty-wide bounded graph over
four candidates is the whole pool. Three rungs are scored. This is the same shape every released
D-sprint ladder has, and the reason the baseline is comparable across them at all.

**Both changed-decision pairings are reported**, whole corpus and by descending class margin:
against the strongest released rung — the baseline S21D7-026 reads — and against the containment
ordering. Neither is an admitted-set count: no bar exists yet, and deriving one here would be
the thing W2's step 0 spent three rulings keeping out of this record.

No timestamp travels in these bytes; the ladder's own `created_at` is the certification seal's
time, because the ladder is a function of sealed bytes and nothing else:

    UV_CACHE_DIR=.cache/uv uv run python scripts/w2_ladder_d7.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/w2_ladder_d7.py --check

Read-only against the D5 and D7 stores: no database, no campaign opened, no final or canary
outcome inspected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    HYPOTHESIS_CLASS,
    ContainmentContrastiveRanker,
    RelationalGroup,
    fit_containment_direction,
    relational_numbers,
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
from cognitive_os.learning.correction_ladder import (  # noqa: E402
    LADDER_RUNGS,
    build_ladder,
    eligible_rungs,
    group_candidates,
)
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow  # noqa: E402
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionFeatureVector,
)
from cognitive_os.learning.repair_containment import containment_ordering  # noqa: E402

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-21d7-w2-ladder.json"

D5_FEATURE_SEALS = EVIDENCE / "sprint-21d5-feature-seals.json"
D5_FITTING_CAMPAIGN = EVIDENCE / "sprint-21d5-self-play-campaign.json"
D7_FEATURE_SEALS = EVIDENCE / "sprint-21d7-feature-seals.json"
D7_CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d7-certification-campaign.json"
D7_SNAPSHOTS = EVIDENCE / "sprint-21d7-snapshots.json"
D7_SUPERSESSION = EVIDENCE / "sprint-21d7-ladder-supersession.json"
D7_DIRECTION = EVIDENCE / "sprint-21d7-w2-direction.json"

D5_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d5")
D7_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7-measured")

REGULARIZATION = Decimal("1")

#: The depths the changed counts are read at. Design readings of the same 100 decisions from the
#: top of the class's margin, not thresholds: no bar exists when this script runs.
DEPTHS = (40, 46, 50, 100)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed(record: dict[str, Any], output: Path, *, write: bool) -> dict[str, Any]:
    record["integrity_content_hash"] = _sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    )
    text = json.dumps(record, indent=1, sort_keys=True) + "\n"
    if write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    elif not output.exists() or output.read_text(encoding="utf-8") != text:
        raise SystemExit(f"{output.name} does not match the record this script derives")
    return record


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
            if _sha256(path.read_bytes()) != path.name:
                raise SystemExit(f"{path.name} does not hash to its own content address")
            return SealedFeatureRecordSetV2.model_validate_json(path.read_text(encoding="utf-8"))
    raise SystemExit(f"the released {partition} feature seal does not resolve in {store.name}")


def _catalogue_maps(catalogue: Any) -> tuple[dict, dict, dict, dict, dict]:
    """Order, requirement text, candidate source, family and baseline source per group."""
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


def _matrix(
    seal: SealedFeatureRecordSetV2, campaign_path: Path, *, split: str, published_hash: str
) -> FittedMatrix:
    """A released matrix rebuilt from its sealed vectors and released labels, then proved."""
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
        for item in _read(campaign_path)["candidate_outcomes"]
    )
    matrix = FittedMatrix(split=split, rows=rows)
    if matrix.content_hash != published_hash:
        raise SystemExit(
            f"the rebuilt {split} matrix is not the published one: {matrix.content_hash} "
            f"against {published_hash}; a rate over drifted rows is a rate about nothing"
        )
    return matrix


def _relational_groups(
    matrix: FittedMatrix,
    order: dict[str, tuple[str, ...]],
    delta: dict[str, str],
    baseline: dict[str, str],
) -> list[RelationalGroup]:
    values: dict[str, dict[str, Any]] = {}
    accepted: dict[str, dict[str, bool]] = {}
    for row in matrix.rows:
        values.setdefault(row.group, {})[str(row.candidate_id)] = row.vector.values
        accepted.setdefault(row.group, {})[str(row.candidate_id)] = row.accepted
    return [
        RelationalGroup(
            group=name,
            order=order[name],
            numbers=relational_numbers(
                values[name],
                baseline_source=baseline[name],
                sources_by_candidate={item: delta[item] for item in order[name]},
            ),
            accepted=accepted[name],
        )
        for name in sorted(order)
    ]


def _direction() -> Any:
    """The wave's one direction, re-fitted and checked against the record that sealed it."""
    seal = _sealed_records(D5_ARTIFACT_ROOT, D5_FEATURE_SEALS, "training")
    order, _, delta, _, baseline = _catalogue_maps(build_d5_fitting_catalogue())
    labels: dict[str, dict[str, bool]] = {}
    for item in _read(D5_FITTING_CAMPAIGN)["candidate_outcomes"]:
        labels.setdefault(str(item["group"]), {})[str(item["candidate_id"])] = bool(
            item["accepted"]
        )
    flat = {str(record.candidate_id): record.values for record in seal.records}
    groups = [
        RelationalGroup(
            group=name,
            order=order[name],
            numbers=relational_numbers(
                {item: flat[item] for item in order[name]},
                baseline_source=baseline[name],
                sources_by_candidate={item: delta[item] for item in order[name]},
            ),
            accepted=labels[name],
        )
        for name in sorted(order)
    ]
    model = fit_containment_direction(groups, regularization=REGULARIZATION)
    sealed_hash = _read(D7_DIRECTION)["fit"]["model_hash"]
    if model.content_hash() != sealed_hash:
        raise SystemExit(
            f"the direction does not match the one W2 sealed: {model.content_hash()} against "
            f"{sealed_hash}. The wave fits once; this script re-derives it only to prove it"
        )
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="re-derive the record in this process and compare; writes nothing",
    )
    write = not parser.parse_args().check

    published = _read(D7_SNAPSHOTS)["fitted_matrices"]["certification_matrix_hash"]
    seal = _sealed_records(D7_ARTIFACT_ROOT, D7_FEATURE_SEALS, "calibration")
    matrix = _matrix(seal, D7_CERTIFICATION_CAMPAIGN, split="calibration", published_hash=published)
    order, requirement, delta, family, baseline = _catalogue_maps(
        build_d7_certification_catalogue()
    )

    # --- the five released rungs, and nothing seated beside them ----------------------------
    ladder = build_ladder(
        matrix,
        order=order,
        requirement_texts=requirement,
        delta_texts=delta,
        created_at=seal.sealed_at,
    )

    accepted: dict[str, dict[str, bool]] = {}
    for row in matrix.rows:
        accepted.setdefault(row.group, {})[str(row.candidate_id)] = row.accepted

    # --- the containment ordering, measured and unseated ------------------------------------
    containment_first = {
        name: containment_ordering(
            baseline[name],
            {item: delta[item] for item in order[name]},
            baseline_order=order[name],
        )[0]
        for name in order
    }
    containment_correct = sum(1 for name in order if accepted[name][containment_first[name]])

    # --- the class, and both changed-decision pairings ---------------------------------------
    model = _direction()
    ranker = ContainmentContrastiveRanker(model, margin_floor=Decimal("0"))
    strongest_name = ladder.strongest_non_learned_name
    strongest_ordering = {
        rung.name: rung for rung in ladder.rungs if rung.eligible and rung.kind != "learned"
    }
    rung_ordering = eligible_rungs(matrix.rows[0].vector.encoder_version)[strongest_name]
    rung_groups = {
        item.group: item
        for item in group_candidates(
            matrix, order=order, requirement_texts=requirement, delta_texts=delta
        )
    }
    rung_first = {name: rung_ordering(group)[0] for name, group in rung_groups.items()}

    rows = []
    for group in _relational_groups(matrix, order, delta, baseline):
        ranking = ranker.rank(group.numbers, baseline_order=group.order)
        first = ranking.ordered_candidate_ids[0]
        rows.append(
            {
                "group": group.group,
                "family": family[group.group],
                "margin": Decimal(str(ranking.confidence)),
                "class_correct": bool(group.accepted[first]),
                "changed_against_the_strongest_rung": first != rung_first[group.group],
                "changed_against_the_containment_ordering": first != containment_first[group.group],
                "strongest_rung_correct": accepted[group.group][rung_first[group.group]],
                "containment_correct": accepted[group.group][containment_first[group.group]],
            }
        )
    rows.sort(key=lambda item: (-item["margin"], item["group"]))

    def _pairing(key: str, correct_key: str) -> dict[str, Any]:
        return {
            "changed_whole_corpus": sum(1 for row in rows if row[key]),
            "by_descending_class_margin": {
                str(depth): {
                    "changed": sum(1 for row in rows[:depth] if row[key]),
                    "class_first_choice": sum(1 for row in rows[:depth] if row["class_correct"]),
                    "comparator_first_choice_on_the_same_decisions": sum(
                        1 for row in rows[:depth] if row[correct_key]
                    ),
                }
                for depth in DEPTHS
            },
        }

    record = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W2",
        "stage": "ladder",
        "items": ["S21D7-032"],
        "final_outcomes_inspected": False,
        "final_or_canary_outcomes_inspected": 0,
        "stores_opened_for_writing": 0,
        "conformal_bars_derived_by_this_record": 0,
        "directions_fitted_by_this_record": 0,
        "inputs": {
            "d7_feature_seals_sha256": _sha256(D7_FEATURE_SEALS.read_bytes()),
            "d7_certification_campaign_sha256": _sha256(D7_CERTIFICATION_CAMPAIGN.read_bytes()),
            "d7_snapshots_sha256": _sha256(D7_SNAPSHOTS.read_bytes()),
            "d7_w2_direction_sha256": _sha256(D7_DIRECTION.read_bytes()),
            "certification_matrix_hash": matrix.content_hash,
            "published_certification_matrix_hash": published,
            "model_hash": model.content_hash(),
        },
        "authority": {
            "item": "S21D7-027",
            "integrity_content_hash": _read(D7_SUPERSESSION)["integrity_content_hash"],
            "reading": (
                "the containment rung is not seated. The ladder below is the five released "
                "rungs; the containment ordering is measured beside them and sets no baseline"
            ),
        },
        "released_rungs": {
            "declared": list(LADDER_RUNGS),
            "scored": len(strongest_ordering),
            "groups": ladder.groups,
            "rungs": [json.loads(rung.model_dump_json()) for rung in ladder.rungs],
            "strongest_non_learned_name": strongest_name,
            "strongest_non_learned_rate": ladder.strongest_non_learned_rate,
            "created_at_is_the_seal_time": (
                "the ladder is a function of sealed bytes; stamping it with a clock would make "
                "the restart check vacuous"
            ),
        },
        "containment_ordering_unseated": {
            "first_choice_rate": str(Decimal(containment_correct) / Decimal(len(order))),
            "groups_scored": len(order),
            "seated": False,
            "sets_the_baseline": False,
            "why_it_is_here": (
                "S21D7-027 unseated it and asked for it to be reported anyway: a rung that "
                "would have been the baseline is worth knowing the rate of, and a number "
                "reported outside the ladder cannot win the comparison it is not in"
            ),
        },
        "class": {
            "hypothesis_class": HYPOTHESIS_CLASS,
            "model_hash": model.content_hash(),
            "margin_floor": "0",
            "first_choice_rate_whole_corpus": str(
                Decimal(sum(1 for row in rows if row["class_correct"])) / Decimal(len(rows))
            ),
            "decisions": len(rows),
        },
        "changed_decision_pairings": {
            "against_the_strongest_released_rung": {
                "comparator": strongest_name,
                "comparator_rate": ladder.strongest_non_learned_rate,
                **_pairing("changed_against_the_strongest_rung", "strongest_rung_correct"),
            },
            "against_the_containment_ordering": {
                "comparator": "repair_containment_ordering (unseated)",
                "comparator_rate": str(Decimal(containment_correct) / Decimal(len(order))),
                **_pairing("changed_against_the_containment_ordering", "containment_correct"),
            },
        },
        "what_this_record_is_not": (
            "an admitted-set measurement. No bar exists when this runs, so every count above "
            "is over the whole corpus or over a depth of the class's own margin ordering; the "
            "admitted counts belong to the certification record that derives the bar"
        ),
    }

    sealed = _sealed(record, OUTPUT, write=write)
    print(
        json.dumps(
            {
                "mode": "write" if write else "check",
                "strongest_released_rung": [strongest_name, ladder.strongest_non_learned_rate],
                "containment_unseated_rate": record["containment_ordering_unseated"][
                    "first_choice_rate"
                ],
                "class_rate": record["class"]["first_choice_rate_whole_corpus"],
                "changed_vs_rung": record["changed_decision_pairings"][
                    "against_the_strongest_released_rung"
                ]["changed_whole_corpus"],
                "changed_vs_containment": record["changed_decision_pairings"][
                    "against_the_containment_ordering"
                ]["changed_whole_corpus"],
                "integrity_content_hash": sealed["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
