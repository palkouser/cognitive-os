"""S21D4-010 through S21D4-018. Freeze the revision-4 contracts and publish the pre-registration.

Everything here is a *declaration*. Not one measured value appears, which is the property the
chronology check exists to defend: revision 4 has to predate every D4 calibration number, every
threshold derivation, every campaign and every retrieval score, or the intervention was chosen
after seeing results.

    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d4.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d4.py --check
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d4.py --check-chronology \\
        --later-evidence docs/sprints/sprint-21/evidence/<file>.json

`--check` is credential-free and offline by design: it reads committed bytes, so a CI lane with
no database and no network can still prove the pre-registration was not edited after the fact.
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
EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"

OUTPUTS = {
    "contracts": EVIDENCE / "sprint-21d4-contracts.json",
    "pre_registration": EVIDENCE / "sprint-21d4-pre-registration.json",
}

#: Amendments, in order. A sealed contract is never edited in place — that is what the W0-F1
#: refusal was for — so a defect in the *wording* of one is answered by a record that names the
#: unchanged original by hash, states what it replaces, and proves it predates every number the
#: contract governs. `--check` verifies the chain and would fail if the original had been
#: touched. The window is not open indefinitely: Section 3 forbids a threshold change once the
#: fresh calibration set is resolved, so an amendment after S21D4-032 is not an amendment.
AMENDMENTS = (EVIDENCE / "sprint-21d4-contracts-amendment-1.json",)

#: W0 records that must exist before revision 4 is published. They establish authority; they do
#: not measure the experiment.
W0_CHILDREN = (
    "sprint-21d4-baseline.json",
    "sprint-21d4-d3-reconciliation.json",
    "sprint-21d4-authority-isolation.json",
    "sprint-21d4-predecessor-inventory.json",
    "sprint-21d4-finding-w0-f1.json",
    "sprint-21d4-holdout-reuse-audit.json",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(document)
    sealed["content_hash"] = _sha256(_canonical(document))
    return sealed


def _contracts() -> dict[str, Any]:
    """The eight frozen revision-4 contracts, S21D4-010 through S21D4-017."""
    return {
        # S21D4-010
        "decision_independence": _seal(
            {
                "item": "S21D4-010",
                "definitions": {
                    "independent_ranking_decision": (
                        "one ranking decision whose fitted feature vector is distinct from every "
                        "other counted decision in the same set"
                    ),
                    "replicated_decision": (
                        "a counted decision whose fitted vector equals another's; valid "
                        "invariance evidence, never an accuracy, error or coverage denominator"
                    ),
                    "coverage": "answered independent decisions over all independent decisions",
                },
                "invariants": [
                    "nominal == independent + replicated",
                    "every reported rate names its denominator",
                    "accuracy, error and coverage rates use the independent denominator",
                ],
                "refusal": (
                    "schema validation refuses a decision set reporting an accuracy, error or "
                    "coverage rate over the nominal denominator"
                ),
                "d3_replay_expectation": {"nominal": 120, "independent": 20, "replicated": 100},
                "why": (
                    "S21D4-001 recomputed, over all 24 D3 settings, that ood_answered was six "
                    "times clean_answered and confident_ood_errors six times clean errors. The "
                    "metamorphic set was 20 decisions replicated six times."
                ),
            }
        ),
        # S21D4-011
        "selective_operating_point": _seal(
            {
                "item": "S21D4-011",
                "score": "the released bounded k-NN confidence for one ranking decision",
                "derivation": [
                    "compute the score for every independent clean calibration decision",
                    "sort answered decisions by score descending",
                    "the zero-error point is the highest threshold at which every answered "
                    "decision above it is correct",
                    "report its coverage and the Clopper-Pearson one-sided 95% upper bound on "
                    "the true error rate, which for zero errors in n is 1 - 0.05 ** (1 / n)",
                ],
                "operating_point_grid": ["0.55", "0.70", "derived_zero_error"],
                "selection_precedence": (
                    "a released fixed floor is preferred when it satisfies the non-silence "
                    "rules; only if none does may the derived point be selected"
                ),
                "single_shot": (
                    "exactly one derivation, from the declared calibration split only; a "
                    "threshold derived from final, promotion or metamorphic data is invalid"
                ),
                "artifact_binding": (
                    "the derived threshold and its calibration provenance are part of the "
                    "selected candidate's identity and are sealed before final access"
                ),
                "adds": "no model, no fit, no dependency, no new fitted channel",
            }
        ),
        # S21D4-012
        "corpus_reallocation": _seal(
            {
                "item": "S21D4-012",
                "fitting": {
                    "groups": 80,
                    "outcomes": 320,
                    "composition": {
                        "d2_training": 50,
                        "d2_calibration": 10,
                        "d3_calibration": 20,
                    },
                    "every_group_is_a_package_to_re_execute": True,
                    "why": (
                        "D4-W0-F1: the D3 learned store holds no observations and no datasets, "
                        "so no predecessor row can be inherited"
                    ),
                },
                "calibration": {"groups": 100, "outcomes": 400, "minimum_families": 15},
                "volume_points": [200, 320],
                "sprint_21c3_corpus": {
                    "included": False,
                    "reason": (
                        "excluded by release-owner decision, not by failed audit; it would have "
                        "carried the pool to about 110 groups and 440 outcomes only if roughly "
                        "thirty of its groups cleared a rights and disjointness audit that has "
                        "not been run"
                    ),
                    "cost": (
                        "a flat risk-coverage curve between 200 and 320 is weaker evidence for "
                        "hypothesis_class_bound than a flat curve to 440 would have been; "
                        "S21D4-039 must report that limitation rather than let a reader infer a "
                        "stronger conclusion than the spacing supports"
                    ),
                    "available_to_a_successor": True,
                },
                "invariance_regression": {"sample_groups": 20, "cases_per_group": 2},
                "promotion": {"groups": 60, "cases_per_group": 2, "independent": 60},
            }
        ),
        # S21D4-013
        "searchable_surface": _seal(
            {
                "item": "S21D4-013",
                "field": "ActionDecisionGraph.search_terms: tuple[str, ...] = ()",
                "excluded_from": ["structural_hash", "ExperienceGraphNode.label"],
                "included_in": ["content_hash", "search_text()"],
                "why_excluded": (
                    "labelled graph-edit distance, edit-path round-tripping and every stored "
                    "D1, D2 and D3 structural hash must stay byte-unchanged"
                ),
                "derivation": [
                    "resolve each node's source blob through the released graph store",
                    "normalise with correction_source.canonical_source_bytes, the released "
                    "alpha-normaliser",
                    "emit a bounded deterministic term list under the existing 1024-character "
                    "attribute bound and the existing forbidden-marker guard",
                ],
                "leak_guard": (
                    "reality_leakage.judgement_leaks must report nothing; a hit refuses the "
                    "whole projection, fail-closed"
                ),
                "excluded_inputs": ["unnormalised bodies", "issue text", "provenance hashes"],
                "adds": "no new store, no new index, no dependency",
            }
        ),
        # S21D4-014
        "power_and_yield": _seal(
            {
                "item": "S21D4-014",
                "independent_calibration_decisions_floor": 100,
                "clean_coverage_floor": "0.40",
                "changed_final_decisions_floor": 20,
                "final_groups": 60,
                "zero_error_upper_bounds": {
                    str(n): round(1.0 - 0.05 ** (1.0 / n), 6) for n in (20, 60, 100, 300)
                },
                "coverage_floor_justification": (
                    "0.40 over 60 final groups projects 24 answered decisions, which is the "
                    "smallest coverage that can still satisfy condition 13's floor of 20 "
                    "changed decisions"
                ),
                "why_0_80_was_wrong": (
                    "D3's 0.80 floor was a self-imposed rule, not a Gate L2 threshold. Combined "
                    "with a zero-error requirement certified on 20 decisions it was "
                    "unsatisfiable by construction: the grid offered coverage 0.95 with six "
                    "clean errors or 0.50 with two, and nothing between. A selective ranker "
                    "buys precision with coverage, and a floor forbidding the purchase forbids "
                    "the mechanism."
                ),
            }
        ),
        # S21D4-015
        "submanifests": _seal(
            {
                "item": "S21D4-015",
                "calibration_invariance_sample": {
                    "groups": 20,
                    "cases": ["identifier_rename_a", "issue_rewrite_a"],
                    "transformed_decisions": 40,
                    "expected_independent_count": 0,
                    "note": "the transformed set is a regression test, never an accuracy sample",
                },
                "promotion_set": {
                    "groups": 60,
                    "cases_per_group": 2,
                    "nominal_decisions": 120,
                    "independent_decisions": 60,
                    "reported_side_by_side": True,
                },
                "frozen_before_measurement": [
                    "seeds",
                    "generator identity",
                    "hard-coded oracle",
                    "eligibility and applicability rules",
                    "case-id derivation",
                    "label authority",
                    "decision semantics",
                    "counting code",
                ],
                "semantic_mutation_controls": (
                    "seeded operator and branch-condition mutations remain mandatory and must "
                    "change the canonical representation"
                ),
            }
        ),
        # S21D4-016
        "retrieval": _seal(
            {
                "item": "S21D4-016",
                "arms": [
                    "no_memory",
                    "exact_signature",
                    "lexical",
                    "minilm_vector",
                    "minilm_shortlist_plus_bounded_ged",
                    "reciprocal_rank_fusion",
                ],
                "fusion": {"constant": 60, "weights": "equal", "tuned": False},
                "truncation": "once, after full-pool fusion",
                "resource_policy": {
                    "nodes_per_graph": 64,
                    "edges_per_graph": 128,
                    "path_depth": 32,
                    "vector_shortlist": 20,
                    "returned_results": 10,
                    "query_budget_seconds": 2,
                },
                "bounded_ged_decision": {
                    "problem": (
                        "networkx.graph_edit_distance under a wall-clock timeout is an anytime "
                        "search, so the score depends on the host and the moment"
                    ),
                    "option_a": (
                        "a fixed iteration budget from networkx.optimize_graph_edit_distance, "
                        "which is host-independent"
                    ),
                    "option_b": "retirement from the frozen set, reported with its reason",
                    "criterion": (
                        "two identical passes must agree byte for byte on every arm; the arm is "
                        "retired if a fixed budget cannot reproduce a stable ranking"
                    ),
                    "d1_d2_d3_numbers": "stay marked irreproducible; nothing is back-filled",
                },
                "floors": {"recall_at_5": "0.70", "mrr_at_10": "0.50"},
                "minimum_queries": 50,
                "read_once": True,
            }
        ),
        # S21D4-017
        "gates_and_stops": _seal(
            {
                "item": "S21D4-017",
                "gate_l2_conditions": 29,
                "gate_l2_thresholds_changed": 0,
                "gate_d1_open": [6, 7, 15],
                "non_silence_rules": {
                    "independent_clean_decisions": 100,
                    "confident_errors_among_answered": 0,
                    "clean_coverage_floor": "0.40",
                    "projected_changed_final_decisions": 20,
                    "first_choice_above_baseline": True,
                    "changed_clean_decisions_minimum": 1,
                    "action_preservation_on_the_regression_sample": "1.00",
                    "every_grid_point_reported": True,
                },
                "typed_stop_kinds": [
                    "reconciliation_not_reproducible",
                    "volume_bound",
                    "hypothesis_class_bound",
                    "invariance_regression",
                    "ood_deficient",
                    "feature_boundary_wrong",
                ],
                "not_opened_record": {
                    "fields": ["item", "status", "stop_hash", "stop_source", "would_have"],
                    "status": "not_opened",
                },
                "success_tag": "sprint-21-learning-baseline",
                "negative_tag": "sprint-21d4-evidence-baseline",
            }
        ),
    }


def _write() -> None:
    recorded_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    contracts = _contracts()

    contracts_document = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W0",
        "items": [f"S21D4-{number:03d}" for number in range(10, 18)],
        "recorded_at": recorded_at,
        "revision": 4,
        "contracts": contracts,
        "unchanged_from_d3": {
            "feature_contract": (
                "492c90a5df420de9d1662d17155ac8b28713e69bbd4bbe56208415d6ca076362"
            ),
            "normaliser": "cogos-python-alpha-normalizer-v2",
            "fitted_channels": 390,
            "note": "D4 changes no encoder, no normaliser and no fitted representation",
        },
        "measured_values": 0,
    }
    contracts_document["integrity_content_hash"] = _sha256(_canonical(contracts_document))
    OUTPUTS["contracts"].write_text(
        json.dumps(contracts_document, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    children = {
        name: _sha256((EVIDENCE / name).read_bytes())
        for name in W0_CHILDREN
        if (EVIDENCE / name).is_file()
    }
    missing = [name for name in W0_CHILDREN if name not in children]
    if missing:
        raise SystemExit(f"W0 authority records are missing: {missing}")

    pre_registration = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W0",
        "items": ["S21D4-018"],
        "revision": 4,
        "recorded_at": recorded_at,
        "predecessor_release": {
            "tag": "sprint-21d3-evidence-baseline",
            "tag_object": "bcf2976dd0f063b1eb4ea16b388eea590e6172dd",
            "peeled_commit": "ef4388b1bf9cb842b25a06aa2255abd1042702c2",
        },
        "contract_hashes": {name: body["content_hash"] for name, body in contracts.items()},
        "contracts_sha256": _sha256(OUTPUTS["contracts"].read_bytes()),
        "evidence_children_sha256": children,
        "decision_tree": [
            "replay the D3 grid under corrected independence denominators; a failure to "
            "reproduce stops with reconciliation_not_reproducible",
            "fit at 200 and at 320 rows and measure the risk-coverage curve on the fresh "
            "calibration set",
            "a grid point reaching zero errors over at least 100 independent decisions at "
            "coverage at least 0.40 proceeds to selection",
            "zero-error coverage above zero but below 0.40 at 320, and materially higher at "
            "320 than at 200, stops with volume_bound",
            "zero-error coverage at or near zero at both volumes and not improving with volume "
            "stops with hypothesis_class_bound",
        ],
        "chronology": {
            "d4_calibration_measurements": 0,
            "d4_threshold_derivations": 0,
            "d4_campaign_outcomes": 0,
            "d4_retrieval_scores": 0,
            "final_or_canary_outcomes_inspected": 0,
        },
        "measured_values": 0,
        "later_evidence_must": (
            "carry this file's sha256 as pre_registration_sha256 and be recorded after recorded_at"
        ),
    }
    pre_registration["integrity_content_hash"] = _sha256(_canonical(pre_registration))
    OUTPUTS["pre_registration"].write_text(
        json.dumps(pre_registration, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "contracts": OUTPUTS["contracts"].name,
                "pre_registration": OUTPUTS["pre_registration"].name,
                "contract_count": len(contracts),
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "measured_values": 0,
            },
            indent=1,
            sort_keys=True,
        )
    )


def _write_amendment_one() -> None:
    """S21D4-011 amendment 1: the derivation step named a family of thresholds, not a point."""
    sys.path.insert(0, str(REPO / "src"))
    from cognitive_os.learning.selective_operating_point import (
        AMENDED_DERIVATION_STEP,
        DERIVATION_RULE,
        SEALED_DERIVATION_STEP,
    )

    contracts = json.loads(OUTPUTS["contracts"].read_text())
    sealed = contracts["contracts"]["selective_operating_point"]
    if SEALED_DERIVATION_STEP not in sealed["derivation"]:
        raise SystemExit("the sealed contract does not contain the sentence being amended")

    body = {key: value for key, value in sealed.items() if key != "content_hash"}
    if _sha256(_canonical(body)) != sealed["content_hash"]:
        raise SystemExit("the sealed contract no longer reproduces its frozen hash")

    pre = json.loads(OUTPUTS["pre_registration"].read_text())
    record = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W2",
        "amendment": 1,
        "items": ["S21D4-011"],
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
        "amends": {
            "contract": "selective_operating_point",
            "frozen_content_hash": sealed["content_hash"],
            "contracts_sha256": _sha256(OUTPUTS["contracts"].read_bytes()),
            "bytes_modified": 0,
        },
        "defect": {
            "sealed_sentence": SEALED_DERIVATION_STEP,
            "why_it_names_no_point": (
                "the thresholds admitting only correct answered decisions are upward-closed: if "
                "every answered decision above t is correct, the same holds for every t' > t, up "
                "to the threshold that admits nothing at all. The sealed sentence therefore "
                "picks out an unbounded family, and its largest member has coverage zero, which "
                "is the opposite of the quantity the contract goes on to require be reported."
            ),
            "found_by": (
                "implementing it at S21D4-021; the implementation had to choose an end of the "
                "interval and recorded the choice in derivation_reading rather than leave it "
                "implicit"
            ),
        },
        "amended_sentence": AMENDED_DERIVATION_STEP,
        "operative_rule": DERIVATION_RULE,
        "operative_rule_sha256": _sha256(DERIVATION_RULE.encode("utf-8")),
        "unchanged_by_this_amendment": [
            "the score, which is the released bounded k-NN confidence",
            "calibration-split-only derivation",
            "the single-derivation rule",
            "the operating-point grid and the selection precedence",
            "the Clopper-Pearson reporting requirement",
            "every other contract, and every threshold or floor in Section 2.3",
        ],
        "chronology": {
            "d4_threshold_derivations_at_amendment_time": 0,
            "d4_calibration_measurements_at_amendment_time": 0,
            "fresh_calibration_set_resolved": False,
            "why_this_matters": (
                "pre-registration exists to stop a rule being chosen after its result is known. "
                "No D4 threshold has been derived and no D4 calibration outcome exists, so this "
                "amendment cannot have been steered by one. Section 3 closes the window at "
                "S21D4-032, when the fresh calibration set is sealed."
            ),
        },
        "why_not_an_in_place_edit": (
            "a sealed record is not edited after publication. The original bytes are unchanged "
            "and still reproduce their frozen hash, which --check verifies; this record "
            "supersedes one sentence and names what it replaced, exactly as S21D4-001 handled "
            "the D3 erratum."
        ),
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    AMENDMENTS[0].write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": AMENDMENTS[0].name,
                "amends": "selective_operating_point",
                "frozen_contract_hash_unchanged": sealed["content_hash"]
                == pre["contract_hashes"]["selective_operating_point"],
                "contract_bytes_modified": 0,
                "thresholds_derived_before_amendment": 0,
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check_amendments(documents: dict[str, Any]) -> list[dict[str, Any]]:
    """Every amendment must leave the record it amends byte-identical, and follow it in time."""
    pre = documents["pre_registration"]
    published = datetime.fromisoformat(pre["recorded_at"].replace("Z", "+00:00"))
    checked: list[dict[str, Any]] = []
    for path in AMENDMENTS:
        if not path.is_file():
            continue
        amendment = json.loads(path.read_text())
        _verify_seal(path, amendment)
        name = amendment["amends"]["contract"]
        if amendment["amends"]["frozen_content_hash"] != pre["contract_hashes"][name]:
            raise SystemExit(f"{path.name} amends a contract hash the pre-registration never had")
        if amendment["amends"]["contracts_sha256"] != _sha256(OUTPUTS["contracts"].read_bytes()):
            raise SystemExit(f"{path.name}: the contracts file changed after the amendment")
        if amendment["pre_registration_sha256"] != _sha256(
            OUTPUTS["pre_registration"].read_bytes()
        ):
            raise SystemExit(f"{path.name} does not carry the pre-registration sha256")
        recorded = datetime.fromisoformat(amendment["recorded_at"].replace("Z", "+00:00"))
        if recorded < published:
            raise SystemExit(f"{path.name} predates the pre-registration it amends")
        governed = (
            "d4_threshold_derivations_at_amendment_time",
            "d4_calibration_measurements_at_amendment_time",
        )
        if any(amendment["chronology"][key] for key in governed):
            raise SystemExit(f"{path.name} was recorded after the numbers it governs")
        checked.append({"amendment": amendment["amendment"], "contract": name})
    return checked


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

    amendments = _check_amendments(documents)

    print(
        json.dumps(
            {
                "checked": sorted(OUTPUTS),
                "contracts_verified": len(pre["contract_hashes"]),
                "w0_children_verified": len(pre["evidence_children_sha256"]),
                "amendments_verified": amendments,
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
        carried = document.get("pre_registration_sha256")
        if carried != expected:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-chronology", action="store_true")
    parser.add_argument("--later-evidence", nargs="*", default=[])
    parser.add_argument(
        "--amend-one",
        action="store_true",
        help="write amendment 1 to the selective_operating_point derivation step",
    )
    arguments = parser.parse_args()

    if arguments.check_chronology:
        _check_chronology(tuple(Path(item) for item in arguments.later_evidence))
    elif arguments.amend_one:
        _write_amendment_one()
    elif arguments.check:
        _check()
    else:
        _write()


if __name__ == "__main__":
    main()
