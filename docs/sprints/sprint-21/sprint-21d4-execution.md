# Sprint 21D4 execution log

- **Branch:** `feature/sprint-21d4-selective-correction-ranking`
- **Waves:** W0 + W1 — authority and design; independence and threshold spine
- **Status:** W0 and W1 complete. The correction branch is open at W2 on a typed `proceed`; the
  retrieval branch is open and independent of it. No D4 calibration, final, promotion or canary
  outcome has been read, no threshold has been derived, and no candidate has been selected.
- **Migration:** none; the D4 authorities are provisioned at the released revision
- **Pre-registration SHA-256:**
  `526d48f83d696290f3ccbb7d06002026d4aa7c05b65c33d95f87c362f83461a9`
- **D4 measurements before pre-registration:** zero

## W0 outcome

The D3 release was verified from live handles rather than from the D3 report: the annotated tag
object `bcf2976dd0f063b1eb4ea16b388eea590e6172dd` peels to `ef4388b1bf9cb842b25a06aa2255abd1042702c2`,
and `scripts/baseline_d4.py` refuses to emit a baseline at all if that tag does not resolve
remotely. The D4 authorities are isolated under `cognitive_os_s21d4{,_test,_integration_test,_restore_test}`,
`artifacts-s21d4` and `backups-s21d4`; the provisioning guard was shown to refuse
`cognitive_os_s21d3_test` by name, with a non-zero exit recorded rather than discarded.

Eight revision-4 contracts were frozen and the pre-registration published with
`measured_values: 0`. `scripts/pre_registration_d4.py --check` reproduces the hash above over
eight contracts and six W0 children, offline and without credentials.

## The decision-independence erratum

[The reconciliation record](evidence/sprint-21d4-d3-reconciliation.json) is the authoritative D4
interpretation of Sprint 21D3 and changes no released byte.

Over all twenty-four D3 settings, `ood_answered` is exactly six times `clean_answered` and
`confident_ood_errors` is exactly six times the clean answered-and-wrong count. **D3's 120
metamorphic ranking decisions were 20 decisions replicated six times**, because six
semantics-preserving transformations of one group encode to one fitted vector by construction.
Observing zero errors in 20 decisions bounds the true error rate at 13.9% with 95% confidence,
not at zero; Gate L2 condition 20's 1% ceiling is an observed-rate requirement, and D4 reports
the bound beside it rather than claiming the bound is met.

The same record reconciles the six W7 recovery values narrated in the D3 execution log against
`sprint-21d3-operations.json`, which is the authority where the two disagree.

## Finding D4-W0-F1 — the Sprint 21D3 learned store is empty

The predecessor inventory found no observations and no datasets in the D3 store. Three
independent signals establish why, and they agree:

1. the append-only Event Store, never truncated, holds committed `learned.observation_recorded`
   events, so the rows were written **and committed**;
2. `pg_stat_user_tables` reports inserts into `learned_observations` with `n_tup_del = 0`, so no
   `DELETE` ever ran;
3. every one of the nine `learned_*` tables has `relfilenode != oid` in one contiguous block,
   while every other table in the database and the whole of Sprint 21D2's store are untouched.

That pattern is a `TRUNCATE`, which also explains signal 2, since `TRUNCATE` does not count
deletes. The mechanism is `cognitive_os.learned_smoke.run_learned_smoke`, which truncates exactly
`LEARNED_EVIDENCE_TABLES` and was fenced only by the database name ending in `_test` — and every
sprint's evidence database ends in `_test`. The erasure occurred 114 seconds before the W7
backup, which is why that restore proof compared matching counts of nothing. The data is
irrecoverable: every backup was taken after it.

The D3 *result* is undisturbed. The learner selection is committed evidence and S21D4-001
recomputes its full 24-setting grid from that file without reading the store.

The fix is the convention the repository already had rather than a second one:
`COGOS_TRUNCATABLE_DATABASE` must name the connected database, which the PostgreSQL integration
fixture has required since W6-F2 for the same reason. A second content fence refuses when the
store holds an observation, a dataset, or any component other than the inert reference one —
kept against the usual rule about second mechanisms because the failure it prevents is
irreversible data loss.

## Finding D4-W0-F2 — a guard query built by interpolation

CI's `quality` lane found a Bandit B608 in the first version of that fix: the content fence
counted rows through an f-string over a table-name loop. The table names were module constants
and never reached user input, so the finding was not exploitable, but a `# nosec` would have
recorded an exception where a rewrite was cheaper. The loop was replaced with two literal
queries. Recorded here rather than in the W0 evidence: the pre-registration had already sealed
`sprint-21d4-finding-w0-f1.json`, and `--check` correctly refused an attempt to amend it. A
sealed record is not edited after publication.

## W1 outcome — independence and threshold spine

### The counting rule (S21D4-020)

Revision 4 is additive; the revision-3 classes keep their bytes, because D4 reads D3's evidence
through them. `DecisionCensusV4` carries the triple — nominal, independent, replicated — and
refuses a census that does not add up and a payload that names the nominal denominator.
`CorrectionDecisionSetV4` takes every accuracy, error and coverage rate over the independent
denominator and names it in the stored bytes. Both are published: the exported schema
`v1/learned/decision-census-v4.schema.json` lists the triple as required, so a payload that omits
it is refused by the schema and not only by the producer.

### The zero-error operating point (S21D4-021)

`cognitive_os.learning.selective_operating_point` derives one threshold from the calibration
split only, over independent decisions only, once. The rule is a sorted quantile and nothing
else: the threshold is the highest score among answered decisions that are wrong, and the
admitted set is everything scoring strictly above it. It adds no model, no fit, no dependency and
no fitted channel.

The frozen contract sentence reads "the highest threshold at which every answered decision above
it is correct". Read literally that set has no highest member — every larger threshold also
admits only correct decisions, up to admitting nothing — so the implementation takes the boundary
of the zero-error region, which is the point that admits the most decisions and the only one
whose coverage is worth reporting. The record carries a `derivation_reading` field saying so,
rather than leaving a reader to infer which end of the interval was taken.

Single-shot and restart determinism are one mechanism, not two: a re-derivation must reproduce
the first `derivation_hash`, which excludes the wall clock. Reproducing is allowed and is the
determinism proof; producing a different answer is refused.

### The D3 grid replayed (S21D4-022)

[The replay](evidence/sprint-21d4-d3-grid-replay.json) recomputes 17 derived values per setting
from the primitives recorded beside them — 408 in total across the 24 settings — and **every one
of them reproduces**. The pre-registered stop `reconciliation_not_reproducible` did not fire.

One quantity is reported as a bound rather than an identity. The metamorphic block's
`clean_first_choice_rate` is not six times the setting's own `clean_correct`: it is the effective
rate, which credits an abstention when the deterministic baseline it fell back to was right. That
is a different quantity wearing a similar name, and the only thing derivable about it from the
recorded primitives is that it lies between the answered-correct count and that count plus every
abstention. The bound holds for all 24 settings. Asserting the identity instead would have
stopped the sprint on a definition mismatch.

Restated over independent decisions, the first setting reads:

| | D3, nominal | D4, independent |
|---|---|---|
| ranking decisions | 120 | 20 |
| answered | 114 | 19 |
| confident errors | 36 | 6 |
| confident error rate (answered) | 0.3158 | 0.3158 |
| coverage | 0.95 | 0.95 |

**The corrected denominator does not rescue D3.** No setting in the grid reached zero confident
errors even over its twenty independent decisions; the count ranges from 2 to 6. D3's stop was
therefore not an artefact of counting replicas. What D3 never had is a per-decision operating
point — the grid's `confidence_floor` is a setting-level constant, while the zero-error point is
chosen from the scores themselves. That is the intervention D4 tests, and this replay does not
test it.

### The seal, receipt and restart spine at D4's shape (S21D4-023)

[The fixture](evidence/sprint-21d4-seal-resume.json) runs two partitions at the campaign sizes
S21D4-012 declares: 80 fitting groups and 100 calibration groups, four candidates each, 180 tasks
and **720 candidate outcomes**. All 720 encode to 720 distinct fitted vectors, so the proof is
not one decision repeated. Per partition, features seal strictly before the first outcome, a
post-outcome seal is attempted and refused, the stored seal time survives serialisation, the
dataset record and both manifests reproduce under fresh application services, the receipt members
resolve the dataset selection, and the effective remainder after restart is empty. Every stored
blob was rehashed against its content address.

Every group is a fixture group named `d4-w1-fixture-group-*`. No D4 fitting, calibration, final,
promotion or canary group was spent to prove the spine.

### The typed continuation (S21D4-024)

[The decision](evidence/sprint-21d4-continuation.json) is **`proceed`**, on four conditions
checked against committed evidence rather than against a recollection of having checked them: the
replay reproduces and derived no threshold; the counting rule is in force, which is exercised by
attempting both refusals and by reading the published schema; the fitting pool and all three
protected roles are resolved and pairwise disjoint with zero outcomes, predictions or receipts;
and the spine holds at the campaign shape. It binds the five hashes those conditions rest on and
records `measurements_opened: 0`.

The decision authorises W2 to author the fresh corpus. It does not authorise reading any D4
calibration, final, promotion or canary outcome, deriving the operating point, or selecting a
candidate.

## Evidence handles

| Record | SHA-256 |
|---|---|
| `sprint-21d4-pre-registration.json` | `526d48f83d696290f3ccbb7d06002026d4aa7c05b65c33d95f87c362f83461a9` |
| `sprint-21d4-contracts.json` | `bcab05107a838fd1a2c0739122ba3a7e51fa8386e83cffcf82e6e5263fb47354` |
| `sprint-21d4-d3-grid-replay.json` | `202b82db8194bd456a1e06929c2342a33a1355a45c0d31757bec3f0418396f16` |
| `sprint-21d4-seal-resume.json` | `e37a37e7fb8fd102d8b6baaaa7d91233675bccaa739058f2accdccd1a214d6bd` |
| `sprint-21d4-continuation.json` | `805761ecc142a9f8b0f71d8c2bc17da559d6cf82164fbfad78e5e62bbe0322d9` |

All three W1 records carry the pre-registration SHA-256 and pass
`pre_registration_d4.py --check-chronology`.

## Gate state

Gate L2 remains closed and Sprint 22A remains blocked. Nothing measurable has been opened. The
next wave is W2 — items 030 through 039 — which authors the 100 calibration groups and the
retrieval pool, fits at 200 and at 320 rows, and measures the risk–coverage curve. Under §2.3,
authoring fewer than 100 groups is answered by recording the achieved independent-decision count
and letting the floor decide, not by lowering the floor or reinstating replicated decisions.
