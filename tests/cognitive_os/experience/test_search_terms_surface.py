"""S21D4-040: the one additive field, and the four things it must not disturb.

An additive field with a default is the easiest change to get wrong in a way no test notices,
because everything that already existed keeps working by construction. So these tests are
mostly about the boundary the field is *not* allowed to cross: the structural hash, the node
label, the sealed hash of a graph that carries no terms, and the edit-path round trip.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from cognitive_os.domain.experience_graph import (
    SEARCH_TERMS_CHARACTER_BOUND,
    ActionDecisionGraph,
    ExperienceGraphEdge,
    ExperienceGraphEdgeKind,
    ExperienceGraphNode,
    ExperienceGraphNodeKind,
)
from cognitive_os.experience.graph_projection import (
    SearchSurfaceLeak,
    search_terms_from_source,
)

SOURCE = '''"""A module."""


import os


def repair(target, limit):
    total = 0
    for line in open(target):
        total += len(line.strip())
    return os.path.basename(target), min(total, limit)
'''


def _graph(**overrides: object) -> ActionDecisionGraph:
    fields: dict[str, object] = {
        "graph_id": "g",
        "domain": "coding",
        "group": "grp",
        "task_signature": "sig",
        "accepted": True,
        "nodes": (
            ExperienceGraphNode(
                logical_id="s0001",
                kind=ExperienceGraphNodeKind.OBSERVATION,
                attributes=(("status", "completed"),),
                source_hash="0" * 64,
            ),
            ExperienceGraphNode(
                logical_id="s0002",
                kind=ExperienceGraphNodeKind.CORRECTION,
                attributes=(("status", "completed"),),
                source_hash="1" * 64,
            ),
        ),
        "edges": (
            ExperienceGraphEdge(
                source_id="s0001", target_id="s0002", kind=ExperienceGraphEdgeKind.NEXT
            ),
        ),
        "source_manifest_hash": "2" * 64,
    }
    fields.update(overrides)
    return ActionDecisionGraph(**fields)  # type: ignore[arg-type]


def test_terms_do_not_move_the_structural_hash_or_any_label() -> None:
    """The exclusion the whole contract change rests on."""
    plain = _graph()
    widened = _graph(search_terms=("alpha", "beta"))
    assert widened.structural_hash == plain.structural_hash
    assert [node.label for node in widened.nodes] == [node.label for node in plain.nodes]


def test_a_graph_without_terms_hashes_exactly_as_it_did_before_the_field_existed() -> None:
    """W3-D1. An empty term list is absent from the *canonical* form, at every nesting depth.

    The field still serialises -- the exported JSON Schema and the stored bytes both carry it
    -- and that is the point of putting the rule in the hashing path rather than in the
    serializer: a graph written before this field existed and one written after it hash the
    same, and neither the published schema nor a stored blob changes shape to achieve it.
    """
    plain = _graph()
    dumped = json.loads(plain.model_dump_json())
    assert dumped["search_terms"] == []
    without_the_key = {key: value for key, value in dumped.items() if key != "search_terms"}
    # A file written before the field existed has no key at all. Both must hash alike, or
    # every stored D1 and D3 pair stops loading.
    assert ActionDecisionGraph.model_validate(without_the_key).content_hash == plain.content_hash
    assert ActionDecisionGraph.model_validate(dumped).content_hash == plain.content_hash


def test_a_graph_with_terms_is_new_bytes() -> None:
    """The other half of the same sentence: a widened graph is not the graph it came from."""
    plain = _graph()
    widened = _graph(search_terms=("alpha",))
    assert widened.content_hash != plain.content_hash
    assert "search_terms" in json.loads(widened.model_dump_json())
    assert ActionDecisionGraph.model_validate(
        json.loads(widened.model_dump_json())
    ).search_terms == ("alpha",)


def test_terms_reach_the_ranked_text() -> None:
    """Excluded from identity, included in what an arm reads. Both, or the field is pointless."""
    assert "alpha" not in _graph().search_text()
    assert "alpha" in _graph(search_terms=("alpha",)).search_text()


@pytest.mark.parametrize(
    "terms",
    [
        pytest.param(("zebra", "alpha"), id="uncanonical_order"),
        pytest.param(("alpha", "alpha"), id="repeated"),
        pytest.param(("",), id="empty_term"),
        pytest.param(("password",), id="forbidden_marker"),
        pytest.param(("/home/somebody",), id="host_path"),
        pytest.param(
            tuple(sorted({f"term_{index:05d}" for index in range(200)})), id="over_the_bound"
        ),
    ],
)
def test_the_contract_refuses_what_it_says_it_refuses(terms: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError):
        _graph(search_terms=terms)


def test_the_bound_is_the_node_attribute_bound() -> None:
    """One number, not two: a retrieval surface and a node attribute are the same exposure."""
    assert SEARCH_TERMS_CHARACTER_BOUND == 1024
    fits = tuple(sorted({f"t{index:04d}" for index in range(170)}))
    assert len(" ".join(fits)) <= SEARCH_TERMS_CHARACTER_BOUND
    assert _graph(search_terms=fits).search_terms == fits
    over = tuple(sorted({*fits, "t0170"}))
    assert len(" ".join(over)) > SEARCH_TERMS_CHARACTER_BOUND
    with pytest.raises(ValidationError):
        _graph(search_terms=over)


def test_the_derivation_keeps_preserved_names_and_drops_local_bindings() -> None:
    """The alpha-normaliser is what keeps retrieval from becoming lookup."""
    terms = search_terms_from_source(SOURCE)
    assert "os" in terms and "basename" in terms and "strip" in terms
    assert "len" in terms and "min" in terms and "open" in terms
    # Locals, parameters and the module-scope function name are placeholders after
    # normalisation, so none of them can identify a task. `path` is deliberately absent from
    # this set: it survives as the *attribute* of `os.path`, not as anything a caller named.
    assert not {"total", "line", "target", "limit", "repair"} & set(terms)
    assert list(terms) == sorted(set(terms))
    assert all(not term.startswith("__cogos_") for term in terms)


def test_the_derivation_is_deterministic() -> None:
    assert search_terms_from_source(SOURCE) == search_terms_from_source(SOURCE)


def test_no_string_constant_reaches_the_surface() -> None:
    """`excluded_inputs` in the frozen contract: no unnormalised body, no issue text."""
    terms = search_terms_from_source('def f(x):\n    return "sensitive_marker_text"\n')
    assert not any("sensitive_marker_text" in term for term in terms)


def test_a_leaking_term_refuses_the_whole_projection() -> None:
    """Fail-closed, not filtered: a partially cleaned leak is still a leak."""
    leaking = "def repair(value):\n    return value.parsing_validation()\n"
    assert "parsing_validation" in search_terms_from_source(leaking)
    with pytest.raises(SearchSurfaceLeak):
        search_terms_from_source(leaking, judgement_labels=("parsing_validation",))


def test_the_derived_terms_satisfy_the_contract_they_are_written_into() -> None:
    """The derivation and the field's validator must not disagree about what is legal."""
    assert _graph(search_terms=search_terms_from_source(SOURCE)).search_terms
