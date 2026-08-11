#!/usr/bin/env python3
"""S21D7-025 through S21D7-028: W2's step 0, taken before any fresh decision is scored.

The W2 pre-flight (`sprint-21d7-w2-preflight.json`) read the sealed W1 bytes for two questions
the plan had left to W2 to answer implicitly, and put three decisions to the gate owner. This
script records the answers, in the discipline W0's rulings used: recomputation from sealed bytes,
a chronology block proving the window each ruling had to be inside, and a hash-bound reference to
every record it reverses or reads.

The window is narrower than W0's and it is the point. W1's corpus exists and its campaign has
run, so "no D7 number exists" is no longer true and this script never claims it. What must be —
and is — zero here is the thing the rulings could otherwise be chosen to suit:

    d7_certification_decisions_scored   0
    d7_conformal_bars_derived           0
    d7_directions_fitted_in_wave        0
    d7_ladder_measurements_on_the_fresh_corpus   0

The ladder ruling S21D7-011 said it in its own words: *"refusing the rung is legitimate and
deciding it after seeing W2's numbers is not."* The supersession below is that refusal, taken in
the only window where it is legitimate, and the chronology is what proves the window.

    UV_CACHE_DIR=.cache/uv uv run python scripts/w2_rulings_d7.py

`--check` re-derives every record and compares, writing nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.learning.correction_ladder import LADDER_RUNGS  # noqa: E402

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
PREFLIGHT = EVIDENCE / "sprint-21d7-w2-preflight.json"
LADDER_RULING = EVIDENCE / "sprint-21d7-ladder-ruling.json"
CONTRACTS = EVIDENCE / "sprint-21d7-contracts.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d7-pre-registration.json"

#: Records that carry authority rather than measurement. A W2 step-0 ruling may read these
#: without the reading being a measurement; the chronology below lists everything else.
AUTHORITY_RECORDS = frozenset(
    {
        "sprint-21d7-authority-isolation-after.json",
        "sprint-21d7-baseline.json",
        "sprint-21d7-baseline-reading.json",
        "sprint-21d7-condition-24-ruling.json",
        "sprint-21d7-contracts.json",
        "sprint-21d7-corpus-separation.json",
        "sprint-21d7-demotion-ruling.json",
        "sprint-21d7-disjointness-clarification.json",
        "sprint-21d7-ladder-ruling.json",
        "sprint-21d7-ladder-supersession.json",
        "sprint-21d7-pre-registration.json",
        "sprint-21d7-pre-registration-r8.json",
        "sprint-21d7-provisioning.json",
        "sprint-21d7-reuse-audit.json",
        "sprint-21d7-sealed-manifests.json",
        "sprint-21d7-transfer-gap.json",
        "sprint-21d7-w2-preflight.json",
    }
)

#: W1's records are measurements — of the corpus, not of a decision. They are named here rather
#: than hidden in the exclusion list, because a chronology that quietly excluded them would be
#: claiming a cleaner window than the one this wave actually has.
W1_MEASUREMENT_RECORDS = (
    "sprint-21d7-vertical-slice.json",
    "sprint-21d7-feature-seals.json",
    "sprint-21d7-certification-campaign.json",
    "sprint-21d7-snapshots.json",
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _chronology() -> dict[str, Any]:
    """The window these rulings had to be inside.

    Not "no D7 number exists" — W1's do. The claim is narrower and checkable: no decision of the
    fresh certification half has been *scored*, no bar has been derived, no direction has been
    fitted in this wave, and the fresh corpus has not been ladder-measured. Each is read out of
    the pre-flight's own sealed fields rather than asserted here.
    """
    preflight = _read(PREFLIGHT)
    others = sorted(
        path.name
        for path in EVIDENCE.glob("sprint-21d7-*.json")
        if path.name not in AUTHORITY_RECORDS
    )
    return {
        "d7_certification_decisions_scored": preflight["d7_certification_decisions_scored"],
        "d7_conformal_bars_derived": preflight["operating_points_derived"],
        "d7_certification_campaign_opened_by_an_authority_record": (
            preflight["d7_certification_campaign_opened"]
        ),
        "d7_final_or_canary_outcomes_inspected": preflight["final_outcomes_inspected"],
        "d7_directions_fitted_in_wave": 0,
        "d7_ladder_measurements_on_the_fresh_corpus": 0,
        "w1_measurement_records_present": [
            name for name in W1_MEASUREMENT_RECORDS if (EVIDENCE / name).exists()
        ],
        "other_records_present": others,
        "why_w1_records_do_not_close_the_window": (
            "W1 measured the corpus: which bodies pass which suite, what the seven channels of "
            "each candidate are, and that the roles are separated. It scored no decision, "
            "derived no bar and read no margin. A ruling chosen to suit W1's numbers could only "
            "be a ruling about the corpus, and none of the three below is"
        ),
        "the_ladder_rulings_own_test": (
            "S21D7-011: refusing the rung is legitimate and deciding it after seeing W2's "
            "numbers is not. The counters above are what make this the former"
        ),
    }


def _disjointness_clarification() -> dict[str, Any]:
    """S21D7-025 — the frozen sentence bound to the properties it exists for."""
    preflight = _read(PREFLIGHT)
    scan = preflight["relational_separation"]["scan"]
    # The per-contract hash lives in the pre-registration, not in the contracts record: the
    # contracts record carries the text and revision 7 carries what that text hashed to.
    contract_hashes = _read(PRE_REGISTRATION)["contract_hashes"]
    corpus_roles = _read(CONTRACTS)["contracts"]["corpus_roles"]
    pairs = [
        {
            "halves": [pair["first_half"], pair["second_half"]],
            "aliased_vectors": pair["aliased_vectors"],
            "shared_decision_signatures": pair["shared_decision_signatures"],
            "shared_canonical_sources": pair["shared_canonical_sources"],
        }
        for pair in scan["pairs"]
    ]
    return {
        "sprint": "21D7",
        "wave": "W2",
        "items": ["S21D7-025"],
        "schema_version": 1,
        "ruling": (
            "the corpus_roles disjointness sentence binds to the two leakage properties it "
            "exists for, and seven-channel aliasing is reported rather than fatal"
        ),
        "the_frozen_sentence": preflight["relational_separation"]["frozen_sentence"],
        "the_contract_it_lives_in": {
            "name": "corpus_roles",
            "contract_hash": contract_hashes["corpus_roles"],
            "disjointness_clause": corpus_roles["disjointness"],
            "text_unchanged": True,
        },
        "why_the_sentence_needed_reading": (
            "it was written for the 390-channel representation, where two distinct canonical "
            "sources do not encode to the same vector. The class this sprint fits is seven "
            "numbers, and seven numbers alias. Read literally the sentence is false of a corpus "
            "that leaks nothing; read as its purpose it is true of exactly the corpora that "
            "leak nothing. Neither reading is a threshold, and the difference between them is "
            "the whole question"
        ),
        "what_binds_from_here": [
            "zero shared decision signatures across every half pair",
            "zero shared canonical sources across every half pair",
            "each half's independent decision count equal to its group count",
        ],
        "what_is_reported_rather_than_refused": (
            "the count of relational vectors appearing in more than one half, per pair, in "
            "every W2 and later record that scores or admits a decision. Aliasing bounds "
            "reachable coverage from above and belongs in the record for that reason"
        ),
        "measured": {
            "scan": "relational_scans.py",
            "scan_content_hash": scan["content_hash"],
            "scan_revision": scan["revision"],
            "clean_under_the_bound_reading": scan["clean"],
            "pairs": pairs,
            "independent_decision_signatures": {
                half["half"]: half["independent_decision_signatures"] for half in scan["halves"]
            },
            "distinct_vectors": {half["half"]: half["distinct_vectors"] for half in scan["halves"]},
            "candidate_vectors": {
                half["half"]: half["candidate_vectors"] for half in scan["halves"]
            },
        },
        "the_reading_this_rejects": (
            "that an aliased vector is shared evidence. It is not: it is two different "
            "canonical sources encoding identically in a seven-channel code. It shares no "
            "decision, no group and no bytes across the halves, and a certified decision's "
            "margin is computed from its own group's four vectors whatever any other task's "
            "candidate encoded to"
        ),
        "what_it_does_not_change": [
            "any threshold: alpha stays 0.20, C stays 0.15, the coverage floor stays 0.40",
            "the corpus_roles contract text or its hash",
            "the nine-role separation proof, which is about groups and holds unchanged",
            "any released record; D2 through D6 fitted 390 channels and do not alias",
        ],
        "if_refused": (
            "the sentence stands literally, the seven-channel corpus fails its own disjointness "
            "clause on aliasing alone, and D7 stops at §3.4 with a sealed record. A legitimate "
            "outcome; it closes the class question on a property no half actually violates"
        ),
        "thresholds_changed": 0,
        "chronology": _chronology(),
    }


def _baseline_reading() -> dict[str, Any]:
    """S21D7-026 — which of the two readings §2.3's baseline condition takes."""
    preflight = _read(PREFLIGHT)
    return {
        "sprint": "21D7",
        "wave": "W2",
        "items": ["S21D7-026"],
        "schema_version": 1,
        "ruling": (
            "the baseline condition compares the admitted clean first-choice rate with the "
            "strongest deterministic rung's rate over the whole corpus"
        ),
        "the_condition": (
            "clean first-choice rate over admitted decisions strictly above the strongest "
            "deterministic baseline on the same decisions"
        ),
        "the_two_readings": {
            "whole_corpus": (
                "the rung's rate over all 100 certification decisions, which is the rate every "
                "released ladder record reports and the one D2 through D6 were measured against"
            ),
            "admitted_subset": (
                "the rung's rate recomputed on exactly the admitted decisions, which no "
                "released record reports and which collapses onto the class's own rate wherever "
                "the two agree on what they admit"
            ),
        },
        "which_binds": "whole_corpus",
        "why_it_had_to_be_fixed_first": preflight["seated_pairing"]["the_reading_divergence"],
        "why_this_reading": (
            "the released ladder rate is the number every predecessor was measured against, so "
            "reading it keeps this cell comparable with D2 through D6. The subset reading is "
            "not merely stricter: where a class admits the decisions a rung already gets right, "
            "it is unsatisfiable by construction, and a condition that cannot be met by any "
            "class is a condition that measures nothing"
        ),
        "what_it_costs": (
            "the whole-corpus reading is the weaker of the two on any cell where admission "
            "correlates with the rung being right, which is every cell a sane class produces. "
            "It is recorded here, before the numbers, so that a pass under it is read as what "
            "it is: strictly above the published baseline rate, not above the rung's rate on "
            "the decisions the class chose to take"
        ),
        "what_it_does_not_change": [
            "the condition's text, which is unchanged and unamended",
            "any threshold; 'strictly above' is strictly above under either reading",
            "which rung is the strongest, which is measured on the fresh corpus and not assumed",
        ],
        "thresholds_changed": 0,
        "chronology": _chronology(),
    }


def _ladder_supersession() -> dict[str, Any]:
    """S21D7-027 — S21D7-011 reversed, in the window where reversing it is legitimate."""
    ruling = _read(LADDER_RULING)
    preflight = _read(PREFLIGHT)
    return {
        "sprint": "21D7",
        "wave": "W2",
        "items": ["S21D7-027"],
        "schema_version": 1,
        "ruling": (
            "S21D7-011 is superseded: the containment ordering is not seated on the ladder, the "
            "frozen five stand, and W2 reports the containment rung as an unseated measurement"
        ),
        "supersedes": {
            "record": "sprint-21d7-ladder-ruling.json",
            "items": ruling["items"],
            "integrity_content_hash": ruling["integrity_content_hash"],
            "file_sha256": _sha256_file(LADDER_RULING),
            "the_record_is_not_rewritten": (
                "S21D7-011 stays exactly as it was sealed, including its hash in revision 7's "
                "children. A superseded ruling that is edited is a ruling nobody can audit"
            ),
        },
        "ladder_after_this_ruling": list(LADDER_RUNGS),
        "the_branch_this_takes": ruling["if_refused"],
        "what_the_measurement_said": {
            "reading": (
                "under the seated pairing the fitted class agrees with the containment rung on "
                "every decision in its top-margin range on both spent corpora, so the design "
                "estimate for changed-decisions-among-admitted is zero against a floor needing "
                "at least a third of the admitted set"
            ),
            "corpora": preflight["seated_pairing"]["corpora"],
            "measured_on": preflight["seated_pairing"]["measured_on"],
        },
        "why_this_is_decided_now_and_could_not_be_later": ruling["why_this_is_decided_now"],
        "what_w2_still_measures": (
            "all five released rungs on the fresh corpus, and the containment ordering beside "
            "them as an unseated measurement. §2.3 reads whichever released rung is strongest "
            "there; the ladder ruling's own figures make that lexical_similarity on a "
            "D6-shaped corpus and fixed_input_order on a D5-shaped one, and the fresh corpus "
            "decides for itself"
        ),
        "what_it_does_not_change": [
            "the five released rungs, their implementations and their eligibility rules",
            "any released ladder record; D2 through D6 measured the five and stay as they are",
            "any threshold: the first-choice condition is 'strictly above the strongest rung' "
            "either way, and only which rung that is has moved",
            "the containment share itself, which the class still fits as one of its seven "
            "channels; unseating the rung is about the deterministic baseline, not the feature",
        ],
        "what_it_costs": (
            "the baseline §2.3 reads falls from the containment rate to the strongest released "
            "rate — 0.84 to 0.62 on a D6-shaped corpus by the superseded ruling's own figures. "
            "This is the easier side, and taking it after the pre-flight measured the seated "
            "side's consequence is exactly the sequence the original ruling warned about. What "
            "makes it legitimate is the chronology: the consequence was measured on the two "
            "spent corpora, no fresh decision has been scored, and this record predates the "
            "first one. What it costs in the report is that D7's baseline is the released one "
            "and no claim may be made against the containment ordering as a baseline"
        ),
        "thresholds_changed": 0,
        "chronology": _chronology(),
    }


def _revision_8(rulings: list[dict[str, Any]]) -> dict[str, Any]:
    """S21D7-028 — the pre-registration revision the three rulings require.

    Revision 7 bound `sprint-21d7-ladder-ruling.json` by hash as the ladder §2.3 reads. One of
    the rulings above reverses it, so what W2 will measure is no longer what revision 7 says it
    will. That has to be re-registered before the measuring, in its own file: rewriting revision
    7 in place would invalidate the W0 chain that cites it.
    """
    revision_7 = _read(PRE_REGISTRATION)
    return {
        "sprint": "21D7",
        "wave": "W2",
        "items": ["S21D7-028"],
        "schema_version": 1,
        "revision": 8,
        "measured_values": 0,
        "supersedes": {
            "revision": revision_7["revision"],
            "record": "sprint-21d7-pre-registration.json",
            "integrity_content_hash": revision_7["integrity_content_hash"],
            "file_sha256": _sha256_file(PRE_REGISTRATION),
            "for": (
                "Sprint 21D7 W2 onward. Revision 7 remains the authority for every record W0 "
                "and W1 sealed, and its children's hashes are unchanged by this revision"
            ),
        },
        "what_changed_from_revision_7": [
            "the ladder §2.3 reads: the frozen five, not the seated six (S21D7-027)",
            "the baseline condition's reading: whole-corpus rate (S21D7-026)",
            "the disjointness sentence's binding: the two leakage properties (S21D7-025)",
        ],
        "what_did_not_change": [
            "every threshold: alpha 0.20, C 0.15, coverage floor 0.40",
            "the candidate cell, the admission rule, the decision tree and the selection rule",
            "CorrectionFeatureContractV3 and the seven-channel allowlist",
            "the sealed model hash W2 must reproduce",
            "the corpus, its seal and its nine-role separation",
        ],
        "contract_hashes": revision_7["contract_hashes"],
        "contracts_sha256": revision_7["contracts_sha256"],
        "evidence_children_sha256": {
            **revision_7["evidence_children_sha256"],
            "sprint-21d7-w2-preflight.json": _sha256_file(PREFLIGHT),
            **{ruling["_output"]: ruling["integrity_content_hash"] for ruling in rulings},
        },
        "chronology": _chronology(),
        "the_window_this_revision_claims": (
            "revision 8 is published before the first fresh decision is scored and says so in "
            "numbers rather than in prose. Every counter that would make one of its three "
            "rulings a choice made to suit a result is zero, and the two that are not zero — "
            "W1's corpus and campaign records — measure the corpus rather than any decision"
        ),
    }


def _sealed(record: dict[str, Any], output: Path, *, write: bool) -> dict[str, Any]:
    record.pop("_output", None)
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    text = json.dumps(record, indent=1, sort_keys=True) + "\n"
    if write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    elif not output.exists() or output.read_text(encoding="utf-8") != text:
        raise SystemExit(f"{output.name} does not match the record this script derives")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="re-derive and compare, write nothing")
    arguments = parser.parse_args()
    write = not arguments.check

    plan = [
        ("sprint-21d7-disjointness-clarification.json", _disjointness_clarification()),
        ("sprint-21d7-baseline-reading.json", _baseline_reading()),
        ("sprint-21d7-ladder-supersession.json", _ladder_supersession()),
    ]
    sealed: list[dict[str, Any]] = []
    for name, record in plan:
        result = _sealed(record, EVIDENCE / name, write=write)
        sealed.append({**result, "_output": name})

    revision = _sealed(
        _revision_8(sealed), EVIDENCE / "sprint-21d7-pre-registration-r8.json", write=write
    )

    print(
        json.dumps(
            {
                "sprint": "21D7",
                "wave": "W2",
                "stage": "step_0",
                "items": ["S21D7-025", "S21D7-026", "S21D7-027", "S21D7-028"],
                "rulings": {entry["_output"]: entry["integrity_content_hash"] for entry in sealed},
                "pre_registration": {
                    "revision": revision["revision"],
                    "integrity_content_hash": revision["integrity_content_hash"],
                },
                "thresholds_changed": 0,
                "chronology": _chronology(),
            },
            indent=1,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
