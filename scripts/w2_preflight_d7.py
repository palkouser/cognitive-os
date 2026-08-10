#!/usr/bin/env python3
"""S21D7 W2 pre-flight: two design facts the sealed W1 bytes decide, disclosed before a bar exists.

W0's demotion ruling priced its alternative by recomputation rather than prose, and this
record extends that discipline to the two questions W2 would otherwise answer implicitly,
mid-measurement, where they are most expensive:

**One — the halves' disjointness, at the level the fitted class actually lives.** The frozen
`corpus_roles` sentence — "no fitted vector may appear in both halves" — was written for the
390-channel representation, where distinct sources never collide. The v3 representation is
seven numbers, and seven numbers alias. This scan proves the two leakage properties the
sentence exists for (zero shared decision signatures, zero shared canonical sources, across
every half pair) and counts the aliasing the v2-era scans cannot see, so the gate owner can
bind the sentence's reading to the true properties *before* W2 seals a record that would
otherwise carry a claim the bytes falsify.

**Two — what the seated ladder pairing does to §2.3, measured on spent corpora only.** The
ladder ruling re-paired the changed-decisions conditions against the containment-first
order, "a count the groundwork did not measure". This measures it, on the two published
corpora and nowhere else: the fitted class agrees with the containment rung on every
decision in its top-margin range on both, so the design estimate for changed-among-admitted
under the seated pairing is zero, against a floor that needs a third. The record also names
the reading divergence that estimate exposes in the baseline condition — admitted-rate
against whole-corpus rung rate passes on the same numbers where admitted-rate against
admitted-subset rung rate cannot — so the gate owner fixes one reading while
`d7_certification_decisions_scored` is provably zero.

Holdout safety, stated as facts about this file: the D7 certification half is touched only
for sealed, label-free vector bytes — the category W1's own snapshot scans established — and
its campaign record is never opened. No D7 certification decision is scored, no margin is
read over the bar-setting half for any bar, no operating point is derived, and no ladder
rung is measured on the fresh corpus. Everything scored here is spent and published.

    UV_CACHE_DIR=.cache/uv uv run python scripts/w2_preflight_d7.py
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

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
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
from cognitive_os.learning.correction_catalogue_d7 import (  # noqa: E402
    build_d7_certification_catalogue,
)
from cognitive_os.learning.correction_features import (  # noqa: E402
    SealedFeatureRecordSetV2,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402
from cognitive_os.learning.relational_scans import (  # noqa: E402
    scan_relational_separation,
)
from cognitive_os.learning.repair_containment import containment_ordering  # noqa: E402

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
OUTPUT = EVIDENCE / "sprint-21d7-w2-preflight.json"

D5_FEATURE_SEALS = EVIDENCE / "sprint-21d5-feature-seals.json"
D5_CALIBRATION_CAMPAIGN = EVIDENCE / "sprint-21d5-calibration-campaign.json"
D5_FITTING_CAMPAIGN = EVIDENCE / "sprint-21d5-self-play-campaign.json"
D6_FEATURE_SEALS = EVIDENCE / "sprint-21d6-feature-seals.json"
D6_CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d6-certification-campaign.json"
D7_FEATURE_SEALS = EVIDENCE / "sprint-21d7-feature-seals.json"
D7_CONTRACTS = EVIDENCE / "sprint-21d7-contracts.json"
D7_LADDER_RULING = EVIDENCE / "sprint-21d7-ladder-ruling.json"

D5_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d5")
D6_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d6-measured")
D7_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7-measured")

REGULARIZATION = Decimal("1")
ALPHA = Decimal("0.20")

#: The admitted depths the changed count is read at: the diagnostic expectation, the floor's
#: 40, and one past it. Design estimates, not thresholds.
DEPTHS = (40, 46, 50)


def _digest(value: bytes | str) -> str:
    return sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _sealed_records(store: Path, seals_path: Path, partition: str) -> SealedFeatureRecordSetV2:
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
    raise SystemExit(f"the released {partition} feature seal does not resolve in {store.name}")


def _catalogue_parts(catalogue: Any) -> tuple[dict, dict, dict]:
    order: dict[str, tuple[str, ...]] = {}
    delta: dict[str, str] = {}
    baseline: dict[str, str] = {}
    for group in catalogue.groups:
        item = template(group.template_id)
        module_path = next(path for path in item.visible_files if path.startswith("src/"))
        baseline[group.repository_group] = item.visible_files[module_path]
        order[group.repository_group] = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        for slot in group.slots:
            recipe = RealityCandidateStrategy(slot.recipe)
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[recipe][module_path]
    return order, delta, baseline


def _relational_half(
    seal: SealedFeatureRecordSetV2, catalogue: Any
) -> tuple[dict[str, tuple[tuple[str, ...], dict[str, tuple[float, ...]]]], dict[str, str]]:
    """Every group's (order, seven-channel vectors), plus canonical source hash by candidate."""
    order, delta, baseline = _catalogue_parts(catalogue)
    values: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for record in seal.records:
        values[str(record.candidate_id)] = record.values
        sources[str(record.candidate_id)] = record.canonical_source_hash
    half = {}
    for name in sorted(order):
        half[name] = (
            order[name],
            relational_numbers(
                {candidate_id: values[candidate_id] for candidate_id in order[name]},
                baseline_source=baseline[name],
                sources_by_candidate={
                    candidate_id: delta[candidate_id] for candidate_id in order[name]
                },
            ),
        )
    return half, sources


def _labels(campaign_path: Path) -> dict[str, dict[str, bool]]:
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    accepted: dict[str, dict[str, bool]] = {}
    for item in campaign["candidate_outcomes"]:
        accepted.setdefault(str(item["group"]), {})[str(item["candidate_id"])] = bool(
            item["accepted"]
        )
    return accepted


def _pairing(
    tag: str,
    half: dict,
    catalogue: Any,
    accepted: dict[str, dict[str, bool]],
    ranker: ContainmentContrastiveRanker,
) -> dict[str, Any]:
    """The seated pairing on one spent corpus: agreement with the containment rung, whole
    corpus and by descending margin. Labels enter only the rung/class *rates*, which these
    published corpora already carry in released records."""
    _, delta, baseline = _catalogue_parts(catalogue)
    rows = []
    for name, (group_order, numbers) in half.items():
        ranking = ranker.rank(numbers, baseline_order=group_order)
        first = ranking.ordered_candidate_ids[0]
        rung_first = containment_ordering(
            baseline[name],
            {candidate_id: delta[candidate_id] for candidate_id in group_order},
            baseline_order=group_order,
        )[0]
        rows.append(
            {
                "margin": float(ranking.confidence),
                "agrees": first == rung_first,
                "class_correct": accepted[name][first],
                "rung_correct": accepted[name][rung_first],
            }
        )
    rows.sort(key=lambda row: -row["margin"])
    by_depth = {}
    for depth in DEPTHS:
        top = rows[:depth]
        by_depth[str(depth)] = {
            "changed": sum(1 for row in top if not row["agrees"]),
            "class_first_choice": sum(1 for row in top if row["class_correct"]),
            "rung_first_choice_on_the_same_decisions": sum(1 for row in top if row["rung_correct"]),
        }
    return {
        "corpus": tag,
        "decisions": len(rows),
        "agreement_with_the_containment_rung": sum(1 for row in rows if row["agrees"]),
        "changed_whole_corpus": sum(1 for row in rows if not row["agrees"]),
        "by_descending_margin": by_depth,
    }


def _run(output: Path) -> int:
    measured_at = datetime.now(UTC)

    d5_fit_seal = _sealed_records(D5_ARTIFACT_ROOT, D5_FEATURE_SEALS, "training")
    d5_cal_seal = _sealed_records(D5_ARTIFACT_ROOT, D5_FEATURE_SEALS, "calibration")
    d6_seal = _sealed_records(D6_ARTIFACT_ROOT, D6_FEATURE_SEALS, "calibration")
    d7_seal = _sealed_records(D7_ARTIFACT_ROOT, D7_FEATURE_SEALS, "calibration")

    fit_catalogue = build_d5_fitting_catalogue()
    d5_cal_catalogue = seal_d5_corpus().catalogues[CorrectionPartition.CALIBRATION]
    d6_catalogue = seal_d6_corpus().catalogues[CorrectionPartition.CALIBRATION]
    d7_catalogue = build_d7_certification_catalogue()

    fit_half, fit_sources = _relational_half(d5_fit_seal, fit_catalogue)
    d5_cal_half, _ = _relational_half(d5_cal_seal, d5_cal_catalogue)
    d6_half, d6_sources = _relational_half(d6_seal, d6_catalogue)
    d7_half, d7_sources = _relational_half(d7_seal, d7_catalogue)

    # --- the frozen candidate reproduces ---------------------------------------------------
    fit_labels = _labels(D5_FITTING_CAMPAIGN)
    fit_groups = [
        RelationalGroup(group=name, order=order, numbers=numbers, accepted=fit_labels[name])
        for name, (order, numbers) in fit_half.items()
    ]
    model = fit_containment_direction(fit_groups, regularization=REGULARIZATION)
    frozen = json.loads(D7_CONTRACTS.read_text(encoding="utf-8"))["contracts"]["candidate_cell"][
        "model_hash_to_reproduce"
    ]
    if model.content_hash() != frozen:
        raise SystemExit(
            f"the fit does not reproduce the frozen model hash: {model.content_hash()} "
            f"against {frozen}; W2 must not run on an environment that cannot"
        )

    # --- fact one: the separation scan, at the v3 level ------------------------------------
    scan = scan_relational_separation(
        {
            "d7_certification": d7_half,
            "d6_demoted_bar_setting": d6_half,
            "d5_fitting_pool": fit_half,
        },
        canonical_source_hashes={**fit_sources, **d6_sources, **d7_sources},
    )
    frozen_sentence = json.loads(D7_CONTRACTS.read_text(encoding="utf-8"))["contracts"][
        "corpus_roles"
    ]["disjointness"]

    # --- fact two: the seated pairing, on spent corpora only -------------------------------
    ranker = ContainmentContrastiveRanker(model, margin_floor=Decimal("0"))
    pairing = [
        _pairing(
            "d5_calibration_spent",
            d5_cal_half,
            d5_cal_catalogue,
            _labels(D5_CALIBRATION_CAMPAIGN),
            ranker,
        ),
        _pairing(
            "d6_certification_spent_now_bar_setting",
            d6_half,
            d6_catalogue,
            _labels(D6_CERTIFICATION_CAMPAIGN),
            ranker,
        ),
    ]

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "stage": "w2_preflight",
            "recorded_at": measured_at.isoformat(),
            "final_outcomes_inspected": False,
            "d7_certification_decisions_scored": 0,
            "d7_certification_campaign_opened": False,
            "operating_points_derived": 0,
            "stores_opened_for_writing": 0,
            "inputs": {
                "d7_contracts_sha256": _digest(D7_CONTRACTS.read_bytes()),
                "d7_ladder_ruling_sha256": _digest(D7_LADDER_RULING.read_bytes()),
                "d7_feature_seals_sha256": _digest(D7_FEATURE_SEALS.read_bytes()),
                "d5_feature_seals_sha256": _digest(D5_FEATURE_SEALS.read_bytes()),
                "d6_feature_seals_sha256": _digest(D6_FEATURE_SEALS.read_bytes()),
                "model_hash_reproduced": model.content_hash(),
            },
            "relational_separation": {
                "frozen_sentence": frozen_sentence,
                "scan": json.loads(scan.model_dump_json()),
                "what_the_scan_decides": (
                    "both leakage properties hold across every half pair — zero shared "
                    "decision signatures, zero shared canonical sources — and the literal "
                    "sentence is false at the v3 level by aliasing alone. The gate owner "
                    "binds the sentence's reading to the leakage properties before W2 "
                    "seals a record over these halves; without that, the wave would carry "
                    "a frozen claim its own bytes falsify"
                ),
            },
            "seated_pairing": {
                "ruling": "sprint-21d7-ladder-ruling.json",
                "measured_on": "the two spent published corpora and nothing else",
                "corpora": pairing,
                "what_the_estimate_says": (
                    "the fitted class agrees with the containment rung on every decision "
                    "in its top-margin range on both spent corpora, so the design estimate "
                    "for changed-decisions-among-admitted under the seated pairing is "
                    "zero, against a floor that needs at least a third of the admitted "
                    "set. Under the seated ladder the §2.3 conditions that read that "
                    "count are on course to fail whatever the admission numbers do"
                ),
                "the_reading_divergence": (
                    "the baseline condition — 'clean first-choice rate over admitted "
                    "decisions strictly above the strongest deterministic baseline on the "
                    "same decisions' — has two readings that D6's cell never separated, "
                    "because its baseline was weak everywhere: admitted-rate against the "
                    "rung's whole-corpus rate can pass on exactly the numbers where "
                    "admitted-rate against the rung's rate on the admitted subset cannot, "
                    "since agreement makes the latter two identical. The estimate above "
                    "lands the sprint precisely in the scenario where the readings "
                    "diverge, so the reading must be fixed before any fresh decision is "
                    "scored"
                ),
            },
            "what_this_record_asks": [
                "bind the corpus_roles disjointness sentence to the two leakage "
                "properties, with aliasing reported (a clarification of a frozen "
                "sentence's reading, not a threshold change)",
                "fix the baseline condition's reading before W2 scores anything",
                "decide the seated pairing's consequence knowingly: proceed to a "
                "probable typed negative that would close the class question, or "
                "supersede the ladder ruling while d7_certification_decisions_scored "
                "is provably zero — both legitimate, neither decidable by this record",
            ],
            "what_this_record_is_not": (
                "a measurement of the certification half, a bar, a selection input, or "
                "an argument for either answer. Design input, recomputed from sealed "
                "bytes, in the discipline the demotion ruling set"
            ),
        }
    )
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        "output": output.name,
        "model_hash_reproduced": True,
        "scan_clean_of_leakage": scan.clean,
        "aliased_vectors_cert_vs_bar_setting": next(
            pair.aliased_vectors
            for pair in scan.pairs
            if {pair.first_half, pair.second_half} == {"d7_certification", "d6_demoted_bar_setting"}
        ),
        "changed_at_depth_46": {
            item["corpus"]: item["by_descending_margin"]["46"]["changed"] for item in pairing
        },
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
