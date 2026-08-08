#!/usr/bin/env python3
"""S21D5-020 through S21D5-022: execute the D5 corpora and prove they are separated.

The authoring contract is only satisfied by *running* every body against both suites, so this
is the tool the corpus is authored against rather than a report written after it. Three
failure modes are invisible without it, and each one shows up as a specific row here:

- two hidden tests probing one defect -> `variant_three` and `variant_four` both pass hidden;
- a baseline broken past its own visible suite -> `baseline` fails visible;
- a near-clone collision -> a cross-group pair in `collisions`.

Nothing here reads an outcome, a candidate score or a verifier label from any D5 role. The runs
are throwaway fixture validation in a temporary directory, exactly as §0.3 permits for corpus
authoring: they never reach the Event Store, the Artifact Store, a learned observation or a
metric.

    UV_CACHE_DIR=.cache/uv uv run python scripts/corpus_d5.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/corpus_d5.py --groups d5-boundary-column-widths

`--groups` narrows execution to named groups, which is what makes per-batch authoring
affordable; separation is always computed over the whole corpus, because a collision is a
property of a pair and a batch cannot see the pair it collides with.
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
from cognitive_os.coding.reality_retrieval_specs_d3 import D3_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d4 import D4_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs import TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d2 import (  # noqa: E402
    D2_TASK_SPECS,
    module_source,
)
from cognitive_os.coding.reality_task_specs_d3 import D3_TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d5 import D5_CALIBRATION_SPECS  # noqa: E402

#: What the corpus contract says each body must do against each suite. A body that disagrees is
#: an authoring defect, and the run is what decides which of the two it is.
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

LABELS = ("baseline", "variant_one", "variant_two", "variant_three", "variant_four")

#: The corpus target. Reported beside the achieved count so a shortfall is a number rather than
#: an impression; §6.2 forbids meeting it by lowering a floor.
CALIBRATION_TARGET = 100


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
    group, label, module, body, suite_name, suite = job
    with tempfile.TemporaryDirectory(prefix="cogos-d5-authoring-") as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(body, encoding="utf-8")
        (root / "test_suite.py").write_text(suite, encoding="utf-8")
        return group, label, suite_name, _pytest(root, "test_suite.py")


def _execute(groups: tuple[str, ...]) -> dict[str, Any]:
    selected = [
        spec for spec in D5_CALIBRATION_SPECS if not groups or spec.repository_group in groups
    ]
    jobs: list[tuple[str, str, str, str, str, str]] = []
    for spec in selected:
        for label in LABELS:
            text = module_source(spec, getattr(spec, label))
            jobs.append(
                (spec.repository_group, label, spec.module, text, "visible", spec.visible_test)
            )
            jobs.append(
                (spec.repository_group, label, spec.module, text, "hidden", spec.hidden_test)
            )

    observed: dict[str, dict[str, bool]] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for group, label, suite_name, passed in pool.map(_job, jobs):
            observed.setdefault(group, {})[f"{label}:{suite_name}"] = passed

    defects = []
    for spec in selected:
        for (label, suite_name), expected in EXPECTED.items():
            actual = observed[spec.repository_group][f"{label}:{suite_name}"]
            if actual != expected:
                defects.append(
                    {
                        "group": spec.repository_group,
                        "body": label,
                        "suite": suite_name,
                        "expected": "passes" if expected else "fails",
                        "observed": "passes" if actual else "fails",
                        "reading": _reading(label, suite_name, actual),
                    }
                )
    return {
        "groups_executed": len(selected),
        "bodies_executed": len(selected) * len(LABELS),
        "suite_runs": len(jobs),
        "contract_defects": defects,
        "every_body_matches_the_contract": not defects,
    }


def _reading(label: str, suite: str, actual: bool) -> str:
    """Name the failure mode rather than restating the row."""
    if label == "baseline" and suite == "visible" and not actual:
        return (
            "failure mode 2: the baseline is broken past its own visible suite, so the defect "
            "is not peripheral enough for the ordinary case to work"
        )
    if label in {"variant_three", "variant_four"} and suite == "hidden" and actual:
        return (
            "failure mode 1: a partial fix passes the hidden suite, so the two hidden tests are "
            "probing one defect wearing two descriptions. Re-author around genuinely "
            "independent defects rather than weakening a test"
        )
    if label in {"variant_one", "variant_two"} and suite == "hidden" and not actual:
        return "a declared full repair does not repair the contract"
    if suite == "visible" and not actual:
        return "the visible suite separates candidates it must not separate"
    return "the body does not do what the contract declares"


def _c3_module_source(spec: Any, body: str) -> str:
    """A C3 body as a module. `module_source` is typed against a D2 spec and a C3 one only
    satisfies it by duck typing, which type-checks by accident at best."""
    header = f'"""{spec.module_doc}"""\n'
    if spec.imports:
        header += f"\n{spec.imports}\n"
    return f"{header}\n\n{body.strip()}\n"


def _sources() -> dict[str, str]:
    """Every released and D5 body, keyed by group and label, for cross-group collision."""
    out: dict[str, str] = {}
    released = (
        *D2_TASK_SPECS,
        *D3_TASK_SPECS,
        *D4_CALIBRATION_SPECS,
        *D3_RETRIEVAL_SPECS,
        *D4_RETRIEVAL_SPECS,
    )
    for spec in released:
        for label in LABELS:
            body = getattr(spec, label, None)
            if body:
                out[f"{spec.repository_group}:{label}"] = module_source(spec, body)
    # C3 specs name their four bodies differently from D2's; the labels are the shape, not a
    # detail, so they are read by their own names rather than through a rename table.
    for spec in TASK_SPECS:
        for label in (
            "baseline",
            "incomplete_a",
            "incomplete_b",
            "correct_narrow",
            "correct_robust",
        ):
            out[f"{spec.repository_group}:{label}"] = _c3_module_source(spec, getattr(spec, label))
    for spec in D5_CALIBRATION_SPECS:
        for label in LABELS:
            out[f"{spec.repository_group}:{label}"] = module_source(spec, getattr(spec, label))
    return out


def _separation() -> dict[str, Any]:
    """Cross-group collisions only. Within one group the four candidates are near-clones by
    design, and a detector scoped to include them would report the corpus as broken for
    obeying its own contract."""
    sources = _sources()
    pairs = near_clone_pairs(sources)
    d5_groups = {spec.repository_group for spec in D5_CALIBRATION_SPECS}
    collisions = []
    for pair in pairs:
        left_group = pair.left.split(":", 1)[0]
        right_group = pair.right.split(":", 1)[0]
        if left_group == right_group:
            continue
        if left_group not in d5_groups and right_group not in d5_groups:
            continue
        collisions.append({"left": pair.left, "right": pair.right, "reason": pair.reason})
    return {
        "bodies_compared": len(sources),
        "d5_groups": len(d5_groups),
        "cross_group_collisions_touching_21d5": collisions,
        "separated": not collisions,
    }


def _families() -> dict[str, int]:
    counts: dict[str, int] = {}
    for spec in D5_CALIBRATION_SPECS:
        counts[spec.family.value] = counts.get(spec.family.value, 0) + 1
    return dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", nargs="*", default=[])
    arguments = parser.parse_args()

    execution = _execute(tuple(arguments.groups))
    separation = _separation()
    report = {
        "sprint": "21D5",
        "items": ["S21D5-020", "S21D5-022"],
        "calibration_groups_authored": len(D5_CALIBRATION_SPECS),
        "calibration_target": CALIBRATION_TARGET,
        "shortfall": CALIBRATION_TARGET - len(D5_CALIBRATION_SPECS),
        "families": _families(),
        "execution": execution,
        "separation": separation,
        "ready": execution["every_body_matches_the_contract"] and separation["separated"],
    }
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
