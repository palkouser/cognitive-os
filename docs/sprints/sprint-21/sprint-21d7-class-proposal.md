# Sprint 21D7 proposal — the transfer gap measured, and the class it implies

- Status: groundwork for the successor experiment the [D7 handoff](sprint-21d7-handoff.md)
  bounds. **Nothing here unblocks Sprint 22A**, re-decides a D6 stop, relaxes any §2.3
  threshold, or reads any unopened evidence — `final_a`, `final_b` and `canary` remain
  unopened for the fifth sprint running.
- Evidence: [`sprint-21d7-transfer-gap.json`](evidence/sprint-21d7-transfer-gap.json),
  produced by `scripts/transfer_gap_d7.py` read-only from the released D5 and D6 bytes. Both
  matrices are rebuilt and proved against their published hashes before a single rate is
  read; both stores are resolved by content address with no database; the script writes to
  no store.
- Authorisation: handoff §4 — the transfer measurement "costs no authoring, no fitting and
  no new contract; every input is released and sealed" — and §4's own decision rule, which
  opens the class question on exactly the outcome measured below. The class diagnostic fits
  on the released 180-group fitting pool, whose licensed role is fitting, under the same
  sentence D5's groundwork exercised on D4's spent evidence. No selection was made, the
  simulated bar below is discarded, and no spent decision is recertified.

## 1. The transfer gap, measured — the difference collapses

§4 pre-registered one quantity: the per-rung first-choice rate on each corpus, and the
learned-minus-baseline difference on each. If the difference is stable and only absolute
rates move, the gap is corpus difficulty and the confidence axis is exhausted. **If the
difference itself collapses, the direction does not transfer, and no admission rule over it
ever will.**

| | D5 calibration corpus | D6 certification corpus | shift |
|---|---:|---:|---:|
| sealed 720 direction, first choice | 0.88 | 0.76 | **−0.12** |
| sealed 320 direction, first choice | 0.91 | 0.70 | −0.21 |
| `fixed_input_order` | 0.42 | 0.42 | 0.00 |
| `deterministic_static_ordering` | 0.09 | 0.16 | +0.07 |
| `lexical_similarity` | 0.41 | 0.62 | +0.21 |
| strongest rung | 0.42 | 0.62 | +0.20 |
| **learned minus strongest** | **+0.46** | **+0.14** | **−0.32** |

The difference collapses by 0.32 while the positional prior holds exactly still at 0.42 on
both corpora. Both sealed directions collapse, the smaller one harder. The reading §6 of the
D6 record named as the exchangeability symptom is confirmed and located: **the direction is
the non-transferring part**, and per the handoff's own rule the class question is now the
right question, well posed.

One level deeper, the record's per-family rates and a scalar-only refit run during
diagnosis locate it further: a direction refitted on the six structural scalars alone
reproduces 0.76 on the fresh corpus — removing all 384 embedding channels changes nothing
there — so **the embedding of the canonical source is where the corpus lives in the fitted
representation**. The class was ranking what an accepted patch looks like in one authoring
run, not what the task asks.

## 2. The signal the representation never read

Every group in this programme is authored to one anatomy, frozen since D4: the baseline
fails the hidden suite, variants one and two repair the contract by materially different
routes, variants three and four each fix one edge case only. The hidden verifier's question
— does this candidate cover both described edge cases — has a structural shadow the fitted
channels never saw: **a complete repair tends to contain each partial repair's change, and a
partial repair contains neither its sibling nor a complete one.**

`repair_containment.py` computes it: a candidate's share is the mean, over the other
candidates whose repair adds at least one line, of the fraction of that repair's added lines
the candidate also carries. Pre-outcome by construction — baseline and candidate sources are
all in the task package before the sandbox runs — label-free, fit-free, and in [0, 1] with
no clip-and-scale envelope, so two corpora are comparable on it without sharing anything.

**Measured as a deterministic ordering, it transfers where the direction does not:** 0.92 on
D5's corpus, 0.84 on D6's — above both sealed directions on both corpora.

**It survives the six frozen invariance cases by construction, and the construction was
measured anyway.** The renames apply one map to every source in a group, and a consistent
rename is a bijection on stripped lines, so every intersection the share reads is preserved
exactly; the issue rewrites touch no source. The evidence record runs all six cases over all
100 eligible fresh groups: **600 case evaluations, zero ordering changes.** The boundary
that made v2 delete `query_to_candidate_cosine` is respected in the other direction: no
channel relating a candidate to the requirement text is computed, because that is the one
relation class the rename cases move.

## 3. The class

**`containment-contrastive-linear-v1`** — `src/cognitive_os/learning/containment_contrastive.py`.
The fit rule, solver, regulariser, tie-break and abstention are byte-for-byte D5's released
pairwise-contrastive ones; what changes is the representation: seven relational channels —
the six sealed v2 scalars unchanged, plus `repair_containment_share` — replacing the 390.
The embedding leaves the fitted representation entirely, which removes the measured
non-transferring part rather than reweighting it, and takes inference from 390 to 7
multiplications.

The direction fitted on the released 720-row pool weights the AST scalar at 5.75 and the
containment share at 4.70 with everything else near zero: the class learns precisely the two
signals the diagnosis found transferring — structural completeness, and coverage of the
group's other proposed changes.

## 4. What the diagnostic measured against the amended §2.3

All numbers are in the sealed record, over the spent corpora, with the admission protocol
simulated exactly as D6 ran it: the bar derived once from the conformal half's wrong margins
at the pre-registered α = 0.20, admission strictly above it, measured on the other corpus.

| | released class (D6, measured) | this class (diagnostic) |
|---|---:|---:|
| first choice, D5 corpus | 0.88 | **0.94** |
| first choice, D6 corpus | 0.76 | **0.84** |
| admitted of 100 | 40 | **46** |
| errors admitted | 6 | **0** |
| coverage against the 0.40 floor | 0.40 | **0.46** |
| Clopper–Pearson 95% bound against the 0.15 ceiling | 0.2747 | **0.0630** |
| first choice over admitted vs the 0.62 baseline | 0.85 | **1.00** |
| changed decisions among admitted | 26 | 36 |
| projected changed final decisions against the floor of 20 | 39 | **47.0** |
| deepest error-free prefix by margin | 6 | **46** |

On D6's corpus — the corpus where the released class's sweep satisfies the amended pair at
zero of 200 points — this class's margin ordering is error-free through its whole admitted
set, the bound lands at 0.063 against a 0.15 ceiling, and every one of the nine amended §2.3
conditions is satisfied by the simulated cell. The same construction is stable the other way:
on D5's corpus the sweep reaches 85 admitted with one error, bound 0.0546. The infeasibility
was a property of the released class's margin, not of the gate.

## 5. What this proposal does not claim, and one question it must surface

- **Not a selection.** The simulated bar is reported and discarded. The class must be
  pre-registered in the successor's W0 — class name, seven-channel allowlist, one λ, one α,
  one cell — before any fresh outcome exists, and certified on a fresh corpus.
- **The spent corpora cannot certify it.** Both sweeps above are now published, which is
  what "spent" means. Their remaining licensed roles are fitting and bar-setting: the
  natural demotion is D5's fitting pool unchanged, and **D6's 100 certification decisions
  demoted to the successor's conformal half** — the same one-step demotion D6 applied to
  D5's calibration half.
- **A diagnostic on spent evidence is an upper bound on hope, not a guarantee.** The signal
  was found after reading D6's published evidence; the construction is licensed by the
  corpus contract's frozen anatomy rather than by that reading, and its transfer is measured
  across two authoring runs above — but the fresh-corpus number is the experiment, exactly
  as D5's 0.32-below-0.40 bet was.
- **The gate owner must decide where the containment ordering lives.** It is deterministic,
  so it is also a candidate sixth rung for the frozen ladder. On the frozen five-rung ladder
  the strongest baseline on D6's corpus is 0.62 and every §2.3 comparison above uses it. If
  the gate owner adds the containment rung, the baseline this class must beat becomes its
  own strongest channel — 0.84 on D6's corpus — and the diagnostic still clears it over
  admitted decisions (1.00 > 0.84, 36 changed decisions against the containment-first
  order's own choices remain to be measured under that pairing). Freezing that choice
  belongs to the W0 amendment process, before any fresh measurement, not to this proposal.

## 6. What the successor sprint still owes

1. **W0**: pre-registration — the class, the seven channels, λ = 1, one α, one cell; the
   conformal-half demotion ruling; the gate owner's ladder decision; a
   `CorrectionFeatureContractV3` freezing the relational allowlist, deliberately not frozen
   next to this diagnostic.
2. **W1**: a fresh 100-group certification corpus under the unchanged authoring contract —
   the only authoring the successor needs, priced by the same arithmetic as D6's: §2.3
   demands 100 independent decisions in the measured set and every released group is spent.
3. **W2+**: the campaign, the seals, the single derivation of the bar from the demoted D6
   half, the read-once certification, and the gate assessment — the released D6 stage
   structure carries over with the class swapped.

The transfer-gap record this proposal stands on is reproducible from released bytes by
`scripts/transfer_gap_d7.py` at any time, and `src/cognitive_os/learning/transfer_gap.py`
is the measurement's permanent home so the successor's W-stage can seal it under its own
pre-registration.
