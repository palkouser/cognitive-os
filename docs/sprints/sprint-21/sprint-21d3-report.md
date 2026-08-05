# Sprint 21D3 report — Invariant Correction Ranking and Independent Retrieval Closure

- Branch: `feature/sprint-21d3-invariant-correction-ranking`
- Pre-registration: revision 3, SHA-256
  `191b3757ded21a1c2c85459a34902f8dee3f2f35b0979b557f84c1a37fe6a191`
- Gate status: [Gate L2 assessment (D3)](gate-l2-d3-assessment.md) — **does not pass**
- Execution log: [Sprint 21D3 execution](sprint-21d3-execution.md)
- Migration head: `0015`, unchanged

## 1. What the sprint set out to do

Sprint 21D2's bounded k-NN ranked an accepted candidate first in nine of ten calibration groups
and then answered confidently and wrongly when identifiers were renamed and issue text reworded
without changing any contract. D2 could say only that *something* moved under an opaque combined
perturbation.

D3 separated the two questions that D2 had conflated. It built `correction-ranking-v2`: an
alpha-normalised canonical source encoding with six structural scalars and a 384-dimension
embedding of the canonical bytes, removing every channel the D2 diagnostic implicated. Then it
asked, on fresh evidence, whether the invariance defect was *representational* — fixable by
spelling the input differently — or a *capacity* residual that no encoding change reaches.

It also ran an independent second experiment: a fixed equal-weight lexical+MiniLM
reciprocal-rank-fusion arm on a distinct unseen retrieval holdout, to close Gate D1 condition 15.

## 2. The intervention

The v2 feature contract, frozen before any measurement, hashes to
`492c90a5df420de9d1662d17155ac8b28713e69bbd4bbe56208415d6ca076362`. It declares:

- a Python 3.12 AST alpha-normaliser (`cogos-python-alpha-normalizer-v2`) producing canonical
  bytes under a fixed prefix, preserving imports, attributes, builtins, magic names and string
  literals while renaming local bindings to a placeholder grammar;
- **390 fitted channels**: six structural scalars and 384 embedding components, in fixed order;
- **seven removed v1 inputs**, including `query_to_candidate_cosine`, the diff-shape counts and
  the two v1 embeddings;
- six exact invariants and seven fail-closed cases.

## 3. Data

| Role | Groups | Outcomes | Real governed runs |
|---|---|---|---|
| fitting | 50 | 200 | 0 |
| calibration | 20 | 80 | 0 |
| calibration metamorphic | 20 | 120 ranking decisions / 480 candidate outcomes | 0 |
| retrieval holdout | 60 | 120 recorded sandbox runs | 0 |

All authored for D3, transitively separated, with zero groups crossing a role and no near-clone
collision touching D3. Final A, final B and canary catalogues were sealed and **never opened**.

## 4. Results

### 4.1 The correction branch — one null selection

All **24** frozen k-NN settings were measured. The intervention worked on the question it was
designed for:

- **action preservation is 1.00 for every setting**, across all six transformation cases;
- equivalence coverage never falls below clean coverage — maximum loss 0.00;
- the strongest setting reaches **0.65** clean first-choice against the **0.5** deterministic
  `lexical_similarity` baseline, with 0.95 coverage and 14 changed decisions.

And failed on a different one: every setting that answers is confidently wrong on some
semantics-preserving case — **12 to 36 confident errors of 120 decisions** — against a contract
that allows exactly zero. The settings with zero confident errors answered no probe at all.

`decide_continuation` recorded `fail_and_stop`, failure kind `ood_deficient`, and S21D3-039
recorded an **immutable null selection**, hash
`68ea06843d2136e390bf8a4ea0698414932987f5447887187907c45c0dcea876`.

**This is not D2's finding repeated.** D3 separates the two questions and answers both: the
alpha-normalised encoding is *exactly invariant* — the same contract spelled differently reaches
the same first action every time — and what remains is absolute ranking accuracy, which at 0.65
cannot produce a zero-confident-error metamorphic set. **A capacity residual, not an invariance
one.** That is the sprint's principal scientific result.

Maximum measured inference was 34.267 ms against a 250 ms budget.

### 4.2 The retrieval branch — one negative result

Sixty distinct unseen queries against a floor of fifty, executed once under the frozen
revision-3 protocol. No arm cleared either floor; the first failed floor is
`recall_at_5` and `winning_arm` is `null`, hash
`f0b53912055223667c2cca9365b967c439b8599c60e47cbdeac78bfb23378824`.

The cause is recorded rather than guessed: `distinct_after_removing_domain_and_signature: 1`.
All sixty candidates share one searchable body once domain and task signature are removed, so
the lexical arm's ranking is the pair-id tie-break for all sixty queries. **Every arm sits at or
below the chance baseline on recall.** D1 hit the same ceiling, and its 14 tier-2 queries scored
1.0000 only because tier 2 was "same domain" and `domain` is in the searchable text — the same
leak, in the predecessor.

The fusion arm is not weak in itself: on the development set it reached **0.7750/0.4478** with
real complementarity (lexical 42, vector 43, both 25, union 60, fusion 62). The holdout is
where the searchable surface runs out, not the arm.

### 4.3 What was built but not opened

W4 implemented the promotion contract, the v2 artifact, the offline loader, the runtime
resolver, receipt-aware sequencing, evidence-bound verification and activation-time byte
revalidation — then refused final access. The pre-final checkpoint records
`authorised: false`, first failed precondition *S21D3-039 selected one candidate*,
and **20 dependent tasks** bound to one stop hash.

## 5. Incidents and deviations

Every wave found defects and repaired them inside the wave; the execution log records each with
an ID. The ones that changed a result rather than a report:

- **W2-F1** — the frozen MiniLM reads 256 word-pieces and all 280 canonical texts tokenise to
  284–1549. Fed whole, the model saw the docstring and discarded the body. The canonical bytes
  are now embedded in 400-character windows and mean-pooled.
- **W3-F1** — the width-20 bounded-GED arm is **not reproducible**: `networkx.graph_edit_distance`
  under a wall-clock timeout is an anytime search, and four runs produced four different metric
  triples. Deliberately not repaired — revision 3 froze the comparator — but reported per arm.
  The D1 and D2 records for this arm are not reproducible by anyone.
- **W3-F2** — the first holdout resolution **leaked its own judgement**: the graph task signature
  spelled the task family, and relevance *is* the family, so the vector arm returned a perfect
  1.0000. The signature is now the executed task's uuid5 identity, a fail-closed guard refuses
  to rank text naming its own label, and the holdout was re-resolved end to end. The leaked run
  decided nothing.
- **W4-F1/F2** — `SHADOW -> VERIFIED` was reachable without evidence, and activation trusted a
  week-old lineage record rather than the bytes. Both are closed.
- **W7-F1** — the dependency audit raised five advisories; the release owner directed the bump
  and `cryptography` moved 49.0.0 → 50.0.0 in `uv.lock`. No measurement is re-derived under the
  new lock, because neither package is imported by any measurement path.

A recurring class is worth naming: **four separate checks passed while measuring nothing** —
W3-A1's fingerprint of the wrong tree, W4-A1's tautological invariance proof, W4-A2's counters
that counted nothing, W7-A2's migration glob pointing at a directory that does not exist. All
were found by reading the evidence file against the question it claims to answer.

## 6. Limitations

- **The 0.65 figure is a calibration measurement, not a benefit.** The final batches were never
  opened. Nothing in this sprint measures uplift on held-out final evidence.
- **No universal claim.** One surface, authored tasks, a frozen encoder, and no selection.
- **The retrieval result bounds the searchable surface, not retrieval.** `search_text()` carries
  no repaired source, no issue text and no provenance hash; two structurally identical
  trajectories are one document to every arm.
- **The graph arm's historical numbers are irreproducible**, and that includes D1's and D2's.
- **Sprint 22A remains blocked.**

## 7. Stores and operations

Four predecessor Artifact Store pairs received **zero writes** and reproduce their released
fingerprints. D3 wrote only to its own isolated pair: `cognitive_os_s21d3_*` and
`artifacts-s21d3`.

The W7 operations wave proved the evidence survives being moved and that damage to the moved
copy is refused: backup, container restart and isolated restore reproduce counts, hashed rows,
both resume inputs and **2096** blob rehashes,
and **18 damage cases all failed closed**. The release matrix runs
**27 rows, 27 passed, 0
skipped**.

## 8. Gate verdict and release route

**Gate L2 does not pass.** Fifteen conditions met, one met as a rejection, thirteen not opened,
none failed. Gate D1 conditions 6, 7 and 15 remain open.

Under §11.3 this is a **valid negative completion**: the first failed pre-registered condition
and every opened result are immutable, no forbidden downstream data was opened after a stop,
every dependent task carries typed not-opened evidence, and the independent branch was completed
while it was still valid.

The permitted tag is `sprint-21d3-evidence-baseline`. The success tag
`sprint-21-learning-baseline` is not created, and its absence is asserted rather than assumed.

## 9. Canonical evidence

| Evidence | Purpose |
|---|---|
| [pre-registration](evidence/sprint-21d3-pre-registration.json) | revision 3, the chronology root |
| [corpus](evidence/sprint-21d3-corpus.json) | authored D3 tasks and the defect ledger |
| [separation](evidence/sprint-21d3-separation.json) | transitive role separation |
| [sealed manifests](evidence/sprint-21d3-sealed-manifests.json) | catalogues sealed before outcomes |
| [self-play campaign](evidence/sprint-21d3-self-play-campaign.json) | 200/50 fitting, 80/20 calibration |
| [calibration metamorphic](evidence/sprint-21d3-calibration-metamorphic.json) | 120 decisions, six cases |
| [learner selection](evidence/sprint-21d3-learner-selection.json) | the ladder, the grid, the null |
| [retrieval holdout](evidence/sprint-21d3-retrieval-holdout-result.json) | 60 queries, one read |
| [runtime invariance](evidence/sprint-21d3-runtime-invariance.json) | loader, resolver, mandatory path |
| [pre-final checkpoint](evidence/sprint-21d3-pre-final-checkpoint.json) | the not-opened map |
| [operations](evidence/sprint-21d3-operations.json) | backup, restore, corruption matrix |
| [verification matrix](evidence/sprint-21d3-verification-matrix.json) | the release rows |
| [Gate L2](evidence/sprint-21d3-gate-l2.json) | the condition table |
