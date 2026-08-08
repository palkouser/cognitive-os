#!/usr/bin/env python3
"""S21D4-047. The advisory Experience Graph boundary, under the widened surface.

A negative retrieval result is a reason to run this, never a reason to skip it: the boundary
has to hold for evidence that lost as much as for evidence that won, and the widened surface
put new text in front of the advisory path that was not there when D1 proved it.

Four properties, executed against the real sixty-pair holdout rather than against fixtures:

*The mandatory sections do not move.* One bundle assembled with graph candidates and one
without, and every section the request did not get from retrieval must be byte-identical. A
retrieval source that could shift a mandatory section would be a retrieval source with
authority over the current run.

*An advisory candidate carries no authority and no body.* Never pinned, never required, never
evidence, and `content is None` -- a suggestion, not a patch someone could execute.

*An empty set degrades rather than fails.* No pairs, no candidates, and a component that is
still healthy: memory being absent is not the run being broken.

*A corrupt store can only lower trust.* A verifier that raises, a verifier that says no, and a
missing artifact id each produce `UNVERIFIED` and never an exception and never `VERIFIED`.

Read-only. It opens no store, starts no container, and writes one evidence file.

    UV_CACHE_DIR=.cache/uv uv run python scripts/advisory_boundary_d4.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.config.context_config import ContextConfiguration  # noqa: E402
from cognitive_os.context.assembly import assemble_bundle  # noqa: E402
from cognitive_os.context.fixtures import sprint11_fixture  # noqa: E402
from cognitive_os.context.ranking import ranking_profile  # noqa: E402
from cognitive_os.context.safety import filter_unsafe_candidates  # noqa: E402
from cognitive_os.context.tokenization import ConservativeUtf8TokenEstimator  # noqa: E402
from cognitive_os.domain.context import (  # noqa: E402
    ContextComponentStatus,
    ContextPurpose,
    ContextSourceType,
    ContextTrustClass,
    RetrievalMode,
    RetrievalSubquery,
)
from cognitive_os.domain.experience_graph import (  # noqa: E402
    GRAPH_RESOURCE_POLICY_REVISION_2,
)
from cognitive_os.experience.graph_context import (  # noqa: E402
    ExperienceGraphContextRetriever,
)
from cognitive_os.experience.graph_store import load_evidence  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
GRAPH_ROOT = EVIDENCE / "sprint-21d4-retrieval-emg-root.json"
HOLDOUT_RESULT = EVIDENCE / "sprint-21d4-retrieval-holdout-result.json"
DECISION = EVIDENCE / "sprint-21d4-retrieval-decision.json"
OUTPUT = EVIDENCE / "sprint-21d4-advisory-boundary.json"

ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d4")
ARTIFACT = UUID(int=7)

#: The query the advisory path is asked to answer. Deliberately not a group name or a task
#: signature: those are what `excluded_groups` removes, and a probe that named one would be
#: measuring the exclusion rather than the boundary.
QUERY = "a failing boundary step that returns one item too many"

#: Fixed so the request is a constant rather than a clock reading.
REQUEST_TIME = datetime(2026, 8, 7, tzinfo=UTC)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _subquery() -> RetrievalSubquery:
    return RetrievalSubquery(
        subquery_id=UUID(int=11),
        source_type=ContextSourceType.EXPERIENCE_GRAPH,
        mode=RetrievalMode.METADATA,
        terms=(),
        maximum_results=10,
    )


def _bundle(candidates: tuple[Any, ...], request: Any, profile: Any) -> Any:
    return assemble_bundle(
        bundle_id=UUID(int=99),
        revision=1,
        previous_revision=None,
        request=request,
        candidates=candidates,
        exclusions=(),
        warnings=(),
        ranking_profile=ranking_profile(ContextConfiguration()),
        provider_profile=profile,
        estimator=ConservativeUtf8TokenEstimator(),
    )


async def _ok(_: UUID) -> bool:
    return True


async def _no(_: UUID) -> bool:
    return False


async def _raises(_: UUID) -> bool:
    raise RuntimeError("the store is corrupt")


async def _measure() -> dict[str, Any]:
    evidence = load_evidence(GRAPH_ROOT, ARTIFACT_ROOT)
    if not evidence.intact:
        raise SystemExit("the D4 retrieval pair set does not resolve")
    pairs = evidence.pairs
    # The released Sprint 11 fixture, not a request built here: it carries the pinned, required
    # task-state and execution-plan candidates that *are* the mandatory sections. A probe that
    # fed the assembler graph candidates alone would compare an empty set of mandatory sections
    # against another empty set and report success -- which the first version of this script
    # did, and reported "byte-identical: True (0 compared)".
    fixture_request, fixture_candidates, _, profile = sprint11_fixture()
    request = fixture_request.model_copy(
        update={
            "context_purpose": ContextPurpose.REPAIR,
            "query": QUERY,
            "allowed_source_types": (
                *fixture_request.allowed_source_types,
                ContextSourceType.EXPERIENCE_GRAPH,
            ),
        }
    )

    retriever = ExperienceGraphContextRetriever(
        pairs,
        artifact_ids={pair.pair_id: ARTIFACT for pair in pairs},
        verifier=_ok,
        limits=GRAPH_RESOURCE_POLICY_REVISION_2,
    )
    candidates = await retriever.retrieve(_subquery(), request)

    # --- the mandatory sections do not move -------------------------------------------------
    with_graph = _bundle((*fixture_candidates, *candidates), request, profile)
    without_graph = _bundle(fixture_candidates, request, profile)

    def _mandatory(bundle: Any) -> dict[str, str]:
        """Sections that carry no Experience Graph reference, keyed by what they are."""
        return {
            f"{section.section_type}:{section.title}": section.content_hash
            for section in bundle.sections
            if not any(
                reference.source_type is ContextSourceType.EXPERIENCE_GRAPH
                for reference in section.source_references
            )
        }

    mandatory_with, mandatory_without = _mandatory(with_graph), _mandatory(without_graph)
    shared = sorted(set(mandatory_with) & set(mandatory_without))

    # --- an advisory candidate carries no authority and no body ------------------------------
    _, exclusions, _ = filter_unsafe_candidates(
        candidates, sensitivity_limit=request.sensitivity_limit
    )

    # --- an empty set degrades rather than fails ----------------------------------------------
    empty = ExperienceGraphContextRetriever((), limits=GRAPH_RESOURCE_POLICY_REVISION_2)
    empty_candidates = await empty.retrieve(_subquery(), request)
    empty_health = await empty.health_check()

    # --- a corrupt store can only lower trust --------------------------------------------------
    degradations = {}
    for name, kwargs in (
        (
            "verifier_raises",
            {"artifact_ids": {p.pair_id: ARTIFACT for p in pairs}, "verifier": _raises},
        ),
        (
            "verifier_says_no",
            {"artifact_ids": {p.pair_id: ARTIFACT for p in pairs}, "verifier": _no},
        ),
        ("no_artifact_id", {"verifier": _ok}),
        ("no_verifier", {"artifact_ids": {p.pair_id: ARTIFACT for p in pairs}}),
    ):
        degraded = ExperienceGraphContextRetriever(
            pairs, limits=GRAPH_RESOURCE_POLICY_REVISION_2, **kwargs
        )
        rows = await degraded.retrieve(_subquery(), request)
        degradations[name] = {
            "candidates": len(rows),
            "trust_classes": sorted({row.trust_class.value for row in rows}),
            "raised": False,
            "only_unverified": all(row.trust_class is ContextTrustClass.UNVERIFIED for row in rows),
        }

    # --- a purpose that is not advisory gets nothing --------------------------------------------
    planning = request.model_copy(update={"context_purpose": ContextPurpose.PLANNING})
    non_advisory = await retriever.retrieve(_subquery(), planning)

    return {
        "pairs": len(pairs),
        "graphs_carrying_terms": sum(
            1 for pair in pairs for graph in (pair.failed, pair.successful) if graph.search_terms
        ),
        "candidates_returned": len(candidates),
        "mandatory_sections": {
            "sections_with_graph": len(with_graph.sections),
            "sections_without_graph": len(without_graph.sections),
            # The graph does not add a section; it joins one. So "retrieval contributed" is
            # this count, not a difference in section totals -- which are equal.
            "sections_carrying_a_graph_reference": len(with_graph.sections) - len(mandatory_with),
            "mandatory_sections": sorted(shared),
            "mandatory_sections_compared": len(shared),
            "byte_identical": [
                key for key in shared if mandatory_with[key] == mandatory_without[key]
            ],
            "moved": [key for key in shared if mandatory_with[key] != mandatory_without[key]],
            "every_mandatory_section_is_byte_identical": bool(shared)
            and all(mandatory_with[key] == mandatory_without[key] for key in shared),
            "a_comparison_over_nothing_is_not_a_pass": (
                "The claim requires at least one mandatory section to compare. An empty "
                "intersection reports false here rather than passing vacuously."
            ),
        },
        "advisory_properties": {
            "pinned": sorted({row.pinned for row in candidates}),
            "required": sorted({row.required for row in candidates}),
            "evidence": sorted({row.evidence for row in candidates}),
            "carries_an_executable_body": any(row.content is not None for row in candidates),
            "never_pinned_required_or_evidence": all(
                not row.pinned and not row.required and not row.evidence for row in candidates
            ),
            "unsafe_exclusions": len(exclusions),
            "summary_says_advisory": all("Advisory only" in row.summary for row in candidates),
        },
        "empty_set": {
            "candidates": len(empty_candidates),
            "raised": False,
            "component_status": empty_health.status.value,
            "degraded_rather_than_unavailable": empty_health.status
            is not ContextComponentStatus.UNAVAILABLE,
        },
        "trust_degradation": degradations,
        "non_advisory_purpose": {
            "purpose": ContextPurpose.PLANNING.value,
            "candidates": len(non_advisory),
            "gets_nothing": not non_advisory,
        },
        "widened_surface_reached_the_advisory_path": any(
            pair.successful.search_terms for pair in pairs
        ),
        "creates_execution_or_correction_authority": False,
        "opened_any_store_for_writing": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    measured = asyncio.run(_measure())
    held = (
        measured["mandatory_sections"]["every_mandatory_section_is_byte_identical"]
        and measured["advisory_properties"]["never_pinned_required_or_evidence"]
        and not measured["advisory_properties"]["carries_an_executable_body"]
        and measured["empty_set"]["degraded_rather_than_unavailable"]
        and all(row["only_unverified"] for row in measured["trust_degradation"].values())
        and measured["non_advisory_purpose"]["gets_nothing"]
    )
    evidence = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W3",
        "items": ["S21D4-047"],
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
        "graph_root_sha256": _digest(GRAPH_ROOT.read_bytes()),
        "holdout_result_sha256": _digest(HOLDOUT_RESULT.read_bytes()),
        "decision_sha256": _digest(DECISION.read_bytes()),
        "runs_on_every_outcome": (
            "The retrieval holdout returned a negative result. The advisory boundary is proved "
            "here anyway: it governs what retrieved history may do, not whether retrieval "
            "scored well, and an unproved boundary over a losing arm is still an unproved "
            "boundary."
        ),
        "measured": measured,
        "boundary_held": held,
        "final_or_canary_outcomes_inspected": 0,
        "final_outcomes_inspected": False,
    }
    sealed = dict(evidence)
    sealed["integrity_content_hash"] = _digest(_canonical(evidence))
    arguments.output.write_bytes(_canonical(sealed) + b"\n")

    print(f"{arguments.output.relative_to(REPOSITORY)}")
    print(
        f"  {measured['pairs']} pairs, {measured['candidates_returned']} advisory candidates, "
        f"{measured['graphs_carrying_terms']} graphs carrying terms"
    )
    print(
        "  mandatory sections byte-identical: "
        f"{measured['mandatory_sections']['every_mandatory_section_is_byte_identical']} "
        f"({measured['mandatory_sections']['mandatory_sections_compared']} compared)"
    )
    print(
        "  never pinned, required or evidence: "
        f"{measured['advisory_properties']['never_pinned_required_or_evidence']}, "
        f"executable body: {measured['advisory_properties']['carries_an_executable_body']}"
    )
    print(f"  empty set: {measured['empty_set']['component_status']}")
    print(
        "  trust degradations that stayed UNVERIFIED: "
        f"{sum(1 for row in measured['trust_degradation'].values() if row['only_unverified'])}"
        f" of {len(measured['trust_degradation'])}"
    )
    print(f"  boundary held: {held}")
    print(f"  seal {sealed['integrity_content_hash']}")
    return 0 if held else 1


if __name__ == "__main__":
    raise SystemExit(main())
