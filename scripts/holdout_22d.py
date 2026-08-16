"""S22D-020. The fresh declarative-fact holdout W1 is measured against, frozen unread.

§1.5 takes 22C's W3-F1 decision head-on: a pipeline whose verification floor is deterministic
kernels can retain exactly one kind of artifact, and a held-out task needs *declarative facts*
that no registered problem type can verify. The gate owner took the second of the three
options — a verification path for declarative facts that is not a kernel — and the plan is
explicit about why the work lands here rather than in a retrofit of 22C: **22C's holdout has
been read, once, to 0 of 4, and changing the acceptance path now so that the number improves
is post-hoc fitting.** So 22C releases as the typed negative it measured, and this is a new
holdout, frozen before W1 writes a line of the acceptance path, read exactly once at the end
of W1.

**Two arms, and W0 proves they differ without spending a case.** Arm A queries the acquired
layer as 22C left it — kernel-retained worked examples only, no declarative facts. Arm B
queries it after W1's path has run. If those two were not mechanically different, W1 would
discover it after building the whole path, which is exactly the trap 22C's pre-registration
avoided by running the mechanism on a probe case *deliberately outside the holdout set*. The
probe here does the same, so the holdout keeps `measured_values: 0` and the mechanism is
still known to work before a wave is paid for.

**Disjoint from the hundred, and asserted rather than intended.** Every fact this holdout
withholds is a fact the microbenchmark never asks about. A holdout that shared facts with the
frozen hundred would leak a W1 reading into a W3 measurement, and §2.3 forbids tuning
anything against the hundred.

    UV_CACHE_DIR=.cache/uv uv run python scripts/holdout_22d.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/holdout_22d.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from benchmark_22d import (  # noqa: E402
    GROUNDING_LADDER,
    SLICE_TIME,
    ArmOutcome,
    canonical,
    verify_answer,
)
from tasks_22d import CHEMISTRY, MICROBENCHMARK_TASKS, PHYSICS  # noqa: E402

OUTPUT = EVIDENCE / "sprint-22d-holdout.json"

HOLDOUT_ID = "sprint-22d-declarative-fact-holdout"

#: Read once, at the end of W1. §2.2 and §2.1: published with `measured_values: 0`.
SEEDS = (22_040, 22_041, 22_042)

#: The two arms, and what makes them different. Neither is a different *model* — both are the
#: same query path over the same store. The only difference is whether W1's acceptance path
#: has put declarative facts in it, which is the one thing this holdout is measuring.
ARM_A = "acquired layer as 22C left it — kernel-retained worked examples only"
ARM_B = "acquired layer after the §1.5 declarative-fact path"

#: A case is answerable when the layer carries the withheld fact at a status the ladder makes
#: retrievable, and the released registered verifier then decides the answer. A case the layer
#: cannot supply is a **refusal with a name**, never a value the provider supplied from its
#: own knowledge — 22C W3-D1, which is now a standing rule and applies with force to a
#: language model, since it will always produce something.
REFUSAL_REASON = "fact_not_in_acquired_layer"

#: Which §1.5 ladder rungs a retrieval may draw on, read off the ladder W0 froze rather than
#: restated here — a second copy of a frozen boundary is a boundary that can drift.
LADDER_RETRIEVABLE = tuple(str(rung["status"]) for rung in GROUNDING_LADDER if rung["retrievable"])

SUCCESS_DEFINITION = (
    "a case succeeds when the acquired layer supplies the withheld fact at a retrievable "
    "ladder status and the registered verifier named on the case returns a pass; a case the "
    "layer cannot supply is refused by name and counts as a failure, never as an answer"
)


#: **The expected answer is computed from the withheld fact, never typed beside it.**
#: Typing both is how `s22d-h-02` was authored with its tolerance in the expected-answer slot
#: — a defect that no decidability check catches, because a malformed expectation is still a
#: perfectly well-formed verifier configuration. Deriving one from the other removes the whole
#: error class rather than the one instance of it (22C's rule about fixing where all callers
#: route through).
def _case(
    case_id: str,
    prompt: str,
    withheld_fact: str,
    withheld_value: str,
    expected: float,
    tolerance: str,
    source: str,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "prompt": prompt,
        "withheld_fact": withheld_fact,
        "withheld_value": withheld_value,
        "verifier_id": "mathematics.numeric",
        "subject_type": "mathematical_expression",
        "verifier_configuration": {
            "expected": f"{expected:.6g}",
            "relative_tolerance": tolerance,
        },
        "grounding_source": source,
        "refusal_reason_when_absent": REFUSAL_REASON,
    }


#: **What each case needs, and how its answer is derived from it.** Added in W1, and it changes
#: no case: the frozen dicts and therefore `case_hashes()` are byte-identical, because a
#: derivation is code and the holdout's content is data.
#:
#: Reading the holdout without this would have to compare the layer's value against the value
#: the case withheld and call that a pass, which is circular — the expected answer was computed
#: *from* that value. With it, arm B derives the answer from whatever the acquired layer
#: actually holds and the case's own registered verifier decides it, which is the frozen
#: success definition read literally.
#:
#: Each entry is `(kind, operand, required_facts)`. `required_facts` is the honest part: a
#: molar mass needs every element in the compound, not only the one the case names as withheld
#: — which is the second half of W0-F4, and the reason a case can be refused for a fact its own
#: record never mentions.
DERIVATIONS: dict[str, tuple[str, float, tuple[tuple[str, int], ...]]] = {}


def _moles(case_id: str, mass: float, fact: str, value: float, source: str) -> dict[str, Any]:
    """How many moles are in `mass` grams — the derivation arm A cannot finish."""
    DERIVATIONS[case_id] = ("moles", mass, ((fact, 1),))
    return _case(
        case_id,
        f"How many moles are in {mass} grams of {fact.split()[-1]} atoms? "
        "Give three significant figures.",
        f"relative atomic mass of {fact.split()[-1]}",
        str(value),
        mass / value,
        "0.005",
        source,
    )


def _mass_of(case_id: str, moles: float, fact: str, value: float, source: str) -> dict[str, Any]:
    DERIVATIONS[case_id] = ("mass_of", moles, ((fact, 1),))
    return _case(
        case_id,
        f"What is the mass in grams of {moles} moles of {fact.split()[-1]} atoms? "
        "Give four significant figures.",
        f"relative atomic mass of {fact.split()[-1]}",
        str(value),
        moles * value,
        "0.002",
        source,
    )


def _molar_mass(
    case_id: str, compound: str, terms: tuple[tuple[int, str, float], ...], source: str
) -> dict[str, Any]:
    """A molar mass summed from its terms, so the sum cannot disagree with the arithmetic.

    Each term names its element, because the derivation needs *every* element in the compound
    and the case record names only the one it calls withheld. That gap is W0-F4's second half.
    """
    DERIVATIONS[case_id] = (
        "molar_mass",
        0.0,
        tuple((element, count) for count, element, _ in terms),
    )
    return _case(
        case_id,
        f"What is the molar mass of {compound} in grams per mole? Give four significant figures.",
        "relative atomic mass of hydrogen",
        "1.008",
        sum(count * value for count, _element, value in terms),
        "0.002",
        source,
    )


def _weight(case_id: str, prompt: str, mass: float, source: str) -> dict[str, Any]:
    DERIVATIONS[case_id] = ("weight", mass, (("standard gravitational field strength", 1),))
    return _case(
        case_id, prompt, "standard gravitational field strength", "9.8", mass * 9.8, "0.005", source
    )


#: Twelve cases. Each withholds exactly one declared fact and states everything else, which is
#: 22C's holdout shape: arm A refuses for want of the fact, arm B solves once the fact is
#: retained. None of these facts appears anywhere in the frozen hundred.
HOLDOUT_CASES = (
    _moles("s22d-h-01", 32.13, "sulfur", 32.06, CHEMISTRY),
    _moles("s22d-h-02", 80.16, "calcium", 40.08, CHEMISTRY),
    _mass_of("s22d-h-03", 3, "chlorine", 35.45, CHEMISTRY),
    _moles("s22d-h-04", 48.61, "magnesium", 24.305, CHEMISTRY),
    _mass_of("s22d-h-05", 0.5, "aluminium", 26.98, CHEMISTRY),
    _moles("s22d-h-06", 111.69, "iron", 55.845, CHEMISTRY),
    _mass_of("s22d-h-07", 1.5, "copper", 63.55, CHEMISTRY),
    # Hydrogen chloride and hydrogen sulfide rather than methane and ammonia: methane needs
    # carbon and ammonia needs nitrogen, and the frozen hundred asks for both of those
    # directly. Chlorine and sulfur are already this holdout's own, so these two cases lean on
    # no fact the hundred also uses — which is what §2.3's separation actually requires, and
    # what the disjointness check would not have caught on its own.
    _molar_mass(
        "s22d-h-08",
        "hydrogen chloride",
        ((1, "hydrogen", 1.008), (1, "chlorine", 35.45)),
        CHEMISTRY,
    ),
    _molar_mass(
        "s22d-h-09", "hydrogen sulfide", ((2, "hydrogen", 1.008), (1, "sulfur", 32.06)), CHEMISTRY
    ),
    _weight(
        "s22d-h-10",
        "A body of mass 8 kilograms is in free fall near the Earth's surface. What is the net "
        "force on it, in newtons?",
        8,
        PHYSICS,
    ),
    _weight(
        "s22d-h-11",
        "A crate of mass 45 kilograms rests on the ground near the Earth's surface. What normal "
        "force in newtons does the ground exert?",
        45,
        PHYSICS,
    ),
    _case(
        "s22d-h-12",
        "How much charge in coulombs is carried by one mole of electrons? Give four significant "
        "figures.",
        "Faraday constant",
        "96485",
        96485,
        "0.002",
        PHYSICS,
    ),
)

#: The Faraday case is a bare constant: the fact *is* the answer, so its derivation is the
#: identity and its required fact is itself.
DERIVATIONS["s22d-h-12"] = ("identity", 1.0, (("Faraday constant", 1),))

#: **The probe, and it is not a holdout case.** Same shape, different fact, run in W0 so the
#: two arms are known to be mechanically different before W1 spends a wave discovering it.
PROBE_CASE = _case(
    "s22d-probe-01",
    "How many moles are in 39.10 grams of a substance whose relative atomic mass is withheld?",
    "relative atomic mass of the probe substance",
    "39.10",
    39.10 / 39.10,
    "0.005",
    CHEMISTRY,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def case_hashes() -> dict[str, str]:
    return {str(case["case_id"]): _sha256(canonical(case)) for case in HOLDOUT_CASES}


async def _arm_mechanism_probe() -> dict[str, Any]:
    """Prove the arms differ — on a case that is not in the holdout.

    Arm A's layer holds no declarative facts, so the case is refused by name and nothing is
    answered. Arm B's layer holds the one fact, so the derivation completes and the *released*
    registered verifier decides it. If either behaved otherwise, W1 would be measured against
    a comparison that cannot distinguish anything.
    """
    case = PROBE_CASE
    results = {}
    for arm, layer in (("arm_a", {}), ("arm_b", {case["withheld_fact"]: case["withheld_value"]})):
        fact = layer.get(str(case["withheld_fact"]))
        if fact is None:
            results[arm] = {
                "answered": False,
                "refused": True,
                "refusal_reason": REFUSAL_REASON,
                "verified": False,
            }
            continue
        # 39.10 g of a substance of relative atomic mass 39.10 is exactly one mole. The
        # arithmetic is the case's, not the verifier's; the verifier decides the answer.
        answer = str(round(39.10 / float(fact), 2))
        verified, undecidable = await verify_answer(
            case,
            ArmOutcome(
                task_id=str(case["case_id"]), arm="local_model", answer=answer, abstained=False
            ),
        )
        results[arm] = {
            "answered": True,
            "refused": False,
            "answer": answer,
            "verified": verified,
            "undecidable": undecidable,
        }
    return {
        "probe_case_id": case["case_id"],
        "probe_is_outside_the_holdout": case["case_id"]
        not in {str(item["case_id"]) for item in HOLDOUT_CASES},
        "arms": results,
        "arms_are_mechanically_different": (
            results["arm_a"]["verified"] is False and results["arm_b"]["verified"] is True
        ),
        "arm_a_refuses_rather_than_guessing": results["arm_a"]["refused"] is True,
        "why_this_matters": (
            "22C proved its two arms differed on a probe outside its holdout rather than "
            "learning it from a holdout case; the same move here keeps measured_values at 0 "
            "while making the improvement claim decidable before W1 is paid for"
        ),
    }


def _disjointness() -> dict[str, Any]:
    """A holdout that shares facts with the frozen hundred leaks W1 into W3."""
    hundred_prompts = " ".join(str(task["prompt"]).casefold() for task in MICROBENCHMARK_TASKS)
    shared = sorted(
        {
            str(case["withheld_fact"])
            for case in HOLDOUT_CASES
            if str(case["withheld_fact"]).casefold() in hundred_prompts
        }
    )
    hundred_ids = {str(task["task_id"]) for task in MICROBENCHMARK_TASKS}
    overlapping_ids = sorted(hundred_ids & {str(case["case_id"]) for case in HOLDOUT_CASES})
    return {
        "case_ids_shared_with_the_hundred": overlapping_ids,
        "withheld_facts_named_in_the_hundred": shared,
        "disjoint": not overlapping_ids and not shared,
        "why": (
            "reading this holdout at the end of W1 must tell nobody anything about a task in "
            "the frozen hundred, or the W3 measurement is contaminated by a W1 result"
        ),
    }


def _record(probe: dict[str, Any]) -> dict[str, Any]:
    hashes = case_hashes()
    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22D-020"],
        "holdout_id": HOLDOUT_ID,
        "case_count": len(HOLDOUT_CASES),
        "case_ids": [str(case["case_id"]) for case in HOLDOUT_CASES],
        "case_hashes": hashes,
        "holdout_hash": _sha256(canonical(hashes)),
        "seeds": list(SEEDS),
        "arms": {"arm_a": ARM_A, "arm_b": ARM_B},
        "success_definition": SUCCESS_DEFINITION,
        "refusal_reason_when_absent": REFUSAL_REASON,
        "grounding_ladder_statuses": [str(rung["status"]) for rung in GROUNDING_LADDER],
        "retrievable_statuses": [
            str(rung["status"]) for rung in GROUNDING_LADDER if rung["retrievable"]
        ],
        "withheld_facts": sorted({str(case["withheld_fact"]) for case in HOLDOUT_CASES}),
        "grounding_sources": sorted({str(case["grounding_source"]) for case in HOLDOUT_CASES}),
        "arm_mechanism_probe": probe,
        "disjointness": _disjointness(),
        "measured_values": 0,
        "read_once": "at the end of W1, and never before",
        "not_22c_holdout": (
            "22C's holdout was read once to arm A 0 of 4 and arm B 0 of 4 and is released "
            "unamended; §2.3 puts any retro-fix, re-read or amendment of it out of scope, and "
            "this is a fresh unread instrument rather than the old one with a new acceptance "
            "path behind it"
        ),
    }
    record["recorded_at"] = SLICE_TIME.isoformat().replace("+00:00", "Z")
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    record = _record(asyncio.run(_arm_mechanism_probe()))
    if arguments.check:
        if not OUTPUT.exists():
            print(f"MISSING {OUTPUT}")
            return 1
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        body = {k: v for k, v in stored.items() if k != "integrity_content_hash"}
        sealed = _sha256(canonical(body)) == stored["integrity_content_hash"]
        identical = stored == record
        print(f"seal_recomputes={sealed} rebuild_identical={identical}")
        return 0 if sealed and identical else 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "cases": record["case_count"],
                "measured_values": record["measured_values"],
                "arms_are_mechanically_different": record["arm_mechanism_probe"][
                    "arms_are_mechanically_different"
                ],
                "arm_a_refuses_rather_than_guessing": record["arm_mechanism_probe"][
                    "arm_a_refuses_rather_than_guessing"
                ],
                "disjoint_from_the_hundred": record["disjointness"]["disjoint"],
                "holdout_hash": record["holdout_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
