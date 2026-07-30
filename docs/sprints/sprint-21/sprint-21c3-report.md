# Sprint 21C3 report — Reality-Grade Learning Inputs

- Branch: `feature/sprint-21c3-reality-inputs`
- Parent: `sprint-21c2-provider-baseline` → `94abe263c8f26f36c8f8c3bc7b86859c14c1f291`
- Alembic head: **0015** at the start and at the end
- Storage: the isolated C3 pair (`cognitive_os_s21c3_test`, `cognitive-os-data/artifacts-s21c3`)
- Gate C3: **pass** — conditions 1–15 evidenced in the assessment, condition 16 closed by the
  verified release annotation
- **Gate L2: closed**

> Reality-grade inputs and local semantic retrieval are available, but useful learned
> behaviour has not yet been demonstrated.

## 1. What was delivered

Seven waves, 40 backlog items, one implementation PR (#215).

| Wave | Items | Result |
| --- | --- | --- |
| W0 | 000–004 | verified C2 parent, ADR 0088, isolated C3 storage |
| W1 | 010–014, 021–023, 064 | one task end to end through sandbox, artifact, event, intake; draft PR opened |
| W2 | 020–024, 030 | 30 tasks, 120 candidates, 420 container runs, leakage checks green |
| W3 | 031–037 | 214 outcomes, 60 trajectories, 420 corpus items |
| W4 | 040–043, 032 | data-policy defaults, preflight, 30 live provider outcomes |
| W5 | 050–056 | pinned MiniLM, frozen retrieval benchmark, float32 decision |
| W6 | 060–065 | operator CLI, integrity report, restore, resume, offline CI lane, release matrix |
| W7 | 070–074 | documentation, gate assessment, this report, D1 handoff, release |

## 2. Statistics

**Tasks.** 30 packages, 6 families, 5 each, 30 repository groups. Byte-identical regeneration;
identities are uuid5 over template and seed. Apache-2.0, project-owned, rights verified per
task with an evidence hash. In the real sandbox: 30 of 30 baselines pass the published suite
and fail the hidden one — the property the whole sprint rests on.

**Outcomes.** **214** unique, against a threshold of 200: 150 offline coding outcomes
(30 tasks × 5 strategies) and 64 re-executed governed benchmark cases across six domains.
`duplicates_excluded: 0`. Of the 150: 60 hidden-passed, 90 hidden-failed, 0 published-suite
failures, 0 strategy disagreements, 0 main-worktree mutations.

**Corrections.** 60 trajectory manifests over 30 unique tasks and four strategy families,
60 distinct compilation identities.

**Corpus.** 420 items routed, all `allowed`, 0 quarantined, 30 groups, **0 groups crossing a
split**, `training_actions_started: 0`, `real_run_items_in_corpus: 0`.

**Learned observations.** 960 in the C3 store at release, all `real_governed_run`: **896**
accepted and evaluation-eligible, 64 quarantined and eligible for nothing. `real_runs_in_
training: 0`, and a training snapshot containing a real governed run was refused rather than
filtered. The store was not emptied before the campaign (deviation W3-D1), so this total spans
every wave; `observations_from_this_campaign` is reported separately in each wave's evidence.

**Rights and leakage.** 0 duplicate candidate sources; 0 near-clone pairs under AST and token
normalization in all five strategy sets; 0 of 120 cross-task transfers solved another task;
0 control tokens in any provider-visible surface, prompt, or retrieval query.

**Verifier.** Every candidate ran in `cognitive-os-sandbox:sprint-5` against the same hidden
suite mounted read-only at `/verification`, never through the tool plane.

**Embeddings.** MiniLM-L6-v2 at `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions,
L2-normalized, CPU, Apache-2.0, tree digest `98eb3ae4…4229`. 60 records embedded in 0.88 s;
peak RSS 742 MiB.

**Retrieval**, on 60 frozen queries:

| Arm | recall@5 | recall@10 | MRR@10 | nDCG@10 | p95 |
| --- | --- | --- | --- | --- | --- |
| lexical | 0.017 | 0.017 | 0.017 | 0.017 | 2.5 ms |
| lexical (OR) | 0.250 | 0.483 | 0.231 | 0.279 | 19.9 ms |
| deterministic *(non-production)* | 0.458 | 0.617 | 0.378 | 0.416 | 20.2 ms |
| **MiniLM** | **0.917** | **0.967** | **0.711** | **0.770** | 24.3 ms |

All §4.15 thresholds pass; margin over the hashing provider 0.4584 against a required 0.15.

## 3. OpenRouter correctness, with the exact denominator

| Provider | correct / attempted | correct / executed | boundary | schema-invalid | diff-invalid |
| --- | --- | --- | --- | --- | --- |
| claude-code | 9/10 | 9/9 | 0 | 0 | 1 |
| codex-cli | 6/10 | 6/6 | 0 | 0 | 4 |
| **openrouter** | **0/10** | **0/0** | **9** | 0 | 1 |

One attempt per task, frozen assignment decided before execution, no retries and no fallback.
OpenRouter's nine boundary failures were `ProviderInvalidResponseError` inside the adapter —
the free route returned a body the client refused before any answer existed. The tenth reply
parsed and produced a diff whose hunk counts disagreed.

OpenRouter was never on the critical path: the 214-outcome corpus was complete before any
provider was called. A paid or pinned route is **not** justified on these numbers, and would
need its own ADR — `maximum_spend_usd` defaults to zero everywhere.

All 15 executed patches were correct. That says these thirty single-edit tasks sit inside both
CLI providers' capability, not that the hidden suite is weak: the same suite failed 90 of 150
offline runs, including 60 patches written to be wrong. **This corpus must not be used to rank
frontier providers.**

## 4. The data-policy amendment

ADR 0088 classifies this project's development material as `public` and makes
`require_zero_data_retention: false` and `allow_data_collection: true` the tracked defaults.

The C2 shape was a strict default plus a per-fixture waiver. Thirty waivers for material the
project already publishes under Apache-2.0 is not a control; it is a prompt that teaches an
operator to click through. No free OpenRouter endpoint offers ZDR, so the strict setting bought
no confidentiality and refused every free route — it made the honest configuration the one an
operator had to override.

What did **not** change: HTTPS-only base URLs, `OPENROUTER_API_KEY` as the only key source,
free-only routing, `maximum_spend_usd: 0.0`, one attempt per task, and the source-rights
decision as an operator input with an evidence hash. Credentials are excluded from provider
requests by the prompt boundary, not by these flags. Internal and restricted material still
requires the strict values; ADR 0087 governs that and is unchanged.

Measured: **0 credentials and 0 control tokens in any of the 30 live provider requests.**

## 5. Storage decision

float32 stays. Migration **0016 is not created**.

Half precision loses nothing measurable on identical vectors and queries — identical rankings
on all 60, top-10 agreement 1.000, slightly better p95 — and still fails §4.16's first
condition: 32.4% total storage saved against 35% required, because the HNSW index does not
shrink with the column. The table alone falls 41.7%. The rehearsed conversion took 6.8 ms,
which is the real argument: a change this cheap later has no reason to happen now.

Scale trigger, recorded in ADR 0089: 100 000 embedded records, or 1 GiB of vector storage
including indexes, whichever comes first.

## 6. Artifact Store isolation

The inconsistent development pair (`cognitive_os_dev` +
`/home/palkouser/projekt/cognitive-os-data/artifacts`) received **zero C3 writes**. Its
path-and-size fingerprint is
`7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf` over 5 files, identical at
C1, C2, W0 and after every wave of C3. It was not deleted, repaired, or rewritten to make a
verifier pass; remediation remains proposed and needs separate operator authority.

The algorithm behind that fingerprint used to live only in shell history. It is now
`cognitive_os.coding.reality_integrity.fingerprint`, with a test that a single added file
changes it.

## 7. Findings

| ID | Wave | What it was |
| --- | --- | --- |
| W1-F1 | W1→W3 | intake stamped its own clock onto a hash-bound record, so re-offering the same outcome raised `idempotency_key_reused`. Fixed by giving `GovernedOutcomeReference` an `occurred_at` and deleting the clock parameter. |
| W1-F2 | W1 | `describe()` missing from the artifact port's fixtures. |
| W2-F1 | W2 | two tasks in one family shared a second edge case; redesigned around genuinely different ones. |
| W2-F2 | W2 | a control path is a control token only when it is absent from the visible files. |
| W2-F3 | W2 | every candidate now round-trips through `parse_unified_diff` and `apply_file_patch`. |
| W3-F1 | W3 | corpus splits made group-aware via `split_group_key`, without changing any pre-C3 caller. |
| W3-F2 | W3 | task manifests hashed a wall clock and a fresh artifact row, so resume rewrote the corpus. Campaign epoch plus bundle passthrough: 156 s → 8 s. |
| W3-F3 | W3 | campaign runner widened from `DockerSandbox` to `SandboxPort`; the `type: ignore`s are gone. |
| W4-F1 | W4 | 32 false control-token leaks — published test names reused by the hidden suite, and correction lines that were prefixes of baseline lines. 32 → 0, planted token still found. |
| W4-F2 | W4 | both CLI adapters hardcoded the advisory schema; they now honour `request.response_schema`. |
| W4-F3 | W4 | one `malformed` bucket conflated boundary failures with unusable diffs. Split into three. |
| W4-F4 | W4 | `apply_file_patch` raises rather than returning `None`; every apply failure is now recorded, not crashed on. |
| W6-F1 | W6 | trajectory compilation read a wall clock, so no trajectory could be verified by recompilation. Campaign epoch, the third plane to inherit this defect. |
| W6-F2 | W6 | **the release matrix erased the C3 evidence store, twice.** The integration fixture truncates the whole schema and guarded only on the name ending `_test` — which the evidence store also does. Recovered in full from the backup taken minutes earlier. Fixed in the fixture, the matrix and CI. |

## 8. Deviations

| ID | What was not done, and why |
| --- | --- |
| W1-D1 | recorded in the W1 evidence file. |
| W2-D1 | recorded in the W2 evidence file. |
| W3-D1 | the isolated C3 store was **not** emptied before the campaign. It held earlier waves' rows, so the report records `store_before_campaign` and reports `observations_from_this_campaign` separately instead of deleting data to make a number clean. |
| W3-D2 | 30 task-package identities written by the pre-W3-F2 pipeline were left in place rather than overwritten. Routed total is 420, not 450. Rewriting recorded corpus material to reach a rounder number is the one thing the corpus plane must not do. |
| W6-D1 | the 60 trajectory manifests compiled in W3 keep their wall-clock `created_at` and are not rewritten. Their `compilation_id` is content-derived, so recompilation cannot match them after the W6-F1 fix; that refusal is correct behaviour reporting a real difference. Affects recompilation only — outcomes, counts, corpus, splits, observations and rankings all reproduce. |

## 9. Limitations

- **No second reviewer.** One collaborator, `required_pull_request_reviews` disabled. No review
  is fabricated and no protection control is weakened to compensate. Unchanged from C1 and C2.
- **Branch protection is unchanged.** 27 required contexts; the branch now runs 29. Adding the
  new `reality-inputs-core` lane to the required list is an operator decision.
- **The provider corpus cannot rank providers.** See §3.
- **Sixty W3 trajectories cannot be verified by recompilation.** See W6-D1.
- **The development Artifact Store pair is untouched, not repaired.** See §6.

## 10. Is there enough honest data for D1?

**Yes, for pre-registering a learning surface. No, for claiming uplift.**

What D1 can rely on: 214 verified outcomes with immutable artifacts and event linkage; 60
failed-to-corrected trajectories over 30 tasks; 420 rights-clean corpus items in group-aware
splits with zero crossing; 896 evaluation-only observations that no training snapshot may
touch; a pinned local embedding model with measured retrieval quality; and an evidence set
that reproduces after backup, restore and restart.

What it may not do with it: treat recall@5 of 0.917 on 60 records as downstream uplift, treat
15 of 15 correct provider patches as a provider ranking, or treat corpus volume as
anti-forgetting evidence or activation authorization. Those are D1's to demonstrate, on
groups frozen here and never tuned on.

Gate L2 remains closed.
