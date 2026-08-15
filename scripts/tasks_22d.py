"""Sprint 22D W0. The frozen 100-task English technical microbenchmark, and the §3.1 fixture.

**Frozen before any arm runs, and never used for selection.** §2.2(b) and §4: task authorship
is the oldest way to make a benchmark agree with you, so the mitigations here are mechanical
rather than intentional — the hundred are content-hashed in `manifest()`, published with
`measured_values: 0`, and §2.3 forbids tuning the model, the prompt, the retrieval
configuration or the escalation threshold against them afterwards. None of that makes a
hundred tasks representative of technical English, and §4 says so rather than implying
otherwise.

**Provenance, which is §1.4's third rights gate.** Every prompt and every expected answer in
this file is authored in-repository and is ours. Nothing is lifted from a source. The
*facts* the thirty factual tasks ask about are ordinary technical constants and definitions
that the two rights-cleared OpenStax sources state; asking an original question about a
stated fact is authorship, and `grounding_source` records which cleared source is expected to
carry it so W1 can measure whether the acquired layer actually does.

**Three kinds of output, and the split is what the fourth exit reads.** Seventy tasks are
closed-form computations over values the prompt itself states — they assert nothing about the
world and cannot be ungrounded. Thirty are factual: twenty state a fact outright, and ten
derive a result that consumes one. Those thirty are the grounding exit's denominator, and
they are also where the ten-point margin over retrieval-only has to come from, because they
are the tasks a search index can find text for and still not answer.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from benchmark_22d import (
    BENCHMARK_DECLARED_DOMAIN,
    BENCHMARK_VERIFIER_IDS,
    FACTUAL_OUTPUT_KINDS,
    OUTPUT_KINDS,
    canonical,
)

PHYSICS = "openstax-physics-cc-by-4.0"
CHEMISTRY = "openstax-chemistry-2e-cc-by-nc-sa-4.0"


def _task(
    task_id: str,
    prompt: str,
    verifier_id: str,
    subject_type: str,
    configuration: dict[str, Any],
    output_kind: str,
    grounding_source: str | None = None,
) -> dict[str, Any]:
    if verifier_id not in BENCHMARK_VERIFIER_IDS:
        raise ValueError(f"{task_id}: {verifier_id} is not in the frozen verifier set")
    if output_kind not in OUTPUT_KINDS:
        raise ValueError(f"{task_id}: {output_kind} is not a frozen output kind")
    if (output_kind in FACTUAL_OUTPUT_KINDS) != (grounding_source is not None):
        raise ValueError(f"{task_id}: a factual task names its grounding source, and only one")
    return {
        "task_id": task_id,
        "prompt": prompt,
        "verifier_id": verifier_id,
        "subject_type": subject_type,
        "verifier_configuration": configuration,
        "output_kind": output_kind,
        "grounding_source": grounding_source,
        "provenance": "authored in-repository for Sprint 22D",
    }


def _conversion(task_id: str, prompt: str, target: str, expected: str) -> dict[str, Any]:
    """A stated quantity re-expressed. The verifier converts, so any equivalent unit passes."""
    return _task(
        task_id,
        prompt,
        "physics.unit_conversion",
        "physical_quantity",
        {"target_unit": target, "expected_magnitude": expected, "absolute_tolerance": "0.005"},
        "closed_form_computation",
    )


def _quantity(task_id: str, prompt: str, magnitude: str, unit: str) -> dict[str, Any]:
    return _task(
        task_id,
        prompt,
        "physics.quantity",
        "physical_quantity",
        {
            "expected": {"magnitude": magnitude, "unit": unit},
            "relative_tolerance": "0.001",
        },
        "closed_form_computation",
    )


def _dimension(task_id: str, prompt: str, expected_unit: str) -> dict[str, Any]:
    return _task(
        task_id,
        prompt,
        "physics.dimension",
        "physical_quantity",
        {"expected_unit": expected_unit},
        "closed_form_computation",
    )


def _numeric(
    task_id: str,
    prompt: str,
    expected: str,
    tolerance: str = "0.001",
    output_kind: str = "closed_form_computation",
    grounding_source: str | None = None,
) -> dict[str, Any]:
    return _task(
        task_id,
        prompt,
        "mathematics.numeric",
        "mathematical_expression",
        {"expected": expected, "relative_tolerance": tolerance},
        output_kind,
        grounding_source,
    )


def _term(task_id: str, prompt: str, expected: str, grounding_source: str) -> dict[str, Any]:
    return _task(
        task_id,
        prompt,
        "generic.exact",
        "structured_value",
        {"expected": expected, "case_sensitive": False, "strip_whitespace": True},
        "declarative_fact",
        grounding_source,
    )


# ---------------------------------------------------------------------------
# Family 1 — unit conversion, 20 tasks. physics.unit_conversion.
# ---------------------------------------------------------------------------

_CONVERSIONS = (
    (
        "A hoist cable is rated for a tension of 3.5 kilonewtons. Express that tension in newtons.",
        "N",
        "3500",
    ),
    ("A survey leg measures 2.4 kilometres. Express that distance in metres.", "m", "2400"),
    ("A test run lasts 45 minutes. Express that duration in seconds.", "s", "2700"),
    ("A component has a mass of 850 grams. Express that mass in kilograms.", "kg", "0.85"),
    ("A cycle dissipates 12 kilojoules. Express that energy in joules.", "J", "12000"),
    ("A pump draws 2.4 kilowatts. Express that power in watts.", "W", "2400"),
    ("A vessel is held at 180 kilopascals. Express that pressure in pascals.", "Pa", "180000"),
    (
        "A carriage travels at 72 kilometres per hour. Express that speed in metres per second.",
        "m/s",
        "20",
    ),
    ("A reservoir holds 3.5 litres. Express that volume in millilitres.", "mL", "3500"),
    ("A signal has a period of 25 milliseconds. Express that period in seconds.", "s", "0.025"),
    ("A bar is 0.75 metres long. Express that length in centimetres.", "cm", "75"),
    ("A rotor turns at 1500 revolutions per minute. Express that rate in hertz.", "Hz", "25"),
    ("A shipment weighs 1.8 tonnes. Express that mass in kilograms.", "kg", "1800"),
    ("A capacitor stores 470 microfarads. Express that capacitance in farads.", "F", "0.00047"),
    ("A resistor is specified as 4.7 kilohms. Express that resistance in ohms.", "ohm", "4700"),
    (
        "A duct carries 0.6 cubic metres per second. Express that flow in litres per second.",
        "L/s",
        "600",
    ),
    ("A heater runs for 3 hours. Express that duration in minutes.", "min", "180"),
    ("A wire carries 250 milliamperes. Express that current in amperes.", "A", "0.25"),
    ("A film is 40 micrometres thick. Express that thickness in millimetres.", "mm", "0.04"),
    ("A beam deflects 3.2 millimetres. Express that deflection in metres.", "m", "0.0032"),
)

# ---------------------------------------------------------------------------
# Family 2 — computed physical quantities, 20 tasks. physics.quantity.
# Every input value appears in the prompt, so nothing here asserts a world fact.
# ---------------------------------------------------------------------------

_QUANTITIES = (
    (
        "A trolley covers 150 metres in 12 seconds at constant speed. What is its speed?",
        "12.5",
        "m/s",
    ),
    ("A force of 24 newtons acts on a 6 kilogram block. What is the acceleration?", "4", "m/s**2"),
    ("A 2.5 kilogram mass moves at 8 metres per second. What is its kinetic energy?", "80", "J"),
    ("A motor does 9000 joules of work in 15 seconds. What is its mean power?", "600", "W"),
    (
        "A force of 500 newtons acts over an area of 0.25 square metres. What is the pressure?",
        "2000",
        "Pa",
    ),
    (
        "A spanner applies 40 newtons at 0.3 metres from the pivot, perpendicular. What is the "
        "torque?",
        "12",
        "N*m",
    ),
    (
        "A 3 kilogram body is raised 4 metres where gravitational field strength is 9.8 newtons "
        "per kilogram. What is the gain in gravitational potential energy?",
        "117.6",
        "J",
    ),
    (
        "A current of 2 amperes flows through a 12 ohm resistor. What is the potential difference?",
        "24",
        "V",
    ),
    ("A 60 watt lamp runs for 300 seconds. What energy does it use?", "18000", "J"),
    ("A wave has frequency 50 hertz and wavelength 6 metres. What is its speed?", "300", "m/s"),
    ("A 1.2 kilogram mass moves at 5 metres per second. What is its momentum?", "6", "kg*m/s"),
    (
        "A spring of stiffness 200 newtons per metre extends 0.15 metres. What is the restoring "
        "force?",
        "30",
        "N",
    ),
    (
        "A body accelerates from rest at 3 metres per second squared for 7 seconds. What is its "
        "final speed?",
        "21",
        "m/s",
    ),
    (
        "A pump raises 500 kilograms of water 8 metres in 40 seconds, with gravitational field "
        "strength 9.8 newtons per kilogram. What is its mean output power?",
        "980",
        "W",
    ),
    ("A resistor dissipates 18 watts at 3 amperes. What is its resistance?", "2", "ohm"),
    (
        "A car of mass 900 kilograms decelerates at 2.5 metres per second squared. What is the "
        "braking force?",
        "2250",
        "N",
    ),
    ("A heater transfers 42000 joules in 7 minutes. What is its mean power?", "100", "W"),
    (
        "A wheel of radius 0.4 metres turns at 15 radians per second. What is the rim speed?",
        "6",
        "m/s",
    ),
    ("A charge of 6 coulombs passes a point in 4 seconds. What is the current?", "1.5", "A"),
    (
        "A gas occupies 0.02 cubic metres at 250 kilopascals. What is the product of pressure and "
        "volume?",
        "5000",
        "J",
    ),
)

# ---------------------------------------------------------------------------
# Family 3 — dimensional analysis, 10 tasks. physics.dimension.
# ---------------------------------------------------------------------------

_DIMENSIONS = (
    ("Give a unit in which mechanical work may be expressed.", "J"),
    ("Give a unit in which linear momentum may be expressed.", "kg*m/s"),
    ("Give a unit in which pressure may be expressed.", "Pa"),
    ("Give a unit in which electrical power may be expressed.", "W"),
    ("Give a unit in which acceleration may be expressed.", "m/s**2"),
    ("Give a unit in which electric charge may be expressed.", "C"),
    ("Give a unit in which frequency may be expressed.", "Hz"),
    ("Give a unit in which density may be expressed.", "kg/m**3"),
    ("Give a unit in which the moment of a force may be expressed.", "N*m"),
    ("Give a unit in which electrical resistance may be expressed.", "ohm"),
)

# ---------------------------------------------------------------------------
# Family 4 — numeric technical computation, 20 tasks. mathematics.numeric.
# ---------------------------------------------------------------------------

_NUMERICS = (
    ("A batch of 480 units is inspected and 36 are rejected. What percentage is rejected?", "7.5"),
    (
        "A signal is attenuated from 240 millivolts to 60 millivolts. By what factor is it "
        "reduced?",
        "4",
    ),
    ("A tank fills at 12 litres per minute for 7.5 minutes. How many litres does it hold?", "90"),
    (
        "A gear pair has 45 and 15 teeth. What is the gear ratio, expressed as the larger over "
        "the smaller?",
        "3",
    ),
    (
        "Three resistors of 6 ohms each are connected in parallel. What is the equivalent "
        "resistance in ohms?",
        "2",
    ),
    (
        "A rectangular plate measures 2.5 metres by 1.6 metres. What is its area in square metres?",
        "4",
    ),
    (
        "A cylinder of radius 2 metres and height 5 metres has what volume in cubic metres, to "
        "three decimal places?",
        "62.832",
    ),
    (
        "A load is shared equally by 8 bolts and totals 26 kilonewtons. What load in kilonewtons "
        "does each bolt carry?",
        "3.25",
    ),
    (
        "A process runs at 92 percent efficiency on an input of 250 kilowatts. What is the useful "
        "output in kilowatts?",
        "230",
    ),
    (
        "A measurement of 4.80 metres has an absolute uncertainty of 0.06 metres. What is the "
        "percentage uncertainty?",
        "1.25",
    ),
    ("A component costs 18 units and 750 are produced. What is the total cost in units?", "13500"),
    ("A right triangle has legs of 9 and 12 units. What is the hypotenuse?", "15"),
    (
        "A sample of 1200 decays to 150 over three half-lives. What fraction remains, as a "
        "decimal?",
        "0.125",
    ),
    (
        "A beam of length 6 metres is loaded at its midpoint. How far in metres is the load from "
        "each support?",
        "3",
    ),
    ("A 15 percent discount is applied to 640 units. What is the reduced figure?", "544"),
    (
        "A pipe of internal diameter 0.1 metres has what cross-sectional area in square metres, "
        "to six decimal places?",
        "0.007854",
    ),
    (
        "A machine completes 1 cycle every 2.5 seconds. How many cycles does it complete in one "
        "hour?",
        "1440",
    ),
    ("A logarithmic gain is 20 decibels. What is the corresponding voltage ratio?", "10"),
    (
        "A mixture is 3 parts to 5 parts by mass and totals 64 kilograms. What is the mass in "
        "kilograms of the smaller part?",
        "24",
    ),
    (
        "A value grows by 10 percent and then falls by 10 percent from 500. What is the final "
        "value?",
        "495",
    ),
)

# ---------------------------------------------------------------------------
# Family 5 — declarative facts, 20 tasks. Twelve numeric, eight terminological.
# These assert something about the world, so every one of them needs grounding.
# ---------------------------------------------------------------------------

_FACT_NUMERIC = (
    (
        "What is the standard acceleration due to gravity at the Earth's surface, in metres per "
        "second squared?",
        "9.8",
        "0.01",
        PHYSICS,
    ),
    (
        "What is the speed of light in a vacuum, in metres per second?",
        "299792458",
        "0.000001",
        PHYSICS,
    ),
    ("What is the relative atomic mass of potassium?", "39.10", "0.002", CHEMISTRY),
    ("What is the relative atomic mass of oxygen?", "16.00", "0.002", CHEMISTRY),
    ("What is the relative atomic mass of carbon?", "12.01", "0.002", CHEMISTRY),
    ("What is the relative atomic mass of nitrogen?", "14.01", "0.002", CHEMISTRY),
    (
        "How many entities are in one mole, expressed as Avogadro's number?",
        "6.022e23",
        "0.001",
        CHEMISTRY,
    ),
    ("What is the molar gas constant, in joules per mole per kelvin?", "8.314", "0.001", CHEMISTRY),
    ("What is the magnitude of the elementary charge, in coulombs?", "1.602e-19", "0.001", PHYSICS),
    (
        "What is the freezing point of water at standard pressure, in degrees Celsius?",
        "0",
        "0",
        CHEMISTRY,
    ),
    (
        "What is the boiling point of water at standard pressure, in degrees Celsius?",
        "100",
        "0.001",
        CHEMISTRY,
    ),
    ("What is standard atmospheric pressure, in kilopascals?", "101.325", "0.001", CHEMISTRY),
)

_FACT_TERM = (
    ("What is the SI unit of pressure? Give its name in lower case.", "pascal", PHYSICS),
    ("What is the SI unit of energy? Give its name in lower case.", "joule", PHYSICS),
    ("What is the SI unit of electric current? Give its name in lower case.", "ampere", PHYSICS),
    ("What is the SI unit of amount of substance? Give its name in lower case.", "mole", CHEMISTRY),
    ("What is the chemical symbol for potassium?", "K", CHEMISTRY),
    ("What is the chemical symbol for sodium?", "Na", CHEMISTRY),
    ("Which quantity does a newton measure? Give the single word in lower case.", "force", PHYSICS),
    ("Which quantity does a watt measure? Give the single word in lower case.", "power", PHYSICS),
)

# ---------------------------------------------------------------------------
# Family 6 — fact-dependent derivations, 10 tasks. The prompt withholds exactly one
# declared fact, so a system that cannot supply that fact cannot finish the derivation.
# This is 22C's holdout shape, moved into the microbenchmark on purpose: it is where the
# acquired layer either contributes something retrieval alone does not, or does not.
# ---------------------------------------------------------------------------

_DERIVATIONS = (
    (
        "How many moles are in 78.2 grams of potassium? Give the answer to three significant "
        "figures.",
        "2.00",
        "0.005",
        CHEMISTRY,
    ),
    (
        "How many moles are in 48.0 grams of oxygen atoms? Give the answer to three significant "
        "figures.",
        "3.00",
        "0.005",
        CHEMISTRY,
    ),
    (
        "What is the mass in grams of 2.5 moles of carbon atoms? Give the answer to three "
        "significant figures.",
        "30.0",
        "0.005",
        CHEMISTRY,
    ),
    (
        "What is the molar mass of carbon dioxide in grams per mole, to four significant figures?",
        "44.01",
        "0.002",
        CHEMISTRY,
    ),
    (
        "What is the molar mass of water in grams per mole, to four significant figures?",
        "18.02",
        "0.002",
        CHEMISTRY,
    ),
    (
        "A 5 kilogram mass rests on the Earth's surface. What is its weight in newtons?",
        "49",
        "0.005",
        PHYSICS,
    ),
    (
        "A 12 kilogram mass is raised 3 metres at the Earth's surface. What is the gain in "
        "gravitational potential energy, in joules?",
        "352.8",
        "0.005",
        PHYSICS,
    ),
    (
        "Light travels for 2 seconds in a vacuum. How far does it travel, in metres?",
        "599584916",
        "0.000001",
        PHYSICS,
    ),
    (
        "How many moles are in 28.02 grams of nitrogen atoms? Give the answer to three "
        "significant figures.",
        "2.00",
        "0.005",
        CHEMISTRY,
    ),
    (
        "How much charge in coulombs is carried by 5 elementary charges? Give the answer in "
        "scientific notation.",
        "8.01e-19",
        "0.001",
        PHYSICS,
    ),
)


def _build() -> tuple[dict[str, Any], ...]:
    tasks: list[dict[str, Any]] = []
    for index, (prompt, target, expected) in enumerate(_CONVERSIONS, start=1):
        tasks.append(_conversion(f"s22d-convert-{index:02d}", prompt, target, expected))
    for index, (prompt, magnitude, unit) in enumerate(_QUANTITIES, start=1):
        tasks.append(_quantity(f"s22d-quantity-{index:02d}", prompt, magnitude, unit))
    for index, (prompt, unit) in enumerate(_DIMENSIONS, start=1):
        tasks.append(_dimension(f"s22d-dimension-{index:02d}", prompt, unit))
    for index, (prompt, expected) in enumerate(_NUMERICS, start=1):
        tasks.append(_numeric(f"s22d-numeric-{index:02d}", prompt, expected))
    for index, (prompt, expected, tolerance, source) in enumerate(_FACT_NUMERIC, start=1):
        tasks.append(
            _numeric(
                f"s22d-fact-{index:02d}",
                prompt,
                expected,
                tolerance,
                "declarative_fact",
                source,
            )
        )
    for index, (prompt, expected, source) in enumerate(_FACT_TERM, start=13):
        tasks.append(_term(f"s22d-fact-{index:02d}", prompt, expected, source))
    for index, (prompt, expected, tolerance, source) in enumerate(_DERIVATIONS, start=1):
        tasks.append(
            _numeric(
                f"s22d-derive-{index:02d}",
                prompt,
                expected,
                tolerance,
                "fact_dependent_derivation",
                source,
            )
        )
    return tuple(tasks)


MICROBENCHMARK_TASKS = _build()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def task_hashes() -> dict[str, str]:
    """One content hash per task, over the whole task including its expected answer."""
    return {str(task["task_id"]): _sha256(canonical(task)) for task in MICROBENCHMARK_TASKS}


def manifest() -> dict[str, Any]:
    """The frozen manifest §2.2(b) requires, with `measured_values: 0`."""
    hashes = task_hashes()
    by_kind: dict[str, int] = {}
    by_verifier: dict[str, int] = {}
    for task in MICROBENCHMARK_TASKS:
        by_kind[str(task["output_kind"])] = by_kind.get(str(task["output_kind"]), 0) + 1
        by_verifier[str(task["verifier_id"])] = by_verifier.get(str(task["verifier_id"]), 0) + 1
    factual = [task for task in MICROBENCHMARK_TASKS if task["output_kind"] in FACTUAL_OUTPUT_KINDS]
    return {
        "benchmark_id": "sprint-22d-english-technical-microbenchmark",
        "declared_domain": BENCHMARK_DECLARED_DOMAIN.value,
        "task_count": len(MICROBENCHMARK_TASKS),
        "task_ids": [str(task["task_id"]) for task in MICROBENCHMARK_TASKS],
        "task_hashes": hashes,
        "manifest_hash": _sha256(canonical(hashes)),
        "tasks_by_output_kind": by_kind,
        "tasks_by_verifier": by_verifier,
        "factual_output_count": len(factual),
        "factual_task_ids": [str(task["task_id"]) for task in factual],
        "grounding_sources": sorted(
            {str(task["grounding_source"]) for task in factual if task["grounding_source"]}
        ),
        "provenance": "every prompt and expected answer authored in-repository for Sprint 22D",
        "measured_values": 0,
        "never_used_for_selection": (
            "the hundred select no model, prompt, retrieval configuration, escalation "
            "threshold or non-inferiority margin; §2.3 forbids tuning any of them after the "
            "first measured number exists"
        ),
    }


# ---------------------------------------------------------------------------
# §3.1. The fixture, which is not the hundred and never becomes it
# ---------------------------------------------------------------------------

#: Two short technical passages authored here, so the slice has registered bytes to resolve a
#: citation into before any cleared source is opened.
FIXTURE_SOURCES = {
    "s22d-fixture-source-a": (
        "Fixture note A. This passage exists so the Sprint 22D slice has registered bytes.\n"
        "The reference bar in this fixture has a stated length of 2.5 metres.\n"
        "The fixture rig applies a stated force of 40 newtons.\n"
        "The fixture rig is specified to draw 150 watts under steady load.\n"
    ),
    "s22d-fixture-source-b": (
        "Fixture note B. A second registered source, so a walk that resolves is not a walk\n"
        "into the only file the runner ever loads.\n"
        "The fixture coolant has a stated density of 1100 kilograms per cubic metre.\n"
        "The fixture cycle has a stated duration of 90 seconds.\n"
    ),
}

FIXTURE_TASKS = (
    _conversion(
        "s22d-fixture-01",
        "A fixture leg measures 1.5 kilometres. Express it in metres.",
        "m",
        "1500",
    ),
    _conversion(
        "s22d-fixture-02", "A fixture cycle lasts 4 minutes. Express it in seconds.", "s", "240"
    ),
    _quantity(
        "s22d-fixture-03",
        "A fixture trolley covers 60 metres in 5 seconds at constant speed. What is its speed?",
        "12",
        "m/s",
    ),
    _dimension("s22d-fixture-04", "Give a unit in which fixture work may be expressed.", "J"),
    _numeric(
        "s22d-fixture-05", "A fixture batch of 200 has 8 rejects. What percentage is rejected?", "4"
    ),
    _numeric(
        "s22d-fixture-06",
        "What is the stated length of the fixture reference bar, in metres?",
        "2.5",
        "0.001",
        "declarative_fact",
        "s22d-fixture-source-a",
    ),
    _numeric(
        "s22d-fixture-07",
        "What is the stated force applied by the fixture rig, in newtons?",
        "40",
        "0.001",
        "declarative_fact",
        "s22d-fixture-source-a",
    ),
    _numeric(
        "s22d-fixture-08",
        "What is the stated density of the fixture coolant, in kilograms per cubic metre?",
        "1100",
        "0.001",
        "declarative_fact",
        "s22d-fixture-source-b",
    ),
    _numeric(
        "s22d-fixture-09",
        "What is the stated steady-load power draw of the fixture rig, in watts?",
        "150",
        "0.001",
        "declarative_fact",
        "s22d-fixture-source-a",
    ),
    _numeric(
        "s22d-fixture-10",
        "The fixture rig runs for the stated fixture cycle duration at its stated power draw. "
        "What energy does it use, in joules?",
        "13500",
        "0.001",
        "fact_dependent_derivation",
        "s22d-fixture-source-b",
    ),
)

_QUOTE_BAR = "a stated length of 2.5 metres"
_QUOTE_FORCE = "a stated force of 40 newtons"
_QUOTE_POWER = "draw 150 watts under steady load"
_QUOTE_DENSITY = "a stated density of 1100 kilograms per cubic metre"
_QUOTE_DURATION = "a stated duration of 90 seconds"

_A = "s22d-fixture-source-a"
_B = "s22d-fixture-source-b"


def _cite(source_id: str, quote: str) -> dict[str, Any]:
    return {"source_id": source_id, "quote": quote}


#: **What each arm answers, and why the four differ mechanically.** §3.1's job is to prove the
#: runner can tell the arms apart before the hundred is touched; 22C paid for that lesson by
#: proving two arms differed before spending a holdout case discovering they did not.
#:
#: * `no_memory` computes what the prompt states and **asserts the facts it cannot know**,
#:   with no citation. That is the third §2.2(d) case, and the slice needs it non-zero to
#:   prove the counter can print more than one outcome (22C W4: a record that can only print
#:   one outcome has verified nothing either way).
#: * `retrieval_only` returns the retrieved sentence rather than the value, so it grounds
#:   everything it answers and verifies almost none of it — a search index, exactly as
#:   §2.2(b) reads it.
#: * `external_teacher` answers everything and cites nothing, at one provider call per task.
#: * `local_model` answers from the grounded layer, cites, and **abstains** where the layer
#:   does not carry the fact.
FIXTURE_ANSWERS: dict[str, dict[str, Any]] = {
    "s22d-fixture-01": {
        "no_memory": {"answer": {"magnitude": "1500", "unit": "m"}, "output_tokens": 12},
        "retrieval_only": {
            "answer": "no registered span matches this prompt",
            "answer_form_valid": False,
        },
        "external_teacher": {
            "answer": {"magnitude": "1500", "unit": "m"},
            "input_tokens": 90,
            "output_tokens": 14,
        },
        "local_model": {
            "answer": {"magnitude": "1.5", "unit": "km"},
            "local_compute_seconds": 0.8,
            "output_tokens": 12,
        },
    },
    "s22d-fixture-02": {
        "no_memory": {"answer": {"magnitude": "240", "unit": "s"}, "output_tokens": 10},
        "retrieval_only": {
            "answer": "no registered span matches this prompt",
            "answer_form_valid": False,
        },
        "external_teacher": {
            "answer": {"magnitude": "240", "unit": "s"},
            "input_tokens": 88,
            "output_tokens": 11,
        },
        "local_model": {
            "answer": {"magnitude": "240", "unit": "s"},
            "local_compute_seconds": 0.7,
            "output_tokens": 10,
        },
    },
    "s22d-fixture-03": {
        "no_memory": {"answer": {"magnitude": "12", "unit": "m/s"}, "output_tokens": 11},
        "retrieval_only": {
            "answer": "no registered span matches this prompt",
            "answer_form_valid": False,
        },
        "external_teacher": {
            "answer": {"magnitude": "12", "unit": "m/s"},
            "input_tokens": 95,
            "output_tokens": 13,
        },
        "local_model": {
            "answer": {"magnitude": "12", "unit": "m/s"},
            "local_compute_seconds": 0.9,
            "output_tokens": 11,
        },
    },
    "s22d-fixture-04": {
        "no_memory": {"answer": {"magnitude": "1", "unit": "J"}, "output_tokens": 8},
        "retrieval_only": {
            "answer": "no registered span matches this prompt",
            "answer_form_valid": False,
        },
        "external_teacher": {
            "answer": {"magnitude": "1", "unit": "N*m"},
            "input_tokens": 80,
            "output_tokens": 9,
        },
        "local_model": {
            "answer": {"magnitude": "1", "unit": "J"},
            "local_compute_seconds": 0.6,
            "output_tokens": 8,
        },
    },
    "s22d-fixture-05": {
        "no_memory": {"answer": "4", "output_tokens": 7},
        "retrieval_only": {
            "answer": "no registered span matches this prompt",
            "answer_form_valid": False,
        },
        "external_teacher": {"answer": "4", "input_tokens": 86, "output_tokens": 8},
        "local_model": {"answer": "4", "local_compute_seconds": 0.7, "output_tokens": 7},
    },
    # The five factual tasks. Everything above this line asserts nothing about the world.
    "s22d-fixture-06": {
        "no_memory": {"answer": "2.5", "output_tokens": 6},
        "retrieval_only": {"answer": _QUOTE_BAR, "citations": (_cite(_A, _QUOTE_BAR),)},
        "external_teacher": {"answer": "2.5", "input_tokens": 92, "output_tokens": 7},
        "local_model": {
            "answer": "2.5",
            "citations": (_cite(_A, _QUOTE_BAR),),
            "local_compute_seconds": 1.1,
            "output_tokens": 6,
        },
    },
    "s22d-fixture-07": {
        "no_memory": {"answer": "40", "output_tokens": 6},
        "retrieval_only": {"answer": _QUOTE_FORCE, "citations": (_cite(_A, _QUOTE_FORCE),)},
        "external_teacher": {"answer": "40", "input_tokens": 91, "output_tokens": 7},
        "local_model": {
            "answer": "40",
            "citations": (_cite(_A, _QUOTE_FORCE),),
            "local_compute_seconds": 1.0,
            "output_tokens": 6,
        },
    },
    "s22d-fixture-08": {
        "no_memory": {"answer": "1000", "output_tokens": 6},
        "retrieval_only": {"answer": _QUOTE_DENSITY, "citations": (_cite(_B, _QUOTE_DENSITY),)},
        "external_teacher": {"answer": "1100", "input_tokens": 93, "output_tokens": 7},
        "local_model": {
            "answer": "1100",
            "citations": (_cite(_B, _QUOTE_DENSITY),),
            "local_compute_seconds": 1.2,
            "output_tokens": 6,
        },
    },
    "s22d-fixture-09": {
        "no_memory": {"answer": "150", "output_tokens": 6},
        "retrieval_only": {"answer": _QUOTE_POWER, "citations": (_cite(_A, _QUOTE_POWER),)},
        "external_teacher": {"answer": "150", "input_tokens": 90, "output_tokens": 7},
        "local_model": {
            "answer": "150",
            "citations": (_cite(_A, _QUOTE_POWER),),
            "local_compute_seconds": 1.0,
            "output_tokens": 6,
        },
    },
    # The one abstention: the derivation needs both stated facts, and the fixture layer is
    # written so the local arm holds only one of them. A typed abstention, not a hedge.
    "s22d-fixture-10": {
        "no_memory": {"answer": "9000", "output_tokens": 9},
        "retrieval_only": {"answer": _QUOTE_DURATION, "citations": (_cite(_B, _QUOTE_DURATION),)},
        "external_teacher": {"answer": "13500", "input_tokens": 104, "output_tokens": 12},
        "local_model": {
            "abstained": True,
            "answer": None,
            "local_compute_seconds": 0.5,
            "output_tokens": 4,
        },
    },
}


def fixture_manifest() -> dict[str, Any]:
    return {
        "fixture_task_count": len(FIXTURE_TASKS),
        "fixture_task_hashes": {
            str(task["task_id"]): _sha256(canonical(task)) for task in FIXTURE_TASKS
        },
        "fixture_source_hashes": {
            key: _sha256(value.encode("utf-8")) for key, value in FIXTURE_SOURCES.items()
        },
        "fixture_is_not_the_hundred": (
            "no fixture task id appears in the microbenchmark manifest, and the slice reads "
            "no exit criterion"
        ),
        "disjoint_from_the_hundred": not (
            {str(task["task_id"]) for task in FIXTURE_TASKS}
            & {str(task["task_id"]) for task in MICROBENCHMARK_TASKS}
        ),
    }


if __name__ == "__main__":
    print(json.dumps(manifest(), indent=1, sort_keys=True))
