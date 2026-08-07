# Sprint 21D4 execution log

- **Branch:** `feature/sprint-21d4-selective-correction-ranking`
- **Waves:** W0 + W1 — authority and design; W2 — fresh evidence at scale; W3 — retrieval
  surface; W4 — artifact and runtime
- **Status:** W0 through W4 complete. Both experiment branches have now returned their own
  hash-bound results, and both are negative: the correction branch selected no candidate
  (S21D4-039, `hypothesis_class_bound`) and the retrieval branch met no floor (S21D4-046, first
  failed floor `mrr_at_10`). W4 refused final access at S21D4-059 and bound twenty-six dependent
  tasks to that one stop. No D4 final, promotion or canary outcome has been read, no threshold
  has been derived, and no candidate has been selected.
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

## W2 outcome — the correction branch answers, and the answer is null

W2 authored 100 calibration groups, sealed 720 feature records before the first container
started, executed both campaigns, materialised two explicit snapshots, resolved the invariance
sample, and measured the risk–coverage curve at two volumes. It reached the floor the wave
exists for: **100 independent decisions, 0 replicated**.

The grid carries signal and cannot be made selective. All 144 cells — 24 settings × 3 operating
points × 2 volumes — beat the strongest deterministic baseline (0.52), at 0.56 to 0.73. Not one
of them reaches zero confident errors, so all 48 zero-error derivations return no point, and the
selection is a typed null under §3.3 step 5.

|  | 200 rows / 50 groups | 320 rows / 80 groups |
|---|---|---|
| best first-choice | 0.735 | 0.712 |
| median first-choice | 0.680 | 0.622 |
| cells beating the baseline | 72/72 | 72/72 |
| fewest confident errors | 13 | 17 |
| zero-error coverage | 0 | 0 |

The stop is `hypothesis_class_bound` rather than `volume_bound` because zero-error coverage is
exactly zero at both volumes: there is no non-zero coverage that more evidence could grow.

W2 also found ten defects, none of them in a measured number: a tautological assertion, `"None"`
written as a threshold string, a CLI branch that was never dispatched, a slot/variant mix-up
that produced 92 phantom label changes, batch-dependent MiniLM embeddings (W2-D9, real and
measured at 6.7e-08 — enough to move a vector hash), and a re-encode claim that checked less
than it said (W2-D10, amended rather than edited).

## W3 outcome — the retrieval branch answers, and the answer is a near miss

W3 made the contract change D3 named and deliberately did not make, decided the comparator D3
left irreproducible, and resolved a fresh sixty-group holdout.

**The surface widened, and the number moved.** D3 measured
`distinct_after_removing_domain_and_signature: 1` over sixty candidates. Under one additive
field — excluded from `structural_hash` and from `ExperienceGraphNode.label`, filled from
canonical terms resolved out of the artifact store — the D4 pool measures **41 of 60**. Ninety-four
of 120 graphs carry terms and 38 of 60 pairs carry different terms on their two sides. Ten
candidates still carry none: repairs written in pure arithmetic over their own parameters, which
the released alpha-normaliser leaves nothing of.

**The comparator is deterministic now.** The released bounded-GED arm returns 28.0 under a 90 ms
clock and 29.0 under a 5 ms clock on the same two graphs — measured on all eight of the largest
stored pairs, which is why three sprints of numbers for that arm cannot be replayed. Under a
fixed iteration budget of one, 140 comparisons agreed with themselves across two passes. The
budget is one because the second distance costs 75 ms where the first costs 4.6, the third 387,
and the fourth did not arrive inside a two-minute ceiling.

**No arm met the floors.**

| arm | Recall@5 | MRR@10 |
|---|---:|---:|
| no_memory | 0.0000 | 0.0000 |
| exact_signature | 0.0000 | 0.0000 |
| lexical | 0.6833 | 0.4954 |
| minilm_vector | 0.6500 | 0.4153 |
| minilm_shortlist_plus_bounded_ged | 0.5833 | 0.3278 |
| **reciprocal_rank_fusion** | **0.7500** | 0.4911 |
| chance baseline | 0.5768 | 0.3317 |
| **floor** | **0.70** | **0.50** |

The fusion clears the recall floor and misses the MRR floor by **0.0089**. Under first-failure
precedence that is a near miss, not a pass. Nothing was reopened to close it: fusion variants 0,
widths 0, weights 0, metrics 0, holdout members added 0.

Beside D3's holdout every arm moved up — fusion from 0.5000 to 0.7500 on recall and 0.3004 to
0.4911 on MRR — and D3's arms all sat at or below a uniformly random ranking where D4's clear it.
**This is not a controlled comparison and must not be read as one:** the pool is different, the
comparator changed, and the surface widened, all at once. No ablation was run, because the
holdout is read once.

The advisory boundary was proved anyway, which is the point of proving it: six mandatory bundle
sections are byte-identical whether or not retrieval contributed, no advisory candidate is
pinned, required or evidence, none carries an executable body, an empty set degrades rather than
fails, and all four ways of breaking the store end at `UNVERIFIED` without raising.

W3 found two more defects, both in what a record claimed rather than in what it measured. W3-D1:
the frozen `searchable_surface` contract cannot mean both of its sentences, because a field
unconditionally inside `content_hash` makes every graph stored before it unloadable — measured
on the real blob, `a8db90af88181437` → `399a7fc9276870c5`, 140 pairs. Amendment 2 records it.
W3-F1: §4.5 calls the widened surface "the minimum that makes sixty repair trajectories sixty
documents"; it makes 41, and the shortfall is named rather than rounded away.

## W4 outcome — the artifact wave has no artifact, and says so once

W4's exit in the wave table is "the D3-built surface exercised against a real artifact, then one
pre-final access decision". There is no real artifact, so the wave is the second half of that
sentence plus the one item that never depended on the first.

**S21D4-050 through -058 are not opened.** Every one of them is downstream of a selected
candidate: there is nothing to bind a threshold into, nothing to fit, nothing to load, sequence,
register, verify or revalidate. The temptation here is the one D3 already answered — D3 built
this machinery against a contract fixture and proved it there. Building a *second* fixture and
measuring it again would produce a record that passes without touching the question the item
asks, which is the defect class the backlog names and which W2 and W3 each hit twice. So they
are refused and recorded rather than performed.

**S21D4-048 is not downstream of anything, and it is the wave's one piece of new contract.**
Gate L2 condition 20 requires at least 100 nominal decisions with at most 1% confident errors.
D3 gave it 120 and the erratum showed those 120 were 20 decisions replicated six times. Nothing
in the D3 payload could have caught it: the metamorphic/OOD row named one number, so there was
no second number for it to disagree with. The row now carries `decision_counts` — nominal,
independent, and the hash of the calibration certificate the answered set was decided under —
and `learning.promotion.condition_20_gate` fills it from a `DecisionCensusV4` rather than from
two integers a caller computed, so a row claiming 120 distinct decisions can only exist if
something hashed 120 distinct fitted vectors. A **measured** row without the counts is refused,
and an **unmeasured** row carrying them is refused too: `not_measured` and `failed` stay
different outcomes, and only one of them has a denominator.

The addition had to move no stored payload, and that is measured rather than claimed. The field
is named in `CANONICAL_ABSENT_WHEN_EMPTY`, so a row without counts is absent from the canonical
form, and `canonical_payload_bytes` excludes nulls, so verification — which re-serialises a
payload and compares the hash the assessment committed to — still sees the bytes D3 wrote. Both
directions are in the record: `d3_byte_sha256 == d4_byte_sha256` for a payload carrying no
counts, and a different `content_hash` for one that does.

**Finding W4-D1.** One payload shape does stop loading, deliberately. A D3 payload asserting
`metamorphic_ood: passed` without denominators is asserting exactly the claim the erratum
disproved, and it is now refused at load. The refusal is the census rule, not a hash mismatch
and not a schema misread: the bytes still verify their own seal and the dispatch still reports
them as `d3-promotion-payload` version 2. The version deliberately did *not* move — bumping it
would make every D3 payload unreadable through `load_promotion_payload`, which is the opposite
of what the item asks. The golden schema pin moved once, additively, and what it used to protect
is now asserted directly against reconstructed D3 bytes instead of against a digest.

**S21D4-050's unchanged clause is checkable without a candidate, and it holds.** 390 channels,
six scalars and 384 embedding dimensions, feature contract hash `492c90a5df420de9…`, normaliser
`cogos-python-alpha-normalizer-v2`, grammar 3.12 — none of them drifted during W2's campaigns or
W3's surface change. The binding half of the item is recorded as not opened, because there is no
derived threshold, derivation instance, split identity or certificate to bind.

**S21D4-059 refused final access.** The preconditions are evaluated in backlog order and the
first failure is the first one:

| Precondition | Result |
|---|---|
| S21D4-039 selected one candidate | **failed** — null, `hypothesis_class_bound` |
| the continuation permits correction work | passed (`proceed`) |
| S21D4-051 stored one artifact | not opened |
| S21D4-054 proved the selected-artifact vertical slice | not opened |
| S21D4-056 registered the artifact and entered SHADOW | not opened |
| the independent retrieval branch reached a result | failed — `winning_arm: null` |

`authorised: false`, `capability_granted: null`. The stop hash is the W2 selection's own seal
`5caa48970898d180…`, and all twenty-six dependent records carry that one hash: the nine E05
items -050 through -058, the ten E06 items -060 through -069, and the seven E07 items -070
through -074, -076 and -077. S21D4-075 is deliberately absent — the backlog names it the one
unconditional substrate gate, and it runs against the isolated lifecycle fixture whether or not
D4 activates. The last precondition is read as D3 read it, a result that names a winning arm;
the retrieval branch did reach a hash-bound result and it is negative, which the record says in
words rather than leaving to the word "result". The decision does not turn on the reading.

No configuration was sealed: sealing happens at authorised final access, and S21D4-070 is the
item that would have done it. `final_or_canary_outcomes_inspected: 0`, no store opened, no
lifecycle state created.

## Evidence handles

| Record | SHA-256 of the file | Seal (`integrity_content_hash`) |
|---|---|---|
| `sprint-21d4-pre-registration.json` | `526d48f83d696290f3ccbb7d06002026d4aa7c05b65c33d95f87c362f83461a9` | `63ffd3484559803208ef4981eaa5ff29948c8d8117dbc31c1aca0553e203c897` |
| `sprint-21d4-contracts.json` | `bcab05107a838fd1a2c0739122ba3a7e51fa8386e83cffcf82e6e5263fb47354` | `9aa54f37a7ddc4d66d9589a7f21089e30c2c0158588d12b1e618f7d8c55a0adc` |
| `sprint-21d4-d3-grid-replay.json` | `202b82db8194bd456a1e06929c2342a33a1355a45c0d31757bec3f0418396f16` | `d1b8115ade6553585aa06a39c647dc1bf2e09ff18b6f87df536bbb37bc7d9fdd` |
| `sprint-21d4-seal-resume.json` | `e37a37e7fb8fd102d8b6baaaa7d91233675bccaa739058f2accdccd1a214d6bd` | `ab6e88422d3ab17305923576864c4c69a9d6ca830acdca0fbad8bccd08319996` |
| `sprint-21d4-continuation.json` | `805761ecc142a9f8b0f71d8c2bc17da559d6cf82164fbfad78e5e62bbe0322d9` | `62dd1aa76136491e5eaf4af06ced3f4350f2baf1855c57d0272977488328eff5` |
| `sprint-21d4-learner-selection.json` | `f1f746af1ed89044b7ae8e768ee3b8386c908fba13e1305d5482356dffb720ed` | `5caa48970898d180ce1f339771399f42af74555a91af2f87e97d1f36c6086c8e` |
| `sprint-21d4-surface.json` | `4f48312d47d83c862816cee3b5eb928862d55cbb5774b50aa04243107d688309` | `11f81209d28436553d0dff36828f4775275ac7d410ab9c22cc0da2addf2cdb05` |
| `sprint-21d4-contracts-amendment-2.json` | `d7dd6b727cf2ac051317164c3cc4e1606eed3948674c42ec28e3119cb74af775` | `6bf0734808b67d9380837e670383c8b92b573017be4c2db6f3bafb863c34b89c` |
| `sprint-21d4-ged-decision.json` | `352f237bc6c27fbb01d482e0cbd39b794e72f3db25e4fbdbabcfad16852d6e13` | `47f88c4c51bca9c863c737673a71e7348c3adf3047ec2a89025c81cdb0e9b4b8` |
| `sprint-21d4-retrieval-development.json` | `56b644c5d4a23c3062c8bffac8d2be8537b17f885c89f4075bb22abc1c77af5e` | `88052aba0ce1700c53ffeace6d98ed341ae6fd3cc3bd2c697a62e0a886ac5279` |
| `sprint-21d4-retrieval-emg-projection.json` | `435edcc8719d0f32b340d45ef7b89bdd000112886a9615384524cc34104f2143` | `5d6108c4385d98902b20367d8b9c9774d63f68157e19398515642c77c752612b` |
| `sprint-21d4-retrieval-query-set.json` | `2302d5378c749c8763d57e3cd57fee84ae8ae7587f2383a3fa0359c39aaa2c84` | `75c7c7cc19a8be4984ce8eda019bd0bbba926b45a716d9408f2006296e6cdd9e` |
| `sprint-21d4-retrieval-holdout-result.json` | `81c41d17205a220023d8356180f7e98cf3e36c9bf1266be89767713ff6a62ff7` | `2cf3cb8a3974c6a49e1426eed4706f125e37e706dfc16aa3478ef325a933c745` |
| `sprint-21d4-retrieval-decision.json` | `f5c19fa0cc290a335d5e250b80c009409cbb509e92e7f2210946c49982d8322f` | `c4ad4b73ff2b8a2b82fb0edb4702d6a7a4d896d742681148f87aa4fbe93c3c52` |
| `sprint-21d4-advisory-boundary.json` | `5d3efbd584dc270a89a834ac104b1e815ac4beb8d545462fa0ae9a2d0d5c7177` | `1dca4f21cf88957b4bf2458475d7e7d8694b619362d237b115c5d9bac45b48f6` |
| `sprint-21d4-pre-final-checkpoint.json` | `fdc1f9f16bda948506604c9f2c9ffc2cc700c51750d4cdcb77a1ef449c57f314` | `87c5473f61c177fe5db5aa1a5971759451c1f7a82b7364e9ac8dc3da99e9c6b1` |

Two hashes, because two things are addressed: the file, which is what another record cites
as `pre_registration_sha256` or `..._sha256`, and the seal inside it, which is what a record
recomputes to prove it was not edited. Every W1, W2, W3 and W4 record carries the
pre-registration SHA-256, and the W1 records pass
`pre_registration_d4.py --check-chronology`.

The W4 record is produced by one credential-free command that needs no database, no Artifact
Store, no model and no network:

```bash
UV_CACHE_DIR=.cache/uv uv run python scripts/artifact_runtime_d4.py
```

## Gate state

Gate L2 remains closed and Sprint 22A remains blocked. Both branches have now returned a
result, and neither authorises what comes next:

- **Gate L2 condition 24 — not met.** No arm reached both retrieval floors.
- **Gate D1 condition 15 — remains open**, on the same evidence.
- **The correction branch selected no candidate**, so S21D4-050 through -058 had nothing to
  fit, store or register. The pre-final access checkpoint at S21D4-059 evaluated its
  preconditions in backlog order, stopped at the first failure, and refused access:
  `authorised: false`, twenty-six dependent tasks bound to one stop hash, zero configurations
  sealed.
- **Gate L2 condition 20's payload is stricter than it was**, which is the one thing W4 moved
  forward rather than closed. The row cannot claim a decision count again without naming how
  many of those decisions were distinct.

What W2 and W3 leave behind is not a guess about why. The correction stop is a measured
hypothesis-class bound over 100 independent decisions, and the retrieval stop is a measured
0.0089 on a widened surface whose widening is itself measured. A successor sprint that wants to
move either number now has a residual to work against rather than a hunch.
