"""S21D5-010 through S21D5-016. Revision 5, frozen before the D5 corpora exist.

Seven contracts and one publication. Everything the D5 experiment is allowed to decide is
fixed here, and the record proves it was fixed *first*: `--check` verifies that neither the
contracts nor the W0 authority records changed after publication, and `--check-chronology`
verifies that every later record carries this file's sha256 and is not back-dated.

Revision 5 changes one thing about revision 4 and inherits the rest. The change is which
quantity plays the role of confidence: D4 admitted decisions on the frozen k-NN's absolute
neighbourhood acceptance mass and measured zero-error coverage of exactly zero at both volumes;
D5 admits them on the pairwise direction's top-two projection margin. **No floor moves.** The
0.40 coverage floor, the zero-confident-error rule, the 100-independent-decision minimum, the
20-projected-changed-decision rule, the retrieval floors, the inference budget and the bootstrap
seed are D4's, restated verbatim so that a reader can diff them rather than trust a sentence.

    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d5.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d5.py --check
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_d5.py --check-chronology

Writing is idempotent in content: the same inputs produce the same contract hashes, so a rerun
that changes a hash is a change to the contract and `--check` is what makes that visible.
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

from cognitive_os.learning.pairwise_contrastive import (  # noqa: E402
    FIT_RULE,
    HYPOTHESIS_CLASS,
)
from cognitive_os.learning.selective_operating_point import (  # noqa: E402
    DERIVATION_RULE,
    zero_error_upper_bound,
)

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"

OUTPUTS = {
    "contracts": EVIDENCE / "sprint-21d5-contracts.json",
    "pre_registration": EVIDENCE / "sprint-21d5-pre-registration.json",
}

#: Amendments, in order. A sealed contract is never edited in place; a defect in the *wording*
#: of one is answered by a record naming the unchanged original by hash. None exists yet.
AMENDMENTS: tuple[Path, ...] = ()

#: W0 records that must exist before revision 5 is published. They establish authority; none of
#: them measures the experiment. The diagnostic is here because it is the evidence §3.4 requires
#: for naming a class, and it was published before this contract rather than after it.
W0_CHILDREN = (
    "sprint-21d5-baseline.json",
    "sprint-21d5-provisioning.json",
    "sprint-21d5-reuse-audit.json",
    "sprint-21d5-hypothesis-class-diagnostic.json",
)

#: Unchanged from D3 and D4. Restated so a diff is possible without reading three documents.
FEATURE_CONTRACT = "492c90a5df420de9d1662d17155ac8b28713e69bbd4bbe56208415d6ca076362"
NORMALISER = "cogos-python-alpha-normalizer-v2"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(document)
    sealed["content_hash"] = _sha256(_canonical(document))
    return sealed


def _contracts() -> dict[str, Any]:
    """The seven frozen revision-5 contracts, S21D5-010 through S21D5-015 plus the tree."""
    return {
        "hypothesis_class": _seal(
            {
                "item": "S21D5-010",
                "name": HYPOTHESIS_CLASS,
                "module": "src/cognitive_os/learning/pairwise_contrastive.py",
                "fit_rule": FIT_RULE,
                "regularization": "1",
                "regularization_chosen_on": (
                    "fitting-pool-internal leave-group-out evidence alone, recorded in "
                    "sprint-21d5-hypothesis-class-diagnostic.json before this contract was "
                    "sealed and before any D5 corpus existed"
                ),
                "regularization_may_be_rechosen": False,
                "confidence_quantity": (
                    "the projection margin between the top two candidates of a group"
                ),
                "why_this_class": (
                    "S21D4-039 measured the frozen k-NN ranking above the strongest "
                    "deterministic baseline everywhere and separating its own errors nowhere. "
                    "Its confidence is the top candidate's absolute neighbourhood acceptance "
                    "mass, and among four deliberate near-clones that mass barely moves between "
                    "a right ordering and a wrong one. The failing quantity is within-group "
                    "contrast, so this class fits within-group contrast and confides only in it"
                ),
                "abstention": (
                    "below the margin floor the ranker declines and the caller runs the "
                    "deterministic order; an abstention is never a changed decision and never a "
                    "correct prediction"
                ),
                "tie_break": "the frozen baseline order, never candidate identity",
                "unchanged_from_d4": {
                    "encoder_version": "correction-ranking-v2",
                    "feature_contract_hash": FEATURE_CONTRACT,
                    "normaliser": NORMALISER,
                    "fitted_channels": 390,
                    "note": (
                        "D5 changes no encoder, no normaliser, no channel and no fitted "
                        "representation; it changes the function fitted on top of them"
                    ),
                },
            }
        ),
        "fitting_composition": _seal(
            {
                "item": "S21D5-011",
                "groups": 180,
                "outcomes": 720,
                "composition": {
                    "d4_training_groups": 80,
                    "d4_calibration_groups": 100,
                },
                "authority": (
                    "sprint-21d5-handoff.md section 2: the spent calibration set remains valid "
                    "fitting and diagnostic evidence"
                ),
                "re_execution": (
                    "every group is a task package re-executed as a new campaign under new run "
                    "identities after fresh feature seals; no row is read from a predecessor "
                    "store"
                ),
                "volume_points": [320, 720],
                "whole_groups_only": (
                    "a volume point never lands inside a group; fitting on three of a group's "
                    "four candidates would put the fourth's siblings in the exemplar set and "
                    "call the result a volume effect"
                ),
                "volume_span": (
                    "2.25x, against D4's 1.6x. S21D4-039 recorded its narrow 200-to-320 span as "
                    "a limitation on its own volume arm; this span is the repair, and it costs "
                    "no authoring because the pool is evidence that already exists"
                ),
            }
        ),
        "corpus_submanifests": _seal(
            {
                "item": "S21D5-012",
                "authored_for_d5": {
                    "calibration": {"groups": 100, "outcomes": 400},
                    "retrieval": {"groups": 60, "qualifying_queries_minimum": 50},
                },
                "carried_unopened": {
                    "final_a": {"groups": 30, "outcomes": 120},
                    "final_b": {"groups": 30, "outcomes": 120},
                    "canary": {"groups": 5, "slots": 20},
                },
                "generated": {
                    "invariance_regression": {"groups": 20, "cases": 2, "decisions": 40},
                    "promotion_metamorphic_ood": {
                        "nominal": 120,
                        "independent": 60,
                        "over_final_groups": 60,
                    },
                },
                "separation_rule": (
                    "seven roles, pairwise group-, clone- and source-disjoint; the authored "
                    "calibration corpus must additionally be disjoint from the spent-for-"
                    "selection digest sealed in sprint-21d5-reuse-audit.json"
                ),
                "near_clone_rule": (
                    "normalized_structure_hash and token_stream_hash run every batch, scoped to "
                    "cross-group pairs against every released corpus; a collision withdraws the "
                    "whole group rather than rewriting a variant"
                ),
                "authoring_shape": (
                    "baseline passes visible and fails hidden; variants one and two pass both; "
                    "variant three repairs edge case 1 only; variant four repairs edge case 2 "
                    "only"
                ),
                "retrieval_overproduction": (
                    "60 authored against a floor of 50: a near-clone withdrawal at exactly the "
                    "floor turns one defect into a sprint-arithmetic failure"
                ),
            }
        ),
        "artifact_v3": _seal(
            {
                "item": "S21D5-013",
                "schema_name": "correction-ranking-artifact-v3",
                "dispatch": "on schema_name, beside v1 and v2, which stay byte-identical",
                "why_not_additive_on_v2": (
                    "v2 declares exemplars with min_length 1 and three proportion floors. "
                    "Making them optional would let an exemplar-free v2 artifact load, which is "
                    "the check-that-passes-without-touching-its-question defect the D4 report "
                    "catalogued twelve times"
                ),
                "carried_from_v2": (
                    "every lineage, encoder, channel, dataset, split, manifest, embedding-model "
                    "and numeric-bound field, plus the operating point, its derivation rule and "
                    "the calibration certificate hash"
                ),
                "replacing_the_exemplar_set": [
                    "weights, 390 floats in FITTED_FEATURE_V2_ALLOWLIST order",
                    "regularization",
                    "fitted_group_count",
                    "fitted_pair_count",
                    "margin_floor",
                    "hypothesis_class",
                ],
                "refusals": [
                    "a weight vector that is not 390 long or not finite",
                    "a channel list that is not the v2 allowlist in fitted order",
                    "a non-positive ridge",
                    "a negative margin floor",
                    "a hypothesis_class the loader does not implement",
                    "a schema_name the loader does not know",
                ],
                "inference_dependency": (
                    "none beyond the standard library; numpy is a fitting dependency only"
                ),
            }
        ),
        "retrieval": _seal(
            {
                "item": "S21D5-014",
                "surface": (
                    "the released widened searchable surface with structure_fallback enabled: a "
                    "source whose identifier terms come up empty falls back to its lowercased "
                    "AST node-type terms from the same canonical dump, minus bookkeeping nodes"
                ),
                "surface_excluded_from": ["structural_hash", "ExperienceGraphNode.label"],
                "leak_guard": (
                    "reality_leakage.judgement_leaks over whatever the surface ends up "
                    "carrying, fail-closed on the whole projection rather than filtering a term"
                ),
                "comparator_budget": (
                    "bounded GED under the fixed iteration budget of one that S21D4-041 "
                    "decided; anything measured under a wall clock before D4 stays unreplayable "
                    "and no back-fill is attempted"
                ),
                "arms": [
                    "no_memory",
                    "exact_signature",
                    "lexical",
                    "minilm_vector",
                    "minilm_shortlist_plus_bounded_ged",
                    "reciprocal_rank_fusion",
                ],
                "floors": {"recall_at_5": "0.70", "mrr_at_10": "0.50"},
                "floors_unchanged_from": "Gate L2 condition 24, frozen contract",
                "minimum_queries": 50,
                "holdout_reads": 1,
                "first_failure_precedence": (
                    "the first floor that fails decides the outcome; a near miss is not a pass "
                    "and nothing is reopened to close it"
                ),
                "chance_baseline_reported_beside_every_arm": True,
            }
        ),
        "power_and_yield": _seal(
            {
                "item": "S21D5-015",
                "rule": DERIVATION_RULE,
                "what_zero_errors_certifies": (
                    "zero errors is not evidence of a zero rate, it is evidence of a rate below "
                    "the Clopper-Pearson one-sided 95% upper bound at the admitted count"
                ),
                "clopper_pearson_upper_bound_95": {
                    "at_20_admitted": str(round(zero_error_upper_bound(20), 6)),
                    "at_40_admitted": str(round(zero_error_upper_bound(40), 6)),
                    "at_100_admitted": str(round(zero_error_upper_bound(100), 6)),
                },
                "reading": (
                    "at the 0.40 coverage floor, 40 admitted decisions with zero errors bound "
                    "the true error rate at about 7.2%, not at zero. The floor is a floor on "
                    "what may be claimed, not a claim of perfection, and the sprint report must "
                    "state the bound beside the rate exactly as D4's erratum required"
                ),
                "denominator": (
                    "every accuracy, error and coverage rate divides by the independent "
                    "decision count and names it in the stored bytes; the published schema "
                    "refuses a payload that omits the nominal/independent/replicated triple"
                ),
                "independence_rule": (
                    "a ranking decision is identified by its four fitted feature vectors in "
                    "slot order; two groups sharing one would be one decision counted twice"
                ),
                "diagnostic_estimate_is_not_a_prediction": (
                    "the spent-evidence diagnostic measured 0.22 and 0.32 zero-error coverage "
                    "against a 0.40 floor. Those are estimates on authored data this class has "
                    "already seen. They justify running the experiment; they do not forecast it"
                ),
            }
        ),
        "decision_tree": _seal(
            {
                "item": "S21D5-016",
                "section": "3.3",
                "published_before": "any D5 calibration number is read",
                "step_1": (
                    "fit the direction at 320 and at 720 exemplar rows and measure the risk-"
                    "coverage curve on the fresh calibration set; record coverage-at-zero-error "
                    "at both volumes"
                ),
                "step_3_select": (
                    "some volume reaches zero confident errors on at least 100 independent "
                    "decisions at coverage at least 0.40, projecting at least 20 changed final "
                    "decisions, above the strongest deterministic baseline"
                ),
                "step_4_volume_bound": (
                    "zero-error coverage above zero and below 0.40 at 720 rows and materially "
                    "higher at 720 than at 320: the residual is evidence volume, the yield "
                    "curve is the deliverable, and the successor is a corpus sprint with a "
                    "target volume derived from it"
                ),
                "step_5_selective_margin_bound": (
                    "coverage above zero, below 0.40, flat across both volumes, with "
                    "first-choice rate still above the baseline: the direction ranks and the "
                    "margin cannot certify enough of what it ranks. The successor pre-registers "
                    "a different confidence construction over the same ranker, split-conformal "
                    "over the margin being the obvious candidate, not a different ranker and "
                    "not a larger corpus"
                ),
                "step_6_hypothesis_class_bound": (
                    "coverage at or near zero at both volumes. This contradicts the spent-"
                    "evidence diagnostic and the record must say so in those words: the "
                    "estimate did not transfer to a fresh corpus, and the next question is why "
                    "the authored distributions differ, not which class comes third"
                ),
                "endings_are_four_different_sprints": True,
                "must_not_be_guessed_in_advance": True,
            }
        ),
        "selection_rule": _seal(
            {
                "item": "S21D5-016",
                "inherited_verbatim_from": "Sprint 21D4 backlog section 2.3",
                "thresholds_changed": 0,
                "minimum_independent_decisions": 100,
                "confident_errors_allowed": 0,
                "minimum_clean_coverage": "0.40",
                "minimum_projected_changed_final_decisions": 20,
                "final_groups": 60,
                "first_choice_rate_must_exceed": (
                    "the strongest deterministic baseline measured on the same decisions"
                ),
                "minimum_changed_clean_decisions": 1,
                "first_action_preservation_on_the_invariance_sample": "100%",
                "inference_budget_ms": "250",
                "every_grid_point_reported": ("including filtered and fully abstaining points"),
                "bootstrap": {"seed": 21041, "resamples": 2000, "lower_bound_above": 0},
                "the_only_substitution": (
                    "the admission signal is the top-two projection margin rather than the "
                    "k-NN's absolute neighbourhood acceptance mass. derive_zero_error_point "
                    "treats a confidence as an opaque ordered score, so the certification "
                    "spine, the independence census, the Clopper-Pearson bound and the single-"
                    "derivation rule are inherited without a line of new code"
                ),
            }
        ),
    }


def _write() -> None:
    recorded_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    contracts = _contracts()

    contracts_document: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W0",
        "items": [f"S21D5-{number:03d}" for number in range(10, 17)],
        "recorded_at": recorded_at,
        "revision": 5,
        "contracts": contracts,
        "unchanged_from_d4": {
            "feature_contract": FEATURE_CONTRACT,
            "normaliser": NORMALISER,
            "fitted_channels": 390,
            "gate_contract": ("9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7"),
            "gate_conditions": 29,
            "thresholds_changed": 0,
            "note": (
                "D5 changes no encoder, no normaliser, no fitted representation and no gate "
                "threshold; it changes the hypothesis class fitted on top of them"
            ),
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
        "sprint": "21D5",
        "wave": "W0",
        "items": ["S21D5-016"],
        "recorded_at": recorded_at,
        "revision": 5,
        "supersedes": {
            "revision": 4,
            "sha256": "526d48f83d696290f3ccbb7d06002026d4aa7c05b65c33d95f87c362f83461a9",
            "for": "Sprint 21D5 only; revision 4 remains the authority for every D4 record",
        },
        "contracts_sha256": _sha256(OUTPUTS["contracts"].read_bytes()),
        "contract_hashes": {name: body["content_hash"] for name, body in contracts.items()},
        "evidence_children_sha256": {
            name: _sha256((EVIDENCE / name).read_bytes()) for name in W0_CHILDREN
        },
        "amendments": [path.name for path in AMENDMENTS],
        "chronology": {
            "calibration_decisions_read": 0,
            "retrieval_holdout_queries_read": 0,
            "final_or_canary_outcomes_inspected": 0,
            "artifacts_fitted": 0,
            "thresholds_derived": 0,
        },
        "measured_values": 0,
        "what_this_publication_forbids": [
            "re-choosing the hypothesis class, its regulariser or its confidence definition",
            "moving any Gate L2 or D1 threshold, or the bootstrap seed",
            "reusing any spent D4 calibration or retrieval evidence for a decision",
            "authoring final, batch-B or canary bodies unless a whole role fails its audit",
            "reading the D5 calibration set before it is authored, separated and sealed",
        ],
    }
    pre["integrity_content_hash"] = _sha256(_canonical(pre))
    OUTPUTS["pre_registration"].write_text(
        json.dumps(pre, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "revision": 5,
                "contracts": sorted(contracts),
                "contracts_sha256": pre["contracts_sha256"],
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "measured_values": 0,
                "thresholds_changed": 0,
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
