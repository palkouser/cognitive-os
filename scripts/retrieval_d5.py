#!/usr/bin/env python3
"""S21D5-021: execute the D5 retrieval pool and prove its queries will qualify.

A retrieval group is lighter than a calibration group -- one defect and its repair, not four
candidates around two independent edge cases -- so it has fewer ways to be wrong and one that
the calibration corpus does not have at all.

- *The pair is not causal.* The failed body must fail the hidden suite and the repair must pass
  it. Declared, that is a claim about two files; executed, it is evidence.
- *A side has no searchable surface.* This is the S21D4 residual, and the reason the D4 pool
  reached 41 of 60: ten repairs were pure arithmetic over their own parameters, the normaliser
  left nothing of them, and an empty document cannot be found by any arm. `structure_fallback`
  answers that, and the only way to know it answered is to project both sides here.
- *The two sides carry the same surface.* A pair whose failed and repaired documents are
  identical is worse than an empty one: it is retrievable and uninformative, and it drags MRR
  down while looking healthy. Nothing in D4 measured this per pair.
- *A term spells the relevance label.* `search_terms_from_source` fails closed on that by
  design; this reports which group tripped it rather than letting the traceback stand in.

Query qualification is S21D1's rule, unchanged: a query is judged by task family, and it
qualifies only when its family holds at least one *other* group to be relevant. Ten groups per
family clears that with room, and the count is reported rather than assumed.

Separation follows S21D4-043's rule and its scope, unchanged: the released detector over the
retrieval bodies, and a **cross-group** collision inside the pool is what has to be zero, because
that is two queries whose answers are the same code and no ranking can decide between them. A
retrieval body coinciding with a *calibration* body is a different thing and not forbidden by any
contract: the two never answer the same question, sit in different roles and reach different
stores. Widening the rule to cover them would be inventing an obligation mid-sprint, so those
coincidences are counted and reported beside the result rather than folded into it or dropped.

    UV_CACHE_DIR=.cache/uv uv run python scripts/retrieval_d5.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/retrieval_d5.py --groups d5r-boundary-...
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_leakage import near_clone_pairs  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d3 import D3RetrievalSpec  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d5 import D5_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d2 import (  # noqa: E402
    D2_TASK_SPECS,
    module_source,
)
from cognitive_os.coding.reality_task_specs_d3 import D3_TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d5 import D5_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.experience.graph_projection import search_terms_from_source  # noqa: E402

#: The four-candidate corpora the observation compares against, and their body names.
TASK_SPECS_ALL = (*D2_TASK_SPECS, *D3_TASK_SPECS, *D4_CALIBRATION_SPECS)
CALIBRATION_LABELS = ("baseline", "variant_one", "variant_two", "variant_three", "variant_four")

#: The pool target and the query floor, both from the frozen retrieval contract (S21D5-014).
#: Sixty is authored against a floor of fifty so one withdrawal is not a sprint arithmetic
#: failure.
POOL_TARGET = 60
MINIMUM_QUERIES = 50

#: What the pair contract says each side must do against the hidden suite.
EXPECTED = {"failed": False, "repaired": True}


def _pytest(root: Path) -> bool:
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_suite.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def _job(job: tuple[str, str, str, str, str]) -> tuple[str, str, bool]:
    group, side, module, body, suite = job
    with tempfile.TemporaryDirectory(prefix="cogos-d5-retrieval-") as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(body, encoding="utf-8")
        (root / "test_suite.py").write_text(suite, encoding="utf-8")
        return group, side, _pytest(root)


def _execute(specs: tuple[D3RetrievalSpec, ...]) -> dict[str, Any]:
    jobs = [
        (
            spec.repository_group,
            side,
            spec.module,
            spec.module_text(getattr(spec, side)),
            spec.hidden_test,
        )
        for spec in specs
        for side in EXPECTED
    ]
    observed: dict[str, dict[str, bool]] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for group, side, passed in pool.map(_job, jobs):
            observed.setdefault(group, {})[side] = passed

    defects = []
    for spec in specs:
        for side, expected in EXPECTED.items():
            actual = observed[spec.repository_group][side]
            if actual != expected:
                defects.append(
                    {
                        "group": spec.repository_group,
                        "side": side,
                        "expected": "passes" if expected else "fails",
                        "observed": "passes" if actual else "fails",
                        "reading": (
                            "the repair does not satisfy the contract it is the repair for"
                            if side == "repaired"
                            else "the defect is not a defect: the hidden suite accepts it, so "
                            "the pair is not causal evidence of anything"
                        ),
                    }
                )
    return {
        "groups_executed": len(specs),
        "bodies_executed": len(jobs),
        "pair_defects": defects,
        "every_pair_is_causal": not defects,
    }


def _labels(spec: D3RetrievalSpec) -> tuple[str, ...]:
    """What relevance is judged by, in every spelling a term could carry it. S21D4-043's rule."""
    return (spec.family.value, spec.family.value.replace("_", " "), spec.repository_group)


def _surface(specs: tuple[D3RetrievalSpec, ...]) -> dict[str, Any]:
    """Project both sides under the contracted surface and read what an arm would see."""
    empty: list[dict[str, str]] = []
    identical: list[dict[str, str]] = []
    leaking: list[dict[str, str]] = []
    fell_back = 0
    for spec in specs:
        terms: dict[str, tuple[str, ...]] = {}
        for side in ("failed", "repaired"):
            source = spec.module_text(getattr(spec, side))
            try:
                bare = search_terms_from_source(source, judgement_labels=_labels(spec))
                complete = search_terms_from_source(
                    source, judgement_labels=_labels(spec), structure_fallback=True
                )
            except ValueError as error:
                leaking.append({"group": spec.repository_group, "side": side, "why": str(error)})
                continue
            if not bare:
                fell_back += 1
            if not complete:
                empty.append({"group": spec.repository_group, "side": side})
            terms[side] = complete
        if len(terms) == 2 and terms["failed"] == terms["repaired"]:
            identical.append(
                {
                    "group": spec.repository_group,
                    "why": (
                        "both sides project the same document, so the pair is retrievable and "
                        "uninformative -- it cannot tell an arm which side it found"
                    ),
                }
            )
    return {
        "sides_projected": len(specs) * 2,
        "sides_needing_the_structure_fallback": fell_back,
        "sides_with_no_terms_at_all": empty,
        "pairs_whose_two_sides_project_the_same_document": identical,
        "groups_leaking_their_relevance_label": leaking,
        "surface_is_usable": not empty and not identical and not leaking,
    }


def _separation() -> dict[str, Any]:
    """S21D4-043's rule at S21D4-043's scope, plus the cross-role count it does not ask for."""
    bodies = {
        f"{spec.repository_group}:{side}": spec.module_text(getattr(spec, side))
        for spec in D5_RETRIEVAL_SPECS
        for side in ("failed", "repaired")
    }
    collisions = sorted(
        f"{pair.left}|{pair.right}|{pair.reason}"
        for pair in near_clone_pairs(bodies)
        if pair.left.split(":")[0] != pair.right.split(":")[0]
    )

    # Not a gate. The small-function space the programme has already occupied is finite, and a
    # two-line retrieval body landing on a calibration body is evidence of that saturation
    # rather than of a leak. Counted so the reader can see the size of it.
    elsewhere = {
        f"{spec.repository_group}:{label}": module_source(spec, getattr(spec, label))
        for spec in (*TASK_SPECS_ALL, *D5_CALIBRATION_SPECS)
        for label in CALIBRATION_LABELS
        if getattr(spec, label, None)
    }
    across = sorted(
        f"{pair.left}|{pair.right}|{pair.reason}"
        for pair in near_clone_pairs({**bodies, **elsewhere})
        if pair.left.split(":")[0] != pair.right.split(":")[0]
        and (pair.left in bodies) != (pair.right in bodies)
    )
    return {
        "scope": "S21D4-043: cross-group pairs inside the retrieval pool",
        "retrieval_bodies_compared": len(bodies),
        "cross_group_collisions_inside_the_pool": collisions,
        "separated": not collisions,
        "observation_only_coincidences_with_a_correction_body": len(across),
        "observation_reading": (
            "not a gate and not forbidden by any contract: a retrieval body and a correction "
            "body never answer the same question. Reported because it measures how much of the "
            "small-function space the programme has already spent"
        ),
    }


def _qualification() -> dict[str, Any]:
    """A query is relevant by task family, so it qualifies only with a peer in that family."""
    by_family: dict[str, list[str]] = {}
    for spec in D5_RETRIEVAL_SPECS:
        by_family.setdefault(spec.family.value, []).append(spec.repository_group)
    qualifying = [
        spec.repository_group
        for spec in D5_RETRIEVAL_SPECS
        if len(by_family[spec.family.value]) > 1
    ]
    return {
        "families": {family: len(groups) for family, groups in sorted(by_family.items())},
        "queries_that_would_qualify": len(qualifying),
        "minimum_queries": MINIMUM_QUERIES,
        "minimum_queries_met": len(qualifying) >= MINIMUM_QUERIES,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", nargs="*", default=[])
    arguments = parser.parse_args()
    wanted = tuple(arguments.groups)
    selected = tuple(
        spec for spec in D5_RETRIEVAL_SPECS if not wanted or spec.repository_group in wanted
    )

    execution = _execute(selected)
    surface = _surface(selected)
    separation = _separation()
    qualification = _qualification()
    report = {
        "sprint": "21D5",
        "items": ["S21D5-021"],
        "retrieval_groups_authored": len(D5_RETRIEVAL_SPECS),
        "pool_target": POOL_TARGET,
        "shortfall": POOL_TARGET - len(D5_RETRIEVAL_SPECS),
        "execution": execution,
        "surface": surface,
        "qualification": qualification,
        "separation": separation,
        "ready": (
            execution["every_pair_is_causal"]
            and surface["surface_is_usable"]
            and separation["separated"]
            and qualification["minimum_queries_met"]
        ),
    }
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
