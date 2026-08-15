"""S22C-013. The frozen holdout, in a module the campaign driver cannot reach.

§2.2c freezes the holdout — task set, verifier, seeds and success definition — in W0, with
`measured_values: 0`, **before any source byte is extracted**. 22B's W1-F6 is a standing
rule here: *a driver that mutates a corpus must not be pointed at the corpus an exit reads*,
and the holdout store is separate by construction rather than by promise. So the separation
is made three ways, each mechanical:

* **by module** — the holdout lives here, and `campaign_22c.py` imports nothing from this
  file. A test asserts that, so a future wave that reaches for a holdout case as curriculum
  breaks the suite rather than the evidence;
* **by store** — the cases are read through `COGOS_HOLDOUT_DATABASE_URL`, a database whose
  name is not derivable from the campaign's own connection string;
* **by hash** — the manifest binds the case hashes and refuses to seal if any of them also
  appears in the curriculum.

**What "improves a held-out verified task" is frozen to mean.** The improvement exit is the
sprint's hardest sentence (§3.2), and the honest way to make it decidable in advance is to
name a task the platform genuinely cannot do without acquired knowledge, and can do with it.

Each holdout case is a released pilot problem whose formal inputs are **deliberately
incomplete**: it omits exactly one declared fact that the source chapter supplies — an
atomic mass, a unit relation. The pilots' own kernels refuse an incomplete case by design
(`atomic_masses: the case must declare the atomic masses it relies on`), so:

* **arm A, artifact inactive** — the gap is not filled, the kernel refuses, the case fails;
* **arm B, artifact active** — the gap is filled from a retained artifact, the kernel solves
  and the *released* `domains.checker` verifies the answer independently.

Nothing about arm B weakens the verification: the checker judges the answer exactly as it
judges every other case, and a wrong value supplied by a wrong artifact fails. The claim the
exit licenses is precisely the existence proof §4 describes — at least one retained
artifact, at least one held-out task, measured improvement — and no learning rate.

    UV_CACHE_DIR=.cache/uv uv run python scripts/holdout_22c.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/holdout_22c.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"

HOLDOUT_ID = "s22c-acquisition-holdout-v1"
VERIFIER_ID = "domains.checker"

#: One seed per case, fixed now. The pilots' kernels are deterministic, so the seeds do not
#: randomise anything — they are recorded because §2.2c requires seeds to be frozen, and a
#: sprint that later introduces a sampled arm must use these rather than choose new ones.
SEEDS = (22_031, 22_032, 22_033, 22_034)

SUCCESS_DEFINITION = (
    "the case is accepted by domains.checker with every capability the registry entry "
    "requires actually exercised, and the answer equals the case's expected answer"
)

#: The store the holdout is read from. Named, never inlined: a manifest sealed into evidence
#: carries no credential.
STORE_URL_ENV = "COGOS_HOLDOUT_DATABASE_URL"


@dataclass(frozen=True, slots=True)
class HoldoutCase:
    """One held-out task, and the exact fact it is missing.

    `withheld_key` and `withheld_value` are what makes the two arms mechanical rather than
    rhetorical: arm A runs `formal_inputs` as written, arm B runs it with `withheld_key`
    restored from a retained artifact. The value is recorded here so the comparison can be
    *checked* — an arm B that supplied something else would be answering a different task.
    """

    case_id: str
    domain_id: str
    problem_type: str
    #: The knowledge the source chapter carries and the case withholds.
    withheld_key: str
    withheld_value: Any
    withheld_description: str
    #: Incomplete on purpose: this is arm A's input exactly as written.
    formal_inputs: dict[str, Any]
    expected_answer: dict[str, Any]

    @property
    def content_hash(self) -> str:
        return _sha256(
            _canonical(
                {
                    "case_id": self.case_id,
                    "domain_id": self.domain_id,
                    "problem_type": self.problem_type,
                    "withheld_key": self.withheld_key,
                    "formal_inputs": self.formal_inputs,
                    "expected_answer": self.expected_answer,
                }
            )
        )

    def arm_a_inputs(self) -> dict[str, Any]:
        """Artifact inactive: the case exactly as frozen, gap and all."""
        return dict(self.formal_inputs)

    def arm_b_inputs(self, supplied: Any) -> dict[str, Any]:
        """Artifact active: the same case with the withheld fact restored.

        `supplied` comes from the retained artifact at measurement time, never from this
        module — a holdout that filled its own gap would be measuring itself.
        """
        return {**self.formal_inputs, self.withheld_key: supplied}


#: Four cases across both pilot domains. Each withholds one fact and nothing else, so a
#: failure in arm A is attributable to the gap rather than to a case that was hard anyway.
HOLDOUT_CASES: tuple[HoldoutCase, ...] = (
    HoldoutCase(
        case_id="holdout-molar-conversion-water",
        domain_id="science.chemistry",
        problem_type="chemistry.molar-conversion",
        withheld_key="atomic_masses",
        withheld_value={"H": 1, "O": 16},
        withheld_description="the atomic masses of hydrogen and oxygen",
        formal_inputs={
            "formula": "H2O",
            "mass": {"magnitude": 90, "unit": "g"},
            "molar_mass_unit": "g/mol",
        },
        expected_answer={"exact_value": "5", "units": "mol"},
    ),
    HoldoutCase(
        case_id="holdout-molar-conversion-methane",
        domain_id="science.chemistry",
        problem_type="chemistry.molar-conversion",
        withheld_key="atomic_masses",
        withheld_value={"C": 12, "H": 1},
        withheld_description="the atomic masses of carbon and hydrogen",
        formal_inputs={
            "formula": "CH4",
            "mass": {"magnitude": 64, "unit": "g"},
            "molar_mass_unit": "g/mol",
        },
        expected_answer={"exact_value": "4", "units": "mol"},
    ),
    HoldoutCase(
        case_id="holdout-mass-balance-ammonia",
        domain_id="science.chemistry",
        problem_type="chemistry.mass-balance",
        withheld_key="atomic_masses",
        withheld_value={"N": 14, "H": 1},
        withheld_description="the atomic masses of nitrogen and hydrogen",
        formal_inputs={
            "reactants": [
                {"formula": "N2", "coefficient": 1},
                {"formula": "H2", "coefficient": 3},
            ],
            "products": [{"formula": "NH3", "coefficient": 2}],
        },
        expected_answer={"structured": {"balanced": True}},
    ),
    HoldoutCase(
        case_id="holdout-uniform-motion-kilometres",
        domain_id="engineering.mechanics",
        problem_type="mechanics.uniform-motion",
        withheld_key="speed",
        withheld_value={"magnitude": 15, "unit": "m/s"},
        withheld_description="the constant speed the passage states for the body",
        formal_inputs={"time": {"magnitude": 200, "unit": "s"}, "result_unit": "m"},
        expected_answer={"exact_value": "3000", "units": "m"},
    ),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def case_hashes() -> tuple[str, ...]:
    return tuple(case.content_hash for case in HOLDOUT_CASES)


def holdout_definition() -> dict[str, Any]:
    """The frozen definition, with `measured_values: 0` and both arms named."""
    return {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W0",
        "items": ["S22C-013"],
        "holdout_id": HOLDOUT_ID,
        "frozen_before_any_source_byte_was_extracted": True,
        "measured_values": 0,
        "verifier_id": VERIFIER_ID,
        "seeds": list(SEEDS),
        "success_definition": SUCCESS_DEFINITION,
        "store_url_env": STORE_URL_ENV,
        "separation": {
            "by_module": (
                "campaign_22c.py imports nothing from holdout_22c.py; a test asserts it, so "
                "a wave that reaches for a holdout case as curriculum breaks the suite"
            ),
            "by_store": (
                "read through COGOS_HOLDOUT_DATABASE_URL — a database whose name is not "
                "derivable from the campaign's own connection string"
            ),
            "by_hash": (
                "CampaignManifestV1 refuses to seal if any holdout case hash also appears "
                "in the curriculum"
            ),
            "standing_rule": "22B W1-F6",
        },
        "arms": {
            "arm_a_artifact_inactive": (
                "the case is run exactly as frozen, with its gap. The pilot kernel refuses "
                "an incomplete case by design, so the case fails"
            ),
            "arm_b_artifact_active": (
                "the same case with the withheld fact restored from a retained artifact. "
                "The kernel solves and the released domains.checker verifies the answer "
                "independently — a wrong value from a wrong artifact still fails"
            ),
            "both_arms_measured_in_22c": True,
            "comparison": (
                "verified success on the holdout with the retained artifact active versus "
                "without it — same tasks, same seeds, same checker"
            ),
            "what_it_does_not_license": (
                "§4: an existence proof, not a learning rate. Nothing about how fast the "
                "system learns, what a chapter is worth, or whether cycle 4 would help"
            ),
        },
        "cases": [
            {
                "case_id": case.case_id,
                "domain_id": case.domain_id,
                "problem_type": case.problem_type,
                "withheld_key": case.withheld_key,
                "withheld_description": case.withheld_description,
                "formal_inputs": case.formal_inputs,
                "expected_answer": case.expected_answer,
                "content_hash": case.content_hash,
            }
            for case in HOLDOUT_CASES
        ],
        "case_count": len(HOLDOUT_CASES),
        "case_hashes": list(case_hashes()),
        "domains_covered": sorted({case.domain_id for case in HOLDOUT_CASES}),
        "limitations": [
            "one holdout, four cases, two pilot domains — §4's 'improvement on one holdout "
            "is not a learning rate' applies in full",
            "every case verifies deterministically, so this says nothing about domains "
            "whose honest verification floor needs proof tools or graded judgment",
            "the withheld facts are declared inputs rather than reasoning steps: the exit "
            "reads whether acquired knowledge makes an unsolvable task solvable, not "
            "whether it makes a solvable task better",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-22c-holdout.json")
    arguments = parser.parse_args()

    record = holdout_definition()
    record["integrity_content_hash"] = _sha256(_canonical(record))
    if arguments.check:
        stored = json.loads(arguments.output.read_text(encoding="utf-8"))
        same = stored == record
        print(
            json.dumps(
                {
                    "path": arguments.output.name,
                    "reproduced": same,
                    "measured_values": stored.get("measured_values"),
                },
                indent=1,
            )
        )
        return 0 if same else 1

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "holdout_id": HOLDOUT_ID,
                "cases": record["case_count"],
                "domains": record["domains_covered"],
                "measured_values": record["measured_values"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
