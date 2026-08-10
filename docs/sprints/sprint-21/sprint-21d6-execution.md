# Sprint 21D6 execution log

- Branch: `sprint-21d6-groundwork`
- Backlog: [Sprint 21D6 Technical Backlog](sprint-21d6-technical-backlog.md)
- **Status: W0 closed.** S21D6-000 through S21D6-004 and S21D6-010 through S21D6-018 are done.
  The two governance decisions W0 exists to obtain were both taken: §2.3's admission clause is
  amended, and condition 24 is inherited rather than re-measured. Revision 6 is published with
  `measured_values: 0`.
- Pre-registration: revision 6, SHA-256
  `e1e4e1d76e51bb53ea845e3a9b9e0e631903921e8b3887d289048ff7eccd6022`
- Migration head: `0015`, unchanged. `0016` remains unallocated.
- Gate L2 does not pass and Sprint 22A remains blocked. W0 measures nothing and closes no
  condition; it establishes the authority every later wave is bound to.

---

## W0 outcome — one clause changed, one condition inherited, nothing measured

Four scripts, five sealed records plus the isolation pair, zero findings. Unlike D5's W0 this
wave had a decision in front of it that no amount of engineering could substitute for: D5 proved
that §2.3's two admission requirements cannot both be met by this ranker, so either the clause
moves or the sprint does not run.

**Four scripts, and none of them released.** `baseline_d6.py` (three phases), `contracts_d6.py`,
`reuse_audit_d6.py` and `pre_registration_d6.py`. The `*_d2` through `*_d5` families produced
released evidence and stay exactly as they are.

### S21D6-000 and S21D6-002 — the starting point, read rather than restated

`sprint-21d6-baseline.json`, integrity
`779420bae68ea7686372dc3ddbfcd247b2758b61912206ff87342fc7a8fbabdb`.

| Fact | Result |
|---|---|
| `sprint-21d5-evidence-baseline` resolves remotely as an annotated tag | yes, object `799190c06497f22e…` peeling to `53cd757909653 7cd…` |
| local and remote tag handles agree | yes |
| branch descends from current `origin/main` | yes |
| `sprint-21-learning-baseline` | **absent**, checked rather than assumed |
| D5 exact-head CI runs `31327874931` and `31328614887` | re-read from the API, 30 of 30 successful each |
| branch protection | administrators enforced, 27 required checks, strict, no force pushes, no deletions |
| migration head | `0015` |
| seven predecessor artifact roots | fingerprinted; the six with a released expectation match it |

`artifacts-s21d5` joins the predecessor list for the reason `artifacts-s21d4` joined D5's: D5 is
released and its evidence is now somebody else's baseline. D6 reads its calibration matrices and
writes nothing back. It has no released "after" fingerprint of its own, so the record says
`first observation at the D6 baseline` rather than inventing a match. The expectation for the
other six is read from `sprint-21d5-authority-isolation-after.json` rather than from D5's
baseline: the after record is the one that proves those digests survived a whole sprint.

### S21D6-001 — provisioned authorities, and D5's finding not repeated

`sprint-21d6-provisioning.json`, integrity
`188284fbbb3302aca184450c276612aa114be12aa27ee8a00f8764da2aa8a12f`.

Three databases created under the `cognitive_os_s21d6` prefix, the evidence store migrated to
head `0015`, `alembic check` reporting **no new upgrade operations detected**. The integration and
restore databases are `unmigrated`, which is their correct state. `.env.s21d6.local` is derived
from `.env.s21d5.local` by substituting the sprint slug — 13 substitutions, no other edit.

S21D5-W0-F1 was a migration that reached the development database because the shared loader
re-reads its own file and overrides exported variables. Every D6 invocation passed
`COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d6.local` explicitly, and the head was verified on both the
D6 store (`0015`, newly migrated) and the D5 store (`0015`, untouched) before the record was
written. **No finding.**

### S21D6-010 — the §2.3 admission amendment

`sprint-21d6-contracts-amendment-2.json`, integrity
`c27630950a7bc651a49fae50d63649008539a2f36345049d22bea1ae5fb90f9b`.

> **Struck:** exactly zero confident errors among admitted independent calibration decisions.
>
> **Replaced by:** admission is a split-conformal bar at the pre-registered alpha, and the
> Clopper-Pearson one-sided 95% upper bound on the error rate among admitted independent
> calibration decisions is at most the pre-registered ceiling C.

The gate contract hash is unchanged and still reproduces; one clause is superseded and the record
names what it replaced, exactly as S21D4-011 handled the derivation step. One threshold changed,
condition 14 affected, every other floor — including the 0.40 coverage floor the amendment is
accused of being about — untouched.

**The justification is recomputed, not typed.** The script reads D5's sealed
`sprint-21d5-learner-selection.json` and derives, per cell, the best coverage available at each
admitted-error count:

| Admitted errors | 720-row cell | 320-row cell |
|---|---|---|
| 0 | coverage **0.27** | coverage **0.26** |
| 1 | coverage **0.58** | coverage 0.32 |
| 2 | coverage 0.67 | coverage **0.45** |

`infeasible_on_every_cell: true`. The pre-amendment pair is not unmet, it is unsatisfiable by any
admission rule over this ranker — the constraint is on where the ranker places its errors, not on
how the bar is chosen. And the sentence the record exists to make legible: **zero confident errors
in 27 admitted decisions bounded the true error rate at 0.105 by the same Clopper-Pearson the
amended clause uses; one tolerated error at 720 rows admits 58 and bounds it at 0.079.** The
struck sentence was a property of a small sample, not a safety property.

Chronology at signature: zero bars derived, zero calibration outcomes, no certification corpus,
no D6 measurement record present, zero files in the D6 artifact store.

### S21D6-011 — condition 24 inherited, with a falsifier

`sprint-21d6-condition-24-ruling.json`, integrity
`ea093455846f80bb9050628e653884710776054bbe01635a13d4c9d04dfb70cf`.

§2.2 would have D6 author **60 retrieval groups yielding 50 queries** to re-evidence a surface it
neither fits, changes nor reads. The ruling inherits D5's sealed measurement instead — the
`lexical` arm, 60 queries, both floors reached — and makes the inheritance conditional on three
identities, each bound to a released hash: the searchable surface
(`sprint-21d5-surface.json`), the retrieval arms, and the comparator. Any of the three moving
voids it, and all three are re-checked at gate close rather than trusted from here.

This is the D5 handoff's own caveat used as a test rather than ignored: condition 24 does not stay
closed for free, but a sprint that changes none of the three has not changed the thing that was
measured. **Sixty authored groups saved; W1 is a single authoring wave.**

### S21D6-003 and S21D6-004 — what changes role, and what stays sealed

`sprint-21d6-reuse-audit.json`, integrity
`7b90d535a2acdbb6c699d2ab9dc6a0ebf3f279786abcba8e3689ebfc9be23cd7`.

**The role transition.** D5's 100 calibration groups become D6's **conformal** half: the evidence
that places the bar, and nothing else. It certifies no coverage, no error rate and no candidate,
and it is not re-executed — the margins are read out of the sealed campaign through the sealed
720-row direction. D4's calibration became D5's fitting pool under the same principle one step
earlier. The 180-group fitting pool stays fitting evidence and is read only through the direction
it already produced. The retrieval pool is spent entirely and D6 authors no replacement.

The record also states why the two halves cannot both come from D5: §2.3 requires 100 independent
decisions in the *measured* set, D5 authored exactly 100, and 100 cannot be both halves. W1
authors the certification half fresh; S21D6-022 will prove the disjointness.

**The carried roles.** `final_a` (30), `final_b` (30) and `canary` (5) audited a fourth time and
a fourth time `reuse`: shapes hold, all three pairwise disjoint, both released generators agree,
65 protected task identities resolved by identity alone, **zero protected bodies opened**. D4's
and D5's stores each hold a complete campaign — 1,076 and 1,136 observations — and it is their
zero count *for protected task identities* that carries the claim, not an empty store.

### S21D6-012 through S21D6-017 — revision 6

`sprint-21d6-contracts.json` and `sprint-21d6-pre-registration.json`.

Five contracts, not D5's seven, because revision 6 changes one thing: the map from a ranked group
to an admit/abstain decision. The contract text is imported from the modules that implement it, so
a rule that drifts in code drifts in the record and `--check` catches it.

| Contract | What it freezes |
|---|---|
| `admission_rule` | `split-conformal-margin-v1`, **alpha = 0.20**, rank 11 of 12, one wrong margin above the bar, single derivation, authorised by amendment 2 |
| `candidate_cell` | one selectable cell, the 720-row direction `9fd297fb40701537…`, unrefitted; the 320-row direction reported and **not** selectable |
| `corpus_roles` | conformal half = the 100 spent D5 groups; certification half = 100 authored fresh; no fitted vector in both |
| `selection_rule` | the amended §2.3, nine clauses, **C = 0.15** |
| `decision_tree` | four typed endings, published before any number exists |

**Why alpha is 0.20 and not lower.** With the sealed m = 12 the finite-sample rank
`ceil((1-alpha)*(m+1))` is 12 for every alpha below 2/13 = 0.1538, and a bar at the 12th of 12
wrong margins *is* the largest wrong margin — the zero-error prefix rule D5 stopped on. Any alpha
that could change the outcome is at least 0.1538; 0.20 is the smallest round value above it, and
at 0.05 no quantile exists at all (12 errors cannot support a 95% bar, which needs 19).

**Why C is 0.15.** At the 58 admitted decisions the design expects, the bound reads 0.079 at one
error, 0.105 at two, 0.128 at three and 0.151 at four. C admits up to three against an expectation
of about 2.4 — a ceiling the design expects to clear and can genuinely fail.

**Design inputs are disclosed rather than counted as zero.** The chronology counters are all zero,
and a separate block names what was read from D5's *released* aggregates to size the experiment:
the sweep, the error count, the two model hashes. Alpha was computed from published numbers and
will be certified on evidence nobody has read. The bar's placement is effectively known in
advance; what it buys on unread evidence is not, and that is the only thing D6 certifies.

### S21D6-002, the other end — zero predecessor writes

`sprint-21d6-authority-isolation-after.json`, integrity
`05ce1b7de992a8f7aabb5cc03b750a7c397088c35cd910b3010a2d47d2a2467f`. Seven roots re-fingerprinted
after the wave against the baseline: **zero drifted, zero writes**.

## W0 evidence index

| Record | SHA-256 (16) | Items |
|---|---|---|
| `sprint-21d6-baseline.json` | `ac71f63aa0377906` | S21D6-000, S21D6-002 |
| `sprint-21d6-provisioning.json` | `159d49cc645ae08c` | S21D6-001 |
| `sprint-21d6-contracts-amendment-2.json` | `9ba7fc1f516c238d` | S21D6-010 |
| `sprint-21d6-condition-24-ruling.json` | `1e2d7c4a18001550` | S21D6-011 |
| `sprint-21d6-reuse-audit.json` | `518dedfdaee8c1e2` | S21D6-003, S21D6-004 |
| `sprint-21d6-contracts.json` | `6d1b1e6614ac52a2` | S21D6-012 … S21D6-016 |
| `sprint-21d6-pre-registration.json` | `e1e4e1d76e51bb53` | S21D6-017 |
| `sprint-21d6-authority-isolation-after.json` | `d8b82663895c2550` | S21D6-002 |

## W0 findings

None.

## W0 validation

- `ruff check` and `ruff format --check` with `--config ruff.cognitive-os.toml` over
  `src tests scripts`;
- `scripts/pre_registration_d6.py --check` — 5 contracts, 5 children, 1 amendment, 0 measured
  values;
- `tests/cognitive_os/learning/test_d6_w0_evidence.py` — 20 assertions over the seven sealed
  records, including the alpha arithmetic and the ceiling table recomputed from
  `conformal_operating_point` rather than read back out of the records that state them;
- the full test suite: **4,027 passed, 0 failed, 217 skipped**.

`contracts_d6.py` and the W0 test were formatted *after* the records were produced, so the
formatted modules were re-imported and their contract text recompared against the sealed files:
**9 values compared, 0 drifted.** A formatter that re-wrapped a contract string would have moved
a frozen hash, and checking is cheaper than assuming it cannot.

## What W0 did not do

- It closed no Gate L2 condition. Gate L2 does not pass and Sprint 22A remains blocked.
- It authored no corpus, executed no campaign, derived no bar and fitted no direction.
- It read no certification decision, no conformal margin, no retrieval query and no final or
  canary body.
- It changed no released code, no encoder, no normaliser, no hypothesis class and no direction —
  and no gate threshold other than the single §2.3 clause amendment 2 names.

## What W1 needs, and what would stop it

W1 authors 100 certification groups and 400 outcomes under the D4/D5 corpus contract, whose two
execution-only defect patterns are budgeted for inside the wave. Nothing else blocks it: the
conformal half is sealed, the direction is sealed, the bar is pre-registered and the ceiling is
published.

The one thing that would stop D6 now is a withdrawal of amendment 2. While no D6 measurement
exists — the state the chronology proves — that withdrawal costs one record and the sprint ends at
§3.4 branch 0, `admission_contract_refused`. After W1's corpus is sealed it costs the corpus too.

---

# W1 — the chain, proven end to end on 15 groups

W1 authors 100 certification groups. Before it authors 85 more, every stage below the corpus was
driven on the 15 that exist, under `--provisional`, so that a defect in the spine is found on a
corpus that can still be edited rather than on one that has been sealed. Every record this
produced says `provisional: true` in its own bytes and carries no outcome that a gate row reads.

## The chain

| Stage | Producer | Result |
|---|---|---|
| authoring, both suites, encodability | `corpus_d6.py` | 15 groups, 75 bodies, 150 suite runs, 0 defects |
| eight-role separation | `separation_d6.py` | 28 pairs, all disjoint; 0 collisions touching D6 |
| manifest seal | `sealed_manifests_d6.py --provisional` | 0 stops; every proof against D5's released bytes |
| feature seal | `reality_campaign_d6.py --stage seal` | 60 records, 60 distinct vectors, 0 containers |
| execution | `reality_campaign_d6.py --stage execute` | 60 runs, 30 hidden-passing, 0 baselines through |
| vertical slice | `vertical_slice_d6.py` | 5 containers, 12 refusals, artifact bound and restored |
| snapshot | `reality_campaign_d6.py --stage snapshot` | **11 of 11 scans passed** |

## S21D6-022: eight roles, and the one D6 authors

D5 separated seven roles and authored two of them. D6 separates eight and authors one. The eighth
is arithmetic rather than growth: D5's retrieval pool joins D4's, both spent, neither replaced —
which is what the condition-24 ruling bought. The pool-against-itself check S21D4-043 introduced
is recorded as `applicable: false` with its reason rather than dropped, because a missing check
and an inapplicable one read identically in a diff.

D5's additional clause was that its authored corpus stay clear of the groups that had already
decided a D4 threshold. D6's is one step sharper, and it is why the sprint authors a corpus at
all: **the half that places the bar may not be the half measured against it.** Both that and
disjointness from the fitting pool are recomputed here rather than inherited from the seal.

## S21D6-023: what the seal proves, and against what

Every claim is checked against `sprint-21d5-sealed-manifests.json` — the released bytes — rather
than re-derived from the same specs, because a re-derivation produces the same number whether or
not the released catalogue moved underneath it.

- three protected roles identical to D5's, carried for the fourth sprint running;
- the 180-group fitting pool by membership *and* by body, with `re_executed: false` — the claim
  that separates D6 from every predecessor, which re-executed its inherited pool;
- the 100-group conformal half by membership and by body, because a drifted body is a drifted
  margin and therefore a different threshold under the same pre-registered alpha;
- `retrieval_groups_authored: 0`, the inherited pool named by hash, the ruling bound by hash.

## S21D6-024: the same fixture, the opposite answer

The slice runs D5's fixture group — outside every one of D6's eight roles, which the seal check
proves rather than declares — under D6's own identities in D6's own store. Steps 1 through 5 and
7 through 9 are D5's slice with D6's identities, deliberately: a spine proof that changed the
parts it is not testing would not be a proof of the parts it is.

Step 6 is the sprint. On four candidates the fixture yields four leave-one-out ordering decisions,
split into two halves of two by alternating position — a rule fixed before the margins were read.
Both folds were correct, so the conformal half holds **zero wrong margins**, and:

> at alpha = 0.20 the finite-sample rank `ceil(0.8 × (0+1))` is **1**, which exceeds the zero
> margins available. **No quantile exists. The component admits nothing.**

D5's slice met the same four clean decisions and its zero-error prefix rule took the
`every_answered_decision_was_correct` branch, **admitted everything, and ran at a floor of zero.**
That difference, on identical fixture data, is the sprint's change executed rather than argued.
No alpha rescues it either — with no wrong decision there is no wrong-margin distribution to take
a quantile from — so the artifact is bound at a floor above every margin the fixture produced and
the ranker abstains, which is what a component without a bar must do.

Twelve refusals executed, including the one that matters most: a second derivation at another
alpha, with the first in hand, is refused by name. The bar also reproduces across the restart.

## S21D6-030: which two matrices, and why

D6 executes one partition, so the snapshot cannot scan a fitting matrix against a calibration one
out of a single store. The pair is the one the experiment rests on: **D5's conformal half against
D6's certification half.** A shared group or a near-duplicate across *that* boundary is what would
break the exchangeability §6 names as the risk the evidence cannot retire, and it is the only
boundary where a leak would flatter the result.

The conformal rows are rebuilt from D5's released bytes, read-only — vectors from its sealed
calibration record, labels from its released campaign record — and the reconstruction proves
itself: `canonical_line` serialises the scaled values, the embedding and the label and nothing
else, so an equal matrix hash means every vector and every label came back intact. It equals D5's
published `106061126df8…` exactly.

One thing cannot be rebuilt. D5's per-row outcome times live in D5's database, which D6 does not
open; they reach no scan but the chronology one, so both timestamps are set to D5's seal time and
that half's chronology is recorded as **inherited** from D5's released campaign record rather than
recomputed. A scan that passes on substituted data is not a scan, and the record says so.

Result: 11 of 11 scans passed. The halves share no group (100 against 15), and the highest
cross-split similarity is **0.989369** against a 0.999 floor. The store holds 64 observations, 60
named by the dataset and 4 belonging to the slice's fixture group, all accounted for.

## W1 findings

Four defects, all found by execution and all fixed inside the wave.

1. **The store guard named the wrong sprint.** Copied from D5, its forbidden list ran to `s21d4`
   and stopped. D6 reads its numeric envelope and its fitted direction out of D5's released seal,
   so a mistyped environment variable could have opened for writing the store the conformal bar
   is computed from. There were three identical copies; there is now one `_isolated_pair()`, and
   the refusal is executed rather than assumed.
2. **The seal claimed a revocation it did not have.** `corpus_authoring_capability_revoked` was
   unconditionally true while 85 groups remained to be written. It is now `not provisional` — the
   validator had already been written for that branch, which is why the field permits it.
3. **The seal record indexed a partition D6 never opens.** The `counts` block still described
   D5's two-partition run and raised `KeyError: TRAINING`.
4. **The template registry did not carry the D6 corpus,** so the runner could not resolve the
   first task. Found in the previous session and recorded here for completeness.

Two further things the run corrected without a defect being present: the conformal matrix must
carry D5's own split label, because `canonical_bytes` prefixes the rows with it and a relabelled
matrix could not be checked against D5's published hash; and `detect-secrets scan --baseline`
rewrites its baseline in place restricted to the paths given, which empties every other entry —
the six new evidence files were merged in surgically, with 0 existing entries lost or altered.

## W1 validation

- `ruff check` and `ruff format --check` with `--config ruff.cognitive-os.toml`;
- `tests/cognitive_os/learning` and `tests/cognitive_os/coding`: **1,897 passed**;
- `sealed_manifests_d6.py --check --provisional`: 0 stops; the same command without
  `--provisional` refuses at 15 groups against a frozen target of 100.

## What W1 has not done

The corpus is **15 of 100**. Every record above is provisional, no coverage or error rate has
been measured, no bar has been derived from the sealed conformal half, and Gate L2 stands where
D5 left it. What W1 has established is that nothing between the corpus and the snapshot will
surprise the wave — which was the point of driving it before authoring the remaining 85 groups.
