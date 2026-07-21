# Corpus-to-Memory Factory

Sprint 15 adds a deterministic, post-execution factory that turns exact local source revisions
into governed corpus items and proposal-only destination packages. It is downstream of the
Experience Compiler and does not replace the Controller, Memory Plane, semantic projection, Skill
Engine, Strategy Graph, event store, or artifact store.

## Authority and pipeline

The fixed pipeline is source registration, safety inspection, normalization, exact deduplication,
lineage construction, deterministic classification, license and usage-right assessment,
sensitivity and secret assessment, twelve-dimensional quality scoring, staging or quarantine,
package-only routing, manifest creation, deterministic splitting, and JSONL export. A provider may
offer bounded prose after deterministic analysis, but that prose cannot alter source facts,
licenses, rights, sensitivity, quality, routing, permissions, budgets, or destination state.

PostgreSQL owns source, item, classification, route, manifest, export, and access metadata. The
artifact store owns original, normalized, package, manifest, and export bytes. The event store owns
lifecycle evidence. Corpus records and accesses are append-only; item status changes use one
compare-and-set PostgreSQL function with a closed transition table.

## Safety boundaries

Only operator-controlled local files, directories, archives, existing subsystem exports, and
proposed Experience Compiler candidates are accepted. Source content is never executed. ZIP and
TAR readers reject traversal, absolute paths, symlinks, hard links, devices, malformed members,
Unicode/case-folding path collisions, excessive depth, excessive file count, oversized content,
and excessive expansion ratios. Originals remain immutable artifacts and normalization produces a
separate content-addressed artifact.

Exact content duplicates remain separately attributable to every source. Near-duplicate handling
is advisory and disabled by default. Unknown or conflicting licenses, missing required usage
rights, secrets, incompatible sensitivity, hard quality blockers, or unsupported destination
schemas fail closed into quarantine or rejection.

## Destination packages

Routing produces only a schema-versioned package artifact and receipt. Packages contain explicit
proposal-only constraints and no authority field. The factory cannot write to a destination,
promote memory, semantic observations, skills, or strategies, start training, upload exports,
change retrieval, or authorize execution. Destination owners must independently validate and
accept packages through their existing governed APIs.

## Operations

Use `uv run python scripts/corpus.py health`, `uv run python scripts/corpus_smoke_test.py`, and
`uv run python scripts/corpus_benchmark.py --cases 14`. PostgreSQL health requires
`COGOS_DATABASE_URL` and the `--database` flag. The 56-case seed benchmark is opt-in and remains
credential-free. Migration `0007` creates the corpus metadata plane.
