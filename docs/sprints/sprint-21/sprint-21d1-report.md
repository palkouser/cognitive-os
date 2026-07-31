# Sprint 21D1 report — Experience Memory Graph and the pre-registered learning surface

- Branch: `feature/sprint-21d1-learning-surface-emg`
- Parent: `sprint-21c3-reality-baseline` → `05809446c726444146d85aad22808e10ce87ca3e`
- Alembic head: **0015** at the start and at the end; `0016` still unallocated
- Storage: the isolated D1 pair (`cognitive_os_s21d1_test`, `cognitive-os-data/artifacts-s21d1`)
- Release: PR #217 squash-merged to `b46c2fcd77d568148ce2046f3ec7c4369bd4a8b9`; main CI run `30657167717`, 30 of 30 success; annotated tag `sprint-21d1-emg-baseline`
- Gate D1: **does not pass** — conditions 6, 7 and 15 open, the other eighteen met
- **Gate L2: closed**

> The Experience Memory Graph exists, is verifiable, and is advisory. Whether it is useful is
> not yet demonstrated, and this sprint says so in numbers rather than in adjectives.

## 1. What was delivered

Eleven waves, 41 backlog items, one implementation PR (#217).

| Wave | Items | Result |
| --- | --- | --- |
| W0 | 000–003 | verified C3 parent, three stores separated, frozen C3 inventory |
| W1 | 004, 010–015 + E1.5 | four surfaces audited, leakage validator, pre-registration with **no primary surface** |
| W2 | 016, 020–026 | 214-outcome canonical view, four-rung ladder, seeded paired bootstrap |
| W3a | 034 | 60 historical coding pairs resolved, zero legacy bytes mutated |
| W3b | 030–033 | 20 fresh logic and mathematics pairs executed and compiled |
| W3c + VS | 035 | 80-pair set frozen; one pair end to end through the whole vertical slice |
| W4 | 040–047 | all 80 pairs projected, edit paths round-tripped, EMG root persisted |
| W5a | 050–054 | five arms over 80 frozen queries; budget and latency measured |
| W5b | 055–057 | advisory Context Builder path, fail-closed on every axis |
| W6a | 060–062 | residual taxonomy, dependency and licence review, **ADR 0090: FGW no-go** |
| W6b | 063–065 | operator commands, unified integrity report, restart/backup/restore |
| W6c | 066–067 | credential-free graph CI lane, 22-row verification matrix |
| W7 | 070–074 | documentation, gate assessment, this report, D2 handoff, release |

13 commits, 77 files, 20 of them code or CI. Four new source modules, one extended CLI, one
extended integrity report, 160 tests in the graph and learning packages.

## 2. The primary surface: a measured negative result

Four candidate surfaces were audited against Gate D1's conditions 6 and 7 **before** any
held-out metric was read. None qualified.

| surface | eligible samples | changeable decisions | verdict |
| --- | --- | --- | --- |
| `governed.outcome_triage` | 214 | 0 | rejected — the label is a function of a forbidden field |
| `experience.strategy_selection` | — | 0 | rejected — no decision can change by construction |
| `experience.correction_ranking` | 120 | — | deferred — 120 against a threshold of 200 |
| `experience.correction_context` | — | — | selected as **secondary** |

`governed.outcome_triage` is the instructive one. `candidate_strategy` predicts the verifier
label with **no error at all** on all 150 enumerated coding outcomes — a perfect oracle, and a
field that must never be a feature. Removing both construction oracles leaves the identical
2-of-5 pattern on every task: exactly 60/60 on the coding half, no rung above 0.5000, and group
frequency at **0.0000**, which is not weak signal but anti-informative. The benchmark half is
single-class, 64 of 64 passed.

The operator decision was to declare the primary surface unavailable and report it, rather than
amend the `§3.3` shortfall cap or breach it. `S21D1-016` therefore generated **zero** new
outcomes, made zero provider calls and zero network calls: sampling more of the same evidence
cannot fix a surface whose label is determined by a field the features may not contain.

The contract enforces the honesty rather than relying on it. `SurfaceSelectionDecision` accepts
an absent primary surface only alongside a recorded reason, and `SurfaceActionCostMatrix`
refuses any cost assignment under which abstaining or requesting repair is cheaper than
verifying a candidate the verifier would reject — which is what would let a predictor quietly
become an acceptance authority.

**Denominator reconciliation.** The released 214 is exactly 150 enumerated coding outcomes plus
64 distinct accepted governed benchmark cases, matching the released histogram. The C3 evidence
store was never emptied between waves, so raw queries over it inflate roughly threefold; every
D1 count anchors to enumerated campaign identities instead.

## 3. The graph set

80 failed-to-success pairs: 60 historical coding corrections and 20 fresh logic and mathematics
cases. Three domains, 50 task signatures, 50 groups, **zero group crossing**, 100% source
resolution.

The 60 historical pairs resolve every required event and artifact with zero legacy bytes
modified, and each carries `legacy_recompilation_unavailable`. The 20 fresh pairs pass
byte-identical Experience Compiler recompilation against a fixed epoch.

All 80 edit paths round trip. The comparison is **structural**, and that is the sprint's main
design finding: `content_hash` includes each node's `source_hash`, and the two sides of a pair
are two different runs whose evidence bytes differ at every step. A byte-identical round trip
was therefore impossible by construction, so `ActionDecisionGraph.structural_hash` covers
labelled structure with provenance deliberately excluded. Provenance is verified separately.

Observed against the declared bounds: largest graph 21 nodes of 64 permitted, max depth 20 of
32, zero over-limit graphs, zero bound changes required.

## 4. Retrieval: what the graph arm is worth

Five arms, 80 frozen queries committed before any ranking, every query excluding its own group.
Group identity is one-to-one with task identity in this corpus, so the benchmark is
unseen-task **by construction** rather than by sampling.

| arm | top-5 recall | MRR@10 | nDCG@10 | p50 | p95 | cutoffs |
| --- | --- | --- | --- | --- | --- | --- |
| `no_memory` | 0.0000 | 0.0000 | 0.0000 | 0.06 ms | 0.09 ms | 0 |
| `exact_signature` | 0.0000 | 0.0000 | 0.0000 | 0.06 ms | 0.10 ms | 0 |
| `lexical` | 0.5250 | 0.4145 | 0.3327 | 1.14 ms | 1.78 ms | 0 |
| `minilm_vector` | 0.5375 | 0.4392 | **0.3740** | 15.3 ms | 27.5 ms | 0 |
| `minilm_shortlist_plus_bounded_ged` | **0.6750** | **0.4481** | 0.3438 | 24.7 ms | 1788.9 ms | 60 |

The graph arm wins recall by +0.1375 and MRR by +0.0089 over the strongest arm needing no
structure, and **loses** nDCG by 0.0302. Both of its headline numbers sit below the
pre-registered floor of 0.70 recall and 0.50 MRR, so **condition 15 stays open**. Nothing was
tuned afterwards; the stop rule was written before the measurement for exactly this case.

`exact_signature` returning zero is correct, not broken: every query excludes its own group,
and group identity here is task identity.

### Why the graph arm wins, and why that is less than it looks

The residual analysis replays the frozen benchmark from committed artifacts alone — no database
— and reproduces the published numbers exactly before classifying anything.

Of 26 residual queries, **19** are shortlist-ceiling misses where no relevant pair reached the
ten-candidate shortlist, so the reranker never saw one. Only **7** are ordering errors a better
structural comparator could address.

The graph score is nearly degenerate: exactly **two** distinct values per query and **six**
across the entire corpus. For the 20 fresh logic and mathematics queries every completed
comparison returned the identical `0.525424`. **61 of 80** rankings had the relevant pair's rank
decided by the pair-id tiebreak rather than by the arm. All three regressions are that effect —
in two of them the vector arm had ranked the relevant pair *first* and the rerank pushed it to
seventh, without ever scoring it below anything.

The binding constraint is the shortlist width, not the comparator. Ranking the whole 78-candidate
pool puts every relevant pair within the vector arm's top thirty. Reranker ceiling by shortlist
width: 0.7625 at ten, 0.9000 at fifteen, **0.9750 at twenty**, 1.0000 at thirty.

## 5. The FGW decision

[ADR 0090](../../adr/0090-no-fused-gromov-wasserstein-and-the-shortlist-constraint.md) records a
**no-go**, and no D2 experiment is approved yet. `§4.11`'s conditions, one by one: the structural
error class is named (met); the ceiling clears the 0.05 margin at +0.2250 recall over the
strongest simpler arm (met); the two-second budget and bounded memory are **not** credible,
because the cheaper comparator already spends 60 cutoffs and 1788.9 ms at p95 on 80 pairs with
827 MB peak (not met); no dependency is proposed, so none is evidenced; clean-room is
satisfiable and not a discriminator.

`git diff origin/main...HEAD -- uv.lock pyproject.toml` is **empty**. The whole sprint added no
package. NetworkX stays the optional BSD-3-Clause `semantic-graph` extra with an empty runtime
dependency closure. The EMG preprint is CC BY-NC-SA 4.0; its concepts informed the design and no
code, asset or figure was copied — the four graph modules carry zero external provenance markers.

## 6. Authority and the advisory boundary

Graph results reach the existing Context Builder as `ContextSourceType.EXPERIENCE_GRAPH`,
default trust class `UNVERIFIED`. A candidate earns `VERIFIED` per retrieval by resolving its
hashes, never by belonging to a source type — a source type that granted trust would make a
corrupt store indistinguishable from a healthy one. Candidates are never pinned, never required,
never evidence, and carry no patch body. A non-advisory purpose receives nothing. A verifier
that raises degrades a candidate rather than propagating, so a corrupt store stays visible
instead of looking like an empty corpus. An empty set reports **degraded**, not unavailable.

**No number in this report is a learned benefit and nothing was activated.** No component was
fitted, no threshold reaches a live decision, and Gate L2 is closed.

## 7. Operations

Five graph commands extend `scripts/experience.py`; there is no second operator entry point and
all five read. That is asserted by fingerprinting the store before and after, not by assertion
in prose. Neither store is guessed, and the vector arms require an explicit model rather than
falling back to a hashing vector.

Graph status joins the unified integrity report rather than arriving as a second release report,
with the four failure modes kept apart — bytes never held, bytes that changed, a root that
disagrees with sound bytes, an edit path that stopped reproducing its graph — and legacy
non-recompilation and retriever availability kept as warnings beside them.

Restart, backup and restore ran through the existing scripts. The store fingerprint, every row
count, the artifact digest and all three graph command outputs are byte-identical before the
backup, after a container restart, and after restoring the archive into a separate scratch
database. On a copy of that archive an appended byte is reported as corruption and a deleted
file as a missing artifact, each exiting non-zero.

The verification matrix runs 22 rows, all on their expected exit status, in 306 seconds. Two
rows expect a non-zero status; a zero there would be the failure.

## 8. Findings

1. **A perfect predictor is a red flag, not a result.** `candidate_strategy` predicting the
   verifier label with no error identified a leaked oracle, not a learnable surface.
2. **Structural hashing was forced by the data.** Two runs of the same task never agree byte for
   byte, so edit-path verification had to be structural or no pair could ever round trip.
3. **A contract must not depend on an optional extra.** The DAG invariant validated through
   `networkx` broke every CI lane that synced without `semantic-graph`. Replaced with Kahn's
   algorithm, and the invariant now has a test that runs with `networkx` blocked.
4. **A declared budget has to be enforced with the per-pair timeout reserved.** Checking only
   elapsed time lets a comparison start at the last moment and overrun by its whole timeout.
5. **Re-embedding per query was 936 ms of a 940 ms median.** A caller-owned cache took the graph
   arm to ~25 ms median with repeated-ranking agreement preserved.
6. **One informative bit can beat a fine-grained score, and still not be a ranking.** The binary
   graph split raises recall while leaving 61 of 80 orders to an arbitrary tiebreak.
7. **Optimise the stage that binds.** 73% of the residual is out of any reranker's reach, which
   is what turned an FGW question into a shortlist question.

## 9. Deviations

| id | observed | resolution |
| --- | --- | --- |
| W0-D1 | `postgres_bootstrap_roles.sh` aborts on `ALTER ROLE cogos_owner NOSUPERUSER` | pre-existing, recorded identically in C1/C2/C3; the two D1 databases were created directly. Not remediated — it belongs to the bootstrap script's owner |
| W0-D2 | no script creates evidence databases | recorded, not fixed, same ownership |
| W4-D1 | CI failed on bandit B101: `__main__` self-checks used `assert` in `src/` | moved to `tests/`, 19 tests. bandit had not been run locally before the push |
| W5A-D1 | the query budget was never enforced; p95 3523 ms | the budget is enforced in-arm with the per-pair timeout reserved; p95 1789 ms |
| W6C-D1 | the first matrix run left the artifact root on the evidence pair; five files appeared | caught by the matrix's own before-and-after fingerprint comparison, removed, store returned to its exact 83-file fingerprint, and every test row now gets a scratch store |
| W6C-D2 | the integration database created in W0 was never migrated | migrated to head 0015, 114 tables; the migration check is now a matrix row |

## 10. Limitations

- No primary learning surface exists on frozen C3 evidence. This is a property of the evidence,
  not of the method.
- 60 of 80 pairs are legacy and cannot be recompiled byte for byte.
- 14 of 20 fresh queries carry only a same-domain relevance judgement, reported as tier 2 and
  never blended into a single number.
- Required approving reviews stay disabled because a second eligible reviewer does not exist.
- No D2 holdout exists. Every number here is over the frozen D1 benchmark.
- The reference host is a local CPU-first developer machine with no GPU; latency figures are
  that host's.

## 11. Is the Experience Memory Graph worth keeping?

Yes, and not because it won. It is verifiable end to end: 80 pairs whose bytes hash to their
names, whose roots agree with their stores, and whose edit paths reproduce their successful
graphs after a restart and a restore. It is bounded, it fails closed, and it cannot execute
anything.

What it is not yet is useful, and D1 says so with a number rather than an adjective. The next
lever is named, measured and free: widen the shortlist and re-measure. If the residual after
that is still dominated by ordering errors, the FGW question reopens with evidence behind it.
