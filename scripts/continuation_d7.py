#!/usr/bin/env python3
"""S21D7-042. The typed continuation decision, on the branch none of D3 through D6 reached.

S21D7-034 measured and §3.4's ending `1_select` fired. This reads what was measured and types the
consequence — and for the first time in five sprints the consequence is a list of work that was
*done* rather than a list of work bound to a stop hash.

The shape is deliberately the same as the stop record's. D6's continuation named every dependent
deliverable and every Gate L2 condition its stop closed, so that "nothing else was opened" was a
checkable claim rather than an assurance. The same list is here, with the same names, and each
entry says which record closed it. A pass that quietly dropped the map would be harder to audit
than the stop that kept it.

The successor sentence is **read from the sealed contracts record, not composed here.** §3.4's six
endings were written in W0 with `measured_values: 0`, and the point of typing an ending is that
the measurement selects one rather than authoring one. A successor sentence written after the
result would be the measurement arguing for its own follow-up.

Three things this pass does **not** claim, each named so a later reader cannot infer more from it
than the measurement supports:

- it does not close Gate L2 by itself. The gate assessment reads the evidence and computes a
  verdict from counts; this record is one of its inputs;
- it does not retire §6's risks. Four of the five are carried forward verbatim, and the fifth was
  *measured* — the class and its own strongest channel are the same signal at admissible margins,
  which is why S21D7-027 had to unseat the containment rung before anything could be scored;
- it does not make the activation a product. What is active routes five groups on one surface.

    UV_CACHE_DIR=.cache/uv uv run python scripts/continuation_d7.py
"""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.domain.common import utc_now  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-21d7-continuation.json"

PRE_REGISTRATION = EVIDENCE / "sprint-21d7-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d7-contracts.json"
SELECTION = EVIDENCE / "sprint-21d7-learner-selection.json"
CONDITION_24_RULING = EVIDENCE / "sprint-21d7-condition-24-ruling.json"

#: Every deliverable §3.4's `1_select` branch opens, named by the words the backlog's wave table
#: uses, with the record that closed it. This is D6's `DEPENDENT_WORK` list with the verdict
#: inverted: there the entries carried a reason for staying shut, here they carry a hash.
DELIVERED: tuple[tuple[str, str], ...] = (
    ("v3 artifact bound to the new conformal point", "sprint-21d7-artifact.json"),
    ("loader, resolver and sequencer against the real artifact", "sprint-21d7-runtime.json"),
    ("the carried final roles opened — final A", "sprint-21d7-final-a-campaign.json"),
    ("the carried final roles opened — final B", "sprint-21d7-final-b-campaign.json"),
    ("final-evidence gain and per-batch direction", "sprint-21d7-final-evidence.json"),
    ("paired group bootstrap", "sprint-21d7-final-evidence.json"),
    ("shadow mode against final evidence", "sprint-21d7-final-evidence.json"),
    ("safety and retention", "sprint-21d7-promotion.json"),
    ("promotion metamorphic inside the admission budget", "sprint-21d7-promotion.json"),
    ("the canary subset executed", "sprint-21d7-canary-campaign.json"),
    ("hash-bound canary manifest, verifier mandatory, kill switch", "sprint-21d7-lifecycle.json"),
    ("exact human approval with no self-approval", "sprint-21d7-lifecycle.json"),
    ("activation, restart survival and deliberate rollback", "sprint-21d7-lifecycle.json"),
    ("the release matrix", "sprint-21d7-verification-matrix.json"),
    ("the gate assessment", "sprint-21d7-gate-l2.json"),
)

#: Records written *after* this one, by design. The gate assessment reads this record's closed
#: set and binds its bytes, so hashing the gate record here would make each run invalidate the
#: other's binding. Named rather than dropped: a deliverable omitted from the map to keep an
#: ordering tidy is exactly the omission the map exists to prevent.
WRITTEN_AFTER_THIS_RECORD = frozenset({"sprint-21d7-gate-l2.json"})

#: The Gate L2 conditions a stop would have closed. D3 closed fifteen this way, D4 sixteen, D5
#: sixteen, D6 nineteen. D7 closes none, and the list is here as the empty set it now is.
CONDITIONS_A_STOP_WOULD_HAVE_CLOSED: tuple[int, ...] = (
    10,
    11,
    13,
    14,
    15,
    16,
    18,
    19,
    20,
    21,
    22,
    23,
    25,
    26,
    27,
)

#: §6's five risks. Carried verbatim rather than summarised, because a risk paraphrased into a
#: successor's plan is a risk that quietly changed scope on the way.
RISKS: tuple[tuple[str, str], ...] = (
    (
        "the class was found after reading D6's published evidence",
        "not retired. The controls held — the construction is licensed by the corpus contract, "
        "every threshold it cleared was frozen before it existed, and the fresh certification "
        "was read once — but a class chosen after looking at spent corpora stays a selection "
        "effect, and one passing sprint does not measure it away",
    ),
    (
        "exchangeability, one pairing over",
        "not retired, and now load-bearing in production: the bar admitting 0.59 of the "
        "certification half was placed on D6's demoted groups. A successor corpus with a "
        "different family profile moves coverage without moving a single threshold",
    ),
    (
        "the anatomy is load-bearing",
        "not retired. The containment signal reads the two-complete-two-partial structure the "
        "authoring contract froze; a corpus contract that varies candidate count or repair "
        "completeness dissolves the signal by design. 22A's domain expansion has to price this "
        "rather than inherit it",
    ),
    (
        "the class and its baseline are the same signal at admissible margins",
        "MEASURED, and it decided the sprint. Under the seated containment rung only 5 of 59 "
        "admitted decisions differ from the containment ordering — 5.085 projected against a "
        "floor of 20 — so the pass exists because S21D7-027 unseated that rung at W2 step 0, "
        "before anything was scored. The honest reading is that the deterministic rung is most "
        "of the value and the fitted direction is the remainder",
    ),
    (
        "representational aliasing is a property of every seven-channel corpus",
        "not retired, and bounded rather than removed: the aliasing counts cap reachable "
        "coverage from above on any corpus of this size, and the leakage-level properties are "
        "what the scans keep proving",
    ),
)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "integrity_content_hash": _digest(_canonical(value))}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _delivered() -> list[dict[str, Any]]:
    """Every opened deliverable, bound to the bytes of the record that closed it."""
    rows: list[dict[str, Any]] = []
    for work, record in DELIVERED:
        path = EVIDENCE / record
        forward = record in WRITTEN_AFTER_THIS_RECORD
        rows.append(
            {
                "work": work,
                "record": record,
                "record_sha256": None
                if forward
                else (_digest(path.read_bytes()) if path.is_file() else None),
                "record_exists": True if forward else path.is_file(),
                "written_after_this_record": forward,
                **(
                    {
                        "why_unhashed": (
                            "it reads this record's closed set and binds these bytes; hashing it "
                            "here would make each run invalidate the other's binding"
                        )
                    }
                    if forward
                    else {}
                ),
            }
        )
    return rows


def _run(output: Path) -> int:
    selection = _read(SELECTION)
    contracts = _read(CONTRACTS)
    ending = str(selection["ending"]["name"])
    endings = contracts["contracts"]["decision_tree"]["endings"]
    if ending not in endings:
        raise SystemExit(f"the selection ends {ending!r}, which the sealed decision tree does not")
    if ending != "1_select":
        raise SystemExit(
            f"this record types the pass branch and the selection ends {ending!r}; a stop is "
            "typed by a different record with a stop hash, and neither may be written by the "
            "other"
        )

    delivered = _delivered()
    missing = [row["work"] for row in delivered if not row["record_exists"]]
    ruling = _read(CONDITION_24_RULING)

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W4",
            "items": ["S21D7-042"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "selection_sha256": _digest(SELECTION.read_bytes()),
            "decision": {
                "outcome": "candidate",
                "ending": ending,
                "ending_sentence": endings[ending],
                "sentence_read_from": {
                    "record": "sprint-21d7-contracts.json",
                    "path": "contracts.decision_tree.endings",
                    "sealed_with_measured_values": contracts["measured_values"],
                    "why": (
                        "the six endings were written in W0 with measured_values: 0, so the "
                        "measurement selects one rather than authoring one. A successor sentence "
                        "composed after the result would be the measurement arguing for its own "
                        "follow-up"
                    ),
                },
                "conditions_evaluated": selection["section_2_3"]["conditions"],
                "failed_conditions": selection["section_2_3"]["failed_conditions"],
                "thresholds_changed_by_this_sprint": contracts["thresholds_changed"],
            },
            "delivered": {
                "work": delivered,
                "count": len(delivered),
                "records_missing": missing,
            },
            "not_opened": {
                "work": [],
                "count": 0,
                "gate_l2_conditions": [],
                "conditions_a_stop_would_have_closed": list(CONDITIONS_A_STOP_WOULD_HAVE_CLOSED),
                "why_the_list_is_here_and_empty": (
                    "D3 through D6 each closed between fifteen and nineteen Gate L2 conditions "
                    "against a stop hash. The same list is printed here so that a reader "
                    "comparing this record with its predecessors sees an empty set rather than "
                    "an absent section — an omitted map is not the same claim as an empty one"
                ),
            },
            "what_sprint_22a_inherits": {
                "a_live_selection_surface": {
                    "surface": "experience.correction_ranking",
                    "component": "learned.containment.correction_ranking",
                    "state": "active on the canary subset, five routed groups",
                    "record": "sprint-21d7-lifecycle.json",
                    "record_sha256": _digest((EVIDENCE / "sprint-21d7-lifecycle.json").read_bytes())
                    if (EVIDENCE / "sprint-21d7-lifecycle.json").is_file()
                    else None,
                },
                "an_admission_rule_with_a_stated_error_budget": {
                    "rule": contracts["unchanged_from_d6"]["admission_rule"],
                    "alpha": contracts["unchanged_from_d6"]["alpha"],
                    "ceiling_c": contracts["unchanged_from_d6"]["ceiling_c"],
                    "coverage_floor": contracts["unchanged_from_d6"]["coverage_floor"],
                    "measured_bound": selection["cell"]["error_upper_bound_95"],
                    "measured_coverage": selection["cell"]["coverage"],
                    "what_it_is_not": (
                        "a zero. The budget is a bound on the error rate among admitted "
                        "decisions, and 41 of 100 certification decisions were abstentions by "
                        "design"
                    ),
                },
                "a_transfer_record": {
                    "record": "sprint-21d7-w2-transfer-gap.json",
                    "says": (
                        "why this class and not the last: the 384 embedding channels carried the "
                        "authoring run rather than the task, which is what collapsed D6's "
                        "direction across corpora and what dropping them fixed"
                    ),
                },
                "an_inherited_retrieval_condition": {
                    "ruling": ruling["ruling"],
                    "inherited_from": ruling["inherited_measurement"]["record"],
                    "winning_arm": ruling["inherited_measurement"]["winning_arm"],
                    "voids_if": sorted(ruling["the_three_identities_that_void_it"]),
                    "note": (
                        "renewed for D7 and re-checked at gate close. It is not renewable "
                        "indefinitely by this record; a successor that touches the surface, the "
                        "arms or the comparator owes a fresh holdout"
                    ),
                },
            },
            "risks_the_evidence_did_not_retire": [
                {"risk": name, "state": state} for name, state in RISKS
            ],
            "what_this_record_is_not": (
                "a gate verdict. The gate assessment computes one from counts over the same "
                "evidence, and this record is an input to it rather than a summary of it"
            ),
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "ending": ending,
                "delivered": len(delivered),
                "records_missing": missing,
                "not_opened": 0,
                "risks_carried": len(RISKS),
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 1 if missing else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return _run(parser.parse_args().output)


if __name__ == "__main__":
    raise SystemExit(main())
