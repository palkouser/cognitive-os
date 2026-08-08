#!/usr/bin/env python3
"""S21D4-040. The widened searchable surface, and the proof that nothing stored moved.

D3 measured `distinct_after_removing_domain_and_signature: 1` over sixty candidates and drew
the only conclusion available: improving an arm cannot widen a surface. Revision 4 makes the
contract change D3 named and deliberately did not make -- one optional field, excluded from
`structural_hash` and from `ExperienceGraphNode.label`, filled from evidence that already
exists behind each node's `source_hash`.

An additive field is the kind of change that is easy to claim and easy to get wrong, so this
records four separate things rather than one assertion:

*Nothing stored moved.* Every D1 and D3 pair is loaded from its real root and its structural
hashes are recomputed and compared against the values the root declared before this field
existed. Recomputation, not inspection. D2 stored no graph root of its own -- it measured on
D1's -- and that is stated rather than left as a silent gap in "D1, D2 and D3".

*The two frozen sentences are in conflict, and the conflict is measured.* The contract says
`search_terms` is included in `content_hash` and that old graphs still deserialise. Both hold
only if an empty term list is absent from the canonical dump; the measured alternative is
recorded with the exact hash it would have produced.

*The surface actually widens.* Counterfactually, on D3's spent holdout: the same sixty stored
graphs, rehydrated in memory with the terms their released sources produce. Nothing is written
back, and the D4 retrieval pool -- which is still an unseen holdout -- is not read.

*The guards fire.* A judgement leak, a forbidden marker, an over-bound list and an
uncanonical list each have to be refused, because a guard that has only ever seen clean input
is an untested guard.

This command reads. It writes one evidence file and nothing else: both artifact roots are
fingerprinted before and after.

    UV_CACHE_DIR=.cache/uv uv run python scripts/surface_d4.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_integrity import fingerprint  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d3 import (  # noqa: E402
    D3_RETRIEVAL_SPECS,
    D3RetrievalSpec,
)
from cognitive_os.domain.experience_graph import (  # noqa: E402
    SEARCH_TERMS_CHARACTER_BOUND,
    ActionDecisionGraph,
    FailedSuccessGraphPair,
)
from cognitive_os.experience.graph_projection import (  # noqa: E402
    SearchSurfaceLeak,
    round_trips,
    search_terms_from_source,
)
from cognitive_os.experience.graph_store import load_evidence  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d4-contracts.json"
OUTPUT = EVIDENCE / "sprint-21d4-surface.json"

DATA = Path("/home/palkouser/projekt/cognitive-os-data")

#: Every stored graph root this repository holds, with the store that backs it. D2 is absent
#: because D2 wrote none: its retrieval diagnostic measured on D1's root, read-only.
STORED_ROOTS = (
    ("sprint-21d1", EVIDENCE / "sprint-21d1-emg-root.json", DATA / "artifacts-s21d1"),
    ("sprint-21d3", EVIDENCE / "sprint-21d3-retrieval-emg-root.json", DATA / "artifacts-s21d3"),
)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    """The D4 convention: the bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _label_hash(graph: ActionDecisionGraph) -> str:
    """One hash over every node label, which is exactly what labelled GED compares."""
    return _digest(
        "\n".join(
            f"{kind}\t{attributes}" for kind, attributes in (node.label for node in graph.nodes)
        )
    )


# ------------------------------------------------------- the unchanged-hash proof


def _stored_graphs() -> dict[str, Any]:
    """Load every stored pair and recompute what the root declared about it.

    The root manifests were written in D1 and D3, before this field existed. Comparing a
    recomputed hash against them is therefore a comparison against the past, which is the only
    comparison that can answer "byte-unchanged".
    """
    roots: dict[str, Any] = {}
    for name, root, artifacts in STORED_ROOTS:
        declared = {child["pair_id"]: child for child in json.loads(root.read_text())["children"]}
        evidence = load_evidence(root, artifacts)
        moved, label_moved, no_round_trip = [], [], []
        for pair in evidence.pairs:
            row = declared[pair.pair_id]
            if (
                pair.content_hash != row["pair_hash"]
                or pair.failed.structural_hash != row["failed_structural"]
                or pair.successful.structural_hash != row["successful_structural"]
                or pair.edit_path.content_hash != row["edit_path_hash"]
            ):
                moved.append(pair.pair_id)
            # The label is what GED reads. Adding terms to a copy of the graph must not move
            # it -- that is the exclusion, executed rather than read off the field list.
            for side in (pair.failed, pair.successful):
                widened = ActionDecisionGraph.model_validate(
                    {
                        **json.loads(side.model_dump_json()),
                        "content_hash": "",
                        "search_terms": ["probe_term"],
                    }
                )
                if (
                    _label_hash(widened) != _label_hash(side)
                    or widened.structural_hash != side.structural_hash
                ):
                    label_moved.append(f"{pair.pair_id}:{side.graph_id}")
            if not round_trips(pair.failed, pair.successful, pair.edit_path):
                no_round_trip.append(pair.pair_id)
        roots[name] = {
            "root": str(root.relative_to(REPOSITORY)),
            "artifact_root": str(artifacts),
            "declared_pairs": evidence.declared_pairs,
            "pairs_deserialised": len(evidence.pairs),
            "all_declared_pairs_loaded": len(evidence.pairs) == evidence.declared_pairs,
            "intact": evidence.intact,
            "missing_bytes": list(evidence.missing_bytes),
            "corrupt_bytes": list(evidence.corrupt_bytes),
            "broken_links": list(evidence.broken_links),
            "graphs_checked": len(evidence.pairs) * 2,
            "pairs_whose_declared_hashes_moved": moved,
            "graphs_whose_label_or_structure_moved_under_terms": label_moved,
            "edit_paths_that_stopped_round_tripping": no_round_trip,
        }
    return {
        "roots": roots,
        "d2_stored_graph_roots": 0,
        "d2_note": (
            "Sprint 21D2 wrote no graph root. Its retrieval diagnostic measured on the D1 "
            "root read-only, so 'every D1, D2 and D3 stored graph' is these two roots."
        ),
        "pairs_total": sum(row["pairs_deserialised"] for row in roots.values()),
        "graphs_total": sum(row["graphs_checked"] for row in roots.values()),
        "every_stored_hash_unchanged": all(
            not row["pairs_whose_declared_hashes_moved"]
            and not row["graphs_whose_label_or_structure_moved_under_terms"]
            and not row["edit_paths_that_stopped_round_tripping"]
            and row["all_declared_pairs_loaded"]
            and row["intact"]
            for row in roots.values()
        ),
    }


# ------------------------------------------------------- W3-D1


def _w3_d1() -> dict[str, Any]:
    """The contradiction inside the frozen contract, measured on a real stored graph."""
    root = json.loads((EVIDENCE / "sprint-21d3-retrieval-emg-root.json").read_text())
    child = root["children"][0]
    blob = DATA / "artifacts-s21d3" / "sha256" / child["content_hash"][:2] / child["content_hash"]
    stored = json.loads(blob.read_bytes())["failed"]

    def sealed_hash(document: dict[str, Any]) -> str:
        """The canonical hash a contract seals, computed *without* the resolution in force.

        Deliberately not `experience._canonicalize`: that function now carries the very rule
        this finding exists to justify, so measuring through it would compare the fix against
        itself and report that nothing was ever wrong. Plain canonical JSON reproduces the
        released hash exactly for a document loaded from JSON, and `reproduces_the_stored_hash`
        below is the anchor that says so rather than assuming it.
        """
        body = {key: value for key, value in document.items() if key != "content_hash"}
        return _digest(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    as_stored = sealed_hash(stored)
    with_empty_field = sealed_hash({**stored, "search_terms": []})
    return {
        "id": "W3-D1",
        "where": "sprint-21d4-contracts.json, searchable_surface",
        "the_two_sentences": [
            "included_in: content_hash",
            "old stored graphs deserialise unchanged under the default",
        ],
        "why_they_conflict": (
            "HashedExperienceContract.seal_content recomputes the canonical hash on load and "
            "refuses a mismatch, so a field that is unconditionally part of that hash makes "
            "every graph stored before it unloadable."
        ),
        "measured_on": f"{child['pair_id']}:failed",
        "hash_as_stored": as_stored,
        "reproduces_the_stored_content_hash": as_stored == stored["content_hash"],
        "hash_if_the_empty_field_were_included": with_empty_field,
        "identical": as_stored == with_empty_field,
        "stored_pairs_that_would_stop_loading": 140,
        "resolution": (
            "An empty term list is absent from the canonical form at every nesting depth, "
            "named once in domain.experience.CANONICAL_ABSENT_WHEN_EMPTY. A graph carrying "
            "terms is new bytes, as the contract requires; a graph carrying none hashes "
            "exactly as it did before the field existed, as the contract also requires. No "
            "other reading satisfies both."
        ),
        "resolution_placed_in": (
            "the hashing path, not the serializer. A model serializer that dropped the empty "
            "key collapsed the exported JSON Schema for ActionDecisionGraph and "
            "FailedSuccessGraphPair from 258 lines to 4, because pydantic cannot infer a "
            "serialization schema through a wrap serializer. The published schema gains eight "
            "additive lines instead."
        ),
        "contract_amended_not_edited": True,
        "affects_any_published_number": False,
    }


# ------------------------------------------------------- the widened document surface


def _counterfactual(pairs: list[FailedSuccessGraphPair]) -> dict[str, Any]:
    """What D3's sixty documents would have been under the widened surface.

    Counterfactual and in memory. The stored graphs are not rewritten, D3's root is not
    touched, and the D4 retrieval pool -- still an unseen holdout -- is not read at all. The
    point is the count, and the count is the D3 finding's direct answer.
    """
    specs: dict[str, D3RetrievalSpec] = {spec.repository_group: spec for spec in D3_RETRIEVAL_SPECS}
    before_documents, after_documents = [], []
    before_without_signature, after_without_signature = [], []
    term_counts, widened = [], []
    for pair in sorted(pairs, key=lambda item: item.pair_id):
        spec = specs[pair.pair_id]
        labels = (spec.family.value, spec.family.value.replace("_", " "), pair.pair_id)
        terms = search_terms_from_source(spec.module_text(spec.repaired), judgement_labels=labels)
        rehydrated = ActionDecisionGraph.model_validate(
            {
                **json.loads(pair.successful.model_dump_json()),
                "content_hash": "",
                "search_terms": list(terms),
            }
        )
        before_documents.append(pair.successful.search_text())
        after_documents.append(rehydrated.search_text())
        before_without_signature.append("\n".join(pair.successful.search_text().splitlines()[2:]))
        after_without_signature.append("\n".join(rehydrated.search_text().splitlines()[2:]))
        term_counts.append(len(terms))
        widened.append(
            {
                "pair_id": pair.pair_id,
                "family": spec.family.value,
                "terms": len(terms),
                "term_key": " ".join(terms),
                "characters": len(" ".join(terms)),
                "content_hash_moved": rehydrated.content_hash != pair.successful.content_hash,
            }
        )

    # Which groups the widened surface still cannot tell apart, and whether that matters.
    # Relevance here is the task family, so two groups sharing a term list inside one family
    # are two relevant documents and cost the ranking nothing; the same collision across two
    # families is a document that can be reached by the wrong query.
    by_terms: dict[str, list[dict[str, Any]]] = {}
    for row in widened:
        by_terms.setdefault(row["term_key"], []).append(row)
    collisions = [rows for rows in by_terms.values() if len(rows) > 1]
    cross_family = [
        sorted(row["pair_id"] for row in rows)
        for rows in collisions
        if len({row["family"] for row in rows}) > 1
    ]
    return {
        "measured_on": "sprint-21d3-retrieval-holdout, spent",
        "written_back": False,
        "d4_retrieval_pool_read": False,
        "candidates": len(widened),
        "distinct_documents_before": len(set(before_documents)),
        "distinct_documents_after": len(set(after_documents)),
        "distinct_after_removing_domain_and_signature_before": len(set(before_without_signature)),
        "distinct_after_removing_domain_and_signature_after": len(set(after_without_signature)),
        "terms_minimum": min(term_counts),
        "terms_median": sorted(term_counts)[len(term_counts) // 2],
        "terms_maximum": max(term_counts),
        "character_bound": SEARCH_TERMS_CHARACTER_BOUND,
        "groups_with_no_terms": [row["pair_id"] for row in widened if not row["terms"]],
        "colliding_term_sets": len(collisions),
        "groups_in_a_collision": sum(len(rows) for rows in collisions),
        "cross_family_collisions": cross_family,
        "every_graph_that_gained_a_term_is_new_bytes": all(
            row["content_hash_moved"] for row in widened if row["terms"]
        ),
        "a_termless_graph_keeps_its_bytes": all(
            not row["content_hash_moved"] for row in widened if not row["terms"]
        ),
        "per_pair": widened,
    }


# ------------------------------------------------------- the guards


def _guards() -> dict[str, Any]:
    """Four refusals, each executed against the released code rather than described."""
    results: dict[str, Any] = {}

    # The leak has to be planted where the normaliser preserves it. A module-scope function
    # named after its own family is alpha-normalised to a placeholder and never reaches the
    # surface at all -- measured beside the refusal, because "the guard did not fire" and "the
    # term never existed" are the same observation until they are told apart.
    leaking = '"""A repair."""\n\n\ndef repair(value):\n    return value.parsing_validation()\n'
    try:
        search_terms_from_source(leaking, judgement_labels=("parsing_validation",))
        results["judgement_leak_refused"] = False
    except SearchSurfaceLeak as error:
        results["judgement_leak_refused"] = True
        results["judgement_leak_message"] = str(error)
    normalised_away = '"""A repair."""\n\n\ndef parsing_validation(value):\n    return value\n'
    results["a_module_scope_name_never_reaches_the_surface"] = (
        search_terms_from_source(normalised_away) == ()
    )

    base = json.loads(
        ActionDecisionGraph(
            graph_id="guard",
            domain="coding",
            group="guard",
            task_signature="guard",
            accepted=True,
            nodes=(
                {
                    "logical_id": "s0001",
                    "kind": "observation",
                    "attributes": (("status", "completed"),),
                    "source_hash": "0" * 64,
                },
            ),
            source_manifest_hash="1" * 64,
        ).model_dump_json()
    )

    def refuses(terms: list[str]) -> bool:
        try:
            ActionDecisionGraph.model_validate({**base, "content_hash": "", "search_terms": terms})
        except ValueError:
            return True
        return False

    results["forbidden_marker_refused"] = refuses(["password"])
    results["uncanonical_order_refused"] = refuses(["zebra", "alpha"])
    results["repeated_term_refused"] = refuses(["alpha", "alpha"])
    results["over_bound_list_refused"] = refuses(
        sorted({f"term_{index:05d}" for index in range(200)})
    )
    results["a_clean_list_is_accepted"] = not refuses(["alpha", "zebra"])
    results["all_guards_fired"] = all(
        value
        for key, value in results.items()
        if key.endswith("_refused")
        or key in {"a_clean_list_is_accepted", "a_module_scope_name_never_reaches_the_surface"}
    )
    return results


def _w3_f1(counterfactual: dict[str, Any]) -> dict[str, Any]:
    """The design claim the measurement does not support, stated as the number it produced."""
    return {
        "id": "W3-F1",
        "kind": "measured_limitation",
        "where": "backlog section 4.5",
        "the_claim": ("This is the minimum that makes sixty repair trajectories sixty documents."),
        "measured": {
            "distinct_documents_after_removing_domain_and_signature": counterfactual[
                "distinct_after_removing_domain_and_signature_after"
            ],
            "of_candidates": counterfactual["candidates"],
            "groups_with_no_terms": len(counterfactual["groups_with_no_terms"]),
            "colliding_term_sets": counterfactual["colliding_term_sets"],
            "cross_family_collisions": len(counterfactual["cross_family_collisions"]),
        },
        "why": (
            "The frozen derivation preserves imports, attributes, builtins and magic names and "
            "replaces every local binding with a placeholder. A repair written in pure "
            "arithmetic over its own parameters therefore has nothing left to preserve, and "
            "seven of D3's sixty groups produce no term at all -- exactly as indistinguishable "
            "as they were before the field existed."
        ),
        "not_repaired_here": (
            "Widening the extraction past the frozen derivation after seeing which groups "
            "collide would be tuning a retrieval surface on a measurement of that surface. "
            "The derivation stands as pre-registered; S21D4-044 measures the D4 pool, which "
            "is the pool the holdout result is read from."
        ),
        "measured_on": "the spent D3 holdout, not the D4 pool",
        "affects_any_published_number": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    before = {name: fingerprint(root) for name, _, root in STORED_ROOTS}
    stored = _stored_graphs()
    d3 = load_evidence(EVIDENCE / "sprint-21d3-retrieval-emg-root.json", DATA / "artifacts-s21d3")
    counterfactual = _counterfactual(list(d3.pairs))
    guards = _guards()
    after = {name: fingerprint(root) for name, _, root in STORED_ROOTS}

    evidence = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W3",
        "items": ["S21D4-040"],
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
        "contracts_sha256": _digest(CONTRACTS.read_bytes()),
        "field": "ActionDecisionGraph.search_terms: tuple[str, ...] = ()",
        "excluded_from": ["structural_hash", "ExperienceGraphNode.label"],
        "included_in": ["content_hash when non-empty", "search_text()"],
        "derivation": [
            "the source behind the trajectory, resolved by the caller through the released store",
            "normalised by correction_source.canonical_source_bytes, the released v2 normaliser",
            "identifiers preserved by that normaliser, placeholders dropped, sorted and unique",
            f"bounded at {SEARCH_TERMS_CHARACTER_BOUND} characters, the node-attribute bound",
            "refused whole when reality_leakage.judgement_leaks reports a hit",
        ],
        "stored_graphs": stored,
        "findings": [_w3_d1(), _w3_f1(counterfactual)],
        "document_surface": counterfactual,
        "guards": guards,
        "store_writes": {
            "fingerprints_before": before,
            "fingerprints_after": after,
            "unchanged": before == after,
        },
        "final_or_canary_outcomes_inspected": 0,
        "final_outcomes_inspected": False,
    }
    sealed = _seal(evidence)
    arguments.output.write_text(
        json.dumps(sealed, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"{arguments.output.relative_to(REPOSITORY)}")
    print(
        f"  stored graphs unchanged: {stored['every_stored_hash_unchanged']} "
        f"({stored['graphs_total']} graphs in {stored['pairs_total']} pairs)"
    )
    print(
        "  distinct documents (domain and signature removed): "
        f"{counterfactual['distinct_after_removing_domain_and_signature_before']} -> "
        f"{counterfactual['distinct_after_removing_domain_and_signature_after']} "
        f"of {counterfactual['candidates']}"
    )
    print(f"  guards fired: {guards['all_guards_fired']}")
    print(f"  store writes: {0 if before == after else -1}")
    print(f"  seal {sealed['integrity_content_hash']}")
    return (
        0
        if stored["every_stored_hash_unchanged"] and guards["all_guards_fired"] and before == after
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
