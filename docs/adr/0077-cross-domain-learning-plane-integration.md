# ADR 0077: Cross-domain runs feed the learning plane through existing authorities

## Status

Accepted for Sprint 20.

## Decision

`src/cognitive_os/domains/learning.py` translates a governed domain run's recorded event trail into
the inputs the Experience Compiler, Memory Plane, semantic extraction, and Corpus Factory already
accept. No learning component is re-implemented, and no candidate, memory, claim, or corpus item is
synthesised outside of what a real recorded event evidences.

- **Experience compilation.** `build_compilation` groups the run's stored events by trajectory
  source — Controller events, tool calls, verifier results, and the acceptance decision — and hands
  the groups to the unmodified `ExperienceCompiler`. Every `TimelineEntry` carries the originating
  event's real `event_id` as its identity and the event's `payload_hash` as its evidence; an event
  type the table does not recognise raises rather than being filed as `unknown` and diluting the
  evidence. The step status is read from the event's payload, not guessed from its name —
  `verifier.completed` records a verifier that *ran*, and only the payload says whether it passed.
- **Compilation identity.** The compilation ID is derived from the content hashes of the recorded
  sources, not from a case ID or a clock reading. Two calls over the same recorded event stream
  compile once; two different executions of the same case — different timestamps, different event
  identities — are different trajectories and get their own compilation, matching what the Experience
  Compiler's own idempotency key already requires.
- **Memory Plane.** `project_run` projects exactly two typed contents — `TaskSummaryMemoryContent`
  and `VerificationSummaryMemoryContent` — because both already have a registered deterministic
  semantic extractor in `semantic_memory/extraction.py`. A memory type with no extractor would be
  unreadable by the layer above it, which is worse than not writing it. `domain_memory_policy()`
  grants only those two types, only `DOMAIN` and `TASK` scope, and `INTERNAL` sensitivity — the
  `MemoryService` gateway enforces the policy on every write, the same governed gateway coding
  trajectories go through.
- **Semantic extraction.** `SemanticExtractionService` runs unmodified over the two typed memories via
  `extract_typed_memory`, grounded through `TrustedSourceResolver` against the same in-memory
  repository the write went to. Nothing is asserted outside of what a memory revision's own fields
  state.
- **Corpus Factory.** Candidates the compiler proposed with `target_subsystem == "corpus-factory"` are
  declared to the unmodified `CorpusFactory`. `corpus_request` derives the usage-rights declaration
  from the case's own `ProvenanceRef` and nothing else: `REDISTRIBUTION` and `PUBLIC_RELEASE` mirror
  `redistributable`, the licence identifier is the declared licence, and `MODEL_TRAINING` and
  `COMMERCIAL_USE` are left undeclared (`None`) because no source in this repository grants them. The
  Factory — not this module — decides what those declarations permit.

## A run that fails is not laundered into success

A rejected run's terminal state is `"rejected"`, and the compiler is not told otherwise. It produces
`FAILURE_PATTERN` and `NEGATIVE_EXAMPLE` candidates instead of `MEMORY` and `SKILL` candidates — the
same branch the compiler already takes for any incomplete or failed trajectory — and the projected
`TaskSummaryMemoryContent.review_status` reads `"rejected"`, not `"accepted"`. A repaired run (one
that failed, then succeeded after a repair cycle) keeps every acceptance decision the Controller
recorded in its timeline; only the terminal state used for routing is the last one.

## Alternatives and consequences

Writing a domain-specific compiler was rejected: the Experience Compiler's mandatory verifiers
(`experience.source_hash_integrity`, `experience.deterministic_reconstruction`,
`experience.no_unsupported_causal_claim`, and the rest) already enforce exactly the integrity
properties a domain trajectory needs, and a second compiler would need to reprove them.

Fabricating synthetic timeline entries to backfill sources the Controller never recorded — for
example, inventing a `PROVIDER` entry because the compiler's fixtures usually include one — was
rejected. The mandatory domain path is provider-free by design (ADR 0076); the compiler's
`enabled_source_types` accepts whatever sources the profile declares, and `PROVIDER` is not one of
them for a domain run.

Persisting learning-plane output to PostgreSQL was considered and rejected for this sprint, matching
ADR 0076's precedent: the mandatory domain path stays offline, credential-free, and CPU-only, and
Memory Plane, semantic memory, and Corpus Factory PostgreSQL adapters already exist and are
exercised by their own integration suites (`test_memory_plane.py`, `test_semantic_memory.py`,
`test_corpus_factory.py`, `test_experience_compiler.py`); this module reuses the in-memory
repositories those suites already validate against, the same choice `domains/runner.py` made for the
event store when it closed the Controller and Tool Plane integration gap.

The consequence is that a governed run now has a second downstream consumer of its event trail beyond
the acceptance decision — compilation is a pure read of what was recorded, so it does not change what
the Controller, Tool Plane, or Acceptance Service decided.

## Verification

All 51 fixture cases compile to `CompilationDecisionType.COMPLETED` with `TrajectoryCompleteness.COMPLETE`
on both the accepted and the wrong-answer path; the wrong-answer path terminates `"rejected"` with
`FAILURE_PATTERN` and `NEGATIVE_EXAMPLE` candidates present. Full ingestion (compile, memory write,
semantic extraction, corpus declaration) runs end to end for every sampled case: 2 memories, 4
semantic observations, and 4 semantic claims per run, plus at least one corpus item (two on the
wrong-answer path, since a negative example is also declared). Three governance invariants —
`learning_recorded_events_only`, `learning_failure_preserved`, `learning_corpus_rights` — run in the
seed benchmark manifest and as parametrised tests, bringing the pilot's total to 25.
