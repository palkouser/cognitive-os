"""The Sprint 21D4 vertical-slice fixture group. One group, in no role, spent on the spine.

S21D4-033 runs a whole four-candidate group from package to ranking so that a defect in the v2
spine is found on a group nobody is allowed to count. Running it on a calibration member would
take a scored group out of the hundred before a single number was read, and Section 6.1 says so
in as many words: the slice spends no calibration case, final member, canary member or retrieval
judgement.

It lives in its own module rather than at the bottom of `reality_task_specs_d4.py`, where that
module's docstring anticipated it, because the corpus file's SHA-256 was sealed into
`evidence/sprint-21d4-corpus.json` by S21D4-030 before this fixture was authored. A sealed record
is amended, never edited, so the fixture moved instead of the seal. `_ALL_TEMPLATES` in
`reality_tasks` joins the two, which is where the registry needed them joined anyway.

The authoring contract is the corpus's, unchanged: the baseline passes the visible suite and
fails the hidden one, variants one and two repair the contract by materially different routes,
and variants three and four each repair exactly one declared edge case. The two defects here are
independent — a leading empty line comes from the flush inside the loop, an empty result from the
flush after it, and neither repair touches the other's site.
"""

from __future__ import annotations

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_task_specs import _test_module
from .reality_task_specs_d2 import D2TaskSpec

D4_FIXTURE_SPEC = D2TaskSpec(
    template_id="d4_fixture.wrap_words",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-fixture-wrap-words",
    module="word_wrapping",
    module_doc="Grouping words into lines of a bounded width.",
    issue=(
        "wrap_words() is documented to group words into lines no wider than a limit. Callers "
        "report that a word longer than the limit is preceded by a blank line, and that an "
        "empty list of words produces one empty line instead of no lines at all."
    ),
    expected=(
        "wrap_words(words, width) returns the lines produced by joining consecutive words with "
        "single spaces while the joined line stays within width, opens no line before the first "
        "word however long it is, and returns no lines for no words."
    ),
    baseline_reason=(
        "it flushes the line in progress without checking that anything is in it, both inside "
        "the loop and after it"
    ),
    edge_cases=(
        "a word longer than the width opens no blank line before it",
        "an empty list of words produces no lines",
    ),
    baseline="""def wrap_words(words, width):
    \"\"\"Return `words` grouped into lines no wider than `width`.\"\"\"
    lines = []
    current = []
    for word in words:
        if len(" ".join(current + [word])) <= width:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    lines.append(" ".join(current))
    return lines""",
    variant_one="""def wrap_words(words, width):
    \"\"\"Return `words` grouped into lines no wider than `width`.\"\"\"
    lines = []
    current = []
    for word in words:
        if current and len(" ".join(current + [word])) > width:
            lines.append(" ".join(current))
            current = []
        current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines""",
    variant_two="""def wrap_words(words, width):
    \"\"\"Return `words` grouped into lines no wider than `width`.\"\"\"
    lines = []
    line = ""
    for word in words:
        candidate = f"{line} {word}" if line else word
        if line and len(candidate) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines""",
    variant_three="""def wrap_words(words, width):
    \"\"\"Return `words` grouped into lines no wider than `width`.\"\"\"
    lines = []
    current = []
    for word in words:
        if current and len(" ".join(current + [word])) > width:
            lines.append(" ".join(current))
            current = []
        current.append(word)
    lines.append(" ".join(current))
    return lines""",
    variant_four="""def wrap_words(words, width):
    \"\"\"Return `words` grouped into lines no wider than `width`.\"\"\"
    lines = []
    current = []
    for word in words:
        if len(" ".join(current + [word])) <= width:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines""",
    visible_test=_test_module(
        "word_wrapping",
        "Published contract for grouping words into bounded lines.",
        """
def test_words_fill_a_line_up_to_the_width() -> None:
    assert wrap_words(["one", "two", "three"], 7) == ["one two", "three"]


def test_a_single_word_within_the_width_is_one_line() -> None:
    assert wrap_words(["alpha"], 5) == ["alpha"]
""",
        imports="from word_wrapping import wrap_words\n",
    ),
    hidden_test=_test_module(
        "word_wrapping",
        "The part of the contract the published tests do not state.",
        """
def test_words_fill_a_line_up_to_the_width() -> None:
    assert wrap_words(["one", "two", "three"], 7) == ["one two", "three"]


def test_a_long_first_word_opens_no_blank_line() -> None:
    assert wrap_words(["abcdefghijk", "hi"], 5) == ["abcdefghijk", "hi"]


def test_no_words_produce_no_lines() -> None:
    assert wrap_words([], 10) == []
""",
        imports="from word_wrapping import wrap_words\n",
    ),
)
