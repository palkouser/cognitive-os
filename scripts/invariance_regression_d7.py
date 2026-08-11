#!/usr/bin/env python3
"""S21D7-033. The invariance-regression sample: forty transformations that add no decision.

The claim is §2.3's first-action condition, on D7's own certification bodies: an identifier
rename and a contract-preserving issue rewrite must not move what the system acts on first.
D5's and D6's samples are properties of their bodies; carrying one across would certify this
sprint's decisions on a predecessor's transformations.

Three things D7 can do that D6 could not, all because the class dropped the embedding:

*The comparison is against the campaign's own numbers.* A v2 feature seal stores the
clip-and-scale bounds it was encoded under, and the six v3 scalars are functions of the source
alone. So this script rebuilds the certification encoder exactly — bounds included — and proves
it by re-encoding the eighty clean bodies and checking every value against its sealed one before
comparing anything transformed. D6 had to fit sample-local bounds and say so; D7 does not.

*No embedding is computed.* No v3 channel reads one, so the encoder is handed a zero vector for
the 384 channels the class ignores. That also retires D4's W2-D9 batch-composition finding for
this record: there is no batch, because there is nothing to embed.

*The first action is measured, not implied.* D6 could only compare the head of the baseline order
and argue the ranker-dependent form followed. Here the fitted direction ranks the clean group and
the transformed group and the two first choices are compared candidate by candidate.

And one control, because a normaliser that erased meaning would pass all of the above: seeded
semantic mutations must change the canonical representation.

This is a precheck. The transformed candidates run under plain pytest in a scratch directory,
never through the governed runner, so no transformed outcome reaches the Event Store, no
observation is projected and no dataset grows.

    UV_CACHE_DIR=.cache/uv uv run python scripts/invariance_regression_d7.py

Read-only against the D5 and D7 artifact stores. No database is opened.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_task_specs_d2 import (  # noqa: E402
    module_source,
    recipe_binding,
)
from cognitive_os.coding.reality_task_specs_d7 import D7_CERTIFICATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.learning import transformations_d3  # noqa: E402
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    ContainmentContrastiveRanker,
    RelationalGroup,
    fit_containment_direction,
    relational_numbers,
)
from cognitive_os.learning.correction_catalogue_d5 import (  # noqa: E402
    build_d5_fitting_catalogue,
)
from cognitive_os.learning.correction_catalogue_d7 import (  # noqa: E402
    D7_CASES,
    build_d7_certification_catalogue,
    seal_d7_corpus,
)
from cognitive_os.learning.correction_features import (  # noqa: E402
    SealedFeatureRecordSetV2,
    feature_input_v2,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    FITTED_FEATURE_V2_SCALARS,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionEncoderV2,
    NumericBoundsV2,
)
from cognitive_os.learning.correction_source import canonical_source_hash  # noqa: E402
from cognitive_os.learning.repair_containment import containment_shares  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d7-pre-registration.json"
SEALED_MANIFESTS = EVIDENCE / "sprint-21d7-sealed-manifests.json"
CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d7-certification-campaign.json"
SNAPSHOTS = EVIDENCE / "sprint-21d7-snapshots.json"
D5_FEATURE_SEALS = EVIDENCE / "sprint-21d5-feature-seals.json"
D5_FITTING_CAMPAIGN = EVIDENCE / "sprint-21d5-self-play-campaign.json"
D7_FEATURE_SEALS = EVIDENCE / "sprint-21d7-feature-seals.json"
D7_DIRECTION = EVIDENCE / "sprint-21d7-w2-direction.json"
OUTPUT = EVIDENCE / "sprint-21d7-invariance-regression.json"

D5_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d5")
D7_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7-measured")

REGULARIZATION = Decimal("1")

#: The 384 channels the class does not read. Handed to the v2 assembler because it demands a
#: vector of that width, and stated here rather than hidden: no number below depends on it.
UNREAD_EMBEDDING = (0.0,) * 384

#: Seeded semantic mutations. Each changes what the program does, so each must change the
#: canonical bytes. Applied to a fixed probe rather than to a corpus body, because a control
#: that depended on which group it landed on would be a different control every run.
PROBE = (
    "def clamp(value, low, high):\n"
    "    if value < low:\n"
    "        return low\n"
    "    if value > high:\n"
    "        return high\n"
    "    return value\n"
)
SEMANTIC_MUTATIONS: tuple[tuple[str, str, str], ...] = (
    ("comparison_flipped", "if value < low:", "if value <= low:"),
    ("bound_swapped", "return low", "return high"),
    ("branch_removed", "    if value > high:\n        return high\n", ""),
    ("constant_introduced", "return value", "return value + 1"),
)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed_records(store: Path, seals_path: Path, partition: str) -> SealedFeatureRecordSetV2:
    row = next(item for item in _read(seals_path)["partitions"] if item["partition"] == partition)
    for path in sorted(store.rglob("*")):
        if not path.is_file() or len(path.name) != 64:
            continue
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if (
            isinstance(candidate, dict)
            and candidate.get("content_hash") == row["feature_seal_hash"]
        ):
            if _digest(path.read_bytes()) != path.name:
                raise SystemExit(f"{path.name} does not hash to its own content address")
            return SealedFeatureRecordSetV2.model_validate_json(path.read_text(encoding="utf-8"))
    raise SystemExit(f"the released {partition} feature seal does not resolve in {store.name}")


@dataclass(frozen=True, slots=True)
class _Case:
    """One sealed case identity turned back into a transformed package."""

    case_id: str
    case_name: str
    group: str
    module: str
    baseline: str
    transformed_baseline: str
    #: `variant index -> body`, in the authored variant order.
    clean_bodies: tuple[str, ...]
    bodies: tuple[str, ...]
    hidden_test: str


def _cases() -> tuple[tuple[_Case, ...], list[str], Any]:
    """Rebuild every sealed case. No score, no label and no vector is read here."""
    submanifest = seal_d7_corpus().invariance_transformations
    by_group = {spec.repository_group: spec for spec in D7_CERTIFICATION_SPECS}
    built: list[_Case] = []
    inapplicable: list[str] = []
    for case in submanifest.cases:
        spec = by_group[case.source_group_id]
        clean = tuple(module_source(spec, body) for body in spec.variants)
        try:
            transformed = transformations_d3.transform(
                case.case_name,
                module_source=module_source(spec, spec.baseline),
                variants=clean,
                visible_test=spec.visible_test,
                hidden_test=spec.hidden_test,
                issue=spec.issue,
            )
        except transformations_d3.PerturbationError as error:  # pragma: no cover - eligibility
            inapplicable.append(f"{case.case_id}:{error}")
            continue
        built.append(
            _Case(
                case_id=case.case_id,
                case_name=case.case_name,
                group=case.source_group_id,
                module=spec.module,
                baseline=module_source(spec, spec.baseline),
                transformed_baseline=transformed.module_source,
                clean_bodies=clean,
                bodies=transformed.variants,
                hidden_test=transformed.hidden_test,
            )
        )
    return tuple(built), inapplicable, submanifest


def _run_one(job: tuple[str, str, str, str]) -> tuple[str, bool]:
    """One transformed candidate against its transformed hidden suite. Never a governed run."""
    key, module, body, hidden = job
    with tempfile.TemporaryDirectory(prefix="cogos-d7-invariance-") as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(body, encoding="utf-8")
        (root / "test_hidden.py").write_text(hidden, encoding="utf-8")
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_hidden.py"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        return key, done.returncode == 0


def _run_all(jobs: list[tuple[str, str, str, str]]) -> dict[str, bool]:
    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4) * 2)) as pool:
        return dict(pool.map(_run_one, jobs))


def _slot_maps() -> tuple[dict[str, dict[int, str]], dict[str, tuple[str, ...]]]:
    """`group -> variant index -> candidate id`, and each group's frozen slot order.

    Indexed by *variant*, not by slot position. `recipe_binding` shuffles which authored variant
    each recipe carries, per template, so slot zero is not variant zero; D4 reported ninety-two
    phantom label changes by comparing them by index.
    """
    catalogue = build_d7_certification_catalogue()
    by_variant: dict[str, dict[int, str]] = {}
    order: dict[str, tuple[str, ...]] = {}
    for group in catalogue.groups:
        binding = [recipe.value for recipe in recipe_binding(group.template_id)]
        order[group.repository_group] = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda item: item.position)
        )
        for slot in group.slots:
            by_variant.setdefault(group.repository_group, {})[binding.index(str(slot.recipe))] = (
                str(slot.candidate_id)
            )
    return by_variant, order


def _clean_labels() -> dict[str, dict[str, bool]]:
    labels: dict[str, dict[str, bool]] = {}
    for row in _read(CERTIFICATION_CAMPAIGN)["candidate_outcomes"]:
        labels.setdefault(str(row["group"]), {})[str(row["candidate_id"])] = bool(row["accepted"])
    return labels


def _direction() -> Any:
    """The wave's one direction, re-derived and checked against the record that sealed it."""
    seal = _sealed_records(D5_ARTIFACT_ROOT, D5_FEATURE_SEALS, "training")
    catalogue = build_d5_fitting_catalogue()
    values = {str(record.candidate_id): record.values for record in seal.records}
    labels: dict[str, dict[str, bool]] = {}
    for item in _read(D5_FITTING_CAMPAIGN)["candidate_outcomes"]:
        labels.setdefault(str(item["group"]), {})[str(item["candidate_id"])] = bool(
            item["accepted"]
        )
    groups = []
    for group in catalogue.groups:
        item = template_of(group)
        order = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        groups.append(
            RelationalGroup(
                group=group.repository_group,
                order=order,
                numbers=relational_numbers(
                    {candidate_id: values[candidate_id] for candidate_id in order},
                    baseline_source=item[0],
                    sources_by_candidate=item[1],
                ),
                accepted=labels[group.repository_group],
            )
        )
    groups.sort(key=lambda item: item.group)
    model = fit_containment_direction(groups, regularization=REGULARIZATION)
    sealed_hash = _read(D7_DIRECTION)["fit"]["model_hash"]
    if model.content_hash() != sealed_hash:
        raise SystemExit(
            f"the direction does not match the one W2 sealed: {model.content_hash()} against "
            f"{sealed_hash}. The wave fits once; this script re-derives it only to prove it"
        )
    return model


def template_of(group: Any) -> tuple[str, dict[str, str]]:
    """One catalogue group's baseline source and its candidates' sources, by candidate id."""
    item = template(group.template_id)
    path = next(name for name in item.visible_files if name.startswith("src/"))
    return item.visible_files[path], {
        str(slot.candidate_id): item.neutral_candidate_sources[
            RealityCandidateStrategy(slot.recipe)
        ][path]
        for slot in group.slots
    }


def _mutation_control() -> dict[str, Any]:
    """A normaliser that erased meaning would pass invariance perfectly and be useless."""
    base = canonical_source_hash(PROBE)
    results = []
    for name, original, replacement in SEMANTIC_MUTATIONS:
        if original not in PROBE:  # pragma: no cover - the probe is a literal above
            raise SystemExit(f"the {name} mutation does not apply to the probe")
        digest = canonical_source_hash(PROBE.replace(original, replacement))
        results.append(
            {"mutation": name, "canonical_hash_changed": digest != base, "canonical_hash": digest}
        )
    return {
        "probe_canonical_hash": base,
        "mutations": results,
        "all_changed_the_canonical_representation": all(
            bool(item["canonical_hash_changed"]) for item in results
        ),
        "distinct_canonical_hashes": len(
            {str(item["canonical_hash"]) for item in results} | {base}
        ),
        "why": (
            "the invariance result says a rename does not move the canonical bytes. This says a "
            "changed meaning does. Without it, a canonicaliser that mapped every program to one "
            "value would satisfy the first claim completely"
        ),
    }


def _run(output: Path) -> int:
    seal = _sealed_records(D7_ARTIFACT_ROOT, D7_FEATURE_SEALS, "calibration")
    encoder = CorrectionEncoderV2(
        NumericBoundsV2(lower=dict(seal.numeric_lower), upper=dict(seal.numeric_upper))
    )
    sealed_values = {str(record.candidate_id): record.values for record in seal.records}
    by_variant, slot_order = _slot_maps()
    cases, inapplicable, submanifest = _cases()
    sample = sorted({case.source_group_id for case in submanifest.cases})
    labels_clean = _clean_labels()

    def _scalars(source: str) -> tuple[tuple[str, float], ...]:
        return encoder.encode(
            feature_input_v2(
                candidate_source=source, canonical_candidate_source_embedding=UNREAD_EMBEDDING
            )
        ).values

    # --- the encoder rebuild is the campaign's, proved before anything transformed is read ----
    rebuild_mismatches = []
    for case in cases:
        for variant, body in enumerate(case.clean_bodies):
            candidate_id = by_variant[case.group][variant]
            if _scalars(body) != tuple(sealed_values[candidate_id]):
                rebuild_mismatches.append({"group": case.group, "variant": variant})
    if rebuild_mismatches:
        raise SystemExit(
            f"{len(rebuild_mismatches)} clean bodies do not re-encode to their sealed values. "
            "The bounds travel in the seal, so this is a broken rebuild rather than moved "
            "evidence, and a comparison against it would compare two encoders"
        )

    sealed_at = utc_now()

    # --- the seven channels, clean against transformed -----------------------------------
    comparisons: list[dict[str, Any]] = []
    clean_numbers: dict[str, dict[str, tuple[float, ...]]] = {}
    transformed_numbers: dict[str, dict[str, tuple[float, ...]]] = {}
    for case in cases:
        ids = {variant: by_variant[case.group][variant] for variant in range(len(case.bodies))}
        clean = relational_numbers(
            {ids[variant]: sealed_values[ids[variant]] for variant in ids},
            baseline_source=case.baseline,
            sources_by_candidate={ids[variant]: case.clean_bodies[variant] for variant in ids},
        )
        transformed = relational_numbers(
            {ids[variant]: _scalars(case.bodies[variant]) for variant in ids},
            baseline_source=case.transformed_baseline,
            sources_by_candidate={ids[variant]: case.bodies[variant] for variant in ids},
        )
        clean_numbers[case.case_id] = clean
        transformed_numbers[case.case_id] = transformed
        clean_shares = containment_shares(
            case.baseline, {ids[variant]: case.clean_bodies[variant] for variant in ids}
        )
        transformed_shares = containment_shares(
            case.transformed_baseline, {ids[variant]: case.bodies[variant] for variant in ids}
        )
        for variant, candidate_id in ids.items():
            comparisons.append(
                {
                    "case_id": case.case_id,
                    "case_name": case.case_name,
                    "group": case.group,
                    "variant": variant,
                    "scalars_unchanged": (
                        tuple(sealed_values[candidate_id]) == _scalars(case.bodies[variant])
                    ),
                    "containment_share_unchanged": (
                        clean_shares[candidate_id] == transformed_shares[candidate_id]
                    ),
                    "relational_vector_unchanged": clean[candidate_id] == transformed[candidate_id],
                    "clean_canonical_source_hash": canonical_source_hash(
                        case.clean_bodies[variant]
                    ),
                    "transformed_canonical_source_hash": canonical_source_hash(
                        case.bodies[variant]
                    ),
                    "canonical_source_unchanged": canonical_source_hash(case.clean_bodies[variant])
                    == canonical_source_hash(case.bodies[variant]),
                }
            )

    # --- the verifier does not change its mind ------------------------------------------
    executed = _run_all(
        [
            (f"{case.case_id}#{variant}", case.module, body, case.hidden_test)
            for case in cases
            for variant, body in enumerate(case.bodies)
        ]
    )
    executed_at = utc_now()
    if executed_at <= sealed_at:  # pragma: no cover - the clock only moves forward
        raise SystemExit("the transformed features were not sealed before their execution")

    label_changes = [
        {
            "case_id": case.case_id,
            "group": case.group,
            "variant": variant,
            "clean": labels_clean[case.group][by_variant[case.group][variant]],
            "transformed": executed[f"{case.case_id}#{variant}"],
        }
        for case in cases
        for variant in range(len(case.bodies))
        if executed[f"{case.case_id}#{variant}"]
        != labels_clean[case.group][by_variant[case.group][variant]]
    ]

    # --- the first action, ranked both ways under the wave's direction --------------------
    model = _direction()
    ranker = ContainmentContrastiveRanker(model, margin_floor=Decimal("0"))
    first_actions = []
    for case in cases:
        order = slot_order[case.group]
        clean_first = ranker.rank(clean_numbers[case.case_id], baseline_order=order)
        transformed_first = ranker.rank(transformed_numbers[case.case_id], baseline_order=order)
        first_actions.append(
            {
                "case_id": case.case_id,
                "group": case.group,
                "clean_first_action": clean_first.ordered_candidate_ids[0],
                "transformed_first_action": transformed_first.ordered_candidate_ids[0],
                "preserved": (
                    clean_first.ordered_candidate_ids[0]
                    == transformed_first.ordered_candidate_ids[0]
                ),
            }
        )
    first_action_changes = [item for item in first_actions if not item["preserved"]]

    changed_vectors = [item for item in comparisons if not item["relational_vector_unchanged"]]
    mutation = _mutation_control()

    stops: list[str] = []
    if changed_vectors or label_changes or first_action_changes:
        stops.append("invariance_regression")
    if not mutation["all_changed_the_canonical_representation"]:
        stops.append("invariance_regression")

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W2",
            "items": ["S21D7-033"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "certification_campaign_sha256": _digest(CERTIFICATION_CAMPAIGN.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "d7_feature_seals_sha256": _digest(D7_FEATURE_SEALS.read_bytes()),
            "w2_direction_sha256": _digest(D7_DIRECTION.read_bytes()),
            "final_outcomes_inspected": False,
            "final_or_canary_access": 0,
            "purpose": (
                "execute the claim the D7 corpus seal makes about its own certification bodies: "
                "a transformation repeats its source group's relational vector, so it adds no "
                "independent decision and cannot move the first action"
            ),
            "encoder": {
                "version": seal.encoder_version,
                "bounds_from": "the D7 certification feature seal, which stores them",
                "rebuild_check": (
                    "every one of the clean bodies re-encodes to its sealed values before any "
                    "transformed body is read"
                ),
                "clean_bodies_re_encoded": len(comparisons),
                "mismatches": len(rebuild_mismatches),
                "embedding": {
                    "computed": False,
                    "supplied": "a zero vector of 384 channels",
                    "why": (
                        "no v3 channel reads an embedding. Supplying zeros keeps the v2 "
                        "assembler's contract without making any number here depend on a model, "
                        "and retires D4's W2-D9 batch-composition finding for this record: "
                        "there is no batch"
                    ),
                },
            },
            "submanifest": {
                "hash": submanifest.content_hash,
                "stage": submanifest.stage,
                "generator_code_hash": submanifest.generator_code_hash,
                "hard_coded_oracle_hash": submanifest.hard_coded_oracle_hash,
                "fitted": submanifest.fitted,
                "nominal_cases": len(submanifest.cases),
                "applicable_cases": len(cases),
                "not_applicable": inapplicable,
                "cases_by_name": {
                    name: sum(1 for case in cases if case.case_name == name) for name in D7_CASES
                },
                "source_groups": len({case.group for case in cases}),
                "sample_groups_named": sample,
                "sample_matches_the_seal": sorted({case.group for case in cases}) == sample,
                "sample_is_drawn_from": (
                    "the D7 certification catalogue — twenty of the hundred groups authored in "
                    "W1, so the property is measured on the corpus the selection is certified on"
                ),
            },
            "chronology": {
                "features_sealed_at": sealed_at.isoformat(),
                "first_transformed_execution_at": executed_at.isoformat(),
                "every_transformed_seal_precedes_its_execution": executed_at > sealed_at,
                "bounds_fitted_on": "nothing here; the campaign's own bounds are read from a seal",
            },
            "independence": {
                "transformed_decisions": len(cases),
                "independent_decisions": 0,
                "candidate_vectors_compared": len(comparisons),
                "relational_vectors_unchanged": len(comparisons) - len(changed_vectors),
                "relational_vectors_changed": len(changed_vectors),
                "changed": changed_vectors[:20],
                "scalars_unchanged": sum(1 for item in comparisons if item["scalars_unchanged"]),
                "containment_share_unchanged": sum(
                    1 for item in comparisons if item["containment_share_unchanged"]
                ),
                "canonical_sources_unchanged": sum(
                    1 for item in comparisons if item["canonical_source_unchanged"]
                ),
                "channels": [*FITTED_FEATURE_V2_SCALARS, "repair_containment_share"],
                "reading": (
                    f"{len(comparisons)} transformed candidate vectors, every one identical to "
                    f"its clean counterpart on all seven channels, so the {len(cases)} "
                    f"transformed decisions repeat {len(sample)} clean ones and add none"
                ),
            },
            "verifier": {
                "candidate_outcomes_executed": len(executed),
                "label_changes": len(label_changes),
                "changed": label_changes[:20],
                "accepted": sum(1 for value in executed.values() if value),
                "governed_runs": 0,
                "how": (
                    "plain pytest in a scratch directory. A precheck that wrote governed "
                    "outcomes would put transformed rows in the store the clean campaign owns"
                ),
            },
            "first_action": {
                "cases_compared": len(first_actions),
                "changes": len(first_action_changes),
                "changed": first_action_changes,
                "preservation": "100%" if not first_action_changes else "below 100%",
                "ranker_dependent_form": {
                    "measured_here": True,
                    "how": (
                        "the wave's fitted direction ranks the clean group and the transformed "
                        "group and the two first choices are compared. D6 could only compare "
                        "the head of the baseline order and argue this followed; the class "
                        "dropped the embedding, so here it is run"
                    ),
                    "model_hash": model.content_hash(),
                    "margin_floor": "0",
                    "tie_break": "the baseline order, frozen by the catalogue",
                },
            },
            "semantic_mutation_control": mutation,
            "entered_any_dataset": False,
            "fitted": False,
            "stops": sorted(set(stops)),
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
                "cases": len(cases),
                "source_groups": len({case.group for case in cases}),
                "candidate_vectors_compared": len(comparisons),
                "relational_vectors_changed": len(changed_vectors),
                "verifier_label_changes": len(label_changes),
                "first_action_changes": len(first_action_changes),
                "independent_decisions": 0,
                "semantic_mutations_all_changed_the_canonical_form": mutation[
                    "all_changed_the_canonical_representation"
                ],
                "stops": evidence["stops"],
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 1 if stops else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return _run(parser.parse_args().output)


if __name__ == "__main__":
    raise SystemExit(main())
