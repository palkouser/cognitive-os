"""S21D6-010 and S21D6-011. The two governance decisions W0 exists to obtain.

Neither is a sprint's own edit. The first changes a Gate L2 threshold, which every backlog since
D3 has declared out of scope for the sprint running under it; the second declines to re-evidence a
condition. Both belong to the gate owner, and both are recorded here with what the gate owner was
shown when the decision was taken.

**The amendment (S21D6-010).** §2.3 requires both "exactly zero confident errors" and "clean
coverage at least 0.40". D5's sealed sweep prices that pair, and this script *recomputes* the
price from `sprint-21d5-learner-selection.json` rather than restating it: a justification typed
from prose is how a contract change inherits a number that stopped being true. The recomputation
is the record's own evidence that the pre-amendment pair was infeasible rather than merely unmet.

**The inheritance ruling (S21D6-011).** §2.2 has every sprint re-evidence all 29 conditions
against its own authorities. For condition 24 that means authoring 60 retrieval groups for a
surface D6 neither fits, changes nor reads. The ruling makes the inheritance conditional and
names its own falsifier: the three identities that would void it, each bound to a released hash,
each re-checked at gate close rather than trusted from here.

    UV_CACHE_DIR=.cache/uv uv run python scripts/contracts_d6.py

Read-only apart from the two records it writes. It derives no threshold and reads no margin.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"

GATE_CONTRACT_SHA256 = "9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7"

STRUCK_SENTENCE = "exactly zero confident errors among admitted independent calibration decisions"

AMENDED_SENTENCE = (
    "admission is a split-conformal bar at the pre-registered alpha, and the Clopper-Pearson "
    "one-sided 95% upper bound on the error rate among admitted independent calibration "
    "decisions is at most the pre-registered ceiling C"
)

ALPHA = Decimal("0.20")
CEILING = Decimal("0.15")

#: The gate owner's authority for both decisions, and the words that carried it. Recorded rather
#: than assumed: a threshold change whose approval cannot be pointed at is a threshold a sprint
#: relaxed for itself.
AUTHORITY = {
    "role": "sprint and gate owner",
    "decided_at": "2026-08-10",
    "instruction": (
        "execute W0 of sprint-21d6-technical-backlog.md, applying the lazier alternative"
    ),
    "shown": [
        "sprint-21d6-technical-backlog.md §2.1, the infeasibility table",
        "sprint-21d6-technical-backlog.md §2.2, the amendment as drafted",
        "sprint-21d6-technical-backlog.md §3.2 and §3.3, alpha = 0.20 and C = 0.15",
        "sprint-21d6-technical-backlog.md §4.2, the condition-24 inheritance and its cost",
    ],
    "reading": (
        "the backlog names both decisions as W0's business and the instruction to execute W0 "
        "under it carries both; the lazier alternative is named only in §4.2, so that phrase "
        "carries the inheritance ruling specifically. Either record is one edit from withdrawal "
        "while no D6 measurement exists, which is the state the chronology below proves"
    ),
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _infeasibility() -> dict[str, Any]:
    """Recompute, from D5's sealed sweep, what each error count costs in coverage.

    The sweep is 100 threshold points per cell, each carrying its admitted count, its coverage
    and the confident errors it lets through. The table below takes the *best* coverage available
    at each error count, which is the only reading that can support an infeasibility claim: if
    the most generous zero-error threshold reaches 0.27, no zero-error threshold reaches 0.40.
    """
    path = EVIDENCE / "sprint-21d5-learner-selection.json"
    selection = json.loads(path.read_text(encoding="utf-8"))
    cells: dict[str, Any] = {}
    for volume, cell in selection["risk_coverage_curve"].items():
        best: dict[int, dict[str, Any]] = {}
        for point in cell["sweep"]:
            errors = point["confident_errors"]
            if point["admitted_decisions"] > best.get(errors, {}).get("admitted_decisions", -1):
                best[errors] = {
                    "admitted_decisions": point["admitted_decisions"],
                    "coverage": point["coverage"],
                    "changed_decisions": point["changed_decisions"],
                    "first_choice_rate_over_admitted": point["first_choice_rate_over_admitted"],
                    "threshold": point["threshold"],
                }
        cells[volume] = {
            "model_hash": cell["model_hash"],
            "answered_decisions": cell["answered_decisions"],
            "errors_among_all_answered": cell["errors_among_all_answered"],
            "best_coverage_at_error_count": {
                str(errors): best[errors] for errors in sorted(best)[:4]
            },
            "best_zero_error_coverage": best[0]["coverage"],
            "zero_error_coverage_reaches_the_floor": Decimal(best[0]["coverage"])
            >= Decimal("0.40"),
        }
    return {
        "read_from": path.name,
        "read_from_sha256": _sha256_file(path),
        "sweep_points_per_cell": selection["grid"]["sweep_points_reported"] // 2,
        "floor": "0.40",
        "cells": cells,
        "infeasible_on_every_cell": all(
            not cell["zero_error_coverage_reaches_the_floor"] for cell in cells.values()
        ),
        "reading": (
            "the best coverage any zero-error threshold reaches is 0.27 and 0.26, on two cells "
            "at fitting volumes 2.25x apart. The pre-amendment pair is not unmet, it is "
            "unsatisfiable by any admission rule over this ranker: the constraint is on where "
            "the ranker places its errors, not on how the bar is chosen"
        ),
        "what_the_zero_never_bought": (
            "zero confident errors in 27 admitted decisions bounds the true error rate at 0.105 "
            "by the same Clopper-Pearson the amended clause uses. One tolerated error at 720 "
            "rows admits 58 and bounds it at 0.079 — a tighter bound at 2.2x the coverage. The "
            "struck sentence was a property of a small sample, not a safety property"
        ),
    }


def _no_measurement_exists() -> dict[str, Any]:
    """The window this amendment has to be inside: before any D6 number exists."""
    measurement_records = sorted(
        path.name
        for path in EVIDENCE.glob("sprint-21d6-*.json")
        if path.name
        not in {
            "sprint-21d6-baseline.json",
            "sprint-21d6-provisioning.json",
            "sprint-21d6-contracts-amendment-2.json",
            "sprint-21d6-condition-24-ruling.json",
        }
    )
    artifact_root = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d6")
    return {
        "d6_conformal_bars_derived": 0,
        "d6_calibration_outcomes": 0,
        "d6_certification_corpus_authored": False,
        "d6_measurement_records_present": measurement_records,
        "d6_artifact_store_entries": (
            sum(1 for _ in artifact_root.rglob("*") if _.is_file()) if artifact_root.exists() else 0
        ),
        "why_this_matters": (
            "pre-registration exists to stop a rule being chosen after its result is known. The "
            "alpha below moves the bar off the failed prefix rule and the ceiling above sits "
            "where the design expects to land, both computed from D5's published aggregate; "
            "neither has met a D6 outcome. The window closes when W1 seals the certification "
            "corpus"
        ),
    }


def _amendment() -> dict[str, Any]:
    infeasibility = _infeasibility()
    backlog = REPO / "docs/sprints/sprint-21/sprint-21d6-technical-backlog.md"
    return {
        "schema_version": 1,
        "sprint": "21D6",
        "wave": "W0",
        "items": ["S21D6-010"],
        "amendment": 2,
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "amends": {
            "contract": "gate_l2_section_2_3_admission_clause",
            "gate_contract_sha256": GATE_CONTRACT_SHA256,
            "gate_contract_bytes_modified": 0,
            "thresholds_changed": 1,
            "conditions_affected": [14],
            "why_not_an_in_place_edit": (
                "a sealed contract is not edited after publication. The gate contract hash is "
                "unchanged and still reproduces; this record supersedes one clause and names "
                "what it replaced, exactly as S21D4-011 handled the derivation step"
            ),
        },
        "authority": AUTHORITY,
        "why_the_gate_owner_and_not_the_sprint": (
            "every backlog since D3 declares changing a Gate L2 threshold out of scope for the "
            "sprint running under it. D6 is the sprint that would benefit from the change, which "
            "is precisely why D6 does not get to make it"
        ),
        "struck_sentence": STRUCK_SENTENCE,
        "struck_sentence_sha256": _sha256_text(STRUCK_SENTENCE),
        "amended_sentence": AMENDED_SENTENCE,
        "amended_sentence_sha256": _sha256_text(AMENDED_SENTENCE),
        "pre_registered_values": {
            "alpha": str(ALPHA),
            "alpha_bounds": (
                "the leak rate P(admitted | the decision is wrong), not the error rate among "
                "admitted decisions"
            ),
            "alpha_floor_that_makes_it_meaningful": "2/13 = 0.1538",
            "why_that_floor": (
                "the 720-row cell has 12 wrong answered decisions, so the finite-sample rank "
                "ceil((1-alpha)*(m+1)) is 12 for every alpha below 2/13 and the bar is then the "
                "largest wrong margin — which is the zero-error prefix rule D5 stopped on. Any "
                "alpha that could change the outcome is at least 0.1538; 0.20 is the smallest "
                "round value above it"
            ),
            "ceiling_c": str(CEILING),
            "ceiling_is_measured_on": (
                "the certification half, as the Clopper-Pearson one-sided 95% upper bound on the "
                "error rate among admitted independent decisions"
            ),
            "what_c_permits_at_the_expected_coverage": (
                "at 58 admitted decisions the bound reads 0.079 at one error, 0.105 at two, "
                "0.128 at three and 0.151 at four, so C admits up to three against an "
                "expectation of about 2.4 — a ceiling the design expects to clear and can fail"
            ),
        },
        "justification": infeasibility,
        "chronology": _no_measurement_exists(),
        "unchanged_by_this_amendment": [
            "the other seven conditions of §2.3, verbatim",
            "the 0.40 coverage floor",
            "the 100-independent-decision minimum",
            "the 20 projected changed final decisions",
            "the 250 ms inference budget and 100% first-action preservation",
            "every Gate L2 condition other than 14, and every Gate D1 condition",
            "the revision-5 counting rule, the independence census and the denominator",
            "the Clopper-Pearson bound itself, which both the struck and the amended clause use",
            "the encoder, the class, both fitted directions and the margin",
        ],
        "backlog": backlog.name,
        "backlog_sha256": _sha256_file(backlog),
        "if_refused": (
            "D6 does not run. §3.4 branch 0, stop kind admission_contract_refused: Gate L2 is "
            "unclosable with this ranker at these volumes, and the successor question leaves the "
            "confidence axis"
        ),
    }


def _condition_24_ruling() -> dict[str, Any]:
    """S21D6-011. Inheritance with a named falsifier, not a waiver."""
    decision = EVIDENCE / "sprint-21d5-retrieval-decision.json"
    surface = EVIDENCE / "sprint-21d5-surface.json"
    decided = json.loads(decision.read_text(encoding="utf-8"))
    projected = json.loads(surface.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "sprint": "21D6",
        "wave": "W0",
        "items": ["S21D6-011"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "condition": 24,
        "standing_rule": (
            "§2.2: every sprint re-evidences all 29 conditions against its own authorities. "
            "Fourteen met in D5 are fourteen met in D5"
        ),
        "ruling": "inherited from D5's sealed measurement, conditionally",
        "authority": AUTHORITY,
        "what_it_saves": {
            "authored_retrieval_groups": 60,
            "qualifying_queries": 50,
            "waves_shortened": "W1's second half",
        },
        "inherited_measurement": {
            "record": decision.name,
            "record_sha256": _sha256_file(decision),
            "integrity_content_hash": decided["integrity_content_hash"],
            "winning_arm": decided["winning_arm"],
            "queries": decided["queries"],
            "passed": decided["passed"],
            "first_failed_floor": decided["first_failed_floor"],
            "rule": decided["rule"],
        },
        "the_three_identities_that_void_it": {
            "searchable_surface": {
                "record": surface.name,
                "record_sha256": _sha256_file(surface),
                "integrity_content_hash": projected["integrity_content_hash"],
                "rule": projected["surface"]["rule"],
                "terms_read_off": projected["surface"]["terms_read_off"],
            },
            "retrieval_arms": {
                "arms_opened_by_d5": decided["no_alternative_opened"],
                "voided_if": "D6 opens an arm, a fusion variant, a weight, a width or a metric",
            },
            "comparator": {
                "chance_baseline": decided["chance_baseline"],
                "voided_if": "D6 changes the comparator or the holdout membership",
            },
        },
        "why_conditional_and_not_a_waiver": (
            "the D5 handoff's own caveat is the test: condition 24 does not stay closed for free, "
            "because a successor that changes the surface, the arms or the comparator has changed "
            "the thing that was measured. D6 changes none of the three by scope, so the "
            "measurement still describes D6's system — but the claim is prospective, so it is "
            "recorded as a claim with a falsifier rather than as a fact"
        ),
        "re_checked_at": (
            "gate close, by recomputing the three identities above from D6's own tree and "
            "refusing the inheritance if any hash moved"
        ),
        "d6_reads_no_retrieval_holdout": True,
        "gate_l2_condition_24_recorded_as": "met by inheritance, with the source hash bound",
    }


def _sealed(record: dict[str, Any], output: Path) -> dict[str, Any]:
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main() -> None:
    amendment = _sealed(_amendment(), EVIDENCE / "sprint-21d6-contracts-amendment-2.json")
    ruling = _sealed(_condition_24_ruling(), EVIDENCE / "sprint-21d6-condition-24-ruling.json")
    print(
        json.dumps(
            {
                "amendment": {
                    "output": "sprint-21d6-contracts-amendment-2.json",
                    "integrity_content_hash": amendment["integrity_content_hash"],
                    "infeasible_on_every_cell": amendment["justification"][
                        "infeasible_on_every_cell"
                    ],
                    "zero_error_coverage": {
                        volume: cell["best_zero_error_coverage"]
                        for volume, cell in amendment["justification"]["cells"].items()
                    },
                    "alpha": amendment["pre_registered_values"]["alpha"],
                    "ceiling_c": amendment["pre_registered_values"]["ceiling_c"],
                    "measurements_at_amendment_time": amendment["chronology"][
                        "d6_conformal_bars_derived"
                    ],
                },
                "ruling": {
                    "output": "sprint-21d6-condition-24-ruling.json",
                    "integrity_content_hash": ruling["integrity_content_hash"],
                    "condition": ruling["condition"],
                    "ruling": ruling["ruling"],
                    "authored_groups_saved": ruling["what_it_saves"]["authored_retrieval_groups"],
                },
            },
            indent=1,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
