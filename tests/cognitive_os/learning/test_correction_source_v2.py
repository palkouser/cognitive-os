from __future__ import annotations

from hashlib import sha256

import pytest

from cognitive_os.learning.calibration_ood import rename_identifiers
from cognitive_os.learning.correction_source import (
    CANONICAL_PREFIX,
    SourceNormalizationError,
    canonical_source_bytes,
)


def test_golden_canonical_bytes_and_hash_are_exact() -> None:
    source = "def add(x, y=1):\n    total = x + y\n    return total\n"
    canonical = canonical_source_bytes(source)

    assert canonical.startswith(CANONICAL_PREFIX)
    assert sha256(canonical).hexdigest() == (
        "6926789b8d0952d87183bc06bf38bd6e062c867060ba72220830d7e88c1ff1f3"
    )
    assert b"__cogos_s0000_b0000" in canonical
    assert b"__cogos_s0001_b0002" in canonical


def test_formatting_and_independent_generator_rename_are_identical() -> None:
    source = (
        "def calculate(value, bonus=1):\n"
        "    result = value + bonus\n"
        "    return result\n"
        "answer = calculate(value=2, bonus=3)\n"
    )
    renamed = rename_identifiers(source)[0]
    reformatted = (
        "\n\ndef calculate( value,bonus = 1 ):\n result=value+bonus\n return result\n"
        "answer=calculate(value=2,bonus=3)\n"
    )

    assert canonical_source_bytes(source) == canonical_source_bytes(renamed)
    assert canonical_source_bytes(source) == canonical_source_bytes(reformatted)


def test_scopes_comprehensions_exceptions_and_matching_keywords_normalise() -> None:
    left = """
class Container:
    factor = 2

def outer(start):
    total = start
    def inner(step):
        nonlocal total
        try:
            values = [item + step for item in range(3)]
        except ValueError as error:
            return str(error)
        total += sum(values)
        return total
    return inner(step=1)

result = outer(start=4)
"""
    right = """
class Holder:
    multiplier = 2

def wrapper(initial):
    aggregate = initial
    def nested(increment):
        nonlocal aggregate
        try:
            numbers = [element + increment for element in range(3)]
        except ValueError as problem:
            return str(problem)
        aggregate += sum(numbers)
        return aggregate
    return nested(increment=1)

output = wrapper(initial=4)
"""

    assert canonical_source_bytes(left) == canonical_source_bytes(right)


def test_global_resolution_is_stable_and_preserved_inputs_stay_literal() -> None:
    left = """
import math as maths
counter = 0
def advance(amount):
    global counter
    counter += amount
    return maths.floor(counter).real
text = "counter and amount stay literal here"
"""
    right = """
import math as maths
state = 0
def move(delta):
    global state
    state += delta
    return maths.floor(state).real
text_value = "counter and amount stay literal here"
"""

    canonical = canonical_source_bytes(left)
    assert canonical == canonical_source_bytes(right)
    assert b"maths" in canonical
    assert b"floor" in canonical
    assert b"real" in canonical
    assert b"counter and amount stay literal here" in canonical


def test_nonlocal_resolves_an_outer_binding_declared_later() -> None:
    left = """
def outer():
    def inner():
        nonlocal value
        value += 1
        return value
    value = 0
    return inner()
"""
    right = """
def wrapper():
    def nested():
        nonlocal count
        count += 1
        return count
    count = 0
    return nested()
"""

    assert canonical_source_bytes(left) == canonical_source_bytes(right)


def test_nonlocal_import_binding_is_preserved() -> None:
    source = (
        "def outer():\n"
        "    import math as maths\n"
        "    def inner():\n"
        "        nonlocal maths\n"
        "        return maths.floor(1.5)\n"
        "    return inner()\n"
    )

    assert b"maths" in canonical_source_bytes(source)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("def broken(:\n", "parse failure"),
        ("__cogos_s0000_b0000 = 1\n", "reserved normalizer prefix"),
        ("from package import *\n", "wildcard import"),
        ("import item\nitem = 1\n", "mapping collision"),
        ("if (value := 1):\n    pass\n", "unsupported syntax"),
        ("def f(value):\n    return locals()[value]\n", "reflection-unsafe"),
        ("def f():\n    snapshot = locals\n    return snapshot()\n", "reflection-unsafe"),
        ("def f(x):\n    return x\nf = 2\n", "ambiguous reassignment"),
    ],
)
def test_unsafe_or_ambiguous_source_fails_closed(source: str, message: str) -> None:
    with pytest.raises(SourceNormalizationError, match=message):
        canonical_source_bytes(source)


def test_semantic_mutation_changes_canonical_bytes() -> None:
    original = "def allowed(value):\n    return value > 3\n"
    mutated = "def allowed(value):\n    return value >= 3\n"

    assert canonical_source_bytes(original) != canonical_source_bytes(mutated)


def test_source_local_name_that_shadows_reflection_builtin_is_not_reflection() -> None:
    left = "def locals():\n    return 1\nvalue = locals()\n"
    right = "def scope_snapshot():\n    return 1\nresult = scope_snapshot()\n"

    assert canonical_source_bytes(left) == canonical_source_bytes(right)
