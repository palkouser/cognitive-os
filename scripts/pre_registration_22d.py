"""S22D-010 through S22D-016. Revision 1, frozen before the first arm runs.

22B pre-registered *readings*, because a measurement sprint fails by quietly redefining a hard
number as a property of a friendlier setup. 22C added a decidable improvement claim, because
an acquisition sprint can meet four pipeline exits perfectly and then discover its one
usefulness claim was never decidable. 22D inherits both failure modes and adds a third that
belongs to it alone: **four of its five exits are read off the same hundred tasks, and the
tasks are authored by the repository they measure.** So this record freezes the instrument
before it exists as a number, and §2.3 forbids touching any of it afterwards.

What is published here, and why each piece could otherwise bend:

* the hundred, with a content hash per task and `measured_values: 0` — task authorship is the
  oldest way to make a benchmark agree with you (§4);
* the four arms and the *pair* the ten-point margin compares, both sides measured in this
  sprint and neither imported (22B W4-A1: measure the middle);
* the enumeration of every external provider, because "no large external LLM" is a coverage
  word and 22A W4-F1's rule is that a coverage word is an enumeration with a test asserting it;
* the typed abstention and the factual-output set, because "grounded or explicitly uncertain"
  becomes a string-matching exercise the moment either half is prose;
* the non-inferiority margin, before any arm exists to be non-inferior to;
* the escalation policy as a decision function, because §3.2 names it as the place this
  sprint could cheat without noticing;
* the §1.5 grounding ladder, because a status boundary chosen after seeing which facts fall on
  which side is the same defect as a tolerance chosen after seeing the answer.

The recipes are imported from the modules that implement them and hashed from there, never
retyped (22B W1-F2), so a driver that drifts drifts this record too and `--check` catches it.

    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22d.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22d.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from benchmark_22d import (  # noqa: E402
    ABSTENTION_VALUE,
    ARMS,
    BENCHMARK_DECLARED_DOMAIN,
    BENCHMARK_DOMAIN_MISMATCH,
    BENCHMARK_VERIFIER_IDS,
    COST_REDUCTION_QUANTITIES,
    EXTERNAL_PROVIDER_IDS,
    FACTUAL_OUTPUT_KINDS,
    GROUNDING_FLOOR,
    GROUNDING_LADDER,
    LOCAL_COMPONENTS_OUT_OF_SCOPE,
    MARGIN_COMPARISON,
    MINIMUM_COST_REDUCTION_PERCENT,
    MINIMUM_GROUNDED_SPANS,
    MINIMUM_LOCAL_SUCCESS_PERCENT,
    MINIMUM_MARGIN_POINTS,
    NON_INFERIORITY_MARGIN_POINTS,
    OUTPUT_DISPOSITIONS,
    SLICE_TIME,
    UNDECIDABLE_COUNTS_AS,
    canonical,
    escalate,
    readings,
    readings_hash,
)
from holdout_22d import (  # noqa: E402
    HOLDOUT_ID,
    REFUSAL_REASON,
    SUCCESS_DEFINITION,
    case_hashes,
)
from tasks_22d import fixture_manifest, manifest, task_hashes  # noqa: E402

OUTPUTS = {
    "contracts": EVIDENCE / "sprint-22d-contracts.json",
    "pre_registration": EVIDENCE / "sprint-22d-pre-registration.json",
}

#: The five exit sentences, from `execution-sprint-allocation.md`, verbatim. Retyped nowhere
#: else in this sprint's evidence: every later record points at these strings.
EXIT_CRITERIA = (
    "no large external LLM is called during the local microbenchmark",
    "local verified success is at least 70% and at least 10 points above retrieval-only",
    "large-LLM calls or equivalent cost fall at least 25% at non-inferior success",
    "factual output is grounded or explicitly uncertain",
    "prior domain, learning, and safety gates remain green",
)

#: 22D's plan contains no gate-owner amendment path, so this is structurally zero rather than
#: merely unused. §2.1: 22D asks nobody for a threshold change.
AMENDMENTS_MADE_BY_22D = 0


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _escalation_truth_table() -> list[dict[str, Any]]:
    """The decision function, *executed* over its input space rather than described.

    A policy published as a sentence is a policy nobody can show later was unchanged. This
    enumerates every combination of the three signals it reads and records what it decides,
    so W3 cannot quietly acquire a fourth signal or flip a branch.
    """
    from benchmark_22d import ArmOutcome, Citation

    rows = []
    for abstained in (False, True):
        for spans in (0, 1):
            for form_valid in (True, False):
                outcome = ArmOutcome(
                    task_id="_policy",
                    arm="local_model",
                    answer=None if abstained else "0",
                    abstained=abstained,
                    citations=tuple(
                        Citation(source_id="_", content_hash="0" * 64, start=0, end=1)
                        for _ in range(spans)
                    ),
                    answer_form_valid=form_valid,
                )
                rows.append(
                    {
                        "abstained": abstained,
                        "grounded_spans": spans,
                        "answer_form_valid": form_valid,
                        "escalates": escalate(outcome),
                    }
                )
    return rows


def _contracts() -> dict[str, Any]:
    published = manifest()
    return {
        "S22D-010": {
            "contract": "the five exit criteria, verbatim from the execution sprint allocation",
            "count": len(EXIT_CRITERIA),
            "criteria": list(EXIT_CRITERIA),
            "source": "docs/sprints/sprint-22/execution-sprint-allocation.md",
            "moved_by_22d": AMENDMENTS_MADE_BY_22D,
        },
        "S22D-011": {
            "reading": "(a) what 'no large external LLM is called' reads",
            "read_as": "a construction, never an audit of what happened",
            "external_providers_enumerated": list(EXTERNAL_PROVIDER_IDS),
            "enumeration_derived_from": (
                "config.provider_config.ProviderAdapterConfig discriminated union, not typed "
                "out beside it"
            ),
            "out_of_scope_by_name": list(LOCAL_COMPONENTS_OUT_OF_SCOPE),
            "the_local_models_own_calls": "counted, and are not external calls",
            "enforced_by": (
                "benchmark_22d.refuse_external_providers raises before a run, and the "
                "manifest budget sets maximum_provider_calls to 0"
            ),
            "a_call_attempt_is": "an error that fails the run, never a line in a log",
        },
        "S22D-012": {
            "reading": "(b) what 'local verified success' and the ten-point margin read",
            "task_count": published["task_count"],
            "manifest_hash": published["manifest_hash"],
            "measured_values": published["measured_values"],
            "arms": list(ARMS),
            "margin_compares": list(MARGIN_COMPARISON),
            "both_sides_measured_in_this_sprint": True,
            "minimum_local_success_percent": MINIMUM_LOCAL_SUCCESS_PERCENT,
            "minimum_margin_points": MINIMUM_MARGIN_POINTS,
            "verified_means": (
                "a registered verifier from the released builtin registry returns a pass — "
                "never a model judging a model"
            ),
            "verifier_ids": list(BENCHMARK_VERIFIER_IDS),
            "undecidable_counts_as": UNDECIDABLE_COUNTS_AS,
            "declared_domain": BENCHMARK_DECLARED_DOMAIN.value,
            "released_vocabulary_mismatch": BENCHMARK_DOMAIN_MISMATCH,
            "same_tasks_same_seeds_same_verifier_for_every_arm": True,
        },
        "S22D-013": {
            "reading": "(c) what the 25 % reduction and 'non-inferior' read",
            "baseline_is": (
                "the external-teacher arm on the same hundred tasks, measured in this sprint "
                "— never a historical figure from another sprint (22B W4-A1)"
            ),
            "quantities": list(COST_REDUCTION_QUANTITIES),
            "both_reported_separately": (
                "so a reduction cannot be claimed on whichever moved further"
            ),
            "minimum_reduction_percent": MINIMUM_COST_REDUCTION_PERCENT,
            "non_inferiority_margin_points": NON_INFERIORITY_MARGIN_POINTS,
            "non_inferiority_is": "a maximum tolerated absolute drop in verified success",
            "outside_the_margin_is": (
                "a failed exit, not a trade-off to narrate, however far the cost fell"
            ),
        },
        "S22D-014": {
            "reading": "(d) what 'grounded or explicitly uncertain' reads",
            "dispositions": list(OUTPUT_DISPOSITIONS),
            "grounded_means": (
                "the output carries a citation the walk resolves by loading the cited source "
                "bytes and hashing the cut span — a digest proves bytes, not usability "
                "(D7 W3-F1)"
            ),
            "explicitly_uncertain_means": (
                "the runtime emitted the typed abstention, a value the verifier recognises "
                "— never a hedging phrase detected in prose"
            ),
            "abstention_value": ABSTENTION_VALUE,
            "factual_output_kinds": list(FACTUAL_OUTPUT_KINDS),
            "factual_output_count": published["factual_output_count"],
            "factual_task_ids": published["factual_task_ids"],
            "third_case": "an ungrounded confident assertion, counted, and the exit reads zero",
            "grounding_floor": GROUNDING_FLOOR,
        },
        "S22D-015": {
            "reading": "§1.5's grounding ladder, frozen before any fact is admitted",
            "ladder": [
                {
                    key: (list(value) if isinstance(value, tuple) else value)
                    for key, value in rung.items()
                }
                for rung in GROUNDING_LADDER
            ],
            "kernel_role": (
                "a consistency oracle, not a recomputation: a declarative fact cannot be "
                "recomputed but a kernel-checkable consequence can corroborate it, compared "
                "as numbers and never within a tolerance (22C W1-F3)"
            ),
            "why_frozen_now": (
                "a status boundary chosen after seeing which facts fall on which side is the "
                "same defect as a tolerance chosen after seeing the answer (22C W1-F3, W3-F2)"
            ),
            "holdout_id": HOLDOUT_ID,
            "holdout_case_count": len(case_hashes()),
            "holdout_success_definition": SUCCESS_DEFINITION,
            "holdout_refusal_reason": REFUSAL_REASON,
            "holdout_measured_values": 0,
        },
        "S22D-016": {
            "reading": "the escalation policy, as a decision function over runtime quantities",
            "minimum_grounded_spans": MINIMUM_GROUNDED_SPANS,
            "signals": ["abstained", "grounded_span_count", "answer_form_valid"],
            "no_self_reported_confidence": (
                "22C W3-D1 — a component that demands an input it does not use is a refusal "
                "with a name, and a model's opinion of itself is exactly the value it will "
                "always produce; grounding support is counted, never asked for"
            ),
            "truth_table": _escalation_truth_table(),
            "not_touched_after": (
                "the first measured number exists (§2.3, and the rule that has held since D2)"
            ),
        },
    }


def _record() -> dict[str, Any]:
    published, fixture = manifest(), fixture_manifest()
    record: dict[str, Any] = {
        "schema_version": 1,
        "revision": 1,
        "items": sorted(_contracts()),
        "sprint": "22D",
        "outcome_tag": "sprint-22d-language-baseline",
        "negative_outcome_tag": "sprint-22d-evidence-baseline",
        "exit_criteria": list(EXIT_CRITERIA),
        "amendments_made_by_22d": AMENDMENTS_MADE_BY_22D,
        "why_amendments_are_structurally_zero": (
            "22D's plan contains no gate-owner amendment path; §2.1 asks nobody for a "
            "threshold change, a new released enum member, a learner refit or a retro-fix of "
            "22C's improvement exit"
        ),
        "microbenchmark": {
            "benchmark_id": published["benchmark_id"],
            "task_count": published["task_count"],
            "manifest_hash": published["manifest_hash"],
            "task_hashes": task_hashes(),
            "tasks_by_output_kind": published["tasks_by_output_kind"],
            "tasks_by_verifier": published["tasks_by_verifier"],
            "factual_output_count": published["factual_output_count"],
            "grounding_sources": published["grounding_sources"],
            "provenance": published["provenance"],
            "measured_values": published["measured_values"],
            "never_used_for_selection": published["never_used_for_selection"],
        },
        "fixture": fixture,
        "holdout": {
            "holdout_id": HOLDOUT_ID,
            "case_hashes": case_hashes(),
            "measured_values": 0,
            "read_once": "at the end of W1, and never before",
        },
        "readings": readings(),
        "readings_hash": readings_hash(),
        "migration_head": {
            "expected_revision": "0015",
            "0016_is": "a refusal by default — a wave that needs a migration has found a finding",
        },
        "out_of_scope": [
            "adapter training, unless W4 has surplus and both preflights are sealed",
            "registering additional problem types in either pilot domain",
            "any retro-fix, re-read or amendment of 22C's improvement exit or its holdout",
            "self-improvement proposals, weakness-to-proposal linkage, Gate M",
            "packaging, installers, operator runbooks",
            "resolving 22C W2-A1 or W3-A1, or any schema change",
            "multilingual capability of any kind",
            "tuning any pre-registered configuration after its first measured number exists",
        ],
    }
    record["recorded_at"] = SLICE_TIME.isoformat().replace("+00:00", "Z")
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    contracts, record = _contracts(), _record()
    built = {"contracts": contracts, "pre_registration": record}

    if arguments.check:
        results = {}
        for key, path in OUTPUTS.items():
            if not path.exists():
                results[key] = {"present": False}
                continue
            stored = json.loads(path.read_text(encoding="utf-8"))
            results[key] = {"present": True, "rebuild_identical": stored == built[key]}
        stored_record = json.loads(OUTPUTS["pre_registration"].read_text(encoding="utf-8"))
        body = {k: v for k, v in stored_record.items() if k != "integrity_content_hash"}
        results["seal_recomputes"] = (
            _sha256(canonical(body)) == stored_record["integrity_content_hash"]
        )
        results["measured_values_still_zero"] = (
            stored_record["microbenchmark"]["measured_values"] == 0
            and stored_record["holdout"]["measured_values"] == 0
        )
        print(json.dumps(results, indent=1, sort_keys=True))
        ok = all(
            item.get("rebuild_identical") for item in results.values() if isinstance(item, dict)
        )
        return 0 if ok and results["seal_recomputes"] else 1

    for key, path in OUTPUTS.items():
        _write(path, built[key])
    print(
        json.dumps(
            {
                "outputs": [path.name for path in OUTPUTS.values()],
                "items": record["items"],
                "exit_criteria": len(EXIT_CRITERIA),
                "amendments_made_by_22d": AMENDMENTS_MADE_BY_22D,
                "tasks": record["microbenchmark"]["task_count"],
                "factual_outputs": record["microbenchmark"]["factual_output_count"],
                "holdout_cases": len(record["holdout"]["case_hashes"]),
                "measured_values": record["microbenchmark"]["measured_values"],
                "readings_hash": record["readings_hash"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
