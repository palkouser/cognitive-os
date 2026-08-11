# Sprint 21D7 execution log

- Branch: `sprint-21d7-groundwork`
- Backlog: [Sprint 21D7 Technical Backlog](sprint-21d7-technical-backlog.md)
- **Status: SPRINT CLOSED. Gate L2 passes at 29 of 29 — 0 pending, 0 failed, 0 not opened.**
  Gate D1's conditions 6, 7 and 15 are all closed. **`not_opened` is zero for the first time in
  the D-series.** Sprint 22A is unblocked.
- Release: `#229` squash-merged into protected `main` at `2026-08-11T09:09:57Z`, commit
  `3f5d7379caf85290da45885e22138506211bee2e`; exact-head post-merge CI run `31476479587`,
  **30 of 30 jobs successful**; annotated tag **`sprint-21-learning-baseline`**, object
  `3025082526cef6d97fe87cc24bd63cab0252e6a2`, created after that CI and never moved.
- **Status: W3 closed. The artifact is activated on the canary subset.** S21D7-000 through
  S21D7-005, S21D7-010 through S21D7-019, S21D7-020 through S21D7-024, S21D7-025 through
  S21D7-034 and S21D7-035 through S21D7-039 are done. W2 ended `1_select` with every amended
  §2.3 condition met; W3 stored the direction as bytes, opened the two carried final roles and
  measured **+0.383 absolute** over the strongest rung on 60 groups, and drove a real governed
  activation across four processes and two database restarts. Conditions **25, 26 and 27** — which
  have read `not_opened` in every gate assessment since D2 — are open and met. **No threshold
  moved in any wave.** **W0 detail follows first**, then W1, W2, W3.
- **One finding in W3**, and it is the wave's: the carried final roles could not be encoded at all.
  See W3-F1.
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
- **At W0**, Gate L2 did not pass and Sprint 22A remained blocked. W0 measures nothing and closes
  no condition; it establishes the authority every later wave is bound to. The status line at the
  top of this log is the sprint's; this bullet and the ones above it are W0's, and the wave
  sections below each keep the state they were written in.

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

---

# W3 closed — the artifact, the final evidence, and a governed activation

Three commits, eleven sealed records, **one finding**, and the three conditions that have read
`not_opened` in every gate assessment since D2 are open and met. W3 is the wave that turns
`1_select` into something that ran: the direction W2 fitted is stored as bytes, bound to a
lineage, measured on 60 groups carried unopened for five sprints, and then activated on five
groups under an approval that names it exactly — and switched off again to prove it can be.

**No threshold moved in W3 either.** α = 0.20, C = 0.15 and the 0.40 coverage floor are still
D6's; D7 amends nothing in any wave.

## The artifact — conditions 11 and 22

`scripts/artifact_d7.py` stores the fitted direction as a v3 correction-ranking artifact:
**4354 bytes**, seven relational channels, model hash `d80160c4…`, artifact hash `afbdb7c0…`.
Its lineage names D5's 180-group fitting pool as the training dataset and the demoted D6
certification half as the calibration dataset, under S21D7-010.

The condition that matters is 22, and it is deliberately not a structural check. **Loading is not
the test; ranking is.** The stored bytes are re-read, rehashed, rebuilt through
`build_ranker_for_evaluation_v3` under a lineage capability, and then made to re-rank all **100**
certification groups: every first choice and every margin reproduced, **0 decisions disagreeing**.
An artifact that loads but ranks differently passes every hash check ever written, and it is the
exact failure this condition exists to catch.

**Seven refusals executed**, not asserted: edited weights, a capability naming another artifact
hash, a wrong descriptor, a wrong revision, a class the loader does not implement, bytes past the
size ceiling, and a purpose the lineage does not authorise. Each one raised.

## The runtime — condition 23

`scripts/runtime_d7.py` drives the resolver to **all 18** `RuntimeHealthReason` values against the
real artifact's own identities. Two words in the condition do the work.

*Real.* The resolver is pure and never opens a store, so a record could reach all eighteen codes
with a fabricated availability struct and prove nothing. Every case here is derived from the
artifact loaded out of D7's store: its component id, surface, revision, byte count and artifact
id. A case that needs a wrong value derives it from the right one.

*Immediate.* For **each of the 17 fallback codes** the deterministic ordering is computed over all
100 certification groups and compared against the released strongest rung's — and all 17 agree
with it and with each other, group for group. Only `active` differs, on **74 of 100** decisions,
which is the model doing something rather than reproducing the baseline expensively.

## W3-F1 — the carried final roles could not be encoded

The seal stage stopped on the first final body it tried to canonicalise:

```
SourceNormalizationError: reflection-unsafe binding through hasattr()
```

**Four authored bodies** predate the source canonicaliser's reflection ban — three bind a name
through `hasattr()`, one uses an assignment expression the frozen grammar does not cover. They
were authored in D2. Five sprints since then recomputed the carried catalogue digests, found them
unchanged, and recorded the roles as carried intact.

They *were* intact. The finding, stated plainly: **a digest recomputed unchanged proves the bytes
did not move, not that anything can use them.** No sprint ran a final body through the
canonicaliser, because opening the roles is what W3 does.

Neither rule was relaxed. The reflection ban exists because the invariance sample renames every
identifier, and a body that reaches a name reflectively survives the rename with different
behaviour. `sprint-21d7-final-role-audit.json` (S21D7-038) is the audit that should have run in
D3: it puts every body of all three carried roles through the canonicaliser, finds two roles
failing, and exercises §3.5's own exception — final bodies may be authored when a whole role fails
its audit. It was sealed with `bodies_authored_by_this_record: 0` and
`replacement_bodies_existing_when_this_was_sealed: 0`, and the chronology block is the proof of
that order: an authorisation written after the replacements exist is a description of what
someone already did.

**Four replacement groups** were then authored in `reality_task_specs_d7_final.py` and substituted
positionally, keeping the frozen **30 groups / 120 outcomes** per final role. The canary role
passed its audit whole and was carried untouched. The two final catalogue hashes are now D7's;
every later record binds the new ones.

The hazard the audit record refuses to hide: the replacements were chosen by an author who had
already seen the selection's numbers. Not the bodies themselves — the class never sees them before
execution and the labels come from the hidden verifier — but the choice of what to author, and a
final batch is meant to be the least contaminated evidence in the sprint.

`tests/cognitive_os/coding/test_reality_d7_final_replacements.py` adds 8 tests, written over the
**roles** rather than over the replacements, so the next carried body is covered too. The first of
them is the check five sprints of unchanged digests did not amount to.

## The final roles, opened once — condition 10

`--role final` seals and executes into records of its own, and refuses to start unless the
selection record says `1_select`. Two campaigns, **30 groups and 120 outcomes each**.

## The final evidence — conditions 13, 14, 15, 16 and 21

| | |
|---|---|
| learned first choice | **52 / 60 = 0.8667** |
| strongest rung on the final set (`fixed_input_order`) | 29 / 60 = 0.4833 |
| **absolute gain** | **+0.3833** (floor 0.05) |
| **relative error reduction** | **0.7419** (floor 0.20) |
| **changed decisions** | **45** (floor 20) |
| final A / final B direction | **+0.300** / **+0.467** |
| paired group bootstrap, 10 000 resamples | **[0.233333, 0.533333]**, excludes zero |
| shadow: would have changed / did change | **45 / 0** |

The baseline is **re-derived per batch** rather than carried: these are D2's groups, not the
certification half's, and `fixed_input_order` came out strongest on both. The bootstrap resamples
**groups**, not decisions — the two orderings answer the same groups, so the per-group difference
is the quantity with a distribution, and resampling decisions independently would break the
pairing that makes the comparison sharp.

Condition 21 records both numbers deliberately. A shadow record showing only that nothing changed
would be satisfied by a component that was never evaluated at all.

## Safety, retention, metamorphic — conditions 18, 19 and 20

- **18:** 240 candidates scanned across five construct classes; **0 of the 45 changed decisions**
  move from a clean candidate to one carrying a named construct. Measured as *movement*: a corpus
  total would pass on a corpus where the model reliably picks the single dangerous candidate.
- **19:** no task family lost a point; worst domain loss **0**, aggregate loss **0**, with losses
  only — a family that gains does not offset a family that loses.
- **20:** **120 nominal / 60 independent** promotion decisions, every transformation repeating its
  source decision, **80 admitted, 0 errors**, Clopper-Pearson bound **0.036754** against C = 0.15.

## The canary role, executed — and what condition 25 needed it for

Condition 25 asks that every learned-first correction runs the verifier. That is only checkable if
learned-first corrections actually run, so `--role canary` was added to the campaign — gated on
the same `1_select` pass the final roles are gated on — and the five canary groups were sealed and
executed in the sandbox: **20 candidate runs, 10 accepted by the hidden suite, 0 baselines
passing**.

## The governed activation — conditions 25, 26 and 27

`scripts/lifecycle_d7.py` runs the whole lifecycle against the measured store as **four separate
processes** with the database container restarted between them. A lifecycle that only ever runs
inside the function that created it passes every check that never restarts anything, which is the
failure condition 26 names.

```
register → lineage → shadow → verify → approve → activate
  ↓ restart
observe: active, artifact loads, five groups routed
  ↓
kill switch: disabled, deterministic on the very next call
  ↓ restart
restore: disabled survived; rollback returns to the exact prior activation
```

The ledger holds **six revisions** for one component, replay matches the projection, the hash
chain verifies and health is green.

### Condition 27 — the approval, and three refusals

The approval names the exact assessment hash `e964dc5d…`, component revision 3 and lineage
`4509e1be…`; the service compares every one of them against durable state before the transition.
The approving identity is a human operator and is **not** the actor that carries the activation
out. **Three refusals executed:**

| attempt | refused by |
|---|---|
| approve the activation with a `model` identity | the contract, at construction |
| activate under a human approval naming another assessment | `evidence_mismatch: ['promotion_assessment_hash']` |
| activate as an actor never granted activation authority | the activation-authority check |

The record states the hazard rather than arguing it away: the approving identity is the human who
ordered the wave, and the hand that carried it out was an agent acting under that instruction. The
separation the condition asks for is the one it gets — the authority is neither a model nor a
provider identity, and it is not the actor in the receipt — but nobody should read the row as an
operator who reviewed the payload byte by byte independently of the process that produced it.

The promotion payload behind it is not shape-only: **all 20 D3 gates** are bound by hash to the D7
record that measured them, and `evaluate_d3_promotion` returns eligible against bindings the
caller supplies rather than fetches. The legacy assessment carries D7's real ladder — pooled over
both final batches — and the contract pins `baseline_metric` to its strongest non-learned rung, so
the comparison cannot be made against a rung chosen afterwards.

### Condition 25 — hash-bound, verified, and immediately reversible

- **Hash-bound.** The routing manifest hash **is** the canary catalogue's own content hash. A
  group outside the subset resolves `group_not_routed`; a manifest hash that moved resolves
  `routing_manifest_mismatch`. Neither permits the learned ordering.
- **Verifier mandatory.** Five corrections proposed, **five verifier labels read**, **zero**
  accepted without one. The model orders candidates; every candidate the sequencer reaches carries
  a label produced by a container run.
- **Kill switch immediate.** One call after the disable the resolver answers `lifecycle_not_active`
  on all five groups with the learned path permitted **nowhere**, in 0.026 s and with **zero**
  artifact loads on the fallback path. The disabled row is handed to the resolver rather than
  filtered out first: "this surface has no component" is a different fact from "the component it
  has was switched off", and the second is the one an operator needs at three in the morning.

What the canary actually did, on the five routed groups: the learned ordering reached an accepted
candidate in **5 attempts**, the released rung in **9**. The learned first choice was accepted
**5 / 5**; the rung's first choice **1 / 5**.

### Condition 26 — what survived

| | |
|---|---|
| processes | **4**, distinct pids |
| database restarts | **2**, container `compose-postgres-1` |
| after restart 1 | `active`, revision 4, surface held, activation receipt unchanged |
| artifact after restart | reloaded, rehashed, model hash matches the sealed one |
| after restart 2 | `disabled` survived; rollback restored `active` |
| rollback target | the original activation receipt, reusing the same approval |
| replay | 6 revisions, projection matches, hash chain verified, health green |

## W3 evidence index

| record | integrity hash (16) |
|---|---|
| `sprint-21d7-artifact.json` | `b38e3f60a13c4c8f` |
| `sprint-21d7-runtime.json` | `d4882a2481d31095` |
| `sprint-21d7-final-role-audit.json` | `067809d5b945e36b` |
| `sprint-21d7-final-feature-seals.json` | `a10d87fc651f0fdf` |
| `sprint-21d7-final-a-campaign.json` | `22ba61e58ac18c3e` |
| `sprint-21d7-final-b-campaign.json` | `fb00fb7c027715a7` |
| `sprint-21d7-final-evidence.json` | `a8aa099a5d32f9a0` |
| `sprint-21d7-promotion.json` | `fde811401cb85dab` |
| `sprint-21d7-canary-feature-seals.json` | `4211799b249c09a7` |
| `sprint-21d7-canary-campaign.json` | `9ac83cf3e14259e9` |
| `sprint-21d7-lifecycle.json` | `155fc87f4bcef558` |

## W3 validation

- `scripts/artifact_d7.py`, `scripts/runtime_d7.py`, `scripts/final_role_audit_d7.py`,
  `scripts/final_evidence_d7.py`, `scripts/promotion_d7.py` and `scripts/lifecycle_d7.py` all
  run clean; every record they write carries its own `integrity_content_hash`.
- The stored artifact rehashes to `afbdb7c0…` and rebuilds to model hash `d80160c4…` in three
  separate processes — the artifact stage, the runtime stage and twice inside the lifecycle,
  once on each side of a database restart.
- All 18 runtime reason codes reached; 17 fallbacks agree with the released rung on all 100
  certification groups.
- The lifecycle ledger replays: 6 revisions, projection matches, hash chain verified, health
  green, 0 integrity failures.
- ruff and ruff format over `scripts/`, `src/`, `tests/` — clean, 1155 files. mypy over
  `src/cognitive_os` — 632 files, no issues.
- **4090 tests passed, 217 skipped.**
- Wave commits `d3a5aef`, `8c4b51f` and `34b9be8` on `sprint-21d7-groundwork`, pull request
  **#229** against protected `main`; CI run **`31466617491`** on head `34b9be8`, **30 of 30
  jobs successful**. The merge is the gate owner's, not the wave's.

## What W3 did not do

- It did **not** enter the bounded steady-state configuration. That configuration is sealed and
  bounded at 400 tasks, and the sprint stops at the canary; the record says so rather than letting
  an unentered configuration read as an operating one.
- It did **not** exercise the rollback *refusal* path — a disable that followed a failed canary
  may not be restored. That half is D4's S21D4-075 on the isolated fixture; re-proving it here
  would have meant ending the sprint with the component disabled and unrestorable.
- It **truncated, erased and nominated for erasure nothing**. Every write to the measured store is
  an append-only ledger row, an evidence row or an artifact; the store that holds the campaign was
  never nominated under `COGOS_TRUNCATABLE_DATABASE`.
- It moved **no threshold**, in this wave or any other.
- It did **not** close Gate L2. The gate assessment is a step of its own, and the conditions this
  wave opened are reported there against the same sealed hashes.

---

# W4 — the release matrix, the gate, and one validator that outlived its claim

Four scripts, four sealed records, **one finding**, and a gate assessment that reads **28 met, 1
pending, 0 failed, 0 not opened**. The pending row is condition 29, which the protected release
closes and which this wave cannot close for itself.

## The release matrix — condition 28

`scripts/verification_matrix_d7.py` runs **46 rows** and records what each actually did: the
command, the expected answer, the exit status, the wall-clock cost and the SHA-256 of the combined
output. Three rules make it a matrix rather than a list — negative rows must fail *for their
declared reason*, nothing is silently skipped, and the record checks itself where it is written
rather than in a test that would read the previous run's copy.

What D7 carries that D6 did not:

- **six `--check` validators instead of two.** Four of D7's records carry no timestamp by
  construction, so `--check` in a fresh process *is* the restart-reproduction proof rather than a
  report about one. A release that did not run them would be taking W2's word for its own
  arithmetic.
- **twelve rows recorded from committed evidence**, eight of them about things D6 never reached:
  an artifact that re-ranks, a resolver that reaches every code, two final batches, a promotion
  payload, a live activation.
- **six negative rows**, up from five. `campaign_refuses_the_d6_store` joins
  `campaign_refuses_the_d5_store` because D7 reads D5's numeric bounds *and* D6's whole conformal
  half out of their stores, and the guard that stops it writing there is one function with one
  list.
- **one row that reads a zero.** `proposals_accepted_without_a_verifier_label` must be exactly
  `0`, named as an expected value rather than left to truthiness — a zero is falsy, and a row
  decided by truthiness there would report a failure as a pass.

**46 of 46 passed, 0 skipped, 0 structural findings.**

## W4-F1 — the W1 seal still claimed three carried roles D7 no longer has

The matrix's first run came back **45 of 46**, failing on `sealed_manifests`:

```
sealed_manifests_d7.py --check  →  stops: ["sealed_manifests_protected_role_drift"]
```

The stop is **correct**. W1 sealed the claim that all three carried roles are byte-identical to
D6's released catalogues, and W3's authorised repair made that false for two of them — final A
`69d5eedc…` → `38be7b0a…`, final B `06a0c2f6…` → `7dd02a38…`. What is stale is not the world; it
is the rule. Nothing had yet told the validator that the change was authorised.

**Why it surfaced here and not in W3.** The validator runs in the release matrix and nowhere
else. W3 had no reason to re-run a W1 seal check, and the repair it performed was recorded in the
audit rather than in the seal. A release matrix that skipped its own sprint's validators would
have shipped the contradiction.

The fix is a **rebinding, not an edit**. `sprint-21d7-protected-role-rebinding.json` (S21D7-044)
supersedes one sentence of the W1 seal and leaves its bytes exactly as they are — the same
discipline S21D7-027 used when it superseded S21D7-011, and for the same two reasons: a sealed
record edited to agree with a later decision stops being evidence of what was known when it was
written, and every W2 and W3 record that binds `sealed_manifests_sha256` would break.

What the rebinding is willing to be wrong about:

| check | result |
|---|---|
| the **canary** role is still byte-identical to D6's | ✅ `027f2d78…` unchanged |
| every moved role is named in S21D7-038's grant | ✅ `final_a`, `final_b` |
| each audit's `sealed_hash_before` equals D6's released hash | ✅ the audit was about these bytes |
| each new hash is the one its W3 campaign **executed against** | ✅ in both the feature seal and the campaign record |
| the frozen counts survive | ✅ 30 groups / 120 slots per final role |

The stop was then narrowed rather than removed: a role that moves still stops the seal unless a
**clean** rebinding record names it. Proved by deleting the rebinding record and re-running —
`sealed_manifests_protected_role_drift` came straight back.

## The gate assessment — 28 met, 1 pending

`scripts/gate_assessment_d7.py` decides every one of the twenty-nine conditions from the evidence
that bears on it. It has no branch that writes `met` without a document behind it, no default that
upgrades a missing file, and the verdict is computed from the counts rather than stated.

**`not_opened` is zero, and that is the sprint.** D3 closed fifteen conditions behind a typed
stop, D4 sixteen, D5 sixteen, D6 nineteen. D7 closes none. The continuation record prints that
set as the empty list it now is — an omitted map is not the same claim as an empty one — and the
gate script refuses to run if the two records disagree about it.

Two rows are D7's own shape:

- **condition 3** is a W0 audit about roles W3 later opened. The row says so instead of printing
  the W0 sentence unqualified, because a reader arriving from the W3 section has just been told
  the roles were opened;
- **condition 5** checks all four campaigns, not the first. D6 had one campaign; D7 has four, and
  a row that checked only certification would leave the 260 outcomes the gate actually turns on
  unexamined. **660 candidate runs, every one carrying an independent hidden-verifier label.**

## Gate D1 — all three closed

| | | |
|---|---|---|
| **6** | 260 held-out verifier-backed outcomes against a floor of 200 | final A 120, final B 120, canary 20 |
| **7** | 45 of 60 final decisions change the advisory action, floor 20 | condition 13's evidence read against the D1 contract |
| **15** | inherited, re-checked at gate close | reads condition 24's verdict rather than reaching its own |

Condition 6 **does not count the 400 certification outcomes**, deliberately. They set the
operating cell, and counting the corpus that chose the operating point as evidence about it is
the mistake the floor exists to stop. 260 clears 200 without them.

## The continuation — the pass branch, typed

`sprint-21d7-continuation.json` types §3.4's ending `1_select` and reads its successor sentence
**out of the sealed contracts record** rather than composing one: the six endings were written in
W0 with `measured_values: 0`, and a successor sentence written after the result would be the
measurement arguing for its own follow-up.

Fifteen deliverables named with the record that closed each; **zero** not opened. The five §6
risks are carried forward verbatim, and the fourth is marked **MEASURED** — the class and its own
strongest channel are the same signal at admissible margins, which is why S21D7-027 had to unseat
the containment rung before anything could be scored.

## W4 evidence index

| record | integrity hash (16) |
|---|---|
| `sprint-21d7-verification-matrix.json` | `41aff1958383f1df` |
| `sprint-21d7-protected-role-rebinding.json` | `22159a3efd30d607` |
| `sprint-21d7-continuation.json` | `db4d6dd0cff2a0d2` |
| `sprint-21d7-gate-l2.json` | `f456f97618e70580` |

## W4 validation

- 46 of 46 matrix rows passed, 0 skipped, 0 structural findings.
- `sealed_manifests_d7.py --check` clean, and proved to still stop when the rebinding record is
  removed.
- ruff and ruff format over `scripts/`, `src/`, `tests/`, `infra/` — clean. mypy over
  `src/cognitive_os` — no issues. bandit, pip-audit, schema export, wheel and editable
  installation, both benchmark replays — all green inside the matrix.
- **4090 tests passed, 217 skipped**, run as a matrix row rather than beside it.

## The release — condition 29

`#229` squash-merged into protected `main` by the gate owner at `2026-08-11T09:09:57Z`, no
administrator bypass, commit `3f5d7379caf85290da45885e22138506211bee2e`. Exact-head post-merge
`main` CI run **`31476479587`**, **30 of 30 jobs successful**, completed `09:25:34Z`. The
annotated tag **`sprint-21-learning-baseline`** created at `09:26:38Z` — after that CI, once, and
never moved — object `3025082526cef6d97fe87cc24bd63cab0252e6a2`, peeling to the release commit.

`scripts/release_d7.py` reads every one of those handles back from GitHub rather than from this
log, and recorded **zero findings**. It creates nothing: no merge, no tag, no push. A record that
could produce the state it describes would be a record of itself.

**The ordering condition 29 forced, and the check that survives it.** Condition 29 *is* the
release, so the gate cannot read a pass until the release record exists — and the first version of
the release script refused to be written for a gate that did not already read one. That is a
deadlock, and it showed up as a finding on the first run rather than as a design note. The honest
form of the check replaced it: **every condition the release does not itself create must be met,
and 29 must be the only row outstanding.** The release was then written against a 28-met
assessment, the gate was regenerated against the release, and both records say which side of that
ordering they were written on.

Gate close: **29 met, 0 pending, 0 failed, 0 not opened, 0 carried. `gate_l2_passes`.**

| record | integrity hash (16) |
|---|---|
| `sprint-21d7-release.json` | `582aa77732308731` |
| `sprint-21d7-gate-l2.json` (regenerated) | `5b83cd4bcfa1cce9` |

## What W4 did not do

- It did **not** create the tag on its own authority. The merge was the gate owner's, and the tag
  was created once, on the exact commit that CI passed on, after that CI.
- It did **not** round 28-of-29 up to a pass at any point. The verdict is computed from the
  counts; while condition 29 was `pending` the assessment read `gate_l2_does_not_pass`, and the
  document that quoted it said so.
- It did **not** enter the bounded steady state, retire any §6 risk, or make the activated
  component a default. It routes five groups.
- It moved **no threshold**. Five waves, zero amendments.
