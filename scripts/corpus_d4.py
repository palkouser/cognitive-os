#!/usr/bin/env python3
"""S21D4-030 and S21D4-031: execute the D4 corpora and prove they are separated.

Two items in one command because they are one one-way door. The corpus is only finished when
every body has been *executed* against its own suites, and separation is only meaningful over a
finished corpus. Running them apart would let a separation proof be written over a corpus whose
last authoring defect had not been found yet.

Nothing here reads an outcome, a candidate score or a verifier label from any D4 role. The runs
below are throwaway fixture validation in a temporary directory, exactly as §0.3 permits for
corpus authoring: they never reach the Event Store, the Artifact Store, a learned observation or
a metric, and the report carries pass/fail and package hashes rather than suitability scores.

    UV_CACHE_DIR=.cache/uv uv run python scripts/corpus_d4.py
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
)
from cognitive_os.coding.reality_retrieval_specs_d3 import D3_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d4 import D4_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs import TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d2 import (  # noqa: E402
    D2_TASK_SPECS,
    INHERITED_VARIANT_FIELDS,
    module_source,
)
from cognitive_os.coding.reality_task_specs_d3 import D3_TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.learning import correction_catalogue as d2_catalogue  # noqa: E402
from cognitive_os.learning import correction_catalogue_d3 as d3_catalogue  # noqa: E402
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402
from cognitive_os.learning.correction_source import (  # noqa: E402
    SourceNormalizationError,
    canonical_source_hash,
)

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d4-contracts.json"
CALIBRATION_SOURCE = REPOSITORY / "src/cognitive_os/coding/reality_task_specs_d4.py"
RETRIEVAL_SOURCE = REPOSITORY / "src/cognitive_os/coding/reality_retrieval_specs_d4.py"

_VARIANT_LABELS = ("variant_one", "variant_two", "variant_three", "variant_four")

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


def _sha256(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash(text: str) -> str:
    return _sha256(text.encode("utf-8"))


def _canonical(value: Any) -> bytes:
    """The D4 convention: the bytes hashed are the bytes written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _write(path: Path, body: dict[str, Any]) -> str:
    sealed = dict(body)
    sealed["integrity_content_hash"] = _sha256(_canonical(body))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(sealed) + b"\n")
    return _sha256(path.read_bytes())


# --------------------------------------------------------------- S21D4-030: executed authoring


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


def _job(job: tuple[str, str, str, str, str, str]) -> tuple[str, str, str, bool]:
    template_id, label, module, body, suite_name, suite = job
    with tempfile.TemporaryDirectory(prefix="cogos-d4-authoring-") as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(body, encoding="utf-8")
        (root / "test_suite.py").write_text(suite, encoding="utf-8")
        return template_id, label, suite_name, _pytest(root, "test_suite.py")


def _execute_corpus() -> tuple[dict[str, Any], dict[str, dict[str, str]], list[str]]:
    jobs: list[tuple[str, str, str, str, str, str]] = []
    for spec in D4_CALIBRATION_SPECS:
        bodies = (
            ("baseline", spec.baseline),
            ("variant_one", spec.variant_one),
            ("variant_two", spec.variant_two),
            ("variant_three", spec.variant_three),
            ("variant_four", spec.variant_four),
        )
        for label, body in bodies:
            text = module_source(spec, body)
            jobs.append((spec.template_id, label, spec.module, text, "visible", spec.visible_test))
            jobs.append((spec.template_id, label, spec.module, text, "hidden", spec.hidden_test))

    retrieval_jobs: list[tuple[str, str, str, str, str, str]] = []
    for spec in D4_RETRIEVAL_SPECS:
        for label, body in (("failed", spec.failed), ("repaired", spec.repaired)):
            text = spec.module_text(body)
            retrieval_jobs.append(
                (spec.template_id, label, spec.module, text, "visible", spec.visible_test)
            )
            retrieval_jobs.append(
                (spec.template_id, label, spec.module, text, "hidden", spec.hidden_test)
            )

    with ThreadPoolExecutor(max_workers=16) as pool:
        calibration = list(pool.map(_job, jobs))
        retrieval = list(pool.map(_job, retrieval_jobs))

    defects: list[str] = []
    verdicts: dict[str, dict[str, str]] = {}
    for template_id, label, suite_name, passed in calibration:
        wanted = EXPECTED[(label, suite_name)]
        verdicts.setdefault(template_id, {})[f"{label}:{suite_name}"] = (
            "as_declared" if passed == wanted else "MISMATCH"
        )
        if passed != wanted:
            defects.append(f"{template_id}:{label}:{suite_name}")
    for template_id, label, suite_name, passed in retrieval:
        wanted = True if suite_name == "visible" else label == "repaired"
        verdicts.setdefault(template_id, {})[f"{label}:{suite_name}"] = (
            "as_declared" if passed == wanted else "MISMATCH"
        )
        if passed != wanted:
            defects.append(f"{template_id}:{label}:{suite_name}")

    report = {
        "calibration_runs": len(calibration),
        "retrieval_runs": len(retrieval),
        "baselines_passing_their_visible_tests": sum(
            passed
            for _t, label, suite, passed in calibration
            if label == "baseline" and suite == "visible"
        ),
        "baselines_failing_their_hidden_tests": sum(
            not passed
            for _t, label, suite, passed in calibration
            if label == "baseline" and suite == "hidden"
        ),
        "declared_repairs_passing_both_suites": sum(
            passed
            for _t, label, _s, passed in calibration
            if label in ("variant_one", "variant_two")
        ),
        "partial_fixes_passing_visible_and_failing_hidden": sum(
            passed == EXPECTED[(label, suite)]
            for _t, label, suite, passed in calibration
            if label in ("variant_three", "variant_four")
        ),
        "retrieval_failed_states_rejected_by_the_verifier": sum(
            not passed
            for _t, label, suite, passed in retrieval
            if label == "failed" and suite == "hidden"
        ),
        "retrieval_repairs_accepted_by_the_verifier": sum(
            passed
            for _t, label, suite, passed in retrieval
            if label == "repaired" and suite == "hidden"
        ),
        "declaration_mismatches": sorted(defects),
    }
    return report, verdicts, defects


def _template_families() -> dict[str, Any]:
    """§2 asks for at least fifteen distinct template families over the hundred groups.

    The guard it states is what fixes the reading: a hundred groups must not be "six families
    with ninety-four seeds". A seed of a template shares that template's shape, so the honest
    mechanical measure is the number of distinct normalised structures among the baselines --
    the same detector S21D4-031 runs, pointed at the corpus rather than across corpora. The six
    `RealityTaskFamily` values are reported alongside because they are what the campaign routes
    on, not because six could ever satisfy a floor of fifteen.
    """
    shapes = {normalized_structure_hash(spec.baseline) for spec in D4_CALIBRATION_SPECS}
    routing: dict[str, int] = {}
    for spec in D4_CALIBRATION_SPECS:
        routing[spec.family.value] = routing.get(spec.family.value, 0) + 1
    return {
        "reading": (
            "a template family is a distinct baseline structure; a seeded family would share "
            "one, which is what the 'six families with ninety-four seeds' guard forbids"
        ),
        "distinct_baseline_structures": len(shapes),
        "required_minimum": 15,
        "satisfied": len(shapes) >= 15,
        "routing_families": routing,
        "routing_families_covered": len(routing),
    }


def _validator_report() -> dict[str, Any]:
    """The sanitised corpus-authoring validator output §0.3 and S21D4-030 allow.

    Package hashes and a parse/execute verdict. No candidate score, no verifier label per
    candidate, no body, no suitability metric -- a validator that reported those would be a
    quiet channel from an unopened role into the sprint.
    """
    packages = {}
    for spec in D4_CALIBRATION_SPECS:
        bodies = (
            spec.baseline,
            spec.variant_one,
            spec.variant_two,
            spec.variant_three,
            spec.variant_four,
        )
        packages[spec.template_id] = _hash(
            "".join(module_source(spec, body) for body in bodies)
            + spec.visible_test
            + spec.hidden_test
        )
    for spec in D4_RETRIEVAL_SPECS:
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


def _defect_ledger() -> list[dict[str, str]]:
    """What execution and the detectors caught while these corpora were being written.

    Recorded because a corpus that reports only its finished state hides the fact that the
    finished state was reached by being told it was wrong.
    """
    return [
        {
            "id": "W2-D1",
            "subject": "d4_boundary.window_sums and d4_boundary.batch_by_size baselines",
            "found_by": "executed visible suite",
            "detail": (
                "Two baselines were broken so thoroughly that they failed their own published "
                "suites. A baseline has to be wrong in the hidden contract and right in the "
                "ordinary case, or the ranking decision never arises."
            ),
        },
        {
            "id": "W2-D2",
            "subject": "five groups across the first two batches",
            "found_by": "executed hidden suite",
            "detail": (
                "Both partial fixes passed the hidden suite, because the two declared edge "
                "cases were one defect wearing two descriptions. The clearest was "
                "rank_positions, where 'ties share a rank' and 'the rank after a tie skips "
                "places' are the same bug. Re-authored around genuinely independent defects "
                "rather than by weakening a test."
            ),
        },
        {
            "id": "W2-D3",
            "subject": "d4_transform.numbered_outline variants one, two and three",
            "found_by": "executed visible suite",
            "detail": (
                "The declared repairs truncated the counter list to the depth itself rather "
                "than one past it, so a second heading at the same depth restarted at one. A "
                "replacement group authored to repair a separation defect brought its own."
            ),
        },
        {
            "id": "W2-D4",
            "subject": "sixteen bodies across batches two to five",
            "found_by": "near-clone detector",
            "detail": (
                "Normalised-AST and token-stream collisions against released D2 bodies and, "
                "twice, against another D4 group written in the same batch. Replaced rather "
                "than renamed: the same shape under a new name is a restated task."
            ),
        },
        {
            "id": "W2-D5",
            "subject": "d4_transform.reorder_columns",
            "found_by": "near-clone detector",
            "detail": (
                "The collision with released d2-transform-order was not cosmetic: that group "
                "states the same contract word for word -- named keys first in the order given, "
                "then everything else in its original order, ignoring a name that is not there. "
                "A separation defect at the level of the task cannot be repaired by rewriting a "
                "variant, so the group was withdrawn and fill_forward authored in its place."
            ),
        },
        {
            "id": "W2-D6",
            "subject": "the near-clone scan itself, and eleven bodies it had not been shown",
            "found_by": "widening the scan to the scope this sprint had already written down",
            "detail": (
                "The scan run while the hundred calibration groups were authored compared D2 "
                "and D3 calibration only. It never loaded the thirty C3 groups in "
                "reality_task_specs.py, and never loaded the sixty D3 retrieval pairs. Every "
                "zero it reported was true of the pool it was shown and not of the pool this "
                "sprint has to clear. Widened to the scope corpus_d3.py published, it found "
                "fifty-six collisions touching D4, eleven of them in calibration groups that "
                "were already committed. Four of those five groups were duplicates at the level "
                "of the task and were withdrawn and replaced (release_number, share_out, "
                "invert_mapping, merge_defaults); bind_alias kept its contract and had one body "
                "reshaped. The retrieval pool, unreleased, took five withdrawals and seventeen "
                "reshapes."
            ),
        },
        {
            "id": "W2-D7",
            "subject": (
                "d2-parsing-coordinate/d2-parsing-range and d2-errors-divmod/d2-numeric-rounding"
            ),
            "found_by": "near-clone detector",
            "detail": (
                "Two collisions internal to the released D2 corpus. Recorded and not repaired: "
                "those bytes are sealed, and D3's released scope is collisions touching the "
                "sprint's own bodies. Neither pair touches a D4 group."
            ),
        },
    ]


def _corpus_evidence(recorded_at: str) -> dict[str, Any]:
    executed, verdicts, defects = _execute_corpus()

    canonical_failures = []
    for spec in D4_CALIBRATION_SPECS:
        bodies = (
            spec.baseline,
            spec.variant_one,
            spec.variant_two,
            spec.variant_three,
            spec.variant_four,
        )
        for body in bodies:
            try:
                canonical_source_hash(module_source(spec, body))
            except SourceNormalizationError as error:  # pragma: no cover - authoring gate
                canonical_failures.append(f"{spec.template_id}: {error}")

    retrieval_families: dict[str, int] = {}
    for spec in D4_RETRIEVAL_SPECS:
        retrieval_families[spec.family.value] = retrieval_families.get(spec.family.value, 0) + 1

    return {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W2",
        "items": ["S21D4-030"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "final_outcomes_inspected": False,
        "purpose": (
            "Record the authored D4 corpora and that every body was executed rather than "
            "declared: a hundred fresh four-candidate calibration groups, which is the smallest "
            "corpus from which §2.3's floor of a hundred independent calibration decisions can "
            "be met, and sixty failed/repair retrieval groups."
        ),
        "calibration_corpus": {
            "groups": len(D4_CALIBRATION_SPECS),
            "required_groups": 100,
            "candidates_per_group": 4,
            "why_a_hundred": (
                "after the W1 erratum an independent decision is a distinct fitted feature "
                "vector, so a transformation of a group is not a second decision and only a "
                "second group is"
            ),
            "template_families": _template_families(),
            "source_file_sha256": _hash(CALIBRATION_SOURCE.read_text(encoding="utf-8")),
        },
        "retrieval_pool": {
            "source_groups": len(D4_RETRIEVAL_SPECS),
            "required_source_groups": 60,
            "families": retrieval_families,
            "shape": "one failed state and one accepted repair per group",
            "source_file_sha256": _hash(RETRIEVAL_SOURCE.read_text(encoding="utf-8")),
        },
        "executed_verification": {
            "note": "Every verdict is an executed pytest run in a throwaway directory.",
            **executed,
        },
        "per_group_verdicts": verdicts,
        "canonical_source_failures": canonical_failures,
        "authoring_defect_ledger": _defect_ledger(),
        "corpus_authoring_validator": _validator_report(),
        "declaration_mismatches_remaining": defects,
    }


# ------------------------------------------------------------------- S21D4-031: separation


def _all_sources() -> dict[str, str]:
    """Every body any sprint has published, keyed by group so collisions can be scoped.

    The pool and the hashing convention are corpus_d3.py's: whole module text, all four
    calibration corpora and both retrieval pools. Reproducing the released scope is the point --
    a narrower pool is how W2-D6 happened.
    """
    sources: dict[str, str] = {}
    for spec in TASK_SPECS:
        sources[f"c3:{spec.repository_group}:baseline"] = module_source(spec, spec.baseline)
        for field in INHERITED_VARIANT_FIELDS:
            sources[f"c3:{spec.repository_group}:{field}"] = module_source(
                spec, getattr(spec, field)
            )
    for spec in D2_TASK_SPECS:
        sources[f"d2:{spec.repository_group}:baseline"] = module_source(spec, spec.baseline)
        for index, body in enumerate(spec.variants):
            sources[f"d2:{spec.repository_group}:v{index}"] = module_source(spec, body)
    for spec in D3_TASK_SPECS:
        sources[f"d3:{spec.repository_group}:baseline"] = module_source(spec, spec.baseline)
        for index, body in enumerate(spec.variants):
            sources[f"d3:{spec.repository_group}:v{index}"] = module_source(spec, body)
    for spec in D3_RETRIEVAL_SPECS:
        sources[f"d3r:{spec.repository_group}:failed"] = spec.module_text(spec.failed)
        sources[f"d3r:{spec.repository_group}:repaired"] = spec.module_text(spec.repaired)
    for spec in D4_CALIBRATION_SPECS:
        sources[f"d4:{spec.repository_group}:baseline"] = module_source(spec, spec.baseline)
        for index, body in enumerate(spec.variants):
            sources[f"d4:{spec.repository_group}:v{index}"] = module_source(spec, body)
    for spec in D4_RETRIEVAL_SPECS:
        sources[f"d4r:{spec.repository_group}:failed"] = spec.module_text(spec.failed)
        sources[f"d4r:{spec.repository_group}:repaired"] = spec.module_text(spec.repaired)
    return sources


def _roles() -> dict[str, list[str]]:
    """Which groups each D4 role holds.

    Fitting, final A, final B and canary are predecessor groups carried under S21D4-004's reuse
    decision, so their membership is read off the released catalogues rather than chosen here.
    The contract's fitting composition -- ten D2 calibration, fifty D2 training, twenty D3
    calibration -- is exactly the three released partitions, so there is no selection to make.
    """
    d2 = {
        partition: {entry.repository_group for entry in entries}
        for partition, entries in d2_catalogue.assign_groups().items()
    }
    d3 = d3_catalogue.seal_d3_corpus()
    return {
        "fitting": sorted(
            d2[CorrectionPartition.CALIBRATION]
            | d2[CorrectionPartition.TRAINING]
            | set(d3.groups_of(CorrectionPartition.CALIBRATION))
        ),
        "calibration": sorted(spec.repository_group for spec in D4_CALIBRATION_SPECS),
        "final_a": sorted(d3.groups_of(CorrectionPartition.FINAL_A)),
        "final_b": sorted(d3.groups_of(CorrectionPartition.FINAL_B)),
        "canary": sorted(d3.groups_of(CorrectionPartition.CANARY)),
        "retrieval": sorted(spec.repository_group for spec in D4_RETRIEVAL_SPECS),
    }


def _separation_evidence(recorded_at: str) -> dict[str, Any]:
    roles = _roles()
    names = sorted(roles)
    crossings = {}
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            crossings[f"{left}|{right}"] = sorted(set(roles[left]) & set(roles[right]))

    sources = _all_sources()
    pairs = near_clone_pairs(sources)

    def group_of(name: str) -> str:
        return name.rsplit(":", 1)[0]

    touching = [
        pair
        for pair in pairs
        if pair.left.startswith(("d4:", "d4r:")) or pair.right.startswith(("d4:", "d4r:"))
    ]
    intra = [pair for pair in touching if group_of(pair.left) == group_of(pair.right)]
    cross = [pair for pair in touching if group_of(pair.left) != group_of(pair.right)]

    # A detector that finds nothing is indistinguishable from a detector that is not running.
    seeded_pool = dict(sources)
    victim = next(name for name in sources if name.startswith("d4:"))
    seeded_pool["seeded:restated_d4_task"] = sources[victim]
    seeded = [
        pair
        for pair in near_clone_pairs(seeded_pool)
        if "seeded:restated_d4_task" in {pair.left, pair.right}
    ]

    released_ids = {spec.template_id for spec in TASK_SPECS}
    released_ids |= {spec.template_id for spec in D2_TASK_SPECS}
    released_ids |= {spec.template_id for spec in D3_TASK_SPECS}
    released_ids |= {spec.template_id for spec in D3_RETRIEVAL_SPECS}
    released_groups = {spec.repository_group for spec in TASK_SPECS}
    released_groups |= {spec.repository_group for spec in D2_TASK_SPECS}
    released_groups |= {spec.repository_group for spec in D3_TASK_SPECS}
    released_groups |= {spec.repository_group for spec in D3_RETRIEVAL_SPECS}
    d4_ids = {spec.template_id for spec in (*D4_CALIBRATION_SPECS, *D4_RETRIEVAL_SPECS)}
    d4_groups = {spec.repository_group for spec in (*D4_CALIBRATION_SPECS, *D4_RETRIEVAL_SPECS)}
    d4_signatures = {spec.task_signature for spec in D4_RETRIEVAL_SPECS} | {
        spec.template_id.replace(".", ":") for spec in D4_CALIBRATION_SPECS
    }
    released_signatures = {spec.task_signature for spec in D3_RETRIEVAL_SPECS}
    released_signatures |= {
        spec.template_id.replace(".", ":") for spec in (*TASK_SPECS, *D2_TASK_SPECS, *D3_TASK_SPECS)
    }

    return {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W2",
        "items": ["S21D4-031"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "final_outcomes_inspected": False,
        "purpose": (
            "Prove that no D4 group crosses a role, that nothing D4 authored restates a task "
            "any predecessor published, and that the detector which says so is running."
        ),
        "role_separation": {
            "group_counts": {name: len(groups) for name, groups in roles.items()},
            "pairs_sharing_a_group": {name: len(shared) for name, shared in crossings.items()},
            "groups_crossing_a_role": sorted(
                {group for shared in crossings.values() for group in shared}
            ),
            "all_pairwise_disjoint": not any(crossings.values()),
            "fitting_composition": {
                "d2_calibration": 10,
                "d2_training": 50,
                "d3_calibration": 20,
                "read_off_the_released_catalogues": True,
            },
        },
        "near_clone": {
            "bodies_compared": len(sources),
            "detectors": ["normalized_ast", "token_stream"],
            "pool": ["c3", "d2", "d3", "d3_retrieval", "d4", "d4_retrieval"],
            "hashed": "whole module text, as corpus_d3.py hashes it",
            "cross_group_collisions_touching_d4": [
                {"left": pair.left, "right": pair.right, "detector": pair.reason} for pair in cross
            ],
            "intra_group_structural_matches": len(intra),
            "intra_group_note": (
                "A calibration group's four candidates are the same task under four repairs, and "
                "a retrieval group's two states are one task before and after one. Their "
                "structural closeness is the edit path the graph projection derives; the ceiling "
                "applies between groups."
            ),
            "seeded_restatement_detected": bool(seeded),
            "seeded_restatement_pairs": len(seeded),
        },
        "lineage": {
            "template_ids_reused_from_a_predecessor": sorted(d4_ids & released_ids),
            "repository_groups_reused_from_a_predecessor": sorted(d4_groups & released_groups),
            "task_signatures_reused_from_a_predecessor": sorted(
                d4_signatures & released_signatures
            ),
            "d4_template_ids": len(d4_ids),
            "d4_repository_groups": len(d4_groups),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=EVIDENCE)
    parser.add_argument("--check", action="store_true", help="verify without rewriting")
    arguments = parser.parse_args()

    recorded_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    corpus = _corpus_evidence(recorded_at)
    separation = _separation_evidence(recorded_at)

    stops: list[str] = []
    if corpus["declaration_mismatches_remaining"]:
        stops.append("corpus_declaration_mismatch")
    if corpus["canonical_source_failures"]:
        stops.append("corpus_source_not_canonical")
    if not corpus["calibration_corpus"]["template_families"]["satisfied"]:
        stops.append("corpus_too_few_template_families")
    if separation["near_clone"]["cross_group_collisions_touching_d4"]:
        stops.append("separation_near_clone_collision")
    if not separation["near_clone"]["seeded_restatement_detected"]:
        stops.append("separation_detector_not_running")
    if not separation["role_separation"]["all_pairwise_disjoint"]:
        stops.append("separation_role_crossing")
    if separation["lineage"]["task_signatures_reused_from_a_predecessor"]:
        stops.append("separation_signature_reuse")

    if arguments.check:
        print(json.dumps({"stops": stops}, indent=1))
        return 1 if stops else 0

    corpus_path = arguments.output_root / "sprint-21d4-corpus.json"
    separation_path = arguments.output_root / "sprint-21d4-separation.json"
    corpus_hash = _write(corpus_path, corpus)
    separation_hash = _write(separation_path, separation)

    executed = corpus["executed_verification"]
    families = corpus["calibration_corpus"]["template_families"]
    print(f"{corpus_path.name}  {corpus_hash}")
    print(f"  calibration runs: {executed['calibration_runs']}")
    print(f"  retrieval runs:   {executed['retrieval_runs']}")
    print(f"  mismatches:       {len(executed['declaration_mismatches'])}")
    print(
        f"  template families: {families['distinct_baseline_structures']} "
        f"(floor {families['required_minimum']})"
    )
    print(f"{separation_path.name}  {separation_hash}")
    print(f"  bodies compared:  {separation['near_clone']['bodies_compared']}")
    print(
        "  cross-group collisions: "
        f"{len(separation['near_clone']['cross_group_collisions_touching_d4'])}"
    )
    print(f"  seeded restatement caught: {separation['near_clone']['seeded_restatement_detected']}")
    print(f"  roles pairwise disjoint:   {separation['role_separation']['all_pairwise_disjoint']}")
    if stops:
        print("STOPS: " + ", ".join(stops))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
