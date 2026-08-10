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

---

# W1 closed — the corpus, and the measured run

## S21D6-020: the certification corpus, 100 groups

Nine batches, 89 groups authored, 85 kept. Families land exactly on the target:
boundary 17, transform 17, error 17, numeric 17, parsing 16, state 16. The corpus executes
clean: **500 bodies, 1,000 suite runs, no contract defect, no collision, every body encodable**,
2,230 bodies compared for separation.

| batch | authored | kept | withdrawn |
|---|---:|---:|---|
| 1 | 10 | 10 | — |
| 2 | 10 | 8 | manifest_diff, cohort_split |
| 3 | 10 | 9 | checked_merge |
| 4 | 10 | 10 | — |
| 5 | 10 | 10 | — |
| 6 | 10 | 10 | — |
| 7 | 10 | 9 | rekey_by_position |
| 8 | 10 | 10 | — |
| 9 | 9 | 9 | — |

**Every withdrawal was failure mode 3, and every one had the same tell.** `manifest_diff` was a
task-level clone of `d5-transform-key-difference`, `checked_merge` of `d5-state-config-patch`,
`cohort_split` of fixed-size chunking, `rekey_by_position` of `d2-transform-zip-records`. In each
case the *body carrying the defect* reduced to a textbook one-liner. `cohort_split` is the one
that taught it: only its defective variant collided, which looked like a code-level coincidence a
rewrite could clear — and rewriting the comprehension as a loop moved the collision to two other
released groups instead. A task whose core step is a saturated primitive collides however it is
written.

**What the pre-check can and cannot do.** `--search` screens the words a contract uses. It killed
a cause-chain walker in batch five before a line of it existed, because D2's `cause_chain` already
publishes "the message of the deepest cause … raises ValueError once the chain passes ten links" —
the same task down to the depth guard. It cannot see saturation, which is why batches two, three
and seven each paid for one group. After the heuristic was written down, retention ran 57 of 60.

**Three authoring findings that only execution produces.**

*A visible case has to be one both readings agree on.* `digit_positions` is about which end of a
number you count from, so almost every input separates the candidates. Its visible case asserted
`digit_positions(1234, 4) == [0]` — the answer from the units — which the baseline, counting from
the other end, fails. The baseline broke its own visible suite. Now `digit_positions(7, 7) == [0]`.

*An accidental repair looks like the careful way to write it.* `outer_fence` turns on
`values[-count:]` returning the whole series when count is zero. Writing the overlap fix I reached
for `values[len(values) - count:]`, which repairs the overlap **and silently repairs the zero case
too**, so variant three passed the hidden suite and the validator called it: two hidden tests
probing one defect.

*Escape only where the escape must survive into the generated module.* Every body lives in a plain
triple-quoted string, so Python resolves its escapes at import. A group built on backslash escapes
has to double each one twice over; the first `escape_pairs` did not, and its module came out an
unterminated string literal. It now escapes with a tilde and carries no backslash at all. The same
layering then put a literal backslash-n on the end of `indent_level`'s import line and failed all
five of its bodies against their own visible suite.

## S21D6-022 and 023, re-taken on the complete corpus

Both records are now non-provisional. The seal that had refused every call since it was written
takes: 100 certification groups, 40 invariance cases, 120 promotion cases over 60 independent
ones, 1,380 candidate slots, corpus authoring revoked. Seal `13ee63c718fa50aa`.

Running the complete corpus through checks that had only seen an unfinished one produced two
repairs of its own.

*The validator was under-checking, and looked as though it meant to.* Its body set listed the
three retrieval pools and read them with D2's five label names, which a retrieval spec does not
carry, so every retrieval body was skipped in silence. S21D4-043 does scope retrieval separation
out — the behaviour was the intended one — but a list that cannot read what it contains makes an
intended scope look like an oversight. The specs are gone and the comment carries the reason;
`bodies_compared` is unchanged at 2,230, which is the proof that nothing was being read.

*One near-clone pair touched the role D6 authored.* `separation_d6.py` reads retrieval bodies
properly and found `cadence_beats:variant_three` — the one-line `total // cadence` — matching a
spent D4 retrieval body. Not an operative collision, and not against the conformal half or the
fitting pool, so not the leak that would flatter anything; but the first such pair D6 itself
created, where the record's explanation only covers inherited ones. Rewritten with `divmod`.
Cross-role pairs are back to **20, every one predating D6**.

## The measured run needed a store of its own

The seal stage refuses to run where the campaign stream already carries events. After the
provisional trial it does, and the guard is right: in that store the seal does not precede the
first container. `cognitive_os_s21d6_measured` and `artifacts-s21d6-measured` were provisioned at
head 0015 — 114 tables, identical to the trial pair — and the vertical slice re-run there first,
as §5.1 asks. The trial store keeps the trial's record. **Nothing was pruned to make a count come
out.**

The slice had `provisional=True` hard-coded in its role-boundary check, which made it unrunnable
the moment the corpus was complete. It now takes whichever seal the corpus can carry and records
which one, and how many groups that seal held.

## The measured chain

| stage | result |
|---|---|
| vertical slice | 5 containers, 12 refusals, artifact bound and restored, bar reproduced across a restart |
| feature seal | **400 records, 400 distinct vectors, 0 containers started** |
| execute | **400 runs, 200 hidden-passing, 0 baselines through hidden, 0 containers on the replay** |
| snapshot | **11 of 11 scans passed** |

200 of 400 passing the hidden suite is the authoring contract at scale: exactly the two full
repairs per group, and not one of the hundred baselines got through.

The snapshot scans D5's conformal half against D6's certification half — the pairing the gate
owner ruled and the only boundary where a leak would flatter the result. The conformal matrix was
rebuilt read-only from D5's released bytes and comes back as `106061126df8…`, the hash D5
published, so every vector and every label survived the round trip. 800 rows, 100 groups against
100 sharing none, 800 distinct feature signatures with none labelled both ways, and the highest
cross-split similarity **0.993313 against a floor of 0.999**.

The store holds 404 observations: the 400 the dataset names and the slice's four fixture rows,
which are outside every role and accounted for by name.

## W1 findings

Beyond the authoring findings above, four defects in the machinery, all fixed inside the wave.
The one that mattered: **the store guard was copied from D5 and its forbidden list stopped at
`s21d4`**, so D6 could have opened for writing the very store its conformal bar is computed from.
Three copies became one `_isolated_pair()`, and the refusal is executed rather than assumed. Also:
the seal claimed `corpus_authoring_capability_revoked` while 85 groups remained; the seal record's
counts block indexed a partition D6 never opens; the template registry did not carry the D6 corpus.

Two hazards worth carrying forward: `detect-secrets scan --baseline F P` rewrites F in place
restricted to P, emptying every other entry — the baseline was merged surgically each time and
verified at zero entries lost; and everything must be linted with `--config ruff.cognitive-os.toml`.

## W1 validation

- `ruff check` and `ruff format --check` under the project config;
- `scripts/corpus_d6.py`: 100 groups, ready, 0 shortfall;
- `scripts/separation_d6.py`: accepted, 28 pairs disjoint, 0 collisions touching D6;
- `scripts/sealed_manifests_d6.py --check`: 0 stops, non-provisional;
- `tests/cognitive_os/learning` and `tests/cognitive_os/coding`: 1,897 passed.

## What W1 has not done

No coverage, no error rate and no bar. The conformal point is derived once, at S21D6-034, from the
sealed conformal half, and nothing in this wave has read a certification margin. **Gate L2 stands
exactly where D5 left it.**

---

# W2 — the bar, derived once, and what it admitted

The wave the sprint exists for. Five items, five records, and the ending is typed:
**`leak_budget_exceeded`**, §3.4 step 2. No candidate was selected, and the null is immutable.

## S21D6-031: the invariance sample, measured on D6's own bodies

The one §2.3 condition the W1 plan did not carry an item for. It is not inheritable: §2.3 reads
first-action preservation against the decisions the selection is certified on, and those are the
certification half's. D5's sample is a property of D5's bodies.

The corpus already declared it — `INVARIANCE_TRANSFORM_SEED = 21068303`, forty cases over twenty
of the hundred certification groups, sealed at S21D6-023 as
`invariance_independent_decisions: 0`. This item executes that claim:

| measured | result |
|---|---|
| candidate vectors compared | **160**, every one identical to its clean counterpart |
| verifier label changes | **0** |
| first-action changes | **0** |
| semantic mutation control | 4 of 4 changed the canonical representation |
| stops | none |

So the forty transformed decisions repeat twenty clean ones and add none — the number the seal
carried, now executed rather than asserted. The transformed candidates ran under plain pytest in a
scratch directory; `entered_any_dataset` is false.

## S21D6-032: where D5 fitted, D6 resolves

The stage that fitted two directions in D5 loads them in D6. Both come out of D5's
content-addressed artifact store **on disk, read-only** — D6 does not open D5's database, so the
artifact id is carried as provenance and the lookup runs over the file names that *are* content
addresses, each checked to hash to its own name.

| direction | published hash | resolved | bytes |
|---|---|---|---|
| 720 rows, 180 groups, 720 pairs | `9fd297fb40701537…` | rehashes exactly | 27,040 = D5's record |
| 320 rows, 80 groups, 320 pairs | `5b15f4af06a2b08d…` | rehashes exactly | 27,099 = D5's record |

`fitted_here: false`, `fitting_rows_opened: 0`. This is the claim that separates D6 from every
predecessor, and it fails loudly rather than falling back to a fit.

## S21D6-033: the baseline is stronger here than it was in D5

The deterministic ladder on the hundred certification decisions, no direction loaded. Five rungs
declared, three eligible, and the two ineligible ones recorded with their reasons so the
comparison cannot be read as narrowed to a rung the learner happens to beat.

| rung | eligible | first choice |
|---|---|---|
| `lexical_similarity` | yes | **0.62 — the strongest** |
| `fixed_input_order` | yes | 0.42 |
| `deterministic_static_ordering` | yes | 0.16 |
| `frozen_minilm_cosine` | no | the channel it orders by is not in the v2 representation |
| `width_20_bounded_graph` | no | four candidates make a twenty-wide shortlist the whole pool |

**D5's corpus put `fixed_input_order` on top at 0.42; D6's puts `lexical_similarity` on top at
0.62.** The bar the learner has to clear is twenty points higher on this corpus than on the one
the direction was fitted against, and it was measured before any margin was read.

## S21D6-034: the bar, derived once

The conformal half is D5's hundred spent calibration decisions, rebuilt from its released bytes
and never re-executed; the certification half is D6's own four hundred outcomes. The
`calibration_source_hash` binds **both halves by identity**, so a swapped certification half
changes the derivation hash even if its aggregates happened to coincide.

The reconstruction is checked before the bar is read off it:

| direction | wrong answered in the conformal half | D5 published | rank at α = 0.20 | wrong margins left above the bar | threshold |
|---|---|---|---|---|---|
| 720 | **12** | 12 | 11 | 1 | `0.448554` |
| 320 | **9** | 9 | 8 | 1 | `0.599892` |

Both reproduce D5's published counts exactly. That check is not decoration: §3.2 computed the
α floor from the 720 entry, so a different count would mean the α argument had been made about a
different distribution than the one the bar is read off. The stage refuses rather than proceeding.

Derivation hashes `6b03d7e4dc016284…` (720) and `77529624d03e0a8f…` (320).

## S21D6-035: one condition failed, and it is the one the amendment introduced

A separate process. It reloads both directions and both sealed derivations, re-scores, and passes
each point back to `derive_conformal_point` as `previous`; a different bar would raise
`ConformalPointError` rather than be written. **Both reproduced**, across three separate runs of
this stage.

The pre-registered cell, at 720 rows:

| the amended §2.3 | required | measured | |
|---|---|---|---|
| independent clean decisions | ≥ 100 | **100** | met |
| clean coverage | ≥ 0.40 | **0.40** | met, exactly at the floor |
| projected changed final decisions | ≥ 20 | **39.0** | met |
| first choice over admitted vs. baseline | strictly above | **0.85 vs 0.62** | met |
| changed clean decisions | ≥ 1 | **26** | met |
| first-action preservation | 100% | **100%** | met |
| every cell and sweep point reported | — | 2 cells, **200 sweep points** | met |
| maximum inference | ≤ 250 ms | **0.023 ms** | met |
| **CP-95 upper bound among admitted** | **≤ 0.15** | **0.274745** | **failed** |

Forty admitted of a hundred, six of them wrong. Eight conditions hold and the ninth — the one
amendment 2 wrote into the contract — misses by a factor of 1.8.

The reported cell, at 320 rows: coverage 0.16, 16 admitted, 2 wrong, CP-95 0.343825. It fails
coverage as well as the ceiling, and it was never selectable.

### The finding the record would have hidden

§3.4's step 2 is worded as *"the bar held its leak guarantee and the admitted precision still
missed."* The first draft of this stage wrote that sentence out as a constant. **It was never
measured.** Fixed inside the wave: every cell now carries the realised leak — the share of that
half's wrong answered decisions that cleared the bar, which is exactly what α bounds — and the
ending reads it instead of asserting it.

| direction | wrong answered on the certification half | cleared the bar | realised leak | α |
|---|---|---|---|---|
| 720 | 24 | 6 | **0.25** | 0.20 |
| 320 | 30 | 2 | 0.067 | 0.20 |

So on the selectable cell the bar missed **both** its leak budget and the ceiling. The typed
ending is still step 2 — it is the nearest one §3.4 provides and no ending may be invented after
the measurement — but the record says in as many words that step 2's premise did not hold here.

### What the numbers say, read together

Three independent readings point the same way, and §6 named the shape in advance:

- the direction scores **0.76** first choice over all answered here, against **0.88** on D5's own
  calibration set;
- the strongest deterministic baseline is **0.62** here against **0.42** there;
- coverage came out **0.40** against the design's expected **0.58**, and the realised leak
  **0.25** against a 0.20 budget.

That is the exchangeability risk §6 said the evidence could not retire, showing up as a
measurement rather than as an argument. The two halves come from one authoring contract and one
generator, which made exchangeability plausible; it did not make it true.

**And the rule D6 replaced does not rescue it.** The zero-error prefix on this corpus admits
**6 of 100** at 720 rows and 5 at 320 — coverage 0.06, against the 0.27 it reached on D5's own
set. Split conformal at α = 0.20 admitted 40 where the prefix rule admitted 6. The successor
construction worked; the corpus is harder than the one the direction was fitted on.

## W2 evidence

| record | item | integrity |
|---|---|---|
| `sprint-21d6-invariance-regression.json` | S21D6-031 | `58aecf706c3e5f3a…` |
| `sprint-21d6-directions.json` | S21D6-032 | `33923373d110e4c3…` |
| `sprint-21d6-baseline-ladder.json` | S21D6-033 | `9c87b2392445d165…` |
| `sprint-21d6-conformal-point.json` | S21D6-034 | `5b6765455439bd62…` |
| `sprint-21d6-learner-selection.json` | S21D6-035 | `198985816aae2eb3…` |

## W2 findings

**The typed ending asserted a guarantee nobody measured.** §3.4 step 2's wording was carried into
the classifier as a constant, and the realised leak — the one quantity α actually bounds — was
absent from the record. It is now measured on both cells, and on the selectable one it exceeded
the budget, which is the finding the constant would have concealed.

**§2.3's invariance condition had no item.** The W1 plan's condition list ran 5–9 and W2's ran
12/14/17; the first-action condition belongs to neither and would have been evaluated against a
predecessor's sample. S21D6-031 measures it on D6's own bodies.

**The store guard and the conformal rebuild are imported, not copied.** W1's most serious defect
was one forbidden-store list of three that stopped at `s21d4`. This wave adds no fourth copy:
`_isolated_pair` and `_conformal_matrix` are imported from `reality_campaign_d6`, with the reason
in a comment above the import.

## W2 validation

- `ruff check` and `ruff format --check` under `ruff.cognitive-os.toml`;
- `tests/cognitive_os/learning` and `tests/cognitive_os/coding`: **1,897 passed**;
- the conformal reconstruction check fired as a guard and passed on both directions: 12 and 9
  wrong answered decisions, reproducing D5's published counts;
- the single-derivation rule executed across a process restart, three times, both directions;
- the measured store still holds **404 learned observations** — the count W1 closed on. W2 wrote
  nothing to it, and nothing to any predecessor store.

## What W2 has not done

No artifact was bound, no component registered, promoted, shadowed, canaried or activated. No
final, batch-B or canary body, outcome or manifest was opened — the eight items in
`dependent_not_opened` are all still closed. Gate L2 conditions 12 and 17 now have their evidence;
**14 and 16 close against the stop hash rather than a measurement**, exactly as D5's did.

The selection is a null, and it is immutable.

---

# W3 — the negative release

The gate owner ruled after W2: go to the negative release. D6's backlog writes W3 for a *selected*
candidate — artifact, loader, lifecycle, final A and B, canary, activation — and there is no
candidate, so what W3 executes is the release a stop still has to make. D4 and D5 both did the
same thing at the same point.

## S21D6-036: the typed continuation, and the successor sentence read rather than written

The stop is typed once and everything that depended on a candidate is listed, because "nothing
else was opened" is a claim about absence and a list is what makes absence checkable. Eight
pieces of W3 work and **fifteen Gate L2 conditions** are recorded as not opened, bound to one
stop hash: **`981bb130d03a45ba512ee3a758abb48db0d45c4b53a35a99bca79238c76e3fcd`**.

The successor sentence is **read out of `sprint-21d6-contracts.json`**, which W0 sealed with
`measured_values: 0`. Typing an ending means the measurement selects one of four sentences written
before it; a successor composed afterwards would be the measurement arguing for its own follow-up.

The W3 deliverables are named by the words the backlog's wave table uses rather than by item
numbers. D6's backlog never allocated item IDs below the W3 wave row, and putting identifiers in
the evidence that no plan ever carried would be worse than naming the work.

## The finding that changed three records

W2 closed with the sweep reported and never asked of it the one question §2.1 had asked of the
*pre-amendment* pair: **is the pair reachable at all?**

It is not. Across the 100 reported thresholds on the selectable cell and the 100 on the reported
one, coverage ≥ 0.40 and CP-95 ≤ 0.15 are satisfied at **zero points**:

| | 720 (selectable) | 320 (reported) |
|---|---|---|
| sweep points | 100 | 100 |
| points satisfying both | **0** | **0** |
| best CP-95 at or above the 0.40 floor | **0.241298** | 0.263698 |
| best coverage anywhere under the 0.15 ceiling | none | none |
| deepest error-free prefix by margin | 6 | 5 |

No threshold at any coverage reaches the ceiling. A tighter α moves the bar along that same curve.
So **§3.4's step-2 sentence — "a tighter alpha needs more than 12 wrong decisions in the conformal
half, which is a volume question" — has a premise this evidence contradicts**, and a successor
sized against it would author a hundred groups to reproduce this result.

Computing it searches nothing: every point was already published and none is selectable. What is
computed is the *absence* of a satisfying point, which is a property of the curve rather than a
threshold anybody could adopt.

Three records changed, and none of them by replacing the typed ending:

- `sprint-21d6-learner-selection.json` gained a `joint_feasibility` block per cell, and the step-2
  reading now names the infeasibility instead of the volume sentence when the curve rules it out;
- `sprint-21d6-continuation.json` carries the sealed successor sentence **unchanged**, with
  `successor_sentence_qualified_by_the_measurement` beside it stating what the sweep shows;
- the handoff names a different successor experiment, and says why the sealed one is not it.

This is the same discipline W2 applied to step 2's leak wording: the pre-written sentence stays,
and what the measurement found is recorded next to it.

## S21D6-091: the twenty-nine, and the two rows that are D6's own shape

Every condition is a row naming the file and the rule that decided it. The script has no branch
that writes `met` without a document behind it, and the verdict is computed from the counts.

**Condition 8 has no D6 fitting partition to count.** D6 executes one partition and refits nothing,
so the fitting floor is met by D5's sealed 720-row pool over 180 groups, read through S21D6-023's
proof that the pool D6 names is byte-for-byte the released one. The row reports both halves and
says which store each came from; a row that counted only the certification half would report half
a condition as if it were all of it.

**Condition 24 is inherited, and the inheritance is re-checked rather than trusted.** The W0
ruling voids itself if D6 changed the searchable surface, opened a retrieval arm or moved the
comparator, and its own `re_checked_at` clause puts the check at gate close. The row recomputes
all three identities from D6's tree — `sprint-21d5-surface.json` by bytes and by seal,
`sprint-21d5-retrieval-decision.json` by bytes and by seal, and D6's own
`retrieval_groups_authored: 0` — and refuses the inheritance if any moved. None moved. Gate D1
condition 15 reads the row condition 24 just decided rather than reaching its own verdict, so the
two cannot disagree about one measurement.

The condition is recorded `met`, **not `carried`**: a carried condition would be a predecessor's
verdict reused; this is a predecessor's measurement whose voiding identities were recomputed here.

## S21D6-086: the release matrix, and what it does not claim

Thirty-six rows: twenty-three commands, five negatives that must refuse for their declared
reason, and eight decided from committed evidence. **36 of 36 passed, 0 skipped, 0 structural findings.**

Three of D5's thirty-two rows are gone and a fourth never existed, and the record names all four
in `not_carried_from_d5` rather than leaving a reader to count. D5 ran a W7 that provisioned,
backed up, restarted, restored and damaged a store, and recorded three matrix rows from that
evidence; D6's backlog allocates no operations wave, so there is no evidence for those rows to
read and inventing one would be a release check about a wave nobody ran. The fourth is a
`learned.py d6-integrity` report, which does not exist because the backlog is explicit that D6
runs code that already exists.

What stands in their place is D6's own: `pre_registration_d6 --check`, `sealed_manifests_d6
--check`, the hundred-group corpus validator, the three predecessor integrity reports still green
over their own evidence, and one negative row this sprint is the first that needed —

```
campaign_refuses_the_d5_store → refusing to run against s21d5; D6 writes only to its own pair
```

**W1's most serious finding, executed rather than described.** D6 reads its numeric envelope,
both directions and its whole conformal half out of D5's store, and the guard that keeps it from
*writing* there is one function with one list. The row proves `s21d5` is on that list. A second
negative row proves the inconsistent development pair is refused too.

## W3 findings

The matrix found two defects on its first run, both in this wave's own code, and both are the
kind that only execution reveals.

**The structural check named D5's negative rows.** `_structural_findings` asserts that a required
set of refusals is present, and the set was inherited verbatim: it named `d4_store_refused`, a row
D6 does not run, and did not name either of D6's two campaign refusals. The first execution
reported `negative rows missing: ['d4_store_refused']` — the check catching its own derivation.
Fixed to D6's five, and the comment now says why the list is asserted rather than computed from
`ROWS`: **a required set derived from the rows present can never notice a row that is absent.**

**The secrets scan failed on two regenerated records.** `sprint-21d6-learner-selection.json` and
`sprint-21d6-authority-isolation-after.json` are tracked and both were rewritten this wave, so
their high-entropy strings moved and no longer matched the baseline. Merged surgically — the
hazard W1 recorded stands, `detect-secrets scan --baseline F P` rewrites F in place restricted to
P — and the seventeen replaced entries are the two files' own stale lines, with no file dropped:
451 → 455.

Neither was a finding about the release. Both were findings about this wave, which is what a
release matrix is for.

## W3 validation

- `ruff check` and `ruff format --check` under `ruff.cognitive-os.toml`, over `src tests scripts
  infra` — the CI scope, not a subset;
- the release matrix: **36 of 36 rows passed, 0 skipped, 0 structural findings**;
- the gate assessment refuses to run unless the continuation record's closed set and its own map
  agree, and they do: fifteen conditions, one stop hash;
- condition 24's three voiding identities recomputed from D6's tree and unmoved;
- the measured store still holds **404 learned observations**, and seven predecessor stores
  re-fingerprinted after the wave show zero drift and zero writes.

## What W3 has not done

No artifact was bound, no component registered, promoted, shadowed, canaried or activated. No
final, batch-B or canary body, outcome or manifest was opened — the eight items in
`dependent_not_opened` are all still closed, for the fourth sprint running. Nothing was written to
the measured store or to any predecessor store.

**Gate L2 does not pass, and Sprint 22A stays blocked.**

## S21D6-095: the release, and the order it had to happen in

A negative release is a complete release. The chronology is the evidence, and it is enforced by
the order the commands were run rather than described afterwards:

| step | handle |
|---|---|
| PR `#227` CI | run `31381783754`, **30 of 30 success** |
| squash-merge into protected `main` | **`cfd22ab6d3e32367ed5c920a3f3844e590acf8b6`**, 2026-08-10T11:19:04Z, `enforce_admins` on, 27 required contexts, no administrator bypass |
| exact-head `main` CI | run `31382974994`, **30 of 30 success**, complete 11:34:12Z |
| annotated tag, once and after that CI | `sprint-21d6-evidence-baseline`, object `29debe41f8dbe16137c0ae528f0ad4390de8d451`, peeling to the merge commit |

`scripts/release_d6.py` reads every one of those handles back from the remote and **creates
nothing** — a record that could produce the state it describes would be a record of itself. It
refuses a tag whose peel disagrees with the merge commit, refuses a run that did not succeed on
every job, and checks `sprint-21-learning-baseline` for **absence** rather than assuming it.
**Zero findings.**

One thing changed against D5's script, and it is a defect its shape invites: D5 carried its PR
number as a module constant, which is correct once the release has happened and wrong every
moment before it. `--pull-request` is required here, so a run against the wrong release fails at
the remote instead of describing one release with another's handles.

## Gate close

With condition 29 decided from the remote handles, the assessment regenerates to its final shape:

| state | conditions |
|---|---:|
| `met` | **14** |
| `not_opened` | **15** |
| `failed` | 0 |
| `carried` | 0 |
| `pending` | 0 |
| `met_as_rejection` | 0 |

**The same fourteen-fifteen split D5 released on**, reached by a different route. D5's fifteen
closed behind `selective_margin_bound`; D6's close behind `leak_budget_exceeded`. A different stop
with the same dependents closes the same set — and the set is not the assessment's to choose: the
script reads it out of the continuation record and refuses to run if the two disagree.

**Gate L2 does not pass. Sprint 22A remains blocked.** The success tag
`sprint-21-learning-baseline` was not created, and its absence is verified rather than assumed.
