# Sprint 21D4 report — Selective Correction Ranking and Searchable-Surface Retrieval

- Branch: `feature/sprint-21d4-selective-correction-ranking`
- Pre-registration: revision 4, SHA-256
  `526d48f83d696290f3ccbb7d06002026d4aa7c05b65c33d95f87c362f83461a9`
- Gate status: [Gate L2 assessment (D4)](gate-l2-d4-assessment.md) — **does not pass**
- Execution log: [Sprint 21D4 execution](sprint-21d4-execution.md)
- Migration head: `0015`, unchanged. `0016` remains unallocated.

## 1. What the sprint set out to do

Sprint 21D3 stopped at the selection door. Its frozen k-NN grid reached no setting that made
zero confident errors while answering often enough, and D3's own handoff named the residual as
capacity rather than representation. D4 was the closing remediation sprint for Gate L2, and it
had exactly two questions to answer.

**Can the frozen learner be made *selective*?** Not "can it be more accurate" — can it be given
a per-decision confidence threshold above which it is never confidently wrong, and does anything
useful remain above that threshold?

**Can retrieval find anything, once it is allowed to see anything?** D3 measured that its sixty
repair trajectories were one document to every ranking arm, and concluded that improving an arm
cannot widen a surface. D4 had to make the contract change D3 named and deliberately did not
make.

The two branches were independent after W0 by design: a correction stop does not cancel the
retrieval branch, and a retrieval failure does not authorise correction activation.

## 2. The correction to D3's arithmetic

Before either experiment, D4 published an erratum, and it changed what every D3 number means.

Over all twenty-four D3 settings, `ood_answered` is exactly six times `clean_answered`. Six
semantics-preserving transformations of one group encode to **one** fitted vector by
construction, so **D3's 120 metamorphic ranking decisions were 20 decisions replicated six
times**. Observing zero errors in 20 decisions bounds the true error rate at 13.9% with 95%
confidence, not at zero. Gate L2 condition 20's 1% ceiling is an observed-rate requirement, and
D4 reports the bound beside it rather than claiming the bound is met.

Revision 4 makes that impossible to repeat quietly. A decision set now reports the triple —
nominal, independent, replicated — independence is equality of the fitted vector, and every
accuracy, error and coverage rate divides by the independent count and names it in the stored
bytes. The published schema refuses a payload that omits the triple, so it is not only the
producer that enforces it.

**The corrected denominator does not rescue D3.** The full 24-setting grid was replayed under it,
408 derived values recomputed, and every one reproduced. No setting reached zero confident errors
even over its twenty independent decisions; the count ranges from 2 to 6. D3's stop was not an
artefact of counting replicas.

## 3. The correction branch, and its answer

W2 authored **100 calibration groups** — 400 four-candidate outcomes, executed rather than
declared — sealed 720 feature records before the first container started, materialised two
explicit snapshots, and measured the risk–coverage curve at two fitting volumes. It reached the
floor the wave exists for: **100 independent decisions, 0 replicated.**

| | 200 rows / 50 groups | 320 rows / 80 groups |
|---|---:|---:|
| best first-choice rate | 0.735 | 0.712 |
| median first-choice rate | 0.680 | 0.622 |
| cells beating the strongest deterministic baseline | 72/72 | 72/72 |
| fewest confident errors in any cell | 13 | 17 |
| **zero-error coverage** | **0** | **0** |

**The grid carries signal and cannot be made selective.** All 144 cells — 24 settings × 3
operating points × 2 volumes — beat the strongest deterministic baseline at 0.56 to 0.73 against
0.52. Not one reaches zero confident errors on a non-empty admitted set, so all 48 zero-error
derivations return no point and the selection is a typed null.

The stop kind is **`hypothesis_class_bound`**, not `volume_bound`, and the difference is
measured rather than argued: zero-error coverage is exactly zero at *both* volumes. There is no
non-zero coverage that more evidence could grow. A selective ranker needs a threshold above which
it is never confidently wrong, and this hypothesis class has none on this representation.

## 4. The retrieval branch, and its answer

W3 made the contract change, decided the comparator D3 left irreproducible, and resolved a fresh
sixty-group holdout.

**The surface widened, and the number moved.** One additive `search_terms` field — excluded from
`structural_hash` and from `ExperienceGraphNode.label`, filled from canonical identifiers
resolved out of the artifact store through the released alpha-normaliser — took the distinct
document count from D3's **1 of 60** to **41 of 60**. Ninety-four of 120 graphs carry terms; ten
candidates carry none, because they are repairs written in pure arithmetic over their own
parameters and the normaliser leaves nothing of those.

**The comparator has a budget instead of a clock.** The released bounded-GED arm returns 28.0
under a 90 ms clock and 29.0 under a 5 ms clock on the same two graphs, measured on all eight of
the largest stored pairs — which is why three sprints of numbers for that arm cannot be replayed.
Under a fixed iteration budget of one, 140 comparisons agreed with themselves across two passes.

**No arm met the floors.**

| arm | Recall@5 | MRR@10 |
|---|---:|---:|
| no_memory | 0.0000 | 0.0000 |
| exact_signature | 0.0000 | 0.0000 |
| lexical | 0.6833 | 0.4954 |
| minilm_vector | 0.6500 | 0.4153 |
| minilm_shortlist_plus_bounded_ged | 0.5833 | 0.3278 |
| **reciprocal_rank_fusion** | **0.7500** | 0.4911 |
| uniformly random chance baseline | 0.5768 | 0.3317 |
| **floor** | **0.70** | **0.50** |

The fusion arm clears the recall floor and misses the MRR floor by **0.0089**. Under first-failure
precedence that is a near miss, not a pass, and nothing was reopened to close it: fusion variants
0, widths 0, weights 0, metrics 0, holdout members added 0.

Beside D3's holdout every arm moved up, and D3's arms all sat at or below a uniformly random
ranking where D4's clear it. **This is not a controlled comparison and must not be read as one:**
the pool is different, the comparator changed, and the surface widened, all at once. No ablation
was run, because the holdout is read once.

The advisory boundary was proved anyway, which is the point of proving it: six mandatory bundle
sections are byte-identical whether or not retrieval contributed, no advisory candidate is
pinned, required or evidence, none carries an executable body, an empty set degrades rather than
fails, and all four ways of breaking the store end at `UNVERIFIED` without raising.

## 5. What the negative result did not stop

Everything downstream of a selected candidate is recorded as `not_opened` against one stop hash,
`5caa48970898d180…`, over twenty-six dependent tasks. Everything the backlog makes unconditional
ran.

- **The condition-20 payload is stricter than it was.** The metamorphic/OOD gate row now carries
  nominal and independent decision counts and the calibration certificate hash, filled from a
  census rather than from two integers a caller computed. The same collapse cannot recur
  undetected.
- **Operations ran in full.** Provisioning at migration `0015` with no `0016`; backup, container
  restart and restore into an isolated database reproducing counts, hashed rows, both resume
  inputs and 3,990 blob rehashes; a twelve-class integrity report clean with both authorities;
  22 damage cases all failing closed; five predecessor stores unchanged.
- **The release matrix is complete.** 30 rows, 30 passed, 0 skipped, 0 structural findings.
- **Rollback was proved where the backlog says to prove it.** S21D4-075 ran on the isolated
  lifecycle fixture: restoration survives a restart, the failed-canary refusal survives one too,
  the rollback deletes no evidence, and the target is not a parameter a caller could pass.

## 6. Findings

| ID | Subject | What it was |
|---|---|---|
| W0-F1 | the D3 learned store | Truncated by the lifecycle smoke behind a `_test` suffix check; 280 D3 observations and both revision-3 datasets irrecoverable, because every backup was taken after. |
| W0-F2 | the fix for W0-F1 | The content fence counted rows through an f-string over a table-name loop; not exploitable, rewritten as two literal queries rather than suppressed. |
| W2-D9 | MiniLM embeddings | Batch-composition dependence, real and measured at 6.7e-08 — enough to move a vector hash. |
| W2-D10 | a re-encode claim | Checked less than it said; amended rather than edited. |
| W3-D1 | the `searchable_surface` contract | Its two sentences cannot both hold: a field unconditionally inside `content_hash` makes every graph stored before it unloadable, measured at `a8db90af88181437` → `399a7fc9276870c5` over 140 pairs. Amendment 2 records it. |
| W3-F1 | §4.5's own claim | It calls the widened surface "the minimum that makes sixty repair trajectories sixty documents". It makes 41. |
| W4-D1 | D3 promotion payloads | A payload asserting `metamorphic_ood: passed` without denominators is now refused at load. Deliberate: it asserts exactly the claim the erratum disproved. |
| W7-F1 | every truncating path | D4-W0-F1 fixed the mechanism in two places and wrote "one rule for both truncating paths". There were **eleven**. Five of the other nine truncated the D4 evidence store during a release-matrix run; three more were found by a completeness scan, and one of those truncates the append-only store itself. |
| W7-F2 | W7-F1's own fix | Placed behind a SQLAlchemy import, which made a pure environment check uncollectable in a credential-free CI lane. Found by CI, not by reading. |

Beyond those, twelve smaller defects were caught and fixed inside their waves, and the majority
share one shape: **a check that passes without touching its question.** A tautological assertion,
`"None"` written as a threshold string, an `all()` over an empty set reporting
`byte-identical: True (0 compared)`, a precedence check that sorted a tuple by its own index, a
`B101` assert, a negative matrix row that refused for the wrong reason, and a test that made the
release command need two runs to go green. Each was found by running the thing and reading the
output against the question it claims to answer.

## 7. Recovery, and why W7-F1 is a finding rather than a second loss

The W7-F1 truncation erased 1,076 committed observations, 9 datasets and 18 artifact lineages
from the D4 evidence store. All of it came back.

W7's own backup step had run three minutes earlier, and its dump hash was already recorded by the
clean operations run that preceded the damage. The backup was restored over the evidence database
through the released restore script; afterwards the store reports 1,076 observations, 9 datasets,
18 lineages, 2,812 events, 3,990 blobs, zero components, and a twelve-class integrity report that
is clean with both authorities supplied.

D3's identical loss was irrecoverable because every backup was taken *after* the erasure. The
difference is not care; it is ordering. That is worth stating plainly, because the fence now in
place is what makes the ordering stop mattering.

## 8. Limitations

- **A passing D4 would have measured one surface.** Correction-candidate ranking, on authored
  tasks, under a frozen encoder. It would not have been evidence about any other surface.
- **The corpus is authored, not harvested.** 100 calibration groups and 60 retrieval groups were
  written for this sprint. They are executed and verifier-labelled, but they are not real
  governed traffic and the distribution they represent is the one that was written.
- **The retrieval comparison across sprints is not controlled.** Pool, comparator and surface all
  changed together. The 0.0089 is a real measurement on D4's holdout; the improvement over D3 is
  not attributable to any one of the three.
- **The widened surface reaches 41 of 60, not 60.** Ten candidates carry no terms at all, so the
  ceiling this contract change can reach is lower than §4.5 assumed.
- **`hypothesis_class_bound` is a statement about this hypothesis class on this representation**,
  measured over 100 independent decisions at two volumes. It is not a statement that selective
  prediction is impossible here.
- **Nothing below the selection was exercised against a real artifact.** The loader, resolver,
  sequencer, verification and activation surfaces D3 built were not re-proved by D4, and three
  Gate L2 conditions D3 met against a contract fixture are recorded here as not opened rather
  than inherited.

## 9. Outcome

Gate L2 does not pass: 12 met, 1 met as a rejection, 15 not opened, 1 pending the release, **0
failed**. Gate D1 conditions 6 and 7 are closed by the selection stop; condition 15 remains open
on its own evidence. Sprint 22A stays blocked.

Both branches returned a hash-bound negative result, and neither is a guess about why. The
correction stop is a measured hypothesis-class bound over 100 independent decisions. The
retrieval stop is a measured 0.0089 on a surface whose widening is itself measured. A successor
sprint that wants to move either number has a residual to work against rather than a hunch —
which is what [the handoff](sprint-21d5-handoff.md) hands over.
