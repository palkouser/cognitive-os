"""S22E-404: the five exit criteria, read once against the sentences the allocation froze.

The five sentences come out of W0's sealed pre-registration verbatim, not out of this file, and
each one is judged against records this sprint sealed as it went. Nothing here is allowed to
soften a sentence: exit (c) says "retained and retrievable", so that is what it is judged on,
and W4's stricter distinguishability probe is reported beside it rather than folded into it.

**A negative needs the same falsifiability a pass does** (22C's release lesson). Every criterion
names the record and path it read, so a reader can resolve the same path and disagree; the two
that fail name the measured value that failed them.

    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/exits_22e.py
    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/exits_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

OUTPUT = EVIDENCE / "sprint-22e-exit-criteria.json"
RECORDED_AT = "2026-08-16T00:00:00Z"

#: Every record this sprint sealed that carries a zero-mutation comparison. Enumerated so that
#: exit (a)'s "rejected proposals" is a list a reader can count rather than a word (22A W4-F1).
MUTATION_RECORDS = (
    "sprint-22e-w0-slice.json",
    "sprint-22e-w1-substrate.json",
    "sprint-22e-w1-dryrun1.json",
    "sprint-22e-w2-dryrun1-continuation.json",
    "sprint-22e-w2-dryrun2.json",
    "sprint-22e-w2-dryrun3.json",
    "sprint-22e-w3-approved-change.json",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def load(name: str) -> dict[str, Any]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def criterion_a() -> dict[str, Any]:
    rows = []
    for name in MUTATION_RECORDS:
        comparison = load(name)["zero_active_state_mutation"]
        rows.append(
            {
                "record": name,
                "zero_active_state_mutation": comparison["zero_active_state_mutation"],
                "mutated_members": comparison["mutated_members"],
                "members_compared": len(comparison["members_compared"]),
            }
        )
    real = load("sprint-22e-w1-dryrun1.json")
    return {
        "met": all(row["zero_active_state_mutation"] for row in rows)
        and all(not row["mutated_members"] for row in rows),
        "traversals_measured": len(rows),
        "records": rows,
        "at_least_one_rejection_was_real": {
            "record": "sprint-22e-w1-dryrun1.json",
            "provider_id": real["provider"]["provider_id"],
            "refusing_gate": next(
                (item["gate_id"] for item in real["gates"] if item.get("passed") is False), None
            ),
            "why_it_counts": (
                "a live provider-advised candidate refused at a gate that actually ran, not a "
                "fixture refusing a fixture"
            ),
        },
        "reads": "each record's zero_active_state_mutation, recomputed by surface_22e.compare",
    }


def criterion_b() -> dict[str, Any]:
    promotion = load("sprint-22e-w3-promotion.json")
    approval = load("sprint-22e-w3-approval.json")
    return {
        "met": (
            promotion["pull_request"]["state"] == "MERGED"
            and promotion["post_merge_ci"]["conclusion"] == "success"
            and promotion["what_landed"]["landed_bytes_are_the_evaluated_bytes"]
        ),
        "pull_request": promotion["pull_request"]["number"],
        "merge_commit": promotion["pull_request"]["merge_commit"],
        "post_merge_ci": promotion["post_merge_ci"]["conclusion"],
        "job_counts": promotion["post_merge_ci"]["job_counts"],
        "landed_bytes_are_the_evaluated_bytes": promotion["what_landed"][
            "landed_bytes_are_the_evaluated_bytes"
        ],
        "approved_by": approval["approver"],
        "one_change_only": len(promotion["what_landed"]["files"]),
        "reads": "sprint-22e-w3-promotion.json",
    }


def criterion_c() -> dict[str, Any]:
    failed = load("sprint-22e-w2-experience.json")
    successful = load("sprint-22e-w4-experience.json")
    return {
        "met": (
            failed["retrieval"]["both_traversals_outrank_every_distractor"]
            and successful["retrieval"]["both_kinds_retained_and_retrievable"]
        ),
        "failed_kind": {
            "record": "sprint-22e-w2-experience.json",
            "traversals": len(failed["traversals"]),
            "outranked_every_distractor": failed["retrieval"][
                "both_traversals_outrank_every_distractor"
            ],
        },
        "successful_kind": {
            "record": "sprint-22e-w4-experience.json",
            "compilation_decision": successful["traversal"]["s22e-approved-change"][
                "compilation_decision"
            ],
            "read_back_validates_as_the_contract": successful["side_store"][
                "read_back_validates_as_the_contract"
            ],
            "outranks_every_distractor": successful["retrieval"][
                "the_successful_traversal_outranks_every_distractor"
            ],
        },
        # Reported beside the verdict, never folded into it. The exit's words are "retained and
        # retrievable"; distinguishability is a stronger property W4 chose to measure, and a
        # stricter probe must not be allowed to redefine the sentence it is testing beside.
        "stricter_probe_not_required_by_the_sentence": {
            "the_two_kinds_are_distinguishable": successful["retrieval"][
                "the_two_kinds_are_distinguishable"
            ],
            "finding": "22E W4-F1 — the first attempt asked for tokens the surface does not emit",
        },
        "reads": "sprint-22e-w2-experience.json and sprint-22e-w4-experience.json",
    }


def criterion_d() -> dict[str, Any]:
    gate = load("sprint-22e-gate-m.json")
    return {
        "met": gate["all_conditions_pass"],
        "counts": gate["counts"],
        "conditions_failed": gate["conditions_failed"],
        "each_failure": [
            {
                "condition": row["condition"],
                "sentence": row["sentence"],
                "reads": row["reads"],
                "measured_value": row["value"],
                "w0_expected_verdict": row.get("w0_expected_verdict"),
            }
            for row in gate["conditions"]
            if not row["met"]
        ],
        "reads": "sprint-22e-gate-m.json",
    }


def criterion_e() -> dict[str, Any]:
    release = load("sprint-22e-release.json")
    return {
        "met": release["tag"]["peels_to"] is not None,
        "programme_tag": release["tag"]["name"],
        "programme_tag_created": release["tag"]["created"],
        "programme_tag_peels_to": release["tag"]["peels_to"],
        "why_not": release["tag"]["why_not_created"],
        "negative_tag": {
            "name": release["negative_tag"]["name"],
            "created": release["negative_tag"]["created"],
            "annotated": release["negative_tag"]["annotated"],
            "peels_to_the_merge_commit": release["negative_tag"]["peels_to_the_merge_commit"],
        },
        "reads": "sprint-22e-release.json",
    }


def build() -> dict[str, Any]:
    from pre_registration_22e import EXIT_CRITERIA

    readings = [criterion_a(), criterion_b(), criterion_c(), criterion_d(), criterion_e()]
    criteria = [
        {"index": index, "criterion": sentence, **reading}
        for index, (sentence, reading) in enumerate(zip(EXIT_CRITERIA, readings, strict=True))
    ]
    met = [item["index"] for item in criteria if item["met"]]
    return {
        "items": ["S22E-404"],
        "sprint": "22E",
        "wave": "W4",
        "schema_version": 1,
        "criteria": criteria,
        "counts": {"total": len(criteria), "met": len(met), "unmet": len(criteria) - len(met)},
        "all_met": len(met) == len(criteria),
        "outcome": "pass" if len(met) == len(criteria) else "typed_negative",
        "the_sentences_are_verbatim_from": (
            "sprint-22e-pre-registration.json, which took them from the execution sprint "
            "allocation; this sprint moved none of them"
        ),
        "a_negative_is_falsifiable_too": (
            "every criterion names the record and path it read, so a reader can resolve the "
            "same path and disagree; the unmet ones name the measured value that failed them"
        ),
        "recorded_at": RECORDED_AT,
    }


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    rebuilt = build()
    return {
        "seal_recomputes": _sha256(canonical(body)) == record["integrity_content_hash"],
        "rebuilds_byte_identical": canonical(rebuilt) == canonical(body),
        "outcome_unchanged": rebuilt["outcome"] == record["outcome"],
        "recorded_not_recomputed": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        verdict = check_record(json.loads(OUTPUT.read_text(encoding="utf-8")))
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return (
            0
            if all(value for key, value in verdict.items() if key != "recorded_not_recomputed")
            else 1
        )

    record = build()
    record["integrity_content_hash"] = _sha256(canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "counts": record["counts"],
                "outcome": record["outcome"],
                "met": [item["index"] for item in record["criteria"] if item["met"]],
                "unmet": [item["index"] for item in record["criteria"] if not item["met"]],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
