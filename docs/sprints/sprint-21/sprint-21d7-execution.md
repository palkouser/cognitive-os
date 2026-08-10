# Sprint 21D7 execution log

- Branch: `sprint-21d7-groundwork`
- Backlog: [Sprint 21D7 Technical Backlog](sprint-21d7-technical-backlog.md)
- **Status: W0 closed.** S21D7-000 through S21D7-005 and S21D7-010 through S21D7-019 are done.
  The three governance rulings W0 exists to obtain were all taken and the condition-24
  inheritance was renewed. Revision 7 is published with `measured_values: 0`, and **no threshold
  moved**.
- Pre-registration: revision 7, SHA-256
  `4017be51c6e06d6123982d2572a9dcd346bb23decc7d1bcfe2c995ee95c2fc7f`
- Migration head: `0015`, unchanged. `0016` remains unallocated.
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
