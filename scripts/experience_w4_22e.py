"""S22E-402: the successful experience — the half exit (c) was still owed.

W2 compiled and queried back the **failed** kind and said so in its own sealed record:
`kind_demonstrated: "failed — both sealed dry-run-1 traversals"`, with
`successful_kind_owed_by: "W3's approved change"`. Exit (c) asks for *failed **and** successful*
experience retained and retrievable, so that sentence names a debt, and W4 is where it comes due.

**Superseded, never edited.** W2's driver rebuilds its record on every `--check`, so widening
`build_traversal` to cover a shape it was not written for would move the bytes of a sealed record
that seven tests hold. This driver is additive: it imports W2's released helpers unchanged and
builds the one traversal shape W2 had no example of.

**Why the retrieval here asks two questions rather than one.** Showing the successful traversal
comes back for a query about success proves it is *stored*. What exit (c) actually needs is that
the two kinds are **distinguishable** — otherwise "both are retrievable" is satisfied by a store
that returns everything for everything. So the same pool is queried twice, with the structural
language of a refusal and of an acceptance, and the record carries both orderings. A store that
ranked them identically would fail here and pass a one-query version.

    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/experience_w4_22e.py
    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/experience_w4_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

OUTPUT = EVIDENCE / "sprint-22e-w4-experience.json"
NAME = "s22e-approved-change"
CHANGE_RECORD = EVIDENCE / "sprint-22e-w3-approved-change.json"
PROMOTION_RECORD = EVIDENCE / "sprint-22e-w3-promotion.json"
RECORDED_AT = "2026-08-16T00:00:00Z"

#: The two structural queries, written in the surface's **own token vocabulary**.
#:
#: The released projection keeps prose off `search_text()` by design — W2 measured five identical
#: zero scores for a natural-language question and moved to structural words. This driver's first
#: run went one step further wrong in the same family as W1-F6: it asked for `completed` and
#: `failed`, and the surface emits `status=completed` and `status=failed`. Bare words match
#: nothing, so both queries scored on the shared tokens alone and the two failed traversals tied
#: at exactly 0.333333 for a question about success. **The caller's query was malformed; the
#: released retrieval was doing precisely what it says.** The token inventory is measured into
#: the record below rather than assumed, so this cannot silently rot.
QUERIES = {
    "acceptance_completed": (
        "self_improvement status=completed accepted_outcome "
        "segment=acceptance segment=verification segment=tool_execution"
    ),
    "acceptance_failed": (
        "self_improvement status=failed tool_result "
        "segment=acceptance segment=verification segment=tool_execution"
    ),
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def sealed(path: Path) -> dict[str, Any]:
    stored = json.loads(path.read_text(encoding="utf-8"))
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != stored["integrity_content_hash"]:
        raise ValueError(f"{path.name} does not recompute its own seal")
    return stored


def build_successful_traversal() -> tuple[Any, Any, Any, dict[str, Any]]:
    """The approved change's traversal: every step completed, and the acceptance *accepted*.

    The shape W2's builder had no example of. Its last entry is the difference that matters:
    a `COMPLETED` acceptance carrying the merge commit and the exact-head CI conclusion, where
    the failed traversals carry a refusing gate.
    """
    from experience_22e import EXPERIENCE_TIME, _entry, _id, _reference

    from cognitive_os.domain.experience import (
        CompilerProfile,
        CompilerResourceLimits,
        ExperienceCandidateType,
        ExperienceCompilationRequest,
        ExperienceStepStatus,
        TimelineEntryType,
        TrajectorySourceType,
    )
    from cognitive_os.experience.registry import (
        CompilerProfileRegistry,
        ResolvedTrajectorySource,
        SourceResolverRegistry,
    )

    payload = CHANGE_RECORD.read_bytes()
    record = sealed(CHANGE_RECORD)
    promotion = sealed(PROMOTION_RECORD)

    task_ref = _reference(NAME, TrajectorySourceType.TASK, payload)
    controller_ref = _reference(NAME, TrajectorySourceType.CONTROLLER_EVENT, payload)
    provider_payload = canonical(record["provider"])
    provider_ref = _reference(NAME, TrajectorySourceType.PROVIDER_CALL, provider_payload)
    tool_payload = canonical(record["repair"])
    tool_ref = _reference(NAME, TrajectorySourceType.TOOL_CALL, tool_payload)
    verifier_payload = canonical(record["gates"])
    verifier_ref = _reference(NAME, TrajectorySourceType.VERIFIER, verifier_payload)
    acceptance_payload = canonical(promotion["what_landed"])
    acceptance_ref = _reference(NAME, TrajectorySourceType.ACCEPTANCE, acceptance_payload)

    files = ", ".join(item["file"] for item in record["repair"]["files"])
    entries = [
        _entry(
            NAME,
            controller_ref,
            1,
            TimelineEntryType.PLAN,
            "proposal.mined",
            ExperienceStepStatus.COMPLETED,
            f"weakness {record['entry_id']} mined from the sealed ledger revision; the gate "
            "owner's selection read from its own record",
        ),
        _entry(
            NAME,
            provider_ref,
            2,
            TimelineEntryType.PROVIDER,
            "provider.proposal",
            ExperienceStepStatus.COMPLETED,
            "live claude-code draft admitted by merge_provider_draft host verification",
        ),
        _entry(
            NAME,
            tool_ref,
            3,
            TimelineEntryType.TOOL,
            "tool.deterministic_replace",
            ExperienceStepStatus.COMPLETED,
            f"repair applied to {files}: the merged provider revision is revalidated so its "
            "seal survives to the approved revision",
        ),
    ]
    sequence = 4
    for gate in record["gates"]:
        if not gate.get("ran"):
            continue
        entries.append(
            _entry(
                NAME,
                verifier_ref,
                sequence,
                TimelineEntryType.VERIFIER,
                "verifier.completed",
                ExperienceStepStatus.COMPLETED,
                f"gate {gate['gate_id']} passed",
            )
        )
        sequence += 1
    entries.append(
        _entry(
            NAME,
            acceptance_ref,
            sequence,
            TimelineEntryType.ACCEPTANCE,
            "acceptance.completed",
            ExperienceStepStatus.COMPLETED,
            f"approved by {promotion['authority']['approver']}, merged at "
            f"{promotion['pull_request']['merge_commit'][:7]}, post-merge exact-head CI "
            f"{promotion['post_merge_ci']['conclusion']}; the landed bytes are the evaluated "
            "bytes",
        )
    )

    resolved = [
        ResolvedTrajectorySource(task_ref, payload),
        ResolvedTrajectorySource(
            controller_ref,
            payload,
            tuple(item for item in entries if item.source_ref == controller_ref),
            "completed",
        ),
        ResolvedTrajectorySource(provider_ref, provider_payload, (entries[1],)),
        ResolvedTrajectorySource(tool_ref, tool_payload, (entries[2],)),
        ResolvedTrajectorySource(
            verifier_ref,
            verifier_payload,
            tuple(item for item in entries if item.source_ref == verifier_ref),
        ),
        ResolvedTrajectorySource(acceptance_ref, acceptance_payload, (entries[-1],)),
    ]
    sources = SourceResolverRegistry()
    for item in resolved:
        sources.register(item)
    sources.freeze()

    profile = CompilerProfile(
        profile_id="s22e-approved-change-v1",
        version=1,
        enabled_source_types=frozenset(item.reference.source_type for item in resolved),
        required_source_types=frozenset(
            {
                TrajectorySourceType.TASK,
                TrajectorySourceType.CONTROLLER_EVENT,
                TrajectorySourceType.VERIFIER,
                TrajectorySourceType.ACCEPTANCE,
            }
        ),
        candidate_types=frozenset(ExperienceCandidateType),
        assessment_policy="conservative-evidence-v1",
        contribution_policy="no-causal-overclaim-v1",
        generalizability_policy="minimum-specificity-v1",
        resource_limits=CompilerResourceLimits(),
        created_at=EXPERIENCE_TIME,
    )
    profiles = CompilerProfileRegistry()
    profiles.register(profile)
    profiles.freeze()

    request = ExperienceCompilationRequest(
        compilation_id=_id("compilation", NAME),
        task_run_id=_id("task-run", NAME),
        trajectory_sources=tuple(item.reference for item in resolved),
        compiler_profile_id=profile.profile_id,
        compiler_profile_version=profile.version,
        compiler_profile_hash=profile.content_hash,
        candidate_types=frozenset(ExperienceCandidateType),
        budget=CompilerResourceLimits(),
        requested_by="s22e-w4",
        idempotency_key=f"s22e-experience:{NAME}",
        created_at=EXPERIENCE_TIME,
    )
    facts = {
        "record": CHANGE_RECORD.name,
        "record_sha256": _sha256(payload),
        "refusing_gate": None,
        "timeline_entries": len(entries),
        "timeline": [
            {
                "sequence": item.sequence,
                "event_type": item.event_type,
                "status": item.status.value,
                "summary": item.payload_summary,
            }
            for item in entries
        ],
    }
    return request, sources, profiles, facts


def compile_successful() -> tuple[Any, dict[str, Any]]:
    from cognitive_os.experience.compiler import ExperienceCompiler
    from cognitive_os.experience.graph_projection import project

    request, sources, profiles, facts = build_successful_traversal()
    result = ExperienceCompiler(sources, profiles).compile(request)
    graph = project(
        result,
        graph_id=f"{NAME}-graph",
        domain="self_improvement",
        group=NAME,
        task_signature=f"s22e:L7:{NAME}",
        accepted=True,
    )
    facts |= {
        "compilation_decision": result.decision.decision.value,
        "manifest_hash": result.manifest.content_hash,
        "graph_hash": graph.content_hash,
        "graph_nodes": len(graph.nodes),
        "projected_as_accepted": True,
    }
    return graph, facts


def _record(*, write: bool = True) -> dict[str, Any]:
    from experience_22e import (
        FIXTURE_DISTRACTORS,
        TRAVERSALS,
        compile_and_project,
        fixture_candidate,
        store_side,
    )

    from cognitive_os.domain.experience_graph import ExperienceGraphQuery, GraphResourceLimits
    from cognitive_os.experience.graph_retrieval import Candidate, eligible_pool, lexical
    from cognitive_os.experience.graph_store import blob_path

    artifact_root = Path(os.environ["COGOS_ARTIFACT_ROOT"])

    graph, facts = compile_successful()
    stored = store_side(graph, facts, artifact_root, write=write)
    pool = [
        Candidate(
            pair_id=NAME,
            group=NAME,
            domain="self_improvement",
            task_signature=f"s22e:L7:{NAME}",
            text=graph.search_text(),
            graph=graph,
        )
    ]
    # W2's two failed traversals, rebuilt through W2's own unchanged code, so the two kinds are
    # ranked against each other rather than each against nothing.
    for name in TRAVERSALS:
        _, failed_graph, _failed_facts = compile_and_project(name)
        pool.append(
            Candidate(
                pair_id=name,
                group=name,
                domain="self_improvement",
                task_signature=f"s22e:L1:{name}",
                text=failed_graph.search_text(),
                graph=failed_graph,
            )
        )
    pool += [fixture_candidate(name) for name in FIXTURE_DISTRACTORS]

    # The surface's own vocabulary, measured rather than assumed. This is what makes the query
    # above checkable: if the projection ever stops emitting `status=failed`, the claim that the
    # refusal query asks for something real fails here rather than degrading into a tie.
    tokens = {
        item.pair_id: sorted(set(item.text.split()))
        for item in pool
        if item.pair_id == NAME or item.pair_id in TRAVERSALS
    }

    rankings: dict[str, Any] = {}
    for key, text in QUERIES.items():
        query = ExperienceGraphQuery(
            query_id=f"s22e-w4-{key}",
            query_text=text,
            domain="self_improvement",
            task_signature="s22e:L7" if key == "acceptance_completed" else "s22e:L1",
            excluded_groups=("s22e-query",),
        )
        result = lexical(query, eligible_pool(pool, query), limits=GraphResourceLimits())
        rankings[key] = {
            "query_text": text,
            "entries": [
                {"pair_id": item.pair_id, "rank": item.rank, "score": item.score}
                for item in result.entries
            ],
        }

    success_rank = {
        item["pair_id"]: item["rank"] for item in rankings["acceptance_completed"]["entries"]
    }
    failure_rank = {
        item["pair_id"]: item["rank"] for item in rankings["acceptance_failed"]["entries"]
    }

    # The answer is read out of the STORE, addressed by the successful query's top rank.
    top = min(success_rank, key=lambda name: success_rank[name])
    document = json.loads(
        blob_path(artifact_root, stored["content_hash"]).read_text(encoding="utf-8")
    )
    summaries = " ".join(item["summary"].lower() for item in document["timeline"])

    return {
        "items": ["S22E-402"],
        "sprint": "22E",
        "wave": "W4",
        "schema_version": 1,
        "kind_demonstrated": "successful — W3's approved change, the half W2 recorded as owed",
        "closes_the_debt_named_in": "sprint-22e-w2-experience.json#successful_kind_owed_by",
        "traversal": {NAME: facts},
        "side_store": stored,
        "rankings": rankings,
        "search_surface_tokens": tokens,
        "what_separates_the_two_kinds_on_the_surface": {
            "successful_has_status_completed": "status=completed" in tokens[NAME],
            "successful_has_status_failed": "status=failed" in tokens[NAME],
            "successful_has_accepted_outcome": "accepted_outcome" in tokens[NAME],
            "failed_have_both_status_tokens": all(
                {"status=completed", "status=failed"} <= set(tokens[name]) for name in TRAVERSALS
            ),
            "failed_have_accepted_outcome": any(
                "accepted_outcome" in tokens[name] for name in TRAVERSALS
            ),
            "so": (
                "a failed traversal's token set is nearly a superset of a successful one's — it "
                "contains completed steps too — and only `accepted_outcome` and the absence of "
                "`status=failed` distinguish the successful graph. Retrieval separates the kinds "
                "only when the query names those two things"
            ),
        },
        "retrieval": {
            "the_successful_traversal_is_top_for_the_acceptance_query": top == NAME,
            "top_for_the_acceptance_query": top,
            "the_failed_traversals_outrank_it_for_the_refusal_query": all(
                failure_rank.get(name, 99) < failure_rank.get(NAME, 99) for name in TRAVERSALS
            ),
            "the_two_kinds_are_distinguishable": (
                top == NAME
                and all(
                    failure_rank.get(name, 99) < failure_rank.get(NAME, 99) for name in TRAVERSALS
                )
            ),
            "why_two_queries": (
                "one query proves the graph is stored; two prove the kinds are told apart. A "
                "store that returned everything for everything would satisfy the first and "
                "fail the second"
            ),
            # **What exit (c) actually asks for, kept separate from the stricter probe above.**
            # The exit's words are "retained and retrievable". Distinguishability is a stronger
            # property this driver chose to measure, and a stricter probe must never be allowed
            # to quietly redefine the sentence it is testing beside.
            "both_kinds_retained_and_retrievable": (
                stored["read_back_validates_as_the_contract"]
                and NAME in success_rank
                and all(name in failure_rank for name in TRAVERSALS)
            ),
            "the_successful_traversal_outranks_every_distractor": all(
                success_rank[NAME] < success_rank[f"fixture-{name}"] for name in FIXTURE_DISTRACTORS
            ),
            "answer_read_from_the_store": {
                "blob_content_hash": stored["content_hash"],
                "what_was_tried": "repair applied" in summaries,
                "what_succeeded": "passed" in summaries,
                "why": "post-merge exact-head ci success" in summaries,
                "the_landed_bytes_claim_is_in_the_timeline": "evaluated" in summaries,
            },
        },
        "recorded_at": RECORDED_AT,
    }


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    rebuilt = _record(write=False)
    return {
        "seal_recomputes": _sha256(canonical(body)) == record["integrity_content_hash"],
        "rebuilds_byte_identical": canonical(rebuilt) == canonical(body),
        "side_read_back_still_validates": rebuilt["side_store"][
            "read_back_validates_as_the_contract"
        ],
        "two_kinds_still_distinguishable": rebuilt["retrieval"][
            "the_two_kinds_are_distinguishable"
        ],
        "recorded_not_recomputed": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        verdict = check_record(json.loads(OUTPUT.read_text(encoding="utf-8")))
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return (
            0
            if all(value for key, value in verdict.items() if key != "recorded_not_recomputed")
            else 1
        )

    record = _record(write=True)
    record["integrity_content_hash"] = _sha256(canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "compilation_decision": record["traversal"][NAME]["compilation_decision"],
                "graph_nodes": record["traversal"][NAME]["graph_nodes"],
                "two_kinds_distinguishable": record["retrieval"][
                    "the_two_kinds_are_distinguishable"
                ],
                "answer_read_from_the_store": record["retrieval"]["answer_read_from_the_store"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
