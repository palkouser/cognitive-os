#!/usr/bin/env python
"""S21D3-030, -031, -032: author, separate and seal the D3 corpora.

One command because the three items are one one-way door. The corpus is only finished when
every body has been *executed* against its own suites; separation is only meaningful over the
finished corpus; and sealing may only happen once separation holds. Splitting them into three
commands would let a seal be written over a corpus whose last defect had not been found yet.

Nothing here reads an outcome, a candidate score or a verifier label from any D3 role. The
executions below are throwaway fixture validation in a temporary directory, exactly as §0.3
permits for corpus authoring: they never reach the Event Store, the Artifact Store, a learned
observation or a metric, and the report carries pass/fail and package hashes rather than
suitability scores.

    scripts/corpus_d3.py --output-root docs/sprints/sprint-21/evidence
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_leakage import (  # noqa: E402
    near_clone_pairs,
    normalized_structure_hash,
    token_stream_hash,
)
from cognitive_os.coding.reality_retrieval_specs_d3 import D3_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs import TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d2 import (  # noqa: E402
    D2_TASK_SPECS,
    INHERITED_VARIANT_FIELDS,
    module_source,
)
from cognitive_os.coding.reality_task_specs_d3 import (  # noqa: E402
    D3_CALIBRATION_SPECS,
    D3_FIXTURE_SPEC,
    D3_TASK_SPECS,
)
from cognitive_os.learning import transformations_d3  # noqa: E402
from cognitive_os.learning.correction_catalogue_d3 import (  # noqa: E402
    CALIBRATION_STAGE,
    PROMOTION_STAGE,
    seal_d3_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402
from cognitive_os.learning.correction_source import (  # noqa: E402
    SourceNormalizationError,
    canonical_source_hash,
)

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d3-pre-registration.json"

#: The whole point of the S21D3-004 audit: three roles were carried, not re-authored.
REUSED_ROLES = (
    CorrectionPartition.TRAINING,
    CorrectionPartition.FINAL_A,
    CorrectionPartition.FINAL_B,
    CorrectionPartition.CANARY,
)


def _hash(text: str) -> str:
    return sha256(text.encode()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _hash(_canonical_bytes(value).decode())
    return sealed


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_seal(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# --------------------------------------------------------------- S21D3-030: executed authoring


def _pytest(root: Path, suite: str) -> bool:
    """Run one throwaway suite. Fixed argv, no shell, temporary directory, no network."""
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", suite],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def _correction_job(job: tuple[str, str, str, str, str, str]) -> tuple[str, str, str, bool]:
    template_id, label, module, body, suite_name, suite = job
    with tempfile.TemporaryDirectory(prefix="cogos-d3-authoring-") as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(body, encoding="utf-8")
        (root / "test_suite.py").write_text(suite, encoding="utf-8")
        return template_id, label, suite_name, _pytest(root, "test_suite.py")


def _retrieval_job(job: tuple[str, str, str, str, str]) -> tuple[str, str, str, bool]:
    template_id, label, module, body, suite = job
    with tempfile.TemporaryDirectory(prefix="cogos-d3r-authoring-") as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(body, encoding="utf-8")
        (root / "test_hidden.py").write_text(suite, encoding="utf-8")
        return template_id, label, "hidden", _pytest(root, "test_hidden.py")


#: What the corpus contract says each body must do. A body that disagrees is an authoring
#: defect, and the run below is what decides which of the two it is.
EXPECTED = {
    ("baseline", "visible"): True,
    ("baseline", "hidden"): False,
    ("variant_one", "visible"): True,
    ("variant_one", "hidden"): True,
    ("variant_two", "visible"): True,
    ("variant_two", "hidden"): True,
    ("variant_three", "visible"): True,
    ("variant_three", "hidden"): False,
    ("variant_four", "visible"): True,
    ("variant_four", "hidden"): False,
}

_VARIANT_LABELS = ("variant_one", "variant_two", "variant_three", "variant_four")


def _execute_corpus() -> tuple[dict[str, Any], list[str]]:
    jobs: list[tuple[str, str, str, str, str, str]] = []
    for spec in D3_TASK_SPECS:
        bodies = [("baseline", spec.baseline)]
        bodies += list(zip(_VARIANT_LABELS, spec.variants, strict=True))
        for label, body in bodies:
            text = module_source(spec, body)
            jobs.append((spec.template_id, label, spec.module, text, "visible", spec.visible_test))
            jobs.append((spec.template_id, label, spec.module, text, "hidden", spec.hidden_test))

    retrieval_jobs = [
        (spec.template_id, label, spec.module, spec.module_text(body), spec.hidden_test)
        for spec in D3_RETRIEVAL_SPECS
        for label, body in (("failed", spec.failed), ("repaired", spec.repaired))
    ]

    with ThreadPoolExecutor(max_workers=16) as pool:
        correction = list(pool.map(_correction_job, jobs))
        retrieval = list(pool.map(_retrieval_job, retrieval_jobs))

    defects: list[str] = []
    for template_id, label, suite_name, passed in correction:
        if passed != EXPECTED[(label, suite_name)]:
            defects.append(f"{template_id}:{label}:{suite_name}")
    for template_id, label, _suite, passed in retrieval:
        if passed != (label == "repaired"):
            defects.append(f"{template_id}:{label}:hidden")

    report = {
        "correction_runs": len(correction),
        "retrieval_runs": len(retrieval),
        "baselines_passing_their_visible_tests": sum(
            passed
            for _t, label, suite, passed in correction
            if label == "baseline" and suite == "visible"
        ),
        "baselines_failing_their_hidden_tests": sum(
            not passed
            for _t, label, suite, passed in correction
            if label == "baseline" and suite == "hidden"
        ),
        "variants_passing_their_visible_tests": sum(
            passed
            for _t, label, suite, passed in correction
            if label != "baseline" and suite == "visible"
        ),
        "variants_matching_their_declaration": sum(
            passed == EXPECTED[(label, suite)]
            for _t, label, suite, passed in correction
            if label != "baseline" and suite == "hidden"
        ),
        "retrieval_failed_states_rejected_by_the_verifier": sum(
            not passed for _t, label, _s, passed in retrieval if label == "failed"
        ),
        "retrieval_repairs_accepted_by_the_verifier": sum(
            passed for _t, label, _s, passed in retrieval if label == "repaired"
        ),
        "declaration_mismatches": sorted(defects),
    }
    return report, defects


def _validator_report() -> dict[str, Any]:
    """The sanitised corpus-authoring validator output §0.3 and S21D3-030 allow.

    Package hashes and a parse/execute verdict. No candidate score, no verifier label per
    candidate, no body, no suitability metric — a validator that reported those would be a
    quiet channel from an unopened role into the sprint.
    """
    packages = {}
    for spec in D3_TASK_SPECS:
        packages[spec.template_id] = _hash(
            "".join(module_source(spec, body) for body in (spec.baseline, *spec.variants))
            + spec.visible_test
            + spec.hidden_test
        )
    for spec in D3_RETRIEVAL_SPECS:
        packages[spec.template_id] = _hash(
            spec.module_text(spec.failed) + spec.module_text(spec.repaired) + spec.hidden_test
        )
    return {
        "capability": "isolated_corpus_authoring_validator",
        "reports": ["package_hash", "parse_and_execute_pass_fail"],
        "never_reports": [
            "candidate_scores",
            "verifier_labels_per_candidate",
            "package_bodies",
            "suitability_metrics",
        ],
        "learned_store_writes": 0,
        "event_store_writes": 0,
        "artifact_store_writes": 0,
        "metric_writes": 0,
        "package_hashes": packages,
    }


def _corpus_evidence(pre_hash: str, recorded_at: str) -> dict[str, Any]:
    executed, defects = _execute_corpus()
    eligible = {
        spec.template_id: transformations_d3.eligible(module_source(spec, spec.baseline))
        for spec in D3_TASK_SPECS
    }
    families: dict[str, int] = {}
    for spec in D3_CALIBRATION_SPECS:
        families[spec.family.value] = families.get(spec.family.value, 0) + 1
    retrieval_families: dict[str, int] = {}
    for spec in D3_RETRIEVAL_SPECS:
        retrieval_families[spec.family.value] = retrieval_families.get(spec.family.value, 0) + 1

    canonical_failures = []
    for spec in D3_TASK_SPECS:
        for body in (spec.baseline, *spec.variants):
            try:
                canonical_source_hash(module_source(spec, body))
            except SourceNormalizationError as error:  # pragma: no cover - authoring gate
                canonical_failures.append(f"{spec.template_id}: {error}")

    return {
        "schema_version": 1,
        "sprint": "21D3",
        "wave": "W2",
        "items": ["S21D3-030"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": pre_hash,
        "final_outcomes_inspected": False,
        "purpose": (
            "Record the authored D3 corpora and that every body was executed rather than "
            "declared: twenty fresh four-candidate calibration groups, one vertical-slice "
            "fixture outside every role, and an overproduced pool of sixty failed/success "
            "retrieval groups."
        ),
        "calibration_corpus": {
            "groups": len(D3_CALIBRATION_SPECS),
            "required_groups": 20,
            "candidates_per_group": 4,
            "families": families,
            "source_file_sha256": _hash(
                (REPOSITORY / "src/cognitive_os/coding/reality_task_specs_d3.py").read_text()
            ),
        },
        "vertical_slice_fixture": {
            "template_id": D3_FIXTURE_SPEC.template_id,
            "repository_group": D3_FIXTURE_SPEC.repository_group,
            "in_any_partition": False,
            "reason": "§6.1 forbids the slice from spending a scored member of any role",
        },
        "retrieval_pool": {
            "source_groups": len(D3_RETRIEVAL_SPECS),
            "required_source_groups": 60,
            "minimum_qualifying_queries": 50,
            "families": retrieval_families,
            "shape": "one failed state and one accepted repair per group",
            "source_file_sha256": _hash(
                (REPOSITORY / "src/cognitive_os/coding/reality_retrieval_specs_d3.py").read_text()
            ),
        },
        "executed_verification": {
            "note": "Every verdict is an executed pytest run in a throwaway directory.",
            **executed,
        },
        "six_case_eligibility": {
            "rule": (
                "both independent rename maps exist, neither collides with an existing name or "
                "a call keyword, and the two disagree on every name"
            ),
            "eligible_groups": sum(eligible.values()),
            "ineligible_groups": sorted(name for name, ok in eligible.items() if not ok),
            "generator_code_hash": transformations_d3.generator_code_hash(),
            "hard_coded_oracle_hash": transformations_d3.hard_coded_oracle_hash(),
        },
        "canonical_source_failures": canonical_failures,
        "authoring_defect_ledger": _defect_ledger(),
        "corpus_authoring_validator": _validator_report(),
        "whole_role_replacements": {
            "final_a": "not_required",
            "final_b": "not_required",
            "canary": "not_required",
            "authority": "S21D3-004 recorded reuse for all three roles",
        },
        "declaration_mismatches_remaining": defects,
    }


def _defect_ledger() -> list[dict[str, str]]:
    """What execution and the detectors caught while this corpus was being written.

    Recorded because a corpus that reports only its finished state hides the fact that the
    finished state was reached by being told it was wrong.
    """
    return [
        {
            "id": "W2-A1",
            "subject": "d3_numeric.share_amount variant_two",
            "found_by": "executed hidden suite",
            "detail": (
                "The incremental route handed the remainder to the last shares rather than the "
                "earliest, so a declared repair failed the contract it was supposed to repair."
            ),
        },
        {
            "id": "W2-A2",
            "subject": "d3_fixture.trim_suffix",
            "found_by": "executed hidden suite",
            "detail": (
                "The baseline sliced with an explicit length rather than a negative offset, so "
                "the empty-suffix edge case was never broken and variant_three repaired both."
            ),
        },
        {
            "id": "W2-A3",
            "subject": "fourteen bodies across both corpora",
            "found_by": "near-clone detector",
            "detail": (
                "Normalised-AST and token-stream collisions against C3 and D2 candidates: the "
                "same shape under new names is a restated task, not a new one."
            ),
        },
        {
            "id": "W2-A4",
            "subject": "d3r_numeric.sum_positive and d3r_errors.lookup_or_raise",
            "found_by": "executed hidden suite",
            "detail": (
                "Two failed states passed their own suites: a zero contributes nothing to a sum, "
                "and KeyError already satisfies a bare pytest.raises(LookupError)."
            ),
        },
        {
            "id": "W2-A5",
            "subject": "calibration_ood._retoken",
            "found_by": "v2 canonical-source comparison",
            "detail": (
                "The released token-stream rename also renamed attribute names, so a module "
                "binding a local called `items` and calling `counts.items()` was perturbed into "
                "a module that does not run. Fixed at the shared function; no D2 calibration "
                "group is affected, so the released diagnostic still reproduces."
            ),
        },
    ]


# ------------------------------------------------------------------- S21D3-031: separation


def _all_sources() -> dict[str, str]:
    sources: dict[str, str] = {}
    for spec in TASK_SPECS:
        sources[f"c3:{spec.template_id}:baseline"] = module_source(spec, spec.baseline)
        for field in INHERITED_VARIANT_FIELDS:
            sources[f"c3:{spec.template_id}:{field}"] = module_source(spec, getattr(spec, field))
    for spec in D2_TASK_SPECS:
        sources[f"d2:{spec.template_id}:baseline"] = module_source(spec, spec.baseline)
        for index, body in enumerate(spec.variants):
            sources[f"d2:{spec.template_id}:v{index}"] = module_source(spec, body)
    for spec in D3_TASK_SPECS:
        sources[f"d3:{spec.template_id}:baseline"] = module_source(spec, spec.baseline)
        for index, body in enumerate(spec.variants):
            sources[f"d3:{spec.template_id}:v{index}"] = module_source(spec, body)
    for spec in D3_RETRIEVAL_SPECS:
        sources[f"d3r:{spec.template_id}:failed"] = spec.module_text(spec.failed)
        sources[f"d3r:{spec.template_id}:repaired"] = spec.module_text(spec.repaired)
    return sources


def _separation_evidence(bundle: Any, pre_hash: str, recorded_at: str) -> dict[str, Any]:
    roles = {
        partition.value: sorted(bundle.groups_of(partition)) for partition in CorrectionPartition
    }
    roles["retrieval"] = sorted(bundle.retrieval_groups)
    roles["vertical_slice_fixture"] = [D3_FIXTURE_SPEC.repository_group]

    matrix = {}
    names = sorted(roles)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            matrix[f"{left}|{right}"] = sorted(set(roles[left]) & set(roles[right]))

    sources = _all_sources()
    pairs = near_clone_pairs(sources)
    fresh = [
        pair
        for pair in pairs
        if pair.left.startswith(("d3:", "d3r:")) or pair.right.startswith(("d3:", "d3r:"))
    ]

    def group_of(name: str) -> str:
        return name.rsplit(":", 1)[0]

    intra = [p for p in fresh if group_of(p.left) == group_of(p.right)]
    cross = [p for p in fresh if group_of(p.left) != group_of(p.right)]

    # A detector that finds nothing is indistinguishable from a detector that is not running.
    duplicate = dict(sources)
    victim = next(name for name in sources if name.startswith("d3:"))
    duplicate["seeded:restated_d3_task"] = sources[victim]
    seeded = [
        p for p in near_clone_pairs(duplicate) if "seeded:restated_d3_task" in {p.left, p.right}
    ]

    return {
        "schema_version": 1,
        "sprint": "21D3",
        "wave": "W2",
        "items": ["S21D3-031"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": pre_hash,
        "final_outcomes_inspected": False,
        "purpose": (
            "One transitive separation and rights report over every D3 role: the four carried "
            "from D2 by exact hash, the fresh calibration partition, and the retrieval pool."
        ),
        "role_group_counts": {name: len(members) for name, members in roles.items()},
        "pairwise_role_overlap": matrix,
        "groups_crossing_any_role": sorted(
            {group for members in matrix.values() for group in members}
        ),
        "transitive_grouping": {
            "components": [
                "task_identity",
                "repository_identity",
                "generator_template_lineage",
                "normalized_source_similarity_cluster",
                "source_lineage",
            ],
            "template_id_collisions": sorted(
                {spec.template_id for spec in D3_TASK_SPECS}
                & ({s.template_id for s in TASK_SPECS} | {s.template_id for s in D2_TASK_SPECS})
            ),
            "module_collisions": sorted(
                {spec.module for spec in (*D3_TASK_SPECS, *D3_RETRIEVAL_SPECS)}
                & ({s.module for s in TASK_SPECS} | {s.module for s in D2_TASK_SPECS})
            ),
        },
        "near_clone": {
            "bodies_compared": len(sources),
            "detectors": ["normalized_ast", "token_stream"],
            "cross_group_collisions_touching_d3": [
                {"left": p.left, "right": p.right, "reason": p.reason} for p in cross
            ],
            "intra_pair_structural_matches": len(intra),
            "intra_pair_note": (
                "A retrieval group's failed and repaired states are two states of one task, not "
                "two tasks. Their structural closeness is the edit path the graph projection "
                "derives; the ceiling applies between groups."
            ),
            "seeded_restatement_detected": len(seeded) > 0,
        },
        "inherited_roles": {
            partition.value: {
                "carried_from_d2_catalogue_hash": bundle.reused_from_d2[partition],
                "d3_catalogue_hash": bundle.catalogues[partition].content_hash,
                "identical": bundle.reused_from_d2[partition]
                == bundle.catalogues[partition].content_hash,
                "groups": len(bundle.catalogues[partition].groups),
            }
            for partition in REUSED_ROLES
        },
        "rights": {
            "licence": "Apache-2.0",
            "origin": "first_party_authored_in_repository",
            "self_play_rights": True,
            "evaluation_rights": True,
            "third_party_sources": 0,
            "fresh_groups_covered": len(D3_TASK_SPECS) + len(D3_RETRIEVAL_SPECS),
        },
        "distinct_structures": {
            "note": "Distinct normalised shapes per corpus; equal to the group count means no "
            "two groups share a shape.",
            "d3_calibration_normalized_ast": len(
                {
                    normalized_structure_hash(module_source(spec, spec.baseline))
                    for spec in D3_CALIBRATION_SPECS
                }
            ),
            "d3_calibration_groups": len(D3_CALIBRATION_SPECS),
            "d3_retrieval_token_stream": len(
                {token_stream_hash(spec.module_text(spec.failed)) for spec in D3_RETRIEVAL_SPECS}
            ),
            "d3_retrieval_groups": len(D3_RETRIEVAL_SPECS),
        },
    }


# ------------------------------------------------------------------ S21D3-032: sealed manifests


def _sealed_evidence(bundle: Any, pre_hash: str, recorded_at: str) -> dict[str, Any]:
    calibration = bundle.calibration_transformations
    promotion = bundle.promotion_transformations
    return {
        "schema_version": 1,
        "sprint": "21D3",
        "wave": "W2",
        "items": ["S21D3-032"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": pre_hash,
        "final_outcomes_inspected": False,
        "purpose": (
            "Seal every D3 campaign and holdout manifest before a single feature is encoded: "
            "exact members, exact case identities, and zero outcomes anywhere."
        ),
        "seal": json.loads(bundle.seal.canonical_json()),
        "catalogues": {
            partition.value: {
                "content_hash": catalogue.content_hash,
                "groups": len(catalogue.groups),
                "candidate_slots": catalogue.candidate_slots,
                "campaign_seed": catalogue.campaign_seed,
                "generator_path": catalogue.generator_path,
                "mode": catalogue.mode.value,
                "provenance": catalogue.provenance,
                "outcomes_present": catalogue.outcomes_present,
                "origin": "carried_from_d2" if partition in REUSED_ROLES else "authored_for_d3",
            }
            for partition, catalogue in bundle.catalogues.items()
        },
        "transformation_submanifests": {
            CALIBRATION_STAGE: {
                "content_hash": calibration.content_hash,
                "cases": len(calibration.cases),
                "groups": len({case.source_group_id for case in calibration.cases}),
                "source_manifest_hash": calibration.source_manifest_hash,
                "generator_code_hash": calibration.generator_code_hash,
                "hard_coded_oracle_hash": calibration.hard_coded_oracle_hash,
                "fitted": calibration.fitted,
                "case_ids": [case.case_id for case in calibration.cases],
            },
            PROMOTION_STAGE: {
                "content_hash": promotion.content_hash,
                "cases": len(promotion.cases),
                "groups": len({case.source_group_id for case in promotion.cases}),
                "source_manifest_hash": promotion.source_manifest_hash,
                "generator_code_hash": promotion.generator_code_hash,
                "hard_coded_oracle_hash": promotion.hard_coded_oracle_hash,
                "fitted": promotion.fitted,
                "selection_rule": (
                    "S21D3-060 walks this manifest order and takes the first twenty eligible "
                    "groups; enumerating all sixty is what makes the reserve visible"
                ),
            },
        },
        "retrieval_pool": {
            "content_hash": bundle.retrieval_pool.content_hash,
            "source_groups": len(bundle.retrieval_pool.groups),
            "outcomes_present": bundle.retrieval_pool.outcomes_present,
            "queries_resolved": bundle.retrieval_pool.queries_resolved,
        },
        "capability_isolation": {
            "fitting_can_read_final_bodies": False,
            "fitting_can_read_canary_bodies": False,
            "calibration_can_read_final_bodies": False,
            "retrieval_can_read_correction_outcomes": False,
            "final_and_canary_body_access_opens_at": "S21D3-059",
            "note": (
                "The D3 campaign command resolves task packages only for the partitions it is "
                "given, and W2 gives it training and calibration."
            ),
        },
        "deferred_to_later_items": {
            "transformed_body_hashes": "S21D3-038 for calibration, S21D3-060 for promotion",
            "feature_hashes": "S21D3-034",
            "prediction_hashes": "S21D3-060",
            "retrieval_queries_and_judgements": "S21D3-043",
        },
        "outcomes_present_at_seal": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=EVIDENCE)
    arguments = parser.parse_args()

    transformations_d3.check_golden_pairs()
    bundle = seal_d3_corpus()
    pre_hash = _hash(PRE_REGISTRATION.read_text())
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    corpus = _corpus_evidence(pre_hash, recorded_at)
    if corpus["declaration_mismatches_remaining"]:
        print(json.dumps(corpus["declaration_mismatches_remaining"], indent=2), file=sys.stderr)
        raise SystemExit("the corpus does not execute as declared; refusing to seal it")
    if corpus["six_case_eligibility"]["ineligible_groups"]:
        raise SystemExit("a calibration group cannot carry all six metamorphic cases")

    separation = _separation_evidence(bundle, pre_hash, recorded_at)
    if separation["groups_crossing_any_role"]:
        raise SystemExit("a group crosses two roles; refusing to seal")
    if separation["near_clone"]["cross_group_collisions_touching_d3"]:
        raise SystemExit("a fresh D3 body restates an existing one; refusing to seal")
    if not separation["near_clone"]["seeded_restatement_detected"]:
        raise SystemExit("the near-clone detector did not catch a seeded restatement")

    sealed = _sealed_evidence(bundle, pre_hash, recorded_at)

    outputs = {
        "sprint-21d3-corpus.json": corpus,
        "sprint-21d3-separation.json": separation,
        "sprint-21d3-sealed-manifests.json": sealed,
    }
    for name, value in outputs.items():
        _write(arguments.output_root / name, value)
    print(
        json.dumps(
            {
                "recorded_at": recorded_at,
                "outputs": sorted(outputs),
                "d3_seal_hash": bundle.seal.content_hash,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - operator entry point
    raise SystemExit(main())
