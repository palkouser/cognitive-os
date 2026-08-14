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
import sys
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
    force_index: bool = False,
) -> dict:
    """Drive one vector shape over the corpus table, warm, with the cold probe kept.

    The caller restarts PostgreSQL before this runs; the first probe here is therefore the
    cold one and is reported separately from the warm distribution, never averaged into it.

    `force_index` sets `enable_seqscan = off` for the statement. It is **never** used for a
    number an exit reads — W2-F2 found that the planner declines the HNSW index for the frozen
    filtered predicate at 10^6, and a shape whose measurement had to be forced into the index
    would be a claim about a plan nobody's query will get. The forced pass runs beside the
    pre-registered one as a diagnostic, so the gap between what the planner chose and what the
    substrate can do is a measured number rather than an opinion.
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
            if force_index:
                await connection.execute(text("SET LOCAL enable_seqscan = off"))
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
        "sequential_scan_disabled": force_index,
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


def restart_postgres(*, timeout: float = 120.0) -> dict:
    """§2.2b's first step, taken literally: the database process is replaced, not hinted at.

    "restart_is_a_real_restart" is the pre-registered wording, and the D7 lifecycle rule behind
    it is that a separate process is the only thing that proves a cache was not carried. So this
    restarts the container `.env.s22b.local` names and waits for the server to answer again,
    reusing the released `learned_restart_smoke.sh` shape rather than inventing a second one.

    **What it does not drop**, and the record says so: the *host page cache*. A container
    restart empties PostgreSQL's shared buffers, not Linux's. "Cold" in this envelope therefore
    means cold-server, and on a host whose shared_buffers is a fraction of the index it is the
    page cache that decides a warm number. Naming that is the difference between a limitation
    and a surprise.
    """
    container = os.environ.get("COGOS_POSTGRES_TOOL_CONTAINER")
    if not container:
        raise SystemExit(
            "COGOS_POSTGRES_TOOL_CONTAINER is required: §2.2b's warm protocol restarts the "
            "database rather than issuing a cache hint, and the container is never guessed"
        )
    url = (os.environ.get("COGOS_DATABASE_ADMIN_URL") or "").replace(
        "postgresql+asyncpg", "postgresql"
    )
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    started = perf_counter()
    subprocess.run(["docker", "restart", container], check=True, capture_output=True)
    ready = False
    while perf_counter() - started < timeout:
        probe = subprocess.run(
            ["psql", url, "-Atqc", "SELECT 1"], capture_output=True, text=True, check=False
        )
        if probe.returncode == 0 and probe.stdout.strip() == "1":
            ready = True
            break
    if not ready:
        raise SystemExit(f"{container} did not answer within {timeout}s of its restart")
    return {
        "container": container,
        "restarted": True,
        "ready_after_seconds": round(perf_counter() - started, 3),
        "shared_buffers_start_empty": True,
        "host_page_cache_dropped": False,
        "limitation": (
            "a container restart empties PostgreSQL's shared buffers, not the host page cache, "
            "so cold here means cold-server rather than cold-storage"
        ),
    }


async def governed_probe_series(
    engine: Any, shape: str, *, probes: int, warmup: int, dataset: str
) -> dict:
    """500 measured probes of one governed shape, with the cold probe kept apart.

    The three shapes here answer over the governed memory store rather than over a corpus
    table, so they do not vary with the dataset — and the record says that in a field rather
    than letting a reader infer it from two identical-looking numbers. They are still measured
    once per dataset, because §2.2b's protocol is per dataset and a shape measured under only
    one restart would be the one shape whose warm state nobody re-established.
    """
    from cognitive_os.infrastructure.embeddings import DeterministicEmbeddingProvider

    provider = DeterministicEmbeddingProvider(dimension=64)
    vector = MemoryVectorQuery(
        provider_id=provider.identity.provider_id,
        model_id=provider.identity.model_id,
        dimension=64,
        vector=tuple(await provider.embed_query("governed ingest probe item 1")),
    )
    as_of = datetime.now(UTC) + timedelta(seconds=1)

    async def one() -> dict:
        if shape == "hybrid":
            return await hybrid_query(engine, text_query="governed ingest probe", vector=vector)
        if shape == "temporal":
            return await temporal_query(engine, as_of=as_of)
        return await governed_query(engine, shape)

    latencies: list[float] = []
    cold_ms: float | None = None
    last: dict = {}
    for index in range(warmup + probes + 1):
        started = perf_counter()
        last = await one()
        elapsed = (perf_counter() - started) * 1_000
        if index == 0:
            cold_ms = round(elapsed, 3)
            continue
        if index <= warmup:
            continue
        latencies.append(elapsed)

    record = {
        "dataset": dataset,
        "shape": shape,
        "varies_with_the_dataset": False,
        "why": (
            "this shape reads the governed memory store, which both datasets share; the corpus "
            "table it does not touch is what the 10^6 rows are in"
        ),
        "cold_first_probe_ms": cold_ms,
        "warmup_probes_discarded": warmup,
        **_percentiles(latencies),
        "reads_an_exit": False,
        "last_result": last,
    }
    if shape == "temporal":
        record["limitation"] = last.get("limitation")
        record["through_the_governed_path"] = False
    return record


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


# --------------------------------------------------------------------------------------
# W3: mutation at scale, through the released lifecycle service.
# --------------------------------------------------------------------------------------


def _lifecycle(engine: Any) -> Any:
    """The released governed lifecycle path, with its event service attached.

    `MemoryService` is the gateway for *creating* memories and exposes no transition at all;
    `MemoryLifecycleService` is the released one that promotes, supersedes, retracts and
    expires, and appends the matching released event for each. W3 composes over it rather than
    writing statuses, so every mutation in this wave leaves a revision, a provenance carry-over
    and an event behind — which is what makes the restore checklist worth running.
    """
    from cognitive_os.memory.lifecycle import MemoryLifecycleService

    return MemoryLifecycleService(
        PostgresMemoryRepository(engine),
        event_service=MemoryEventService(PostgresEventStore(engine, build_default_event_catalog())),
    )


def _ingest_memory_id(index: int) -> UUID:
    """The id `_write_request` derived for item `index`.

    The mutation waves address the store by recomputing ids rather than by selecting rows, for
    the same reason the corpus is a seeded stream: a wave that picks its victims with a query
    would mutate a different set on every run, and a re-run is how this programme checks itself.
    """
    return uuid5(NAMESPACE_URL, f"sprint-22b-ingest:{index}")


def _promotion_evidence(index: int) -> Any:
    """The two source types `MemoryLifecycleService.promote` refuses to proceed without.

    Released rule, not a 22B one: promotion requires accepted authoritative trajectory
    evidence — an acceptance decision *and* a coding trajectory — and a non-provider actor.
    W3 satisfies it by composition rather than by widening the rule.
    """
    return MemoryProvenanceBundle(
        sources=tuple(
            MemorySourceRef(
                identity=MemorySourceIdentity(
                    source_type=source_type,
                    source_id=uuid5(NAMESPACE_URL, f"sprint-22b-w3-{source_type.value}:{index}"),
                ),
                source_hash=hashlib.sha256(
                    f"sprint-22b-w3:{source_type.value}:{index}".encode()
                ).hexdigest(),
                relationship="mutation_wave_evidence",
            )
            for source_type in (
                MemorySourceType.ACCEPTANCE_DECISION,
                MemorySourceType.CODING_TRAJECTORY,
            )
        )
    )


#: The actor every W3 transition is attributed to. An operator, because the released promotion
#: path refuses a provider — an authority a provider does not have is not one a driver may lend
#: it to make a wave run.
W3_ACTOR = MemoryCreator(creator_type=MemoryCreatorType.OPERATOR, creator_id="sprint-22b-w3")


async def active_view(engine: Any) -> dict:
    """The active view, queried two ways that must agree.

    §2.2e asks for the active view *queried, not counted*, and W3 is the wave where the
    distinction earns its keep. `memory_items.status` is maintained by the released
    `advance_memory_item`; the released reader joins each item to the revision its
    `current_revision` names. After ten thousand transitions those two can only still agree if
    every transition advanced both halves — so the driver asks both and reports whether they
    do, instead of asking the cheaper one and trusting it.
    """
    active = [MemoryStatus.CANDIDATE.value, MemoryStatus.VERIFIED.value]
    async with engine.connect() as connection:
        by_item = int(
            await connection.scalar(
                text(
                    "SELECT count(*) FROM cognitive_os.memory_items WHERE status = ANY(:statuses)"
                ),
                {"statuses": active},
            )
            or 0
        )
        by_revision = int(
            await connection.scalar(
                text(
                    "SELECT count(*) FROM cognitive_os.memory_items i "
                    "JOIN cognitive_os.memory_revisions r ON r.memory_id = i.memory_id "
                    "AND r.revision = i.current_revision "
                    "WHERE r.status = ANY(:statuses)"
                ),
                {"statuses": active},
            )
            or 0
        )
        by_status = {
            status: int(count)
            for status, count in (
                await connection.execute(
                    text("SELECT status, count(*) FROM cognitive_os.memory_items GROUP BY status")
                )
            ).all()
        }
        revisions = int(
            await connection.scalar(text("SELECT count(*) FROM cognitive_os.memory_revisions")) or 0
        )
        events = int(await connection.scalar(text("SELECT count(*) FROM cognitive_os.events")) or 0)
    return {
        "active_rows_by_item_status": by_item,
        "active_rows_by_current_revision_join": by_revision,
        "the_two_readings_agree": by_item == by_revision,
        "items_by_status": by_status,
        "revisions": revisions,
        "events": events,
        "queried_not_counted": True,
    }


async def mutation_wave(
    engine: Any, kind: str, *, count: int, start: int, successor_offset: int = 1
) -> dict:
    """One supersession or tombstone wave, item by item, through the released service.

    **A supersession costs two transitions, and that is the released lifecycle's rule.** A
    candidate may not go straight to superseded: `can_transition_memory` allows candidate ->
    verified and verified -> superseded, so every superseded item is promoted first, with the
    evidence the released promotion path demands. The wave therefore writes two revisions and
    two events per item, and reports both counts rather than one.

    A tombstone is one transition: candidate -> retracted is legal directly.
    """
    from cognitive_os.domain.memory import (
        MemoryPromotionRequest,
        MemoryRetractionRequest,
        MemorySupersessionRequest,
        MemoryTransitionReason,
    )

    service = _lifecycle(engine)
    started = perf_counter()
    transitions = 0
    promoted = 0
    mutated: list[str] = []
    failures: list[dict[str, Any]] = []

    for index in range(start, start + count):
        memory_id = _ingest_memory_id(index)
        try:
            if kind == "supersession":
                await service.promote(
                    MemoryPromotionRequest(
                        request_id=uuid5(NAMESPACE_URL, f"sprint-22b-w3-promote:{index}"),
                        memory_id=memory_id,
                        expected_revision=1,
                        evidence=_promotion_evidence(index),
                        actor=W3_ACTOR,
                    )
                )
                promoted += 1
                transitions += 1
                await service.supersede(
                    MemorySupersessionRequest(
                        request_id=uuid5(NAMESPACE_URL, f"sprint-22b-w3-supersede:{index}"),
                        memory_id=memory_id,
                        successor_memory_id=_ingest_memory_id(index + successor_offset),
                        expected_revision=2,
                        actor=W3_ACTOR,
                    )
                )
                transitions += 1
            else:
                await service.retract(
                    MemoryRetractionRequest(
                        request_id=uuid5(NAMESPACE_URL, f"sprint-22b-w3-retract:{index}"),
                        memory_id=memory_id,
                        expected_revision=1,
                        actor=W3_ACTOR,
                        reason=MemoryTransitionReason.POLICY_RETRACTION,
                    )
                )
                transitions += 1
            mutated.append(str(memory_id))
        except Exception as error:  # a refused transition is a result, not a crash
            failures.append({"index": index, "error": f"{type(error).__name__}: {error}"})

    elapsed = perf_counter() - started
    return {
        "wave": kind,
        "path": "governed: MemoryLifecycleService -> revision + provenance carry-over + event",
        "first_index": start,
        "items_requested": count,
        "items_mutated": len(mutated),
        "promotions": promoted,
        "transitions": transitions,
        "seconds": round(elapsed, 3),
        "transitions_per_second": round(transitions / elapsed, 2) if elapsed else None,
        "failures": failures[:20],
        "failure_count": len(failures),
        "reads_an_exit_criterion": False,
        "why_two_transitions": (
            "candidate -> superseded is not a legal released transition; candidate -> verified "
            "-> superseded is. The promotion carries the acceptance-decision and "
            "coding-trajectory evidence the released path requires"
        )
        if kind == "supersession"
        else "candidate -> retracted is legal directly, so a tombstone is one transition",
    }


async def _governed_item_count(url: str) -> int:
    engine = create_postgres_engine(url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as connection:
            return int(
                await connection.scalar(text("SELECT count(*) FROM cognitive_os.memory_items")) or 0
            )
    finally:
        await engine.dispose()


async def crash_mid_ingest(*, items: int, start: int, kill_after: int) -> dict:
    """Kill the database mid-ingest, once, on purpose, and ask what survived.

    **The writer is not what gets killed — the database is.** Killing the client would test
    whether a Python process can be restarted, which nobody doubts. `docker kill` sends SIGKILL
    to PostgreSQL, so the server dies without a checkpoint and comes back through crash
    recovery, which is the failure a scale sprint owes a measurement of.

    What is checked afterwards is deliberately narrow and deliberately unflattering:

    *Did any item lose its revision?* Both are written in one transaction, so this must be zero
    and the check exists to prove the transaction is real rather than assumed.

    *Did any item lose its event?* This one is **not** guaranteed by construction.
    `MemoryService.create` commits the record and then appends the event in a *separate*
    transaction, so a crash in the window between them leaves a governed item with no
    `memory.item_created` event. The driver counts them instead of hoping.

    *Can the ingest resume?* The same range is re-run afterwards. The idempotency key makes a
    re-created item return the existing one, so a resumed range must not duplicate anything.
    """
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    container = os.environ.get("COGOS_POSTGRES_TOOL_CONTAINER")
    if not url or not container:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL and COGOS_POSTGRES_TOOL_CONTAINER are required")
    psql_url = url.replace("postgresql+asyncpg", "postgresql")

    before = await _governed_item_count(url)
    writer = subprocess.Popen(  # fixed argv, no shell
        [
            sys.executable,
            str(REPO / "scripts/scale_22b.py"),
            "--ingest",
            "--ingest-items",
            str(items),
            "--ingest-start",
            str(start),
        ],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    killed_at_count: int | None = None
    kill_started = perf_counter()
    try:
        while perf_counter() - kill_started < 300:
            written = await _governed_item_count(url) - before
            if written >= kill_after:
                killed_at_count = written
                break
            if writer.poll() is not None:
                break
        if killed_at_count is None:
            writer.kill()
            raise SystemExit(
                "the ingest never reached the kill threshold; the crash was not taken and "
                "nothing here would be a recovery measurement"
            )
        subprocess.run(["docker", "kill", container], check=True, capture_output=True)
        killed_wall = perf_counter()
        writer_stdout, writer_stderr = writer.communicate(timeout=120)
    finally:
        if writer.poll() is None:
            writer.kill()

    # `check=False`, and the readiness poll below is what actually decides. The compose service
    # declares `restart: unless-stopped`, so Docker has usually restarted the container before
    # this line runs — which is not a flaw in the test but the thing being tested: a deployed
    # operator gets exactly that policy, and the recovery time measured here includes it.
    subprocess.run(["docker", "start", container], check=False, capture_output=True)
    ready = False
    while perf_counter() - killed_wall < 180:
        probe = subprocess.run(  # fixed argv, no shell
            ["psql", psql_url, "-Atqc", "SELECT 1"], capture_output=True, text=True, check=False
        )
        if probe.returncode == 0 and probe.stdout.strip() == "1":
            ready = True
            break
    if not ready:
        raise SystemExit(f"{container} did not come back within 180s of being killed")
    recovery_seconds = perf_counter() - killed_wall

    engine = create_postgres_engine(url, pool_size=2, max_overflow=0)
    try:
        async with engine.connect() as connection:
            after = int(
                await connection.scalar(text("SELECT count(*) FROM cognitive_os.memory_items")) or 0
            )
            orphan_items = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.memory_items i "
                        "LEFT JOIN cognitive_os.memory_revisions r "
                        "ON r.memory_id = i.memory_id AND r.revision = i.current_revision "
                        "WHERE r.memory_id IS NULL"
                    )
                )
                or 0
            )
            eventless_items = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.memory_items i "
                        "WHERE NOT EXISTS (SELECT 1 FROM cognitive_os.events e "
                        "WHERE e.stream_id = i.memory_id)"
                    )
                )
                or 0
            )
    finally:
        await engine.dispose()

    resumed = await _ingest(items, start)
    resumed_count = await _governed_item_count(url)

    return {
        "what_was_killed": f"the PostgreSQL container {container}, with SIGKILL, mid-ingest",
        "why_the_database_and_not_the_writer": (
            "killing the client tests whether a process can be restarted; killing the server "
            "without a checkpoint tests crash recovery, which is what W3 owes"
        ),
        "items_before": before,
        "items_written_before_the_kill": killed_at_count,
        "items_after_recovery": after,
        "writer_exit_code": writer.returncode,
        "writer_stderr_tail": (writer_stderr or "").strip().splitlines()[-3:],
        "writer_stdout_bytes": len(writer_stdout or ""),
        "database_recovered": True,
        "recovery_seconds": round(recovery_seconds, 3),
        "items_missing_their_current_revision": orphan_items,
        "items_missing_an_event": eventless_items,
        "resumed_items": resumed["items"],
        "items_after_resume": resumed_count,
        # The resume re-runs the whole range, so the store must end at exactly what a clean run
        # would have produced: the idempotency key turns every re-created item into a lookup,
        # and any other outcome is a duplicate this check exists to catch.
        "resume_duplicated_nothing": resumed_count == before + items,
        "expected_items_after_resume": before + items,
        "reads_an_exit_criterion": False,
        "why_no_exit": (
            "no exit criterion reads a crash. This measures what the governed write path leaves "
            "behind when the server dies mid-run, so the restore checklist is verified against a "
            "store that has actually survived one"
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


#: Where the graph half's candidates come from. Deliberately **not** part of RECIPES, on the
#: same reasoning as `LIVE_LEARNED_ARTIFACT_SOURCE`: §2.2d freezes the bounded *configuration*,
#: and which released graph set the pairs are read out of is an operational pointer, not a
#: reading. Widening a frozen contract to carry one would move the recipes hash for no reading
#: at all.
#:
#: It is the D1 set on purpose. 1 788.9 ms is the only graph-arm latency this programme has ever
#: measured, and 500 ms is a claim about the same arm; measuring a different pair corpus would
#: leave the comparison to prose. §2.3 forbids 22B authoring a corpus, so the graphs are the
#: released ones and the scale enters through the shortlist, which is exactly where §2.2d puts
#: it: "ANN shortlist first, budgeted graph expansion second".
BOUNDED_GRAPH_POOL = {
    "root": "docs/sprints/sprint-21/evidence/sprint-21d1-emg-root.json",
    "artifact_root": str(DATA_ROOT / "artifacts-s21d1"),
    "graph_set_id": "sprint-21d1-emg-root",
    "pairs": 80,
    "arm_source": "cognitive_os.experience.graph_retrieval.bounded_ged, released",
}


def _graph_pool() -> tuple[Any, Any]:
    """The released D1 pair corpus and its candidates, or a refusal.

    `load_evidence` resolves every pair's bytes out of the artifact store and reports what it
    could not resolve. A pool that is not intact is refused rather than measured short: a graph
    p95 over a silently smaller pool is a faster number about a different arm.
    """
    from cognitive_os.experience import graph_retrieval
    from cognitive_os.experience.graph_store import load_evidence

    evidence = load_evidence(
        REPO / BOUNDED_GRAPH_POOL["root"], Path(BOUNDED_GRAPH_POOL["artifact_root"])
    )
    if not evidence.intact or len(evidence.pairs) != BOUNDED_GRAPH_POOL["pairs"]:
        raise SystemExit(
            f"the D1 graph set resolved {len(evidence.pairs)} of "
            f"{BOUNDED_GRAPH_POOL['pairs']} pairs (intact={evidence.intact})"
        )
    return evidence.pairs, graph_retrieval.candidates_from(evidence.pairs)


def _graph_embedder(model: Path) -> Any:
    """The frozen local MiniLM, or a refusal — never the hashing provider.

    `build_embedding_provider` is the released factory whose one rule is that it raises rather
    than substituting. Reached through it rather than around it, because a graph number
    produced by a hashing vector would carry the model's name over an arm that never ran.
    """
    from cognitive_os.config.memory_config import EmbeddingProviderConfiguration
    from cognitive_os.infrastructure.embeddings import build_embedding_provider, minilm

    manifest = minilm.read_manifest(model)
    if manifest is None:
        raise SystemExit(f"no usable local embedding model at {model}")
    provider = build_embedding_provider(
        EmbeddingProviderConfiguration(
            provider_type="sentence_transformers",
            model_id=minilm.MODEL_ID,
            dimension=minilm.DIMENSION,
            local_model_path=model,
            local_model_digest=manifest["tree_digest"],
        )
    )
    return provider, str(manifest["tree_digest"])


async def bounded_graph_probes(
    engine: Any,
    dataset: str,
    *,
    probes: int,
    warmup: int,
    model: Path,
    ef_search: int = 1_000,
) -> dict:
    """The §2.2d shape end to end: an ANN shortlist at 10^6, then the released bounded GED arm.

    **What the two legs are.** The shortlist is a real ANN query against this dataset's
    million-row corpus, cut to the frozen `vector_shortlist` of 20 — that is where the scale
    enters. The expansion is `graph_retrieval.bounded_ged` under the frozen limits, over the
    pairs those twenty rows name. The exit reads the sum, because the sum is the shape.

    **The join between them is synthetic, and the record says so.** 22B authors no experience
    corpus (§2.3), so a corpus row is associated with a released D1 pair by `row_id % 80`. The
    association is deterministic and carries no information about either side, which is what
    makes it honest: it decides *which* twenty graphs get expanded, never how good they are.
    The number this produces is therefore a latency measurement and never a quality one, and no
    22B exit reads graph quality — D1's usefulness floor is Gate D1's, still open, untouched.

    **Cutoffs are reported beside the p95**, as `BOUNDED_GRAPH_READING.the_cutoff_trap`
    requires: a budget cutoff returns a shorter list faster, so a recipe that cuts off more
    looks quicker while answering less, and a p95 met with a rising cutoff count is a miss.
    """
    from cognitive_os.domain.experience_graph import ExperienceGraphQuery
    from cognitive_os.experience import graph_retrieval

    pairs, candidates = _graph_pool()
    embed, model_digest = _graph_embedder(model)
    by_pair_id = {pair.pair_id: pair for pair in pairs}
    shortlist_width = int(BOUNDED_GRAPH_LIMITS.vector_shortlist)
    dimension = int(DATASETS[dataset]["dimension"])
    literals = probe_literals(dataset, warmup + probes + 1)
    token = run_token()
    # The pool's texts are embedded once and shared, exactly as the released benchmark does it:
    # S21D3 measured re-embedding the pool per query as ~936 ms of the arm's 940 ms median, so a
    # per-query re-embed would measure the cache's absence rather than the arm. The warmup
    # probes fill it, which is part of what "warm" means for this shape.
    cache: dict[str, tuple[float, ...]] = {}

    totals: list[float] = []
    shortlists: list[float] = []
    expansions: list[float] = []
    cold: dict[str, float] | None = None
    cutoffs = timeouts = returned = 0
    pool_sizes: set[int] = set()

    async with engine.connect() as connection:
        for index, literal in enumerate(literals):
            started = perf_counter()
            await connection.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))
            rows = tuple(
                (
                    await connection.execute(
                        text(
                            f"SELECT row_id FROM cognitive_os.{corpus_table(dataset)} "
                            f"WHERE dimension = {dimension} "
                            f"ORDER BY (embedding::vector({dimension})) <=> '{literal}'::vector "
                            f"LIMIT {shortlist_width}"
                        )
                    )
                ).scalars()
            )
            shortlist_ms = (perf_counter() - started) * 1_000

            shortlisted = list(dict.fromkeys(pairs[row_id % len(pairs)].pair_id for row_id in rows))
            head = by_pair_id[shortlisted[0]]
            query = ExperienceGraphQuery(
                query_id=f"sprint-22b-graph:{dataset}:{index}:{token}",
                query_text=head.failed.search_text(),
                domain=head.domain,
                task_signature=head.task_signature,
                excluded_groups=(head.group,),
            )
            # Group exclusion before the arm, never inside it — the released pool discipline.
            # The query's own pair leaves the pool, which is why a shortlist of twenty expands
            # nineteen or fewer and why the record reports the sizes it actually saw.
            pool = graph_retrieval.eligible_pool(
                tuple(c for c in candidates if c.pair_id in set(shortlisted)), query
            )
            pool_sizes.add(len(pool))
            expansion_started = perf_counter()
            result = await graph_retrieval.bounded_ged(
                query,
                pool,
                head.failed,
                limits=BOUNDED_GRAPH_LIMITS,
                embed=embed,
                cache=cache,
            )
            expansion_ms = (perf_counter() - expansion_started) * 1_000
            total_ms = (perf_counter() - started) * 1_000

            if index == 0:
                cold = {
                    "total_ms": round(total_ms, 3),
                    "ann_shortlist_ms": round(shortlist_ms, 3),
                    "graph_expansion_ms": round(expansion_ms, 3),
                }
                continue
            if index <= warmup:
                continue
            totals.append(total_ms)
            shortlists.append(shortlist_ms)
            expansions.append(expansion_ms)
            cutoffs += result.budget_cutoffs
            timeouts += result.timed_out
            returned += len(result.entries)

    percentiles = _percentiles(totals)
    return {
        "dataset": dataset,
        "shape": "bounded_graph_assisted",
        "arm": graph_retrieval.BOUNDED_GED,
        "configuration": bounded_graph_configuration(),
        "pool": {
            **BOUNDED_GRAPH_POOL,
            "shortlist_width": shortlist_width,
            "expanded_pool_sizes": sorted(pool_sizes),
            "join": "row_id % 80, deterministic and information-free",
        },
        "embedding_model_digest": model_digest,
        "embedding_cache_shared_across_probes": True,
        "cold_first_probe": cold,
        "warmup_probes_discarded": warmup,
        **percentiles,
        "ann_shortlist_leg": _percentiles(shortlists),
        "graph_expansion_leg": _percentiles(expansions),
        "budget_cutoffs": cutoffs,
        "per_pair_timeouts": timeouts,
        "mean_results_returned": round(returned / len(totals), 3) if totals else None,
        "reads_an_exit": "p95 <= 500 ms",
        "exit_threshold_ms": BOUNDED_GRAPH_READING["exit_ms"],
        "meets_exit": percentiles["p95_ms"] <= float(BOUNDED_GRAPH_READING["exit_ms"]),
        "prior_measurement_ms": BOUNDED_GRAPH_READING["only_prior_measurement_ms"],
        "limitation": (
            "the graph half expands the released D1 pairs, joined to this corpus by row_id % "
            "80: §2.3 forbids 22B authoring a corpus, so the 10^6 scale enters through the ANN "
            "shortlist leg and the expansion leg's cost is a property of the released 80-pair "
            "set. A latency measurement of the released arm, never a quality one"
        ),
        "measures_quality": False,
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
    engine: Any,
    index: str,
    *,
    readers: int,
    seconds: float,
    table: str = CORPUS_TABLE,
    dataset: str | None = None,
) -> dict:
    """Reindex concurrently while readers probe, and measure what the readers saw.

    A reindex that is only timed proves the reindex finished. §3's W3 asks what concurrent
    reads did *during* it, so the readers are measured and their latencies reported beside the
    reindex duration.

    **W3-F2: the readers have to read through the index being rebuilt.** They used to run
    `SELECT count(*) ... WHERE scope_id = :s`, which is a reader in the sense that it reads —
    and useless here, because a counting scan never touches the HNSW graph and so cannot show
    whether approximate retrieval survives its own index being rebuilt. Measured that way the
    first time, 408 065 reader queries came back at a p95 of 52.3 ms and answered a question
    nobody asked. When `dataset` is given the readers now run the ANN probe the index exists to
    serve, and the record says which reader produced the numbers.

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
    dimension = int(DATASETS[dataset]["dimension"]) if dataset else None
    # Drawn once, outside the loop: a probe drawn per iteration would put the generator's cost
    # inside the latency the readers are supposed to be reporting.
    probes = probe_literals(dataset, 64) if dataset else []
    reader_query = (
        f"ANN top-10 through {index}, ef_search 1000 — the shape the index exists to serve"
        if dataset
        else f"SELECT count(*) FROM {table} WHERE scope_id = :s — a scan that never touches "
        "the index being rebuilt (W3-F2)"
    )

    async def reader(worker: int) -> list[float]:
        latencies: list[float] = []
        async with engine.connect() as connection:
            await connection.execution_options(isolation_level="AUTOCOMMIT")
            probe_index = worker
            while not stop.is_set():
                started = perf_counter()
                if dataset:
                    await connection.execute(text("SET hnsw.ef_search = 1000"))
                    await connection.execute(
                        text(
                            f"SELECT row_id FROM cognitive_os.{table} "
                            f"WHERE dimension = {dimension} ORDER BY "
                            f"(embedding::vector({dimension})) <=> "
                            f"'{probes[probe_index % len(probes)]}'::vector LIMIT 10"
                        )
                    )
                    probe_index += 1
                else:
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
        "reader_query": reader_query,
        "readers_read_through_the_index": dataset is not None,
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


#: The seven shapes in the order W2 measures them. §3.2: "Schedule it first inside W2, because
#: if it misses, the remaining waves proceed unchanged toward an honest partial."
ENVELOPE_ORDER = (
    "bounded_graph_assisted",
    "ann",
    "filtered_ann",
    "exact_vector",
    "hybrid",
    "temporal",
    "stale_item",
)

CORPUS_SHAPES = ("exact_vector", "ann", "filtered_ann")
GOVERNED_SHAPES = ("hybrid", "temporal", "stale_item")


async def _database_name(engine: Any) -> str:
    """Which store this record is about.

    W4 re-measures the whole envelope against the *restored* database to find out whether a
    restore changes it. Both runs use the same drivers, the same recipes and the same host, so
    without this field the two records differ only in their numbers — and a reader comparing
    them would have to take on trust which one came from where. The driver asks the server.
    """
    async with engine.connect() as connection:
        return str(await connection.scalar(text("SELECT current_database()")) or "")


async def server_memory_reading(engine: Any, dataset: str) -> dict:
    """What this host can hold, beside what it is being asked to hold.

    Every latency in this envelope is a claim about the declared reference host (§1.4), and the
    part of that host which decides an ANN latency is not the disk — it is how much of a
    3.8 GiB index the server can keep resident. The reference host runs the released compose
    file's PostgreSQL defaults, so `shared_buffers` is 128 MB against an index thirty times
    that. This block is that arithmetic, sealed beside the numbers it explains.

    It is a *reading*, not a knob 22B turns. Raising `shared_buffers` after a latency exists
    would be tuning a configuration against an exit, which §2.3's last bullet forbids by name,
    and the host record seals PostgreSQL's settings precisely so that a quiet change to them
    cannot pass as the same host.
    """
    index = f"{corpus_table(dataset)}_hnsw_{int(DATASETS[dataset]['dimension'])}"
    async with engine.connect() as connection:
        # W2-F1: this rendered `setting + unit` with no separator, and PostgreSQL's unit for
        # `shared_buffers` is itself "8kB" — so 16384 blocks of 8 kB came out as the string
        # "163848kB", a number that reads as 160 MB, is actually 128 MB, and is wrong either
        # way. A settings block whose whole job is to state a constraint has to state it in
        # units a reader can check, so the separator is explicit and the bytes are computed
        # below rather than parsed back out of this string.
        settings = {
            name: f"{setting} {unit}" if unit else str(setting)
            for name, setting, unit in (
                await connection.execute(
                    text(
                        "SELECT name, setting, unit FROM pg_settings WHERE name IN "
                        "('shared_buffers','effective_cache_size','work_mem',"
                        "'maintenance_work_mem','max_parallel_workers',"
                        "'max_parallel_workers_per_gather','random_page_cost')"
                    )
                )
            ).all()
        }
        shared_buffers_bytes = int(
            await connection.scalar(
                text("SELECT setting::bigint * 8192 FROM pg_settings WHERE name='shared_buffers'")
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
        table_bytes = int(
            await connection.scalar(
                text("SELECT pg_total_relation_size(CAST(:name AS regclass))"),
                {"name": f"cognitive_os.{corpus_table(dataset)}"},
            )
            or 0
        )
    memory = {
        key: int(value.split()[0])
        for key, _, value in (
            line.partition(":") for line in Path("/proc/meminfo").read_text().splitlines()
        )
        if key in {"MemTotal", "MemAvailable"}
    }
    return {
        "settings": settings,
        "shared_buffers_bytes": shared_buffers_bytes,
        "index_bytes": index_bytes,
        "table_total_bytes": table_bytes,
        "index_over_shared_buffers": (
            round(index_bytes / shared_buffers_bytes, 1) if shared_buffers_bytes else None
        ),
        "host_memory_total_kib": memory.get("MemTotal"),
        "host_memory_available_kib": memory.get("MemAvailable"),
        "index_fits_in_host_memory": index_bytes < int(memory.get("MemTotal", 0)) * 1024,
        "reading": (
            "the index does not fit in the server's buffer pool and does fit in host memory, so "
            "a warm number here is served by the Linux page cache rather than by shared_buffers"
        ),
        "not_tuned_by_22b": True,
        "why_not_tuned": (
            "§2.3 forbids tuning a pre-registered configuration after its first measured number "
            "exists, and the sealed host record makes a PostgreSQL settings change a host "
            "supersession rather than an adjustment"
        ),
    }


async def _envelope(
    dataset: str, *, shapes: tuple[str, ...], probes: int, warmup: int, model: Path | None
) -> dict:
    """One restart, then the named shapes over one dataset, at the pre-registered probe counts.

    The restart is per invocation and not per shape: §2.2b defines warm as "index built,
    PostgreSQL restarted, then 100 discarded warmup probes, then the measured probes", and each
    shape runs its own warmup after the restart. Restarting between shapes would also be
    defensible; restarting *never* would not, which is the one thing this refuses to do.
    """
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    unknown = tuple(shape for shape in shapes if shape not in QUERY_SHAPES)
    if unknown:
        raise SystemExit(f"not a pre-registered shape: {', '.join(unknown)}")
    if "bounded_graph_assisted" in shapes and model is None:
        raise SystemExit("--model is required for the bounded graph-assisted shape")

    restart = restart_postgres()
    engine = create_postgres_engine(url, pool_size=2, max_overflow=0, command_timeout_seconds=7_200)
    measured: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {}
    try:
        database = await _database_name(engine)
        memory = await server_memory_reading(engine, dataset)
        for shape in ENVELOPE_ORDER:
            if shape not in shapes:
                continue
            if shape in CORPUS_SHAPES:
                measured[shape] = await probe_corpus(
                    engine, dataset, shape=shape, probes=probes, warmup=warmup
                )
                if shape == "filtered_ann":
                    # W2-F2. Beside the pre-registered number, never instead of it.
                    diagnostics["filtered_ann_index_forced"] = await probe_corpus(
                        engine,
                        dataset,
                        shape=shape,
                        probes=probes,
                        warmup=warmup,
                        force_index=True,
                    )
            elif shape in GOVERNED_SHAPES:
                measured[shape] = await governed_probe_series(
                    engine, shape, probes=probes, warmup=warmup, dataset=dataset
                )
            else:
                assert model is not None
                measured[shape] = await bounded_graph_probes(
                    engine, dataset, probes=probes, warmup=warmup, model=model
                )
    finally:
        await engine.dispose()

    return {
        "dataset": dataset,
        "database": database,
        "corpus_rows": 1_000_000,
        "protocol": PROBE_PROTOCOL,
        "restart": restart,
        "server_memory": memory,
        "shapes_measured": sorted(measured),
        "shapes_measured_count": len(measured),
        "shapes_in_the_pre_registration": sorted(QUERY_SHAPES),
        "measured": measured,
        "diagnostics": diagnostics,
        "diagnostics_read_no_exit": True,
        "probes_per_shape": probes,
        "warmup_per_shape": warmup,
        "recipes_hash": recipes_hash(),
    }


async def _mutate(supersessions: int, tombstones: int, start: int) -> dict:
    """W3's mutation waves, with the active view queried before and after each one.

    The two waves address disjoint ranges of the governed store on purpose. A tombstone wave
    that overlapped the supersession wave would meet items whose status had already moved, and
    the refusals would be the released transition table doing its job — a correct outcome that
    tells nobody anything about mutation at scale.

    Neither wave touches a corpus table. W1-F6's lesson, applied before rather than after: the
    clustered corpus is what the recall exit reads, and a wave that mutates what an exit reads
    invalidates the exit rather than measuring anything.
    """
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    engine = create_postgres_engine(url, pool_size=2, max_overflow=0, command_timeout_seconds=3_600)
    try:
        before = await active_view(engine)
        supersession = await mutation_wave(engine, "supersession", count=supersessions, start=start)
        after_supersessions = await active_view(engine)
        tombstone = await mutation_wave(
            engine, "tombstone", count=tombstones, start=start + supersessions
        )
        after_tombstones = await active_view(engine)
    finally:
        await engine.dispose()

    expected = (
        before["active_rows_by_item_status"]
        - supersession["items_mutated"]
        - tombstone["items_mutated"]
    )
    return {
        "waves": [supersession, tombstone],
        "active_view": {
            "before": before,
            "after_supersessions": after_supersessions,
            "after_tombstones": after_tombstones,
        },
        "expected_active_rows_after": expected,
        "active_rows_after": after_tombstones["active_rows_by_item_status"],
        "active_view_matches_the_mutations": (
            after_tombstones["active_rows_by_item_status"] == expected
        ),
        "both_readings_agree_throughout": all(
            view["the_two_readings_agree"]
            for view in (before, after_supersessions, after_tombstones)
        ),
        "corpus_tables_untouched": True,
        "recipes_hash": recipes_hash(),
    }


async def _crash(items: int, start: int, kill_after: int) -> dict:
    record = await crash_mid_ingest(items=items, start=start, kill_after=kill_after)
    record["recipes_hash"] = recipes_hash()
    return record


async def _bloat_reindex(dataset: str, readers: int, seconds: float, mutate: int = 0) -> dict:
    """Bloat measured exactly, then a reindex with concurrent readers measured throughout.

    The corpus this runs against is **uniform** by default — the dataset no exit criterion
    reads. A `REINDEX` rebuilds the HNSW graph, and rebuilding the index the recall exit was
    measured over would replace the measured object with a differently-built one. That is
    W1-F6's rule stated ahead of the mistake rather than after it.

    The governed tables are measured too, because that is where W3's ten thousand transitions
    actually left dead tuples: an append-only revision table grows, and the item table is
    updated in place once per transition.
    """
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    engine = create_postgres_engine(
        url, pool_size=8, max_overflow=0, command_timeout_seconds=21_600
    )
    table = corpus_table(dataset)
    index = f"{table}_hnsw_{int(DATASETS[dataset]['dimension'])}"
    try:
        # W3-F3: bloat has to be measured while it exists. The first run measured the governed
        # tables ninety minutes after the mutation waves — long enough for autovacuum to have
        # cleaned every dead tuple — and reported 0.00% everywhere, which is a true statement
        # about a vacuumed store and no statement at all about mutation at scale. When `mutate`
        # is given, a wave runs here and the very next thing that happens is the measurement.
        mutation = (
            await mutation_wave(engine, "supersession", count=mutate, start=11_000)
            if mutate
            else None
        )
        governed_before = {
            name: await table_bloat(engine, name)
            for name in ("memory_items", "memory_revisions", "memory_sources")
        }
        corpus_before = await table_bloat(engine, table)
        reindex = await reindex_with_readers(
            engine, index, readers=readers, seconds=seconds, table=table, dataset=dataset
        )
        corpus_after = await table_bloat(engine, table)
        async with engine.connect() as connection:
            await connection.execution_options(isolation_level="AUTOCOMMIT")
            await connection.execute(text("VACUUM ANALYZE cognitive_os.memory_items"))
        governed_after = {
            name: await table_bloat(engine, name)
            for name in ("memory_items", "memory_revisions", "memory_sources")
        }
    finally:
        await engine.dispose()
    return {
        "dataset": dataset,
        "reads_an_exit_criterion": False,
        "why_this_dataset": (
            "uniform reads no exit criterion, and a reindex rebuilds the HNSW graph the "
            "clustered recall number was measured over"
        ),
        "mutation_wave_immediately_before": mutation,
        "bloat_measured_before_autovacuum_could_run": mutate > 0,
        "governed_tables_before": governed_before,
        "governed_tables_after_vacuum": governed_after,
        "corpus_before": corpus_before,
        "corpus_after": corpus_after,
        "reindex_with_readers": reindex,
        "recipes_hash": recipes_hash(),
    }


async def _recall(dataset: str, probes: int) -> dict:
    """The recall exit's own run: an exact scan per probe, never sampled (§4).

    Separate from `--envelope` because it is the sprint's most expensive measurement and the one
    a rerun must be able to reach without re-measuring six shapes to get to it.
    """
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    engine = create_postgres_engine(url, pool_size=2, max_overflow=0, command_timeout_seconds=7_200)
    started = perf_counter()
    try:
        database = await _database_name(engine)
        record = await recall_at(engine, dataset, probes=probes)
        record["database"] = database
    finally:
        await engine.dispose()
    threshold = 0.95
    record["threshold"] = threshold
    record["meets_exit"] = (
        bool(DATASETS[dataset]["reads_the_recall_exit"])
        and record["recall_at_k"] is not None
        and record["recall_at_k"] >= threshold
    )
    record["seconds"] = round(perf_counter() - started, 3)
    record["recipes_hash"] = recipes_hash()
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipes", action="store_true", help="print the frozen recipes")
    parser.add_argument("--slice", action="store_true", help="run every driver at fixture scale")
    parser.add_argument("--corpus", action="store_true", help="build one dataset at full scale")
    parser.add_argument("--ingest", action="store_true", help="the governed-ingest exit run")
    parser.add_argument("--incremental", action="store_true", help="insert into the built index")
    parser.add_argument("--restore-corpus", action="store_true", help="W1-F6 repair")
    parser.add_argument("--restore-check", action="store_true", help="the §2.2e checklist")
    parser.add_argument("--mutate", action="store_true", help="the W3 supersession/tombstone waves")
    parser.add_argument("--crash", action="store_true", help="kill the database mid-ingest, once")
    parser.add_argument(
        "--bloat-reindex", action="store_true", help="bloat, then reindex under load"
    )
    parser.add_argument("--supersessions", type=int, default=5_000)
    parser.add_argument("--tombstones", type=int, default=5_000)
    parser.add_argument("--mutate-start", type=int, default=1_000)
    parser.add_argument("--crash-items", type=int, default=5_000)
    parser.add_argument("--crash-start", type=int, default=60_000)
    parser.add_argument("--crash-after", type=int, default=500)
    parser.add_argument("--readers", type=int, default=3)
    parser.add_argument(
        "--mutate-before-bloat",
        type=int,
        default=0,
        help="run a supersession wave immediately before measuring bloat (W3-F3)",
    )
    parser.add_argument("--reader-seconds", type=float, default=5.0)
    parser.add_argument("--envelope", action="store_true", help="the W2 retrieval envelope")
    parser.add_argument("--recall", action="store_true", help="recall@10 against an exact scan")
    parser.add_argument(
        "--shape",
        action="append",
        choices=sorted(QUERY_SHAPES),
        help="restrict --envelope to one shape; repeatable, defaults to all seven",
    )
    parser.add_argument("--probes", type=int, default=PROBE_PROTOCOL["measured_probes"])
    parser.add_argument("--warmup", type=int, default=PROBE_PROTOCOL["warmup_probes"])
    parser.add_argument("--model", type=Path, help="the frozen local MiniLM the graph arm needs")
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
    elif arguments.mutate:
        payload = asyncio.run(
            _mutate(arguments.supersessions, arguments.tombstones, arguments.mutate_start)
        )
    elif arguments.crash:
        payload = asyncio.run(
            _crash(arguments.crash_items, arguments.crash_start, arguments.crash_after)
        )
    elif arguments.bloat_reindex:
        payload = asyncio.run(
            _bloat_reindex(
                arguments.dataset,
                arguments.readers,
                arguments.reader_seconds,
                arguments.mutate_before_bloat,
            )
        )
    elif arguments.envelope:
        payload = asyncio.run(
            _envelope(
                arguments.dataset,
                shapes=tuple(arguments.shape or sorted(QUERY_SHAPES)),
                probes=arguments.probes,
                warmup=arguments.warmup,
                model=arguments.model,
            )
        )
    elif arguments.recall:
        payload = asyncio.run(_recall(arguments.dataset, arguments.probes))
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
        parser.error(
            "choose --recipes, --slice, --corpus, --ingest, --envelope, --recall or --seed-artifact"
        )

    encoded = json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
