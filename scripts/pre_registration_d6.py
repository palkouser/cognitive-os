"""S21D6-012 through S21D6-017. Revision 6, frozen before any D6 measurement exists.

Revision 5 pre-registered a hypothesis class, a regulariser and a confidence. Revision 6 keeps
all three and changes one thing: **the map from a ranked group to an admit/abstain decision.**
That is the whole experiment, so this document is five contracts rather than D5's seven, and
four of the five exist to fence the one that matters.

The contract text is imported from the modules that implement it rather than retyped, so a rule
that drifts in code drifts in the record too and `--check` catches it.

    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d6.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d6.py --check
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d6.py --check-chronology \\
        --later docs/sprints/sprint-21/evidence/sprint-21d6-<later>.json

Publishing this closes the window in which alpha could be chosen. Everything after it is
measurement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.learning.conformal_operating_point import (  # noqa: E402
    DERIVATION_READING,
    DERIVATION_RULE,
    admitted_error_upper_bound,
    conformal_rank,
)
from cognitive_os.learning.pairwise_contrastive import (  # noqa: E402
    HYPOTHESIS_CLASS,
)

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"

OUTPUTS = {
    "contracts": EVIDENCE / "sprint-21d6-contracts.json",
    "pre_registration": EVIDENCE / "sprint-21d6-pre-registration.json",
}

#: Amendments, in order. Unlike D5's empty tuple, D6 has one before it starts — and it is the
#: reason D6 can run at all. A sealed contract is never edited in place.
AMENDMENTS: tuple[Path, ...] = (EVIDENCE / "sprint-21d6-contracts-amendment-2.json",)

#: W0 records that must exist before revision 6 is published. They establish authority; none of
#: them measures the experiment.
W0_CHILDREN = (
    "sprint-21d6-baseline.json",
    "sprint-21d6-provisioning.json",
    "sprint-21d6-reuse-audit.json",
    "sprint-21d6-contracts-amendment-2.json",
    "sprint-21d6-condition-24-ruling.json",
)

#: Unchanged from D3, D4 and D5. Restated so a diff is possible without reading four documents.
FEATURE_CONTRACT = "492c90a5df420de9d1662d17155ac8b28713e69bbd4bbe56208415d6ca076362"
NORMALISER = "cogos-python-alpha-normalizer-v2"
GATE_CONTRACT = "9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7"

ALPHA = "0.20"
CEILING = "0.15"
#: The 720-row direction. The one cell revision 6 pre-registers.
SELECTED_DIRECTION = "9fd297fb407015374485e8f7ef8fbb557e6f89f7ac3286e2572769fdab937d74"
REPORTED_DIRECTION = "5b15f4af06a2b08d0d8269b59f47127bf97d610a22c12c645f8fbde9fa0f47cd"
#: Sealed in D5 and repeated here because the alpha floor is a function of it.
WRONG_DECISIONS_AT_720 = 12


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(document)
    sealed["content_hash"] = _sha256(_canonical(document))
    return sealed


def _contracts() -> dict[str, Any]:
    """The five frozen revision-6 contracts, S21D6-012 through S21D6-016."""
    from decimal import Decimal

    return {
        "admission_rule": _seal(
            {
                "item": "S21D6-012",
                "name": "split-conformal-margin-v1",
                "module": "src/cognitive_os/learning/conformal_operating_point.py",
                "derivation_rule": DERIVATION_RULE,
                "derivation_reading": DERIVATION_READING,
                "alpha": ALPHA,
                "alpha_may_be_rechosen": False,
                "alpha_bounds": (
                    "the leak rate P(admitted | the decision is wrong), not the error rate among "
                    "admitted decisions"
                ),
                "alpha_floor_below_which_the_bar_is_the_failed_rule": "0.1538",
                "rank_at_this_alpha": conformal_rank(Decimal(ALPHA), WRONG_DECISIONS_AT_720),
                "wrong_decisions_in_the_conformal_half": WRONG_DECISIONS_AT_720,
                "wrong_margins_left_above_the_bar": (
                    WRONG_DECISIONS_AT_720 - conformal_rank(Decimal(ALPHA), WRONG_DECISIONS_AT_720)
                ),
                "why_this_rule": (
                    "D5's zero-error prefix rule walks the margin ordering to the first wrong "
                    "decision and stops, so one badly-placed error truncates everything below "
                    "it. Its coverage is decided by the position of one error, which is variance "
                    "rather than a bound. The conformal bar is a quantile of the wrong "
                    "decisions' margins, so coverage degrades smoothly with alpha"
                ),
                "authorised_by": "sprint-21d6-contracts-amendment-2.json",
                "single_derivation": (
                    "one bar, derived once from the conformal half; a second derivation that "
                    "does not reproduce the first is refused across a process restart by the "
                    "`previous=` rule, alpha included in the derivation hash"
                ),
            }
        ),
        "candidate_cell": _seal(
            {
                "item": "S21D6-013",
                "hypothesis_class": HYPOTHESIS_CLASS,
                "selected_direction": SELECTED_DIRECTION,
                "selected_direction_fitting_rows": 720,
                "reported_but_not_selectable": {
                    "direction": REPORTED_DIRECTION,
                    "fitting_rows": 320,
                    "why_reported": "§2.3 requires every cell and sweep point reported",
                    "why_not_selectable": (
                        "one cell, chosen a priori as the larger fit on a question D5 answered: "
                        "coverage moved one point across a 2.25x span, so there is no volume "
                        "slope to exploit. Two selectable cells would be a search"
                    ),
                },
                "refitted": False,
                "read_from": "the sealed D5 matrices, rehashed on load",
                "lambda": "1",
                "margin_floor": "0",
                "tie_break": "the baseline order",
                "encoder": NORMALISER,
                "fitted_channels": 390,
            }
        ),
        "corpus_roles": _seal(
            {
                "item": "S21D6-014",
                "conformal_half": {
                    "source": "the 100 spent D5 calibration groups, 400 outcomes",
                    "use": "places the bar and certifies nothing",
                    "re_executed": False,
                    "audited_in": "sprint-21d6-reuse-audit.json",
                },
                "certification_half": {
                    "groups": 100,
                    "outcomes": 400,
                    "authored_by": "S21D6-020, freshly, in W1",
                    "read_before_the_bar_exists": False,
                },
                "why_not_a_50_50_split_of_d5": (
                    "§2.3 requires 100 independent decisions in the measured set; a 50/50 split "
                    "certifies 50 and fails a condition the amendment does not touch"
                ),
                "why_not_certify_on_d5": (
                    "its full sweep is published; a holdout that has been read is spent"
                ),
                "disjointness": "no fitted vector may appear in both halves; S21D6-022 proves it",
                "carried_roles": {
                    "final_a": 30,
                    "final_b": 30,
                    "canary": 5,
                    "audited": "sprint-21d6-reuse-audit.json, decision reuse, zero bodies opened",
                },
                "retrieval": {
                    "authored": 0,
                    "condition_24": "inherited under sprint-21d6-condition-24-ruling.json",
                },
            }
        ),
        "selection_rule": _seal(
            {
                "item": "S21D6-015",
                "section": "§2.3 as amended by amendment 2",
                "conditions": [
                    "at least 100 independent clean ranking decisions in the certification set",
                    (
                        "admission by the split-conformal bar at alpha, and a Clopper-Pearson "
                        f"one-sided 95% upper bound at most {CEILING} on the error rate among "
                        "admitted independent decisions"
                    ),
                    "clean coverage at least 0.40",
                    "at least 20 projected changed decisions over the 60 final groups",
                    (
                        "clean first-choice rate over admitted decisions strictly above the "
                        "strongest deterministic baseline on the same decisions"
                    ),
                    "at least one changed clean decision",
                    "100% first-action preservation on the invariance-regression sample",
                    "every cell and sweep point reported, filtered and abstaining ones included",
                    "maximum inference within the 250 ms budget",
                ],
                "ceiling_c": CEILING,
                "bound_at_the_expected_coverage": {
                    str(errors): round(admitted_error_upper_bound(errors, 58), 6)
                    for errors in range(5)
                },
                "what_the_ceiling_replaces": (
                    "zero confident errors in 27 admitted decisions, which bounded the same "
                    "quantity at 0.105 by the same Clopper-Pearson"
                ),
                "a_cell_failing_one_condition_is_not_a_candidate": True,
            }
        ),
        "decision_tree": _seal(
            {
                "item": "S21D6-016",
                "evaluated_on": "the fresh certification set only, once",
                "endings": {
                    "0_admission_contract_refused": (
                        "the amendment is refused; Gate L2 is unclosable with this ranker at "
                        "these volumes and the successor question leaves the confidence axis"
                    ),
                    "1_select": (
                        "all conditions hold; bind the artifact, run the lifecycle, close the "
                        "gate, unblock Sprint 22A"
                    ),
                    "2_leak_budget_exceeded": (
                        "coverage at least 0.40 and the bound above the ceiling; the bar held "
                        "its leak guarantee and admitted precision missed. A tighter alpha needs "
                        "more than 12 wrong decisions in the conformal half, which is a volume "
                        "question and the first measured reason this programme would have to "
                        "author more"
                    ),
                    "3_margin_coverage_bound": (
                        "coverage below 0.40 at the pre-registered alpha; the margin does not "
                        "concentrate errors at low margins on unread evidence. The confidence "
                        "construction has then been varied twice and failed twice, and the next "
                        "axis is §3.3 step 6, hypothesis_class_bound"
                    ),
                    "4_no_quantile": (
                        "unreachable by construction: the rank at this alpha is 11 and the "
                        "conformal half has 12 wrong decisions. If it happens the derivation is "
                        "wrong, not the evidence"
                    ),
                },
                "endings_are_four_different_sprints": True,
                "no_ending_may_be_chosen_after_the_measurement": True,
            }
        ),
    }


def _write() -> None:
    recorded_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    contracts = _contracts()

    contracts_document: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D6",
        "wave": "W0",
        "items": [f"S21D6-{number:03d}" for number in range(12, 17)],
        "recorded_at": recorded_at,
        "revision": 6,
        "contracts": contracts,
        "unchanged_from_d5": {
            "feature_contract": FEATURE_CONTRACT,
            "normaliser": NORMALISER,
            "fitted_channels": 390,
            "hypothesis_class": HYPOTHESIS_CLASS,
            "directions_refitted": 0,
            "gate_contract": GATE_CONTRACT,
            "gate_conditions": 29,
            "counting_rule": "revision 5, the independence census and the independent denominator",
            "note": (
                "D6 changes no encoder, no normaliser, no fitted representation, no hypothesis "
                "class and no direction; it changes the admission rule fitted on top of them"
            ),
        },
        "thresholds_changed": {
            "count": 1,
            "which": "§2.3's admission clause, condition 14",
            "authorised_by": "sprint-21d6-contracts-amendment-2.json",
            "every_other_threshold": "unchanged, including the 0.40 coverage floor",
        },
        "measured_values": 0,
    }
    contracts_document["integrity_content_hash"] = _sha256(_canonical(contracts_document))
    OUTPUTS["contracts"].write_text(
        json.dumps(contracts_document, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    pre: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D6",
        "wave": "W0",
        "items": ["S21D6-017"],
        "recorded_at": recorded_at,
        "revision": 6,
        "supersedes": {
            "revision": 5,
            "sha256": "ed983599bfcdb75993856419de531777d9f4f6cdcce127ead03dcdcddee34b1a",
            "for": "Sprint 21D6 only; revision 5 remains the authority for every D5 record",
        },
        "contracts_sha256": _sha256(OUTPUTS["contracts"].read_bytes()),
        "contract_hashes": {name: body["content_hash"] for name, body in contracts.items()},
        "evidence_children_sha256": {
            name: _sha256((EVIDENCE / name).read_bytes()) for name in W0_CHILDREN
        },
        "amendments": [path.name for path in AMENDMENTS],
        "chronology": {
            "certification_decisions_read": 0,
            "conformal_margins_read": 0,
            "retrieval_holdout_queries_read": 0,
            "final_or_canary_outcomes_inspected": 0,
            "artifacts_fitted": 0,
            "bars_derived": 0,
        },
        #: Disclosed rather than counted. These are released D5 aggregates read to size the
        #: experiment — the same use D5 made of D4's published numbers — and the distinction
        #: from the counters above is that none of them is a D6 outcome. Hiding them would be
        #: the dishonest option; pretending alpha was chosen without them would be worse.
        "design_inputs_from_released_evidence": {
            "sprint-21d5-learner-selection.json": [
                "the risk-coverage sweep, for the infeasibility table in amendment 2",
                "errors_among_all_answered = 12 at 720 rows, for the alpha floor",
                "the two model hashes, for the cell choice",
            ],
            "reading": (
                "alpha and the ceiling are computed from published aggregates and certified on "
                "evidence nobody has read. The bar's placement is effectively known in advance; "
                "what it buys on unread evidence is not, and that is the only thing D6 certifies"
            ),
        },
        "measured_values": 0,
        "what_this_publication_forbids": [
            "re-choosing alpha, the ceiling, the split rule or the admission rule",
            "refitting either direction, or selecting the 320-row cell",
            "moving any Gate L2 or D1 threshold other than the clause amendment 2 names",
            "certifying on the conformal half, or letting one fitted vector reach both halves",
            "authoring final, batch-B or canary bodies unless a whole role fails its audit",
            "reading the D6 certification set before it is authored, separated and sealed",
            "opening a retrieval arm, which would void the condition-24 inheritance",
        ],
    }
    pre["integrity_content_hash"] = _sha256(_canonical(pre))
    OUTPUTS["pre_registration"].write_text(
        json.dumps(pre, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "revision": 6,
                "contracts": sorted(contracts),
                "contracts_sha256": pre["contracts_sha256"],
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "measured_values": 0,
                "thresholds_changed": 1,
                "alpha": ALPHA,
                "ceiling_c": CEILING,
            },
            indent=1,
            sort_keys=True,
        )
    )


def _verify_seal(path: Path, document: dict[str, Any]) -> None:
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    if _sha256(_canonical(body)) != document.get("integrity_content_hash"):
        raise SystemExit(f"{path.name} integrity hash does not match its content")


def _check() -> None:
    documents = {name: json.loads(path.read_text()) for name, path in OUTPUTS.items()}
    for name, document in documents.items():
        _verify_seal(OUTPUTS[name], document)

    pre = documents["pre_registration"]
    if _sha256(OUTPUTS["contracts"].read_bytes()) != pre["contracts_sha256"]:
        raise SystemExit("the contracts file changed after the pre-registration was published")
    for name, expected in pre["evidence_children_sha256"].items():
        if _sha256((EVIDENCE / name).read_bytes()) != expected:
            raise SystemExit(f"W0 authority record changed after publication: {name}")
    for name, expected in pre["contract_hashes"].items():
        body = dict(documents["contracts"]["contracts"][name])
        if body.pop("content_hash") != expected or _sha256(_canonical(body)) != expected:
            raise SystemExit(f"contract {name} does not reproduce its frozen hash")
    if any(pre["chronology"].values()) or pre["measured_values"]:
        raise SystemExit("the pre-registration contains measured values")
    for path in AMENDMENTS:
        amendment = json.loads(path.read_text())
        if amendment["amends"]["gate_contract_sha256"] != GATE_CONTRACT:
            raise SystemExit(f"{path.name} amends a gate contract this revision does not name")

    print(
        json.dumps(
            {
                "checked": sorted(OUTPUTS),
                "contracts_verified": len(pre["contract_hashes"]),
                "w0_children_verified": len(pre["evidence_children_sha256"]),
                "amendments_verified": len(pre["amendments"]),
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "measured_values_before_publication": 0,
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check_chronology(later: tuple[Path, ...]) -> None:
    pre_path = OUTPUTS["pre_registration"]
    pre = json.loads(pre_path.read_text())
    _verify_seal(pre_path, pre)
    expected = _sha256(pre_path.read_bytes())
    published = datetime.fromisoformat(pre["recorded_at"].replace("Z", "+00:00"))

    accepted = []
    for path in later:
        document = json.loads(path.read_text())
        if document.get("pre_registration_sha256") != expected:
            raise SystemExit(f"{path.name} does not carry the pre-registration sha256")
        recorded = datetime.fromisoformat(document["recorded_at"].replace("Z", "+00:00"))
        if recorded < published:
            raise SystemExit(f"{path.name} predates the pre-registration it claims to follow")
        accepted.append(path.name)

    print(
        json.dumps(
            {"pre_registration_sha256": expected, "accepted": sorted(accepted)},
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-chronology", action="store_true")
    parser.add_argument("--later", nargs="*", default=[])
    arguments = parser.parse_args()

    if arguments.check:
        _check()
    if arguments.check_chronology:
        _check_chronology(tuple(Path(item) for item in arguments.later))
    if not arguments.check and not arguments.check_chronology:
        _write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
