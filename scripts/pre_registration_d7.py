"""S21D7-013 through S21D7-019. Revision 7, frozen before any D7 measurement exists.

Revision 6 kept D5's class and changed the admission rule. Revision 7 does the inversion: it
keeps **every threshold revision 6 published** — alpha, the ceiling, the coverage floor, the
changed-decisions floor, the inference budget — and changes one thing: **the hypothesis class
under them.** So the document freezes six contracts, and five of them exist to fence the one
that matters.

The contract text is imported from the modules that implement it rather than retyped, so a rule
that drifts in code drifts in the record too and `--check` catches it.

    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d7.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d7.py --check
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d7.py --check-chronology \\
        --later docs/sprints/sprint-21/evidence/sprint-21d7-<later>.json

Publishing this closes the window in which the class could be chosen. Everything after it is
measurement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
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
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    FIT_RULE,
    FITTED_RELATIONAL_CHANNELS,
    HYPOTHESIS_CLASS,
)
from cognitive_os.learning.correction_ladder import LADDER_RUNGS  # noqa: E402
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    FITTED_FEATURE_V2_EMBEDDING,
    FITTED_FEATURE_V2_SCALARS,
)
from cognitive_os.learning.repair_containment import (  # noqa: E402
    REPAIR_CONTAINMENT_CHANNEL,
)

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"

OUTPUTS = {
    "contracts": EVIDENCE / "sprint-21d7-contracts.json",
    "pre_registration": EVIDENCE / "sprint-21d7-pre-registration.json",
}

#: Revision 6's amendment stays in force and is carried, not re-made. D7 amends nothing.
AMENDMENTS: tuple[Path, ...] = (EVIDENCE / "sprint-21d6-contracts-amendment-2.json",)

#: The three rulings and the renewal revision 7 rests on, plus the authority records. Every one
#: of them establishes authority; none of them measures the experiment.
W0_CHILDREN = (
    "sprint-21d7-baseline.json",
    "sprint-21d7-provisioning.json",
    "sprint-21d7-reuse-audit.json",
    "sprint-21d7-demotion-ruling.json",
    "sprint-21d7-ladder-ruling.json",
    "sprint-21d7-condition-24-ruling.json",
    "sprint-21d7-transfer-gap.json",
)

#: Unchanged from D3 through D6. Restated so a diff is possible without reading five documents.
FEATURE_CONTRACT_V2 = "492c90a5df420de9d1662d17155ac8b28713e69bbd4bbe56208415d6ca076362"
NORMALISER = "cogos-python-alpha-normalizer-v2"
GATE_CONTRACT = "9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7"
PREDECESSOR_PRE_REGISTRATION = EVIDENCE / "sprint-21d6-pre-registration.json"

ALPHA = "0.20"
CEILING = "0.15"
COVERAGE_FLOOR = "0.40"
#: The groundwork's sealed fit, and the hash W2 must reproduce bit-for-bit on the same pool.
GROUNDWORK_MODEL_HASH = "d80160c4aa795fadd98fb4e6d4f64b7b29a2a3685c537454b8aff95daa124859"
#: The two released 390-channel directions. Reported by D6, re-scored by nobody.
RELEASED_DIRECTION_720 = "9fd297fb407015374485e8f7ef8fbb557e6f89f7ac3286e2572769fdab937d74"
RELEASED_DIRECTION_320 = "5b15f4af06a2b08d0d8269b59f47127bf97d610a22c12c645f8fbde9fa0f47cd"
#: The demoted half's wrong answered decisions, as the groundwork's diagnostic implies them. The
#: alpha table is a function of it; the in-wave m is whatever W2's sealed re-scoring finds.
WRONG_DECISIONS_IN_THE_DEMOTED_HALF = 16
#: The coverage the design expects, from the same diagnostic. The ceiling table is read at it.
EXPECTED_ADMITTED = 46


def _alpha_floor(wrong: int) -> str:
    """The bound below which `ceil((1-alpha)(m+1))` reaches m and the bar is the prefix rule.

    Rounded **down**, so the published decimal is a value at which the rule still degenerates.
    Typing this constant is how a record ends up refuting its own field name: 2/17 rounded up
    is an alpha whose rank is 15 of 16, which is exactly not the failed rule.
    """
    exact = Decimal(2) / Decimal(wrong + 1)
    return str(exact.quantize(Decimal("0.000001"), rounding=ROUND_DOWN))


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(document)
    sealed["content_hash"] = _sha256(_canonical(document))
    return sealed


def _contracts() -> dict[str, Any]:
    """The six frozen revision-7 contracts, S21D7-013 through S21D7-018."""
    return {
        "feature_contract_v3": _seal(
            {
                "item": "S21D7-013",
                "name": "CorrectionFeatureContractV3",
                "representation": "relational, seven channels, assembled per group",
                "allowlist": list(FITTED_RELATIONAL_CHANNELS),
                "channels": len(FITTED_RELATIONAL_CHANNELS),
                "scalar_half": {
                    "channels": list(FITTED_FEATURE_V2_SCALARS),
                    "source": "the sealed v2 feature records, read by name and unchanged",
                    "re_encoded": False,
                    "normalisation": "D5's inherited clip-and-scale bounds, unchanged",
                },
                "derived_half": {
                    "channel": REPAIR_CONTAINMENT_CHANNEL,
                    "module": "src/cognitive_os/learning/repair_containment.py",
                    "definition": (
                        "the mean, over the other candidates whose repair adds at least one "
                        "line, of the fraction of that candidate's baseline-added lines this "
                        "candidate also carries"
                    ),
                    "availability": "pre_outcome; the baseline module and the candidate sources",
                    "envelope": None,
                    "why_no_envelope": (
                        "the share is in [0, 1] by construction, so a clip-and-scale fitted on "
                        "training rows would add a corpus-dependent parameter to a channel that "
                        "has none. Two corpora are comparable on it without sharing anything"
                    ),
                },
                "channel_rules": {
                    "admissible": (
                        "within-group source-to-source relations: both sides move together under "
                        "the frozen rename cases, so the relation is invariant"
                    ),
                    "banned": (
                        "source-to-requirement relations, under any name. The six cases rename "
                        "every source with one map and rewrite the issue text, so one side of "
                        "that relation moves alone — the v1 query_to_candidate_cosine lesson, "
                        "which v2 removed and v3 does not reintroduce"
                    ),
                },
                "embedding": {
                    "channels": len(FITTED_FEATURE_V2_EMBEDDING),
                    "computed_and_sealed": True,
                    "read_by_any_v3_channel": False,
                    "why_both": (
                        "the v2 record stays complete because the surface scans and the "
                        "independence census read it; the §4 measurement located the "
                        "non-transferring part in exactly these 384 channels, so no v3 channel "
                        "reads one. The seal must make both facts checkable"
                    ),
                },
                "supersedes_for_fitting_only": FEATURE_CONTRACT_V2,
                "encoder_unchanged": NORMALISER,
            }
        ),
        "candidate_cell": _seal(
            {
                "item": "S21D7-014",
                "hypothesis_class": HYPOTHESIS_CLASS,
                "fit_rule": FIT_RULE,
                "module": "src/cognitive_os/learning/containment_contrastive.py",
                "fitted_on": "the released 180-group / 720-row pool, its licensed fitting role",
                "fitted_once": True,
                "lambda": "1",
                "margin_floor": "0",
                "tie_break": "the baseline order",
                "fitted_channels": len(FITTED_RELATIONAL_CHANNELS),
                "cells": 1,
                "volume_ladder": None,
                "why_no_volume_ladder": (
                    "D5 answered volume — coverage moved one point across a 2.25x span — and "
                    "nothing since has reopened it. Two selectable cells would be a search"
                ),
                "model_hash_to_reproduce": GROUNDWORK_MODEL_HASH,
                "reproduction_rule": (
                    "W2 fits the direction, seals it by content hash and reproduces it across a "
                    "process restart. A fit that does not reproduce the hash above on the same "
                    "pool is a determinism defect in the environment and a stop, not a number "
                    "to shrug at: hashes are compared, fits are not repeated"
                ),
                "released_directions_not_re_scored": [
                    RELEASED_DIRECTION_720,
                    RELEASED_DIRECTION_320,
                ],
                "why_not": (
                    "they are a different class over 390 channels, their sweep is published, and "
                    "re-reporting them would be motion without information"
                ),
                "inference_budget_ms": 250,
            }
        ),
        "admission_rule": _seal(
            {
                "item": "S21D7-015",
                "name": "split-conformal-margin-v1",
                "module": "src/cognitive_os/learning/conformal_operating_point.py",
                "derivation_rule": DERIVATION_RULE,
                "derivation_reading": DERIVATION_READING,
                "alpha": ALPHA,
                "alpha_may_be_rechosen": False,
                "alpha_is_carried_not_re_chosen": (
                    "the value comes from amendment 2 and is not re-derived here. What changed "
                    "is the half it is taken from, not the leak budget"
                ),
                "alpha_bounds": (
                    "the leak rate P(admitted | the decision is wrong), not the error rate among "
                    "admitted decisions"
                ),
                "wrong_decisions_in_the_bar_setting_half": WRONG_DECISIONS_IN_THE_DEMOTED_HALF,
                "wrong_decisions_are_a_design_estimate": (
                    "implied by the groundwork's diagnostic rate on the spent D6 corpus; the "
                    "in-wave m is whatever the sealed re-scoring finds"
                ),
                "rank_at_this_alpha": conformal_rank(
                    Decimal(ALPHA), WRONG_DECISIONS_IN_THE_DEMOTED_HALF
                ),
                "wrong_margins_left_above_the_bar": (
                    WRONG_DECISIONS_IN_THE_DEMOTED_HALF
                    - conformal_rank(Decimal(ALPHA), WRONG_DECISIONS_IN_THE_DEMOTED_HALF)
                ),
                "alpha_floor_below_which_the_bar_is_the_failed_rule": _alpha_floor(
                    WRONG_DECISIONS_IN_THE_DEMOTED_HALF
                ),
                "alpha_floor_exact": f"2/{WRONG_DECISIONS_IN_THE_DEMOTED_HALF + 1}",
                "why_that_floor": (
                    "the rank reaches the whole set — and the bar becomes the largest wrong "
                    "margin, which is the zero-error prefix rule D5 stopped on — for every alpha "
                    "strictly below 2/(m+1). The decimal above is that bound rounded down, so it "
                    "is a value at which the rule still degenerates rather than one just past it"
                ),
                "bar_setting_half": "the demoted D6 certification half, per S21D7-010",
                "authorised_by": "sprint-21d6-contracts-amendment-2.json, carried unchanged",
                "single_derivation": (
                    "one bar, derived once from the demoted half; a second derivation that does "
                    "not reproduce the first is refused across a process restart by the "
                    "`previous=` rule, alpha included in the derivation hash"
                ),
            }
        ),
        "corpus_roles": _seal(
            {
                "item": "S21D7-016",
                "bar_setting_half": {
                    "source": "the 100 spent D6 certification groups, 400 outcomes",
                    "use": "places the bar and certifies nothing",
                    "re_executed": False,
                    "re_scored_under": HYPOTHESIS_CLASS,
                    "ruling": "sprint-21d7-demotion-ruling.json",
                    "audited_in": "sprint-21d7-reuse-audit.json",
                },
                "certification_half": {
                    "groups": 100,
                    "outcomes": 400,
                    "authored_by": "S21D7-020, freshly, in W1",
                    "read_before_the_bar_exists": False,
                },
                "fitting_pool": {
                    "groups": 180,
                    "rows": 720,
                    "use": "the one fit this sprint performs",
                },
                "invariance_sample": {"groups": 20, "transformed_decisions": 40},
                "promotion_submanifest": {"nominal": 120, "independent": 60},
                "carried_roles": {
                    "final_a": 30,
                    "final_b": 30,
                    "canary": 5,
                    "audited": "sprint-21d7-reuse-audit.json, decision reuse, zero bodies opened",
                },
                "retrieval": {
                    "authored": 0,
                    "condition_24": "inherited under sprint-21d7-condition-24-ruling.json",
                },
                "why_not_a_50_50_split_of_d6": (
                    "§2.3 requires 100 independent decisions in the measured set; a 50/50 split "
                    "certifies 50 and fails a condition no ruling touches"
                ),
                "disjointness": "no fitted vector may appear in both halves; S21D7-022 proves it",
            }
        ),
        "selection_rule": _seal(
            {
                "item": "S21D7-017",
                "section": "§2.3 as amended by amendment 2, unchanged by D7",
                "thresholds_changed_by_this_revision": 0,
                "conditions": [
                    "at least 100 independent clean ranking decisions in the certification set",
                    (
                        "admission by the split-conformal bar at alpha, and a Clopper-Pearson "
                        f"one-sided 95% upper bound at most {CEILING} on the error rate among "
                        "admitted independent decisions"
                    ),
                    f"clean coverage at least {COVERAGE_FLOOR}",
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
                "coverage_floor": COVERAGE_FLOOR,
                "bound_at_the_expected_coverage": {
                    str(errors): round(admitted_error_upper_bound(errors, EXPECTED_ADMITTED), 6)
                    for errors in range(5)
                },
                "expected_admitted": EXPECTED_ADMITTED,
                "ladder": {
                    "rungs": [*LADDER_RUNGS, REPAIR_CONTAINMENT_CHANNEL],
                    "seated_by": "sprint-21d7-ladder-ruling.json",
                    "strongest_rung_is_derived_not_named": True,
                    "changed_decisions_pair_against": (
                        "the seated ladder's strongest rung; W2 reports both pairings and §2.3 "
                        "reads the seated one"
                    ),
                },
                "a_cell_failing_one_condition_is_not_a_candidate": True,
            }
        ),
        "decision_tree": _seal(
            {
                "item": "S21D7-018",
                "evaluated_on": "the fresh certification set only, once",
                "endings": {
                    "0_successor_contract_refused": (
                        "a §2.2 ruling is refused; the class question cannot be posed under the "
                        "frozen gate and the record states which ruling and why"
                    ),
                    "1_select": (
                        "all nine conditions hold; bind the v3 artifact to the new conformal "
                        "point, run the lifecycle, close the gate, unblock Sprint 22A"
                    ),
                    "2_leak_budget_exceeded": (
                        "coverage at least the floor and the bound above the ceiling. Read "
                        "against the sealed transfer record: the class transferred on two spent "
                        "corpora and failed on unread evidence, which is the exchangeability "
                        "symptom — the successor question is authoring-run drift, not another "
                        "class, and the sealed per-family rates say where"
                    ),
                    "3_margin_coverage_bound": (
                        "coverage below the floor at this alpha; the class ranks but its margin "
                        "does not concentrate errors on unread evidence. The containment rung's "
                        "own result decides whether the signal or the fit is what failed"
                    ),
                    "4_baseline_not_beaten": (
                        "first choice over admitted not above the seated ladder's strongest "
                        "rung. Reachable only because S21D7-011 seated the containment rung: the "
                        "fitted class could not outrank its own strongest channel, which would "
                        "itself be the finding that the other six channels add nothing"
                    ),
                    "5_invariance_violated": (
                        "any first-action flip on the invariance sample. The containment share "
                        "cannot move under the six cases by construction, so a flip indicts the "
                        "scalar half or the assembly, not the signal"
                    ),
                },
                "endings_are_six_different_sprints": True,
                "no_ending_may_be_chosen_after_the_measurement": True,
            }
        ),
    }


def _write() -> None:
    recorded_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    contracts = _contracts()

    contracts_document: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W0",
        "items": [f"S21D7-{number:03d}" for number in range(13, 19)],
        "recorded_at": recorded_at,
        "revision": 7,
        "contracts": contracts,
        "unchanged_from_d6": {
            "normaliser": NORMALISER,
            "encoder": "correction-ranking-v2, unchanged; the v2 records are read, not re-made",
            "alpha": ALPHA,
            "ceiling_c": CEILING,
            "coverage_floor": COVERAGE_FLOOR,
            "admission_rule": "split-conformal-margin-v1",
            "gate_contract": GATE_CONTRACT,
            "gate_conditions": 29,
            "counting_rule": "revision 5, the independence census and the independent denominator",
            "note": (
                "D7 changes no threshold, no admission rule, no alpha and no ceiling. It changes "
                "the hypothesis class under them, and seats one deterministic rung on the "
                "ladder that class must beat"
            ),
        },
        "changed_by_this_revision": {
            "hypothesis_class": {
                "from": "pairwise-contrastive-linear-v1 over 390 channels",
                "to": f"{HYPOTHESIS_CLASS} over {len(FITTED_RELATIONAL_CHANNELS)} channels",
                "licensed_by": (
                    "the §4 transfer measurement's collapse, by the D7 handoff's own decision "
                    "rule; sprint-21d7-transfer-gap.json"
                ),
            },
            "baseline_ladder": {
                "from": f"{len(LADDER_RUNGS)} rungs",
                "to": f"{len(LADDER_RUNGS) + 1} rungs",
                "authorised_by": "sprint-21d7-ladder-ruling.json",
                "direction": "raises the baseline the learned class must beat",
            },
            "bar_setting_half": {
                "from": "the demoted D5 calibration half",
                "to": "the demoted D6 certification half",
                "authorised_by": "sprint-21d7-demotion-ruling.json",
            },
        },
        "thresholds_changed": {"count": 0, "amendments_made_by_d7": 0},
        "measured_values": 0,
    }
    contracts_document["integrity_content_hash"] = _sha256(_canonical(contracts_document))
    OUTPUTS["contracts"].write_text(
        json.dumps(contracts_document, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    pre: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W0",
        "items": ["S21D7-019"],
        "recorded_at": recorded_at,
        "revision": 7,
        "supersedes": {
            "revision": 6,
            "sha256": _sha256(PREDECESSOR_PRE_REGISTRATION.read_bytes()),
            "for": "Sprint 21D7 only; revision 6 remains the authority for every D6 record",
        },
        "contracts_sha256": _sha256(OUTPUTS["contracts"].read_bytes()),
        "contract_hashes": {name: body["content_hash"] for name, body in contracts.items()},
        "evidence_children_sha256": {
            name: _sha256((EVIDENCE / name).read_bytes()) for name in W0_CHILDREN
        },
        "amendments": [path.name for path in AMENDMENTS],
        "amendments_made_by_this_sprint": 0,
        "chronology": {
            "certification_decisions_read": 0,
            "bar_setting_margins_read": 0,
            "retrieval_holdout_queries_read": 0,
            "final_or_canary_outcomes_inspected": 0,
            "artifacts_fitted": 0,
            "directions_fitted": 0,
            "bars_derived": 0,
        },
        #: Disclosed rather than counted. Revision 7's honesty problem is sharper than revision
        #: 6's: the class was constructed after reading D6's published evidence, and its
        #: diagnostic was read off two spent corpora. Hiding that would be the dishonest option;
        #: pretending the thresholds were chosen around it would be worse — they were all frozen
        #: by predecessors before this class existed.
        "design_inputs_from_released_and_groundwork_evidence": {
            "sprint-21d7-transfer-gap.json": [
                "the §4 collapse, which licenses the class question at all",
                "the diagnostic first-choice rates, for the demotion ruling's rank table",
                "the containment rung's rates, for the ladder ruling's cost",
                "the 46-admitted diagnostic, for the ceiling table's expected coverage",
                "the sealed model hash W2 must reproduce",
            ],
            "sprint-21d6-learner-selection.json": [
                "the published sweep showing the amended pair unreachable for the released class"
            ],
            "reading": (
                "every threshold this class must clear was frozen before the class existed, and "
                "the diagnostic that motivated it is sealed and cited rather than repeated. The "
                "46-with-zero-errors observation is an upper bound on hope, exactly as D5's "
                "0.32-below-the-floor was a lower one. The fresh certification is read once"
            ),
        },
        "measured_values": 0,
        "what_this_publication_forbids": [
            "re-choosing the class, the channel allowlist, alpha, the ceiling or any floor",
            "a second fitted class, a second lambda, a second alpha or a volume ladder",
            "refitting the direction after W2 seals it, or deriving the bar twice",
            "certifying on the demoted half, or letting one fitted vector reach both halves",
            "re-pairing the halves after W0, or re-deciding the ladder after W2 measures it",
            "any source-to-requirement channel, under any name",
            "authoring final, batch-B or canary bodies unless a whole role fails its audit",
            "reading the D7 certification set before it is authored, separated and sealed",
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
                "revision": 7,
                "contracts": sorted(contracts),
                "contracts_sha256": pre["contracts_sha256"],
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "measured_values": 0,
                "thresholds_changed": 0,
                "hypothesis_class": HYPOTHESIS_CLASS,
                "fitted_channels": len(FITTED_RELATIONAL_CHANNELS),
                "ladder_rungs": len(LADDER_RUNGS) + 1,
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
    if documents["contracts"]["thresholds_changed"]["count"]:
        raise SystemExit("revision 7 moves a threshold; D7 refuses a second amendment in advance")
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
                "amendments_carried": len(pre["amendments"]),
                "amendments_made_by_this_sprint": pre["amendments_made_by_this_sprint"],
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "measured_values_before_publication": 0,
                "thresholds_changed": 0,
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
