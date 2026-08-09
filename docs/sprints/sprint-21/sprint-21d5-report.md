# Sprint 21D5 report — a direction that ranks, a margin that cannot certify, and a surface that finally answers

- Branch: `feature/sprint-21d5-pairwise-selective-ranking`
- Pre-registration: revision 5, SHA-256
  `ed983599bfcdb75993856419de531777d9f4f6cdcce127ead03dcdcddee34b1a`, published with
  `measured_values: 0`
- Gate assessment: [`gate-l2-d5-assessment.md`](gate-l2-d5-assessment.md)
- Execution log: [`sprint-21d5-execution.md`](sprint-21d5-execution.md)
- Outcome: **Gate L2 does not pass. Sprint 22A remains blocked.** One condition of twenty-nine
  closed.

---

## 1. What the sprint set out to do

Sprint 21D4 asked whether the frozen k-NN correction ranker could be made *selective* — given a
per-decision confidence above which it is never confidently wrong, does anything useful remain
above it? The answer was zero-error coverage of **exactly zero**, in all 144 cells, at both
volumes. The failing quantity was named: the k-NN's confidence is the top candidate's absolute
neighbourhood acceptance mass, and among four deliberate near-clones that mass barely moves
between a right ordering and a wrong one.

D5 pre-registered the smallest change that addresses that diagnosis and nothing else: **a
different hypothesis class over the same representation**, whose confidence is within-group
contrast rather than absolute mass. In parallel and independently, D5 completed the searchable
surface D4 widened but did not finish, and re-measured the retrieval floors D4 missed by 0.0089.

Two branches, independent after W0, and the sprint budgeted for them answering differently. They
did.

## 2. The hypothesis class, and what it did not change

`pairwise-contrastive-linear-v1` fits one linear direction by ridge-regularised logistic
regression on the antisymmetric set of within-group accepted-minus-rejected differences, ranks a
group's candidates by their projection onto it, and reports the **projection margin between the
top two** as the decision's confidence. λ = 1, chosen on fitting-pool-internal leave-one-group-out
evidence recorded *before* the contract was sealed and before any D5 corpus existed, and declared
non-re-choosable.

What did not change is the load-bearing part: no encoder, no normaliser, no channel, no fitted
representation. The 390 v2 channels are the same 390, hashing to the same
`492c90a5df42…`. `derive_zero_error_point` treats a confidence as an opaque ordered score, so the
entire certification spine — the independence census, the Clopper–Pearson bound, the
single-derivation rule — was inherited without a line of new code. D5 changed the function fitted
on top of the representation, and only that.

Two gates, kept apart deliberately: the **margin floor** decides abstention and was held at zero
all sprint; the **derived operating point** decides admission.

## 3. The correction branch, and its answer

The corpus was authored fresh: **100 calibration groups / 400 outcomes**, group-, clone- and
source-disjoint from every spent and carried role, executed under new run identities. The fitting
pool is the **180 spent groups / 720 outcomes** the handoff permits as fitting evidence, at two
volume points 2.25× apart — which repairs D4's own recorded limitation about its narrow 200→320
span at no authoring cost.

| | 320 rows | 720 rows |
|---|---:|---:|
| first-choice over all answered | **0.91** | **0.88** |
| strongest deterministic baseline | 0.42 | 0.42 |
| admitted decisions of 100 independent | 26 | 27 |
| zero-error coverage (floor 0.40) | **0.26** | **0.27** |
| confident errors | **0** | **0** |
| first-choice over admitted | 1.00 | 1.00 |
| 95% upper bound on the admitted error rate | 0.1088 | 0.1050 |
| changed clean decisions | 22 | 21 |
| projected changed final decisions (floor 20) | 50.8 | 46.7 |
| maximum inference (budget 250 ms) | 0.080 ms | 0.067 ms |

Both cells satisfy **seven** of §2.3's eight conditions and fail exactly one: clean coverage below
0.40. Zero eligible cells, no candidate.

**The ending is §3.3 step 5, `selective_margin_bound`**, and the two neighbouring endings are
ruled out by measurement rather than by preference. Coverage is *above zero*, which rules out step
6 — the class is not the wrong class in D4's sense; its confidence separates errors, which D4's
never did anywhere. Coverage is *flat* across a 2.25× volume span — 0.26 to 0.27, one point —
which rules out step 4: this is not a corpus that needs to be bigger.

The shape is visible in the sweep. At 720 rows the margin ordering would admit 50 of 100 decisions
at the cost of a single error; the zero-error rule stops at 27 because the 28th-ranked decision is
wrong. The direction ranks. The margin cannot certify enough of what it ranks.

The spent-evidence diagnostic run before the corpus existed estimated 0.22 at 80 groups and 0.32
at 179; the fresh measurement returned 0.26 and 0.27. The small-pool estimate transferred and the
large-pool one was 1.2× optimistic — recorded because a diagnostic that is never scored against
its own prediction is a diagnostic nobody can calibrate.

## 4. The retrieval branch, and its answer

D4 measured 41 of 60 candidates distinct and missed MRR@10 by 0.0089, and named the cause: repairs
written in pure arithmetic over their own parameters yield no identifier terms. D5 completed the
surface with one flag — `search_terms_from_source(..., structure_fallback=True)` falls back to
lowercased AST node-type names — and re-measured.

**120 of 120 sides carry terms**, 27 through the fallback. Distinct documents reach **55 of 60**
against D3's 1 and D4's 41. The flag moves no hash: `search_terms` stays out of `structural_hash`
and out of `ExperienceGraphNode.label`, and every one of the sixty pairs records
`structural_hash_is_the_same_with_and_without_the_flag`.

On sixty freshly authored unseen-task queries, read once, six frozen arms evaluated exactly once:

| | measured | floor | chance baseline |
|---|---:|---:|---:|
| Recall@5 (`lexical`) | **0.7500** | 0.70 | 0.5768 |
| MRR@10 (`lexical`) | **0.5389** | 0.50 | 0.3317 |

**Gate L2 condition 24 is met. Gate D1 condition 15 is closed.** This is the sprint's one closed
condition, and §8.2 requires it to be retained whichever way the correction branch went.

The mechanism, stated rather than glossed: relevance is the task family, and same-family tasks
share structure by construction, so the 27 fallback sides carry a legitimate signal rather than a
leak. The family label appears in no document, and the leak guard ran over all 120 complete
documents. **No ablation was run** — the holdout is read once, and an ablation is a second read.

## 5. What the stop did not stop

The correction stop closed 26 items and 15 Gate L2 conditions, all bound to one hash. It closed
nothing else.

- **The retrieval result stands.** Independent after W0, valid on its own evidence, and released.
- **Operations is release-graded.** Twelve integrity classes clean with both authorities against a
  copy restored from a backup taken before any damage; 28 damage cases and 2 controls, all
  holding; provisioning at `0015` with no `0016`; a 32-row release matrix with nothing skipped.
- **Condition 20's certificate is stricter than it was.** `PromotionDecisionCounts` now carries
  `hypothesis_class`, and `condition_20_gate` refuses a class no loader implements. A future row
  cannot claim confidences without naming what produced them.
- **The v3 artifact contract exists and is exercised.** `CorrectionArtifactPayloadV3` carries a
  fitted direction where v2 carried an exemplar set — the same 390 floats whatever it was fitted
  on. It was not built for a candidate, because there is no candidate, and the sprint does not
  claim condition 22 on it.

## 6. Findings

| ID | What | Cost |
|---|---|---|
| **S21D5-W0-F1** | The first migration invocation targeted `cognitive_os_dev`, because `scripts/postgres_common.sh` re-reads its own environment file under `set -a` and overrides exported values by design. | Operator error against documented behaviour, not a code defect. Two additive migrations on the development database, zero rows, no evidence store touched. Every D5 shell invocation since passes `COGOS_POSTGRES_ENV_FILE` instead of exporting. |
| **S21D5-W1-F1** | The sealed contract's literal seven-role clone rule is already false of the carried roles: 20 cross-role near-clone pairs exist, and four of them are between two roles D5 authored neither side of. | The literal reading was violated before the sprint began and cannot be satisfied without re-authoring roles §3.2 bars D5 from touching. The operative rule is the one in the same sealed object's own `near_clone_rule` field, and the record says which reading it applied and why. |
| **S21D5-W2-A1** | Adding `hypothesis_class` to the promotion payload left `canonical_payload_bytes` stable and silently moved the `content_hash` of every payload already carrying a counts row. | Caught by the item's own test before it shipped. Fixed with the mechanism D4 built for exactly this: the field joins `CANONICAL_ABSENT_WHEN_EMPTY`. Both halves are now measured. |
| **S21D5-W3-F1** | `sprint-21d4-retrieval-emg-root.json` declares 60 pairs and none of their blobs resolves anywhere under `cognitive-os-data`, backups included, searched by all five declared hashes. | The root is byte-identical to what S21D4-044 recorded with `intact: true`, and D4 published no store fingerprint, so when they went is undeterminable. Recorded, **not reconstructed**: regenerating them would mean running D4's groups under D5's runner and calling the result D4's evidence. D5's own pairs resolve and rehash. |
| **S21D5-W7-A1** | The ported `matrix_embedding_scans` integrity class read its required scan count out of the record it was checking. D4's snapshots declare `scans.required`; D5's do not, so the fallback made the whole check `11 < 11`. | Caught by writing the test that has to make the class fail. The class now names the nine scans the released scanner emits. |
| **S21D5-W7-F1** | Two of D4's six recorded release-matrix rows were decided by truthiness over a string, so `first_failed_floor` would have passed on any wording at all — including one reporting the opposite result. | A defect in a released command. D5's matrix names the value each row expects and refuses a recorded row that reads a string and names nothing. `scripts/verification_matrix_d4.py` is left as released: its record is published and will not be regenerated. |

Five of the six share one shape, and it is the shape this programme keeps finding: **a check that
passes without touching its question.** W7-A1 compared a number with itself; W7-F1 compared a
string with nothing; W1-F1 was a rule that could only ever be violated; W2-A1 was a stability
claim about the wrong serialisation. None was found by reading code. All were found by running
the thing and reading the output against the question it claimed to answer.

## 7. Limitations

**The result is about one confidence construction, not about the class.** The direction ranks at
0.91 and its errors *are* separable — coverage is above zero everywhere, which is the thing D4
could not achieve. What fails is the specific reduction of a ranking to one scalar margin and the
specific rule that admits only a prefix with zero errors in it. A different construction over the
same fitted direction is untested and is exactly what the handoff names.

**The baseline is weak, and the 0.91 should not be read against it as an achievement.**
`fixed_input_order` at 0.42 is near chance in a corpus where two of four candidates repair. The
gap is real and the opponent is not strong.

**One hundred independent decisions is a small denominator for a coverage claim.** Zero errors in
26 admitted decisions bounds the true error rate at 10.9%, not at zero, and the record reports
that bound beside the coverage rather than under it.

**The corpus is authored.** Every calibration and retrieval group was written for this sprint by
one author against a design table. It is disjoint, balanced and validated, and it is not
production traffic.

**The retrieval pass measures one surface, on authored tasks, under a frozen encoder, read once.**
It says nothing about the correction branch, nothing about production retrieval, and — because no
ablation was run — nothing about how much of the gain the fallback contributed. The chance
baseline is reported beside it so the margin over chance is visible rather than implied.

**The volume arm is two points, not a curve.** 320 and 720 rows is a 2.25× span, wider than D4's
1.6×, and it is still two points. "Flat" means flat between them.

**Nothing below the selection ran against a real model.** No artifact was built, stored, loaded,
sequenced, registered, promoted, shadowed, activated or rolled back for a candidate, because there
is no candidate. The lifecycle surfaces remain exercised only against fixtures and the isolated
inert component.

## 8. Outcome

**Gate L2 does not pass. Sprint 22A remains blocked.** Fourteen conditions met, fifteen never
opened behind one typed stop, zero failed, zero carried, zero met as a rejection. Condition 29 is
among the met — the release happened, was verified from the remote and closed the one condition
still moving. No threshold was relaxed and no condition is met against a fixture.

Two branches asked two questions and got two different answers, and both answers are measurements
rather than absences. The correction branch has a residual to work against: not "the class is
wrong" but "the margin certifies 0.27 of what it ranks, flat in volume, with zero errors in what
it admits." The retrieval branch has a closed condition that survives the stop.

§8.2 is explicit that a negative release is a complete release. This one is:
`sprint-21d5-evidence-baseline`, protected, verified from the remote, with every record sealed and
every stop bound to one hash.
