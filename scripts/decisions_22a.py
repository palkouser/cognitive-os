"""S22A-010 and S22A-011. The two §2.2 governance decisions, taken rather than drifted into.

Both were named by the backlog as W0's business and both are recorded here at the moment they
were taken, with `measured_values: 0` and no threshold moved. Neither decides anything about
domains: they decide what 22A does **not** do to the released learning surface.

**S22A-010, the rung-as-product either/or.** The D7 handoff put it in one sentence — *"if 22A
wants the cheap win, the rung is the product"* — and the backlog refused to let it drift: the
containment ordering beats the released deterministic fallback by a wide, sealed margin, but
the released runtime's seventeen fallback codes are Gate L2 condition 23 evidence naming the
lexical ordering, so swapping the advisory is a governed change to a released surface with its
own evidence trail, or it is not done at all. The prices below are **read out of D7's sealed
ladder ruling and runtime record**, never retyped, so a record that drifts from the evidence it
cites fails its own `--check`.

**S22A-011, the steady-state door.** Recorded as a decision rather than left as a default: 22A
does not enter the bounded steady state, and the sealed canary→steady transition condition
remains the named key to that door.

    UV_CACHE_DIR=.cache/uv uv run python scripts/decisions_22a.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/decisions_22a.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
D7_EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-22a-decisions.json"

#: The sealed D7 records these decisions are priced from. Named, so the prices below are
#: attributable and a change to them is visible (W4-F1: an assertion names the record it reads).
LADDER_RULING = D7_EVIDENCE / "sprint-21d7-ladder-ruling.json"
RUNTIME = D7_EVIDENCE / "sprint-21d7-runtime.json"
GATE = D7_EVIDENCE / "sprint-21d7-gate-l2.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(document)
    sealed["content_hash"] = _sha256(_canonical(document))
    return sealed


def _rung_prices() -> dict[str, Any]:
    """What each branch is worth, recomputed out of D7's sealed ladder ruling."""
    corpora = _load(LADDER_RULING)["what_it_costs"]["corpora"]
    runtime = _load(RUNTIME)
    fallback = runtime["deterministic_fallback"]
    return {
        "released_runtime_fallback_rung": fallback["rung"],
        "fallback_is_immediate": fallback["immediate"],
        "fallback_decisions_exercised": fallback["decisions"],
        "fallback_codes": runtime["reason_codes"]["fallback_codes"],
        "per_corpus": {
            name: {
                "containment_rung_rate": body["containment_rung_rate"],
                "released_fallback_rate": body["released_rungs"][fallback["rung"]],
                "strongest_released_rung": body["strongest_released_rung"],
                "strongest_released_rate": body["strongest_released_rate"],
            }
            for name, body in corpora.items()
        },
        "read_from": {
            LADDER_RULING.name: _sha256(LADDER_RULING.read_bytes()),
            RUNTIME.name: _sha256(RUNTIME.read_bytes()),
        },
    }


def _decisions() -> dict[str, Any]:
    prices = _rung_prices()
    return {
        "rung_as_product": _seal(
            {
                "item": "S22A-010",
                "question": (
                    "does 22A make the deterministic containment ordering the released "
                    "runtime's deterministic advisory, in place of the lexical ordering?"
                ),
                "decision": "deferred to its own governed record; not taken by 22A, not refused",
                "prices": prices,
                "why_the_question_exists": (
                    "the containment ordering is deterministic, label-free and computable "
                    "before the sandbox runs, and it outranks the released fallback on both "
                    "sealed pools. The D7 handoff named it the cheap win"
                ),
                "why_it_is_not_free": (
                    "the released runtime's deterministic fallback is gate evidence. Gate L2 "
                    "condition 23 is closed on a record that names the lexical ordering and "
                    "reports every fallback code reached, so changing the advisory re-opens "
                    "that condition and needs its own evidence trail — it is a governed change "
                    "to a released surface, or it is not done at all"
                ),
                "gate_condition_touched_if_taken": 23,
                "what_deferral_costs": (
                    "the sealed margin stays unbanked: on the D6 pool the containment ordering "
                    "first-choices 0.84 where the released fallback reaches 0.62, and on the D5 "
                    "pool 0.92 against 0.41. The number is not lost, it is unspent"
                ),
                "what_deferral_buys": (
                    "22A's exit criteria are about domain registration and say nothing about "
                    "the correction surface. Taking the swap here would add a released-runtime "
                    "change, a re-evidenced gate condition and a second replay bill to a sprint "
                    "whose longest item is already replay"
                ),
                "blocks_no_item_in_this_plan": True,
                "successor_may_take_it": (
                    "any sprint may take it under its own record, with condition 23 re-evidenced "
                    "and the fallback swap replayed. Deferral is not a refusal and does not "
                    "expire"
                ),
                "released_runtime_changed_by_this_decision": False,
                "thresholds_changed": 0,
            }
        ),
        "steady_state_door": _seal(
            {
                "item": "S22A-011",
                "question": (
                    "does 22A promote the learned correction component out of its bounded "
                    "canary configuration into the sealed steady state?"
                ),
                "decision": "no; the door stays closed and this is a decision, not a default",
                "current_state": (
                    "learned.containment.correction_ranking is active on "
                    "experience.correction_ranking, bounded to five canary groups; the bounded "
                    "steady-state configuration is sealed and was never entered"
                ),
                "the_named_key": (
                    "the sealed canary→steady transition condition — canary tasks, safety "
                    "regressions, verifier disagreements — remains the only way through, and "
                    "taking it is the gate owner's separate governed decision"
                ),
                "why_not_here": (
                    "22A varies nothing that learns. A domain expansion that varies candidate "
                    "count or repair completeness dissolves the containment signal by design, "
                    "so a promotion decided beside a domain expansion would be decided on "
                    "evidence about a different population"
                ),
                "canary_groups_routed": 5,
                "canary_routing_changed_by_22a": False,
                "thresholds_changed": 0,
            }
        ),
    }


def _write() -> None:
    decisions = _decisions()
    gate = _load(GATE)
    document: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W0",
        "items": ["S22A-010", "S22A-011"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authority": {
            "role": "sprint and gate owner",
            "instruction": "execute the W0 wave of the attached plan",
            "reading": (
                "the backlog names both §2.2 decisions as W0's business and the instruction to "
                "execute W0 under it carries them. The rung either/or was put to the gate owner "
                "explicitly, with both branches priced out of the sealed D7 evidence rather "
                "than described, and the answer was to defer it under its own record"
            ),
            "shown": [
                "sprint-22a-technical-backlog.md §2.2a, the either/or and why it is not free",
                "sprint-22a-technical-backlog.md §2.2b, the steady-state door",
                "sprint-21d7-ladder-ruling.json, the per-corpus rung prices",
                "sprint-21d7-runtime.json, the released fallback and its seventeen codes",
            ],
        },
        "decisions": decisions,
        "gate_state_read": {
            "gate_l2": gate["verdict"],
            "counts": gate["counts"],
            "source_sha256": _sha256(GATE.read_bytes()),
        },
        "what_these_decisions_do_not_change": [
            "the conformal bar, the admitted set, the routed groups or any §2.3 threshold",
            "the released ladder, its six rungs or any released ladder record",
            "the released runtime's deterministic fallback path or its reason codes",
            "any Gate L2 or Gate D1 condition, all of which stay exactly as D7 closed them",
        ],
        "thresholds_changed": {"count": 0, "amendments_made_by_22a": 0},
        "measured_values": 0,
    }
    document["integrity_content_hash"] = _sha256(_canonical(document))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "decisions": sorted(decisions),
                "rung_as_product": decisions["rung_as_product"]["decision"],
                "steady_state_door": decisions["steady_state_door"]["decision"],
                "thresholds_changed": 0,
                "measured_values": 0,
                "sha256": _sha256(OUTPUT.read_bytes()),
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check() -> None:
    document = _load(OUTPUT)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    if _sha256(_canonical(body)) != document["integrity_content_hash"]:
        raise SystemExit(f"{OUTPUT.name} integrity hash does not match its content")

    for name, decision in document["decisions"].items():
        recomputed = {key: value for key, value in decision.items() if key != "content_hash"}
        if _sha256(_canonical(recomputed)) != decision["content_hash"]:
            raise SystemExit(f"decision {name} does not reproduce its own hash")

    prices = document["decisions"]["rung_as_product"]["prices"]
    for name, expected in prices["read_from"].items():
        if _sha256((D7_EVIDENCE / name).read_bytes()) != expected:
            raise SystemExit(f"a priced D7 record changed after the decision was taken: {name}")
    if document["measured_values"] or document["thresholds_changed"]["count"]:
        raise SystemExit("the decision record contains a measured value or a moved threshold")

    print(
        json.dumps(
            {
                "checked": OUTPUT.name,
                "decisions_verified": len(document["decisions"]),
                "priced_records_verified": len(prices["read_from"]),
                "thresholds_changed": 0,
                "measured_values": 0,
                "sha256": _sha256(OUTPUT.read_bytes()),
            },
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    _check() if arguments.check else _write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
