"""S21D4-022. Replay Sprint 21D3's twenty-four settings under the corrected denominators.

Two questions, in this order, and the second is only asked if the first answers cleanly.

*Does D3's grid reproduce from D3's own evidence?* Every derived value in
`sprint-21d3-learner-selection.json` is recomputed from the primitive counts recorded beside it.
If one of them does not come back, the erratum this sprint is built on is not established and
the pre-registered stop `reconciliation_not_reproducible` fires here rather than after a corpus
has been authored against it.

*What does the grid say when a decision is counted once?* D3 reported 120 metamorphic ranking
decisions per setting. S21D4-001 established that those were 20 decisions encoded six times, and
this replay restates every rate over the 20. The rates move; the underlying behaviour does not,
because nothing is re-measured here.

One number is *not* recomputed, and saying so is part of the reproduction. The metamorphic
block's `clean_first_choice_rate` is not six times the setting's own `clean_correct`: it is the
*effective* rate, which credits an abstention when the deterministic baseline it falls back to
was right. That is a different quantity wearing a similar name, not a disagreement, and the only
thing derivable about it from the recorded primitives is a bound — at least the answered-correct
count, at most that plus every abstention. The replay checks the bound and records that it is a
bound, rather than asserting an identity that does not hold and stopping on it.

Development-only. It derives no threshold, opens no D4 partition, and reads two committed JSON
files. There is no database connection in this file.

    UV_CACHE_DIR=.cache/uv uv run python scripts/d3_grid_replay_d4.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionDecisionSetV4,
    DecisionCensusV4,
)
from cognitive_os.learning.selective_operating_point import (  # noqa: E402
    zero_error_upper_bound,
)

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
SELECTION = EVIDENCE / "sprint-21d3-learner-selection.json"
RECONCILIATION = EVIDENCE / "sprint-21d4-d3-reconciliation.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"

CASES_PER_GROUP = 6
STOP_KIND = "reconciliation_not_reproducible"


class NotReproducible(RuntimeError):
    """A D3 recorded value did not come back from D3's own primitives."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _reproduce(setting: dict[str, Any]) -> list[dict[str, Any]]:
    """Every derived D3 value, recomputed from the primitives recorded beside it."""
    metamorphic = setting["metamorphic"]
    counts = metamorphic["counts"]
    decisions = Decimal(setting["clean_decisions"])
    answered = Decimal(setting["clean_answered"])
    correct = Decimal(setting["clean_correct"])
    nominal = Decimal(counts["ranking_decisions"])
    nominal_answered = Decimal(counts["answered_decisions"])
    errors = Decimal(counts["confident_errors"])

    expected: list[tuple[str, Any, Any]] = [
        ("coverage", setting["coverage"], str(answered / decisions)),
        ("abstention_rate", setting["abstention_rate"], str(Decimal(1) - answered / decisions)),
        ("first_choice_rate", setting["first_choice_rate"], str(correct / decisions)),
        ("changed_decisions", setting["changed_decisions"], setting["clean_changed"]),
        ("ood_answered", setting["ood_answered"], counts["answered_decisions"]),
        ("confident_ood_errors", setting["confident_ood_errors"], counts["confident_errors"]),
        (
            "metamorphic_ranking_decisions",
            counts["ranking_decisions"],
            counts["answered_decisions"] + counts["abstained_decisions"],
        ),
        (
            "metamorphic_candidate_outcomes",
            counts["candidate_outcomes"],
            counts["ranking_decisions"] * counts["candidates_per_decision"],
        ),
        ("metamorphic_cases", counts["metamorphic_cases"], counts["ranking_decisions"]),
        (
            "confident_error_rate_all_decisions",
            metamorphic["confident_error_rate_all_decisions"],
            str(errors / nominal),
        ),
        (
            "confident_error_rate_answered_decisions",
            metamorphic["confident_error_rate_answered_decisions"],
            str(errors / nominal_answered) if nominal_answered else None,
        ),
        ("clean_coverage", metamorphic["clean_coverage"], str(answered / decisions)),
        (
            "equivalence_coverage",
            metamorphic["equivalence_coverage"],
            str(nominal_answered / nominal),
        ),
        (
            "non_silence_failures",
            setting["non_silence_failures"],
            metamorphic["ineligible_reasons"],
        ),
        # The six-into-one collapse itself, restated per setting so the replay is the check.
        (
            "ood_answered_is_six_times_clean",
            setting["ood_answered"],
            CASES_PER_GROUP * int(answered),
        ),
        (
            "confident_errors_are_six_times_clean_errors",
            setting["confident_ood_errors"],
            CASES_PER_GROUP * int(answered - correct),
        ),
        (
            "changed_clean_decisions_are_six_times_clean_changed",
            metamorphic["changed_clean_decisions"],
            CASES_PER_GROUP * setting["clean_changed"],
        ),
    ]
    return [
        {
            "value": name,
            "recorded": recorded,
            "recomputed": recomputed,
            "agrees": str(recorded) == str(recomputed),
        }
        for name, recorded, recomputed in expected
    ]


def _effective_rate_bound(setting: dict[str, Any]) -> dict[str, Any]:
    """`clean_first_choice_rate` is the effective rate; only its bound is derivable."""
    numerator = int(Decimal(setting["metamorphic"]["clean_first_choice_rate"]) * 120)
    per_case, remainder = divmod(numerator, CASES_PER_GROUP)
    lowest = setting["clean_correct"]
    highest = setting["clean_correct"] + (setting["clean_decisions"] - setting["clean_answered"])
    return {
        "effective_first_choice_correct": per_case,
        "divides_by_six_exactly": remainder == 0,
        "answered_and_correct": lowest,
        "at_most_answered_correct_plus_abstentions": highest,
        "within_bound": remainder == 0 and lowest <= per_case <= highest,
        "definition": (
            "an abstention executes the deterministic baseline order, and the metamorphic block "
            "credits it when that order was right; the setting's own first_choice_rate does not"
        ),
    }


def _under_independent_denominators(setting: dict[str, Any]) -> dict[str, Any]:
    """One setting, counted once per distinct fitted vector."""
    answered = setting["clean_answered"]
    correct = setting["clean_correct"]
    errors = answered - correct
    census = DecisionCensusV4(
        nominal_decisions=setting["metamorphic_ranking_decisions"],
        independent_decisions=setting["clean_decisions"],
        replicated_decisions=(
            setting["metamorphic_ranking_decisions"] - setting["clean_decisions"]
        ),
    )
    measured = CorrectionDecisionSetV4(
        label=setting["setting_identity"],
        census=census,
        answered_decisions=answered,
        correct_decisions=correct,
        confident_errors=errors,
        changed_actions=setting["clean_changed"],
    )
    coverage = measured.coverage
    return {
        "setting_identity": setting["setting_identity"],
        "old": {
            "denominator": "nominal_decisions",
            "ranking_decisions": setting["metamorphic_ranking_decisions"],
            "answered_decisions": setting["ood_answered"],
            "confident_errors": setting["confident_ood_errors"],
            "confident_error_rate_all_decisions": setting["metamorphic"][
                "confident_error_rate_all_decisions"
            ],
            "confident_error_rate_answered_decisions": setting["metamorphic"][
                "confident_error_rate_answered_decisions"
            ],
        },
        "new": {
            "denominator": census.rate_denominator,
            "census": census.model_dump(mode="json", exclude={"content_hash", "independence_rule"}),
            "answered_decisions": answered,
            "correct_decisions": correct,
            "confident_errors": errors,
            "coverage": str(coverage) if coverage is not None else None,
            "accuracy": str(measured.accuracy) if measured.accuracy is not None else None,
            "confident_error_rate": (
                str(measured.confident_error_rate)
                if measured.confident_error_rate is not None
                else None
            ),
            "zero_error_upper_bound_95_if_it_had_been_clean": (
                round(zero_error_upper_bound(answered), 6) if answered else None
            ),
        },
        "effective_first_choice": _effective_rate_bound(setting),
        "eligible_in_d3": setting["eligible"],
        "d3_ineligible_reason": setting["ineligible_reason"],
    }


def build() -> dict[str, Any]:
    selection = json.loads(SELECTION.read_text())
    settings = selection["settings"]

    checks = {setting["setting_identity"]: _reproduce(setting) for setting in settings}
    differences = [
        {
            "setting_identity": identity,
            "differences": [item for item in comparisons if not item["agrees"]],
        }
        for identity, comparisons in checks.items()
        if not all(item["agrees"] for item in comparisons)
    ]
    bounds_violated = [
        setting["setting_identity"]
        for setting in settings
        if not _effective_rate_bound(setting)["within_bound"]
    ]
    if differences or bounds_violated:
        raise NotReproducible(
            json.dumps(
                {
                    "stop": STOP_KIND,
                    "settings_that_did_not_reproduce": differences,
                    "effective_rate_bound_violated": bounds_violated,
                },
                indent=1,
                sort_keys=True,
            )
        )

    replayed = [_under_independent_denominators(setting) for setting in settings]
    zero_error_settings = [
        item["setting_identity"] for item in replayed if item["new"]["confident_errors"] == 0
    ]
    errors = [item["new"]["confident_errors"] for item in replayed]

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W1",
        "items": ["S21D4-022"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "purpose": (
            "Reproduce every Sprint 21D3 recorded value from Sprint 21D3 evidence, then restate "
            "each setting over independent decisions."
        ),
        "sources": {
            "selection": {
                "path": SELECTION.name,
                "sha256": _sha256(SELECTION.read_bytes()),
            },
            "reconciliation": {
                "path": RECONCILIATION.name,
                "sha256": _sha256(RECONCILIATION.read_bytes()),
            },
        },
        "reproduction": {
            "settings_examined": len(settings),
            "derived_values_checked_per_setting": len(next(iter(checks.values()))),
            "derived_values_checked": sum(len(item) for item in checks.values()),
            "effective_rate_bounds_checked": len(settings),
            "settings_that_did_not_reproduce": differences,
            "stop_kind_if_it_had_failed": STOP_KIND,
            "reproduced": True,
        },
        "per_setting": replayed,
        "observations": {
            "every_setting_collapses_six_into_one": True,
            "settings_with_zero_confident_errors_over_independent_decisions": zero_error_settings,
            "confident_errors_over_twenty_independent_decisions": {
                "minimum": min(errors),
                "maximum": max(errors),
            },
            "what_this_means": (
                "the corrected denominator does not rescue D3. No setting in the grid reached "
                "zero confident errors even over its twenty independent decisions, so D3's stop "
                "was not an artefact of counting replicas. What D3 never had was a per-decision "
                "operating point: the grid's confidence_floor is a setting-level constant, and "
                "the zero-error point S21D4-021 derives is chosen from the scores themselves. "
                "That is the intervention D4 tests, and this replay does not test it."
            ),
        },
        "boundary": {
            "development_only": True,
            "selection_authority": False,
            "thresholds_derived": 0,
            "d4_calibration_decisions_read": 0,
            "d4_final_outcomes_read": 0,
            "d4_canary_outcomes_read": 0,
            "predecessor_store_writes": 0,
            "database_connections_opened": 0,
            "inputs": "two committed JSON files, read-only",
        },
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d4-d3-grid-replay.json"))
    arguments = parser.parse_args()

    try:
        record = build()
    except NotReproducible as stop:
        print(str(stop), file=sys.stderr)
        return 1

    Path(arguments.output).write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": Path(arguments.output).name,
                "settings_examined": record["reproduction"]["settings_examined"],
                "reproduced": record["reproduction"]["reproduced"],
                "zero_error_settings_over_independent_decisions": len(
                    record["observations"][
                        "settings_with_zero_confident_errors_over_independent_decisions"
                    ]
                ),
                "thresholds_derived": 0,
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
