"""S21D7-010, S21D7-011 and S21D7-012. The three governance decisions W0 exists to obtain.

None of them is a sprint's own edit, and — unlike D6's — none of them moves a threshold. D7 asks
for no amendment: alpha, the ceiling, the coverage floor and every §2.3 sentence stay as D6 left
them. What the gate owner is asked for is which evidence may set the bar, which ladder §2.3
reads, and whether a condition may be inherited a second time.

**The demotion ruling (S21D7-010).** The bar-setting half and the certified half may share no
fitted vector, and §2.3 counts 100 independent decisions in the *measured* set, so the
bar-setting half has to come from spent evidence. The ruling names D6's 100 certification
decisions and states the rule in both directions: a demoted half may set a threshold and may
never certify. The alternative is priced by recomputation rather than by prose — at the wrong
count the *other* candidate half carries, alpha = 0.20 has no quantile to take.

**The ladder ruling (S21D7-011).** The containment ordering is deterministic, so it is a
legitimate sixth rung. Seating it raises the baseline the learned class must beat, and the
record recomputes by how much from the sealed groundwork record rather than asserting it. The
trade is decided here, before W2 measures anything, because a rung chosen after the numbers are
in is a baseline chosen to be beaten.

**The condition-24 renewal (S21D7-012).** D6's ruling inherited D5's sealed retrieval
measurement conditionally, on three identities. D7 renews it on the same three, re-bound to the
same released hashes, with the same falsifier and the same re-check at gate close.

    UV_CACHE_DIR=.cache/uv uv run python scripts/contracts_d7.py

Read-only apart from the three records it writes. It derives no threshold and reads no margin.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.learning.conformal_operating_point import conformal_rank  # noqa: E402
from cognitive_os.learning.correction_ladder import LADDER_RUNGS  # noqa: E402
from cognitive_os.learning.repair_containment import (  # noqa: E402
    REPAIR_CONTAINMENT_CHANNEL,
)

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
GROUNDWORK = EVIDENCE / "sprint-21d7-transfer-gap.json"

GATE_CONTRACT_SHA256 = "9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7"

ALPHA = Decimal("0.20")
CEILING = Decimal("0.15")
COVERAGE_FLOOR = Decimal("0.40")

#: The gate owner's authority for all three decisions, and the words that carried them. Recorded
#: rather than assumed: a ruling whose approval cannot be pointed at is a ruling a sprint made
#: for itself.
AUTHORITY = {
    "role": "sprint and gate owner",
    "decided_at": "2026-08-10",
    "instruction": "execute the W0 wave of the attached plan",
    "shown": [
        "sprint-21d7-technical-backlog.md §2.1, what is proven infeasible and what is licensed",
        "sprint-21d7-technical-backlog.md §2.2, the three rulings as drafted",
        "sprint-21d7-technical-backlog.md §2.2b, both sides of the ladder trade and its cost",
        "sprint-21d7-technical-backlog.md §3.2, the rank table under each candidate half",
        "sprint-21d7-technical-backlog.md §4.1, the condition-24 renewal and what it saves",
    ],
    "decisions": {
        "conformal_half_demotion": "granted, on D6's 100 certification decisions",
        "ladder_rung": "granted: the containment ordering is seated as a sixth rung",
        "feature_contract_v3": "granted; frozen in revision 7, not in this record",
        "condition_24_renewal": "granted, on D6's exact form",
    },
    "reading": (
        "the backlog names all three rulings plus the renewal as W0's business and the "
        "instruction to execute W0 under it carries them. The ladder ruling was put to the gate "
        "owner as an explicit either/or, with the baseline each side implies, and the answer was "
        "to seat the rung — the side that raises the bar the learned class must clear. Every "
        "record here is one edit from withdrawal while no D7 measurement exists, which is the "
        "state the chronology below proves"
    ),
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _groundwork() -> dict[str, Any]:
    return json.loads(GROUNDWORK.read_text(encoding="utf-8"))


def _wrong_count(first_choice_rate: str, groups: int) -> int:
    """Wrong answered decisions implied by a sealed first-choice rate over `groups`."""
    return int(groups - Decimal(str(first_choice_rate)) * groups)


def _rank_table(wrong: int) -> dict[str, Any]:
    """`ceil((1-alpha)(m+1))` at each alpha, and what is left above the bar.

    A rank above `m` is no quantile at all; a rank equal to `m` puts the bar at the largest
    wrong margin, which is the zero-error prefix rule D5 stopped on wearing a new name.
    """
    table = {}
    for alpha in ("0.05", "0.10", "0.15", "0.20", "0.25"):
        rank = conformal_rank(Decimal(alpha), wrong)
        table[alpha] = {
            "rank": rank,
            "wrong_margins_above_the_bar": max(wrong - rank, 0),
            "quantile_exists": rank <= wrong,
            "degenerates_to_the_prefix_rule": rank >= wrong,
        }
    return table


#: Every D7 record that establishes authority rather than measuring the experiment. The
#: chronology field below lists what is *not* on this list, so it means "no measurement record
#: exists" rather than "no file exists" — W0-F3. Written the other way, the field goes non-empty
#: the moment the W0 records are regenerated in dependency order, which says nothing about
#: whether a number has been read.
W0_AUTHORITY_RECORDS = frozenset(
    {
        "sprint-21d7-baseline.json",
        "sprint-21d7-provisioning.json",
        "sprint-21d7-authority-isolation-after.json",
        "sprint-21d7-transfer-gap.json",
        "sprint-21d7-reuse-audit.json",
        "sprint-21d7-demotion-ruling.json",
        "sprint-21d7-ladder-ruling.json",
        "sprint-21d7-condition-24-ruling.json",
        "sprint-21d7-contracts.json",
        "sprint-21d7-pre-registration.json",
    }
)


def _no_measurement_exists() -> dict[str, Any]:
    """The window these rulings have to be inside: before any D7 number exists."""
    measurement_records = sorted(
        path.name
        for path in EVIDENCE.glob("sprint-21d7-*.json")
        if path.name not in W0_AUTHORITY_RECORDS
    )
    artifact_root = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7")
    return {
        "d7_conformal_bars_derived": 0,
        "d7_certification_outcomes": 0,
        "d7_certification_corpus_authored": False,
        "d7_directions_fitted": 0,
        "d7_measurement_records_present": measurement_records,
        "authority_records_excluded_from_that_list": sorted(W0_AUTHORITY_RECORDS),
        "d7_artifact_store_entries": (
            sum(1 for path in artifact_root.rglob("*") if path.is_file())
            if artifact_root.exists()
            else 0
        ),
        "groundwork_is_not_a_measurement_of_this_sprint": (
            "sprint-21d7-transfer-gap.json is present and read by these rulings. It measures "
            "released D5 and D6 bytes, contains no D7 outcome, and its admission simulation is "
            "discarded by its own text. §6 of the backlog prices exactly this: the class was "
            "found after reading spent evidence, and the fresh certification is read once"
        ),
    }


def _demotion_ruling() -> dict[str, Any]:
    """S21D7-010. Which spent half may set the bar, and the arithmetic that chooses it."""
    groundwork = _groundwork()
    diagnostic = groundwork["class_diagnostic"]
    candidates = {
        "d6_certification": {
            "role_in_its_own_sprint": "the certified half; its full sweep is published",
            "groups": 100,
            "spent_times_before_d7": 1,
            "first_choice_rate_under_the_new_class": str(
                diagnostic["first_choice_rate"]["d6_certification"]
            ),
        },
        "d5_calibration": {
            "role_in_its_own_sprint": "D5's calibration half, then D6's bar-setting half",
            "groups": 100,
            "spent_times_before_d7": 2,
            "first_choice_rate_under_the_new_class": str(
                diagnostic["first_choice_rate"]["d5_calibration"]
            ),
        },
    }
    for body in candidates.values():
        wrong = _wrong_count(body["first_choice_rate_under_the_new_class"], body["groups"])
        body["wrong_answered_decisions"] = wrong
        body["rank_table"] = _rank_table(wrong)
        body["alpha_0_20_is_a_genuine_quantile"] = bool(
            body["rank_table"][str(ALPHA)]["quantile_exists"]
            and not body["rank_table"][str(ALPHA)]["degenerates_to_the_prefix_rule"]
        )

    return {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W0",
        "items": ["S21D7-010"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ruling": "D6's 100 certification decisions are demoted to D7's bar-setting half",
        "authority": AUTHORITY,
        "thresholds_changed": 0,
        "gate_contract_sha256": GATE_CONTRACT_SHA256,
        "gate_contract_bytes_modified": 0,
        "why_a_demotion_is_needed_at_all": (
            "§2.3 counts 100 independent decisions in the measured set and the two halves may "
            "share no fitted vector, so a sprint that authors 100 fresh groups must take its "
            "bar-setting half from spent evidence. D6 applied the same one-step demotion to D5's "
            "calibration half; this is that step, one sprint on"
        ),
        "the_rule_in_both_directions": {
            "may": "set a threshold, once, from margins re-scored out of a sealed campaign",
            "may_not": (
                "certify coverage, an error rate, a first-choice rate or a candidate; appear in "
                "the measured set; or be re-executed under new run identities"
            ),
            "binding": (
                "the half is bound by the released certification matrix hash below, and the "
                "re-scoring must reproduce that hash from the released bytes before a single "
                "margin is read"
            ),
        },
        "named_half": {
            "half": "d6_certification",
            "matrix_hash": groundwork["inputs"]["d6_certification_matrix_hash"],
            "campaign_sha256": groundwork["inputs"]["d6_certification_campaign_sha256"],
            "feature_seals_sha256": groundwork["inputs"]["d6_feature_seals_sha256"],
            "re_executed": False,
            "re_scored_under": diagnostic["hypothesis_class"],
        },
        "justification": {
            "read_from": GROUNDWORK.name,
            "read_from_sha256": _sha256_file(GROUNDWORK),
            "alpha": str(ALPHA),
            "candidates": candidates,
            "rule": "ceil((1-alpha)*(m+1)) over the wrong answered decisions of the half",
            "reading": (
                "at the wrong count D5's twice-spent half carries under this class, the rank at "
                "alpha = 0.20 is the whole set: the bar becomes the largest wrong margin, which "
                "is the zero-error prefix rule D5 stopped on and carries no conformal content. "
                "D6's half is the only candidate at which this alpha is a genuine quantile"
            ),
            "the_in_wave_number_is_not_this_one": (
                "the wrong counts above are implied by the groundwork's diagnostic first-choice "
                "rates on spent corpora. The m that sets the bar is whatever W2's sealed "
                "re-scoring finds, and the ruling names the half, not the count"
            ),
        },
        "chronology": _no_measurement_exists(),
        "unchanged_by_this_ruling": [
            "alpha, the ceiling C, the coverage floor and every other §2.3 sentence",
            "the gate contract and all 29 conditions",
            "the released encoder, normaliser, directions and hypothesis class",
            "the carried final, batch-B and canary roles, which stay unopened",
        ],
        "if_refused": (
            "D7 does not run. §3.4 branch 0, stop kind successor_contract_refused: the class "
            "question cannot be posed under the frozen gate, because no half is left that may "
            "set a bar"
        ),
    }


def _ladder_ruling() -> dict[str, Any]:
    """S21D7-011. The sixth rung, decided before the numbers that would tempt either way."""
    groundwork = _groundwork()
    diagnostic = groundwork["class_diagnostic"]
    containment = diagnostic["containment_rung_alone_first_choice"]

    corpora = {}
    for corpus in groundwork["transfer_gap"]["corpora"]:
        eligible = {
            rung["rung"]: Decimal(str(rung["first_choice_rate"]))
            for rung in corpus["rungs"]
            if rung["eligible"]
        }
        released_best = max(eligible.items(), key=lambda item: item[1])
        rung_rate = Decimal(str(containment[corpus["corpus"]]))
        corpora[corpus["corpus"]] = {
            "released_rungs": {name: str(rate) for name, rate in eligible.items()},
            "strongest_released_rung": released_best[0],
            "strongest_released_rate": str(released_best[1]),
            "containment_rung_rate": str(rung_rate),
            "seated_baseline": str(max(released_best[1], rung_rate)),
            "raises_the_baseline_by": str(max(released_best[1], rung_rate) - released_best[1]),
            "containment_is_strongest": rung_rate > released_best[1],
        }

    return {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W0",
        "items": ["S21D7-011"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ruling": "the containment ordering is seated as a sixth rung on the frozen ladder",
        "authority": AUTHORITY,
        "thresholds_changed": 0,
        "rung": {
            "name": REPAIR_CONTAINMENT_CHANNEL,
            "ordering": "descending containment share, ties on the frozen baseline order",
            "module": "src/cognitive_os/learning/repair_containment.py",
            "kind": "deterministic",
            "reads_a_label": False,
            "reads_only": "the baseline module and the four candidate sources, pre-outcome",
            "why_it_qualifies": (
                "a rung must be deterministic, label-free and computable before the sandbox "
                "runs. The containment ordering is all three, and a signal a learned class is "
                "allowed to fit is a signal the ladder is allowed to run alone"
            ),
        },
        "frozen_five": list(LADDER_RUNGS),
        "ladder_after_this_ruling": [*LADDER_RUNGS, REPAIR_CONTAINMENT_CHANNEL],
        "what_it_costs": {
            "read_from": GROUNDWORK.name,
            "read_from_sha256": _sha256_file(GROUNDWORK),
            "corpora": corpora,
            "reading": (
                "on both spent corpora the containment rung alone is stronger than every "
                "released rung, so seating it replaces the baseline §2.3's first-choice "
                "condition reads. The learned class must then outrank its own strongest channel "
                "on fresh evidence rather than outrank lexical similarity"
            ),
            "changed_decisions_re_pair": (
                "§2.3's changed-decisions conditions pair against the strongest rung's order, so "
                "seating the rung re-pairs them against the containment-first order — a count "
                "the groundwork did not measure. W2 reports both pairings; this ruling fixes "
                "that §2.3 reads the seated one"
            ),
            "diagnostic_headroom": (
                "the simulated first-choice rate over admitted decisions was 1.00, which clears "
                "even the seated baseline. That is an upper bound on hope read off spent "
                "evidence, not a promise about the fresh corpus"
            ),
        },
        "why_this_is_decided_now": (
            "refusing the rung is legitimate and deciding it after seeing W2's numbers is not. "
            "A ladder chosen once the learned rate is known is a baseline chosen to be beaten, "
            "which is the one failure a deterministic baseline exists to prevent"
        ),
        "what_it_does_not_change": [
            "the five released rungs, their implementations and their eligibility rules",
            "any released ladder record; D2 through D6 measured the five and stay as they are",
            "any threshold: the first-choice condition is 'strictly above the strongest rung' "
            "either way, and only which rung that is has moved",
        ],
        "chronology": _no_measurement_exists(),
        "if_refused": (
            "the frozen five stand, §2.3 reads lexical_similarity as the strongest rung on a "
            "D6-shaped corpus, and W2 reports the containment rung as an unseated measurement. "
            "A legitimate outcome, not a stop"
        ),
    }


def _condition_24_ruling() -> dict[str, Any]:
    """S21D7-012. D6's inheritance renewed on its exact form, with the same falsifier."""
    decision = EVIDENCE / "sprint-21d5-retrieval-decision.json"
    surface = EVIDENCE / "sprint-21d5-surface.json"
    predecessor = EVIDENCE / "sprint-21d6-condition-24-ruling.json"
    decided = json.loads(decision.read_text(encoding="utf-8"))
    projected = json.loads(surface.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W0",
        "items": ["S21D7-012"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "condition": 24,
        "standing_rule": (
            "§2.2: every sprint re-evidences all 29 conditions against its own authorities. "
            "Fourteen met in D6 are fourteen met in D6"
        ),
        "ruling": "inherited from D5's sealed measurement, conditionally, renewed for D7",
        "renews": {
            "record": predecessor.name,
            "record_sha256": _sha256_file(predecessor),
            "form": "identical: same measurement, same three identities, same re-check",
            "why_a_renewal_and_not_a_reference": (
                "the inheritance is prospective and its falsifier is about the *sprint that "
                "claims it*. D6's ruling says D6 changed none of the three; only a D7 record can "
                "say that about D7"
            ),
        },
        "authority": AUTHORITY,
        "what_it_saves": {
            "authored_retrieval_groups": 60,
            "qualifying_queries": 50,
            "waves_shortened": "W1 stays a single authoring wave",
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
                "voided_if": "D7 opens an arm, a fusion variant, a weight, a width or a metric",
            },
            "comparator": {
                "chance_baseline": decided["chance_baseline"],
                "voided_if": "D7 changes the comparator or the holdout membership",
            },
        },
        "why_d7_changes_none_of_the_three": (
            "D7 authors no retrieval group, opens no arm, and changes neither the searchable "
            "surface nor the comparator. The sixth ladder rung S21D7-011 seats is a *correction "
            "ranking* rung on four presented candidates; it touches no retrieval arm and no "
            "shortlist width, so it is outside all three identities"
        ),
        "re_checked_at": (
            "gate close, by recomputing the three identities above from D7's own tree and "
            "refusing the inheritance if any hash moved"
        ),
        "d7_reads_no_retrieval_holdout": True,
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
    demotion = _sealed(_demotion_ruling(), EVIDENCE / "sprint-21d7-demotion-ruling.json")
    ladder = _sealed(_ladder_ruling(), EVIDENCE / "sprint-21d7-ladder-ruling.json")
    renewal = _sealed(_condition_24_ruling(), EVIDENCE / "sprint-21d7-condition-24-ruling.json")
    print(
        json.dumps(
            {
                "demotion": {
                    "output": "sprint-21d7-demotion-ruling.json",
                    "integrity_content_hash": demotion["integrity_content_hash"],
                    "named_half": demotion["named_half"]["half"],
                    "thresholds_changed": demotion["thresholds_changed"],
                    "wrong_decisions": {
                        name: body["wrong_answered_decisions"]
                        for name, body in demotion["justification"]["candidates"].items()
                    },
                    "alpha_is_a_genuine_quantile": {
                        name: body["alpha_0_20_is_a_genuine_quantile"]
                        for name, body in demotion["justification"]["candidates"].items()
                    },
                },
                "ladder": {
                    "output": "sprint-21d7-ladder-ruling.json",
                    "integrity_content_hash": ladder["integrity_content_hash"],
                    "rungs_after": len(ladder["ladder_after_this_ruling"]),
                    "baseline": {
                        corpus: body["seated_baseline"]
                        for corpus, body in ladder["what_it_costs"]["corpora"].items()
                    },
                    "raises_the_baseline_by": {
                        corpus: body["raises_the_baseline_by"]
                        for corpus, body in ladder["what_it_costs"]["corpora"].items()
                    },
                },
                "condition_24": {
                    "output": "sprint-21d7-condition-24-ruling.json",
                    "integrity_content_hash": renewal["integrity_content_hash"],
                    "condition": renewal["condition"],
                    "ruling": renewal["ruling"],
                    "authored_groups_saved": renewal["what_it_saves"]["authored_retrieval_groups"],
                },
                "coverage_floor_unchanged": str(COVERAGE_FLOOR),
                "ceiling_unchanged": str(CEILING),
            },
            indent=1,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
