# Sprint 21D1 handoff — learning surface and EMG

Sprint 21C1 built the durable evidence layer. 21C2 built the governed boundary an outside
teacher reaches it through. 21C3 filled it with **real** outcomes: executed, verified,
rights-clean, and split so that nothing in the evaluation groups can be trained on.

D1 is where the question this project has been deferring finally gets asked. Not "can this be
recorded safely" — that is answered — but **"does any learned component actually help?"**
Nothing in C1, C2 or C3 has answered it, and C3's numbers must not be mistaken for an answer.

## 1. Starting point

| | |
| --- | --- |
| Parent tag | `sprint-21c3-reality-baseline`, annotated tag object `497f959bc55989541016a61bd9034e12523b8573` |
| Parent commit | `05809446c726444146d85aad22808e10ce87ca3e`, equal to verified `main` and `origin/main` |
| Parent pull request | `#215`, squash-merged |
| Parent final CI | run `30571166301`, 29 of 29 jobs success on the parent commit |
| Parent migration head | `0015` |
| Next available migration | `0016` — still unallocated. ADR 0089 declined it deliberately; see §6. |
| Gate C3 | **pass** — 15 of 16 conditions on evidence, the sixteenth closed by the release |
| Gate L2 | **closed** |
| Recommended branch | `feature/sprint-21d1-learning-surface-emg` |

Remote state can change. Reverify the tag object, the peeled commit, remote `main` and the
migration head on day one rather than trusting this table.

## 2. What C3 leaves behind, by API

### Tasks

- `cognitive_os.coding.reality_task_specs` — the 30-task table. Adding a family is a data
  change; if it needs new machinery in `reality_tasks`, the shape is wrong.
- `cognitive_os.coding.reality_tasks` — `available_templates()`, `template(id)`,
  `build_manifest(...)`, `write_task(...)`. Byte-identical regeneration; identity is uuid5 over
  template and seed. `write_task` puts visible files under `<root>/workspace` and the control
  bundle under `<root>/control`, never nested.
- `cognitive_os.coding.reality_leakage` — `control_tokens(manifest, template)`. Run it over
  anything a candidate, a provider or an indexer will see.

### Outcomes and trajectories

- `cognitive_os.coding.outcome_recording.CodingOutcomeRecorder` — one immutable artifact and
  one `coding.outcome_recorded` event per run.
- `cognitive_os.coding.reality_trajectories` — `plan_paths(...)`, `build_request(...)`,
  `compiler_profile()`. **Pass a fixed epoch, never a clock:** `ExperienceCompilerService`
  verifies a persisted manifest by recompiling and comparing for exact equality (W6-F1).
- `cognitive_os.application.services.reality_campaign.RealityCampaignLedger` —
  `plan_resume(...)`, `recorded_runs(...)`, `completed_by_identity(...)`. Resume is safe and is
  the default.

### Corpus

- `cognitive_os.coding.reality_corpus_items` — `task_package_request`, `correction_request`,
  and the sources for both. Both declare `split_group_key` and a scope naming the repository
  group.
- `cognitive_os.domain.corpus.CorpusFactoryRequest.split_group_key` — set it, and every item in
  the request takes the split derived from the group hash. Leave it unset and the pre-C3
  lineage-based split is unchanged.

### Learned evidence

- `cognitive_os.application.services.learned_intake.LearnedObservationIntake` — takes
  `GovernedOutcomeReference` with its own `occurred_at`. It reads no clock; re-offering the
  same outcome is a free no-op (W1-F1).
- `REAL_GOVERNED_RUN` provenance is **evaluation-only**. A training snapshot containing one is
  refused, not filtered.

### Embeddings and retrieval

- `cognitive_os.infrastructure.embeddings.minilm` — the frozen identity, `health(root)`, the
  manifest helpers.
- `cognitive_os.infrastructure.embeddings.build_embedding_provider(config)` — raises when the
  local model is unusable. **It never substitutes the hashing provider.** Depend on that.
- `cognitive_os.coding.reality_retrieval` — `build_benchmark()`, `cross_group_leakage(...)`,
  `kind_counts(...)`.
- `scripts/retrieval_benchmark.py` — the four-arm measurement plus the precision comparison.

### Operations

- `scripts/reality_inputs.py` — one entry point: `generate`, `validate`, `stats`, `harvest`,
  `verify`, and forwarding for `run`, `resume`, `embed`, `provider`.
- `cognitive_os.coding.reality_integrity` — 15 checks, and the `failure`/`warning` split. Add
  D1's own authority links here rather than starting a second report.
- `scripts/verification_matrix.py` — the release matrix. **Every test row runs against the
  scratch store**, never the evidence pair (W6-F2). Keep it that way.

## 3. Frozen material — do not regenerate, do not tune on

| What | Identity |
| --- | --- |
| Task corpus | 30 templates, seed 1, uuid5 over template and seed |
| Retrieval benchmark | manifest hash `c9d2ac44731e81f2443545111c8e4832f848d63b68557862a7319cdd8beeca9d`, 60 records, 60 queries |
| Group-aware splits | profile `sprint21c3-group-aware-split-v1`, seed 15, 30 groups, 0 crossing |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` @ `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, tree digest `98eb3ae4df320d0b721902aabef795cafb36c3a516f036e92e2b046f55ef4229` |
| Evaluation observations | 896 accepted `real_governed_run`, evaluation-eligible, never training-eligible |

§4.15 is explicit and D1 inherits it: **if a threshold fails, the gate stays open or the
benchmark and task representation are corrected — the evaluation groups are never tuned on.**

## 4. Candidate learning surfaces

Listed as candidates, deliberately **without** consulting held-out results. Picking a surface
because it already looks good on the evaluation groups is the failure mode this whole
separation exists to prevent. Pre-register one, then measure.

1. **Correction ranking.** 60 failed-to-corrected trajectories over 30 tasks, two path
   families per task. The surface: given a failing state and candidate patches, rank them.
2. **Retrieval-augmented repair context.** 384-dimensional embeddings over the corpus, with
   measured baseline retrieval quality already recorded. The surface: which prior records to
   put in front of a repair attempt.
3. **Verifier-outcome prediction.** 214 outcomes with verifier evidence and 90 recorded hidden
   failures. The surface: predict the hidden verdict before running the container.
4. **Strategy selection.** Four candidate strategies with known per-strategy outcomes across
   all 30 tasks.

Whichever is chosen, D1 has to answer the question C3 could not: material downstream uplift,
anti-forgetting evidence, and shadow safety. Corpus volume and recall@5 are prerequisites, not
any of those three.

## 5. Limitations carried forward, with owners

| Limitation | Owner | Note |
| --- | --- | --- |
| No second reviewer; `required_pull_request_reviews` disabled | project owner | Carried since C1. No review has ever been fabricated to compensate. |
| `reality-inputs-core` is not a required check (27 required, 29 run) | project owner | Adding it changes branch protection — an operator decision, not a sprint's. |
| Inconsistent development Artifact Store pair | project owner | Fingerprint `7e85d9a6…82dcf` over 5 files, unchanged since C1. Remediation proposed, never executed; needs separate authority. |
| 60 W3 trajectory manifests cannot be verified by recompilation | D1 | W6-D1. A campaign on a clean store reproduces exactly; these rows keep a wall clock and are not rewritten. |
| OpenRouter free routes are unreliable (0/10, 9 boundary failures) | D1 | Off the critical path. A paid or pinned route needs its own ADR; `maximum_spend_usd` is zero everywhere. |
| The provider corpus cannot rank frontier providers | D1 | 15/15 executed patches correct on thirty single-edit tasks. Do not build a leaderboard from it. |
| Open-development data policy is `public` only | project owner | ADR 0088. Internal and restricted material still requires the strict ZDR values under ADR 0087. |

## 6. Migration `0016`

Still unallocated, and deliberately so. ADR 0089 measured half-precision vector storage and
declined the migration: 32.4% total saving against a 35% threshold, because the HNSW index
does not shrink with the column. The rehearsed conversion took 6.8 ms.

D1 may claim `0016` for its own schema. If it instead wants the half-precision conversion,
the trigger is in ADR 0089 — 100 000 embedded records or 1 GiB of vector storage including
indexes — and it must be re-measured on the corpus of the day, not argued from C3's numbers.

## 7. What must not be smuggled in

No training run, no component activation, no promotion of a C3 metric into a claim of learned
behaviour. Gate L2 is closed and D1 opens it only with the evidence L2 actually asks for.
