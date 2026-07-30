# Gate C3 assessment — Reality-Grade Learning Inputs

- Sprint: 21C3
- Branch: `feature/sprint-21c3-reality-inputs`
- Parent baseline: `sprint-21c2-provider-baseline` → `94abe263c8f26f36c8f8c3bc7b86859c14c1f291`
- Alembic head: **0015**, unchanged for the whole sprint
- Assessed: 2026-07-30

Every row below cites a machine-readable file under `evidence/`. A condition with a caveat is
not a pass; it is recorded as open with the caveat stated.

## Summary

| | Count |
| --- | --- |
| Conditions passed | 15 |
| Conditions open | 1 (condition 16 — the release itself) |
| Conditions failed | 0 |

**Gate L2 remains closed.** Nothing in this sprint trained or activated a learned component.

> Reality-grade inputs and local semantic retrieval are available, but useful learned
> behaviour has not yet been demonstrated.

## The sixteen conditions

### 1. C2 parent, peeled commit, remote `main`, final CI and migration head verified — **PASS**

Tag object `23b3304890f4a90112514c633c7e2b768f7eeeff`, peeled to
`94abe263c8f26f36c8f8c3bc7b86859c14c1f291`, identical to local and remote `main`. Final parent
CI run `30434494612`, 28 of 28 required checks, conclusion success. Alembic head `0015`.

*Evidence:* `sprint-21c3-baseline.json` → `parent_baseline`.

### 2. Open-development data policy implemented, documented and tested — **PASS**

ADR 0088 accepted; `require_zero_data_retention` defaults to `false` and
`allow_data_collection` to `true`, sent to OpenRouter as provider preferences. Credential
handling is unchanged: `OPENROUTER_API_KEY` remains the only accepted key source, the CLI
`environment_allowlist` still excludes secret-like names, and the prompt boundary — not these
flags — is what keeps credentials out of requests. Source rights remain an operator input with
an evidence hash. Measured in the live campaign: **0 credentials and 0 control tokens in any
provider request**.

*Evidence:* `sprint-21c3-w4-provider-campaign.json` → `data_policy`; ADR 0088;
`docs/operations/provider-configuration.md`.

### 3. At least 30 task packages across at least six families — **PASS**

30 tasks, 6 families, 5 per family, 30 distinct repository groups. Regeneration is
byte-identical: identities are uuid5 over template and seed. Rights are Apache-2.0,
project-owned, verified per task with an evidence hash. Verified in the real sandbox:
**30 of 30** baselines pass the published suite and fail the hidden one.

*Evidence:* `sprint-21c3-w2-task-corpus.json` → `corpus`,
`corpus_contract_verified_in_the_real_sandbox`.

### 4. Control material unreachable from provider context, features, embeddings and selection — **PASS**

Structural, not filtered: `RealityTaskProjection` cannot carry control material, and the
assembled prompt is re-scanned before it is sent. 0 control tokens in provider-visible
surfaces, 0 lookup-key leaks in the projection, 0 control tokens in the 60 retrieval queries.
The W4-F1 fix removed 32 false positives from the scanner without turning it off — the planted
hidden name is still found.

*Evidence:* `sprint-21c3-w2-task-corpus.json` → `leakage_and_shortcuts`;
`sprint-21c3-w6-operations.json` → `operator_cli`; `tests/cognitive_os/coding/test_reality_provider.py`.

### 5. Every candidate executed in the rootless sandbox with an immutable artifact and event — **PASS**

420 container runs in W2 for the corpus contract, 150 in the W3 campaign, 15 provider patches
in W4, all against the same hidden verifier in `cognitive-os-sandbox:sprint-5`. Every outcome
produced a full artifact and a `coding.outcome_recorded` event; every artifact row has bytes
and every artifact citing an event resolves.

*Evidence:* `sprint-21c3-w3-campaign.json` → `execution`;
`sprint-21c3-w6-operations.json` → `integrity_report`.

### 6. At least 200 unique outcomes with verifier evidence, no duplicate identity counted twice — **PASS**

**214** unique outcomes: 150 offline coding outcomes (30 tasks × 5 strategies) plus 64
re-executed governed benchmark cases across six domains. `duplicates_excluded: 0`,
`unique_outcomes: 150` against `runs_recorded: 150`, and the W6 resume replayed 150 of 150
without adding one.

*Evidence:* `sprint-21c3-w3-campaign.json` → `execution`, `benchmark_replay`;
`sprint-21c3-w6-operations.json` → `campaign_resume`.

### 7. At least 50 trajectories over at least 20 tasks and two strategy families — **PASS**

**60** compiled trajectory manifests, 60 distinct compilation identities, **30** unique tasks,
four strategy families (`incomplete_a`/`correct_narrow` and `incomplete_b`/`correct_robust`),
0 failed compilations at the time of compilation.

*Evidence:* `sprint-21c3-w3-campaign.json` → `trajectories`.

Recompiling those sixty manifests now refuses, because they carry a wall-clock `created_at`
(W6-F1, deviation W6-D1). The trajectories themselves are intact and counted; what is not
available is after-the-fact verification *of these particular rows* by recompilation. Stated
here rather than left to the report.

### 8. Group-aware split, duplicate detection, similarity checks and universal-patch adversary find no leakage — **PASS**

0 duplicate candidate sources, 0 near-clone pairs in any of the five strategy sets under AST
and token normalization, 0 cross-task transfers that solved another task out of 120 attempted.
420 corpus items routed across 30 groups with **0 groups crossing a split**, re-verified by SQL
against the store rather than by the process that wrote them.

*Evidence:* `sprint-21c3-w2-task-corpus.json` → `leakage_and_shortcuts`;
`sprint-21c3-w3-campaign.json` → `corpus`; `sprint-21c3-w6-operations.json` →
`integrity_report.checks.no_repository_group_crosses_a_split`.

### 9. OpenRouter non-critical, single-attempt, ZDR-relaxed, exact denominators — **PASS**

`maximum_attempts` is 1 and no retry loop exists. OpenRouter is off the critical path: the
200-outcome corpus was complete before any provider was called. Denominators, exactly:

| Provider | correct / attempted | correct / executed | boundary | schema-invalid | diff-invalid |
| --- | --- | --- | --- | --- | --- |
| claude-code | 9/10 | 9/9 | 0 | 0 | 1 |
| codex-cli | 6/10 | 6/6 | 0 | 0 | 4 |
| openrouter | 0/10 | 0/0 | 9 | 0 | 1 |

*Evidence:* `sprint-21c3-w4-provider-campaign.json` → `statistics`, `reliability`.

### 10. Real governed runs are evaluation-only, zero enter a training snapshot — **PASS**

960 observations, all `real_governed_run`: 896 accepted and evaluation-eligible, 64
quarantined and eligible for nothing. `real_runs_in_training: 0`, and a training snapshot
containing a real governed run was **refused** rather than filtered. Re-checked as an
invariant over the store, not a counter in the campaign process.

*Evidence:* `sprint-21c3-w3-campaign.json` → `learned_evidence`;
`sprint-21c3-w6-operations.json` → `integrity_report`.

### 11. Self-play corpus candidates pass rights, lineage, classification and split checks without training — **PASS**

420 items routed, all `allowed`, 0 quarantined, `training_actions_started: 0`,
`real_run_items_in_corpus: 0` — self-play material and real-run evidence never mix.

*Evidence:* `sprint-21c3-w3-campaign.json` → `corpus`.

30 task-package identities written by the pre-W3-F2 pipeline were reported as already present
and left alone rather than overwritten (deviation W3-D2), which is why the routed total is 420
and not 450.

### 12. Pinned local MiniLM producing normalized 384-dimensional CPU embeddings with full evidence — **PASS**

`sentence-transformers/all-MiniLM-L6-v2` at revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, Apache-2.0 by the model card at that revision,
tree digest `98eb3ae4df320d0b721902aabef795cafb36c3a516f036e92e2b046f55ef4229` over eleven
files. Runtime is `local_files_only=True`; the only downloading path refuses any other
revision and any relative destination. The model is not committed.

*Evidence:* `sprint-21c3-w5-retrieval.json` → `model`; ADR 0089;
`docs/operations/local-embedding-model.md`.

### 13. Frozen retrieval benchmark passes the declared thresholds; hash embeddings stay test-only — **PASS**

60 records, 60 queries, five query shapes, six families, manifest hash
`c9d2ac44731e81f2443545111c8e4832f848d63b68557862a7319cdd8beeca9d`.

| §4.15 threshold | Required | Measured |
| --- | --- | --- |
| recall@5 | ≥ 0.80 | **0.9167** |
| MRR@10 | ≥ 0.65 | **0.7105** |
| recall@5 over deterministic | ≥ 0.15 | **0.4584** |
| cross-group leakage | 0 | **0** |
| identical rankings on repeat | yes | **yes, all four arms** |

The deterministic hashing provider is labelled `non-production hashing vector` wherever it
appears, and `build_embedding_provider` raises rather than substituting it.

*Evidence:* `sprint-21c3-w5-retrieval.json` → `arms`, `thresholds`.

### 14. Full and half precision compared on identical vectors and queries; decision recorded — **PASS**

Same 60 vectors, same 60 queries, temporary `vector(384)` and `halfvec(384)` tables with HNSW
on both. Half precision loses nothing measurable — identical rankings, top-10 agreement 1.000,
better p95 — and still fails §4.16's first condition: **32.4%** total storage saved against
35% required, because the index does not shrink with the column. Decision: float32,
**migration `0016` not created**, scale trigger recorded in ADR 0089.

*Evidence:* `sprint-21c3-w5-retrieval.json` → `precision_comparison`, `thresholds.section_4_16`.

### 15. Health, restart, backup/restore, artifact verification, resume, replay, CI and the full local matrix — **PASS**

19 of 19 matrix commands passed, **0 skipped**. Backup and `--test-restore` verified 8500
artifact files and every history hash. A PostgreSQL restart changed no count and no check.
Resume replayed 150 of 150 with 0 duplicates. Retrieval reproduced byte-for-byte after a
backup, a test-restore and a restart. Remote CI: 29 of 29.

*Evidence:* `sprint-21c3-w6-matrix.json`; `sprint-21c3-w6-operations.json`.

The backup path was exercised in anger, not only as a drill: W6-F2 erased the evidence store
twice and both wipes were recovered in full from it.

### 16. Protected merge, post-merge CI, annotated tag, remote verification, report, gate assessment, D1 handoff — **OPEN**

Not a failure — not yet done. The PR is open and in draft with 29 of 29 checks green on
`0bd490b`; the report, this assessment and the D1 handoff are written; the merge, the
post-merge `main` CI and the `sprint-21c3-reality-baseline` tag remain.

This row is updated when S21C3-073 completes, and not before.

## Limitations that remain explicit

- **No second reviewer.** The repository has one collaborator and
  `required_pull_request_reviews` is disabled. No review is fabricated and no protection
  control is weakened to compensate. Carried forward from C1 and C2.
- **The new `reality-inputs-core` lane is not in the required-checks list.** 27 contexts are
  required; the branch now runs 29. Adding it would change branch protection, which is an
  operator decision, not one this sprint takes on its own.
- **The inconsistent development Artifact Store pair is untouched, not repaired.**
  Fingerprint `7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf` over 5 files,
  identical at C1, C2, W0 and every wave of C3. Remediation is proposed, not executed.
- **Sixty W3 trajectory manifests cannot be verified by recompilation** (W6-D1).
- **The provider corpus cannot rank frontier providers.** Thirty single-edit tasks sit inside
  both CLI providers' capability; 15 of 15 executed patches were correct. That says the tasks
  are easy for them, not that the hidden suite is weak — the same suite failed 90 of 150
  offline runs.
- **Retrieval quality is not learned behaviour.** recall@5 of 0.917 on 60 records is a
  prerequisite for D1, not downstream uplift, anti-forgetting evidence or shadow safety.
