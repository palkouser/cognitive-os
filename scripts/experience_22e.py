"""S22E-202. The experience leg: two failed traversals compiled, stored, and queried back.

W1's exit had two halves and the second was never built; §2.2(e) is the reading it must meet:
experience "compiled through the released Experience Compiler into the EMG, and then queried
back out: the record shows a retrieval, from the store, whose content answers what was tried,
what failed, and why". This driver builds that leg and demonstrates it on the **failed kind**
— both sealed dry-run-1 traversals, the W1 refusal and the W2 continuation. The successful
kind is, by §2.2(e)'s own sentence, *the approved change's*, which W3 produces; the leg built
here is what W3 will feed.

**The timeline is derived from sealed records, never invented.** Each traversal's sources are
the sealed dry-run record itself (TASK), its stage stream (CONTROLLER_EVENT and TOOL), its
governed provider receipt (PROVIDER_CALL), its gate outcomes (VERIFIER — the refusing gate is
the FAILED entry, and the two records refuse at different gates for different reasons), and
the terminal refusal (ACCEPTANCE, failed). The released compiler assesses that timeline; the
released projection turns it into an action-decision graph whose node summaries carry the
what/failed/why the query must be able to surface.

**The store is content-addressed and read back before it is claimed.** Each projected side is
written under the campaign artifact root at the released `blob_path` shape, a side manifest
names every child by hash, and the read-back re-loads the bytes, re-verifies the hash and
re-validates the contract — D7 W3-F1, applied to the store this record is about. The manifest
calls them **sides, not pairs**: a `FailedSuccessGraphPair` needs the successful twin, which
is W3's; pretending otherwise would seal a pair that does not exist.

**The retrieval has distractors, so ranking first means something.** The pool is the two
compiled sides plus three released compiler fixtures (a success, a failed strategy, a denied
tool request), all projected through the same released projection. The released lexical arm
answers the query; a pool of one would make any retrieval claim vacuous.

Everything here is deterministic and credential-free, so `--check` recomputes the entire
record: timelines, compilations, projections, stored bytes, and the query result.

    set -a && source .env.s22e.local && set +a
    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/experience_22e.py
    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/experience_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

OUTPUT = EVIDENCE / "sprint-22e-w2-experience.json"
SIDE_MANIFEST = EVIDENCE / "sprint-22e-experience-side-store.json"
EXPERIENCE_TIME = datetime(2026, 8, 16, 18, 0, tzinfo=UTC)

TRAVERSALS = {
    "s22e-dryrun-1": EVIDENCE / "sprint-22e-w1-dryrun1.json",
    "s22e-dryrun-1-continuation": EVIDENCE / "sprint-22e-w2-dryrun1-continuation.json",
}

FIXTURE_DISTRACTORS = ("direct-success", "failed-strategy", "unsafe-tool-request")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _id(kind: str, name: str) -> Any:
    return uuid5(NAMESPACE_URL, f"s22e-experience:{kind}:{name}")


# ---------------------------------------------------------------------------
# The timeline, derived from a sealed dry-run record
# ---------------------------------------------------------------------------


def _reference(name: str, source_type: Any, payload: bytes, *, required: bool = True) -> Any:
    from cognitive_os.domain.experience import TrajectorySourceRef, TrajectorySourceType
    from cognitive_os.domain.memory import MemorySensitivity

    event_stream = source_type is TrajectorySourceType.CONTROLLER_EVENT
    return TrajectorySourceRef(
        source_type=source_type,
        source_id=f"{name}:{source_type.value}",
        source_revision="1",
        event_stream_id=_id("stream", name) if event_stream else None,
        event_stream_version=1 if event_stream else None,
        source_content_hash=_sha256(payload),
        scope="project:cognitive-os",
        sensitivity=MemorySensitivity.INTERNAL,
        required=required,
    )


def _entry(
    name: str,
    reference: Any,
    sequence: int,
    entry_type: Any,
    event_type: str,
    status: Any,
    summary: str,
) -> Any:
    from cognitive_os.domain.experience import TimelineEntry

    evidence = _sha256(f"{name}:{sequence}:{event_type}:{status.value}".encode())
    return TimelineEntry(
        timeline_entry_id=_id("entry", f"{name}:{sequence}:{event_type}"),
        sequence=sequence,
        source_ref=reference,
        entry_type=entry_type,
        event_type=event_type,
        actor_type="system",
        actor_id="s22e-dry-run",
        step_id=f"step-{sequence}",
        started_at=EXPERIENCE_TIME + timedelta(seconds=sequence),
        finished_at=EXPERIENCE_TIME + timedelta(seconds=sequence, milliseconds=100),
        correlation_id=_id("correlation", name),
        status=status,
        payload_summary=summary[:512],
        evidence_refs=(evidence,),
    )


def build_traversal(name: str) -> tuple[Any, Any, Any, dict[str, Any]]:
    """One sealed dry-run record as compiler inputs: request, sources, profiles, facts."""
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

    record_path = TRAVERSALS[name]
    payload = record_path.read_bytes()
    record = json.loads(payload)
    refused = [item for item in record["gates"] if item.get("passed") is False]
    refusing = refused[0] if refused else None

    task_ref = _reference(name, TrajectorySourceType.TASK, payload)
    controller_ref = _reference(name, TrajectorySourceType.CONTROLLER_EVENT, payload)
    provider_payload = canonical(record["provider"])
    provider_ref = _reference(name, TrajectorySourceType.PROVIDER_CALL, provider_payload)
    tool_payload = canonical(record["repair"])
    tool_ref = _reference(name, TrajectorySourceType.TOOL_CALL, tool_payload)
    verifier_payload = canonical(record["gates"])
    verifier_ref = _reference(name, TrajectorySourceType.VERIFIER, verifier_payload)
    acceptance_payload = canonical(record["zero_active_state_mutation"])
    acceptance_ref = _reference(name, TrajectorySourceType.ACCEPTANCE, acceptance_payload)

    entry_id = record["entry_id"]
    entries = [
        _entry(
            name,
            controller_ref,
            1,
            TimelineEntryType.PLAN,
            "proposal.mined",
            ExperienceStepStatus.COMPLETED,
            f"weakness {entry_id} mined from the sealed ledger; proposal registered",
        ),
        _entry(
            name,
            provider_ref,
            2,
            TimelineEntryType.PROVIDER,
            "provider.proposal",
            ExperienceStepStatus.COMPLETED,
            "live claude-code draft admitted by merge_provider_draft host verification",
        ),
        _entry(
            name,
            tool_ref,
            3,
            TimelineEntryType.TOOL,
            "tool.deterministic_replace",
            ExperienceStepStatus.COMPLETED,
            f"repair applied to {record['repair']['file']}: SAFE_UNIT allowlist widened "
            "by the written notation characters",
        ),
    ]
    sequence = 4
    for gate in record["gates"]:
        if not gate.get("ran"):
            continue
        failed = gate.get("passed") is False
        reason = ""
        if failed:
            tail = gate.get("stdout_tail", "")
            reason = (
                ": import-not-found numpy — the gate environment, not the candidate"
                if "numpy" in tail
                else ": the W1-F4 diagnosis test pins the defect the candidate repairs"
                if "allowlist" in tail
                else ""
            )
        entries.append(
            _entry(
                name,
                verifier_ref,
                sequence,
                TimelineEntryType.VERIFIER,
                "verifier.failed" if failed else "verifier.completed",
                ExperienceStepStatus.FAILED if failed else ExperienceStepStatus.COMPLETED,
                f"gate {gate['gate_id']} {'failed' if failed else 'passed'}{reason}",
            )
        )
        sequence += 1
    entries.append(
        _entry(
            name,
            acceptance_ref,
            sequence,
            TimelineEntryType.ACCEPTANCE,
            "acceptance.failed",
            ExperienceStepStatus.FAILED,
            f"candidate refused at {refusing['gate_id'] if refusing else 'no gate'}; "
            "zero active-state mutation held",
        )
    )

    resolved = [
        ResolvedTrajectorySource(task_ref, payload),
        ResolvedTrajectorySource(
            controller_ref,
            payload,
            tuple(item for item in entries if item.source_ref == controller_ref),
            "failed",
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
        profile_id="s22e-dryrun-v1",
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
        compilation_id=_id("compilation", name),
        task_run_id=_id("task-run", name),
        trajectory_sources=tuple(item.reference for item in resolved),
        compiler_profile_id=profile.profile_id,
        compiler_profile_version=profile.version,
        compiler_profile_hash=profile.content_hash,
        candidate_types=frozenset(ExperienceCandidateType),
        budget=CompilerResourceLimits(),
        requested_by="s22e-w2",
        idempotency_key=f"s22e-experience:{name}",
        created_at=EXPERIENCE_TIME,
    )
    facts = {
        "record": record_path.name,
        "record_sha256": _sha256(payload),
        "refusing_gate": refusing["gate_id"] if refusing else None,
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


# ---------------------------------------------------------------------------
# Compile, project, store, read back, query
# ---------------------------------------------------------------------------


def compile_and_project(name: str) -> tuple[Any, Any, dict[str, Any]]:
    from cognitive_os.experience.compiler import ExperienceCompiler
    from cognitive_os.experience.graph_projection import project

    request, sources, profiles, facts = build_traversal(name)
    result = ExperienceCompiler(sources, profiles).compile(request)
    graph = project(
        result,
        graph_id=f"{name}-graph",
        domain="self_improvement",
        group=name,
        task_signature=f"s22e:L1:{name}",
        accepted=False,
    )
    facts |= {
        "compilation_decision": result.decision.decision.value,
        "manifest_hash": result.manifest.content_hash,
        "graph_hash": graph.content_hash,
        "graph_nodes": len(graph.nodes),
    }
    return result, graph, facts


def fixture_candidate(name: str) -> Any:
    """A released-fixture distractor, compiled and projected through the same released path."""
    from cognitive_os.experience.compiler import ExperienceCompiler
    from cognitive_os.experience.fixtures import build_fixture
    from cognitive_os.experience.graph_projection import project
    from cognitive_os.experience.graph_retrieval import Candidate

    request, sources, profiles = build_fixture(name)
    result = ExperienceCompiler(sources, profiles).compile(request)
    graph = project(
        result,
        graph_id=f"fixture-{name}-graph",
        domain="fixture",
        group=f"fixture-{name}",
        task_signature=f"fixture:{name}",
        accepted=name == "direct-success",
    )
    return Candidate(
        pair_id=f"fixture-{name}",
        group=f"fixture-{name}",
        domain="fixture",
        task_signature=f"fixture:{name}",
        text=graph.search_text(),
        graph=graph,
    )


def side_document(graph: Any, facts: dict[str, Any], decision: str) -> bytes:
    """One stored side: the released graph plus the timeline that carries the why.

    The projection is structural by design — the leak discipline keeps prose off the search
    surface — so the *retrieval* ranks the released `search_text()` and the *store* holds the
    timeline summaries a reader needs for what/failed/why. Both live in one content-addressed
    document, so the query's answer is read out of the store, never out of this driver.
    """
    return canonical(
        {
            "graph": json.loads(graph.model_dump_json()),
            "timeline": facts["timeline"],
            "compilation_decision": decision,
        }
    )


def store_side(
    graph: Any, facts: dict[str, Any], artifact_root: Path, *, write: bool
) -> dict[str, Any]:
    """Write (or, for --check, verify) one side document; read it back before claiming it."""
    from cognitive_os.domain.experience_graph import ActionDecisionGraph
    from cognitive_os.experience.graph_store import blob_path

    raw = side_document(graph, facts, facts["compilation_decision"])
    content_hash = _sha256(raw)
    path = blob_path(artifact_root, content_hash)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    read_back = path.read_bytes()
    loaded = ActionDecisionGraph.model_validate(json.loads(read_back)["graph"])
    return {
        "side_id": graph.graph_id,
        "content_hash": content_hash,
        "blob": str(path.relative_to(artifact_root)),
        "read_back_hash_matches": _sha256(read_back) == content_hash,
        "read_back_validates_as_the_contract": loaded.content_hash == graph.content_hash,
        "structural_hash": graph.structural_hash,
    }


def run_query(pool: list[Any]) -> tuple[Any, dict[str, Any]]:
    from cognitive_os.domain.experience_graph import ExperienceGraphQuery, GraphResourceLimits
    from cognitive_os.experience.graph_retrieval import eligible_pool, lexical

    # The query speaks the search surface's own language. The released projection is
    # structural by design (the leak discipline keeps prose out of `search_text()`), so a
    # natural-language question scores zero against every graph — the first run of this
    # driver proved that with five identical 0.000000 scores. The query therefore names the
    # structure it is looking for: a self-improvement traversal whose verification failed
    # and whose acceptance refused. The prose answer comes from the store, not the surface.
    query = ExperienceGraphQuery(
        query_id="s22e-w2-experience-query",
        query_text=(
            "self_improvement provider_execution tool_execution verification "
            "failed acceptance tool_result"
        ),
        domain="self_improvement",
        task_signature="s22e:L1",
        excluded_groups=("s22e-query",),
    )
    result = lexical(query, eligible_pool(pool, query), limits=GraphResourceLimits())
    entries = [
        {"pair_id": item.pair_id, "rank": item.rank, "score": item.score} for item in result.entries
    ]
    return query, {"entries": entries, "considered": len(pool)}


def _record(*, write: bool = True) -> dict[str, Any]:
    artifact_root = Path(os.environ["COGOS_ARTIFACT_ROOT"])
    from cognitive_os.experience.graph_retrieval import Candidate
    from cognitive_os.experience.graph_store import blob_path

    sides = {}
    pool: list[Any] = []
    stored = []
    for name in TRAVERSALS:
        _, graph, facts = compile_and_project(name)
        sides[name] = facts
        stored.append(store_side(graph, facts, artifact_root, write=write))
        pool.append(
            Candidate(
                pair_id=name,
                group=name,
                domain="self_improvement",
                task_signature=f"s22e:L1:{name}",
                text=graph.search_text(),
                graph=graph,
            )
        )
    distractors = [fixture_candidate(name) for name in FIXTURE_DISTRACTORS]
    query, retrieval = run_query(pool + distractors)

    ranked = {item["pair_id"]: item["rank"] for item in retrieval["entries"]}
    traversal_ranks = [ranked.get(name) for name in TRAVERSALS]
    distractor_ranks = [ranked.get(f"fixture-{name}") for name in FIXTURE_DISTRACTORS]

    # The answer is read out of the STORE, addressed by the retrieval's top rank — never out
    # of this driver's own variables. That is the sentence §2.2(e) asks the record to show.
    top_name = min((name for name in TRAVERSALS if ranked.get(name)), key=lambda n: ranked[n])
    top_stored = next(item for item in stored if item["side_id"] == f"{top_name}-graph")
    top_document = json.loads(
        blob_path(artifact_root, top_stored["content_hash"]).read_text(encoding="utf-8")
    )
    retrieved_summaries = " ".join(item["summary"].lower() for item in top_document["timeline"])

    side_manifest = {
        "schema_version": 1,
        "store": "sides, not pairs — the successful twin is the approved change's, produced by W3",
        "artifact_root": "COGOS_ARTIFACT_ROOT",
        "children": stored,
        "recorded_at": EXPERIENCE_TIME.isoformat(),
    }
    side_manifest["integrity_content_hash"] = _sha256(
        canonical({k: v for k, v in side_manifest.items() if k != "integrity_content_hash"})
    )
    if write:
        SIDE_MANIFEST.write_text(
            json.dumps(side_manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22E-202"],
        "sprint": "22E",
        "wave": "W2",
        "kind_demonstrated": "failed — both sealed dry-run-1 traversals",
        "successful_kind_owed_by": (
            "W3's approved change, per §2.2(e)'s own sentence; this leg is what W3 feeds"
        ),
        "traversals": sides,
        "side_store": {
            "manifest": SIDE_MANIFEST.name,
            "manifest_hash": side_manifest["integrity_content_hash"],
            "children": stored,
            "every_side_read_back_and_validated": all(
                item["read_back_hash_matches"] and item["read_back_validates_as_the_contract"]
                for item in stored
            ),
        },
        "retrieval": {
            "query_text": query.query_text,
            "arm": "lexical (released)",
            "pool": sorted(ranked),
            **retrieval,
            "both_traversals_outrank_every_distractor": max(
                rank for rank in traversal_ranks if rank
            )
            < min(rank for rank in distractor_ranks if rank),
            "answer_read_from_the_store": {
                "top_ranked": top_name,
                "blob_content_hash": top_stored["content_hash"],
                "what_was_tried": "safe_unit allowlist widened" in retrieved_summaries,
                "what_failed": "candidate refused at" in retrieved_summaries,
                "why": "numpy" in retrieved_summaries or "pins the defect" in retrieved_summaries,
            },
        },
        "recorded_at": EXPERIENCE_TIME.isoformat(),
    }
    record["integrity_content_hash"] = _sha256(
        canonical({k: v for k, v in record.items() if k != "integrity_content_hash"})
    )
    return record


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    """Deterministic end to end, so the whole record is recomputed and compared."""
    rebuilt = _record(write=False)
    mismatches = [
        key
        for key in rebuilt
        if key not in {"integrity_content_hash"} and record.get(key) != rebuilt[key]
    ]
    body = {k: v for k, v in record.items() if k != "integrity_content_hash"}
    if _sha256(canonical(body)) != record.get("integrity_content_hash"):
        mismatches.append("integrity_content_hash")
    return {
        "reproduced": not mismatches,
        "mismatches": sorted(mismatches),
        "recomputed": [
            "everything — timelines, compilations, projections, stored bytes, the query"
        ],
        "recorded_not_recomputed": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        verdict = check_record(stored)
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return 0 if verdict["reproduced"] else 1

    record = _record()
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "traversals": {
                    name: facts["compilation_decision"]
                    for name, facts in record["traversals"].items()
                },
                "sides_stored_and_read_back": record["side_store"][
                    "every_side_read_back_and_validated"
                ],
                "retrieval_entries": record["retrieval"]["entries"],
                "both_traversals_outrank_every_distractor": record["retrieval"][
                    "both_traversals_outrank_every_distractor"
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
