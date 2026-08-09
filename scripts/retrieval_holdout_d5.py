#!/usr/bin/env python3
"""S21D5-043 to -046: resolve, project, evaluate and decide the D5 retrieval holdout.

Adapted from `retrieval_holdout_d4.py`, which had the pipeline right, with one substantive
change and one addition:

*The projection runs under the complete surface.* `structure_fallback=True`, which S21D5-040
measured on this corpus: 27 of 120 sides carry no identifier at all and would have projected
empty under the released extraction. D4's pool reached 41 of 60 documents for exactly that
reason, and this is the wave that turns the answer on.

*Separation is checked against three predecessor query sets, not two.* D4 published its own
sixty queries and sixty task signatures, and a D5 query reusing one would be a query the
programme has already answered.

    --stage resolve    S21D5-043 and -044. Separation, then sixty groups executed rather than
                       declared, projected into failed/success pairs under the complete
                       surface, stored, verified by the released graph store, and the queries
                       frozen to disk. Writes the EMG root, the query manifest, two records.
    --stage evaluate   S21D5-045. Every frozen arm exactly once, through the operator
                       benchmark, against queries that were already on disk before it started.
    --stage decide     S21D5-046. The frozen floors applied to the recorded numbers, in a
                       separate record, because the result it reads is sealed.

Nothing here tunes anything. The arms, the fusion constant, the weights, the resource policy,
the GED iteration budget and the floors were all frozen before this pool existed, and the
relevance rule is Sprint 21D1's — same task family — recorded with the chance baseline it
implies so nobody has to take "0.70 is a high bar" on trust.

Storage is the isolated D5 pair (`COGOS_DATABASE_URL`, `COGOS_ARTIFACT_ROOT`, from
`.env.s21d5.local`). No predecessor store is opened for writing and all three are fingerprinted.

    set -a && . ./.env.s21d5.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/retrieval_holdout_d5.py --stage resolve
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
from cognitive_os.coding.diff import apply_file_patch, parse_unified_diff  # noqa: E402
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder  # noqa: E402
from cognitive_os.coding.reality_integrity import fingerprint  # noqa: E402
from cognitive_os.coding.reality_leakage import judgement_leaks, near_clone_pairs  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d3 import D3RetrievalSpec  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d5 import D5_RETRIEVAL_SPECS  # noqa: E402
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
from cognitive_os.experience.graph_retrieval import GED_ITERATION_BUDGET  # noqa: E402
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
from cognitive_os.learning.correction_catalogue_d5 import (  # noqa: E402
    build_d5_retrieval_pool,
    seal_d5_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d5-contracts.json"
SURFACE = EVIDENCE / "sprint-21d5-surface.json"
SEPARATION_RECORD = EVIDENCE / "sprint-21d5-corpus-separation.json"
GED_DECISION = EVIDENCE / "sprint-21d4-ged-decision.json"

PREDECESSOR_QUERIES = (
    EVIDENCE / "sprint-21d1-graph-queries.json",
    EVIDENCE / "sprint-21d3-retrieval-queries.json",
    EVIDENCE / "sprint-21d4-retrieval-queries.json",
)

GRAPH_ROOT = EVIDENCE / "sprint-21d5-retrieval-emg-root.json"
QUERY_MANIFEST = EVIDENCE / "sprint-21d5-retrieval-queries.json"
QUERY_SET_RECORD = EVIDENCE / "sprint-21d5-retrieval-query-set.json"
PROJECTION_RECORD = EVIDENCE / "sprint-21d5-retrieval-emg-projection.json"
HOLDOUT_RESULT = EVIDENCE / "sprint-21d5-retrieval-holdout-result.json"
DECISION_RECORD = EVIDENCE / "sprint-21d5-retrieval-decision.json"

SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

#: The same identity the D5 correction campaign used, so a retrieval run and a correction run
#: are decided by one verifier profile rather than by two that happen to agree.
D5_CAMPAIGN_NAMESPACE = UUID("8ce6e0b5-5fb1-5547-abc2-5113999efda8")
D5_VERIFIER_PROFILE_HASH = uuid5(D5_CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2
D5_CAMPAIGN_VERSION = 5

#: Task generation is a pure function of the template, the seed and this constant. The epoch is
#: S21D5-025's, so every D5 package this sprint materialises is generated the same way.
GENERATION_EPOCH = datetime(2026, 8, 8, tzinfo=UTC)
RETRIEVAL_SEED = 21_053_705

LIMITS = SandboxLimits(
    timeout_seconds=120,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=200_000,
    maximum_stderr_bytes=200_000,
    maximum_artifact_bytes=200_000,
)

#: S21D5-014's floors, verbatim from the frozen retrieval contract. Not parameters.
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

#: What a retrieval stop would close that is not already closed. S21D5-047 is deliberately
#: absent: it proves the advisory boundary for *every* retrieval outcome, so a negative result
#: is a reason to run it rather than a reason to skip it.
DEPENDENT_ON_A_RETRIEVAL_STOP: tuple[str, ...] = ()

#: Named so a stop record says where the correction-branch dependants are already bound rather
#: than implying this decision closed them.
EARLIER_STOP = "sprint-21d5-continuation.json, S21D5-036 selective_margin_bound"

DATA = Path("/home/palkouser/projekt/cognitive-os-data")
PREDECESSOR_STORES = {
    "artifacts-s21d1": DATA / "artifacts-s21d1",
    "artifacts-s21d3": DATA / "artifacts-s21d3",
    "artifacts-s21d4": DATA / "artifacts-s21d4",
}


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D5 environment first:\n"
            f"    set -a && . ./.env.s21d5.local && set +a"
        )
    return value


def _isolated() -> tuple[str, Path]:
    """The D5 pair, or nothing. A retrieval run must not reach a predecessor store."""
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1", "s21d2", "s21d3", "s21d4"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D5 writes only to its own pair")
    return database_url, artifact_root


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    """The convention every D4 and D5 record shares: hashed bytes are written bytes."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _write(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, dict):
        value = {**value, "integrity_content_hash": _digest(_canonical(value))}
    path.write_bytes(_canonical(value) + b"\n")
    return (
        value["integrity_content_hash"] if isinstance(value, dict) else _digest(_canonical(value))
    )


def _labels(spec: D3RetrievalSpec) -> tuple[str, ...]:
    """What relevance is judged by here, in every spelling a term could carry it."""
    return (spec.family.value, spec.family.value.replace("_", " "), spec.repository_group)


# --------------------------------------------------------------- S21D5-043: separation


def _separation() -> dict[str, Any]:
    """Every way a D5 holdout query could be something the programme has already seen.

    Cheap and first, before a single container starts: a pool that fails separation is not a
    pool whose execution is worth paying for.
    """
    bundle = seal_d5_corpus()
    correction_groups = {
        partition.value: bundle.groups_of(partition) for partition in CorrectionPartition
    }
    retrieval_groups = {spec.repository_group for spec in D5_RETRIEVAL_SPECS}
    seen_signatures: set[str] = set()
    seen_queries: set[str] = set()
    for path in PREDECESSOR_QUERIES:
        for record in json.loads(path.read_text()):
            seen_signatures.add(record["task_signature"])
            seen_queries.add(record["query_id"])

    # The released detector over every retrieval body, at S21D4-043's scope. An intra-pair
    # collision is a group's own two states, which is the edit path the projection derives; a
    # *cross-group* collision would be two queries whose answers are the same code, and that is
    # what has to be zero.
    bodies = {
        f"{spec.repository_group}:{state}": spec.module_text(body)
        for spec in D5_RETRIEVAL_SPECS
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
        "task_signatures_reused_from_a_predecessor": sorted(
            {spec.task_signature for spec in D5_RETRIEVAL_SPECS} & seen_signatures
        ),
        "query_ids_reused_from_a_predecessor": sorted(
            {f"q:{spec.repository_group}" for spec in D5_RETRIEVAL_SPECS} & seen_queries
        ),
        "predecessor_query_sets": {
            path.name: _digest(path.read_bytes()) for path in PREDECESSOR_QUERIES
        },
        "predecessor_queries_compared_against": sum(
            len(json.loads(path.read_text())) for path in PREDECESSOR_QUERIES
        ),
        "cross_group_near_clones": cross_group_clones,
        "sealed_pool_hash": build_d5_retrieval_pool().content_hash,
        "d5_seal_hash": bundle.seal.content_hash,
        "spent_pool_hash": bundle.seal.spent_retrieval_pool_hash,
        "the_d5_pool_is_not_the_spent_one": (
            build_d5_retrieval_pool().content_hash != bundle.seal.spent_retrieval_pool_hash
        ),
    }


# --------------------------------------------------------------- S21D5-044: execute and project


async def _complete_sources(
    prepared: Any, repair: Any, *, artifacts: ArtifactService
) -> tuple[str, str, dict[str, Any]]:
    """The two module texts behind this pair, re-read from the store rather than from memory.

    The spec table holds both bodies, and using it would be one line shorter and worth less: it
    would tie the searchable terms to what the corpus *says* rather than to what ran. The patch
    is fetched by its recorded artifact id, checked against the hash the candidate declares, and
    applied to the file the sandbox actually executed.
    """
    patch_bytes = await artifacts.get_bytes(repair.step.candidate.patch_artifact_id)
    if _digest(patch_bytes) != repair.step.candidate.patch_hash:
        raise SystemExit("the stored patch does not hash to what the candidate declares")
    patches = parse_unified_diff(patch_bytes.decode())
    if len(patches) != 1:
        raise SystemExit(f"a retrieval repair must touch one file, not {len(patches)}")
    target = prepared.generated.workspace / patches[0].path
    failed_source = target.read_text()
    repaired = apply_file_patch(failed_source.encode(), patches[0])
    if repaired is None:
        raise SystemExit("the stored patch does not apply to the executed workspace")
    return (
        failed_source,
        repaired.decode(),
        {
            "patch_artifact_id": str(repair.step.candidate.patch_artifact_id),
            "patch_hash": repair.step.candidate.patch_hash,
            "patch_rehashed_from_the_store": True,
            "target": patches[0].path,
            "applied_to_the_executed_workspace": True,
        },
    )


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
    # W3-F2, inherited from D3: `search_text()` puts the task signature in front of every arm,
    # so a signature that spells its own task family hands the relevance judgement to the
    # ranker. The signature is the reality task id -- an opaque uuid5 over template and seed.
    signature = str(prepared.generated.manifest.task_id)
    failed_source, repaired_source, resolution = await _complete_sources(
        prepared, repair, artifacts=artifacts
    )
    failed, successful = project_correction(
        assessments,
        domain="coding",
        group=spec.repository_group,
        task_signature=signature,
        source_manifest_hash=result.manifest.content_hash,
        limits=GRAPH_RESOURCE_POLICY_REVISION_2,
        failed_source=failed_source,
        repaired_source=repaired_source,
        judgement_labels=_labels(spec),
        structure_fallback=True,
    )
    # The same two graphs without the flag, in memory and never stored. It is what makes "the
    # complete surface reached this side" a difference rather than an assertion.
    released_failed, released_successful = project_correction(
        assessments,
        domain="coding",
        group=spec.repository_group,
        task_signature=signature,
        source_manifest_hash=result.manifest.content_hash,
        limits=GRAPH_RESOURCE_POLICY_REVISION_2,
        failed_source=failed_source,
        repaired_source=repaired_source,
        judgement_labels=_labels(spec),
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
        "complete_surface": {
            **resolution,
            "failed_terms": len(failed.search_terms),
            "successful_terms": len(successful.search_terms),
            "failed_terms_under_the_released_extraction": len(released_failed.search_terms),
            "successful_terms_under_the_released_extraction": len(released_successful.search_terms),
            "failed_needed_the_fallback": (
                not released_failed.search_terms and bool(failed.search_terms)
            ),
            "successful_needed_the_fallback": (
                not released_successful.search_terms and bool(successful.search_terms)
            ),
            "terms_differ_between_the_two_sides": (failed.search_terms != successful.search_terms),
            "structural_hash_is_the_same_with_and_without_the_flag": (
                failed.structural_hash == released_failed.structural_hash
                and successful.structural_hash == released_successful.structural_hash
            ),
        },
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
    """Read each stored source back and compare its bytes to the hash the pair declares."""
    for artifact_id, expected in references:
        try:
            payload = await artifacts.get_bytes(artifact_id)
        except Exception:  # every store failure is the same failure here
            return False
        if _digest(payload) != expected:
            return False
    return True


def _store_pairs(pairs: list[FailedSuccessGraphPair], *, artifact_root: Path) -> dict[str, Any]:
    """Write each pair as a content-addressed blob and declare it in one root manifest."""
    children = []
    for pair in pairs:
        raw = pair.model_dump_json().encode()
        digest = _digest(raw)
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
        "graph_set_id": "sprint-21d5-retrieval-holdout",
        "pair_count": len(children),
        "children": sorted(children, key=lambda item: item["pair_id"]),
    }


def _seeded_refusals(artifact_root: Path) -> dict[str, Any]:
    """Damage this pair set on purpose and check the released store refuses it. §S21D5-044.

    All three seeds are read-only against the real store: two rewrite a *copy* of the root
    manifest, and the third builds a one-blob temporary store with tampered bytes. The real
    root and the real blobs are never written.
    """
    root = json.loads(GRAPH_ROOT.read_text())
    victim = root["children"][0]["pair_id"]
    results: dict[str, Any] = {"victim_pair": victim}
    with tempfile.TemporaryDirectory(prefix="cogos-d5-seed-") as scratch:
        seeded = Path(scratch)

        missing = json.loads(GRAPH_ROOT.read_text())
        missing["children"][0]["content_hash"] = "0" * 64
        (path := seeded / "missing.json").write_text(json.dumps(missing))
        results["missing_bytes_refused"] = load_evidence(path, artifact_root).missing_bytes == (
            victim,
        )

        broken = json.loads(GRAPH_ROOT.read_text())
        broken["children"][0]["successful_structural"] = "1" * 64
        (path := seeded / "broken.json").write_text(json.dumps(broken))
        results["broken_link_refused"] = load_evidence(path, artifact_root).broken_links == (
            victim,
        )

        store = seeded / "store"
        digest = root["children"][0]["content_hash"]
        blob = blob_path(store, digest)
        blob.parent.mkdir(parents=True, exist_ok=True)
        blob.write_bytes(blob_path(artifact_root, digest).read_bytes() + b" ")
        (path := seeded / "corrupt.json").write_text(
            json.dumps({**root, "pair_count": 1, "children": root["children"][:1]})
        )
        results["corrupt_bytes_refused"] = load_evidence(path, store).corrupt_bytes == (victim,)

    results["all_three_refused"] = all(
        value for key, value in results.items() if key.endswith("_refused")
    )
    return results


def _predecessors_untouched(before: dict[str, str]) -> dict[str, Any]:
    """The predecessor stores this wave reads, by fingerprint, before and after."""
    after = {name: fingerprint(path) for name, path in PREDECESSOR_STORES.items()}
    return {
        "fingerprints_before": before,
        "fingerprints_after": after,
        "unchanged": before == after,
        "writes": 0 if before == after else -1,
    }


# --------------------------------------------------------------- S21D5-043: queries


def _judgement_leaks(
    pairs: list[FailedSuccessGraphPair], specs: dict[str, D3RetrievalSpec]
) -> list[str]:
    """Every ranked text of this holdout, against the labels it is judged by.

    Now over the *complete* text: the projection already refused a leaking term list per graph,
    and this is the second reading, over the whole document each arm sees. The fallback puts
    node-type terms in front of a ranker that never saw them in D4, which is exactly why this
    reading is taken again rather than inherited. Fail-closed rather than reported.
    """
    searchable = {
        f"{pair.pair_id}:{side}": graph.search_text()
        for pair in pairs
        for side, graph in (("failed", pair.failed), ("successful", pair.successful))
    }
    labels = {key: _labels(specs[key.split(":")[0]]) for key in searchable}
    return list(judgement_leaks(searchable, labels))


def _queries(pairs: list[FailedSuccessGraphPair], specs: dict[str, D3RetrievalSpec]) -> list[dict]:
    """One query per pair, judged by task family, frozen before any arm exists."""
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
                "query_hash": _digest(pair.failed.search_text()),
            }
        )
    return records


def _discriminability(pairs: list[FailedSuccessGraphPair]) -> dict[str, Any]:
    """How much of the searchable text actually differs between two candidates.

    The comparable number. D3 measured 1 distinct document over sixty candidates; D4 measured
    41 of 60 under the widened surface with the fallback off. This is the same measurement,
    taken the same way, on this pool under the complete surface.
    """
    texts = [pair.successful.search_text() for pair in pairs]
    without_signature = ["\n".join(text.splitlines()[2:]) for text in texts]
    termless = [pair.pair_id for pair in pairs if not pair.successful.search_terms]
    return {
        "candidates": len(texts),
        "distinct_searchable_texts": len(set(texts)),
        "distinct_after_removing_domain_and_signature": len(set(without_signature)),
        "candidates_with_no_terms": termless,
        "d3_measured": 1,
        "d4_measured": 41,
        "note": (
            "D3's 1 and D4's 41 are context, not a controlled comparison: three different "
            "pools, three different sets of bodies, and the fallback only on here. What is "
            "comparable is the measurement, which is taken identically in all three."
        ),
    }


def _chance_baseline(records: list[dict], pool: int) -> dict[str, float]:
    """What a uniformly random ranking would score, so a floor can be read in context."""
    recall, reciprocal = [], []
    for record in records:
        eligible = pool - len(record["excluded_groups"])
        relevant = len(record["relevant_pair_ids"])
        miss = comb(eligible - relevant, 5) / comb(eligible, 5) if eligible - relevant >= 5 else 0
        recall.append(1 - miss)
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
    }


# --------------------------------------------------------------- stages


async def _resolve(group_limit: int | None) -> int:
    """S21D5-043 and -044: execute, project, store, verify, and freeze the queries."""
    _, artifact_root = _isolated()
    separation = _separation()
    for key in (
        "retrieval_crossing_a_correction_role",
        "task_signatures_reused_from_a_predecessor",
        "query_ids_reused_from_a_predecessor",
        "cross_group_near_clones",
    ):
        if separation[key]:
            raise SystemExit(f"refusing to resolve a holdout that fails separation: {key}")
    if not separation["the_d5_pool_is_not_the_spent_one"]:
        raise SystemExit("the D5 retrieval pool hashes to the spent D4 one")

    before = {name: fingerprint(path) for name, path in PREDECESSOR_STORES.items()}
    engine = create_postgres_engine(_require("COGOS_DATABASE_URL"))
    specs = {spec.repository_group: spec for spec in D5_RETRIEVAL_SPECS}
    selected = list(D5_RETRIEVAL_SPECS)[: group_limit or len(D5_RETRIEVAL_SPECS)]
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
            verifier_profile_hash=D5_VERIFIER_PROFILE_HASH,
            campaign_version=D5_CAMPAIGN_VERSION,
        )
        with tempfile.TemporaryDirectory(prefix="cogos-d5-retrieval-") as scratch:
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
    GRAPH_ROOT.write_bytes(_canonical(root) + b"\n")
    evidence = load_evidence(GRAPH_ROOT, artifact_root)
    if not evidence.intact:
        raise SystemExit(f"the projected pair set does not resolve: {evidence.missing_bytes}")

    leaks = _judgement_leaks(pairs, specs)
    if leaks:
        raise SystemExit(f"refusing to rank text that names its own judgement: {leaks[:5]}")

    records = _queries(pairs, specs)
    QUERY_MANIFEST.write_bytes(_canonical(records) + b"\n")
    if len(records) < MINIMUM_QUERIES:
        raise SystemExit(f"{len(records)} queries qualify; the floor is {MINIMUM_QUERIES}")

    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    common = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W3",
        "recorded_at": recorded_at,
        "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
        "contracts_sha256": _digest(CONTRACTS.read_bytes()),
        "final_or_canary_outcomes_inspected": 0,
        "final_outcomes_inspected": False,
    }
    projection_seal = _write(
        PROJECTION_RECORD,
        {
            **common,
            "items": ["S21D5-044"],
            "surface_sha256": _digest(SURFACE.read_bytes()),
            "separation_record_sha256": _digest(SEPARATION_RECORD.read_bytes()),
            "separation": separation,
            "execution": {
                "groups_requested": len(selected),
                "groups_executed": len(pairs),
                "executed_not_declared": True,
                "campaign_version": D5_CAMPAIGN_VERSION,
                "verifier_profile_hash": D5_VERIFIER_PROFILE_HASH,
                "sandbox_image": SANDBOX_IMAGE,
                "seed": RETRIEVAL_SEED,
                "baselines_that_failed_their_hidden_suite": sum(
                    1 for row in projections if not row["baseline_hidden_passed"]
                ),
                "repairs_that_passed_their_hidden_suite": sum(
                    1 for row in projections if row["repair_hidden_passed"]
                ),
            },
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
                "seeded_refusals": _seeded_refusals(artifact_root),
                "per_pair": projections,
            },
            "complete_surface": {
                "structure_fallback": True,
                "graphs": len(pairs) * 2,
                "graphs_carrying_terms": sum(
                    1
                    for pair in pairs
                    for graph in (pair.failed, pair.successful)
                    if graph.search_terms
                ),
                "sides_that_needed_the_fallback": sum(
                    int(row["complete_surface"]["failed_needed_the_fallback"])
                    + int(row["complete_surface"]["successful_needed_the_fallback"])
                    for row in projections
                ),
                "pairs_whose_two_sides_differ_in_terms": sum(
                    1
                    for row in projections
                    if row["complete_surface"]["terms_differ_between_the_two_sides"]
                ),
                "terms_resolved_from_the_store": all(
                    row["complete_surface"]["patch_rehashed_from_the_store"] for row in projections
                ),
                "structural_hash_unmoved_by_the_flag": all(
                    row["complete_surface"]["structural_hash_is_the_same_with_and_without_the_flag"]
                    for row in projections
                ),
                "why_both_projections": (
                    "each pair is projected twice in memory, with the flag and without it, and "
                    "only the complete one is stored. Without the second projection 'the "
                    "fallback reached this side' would be an assertion about a number with "
                    "nothing to compare it to"
                ),
                "discriminability": _discriminability(pairs),
            },
            "graph_set": {
                "root": str(GRAPH_ROOT.relative_to(REPOSITORY)),
                "root_sha256": _digest(GRAPH_ROOT.read_bytes()),
                "graph_set_id": evidence.graph_set_id,
                "declared_pairs": evidence.declared_pairs,
                "resolved_pairs": len(evidence.pairs),
                "intact": evidence.intact,
                "artifact_root": str(artifact_root),
            },
            "predecessor_stores": _predecessors_untouched(before),
        },
    )
    query_seal = _write(
        QUERY_SET_RECORD,
        {
            **common,
            "items": ["S21D5-043"],
            "path": str(QUERY_MANIFEST.relative_to(REPOSITORY)),
            "sha256": _digest(QUERY_MANIFEST.read_bytes()),
            "queries": len(records),
            "minimum_queries": MINIMUM_QUERIES,
            "minimum_queries_met": len(records) >= MINIMUM_QUERIES,
            "groups_executed": len(pairs),
            "by_domain": dict(Counter(record["domain"] for record in records)),
            "by_tier": dict(Counter(str(record["relevance_tier"]) for record in records)),
            "by_family": dict(Counter(record["relevance_family"] for record in records)),
            "relevance_rule": "Sprint 21D1 tier 1: same task family, own group always excluded",
            "every_query_excludes_its_own_group": all(
                record["excluded_groups"] == [record["query_id"].removeprefix("q:")]
                for record in records
            ),
            "frozen_before_any_arm_ran": True,
            "written_before_the_benchmark_subprocess_exists": True,
            "arms_can_read_judgements": False,
            "searchable_text_naming_its_own_judgement": leaks,
            "leak_guard_ran_over_the_complete_text": True,
            "seen_task_queries": 0,
            "chance_baseline": _chance_baseline(records, len(pairs)),
            "separation": separation,
            "projection_record_sha256": _digest(PROJECTION_RECORD.read_bytes()),
        },
    )

    print(f"\n{PROJECTION_RECORD.relative_to(REPOSITORY)}  seal {projection_seal}")
    print(f"{QUERY_SET_RECORD.name}  {query_seal}")
    print(f"  groups executed: {len(pairs)}  queries: {len(records)}")
    discriminability = _discriminability(pairs)
    print(
        "  distinct documents, domain and signature removed: "
        f"{discriminability['distinct_after_removing_domain_and_signature']} of {len(pairs)}"
        f"  (D3 measured 1, D4 measured 41)"
    )
    print(f"  predecessor store writes: {_predecessors_untouched(before)['writes']}")
    return 0


def _evaluate(model: Path) -> int:
    """S21D5-045: every frozen arm, exactly once, against queries already on disk."""
    _, artifact_root = _isolated()
    if not QUERY_MANIFEST.is_file():
        raise SystemExit("resolve the holdout before evaluating it")
    before = {name: fingerprint(path) for name, path in PREDECESSOR_STORES.items()}
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
            str(model.resolve()),
            "--policy-hash",
            GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
        ],
        capture_output=True,
        text=True,
        cwd=REPOSITORY,
        check=False,
    )
    if done.returncode != 0:
        raise SystemExit(f"graph-benchmark refused:\n{done.stderr}")
    payload = json.loads(done.stdout)

    seal = _write(
        HOLDOUT_RESULT,
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W3",
            "items": ["S21D5-045"],
            "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "query_set_sha256": _digest(QUERY_MANIFEST.read_bytes()),
            "graph_root_sha256": _digest(GRAPH_ROOT.read_bytes()),
            "projection_record_sha256": _digest(PROJECTION_RECORD.read_bytes()),
            "ged_decision_sha256": _digest(GED_DECISION.read_bytes()),
            "ged_iteration_budget": GED_ITERATION_BUDGET,
            "ged_budget_inherited_from": "S21D4-041; not re-decided in D5",
            "executions": 1,
            "reran_after_metrics_were_known": False,
            "benchmark": {
                "content_hash": payload["content_hash"],
                "schema_version": payload["schema_version"],
                "resource_policy": payload["resource_policy"],
                "model": payload["model"],
                "queries": payload["queries"],
                "repeated_ranking_agreement": payload["repeated_ranking_agreement"],
                "repeated_ranking_agreement_by_arm": payload["repeated_ranking_agreement_by_arm"],
                "command": (
                    "scripts/experience.py graph-benchmark --graph-root <root> --artifact-root "
                    "<store> --queries <manifest> --model <frozen-minilm> --policy-hash "
                    f"{GRAPH_RESOURCE_POLICY_REVISION_2_HASH}"
                ),
            },
            "chance_baseline": json.loads(QUERY_SET_RECORD.read_text())["chance_baseline"],
            "arms": {arm: payload["arms"][arm] for arm in ARM_ORDER},
            "per_query": payload["per_query"],
            "predecessor_stores": _predecessors_untouched(before),
            "final_or_canary_outcomes_inspected": 0,
            "final_outcomes_inspected": False,
        },
    )
    print(f"{HOLDOUT_RESULT.relative_to(REPOSITORY)}")
    for arm in ARM_ORDER:
        row = payload["arms"][arm]
        print(
            f"  {arm:<34} recall@5={row['top_5_recall']:.4f} mrr@10={row['mrr_at_10']:.4f} "
            f"ndcg@10={row['ndcg_at_10']:.4f} p95={row['p95_latency_ms']:.1f}ms"
        )
    print(f"  seal {seal}")
    return 0


def _decide() -> int:
    """S21D5-046: the frozen floors, applied in the frozen order, to sealed numbers.

    A separate record rather than a field appended to the result: the result is sealed, and
    this decision reads it by hash. First-failure precedence, so a pass needs one arm to clear
    *both* floors; an arm that clears recall and misses MRR is a recorded near miss.
    """
    result = json.loads(HOLDOUT_RESULT.read_text())
    payload_arms = result["arms"]
    policy = result["benchmark"]["resource_policy"]
    agreement = result["benchmark"]["repeated_ranking_agreement_by_arm"]
    queries = result["benchmark"]["queries"]
    recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    trace, winner = [], None
    for arm in ARM_ORDER:
        metrics = payload_arms[arm]
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
                and metrics["max_latency_ms"] <= policy["query_budget_seconds"] * 1000,
                "reproducible": agreement[arm],
            }
        )
        if winner is None and recall_ok and mrr_ok and trace[-1]["within_budgets"]:
            winner = arm
    enough = queries >= MINIMUM_QUERIES
    passed = winner is not None and enough
    stop_hash = (
        None if passed else _digest(_canonical({"trace": trace, "at": recorded_at}).decode())
    )
    seal = _write(
        DECISION_RECORD,
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W3",
            "items": ["S21D5-046"],
            "recorded_at": recorded_at,
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "holdout_result_sha256": _digest(HOLDOUT_RESULT.read_bytes()),
            "immutable": True,
            "rule": (
                f"one arm reaches Recall@5 >= {RECALL_AT_5_FLOOR} and MRR@10 >= "
                f"{MRR_AT_10_FLOOR} on at least {MINIMUM_QUERIES} unseen-task queries, inside "
                "all fixed budgets"
            ),
            "queries": queries,
            "minimum_queries_met": enough,
            "chance_baseline": result["chance_baseline"],
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
            "d4_decided_this_as_a_near_miss": {
                "record": "sprint-21d4-retrieval-decision.json",
                "reading": (
                    "D4's fusion arm cleared the recall floor and missed MRR by 0.0089. That "
                    "decision is not reopened and is not evidence about this pool: a different "
                    "corpus, a complete surface, and a holdout read once"
                ),
            },
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
                    "content_hash": _digest(f"{item}:{stop_hash}"),
                }
                for item in (() if passed else DEPENDENT_ON_A_RETRIEVAL_STOP)
            ],
            "dependants_already_bound_to_an_earlier_stop": ("" if passed else EARLIER_STOP),
            "s21d5_047_runs_on_every_outcome": True,
            "final_or_canary_outcomes_inspected": 0,
            "final_outcomes_inspected": False,
        },
    )
    print(f"{DECISION_RECORD.relative_to(REPOSITORY)}")
    for row in trace:
        print(
            f"  {row['arm']:<34} recall@5={row['recall_at_5']:.4f} "
            f"mrr@10={row['mrr_at_10']:.4f} failed={row['first_failed_floor'] or 'none'}"
        )
    print(f"  winner={winner} passed={passed}")
    print(f"  gate D1 condition 15: {'closed' if passed else 'remains_open'}")
    print(f"  seal {seal}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("resolve", "evaluate", "decide"), required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--groups", type=int, help="run fewer groups; for a smoke run only")
    arguments = parser.parse_args()

    if arguments.stage == "resolve":
        return asyncio.run(_resolve(arguments.groups))
    if arguments.stage == "evaluate":
        if arguments.model is None:
            parser.error("--model is required for --stage evaluate")
        return _evaluate(arguments.model)
    if arguments.stage == "decide":
        return _decide()
    raise AssertionError(arguments.stage)


if __name__ == "__main__":
    raise SystemExit(main())
