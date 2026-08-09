"""Every authored corpus spec resolves to a task the runner can materialise.

This is the check whose absence let S21D5-020 and S21D5-021 land a hundred and sixty specs that
no campaign could run. The spec modules were complete, validated and separated; they were simply
never added to `_ALL_TEMPLATES`, and nothing between authoring and the first `prepare_task` call
asks whether a `template_id` resolves. The corpus validators read the spec tuples directly, so
they were all green.

Parameterised over every released corpus rather than written for D5, because the gap is
structural: a sprint authors a spec module, and the one line that publishes it to the registry
lives in a different file.
"""

from __future__ import annotations

import pytest

from cognitive_os.coding.reality_retrieval_specs_d3 import D3_RETRIEVAL_SPECS
from cognitive_os.coding.reality_retrieval_specs_d4 import D4_RETRIEVAL_SPECS
from cognitive_os.coding.reality_retrieval_specs_d5 import D5_RETRIEVAL_SPECS
from cognitive_os.coding.reality_task_specs import TASK_SPECS
from cognitive_os.coding.reality_task_specs_d2 import D2_TASK_SPECS
from cognitive_os.coding.reality_task_specs_d3 import D3_TASK_SPECS
from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS
from cognitive_os.coding.reality_task_specs_d5 import D5_CALIBRATION_SPECS
from cognitive_os.coding.reality_tasks import template

CORPORA = {
    "c3": TASK_SPECS,
    "d2": D2_TASK_SPECS,
    "d3": D3_TASK_SPECS,
    "d3_retrieval": D3_RETRIEVAL_SPECS,
    "d4": D4_CALIBRATION_SPECS,
    "d4_retrieval": D4_RETRIEVAL_SPECS,
    "d5": D5_CALIBRATION_SPECS,
    "d5_retrieval": D5_RETRIEVAL_SPECS,
}


@pytest.mark.parametrize("corpus", sorted(CORPORA))
def test_every_authored_spec_is_addressable(corpus: str) -> None:
    """An unregistered spec is a task that exists in source and cannot be run."""
    missing = []
    for spec in CORPORA[corpus]:
        try:
            template(spec.template_id)
        except KeyError:
            missing.append(spec.template_id)
    assert not missing, f"{corpus} authored {len(missing)} specs no runner can address: {missing}"


def test_no_two_corpora_claim_one_template_id() -> None:
    """The registries merge into one lookup, so a collision would silently drop a task."""
    seen: dict[str, str] = {}
    collisions = []
    for corpus, specs in sorted(CORPORA.items()):
        for spec in specs:
            previous = seen.setdefault(spec.template_id, corpus)
            if previous != corpus:
                collisions.append(f"{spec.template_id} in both {previous} and {corpus}")
    assert not collisions, collisions
