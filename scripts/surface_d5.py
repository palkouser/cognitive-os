#!/usr/bin/env python3
"""S21D5-040 and S21D5-041. The complete surface, projected on D5's corpus and measured there.

D4 built the widened surface and measured it on D4's pool: 41 of 60 documents distinct, ten
candidates carrying no term at all because their repairs were pure arithmetic over their own
parameters. `structure_fallback` is the released answer to that residual, off by default at
every call site. D5 turns it on for its own projection, and this is where that is executed
rather than assumed.

Five things, each run rather than described:

*The pairs project.* Every one of the 120 D5 retrieval sides is projected under the complete
surface, and the terms come off `canonical_source_bytes` — the released v2 normaliser — not off
the spec table's prose.

*Nothing stored moved.* Every D1, D3 and D4 stored pair is loaded from its real root and its
declared hashes are recomputed and compared. Turning a default-off flag on for a new projection
must not touch a byte of released evidence, and recomputation is the only way to say so.

*The exclusions hold.* A graph carrying terms and the same graph without them must agree on
`structural_hash` and on every node label, because those are what a structural comparator and
labelled GED read. Executed on the stored graphs rather than read off a field list.

*The guards fire.* A judgement leak, a forbidden marker, an uncanonical list, a repeated term
and an over-bound list each have to be refused. A guard that has only ever seen clean input is
an untested guard.

*The completion is measured on D5's corpus, not D4's.* Reached fraction, empty fraction,
distinctness, and how many sides needed the fallback to be non-empty at all.

This command reads. It writes one evidence file and nothing else; every artifact root it opens
is fingerprinted before and after.

    UV_CACHE_DIR=.cache/uv uv run python scripts/surface_d5.py
"""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_integrity import fingerprint  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d3 import D3RetrievalSpec  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d5 import D5_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.experience_graph import (  # noqa: E402
    SEARCH_TERMS_CHARACTER_BOUND,
    ActionDecisionGraph,
)
from cognitive_os.experience.graph_projection import (  # noqa: E402
    SearchSurfaceLeak,
    round_trips,
    search_terms_from_source,
)
from cognitive_os.experience.graph_store import load_evidence  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d5-contracts.json"
SEPARATION = EVIDENCE / "sprint-21d5-corpus-separation.json"
SEALED_MANIFESTS = EVIDENCE / "sprint-21d5-sealed-manifests.json"
D4_SURFACE = EVIDENCE / "sprint-21d4-surface.json"
OUTPUT = EVIDENCE / "sprint-21d5-surface.json"

DATA = Path("/home/palkouser/projekt/cognitive-os-data")

#: Every graph root the programme has released, with the store that backs it. All three are
#: read-only here: D5 writes to its own pair and to nothing else.
STORED_ROOTS = (
    ("sprint-21d1", EVIDENCE / "sprint-21d1-emg-root.json", DATA / "artifacts-s21d1"),
    ("sprint-21d3", EVIDENCE / "sprint-21d3-retrieval-emg-root.json", DATA / "artifacts-s21d3"),
    ("sprint-21d4", EVIDENCE / "sprint-21d4-retrieval-emg-root.json", DATA / "artifacts-s21d4"),
)

#: D4's released measurement, for context. Not a controlled comparison and labelled as such
#: wherever it appears: different pool, different bodies, and the flag was off there.
D4_DISTINCT_DOCUMENTS = 41
D4_CANDIDATES = 60


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    """The convention every D4 and D5 record shares: hashed bytes are written bytes."""
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


def _labels(spec: D3RetrievalSpec) -> tuple[str, ...]:
    """What relevance is judged by here, in every spelling a term could carry it."""
    return (spec.family.value, spec.family.value.replace("_", " "), spec.repository_group)


# ------------------------------------------------------------------- S21D5-040: the projection


def _projected() -> list[dict[str, Any]]:
    """Both sides of all sixty groups, with the flag off and with it on.

    Off as well as on, because "the fallback answered the residual" is a claim about a
    difference, and a record that only ever ran the flag on has no second number to show it.
    """
    rows: list[dict[str, Any]] = []
    for spec in D5_RETRIEVAL_SPECS:
        labels = _labels(spec)
        for side, body in (("failed", spec.failed), ("repaired", spec.repaired)):
            source = spec.module_text(body)
            released = search_terms_from_source(source, judgement_labels=labels)
            complete = search_terms_from_source(
                source, judgement_labels=labels, structure_fallback=True
            )
            rows.append(
                {
                    "group": spec.repository_group,
                    "family": spec.family.value,
                    "side": side,
                    "terms_under_the_released_extraction": len(released),
                    "terms_under_the_complete_surface": len(complete),
                    "needed_the_fallback": not released and bool(complete),
                    "empty_under_the_complete_surface": not complete,
                    "term_key": " ".join(complete),
                    "characters": len(" ".join(complete)),
                    "within_the_character_bound": (
                        len(" ".join(complete)) <= SEARCH_TERMS_CHARACTER_BOUND
                    ),
                }
            )
    return rows


def _stored_graphs() -> dict[str, Any]:
    """Load every stored pair, recompute what its root declared, and probe the exclusions.

    The roots were written before D5 existed, so comparing a recomputed hash against them is a
    comparison against the past — the only comparison that can answer "byte-unchanged". The
    probe adds a term to an in-memory copy and requires the structural hash and every node
    label to stay put; that is the exclusion executed rather than read off a field list.
    """
    roots: dict[str, Any] = {}
    for name, root, artifacts in STORED_ROOTS:
        declared = {child["pair_id"]: child for child in json.loads(root.read_text())["children"]}
        evidence = load_evidence(root, artifacts)
        moved, label_moved, no_round_trip, carrying = [], [], [], 0
        for pair in evidence.pairs:
            row = declared[pair.pair_id]
            if (
                pair.content_hash != row["pair_hash"]
                or pair.failed.structural_hash != row["failed_structural"]
                or pair.successful.structural_hash != row["successful_structural"]
                or pair.edit_path.content_hash != row["edit_path_hash"]
            ):
                moved.append(pair.pair_id)
            for graph in (pair.failed, pair.successful):
                carrying += 1 if graph.search_terms else 0
                widened = ActionDecisionGraph.model_validate(
                    {
                        **json.loads(graph.model_dump_json()),
                        "content_hash": "",
                        "search_terms": sorted({*graph.search_terms, "probe_term"}),
                    }
                )
                if (
                    _label_hash(widened) != _label_hash(graph)
                    or widened.structural_hash != graph.structural_hash
                ):
                    label_moved.append(f"{pair.pair_id}:{graph.graph_id}")
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
            "graphs_already_carrying_terms": carrying,
            "pairs_whose_declared_hashes_moved": moved,
            "graphs_whose_label_or_structure_moved_under_terms": label_moved,
            "edit_paths_that_stopped_round_tripping": no_round_trip,
        }
    resolvable = {name: row for name, row in roots.items() if row["pairs_deserialised"]}
    unresolvable = sorted(set(roots) - set(resolvable))
    return {
        "roots": roots,
        "pairs_total": sum(row["pairs_deserialised"] for row in roots.values()),
        "graphs_total": sum(row["graphs_checked"] for row in roots.values()),
        "d2_stored_graph_roots": 0,
        "d2_note": (
            "Sprint 21D2 wrote no graph root; its retrieval diagnostic measured on D1's root "
            "read-only, so 'every stored graph' is these three roots"
        ),
        "roots_that_resolve": sorted(resolvable),
        "roots_that_do_not_resolve": unresolvable,
        # Split on purpose. "A declared pair whose recomputed hash disagrees with its root" is a
        # regression this wave could have caused; "a declared pair whose bytes are not in any
        # store" is an availability fact about released evidence, and folding the two together
        # would let either hide behind the other.
        "every_resolvable_hash_unchanged": all(
            not row["pairs_whose_declared_hashes_moved"]
            and not row["graphs_whose_label_or_structure_moved_under_terms"]
            and not row["edit_paths_that_stopped_round_tripping"]
            and row["all_declared_pairs_loaded"]
            and row["intact"]
            for row in resolvable.values()
        ),
        "finding_when_a_root_does_not_resolve": _w3_f1(roots) if unresolvable else None,
    }


def _w3_f1(roots: dict[str, Any]) -> dict[str, Any]:
    """S21D5-W3-F1: a released graph set whose bytes are no longer anywhere."""
    return {
        "id": "S21D5-W3-F1",
        "what": (
            "sprint-21d4-retrieval-emg-root.json declares 60 pairs and none of their blobs "
            "resolves. The root file is byte-identical to the one S21D4-044 recorded "
            "(0960818f07981523…), and that record reports resolved_pairs: 60, intact: true, so "
            "the bytes existed when D4 wrote them"
        ),
        "searched": (
            "every file under cognitive-os-data, including backups, by all five hashes each "
            "root child declares. 0 of 60 found under any of them"
        ),
        "when_it_happened_is_not_determinable_from_evidence": (
            "D4 released no fingerprint of its own artifact store. sprint-21d4-operations.json "
            "recorded artifacts-s21d4 at 3,990 files before and after W7, and the D5 baseline's "
            "first observation is 4,006 with 'no released expectation exists'. Neither count "
            "can be decomposed into which files they were"
        ),
        "consequence_for_d5": (
            "the D4 retrieval pool cannot serve as a development replay pool in S21D5-042 and "
            "its numbers cannot be re-derived from its graphs. Its released result record "
            "remains valid evidence of what was measured; it is simply no longer re-runnable"
        ),
        "consequence_for_d5_s_own_holdout": (
            "none. D5 projects, stores and reads its own pairs in its own store, and S21D5-044 "
            "verifies them by loading them back through the released graph store"
        ),
        "not_repaired_here": (
            "regenerating the blobs would mean re-executing D4's sixty groups under D5's "
            "runner and calling the result D4's evidence. A missing predecessor blob is "
            "recorded, not reconstructed"
        ),
        "per_root": {
            name: {
                "declared_pairs": row["declared_pairs"],
                "pairs_deserialised": row["pairs_deserialised"],
                "missing_bytes": len(row["missing_bytes"]),
            }
            for name, row in roots.items()
        },
    }


def _guards() -> dict[str, Any]:
    """Every refusal on this path, executed against the released code.

    The leak has to be planted where the normaliser preserves it: a module-scope function named
    after its own family is alpha-normalised to a placeholder and never reaches the surface at
    all, so "the guard did not fire" and "the term never existed" are measured apart.
    """
    results: dict[str, Any] = {}
    leaking = '"""A repair."""\n\n\ndef repair(value):\n    return value.parsing_validation()\n'
    try:
        search_terms_from_source(leaking, judgement_labels=("parsing_validation",))
        results["judgement_leak_refused"] = False
    except SearchSurfaceLeak as error:
        results["judgement_leak_refused"] = True
        results["judgement_leak_message"] = str(error)

    # The same refusal with the flag on. The fallback produces node-type terms from the same
    # dump, and a fallback that bypassed the guard would be a new way to leak a judgement.
    arithmetic = '"""A repair."""\n\n\ndef repair(a, b):\n    return a * 2 + b\n'
    fallback_terms = search_terms_from_source(arithmetic, structure_fallback=True)
    results["the_fallback_produces_terms_where_the_released_extraction_does_not"] = (
        search_terms_from_source(arithmetic) == () and bool(fallback_terms)
    )
    results["fallback_terms_on_the_probe"] = list(fallback_terms)
    try:
        search_terms_from_source(
            arithmetic, judgement_labels=fallback_terms[:1], structure_fallback=True
        )
        results["a_leaking_fallback_term_refused"] = False
    except SearchSurfaceLeak:
        results["a_leaking_fallback_term_refused"] = True

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
        or key
        in {
            "a_clean_list_is_accepted",
            "a_module_scope_name_never_reaches_the_surface",
            "the_fallback_produces_terms_where_the_released_extraction_does_not",
        }
    )
    return results


# ------------------------------------------------------------------- S21D5-041: the completion


def _completion(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Reached, empty and distinct — on D5's corpus, which is the whole point of the item."""
    repaired = [row for row in rows if row["side"] == "repaired"]
    by_terms: dict[str, list[dict[str, Any]]] = {}
    for row in repaired:
        by_terms.setdefault(row["term_key"], []).append(row)
    collisions = [group for group in by_terms.values() if len(group) > 1]
    cross_family = [
        sorted(row["group"] for row in group)
        for group in collisions
        if len({row["family"] for row in group}) > 1
    ]
    pairs: dict[str, dict[str, str]] = {}
    for row in rows:
        pairs.setdefault(row["group"], {})[row["side"]] = row["term_key"]
    identical_sides = sorted(
        group for group, sides in pairs.items() if sides["failed"] == sides["repaired"]
    )
    counts = sorted(row["terms_under_the_complete_surface"] for row in rows)
    empty = [
        f"{row['group']}:{row['side']}" for row in rows if row["empty_under_the_complete_surface"]
    ]
    return {
        "measured_on": "the sixty D5 retrieval groups authored by S21D5-021",
        "sides": len(rows),
        "candidates": len(repaired),
        "sides_carrying_terms": len(rows) - len(empty),
        "sides_empty_under_the_complete_surface": empty,
        "sides_that_needed_the_fallback": sum(1 for row in rows if row["needed_the_fallback"]),
        "sides_empty_under_the_released_extraction": sum(
            1 for row in rows if not row["terms_under_the_released_extraction"]
        ),
        "reached_fraction": round((len(rows) - len(empty)) / len(rows), 4),
        "empty_fraction": round(len(empty) / len(rows), 4),
        "distinct_candidate_term_sets": len({row["term_key"] for row in repaired}),
        "pairs_whose_two_sides_carry_the_same_terms": identical_sides,
        "colliding_term_sets": len(collisions),
        "candidates_in_a_collision": sum(len(group) for group in collisions),
        "cross_family_collisions": cross_family,
        "terms_minimum": counts[0],
        "terms_median": counts[len(counts) // 2],
        "terms_maximum": counts[-1],
        "character_bound": SEARCH_TERMS_CHARACTER_BOUND,
        "every_side_within_the_character_bound": all(
            row["within_the_character_bound"] for row in rows
        ),
        "d4_released_reading": {
            "distinct_documents": D4_DISTINCT_DOCUMENTS,
            "candidates": D4_CANDIDATES,
            "candidates_with_no_terms": 10,
            "not_a_controlled_comparison": (
                "a different pool, different bodies, and the fallback off. D4's 41 of 60 is "
                "context for what the residual looked like, not a before-value this number "
                "improves on"
            ),
            "and_not_even_the_same_quantity": (
                "D4's 41 counts distinct *documents* with domain and signature removed, over "
                "projected graphs. The number beside it here counts distinct term sets over "
                "sources, because no graph exists yet at this item. The comparable measurement "
                "is S21D5-044's discriminability block, taken on the real projected pairs"
            ),
        },
        "cross_family_collision_reading": (
            "two term sets shared across families are two documents a query from the wrong "
            "family can reach, which is the shape that costs ranking. Within a family a shared "
            "term set costs nothing: both documents are relevant to the same query. Both counts "
            "are above; the searchable document also carries domain and task signature, so a "
            "shared term set is not a shared document"
        ),
        "why_a_same_term_pair_would_matter": (
            "a pair whose failed and repaired sides project the same document is retrievable "
            "and uninformative: it drags MRR down while looking healthy. S21D5-021 found nine "
            "and re-authored every one; this is the same check at the surface the holdout will "
            "actually be ranked on"
        ),
    }


def _run(output: Path) -> int:
    before = {name: fingerprint(root) for name, _, root in STORED_ROOTS}
    rows = _projected()
    stored = _stored_graphs()
    guards = _guards()
    completion = _completion(rows)
    after = {name: fingerprint(root) for name, _, root in STORED_ROOTS}

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W3",
            "items": ["S21D5-040", "S21D5-041"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "separation_sha256": _digest(SEPARATION.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "d4_surface_sha256": _digest(D4_SURFACE.read_bytes()),
            "final_outcomes_inspected": False,
            "holdout_resolved_here": False,
            "surface": {
                "structure_fallback": True,
                "released_default": False,
                "excluded_from": ["structural_hash", "ExperienceGraphNode.label"],
                "rule": (
                    "a source whose identifier terms come up empty falls back to its lowercased "
                    "AST node-type terms from the same canonical dump, minus bookkeeping nodes"
                ),
                "terms_read_off": "canonical_source_bytes, the released v2 alpha-normaliser",
            },
            "projection": {
                "groups": len(D5_RETRIEVAL_SPECS),
                "sides": len(rows),
                "projected_with_the_flag_off_as_well": True,
                "why_both": (
                    "'the fallback answered the D4 residual' is a claim about a difference, and "
                    "a record that only ran the flag on has no second number to show it"
                ),
                "per_side": rows,
            },
            "stored_evidence_unchanged": stored,
            "guards": guards,
            "completion": completion,
            "predecessor_stores": {
                "fingerprints_before": before,
                "fingerprints_after": after,
                "unchanged": before == after,
                "writes": 0 if before == after else -1,
            },
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_canonical(evidence) + b"\n")
    print(
        json.dumps(
            {
                "output": output.name,
                "sides": completion["sides"],
                "sides_that_needed_the_fallback": completion["sides_that_needed_the_fallback"],
                "sides_empty_under_the_complete_surface": len(
                    completion["sides_empty_under_the_complete_surface"]
                ),
                "reached_fraction": completion["reached_fraction"],
                "distinct_candidate_term_sets": completion["distinct_candidate_term_sets"],
                "pairs_whose_two_sides_carry_the_same_terms": len(
                    completion["pairs_whose_two_sides_carry_the_same_terms"]
                ),
                "stored_pairs_checked": stored["pairs_total"],
                "every_resolvable_hash_unchanged": stored["every_resolvable_hash_unchanged"],
                "roots_that_do_not_resolve": stored["roots_that_do_not_resolve"],
                "all_guards_fired": guards["all_guards_fired"],
                "predecessor_store_writes": evidence["predecessor_stores"]["writes"],
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    # The exit code is about what this wave controls. A predecessor blob that is gone is a
    # finding recorded in the record above; failing this item on it would make D5 unable to
    # close an item because D4's store lost bytes D5 never wrote.
    ok = (
        stored["every_resolvable_hash_unchanged"]
        and guards["all_guards_fired"]
        and not completion["sides_empty_under_the_complete_surface"]
        and not completion["pairs_whose_two_sides_carry_the_same_terms"]
        and evidence["predecessor_stores"]["unchanged"]
    )
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    return _run(arguments.output)


if __name__ == "__main__":
    raise SystemExit(main())
