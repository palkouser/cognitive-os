#!/usr/bin/env python3
"""S21D7-020 and S21D7-022: execute the D7 certification corpus and prove it is separated.

The authoring contract is only satisfied by *running* every body against both suites, so this
is the tool the corpus is authored against rather than a report written after it. Three
failure modes are invisible without it, and each one shows up as a specific row here:

- two hidden tests probing one defect -> `variant_three` and `variant_four` both pass hidden;
- a baseline broken past its own visible suite -> `baseline` fails visible;
- a near-clone collision -> a cross-group pair in `collisions`.

Nothing here reads an outcome, a candidate score or a verifier label from any D5, D6 or D7
role.
The runs are throwaway fixture validation in a temporary directory, exactly as §0.3 permits for
corpus authoring: they never reach the Event Store, the Artifact Store, a learned observation or
a metric. In particular this tool never reads a conformal margin: the bar belongs to W2.

    UV_CACHE_DIR=.cache/uv uv run python scripts/corpus_d7.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/corpus_d7.py --groups d7-boundary-run-bounds

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
from cognitive_os.coding.reality_retrieval_specs_d5 import D5_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs import TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d2 import (  # noqa: E402
    D2_TASK_SPECS,
    module_source,
)
from cognitive_os.coding.reality_task_specs_d3 import D3_TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d5 import D5_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d6 import D6_CERTIFICATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d7 import D7_CERTIFICATION_SPECS  # noqa: E402
from cognitive_os.learning.correction_source import (  # noqa: E402
    SourceNormalizationError,
    canonical_source_bytes,
)

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
CERTIFICATION_TARGET = 100


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
    with tempfile.TemporaryDirectory(prefix="cogos-d7-authoring-") as directory:
        root = Path(directory)
        (root / f"{module}.py").write_text(body, encoding="utf-8")
        (root / "test_suite.py").write_text(suite, encoding="utf-8")
        return group, label, suite_name, _pytest(root, "test_suite.py")


def _execute(groups: tuple[str, ...]) -> dict[str, Any]:
    selected = [
        spec for spec in D7_CERTIFICATION_SPECS if not groups or spec.repository_group in groups
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
    # The retrieval pools are deliberately absent from this tuple. They used to sit in it and
    # contribute nothing, because a retrieval spec names its two bodies `failed` and `repaired`
    # and this loop reads D2's five labels, so every retrieval body was skipped in silence. The
    # exclusion below is the one S21D4-043 intends; leaving the specs in a list that cannot read
    # them made an intended scope look like an oversight, which is worse than either.
    released = (
        *D2_TASK_SPECS,
        *D3_TASK_SPECS,
        *D4_CALIBRATION_SPECS,
        *D5_CALIBRATION_SPECS,
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
    # D6's released certification corpus joins the released set: it is the bar-setting half, so
    # a D7 body colliding with one of its bodies is a collision across the one boundary the
    # experiment rests on.
    for spec in (*D6_CERTIFICATION_SPECS, *D7_CERTIFICATION_SPECS):
        for label in LABELS:
            out[f"{spec.repository_group}:{label}"] = module_source(spec, getattr(spec, label))
    # The retrieval pools are *not* read here. S21D4-043 scopes retrieval separation to the
    # retrieval pool against itself and says why in its own words: a cross-group collision
    # "would be two queries whose answers are the same code". A retrieval body coinciding with
    # a calibration body is not that -- the two never answer the same question, live in
    # different roles and reach different stores. `retrieval_d5.py` runs the released rule and
    # reports the cross-role coincidences beside it as an observation.
    return out


def _separation() -> dict[str, Any]:
    """Cross-group collisions only. Within one group the four candidates are near-clones by
    design, and a detector scoped to include them would report the corpus as broken for
    obeying its own contract."""
    sources = _sources()
    pairs = near_clone_pairs(sources)
    d7_groups = {spec.repository_group for spec in D7_CERTIFICATION_SPECS}
    collisions = []
    for pair in pairs:
        left_group = pair.left.split(":", 1)[0]
        right_group = pair.right.split(":", 1)[0]
        if left_group == right_group:
            continue
        if left_group not in d7_groups and right_group not in d7_groups:
            continue
        collisions.append({"left": pair.left, "right": pair.right, "reason": pair.reason})
    # A group authored twice is not a near-clone pair: the second spec never reaches the
    # comparison at all, because the template registry is a mapping and the later spec simply
    # replaces the earlier one under the same key. The count above is the only trace it leaves,
    # so the names are reported rather than left to be read out of a discrepancy.
    reused = sorted(
        {
            spec.repository_group
            for spec in D7_CERTIFICATION_SPECS
            if sum(
                other.repository_group == spec.repository_group for other in D7_CERTIFICATION_SPECS
            )
            > 1
        }
    )
    return {
        "bodies_compared": len(sources),
        "d7_groups": len(d7_groups),
        "groups_authored_twice": reused,
        "cross_group_collisions_touching_21d7": collisions,
        "separated": not collisions and not reused,
    }


def _search(words: tuple[str, ...]) -> int:
    """The pre-check: does any released group already do this?

    Failure mode 3 is a collision at the level of the *task*, and rewriting a variant cannot
    repair it — the group is withdrawn and the authoring effort is lost. D4 discovered its
    collisions after writing the bodies. Asking first turns that rework into a lookup, and the
    question is answerable because every spec states its contract in prose it already carries.
    """
    released = (
        *TASK_SPECS,
        *D2_TASK_SPECS,
        *D3_TASK_SPECS,
        *D4_CALIBRATION_SPECS,
        *D3_RETRIEVAL_SPECS,
        *D4_RETRIEVAL_SPECS,
        # D5's own corpora count as occupied ground the moment they are authored: the retrieval
        # pool has to be disjoint from the calibration corpus, not only from the predecessors.
        *D5_CALIBRATION_SPECS,
        *D5_RETRIEVAL_SPECS,
        # D6's released corpus, and D7's own the moment a group of it is authored.
        *D6_CERTIFICATION_SPECS,
        *D7_CERTIFICATION_SPECS,
    )
    wanted = tuple(word.lower() for word in words)
    hits = []
    for spec in released:
        haystack = " ".join(
            (
                spec.module,
                spec.repository_group,
                spec.template_id,
                getattr(spec, "issue", ""),
                getattr(spec, "expected", ""),
            )
        ).lower()
        matched = [word for word in wanted if word in haystack]
        if matched:
            hits.append(
                {
                    "module": spec.module,
                    "group": spec.repository_group,
                    "matched": matched,
                    "expected": getattr(spec, "expected", "")[:160],
                }
            )
    hits.sort(key=lambda item: (-len(item["matched"]), item["module"]))
    # `closest` is ranked by how many of the searched words a group matched, which is the wrong
    # ranking for the question actually being asked. A word searched alongside seven others gets
    # one match each and sinks below the multi-word hits, so truncating the list can drop every
    # group that matched it and leave the word looking unoccupied. `by_word` is not truncated:
    # a word with hits must never be able to print as free, whatever else was searched with it.
    by_word = {
        word: sorted(hit["group"] for hit in hits if word in hit["matched"]) for word in wanted
    }
    print(
        json.dumps(
            {
                "searched": list(wanted),
                "released_groups": len(released),
                "hits": len(hits),
                "by_word": by_word,
                "closest": hits[:12],
                "reading": (
                    "a hit is not automatically a collision, but a hit whose 'expected' states "
                    "the same contract is one, and it is cheaper to read it now than to author "
                    "five bodies and withdraw them; a word whose 'by_word' list is empty is the "
                    "only kind of free, and 'closest' is a ranked sample rather than the answer"
                ),
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def _encodable() -> dict[str, Any]:
    """Every body must survive the v2 source normaliser, or no campaign can encode it.

    Added after S21D5-025 hit it on D5's eighty-first calibration group: `d5_error.short_circuit`
    reached variant two with a walrus in a comprehension. The body was correct Python, passed
    both suites by a materially different route, and was clone-clean — and the normaliser
    refuses assignment expressions, so the group could never have been sealed.

    Nothing before this asked the question. The five-body execution check runs pytest, which
    accepts every construct Python accepts; the near-clone detectors read the AST but do not
    normalise it. The first thing in the programme that reads a body through the encoder is the
    feature seal, which is two waves and one campaign after the body is authored.
    """
    refused: list[dict[str, str]] = []
    checked = 0
    for spec in D7_CERTIFICATION_SPECS:
        for label in LABELS:
            checked += 1
            try:
                canonical_source_bytes(module_source(spec, getattr(spec, label)))
            except SourceNormalizationError as error:
                refused.append({"group": spec.repository_group, "body": label, "error": str(error)})
    return {
        "bodies_checked": checked,
        "bodies_the_normaliser_refuses": refused,
        "every_body_can_be_encoded": not refused,
    }


def _families() -> dict[str, int]:
    counts: dict[str, int] = {}
    for spec in D7_CERTIFICATION_SPECS:
        counts[spec.family.value] = counts.get(spec.family.value, 0) + 1
    return dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", nargs="*", default=[])
    parser.add_argument(
        "--search",
        nargs="*",
        default=[],
        help="report released groups whose contract mentions these words, before authoring",
    )
    arguments = parser.parse_args()

    if arguments.search:
        return _search(tuple(arguments.search))

    execution = _execute(tuple(arguments.groups))
    separation = _separation()
    encodable = _encodable()
    report = {
        "sprint": "21D7",
        "items": ["S21D7-020", "S21D7-022"],
        "certification_groups_authored": len(D7_CERTIFICATION_SPECS),
        "calibration_target": CERTIFICATION_TARGET,
        "shortfall": CERTIFICATION_TARGET - len(D7_CERTIFICATION_SPECS),
        "families": _families(),
        "execution": execution,
        "encodability": encodable,
        "separation": separation,
        "ready": (
            execution["every_body_matches_the_contract"]
            and separation["separated"]
            and encodable["every_body_can_be_encoded"]
        ),
    }
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
