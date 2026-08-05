#!/usr/bin/env python
"""S21D3-043 to -046: resolve, project, evaluate and decide the new retrieval holdout.

One command, because the four items are one one-way door and the order *is* the evidence:

1. the sixty sealed retrieval groups are checked against every correction role and against the
   D1 query set, so a query that reuses a task, a signature or a body never reaches a ranking;
2. each surviving group is executed — the failed state fails its hidden suite, the repair
   passes it — and the two runs are compiled into one correction trajectory;
3. the trajectory is projected into a bounded failed/success graph pair with a canonical edit
   path, and the pair set is verified by the released graph store rather than by this script;
4. the queries and their relevance judgements are frozen and written *before* any arm runs;
5. every arm is evaluated exactly once, through the operator benchmark;
6. the pre-registered floors are applied to what came out.

Nothing here tunes anything. The arms, the fusion constant, the weights, the resource policy
and the floors were all frozen in W0, and the relevance rule is Sprint 21D1's — same task
family — chosen here before the first ranking existed and recorded with the chance baseline it
implies, so nobody has to take "0.70 is a high bar" on trust.

Storage is the isolated D3 pair from S21D3-002 (`COGOS_DATABASE_URL`, `COGOS_ARTIFACT_ROOT`,
normally from `.env.s21d3.local`). No predecessor store is opened.

    scripts/retrieval_holdout_d3.py --model <frozen-minilm>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from math import comb
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.application.services.reality_campaign_runner import (  # noqa: E402
    RealityCampaignRunner,
)
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder  # noqa: E402
from cognitive_os.coding.reality_integrity import fingerprint  # noqa: E402
from cognitive_os.coding.reality_leakage import (  # noqa: E402
    judgement_leaks,
    near_clone_pairs,
)
from cognitive_os.coding.reality_retrieval_specs_d3 import (  # noqa: E402
    D3_RETRIEVAL_SPECS,
    D3RetrievalSpec,
)
from cognitive_os.coding.reality_trajectories import (  # noqa: E402
    CorrectionStep,
    build_request,
    plan_repair_path,
)
from cognitive_os.domain.experience_graph import (  # noqa: E402
    GRAPH_RESOURCE_POLICY_REVISION_2,
    GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
    FailedSuccessGraphPair,
)
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.domain.sandbox import SandboxLimits  # noqa: E402
from cognitive_os.events.catalog import build_default_event_catalog  # noqa: E402
from cognitive_os.events.coding_event_service import CodingEventService  # noqa: E402
from cognitive_os.experience.compiler import ExperienceCompiler  # noqa: E402
from cognitive_os.experience.graph_projection import (  # noqa: E402
    derive_edit_path,
    project_correction,
    round_trips,
)
from cognitive_os.experience.graph_store import blob_path, load_evidence  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402
from cognitive_os.learning.correction_catalogue_d3 import (  # noqa: E402
    build_retrieval_pool,
    seal_d3_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox  # noqa: E402

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d3-pre-registration.json"
D1_QUERIES = EVIDENCE / "sprint-21d1-graph-queries.json"
D1_ROOT = EVIDENCE / "sprint-21d1-emg-root.json"
D1_BENCHMARK = EVIDENCE / "sprint-21d1-retrieval-benchmark.json"
D1_ARTIFACTS = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d1")

#: What S21D3-001 recorded for the frozen query set. Naming it makes "unchanged" a comparison
#: against a released value rather than against whatever is on disk right now.
D1_QUERY_SET_SHA256 = "0a82bfe390a9216f1017bbeb70a09e29ef4747519fb4b8fd6bcf0803efb6650a"

GRAPH_ROOT = EVIDENCE / "sprint-21d3-retrieval-emg-root.json"
QUERY_MANIFEST = EVIDENCE / "sprint-21d3-retrieval-queries.json"
HOLDOUT_RESULT = EVIDENCE / "sprint-21d3-retrieval-holdout-result.json"

SANDBOX_IMAGE = "cognitive-os-sandbox:sprint-5"

#: The same identity S21D3-034 used, so a retrieval run and a correction run are decided by
#: one verifier profile rather than by two that happen to agree.
D3_CAMPAIGN_NAMESPACE = UUID("b7d61c48-2e05-5a3f-9c14-7f2a8d6b4e93")
D3_VERIFIER_PROFILE_HASH = uuid5(D3_CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2
D3_CAMPAIGN_VERSION = 3

#: Task generation is a pure function of the template, the seed and this constant.
GENERATION_EPOCH = datetime(2026, 8, 5, tzinfo=UTC)
RETRIEVAL_SEED = 21_043_707

LIMITS = SandboxLimits(
    timeout_seconds=120,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=200_000,
    maximum_stderr_bytes=200_000,
    maximum_artifact_bytes=200_000,
)

#: S21D3-046's floors, verbatim from the gate manifest. Not parameters.
RECALL_AT_5_FLOOR = 0.70
MRR_AT_10_FLOOR = 0.50
MINIMUM_QUERIES = 50

ARM_ORDER = (
    "no_memory",
    "exact_signature",
    "lexical",
    "minilm_vector",
    "minilm_shortlist_plus_bounded_ged",
    "reciprocal_rank_fusion",
)

#: What a retrieval stop closes that was not already closed. S21D3-047 is deliberately absent:
#: it proves the advisory boundary for *every* retrieval outcome, so a negative result is a
#: reason to run it rather than a reason to skip it. Everything downstream of a closed
#: condition 15 — S21D3-067, -068 and the success release — already carries a `not_opened`
#: record bound to W2's earlier correction stop, and first-failure precedence says a dependent
#: is bound to the *first* failure, not to every later one.
DEPENDENT_ON_A_RETRIEVAL_STOP: tuple[str, ...] = ()

#: Named so the record says where those dependants are already bound rather than implying
#: nothing closed them.
EARLIER_STOP = "sprint-21d3-learner-selection.json, S21D3-039 null selection"


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D3 environment first:\n"
            f"    set -a && . ./.env.s21d3.local && set +a"
        )
    return value


def _hash(text: str) -> str:
    return sha256(text.encode()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, dict):
        value = {**value, "integrity_content_hash": _hash(_canonical_bytes(value).decode())}
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


# --------------------------------------------------------------- S21D3-043: separation


def _separation() -> dict[str, Any]:
    """Every way a holdout query could be something the experiment has already seen.

    Cheap and first, before a single container starts: a pool that fails separation is not a
    pool whose execution is worth paying for.
    """
    bundle = seal_d3_corpus()
    correction_groups = {
        partition.value: bundle.groups_of(partition) for partition in CorrectionPartition
    }
    retrieval_groups = {spec.repository_group for spec in D3_RETRIEVAL_SPECS}
    d1 = json.loads(D1_QUERIES.read_text())
    d1_signatures = {record["task_signature"] for record in d1}
    d1_queries = {record["query_id"] for record in d1}

    # The released detector over every retrieval body. An intra-pair collision is a group's own
    # two states, which is the edit path the projection derives; a *cross-group* collision would
    # be two queries whose answers are the same code, and that is what has to be zero.
    bodies = {
        f"{spec.repository_group}:{state}": spec.module_text(body)
        for spec in D3_RETRIEVAL_SPECS
        for state, body in (("failed", spec.failed), ("repaired", spec.repaired))
    }
    cross_group_clones = sorted(
        f"{item.left}|{item.right}|{item.reason}"
        for item in near_clone_pairs(bodies)
        if item.left.split(":")[0] != item.right.split(":")[0]
    )
    return {
        "retrieval_groups": len(retrieval_groups),
        "correction_groups_by_role": {
            role: len(members) for role, members in sorted(correction_groups.items())
        },
        "retrieval_crossing_a_correction_role": sorted(
            retrieval_groups & set().union(*correction_groups.values())
        ),
        "task_signatures_reused_from_d1": sorted(
            {spec.task_signature for spec in D3_RETRIEVAL_SPECS} & d1_signatures
        ),
        "query_ids_reused_from_d1": sorted(
            {f"q:{spec.repository_group}" for spec in D3_RETRIEVAL_SPECS} & d1_queries
        ),
        "d1_query_set_sha256": _hash(D1_QUERIES.read_text()),
        "cross_group_near_clones": cross_group_clones,
        "sealed_pool_hash": build_retrieval_pool().content_hash,
        "d3_seal_hash": bundle.seal.content_hash,
    }


# --------------------------------------------------------------- S21D3-044: execute and project


async def _pair_for(
    spec: D3RetrievalSpec,
    *,
    runner: RealityCampaignRunner,
    artifacts: ArtifactService,
    scratch: Path,
) -> tuple[FailedSuccessGraphPair, dict[str, Any]]:
    """Run one group's two states, compile the path they form, and project the pair.

    The baseline is the failed state and the single candidate is the repair, so the recorded
    claim is exactly the one the corpus authored: the verifier refused this, then accepted
    that. `RealityOutcomeReference` refuses a baseline that passed and a `correct_*` candidate
    that failed, so a group whose declaration was wrong cannot reach the projection.
    """
    prepared = await runner.prepare_task(
        spec.template_id,
        root=scratch / spec.repository_group,
        seed=RETRIEVAL_SEED,
        generated_at=GENERATION_EPOCH,
    )
    baseline = await runner.run_baseline(prepared)
    repair = await runner.run_candidate(prepared, RealityCandidateStrategy.CORRECT_NARROW)

    plan = plan_repair_path(
        task_id=prepared.generated.manifest.task_id,
        baseline=CorrectionStep(reference=baseline.step.reference),
        repair=repair.step,
    )
    request, sources, profiles = await build_request(
        plan, task=prepared.generated.manifest, artifacts=artifacts, created_at=GENERATION_EPOCH
    )
    result = ExperienceCompiler(sources, profiles).compile(request)
    assessments = [item.model_dump(mode="json") for item in result.assessments]
    # W3-F2. `search_text()` puts the task signature in front of every arm, so a signature
    # that spells its own task family hands the relevance judgement to the ranker. Sprint
    # 21D1's signature is the reality task id — an opaque uuid5 over template and seed — and
    # that is what a graph signature is for: binding the pair to the run that produced it,
    # not describing it. The sealed pool keeps its own readable identity; separation is a
    # different question from what a ranker may see.
    signature = str(prepared.generated.manifest.task_id)
    failed, successful = project_correction(
        assessments,
        domain="coding",
        group=spec.repository_group,
        task_signature=signature,
        source_manifest_hash=result.manifest.content_hash,
        limits=GRAPH_RESOURCE_POLICY_REVISION_2,
    )
    edit_path = derive_edit_path(failed, successful, path_id=spec.repository_group)
    pair = FailedSuccessGraphPair(
        pair_id=spec.repository_group,
        domain="coding",
        group=spec.repository_group,
        task_signature=signature,
        failed=failed,
        successful=successful,
        edit_path=edit_path,
        legacy_recompilation_unavailable=False,
        verification_mode="compiled_from_recorded_outcomes",
        compiled_at=GENERATION_EPOCH,
    )
    report = {
        "group": spec.repository_group,
        "family": spec.family.value,
        "template_id": spec.template_id,
        "task_id": signature,
        "graph_task_signature_names_the_family": spec.family.value in signature,
        "task_manifest_hash": prepared.generated.manifest.content_hash,
        "compilation_id": str(result.manifest.compilation_id),
        "baseline_hidden_passed": baseline.step.reference.hidden_verification_passed,
        "repair_hidden_passed": repair.step.reference.hidden_verification_passed,
        "assessments": len(assessments),
        "failed_nodes": len(failed.nodes),
        "successful_nodes": len(successful.nodes),
        "edit_operations": len(edit_path.operations),
        "round_trips": round_trips(failed, successful, edit_path),
        "pair_hash": pair.content_hash,
        "trajectory_sources_declared": len(request.trajectory_sources),
        "trajectory_sources_resolved": len(result.snapshot.source_refs),
        "verifier_bundle_passed": result.verifier_bundle.passed,
        "source_hashes_resolved": await _store_backed_sources_resolve(
            [
                (
                    baseline.step.reference.hidden_evidence_artifact_id,
                    baseline.step.reference.hidden_evidence_hash,
                ),
                (
                    repair.step.reference.hidden_evidence_artifact_id,
                    repair.step.reference.hidden_evidence_hash,
                ),
                (repair.step.candidate.patch_artifact_id, repair.step.candidate.patch_hash),
            ],
            artifacts=artifacts,
        ),
    }
    return pair, report


async def _store_backed_sources_resolve(
    references: list[tuple[UUID, str]], *, artifacts: ArtifactService
) -> bool:
    """Read each stored source back and compare its bytes to the hash the pair declares.

    `build_request` already refuses a path whose artifacts do not resolve, so this is a second
    read after the fact rather than the only one — and a second read is what turns "the
    compiler did not complain" into a resolution the evidence file can state.
    """
    for artifact_id, expected in references:
        try:
            payload = await artifacts.get_bytes(artifact_id)
        except Exception:  # every store failure is the same failure here
            return False
        if sha256(payload).hexdigest() != expected:
            return False
    return True


def _store_pairs(pairs: list[FailedSuccessGraphPair], *, artifact_root: Path) -> dict[str, Any]:
    """Write each pair as a content-addressed blob and declare it in one root manifest."""
    children = []
    for pair in pairs:
        raw = pair.model_dump_json().encode()
        digest = sha256(raw).hexdigest()
        path = blob_path(artifact_root, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        children.append(
            {
                "pair_id": pair.pair_id,
                "content_hash": digest,
                "pair_hash": pair.content_hash,
                "failed_structural": pair.failed.structural_hash,
                "successful_structural": pair.successful.structural_hash,
                "edit_path_hash": pair.edit_path.content_hash,
                "group": pair.group,
                "role": "retrieval_holdout",
            }
        )
    return {
        "graph_set_id": "sprint-21d3-retrieval-holdout",
        "pair_count": len(children),
        "children": sorted(children, key=lambda item: item["pair_id"]),
    }


# --------------------------------------------------------------- S21D3-043: queries


def _d1_untouched() -> dict[str, Any]:
    """The predecessor evidence this wave reads, by hash, and its store by fingerprint.

    Fingerprinting the whole `docs/sprints/sprint-21` tree would be the wrong check: this
    command writes its own evidence into that tree, so the answer would always be "changed"
    and would say nothing about D1. What has to be unchanged is D1's own files and D1's own
    Artifact Store, and the query set is compared against the hash S21D3-001 published.
    """
    return {
        "artifact_store": str(D1_ARTIFACTS),
        "artifact_store_fingerprint": fingerprint(D1_ARTIFACTS),
        "artifact_store_writes": 0,
        "graph_root_sha256": _hash(D1_ROOT.read_text()),
        "retrieval_benchmark_sha256": _hash(D1_BENCHMARK.read_text()),
        "query_set_sha256": _hash(D1_QUERIES.read_text()),
        "query_set_matches_the_published_hash": (
            _hash(D1_QUERIES.read_text()) == D1_QUERY_SET_SHA256
        ),
        "d1_or_d2_evidence_files_written": 0,
    }


def _judgement_leaks(
    pairs: list[FailedSuccessGraphPair], specs: dict[str, D3RetrievalSpec]
) -> list[str]:
    """Every ranked text of this holdout, against the labels it is judged by. §S21D3-043.

    Relevance here is "same task family", so a family name anywhere in a searchable text is
    the label itself. Fail-closed rather than reported: a benchmark that can return a perfect
    1.0000 by reading its own judgement is not a benchmark.
    """
    searchable = {
        f"{pair.pair_id}:{side}": graph.search_text()
        for pair in pairs
        for side, graph in (("failed", pair.failed), ("successful", pair.successful))
    }
    labels = {
        key: (
            specs[key.split(":")[0]].family.value,
            specs[key.split(":")[0]].family.value.replace("_", " "),
            key.split(":")[0],
        )
        for key in searchable
    }
    return list(judgement_leaks(searchable, labels))


def _queries(pairs: list[FailedSuccessGraphPair], specs: dict[str, D3RetrievalSpec]) -> list[dict]:
    """One query per pair, judged by task family, frozen here and written before any ranking.

    Sprint 21D1's tier-1 rule verbatim: for a coding pair, relevance is the same task family.
    Choosing a rule *after* seeing a ranking is how a holdout becomes a development set, so
    this runs before the benchmark subprocess exists and its output is hashed into the record.
    """
    by_family: dict[str, list[str]] = {}
    for pair in pairs:
        by_family.setdefault(specs[pair.pair_id].family.value, []).append(pair.pair_id)
    records = []
    for pair in sorted(pairs, key=lambda item: item.pair_id):
        family = specs[pair.pair_id].family.value
        relevant = sorted(set(by_family[family]) - {pair.pair_id})
        if not relevant:
            continue
        records.append(
            {
                "query_id": f"q:{pair.pair_id}",
                "domain": pair.domain,
                "task_signature": pair.task_signature,
                "relevance_family": family,
                "relevance_tier": 1,
                "seen_task": False,
                "excluded_groups": [pair.group],
                "relevant_pair_ids": relevant,
                "query_hash": _hash(pair.failed.search_text()),
            }
        )
    return records


def _discriminability(
    pairs: list[FailedSuccessGraphPair], payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """How much of the searchable text actually differs between two candidates.

    A retrieval floor is only informative if the arms have something to rank on. The
    released projection puts trajectory *shape* in front of an arm — node kinds, four
    assessment attributes, edge kinds — and deliberately keeps the repaired code, the issue
    text and the provenance hashes out of it. On a corpus of uniform repair paths that
    leaves one line differing per candidate, and this says so as a count rather than
    leaving a reader to infer it from a suspiciously flat table.
    """
    texts = [pair.successful.search_text() for pair in pairs]
    without_signature = ["\n".join(text.splitlines()[2:]) for text in texts]
    report: dict[str, Any] = {
        "candidates": len(texts),
        "distinct_searchable_texts": len(set(texts)),
        "distinct_after_removing_domain_and_signature": len(set(without_signature)),
        "note": (
            "ActionDecisionGraph.search_text() is domain, task signature, node labels and "
            "edge kinds. It carries no repaired source, no issue text and no provenance "
            "hash, so two structurally identical trajectories are one document to every arm "
            "except for their opaque signatures."
        ),
    }
    if payload is not None:
        alphabetical = sorted(pair.pair_id for pair in pairs)
        report["arms_ranking_by_the_pair_id_tie_break"] = sorted(
            arm
            for arm, rows in payload["per_query"].items()
            if rows
            and all(
                row["ranked_pair_ids"]
                == [item for item in alphabetical if item not in row["query_id"]][
                    : len(row["ranked_pair_ids"])
                ]
                for row in rows
            )
            and any(row["ranked_pair_ids"] for row in rows)
        )
    return report


def _chance_baseline(records: list[dict], pool: int) -> dict[str, float]:
    """What a uniformly random ranking would score, so a floor can be read in context.

    A floor is only a bar if it is above what nothing achieves. `no_memory` measures zero
    because it returns nothing at all; the interesting null is an arm that returns *something*
    arbitrary, and that is arithmetic rather than a run.
    """
    recall = []
    reciprocal = []
    for record in records:
        eligible = pool - len(record["excluded_groups"])
        relevant = len(record["relevant_pair_ids"])
        miss = comb(eligible - relevant, 5) / comb(eligible, 5) if eligible - relevant >= 5 else 0
        recall.append(1 - miss)
        # E[1/rank of the first relevant] over a uniformly random permutation, truncated at ten.
        expectation = 0.0
        for rank in range(1, 11):
            survivors = eligible - relevant - (rank - 1)
            if survivors < 0:
                break
            probability = (comb(eligible - relevant, rank - 1) / comb(eligible, rank - 1)) * (
                relevant / (eligible - rank + 1)
            )
            expectation += probability / rank
        reciprocal.append(expectation)
    return {
        "recall_at_5": round(sum(recall) / len(recall), 4),
        "mrr_at_10": round(sum(reciprocal) / len(reciprocal), 4),
        "arm": "uniformly_random_ranking_of_the_eligible_pool",
    }


# --------------------------------------------------------------- S21D3-045/046


def _evaluate(model: Path, artifact_root: Path) -> dict[str, Any]:
    """The operator benchmark, once, after the queries and judgements are on disk."""
    done = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY / "scripts" / "experience.py"),
            "graph-benchmark",
            "--graph-root",
            str(GRAPH_ROOT),
            "--artifact-root",
            str(artifact_root),
            "--queries",
            str(QUERY_MANIFEST),
            "--model",
            str(model),
            "--policy-hash",
            GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
        ],
        capture_output=True,
        text=True,
        cwd=REPOSITORY,
    )
    if done.returncode != 0:
        raise SystemExit(f"graph-benchmark refused:\n{done.stderr}")
    return json.loads(done.stdout)


def _decide(payload: dict[str, Any], recorded_at: str) -> dict[str, Any]:
    """S21D3-046: the frozen floors, applied in the frozen order, to what came out.

    First-failure precedence, so a pass needs one arm to clear *both* floors; an arm that
    clears recall and misses MRR is a recorded near miss, never a pass.
    """
    trace = []
    winner = None
    for arm in ARM_ORDER:
        metrics = payload["arms"][arm]
        recall_ok = metrics["top_5_recall"] >= RECALL_AT_5_FLOOR
        mrr_ok = metrics["mrr_at_10"] >= MRR_AT_10_FLOOR
        trace.append(
            {
                "arm": arm,
                "recall_at_5": metrics["top_5_recall"],
                "recall_at_5_floor_met": recall_ok,
                "mrr_at_10": metrics["mrr_at_10"],
                "mrr_at_10_floor_met": mrr_ok,
                "first_failed_floor": (
                    None
                    if recall_ok and mrr_ok
                    else ("recall_at_5" if not recall_ok else "mrr_at_10")
                ),
                "within_budgets": metrics["timeouts"] == 0
                and metrics["max_latency_ms"]
                <= payload["resource_policy"]["query_budget_seconds"] * 1000,
                "reproducible": payload["repeated_ranking_agreement_by_arm"][arm],
            }
        )
        if winner is None and recall_ok and mrr_ok and trace[-1]["within_budgets"]:
            winner = arm
    enough = payload["queries"] >= MINIMUM_QUERIES
    passed = winner is not None and enough
    stop_hash = (
        None if passed else _hash(_canonical_bytes({"trace": trace, "at": recorded_at}).decode())
    )
    return {
        "rule": (
            f"one arm reaches Recall@5 >= {RECALL_AT_5_FLOOR} and MRR@10 >= {MRR_AT_10_FLOOR} "
            f"on at least {MINIMUM_QUERIES} unseen-task queries, inside all fixed budgets"
        ),
        "queries": payload["queries"],
        "minimum_queries_met": enough,
        "trace": trace,
        "winning_arm": winner,
        "passed": passed,
        "first_failed_floor": (
            None
            if passed
            else (
                "query_count"
                if not enough
                else min(
                    (row for row in trace if row["first_failed_floor"]),
                    key=lambda row: (-row["recall_at_5"], -row["mrr_at_10"]),
                )["first_failed_floor"]
            )
        ),
        "stop_hash": stop_hash,
        "gate_d1_condition_15": "closed" if passed else "remains_open",
        "gate_l2_condition_24": "met" if passed else "not_met",
        "negative_retrieval_result": not passed,
        "no_alternative_opened": {
            "fusion_variants": 0,
            "widths": 0,
            "weights": 0,
            "metrics": 0,
            "holdout_members_added": 0,
        },
        "dependent_not_opened": [
            {
                "status": "not_opened",
                "item": item,
                "parent_stop_hash": stop_hash,
                "reason": "the independent retrieval holdout returned a negative result",
                "recorded_at": recorded_at,
                "content_hash": _hash(f"{item}:{stop_hash}"),
            }
            for item in (() if passed else DEPENDENT_ON_A_RETRIEVAL_STOP)
        ],
        "dependants_already_bound_to_an_earlier_stop": ("" if passed else EARLIER_STOP),
        "s21d3_047_runs_on_every_outcome": True,
    }


# --------------------------------------------------------------- the command


async def _run(model: Path, output: Path, group_limit: int | None) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1", "s21d2"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D3 writes only to its own pair")

    separation = _separation()
    for key in (
        "retrieval_crossing_a_correction_role",
        "task_signatures_reused_from_d1",
        "query_ids_reused_from_d1",
        "cross_group_near_clones",
    ):
        if separation[key]:
            raise SystemExit(f"refusing to resolve a holdout that fails separation: {key}")

    engine = create_postgres_engine(database_url)
    specs = {spec.repository_group: spec for spec in D3_RETRIEVAL_SPECS}
    selected = list(D3_RETRIEVAL_SPECS)[: group_limit or len(D3_RETRIEVAL_SPECS)]
    pairs: list[FailedSuccessGraphPair] = []
    projections: list[dict[str, Any]] = []
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        recorder = CodingOutcomeRecorder(artifacts, CodingEventService(events), events)
        runner = RealityCampaignRunner(
            sandbox=DockerSandbox(SANDBOX_IMAGE),
            artifacts=artifacts,
            recorder=recorder,
            harvester=None,
            limits=LIMITS,
            image_digest=SANDBOX_IMAGE,
            verifier_profile_hash=D3_VERIFIER_PROFILE_HASH,
            campaign_version=D3_CAMPAIGN_VERSION,
        )
        with tempfile.TemporaryDirectory(prefix="cogos-d3-retrieval-") as scratch:
            for index, spec in enumerate(selected):
                print(
                    f"[pair {index + 1}/{len(selected)}] {spec.repository_group}", file=sys.stderr
                )
                pair, report = await _pair_for(
                    spec, runner=runner, artifacts=artifacts, scratch=Path(scratch)
                )
                pairs.append(pair)
                projections.append(report)
    finally:
        await engine.dispose()

    root = _store_pairs(pairs, artifact_root=artifact_root)
    _write(GRAPH_ROOT, root)
    evidence = load_evidence(GRAPH_ROOT, artifact_root)
    if not evidence.intact:
        raise SystemExit(f"the projected pair set does not resolve: {evidence.missing_bytes}")

    leaks = _judgement_leaks(pairs, specs)
    if leaks:
        raise SystemExit(f"refusing to rank text that names its own judgement: {leaks[:5]}")

    records = _queries(pairs, specs)
    _write(QUERY_MANIFEST, records)
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    payload = _evaluate(model.resolve(), artifact_root)
    decision = _decide(payload, recorded_at)

    result = {
        "schema_version": 1,
        "sprint": "21D3",
        "wave": "W3",
        "items": ["S21D3-043", "S21D3-044", "S21D3-045", "S21D3-046"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": _hash(PRE_REGISTRATION.read_text()),
        "final_outcomes_inspected": False,
        "separation": separation,
        "projection": {
            "pairs": len(pairs),
            "source_resolution": sum(1 for row in projections if row["source_hashes_resolved"]),
            "edit_path_round_trips": sum(1 for row in projections if row["round_trips"]),
            "bounds": {
                "declared": GRAPH_RESOURCE_POLICY_REVISION_2.model_dump(mode="json"),
                "max_nodes": max(row["successful_nodes"] for row in projections),
                "min_nodes": min(row["failed_nodes"] for row in projections),
                "max_edit_operations": max(row["edit_operations"] for row in projections),
                "over_limit_graphs": 0,
            },
            "creates_execution_or_correction_authority": False,
            "per_pair": projections,
        },
        "graph_set": {
            "root": str(GRAPH_ROOT.relative_to(REPOSITORY)),
            "root_sha256": _hash(GRAPH_ROOT.read_text()),
            "graph_set_id": evidence.graph_set_id,
            "declared_pairs": evidence.declared_pairs,
            "resolved_pairs": len(evidence.pairs),
            "intact": evidence.intact,
            "artifact_root": str(artifact_root),
        },
        "query_set": {
            "path": str(QUERY_MANIFEST.relative_to(REPOSITORY)),
            "sha256": _hash(QUERY_MANIFEST.read_text()),
            "queries": len(records),
            "by_domain": dict(Counter(record["domain"] for record in records)),
            "by_tier": dict(Counter(str(record["relevance_tier"]) for record in records)),
            "by_family": dict(Counter(record["relevance_family"] for record in records)),
            "relevance_rule": "Sprint 21D1 tier 1: same task family, own group always excluded",
            "frozen_before_ranking": True,
            "arms_can_read_judgements": False,
            "searchable_text_naming_its_own_judgement": leaks,
            "seen_task_queries": 0,
            "chance_baseline": _chance_baseline(records, len(pairs)),
        },
        "discriminability": _discriminability(pairs, payload),
        "benchmark": {
            "content_hash": payload["content_hash"],
            "schema_version": payload["schema_version"],
            "executions": 1,
            "resource_policy": payload["resource_policy"],
            "model": payload["model"],
            "repeated_ranking_agreement": payload["repeated_ranking_agreement"],
            "repeated_ranking_agreement_by_arm": payload["repeated_ranking_agreement_by_arm"],
            "command": (
                "scripts/experience.py graph-benchmark --graph-root <root> --artifact-root "
                "<store> --queries <manifest> --model <frozen-minilm> --policy-hash "
                f"{GRAPH_RESOURCE_POLICY_REVISION_2_HASH}"
            ),
        },
        "arms": {arm: payload["arms"][arm] for arm in ARM_ORDER},
        "per_query": payload["per_query"],
        "decision": decision,
        "predecessor_read_only": _d1_untouched(),
    }
    _write(output, result)

    print(f"\n{output}")
    for arm in ARM_ORDER:
        row = result["arms"][arm]
        print(
            f"  {arm:<34} recall@5={row['top_5_recall']:.4f} mrr@10={row['mrr_at_10']:.4f} "
            f"ndcg@10={row['ndcg_at_10']:.4f} p95={row['p95_latency_ms']:.1f}ms"
        )
    print(f"  queries={len(records)} winner={decision['winning_arm']} passed={decision['passed']}")
    return 0


def _redecide(output: Path) -> int:
    """Re-apply the frozen rule to the numbers already recorded. No arm runs.

    S21D3-045 forbids a rerun after metrics are read, and it should: a second execution is a
    second sample. Re-deriving a *decision* from the stored metrics is not that — `_decide` is
    a pure function of numbers this file already holds, and the arms, queries and judgements
    are untouched. Used when the rule's own bookkeeping was wrong and the measurement was not.
    """
    stored = json.loads(output.read_text())
    payload = {
        "arms": stored["arms"],
        "queries": stored["query_set"]["queries"],
        "resource_policy": stored["benchmark"]["resource_policy"],
        "repeated_ranking_agreement_by_arm": stored["benchmark"][
            "repeated_ranking_agreement_by_arm"
        ],
    }
    stored.pop("integrity_content_hash", None)
    stored.pop("d1_evidence_tree_unchanged", None)
    stored["decision"] = _decide(payload, stored["recorded_at"])
    stored["decision"]["rederived_without_re_execution"] = True
    # A filesystem property, not a measurement: recomputing it now is the same read.
    stored["predecessor_read_only"] = _d1_untouched()
    _write(output, stored)
    print(f"{output}: decision re-derived from the recorded metrics, zero arms executed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--output", type=Path, default=HOLDOUT_RESULT)
    parser.add_argument("--groups", type=int, help="run fewer groups; for a smoke run only")
    parser.add_argument(
        "--redecide",
        action="store_true",
        help="re-apply the frozen rule to an existing result; executes no arm",
    )
    arguments = parser.parse_args()
    if arguments.redecide:
        return _redecide(arguments.output)
    if arguments.model is None:
        parser.error("--model is required unless --redecide is given")
    return asyncio.run(_run(arguments.model, arguments.output, arguments.groups))


if __name__ == "__main__":
    raise SystemExit(main())
