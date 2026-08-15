"""S22C-030 through S22C-032. The two repairs 22B handed over by name, before any cycle.

§3 puts both of these in W1 and says why: they are released-behaviour changes, and a cycle
run on the unrepaired system is a cycle measuring a system 22C does not ship. So they land
first, and each is proven against **22B's own reproduction** rather than against a new one
chosen to be easier.

**22B W3-F1 — a governed item outside its own event stream.** `MemoryService.create` wrote
the record in one transaction and appended `memory.item_created` in another, and decided
whether to append by asking whether the memory existed *before* the write. Both halves are
wrong. The window is real — 22B killed the database mid-ingest and one write in 502 came
back with a row and no event — and the pre-check made it permanent, because the resume that
re-runs a crashed range finds the row through its idempotency key, concludes the item is not
new, and never reaches the append. The more often you resume, the more certain the orphan.

The repair asks the stream instead of the record (`MemoryEventService.ensure_item_created`),
so the resume repairs. It does **not** close the window, and this record says so twice: once
in the measurement, where the orphan is still there after recovery, and once in the
limitations. Closing it needs the record and the event in one transaction, which needs a
transactional boundary `MemoryRepositoryPort` and `EventStorePort` do not share and §1.4
froze `0016` as a refusal, so it is named as owed rather than quietly counted as done.

Two proofs, because the crash alone is not one. The crash is a timing race: a re-run that
happens to miss the window would report zero orphans and prove nothing at all, so the
driver reports whether the window opened and refuses to read a run where it did not. The
deterministic proof plants an orphan directly — a record written through the repository with
no event, which is exactly what the crash leaves — and re-runs the create over it.

**22B W4-F1 — the restore that silently loses recall.** `pg_restore` rebuilds HNSW indexes
rather than copying them, and the rebuilt graph read 0.9410 against a 0.95 floor. §1.1 gives
22C the fix and the obligation to prove it on 22B's measurement. The procedure is
pre-registered *before* the first REINDEX (S22C-030), with the mechanism stated as a
hypothesis and its falsifier named, because a procedure chosen after seeing which knob moved
the number is a knob, not a procedure.

    UV_CACHE_DIR=.cache/uv uv run python scripts/repairs_22c.py --pre-register
    UV_CACHE_DIR=.cache/uv uv run python scripts/repairs_22c.py --orphan-repair
    UV_CACHE_DIR=.cache/uv uv run python scripts/repairs_22c.py --crash
    UV_CACHE_DIR=.cache/uv uv run python scripts/repairs_22c.py --reindex
    UV_CACHE_DIR=.cache/uv uv run python scripts/repairs_22c.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import inspect
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy import text

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from scale_22b import (  # noqa: E402
    DATASETS,
    _database_name,
    _governed_item_count,
    _ingest,
    _write_request,
    corpus_table,
    recall_at,
)

from cognitive_os.application.services.memory_service import MemoryService  # noqa: E402
from cognitive_os.domain.memory import (  # noqa: E402
    MemoryScopeType,
    MemorySensitivity,
    MemoryType,
    MemoryWritePolicy,
)
from cognitive_os.events.catalog import build_default_event_catalog  # noqa: E402
from cognitive_os.events.memory_event_service import MemoryEventService  # noqa: E402
from cognitive_os.infrastructure.memory.postgres.repository import (  # noqa: E402
    PostgresMemoryRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402

#: The store 22B restored into and measured 0.9410 on. The procedure is applied to *that*
#: store, so the rows, the probes and the host are the ones the sealed number came from and
#: the only thing that changes between the two readings is the index.
RESTORED_DATABASE = "cognitive_os_s22b_restore_test"

#: 22B's sealed clustered readings, retyped nowhere: `--check` reads them from the records.
SOURCE_RECALL_RECORD = EVIDENCE / "sprint-22b-w2-recall-clustered.json"
RESTORED_RECALL_RECORD = EVIDENCE / "sprint-22b-w4-restored-recall-clustered.json"
CRASH_RECORD = EVIDENCE / "sprint-22b-w3-crash.json"

#: §2.2b's clustered reading, unchanged. Beating a floor by measuring fewer probes, or by
#: sampling the ground truth, is the failure mode the D-series exists to refuse.
RECALL_PROBES = 500
RECALL_K = 10
RECALL_FLOOR = 0.95

#: The ingest range this sprint's crash uses. 22B's own crash ran 5 000 items from 60 000 and
#: killed after 500 writes; the same shape, in 22C's store, which starts empty of them.
CRASH_ITEMS = 5_000
CRASH_START = 60_000
CRASH_KILL_AFTER = 500
#: A crash that misses the window measures nothing, so the driver takes it again. Four is a
#: budget, not a target: the first run to open the window is the one that is read.
CRASH_ATTEMPTS = 4


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _seal(record: dict[str, Any]) -> dict[str, Any]:
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _admin_url() -> str:
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required")
    return url


def _restored_url() -> str:
    """The restored store's URL, derived from the admin URL's server rather than typed."""
    url = _admin_url()
    head, _, _ = url.rpartition("/")
    return f"{head}/{RESTORED_DATABASE}"


# --------------------------------------------------------------------------------------
# S22C-030. The reindex procedure, frozen before the first REINDEX.
# --------------------------------------------------------------------------------------

#: The procedure, as an operator would run it. Pre-registered, hashed, and executed from
#: this same object by `--reindex`, so the record cannot describe one procedure and run
#: another (22B W1-F2: pin the recipe, not the driver's bytes).
#: **Revision 1's hash, kept.** Revision 1 is sealed in `sprint-22c-repair-plan.json` and is
#: not edited: it was the procedure this wave committed to, and it failed. W1-F4 below is
#: what it failed on, and revision 2 supersedes it in a record of its own.
PROCEDURE_REVISION_1_HASH = "f9cc68d5b767a50e1012bee5a198e11947fc04a568d2e41c3f7962e5e066a3b2"

REINDEX_PROCEDURE: dict[str, Any] = {
    "revision": 2,
    "supersedes": {
        "revision": 1,
        "procedure_hash": PROCEDURE_REVISION_1_HASH,
        "sealed_in": "sprint-22c-repair-plan.json",
        "prescribed": "SET max_parallel_maintenance_workers = 4",
        # W1-F4. Recorded in the procedure itself, because a reader deciding whether to trust
        # revision 2 needs to know that revision 1 existed and what happened to it.
        "failed_with": (
            "DiskFullError: could not resize shared memory segment to 12881825280 bytes: No "
            "space left on device — on a host with 821 GB free"
        ),
        "why_it_failed": (
            "a parallel HNSW build puts its shared graph in dynamic shared memory, which "
            "PostgreSQL allocates from /dev/shm. The container gives /dev/shm 2 GB — a limit "
            "22B raised from Docker's 64 MB default in its own W1-F5, sized for the build 22B "
            "ran. Revision 1 raised maintenance_work_mem to 12 GB *and* kept parallel workers, "
            "so it asked a 2 GB filesystem for 12 GB. The two settings are safe apart and "
            "incompatible together, and nothing in either one's documentation says so"
        ),
        "when_it_failed": (
            "after the 40-minute precondition measurement and before any index was touched, "
            "so the restored index was left exactly as 22B sealed it"
        ),
    },
    "applies_to": "any store restored from a pg_dump archive containing HNSW indexes",
    "steps": [
        {
            "order": 1,
            "sql": "SET maintenance_work_mem = '12GB'",
            "why": (
                "the lever §1.1 names. pgvector builds an HNSW graph in memory and falls back "
                "to a two-phase on-disk build the moment the graph outgrows "
                "maintenance_work_mem; the second phase inserts the remaining tuples one at a "
                "time into a graph it can no longer see whole, and the result is a worse graph "
                "with no error and no warning at the SQL level"
            ),
        },
        {
            "order": 2,
            "sql": "SET max_parallel_maintenance_workers = 0",
            "why": (
                "**revision 2.** A serial build takes its memory from the backend's own heap "
                "rather than from dynamic shared memory, so the raised budget is honoured "
                "without touching /dev/shm and the procedure runs on a default container "
                "instead of requiring an infrastructure change. Revision 1 claimed parallel "
                "workers were 'rebuild wall-clock only'; that claim was too confident and is "
                "withdrawn — an HNSW build is order-dependent, and a serial build is a "
                "different graph from a parallel one. What is unchanged is the hypothesis "
                "under test, which is about the memory budget, and the reading, which is "
                "recall over the same probes"
            ),
        },
        {
            "order": 3,
            "sql": "REINDEX INDEX cognitive_os.{index}",
            "why": "rebuild the graph under the raised budget, in place, without dropping it",
        },
        {
            "order": 4,
            "sql": "ANALYZE cognitive_os.{table}",
            "why": "the planner's statistics are rebuilt with the index, never assumed",
        },
    ],
    "hypothesis": (
        "the restored index reads below the floor because it was rebuilt under the server's "
        "default maintenance_work_mem of 64 MB against an index of 3906 MB, so pg_restore's "
        "rebuild took pgvector's two-phase path. The source index was built by the same code "
        "under the same setting, so the two-phase path alone is not the whole story: the "
        "phases split at a different point because pg_restore loads rows in the archive's "
        "order rather than the original insert order, and which tuples land in the in-memory "
        "phase decides the graph both phases inherit"
    ),
    "falsifier": (
        "if the rebuild runs entirely in memory and clustered recall@10 still reads below "
        "0.95, the hypothesis is wrong and this record says so. The fallback below is then "
        "the second lever, reported as its own measurement and never as a replacement"
    ),
    "fallback_if_the_hypothesis_is_wrong": {
        "sql": "SET hnsw.ef_construction = 200",
        "why": (
            "a denser candidate list at build time, the other lever §1.1 names. It is a "
            "fallback and not the first move because it changes the index's parameters, "
            "while raising the memory budget only lets the same parameters be honoured"
        ),
    },
    "success_reads": (
        f"clustered recall@{RECALL_K} over {RECALL_PROBES} probes, exact-scan ground truth "
        f"per probe, hnsw.ef_search = 1000, at or above {RECALL_FLOOR}"
    ),
    "precondition": (
        "before the index is touched, the restored store is re-measured unchanged and must "
        "reproduce 22B's sealed 0.9410 exactly. The reading is deterministic given the same "
        "index and the same probe seed, so any other value means the store or the reading "
        "moved since 22B sealed it, and the comparison this repair rests on is void"
    ),
    "what_this_does_not_claim": (
        "that the repaired index is the one 22B built at the source. It is not: it is a third "
        "graph, built under a budget neither earlier build had. The claim is only that a "
        "restored store can be returned above the floor by a procedure fixed in advance"
    ),
}


def procedure_hash() -> str:
    return _sha256(_canonical(REINDEX_PROCEDURE))


#: The repair to the governed write path, hashed from the code that implements it rather
#: than described. If `ensure_item_created` changes, this record stops reproducing.
def repair_source_hash() -> str:
    return _sha256(
        inspect.getsource(MemoryEventService.ensure_item_created).encode("utf-8")
        + inspect.getsource(MemoryService.create).encode("utf-8")
    )


def _pre_registration() -> dict[str, Any]:
    restored = _load(RESTORED_RECALL_RECORD)
    source = _load(SOURCE_RECALL_RECORD)
    crash = _load(CRASH_RECORD)
    return _seal(
        {
            "schema_version": 1,
            "sprint": "22C",
            "wave": "W1",
            "items": ["S22C-030"],
            "recorded_at": _now(),
            "revision": 2,
            # Accurate for *this* revision, not inherited from revision 1. Revision 1 was
            # frozen before both measurements; revision 2 was sealed after the crash
            # reproduction had already run under revision 1 and after revision 1's rebuild
            # failed without touching an index. Saying "before the crash reproduction" here
            # would be a claim about the wrong revision.
            "frozen_before": (
                "the first REINDEX to touch an index. Revision 1's never ran, so no index "
                "has been rebuilt under any revision of this procedure at the moment this "
                "record is sealed"
            ),
            "frozen_after": (
                "the crash reproduction, which ran under revision 1 and is unaffected by "
                "this amendment: the two repairs share a pre-registration record and nothing "
                "else"
            ),
            "supersedes": REINDEX_PROCEDURE["supersedes"],
            "why_a_second_revision": (
                "revision 1's procedure could not be executed on this host and never touched "
                "an index (W1-F4). Revision 1 stays sealed in sprint-22c-repair-plan.json "
                "exactly as it was published: a pre-registration that is edited after it "
                "fails is not a pre-registration. This is the revision the measurement runs "
                "under, it names revision 1 by hash, and both are in the evidence index"
            ),
            "w4_f1": {
                "inherited_from": "22B W4-F1",
                "sealed_source_recall": source["recall_at_k"],
                "sealed_restored_recall": restored["recall_at_k"],
                "floor": RECALL_FLOOR,
                "store": RESTORED_DATABASE,
                "procedure": REINDEX_PROCEDURE,
                "procedure_hash": procedure_hash(),
                "reading": {
                    "probes": RECALL_PROBES,
                    "k": RECALL_K,
                    "ground_truth": "exact scan per probe, never sampled",
                    "driver": "scale_22b.recall_at, imported and not reimplemented",
                    "probe_seed": DATASETS["clustered"]["probe_seed"],
                },
            },
            "w3_f1": {
                "inherited_from": "22B W3-F1",
                "sealed_orphans_after_the_crash": crash["items_missing_an_event"],
                "sealed_writes_before_the_kill": crash["items_written_before_the_kill"],
                "repair": (
                    "MemoryEventService.ensure_item_created — the create asks the event "
                    "stream whether the record has its creation event, instead of asking the "
                    "repository whether the record existed a moment ago"
                ),
                "repair_source_hash": repair_source_hash(),
                "reads": (
                    "items_missing_an_event, counted twice: after crash recovery, where the "
                    "window is expected to still be open, and after the resume, where the "
                    "repair must have closed every orphan the run produced"
                ),
                "a_run_that_proves_nothing": (
                    "a crash that lands outside the window leaves zero orphans after "
                    "recovery. Such a run satisfies 'zero after the resume' without the "
                    "repair having run at all, so the driver records window_opened and the "
                    "reading is refused when it is false"
                ),
                "crash_attempts_budget": CRASH_ATTEMPTS,
            },
            "amendments_made_by_22c": 0,
        }
    )


# --------------------------------------------------------------------------------------
# S22C-031. The repaired write path, proved deterministically and then under a real crash.
# --------------------------------------------------------------------------------------


def _service(engine: Any) -> MemoryService:
    """The governed path exactly as `scale_22b.governed_ingest` composes it."""
    return MemoryService(
        PostgresMemoryRepository(engine),
        MemoryWritePolicy(
            allowed_types=frozenset(MemoryType),
            allowed_scopes=frozenset(MemoryScopeType),
            maximum_sensitivity=MemorySensitivity.INTERNAL,
        ),
        event_service=MemoryEventService(PostgresEventStore(engine, build_default_event_catalog())),
    )


async def _creation_events(engine: Any, memory_id: Any) -> int:
    async with engine.connect() as connection:
        return int(
            await connection.scalar(
                text(
                    "SELECT count(*) FROM cognitive_os.events "
                    "WHERE stream_id = :sid AND event_type = 'memory.item_created'"
                ),
                {"sid": memory_id},
            )
            or 0
        )


async def _eventless_items(engine: Any) -> int:
    """22B's own query, unchanged: a governed item with nothing in its stream."""
    async with engine.connect() as connection:
        return int(
            await connection.scalar(
                text(
                    "SELECT count(*) FROM cognitive_os.memory_items i "
                    "WHERE NOT EXISTS (SELECT 1 FROM cognitive_os.events e "
                    "WHERE e.stream_id = i.memory_id)"
                )
            )
            or 0
        )


async def orphan_repair() -> dict[str, Any]:
    """Plant the orphan the crash leaves, then run the resume over it.

    The crash cannot be asked to happen on demand, so the state it produces is written
    directly: `PostgresMemoryRepository.create_memory` commits the record and knows nothing
    about events, which is precisely the state a process killed one statement later leaves
    behind. Then the governed create runs over the same request, as a resume does.

    The counterfactual is stated rather than re-executed: under the released code this call
    reached `get_current`, found the record, and returned without appending. That behaviour
    is pinned by a unit test over the ports, where it can be asserted instead of narrated.
    """
    url = _admin_url()
    engine = create_postgres_engine(url, pool_size=2, max_overflow=0)
    try:
        database = await _database_name(engine)
        # A range of its own, so nothing here disturbs a measured ingest.
        index = 900_001
        request = _write_request(index)
        repository = PostgresMemoryRepository(engine)

        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM cognitive_os.events WHERE stream_id = :sid"),
                {"sid": request.memory_id},
            )
            await connection.execute(
                text("DELETE FROM cognitive_os.event_streams WHERE stream_id = :sid"),
                {"sid": request.memory_id},
            )
            for table in ("memory_sources", "memory_revisions", "memory_items"):
                await connection.execute(
                    text(f"DELETE FROM cognitive_os.{table} WHERE memory_id = :mid"),
                    {"mid": request.memory_id},
                )

        # The crash state: the record, with no event. Written through the released repository,
        # not through SQL, so the row is exactly the one the governed path produces.
        await repository.create_memory(request)
        events_after_the_planted_crash = await _creation_events(engine, request.memory_id)

        # The resume: the same request, through the governed service.
        service = _service(engine)
        _, created = await service.create(request)
        events_after_the_resume = await _creation_events(engine, request.memory_id)

        # And the resume is idempotent: running it a third time must not append a second
        # creation event, or the repair has traded an orphan for a duplicate.
        await service.create(request)
        events_after_a_second_resume = await _creation_events(engine, request.memory_id)

        async with engine.connect() as connection:
            revisions = int(
                await connection.scalar(
                    text(
                        "SELECT count(*) FROM cognitive_os.memory_revisions WHERE memory_id = :mid"
                    ),
                    {"mid": request.memory_id},
                )
                or 0
            )
    finally:
        await engine.dispose()

    return _seal(
        {
            "schema_version": 1,
            "sprint": "22C",
            "wave": "W1",
            "items": ["S22C-031"],
            "recorded_at": _now(),
            "database": database,
            "repairs": "22B W3-F1",
            "memory_id": str(request.memory_id),
            "the_state_a_crash_leaves": (
                "a memory_items row written by the repository's own transaction, with no "
                "memory.item_created event, because the append is a second transaction"
            ),
            "creation_events_after_the_planted_crash": events_after_the_planted_crash,
            "creation_events_after_the_resume": events_after_the_resume,
            "creation_events_after_a_second_resume": events_after_a_second_resume,
            "revisions": revisions,
            "resume_repaired_the_orphan": (
                events_after_the_planted_crash == 0 and events_after_the_resume == 1
            ),
            "resume_is_idempotent": events_after_a_second_resume == 1,
            "resume_returned_the_same_record": created is not None
            and created[0].memory_id == request.memory_id,
            "counterfactual": (
                "the released code appended only when the memory did not exist before the "
                "write, so this call would have found the record and returned with the "
                "stream still empty. Asserted over the ports in "
                "tests/cognitive_os/memory/test_creation_event_repair.py, where the old "
                "decision can be reproduced without a second copy of the released service"
            ),
            "reads_an_exit_criterion": False,
            "why_no_exit": (
                "no 22C exit reads a crash. This is an inherited repair, and what it owes is "
                "22B's own reproduction returning a different number"
            ),
        }
    )


async def crash_and_resume(*, attempts: int = CRASH_ATTEMPTS) -> dict[str, Any]:
    """22B's crash reproduction, with the one question the repair adds.

    22B counted eventless items **after recovery** and stopped. That is the right place to
    look for the window and the wrong place to look for the repair, because the repair runs
    during the resume that 22B performed immediately afterwards and never re-counted. Both
    counts are taken here, and the pair is the finding: the window is still open, and the
    resume closes what it opened.
    """
    url = _admin_url()
    container = os.environ.get("COGOS_POSTGRES_TOOL_CONTAINER")
    if not container:
        raise SystemExit("COGOS_POSTGRES_TOOL_CONTAINER is required")
    psql_url = url.replace("postgresql+asyncpg", "postgresql")

    runs: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        run = await _one_crash(url, psql_url, container, attempt)
        runs.append(run)
        if run["window_opened"]:
            break

    read = next((run for run in runs if run["window_opened"]), None)
    return _seal(
        {
            "schema_version": 1,
            "sprint": "22C",
            "wave": "W1",
            "items": ["S22C-031"],
            "recorded_at": _now(),
            "repairs": "22B W3-F1",
            "reproduction": "22B W3's crash: SIGKILL to the PostgreSQL container, mid-ingest",
            "what_22b_measured": {
                "items_missing_an_event": _load(CRASH_RECORD)["items_missing_an_event"],
                "measured_when": "after crash recovery, before the resume",
                "and_never_again": (
                    "22B resumed the range immediately afterwards and did not re-count. Under "
                    "the released code the count would not have moved, which is the defect"
                ),
            },
            "attempts": len(runs),
            "attempts_budget": attempts,
            "runs": runs,
            "window_opened": read is not None,
            "items_missing_an_event_after_recovery": (read or {}).get("eventless_after_recovery"),
            "items_missing_an_event_after_resume": (read or {}).get("eventless_after_resume"),
            "repair_closed_every_orphan": bool(
                read
                and read["eventless_after_recovery"] > 0
                and read["eventless_after_resume"] == 0
            ),
            "reading_is_refused": None
            if read
            else (
                "no attempt landed in the window, so no attempt has anything to say about the "
                "repair. A zero here would be the crash missing, not the repair working"
            ),
            "limitations": [
                "the window is not closed. An item whose range is never re-run keeps its "
                "orphan, and this measurement only shows that a resume repairs one",
                "a repaired creation event is stamped when the repair ran. The event stream "
                "regains the item; it does not regain the moment the item was written",
            ],
            "reads_an_exit_criterion": False,
        }
    )


async def _one_crash(url: str, psql_url: str, container: str, attempt: int) -> dict[str, Any]:
    engine = create_postgres_engine(url, pool_size=2, max_overflow=0)
    try:
        before = await _governed_item_count(url)
        eventless_before = await _eventless_items(engine)
    finally:
        await engine.dispose()

    start = CRASH_START + (attempt - 1) * CRASH_ITEMS
    writer = subprocess.Popen(  # fixed argv, no shell
        [
            sys.executable,
            str(REPO / "scripts/scale_22b.py"),
            "--ingest",
            "--ingest-items",
            str(CRASH_ITEMS),
            "--ingest-start",
            str(start),
        ],
        cwd=str(REPO),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    killed_at: int | None = None
    kill_started = perf_counter()
    try:
        while perf_counter() - kill_started < 300:
            if await _governed_item_count(url) - before >= CRASH_KILL_AFTER:
                killed_at = await _governed_item_count(url) - before
                break
            if writer.poll() is not None:
                break
        if killed_at is None:
            writer.kill()
            raise SystemExit("the ingest never reached the kill threshold; no crash was taken")
        subprocess.run(["docker", "kill", container], check=True, capture_output=True)
        killed_wall = perf_counter()
        writer.communicate(timeout=120)
    finally:
        if writer.poll() is None:
            writer.kill()

    subprocess.run(["docker", "start", container], check=False, capture_output=True)
    ready = False
    while perf_counter() - killed_wall < 180:
        probe = subprocess.run(  # fixed argv, no shell
            ["psql", psql_url, "-Atqc", "SELECT 1"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode == 0 and probe.stdout.strip() == "1":
            ready = True
            break
    if not ready:
        raise SystemExit(f"{container} did not come back within 180s of being killed")
    recovery_seconds = perf_counter() - killed_wall

    engine = create_postgres_engine(url, pool_size=2, max_overflow=0)
    try:
        eventless_after_recovery = await _eventless_items(engine)
        items_after_recovery = await _governed_item_count(url)
    finally:
        await engine.dispose()

    resumed = await _ingest(CRASH_ITEMS, start)

    engine = create_postgres_engine(url, pool_size=2, max_overflow=0)
    try:
        eventless_after_resume = await _eventless_items(engine)
    finally:
        await engine.dispose()
    resumed_count = await _governed_item_count(url)

    return {
        "attempt": attempt,
        "ingest_start": start,
        "items_before": before,
        "eventless_before": eventless_before,
        "items_written_before_the_kill": killed_at,
        "items_after_recovery": items_after_recovery,
        "recovery_seconds": round(recovery_seconds, 3),
        "eventless_after_recovery": eventless_after_recovery,
        "eventless_after_resume": eventless_after_resume,
        # The window is this run's own, not the store's history: a store carrying an orphan
        # from an earlier attempt would otherwise read as a window this attempt opened.
        "window_opened": eventless_after_recovery > eventless_before,
        "resumed_items": resumed["items"],
        "items_after_resume": resumed_count,
        "resume_duplicated_nothing": resumed_count == before + CRASH_ITEMS,
        "expected_items_after_resume": before + CRASH_ITEMS,
    }


# --------------------------------------------------------------------------------------
# S22C-032. The pre-registered procedure, executed and read.
# --------------------------------------------------------------------------------------


async def restore_reindex(*, fallback: bool = False) -> dict[str, Any]:
    """Confirm the sealed number, apply the frozen procedure, read the floor again.

    **W1-F4's operational half.** The precondition costs eleven minutes of exact scans and the
    rebuild that follows it can fail — revision 1's did. The first version of this function
    held the precondition in a local variable until the end, so a failed rebuild threw away a
    measurement that had already succeeded and told nobody it had. The precondition is now
    sealed into its own record the moment it is read, before anything is put at risk.
    """
    plan = _load(OUTPUTS["pre_register_2"])
    if plan["w4_f1"]["procedure_hash"] != procedure_hash():
        raise SystemExit(
            "the procedure has changed since it was pre-registered; re-freeze S22C-030 "
            "deliberately or restore the procedure, but do not measure under a third one"
        )

    table = corpus_table("clustered")
    dimension = int(DATASETS["clustered"]["dimension"])
    index = f"{table}_hnsw_{dimension}"
    url = _restored_url()
    engine = create_postgres_engine(
        url, pool_size=2, max_overflow=0, command_timeout_seconds=21_600
    )
    try:
        database = await _database_name(engine)
        if database != RESTORED_DATABASE:
            raise SystemExit(f"expected {RESTORED_DATABASE}, connected to {database}")

        async with engine.connect() as connection:
            rows = int(
                await connection.scalar(text(f"SELECT count(*) FROM cognitive_os.{table}")) or 0
            )
            index_bytes_before = int(
                await connection.scalar(
                    text("SELECT pg_relation_size(CAST(:name AS regclass))"),
                    {"name": f"cognitive_os.{index}"},
                )
                or 0
            )
            default_maintenance_work_mem = str(
                await connection.scalar(text("SHOW maintenance_work_mem"))
            )

        # The precondition: the store still reads what 22B sealed, before anything is rebuilt.
        started = perf_counter()
        before = await recall_at(engine, "clustered", probes=RECALL_PROBES, k=RECALL_K)
        before_seconds = round(perf_counter() - started, 3)
        sealed = _load(RESTORED_RECALL_RECORD)["recall_at_k"]
        precondition_held = before["recall_at_k"] == sealed

        # Sealed here, before the rebuild is attempted. Whatever happens next, this reading
        # exists: 22B's restored store was independently re-measured and read what 22B said.
        _write(
            OUTPUTS["precondition"],
            _seal(
                {
                    "schema_version": 1,
                    "sprint": "22C",
                    "wave": "W1",
                    "items": ["S22C-032"],
                    "recorded_at": _now(),
                    "database": database,
                    "measures": "22B's restored clustered index, unchanged, before any repair",
                    "sealed_restored_recall": sealed,
                    "remeasured_restored_recall": before["recall_at_k"],
                    "held": precondition_held,
                    "seconds": before_seconds,
                    "index_bytes": index_bytes_before,
                    "rows": rows,
                    "recall": before,
                    "why_this_is_its_own_record": (
                        "it is a reading of a state that the next statement destroys. Held "
                        "in a variable it would have been lost with revision 1's failed "
                        "rebuild (W1-F4), and the forty minutes with it"
                    ),
                    "why_it_must_hold": REINDEX_PROCEDURE["precondition"],
                }
            ),
            {"held": precondition_held, "recall_at_k": before["recall_at_k"]},
        )
        if not precondition_held:
            return _seal(
                {
                    "schema_version": 1,
                    "sprint": "22C",
                    "wave": "W1",
                    "items": ["S22C-032"],
                    "recorded_at": _now(),
                    "database": database,
                    "stopped_on_the_precondition": True,
                    "sealed_restored_recall": sealed,
                    "remeasured_restored_recall": before["recall_at_k"],
                    "why_stopped": (
                        "the reading is deterministic given the same index and probe seed, so "
                        "a different value means the store or the reading moved since 22B "
                        "sealed it. Rebuilding the index now would compare a repaired store "
                        "against a number that no longer describes the unrepaired one"
                    ),
                    "index_was_not_touched": True,
                }
            )

        applied: list[dict[str, Any]] = []
        rebuild_started = perf_counter()
        async with engine.connect() as connection:
            await connection.execution_options(isolation_level="AUTOCOMMIT")
            for step in REINDEX_PROCEDURE["steps"]:
                statement = str(step["sql"]).format(index=index, table=table)
                step_started = perf_counter()
                await connection.execute(text(statement))
                applied.append(
                    {
                        "order": step["order"],
                        "sql": statement,
                        "seconds": round(perf_counter() - step_started, 3),
                    }
                )
            if fallback:
                await connection.execute(
                    text(REINDEX_PROCEDURE["fallback_if_the_hypothesis_is_wrong"]["sql"])
                )
                step_started = perf_counter()
                await connection.execute(text(f"REINDEX INDEX cognitive_os.{index}"))
                applied.append(
                    {
                        "order": 5,
                        "sql": (
                            f"{REINDEX_PROCEDURE['fallback_if_the_hypothesis_is_wrong']['sql']}; "
                            f"REINDEX INDEX cognitive_os.{index}"
                        ),
                        "seconds": round(perf_counter() - step_started, 3),
                    }
                )
        rebuild_seconds = round(perf_counter() - rebuild_started, 3)

        async with engine.connect() as connection:
            index_bytes_after = int(
                await connection.scalar(
                    text("SELECT pg_relation_size(CAST(:name AS regclass))"),
                    {"name": f"cognitive_os.{index}"},
                )
                or 0
            )

        started = perf_counter()
        after = await recall_at(engine, "clustered", probes=RECALL_PROBES, k=RECALL_K)
        after_seconds = round(perf_counter() - started, 3)
    finally:
        await engine.dispose()

    source = _load(SOURCE_RECALL_RECORD)["recall_at_k"]
    recall = after["recall_at_k"]
    return _seal(
        {
            "schema_version": 1,
            "sprint": "22C",
            "wave": "W1",
            "items": ["S22C-032"],
            "recorded_at": _now(),
            "repairs": "22B W4-F1",
            "database": database,
            "table": table,
            "index": index,
            "rows": rows,
            "used_the_fallback": fallback,
            "procedure_hash": procedure_hash(),
            "procedure_was_frozen_first": True,
            "server_default_maintenance_work_mem": default_maintenance_work_mem,
            "precondition": {
                "sealed_restored_recall": sealed,
                "remeasured_before_the_rebuild": before["recall_at_k"],
                "held": precondition_held,
                "seconds": before_seconds,
                "why": REINDEX_PROCEDURE["precondition"],
            },
            "rebuild": {
                "steps": applied,
                "seconds": rebuild_seconds,
                "index_bytes_before": index_bytes_before,
                "index_bytes_after": index_bytes_after,
            },
            "recall": {
                **after,
                "seconds": after_seconds,
                "floor": RECALL_FLOOR,
                "meets_floor": recall is not None and recall >= RECALL_FLOOR,
            },
            "comparison": {
                "sealed_source_recall": source,
                "sealed_restored_recall": sealed,
                "repaired_restored_recall": recall,
                "recovered_by": None if recall is None else round(recall - sealed, 4),
                "against_the_source": None if recall is None else round(recall - source, 4),
            },
            "hypothesis_held": recall is not None and recall >= RECALL_FLOOR and not fallback,
            "what_this_does_not_claim": REINDEX_PROCEDURE["what_this_does_not_claim"],
            "limitations": [
                "one store, one dataset, one restore. The procedure is proven on the "
                "measurement 22B left behind and on nothing else",
                "the rebuild is not free: its wall-clock is recorded above and an operator "
                "restoring a governed store pays it before the store's recall is trustworthy",
            ],
            "reads_an_exit_criterion": False,
            "why_no_exit": (
                "22C's five exits are about acquisition. This is 22B's floor, repaired, and "
                "it is read by the definition of done's inherited-repair clause"
            ),
        }
    )


# --------------------------------------------------------------------------------------


OUTPUTS = {
    # Revision 1, sealed before the wave's first measurement and left exactly as published
    # even though its procedure could not run. See W1-F4.
    "pre_register": EVIDENCE / "sprint-22c-repair-plan.json",
    "pre_register_2": EVIDENCE / "sprint-22c-repair-plan-r2.json",
    "orphan_repair": EVIDENCE / "sprint-22c-w1-event-repair.json",
    "crash": EVIDENCE / "sprint-22c-w1-crash.json",
    "precondition": EVIDENCE / "sprint-22c-w1-restore-precondition.json",
    "reindex": EVIDENCE / "sprint-22c-w1-restore-reindex.json",
}


def _write(path: Path, record: dict[str, Any], summary: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": path.name, **summary}, indent=1, sort_keys=True))
    return 0


def _check() -> int:
    """Seals reproduce, the frozen procedure is the one that ran, and the numbers agree.

    W1-F1's split applies here too: everything in these records is a *measurement*, which no
    validator can recompute without re-crashing a database. So the check verifies the seals,
    the pre-registration's binding to the code and the procedure, and the internal agreement
    between the records — never by re-running them.
    """
    results: list[dict[str, Any]] = []
    for name, path in OUTPUTS.items():
        if not path.exists():
            results.append({"record": path.name, "present": False, "reproduced": False})
            continue
        stored = _load(path)
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        results.append(
            {
                "record": path.name,
                "present": True,
                "reproduced": _sha256(_canonical(body)) == stored["integrity_content_hash"],
                "step": name,
            }
        )

    revision_1 = _load(OUTPUTS["pre_register"])
    plan = _load(OUTPUTS["pre_register_2"]) if OUTPUTS["pre_register_2"].exists() else {}
    bindings = {
        # Revision 1 is checked against the hash it was published with, not against today's
        # procedure. It is history: it must still be *itself*, and it must still not match.
        "revision_1_is_unedited": revision_1["w4_f1"]["procedure_hash"]
        == PROCEDURE_REVISION_1_HASH,
        "revision_2_supersedes_revision_1_by_hash": bool(plan)
        and plan["supersedes"]["procedure_hash"] == PROCEDURE_REVISION_1_HASH,
        "procedure_is_the_frozen_one": bool(plan)
        and plan["w4_f1"]["procedure_hash"] == procedure_hash(),
        "repair_source_is_the_frozen_one": bool(plan)
        and plan["w3_f1"]["repair_source_hash"] == repair_source_hash(),
    }
    if OUTPUTS["reindex"].exists():
        reindex = _load(OUTPUTS["reindex"])
        bindings["reindex_ran_the_frozen_procedure"] = (
            reindex.get("procedure_hash") == plan["w4_f1"]["procedure_hash"]
        )
        bindings["reindex_agrees_with_the_sealed_precondition"] = (
            reindex["precondition"]["remeasured_before_the_rebuild"]
            == _load(OUTPUTS["precondition"])["remeasured_restored_recall"]
        )
        bindings["reindex_compared_against_22b_sealed_numbers"] = (
            reindex["comparison"]["sealed_restored_recall"]
            == _load(RESTORED_RECALL_RECORD)["recall_at_k"]
            and reindex["comparison"]["sealed_source_recall"]
            == _load(SOURCE_RECALL_RECORD)["recall_at_k"]
        )

    ok = all(item["reproduced"] for item in results if item["present"]) and all(bindings.values())
    print(
        json.dumps(
            {"records": results, "bindings": bindings, "ok": ok},
            indent=1,
            sort_keys=True,
        )
    )
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pre-register", action="store_true")
    parser.add_argument("--orphan-repair", action="store_true")
    parser.add_argument("--crash", action="store_true")
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="run the pre-registered fallback lever, after the primary one has been read",
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        return _check()
    if arguments.pre_register:
        record = _pre_registration()
        return _write(
            OUTPUTS["pre_register_2"],
            record,
            {
                "procedure_hash": record["w4_f1"]["procedure_hash"],
                "repair_source_hash": record["w3_f1"]["repair_source_hash"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
        )
    if arguments.orphan_repair:
        record = asyncio.run(orphan_repair())
        return _write(
            OUTPUTS["orphan_repair"],
            record,
            {
                "resume_repaired_the_orphan": record["resume_repaired_the_orphan"],
                "resume_is_idempotent": record["resume_is_idempotent"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
        )
    if arguments.crash:
        record = asyncio.run(crash_and_resume())
        return _write(
            OUTPUTS["crash"],
            record,
            {
                "attempts": record["attempts"],
                "window_opened": record["window_opened"],
                "after_recovery": record["items_missing_an_event_after_recovery"],
                "after_resume": record["items_missing_an_event_after_resume"],
                "repair_closed_every_orphan": record["repair_closed_every_orphan"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
        )
    if arguments.reindex:
        record = asyncio.run(restore_reindex(fallback=arguments.fallback))
        return _write(
            OUTPUTS["reindex"],
            record,
            {
                "stopped_on_the_precondition": record.get("stopped_on_the_precondition", False),
                "repaired_recall": record.get("recall", {}).get("recall_at_k"),
                "meets_floor": record.get("recall", {}).get("meets_floor"),
                "rebuild_seconds": record.get("rebuild", {}).get("seconds"),
                "integrity_content_hash": record["integrity_content_hash"],
            },
        )
    parser.error("choose one of --pre-register, --orphan-repair, --crash, --reindex, --check")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
