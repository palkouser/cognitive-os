"""The Sprint 21D5 vertical-slice fixture group. One group, in no role, spent on the spine.

S21D5-024 runs a whole four-candidate group from package to ranking so that a defect in the
spine is found on a group nobody is allowed to count. Running it on a calibration member would
take a scored group out of the hundred before a single number was read, and §6.1 says so in as
many words: the slice spends no calibration case, final member, canary member or retrieval
judgement.

It lives in its own module for the reason D4's does: `reality_task_specs_d5.py` was hashed into
the corpus records by S21D5-020 and into the separation and seal records after it, and a sealed
record is amended, never edited. `_ALL_TEMPLATES` in `reality_tasks` joins the two.

Rendering rather than parsing, deliberately. The released corpora hold four duration groups and
every one of them reads text and returns a number; this one takes a number and returns text, so
it shares a subject with them and no contract.

The two defects are independent and sit at different places. The all-zero fallback is a single
decision taken after the parts exist; the per-unit filter is a decision taken once per unit while
they are being built. Neither repair touches the other's site, which is what lets variant three
and variant four each repair exactly one of them.
"""

from __future__ import annotations

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_task_specs import _test_module
from .reality_task_specs_d2 import D2TaskSpec

D5_FIXTURE_SPEC = D2TaskSpec(
    template_id="d5_fixture.render_duration",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-fixture-render-duration",
    module="duration_rendering",
    module_doc="Rendering a whole number of seconds as a human-readable duration.",
    issue=(
        "render_duration() is documented to render a duration and leave out the units that are "
        "zero. Callers report that a duration of zero comes back empty instead of as '0s', and "
        "that a zero unit sitting between two non-zero ones is printed rather than left out."
    ),
    expected=(
        "render_duration(seconds) returns the hours, minutes and seconds of `seconds` as "
        "'<n>h <n>m <n>s', leaving out every unit whose amount is zero, and returns '0s' when "
        "the whole duration is zero."
    ),
    baseline_reason=(
        "it renders all three units unconditionally and joins them, so it never leaves one out "
        "and has no answer of its own for a duration of nothing"
    ),
    edge_cases=(
        "a duration of zero renders as '0s' rather than as nothing",
        "a zero unit between two non-zero ones is left out",
    ),
    baseline='''def render_duration(seconds):
    """Return `seconds` as a duration, leaving out the units that are zero."""
    hours, rest = divmod(seconds, 3600)
    minutes, whole = divmod(rest, 60)
    parts = [f"{hours}h", f"{minutes}m", f"{whole}s"]
    return " ".join(parts)''',
    variant_one='''def render_duration(seconds):
    """Return `seconds` as a duration, leaving out the units that are zero."""
    hours, rest = divmod(seconds, 3600)
    minutes, whole = divmod(rest, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if whole:
        parts.append(f"{whole}s")
    if not parts:
        return "0s"
    return " ".join(parts)''',
    variant_two='''def render_duration(seconds):
    """Return `seconds` as a duration, leaving out the units that are zero."""
    rest = seconds
    rendered = []
    for suffix, size in (("h", 3600), ("m", 60), ("s", 1)):
        amount, rest = divmod(rest, size)
        if amount:
            rendered.append(str(amount) + suffix)
    return " ".join(rendered) or "0s"''',
    variant_three='''def render_duration(seconds):
    """Return `seconds` as a duration, leaving out the units that are zero."""
    hours, rest = divmod(seconds, 3600)
    minutes, whole = divmod(rest, 60)
    parts = [f"{hours}h", f"{minutes}m", f"{whole}s"]
    if not seconds:
        return "0s"
    return " ".join(parts)''',
    variant_four='''def render_duration(seconds):
    """Return `seconds` as a duration, leaving out the units that are zero."""
    hours, rest = divmod(seconds, 3600)
    minutes, whole = divmod(rest, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if whole:
        parts.append(f"{whole}s")
    return " ".join(parts)''',
    visible_test=_test_module(
        "duration_rendering",
        "Published contract for rendering a duration.",
        """
def test_every_unit_is_rendered_when_none_is_zero() -> None:
    assert render_duration(7325) == "2h 2m 5s"


def test_the_units_are_hours_minutes_and_seconds() -> None:
    assert render_duration(3661) == "1h 1m 1s"
""",
        imports="from duration_rendering import render_duration\n",
    ),
    hidden_test=_test_module(
        "duration_rendering",
        "The part of the contract the published tests do not state.",
        """
def test_every_unit_is_rendered_when_none_is_zero() -> None:
    assert render_duration(7325) == "2h 2m 5s"


def test_a_duration_of_zero_renders_as_zero_seconds() -> None:
    assert render_duration(0) == "0s"


def test_a_zero_unit_between_two_others_is_left_out() -> None:
    assert render_duration(3605) == "1h 5s"
""",
        imports="from duration_rendering import render_duration\n",
    ),
)
