"""S21D4-033: the vertical-slice fixture group obeys the corpus's authoring contract.

The slice is only a spine proof if its group is a real four-candidate decision: a baseline the
visible suite cannot fault, two repairs that hold, and two partial fixes that a visible suite
cannot tell from the repairs. A fixture that failed its own visible suite, or whose two declared
edge cases were one defect wearing two names, would make the ranking meaningless before the
pipeline ever ran.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from cognitive_os.coding.reality_fixture_spec_d4 import D4_FIXTURE_SPEC
from cognitive_os.coding.reality_task_specs_d2 import module_source

#: `body -> (passes visible, passes hidden)`, straight from the corpus authoring contract.
CONTRACT = {
    "baseline": (True, False),
    "variant_one": (True, True),
    "variant_two": (True, True),
    "variant_three": (True, False),
    "variant_four": (True, False),
}


def _passes(root: Path, suite: str) -> bool:
    (root / "test_suite.py").write_text(suite, encoding="utf-8")
    return (
        subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "test_suite.py"],
            cwd=root,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def _run(body: str) -> tuple[bool, bool]:
    spec = D4_FIXTURE_SPEC
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / f"{spec.module}.py").write_text(module_source(spec, body), encoding="utf-8")
        return _passes(root, spec.visible_test), _passes(root, spec.hidden_test)


@pytest.mark.parametrize(("name", "expected"), sorted(CONTRACT.items()))
def test_each_body_behaves_the_way_the_spec_declares(
    name: str, expected: tuple[bool, bool]
) -> None:
    assert _run(getattr(D4_FIXTURE_SPEC, name)) == expected


def test_the_two_declared_edge_cases_are_two_defects() -> None:
    """Variant three repairs the first and not the second; variant four the reverse.

    If one repair fixed both, the group would be one defect declared twice and the partial
    fixes would be indistinguishable from the correct ones.
    """
    namespaces: dict[str, dict[str, object]] = {}
    for name in ("baseline", "variant_one", "variant_three", "variant_four"):
        namespace: dict[str, object] = {}
        exec(getattr(D4_FIXTURE_SPEC, name), namespace)  # the corpus body under test
        namespaces[name] = namespace

    def wrap(name: str, words: list[str], width: int) -> object:
        return namespaces[name]["wrap_words"](words, width)  # type: ignore[operator]

    long_first = (["abcdefghijk", "hi"], 5)
    empty = ([], 10)
    assert wrap("baseline", *long_first) == ["", "abcdefghijk", "hi"]
    assert wrap("baseline", *empty) == [""]
    # Edge case one only.
    assert wrap("variant_three", *long_first) == ["abcdefghijk", "hi"]
    assert wrap("variant_three", *empty) == [""]
    # Edge case two only.
    assert wrap("variant_four", *long_first) == ["", "abcdefghijk", "hi"]
    assert wrap("variant_four", *empty) == []
    # Both.
    assert wrap("variant_one", *long_first) == ["abcdefghijk", "hi"]
    assert wrap("variant_one", *empty) == []


def test_the_visible_suite_exercises_neither_declared_edge_case() -> None:
    """A visible test that caught a partial fix would turn the decision into a lookup."""
    assert len(D4_FIXTURE_SPEC.edge_cases) == 2
    visible = D4_FIXTURE_SPEC.visible_test
    assert "abcdefghijk" not in visible
    assert "wrap_words([], " not in visible
