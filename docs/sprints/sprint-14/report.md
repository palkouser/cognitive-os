# Sprint 14 report

Status: Implemented and locally validated; remote CI, merge, and baseline tag pending

## Baseline and authority

Sprint 14 branches from `sprint-13-baseline` on
`feature/sprint-14-experience-compiler`. The implementation follows the Group 3 technical
specification and preserves all Sprint 9–13 authority boundaries. PostgreSQL remains authoritative
for memory, semantic, skill, strategy, Experience Compiler, candidate, decision, and access state;
the event store retains lifecycle evidence; the artifact store owns referenced large content; and
the existing Controller remains the only execution authority. No upstream LightAgent runtime file
is changed.

The compiler is post-execution and deterministic. Provider output may be analyzed only as untrusted
proposal data and cannot create evidence, establish causality, promote a candidate, mutate a
destination subsystem, alter policy, or authorize execution.

## Delivered scope

- Immutable source, profile, request, snapshot, reconstruction, segment, step assessment, path,
  correction, contribution, generalizability, candidate, revision, routing, verifier, decision,
  manifest, and access contracts with exported JSON Schemas.
- Exact source revision and content-hash validation, frozen source/profile registries, canonical
  event ordering, explicit gaps and conflicts, deterministic reconstruction, cancellation, resume,
  and idempotent recompilation.
- Evidence-linked success, failure, repair, fallback, correction, recovery, first-incorrect-step,
  contribution, limitation, sensitivity, and generalizability assessment without provider-authored
  authoritative claims.
- Nine proposed candidate types: memory, semantic observation, skill, strategy, failure pattern,
  routing observation, benchmark case, negative example, and corpus item. Every candidate retains
  exact source provenance and begins in the non-authoritative `proposed` state.
- Fifteen verifier capabilities covering source integrity, reconstruction, ordering, segmentation,
  assessment, first-incorrect-step evidence, paths, contribution, generalizability, provenance,
  schema, authority, sensitivity, determinism, and access auditing.
- Migration `0006` with nine Experience Compiler tables, append-only history, validated initial
  state, controlled compare-and-set finalization and candidate transitions, least-privilege grants,
  a transactional PostgreSQL repository, and read-only health checks.
- Eight lifecycle event types, deterministic replay-compatible payloads, audited source and
  reconstruction access, backup/restore manifest coverage, and CLI, smoke, health, export, and
  scale surfaces.
- Ten credential-free deterministic fixtures, 12-case CI and 48-case seed benchmarks, CI gates,
  operating, configuration, security, benchmark, and architecture documentation, plus ADRs
  0047–0050.

## Validation

- Required checks passed: Ruff; Ruff format; Cognitive OS tests: **601 passed, 5 opt-in tests
  skipped**; contract schema drift check passed.
- Full repository regression: **742 passed, 32 opt-in tests skipped**; contract tests: **65
  passed**; PostgreSQL and Controller integration: **21 passed**.
- Strict MyPy passed on **389 source files**. Bandit reported no findings. Repository-language
  policy, dependency audit, wheel/sdist installation, editable installation, and
  `git diff --check` passed.
- Migration `0006` downgrade-to-`0005`, re-upgrade, Alembic drift, initial-state triggers,
  append-only triggers, runtime grants, concurrent idempotency, direct-promotion denial, and health
  checks passed.
- Isolated backup and restore verification passed from `cognitive_os_integration_test` into
  `cognitive_os_restore_test`, including exact Experience Compiler counts, snapshot history, and
  cross-subsystem integrity checks.
- Experience benchmarks matched **12/12 CI** and **48/48 seed** cases with exact deterministic
  manifests, complete access audits, and zero scope leaks, sensitivity leaks, automatic
  promotions, destination writes, or provider calls.
- The deterministic smoke produced manifest hash
  `f479e403806777b7b6bc69dcf447dd714359ef69b4abe2cd1cbb6e944b62e924`, source snapshot hash
  `94b74f63bd9c9ebddd3bcdc4162cfa1cdfcb50918cc75aa766640bdbbaf49a40`, and reconstruction hash
  `6e748684d376be6080dc9c3ed4dff522aa1b6ff6a7fd32b293a4cb788393786b`.
- The CPU-only scale run completed **10,000 compilations** and produced 49,000 source references,
  41,000 timeline entries, 41,000 step assessments, and 52,000 proposed candidates with zero
  provider calls and destination writes. Compilation p50 was **3.891 ms**, p95 **5.937 ms**, peak
  traced memory **46,716 KiB**, and total runtime **48.202 seconds**.

## Restore instructions

Apply migration `0006`, create a backup with `scripts/backup_event_store.sh`, and validate only into
an isolated restore database with `scripts/restore_event_store.sh --test-restore`. The restore gate
checks exact Experience Compiler row counts and hashes, candidate revision and source lineage,
manifest and access integrity, artifact content, and all existing memory, semantic, Wiki, skill,
and strategy state.

## Known limitations

The compiler consumes already-recorded execution evidence; it does not run providers, tools,
verifiers, or the Controller. Candidate output remains a proposal and requires the Sprint 15
governed normalization, quality, licensing, staging, and destination-routing path. Provider-assisted
analysis is optional and may only return bounded hints that are checked against exact source
evidence. Automatic compilation, promotion, learned ranking, adaptive routing, unrestricted entity
resolution, graph databases, network model downloads, GPU requirements, and destination mutation
remain disabled.

## Gate G and Sprint 15 hand-off

Gate G — Experience compilation — is complete locally: Cognitive OS can reconstruct bounded task
trajectories from exact records, assess successful and failed execution paths conservatively,
produce evidence-linked proposed learning candidates, verify authority and provenance, and preserve
deterministic manifests and audited access without mutating the systems that own the source data.

Sprint 15 may consume the proposed candidate, source reference, evidence, limitation,
generalizability, sensitivity, verifier, decision, manifest, revision, routing-envelope, and access
contracts. It must not reinterpret provider prose as evidence, bypass candidate verification,
promote directly from the compiler, mutate source records, or weaken existing Controller,
repository, event, artifact, memory, semantic, skill, strategy, acceptance, or policy authority.
