"""S22B-003. The Sprint 22B measurement drivers, and the recipes they are frozen to.

§1.3 of the backlog lists what 22B must build, and constrains it hard: "None of these changes
a released behaviour; each is a driver over what is already there, and any gap that turns out
to need more than composition is a finding to surface, not to absorb silently." This module is
that list, in one file, because seven scripts that share a corpus, a probe protocol and a host
record are one script wearing seven hats.

**What is reused rather than rebuilt.** The corpus geometry, the bulk load, the HNSW build and
the exact/approximate envelope come from `scripts/memory_ann_baseline.py` — the same harness
that sealed the 10^5 envelope on 2026-07-25. That is not only laziness: a 10^6 number is
comparable to the 10^5 number *only* if the same generator drew both, so re-implementing the
geometry would quietly destroy the one comparison this sprint has. Its `_vector_literal` and
`_clustered_literal` are imported here, never copied. The restore round trip reuses
`scripts/restore_event_store.sh` and `scripts/artifact_restore_verify.py`. The fusion under the
hybrid recipe is the released Context Plane's `rank_candidates`, not a second RRF.

**What is genuinely new**, because nothing released does it: a governed-ingest throughput
runner, the metadata-carrying corpus table the filtered shapes need, the warm/cold probe
protocol of §2.2b, the mutation and reindex drivers, and the restore checklist that *queries*.

**Three gaps found while composing, and surfaced rather than absorbed** — see W0-F2, W0-F3 and
W0-D1 in the execution log. In short: `MemoryMetadataFilter.include_historical` is a released
field that no released code reads, so the temporal shape cannot be a `MemoryQuery`; the released
`MemoryQuery` forbids text and vector in one query, so hybrid is two queries and a released
fusion; and the filtered-ANN exit reads a predicate whose selectivity nobody had frozen, so W0
freezes it here before a number exists.

    UV_CACHE_DIR=.cache/uv uv run python scripts/scale_22b.py --slice --items 200
    UV_CACHE_DIR=.cache/uv uv run python scripts/scale_22b.py --recipes

`--recipes` is read-only and needs no database. `--slice` writes to the 22B store only.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import random
import shutil
import statistics
import subprocess
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from itertools import islice
from pathlib import Path
from tempfile import mkdtemp as _mkdtemp
from time import perf_counter
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import text

from cognitive_os.application.services.memory_service import MemoryService
from cognitive_os.domain.experience_graph import GraphResourceLimits
from cognitive_os.domain.memory import (
    MemoryCreator,
    MemoryCreatorType,
    MemoryMetadataFilter,
    MemoryProvenanceBundle,
    MemoryQuery,
    MemoryRetrievalMode,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemorySourceIdentity,
    MemorySourceRef,
    MemorySourceType,
    MemoryStatus,
    MemoryTextQuery,
    MemoryType,
    MemoryVectorQuery,
    MemoryWritePolicy,
    MemoryWriteRequest,
    ObservationMemoryContent,
)
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.memory_event_service import MemoryEventService
from cognitive_os.infrastructure.memory.postgres.repository import PostgresMemoryRepository
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.memory.embeddings import MemoryEmbeddingService
from cognitive_os.memory.retrieval import MemoryRetrievalService

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")

#: 22B's own corpus table. Named after the released harness's scratch table and kept separate
#: from it, so a 22B run can never be mistaken for — or overwrite — a baseline run.
CORPUS_TABLE = "memory_scale_22b_corpus"


def corpus_table(dataset: str) -> str:
    """One table per dataset.

    W1-F3: a single shared table meant the second 10^6 corpus dropped the first. W2 measures
    500 probes per mode *per dataset*, so both have to exist at once; rebuilding the other
    corpus between waves would cost a second multi-hour HNSW build and would silently make the
    two envelopes measurements of different machine states.
    """
    return f"{CORPUS_TABLE}_{dataset}"


def _released_generators() -> tuple[Callable[..., str], Callable[..., str]]:
    """The 10^5 envelope's own generators, imported rather than copied.

    D4 W7-A1: never a second implementation of something released. Here the stake is higher
    than tidiness — a 10^6 recall number is only comparable to the sealed 10^5 one if the same
    function drew both corpora.
    """
    path = REPO / "scripts/memory_ann_baseline.py"
    spec = importlib.util.spec_from_file_location("memory_ann_baseline_22b", path)
    if spec is None or spec.loader is None:
        raise SystemExit("the released ANN baseline harness could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._vector_literal, module._clustered_literal


# --------------------------------------------------------------------------------------
# The frozen recipes. Everything below this line is a choice that could bend after a number
# exists, so W0 fixes it and the pre-registration binds this module's bytes.
# --------------------------------------------------------------------------------------

#: §2.2a. Two datasets, both drawn by the released generators, both reproducible from a seed.
#: The clustered one is where the recall floor is met or missed; the uniform one is the
#: adversarial bound, measured in full and read by no exit criterion.
DATASETS: dict[str, dict[str, Any]] = {
    "clustered": {
        "generator": "scripts/memory_ann_baseline.py::_clustered_literal",
        "corpus_seed": 20_250_321,
        "probe_seed": 777,
        "dimension": 768,
        "clusters": 64,
        "cluster_spread": 0.35,
        "reads_the_recall_exit": True,
        "why": (
            "the geometry real embeddings have. The sealed 10^5 run reached recall 0.992 here; "
            "whether that survives 10x the corpus is the sprint's question"
        ),
    },
    "uniform": {
        "generator": "scripts/memory_ann_baseline.py::_vector_literal",
        "corpus_seed": 20_250_321,
        "probe_seed": 777,
        "dimension": 768,
        "clusters": 0,
        "cluster_spread": 0.35,
        "reads_the_recall_exit": False,
        "why": (
            "independent gaussians in 768 dimensions have no neighbourhood structure, so ANN "
            "recall collapses on them by construction: 0.496 at 10^5 is a property of the "
            "geometry, not of the index. Reported in full, read by nothing"
        ),
    },
}

#: §2.2b. Warm is a protocol, not an adjective.
PROBE_PROTOCOL = {
    "warm_definition": (
        "index built, PostgreSQL restarted, then 100 discarded warmup probes, then the "
        "measured probes"
    ),
    "cold_definition": "the first probe after the restart, before any warmup probe",
    "warmup_probes": 100,
    "measured_probes": 500,
    "why_500": (
        "the 10^5 envelope measured 50, and a p95 over 50 probes is decided by its three worst "
        "readings. 500 makes the 95th percentile a measurement rather than an anecdote"
    ),
    "restart_is_a_real_restart": (
        "the database process is restarted, not a cache hint issued. D7 lifecycle: separate "
        "processes or it proved nothing"
    ),
}

#: §2.2d. The bounded graph-assisted configuration, pre-registered rather than searched.
#: Every field is a released `GraphResourceLimits` field; nothing here is a new knob.
BOUNDED_GRAPH_LIMITS = GraphResourceLimits(
    vector_shortlist=20,
    per_pair_ged_timeout_ms=250,
    path_depth=8,
    returned_results=10,
    query_budget_seconds=2,
    nodes_per_graph=64,
    edges_per_graph=128,
    cross_task_similarity_neighbors=3,
)

BOUNDED_GRAPH_READING = {
    "shape": "ANN shortlist first, budgeted graph expansion second",
    "exit_ms": 500,
    "only_prior_measurement_ms": 1788.9,
    "prior_measurement_source": "sprint-21d1-w5a-retrieval.json, arm "
    "minilm_shortlist_plus_bounded_ged",
    "tighter_by": "3.6x, at 10x the scale",
    "may_be_tuned_after_a_number_exists": False,
    "the_cutoff_trap": (
        "D1 reached 1788.9 ms with 60 queries cut off at its 2 s budget. A budget cutoff "
        "returns a short list fast, so a recipe that cuts off more looks quicker while "
        "answering less. Every 22B graph record reports its cutoff count beside its p95, and a "
        "p95 met with a rising cutoff count is a miss reported as one"
    ),
}

#: The predicate the 300 ms filtered-ANN exit reads. W0-D1: the plan froze five readings and
#: this was a sixth — a metadata predicate has a selectivity, and choosing it after the numbers
#: exist would let the exit be met by filtering to a friendlier slice. Frozen here.
FILTER_PREDICATE = {
    "predicate": "scope_id = :scope AND status = ANY(:statuses) AND memory_type = :type",
    "target_selectivity": 0.10,
    "scopes_in_corpus": 10,
    "statuses": [MemoryStatus.CANDIDATE.value, MemoryStatus.VERIFIED.value],
    "memory_type": MemoryType.EPISODE.value,
    "applied_as": "a pre-filter in the same statement as the ANN order-by, one query",
    "why_frozen": (
        "a filtered-ANN latency is a function of how much the filter removes. Ten scopes, one "
        "selected, is a tenth of the corpus and is fixed before any probe runs. §2.3's last "
        "bullet forbids tuning a pre-registered configuration once a number exists, and a "
        "selectivity is a configuration"
    ),
}

#: The released retrieval modes the drivers exercise but W2's envelope does not count as one
#: of its seven shapes. They are not hidden: `stale_item` is a metadata query and `hybrid`'s
#: first leg is a text query, so both modes are driven — they are simply not separate rows in
#: the envelope W2 reports.
SUPPORTING_MODES: dict[str, dict[str, Any]] = {
    "metadata": {
        "mode": MemoryRetrievalMode.METADATA.value,
        "composition": "released MemoryQuery through MemoryRetrievalService",
        "used_by": ["stale_item"],
    },
    "text": {
        "mode": MemoryRetrievalMode.TEXT.value,
        "composition": "released MemoryQuery through MemoryRetrievalService",
        "used_by": ["hybrid"],
    },
}

#: The seven shapes W2 drives, and how each is composed. `composition` is the honest column:
#: it says what released thing answers the shape, or names the gap.
#:
#: W0-F8: this list had eight entries and was missing the bounded graph-assisted shape — it
#: counted `metadata` and `text` as envelope shapes and left out the one the sprint's hardest
#: exit reads. W2's row names seven, and the pre-registration's own enumeration check is what
#: caught it: exactly 22A W4-F1, a coverage word that had not been counted.
QUERY_SHAPES: dict[str, dict[str, Any]] = {
    "exact_vector": {
        "mode": MemoryRetrievalMode.VECTOR.value,
        "composition": "released harness's exhaustive scan; also the recall ground truth",
        "reads_an_exit": False,
    },
    "ann": {
        "mode": MemoryRetrievalMode.VECTOR_APPROXIMATE.value,
        "composition": "released harness's approximate scan with the plan read back",
        "reads_an_exit": "recall@10 >= 0.95, clustered dataset only",
    },
    "filtered_ann": {
        "mode": MemoryRetrievalMode.VECTOR_APPROXIMATE.value,
        "composition": "the frozen FILTER_PREDICATE and the ANN order-by in one statement",
        "reads_an_exit": "warm p95 <= 300 ms",
    },
    "hybrid": {
        "mode": "text + vector_approximate, fused",
        "composition": (
            "two released MemoryQuery executions fused by the released Context Plane's "
            "rank_candidates. W0-F3: MemoryQuery.exactly_one_mode_payload refuses text and "
            "vector in one query, so hybrid is two queries by construction, not by choice"
        ),
        "reads_an_exit": False,
    },
    "temporal": {
        "mode": "active view as of a moment",
        "composition": (
            "raw SQL over the released memory_revisions.created_at. W0-F2: this is the one "
            "shape that is NOT expressible as a MemoryQuery — the released filter has no "
            "as-of predicate, and its include_historical field is read by no released code. "
            "The recipe therefore bypasses the governed retrieval path and its access audit, "
            "and every temporal record carries that as a sealed limitation"
        ),
        "reads_an_exit": False,
    },
    "stale_item": {
        "mode": MemoryRetrievalMode.METADATA.value,
        "composition": (
            "released MemoryQuery with statuses=(superseded, retracted, expired) — the one "
            "history-adjacent shape the released filter does answer"
        ),
        "reads_an_exit": False,
    },
    "bounded_graph_assisted": {
        "mode": "ann shortlist, then bounded graph edit distance",
        "composition": (
            "the released EMG arm under the frozen §2.2d GraphResourceLimits: shortlist 20, "
            "per-pair budget 250 ms, walk depth capped, whole-query budget bounded"
        ),
        "reads_an_exit": "p95 <= 500 ms — the sprint's hardest number",
    },
}

#: §2.2e. What a restore must reproduce, as a checklist a machine can fail.
RESTORE_CHECKLIST = (
    "exact row counts per table",
    "content hashes of the artifact store",
    "the active view after supersessions and tombstones, queried rather than counted",
    "the live learned artifact pointer resolved and its bytes loaded",
)

#: The one live learned artifact a restore must resolve and load. D7 W3-F1: a digest proves
#: bytes, not usability.
LIVE_LEARNED_ARTIFACT = {
    "surface": "experience.correction_ranking",
    "component": "learned.containment.correction_ranking",
    "artifact_hash": "afbdb7c05c73aec8b1a46dd9b20cd8f2f8915819b29a1ea3b364ad8acbb48edb",
    "verified_by": "resolving the pointer in the restored store and loading the bytes",
}

#: Where W1 copies the live learned artifact's bytes from (W1-D1). Deliberately **not** part
#: of RECIPES: §2.2e freezes what a restore must reproduce, not which store the bytes were
#: first registered in, and widening a frozen contract to carry an operational detail would
#: move the recipes hash for no reading at all.
LIVE_LEARNED_ARTIFACT_SOURCE = {
    "path": (
        "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7-measured/sha256/af/"
        "afbdb7c05c73aec8b1a46dd9b20cd8f2f8915819b29a1ea3b364ad8acbb48edb"
    ),
    "store": "cognitive_os_s21d7_measured",
}

RECIPES: dict[str, Any] = {
    "datasets": DATASETS,
    "probe_protocol": PROBE_PROTOCOL,
    "bounded_graph_limits": json.loads(BOUNDED_GRAPH_LIMITS.model_dump_json()),
    "bounded_graph_reading": BOUNDED_GRAPH_READING,
    "filter_predicate": FILTER_PREDICATE,
    "query_shapes": QUERY_SHAPES,
    "supporting_modes": SUPPORTING_MODES,
    "restore_checklist": list(RESTORE_CHECKLIST),
    "live_learned_artifact": LIVE_LEARNED_ARTIFACT,
    "corpus_table": CORPUS_TABLE,
}


def recipes_hash() -> str:
    """The frozen recipes as one hash, so the pre-registration binds behaviour not prose."""
    return hashlib.sha256(
        json.dumps(RECIPES, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


# --------------------------------------------------------------------------------------
# Corpus: the metadata-carrying table the filtered shapes need.
# --------------------------------------------------------------------------------------


def corpus_stream(dataset: str) -> Iterator[tuple[str, str, str, str]]:
    """The corpus, drawn once, in order, for as long as the caller keeps pulling.

    This is *the* definition of the draw order. `corpus_rows` addresses into it and
    `create_corpus` streams it, so there is one implementation of what row `i` is and no way
    for a batch loader and a test to disagree about the corpus.

    W1-F1: the previous shape re-seeded and re-drew `offset` rows on every call, which made a
    batched load quadratic. Measured at 0.33 ms per drawn row, a 10^6 load in batches of 1000
    would have drawn 5.0e8 rows — **about 46 hours per dataset** — against roughly six minutes
    streamed. The rows are unchanged: a single `random.Random` consumed sequentially yields
    exactly the sequence the discard loop was reproducing, and a test asserts the two agree.
    """
    recipe = DATASETS[dataset]
    vector_literal, clustered_literal = _released_generators()
    dimension = int(recipe["dimension"])
    clusters = int(recipe["clusters"])
    spread = float(recipe["cluster_spread"])
    scopes = int(FILTER_PREDICATE["scopes_in_corpus"])

    rnd = random.Random(recipe["corpus_seed"])
    centres = [[rnd.gauss(0.0, 1.0) for _ in range(dimension)] for _ in range(clusters)]

    index = 0
    while True:
        literal = (
            clustered_literal(rnd, dimension, centres, spread)
            if centres
            else vector_literal(rnd, dimension)
        )
        # Metadata is derived from the row index rather than drawn, so the frozen selectivity
        # is a property of the recipe and not of a random seed.
        status = MemoryStatus.VERIFIED.value if index % 4 else MemoryStatus.SUPERSEDED.value
        yield literal, f"scope-{index % scopes:02d}", status, MemoryType.EPISODE.value
        index += 1


def corpus_rows(dataset: str, count: int, *, offset: int = 0) -> list[tuple[str, str, str, str]]:
    """Rows `offset` through `offset + count` of the corpus, addressed into the stream."""
    return list(islice(corpus_stream(dataset), offset, offset + count))


def corpus_centres(dataset: str) -> list[list[float]]:
    """The cluster centres probes must reuse. A uniform probe against a clustered corpus
    lands in empty space, where nothing is a near neighbour."""
    recipe = DATASETS[dataset]
    rnd = random.Random(recipe["corpus_seed"])
    return [
        [rnd.gauss(0.0, 1.0) for _ in range(int(recipe["dimension"]))]
        for _ in range(int(recipe["clusters"]))
    ]


def probe_literals(dataset: str, count: int) -> list[str]:
    """Probes drawn from the corpus distribution, from the frozen probe seed."""
    recipe = DATASETS[dataset]
    vector_literal, clustered_literal = _released_generators()
    dimension = int(recipe["dimension"])
    centres = corpus_centres(dataset)
    rnd = random.Random(recipe["probe_seed"])
    return [
        clustered_literal(rnd, dimension, centres, float(recipe["cluster_spread"]))
        if centres
        else vector_literal(rnd, dimension)
        for _ in range(count)
    ]


async def create_corpus(engine: Any, dataset: str, count: int, *, batch: int = 1_000) -> dict:
    """Bulk engine load. §2.2c: measured and reported as engine capacity, read by no exit."""
    dimension = int(DATASETS[dataset]["dimension"])
    table = corpus_table(dataset)
    async with engine.begin() as connection:
        await connection.execute(text(f"DROP TABLE IF EXISTS cognitive_os.{table}"))
        await connection.execute(
            text(
                f"CREATE TABLE cognitive_os.{table} ("
                "row_id bigserial PRIMARY KEY, dimension int NOT NULL, "
                "scope_id text NOT NULL, status text NOT NULL, memory_type text NOT NULL, "
                "embedding vector NOT NULL)"
            )
        )
    started = perf_counter()
    loaded = 0
    stream = corpus_stream(dataset)
    while loaded < count:
        size = min(batch, count - loaded)
        values = ",".join(
            f"({dimension}, '{scope}', '{status}', '{kind}', '{literal}')"
            for literal, scope, status, kind in islice(stream, size)
        )
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    f"INSERT INTO cognitive_os.{table} "
                    f"(dimension, scope_id, status, memory_type, embedding) VALUES {values}"
                )
            )
        loaded += size
    elapsed = perf_counter() - started
    return {
        "dataset": dataset,
        "table": table,
        "rows": loaded,
        "dimension": dimension,
        "load_seconds": round(elapsed, 3),
        "rows_per_second": round(loaded / elapsed, 1) if elapsed else None,
        "reads_an_exit_criterion": False,
        "limitation": (
            "bulk engine load outside the governed write path: this is engine capacity, not "
            "governed ingestion throughput (§2.2c)"
        ),
    }


async def build_corpus_index(engine: Any, dataset: str) -> dict:
    dimension = int(DATASETS[dataset]["dimension"])
    table = corpus_table(dataset)
    name = f"{table}_hnsw_{dimension}"
    started = perf_counter()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                f"CREATE INDEX {name} ON cognitive_os.{table} "
                f"USING hnsw ((embedding::vector({dimension})) vector_cosine_ops) "
                f"WHERE dimension = {dimension}"
            )
        )
        await connection.execute(text(f"ANALYZE cognitive_os.{table}"))
    elapsed = perf_counter() - started
    async with engine.connect() as connection:
        size = int(
            await connection.scalar(
                text("SELECT pg_relation_size(CAST(:name AS regclass))"),
                {"name": f"cognitive_os.{name}"},
            )
            or 0
        )
    return {"index": name, "build_seconds": round(elapsed, 3), "size_bytes": size}


# --------------------------------------------------------------------------------------
# Probes: the shapes, and the warm/cold protocol of §2.2b.
# --------------------------------------------------------------------------------------


def _percentiles(values: Sequence[float]) -> dict[str, float]:
    ordered = sorted(values)
    if len(ordered) == 1:
        return {
            "p50_ms": round(ordered[0], 3),
            "p95_ms": round(ordered[0], 3),
            "max_ms": round(ordered[0], 3),
            "probes": 1,
        }
    return {
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(statistics.quantiles(ordered, n=20, method="inclusive")[18], 3),
        "max_ms": round(ordered[-1], 3),
        "probes": len(ordered),
    }


async def probe_corpus(
    engine: Any,
    dataset: str,
    *,
    shape: str,
    probes: int,
    warmup: int,
    result_limit: int = 10,
    candidate_limit: int = 1_000,
    ef_search: int = 1_000,
) -> dict:
    """Drive one vector shape over the corpus table, warm, with the cold probe kept.

    The caller restarts PostgreSQL before this runs; the first probe here is therefore the
    cold one and is reported separately from the warm distribution, never averaged into it.
    """
    recipe = DATASETS[dataset]
    dimension = int(recipe["dimension"])
    literals = probe_literals(dataset, warmup + probes + 1)
    ef_search = max(ef_search, candidate_limit)

    filtered = shape == "filtered_ann"
    exact = shape == "exact_vector"
    where = f"WHERE dimension = {dimension}"
    parameters: dict[str, Any] = {}
    if filtered:
        where += " AND scope_id = :scope AND status = ANY(:statuses) AND memory_type = :kind"
        parameters = {
            "scope": "scope-00",
            "statuses": list(FILTER_PREDICATE["statuses"]),
            "kind": FILTER_PREDICATE["memory_type"],
        }
    order = (
        "embedding <=> '{probe}'::vector"
        if exact
        else f"(embedding::vector({dimension})) <=> '{{probe}}'::vector"
    )

    latencies: list[float] = []
    cold_ms: float | None = None
    plan_confirmed: bool | None = None
    async with engine.connect() as connection:
        for index, literal in enumerate(literals):
            if not exact:
                await connection.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))
            statement = text(
                f"SELECT row_id FROM cognitive_os.{corpus_table(dataset)} {where} "
                f"ORDER BY {order.format(probe=literal)} LIMIT {candidate_limit}"
            )
            started = perf_counter()
            rows = tuple((await connection.execute(statement, parameters)).scalars())
            elapsed = (perf_counter() - started) * 1_000
            if index == 0:
                cold_ms = round(elapsed, 3)
                continue
            if index <= warmup:
                continue
            latencies.append(elapsed)
            if plan_confirmed is None and not exact:
                # Read the plan back rather than trust it. A cost-based planner declines the
                # index on a small corpus, and the recall then comes out at 1 because the query
                # was exhaustive — a clean number that says nothing about the index.
                plan = "\n".join(
                    (
                        await connection.execute(
                            text(f"EXPLAIN (COSTS OFF) {statement.text}"), parameters
                        )
                    ).scalars()
                )
                plan_confirmed = "Index Scan using" in plan and "hnsw" in plan.lower()
            del rows

    record = {
        "dataset": dataset,
        "shape": shape,
        "result_limit": result_limit,
        "candidate_limit": candidate_limit,
        "ef_search": None if exact else ef_search,
        "cold_first_probe_ms": cold_ms,
        "warmup_probes_discarded": warmup,
        "index_scan_confirmed": plan_confirmed,
        **_percentiles(latencies),
    }
    if plan_confirmed is False:
        record["limitation"] = (
            "the planner declined the index at this corpus size and scanned exhaustively, so "
            "these are not approximate-retrieval numbers"
        )
    return record


async def recall_at(
    engine: Any, dataset: str, *, probes: int, k: int = 10, ef_search: int = 1_000
) -> dict:
    """recall@k against an exact-scan ground truth, on the same probes.

    §4: the ground truth is an exact scan per probe and cannot be shortcut. A sampled ground
    truth would make the recall exit unfalsifiable in exactly the way this programme refuses.
    """
    dimension = int(DATASETS[dataset]["dimension"])
    literals = probe_literals(dataset, probes)
    overlaps: list[float] = []
    async with engine.connect() as connection:
        for literal in literals:
            truth = tuple(
                (
                    await connection.execute(
                        text(
                            f"SELECT row_id FROM cognitive_os.{corpus_table(dataset)} "
                            f"WHERE dimension = {dimension} "
                            f"ORDER BY embedding <=> '{literal}'::vector LIMIT {k}"
                        )
                    )
                ).scalars()
            )
            await connection.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))
            found = tuple(
                (
                    await connection.execute(
                        text(
                            f"SELECT row_id FROM cognitive_os.{corpus_table(dataset)} "
                            f"WHERE dimension = {dimension} "
                            f"ORDER BY (embedding::vector({dimension})) <=> '{literal}'::vector "
                            f"LIMIT {k}"
                        )
                    )
                ).scalars()
            )
            if truth:
                overlaps.append(len(set(found) & set(truth)) / len(truth))
    return {
        "dataset": dataset,
        "k": k,
        "probes": len(overlaps),
        "recall_at_k": round(sum(overlaps) / len(overlaps), 4) if overlaps else None,
        "ground_truth": "exact scan per probe, never sampled",
        "reads_the_recall_exit": bool(DATASETS[dataset]["reads_the_recall_exit"]),
    }


# --------------------------------------------------------------------------------------
# Governed ingest: the one exit whose path nobody has ever measured.
# --------------------------------------------------------------------------------------


def _write_request(index: int) -> MemoryWriteRequest:
    memory_id = uuid5(NAMESPACE_URL, f"sprint-22b-ingest:{index}")
    return MemoryWriteRequest(
        request_id=uuid5(NAMESPACE_URL, f"sprint-22b-ingest-request:{index}"),
        memory_id=memory_id,
        idempotency_key=hashlib.sha256(f"sprint-22b:{index}".encode()).hexdigest(),
        memory_type=MemoryType.OBSERVATION,
        scope=MemoryScope(
            scope_type=MemoryScopeType.PROJECT,
            scope_id=f"scope-{index % int(FILTER_PREDICATE['scopes_in_corpus']):02d}",
        ),
        title=f"Sprint 22B governed ingest item {index}",
        content=ObservationMemoryContent(
            observation=f"governed ingest probe item {index}",
            evidence_summary=(f"Sprint 22B measures the governed write path at item {index}."),
        ),
        confidence=0.5,
        salience=0.5,
        sensitivity=MemorySensitivity.INTERNAL,
        actor=MemoryCreator(
            creator_type=MemoryCreatorType.OPERATOR, creator_id="sprint-22b-ingest"
        ),
        provenance=MemoryProvenanceBundle(
            sources=(
                MemorySourceRef(
                    identity=MemorySourceIdentity(
                        source_type=MemorySourceType.TASK_RUN,
                        source_id=uuid5(NAMESPACE_URL, f"sprint-22b-ingest-run:{index}"),
                    ),
                    source_hash=hashlib.sha256(f"sprint-22b-source:{index}".encode()).hexdigest(),
                    relationship="measured_ingest",
                ),
            )
        ),
    )


async def governed_ingest(engine: Any, items: int, *, deciles: int = 10, start: int = 0) -> dict:
    """The >= 100 items/s exit, through the real governed path.

    Every item is a real memory record with provenance, an event and a revision — the path
    §2.2c names, not the bulk load. The rate is reported per decile so a fading rate is
    visible rather than averaged away.
    """
    repository = PostgresMemoryRepository(engine)
    service = MemoryService(
        repository,
        MemoryWritePolicy(
            allowed_types=frozenset(MemoryType),
            allowed_scopes=frozenset(MemoryScopeType),
            maximum_sensitivity=MemorySensitivity.INTERNAL,
        ),
        event_service=MemoryEventService(PostgresEventStore(engine, build_default_event_catalog())),
    )

    # W1: `start` exists because the memory ids are deterministic and the event store is
    # append-only. The fixture-scale runs already wrote items 0..39, and the measured run must
    # neither collide with them nor delete them — an evidence store that a wave may erase to
    # make its own measurement fit is not an evidence store.
    bucket = max(items // deciles, 1)
    rates: list[dict[str, Any]] = []
    started = perf_counter()
    bucket_started = started
    written = 0
    for index in range(start, start + items):
        await service.create(_write_request(index))
        written += 1
        if written % bucket == 0 or written == items:
            now = perf_counter()
            span = now - bucket_started
            rates.append(
                {
                    "decile": len(rates) + 1,
                    "items": bucket if written % bucket == 0 else written % bucket or bucket,
                    "seconds": round(span, 3),
                    "items_per_second": round((bucket if span else 0) / span, 2) if span else None,
                }
            )
            bucket_started = now
    total = perf_counter() - started
    per_second = round(written / total, 2) if total else None
    return {
        "path": "governed: MemoryService.create -> repository + provenance + event + revision",
        "first_item_index": start,
        "items": written,
        "seconds": round(total, 3),
        "items_per_second": per_second,
        "per_decile": rates,
        "reads_the_ingest_exit": True,
        "exit_threshold_items_per_second": 100,
        "slowest_decile_items_per_second": min(
            (item["items_per_second"] for item in rates if item["items_per_second"]), default=None
        ),
        "why_per_decile": (
            "a sustained rate that fades is a different result from a sustained rate that "
            "holds, and a single average hides which one happened"
        ),
    }


async def governed_embed(engine: Any, items: int, *, dimension: int = 64) -> dict:
    """Embed governed items, measured separately from the ingest rate.

    W0-F6: the hybrid recipe's vector leg returned nothing, because governed ingest writes a
    record, its provenance, its event and its revision — and no embedding. §2.2c names exactly
    that path for the >= 100 items/s exit, so the fix is *not* to fold embedding writes into
    the ingest loop, which would change what the exit reads after the reading was frozen.
    Embedding is its own measured step, reported beside the ingest rate and read by no exit.
    """
    from cognitive_os.infrastructure.embeddings import DeterministicEmbeddingProvider

    repository = PostgresMemoryRepository(engine)
    provider = DeterministicEmbeddingProvider(dimension=dimension)
    service = MemoryEmbeddingService(repository, {provider.identity.provider_id: provider})

    started = perf_counter()
    embedded = 0
    for index in range(items):
        memory_id = uuid5(NAMESPACE_URL, f"sprint-22b-ingest:{index}")
        current = await repository.get_current(memory_id)
        if current is None:
            continue
        _, revision = current
        await service.create(
            memory_id, revision.revision, revision.content_hash, provider.identity.provider_id
        )
        embedded += 1
    elapsed = perf_counter() - started
    return {
        "embedded": embedded,
        "dimension": dimension,
        "provider_id": provider.identity.provider_id,
        "model_id": provider.identity.model_id,
        "seconds": round(elapsed, 3),
        "items_per_second": round(embedded / elapsed, 2) if elapsed else None,
        "reads_an_exit_criterion": False,
        "why_separate": (
            "§2.2c froze the ingest exit as the governed record path. Folding an embedding "
            "write into that loop would change what the frozen reading measures"
        ),
    }


# --------------------------------------------------------------------------------------
# The governed query shapes: metadata, text, stale, hybrid — and the temporal gap.
# --------------------------------------------------------------------------------------


def run_token() -> str:
    """A fresh token per driver invocation, so query ids do not collide across runs.

    W0-F4: these query ids were `uuid5` of the shape name alone, which made them stable across
    invocations — and `MemoryRetrievalService` derives each access record's primary key from
    the query id, the memory id, the revision and the rank. The second run of any shape
    therefore hit a duplicate key and the service failed closed on its own audit. Found by
    running the driver twice, which is what 22A W4-F3 says to do before trusting one. The
    probe *vectors* stay deterministic; only the audit identity varies, because an audit
    record is a fact about one execution.
    """
    return uuid4().hex


async def governed_query(
    engine: Any,
    shape: str,
    *,
    statuses: tuple[MemoryStatus, ...] | None = None,
    token: str | None = None,
) -> dict:
    """Drive one released `MemoryQuery` shape through the released retrieval service."""
    token = token or run_token()
    service = MemoryRetrievalService(PostgresMemoryRepository(engine))
    filters = MemoryMetadataFilter(
        statuses=statuses
        or (
            (MemoryStatus.SUPERSEDED, MemoryStatus.RETRACTED, MemoryStatus.EXPIRED)
            if shape == "stale_item"
            else (MemoryStatus.CANDIDATE, MemoryStatus.VERIFIED)
        )
    )
    query = MemoryQuery(
        query_id=uuid5(NAMESPACE_URL, f"sprint-22b-{shape}:{token}"),
        mode=MemoryRetrievalMode.TEXT if shape == "text" else MemoryRetrievalMode.METADATA,
        filters=filters,
        text=MemoryTextQuery(text="governed ingest probe") if shape == "text" else None,
    )
    started = perf_counter()
    page, _ = await service.retrieve(query)
    elapsed = (perf_counter() - started) * 1_000
    return {
        "shape": shape,
        "mode": query.mode.value,
        "statuses": [status.value for status in filters.statuses],
        "results": len(page.results),
        "elapsed_ms": round(elapsed, 3),
        "through_the_governed_path": True,
    }


async def hybrid_query(
    engine: Any, *, text_query: str, vector: MemoryVectorQuery, token: str | None = None
) -> dict:
    """Text and vector, fused by the released Context Plane ranking.

    W0-F3: `MemoryQuery.exactly_one_mode_payload` refuses a query carrying both a text and a
    vector payload, so "hybrid" is necessarily two released queries and a fusion. The fusion is
    the released reciprocal-rank formula from `cognitive_os.context.ranking`, reached through
    its own configuration rather than re-derived here.
    """
    from cognitive_os.config.context_config import ContextConfiguration
    from cognitive_os.context.ranking import ranking_profile

    token = token or run_token()
    profile = ranking_profile(ContextConfiguration())
    service = MemoryRetrievalService(PostgresMemoryRepository(engine))
    filters = MemoryMetadataFilter(statuses=(MemoryStatus.CANDIDATE, MemoryStatus.VERIFIED))
    started = perf_counter()
    text_page, _ = await service.retrieve(
        MemoryQuery(
            query_id=uuid5(NAMESPACE_URL, f"sprint-22b-hybrid-text:{token}"),
            mode=MemoryRetrievalMode.TEXT,
            filters=filters,
            text=MemoryTextQuery(text=text_query),
        )
    )
    vector_page, _ = await service.retrieve(
        MemoryQuery(
            query_id=uuid5(NAMESPACE_URL, f"sprint-22b-hybrid-vector:{token}"),
            mode=MemoryRetrievalMode.VECTOR,
            filters=filters,
            vector=vector,
        )
    )
    rrf_k = profile.rrf_k
    fused: dict[UUID, float] = {}
    for page in (text_page, vector_page):
        for result in page.results:
            fused[result.memory_id] = fused.get(result.memory_id, 0.0) + 1.0 / (rrf_k + result.rank)
    elapsed = (perf_counter() - started) * 1_000
    return {
        "shape": "hybrid",
        "composition": "two released MemoryQuery executions, reciprocal-rank fused",
        "rrf_k": rrf_k,
        "rrf_k_source": f"cognitive_os.context.ranking.ranking_profile -> {profile.profile_id}",
        "text_results": len(text_page.results),
        "vector_results": len(vector_page.results),
        "fused_results": len(fused),
        "elapsed_ms": round(elapsed, 3),
        "through_the_governed_path": True,
    }


async def temporal_query(engine: Any, *, as_of: datetime) -> dict:
    """The active view as of a moment — the one shape the released filter cannot express.

    W0-F2: `MemoryMetadataFilter` carries no as-of predicate, and its `include_historical`
    field is read by no released code — `current_memory_statement` joins strictly on
    `revision = current_revision`. The recipe is therefore raw SQL over the released
    `memory_revisions.created_at`, which needs no migration and changes no released behaviour,
    but does not travel through the governed retrieval path and records no access audit. That
    limitation is sealed on the record rather than mentioned in a report.
    """
    started = perf_counter()
    async with engine.connect() as connection:
        rows = int(
            await connection.scalar(
                text(
                    "SELECT count(*) FROM (SELECT DISTINCT ON (memory_id) memory_id, status "
                    "FROM cognitive_os.memory_revisions WHERE created_at <= :as_of "
                    "ORDER BY memory_id, revision DESC) AS view "
                    "WHERE status = ANY(:statuses)"
                ),
                {
                    "as_of": as_of,
                    "statuses": [MemoryStatus.CANDIDATE.value, MemoryStatus.VERIFIED.value],
                },
            )
            or 0
        )
    elapsed = (perf_counter() - started) * 1_000
    return {
        "shape": "temporal",
        "as_of": as_of.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "active_rows": rows,
        "elapsed_ms": round(elapsed, 3),
        "through_the_governed_path": False,
        "limitation": (
            "raw SQL over memory_revisions.created_at: the released MemoryQuery has no as-of "
            "predicate and MemoryMetadataFilter.include_historical is read by no released "
            "code, so this shape records no access audit (W0-F2)"
        ),
    }


# --------------------------------------------------------------------------------------
# Bounded graph-assisted retrieval: the sprint's hardest number.
# --------------------------------------------------------------------------------------


def bounded_graph_configuration() -> dict:
    """The frozen §2.2d recipe, rendered from the released limits object.

    Nothing here searches for a configuration. If it misses 500 ms the sprint reports the miss
    and the measured slope, and does not tune the recipe against the exit.
    """
    return {
        "limits": json.loads(BOUNDED_GRAPH_LIMITS.model_dump_json()),
        "limits_hash": BOUNDED_GRAPH_LIMITS.canonical_hash(),
        "arm": "minilm shortlist, then bounded graph edit distance",
        "shortlist_width": BOUNDED_GRAPH_LIMITS.vector_shortlist,
        "per_pair_timeout_ms": BOUNDED_GRAPH_LIMITS.per_pair_ged_timeout_ms,
        "walk_depth_cap": BOUNDED_GRAPH_LIMITS.path_depth,
        "query_budget_seconds": BOUNDED_GRAPH_LIMITS.query_budget_seconds,
        "returned_results": BOUNDED_GRAPH_LIMITS.returned_results,
        **BOUNDED_GRAPH_READING,
    }


# --------------------------------------------------------------------------------------
# Mutation, bloat, reindex, concurrency.
# --------------------------------------------------------------------------------------


async def table_bloat(engine: Any, table: str = CORPUS_TABLE) -> dict:
    """Dead tuples and physical size, read exactly from the heap.

    W0-F5: this read `pg_stat_user_tables`, whose counters the statistics collector updates
    asynchronously. Deleting a fifth of the corpus and measuring immediately reported zero dead
    tuples — a bloat measurement that could not notice bloat, which is 22A W4-F2 in its purest
    form. `pgstattuple` scans the heap and answers synchronously, so the number is a fact about
    the table rather than about how long the collector had been given. It costs a full scan,
    which W3 must budget for at 10^6 rows and which is the honest price of an exact answer.
    """
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgstattuple"))
    async with engine.connect() as connection:
        if not await connection.scalar(
            text("SELECT to_regclass(:name)"), {"name": f"cognitive_os.{table}"}
        ):
            return {"table": table, "present": False}
        row = (
            await connection.execute(
                text(
                    "SELECT table_len, tuple_count, dead_tuple_count, dead_tuple_percent, "
                    "free_percent FROM pgstattuple(:name)"
                ),
                {"name": f"cognitive_os.{table}"},
            )
        ).one()
        total = int(
            await connection.scalar(
                text("SELECT pg_total_relation_size(CAST(:name AS regclass))"),
                {"name": f"cognitive_os.{table}"},
            )
            or 0
        )
    length, live, dead, dead_percent, free_percent = row
    return {
        "table": table,
        "present": True,
        "source": "pgstattuple, an exact heap scan",
        "live_tuples": int(live),
        "dead_tuples": int(dead),
        "dead_tuple_percent": float(dead_percent),
        "free_percent": float(free_percent),
        "heap_length_bytes": int(length),
        "total_relation_size_bytes": total,
    }


async def reindex_with_readers(
    engine: Any, index: str, *, readers: int, seconds: float, table: str = CORPUS_TABLE
) -> dict:
    """Reindex concurrently while readers probe, and measure what the readers saw.

    A reindex that is only timed proves the reindex finished. §3's W3 asks what concurrent
    reads did *during* it, so the readers are measured and their latencies reported beside the
    reindex duration.

    **W1-F4: the readers must not hold open transactions, or this driver deadlocks against
    itself.** A SQLAlchemy connection begins a transaction on its first statement and holds it
    until the block exits, so three readers looping inside `engine.connect()` kept an
    `AccessShareLock` open for their whole lifetime. `REINDEX INDEX CONCURRENTLY` waits for
    exactly those transactions to end, and they end only when `stop` is set — which happens
    only after the reindex returns. Observed directly: the reindex backend sat in
    `Lock/virtualxid` while all three readers stayed `active`.

    It passed at W0's 200 rows because the reindex finished before the readers opened their
    first transaction — a race the driver won once and would have lost for hours at 10^6. The
    readers now run in `AUTOCOMMIT`, so each probe commits as it completes and the reindex has
    something to finish waiting for. That is also the more honest measurement: a real
    concurrent reader is a stream of short queries, not one transaction held open for the
    duration of a maintenance operation.
    """
    stop = asyncio.Event()

    async def reader(worker: int) -> list[float]:
        latencies: list[float] = []
        async with engine.connect() as connection:
            await connection.execution_options(isolation_level="AUTOCOMMIT")
            while not stop.is_set():
                started = perf_counter()
                await connection.execute(
                    text(f"SELECT count(*) FROM cognitive_os.{table} WHERE scope_id = :s"),
                    {"s": f"scope-{worker % int(FILTER_PREDICATE['scopes_in_corpus']):02d}"},
                )
                latencies.append((perf_counter() - started) * 1_000)
        return latencies

    async def rebuild() -> float:
        started = perf_counter()
        async with engine.connect() as connection:
            await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text(f"REINDEX INDEX CONCURRENTLY cognitive_os.{index}"))
        return perf_counter() - started

    tasks = [asyncio.create_task(reader(worker)) for worker in range(readers)]
    guard = asyncio.create_task(asyncio.sleep(seconds))
    try:
        elapsed = await rebuild()
    finally:
        await guard
        stop.set()
        results = await asyncio.gather(*tasks)

    latencies = [value for group in results for value in group]
    return {
        "index": index,
        "reindex_seconds": round(elapsed, 3),
        "concurrent_readers": readers,
        "reader_queries": len(latencies),
        "reader_latency": _percentiles(latencies) if latencies else None,
        "readers_saw_an_error": False,
    }


# --------------------------------------------------------------------------------------
# Restore: verified by querying, never by comparing hashes alone.
# --------------------------------------------------------------------------------------


async def seed_learned_artifact(engine: Any) -> dict:
    """Put the live learned artifact's bytes into 22B's own store, through the released path.

    W1-D1. §2.2e requires the *restored* store to resolve
    `learned.containment.correction_ranking`'s artifact and load its bytes. That artifact is
    registered in `cognitive_os_s21d7_measured` and nowhere else, so against 22B's fresh store
    the checklist's artifact leg passed vacuously — W0's slice reported `resolved: false` and
    flagged it.

    The fix registers the **same bytes** here through `ArtifactService.put_file`, the released
    content-addressed path: the store computes the hash itself, so this is a genuine
    registration rather than a hand-written ledger row, and the content hash is the identity —
    re-registering identical bytes in a second store is what content addressing is for.

    What is deliberately **not** copied is D7's learned *lineage*: component revisions,
    activation history and evidence records stay where they were produced. §2.3 puts learners
    out of 22B's scope, and a lineage cannot be moved without either a real activation run or
    fabricated provenance. So the checklist verifies that a restore reproduces the artifact's
    pointer and its loadable bytes — which is what D7 W3-F1 asked for — and says plainly that
    it does not verify the learned component's governance chain.
    """
    from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )

    source = Path(LIVE_LEARNED_ARTIFACT_SOURCE["path"])
    if not source.is_file():
        raise SystemExit(
            f"the live learned artifact is not at {source}. 22B does not synthesise it: "
            "without the released bytes the §2.2e artifact leg cannot be made reachable"
        )
    root = Path(os.environ.get("COGOS_ARTIFACT_ROOT", ""))
    if not root.is_dir():
        raise SystemExit("COGOS_ARTIFACT_ROOT must point at 22B's artifact root")

    service = ArtifactService(ContentAddressedFilesystem(root), PostgresArtifactRepository(engine))
    reference = await service.put_file(source, media_type="application/octet-stream")
    loaded = await service.get_bytes(reference.artifact_id)
    return {
        "component": LIVE_LEARNED_ARTIFACT["component"],
        "source_path": str(source),
        "source_store": LIVE_LEARNED_ARTIFACT_SOURCE["store"],
        "artifact_id": str(reference.artifact_id),
        "content_hash": reference.content_hash,
        "storage_key": reference.storage_key,
        "size_bytes": reference.size_bytes,
        "matches_expected_hash": reference.content_hash == LIVE_LEARNED_ARTIFACT["artifact_hash"],
        "bytes_load_back": len(loaded) == reference.size_bytes,
        "registered_through": "released ArtifactService.put_file, content-addressed",
        "learned_lineage_copied": False,
        "why_not": (
            "component revisions, activation history and evidence records are D7's and stay "
            "there; §2.3 puts learners out of 22B's scope. The restore checklist therefore "
            "verifies the artifact pointer and its loadable bytes, not the learned "
            "component's governance chain"
        ),
    }


async def restore_query_checklist(restore_url: str) -> dict:
    """§2.2e, executed against the restored store.

    D7 W3-F1: a digest proves bytes, not usability. Every line here is a query answered by the
    restored database, and the artifact line loads bytes rather than comparing a hash to a
    hash.
    """
    engine = create_postgres_engine(restore_url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as connection:
            counts = {
                name: int(
                    await connection.scalar(text(f"SELECT count(*) FROM cognitive_os.{name}")) or 0
                )
                for name in ("events", "artifacts", "memory_items", "memory_revisions")
            }
            active = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.memory_items "
                        "WHERE status = ANY(:statuses)"
                    ),
                    {
                        "statuses": [
                            MemoryStatus.CANDIDATE.value,
                            MemoryStatus.VERIFIED.value,
                        ]
                    },
                )
                or 0
            )
            # The same join `backup_event_store.sh` and `restore_event_store.sh` use: the
            # storage key lives on the blob, not on the artifact row. W0-F7: this read a
            # `storage_key` column off `cognitive_os.artifacts`, which has never had one, so
            # the artifact leg of the checklist could only ever have raised.
            artifact = (
                await connection.execute(
                    text(
                        "SELECT b.storage_key, b.size_bytes FROM cognitive_os.artifact_blobs b "
                        "JOIN cognitive_os.artifacts a ON a.content_hash = b.content_hash "
                        "WHERE b.content_hash = :hash LIMIT 1"
                    ),
                    {"hash": LIVE_LEARNED_ARTIFACT["artifact_hash"]},
                )
            ).first()
    finally:
        await engine.dispose()
    return {
        "row_counts": counts,
        "active_view_rows": active,
        "active_view_was_queried": True,
        "learned_artifact_pointer_resolved": artifact is not None,
        "learned_artifact_storage_key": artifact[0] if artifact else None,
        "learned_artifact_size_bytes": artifact[1] if artifact else None,
        "learned_artifact_hash": LIVE_LEARNED_ARTIFACT["artifact_hash"],
        "checklist": list(RESTORE_CHECKLIST),
    }


def load_restored_artifact(root: Path, storage_key: str, expected_hash: str) -> dict:
    """Load the restored artifact's bytes and hash them. Loading, not comparing metadata."""
    path = root.joinpath(*Path(storage_key).parts)
    if not path.is_file():
        return {"loaded": False, "reason": "the restored artifact file is missing"}
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    return {
        "loaded": True,
        "bytes": len(data),
        "content_hash": digest,
        "matches_expected": digest == expected_hash,
    }


# --------------------------------------------------------------------------------------
# The fixture-scale slice W0 runs to prove the drivers compose.
# --------------------------------------------------------------------------------------


async def _slice(items: int, dataset: str) -> dict:
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required: the slice creates a table")
    engine = create_postgres_engine(url, pool_size=4, max_overflow=2, command_timeout_seconds=600)
    try:
        load = await create_corpus(engine, dataset, items)
        index = await build_corpus_index(engine, dataset)
        probes = {
            shape: await probe_corpus(
                engine, dataset, shape=shape, probes=8, warmup=2, candidate_limit=10
            )
            for shape in ("exact_vector", "ann", "filtered_ann")
        }
        recall = await recall_at(engine, dataset, probes=8)
        ingest = await governed_ingest(engine, min(items, 40), deciles=4)
        governed = {
            shape: await governed_query(engine, shape)
            for shape in ("metadata", "text", "stale_item")
        }
        embed = await governed_embed(engine, min(items, 40))
        from cognitive_os.infrastructure.embeddings import DeterministicEmbeddingProvider

        provider = DeterministicEmbeddingProvider(dimension=64)
        hybrid = await hybrid_query(
            engine,
            text_query="governed ingest probe",
            vector=MemoryVectorQuery(
                provider_id=provider.identity.provider_id,
                model_id=provider.identity.model_id,
                dimension=64,
                vector=tuple(await provider.embed_query("governed ingest probe item 1")),
            ),
        )
        temporal = await temporal_query(engine, as_of=datetime.now(UTC) + timedelta(seconds=1))
        bloat_before = await table_bloat(engine, corpus_table(dataset))
        async with engine.begin() as connection:
            await connection.execute(
                text(f"DELETE FROM cognitive_os.{corpus_table(dataset)} WHERE row_id % 5 = 0")
            )
            await connection.execute(text(f"ANALYZE cognitive_os.{corpus_table(dataset)}"))
        bloat_after = await table_bloat(engine, corpus_table(dataset))
        reindex = await reindex_with_readers(
            engine, index["index"], readers=3, seconds=0.2, table=corpus_table(dataset)
        )
    finally:
        await engine.dispose()

    # The §2.2e checklist, executed against 22B's own store rather than a restored one. W0
    # proves the checklist is answerable by query; the full backup-restore round trip is W1's
    # vertical-slice item (§3.1). Running it here also shows the checklist can *fail*: this
    # store has never held the live learned artifact, so the pointer does not resolve, and the
    # checklist says so instead of passing vacuously.
    checklist = await restore_query_checklist(url)

    return {
        "dataset": dataset,
        "corpus_rows": items,
        "scale": "fixture",
        "decides_no_exit_criterion": True,
        "why_this_is_not_a_measurement": (
            "every 22B exit is a claim at 10^6 items, and this record is a few hundred rows "
            "run to prove the drivers compose and can fail. The `reads_an_exit` flags below "
            "describe which shape a driver serves at full scale, never that this run decided "
            "anything. Publishing the pre-registration after this slice is therefore not "
            "publishing it after the numbers: no number here is one of the five"
        ),
        "bulk_load": load,
        "index": index,
        "vector_probes": probes,
        "recall": recall,
        "governed_ingest": ingest,
        "governed_embed": embed,
        "governed_queries": governed,
        "hybrid": hybrid,
        "temporal": temporal,
        "bloat_before": bloat_before,
        "bloat_after": bloat_after,
        "reindex_with_readers": reindex,
        "restore_checklist_shape": checklist,
        "bounded_graph_configuration": bounded_graph_configuration(),
    }


async def incremental_insert(engine: Any, dataset: str, rows: int, *, batch: int = 100) -> dict:
    """Insert into a corpus that already carries its HNSW index, and price the difference.

    W1 owes this because the bulk load builds the index *afterwards*, which is the cheap order
    and not the one a running system uses. Every insert into an indexed table also inserts into
    the graph, and the gap between the two rates is what an operator actually pays for keeping
    a million-item index live. The rows continue the frozen stream past the corpus, so they are
    the recipe's own rows rather than fresh arbitrary vectors.
    """
    table = corpus_table(dataset)
    dimension = int(DATASETS[dataset]["dimension"])
    async with engine.connect() as connection:
        before = int(
            await connection.scalar(text(f"SELECT count(*) FROM cognitive_os.{table}")) or 0
        )
    stream = islice(corpus_stream(dataset), before, before + rows)
    started = perf_counter()
    written = 0
    while written < rows:
        values = ",".join(
            f"({dimension}, '{scope}', '{status}', '{kind}', '{literal}')"
            for literal, scope, status, kind in islice(stream, min(batch, rows - written))
        )
        if not values:
            break
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    f"INSERT INTO cognitive_os.{table} "
                    f"(dimension, scope_id, status, memory_type, embedding) VALUES {values}"
                )
            )
        written += min(batch, rows - written)
    elapsed = perf_counter() - started
    async with engine.connect() as connection:
        after = int(
            await connection.scalar(text(f"SELECT count(*) FROM cognitive_os.{table}")) or 0
        )
    return {
        "dataset": dataset,
        "table": table,
        "rows_before": before,
        "rows_inserted": written,
        "rows_after": after,
        "seconds": round(elapsed, 3),
        "rows_per_second": round(written / elapsed, 1) if elapsed else None,
        "index_present_during_insert": True,
        "reads_an_exit_criterion": False,
        "why": (
            "the bulk load builds the index afterwards; a live system does not. This is the "
            "price of keeping a 10^6 HNSW index current, reported beside the load rate it "
            "should be compared against"
        ),
    }


async def restore_corpus_to_pre_registered_size(
    engine: Any, dataset: str, rows: int = 1_000_000
) -> dict:
    """Return a corpus to exactly the pre-registered row count, with a clean index.

    W1-F6. The incremental-insert measurement appends to the corpus, and it was run against
    `clustered` — the one dataset an exit criterion reads. That left the recall corpus at
    1 010 000 rows, which is not the million the pre-registration names, and a recall number
    measured over it would be a number about a corpus nobody registered.

    Deleting the appended rows is not enough on its own: the HNSW graph would still carry their
    traces, so the index W2 measures would not be the index whose build was sealed. The rebuild
    is therefore part of the repair, and its duration is recorded so the cost of the mistake is
    visible rather than absorbed.
    """
    table = corpus_table(dataset)
    index = f"{table}_hnsw_{int(DATASETS[dataset]['dimension'])}"
    async with engine.connect() as connection:
        before = int(
            await connection.scalar(text(f"SELECT count(*) FROM cognitive_os.{table}")) or 0
        )
    started = perf_counter()
    async with engine.begin() as connection:
        await connection.execute(
            text(f"DELETE FROM cognitive_os.{table} WHERE row_id > :rows"), {"rows": rows}
        )
    async with engine.connect() as connection:
        await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(text(f"VACUUM ANALYZE cognitive_os.{table}"))
        rebuild_started = perf_counter()
        await connection.execute(text(f"REINDEX INDEX cognitive_os.{index}"))
        rebuild_seconds = perf_counter() - rebuild_started
    async with engine.connect() as connection:
        after = int(
            await connection.scalar(text(f"SELECT count(*) FROM cognitive_os.{table}")) or 0
        )
        index_bytes = int(
            await connection.scalar(
                text("SELECT pg_relation_size(CAST(:name AS regclass))"),
                {"name": f"cognitive_os.{index}"},
            )
            or 0
        )
    return {
        "dataset": dataset,
        "table": table,
        "rows_before": before,
        "rows_after": after,
        "pre_registered_rows": rows,
        "restored": after == rows,
        "total_seconds": round(perf_counter() - started, 3),
        "index_rebuild_seconds": round(rebuild_seconds, 3),
        "index_bytes_after": index_bytes,
        "why": (
            "W1-F6: the incremental-insert driver was run against the dataset the recall exit "
            "reads. The corpus is returned to the pre-registered million and the index rebuilt, "
            "so W2 measures the corpus that was registered rather than the one W1 left behind"
        ),
    }


async def storage_report(engine: Any, dataset: str, index: str) -> dict:
    """What the corpus costs on disk and in the server, sealed beside its build time."""
    table = corpus_table(dataset)
    async with engine.connect() as connection:
        rows = int(await connection.scalar(text(f"SELECT count(*) FROM cognitive_os.{table}")) or 0)
        table_bytes = int(
            await connection.scalar(
                text("SELECT pg_total_relation_size(CAST(:name AS regclass))"),
                {"name": f"cognitive_os.{table}"},
            )
            or 0
        )
        index_bytes = int(
            await connection.scalar(
                text("SELECT pg_relation_size(CAST(:name AS regclass))"),
                {"name": f"cognitive_os.{index}"},
            )
            or 0
        )
        database_bytes = int(
            await connection.scalar(text("SELECT pg_database_size(current_database())")) or 0
        )
    usage = shutil.disk_usage(DATA_ROOT)
    memory = {
        key: int(value.split()[0])
        for key, _, value in (
            line.partition(":") for line in Path("/proc/meminfo").read_text().splitlines()
        )
        if key in {"MemTotal", "MemAvailable"}
    }
    return {
        "rows": rows,
        "table_total_bytes": table_bytes,
        "index_bytes": index_bytes,
        "database_bytes": database_bytes,
        "data_root_free_bytes": usage.free,
        "host_memory_total_kib": memory.get("MemTotal"),
        "host_memory_available_kib": memory.get("MemAvailable"),
    }


async def _restore_corpus(dataset: str, rows: int) -> dict:
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    engine = create_postgres_engine(
        url, pool_size=2, max_overflow=0, command_timeout_seconds=21_600
    )
    try:
        record = await restore_corpus_to_pre_registered_size(engine, dataset, rows)
    finally:
        await engine.dispose()
    record["recipes_hash"] = recipes_hash()
    return record


async def _incremental(dataset: str, rows: int) -> dict:
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    engine = create_postgres_engine(url, pool_size=2, max_overflow=0, command_timeout_seconds=3600)
    try:
        record = await incremental_insert(engine, dataset, rows)
    finally:
        await engine.dispose()
    record["recipes_hash"] = recipes_hash()
    return record


async def _ingest(items: int, start: int) -> dict:
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    engine = create_postgres_engine(url, pool_size=2, max_overflow=0, command_timeout_seconds=3600)
    try:
        record = await governed_ingest(engine, items, start=start)
    finally:
        await engine.dispose()
    record["recipes_hash"] = recipes_hash()
    return record


async def _restore_check() -> dict:
    """§2.2e end to end: source against restored, queried, with the artifact bytes loaded.

    The artifact is loaded out of the **restored archive** rather than the live artifact root,
    because a restore that quietly reads the source's bytes has verified nothing (D7 W3-F1).
    """
    source_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not source_url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    restore_url = source_url.replace("cognitive_os_s22b_test", "cognitive_os_s22b_restore_test")
    source = await restore_query_checklist(source_url)
    restored = await restore_query_checklist(restore_url)

    backups = Path(os.environ.get("COGOS_BACKUP_ROOT", "")) / "artifacts"
    archives = sorted(backups.glob("*-artifacts.tar.zst"))
    if not archives:
        raise SystemExit("no restored artifact archive to load bytes from")
    root = Path(_mkdtemp(prefix="s22b-restore-artifacts-"))
    subprocess.run(["bash", "-c", f"zstd -q -dc {archives[-1]} | tar -xf - -C {root}"], check=True)
    loaded = load_restored_artifact(
        root, restored["learned_artifact_storage_key"] or "", restored["learned_artifact_hash"]
    )
    checks = {
        "row_counts_identical": source["row_counts"] == restored["row_counts"],
        "active_view_identical": source["active_view_rows"] == restored["active_view_rows"],
        "artifact_pointer_resolved": bool(restored["learned_artifact_pointer_resolved"]),
        "artifact_bytes_loaded_and_match": bool(loaded.get("matches_expected")),
    }
    return {
        "checklist": list(RESTORE_CHECKLIST),
        "source": source,
        "restored": restored,
        "artifact_loaded_from_restored_archive": loaded,
        "archive": archives[-1].name,
        "checks": checks,
        "all_four_met": all(checks.values()),
        "verified_by_query_not_by_digest": True,
        "recipes_hash": recipes_hash(),
    }


async def _seed() -> dict:
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    engine = create_postgres_engine(url, pool_size=2, max_overflow=0)
    try:
        return await seed_learned_artifact(engine)
    finally:
        await engine.dispose()


async def _corpus(dataset: str, rows: int, batch: int, timeout: float) -> dict:
    """Build one dataset's corpus at full scale and seal what it cost.

    Separate from `--slice` because this is the measurement: load seconds, build seconds,
    index size and disk are the storage report W1 owes, and they are only meaningful if
    nothing else is running on the reference host while they are taken.
    """
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required: the corpus creates a table")
    engine = create_postgres_engine(
        url, pool_size=2, max_overflow=0, command_timeout_seconds=timeout
    )
    try:
        load = await create_corpus(engine, dataset, rows, batch=batch)
        index = await build_corpus_index(engine, dataset)
        storage = await storage_report(engine, dataset, index["index"])
    finally:
        await engine.dispose()
    return {
        "dataset": dataset,
        "corpus_rows": rows,
        "bulk_load": load,
        "index": index,
        "storage": storage,
        "recipes_hash": recipes_hash(),
        "reads_an_exit_criterion": False,
        "why_no_exit": (
            "§2.2c: the bulk engine load is engine capacity and reads no exit. The retrieval "
            "envelope over this corpus is W2's, and the governed-ingest exit reads a different "
            "path entirely"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipes", action="store_true", help="print the frozen recipes")
    parser.add_argument("--slice", action="store_true", help="run every driver at fixture scale")
    parser.add_argument("--corpus", action="store_true", help="build one dataset at full scale")
    parser.add_argument("--ingest", action="store_true", help="the governed-ingest exit run")
    parser.add_argument("--incremental", action="store_true", help="insert into the built index")
    parser.add_argument("--restore-corpus", action="store_true", help="W1-F6 repair")
    parser.add_argument("--restore-check", action="store_true", help="the §2.2e checklist")
    parser.add_argument("--incremental-rows", type=int, default=10_000)
    parser.add_argument("--ingest-items", type=int, default=50_000)
    parser.add_argument("--ingest-start", type=int, default=1_000)
    parser.add_argument(
        "--seed-artifact",
        action="store_true",
        help="register the live learned artifact's bytes in 22B's store (W1-D1)",
    )
    parser.add_argument("--rows", type=int, default=1_000_000)
    parser.add_argument("--batch", type=int, default=1_000)
    parser.add_argument("--command-timeout", type=float, default=21_600.0)
    parser.add_argument("--items", type=int, default=200)
    parser.add_argument("--dataset", choices=sorted(DATASETS), default="clustered")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    if arguments.recipes:
        payload: dict[str, Any] = {"recipes": RECIPES, "recipes_hash": recipes_hash()}
    elif arguments.restore_check:
        payload = asyncio.run(_restore_check())
    elif arguments.restore_corpus:
        payload = asyncio.run(_restore_corpus(arguments.dataset, arguments.rows))
    elif arguments.incremental:
        payload = asyncio.run(_incremental(arguments.dataset, arguments.incremental_rows))
    elif arguments.ingest:
        payload = asyncio.run(_ingest(arguments.ingest_items, arguments.ingest_start))
    elif arguments.seed_artifact:
        payload = asyncio.run(_seed())
    elif arguments.corpus:
        payload = asyncio.run(
            _corpus(arguments.dataset, arguments.rows, arguments.batch, arguments.command_timeout)
        )
    elif arguments.slice:
        payload = asyncio.run(_slice(arguments.items, arguments.dataset))
        payload["recipes_hash"] = recipes_hash()
    else:
        parser.error("choose --recipes, --slice, --corpus, --ingest or --seed-artifact")

    encoded = json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
