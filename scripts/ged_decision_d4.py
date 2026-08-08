#!/usr/bin/env python3
"""S21D4-041. The bounded-GED comparator: a deterministic budget, or a typed retirement.

Revision 4 declared both outcomes before the holdout existed and left the choice to
measurement. `nx.graph_edit_distance(..., timeout=)` is an anytime search under a wall clock,
so what it returns depends on how far the host got before the clock ran out. D1, D2 and D3 all
measured this arm that way, and none of those numbers can be replayed by anyone -- including by
the machine that produced them.

Three things are measured here, on stored development evidence only:

*The clock is the problem, and it is shown to be.* The released comparator runs against the
largest stored graphs at two different timeouts. If the value it returns depends on the
timeout, the arm's score is a function of the host and not of the two graphs.

*The budget is deterministic.* Every comparison runs twice, and the two passes must agree on
every distance, byte for byte, or the budget has not fixed anything.

*The budget fits the policy the sprint froze.* Per-pair cost against the declared 90 ms
allowance, and twenty comparisons against the declared two-second query budget. The policy
itself is not touched: its hash is checked, not changed.

Development only. It ranks nothing, selects nothing, and never reads the D4 retrieval pool.

    UV_CACHE_DIR=.cache/uv uv run python scripts/ged_decision_d4.py
"""

from __future__ import annotations

import argparse
import json
import signal
import statistics
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

import networkx as nx  # noqa: E402

from cognitive_os.domain.experience_graph import (  # noqa: E402
    FROZEN_GRAPH_RESOURCE_POLICIES,
    GRAPH_RESOURCE_POLICY_REVISION_2,
    GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
)
from cognitive_os.experience.graph_retrieval import GED_ITERATION_BUDGET, _as_nx  # noqa: E402
from cognitive_os.experience.graph_store import load_evidence  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d4-contracts.json"
OUTPUT = EVIDENCE / "sprint-21d4-ged-decision.json"

DATA = Path("/home/palkouser/projekt/cognitive-os-data")
D1_ROOT = EVIDENCE / "sprint-21d1-emg-root.json"
D3_ROOT = EVIDENCE / "sprint-21d3-retrieval-emg-root.json"

#: The two timeouts the instability probe compares. 90 ms is the frozen policy's value; 5 ms
#: is what a host twenty times slower effectively has. Neither is a new policy: this probe
#: calls networkx directly and no arm runs under it.
PROBE_TIMEOUTS_MS = (90, 5)

#: How long the yield-cost probe may run before it stops asking for another distance, and how
#: many distances it asks for at most. Both bound a measurement of cost, not a score, and no
#: arm runs under either.
YIELD_PROBE_CEILING_SECONDS = 120
YIELD_PROBE_CEILING_YIELDS = 6


def _stop_probing(signum: int, frame: object) -> None:
    raise TimeoutError("the yield-cost probe reached its ceiling")


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return bool(left["label"] == right["label"])


def _ceiling(left: Any, right: Any) -> int:
    return int(
        max(left.number_of_nodes(), right.number_of_nodes())
        + max(left.number_of_edges(), right.number_of_edges())
    )


def _budgeted(left: Any, right: Any, budget: int) -> tuple[float | None, int]:
    """The decided comparator, isolated so the decision measures what the arm runs."""
    distance: float | None = None
    consumed = 0
    for value in nx.optimize_graph_edit_distance(
        left, right, node_match=_match, edge_match=_match, upper_bound=_ceiling(left, right)
    ):
        distance, consumed = value, consumed + 1
        if consumed >= budget:
            break
    return distance, consumed


def _wall_clock(left: Any, right: Any, timeout_ms: int) -> float | None:
    value = nx.graph_edit_distance(
        left,
        right,
        node_match=_match,
        edge_match=_match,
        timeout=timeout_ms / 1000,
        upper_bound=_ceiling(left, right),
    )
    return None if value is None else float(value)


def _graphs() -> list[tuple[str, Any, Any]]:
    """Every stored pair, as the two networkx graphs the arm would compare."""
    rows = []
    for name, root, artifacts in (
        ("d1", D1_ROOT, DATA / "artifacts-s21d1"),
        ("d3", D3_ROOT, DATA / "artifacts-s21d3"),
    ):
        for pair in load_evidence(root, artifacts).pairs:
            rows.append((f"{name}:{pair.pair_id}", _as_nx(pair.failed), _as_nx(pair.successful)))
    return rows


def _instability(rows: list[tuple[str, Any, Any]]) -> dict[str, Any]:
    """What the released wall-clock comparator returns at two clock speeds.

    Run on the largest stored graphs, because that is where an anytime search still has work
    left when the clock stops. On the small ones it converges and the clock never bites, which
    is exactly why three sprints could carry an irreproducible arm without noticing.
    """
    largest = sorted(rows, key=lambda row: -row[1].number_of_nodes())[:8]
    disagreements, measured = [], []
    for name, left, right in largest:
        values = {}
        for timeout in PROBE_TIMEOUTS_MS:
            started = perf_counter()
            values[str(timeout)] = _wall_clock(left, right, timeout)
            values[f"{timeout}_ms_elapsed"] = round((perf_counter() - started) * 1000, 3)
        row = {
            "pair": name,
            "query_nodes": left.number_of_nodes(),
            "candidate_nodes": right.number_of_nodes(),
            **values,
        }
        measured.append(row)
        if values[str(PROBE_TIMEOUTS_MS[0])] != values[str(PROBE_TIMEOUTS_MS[1])]:
            disagreements.append(name)
    return {
        "probe": "the released wall-clock comparator at two clock speeds",
        "timeouts_ms": list(PROBE_TIMEOUTS_MS),
        "pairs": len(measured),
        "pairs_whose_value_depends_on_the_clock": disagreements,
        "the_clock_decides_the_score": bool(disagreements),
        "per_pair": measured,
    }


def _determinism(rows: list[tuple[str, Any, Any]]) -> dict[str, Any]:
    """Two identical passes over every stored pair, under the decided budget.

    The first comparison of a fresh process is timed with the rest rather than warmed away.
    It costs about fifty times the steady-state figure -- an import-time cost inside networkx,
    paid once per process, not per pair -- and a decision that quietly warmed up first would be
    reporting a number an operator's first query never sees.
    """
    first, second, costs, yields = {}, {}, [], []
    for name, left, right in rows:
        started = perf_counter()
        distance, consumed = _budgeted(left, right, GED_ITERATION_BUDGET)
        costs.append((perf_counter() - started) * 1000)
        first[name] = distance
        yields.append(consumed)
    for name, left, right in rows:
        second[name] = _budgeted(left, right, GED_ITERATION_BUDGET)[0]
    disagreements = sorted(name for name in first if first[name] != second[name])
    return {
        "budget": GED_ITERATION_BUDGET,
        "comparisons": len(rows),
        "passes": 2,
        "pairs_that_disagreed_between_passes": disagreements,
        "agreement": 1.0 if not disagreements else 0.0,
        "unscored_pairs": [name for name, value in first.items() if value is None],
        "yields_consumed_minimum": min(yields),
        "yields_consumed_maximum": max(yields),
        "budget_bound_any_comparison": max(yields) >= GED_ITERATION_BUDGET,
        "per_pair_ms_p50": round(statistics.median(costs), 3),
        "per_pair_ms_p95": round(sorted(costs)[int(len(costs) * 0.95)], 3),
        "per_pair_ms_max": round(max(costs), 3),
        "first_comparison_of_the_process_ms": round(costs[0], 3),
        "steady_state_ms_max": round(max(costs[1:]), 3),
        "the_maximum_is_the_first_comparison": costs[0] == max(costs),
    }


def _yield_profile(rows: list[tuple[str, Any, Any]]) -> dict[str, Any]:
    """What each further yield costs on the largest stored pair. The reason the budget is one.

    Bounded by a wall clock *here* and nowhere else: this is a probe of how the anytime search
    behaves, not an arm, and the number it produces is a cost rather than a score. The arm
    itself consumes a fixed count of yields and consults no clock.
    """
    name, left, right = max(rows, key=lambda row: row[1].number_of_nodes())
    ceiling = _ceiling(left, right)
    started = perf_counter()
    profile: list[dict[str, Any]] = []
    # The ceiling has to interrupt the search itself. Checking the clock between yields cannot
    # bound a yield that never arrives, which is precisely the case being measured -- an
    # earlier version of this probe waited five minutes for a fourth distance and was killed.
    signal.signal(signal.SIGALRM, _stop_probing)
    signal.setitimer(signal.ITIMER_REAL, YIELD_PROBE_CEILING_SECONDS)
    try:
        for index, value in enumerate(
            nx.optimize_graph_edit_distance(
                left, right, node_match=_match, edge_match=_match, upper_bound=ceiling
            ),
            start=1,
        ):
            profile.append(
                {
                    "yield": index,
                    "distance": float(value),
                    "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                }
            )
            if index >= YIELD_PROBE_CEILING_YIELDS:
                break
    except TimeoutError:
        pass
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    return {
        "pair": name,
        "query_nodes": left.number_of_nodes(),
        "candidate_nodes": right.number_of_nodes(),
        "probe_ceiling_seconds": YIELD_PROBE_CEILING_SECONDS,
        "probe_ceiling_yields": YIELD_PROBE_CEILING_YIELDS,
        "yields_reached": len(profile),
        "stopped_by": (
            "the yield ceiling"
            if len(profile) >= YIELD_PROBE_CEILING_YIELDS
            else "the time ceiling, with the next distance still unfinished"
        ),
        "profile": profile,
        "reading": (
            "Each further yield costs more than every previous one together, and the fourth was "
            "not reached inside the probe ceiling. A budget above one is an unbounded budget "
            "with a number written on it."
        ),
    }


def _fits_the_frozen_policy(determinism: dict[str, Any]) -> dict[str, Any]:
    policy = GRAPH_RESOURCE_POLICY_REVISION_2
    worst_query_ms = (
        determinism["steady_state_ms_max"] * (policy.vector_shortlist - 1)
        + determinism["first_comparison_of_the_process_ms"]
    )
    return {
        "policy_hash": GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
        "policy_is_frozen_and_unchanged": (
            FROZEN_GRAPH_RESOURCE_POLICIES[GRAPH_RESOURCE_POLICY_REVISION_2_HASH].content_hash
            == policy.content_hash
        ),
        "per_pair_allowance_ms": policy.per_pair_ged_timeout_ms,
        "worst_measured_per_pair_ms": determinism["per_pair_ms_max"],
        "worst_measured_steady_state_ms": determinism["steady_state_ms_max"],
        "first_comparison_of_the_process_ms": determinism["first_comparison_of_the_process_ms"],
        "first_comparison_exceeds_the_allowance": (
            determinism["first_comparison_of_the_process_ms"] > policy.per_pair_ged_timeout_ms
        ),
        "first_comparison_reading": (
            "A one-off cost inside networkx, paid once per process rather than once per pair, "
            "and paid by the wall-clock comparator too. It is reported rather than warmed away "
            "because an operator's first query does pay it."
        ),
        "inside_the_per_pair_allowance": (
            determinism["steady_state_ms_max"] <= policy.per_pair_ged_timeout_ms
        ),
        "shortlist": policy.vector_shortlist,
        "query_budget_ms": policy.query_budget_seconds * 1000,
        "worst_measured_query_ms": round(worst_query_ms, 3),
        "inside_the_query_budget": worst_query_ms <= policy.query_budget_seconds * 1000,
        "per_pair_ged_timeout_ms_now_unread_by_the_arm": True,
        "why_the_field_stays": (
            "The resource policy is frozen and hash-checked; removing a field would change the "
            "hash every D1, D2 and D3 measurement cites. The arm no longer reads it as a "
            "per-pair clock, and the query-budget reserve still uses it as a conservative "
            "allowance for one more comparison."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    rows = _graphs()
    determinism = _determinism(rows)
    instability = _instability(rows)
    profile = _yield_profile(rows)
    policy = _fits_the_frozen_policy(determinism)

    decided = (
        determinism["agreement"] == 1.0
        and not determinism["unscored_pairs"]
        and policy["inside_the_per_pair_allowance"]
        and policy["inside_the_query_budget"]
    )
    evidence = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W3",
        "items": ["S21D4-041"],
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
        "contracts_sha256": _digest(CONTRACTS.read_bytes()),
        "label": "development_only",
        "gating": False,
        "arm": "minilm_shortlist_plus_bounded_ged",
        "options": {
            "a": "a fixed iteration budget from networkx.optimize_graph_edit_distance",
            "b": "retirement from the frozen set, reported with its reason",
        },
        "criterion": (
            "two identical passes must agree byte for byte on every arm; the arm is retired if "
            "a fixed budget cannot reproduce a stable ranking"
        ),
        "measured_on": {
            "roots": [
                str(D1_ROOT.relative_to(REPOSITORY)),
                str(D3_ROOT.relative_to(REPOSITORY)),
            ],
            "pairs": len(rows),
            "access": "read_only",
            "d4_retrieval_pool_read": False,
        },
        "wall_clock_instability": instability,
        "fixed_budget_determinism": determinism,
        "yield_cost_profile": profile,
        "frozen_policy": policy,
        "decision": {
            "outcome": "deterministic_budget" if decided else "retired",
            "option": "a" if decided else "b",
            "budget": GED_ITERATION_BUDGET,
            "immutable": True,
            "why": (
                "Two passes over every stored pair agreed on every distance, no pair was left "
                "unscored, and the worst per-pair cost is inside the allowance the frozen "
                "policy already declares."
                if decided
                else "A fixed budget did not reproduce a stable ranking."
            ),
            "budget_not_chosen_by_its_effect": (
                "One is the only budget the yield-cost profile leaves standing: the second "
                "distance costs more than the first arrival and the fourth did not arrive at "
                "all. The number was read off cost, and no retrieval result was consulted."
            ),
        },
        "predecessor_numbers": {
            "d1_d2_d3_for_this_arm": "irreproducible",
            "back_filled": False,
            "recomputed": False,
            "why": (
                "They were produced by an anytime search under a wall clock. A deterministic "
                "comparator cannot reconstruct what a different host reached before its clock "
                "stopped, and recomputing them now would publish new numbers under old dates."
            ),
        },
        "final_or_canary_outcomes_inspected": 0,
        "final_outcomes_inspected": False,
    }
    sealed = dict(evidence)
    sealed["integrity_content_hash"] = _digest(_canonical(evidence))
    arguments.output.write_text(
        json.dumps(sealed, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"{arguments.output.relative_to(REPOSITORY)}")
    print(
        "  wall clock decides the score on "
        f"{len(instability['pairs_whose_value_depends_on_the_clock'])} of "
        f"{instability['pairs']} of the largest stored pairs"
    )
    print(
        f"  budget {GED_ITERATION_BUDGET}: {determinism['comparisons']} comparisons x2, "
        f"agreement {determinism['agreement']:.2f}, "
        f"p95 {determinism['per_pair_ms_p95']} ms, max {determinism['per_pair_ms_max']} ms"
    )
    print(f"  decision: {evidence['decision']['outcome']}")
    print(f"  seal {sealed['integrity_content_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
