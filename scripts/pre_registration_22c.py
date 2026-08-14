"""S22C-010 through S22C-018. Revision 1, frozen before the first cycle runs.

The D-series pre-registered learners; 22A pre-registered a vocabulary and a refusal; 22B
pre-registered *readings*, because a measurement sprint fails by quietly redefining a hard
number as a property of a friendlier setup. 22C inherits that failure mode and adds its own:
an acquisition sprint can meet four pipeline exits perfectly and then discover that its one
usefulness claim was never decidable. So this record freezes two different kinds of thing.

**The five readings §2.2 names** — what a cycle is, what the plant is, what improvement
reads, what a surviving citation means, and what supersession without deletion means. None
of them is a threshold: the five exit sentences are the execution sprint allocation's,
verbatim, and this publication moves none of them. 22C's plan contains no gate-owner
amendment path, so `amendments_made_by_22c` is structurally zero rather than merely unused.

**The one thing 22B did not have to freeze: a decidable improvement claim.** §3.2 schedules
the sprint around the risk that the pipeline works and the artifact still does not move the
holdout. A holdout frozen as prose would let W3 discover, after three cycles, that its two
arms were never mechanically different. So this record does something a pre-registration
normally must not: it runs the arm mechanism — on a **probe case deliberately outside the
holdout set**, so the holdout keeps `measured_values: 0` and the mechanism is still known to
work before a cycle is paid for.

The recipes are imported from the modules that implement them and hashed from there, never
retyped (22B W1-F2: pin the readings, not the driver's bytes), so a driver that drifts drifts
this record too and `--check` catches it.

    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22c.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22c.py --check

Publishing this closes the window in which a cycle definition, a plant, a holdout, a citation
standard or a supersession reading could be chosen. Everything after it is campaign work.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from campaign_22c import (  # noqa: E402
    CAMPAIGN_PREDICATE_ID,
    PLANT,
    all_segments,
    attempt_case,
    contracts_hash,
    fixture_manifest,
    fixture_source_hash,
    register_pilots,
)
from holdout_22c import (  # noqa: E402
    HOLDOUT_CASES,
    HOLDOUT_ID,
    SEEDS,
    STORE_URL_ENV,
    SUCCESS_DEFINITION,
    VERIFIER_ID,
    case_hashes,
)

from cognitive_os.domain.campaigns import CAMPAIGN_STAGES  # noqa: E402
from cognitive_os.domains import registry  # noqa: E402

OUTPUTS = {
    "contracts": EVIDENCE / "sprint-22c-contracts.json",
    "pre_registration": EVIDENCE / "sprint-22c-pre-registration.json",
}

#: The five exit sentences, from `execution-sprint-allocation.md`, verbatim. Retyped nowhere
#: else in this sprint's evidence: every later record points at these strings.
EXIT_CRITERIA = (
    "every cycle replays all retained domains",
    "a planted harmful update is quarantined",
    "a valid new revision supersedes the active view without deleting history",
    "source citations and hashes survive every derivative",
    "at least one retained artifact improves a held-out verified task",
)

#: **The arm-mechanism probe.** Not a holdout case, on purpose (§2.2c: the holdout is never
#: read before W3). It is the same *shape* — a chemistry conversion missing exactly one
#: declared fact — so running it proves the two arms are mechanically different without
#: spending a holdout case to learn it.
PROBE_CASE = {
    "problem_type": "chemistry.molar-conversion",
    "withheld_key": "atomic_masses",
    "withheld_value": {"O": 16},
    "arm_a_inputs": {
        "formula": "O2",
        "mass": {"magnitude": 96, "unit": "g"},
        "molar_mass_unit": "g/mol",
    },
    "expected_arm_b_answer": "3",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


async def _arm_mechanism_probe() -> dict[str, Any]:
    """Prove the two arms differ — on a case that is not in the holdout.

    Arm A must fail because the kernel refuses an incomplete case; arm B must be accepted by
    the released checker. If either behaved otherwise, the improvement exit would be frozen
    against a comparison that cannot distinguish anything, and W3 would find that out after
    three cycles instead of before one.
    """
    register_pilots()
    arm_a = await attempt_case(PROBE_CASE["problem_type"], PROBE_CASE["arm_a_inputs"])
    arm_b_inputs = {
        **PROBE_CASE["arm_a_inputs"],
        PROBE_CASE["withheld_key"]: PROBE_CASE["withheld_value"],
    }
    arm_b = await attempt_case(PROBE_CASE["problem_type"], arm_b_inputs)
    return {
        "probe_case_is_in_the_holdout": False,
        "why_a_probe": (
            "§2.2c keeps the holdout unread until W3, so the mechanism is proved on a case "
            "of the same shape that the holdout does not contain"
        ),
        "problem_type": PROBE_CASE["problem_type"],
        "withheld_key": PROBE_CASE["withheld_key"],
        "arm_a_artifact_inactive": {
            "refused_before_solving": arm_a.refused_before_solving,
            "verifier_status": arm_a.verifier_status,
            "accepted": arm_a.accepted,
            "message": arm_a.message,
        },
        "arm_b_artifact_active": {
            "refused_before_solving": arm_b.refused_before_solving,
            "verifier_status": arm_b.verifier_status,
            "accepted": arm_b.accepted,
            "answer": arm_b.candidate.get("exact_value"),
            "units": arm_b.candidate.get("units"),
        },
        "arms_are_mechanically_different": bool(not arm_a.accepted and arm_b.accepted),
        "arm_b_answer_is_the_expected_one": (
            arm_b.candidate.get("exact_value") == PROBE_CASE["expected_arm_b_answer"]
        ),
        "measures_no_exit_criterion": True,
    }


def _contracts(readings: dict[str, Any]) -> dict[str, Any]:
    manifest = fixture_manifest()
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W0",
        "revision": 1,
        "items": sorted(["S22C-010", *readings, "S22C-016", "S22C-017", "S22C-018"]),
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "S22C-010": {
            "contract": "the five exit criteria, verbatim from the execution sprint allocation",
            "criteria": list(EXIT_CRITERIA),
            "count": len(EXIT_CRITERIA),
            "source": "docs/sprints/sprint-22/execution-sprint-allocation.md",
            "moved_by_22c": 0,
        },
        **readings,
        "S22C-016": {
            "contract": "the campaign manifest contract",
            "class": "cognitive_os.domain.campaigns.CampaignManifestV1",
            "schema_version": 1,
            "one_sealed_object_per_campaign": True,
            "frozen_before_the_campaigns_first_cycle": True,
            "fields": [
                "rights",
                "domain_ids",
                "goals",
                "budget",
                "providers",
                "curriculum",
                "holdouts",
                "stop_conditions",
                "declared_uses",
            ],
            "rights_are_a_gate_not_a_field": (
                "CampaignSourceRights cannot hold an unconcluded review, and a manifest "
                "cannot declare a use its clearance does not permit"
            ),
            "holdout_disjointness_is_a_validator": True,
            "campaign_predicate": CAMPAIGN_PREDICATE_ID,
            "fixture_manifest_content_hash": manifest.content_hash,
        },
        "S22C-017": {
            "contract": "the §1.4 decision, taken in W0 or never",
            "decision": "the plan's frozen default is taken; no migration is allocated",
            "holdout_evaluation_path": "domains.solve and domains.checker, resolving by "
            "problem type",
            "outcomes_sealed_as": "22C evidence records, not domain_pilot_runs rows",
            "migration_0016": "remains a refusal",
            "22a_w2_a1": "stays carried by name",
            "22a_w3_a1": "untouched by any campaign work, stays carried by name",
            "why_now_or_never": (
                "a persistence path that appeared between cycle 1 and cycle 3 would make "
                "the cycles measurements of different systems"
            ),
        },
        "S22C-018": {
            "contract": "the fixture-scale source and the recipes, hashed from the module",
            "source_content_hash": fixture_source_hash(),
            "segments": len(all_segments()),
            "recipes_hash": contracts_hash(),
            "pins_the_readings_not_the_drivers_bytes": (
                "22B W1-F2: the thing that must not move is the source and the readings, "
                "not the implementation that produces them"
            ),
        },
    }
    # 22B W2-F1/F2: never bind a value that moves with the clock. The seal below covers the
    # whole body, `recorded_at` included, so it is the right hash for "this file is intact"
    # and the wrong one for "the contracts have not changed". The substance hash is the
    # second, and it is what the pre-registration binds.
    record["substance_hash"] = _sha256(
        _canonical({key: value for key, value in record.items() if key != "recorded_at"})
    )
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def _pre_registration(contracts: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W0",
        "revision": 1,
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "published_before": "the first campaign cycle",
        "measured_values": 0,
        "why_zero": (
            "the W0 slice runs against a fixture chapter authored in this repository and "
            "decides no exit criterion; every 22C exit is a claim about the real "
            "rights-cleared source across three cycles"
        ),
        "thresholds_changed": 0,
        "amendments_made_by_22c": 0,
        "why_structurally_zero": (
            "22C's plan contains no gate-owner amendment path. The five exit sentences are "
            "the allocation's, verbatim, and §2.3 forbids tuning any pre-registered "
            "configuration after its first measured number exists"
        ),
        "contracts_sha256": _sha256(OUTPUTS["contracts"].read_bytes())
        if OUTPUTS["contracts"].exists()
        else None,
        "contracts_substance_hash": contracts["substance_hash"],
        "recipes_hash": contracts_hash(),
        "exit_criteria": list(EXIT_CRITERIA),
        "chronology": {name: 0 for name in sorted(EXIT_CRITERIA)},
        "arm_mechanism_probe": probe,
        "out_of_scope": [
            "any learner refit, conformal machinery, corpus authoring for Gate L2, or touch "
            "on the canary routing",
            "promotion of either pilot domain past lifecycle: pilot",
            "domains whose honest verification floor cannot be met by deterministic kernels",
            "local English capability, model selection, adapter work — 22D's",
            "self-improvement proposals — 22E's",
            "resolving W3-A1, or any schema change beyond the single §1.4 decision",
            "tuning any pre-registered configuration after its first measured number exists",
        ],
        "blocked_on": {
            "source_rights_clearance": "see sprint-22c-rights-gate.json; blocks W1, not W0",
        },
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def build_readings() -> dict[str, Any]:
    """§2.2's five readings, each frozen as the thing a later wave must meet."""
    return {
        "S22C-011": {
            "reading": "(a) what a cycle is, and what 'replays all retained domains' reads",
            "a_cycle_is": (
                "one full pass of the nine §9.1 stages under one sealed manifest, in order"
            ),
            "stage_enumeration": [stage.value for stage in CAMPAIGN_STAGES],
            "stages": len(CAMPAIGN_STAGES),
            "a_skipped_stage_is_not_a_cycle": True,
            "enforced_by": "campaign_22c.CycleRunner.enter, against CAMPAIGN_STAGES",
            "minimum_cycles": 3,
            "cycle_count_counts": "completed nine-stage passes",
            "all_retained_domains_enumerated_from": "registry.domain_ids()",
            "domains_enumerated_at_freeze": list(registry.domain_ids()),
            "replay_executes": True,
            "why_execute": (
                "D7 W3-F1 — a digest proves bytes, not usability; a hash comparison replays nothing"
            ),
            "per_domain_rates_recorded_every_cycle": True,
            "forgetting_is": "a measured delta across cycles, never an alert that fired",
            "a_domain_with_no_retained_cases": (
                "is reported with cases: 0 rather than omitted, because 'all retained "
                "domains' is an enumeration the record must be able to be wrong about "
                "(22A W4-F1)"
            ),
        },
        "S22C-012": {
            "reading": "(b) what the planted harmful update is, and what 'quarantined' means",
            "plant_segment_id": PLANT.segment_id,
            "plant_content_hash": PLANT.content_hash,
            "sealed_in_w0_before_any_cycle": True,
            "enters_through": "the same intake path as genuine content",
            "why_not_a_special_door": "a plant fed to a special door proves the special door",
            "quarantined_means": [
                "reaches a quarantine state with a named reason from the released "
                "CorpusQuarantineReason vocabulary",
                "never reaches an active state",
                "appears in the cycle's quarantine report",
                "stays quarantined through every later cycle's replay",
            ],
            "detection_of_unplanted_errors": ("reported when it happens; the exit reads the plant"),
            "the_plant_is_not_malformed": (
                "it states a plausible stoichiometric conclusion with one coefficient "
                "altered, so nothing about its shape distinguishes it from genuine content"
            ),
        },
        "S22C-013": {
            "reading": "(c) what 'improves a held-out verified task' reads",
            "holdout_id": HOLDOUT_ID,
            "frozen_in_w0_before_any_source_byte": True,
            "measured_values": 0,
            "verifier_id": VERIFIER_ID,
            "seeds": list(SEEDS),
            "success_definition": SUCCESS_DEFINITION,
            "case_count": len(HOLDOUT_CASES),
            "case_hashes": list(case_hashes()),
            "store_url_env": STORE_URL_ENV,
            "comparison": (
                "verified success on the holdout with the retained artifact active versus "
                "without it — same tasks, same seeds, same checker, both arms measured in 22C"
            ),
            "holdout_never_used_as_curriculum": True,
            "source_leakage_check_runs_before_the_comparison_is_read": True,
            "on_failure": (
                "the sprint reports the measured gap as a typed negative; it does not go "
                "looking for a friendlier task after the fact"
            ),
            "separated_by": ["module", "store", "hash"],
        },
        "S22C-014": {
            "reading": "(d) what 'citations survive every derivative' means",
            "derivatives_enumerated": [
                "claim",
                "concept",
                "example",
                "problem",
                "procedure",
                "skill",
                "test",
            ],
            "verified_by": (
                "walking the chain backward from every promoted artifact and loading the "
                "cited source bytes"
            ),
            "not_verified_by": "asserting the provenance field is non-empty",
            "enumeration_counted_from": "the store, per 22A W4-F1",
            "sampling_forbidden": True,
            "why": "a citation check that samples has verified the sample",
            "hops": [
                "promoted memory record -> list_sources(memory_id, revision)",
                "artifact id and hash -> artifact bytes loaded and rehashed",
                "canonical content hash -> corpus item",
                "corpus item -> source manifest",
                "source manifest -> the registered source's own file hashes",
            ],
        },
        "S22C-015": {
            "reading": "(e) what 'supersedes without deleting history' reads",
            "lifecycle": "candidate -> verified -> superseded, through the released path",
            "verified_two_ways_that_must_agree": [
                "the active view queried",
                "the supersession chain walked",
            ],
            "history_surviving_means": (
                "the superseded revision is still loadable with its citations intact, and "
                "the event stream contains the full transition sequence"
            ),
            "row_deletion_anywhere_in_the_path": "a finding",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    readings = build_readings()
    probe = asyncio.run(_arm_mechanism_probe())
    contracts = _contracts(readings)

    if arguments.check:
        stored_contracts = json.loads(OUTPUTS["contracts"].read_text(encoding="utf-8"))
        stored_pre = json.loads(OUTPUTS["pre_registration"].read_text(encoding="utf-8"))
        moving = {"recorded_at", "integrity_content_hash", "contracts_sha256"}
        contracts_same = {k: v for k, v in stored_contracts.items() if k not in moving} == {
            k: v for k, v in contracts.items() if k not in moving
        }
        pre = _pre_registration(contracts, probe)
        pre_same = {k: v for k, v in stored_pre.items() if k not in moving} == {
            k: v for k, v in pre.items() if k not in moving
        }
        print(
            json.dumps(
                {
                    "contracts_reproduced": contracts_same,
                    "pre_registration_reproduced": pre_same,
                    "measured_values": stored_pre.get("measured_values"),
                    "thresholds_changed": stored_pre.get("thresholds_changed"),
                    "recipes_hash": contracts_hash(),
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if contracts_same and pre_same else 1

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    OUTPUTS["contracts"].write_text(
        json.dumps(contracts, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    pre = _pre_registration(contracts, probe)
    OUTPUTS["pre_registration"].write_text(
        json.dumps(pre, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "contracts": OUTPUTS["contracts"].name,
                "pre_registration": OUTPUTS["pre_registration"].name,
                "contracts_frozen": len(contracts["items"]),
                "exit_criteria": len(EXIT_CRITERIA),
                "measured_values": pre["measured_values"],
                "thresholds_changed": pre["thresholds_changed"],
                "amendments_made_by_22c": pre["amendments_made_by_22c"],
                "arms_are_mechanically_different": probe["arms_are_mechanically_different"],
                "recipes_hash": contracts_hash(),
                "integrity_content_hash": pre["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
