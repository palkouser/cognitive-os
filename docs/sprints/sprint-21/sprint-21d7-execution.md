# Sprint 21D7 execution log

- Branch: `sprint-21d7-groundwork`
- Backlog: [Sprint 21D7 Technical Backlog](sprint-21d7-technical-backlog.md)
- **Status: W2 closed, ending `1_select`.** S21D7-000 through S21D7-005, S21D7-010 through
  S21D7-019, S21D7-020 through S21D7-024 and S21D7-025 through S21D7-034 are done. The class
  `containment-contrastive-linear-v1` met **every** amended §2.3 condition on the fresh 100-group
  certification corpus: coverage 0.59, Clopper-Pearson bound 0.126207 against the 0.15 ceiling,
  0.9492 first choice over admitted against a 0.61 baseline, 46.78 projected changed final
  decisions, 100% first-action preservation. **No threshold moved in any wave.** W2 decides
  eligibility only — it promotes nothing and closes no gate condition. **W0 detail follows
  first**, then W1, then W2.
- **W0 closed.** S21D7-000 through S21D7-005 and S21D7-010 through S21D7-019 are done.
  The three governance rulings W0 exists to obtain were all taken and the condition-24
  inheritance was renewed. Revision 7 is published with `measured_values: 0`, and **no threshold
  moved**.
- Pre-registration: revision 7, SHA-256
  `4017be51c6e06d6123982d2572a9dcd346bb23decc7d1bcfe2c995ee95c2fc7f`
- Migration head: `0015`, unchanged. `0016` remains unallocated.
- Wave commit `80eec47`, pull request **#229** against protected `main`; CI run **`31393808250`**
  on that exact head, **30 of 30 jobs successful**. The merge is the gate owner's, not the
  wave's — W0 leaves the branch reviewable rather than merged.
- Gate L2 does not pass and Sprint 22A remains blocked. W0 measures nothing and closes no
  condition; it establishes the authority every later wave is bound to.

---

## W0 outcome — three rulings, one class frozen, and three findings

Four scripts, eight sealed records plus the carried groundwork record, **three findings**, and
one arithmetic correction to a number this wave wrote itself.

Unlike D6's W0 this wave had no threshold in front of it. D6 had to change §2.3 or not run; D7
asks for **no amendment at all** — alpha stays 0.20, C stays 0.15, the coverage floor stays 0.40,
every §2.3 sentence stays as D6 left it. What the gate owner was asked for instead is *which
spent evidence may set a bar*, *which ladder §2.3 reads*, and *whether a condition may be
inherited a second time*. All three were granted, and the one with two legitimate answers — the
ladder rung — was put as an explicit either/or with the baseline each side implies before it was
decided.

**Four scripts, and none of them released.** `baseline_d7.py` (three phases), `contracts_d7.py`,
`reuse_audit_d7.py` and `pre_registration_d7.py`. The `*_d2` through `*_d6` families produced
released evidence and stay exactly as they are.

### S21D7-000 and S21D7-002 — the starting point, read rather than restated

`sprint-21d7-baseline.json`, integrity
`b39b16c239f3fe5e…`.

| Fact | Result |
|---|---|
| `sprint-21d6-evidence-baseline` resolves remotely as an annotated tag | yes, object `29debe41f8dbe161…` peeling to `cfd22ab6d3e32367…` |
| local and remote tag handles agree | yes |
| branch descends from current `origin/main` (`51cd4879…`) | yes, one commit ahead |
| `sprint-21-learning-baseline` | **absent**, checked rather than assumed |
| D6 exact-head CI runs `31381783754` and `31382974994` | re-read from the API, 30 of 30 successful each |
| branch protection | administrators enforced, 27 required checks, strict, no force pushes, no deletions |
| migration head | `0015` |
| **nine** predecessor artifact roots | fingerprinted; the eight with a released expectation match it |

`artifacts-s21d6` joins the predecessor list for the reason `artifacts-s21d5` joined D6's: D6 is
released and its evidence is now somebody else's baseline. Unlike D5's root at the D6 baseline it
arrives **already bound** — D6 re-ran its after phase in its last wave, so
`sprint-21d6-authority-isolation-after.json` carries a released fingerprint for D6's own root and
D7 compares against it rather than recording a first observation.

The ninth root is W0-F1, below.

### S21D7-001 — provisioned authorities, and D5's finding still not repeated

`sprint-21d7-provisioning.json`, integrity `fc572bb24bfb6a23…`.

Three databases created under the `cognitive_os_s21d7` prefix, the evidence store migrated to
head `0015`, `alembic check` reporting **no new upgrade operations detected**. The integration and
restore databases are `unmigrated`, which is their correct state. `.env.s21d7.local` is derived
from `.env.s21d6.local` by substituting the sprint slug — 13 substitutions, no other edit.

S21D5-W0-F1 was a migration that reached the development database because the shared loader
re-reads its own file and overrides exported variables. Every D7 invocation passed
`COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d7.local` explicitly, and the head was verified on the D7
store (`0015`, newly migrated) and on D5's and D6's (`0015`, untouched) before the record was
written. **No finding.**

### S21D7-010 — the conformal-half demotion

`sprint-21d7-demotion-ruling.json`, integrity `b72b1cb178d8fc70…`. **Thresholds changed: 0.**

D6's 100 certification decisions are demoted to D7's bar-setting half. The rule is recorded in
both directions: a demoted half **may** place one bar from margins re-scored out of a sealed
campaign, and **may not** certify coverage, an error rate, a first-choice rate or a candidate,
appear in the measured set, or be re-executed under new run identities.

**The alternative is priced by recomputation, not by prose.** The script takes each candidate
half's first-choice rate under the new class out of the sealed groundwork record, derives the
wrong count, and runs `conformal_rank` over it:

| candidate half | spent before | wrong decisions | rank at α = 0.20 | wrong margins above the bar |
|---|---:|---:|---:|---:|
| D5 calibration | twice | 6 | 6 of 6 | **0 — the prefix rule again** |
| **D6 certification** | once | 16 | 14 of 16 | **2 — a genuine quantile** |

At m = 6 the bar *is* the largest wrong margin, which is the zero-error prefix rule D5 stopped
on wearing a new name. D6's half is the only candidate at which the carried alpha buys anything,
and the record says so with the arithmetic rather than with an adjective. The wrong counts are
design estimates off spent corpora; **the m that sets the bar is whatever W2's sealed re-scoring
finds**, and the ruling names the half, not the count.

### S21D7-011 — the sixth rung, seated

`sprint-21d7-ladder-ruling.json`, integrity `e9553eb0ee1016bd…`. **Thresholds changed: 0.**

The containment ordering is deterministic, label-free and computable before the sandbox runs, so
it is a legitimate rung. It is seated, and the record recomputes what that costs from the sealed
groundwork record:

| corpus | strongest released rung | containment rung | baseline §2.3 now reads | raised by |
|---|---|---:|---:|---:|
| D5 calibration | `fixed_input_order` 0.42 | 0.92 | **0.92** | +0.50 |
| D6 certification | `lexical_similarity` 0.62 | 0.84 | **0.84** | +0.22 |

Seating the rung means the learned class must outrank **its own strongest channel** on fresh
evidence rather than outrank lexical similarity, and §2.3's changed-decisions conditions re-pair
against the containment-first order — a count the groundwork did not measure. W2 reports both
pairings; this ruling fixes which one §2.3 reads. It also makes §3.4's ending 4,
`baseline_not_beaten`, reachable for the first time, and the decision tree says so in the ending's
own text.

Refusing the rung was a legitimate answer and was offered as one. It was declined in the
direction that makes the sprint harder to pass.

### S21D7-012 — condition 24 renewed, not referenced

`sprint-21d7-condition-24-ruling.json`, integrity `6cb08f6d4c84f3b7…`.

D6's ruling inherited D5's sealed retrieval measurement conditionally, on three identities. D7
renews it on the same three, re-bound to the same released hashes, with the same falsifier and
the same re-check at gate close — **and it is a renewal rather than a citation on purpose**: the
inheritance's falsifier is about the sprint claiming it, and only a D7 record can say that D7
changed neither the searchable surface, the retrieval arms nor the comparator. The record also
states why the sixth ladder rung does not void it: a correction-ranking rung over four presented
candidates touches no arm, no shortlist width and no metric.

**Sixty authored groups saved; W1 stays a single authoring wave.**

### S21D7-003 and S21D7-004 — what changes role, and what stays sealed

`sprint-21d7-reuse-audit.json`, integrity `8dd2fd1744cb0820…`.

**The role transition.** D6's 100 certification groups become D7's conformal half under the
S21D7-010 ruling — the same one-step demotion D6 applied to D5's calibration half, one sprint on.
The half is bound by the released certification matrix hash `747eb9664bbcfd3b…`, is not
re-executed, and certifies nothing. The 180-group fitting pool stays fitting evidence, and this
is the sprint where that matters: **D7 fits a new direction on it**, which is the pool's licensed
role and the reason it was never a selection input. The retrieval pool is spent entirely and D7
authors no replacement. The record also names the half **not** taken and why, rather than leaving
the alternative unmentioned.

**The carried roles.** `final_a` (30), `final_b` (30) and `canary` (5) audited a fifth time and a
fifth time `reuse`: shapes hold, all three pairwise disjoint, both released generators agree
(D6's bundle against the D5 one it was carried from), 65 protected task identities resolved by
identity alone, **zero protected bodies opened**. Five stores were read for outcomes, predictions
and receipts — and the fifth is W0-F1.

### S21D7-013 through S21D7-019 — revision 7

`sprint-21d7-contracts.json` and `sprint-21d7-pre-registration.json`.

Six contracts, and five of them exist to fence the one that matters. The contract text is
imported from the modules that implement it, so a rule that drifts in code drifts in the record
and `--check` catches it.

| Contract | What it freezes |
|---|---|
| `feature_contract_v3` | `CorrectionFeatureContractV3`: the **seven-channel** allowlist, the two channel rules (within-group source-to-source admissible, source-to-requirement banned under any name), no envelope on the share because it is in [0, 1] by construction, and the embedding **computed and sealed but read by no v3 channel** |
| `candidate_cell` | `containment-contrastive-linear-v1`, one cell, fitted once on the 720-row pool, λ = 1, margin floor 0, **model hash `d80160c4aa795fad…` to reproduce**, no volume ladder, the two released 390-channel directions not re-scored |
| `admission_rule` | `split-conformal-margin-v1`, **alpha = 0.20 carried, not re-chosen**, rank 14 of 16, two wrong margins above the bar, single derivation, the demoted half named |
| `corpus_roles` | bar-setting half = the demoted D6 certification half; certification half = 100 authored fresh; fitting pool = 180 groups; invariance 20/40; promotion 120/60; retrieval 0 |
| `selection_rule` | the amended §2.3, nine clauses, C = 0.15, floor 0.40, **the six-rung ladder**, and the changed-decisions pairing the ruling fixed |
| `decision_tree` | **six** typed endings, published before any number exists |

**Why alpha is not re-derived.** It is carried from amendment 2, which stays in force and is
**not re-made** — `amendments_made_by_this_sprint: 0`. What changed is the half it is taken from.
At the demoted half's m = 16 the rank is 14, so two wrong margins stay above the bar; below
2/17 ≈ 0.117647 the rank reaches the whole set and the bar is the failed prefix rule again.

**Why C = 0.15 still exposes the design.** At the 46 admitted decisions the diagnostic expects,
the bound reads 0.063 at zero errors, 0.099 at one, 0.131 at two and 0.160 at three. C admits up
to **two** against a diagnostic observation of zero — a ceiling the design expects to clear and
can genuinely fail on three admitted errors.

**Design inputs are disclosed rather than counted as zero,** and revision 7's disclosure is
sharper than revision 6's: the class was constructed *after* reading D6's published evidence and
its diagnostic was read off two spent corpora. Every threshold it must clear was frozen by a
predecessor before the class existed, the groundwork record is cited by hash rather than
repeated, and the fresh certification is read once. The 46-with-zero-errors observation is an
upper bound on hope, exactly as D5's 0.32-below-the-floor was a lower one.

### S21D7-005 — the W0 test module

`tests/cognitive_os/learning/test_d7_w0_evidence.py`, 24 assertions over the eight sealed records.
The ones that would have caught something: the demotion ruling's rank tables recomputed from
`conformal_operating_point` rather than read back; the ladder ruling's seated baseline recomputed
from the sealed groundwork rungs and required to be no lower than the released strongest; the
ceiling table recomputed at 46 admitted; and the groundwork's **model hash rebuilt from its own
sealed weights through the released class**, so the hash W2 is bound to reproduce is proved to
describe those weights rather than to be a string somebody typed.

### S21D7-002, the other end — zero predecessor writes

`sprint-21d7-authority-isolation-after.json`, integrity `45ea812cb857f270…`. Nine roots
re-fingerprinted after the wave against the baseline: **zero drifted, zero writes**.

## W0 evidence index

| Record | SHA-256 (16) | Items |
|---|---|---|
| `sprint-21d7-baseline.json` | `b8fe663d6d888488` | S21D7-000, S21D7-002 |
| `sprint-21d7-provisioning.json` | `c23f5a117bc7b484` | S21D7-001 |
| `sprint-21d7-demotion-ruling.json` | `2cc8de528331a707` | S21D7-010 |
| `sprint-21d7-ladder-ruling.json` | `0648bdd054099703` | S21D7-011 |
| `sprint-21d7-condition-24-ruling.json` | `af2144a33ce1b142` | S21D7-012 |
| `sprint-21d7-reuse-audit.json` | `b63708754ca49e06` | S21D7-003, S21D7-004 |
| `sprint-21d7-contracts.json` | `777dc392ee039296` | S21D7-013 … S21D7-018 |
| `sprint-21d7-pre-registration.json` | `984a21f012cddb1e` | S21D7-019 |
| `sprint-21d7-authority-isolation-after.json` | `b42ec5aff8abf3a3` | S21D7-002 |
| `sprint-21d7-transfer-gap.json` (carried) | `ee66c6b195207a51` | groundwork, bound as a child |

## W0 findings

| ID | Finding | Fix |
|---|---|---|
| **W0-F1** | D6 provisioned a **second** store pair when its seal stage refused a store whose campaign stream already carried events, and `cognitive_os_s21d6_measured` / `artifacts-s21d6-measured` is where D6's measured campaign actually ran. **No released record fingerprints either.** The store holding the bytes D7's demoted half is rebuilt from was under no freeze, and an audit of `cognitive_os_s21d6_test` alone would have proved zero protected outcomes in the store where D6 did the least work. | The root joins `PREDECESSOR_STORES` as the ninth pair (first observation; there is no released expectation to compare against, and the record says so rather than inventing one) and the database joins the reuse audit's store list. It holds **404 observations, 0 for protected roles, 0 accesses**. |
| **W0-F2** | The published alpha floor was typed as `0.1177`, which is *above* 2/17 — at that alpha the rank is 15 of 16 and the rule does **not** degenerate. The field refuted its own name. | The floor is derived in-script from `2/(m+1)` and rounded **down**, so the published decimal is a value at which the rule still degenerates: `0.117647`, with the exact fraction beside it. The W0 test checks the rank *at* the published floor rather than only that it is below alpha. |
| **W0-F3** | The rulings' `d7_measurement_records_present` was computed as "every D7 evidence file except a hard-coded few", so it went non-empty as soon as the W0 records were regenerated in dependency order — a chronology claim that reported file existence rather than measurement. | The exclusion list names the ten W0 authority records explicitly and is published inside the record, so the field means *no measurement record exists* and still catches every W1+ record. |

None of the three changes a threshold, and none of them touches a released record.

## W0 validation

- `ruff check` and `ruff format --check` with `--config ruff.cognitive-os.toml` over
  `src tests scripts infra`;
- `mypy src/cognitive_os` — 628 source files, no issues; `bandit -r src/cognitive_os`;
- `python -m cognitive_os.schemas.export --check`; `scripts/check_repository_language.sh`;
- `scripts/pre_registration_d7.py --check` — 6 contracts, 7 children, 1 amendment **carried and
  0 made**, 0 measured values, 0 thresholds changed;
- `tests/cognitive_os/learning/test_d7_w0_evidence.py` — 24 assertions over the eight sealed
  records, with every arithmetic claim recomputed from the modules rather than read back;
- the three groundwork modules' own tests — `test_repair_containment.py` (7),
  `test_containment_contrastive.py` (11), `test_transfer_gap.py` (7);
- the full test suite: **4,076 passed, 0 failed, 217 skipped**.

All four scripts and the four test modules were formatted **before** the records they produce
were regenerated, and every record was then rewritten in dependency order — rulings, audit,
revision 7 — so no sealed hash carries a pre-format byte. `--check` re-verifies the seven child
hashes after the fact.

Two of the three findings were caught by that regeneration rather than by review: W0-F3 is
visible only when the generators run twice, and a fixture defect behind W0's transfer-gap
tests — a `hash()`-derived seed, which Python salts per process — was caught the same way and
fixed before it could flake in CI.

## What W0 did not do

- It closed no Gate L2 condition. Gate L2 does not pass and Sprint 22A remains blocked.
- It authored no corpus, executed no campaign, derived no bar and **fitted no direction**.
- It read no certification decision, no bar-setting margin, no retrieval query and no final or
  canary body.
- It changed no released code, no encoder, no normaliser, no released hypothesis class and no
  released direction — **and no gate threshold of any kind**. D7 made no amendment.

## What W1 needs, and what would stop it

W1 authors 100 certification groups and 400 outcomes under the D4 authoring contract, whose two
execution-only defect patterns and rising withdrawal rate are budgeted for inside the wave, and
runs the §5.1 vertical slice first — with the two seams the backlog names: `relational_numbers`
refusing drifted scalar names, which the W0 unit tests already exercise on fixtures, and the
pure-deletion group, which `test_repair_containment.py` pins to every share zero and the frozen
order standing.

Nothing else blocks it: the bar-setting half is named and bound, the fitting pool is sealed, the
class is frozen with the model hash W2 must reproduce, and the ladder §2.3 reads is decided.

The one thing that would stop D7 now is a withdrawal of one of the three rulings. While no D7
measurement exists — the state the chronology proves — that withdrawal costs one record and the
sprint ends at §3.4 branch 0, `successor_contract_refused`. After W1's corpus is sealed it costs
the corpus too.

---

# W1 closed — the corpus, and the measured run

- **Status: W1 closed.** S21D7-020 through S21D7-024 are done. The certification corpus is
  complete at **100 groups**, sealed non-provisionally, and the measured campaign has been run
  in a store of its own.
- Corpus seal: `4b946104b71a276daf71402316cb81266161c35eb7840442bb442e61e239feb0`,
  `provisional: false`, revision 7, 1380 candidate slots, volume point 720.
- Migration head: `0015`, unchanged.
- Gate L2 still does not pass. W1 measures the corpus, not the bar: no operating point has been
  derived, no margin has been read, and §2.3 is untouched. The bar belongs to W2.

## The corpus

Sixteen batches, seven groups withdrawn, twenty-four further ideas rejected before a body was
written. The result is exactly the shape the backlog asks for:

| family | groups | | family | groups |
|---|---|---|---|---|
| boundary and collections | 17 | | numeric logic | 17 |
| data transformation | 17 | | parsing and validation | 16 |
| error handling | 17 | | state and idempotency | 16 |

`certification_corpus_complete` is true and the shortfall is zero. The whole corpus was then run
rather than the last batch: **500 bodies against both suites, 1000 suite runs, 0 contract
defects**, every body encodable by the canonicaliser. Separation holds over all nine roles — 36
pairs, all disjoint, **0 cross-group collisions touching D7**, and no group authored twice.

## W1 findings

### W1-F1 — the pre-check could report occupied ground as free

`corpus_d7.py --search` printed the twelve *closest* hits, ranked by how many of the searched
words a group matched. A word searched alongside seven others matches once and sinks below every
multi-word hit, so the ranking discards precisely the groups that answer the question being
asked. `rename` reported free with `d4-transform-rename-fields` seventh in its own list; `seat`
reported free with D7's own `_G009` in it. Both were authored a second time, and the duplicate
template ID did not fail — it replaced the first under the same key in the registry mapping, and
the only trace was a group count one short of the spec count.

Fixed inside the wave, in the tool rather than in the bodies: `--search` now reports `by_word`,
untruncated, so a word with hits cannot print as free whatever else was searched beside it; and
separation reports `groups_authored_twice`, because a group authored twice is not a near-clone
pair — the second spec never reaches the comparison at all.

### W1-F2 — two task-level duplicates, one of them already committed

`d7-parsing-timezone-offset` is `d4-parsing-utc-offset`: the same function name, the same two
edge cases — the sign applied to the minutes as well as the hours, and Z read as no offset — and
the same baseline reason. Its bodies were written independently enough that the near-clone
detector never flagged them, and the two contracts share no vocabulary the prose search could
match, so it sat in the corpus through two commits until a search for a different group
surfaced the released one.

`d7-error-stall-fallback` went the same way. Reading `d5-error-suppress-expected` to condemn a
*new* group condemned that one too: both carry the same two distinguishing clauses — the
fallback belongs to one named failure, and a falsy answer is still an answer.

Both are withdrawn and replaced. The general statement is worth keeping: **a task-level
collision is invisible to the near-clone detector whenever the bodies were written
independently, and invisible to the prose search whenever the two contracts use different
vocabulary.** What catches it is reading the closest released contract in full, before the
bodies. That is now where most of the authoring effort goes, and it is the cheapest part of the
wave.

### W1-F3 — a hidden test written in the direction the defect does not run

`refund-once`'s second hidden case asked for a *refusal* that both readings give. The buggy
comparison — the amount against the allowance left across all orders, rather than against the
order's own value — is strictly harsher than the contract: it never accepts what the contract
refuses, only refuses what the contract accepts. A hidden test written in the refusing direction
therefore separated nothing, and `variant_three` passed the hidden suite. The case is now
written in the direction the defect actually runs, and the clause both readings agree on moved
to the visible suite, where a case both candidates satisfy belongs.

This is failure mode 1 in the disguise the pre-check cannot see, and only execution reveals it.

### W1-F4 — the released registry did not carry the corpus

`reality_tasks.py` addressed no D7 template, so the first campaign run failed on
`KeyError: 'd7_boundary.escort_pairs'`. This is D6's W1 finding #4 repeating on the wave that
inherited the file: registering the corpus is a step the corpus module cannot take for itself.
`_D7_TEMPLATES` is registered and the arithmetic guard updated; the guard is what would have
caught a template ID colliding across corpora, and it is now the only thing that does.

## The measured run needed a store of its own

The seal stage refuses to run where the campaign stream already carries events, and after the
provisional trial it does. The guard is right: in that store the seal does not precede the first
container. `cognitive_os_s21d7_measured` and `artifacts-s21d7-measured` were provisioned at head
`0015` — 115 tables, identical to the trial pair — and the §5.1 vertical slice re-run there
first. The trial store keeps the trial's record; nothing was pruned to make a count come out.

## The measured chain

| stage | result |
|---|---|
| vertical slice | 5 containers, 12 refusals, artifact bound and restored, bar reproduced across a restart, 0 containers on the replay |
| feature seal | **400 records, 400 distinct vectors, 0 containers started**, 2 refusals |
| v3 relational assembly | 100 groups, 377 distinct relational vectors, content hash `943ac1f086a7d8d3` |
| execute | **400 runs, 200 hidden-passing, 0 baselines through hidden**, 0 containers on the replay |
| snapshot | **11 of 11 scans passed**, maximum cross-split similarity `0.989324` against the 0.999 floor |

200 of 400 passing the hidden suite is the authoring contract at scale: exactly the two full
repairs per group, and not one of the hundred baselines got through.

The snapshot rebuilds D6's certification matrix from its released bytes and proves it against
the hash D6 published — `conformal_matrix_is_d6s_published_one: true`, `rebuilt_identically:
true`. Those bytes are resolved out of the `-measured` store that W0-F1 put under the freeze;
without that finding the bar-setting half would have been rebuilt from bytes no released record
fingerprints.

## W1 evidence index

| record | integrity hash |
|---|---|
| `sprint-21d7-corpus-separation.json` | `bf27eaea142e0560` |
| `sprint-21d7-sealed-manifests.json` | `bd1c45c3c0d5b390` |
| `sprint-21d7-vertical-slice.json` | `c79e372cab420a55` |
| `sprint-21d7-feature-seals.json` | `ac3bd37c684b2b70` |
| `sprint-21d7-certification-campaign.json` | `65c44ed9634569bf` |
| `sprint-21d7-snapshots.json` | `63018e8987253310` |

## W1 validation

- `scripts/corpus_d7.py` — 100 groups, 1000 suite runs, 0 contract defects, 500 of 500 bodies
  encodable, `ready: true`, shortfall 0.
- `scripts/separation_d7.py` — 9 roles, 36 pairs, all pairwise disjoint, 0 collisions touching
  D7, `certification_corpus_complete: true`, every predecessor digest unchanged.
- `scripts/sealed_manifests_d7.py` — `provisional: false`, protected roles identical to D6,
  fitting pool membership and body both true and **not re-executed**, conformal half membership
  and body both true, 0 retrieval groups authored by D7.
- ruff, ruff format, mypy over `src/cognitive_os` — clean.
- 1952 coding and learning tests green.

## What W1 did not do

- It derived **no operating point** and read **no conformal margin**. `quantile_exists_at_alpha_0_20`
  is false on the slice fixture and no margin was taken over the sealed bar-setting half at all.
- It moved **no gate threshold**, amended **no §2.3 sentence**, and changed no released code,
  encoder, normaliser or released hypothesis class.
- It wrote **nothing** to any predecessor store. D5's and D6's stores were read for the envelope
  and the bar-setting half's bytes, by artifact identity, read-only.
- It authored **no retrieval groups**: the retrieval pool is inherited whole.

---

## W2 outcome — three rulings before the first score, one bar, and `1_select`

Five scripts, ten sealed records, **one measurement**. The wave that D5, D6 and D7's own
groundwork were building toward ends at §3.4's **step 1**: every amended §2.3 condition holds on
the one pre-registered cell. What follows states the numbers, and — because a pass is easier to
publish than to read — states beside them exactly which rulings the pass depended on and what
the other branch of each would have said.

### Step 0 — the three rulings, taken before anything was scored

`scripts/w2_rulings_d7.py`. The W2 pre-flight had put two readings and one reversal to the gate
owner; all three were answered before a single certification decision was ranked. The chronology
block that licenses them reports what had to be zero and was:

```
d7_certification_decisions_scored             0
d7_conformal_bars_derived                     0
d7_directions_fitted_in_wave                  0
d7_ladder_measurements_on_the_fresh_corpus    0
```

W1's four measurement records are **named** in that block rather than excluded from it. They
measure the corpus — which bodies pass which suite, what seven channels each candidate has —
and score no decision, so a ruling chosen to suit them could only be a ruling about the corpus,
and none of the three is.

| item | ruling | thresholds moved |
|---|---|---|
| **S21D7-025** | the frozen disjointness sentence binds to its two leakage properties: zero shared decision signatures, zero shared canonical sources. Aliasing is reported as the coverage ceiling, never as a pass | 0 |
| **S21D7-026** | the baseline condition reads the strongest rung's **whole-corpus** rate, the rate every released ladder record publishes | 0 |
| **S21D7-027** | **S21D7-011 superseded** — the containment rung is *unseated*; the frozen five stand and the containment ordering is reported beside them as an unseated measurement | 0 |
| **S21D7-028** | revision **8**, in its own file so revision 7's children hashes stay valid, `measured_values: 0` | 0 |

The superseded ruling is **not rewritten**. It stays sealed exactly as W0 left it, hash included,
inside revision 7's children; the supersession references it by `file_sha256`. A superseded
ruling that is edited is a ruling nobody can audit.

### The one fit — `d80160c4…` reproduced

`scripts/w2_direction_d7.py`. `containment-contrastive-linear-v1` fitted **once**, on the
released 180-group / 720-pair D5 fitting pool, λ = 1, margin floor 0. The model hash is
`d80160c4aa795fadd98fb4e6d4f64b7b29a2a3685c537454b8aff95daa124859` — the value revision 7 froze
before the class had been fitted in this sprint. A second process re-derives the record byte for
byte; **no record written by this wave's fit carries a timestamp**, precisely so that the restart
check cannot pass vacuously.

The §4 transfer gap is re-sealed as W-stage evidence in the same run, bound to the groundwork
bytes by file hash rather than pointed at: it is the measurement that licenses the class question
at all, and the direction it diagnosed is the direction fitted here.

### The scan, at the level the class reads

`sprint-21d7-w2-relational-scan.json` carries **both** levels beside each other. W1's eleven
released scans prove separation over the 390-channel v2 representation; they cannot see what
seven numbers collide on. At the v3 level, across all three half pairs:

| pair | shared decision signatures | shared canonical sources | aliased vectors |
|---|---|---|---|
| fitting pool ↔ demoted bar-setting | 0 | 0 | 15 |
| fitting pool ↔ certification | 0 | 0 | 23 |
| demoted bar-setting ↔ certification | 0 | 0 | 11 |

Zero on both leakage properties, on every pair. The aliasing counts are published as the ceiling
on reachable coverage, which is what S21D7-025 bound them to.

### The ladder on the fresh corpus — five rungs, one unseated measurement

`scripts/w2_ladder_d7.py`. The five released rungs, of which three are eligible on this surface
for the reasons the released implementations state in their own words:

| rung | eligible | first-choice rate |
|---|---|---|
| `fixed_input_order` | yes | 0.47 |
| `deterministic_static_ordering` | yes | 0.13 |
| **`lexical_similarity`** | yes | **0.61** ← strongest |
| `frozen_minilm_cosine` | no — no columns under the v2 encoder | — |
| `width_20_bounded_graph` | no — twenty wide over four candidates is the whole pool | — |
| *`repair_containment_share`* | **unseated** | *0.82, reported, sets no baseline* |

The class's own whole-corpus first-choice rate on this corpus is **0.83**. Both changed-decision
pairings are reported: **74** decisions differ from the strongest released rung over the whole
corpus, **26** from the containment ordering.

### The bar, derived once

`scripts/learner_selection_d7.py`. The demoted D6 certification half — the bar-setting half under
S21D7-010 — re-scored under the class: **0.84** first-choice, **16** wrong answered decisions,
quantile rank **14** at α = 0.20, exactly the arithmetic the demotion ruling published before the
half was re-scored. The bar is `0.489867`, derivation hash
`04b34f7e0c94ffa25fd6119c92bb3279d0f673e7e2fa5418e14e7fed87d8c4c5`, and it reproduces across a
process restart.

A decision's identity is its four **relational** vectors in slot order, per S21D7-025. The
derivation refuses two halves sharing one and refuses a half containing a replica; neither
refusal fired.

### The certification cell

| quantity | value | condition |
|---|---|---|
| independent clean decisions | **100** | ≥ 100 ✓ |
| answered | 100 | — |
| admitted | **59** | — |
| clean coverage | **0.59** | ≥ 0.40 ✓ |
| errors admitted | **3** | — |
| Clopper-Pearson 95% upper bound | **0.126207** | ≤ 0.15 ✓ |
| first choice over admitted | **0.9492** | > 0.61 ✓ |
| changed decisions | **46** | ≥ 1 ✓ |
| projected changed final decisions | **46.780** | ≥ 20 ✓ |
| first-action preservation | **100%**, 0 flips of 40 | 100% ✓ |
| sweep points reported | **90**, none selectable | all ✓ |
| maximum inference | 0.023 ms | ≤ 250 ms ✓ |

The realised leak is **3 of 17** wrong decisions clearing the bar — 0.176 against the 0.20 budget
— so the bar held the guarantee α actually makes, and the ceiling the amended §2.3 reads was met
separately. Of the 90 sweep points, 52 sit at or above the coverage floor and **39** satisfy the
amended pair, best bound `0.086407`: the pair is reachable on this corpus and not only at the
derived bar.

**Ending: `1_select`.** No condition failed.

### What the pass depended on — both rulings, priced

A pass whose margin comes from a ruling has to publish what the other branch would have said, so
the selection record carries both, neither as a condition:

- **S21D7-026 was not load-bearing.** Recomputed on exactly the 59 admitted decisions,
  `lexical_similarity` scores **0.627** against the class's 0.949. The condition passes under the
  reading the ruling *declined* as well as the one it took.
- **S21D7-027 was load-bearing, on the condition the pre-flight predicted.** Against the
  containment ordering the class's admitted rate 0.949 still clears 0.82 — but only **5** of the
  59 admitted decisions differ from it, projecting **5.085** changed final decisions against a
  floor of 20. Under the seated pairing this cell fails `§2.3` on the changed-decision condition.
  The pre-flight measured that consequence on the two spent corpora *before* the ruling was
  taken, which is the whole reason the ruling was legitimate to take.

### The invariance regression, measured rather than implied

`scripts/invariance_regression_d7.py`. 40 cases over 20 certification groups, 160 candidate
vectors: **0** relational vectors changed, **0** verifier label changes, **0** first-action flips,
and all four seeded semantic mutations changed the canonical representation.

Three things this run does that D6's could not, all because the class dropped the embedding:
the encoder is rebuilt from the **campaign's own sealed bounds** and proved by re-encoding all 80
clean bodies against their sealed values before anything transformed is read; **no embedding is
computed at all**, which retires D4's W2-D9 batch-composition finding for this record; and the
first action is compared under the fitted direction directly rather than argued from premises.

### W2 findings

**W2-F1 — a `--check` that expires.** `w2_rulings_d7.py --check` re-globbed the evidence
directory to rebuild the chronology block. That block describes a *moment*, and W2's own
measurement records did not exist at it — so from the first record this wave wrote, the check
compared two different moments and failed on the passage of time rather than on drift. Fixed
in-wave: under `--check` the file listing is taken from the sealed record and every *claim* is
still re-derived from the pre-flight. A verification tool that can only pass once is not one.

**W2-F2 — a stopwatch in a reproducibility check.** The cell reports `maximum_inference_ms`,
measured live, so the selection record could never reproduce byte for byte. `--check` now ignores
exactly three fields — two wall clocks and that stopwatch — and still compares
`within_inference_budget`, so a run that breached the 250 ms budget fails the comparison.

### W2 evidence index

| record | integrity hash (16) |
|---|---|
| `sprint-21d7-disjointness-clarification.json` | `9f8410a0cce03ad4` |
| `sprint-21d7-baseline-reading.json` | `2323dbc19d391b59` |
| `sprint-21d7-ladder-supersession.json` | `1f42f706e5bcc735` |
| `sprint-21d7-pre-registration-r8.json` | `e14ce34293ed6852` |
| `sprint-21d7-w2-direction.json` | `0790e1f68d64e551` |
| `sprint-21d7-w2-transfer-gap.json` | `ed6c621d7c4e72f8` |
| `sprint-21d7-w2-relational-scan.json` | `31eda3cdc815bda4` |
| `sprint-21d7-w2-ladder.json` | `c301dddb117ecc49` |
| `sprint-21d7-invariance-regression.json` | `90a2c63719456993` |
| `sprint-21d7-learner-selection.json` | `63fd43dab720c57e` |

## W2 validation

- `scripts/w2_rulings_d7.py --check`, `scripts/w2_direction_d7.py --check`,
  `scripts/w2_ladder_d7.py --check`, `scripts/learner_selection_d7.py --check` — all reproduce;
  the last run twice in two fresh processes.
- The direction reproduces `d80160c4…`; the bar reproduces derivation hash `04b34f7e…`.
- Both rebuilt matrices equal their published hashes: `747eb966…` (bar-setting), `1a0f9e65…`
  (certification).
- ruff, ruff format over `scripts/`, `src/`, `tests/` — clean. mypy over `src/cognitive_os` —
  631 files, no issues.
- **4082 tests passed, 217 skipped.**

## What W2 did not do

- It fitted **one** direction and derived **one** bar. No second cell, no second alpha, no volume
  ladder, and no threshold chosen off the 90-point sweep — every point is reported and none is
  selectable.
- It moved **no threshold**. α = 0.20, C = 0.15 and the 0.40 coverage floor are D6's, carried
  unchanged; D7 makes zero amendments across all three waves.
- It opened **no final, batch-B or canary body** and inspected **no** such outcome.
- It wrote to **no** store. Three artifact stores were read by content address, read-only, and no
  database was opened.
- It did **not** promote anything. `1_select` is eligibility under §2.3; binding the artifact,
  running the lifecycle and closing Gate L2 are later steps with records of their own.
