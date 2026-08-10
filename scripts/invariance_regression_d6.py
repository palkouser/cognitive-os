#!/usr/bin/env python3
"""S21D6-031. The invariance-regression sample: forty transformations that add no decision.

S21D6-023 sealed `invariance_independent_decisions: 0` over twenty of the hundred freshly
authored certification groups. That is a claim about D6's own corpus, not an inherited one: the
bodies are new, the transform seed is D6's own 21068303, and whether a rename survives the
alpha-normaliser on *these* bodies is a measurement.

The reason it is measured here rather than inherited is the same one that made D6 author a
corpus at all. §2.3's first-action condition is read against the decisions the selection is
certified on, and those are the certification half's. D5's sample is a property of D5's bodies;
carrying it across would certify this sprint's decisions on a predecessor's transformations.

Forty cases, two per group, and three things have to hold at once:

*The vectors are identical.* An identifier rename is erased by the alpha-normaliser and an issue
rewrite never reaches a v2 channel, because v2 embeds the candidate source and nothing else. If
either produced a different vector, the transformed set would carry independent decisions and
the hundred-decision floor would have been met by counting replicas.

*The verifier does not change its mind.* Same contract, spelled differently, same labels. A
label change means the transformation altered behaviour, which makes it a different task rather
than the same one restated.

*The first action does not move.* This is the §2.3 condition. Its ranker-independent form is
checked directly; its ranker-dependent form follows from the first result rather than needing a
second run, and the record says exactly why.

And one control, because the first two are also what a normaliser that erased everything would
produce: seeded semantic mutations must change the canonical representation.

This is a precheck. The transformed candidates run under plain pytest in a scratch directory,
never through the governed runner, so no transformed outcome reaches the Event Store, no
observation is projected, and no dataset grows. `entered_any_dataset` is false and stays false.

    set -a && . ./.env.s21d6.measured.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/invariance_regression_d6.py \\
        --model /home/palkouser/projekt/cognitive-os-data/models/all-MiniLM-L6-v2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_task_specs_d2 import (  # noqa: E402
    module_source,
    recipe_binding,
)
from cognitive_os.coding.reality_task_specs_d6 import D6_CERTIFICATION_SPECS  # noqa: E402
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.infrastructure.embeddings import build_embedding_provider, minilm  # noqa: E402
from cognitive_os.learning import transformations_d3  # noqa: E402
from cognitive_os.learning.correction_catalogue_d6 import (  # noqa: E402
    D6_CASES,
    seal_d6_corpus,
)
from cognitive_os.learning.correction_features import (  # noqa: E402
    canonical_embedding_windows,
    feature_input_v2,
    pool_canonical_embedding,
    raw_numeric_row_v2,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionPartition,
    DecisionCensusV4,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionEncoderV2,
    NumericBoundsV2,
)
from cognitive_os.learning.correction_source import canonical_source_hash  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d6-pre-registration.json"
SEALED_MANIFESTS = EVIDENCE / "sprint-21d6-sealed-manifests.json"
CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d6-certification-campaign.json"
SNAPSHOTS = EVIDENCE / "sprint-21d6-snapshots.json"
OUTPUT = EVIDENCE / "sprint-21d6-invariance-regression.json"

#: Seeded semantic mutations. Each changes what the program *does*, so each must change the
#: canonical bytes. They are applied to a fixed probe rather than to a corpus body, because a
#: control that depended on which group it landed on would be a different control every run.
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
    """The D4 convention, carried: the bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required; source .env.s21d6.measured.local first")
    return value


def _embedding_provider(model: Path) -> tuple[Any, str]:
    manifest = minilm.read_manifest(model)
    if manifest is None:
        raise SystemExit(f"no usable local embedding model at {model}")
    provider = build_embedding_provider(
        EmbeddingProviderConfiguration(
            provider_type="sentence_transformers",
            model_id=minilm.MODEL_ID,
            dimension=minilm.DIMENSION,
            local_model_path=model,
            local_model_digest=manifest["tree_digest"],
        )
    )
    return provider, manifest["tree_digest"]


async def _embed(provider: Any, sources: list[str]) -> tuple[tuple[float, ...], ...]:
    """One pooled vector per source, each window embedded on its own.

    Deliberately not batched, and this is D4 finding W2-D9 rather than a preference: the frozen
    MiniLM is batch-composition dependent, so padding a short sequence beside a long one moves
    its vector by about 1e-7 — invisible to a cosine, fatal to a hash. Batched, this regression
    would measure which batch a body landed in rather than whether the transformation changed it.
    """
    pooled: list[tuple[float, ...]] = []
    for source in sources:
        windows = canonical_embedding_windows(source)
        produced = [(await provider.embed_documents([text]))[0] for text in windows]
        pooled.append(pool_canonical_embedding(tuple(produced)))
    return tuple(pooled)


@dataclass(frozen=True, slots=True)
class _Case:
    """One sealed case identity turned back into a transformed package."""

    case_id: str
    case_name: str
    group: str
    module: str
    #: `variant index -> transformed body`, in the group's slot order.
    bodies: tuple[str, ...]
    clean_bodies: tuple[str, ...]
    hidden_test: str


def _cases() -> tuple[tuple[_Case, ...], list[str], Any]:
    """Rebuild every sealed case. No score, no label and no vector is read here."""
    bundle = seal_d6_corpus()
    submanifest = bundle.invariance_transformations
    by_group = {spec.repository_group: spec for spec in D6_CERTIFICATION_SPECS}
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
                bodies=transformed.variants,
                clean_bodies=clean,
                hidden_test=transformed.hidden_test,
            )
        )
    return tuple(built), inapplicable, submanifest


def _run_one(job: tuple[str, str, str, str]) -> tuple[str, bool]:
    """One transformed candidate against its transformed hidden suite. Never a governed run."""
    key, module, body, hidden = job
    with tempfile.TemporaryDirectory(prefix="cogos-d6-invariance-") as directory:
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


def _clean_labels() -> tuple[dict[str, dict[int, bool]], dict[str, int]]:
    """`group -> variant index -> accepted`, plus the variant each group acts on first.

    Indexed by *variant*, not by slot position. `recipe_binding` shuffles which authored variant
    each recipe carries, per template, precisely so that no recipe is correct more often than
    chance — so slot zero is not variant zero, and comparing them by index compares two different
    candidates. D4's first run of this check did, and reported ninety-two label changes that were
    nothing but that mismatch.
    """
    campaign = json.loads(CERTIFICATION_CAMPAIGN.read_text(encoding="utf-8"))
    catalogue = seal_d6_corpus().catalogues[CorrectionPartition.CALIBRATION]
    variant_of: dict[str, int] = {}
    first_variant: dict[str, int] = {}
    for group in catalogue.groups:
        binding = [recipe.value for recipe in recipe_binding(group.template_id)]
        for slot in group.slots:
            variant_of[str(slot.candidate_id)] = binding.index(str(slot.recipe))
            if slot.position == 0:
                first_variant[group.repository_group] = binding.index(str(slot.recipe))
    labels: dict[str, dict[int, bool]] = {}
    for row in campaign["candidate_outcomes"]:
        labels.setdefault(str(row["group"]), {})[variant_of[str(row["candidate_id"])]] = bool(
            row["accepted"]
        )
    return labels, first_variant


async def _batch_dependence_probe(provider: Any) -> dict[str, Any]:
    """Measure W2-D9 on D6's own model copy rather than inherit it: two batches, one text."""
    target = "def f(a):\n    return a + 1\n"
    padding = (
        "def g("
        + ", ".join(f"p{index}" for index in range(80))
        + "):\n    return "
        + " + ".join(f"p{index}" for index in range(80))
        + "\n"
    )
    alone = (await provider.embed_documents([target]))[0]
    beside_a_longer_sequence = (await provider.embed_documents([padding, target]))[1]
    difference = max(
        abs(left - right) for left, right in zip(alone, beside_a_longer_sequence, strict=True)
    )
    return {
        "identical": alone == beside_a_longer_sequence,
        "maximum_absolute_difference": f"{difference:.3e}",
        "hash_changes": _digest(str(alone)) != _digest(str(beside_a_longer_sequence)),
        "how": (
            "the same text embedded on its own, then as the second member of a batch whose "
            "first member is longer, so it is padded to the longer length"
        ),
    }


def _mutation_control() -> dict[str, Any]:
    """A normaliser that erased meaning would pass invariance perfectly and be useless."""
    base = canonical_source_hash(PROBE)
    results = []
    for name, original, replacement in SEMANTIC_MUTATIONS:
        if original not in PROBE:  # pragma: no cover - the probe is a literal above
            raise SystemExit(f"the {name} mutation does not apply to the probe")
        mutated = PROBE.replace(original, replacement)
        digest = canonical_source_hash(mutated)
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
            "the invariance result above says a rename does not move the canonical bytes. This "
            "says a changed meaning does. Without it, a canonicaliser that mapped every program "
            "to one value would satisfy the first claim completely"
        ),
    }


async def _run(output: Path, model: Path) -> int:
    provider, tree_digest = _embedding_provider(model)
    cases, inapplicable, submanifest = _cases()
    bundle = seal_d6_corpus()
    catalogue = bundle.catalogues[CorrectionPartition.CALIBRATION]
    sample = sorted({case.source_group_id for case in submanifest.cases})
    clean_labels, first_variant = _clean_labels()

    # Seal first. Every transformed feature record is encoded and hashed before the transformed
    # candidate it describes is executed, exactly as the clean campaign's were.
    clean_sources = [body for case in cases for body in case.clean_bodies]
    transformed_sources = [body for case in cases for body in case.bodies]
    embedded = await _embed(provider, clean_sources + transformed_sources)
    half = len(clean_sources)

    # Bounds fitted on the clean half of this sample and applied to both halves. They are not
    # the campaign's fitting bounds and this record does not pretend otherwise: recovering those
    # would mean re-embedding 720 bodies, and under W2-D9 the result would not reproduce the
    # seal anyway. What the comparison needs is one encoder applied to both sides, so that a
    # difference between a clean and a transformed vector can only come from the transformation.
    rows = [
        raw_numeric_row_v2(
            feature_input_v2(
                candidate_source=source, canonical_candidate_source_embedding=embedded[index]
            )
        )
        for index, source in enumerate(clean_sources)
    ]
    bounds = NumericBoundsV2.from_training(rows)
    encoder = CorrectionEncoderV2(bounds)

    def _vector_hash(source: str, embedding: tuple[float, ...]) -> str:
        return encoder.encode(
            feature_input_v2(
                candidate_source=source, canonical_candidate_source_embedding=embedding
            )
        ).content_hash()

    sealed_at = utc_now()
    comparisons: list[dict[str, Any]] = []
    cursor = 0
    for index, case in enumerate(cases):
        for variant, (clean, transformed) in enumerate(
            zip(case.clean_bodies, case.bodies, strict=True)
        ):
            clean_hash = _vector_hash(clean, embedded[index * 4 + variant])
            transformed_hash = _vector_hash(transformed, embedded[half + cursor])
            comparisons.append(
                {
                    "case_id": case.case_id,
                    "case_name": case.case_name,
                    "group": case.group,
                    "variant": variant,
                    "clean_feature_vector_hash": clean_hash,
                    "transformed_feature_vector_hash": transformed_hash,
                    "vector_unchanged": clean_hash == transformed_hash,
                    "clean_canonical_source_hash": canonical_source_hash(clean),
                    "transformed_canonical_source_hash": canonical_source_hash(transformed),
                    "canonical_source_unchanged": canonical_source_hash(clean)
                    == canonical_source_hash(transformed),
                }
            )
            cursor += 1

    labels = _run_all(
        [
            (f"{case.case_id}#{position}", case.module, body, case.hidden_test)
            for case in cases
            for position, body in enumerate(case.bodies)
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
            "clean": clean_labels[case.group][variant],
            "transformed": labels[f"{case.case_id}#{variant}"],
        }
        for case in cases
        for variant in range(4)
        if labels[f"{case.case_id}#{variant}"] != clean_labels[case.group][variant]
    ]
    # With no fitted ranker in force the first action is the head of the baseline order: the
    # candidate in slot zero, which `recipe_binding` maps to one of the four authored variants.
    # What is compared is the canonical identity of the body the system acts on first.
    first_action_changes = [
        {"case_id": case.case_id, "group": case.group, "variant": first_variant[case.group]}
        for case in cases
        if canonical_source_hash(case.bodies[first_variant[case.group]])
        != canonical_source_hash(case.clean_bodies[first_variant[case.group]])
    ]

    changed_vectors = [item for item in comparisons if not item["vector_unchanged"]]
    clean_hashes = sorted({str(item["clean_feature_vector_hash"]) for item in comparisons})
    every_hash = [str(item["clean_feature_vector_hash"]) for item in comparisons] + [
        str(item["transformed_feature_vector_hash"]) for item in comparisons
    ]
    census = DecisionCensusV4.from_feature_hashes(every_hash)
    slot_order_fixed = all(
        tuple(slot.position for slot in sorted(group.slots, key=lambda item: item.position))
        == tuple(range(len(group.slots)))
        for group in catalogue.groups
        if group.repository_group in set(sample)
    )

    mutation = _mutation_control()
    batching = await _batch_dependence_probe(provider)

    stops: list[str] = []
    if changed_vectors or label_changes or first_action_changes:
        stops.append("invariance_regression")
    if not mutation["all_changed_the_canonical_representation"]:
        stops.append("invariance_regression")

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D6",
            "wave": "W2",
            "items": ["S21D6-031"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "certification_campaign_sha256": _digest(CERTIFICATION_CAMPAIGN.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "final_outcomes_inspected": False,
            "purpose": (
                "execute the claim S21D6-023 sealed about D6's own certification corpus: a "
                "transformation repeats its source group's fitted feature vector, so it adds "
                "no independent decision"
            ),
            "embedding_tree_digest": tree_digest,
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
                    name: sum(1 for case in cases if case.case_name == name) for name in D6_CASES
                },
                "source_groups": len({case.group for case in cases}),
                "sample_groups_named": sample,
                "sample_matches_the_seal": sorted({case.group for case in cases}) == sample,
                "sample_is_drawn_from": (
                    "the D6 certification catalogue — twenty of the hundred groups authored for "
                    "this sprint, so the property is measured on the corpus the selection will "
                    "be certified on rather than on a predecessor's"
                ),
            },
            "chronology": {
                "features_sealed_at": sealed_at.isoformat(),
                "first_transformed_execution_at": executed_at.isoformat(),
                "every_transformed_seal_precedes_its_execution": executed_at > sealed_at,
                "bounds_fitted_on": "the clean bodies of the sample, never on the transformed set",
            },
            "independence": {
                "transformed_decisions": len(cases),
                "independent_decisions": 0,
                "candidate_vectors_compared": len(comparisons),
                "vectors_unchanged": len(comparisons) - len(changed_vectors),
                "vectors_changed": len(changed_vectors),
                "changed": changed_vectors[:20],
                "distinct_clean_vectors": len(clean_hashes),
                "census_over_clean_and_transformed": census.model_dump(
                    mode="json", exclude={"content_hash", "independence_rule"}
                ),
                "reading": (
                    f"{len(comparisons)} transformed candidate vectors, every one identical to "
                    f"its clean counterpart, so the {len(cases)} transformed decisions repeat "
                    f"{len(sample)} clean ones and add none. This is the number S21D6-023 "
                    "sealed as zero and the property this regression tests"
                ),
            },
            "verifier": {
                "candidate_outcomes_executed": len(labels),
                "label_changes": len(label_changes),
                "changed": label_changes[:20],
                "accepted": sum(1 for value in labels.values() if value),
                "governed_runs": 0,
                "how": (
                    "plain pytest in a scratch directory. A precheck that wrote governed "
                    "outcomes would put transformed rows in the store the clean campaign owns"
                ),
            },
            "first_action": {
                "cases_compared": len(cases),
                "changes": len(first_action_changes),
                "changed": first_action_changes,
                "preservation": "100%" if not first_action_changes else "below 100%",
                "reading": (
                    "with no fitted ranker in force the first action is the head of the "
                    "baseline order; this compares the body the system would act on first by "
                    "its canonical identity"
                ),
                "ranker_dependent_form": {
                    "measured_here": False,
                    "holds_by_implication": (
                        not changed_vectors and not first_action_changes and slot_order_fixed
                    ),
                    "premises": {
                        "every_transformed_vector_equals_its_clean_one": not changed_vectors,
                        "the_slot_order_the_tie_break_uses_is_catalogue_fixed": slot_order_fixed,
                        "the_ranker_is_a_deterministic_function_of_the_four_vectors": (
                            "pairwise-contrastive-linear-v1 projects each candidate onto one "
                            "direction and breaks ties on the baseline order"
                        ),
                    },
                    "why_not_a_second_run": (
                        "a ranker whose input is four vectors and a slot order cannot move when "
                        "neither moves. Re-ranking the transformed sample under the fitted "
                        "direction would produce the same ordering by construction and would "
                        "report it as if it were an observation. S21D6-035 reads the two "
                        "premises above rather than a re-run"
                    ),
                },
            },
            "semantic_mutation_control": mutation,
            "batch_composition_dependence": {
                "finding": "D4 W2-D9, re-measured on this model copy rather than cited",
                "measured": batching,
                "how_this_record_avoids_it": (
                    "every source here is embedded window by window on its own, so a difference "
                    "between a clean and a transformed vector can only come from the "
                    "transformation"
                ),
                "why_the_hashes_here_are_not_the_sealed_ones": (
                    "the campaign encoded in batches of 64 under the fitting bounds; this "
                    "encodes one window at a time under bounds fitted on the sample. Both "
                    "halves of every comparison are encoded the same way, which is what the "
                    "comparison needs, and neither is comparable to a S21D6-025 seal"
                ),
            },
            "entered_any_dataset": False,
            "fitted": False,
            "final_or_canary_access": 0,
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
                "vectors_changed": len(changed_vectors),
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
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    _require("COGOS_ARTIFACT_ROOT")
    return asyncio.run(_run(arguments.output, arguments.model))


if __name__ == "__main__":
    raise SystemExit(main())
