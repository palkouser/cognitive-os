#!/usr/bin/env python3
"""S21D7 W2: the one fit of the wave, the §4 transfer gap as W-stage evidence, and the v3 scan.

Three records, in the order the backlog's W2 row states them and for one reason each:

1. **The direction.** `containment-contrastive-linear-v1` is fitted **once** in this wave, on
   the released 180-group / 720-pair fitting pool — its licensed role — and must reproduce the
   model hash revision 7 froze, `d80160c4…`. A fit that does not reproduce bit-for-bit is not a
   number to shrug at: it means the environment computing W2's margins is not the environment
   the pre-registration was written against, and this script exits non-zero rather than carry
   on. Nothing downstream may fit again; every later W2 step reads this record's hash.

2. **The transfer gap.** D7's groundwork measured the §4 question and decided *collapsed*. That
   measurement is what licenses the class question at all, so W2 seals it as its own W-stage
   evidence rather than pointing at a groundwork file: the record below binds the groundwork
   bytes by file hash and restates the quantities the decision rests on, and the direction it
   diagnosed is the direction record 1 re-derives here.

3. **The scan, at both levels.** W1's eleven released scans prove separation where the *v2*
   representation lives — 390 channels, 800 rows, one encoder identity. The class W2 certifies
   reads *seven* numbers, and seven numbers alias. Under S21D7-025 the frozen disjointness
   sentence is bound to its two leakage properties; this record is where that binding is
   discharged with numbers: zero shared decision signatures and zero shared canonical sources
   on every half pair, with the aliasing counts reported beside them as the coverage ceiling.

**No timestamp travels in these bytes.** The reproduction claim is that a fresh process derives
the identical record, and a clock in the record would make that check vacuous:

    UV_CACHE_DIR=.cache/uv uv run python scripts/w2_direction_d7.py     # writes
    UV_CACHE_DIR=.cache/uv uv run python scripts/w2_direction_d7.py --check   # the restart

Read-only against all three stores: no database, no campaign opened, no outcome inspected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    FIT_RULE,
    FITTED_RELATIONAL_CHANNELS,
    HYPOTHESIS_CLASS,
    RelationalGroup,
    fit_containment_direction,
    relational_numbers,
)
from cognitive_os.learning.correction_catalogue_d5 import (  # noqa: E402
    build_d5_fitting_catalogue,
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

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"

D5_FEATURE_SEALS = EVIDENCE / "sprint-21d5-feature-seals.json"
D5_FITTING_CAMPAIGN = EVIDENCE / "sprint-21d5-self-play-campaign.json"
D6_FEATURE_SEALS = EVIDENCE / "sprint-21d6-feature-seals.json"
D7_FEATURE_SEALS = EVIDENCE / "sprint-21d7-feature-seals.json"
D7_CONTRACTS = EVIDENCE / "sprint-21d7-contracts.json"
D7_SNAPSHOTS = EVIDENCE / "sprint-21d7-snapshots.json"
D7_TRANSFER_GAP = EVIDENCE / "sprint-21d7-transfer-gap.json"
D7_DISJOINTNESS = EVIDENCE / "sprint-21d7-disjointness-clarification.json"

D5_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d5")
D6_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d6-measured")
D7_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7-measured")

REGULARIZATION = Decimal("1")


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
    """Resolve one released partition seal inside a content-addressed store."""
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


def _catalogue_parts(catalogue: Any) -> tuple[dict[str, tuple[str, ...]], dict[str, str], dict]:
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
) -> tuple[dict[str, tuple[tuple[str, ...], dict[str, Any]]], dict[str, str]]:
    """Every group's (slot order, seven-channel vectors), plus canonical source hash per slot."""
    order, delta, baseline = _catalogue_parts(catalogue)
    values = {str(record.candidate_id): record.values for record in seal.records}
    sources = {str(record.candidate_id): record.canonical_source_hash for record in seal.records}
    half = {
        name: (
            order[name],
            relational_numbers(
                {candidate_id: values[candidate_id] for candidate_id in order[name]},
                baseline_source=baseline[name],
                sources_by_candidate={
                    candidate_id: delta[candidate_id] for candidate_id in order[name]
                },
            ),
        )
        for name in sorted(order)
    }
    return half, sources


def _labels(campaign_path: Path) -> dict[str, dict[str, bool]]:
    accepted: dict[str, dict[str, bool]] = {}
    for item in _read(campaign_path)["candidate_outcomes"]:
        accepted.setdefault(str(item["group"]), {})[str(item["candidate_id"])] = bool(
            item["accepted"]
        )
    return accepted


def _direction_record(fit_half: dict, model: Any, frozen: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W2",
        "stage": "direction",
        "items": ["S21D7-029"],
        "final_outcomes_inspected": False,
        "final_or_canary_outcomes_inspected": 0,
        "stores_opened_for_writing": 0,
        "certification_decisions_scored_by_this_record": 0,
        "inputs": {
            "d5_feature_seals_sha256": _sha256(D5_FEATURE_SEALS.read_bytes()),
            "d5_fitting_campaign_sha256": _sha256(D5_FITTING_CAMPAIGN.read_bytes()),
            "d7_contracts_sha256": _sha256(D7_CONTRACTS.read_bytes()),
            "store": D5_ARTIFACT_ROOT.name,
        },
        "fit": {
            "hypothesis_class": HYPOTHESIS_CLASS,
            "fit_rule": FIT_RULE,
            "channels": list(FITTED_RELATIONAL_CHANNELS),
            "pool": "the released 180-group D5 fitting pool, its licensed role",
            "groups": model.fitted_group_count,
            "pairs": model.fitted_pair_count,
            "regularization": str(model.regularization),
            "margin_floor": "0",
            "model_hash": model.content_hash(),
            "weights": {
                name: f"{weight:.12g}"
                for name, weight in zip(model.channel_names, model.weights, strict=True)
            },
        },
        "fits_performed_in_this_wave": 1,
        "reproduction": {
            "frozen_by": "revision 7, §candidate_cell, model_hash_to_reproduce",
            "expected_model_hash": frozen,
            "reproduced": model.content_hash() == frozen,
            "across_a_process_restart": (
                "this record carries no timestamp, so a second process deriving it must "
                "produce these bytes exactly; `--check` is that second process"
            ),
            "on_failure": (
                "stop. A direction that does not reproduce means W2's margins would be "
                "computed by an environment the pre-registration was not written against"
            ),
        },
        "fit_pool_shape": {
            "groups": len(fit_half),
            "candidate_vectors": sum(len(order) for order, _ in fit_half.values()),
        },
        "what_this_record_is_not": (
            "a score. No decision of the certification half is ranked here, no bar is derived "
            "and no margin is read; the direction is fitted on the fitting pool alone"
        ),
    }


def _transfer_gap_record(model_hash: str) -> dict[str, Any]:
    """The §4 measurement, re-sealed as W-stage evidence and bound to the groundwork bytes."""
    groundwork = _read(D7_TRANSFER_GAP)
    gap = groundwork["transfer_gap"]
    return {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W2",
        "stage": "transfer_gap",
        "items": ["S21D7-030"],
        "final_outcomes_inspected": False,
        "final_or_canary_outcomes_inspected": 0,
        "stores_opened_for_writing": 0,
        "measures": (
            "nothing new. This record raises the groundwork's §4 measurement to W-stage "
            "evidence and binds it by hash, because it is the measurement that licenses the "
            "class question W2 certifies"
        ),
        "groundwork_record": {
            "file": D7_TRANSFER_GAP.name,
            "file_sha256": _sha256(D7_TRANSFER_GAP.read_bytes()),
            "integrity_content_hash": groundwork["integrity_content_hash"],
            "transfer_gap_content_hash": gap["content_hash"],
        },
        "decision": "collapsed",
        "quantities": {
            "difference_shift": gap["difference_shift"],
            "learned_shift": gap["learned_shift"],
            "collapsed_reading": gap["collapsed_reading"],
            "stable_reading_not_taken": gap["stable_reading"],
            "baseline_shift_by_rung": gap["baseline_shift_by_rung"],
            "corpora": [
                {
                    "corpus": corpus["corpus"],
                    "groups": corpus["groups"],
                    "strongest_rung": corpus["strongest_rung"],
                    "strongest_rung_rate": corpus["strongest_rung_rate"],
                    "learned_first_choice_rate": corpus["learned_first_choice_rate"],
                }
                for corpus in gap["corpora"]
            ],
        },
        "what_collapsed": (
            "learned-minus-strongest fell from +0.46 to +0.14 while fixed_input_order held at "
            "0.42 on both corpora: the sealed 390-channel direction carried the authoring run, "
            "not the task, so no admission rule over it would have transferred either"
        ),
        "the_successor_it_licenses": {
            "hypothesis_class": HYPOTHESIS_CLASS,
            "model_hash": model_hash,
            "diagnosed_in_the_groundwork_record": (
                groundwork["class_diagnostic"]["model_hash"] == model_hash
            ),
            "certified_on": "a fresh 100-group corpus the class has never seen",
        },
        "what_this_record_is_not": (
            "a re-decision. The groundwork's stop stands as taken; nothing here re-opens it, "
            "and the diagnostic bar it simulated was discarded there and is not read here"
        ),
    }


def _scan_record(scan: Any, frozen_sentence: str) -> dict[str, Any]:
    """The v3 separation scan, sealed beside the released v2 scans it does not replace."""
    snapshots = _read(D7_SNAPSHOTS)
    v2 = snapshots["scans"]
    clarification = _read(D7_DISJOINTNESS)
    pairs = json.loads(scan.model_dump_json())["pairs"]
    return {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W2",
        "stage": "separation_scan",
        "items": ["S21D7-031"],
        "final_outcomes_inspected": False,
        "final_or_canary_outcomes_inspected": 0,
        "stores_opened_for_writing": 0,
        "inputs": {
            "d5_feature_seals_sha256": _sha256(D5_FEATURE_SEALS.read_bytes()),
            "d6_feature_seals_sha256": _sha256(D6_FEATURE_SEALS.read_bytes()),
            "d7_feature_seals_sha256": _sha256(D7_FEATURE_SEALS.read_bytes()),
            "d7_snapshots_sha256": _sha256(D7_SNAPSHOTS.read_bytes()),
            "d7_disjointness_clarification_sha256": _sha256(D7_DISJOINTNESS.read_bytes()),
        },
        "released_v2_scans": {
            "level": "the 390-channel v2 representation, 800 rows, one encoder identity",
            "sealed_in": D7_SNAPSHOTS.name,
            "count": v2["count"],
            "all_passed": v2["all_passed"],
            "failed": v2["failed"],
            "results": v2["results"],
            "why_they_are_not_enough_alone": (
                "they prove separation where the v2 representation lives. The class W2 "
                "certifies reads seven numbers, and a scan of 390 channels cannot see what "
                "seven numbers collide on"
            ),
        },
        "v3_relational_scan": json.loads(scan.model_dump_json()),
        "frozen_sentence": frozen_sentence,
        "clarification": {
            "item": "S21D7-025",
            "integrity_content_hash": clarification["integrity_content_hash"],
            "reading": (
                "the sentence is bound to the two leakage properties it exists to prevent: no "
                "shared decision signature and no shared canonical source across any half pair"
            ),
        },
        "leakage_properties": {
            "shared_decision_signatures": sum(pair["shared_decision_signatures"] for pair in pairs),
            "shared_canonical_sources": sum(pair["shared_canonical_sources"] for pair in pairs),
            "clean": scan.clean,
        },
        "aliasing": {
            "by_pair": {
                f"{pair['first_half']}|{pair['second_half']}": pair["aliased_vectors"]
                for pair in pairs
            },
            "reported_as": (
                "the upper bound on reachable coverage, never as a pass. An aliased vector is "
                "two different canonical sources encoding identically in a low-entropy code; "
                "it shares no decision, no group and no bytes, and a certified decision's "
                "margin is computed from its own group's four vectors regardless"
            ),
        },
        "what_this_record_is_not": (
            "a label-bearing measurement. The scan reads sealed vectors and canonical source "
            "hashes only — no outcome, no label, no margin, no ordering — which is what makes "
            "it safe over an unscored certification half"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="re-derive every record in this process and compare; writes nothing",
    )
    write = not parser.parse_args().check

    fit_seal = _sealed_records(D5_ARTIFACT_ROOT, D5_FEATURE_SEALS, "training")
    d6_seal = _sealed_records(D6_ARTIFACT_ROOT, D6_FEATURE_SEALS, "calibration")
    d7_seal = _sealed_records(D7_ARTIFACT_ROOT, D7_FEATURE_SEALS, "calibration")

    fit_half, fit_sources = _relational_half(fit_seal, build_d5_fitting_catalogue())
    d6_half, d6_sources = _relational_half(
        d6_seal, seal_d6_corpus().catalogues[CorrectionPartition.CALIBRATION]
    )
    d7_half, d7_sources = _relational_half(d7_seal, build_d7_certification_catalogue())

    # --- the one fit of the wave -----------------------------------------------------------
    labels = _labels(D5_FITTING_CAMPAIGN)
    model = fit_containment_direction(
        [
            RelationalGroup(group=name, order=order, numbers=numbers, accepted=labels[name])
            for name, (order, numbers) in fit_half.items()
        ],
        regularization=REGULARIZATION,
    )
    contracts = _read(D7_CONTRACTS)["contracts"]
    frozen = contracts["candidate_cell"]["model_hash_to_reproduce"]
    direction = _sealed(
        _direction_record(fit_half, model, frozen),
        EVIDENCE / "sprint-21d7-w2-direction.json",
        write=write,
    )
    if not direction["reproduction"]["reproduced"]:
        print(
            json.dumps(
                {
                    "stop": "the direction does not reproduce the frozen model hash",
                    "derived": model.content_hash(),
                    "expected": frozen,
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 1

    transfer = _sealed(
        _transfer_gap_record(model.content_hash()),
        EVIDENCE / "sprint-21d7-w2-transfer-gap.json",
        write=write,
    )

    # --- the scan, at the level the class actually reads ------------------------------------
    scan = scan_relational_separation(
        {
            "d5_fitting_pool": fit_half,
            "d6_demoted_bar_setting": d6_half,
            "d7_certification": d7_half,
        },
        canonical_source_hashes={**fit_sources, **d6_sources, **d7_sources},
    )
    scan_record = _sealed(
        _scan_record(scan, contracts["corpus_roles"]["disjointness"]),
        EVIDENCE / "sprint-21d7-w2-relational-scan.json",
        write=write,
    )

    print(
        json.dumps(
            {
                "mode": "check" if not write else "write",
                "model_hash": model.content_hash(),
                "reproduced": True,
                "fits_performed_in_this_wave": 1,
                "leakage": scan_record["leakage_properties"],
                "aliasing_by_pair": scan_record["aliasing"]["by_pair"],
                "records": {
                    "sprint-21d7-w2-direction.json": direction["integrity_content_hash"],
                    "sprint-21d7-w2-transfer-gap.json": transfer["integrity_content_hash"],
                    "sprint-21d7-w2-relational-scan.json": scan_record["integrity_content_hash"],
                },
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
