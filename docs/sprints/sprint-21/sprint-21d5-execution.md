# Sprint 21D5 execution log

- Branch: `feature/sprint-21d5-pairwise-selective-ranking`
- Backlog: [Sprint 21D5 Technical Backlog](sprint-21d5-technical-backlog.md)
- **Status: W0 through W3 complete — S21D5-020 through S21D5-047 and S21D5-050 closed. Both
  branches have answered, and they answered differently. Correction: the fitted direction ranks
  at 0.91 and 0.88 first-choice against a 0.42 baseline and certifies 0.26 and 0.27 zero-error
  coverage against a 0.40 floor, flat across a 2.25× volume span — §3.3 step 5,
  `selective_margin_bound`, no candidate, 26 dependent items and 15 conditions not opened.
  Retrieval: the `lexical` arm reaches Recall@5 0.7500 and MRR@10 0.5389 on sixty unseen-task
  queries read once, so **Gate L2 condition 24 is met and Gate D1 condition 15 closes**.**
  W4 through W8 not started; W4 to W6 stay closed behind the correction stop.
- Pre-registration: revision 5, SHA-256
  `ed983599bfcdb75993856419de531777d9f4f6cdcce127ead03dcdcddee34b1a`
- Migration head: `0015`, unchanged. `0016` remains unallocated.
- Gate L2 does not pass and Sprint 22A remains blocked. W0 measures nothing and closes no
  condition; it establishes the authority every later wave is bound to.

---

## W0 outcome — authority, reuse, and a contract frozen before any corpus exists

Seven items, three new scripts, one finding, zero measurements. The wave's whole job is to make
the D5 experiment un-tunable after the fact, and it does that by publishing revision 5 with
`measured_values: 0` and sealing the hash of every authority record it rests on.

**Three scripts, not six.** D4 ran W0 out of `baseline_d4.py`, `authority_isolation_d4.py`,
`predecessor_inventory_d4.py`, `holdout_reuse_audit_d4.py` and `pre_registration_d4.py`. D5 does
the same work from `baseline_d5.py` (three phases: `before`, `provisioned`, `after`),
`reuse_audit_d5.py` and `pre_registration_d5.py`. The merges are justified by the reads, not by
brevity: the starting point and the predecessor freeze are one set of directory reads, and the
role transition and the carried-role audit are one question about two halves of the same corpus.
Reading the same six roots twice and hoping the two records agree is the failure mode the merge
removes.

Nothing released was refactored. The `*_d2`, `*_d3` and `*_d4` script families produced released
evidence and stay exactly as they are.

### S21D5-000 — the starting point, read rather than restated

`sprint-21d5-baseline.json`, integrity
`37c2a646cf15e3ae7cdc5db1a0e267b359ff334182735fa9fa6328ec82c8ab07`.

| Fact | Result |
|---|---|
| `sprint-21d4-evidence-baseline` resolves remotely as an annotated tag | yes, object `0f1e4c897c72cedc…` peeling to `18564a55e65f7b33…` |
| local and remote tag handles agree | yes |
| branch descends from current `origin/main` | yes |
| `sprint-21-learning-baseline` | **absent**, checked rather than assumed |
| D4 exact-head CI runs `31244781354` and `31245482819` | re-read from the API, 30 of 30 successful each |
| branch protection | administrators enforced, 27 required checks, strict, no force pushes, no deletions |
| migration head | `0015` |
| six predecessor artifact roots | fingerprinted; the five with a released expectation match it |

`artifacts-s21d4` joins the predecessor list because D4 is released and its evidence is now
somebody else's baseline. It has no released "after" fingerprint of its own, so the record says
so in the field rather than inventing a match: `expected_from: first observation at the D5
baseline; no released expectation exists`.

### S21D5-001 — isolated authorities, and the finding that came with them

`sprint-21d5-provisioning.json`, integrity
`56a7771c2abca9d6bc6f6af29ed4bee1b883627a0623815c47804b72623a803f`.

Three databases created under the `cognitive_os_s21d5` prefix, the evidence store migrated to
head `0015` with 114 `cognitive_os` tables and `alembic check` reporting **no new upgrade
operations detected**. The integration and restore databases are recorded as `unmigrated`,
which is their correct state: the integration fixture and a restore populate them, not W0. The
artifact and backup roots exist and are empty.

`.env.s21d5.local` is derived from `.env.s21d4.local` by substituting the sprint slug. The
PostgreSQL roles are shared (`cogos_owner`, `cogos_app`), so the substitution touches only
database names, the two roots and the evidence prefix.

### Finding S21D5-W0-F1 — the migration went to the development database first

`sprint-21d5-finding-w0-f1.json`, integrity
`7f22968bb52ccc152692ead6a1e7dc042e4d68661fc7d211ac6f55b38b2c4480`.

The first invocation of `postgres_migrate.sh` exported the D5 environment into the shell
(`set -a; . ./.env.s21d5.local; set +a`) instead of passing `COGOS_POSTGRES_ENV_FILE`.
`postgres_common.sh` re-reads `.env.postgres.local` under `set -a` and overrides exported
values, so the command upgraded `cognitive_os_dev` from `0013` to `0015`.

**This is operator error against documented behaviour, not a code defect.**
`docs/operations/learned-evidence.md` states the override in three lines and calls it
deliberate — "it is what stops a mis-scoped command reaching a real database" — and every
released operations document uses `COGOS_POSTGRES_ENV_FILE=$PWD/.env.<sprint>.local`. The
loader did what it says it does. The invocation did not read the document.

Damage: two additive migrations on the development database, both creating tables, neither
dropping or rewriting one; 0 rows written, 0 deleted, both new tables empty; no evidence store,
no predecessor artifact store and no D5 store touched. It is **not rolled back**, deliberately:
`cognitive_os_dev` holds no sprint evidence and was stale at `0013` against a repository head of
`0015`, so a downgrade would be a second unintended write executing `DROP` statements against a
database that is now simply current. The state is recorded rather than reversed.

**One earlier reading is superseded and the correction matters.** The first migration check
reported a `TEXT` versus `Numeric(5,4)` drift on
`cognitive_os.experience_step_assessments.confidence`, and because the mis-scoped invocation was
repeated against the D4 environment it appeared to reproduce there too. It does not.
Both `cognitive_os_s21d4_test` and `cognitive_os_s21d5_test` report `numeric(5,4)`, which is
what `experience/postgres/tables.py` declares. The drift belongs to `cognitive_os_dev` alone —
the inconsistent development pair every sprint since C1 has left alone — and **neither the D4
release nor the D5 provisioning carries it.**

What a reader should take from the finding, stated once and left for the release owner: the
loader's purpose is to stop a mis-scoped command reaching a real database, and here it
redirected one into a different real database instead, silently. That is an observation about
the fallback target. No released behaviour was changed on the strength of it.

### The truncation fence, proved rather than asserted

The provisioning record claims the fence is in force. It is, and W0 has direct evidence
because it tripped.

An attempt to run `tests/integration/postgres` with the D5 environment exported and
`COGOS_TRUNCATABLE_DATABASE=cognitive_os_s21d5_integration_test` **refused at fixture setup**:
the fixture resolves its admin URL from `COGOS_DATABASE_ADMIN_URL`, which names the *evidence*
store `cognitive_os_s21d5_test`, and a nomination naming a different database is the loud
outcome by design. The next thing that fixture does is `TRUNCATE` the whole `cognitive_os`
schema. W7-F1 cost 1,076 observations to learn that lesson; here the rule stopped the same
shape of mistake before a single row moved.

The integration lane needs its own environment file, the way D3 has
`.env.s21d3.integration.local`, and building it is **W7's** work (S21D5-085 and S21D5-086), not
W0's. The lane skips without one, which is its designed opt-in behaviour and is why the local
suite reports 217 skipped rather than 206.

### S21D5-003 and S21D5-004 — what changes role, and what stays sealed

`sprint-21d5-reuse-audit.json`, integrity
`a880c5c586184b8501dc0c39dcd56a2f8f0c365731869ed1734f7babc6ecf046`.

**The role transition.** D4's 80 fitting and 100 calibration groups become D5's **180-group,
720-outcome fitting pool**, which is the one sentence the D5 handoff permits and permits for
nothing else. The calibration set has now been read by two selection rules — S21D4-039's grid
and the pairwise diagnostic — so it is spent for selection permanently. Its 100 group names are
enumerated and digested here, before W1 authors anything, so the authored corpus is bound to be
disjoint from a list that predates it. S21D5-022 proves the disjointness once the corpus exists.

D4's 60-group retrieval pool and its 60 queries are recorded as **spent entirely**: unlike the
calibration set there is no fitting role a read-once holdout can fall back into.

The pool also fixes something D4 wrote about itself. S21D4-039 recorded its 200-to-320 volume
span as a limitation on its own volume arm. D5's 320-to-720 span is 2.25×, and it costs no
authoring because the pool is evidence that already exists.

**The carried roles.** final A (30 groups / 120 slots), final B (30 / 120) and canary (5 / 20)
audit `reuse` for the third time: shapes hold, all three pairwise group-disjoint, 65 protected
task identities intact, `protected_bodies_resolved: 0`, and zero observations, evidence records
or accesses naming a protected task across the D2, D3 **and D4** stores. D4's store is the one
that matters here — it holds a completed campaign of 1,076 observations, and none of them names
a protected identity.

One check is new. D4's audit read the carried roles out of the D2 bundle; D5 reads them out of
the D4 bundle. Both are released generators, and if they disagreed then "carried unopened" would
be a claim about two different corpora wearing one name. They agree: identical group digests for
all three roles.

### S21D5-010 through S21D5-016 — revision 5

`sprint-21d5-contracts.json`, SHA-256 `bee8bafca8c3a330…`;
`sprint-21d5-pre-registration.json`, SHA-256 `ed983599bfcdb759…`.

Eight sealed contracts, four W0 authority records bound by hash, `measured_values: 0`, and
`--check` passing: 8 contracts reproduce their frozen hashes, 4 children unchanged since
publication.

| Contract | What it freezes |
|---|---|
| `hypothesis_class` | `pairwise-contrastive-linear-v1`, its fit rule, λ = 1, the margin as confidence, and why *this* residual implies it |
| `fitting_composition` | 180 groups / 720 outcomes, volume points 320 and 720, whole groups only |
| `corpus_submanifests` | 100 authored calibration groups, 60 retrieval groups against a floor of 50, the carried roles, the generated samples, the separation and near-clone rules |
| `artifact_v3` | the v3 schema name, its dispatch, its six replacing fields and its six refusals |
| `retrieval` | the completed surface, the comparator budget, six arms, both floors, one holdout read |
| `power_and_yield` | what zero errors certifies, and the Clopper-Pearson bounds |
| `decision_tree` | §3.3's four endings |
| `selection_rule` | §2.3 verbatim from D4, `thresholds_changed: 0` |

**λ = 1 is frozen with its provenance, and the provenance is the point.** It was chosen on
fitting-pool-internal leave-group-out evidence recorded in the diagnostic before this contract
existed and before any D5 corpus existed, and `regularization_may_be_rechosen: false` says so in
the stored bytes. A D5 that misses a floor stops; it does not search for a λ that would not have.

**The power contract states the uncomfortable number rather than burying it.** Zero errors over
40 admitted decisions — exactly the 0.40 coverage floor — bounds the true error rate at
**7.2%**, not at zero. Over 100 admitted it is 2.95%. D4's erratum existed because a bound was
not reported beside a rate; revision 5 makes the bound part of the contract.

**The contract also refuses to treat the diagnostic as a forecast**, in its own field:
`diagnostic_estimate_is_not_a_prediction`. The 0.22 and 0.32 estimates are measurements on
authored data this class has already seen. They justify running the experiment. They do not
predict it.

### S21D5-005 — the implementation pull request

PR [#225](https://github.com/palkouser/cognitive-os/pull/225), already open on this branch, is
the coherent implementation PR §6.3 asks for. It carries the groundwork the class and the
surface needed, the backlog, and now W0. No separate pre-registration-only PR was opened,
because W0 measures nothing and no campaign needs to begin from protected authority yet.

### S21D5-002 — the predecessor freeze, both ends

`sprint-21d5-authority-isolation-after.json`, integrity
`2cab4eed45bb96dcee75f99a489bf7643d873a6784ae98f9ab9706b6e6fbb040`.

All six predecessor roots re-fingerprinted after every W0 write: **`zero_predecessor_writes:
true`**, `drifted_stores: {}`. The `after` phase refuses to run at all if the `before` record is
missing, because "unchanged" needs two observations.

---

## W0 evidence index

| Record | SHA-256 (16) | Items |
|---|---|---|
| `sprint-21d5-baseline.json` | `adf504379c7d8b20` | S21D5-000, S21D5-002 |
| `sprint-21d5-provisioning.json` | `3a17dd16ca6035ca` | S21D5-001 |
| `sprint-21d5-finding-w0-f1.json` | `0a8fb454adc20e59` | S21D5-001 |
| `sprint-21d5-reuse-audit.json` | `d7ef009e7eb18269` | S21D5-003, S21D5-004 |
| `sprint-21d5-contracts.json` | `bee8bafca8c3a330` | S21D5-010 … S21D5-015 |
| `sprint-21d5-pre-registration.json` | `ed983599bfcdb759` | S21D5-016 |
| `sprint-21d5-authority-isolation-after.json` | `a0882de988e359be` | S21D5-002 |
| `sprint-21d5-hypothesis-class-diagnostic.json` | `0559a99b4c52db3f` | groundwork, PR #225 |

## W0 findings

| ID | Subject | What it was |
|---|---|---|
| S21D5-W0-F1 | the first migration invocation | Targeted `cognitive_os_dev` rather than the D5 store, because the shared loader overrides exported variables by design. Operator error against a documented convention; two additive migrations, zero rows, no evidence store touched, not rolled back. It also superseded a TEXT-versus-Numeric reading that turned out to belong to the development database alone. |

## W0 validation

- `ruff check` and `ruff format --check` with `--config ruff.cognitive-os.toml` over
  `src tests scripts infra`;
- `mypy` on `src/cognitive_os`;
- `bandit` on `src/cognitive_os`;
- the contract schema export `--check`;
- `scripts/check_repository_language.sh`;
- `scripts/pre_registration_d5.py --check` — 8 contracts, 4 children, 0 measured values;
- the full test suite: **3,838 passed, 0 failed, 217 skipped**.

The three new scripts were formatted after they produced their records, so the formatted
`pre_registration_d5.py` was re-imported and its eight contract hashes recompared against the
sealed file: 8 compared, 0 drifted. A formatter that re-wrapped a contract string would have
changed a frozen hash, and checking is cheaper than assuming it cannot.

## What W0 did not do

- It closed no Gate L2 condition. Gate L2 does not pass and Sprint 22A remains blocked.
- It authored no corpus, executed no campaign and fitted no direction.
- It read no calibration decision, no retrieval query and no final or canary body.
- It changed no released code, no encoder, no normaliser and no gate threshold.

---

## W1 progress — the authoring loop, proved on six groups

**W1 is not complete.** Eighteen of one hundred calibration groups are authored and validated;
the sixty retrieval groups are not started. What is complete is the loop the remaining authoring
runs in, and one measurement that changes the estimate for it.

### The validator is the tool, not the report

`scripts/corpus_d5.py` executes every body against both suites and computes cross-group
near-clone separation over the whole released corpus. It is run *while* authoring rather than
after it, because all three known failure modes are invisible without execution, and each one
now surfaces as a named row:

| Observation | `reading` |
|---|---|
| `variant_three` or `variant_four` passes hidden | failure mode 1 — the two hidden tests probe one defect wearing two descriptions |
| `baseline` fails visible | failure mode 2 — the baseline is broken past its own visible suite |
| a cross-group pair in `collisions` | failure mode 3 — a near-clone at the level of the task |

`--groups` narrows execution to a batch, which is what makes per-batch authoring affordable.
Separation is always computed over the whole corpus, because a collision is a property of a
pair and a batch cannot see the pair it collides with.

### Batch one

Six groups, one per family, all six contract rows correct on the first validated run:

| Group | Family | The two independent edge cases |
|---|---|---|
| `d5-boundary-column-widths` | boundary_collections | a longer row extends the result; a non-text cell is measured as rendered |
| `d5-numeric-nearest-rank` | numeric_logic | a fraction between ranks takes the upper one; an empty series raises `ValueError` |
| `d5-parsing-csv-quoting` | parsing_validation | a contained quote is doubled; padding forces quoting |
| `d5-transform-key-difference` | data_transformation | the lists are sorted; a value that became `None` is changed, not removed |
| `d5-state-partition-offsets` | state_idempotency | a late report does not move an offset backwards; an unknown partition is added |
| `d5-error-batch-outcome` | error_handling | a batch where nothing succeeded is failed, not partial; an empty batch succeeded |

Measured: 30 bodies executed, 60 suite runs, **0 contract defects**, **0 cross-group collisions**
against 1,260 released and D5 bodies, families balanced 1/1/1/1/1/1.

### The finding that changes the W1 estimate

**Eight of eight first-draft task ideas collided with the released corpus, at the level of the
task rather than the code.** Merging intervals, key-value parsing, tag addition, averaging,
describing an exception, renaming fields, finding the first gap and splitting an amount are all
already released — as `interval_merge`, `pair_syntax`, `tag_addition`, `arithmetic_mean`,
`error_description`, `field_rename`, `gap_finding` and `amount_shares`. All eight were withdrawn
before a body was written.

That is the real cost of W1, and it is not typing. Across C3, D2, D3 and D4 the released corpus
occupies **331 distinct module-level task ideas** in the small-pure-function repair space. Every
further group has to be novel against all of them *and* carry two genuinely independent defects,
and the second constraint rules out most of what is left, because the easiest novel tasks are
the ones with a single concern.

The practical consequence, recorded so the successor does not rediscover it: **check a proposed
task against the released module list before authoring its bodies.** D4 discovered its
collisions after writing them and had to withdraw whole groups; the pre-check turns that rework
into a lookup.

### Batch two, and the pre-check made operative

The finding above said to check a task against the released corpus before authoring its bodies.
`scripts/corpus_d5.py --search` is that check: it reports every released group whose module,
group, template id, `issue` or `expected` mentions the given words, so an idea is answered by a
lookup instead of by five bodies and a withdrawal.

It changed the hit rate immediately. Of eighteen ideas checked, `transpose`, `roman`,
`thousands separator` and `leading zero` came back occupied — `row_transposition`,
`roman_value`, `grouped_numbers`, `clock_rendering` — and were dropped before any body existed.
The other fourteen came back clean, and twelve became batch two.

| Group | Family | The two independent edge cases |
|---|---|---|
| `d5-boundary-round-robin` | boundary_collections | a shorter queue drops out of the rotation; no queues at all yields nothing |
| `d5-boundary-bin-packing` | boundary_collections | a bin may be filled exactly; a weight above the capacity is refused |
| `d5-parsing-ipv4-octets` | parsing_validation | a leading zero is refused; an octet above 255 is refused |
| `d5-parsing-glob-match` | parsing_validation | the pattern must match the whole name; a full stop is literal |
| `d5-numeric-luhn-check` | numeric_logic | grouping separators are ignored; a number with no digits is invalid |
| `d5-numeric-significant-figures` | numeric_logic | zero rounds to zero; a negative keeps its sign |
| `d5-transform-value-histogram` | data_transformation | all-equal readings fall in the first bucket; an empty series counts nothing |
| `d5-transform-topological-order` | data_transformation | a step named only as a prerequisite is included; a cycle raises |
| `d5-state-debounce-window` | state_idempotency | the first action for a key is allowed; exactly one window later is allowed |
| `d5-state-replica-reconcile` | state_idempotency | a remote-only key is adopted; an equal version keeps the local entry |
| `d5-error-circuit-breaker` | error_handling | below the minimum it never trips; exactly on the threshold it trips |
| `d5-error-duplicate-suppression` | error_handling | first-seen order, not sorted; trailing whitespace does not distinguish |

Measured over the whole authored corpus: 18 groups, 90 bodies, **180 suite runs, 0 contract
defects**, **0 cross-group collisions** against 1,320 released and D5 bodies, families balanced
**3/3/3/3/3/3**.

### One group withdrawn at the design table

A sliding-median smoother was designed, and then withdrawn before a body was written, because
its two edge cases **cannot** be independent. The candidate pair was "a window running past the
end repeats the final value" and "an even window takes the lower of the two middle values". For
a window truncated to two elements the lower middle *is* the minimum, and padding with the final
value gives the final value; the two rules therefore agree exactly when the final value is the
smaller one, and where they disagree the baseline is already correct. No partial fix could
repair one and leave the other, which is failure mode 1 by construction rather than by accident.

That is worth recording because it is the cheap version of the same discovery: the validator
catches this defect after five bodies are written, and arithmetic catches it before any are.

### Batch three, and the two collisions the run caught

Twelve more groups, taking the corpus to thirty and the family balance to **5/5/5/5/5/5**. The
pre-check disposed of twelve ideas before any body existed — `run-length`, `semver`, `duration`,
`query string`, `byte size`, `weighted average`, `flatten nested`, `left join`, `invert mapping`,
`fallback chain`, `key=value with continuation`, and `collect all errors` were all occupied.

| Group | Family | The two independent edge cases |
|---|---|---|
| `d5-boundary-word-wrap` | boundary_collections | a run of spaces separates as one; an over-long word takes its own line |
| `d5-boundary-ring-read` | boundary_collections | a span past the end continues from the front; a count above the buffer is refused |
| `d5-numeric-half-even` | numeric_logic | a tie goes to the even digit; a float is read at its literal, not its binary expansion |
| `d5-numeric-prime-factors` | numeric_logic | a prime factor above the square root is collected; a number below two is refused |
| `d5-parsing-line-continuation` | parsing_validation | a continuation open at EOF still yields its line; an indented continuation loses its indent |
| `d5-parsing-accept-quality` | parsing_validation | no explicit q means quality one; q=0 is left out |
| `d5-transform-collate-values` | data_transformation | a label coming back later keeps what it gathered; readings keep arrival order |
| `d5-transform-sequence-diff` | data_transformation | multiplicity, not set membership; reading order, not sorted |
| `d5-state-token-bucket` | state_idempotency | a long idle fills only to capacity; a reading before the stamp gains nothing |
| `d5-state-config-patch` | state_idempotency | a null removes the setting, absent or not; a section is laid over, not replaced |
| `d5-error-rollback-steps` | error_handling | the applied steps are undone backwards; the step that raised is not undone |
| `d5-error-redact-secrets` | error_handling | every occurrence is scrubbed; a contained secret leaves nothing behind |

All twelve satisfied the authoring contract on the **first** run — 60 bodies, 120 suite runs, 0
contract defects. Separation did not, and the two collisions it reported are different in kind:

**`d5-transform-pivot-sum` ≡ `d2-transform-pivot`, at the level of the task.** The released
group's contract reads *"pivot(records, row_key, column_key, value_key) totals every record that
lands in a cell, and treats a record without the measure as contributing zero"* — the same four
parameters and the same two edge cases as the group just authored. That is failure mode 3, and
rewriting a variant cannot repair it. The group was **withdrawn** and `d5-transform-collate-values`
authored in its place.

The pre-check had the answer and the reading of it was wrong. Searching `pivot` alone returns
exactly one hit, `d2-transform-pivot`, with its contract in the row. The query that was actually
run was `pivot aggregate group`; the extra words matched a dozen unrelated groups on `group`, the
hits are ranked by *how many* words matched, and with every hit tied at one the ranking fell back
to module name — pushing `pair_pivoting` out of the window that got read. **A multi-word query
dilutes the ranking; the check is read by contract, not by hit count.** One-word queries were used
for the replacement, and found the ground clear.

**`d5-state-config-patch:baseline` ≡ `d5-state-partition-offsets:variant_four`, at the level of
the body.** Both were `updated = dict(x)`, a loop assigning every item, `return updated` —
identical normalised AST, but the *tasks* are unrelated (stream offsets against a settings
overlay). Nothing had to be withdrawn: the baseline was re-authored as `return {**config, **patch}`,
which carries both declared defects unchanged, is what the naive implementation actually looks
like, and is three tokens rather than thirty.

The distinction matters for the remaining seventy groups. A task collision costs the group; a body
collision costs one body. Only the first is worth a pre-check, which is why the pre-check reads
contracts and the detector reads bodies.

Measured over the whole authored corpus: 30 groups, 150 bodies, **300 suite runs, 0 contract
defects**, **0 cross-group collisions** against 1,380 released and D5 bodies, families balanced
**5/5/5/5/5/5**.

### Batch four, and what a clean run costs

Twelve more groups, taking the corpus to forty-two at **7/7/7/7/7/7**. This is the first batch to
clear both the contract and separation on the **first** run — 60 bodies, 120 suite runs, 0 contract
defects, 0 collisions — and the cost of that shows up entirely before any body was written.

Thirty-two ideas were probed one word at a time. Sixteen came back occupied and were dropped at
once: sliding windows (`d4-boundary-overlapping-windows`), unpivot (`d4-transform-melt-columns`),
URL dot-segments (`d4-parsing-tidy-route`), exception-type to exit code (`d2-errors-exit-codes`),
error wrapping (`d2-errors-wrapping`), fill-forward, fill-gaps, coalesce, rotate, longest run,
stride, pad, cumulative, bearings, interpolation and claim-a-slot. Reading the *contract* of each
hit rather than counting hits is what made the difference from batch three.

| Group | Family | The two independent edge cases |
|---|---|---|
| `d5-boundary-spiral-order` | boundary_collections | a ring one row deep is read once; a grid with no rows returns nothing |
| `d5-boundary-split-on-marker` | boundary_collections | a stream opening on a marker has nothing in front of it; an empty stream yields no sections |
| `d5-numeric-reading-spread` | numeric_logic | a mean that is not whole is not truncated; no readings is refused |
| `d5-numeric-proportional-allocate` | numeric_logic | the parts sum to exactly the total; zero total weight is refused |
| `d5-parsing-markdown-links` | parsing_validation | an image is not a link; a link with an empty target is left out |
| `d5-parsing-postcode-format` | parsing_validation | an internal space is removed too; anything under five characters is refused |
| `d5-transform-secondary-order` | data_transformation | ties settle on the secondary descending; a record lacking it comes last |
| `d5-transform-swap-levels` | data_transformation | an inner key under several outer keys keeps them all; a non-mapping is refused |
| `d5-state-recent-cache` | state_idempotency | a key in use moves rather than repeats; the oldest is dropped at the limit |
| `d5-state-inflight-claim` | state_idempotency | a hold that has run out counts as free; a finished piece is never handed out |
| `d5-error-quarantine-batch` | error_handling | the reason is the error's text; an interruption is raised on, not quarantined |
| `d5-error-cleanup-suppressed` | error_handling | a failing cleanup does not replace the body's failure, nor stop the ones after it |

**A second group withdrawn at the design table.** A union-of-columns transformer was designed and
dropped before a body existed, on the same kind of proof as the sliding-median group in batch two.
Its candidate pair was "the field list is the union across all records" and "a record missing a
field takes the default" — but a later record can only *add* a field by the earlier ones lacking
it, so the first edge case cannot be exercised without the second. Failure mode 1 by construction.
`d5-transform-swap-levels` was authored instead.

Two design-table withdrawals in four batches is the loop working as intended: the arithmetic is
free, the validator costs five bodies, and the near-clone detector costs a whole group.

Measured over the whole authored corpus: 42 groups, 210 bodies, **420 suite runs, 0 contract
defects**, **0 cross-group collisions** against 1,440 released and D5 bodies, families balanced
**7/7/7/7/7/7**.

### Batch five, and the loop at steady state

Twelve more, taking the corpus to fifty-four at **9/9/9/9/9/9**, clean on the first run again —
0 contract defects, 0 collisions. Thirty-nine ideas were probed; the occupied ones this time were
median, MAC addresses, state machines, ratios-as-percentages, prefixes, feature flags, severity
ladders, guarded division and the `top`/`written`/`port` families, all dropped at the probe.

| Group | Family | The two independent edge cases |
|---|---|---|
| `d5-boundary-unzip-pairs` | boundary_collections | an empty list gives two empty columns; a row that is not a pair is refused |
| `d5-boundary-sparse-expand` | boundary_collections | a position outside the run is refused; each slot holds its own copy of the default |
| `d5-numeric-simplify-ratio` | numeric_logic | the sign moves above the line; a denominator of zero is refused |
| `d5-numeric-month-length` | numeric_logic | a century year needs four hundred; a month outside one to twelve is refused |
| `d5-parsing-morse-decode` | parsing_validation | three spaces are a word gap; an unknown symbol is refused |
| `d5-parsing-locale-tag` | parsing_validation | a four-letter script takes title case; an empty subtag is refused |
| `d5-transform-prune-empty` | data_transformation | a branch left with nothing is dropped in its turn; a falsy-but-not-empty value is kept |
| `d5-transform-top-per-group` | data_transformation | groups keep first-seen order; a record with no score is left out |
| `d5-state-idempotent-transfer` | state_idempotency | a repeated instruction changes nothing; an uncovered instruction is refused |
| `d5-state-reentrancy-guard` | state_idempotency | a name already running is refused; the mark comes off even when the body raises |
| `d5-error-partial-flush` | error_handling | the count leaves out the failed batch; no batch is attempted after a failure |
| `d5-error-admit-limit` | error_handling | a request filling the allowance exactly is let through; a negative request is refused |

Two things are worth recording about the isolation of the edge cases, because both were designed
around rather than discovered:

- `d5-transform-top-per-group` returns a mapping, and **mapping equality ignores order**, so the
  first-seen-order edge case cannot be tested with `==` at all. Its hidden test asserts
  `list(result) == ["b", "a"]` instead. An edge case that the natural assertion cannot see is
  indistinguishable from an edge case that does not exist.
- `d5-error-partial-flush`'s two edge cases would entangle if the same scenario tested both. The
  count test uses exactly two batches, so stopping early cannot change the answer; the
  stopping test asserts only the write log, so the count cannot change the answer. Each test is
  blind to the other defect by construction.

Measured over the whole authored corpus: 54 groups, 270 bodies, **540 suite runs, 0 contract
defects**, **0 cross-group collisions** against 1,500 released and D5 bodies, families balanced
**9/9/9/9/9/9**.

### Batch six, and a defect the validator caught that arithmetic could not

Twelve more, taking the corpus to sixty-six at **11/11/11/11/11/11**.

| Group | Family | The two independent edge cases |
|---|---|---|
| `d5-boundary-cartesian-rows` | boundary_collections | no groups gives the single empty combination; the last group turns fastest |
| `d5-boundary-cluster-by-gap` | boundary_collections | a step exactly the gap keeps readings together; no readings gives no groups |
| `d5-numeric-integer-root` | numeric_logic | an exact power returns its whole root; a negative value or degree below one is refused |
| `d5-numeric-geometric-mean` | numeric_logic | a run containing a zero averages to zero; no readings is refused |
| `d5-parsing-name-initials` | parsing_validation | both sides of a hyphen give an initial; a lowercase particle is left out |
| `d5-parsing-entity-unescape` | parsing_validation | a numeric entity decodes; an escaped ampersand is not decoded twice |
| `d5-transform-compose-pipeline` | data_transformation | the steps run in reading order; the list is read once when the pipeline is built |
| `d5-transform-longest-match` | data_transformation | the longest matching prefix wins; no match returns the default |
| `d5-state-journal-replay` | state_idempotency | an entry at or below the cursor is skipped; a gap in the sequence is refused |
| `d5-state-snapshot-restore` | state_idempotency | an unsaved name is refused; the working copy does not reach back into the saved one |
| `d5-error-degrade-mode` | error_handling | the standby is not asked when the primary answers; the primary's failure is the one raised |
| `d5-error-required-fields` | error_handling | a field holding None counts as missing; an unnamed field is ignored |

**The validator caught one, and the reason matters.** `d5-boundary-cartesian-rows`'s
`variant_four` passed the hidden suite when it must fail it. The cause was not entangled edge
cases: `variant_four` is supposed to fix the ordering only, and it was written as
`rows = [(option,) for option in groups[0]] if groups else [()]` — the trailing guard
**accidentally fixed the other edge case too**, so a body meant to be half-repaired was whole.
Removing the guard restored it.

That is worth recording because the validator's own reading was wrong about the cause. The row
`variant_four` / `hidden` / `passes` is labelled *failure mode 1 — the two hidden tests probe one
defect*, and here it was an authoring slip in a single expression instead. **The reading names the
usual cause of a row, not the only one.** Two batches of arithmetic-at-the-design-table cannot
catch this class: the edge cases genuinely were independent, and the fault was in the body that
was supposed to demonstrate it. Only executing all five bodies against both suites finds it.

**Two more groups withdrawn at the design table**, both for entangled edge cases, both proved
rather than run:

- A *failure latch* — "the first failure is kept when a second arrives" and "a success does not
  clear a remembered failure". One rule, *keep the first failure whatever arrives*, satisfies
  both, so no partial fix can separate them.
- A *memoiser* — "a cached value is not recomputed" and "a cached None is still a hit". The
  second edge case presupposes a cache read, which is the first, so nothing can fix the second
  alone.

That makes four design-table withdrawals across six batches, against one defect the validator had
to find. The arithmetic catches entanglement; only execution catches a body that does not do what
its label says.

Measured over the whole authored corpus: 66 groups, 330 bodies, **660 suite runs, 0 contract
defects**, **0 cross-group collisions** against 1,560 released and D5 bodies, families balanced
**11/11/11/11/11/11**.

### Batch seven

Twelve more, taking the corpus to seventy-eight at **13/13/13/13/13/13**. Clean on the first run:
0 contract defects, 0 collisions.

| Group | Family | The two independent edge cases |
|---|---|---|
| `d5-boundary-missing-numbers` | boundary_collections | the run includes its last number; a backwards run is refused |
| `d5-boundary-knight-moves` | boundary_collections | a move off the board is left out; the squares come back ascending |
| `d5-numeric-twos-complement` | numeric_logic | the halfway value is the most negative; a value too wide is refused |
| `d5-numeric-triangle-kind` | numeric_logic | the equal pair is found whichever two it is; sides that cannot close are refused |
| `d5-parsing-subtitle-timestamp` | parsing_validation | a full stop reads like a comma; a field of sixty or more is refused |
| `d5-parsing-mime-type` | parsing_validation | a quoted value loses its quotes; a parameter value keeps its case |
| `d5-transform-fill-template` | data_transformation | an unsupplied hole is left as written; a doubled brace is one literal brace |
| `d5-transform-explode-delimited` | data_transformation | the space after a separator is trimmed; a record without the field passes through |
| `d5-state-leader-lease` | state_idempotency | a lapsed lease may be taken; the holder may renew a live one |
| `d5-state-reference-count` | state_idempotency | the last hold clears the handle away; releasing an unheld handle is refused |
| `d5-error-quorum-outcome` | error_handling | exactly the number needed is enough; one member answering thrice is one member |
| `d5-error-suppress-expected` | error_handling | a derived failure is swallowed too; an answer of None is the answer |

Two of these needed their isolation arranged rather than assumed, and the arrangement is worth
naming because it is the same trick both times: **put the second edge case where the first cannot
reach it.**

- `d5-boundary-knight-moves` has "off-board moves are dropped" and "the squares come back
  ascending". The corner test would exercise both at once, except that a corner knight's two legal
  moves are `(1, 2)` and `(2, 1)` — already ascending in the move table's own order. A body fixing
  only the first passes it; a body fixing only the ordering keeps the negatives and fails. The
  ordering test then uses a central square where nothing is off the board.
- `d5-error-quorum-outcome` has "exactly the number needed is enough" and "a repeated answer
  counts once". The repetition test uses three answers from one member: a body counting answers
  sees three, clears the bar, and returns True where a refusal is required — while a body that
  only relaxes the comparison to `>=` still counts three and still fails. Two duplicate answers
  would not have separated them, because both readings land on the same side of the bar.

Measured over the whole authored corpus: 78 groups, 390 bodies, **780 suite runs, 0 contract
defects**, **0 cross-group collisions** against 1,620 released and D5 bodies, families balanced
**13/13/13/13/13/13**.

### Batch eight

Twelve more, taking the corpus to ninety at **15/15/15/15/15/15**. Clean on the first run:
0 contract defects, 0 collisions.

| Group | Family | The two independent edge cases |
|---|---|---|
| `d5-boundary-diagonal-read` | boundary_collections | a grid taller than wide stops at the shorter side; ragged rows are refused |
| `d5-boundary-increasing-runs` | boundary_collections | a repeated reading starts a new stretch; no readings gives no stretches |
| `d5-numeric-modular-inverse` | numeric_logic | a shared factor means no inverse; the answer is brought inside the modulus |
| `d5-numeric-business-days` | numeric_logic | the left-over days wrap round the week; a negative stretch is refused |
| `d5-parsing-email-parts` | parsing_validation | not exactly one at sign is refused; the local part keeps its case |
| `d5-parsing-wildcard-host` | parsing_validation | a wildcard is exactly one label; the comparison ignores case |
| `d5-transform-fixed-width` | data_transformation | an over-long value is cut to the column; a missing field renders as blanks |
| `d5-transform-page-cursor` | data_transformation | the last page carries on from nowhere; a cursor below zero is refused |
| `d5-state-shelf-slots` | state_idempotency | an item on the shelf keeps its place; a given-up place is filled first |
| `d5-state-upsert-version` | state_idempotency | the write that already landed changes nothing; a skipped version is refused |
| `d5-error-short-circuit` | error_handling | no check runs after the first objection; a raising check is an objection |
| `d5-error-guard-argument-types` | error_handling | a boolean is not a whole number; an unsupplied argument is refused |

Two groups here were re-scoped at the design table rather than withdrawn, which is a cheaper
outcome than either a withdrawal or a validator catch and worth distinguishing from both.

- A *take-from-both-ends* group was designed with "an odd count does not repeat the middle item"
  and "a count above the length is refused". The first edge case turned out to be **unobservable
  under the second**: the duplicated middle always lands last in the built list, so the `count`
  slice removes it in every case the contract allows. The group was rebuilt as
  `d5-boundary-diagonal-read`, whose two edge cases sit on different axes of the same grid.
- A *one-of-these-fields* error group was dropped for colliding with `d5-error-required-fields`
  at the level of the task — same payload-and-field framing, and its first edge case was the same
  "a field holding None counts as missing" clause. `d5-error-guard-argument-types` replaced it,
  and it collides with nothing because the thing being checked is the *kind*, not the presence.

Measured over the whole authored corpus: 90 groups, 450 bodies, **900 suite runs, 0 contract
defects**, **0 cross-group collisions** against 1,680 released and D5 bodies, families balanced
**15/15/15/15/15/15**.

### Batch nine — S21D5-020 closed at a hundred

Ten more, taking the corpus to **one hundred** at 17/17/17/17/16/16. One hundred does not divide
by six, so that is the closest balance the target allows; the two families short a group are
`error_handling` and `state_idempotency`, chosen arbitrarily and recorded here so the choice is
not mistaken for a finding.

| Group | Family | The two independent edge cases |
|---|---|---|
| `d5-boundary-zigzag-rows` | boundary_collections | the deal turns back at the last row; fewer than one row is refused |
| `d5-boundary-first-duplicate` | boundary_collections | the earliest repeat wins over the earliest repeater; no repeat reports nothing |
| `d5-numeric-scientific-mantissa` | numeric_logic | a reading of zero splits to (0.0, 0); a negative keeps its sign |
| `d5-numeric-temperature-convert` | numeric_logic | same-scale conversion changes nothing at all; an unknown scale is refused |
| `d5-parsing-user-agent` | parsing_validation | a token with no slash has no version; leading whitespace is ignored |
| `d5-parsing-algebraic-square` | parsing_validation | a capital file letter reads the same; a square off the board is refused |
| `d5-transform-summarise-columns` | data_transformation | an empty column is left out; a boolean is not a reading |
| `d5-transform-normalise-weights` | data_transformation | weights totalling zero are refused; a weight below zero is refused |
| `d5-state-reload-rollback` | state_idempotency | a failing candidate is not taken on; a check that falls over is an objection |
| `d5-error-summarise-failures` | error_handling | a component failing twice is named once; nothing failed says so in words |

**The validator caught three, and two of them were tests that could not see their own edge case.**
This is the same class as the `top_per_group` problem in batch five, but found by execution rather
than by inspection, and it is the most valuable thing this batch produced.

- `d5-numeric-temperature-convert`'s edge case is "converting to the scale a reading is already in
  changes nothing at all", written against `convert(98.6, "F", "F")`. The Fahrenheit round trip
  `(v - 32) * 5 / 9 * 9 / 5 + 32` turns out to be **exact in binary floating point** for 98.6 —
  and for 100.0, 37.5, 212.0, 68.0, 99.9 and 451.0, every value tried. The Kelvin round trip is
  not: `25.3 - 273.15 + 273.15` is `25.30000000000001`. The test now uses Kelvin.
- `d5-transform-summarise-columns`'s edge case is "a boolean is not a reading", written against
  `[{"a": 1}, {"a": True}]`. Since `True == 1`, the minimum, maximum and mean are the same whether
  the boolean is counted or skipped. Beside a reading of 5 they are not, and the test now uses 5.

In both cases the *edge case was real and the fix was correct*; what failed was the data chosen to
demonstrate it. A test that cannot distinguish the repaired body from the broken one is worth
nothing, and neither arithmetic at the design table nor a reading of the body would have found
either — only running variant three and variant four against the hidden suite does.

The third was a body-level clone: `d5-boundary-zigzag-rows`'s baseline was byte-for-byte
`d2-boundary-even-split:variant_three`, because the naive way to deal items into rows is the
round-robin `place % rows` loop and somebody has already written it. The baseline and its
half-repair were re-authored as per-row comprehensions, carrying the same two defects in a
different shape.

**S21D5-020 is closed.** Measured over the whole corpus: 100 groups, 500 bodies, **1,000 suite
runs, 0 contract defects**, **0 cross-group collisions** against 1,730 released and D5 bodies,
`shortfall: 0`.

### What the nine batches cost, and where the defects were caught

| Caught by | Count | What it cost |
|---|---:|---|
| The `--search` pre-check, before authoring | 40 ideas | nothing |
| Arithmetic at the design table | 4 groups | nothing |
| Re-scoped at the design table | 2 groups | nothing |
| The validator, after five bodies existed | 4 defects | one group re-authored each |
| The near-clone detector | 3 collisions | one group withdrawn, two bodies re-authored |

The four the validator caught divide into two kinds, and the distinction is the one W1 did not
know at the start. Two were **bodies that did not do what their label said** — a half-repair that
accidentally repaired both edge cases. Two were **tests that could not see their own edge case** —
correct bodies, correct edge cases, data that made the two indistinguishable. Nothing short of
executing all five bodies against both suites finds either.

## S21D5-021 — the retrieval pool, and a rule that was not widened to make it pass

Sixty groups in `reality_retrieval_specs_d5.py`, ten per family, validated by
`scripts/retrieval_d5.py`. A retrieval group is one defect and its repair, not four candidates
around two independent edge cases, so it has fewer ways to be wrong — and one the calibration
corpus does not have at all.

| Check | Result |
|---|---|
| pairs executed, failed body fails hidden and repair passes it | **120 bodies, 0 pair defects** |
| both sides project a non-empty searchable surface | **0 sides with no terms** |
| the two sides project *different* documents | **0 identical pairs** |
| a term spelling the relevance label | **0** |
| cross-group collisions inside the pool | **0** over 120 bodies |
| queries that would qualify | **60**, against a floor of 50 |
| family balance | 10 / 10 / 10 / 10 / 10 / 10 |

### The surface check is new, and it earned its place

D4's pool reached 41 of 60 because ten repairs were pure arithmetic over their own parameters:
the normaliser left nothing of them and an empty document cannot be found by any arm.
`structure_fallback` answers that, and this wave is the first time it has been pointed at a live
corpus. **27 of 120 sides needed it** — they carry no identifier at all and would have projected
empty under the released extraction. That is the D4 residual, measured rather than argued.

The fallback alone is not enough, and the second half of the check is what found the real
problem. A pair whose two sides project the *same* document is worse than an empty one: it is
retrievable and uninformative, and it drags MRR down while looking healthy. Nothing in D4
measured this per pair. Here it caught **nine pairs**, and eight of them shared one cause:

> **A guard-only repair carries no new name.** The normaliser reads identifiers — builtins,
> methods, modules, exception classes. Wrapping the same call in `if` adds control flow and no
> identifier, so `out.append(x)` and `if x not in out: out.append(x)` project the identical
> document. Five of the sixty repairs were guard-only, and three more differed only by an
> operator or by the order of two operands.

Each was re-authored to reach for one name of its own — `dict.fromkeys` instead of a membership
guard, `divmod` instead of a second `len`, `str(error)` inside the wrapped message. The defect
and the repair are unchanged in what they *do*; what changed is that an arm can now tell them
apart.

### The separation rule was checked against its released scope, not widened

Folding the retrieval pool into `corpus_d5.py`'s corpus-wide separation reported **34
collisions**. Before repairing any of them, the released rule was read. S21D4-043 scopes
retrieval separation to the retrieval pool against itself and states its reason in its own
words: a cross-group collision "would be two queries whose answers are the same code". A
retrieval body coinciding with a *calibration* body is not that — the two never answer the same
question, sit in different roles and reach different stores.

So the corpus-wide comparison was an obligation this session invented, and it was withdrawn.
`corpus_d5.py` returns to the calibration corpus; `retrieval_d5.py` runs S21D4-043's rule at
S21D4-043's scope. Under the released rule the pool had **15 collisions across 8 pairs**, every
one of them real, and all eight were re-authored.

The 10 remaining coincidences with a correction body are **reported beside the result and not
folded into it**. They break no contract, and they measure something worth knowing: the
small-function space the programme has spent across 466 groups is saturated enough that a
two-line retrieval body lands on an existing correction body once in twelve. Dropping the number
would have been the dishonest way to a clean report; enforcing it would have been the dishonest
way to a strict one.

## S21D5-022 — separation, and a rule read rather than assumed

[`sprint-21d5-corpus-separation.json`](evidence/sprint-21d5-corpus-separation.json), integrity
`a17479daa959dd79…`, produced by `scripts/separation_d5.py`. W0 could not run this and said so:
`sprint-21d5-reuse-audit.json` carries
`disjointness_check_deferred_to: "S21D5-022, after W1 authors the corpus"`. Two of the seven
roles did not exist then. Both do now.

| Separation | Result |
|---|---|
| group-disjoint, 21 pairs over 7 roles | **465 groups, 465 distinct, 0 pairs sharing one** |
| source-disjoint, every body hashed | **1,965 bodies, 1,965 distinct hashes, 0 shared** |
| `cross_group_collisions_touching_21d5` | **`[]`** over 1,730 calibration and 120 retrieval bodies |
| calibration ∩ spent-for-selection | **∅** — the contract's additional clause |
| D5 authoring into a protected role | **none** |
| lineage: every W0 digest recomputed | **6 of 6 unchanged** |
| protected task identities intact | **65**, 0 bodies resolved |

### Finding S21D5-W1-F1 — the literal seven-role clone rule is already false of the carried roles

The sealed contract asks for "seven roles, pairwise group-, clone- and source-disjoint". Group
and source come back clean. Clone does not: the released detectors report **20 cross-role
near-clone pairs** over all seven roles.

Four of the twenty decide how the rule has to be read, because **D5 authored neither side of
them**:

| pair | roles |
|---|---|
| `d2-numeric-rounding:baseline` ↔ `d2-errors-divmod:baseline` | final_b ↔ fitting |
| `d2-parsing-range:baseline` ↔ `d2-parsing-coordinate:baseline` | final_b ↔ fitting |

Both are D2 groups, sealed by D3 and carried unopened through D4 into D5. §3.2 forbids D5 from
authoring into final A, final B or canary at all. So the literal reading — *no near-clone pair
may span two roles* — was **already violated before this sprint began**, and cannot be satisfied
without re-authoring roles the sprint is explicitly barred from touching.

A rule the inherited roles cannot satisfy is not the operative rule. The operative one is stated
in the same sealed object, in its own `near_clone_rule` field: *"normalized_structure_hash and
token_stream_hash run every batch, scoped to cross-group pairs against every released corpus; a
collision withdraws the whole group."* That is a rule about the **authored** corpora, it is what
`corpus_d5.py` and `retrieval_d5.py` have enforced on every batch of this wave, and it reports
**zero** — which is the acceptance criterion the backlog actually names for this item.

The remaining 16 pairs touch a D5-authored role and are reported in full rather than filtered.
They are the same saturation S21D5-021 measured: across 465 groups the small-function space is
spent enough that short bodies coincide. None of them is a group collision, none is a byte
collision, and none is in scope for the rule the contract enforces.

**Nothing was weakened to reach this verdict.** The stricter reading was computed first, its four
decisive pairs were named, and the contract was then read to see which rule it states. The record
carries both numbers so a reader can disagree with the reading without having to re-run anything.

### The lineage check caught its own recipe

The first run reported all three carried digests drifting. They had not. W0 digested the carried
roles by each group's **`content_hash`**, not by its name, and this check recomputed names. The
two are different quantities, and the content-hash one is stronger — it sees a body drift under
an unchanged name, which a name digest cannot. Recomputed the way W0 recorded it, all three
reproduce.

Worth keeping because the check failed in the safe direction: a mismatched recipe reported a
drift that was not there, rather than agreeing by accident with a drift that was.

## S21D5-023 — the seal, and a pool that needed proving twice

`scripts/sealed_manifests_d5.py` → `evidence/sprint-21d5-sealed-manifests.json`, integrity
`5cc9fbb27020bd06…`. The D5 corpus seal is
`4e73f290728aad42f3a665b2f2026971524ffe2e3919df26feb190e4b667a75e`, revision 5, and it is the
point at which the corpus stops being editable and starts being spent.

| role | groups | catalogue hash | how it got here |
|---|---:|---|---|
| fitting | 180 | `e07691bd53df5e84…` | D4's fitting and calibration partitions, re-interleaved |
| calibration | 100 | `f4f9d86f701e70ac…` | authored at S21D5-020 |
| retrieval | 60 | `2785ca8075ed6500…` | authored at S21D5-021 |
| final A | 30 | `69d5eedcaeccdfdc…` | carried unopened, third sprint running |
| final B | 30 | `06a0c2f6641e4bf3…` | carried unopened, third sprint running |
| canary | 5 | `027f2d78500a14b3…` | carried unopened, third sprint running |

1,380 candidate slots. Invariance: 40 transformed decisions, **0 independent**. Promotion: 120
nominal, 60 independent. No outcome present, corpus authoring revoked, and `scripts/corpus_d5.py`
and `scripts/retrieval_d5.py` named as what the revocation closes.

### The fitting pool is the one thing D5 had to prove twice

The three protected roles are proved the way D4 proved its: compared against the bytes
`sprint-21d4-sealed-manifests.json` published, not against a re-derivation. A re-derivation from
the same specs returns the same number whether or not the released catalogue moved underneath it.

The 180-group fitting pool could not be proved that way, because W0 digested it **by group name**.
A name digest fixes *which* 180 groups the pool is and is blind to a body edited under an
unchanged name — and the bodies are the whole point here, since every one of those groups is being
re-executed rather than read from a store. So the seal carries two proofs:

| claim | how | result |
|---|---|---|
| the pool is the 180 groups W0 named | `names_digest` against the reuse audit | reproduces |
| no body drifted under its name | D4's two catalogue hashes against the released D4 bytes | both identical |

The second is available only because D5's fitting pool *is* two released D4 partitions, so the
released D4 evidence is a body-level record of it. It cost one comparison and closes the half of
the claim W0's recipe cannot reach.

### Two refusals the seal has that D4's did not

Both come from the volume arm, which is new in D5:

- **A volume point that does not land on a whole group is refused.** 320 and 720 outcomes are 80
  and 180 groups exactly. Fitting on three of a group's four candidates would put the fourth's
  siblings in the exemplar set and then call the difference a volume effect. The top rung must
  also be the whole pool, or the ladder measures a span nobody declared.
- **A seal whose retrieval pool is D4's is refused.** D4's pool was read once and is spent;
  measuring retrieval against it again measures recall of an answer already seen. The two hashes
  must differ and the two pools must share no group. Both hold.

One more collision was worth checking rather than assuming: D4 and D5 transform the **same** sixty
final groups under the **same** two released cases, so the seed is the only thing separating their
case identities. The 120 D5 promotion case ids and the 120 D4 ones intersect in zero — asserted in
the test suite, not in prose.

### What the seal reuses instead of restating

`build_d4_retrieval_pool` and its D3 twin were the same seventeen lines over a different spec
tuple, and both submanifest builders were the same construction over a different seed. Factored to
`retrieval_pool_of(specs)` and `submanifest_of(...)`; D5 calls them rather than carrying a third
copy. The released D3 and D4 seal hashes are byte-identical before and after — checked explicitly,
because a refactor of a sealed-manifest generator is only safe if the manifest does not move.

### One defect, mine, caught by the script's own stop

The first `--check` reported `sealed_manifests_ineligible_group_inside_the_invariance_sample`.
There was no ineligible group. The invariance sample names **repository groups** and the
eligibility list names **template ids**; subtracting one from the other reports every sampled group
as ineligible. Fixed by translating before subtracting. All 100 D5 calibration groups are eligible
for both transformation cases, and the 20 in the sample are among them.

The check itself stays, because the rule it guards is real: the sample is the first twenty of the
manifest by a frozen rule, not the first twenty *eligible* ones. An ineligible group inside it
would quietly shrink the regression rather than fail it.

## S21D5-025 — the feature seals, and two defects only execution could find

`scripts/reality_campaign_d5.py --stage seal` → `evidence/sprint-21d5-feature-seals.json`,
integrity `1961fc37387e190f…`. **1,120 v2 feature records sealed before any container**: 720
fitting and 400 calibration, every one of them a distinct vector.

| partition | groups | records | feature seal | stream version before the seal |
|---|---:|---:|---|---:|
| fitting | 180 | 720 | `182adf2e1ca18055…` | 0 |
| calibration | 100 | 400 | `211de7dc53b1fd70…` | 0 |

Bounds fitted on the fitting rows and reused for calibration — refitting per partition would
carry calibration statistics into the encoder, which no feature-name check would catch, because
the names would all still be right. Both partitions re-encode identically from source alone and
reserialise to the same hash. Containers started: **0**. Learned observations written: **0**.

The chronology refusal is executed, not described: sealing either partition again with an outcome
in hand raises `v2 feature records must be sealed strictly before every outcome`. Two seeded
refusals, two `ValueError`s.

### The 180 re-executed groups take D5 identities, and that is checked

D5's fitting pool is D4's two partitions **by body**. The contract calls for re-execution under
new run identities, and the catalogue seed reaches candidate identity, so this is a checkable
claim rather than a promise: of 1,120 D5 candidate identities, **zero** coincide with a D4 one,
and no D5 task identity does either. Asserting the seeds differ would only have restated the
input.

### Defect 1 — a hundred and sixty specs no runner could address

The first run died on the first calibration package: `KeyError: 'd5_boundary.bin_packing'`.

S21D5-020 and S21D5-021 authored both spec modules, validated every body by execution, proved
them separated and sealed them — and **never registered them in `_ALL_TEMPLATES`**. The one line
that publishes a corpus to the task registry lives in `reality_tasks.py`, a different file from
the spec module, and nothing between authoring and the first `prepare_task` call asks whether a
`template_id` resolves. Every D5 validator reads the spec tuples directly, so all of them were
green against a corpus no campaign could run.

Registered both, plus `d5_templates()` and `d5_retrieval_templates()`. The root-cause fix is
`tests/cognitive_os/coding/test_reality_task_registry.py`: every authored spec in every released
corpus must resolve to a template, parameterised over all eight corpora rather than written for
D5. The gap is structural and the next sprint would have walked into it too.

### Defect 2 — a body that is valid Python and cannot be encoded

The second run died at calibration 81/100:
`SourceNormalizationError: unsupported syntax: assignment expression`.

`d5_error.short_circuit:variant_two` used a walrus inside a comprehension condition. The body was
correct, passed both suites, took a materially different route from variant one, and was
clone-clean. The v2 source normaliser refuses assignment expressions, so the group could never
have been encoded — and **nothing in the authoring loop asked**. The five-body execution check
runs pytest, which accepts every construct Python accepts; the near-clone detectors read the AST
but do not normalise it. The first thing in the programme that reads a body through the encoder
is the feature seal, two items later.

Re-authored without the walrus, keeping the generator-and-`next` route distinct from variant
one's explicit loop. Then the root-cause fix, and the part worth keeping: rather than fix the one
crash and restart, **every D5 body was run through the normaliser first** — 620 bodies, exactly
one refused. `scripts/corpus_d5.py` now carries that as an `encodability` gate in `ready`, so the
question is asked at authoring time instead of two waves later.

This is failure mode 6 for the D4 authoring ledger: *a body the encoder cannot read*. Like modes
4 and 5 it is invisible to every check that only runs the code.

### What the body change did and did not move

Re-authoring a variant changes the bodies but not the catalogue: `CatalogueGroup` hashes the
template, the task identity and the **hidden verifier**, not the four variant sources. So the D5
corpus seal is still `4e73f290728aad42…` and S21D5-023 needed no re-seal.

The separation record does hash every body, so it was regenerated (`243867bb67cf1379…`, still
`accepted: true`, still zero cross-group collisions), and the sealed-manifests record after it,
because it binds the separation file by hash. Both bindings in the feature-seal record were
verified against the files on disk rather than assumed.

## S21D5-050 — the v3 artifact, pulled forward out of W4

§6.1 puts the vertical slice before the bulk campaigns, S21D5-024 depends on S21D5-050, and
S21D5-050's own dependency (013) closed in W0. So the artifact module is built here, ahead of its
wave, rather than leaving W1 unable to finish in the order its own §6.1 requires.

`scripts/artifact_v3_d5.py` → `evidence/sprint-21d5-artifact-v3.json`, integrity
`06d3771a7014906d…`.

### Why a third schema rather than a relaxed second

`CorrectionArtifactPayloadV2` is k-NN-shaped by construction: `exemplars` with `min_length=1`,
`k`, `embedding_weight` and three proportion floors. A direction has none of them. Making them
optional would let an exemplar-free v2 artifact load — the *check-that-passes-without-touching-
its-question* defect the D4 report catalogued twelve times. So `correction-ranking-artifact-v3`
is a third name, and v1 and v2 stay exactly as strict.

Carried from v2 unchanged: normaliser, grammar, canonical prefix and payload, feature contract
hash, the 390 channels in fitted order, the six numeric bounds, the embedding model and its tree
digest. **D5 changes no encoder, no channel and no fitted representation; it changes the function
fitted on top of them.** Replacing the exemplar set: 390 weights, the ridge, the pair and group
counts, the margin floor, and the hypothesis class. Plus S21D4-050's operating-point fields —
the derived point's identity, the derivation rule and the calibration certificate hash.

| executed | result |
|---|---|
| round trip into exactly one class | `PairwiseContrastiveRanker`, model hash unchanged |
| frozen refusals driven with bytes breaking one rule each | **7 executed, 7 refuse** |
| dispatch: descriptor required where the schema binds one, refused where it does not | both refuse |
| released v2 schema digest still the D3 golden | unmoved |
| direction vs. exemplar set at D5's 720 fitting rows | **153.8× smaller**, measured not asserted |

### Two decisions worth naming

**The derivation rule is checked, not stored.** A model carrying its own account of how its
threshold was derived can say anything, so `build_payload_v3` copies the released constant and
the loader refuses anything else. Its wording names the *k-NN* confidence, and that is correct:
§S21D5-016's only substitution is the quantity scored — the top-two projection margin instead of
neighbourhood acceptance mass — and `derive_zero_error_point` treats a confidence as an opaque
ordered score. The certification spine is inherited, not rewritten. Which quantity was scored is
named by `hypothesis_class`.

**The dispatcher enforces an asymmetry rather than ignoring a field.** v2 and v3 bind a
descriptor hash; v1 has no field for one. So `load_correction_ranker_any` *requires* the
descriptor for v2/v3 and *refuses* it for v1. A caller passing a descriptor believes it is being
checked; silently accepting it against a schema with nowhere to check it is a lineage check that
never happened. Both directions are executed in the record.

Nothing here is fitted on a D5 role: 0 calibration cases, 0 final members, 0 canary members, 0
retrieval judgements. The first fitted artifact is S21D5-052's, after a candidate is selected.

## S21D5-024 — the vertical slice, on a group nobody may count

`scripts/vertical_slice_d5.py` → `evidence/sprint-21d5-vertical-slice.json`, integrity
`ead53a551c3ce924…`. Fixture: `d5_fixture.render_duration`, checked against the sealed
S21D5-023 bundle before anything ran — **0 calibration cases, 0 final members, 0 canary members,
0 retrieval judgements spent.**

The corpus parses durations in four released groups; none renders one. Two independent defects at
different sites: the all-zero fallback (one decision after the parts exist) and the per-unit
filter (one decision per unit while they are built). Validated the way every D5 group was —
ten suite runs, no contract defect; encodable; **no near-clone collision across 1,740 bodies.**

| step | result |
|---|---|
| 1. package | rights-clean, 4 candidate slots, hidden suite ≠ visible suite |
| 2. canonical v2 bytes | 390 channels from the frozen local model |
| 3. seal before the first outcome | **true**, receipt bound at seal time |
| 4. self-play | 5 containers, verifier decided every label, 2 of 4 accepted, baseline failed hidden |
| 5. dataset + matrix | revision-3 identity, rebuilt identically, 0 `real_governed_run`, 390 columns |
| 6. pairwise ranking | 390-weight direction, 4 pairs, ridge 1; margin `0.197353`; did not abstain |
| 7. v3 artifact | 28,459 bytes, reloaded from its own bytes, payload and ranking reproduced |
| 8. refusals + restart + restore | 3 artifact refusals; replay **0 containers**, remainder empty; backup restored and re-ranked |
| 9. capabilities | 5 refusals executed, each naming the exception the released code raised |

### The operating point exists, and that is worth reading carefully

Four leave-one-candidate-out folds, each a real within-group ordering decision with its own
margin. All four answered and all four were right — so the rule names **no threshold** (there is
no wrong answered decision for one to sit above), the point admits everything, and the ranking
runs at a floor of zero. That is the `every_answered_decision_was_correct` branch behaving as
D4's W2-D7 rebuilt it.

It is **not** evidence the class ranks well. Four decisions from a direction fitted on the same
four candidates is a wiring proof, and the Clopper-Pearson bound beside it says so in a number:
after four clean decisions the true error rate is bounded only below **0.53**.

### Five scans report `passed: false`, and the record now says why for each

D4's slice had the identical five, for the identical reason: the slice holds one matrix, so it is
scanned against itself, and every cross-split scan is answering a question the slice cannot ask.
Each row appears twice because both splits are the same matrix; the one group is in both splits;
each row's nearest cross-split neighbour is itself at similarity one; and four rows carrying two
labels are separated perfectly by many columns, as four points usually are.

D4's record explained one of the five in a single note. This one names all five and where the
question is asked for real — S21D5-030, over 720 and 400 disjoint rows, where a red row is a
finding rather than arithmetic.

### Backup and restore, at the level the slice owns

§6.1 lists "backup and restore" among the slice's obligations. The event store's own dump and
reload is a whole-database operation, and running it here would tear down the store this wave is
writing into — so the slice proves the artifact it produced survives a round trip through the
backup root and still rebuilds the same ranker from the restored bytes. Recorded with its scope
named and with the item that owns the wider proof (S21D5-082). D4's slice did neither.

### One module change the slice needed

`build_ranker_for_evaluation` returns a `CorrectionKnn`, and every released caller depends on
getting exactly that, so v3 got its own door: `build_ranker_for_evaluation_v3`, same order —
rehash, then read, then check the four dataset identities — over a shared lineage helper.
S21D5-057 and S21D5-058 need it too.

## S21D5-026 — both campaigns executed and ingested

`scripts/reality_campaign_d5.py --stage execute`, one partition at a time.
`evidence/sprint-21d5-self-play-campaign.json` (`2baa476759c37c16…`) and
`evidence/sprint-21d5-calibration-campaign.json` (`b8d56397395c84d7…`).

| | fitting | calibration |
|---|---:|---:|
| groups | 180 | 100 |
| candidate runs | **720** | **400** |
| unique outcomes / duplicates excluded | 720 / 0 | 400 / 0 |
| hidden passed / failed | 360 / 360 | 200 / 200 |
| baselines passing hidden verification | **0** | **0** |
| candidates left unattempted | 0 | 0 |
| every outcome follows the seal | true | true |
| observations recorded | 720 | 400 |
| distinct sealed feature vectors | 720 | 400 |
| **`REAL_GOVERNED_RUN` observations** | **0** | **0** |
| replay: identities resolved / replayed / containers | 900 / 900 / **0** | 500 / 500 / **0** |
| receipt resumable, effective remainder | true, empty | true, empty |

1,120 outcomes, which is the contract's number exactly, all `self_play`, none of them a governed
run. Every group reported `all_candidates_labelled`: nothing was left unattempted and no
sequence stopped early.

### The seal is reloaded, not rebuilt

The execute stage reads the feature seal back out of the artifact store by the artifact id
S21D5-025 recorded, and refuses if it does not hash to the recorded value. A campaign that
re-derived its seal would execute against whatever the encoder produces today, which is a
different model wearing the same lineage. It also re-prepares each task package and refuses if
the manifest no longer hashes to what the seal was bound to — because every planned run identity
would differ from the receipt's, and the resume would silently pay for its containers twice.

### The pass rate is exactly half, and that is the corpus, not a coincidence

360 of 720 and 200 of 400. The authoring contract puts two full repairs and two half-repairs in
every group, so half of every group's candidates pass the hidden suite by construction. The
number confirms the corpus is the one that was authored; it is not a measurement of anything.

What *is* worth reading is acceptance **by recipe**, because the recipe-to-variant binding is
shuffled per group and a recipe that predicted the label would be a leak the feature channels
never see:

| | alpha | beta | gamma | delta |
|---|---:|---:|---:|---:|
| fitting | 0.544 | 0.450 | 0.467 | 0.539 |
| calibration | 0.330 | 0.600 | 0.530 | 0.540 |

Spread around a half, and the ordering does not agree between the two partitions. A recipe
sitting near 0 or 1 in both would have meant the shuffle was not shuffling.

### Sixteen observations in the store that no campaign recorded

The store holds 1,136 observations; the two campaigns recorded 1,120. The difference is eight
from the two vertical-slice runs and eight from a two-group smoke test of the execute stage,
which re-ran `boundary_collections.chunk` and `d2_transform.chunk_mapping` before the full
campaign did.

They are left in place rather than deleted: the learned store is append-only, and quietly
removing rows to make a total match is the opposite of what an evidence store is for. They cannot
reach a dataset — S21D5-030 builds an **explicit** selection from the campaign records' own
observation ids, so membership is named rather than queried. Recorded here so the count
difference is a sentence somebody wrote rather than a discrepancy somebody finds.

### W1 is closed

S21D5-020 through S21D5-026 and S21D5-050. Both corpora authored, validated, separated and
sealed; 1,120 features sealed before any container; the v3 artifact built and proved; the
vertical slice run end to end on a group in no role; both campaigns executed and ingested under
new run identities.

**Gate L2 does not pass and Sprint 22A remains blocked.** W1 measures nothing about the
hypothesis: the first number that bears on it is W2's risk–coverage curve at 320 and 720 rows.

Section 6.2 of the backlog governs a shortfall: if W1 could not reach 100 groups, the honest
response was to author fewer, record the achieved independent-decision count and let §2.3's floor
decide the outcome — never to lower the floor, and never to reinstate replicated decisions to
reach it. **The provision did not have to be used.** The corpus reached 100 with no floor touched,
no threshold changed and `shortfall: 0` on the validator's own report.

---

## W2 outcome — the correction branch answers, and the answer is a margin that ranks but cannot certify

Eight items, two new scripts, one extended contract, and the first D5 numbers that bear on the
hypothesis. The wave ends at **§3.3 step 5, `selective_margin_bound`**: the fitted direction
ranks far above the strongest deterministic baseline, and the projection margin cannot certify
enough of what it ranks to reach the 0.40 coverage floor at either volume.

| | 320 rows | 720 rows |
|---|---:|---:|
| fitting groups / pairs | 80 / 320 | 180 / 720 |
| first-choice rate over all 100 answered | **0.91** | **0.88** |
| strongest deterministic baseline, same decisions | 0.42 | 0.42 |
| derived zero-error threshold | 0.651587 | 1.071794 |
| admitted at that point | 26 | 27 |
| **zero-error coverage** | **0.26** | **0.27** |
| confident errors among admitted | 0 | 0 |
| Clopper-Pearson 95% upper bound at that count | 0.10883 | 0.105019 |
| projected changed final decisions | 50.8 | 46.7 |
| maximum inference, per candidate | 0.080 ms | 0.067 ms |

Both cells fail **exactly one** §2.3 condition — `clean_coverage_below_0.40` — and satisfy the
other seven, including the one D4 could never reach: zero confident errors on a non-empty
admitted set.

### S21D5-030 — the snapshots, and two matrices that can be scanned against each other

`scripts/reality_campaign_d5.py --stage snapshot`, `evidence/sprint-21d5-snapshots.json`
(`ec85be4212ac86c8…`).

Two explicit revision-3 selections naming the 1,120 recorded observation ids, each dataset built
twice through **fresh** application services over the same durable authorities, and both rebuilt
identically. 720 fitting rows over 180 groups, 400 calibration rows over 100, 390 fitted
dimensions, the channel list equal to the v2 allowlist in order, and no group crossing the split.

**Eleven scans, eleven passed.** S21D5-024's five red rows were the consequence of a slice that
had only one matrix to give and had to scan it against itself; here the two matrices are genuinely
different sets, which is the condition those scans were written for. Maximum cross-split
similarity is 0.990806 against a near-duplicate threshold of 0.999.

The labels are read from the durable outcome ledger, not from the campaign reports, and the stage
refuses if any of the 1,120 disagrees with what the campaign recorded. Nothing disagreed. Both
matrix hashes are recorded, and every later stage in this wave refuses to score rows whose matrix
does not hash to one of them — the fitting matrix is `2d86677c44b9cdd7…` and the calibration
matrix `106061126df83261…`.

The store holds 1,136 observations to the datasets' 1,120. Each unreferenced prefix is resolved
against a manifest this sprint released rather than described: eight under the S21D5-024 fixture
manifest, eight under the fitting campaign manifest from the two-group smoke test.

### S21D5-031 — invariance, measured on D5's own bodies

`scripts/invariance_regression_d5.py`, `evidence/sprint-21d5-invariance-regression.json`
(`2543558f322d8cf4…`).

Forty transformed cases over twenty of the hundred freshly authored calibration groups, two cases
per group, 160 candidate vectors compared:

- **0 vectors changed.** Every transformed feature vector is identical to its clean counterpart,
  so the forty transformed decisions repeat twenty clean ones and add none — the zero S21D5-023
  sealed, now executed on D5's own corpus rather than inherited from D4's.
- **0 verifier label changes** across 160 transformed candidates run under plain pytest in a
  scratch directory. No governed run, no observation, no dataset growth.
- **0 first-action changes**, so §2.3's 100% preservation condition holds.
- The semantic-mutation control changed the canonical representation in all four cases, which is
  what keeps the first result from being satisfied by a canonicaliser that erased everything.

**The ranker-dependent form is an implication, not a second run.** A ranker whose input is four
vectors and a slot order cannot move when neither moves, and both premises are measured here:
every transformed vector equals its clean one, and the slot order the tie-break uses is
catalogue-fixed. Re-ranking the sample under the fitted direction would reproduce the same
ordering by construction and report it as though it were an observation. S21D5-035 reads the two
premises instead.

W2-D9 is re-measured on this model copy rather than cited: every source is embedded window by
window on its own, so a difference between a clean and a transformed vector can only come from the
transformation. The record also states what it therefore cannot claim — these vector hashes are
not the S21D5-025 seals, because the campaign encoded in batches of 64 under the fitting bounds
and this encodes one window at a time under bounds fitted on the sample.

### S21D5-032 — two directions, sealed before any calibration label is read

`scripts/learner_selection_d5.py --stage fit`, `evidence/sprint-21d5-direction-fit.json`
(`1f2d9b615d3c8b1d…`).

The stage loads the fitting matrix and nothing else, which is what makes "sealed before any
calibration decision is scored" checkable rather than asserted. Two directions, 390 weights each,
stored in the artifact store as round-trippable bytes:

| | 320 rows | 720 rows |
|---|---|---|
| model hash | `5b15f4af06a2b08d…` | `9fd297fb40701537…` |
| fitted groups / pairs | 80 / 320 | 180 / 720 |
| stored bytes | 27,099 | 27,040 |
| largest / median absolute weight | 3.42547 / 0.207676 | 6.35684 / 0.273668 |

A refit in the same process reproduces each hash, and a reload from the store reproduces it too.
That says the solver is deterministic on this machine; it does not say the weights are
bit-identical on another BLAS, which is why every later stage reloads the stored bytes instead of
refitting.

### S21D5-033 — the baseline, and an honest note about how weak a bar it is

`scripts/learner_selection_d5.py --stage baseline`,
`evidence/sprint-21d5-baseline-ladder.json` (`6cd373eea06988c9…`). No model is loaded; the
baseline is a property of the corpus.

| rung | eligible | first-choice rate |
|---|---|---:|
| `fixed_input_order` | yes | **0.42** |
| `lexical_similarity` | yes | 0.41 |
| `deterministic_static_ordering` | yes | 0.09 |
| `frozen_minilm_cosine` | no | — |
| `width_20_bounded_graph` | no | — |

Both ineligible rungs are recorded with the reason: v2 removed the channel the cosine rung orders
by, and a four-candidate task makes a twenty-wide shortlist the entire pool.

**0.42 is at chance and the record should say so.** Two of every four candidates repair the
contract, so a rung that cannot read the code picks a correct one about half the time, and the
recipe-to-variant shuffle is designed to keep it there. Reading 0.91 against 0.42 as a large
margin over a strong opponent would overstate it: what §2.3 asks is that the learner beat the best
thing available that does not learn, and the best thing available that does not learn is close to
a coin. The number that matters for the sprint is the coverage, not this gap.

### S21D5-034 and S21D5-035 — derived once, reproduced across a restart, and typed

`--stage point` → `evidence/sprint-21d5-operating-point.json` (`b978c57d0f4ccf1a…`), then
`--stage select` → `evidence/sprint-21d5-learner-selection.json` (`4d45fc00188c00ca…`) in a
**separate process**, which reloads each sealed `OperatingPointV4` and passes it back to
`derive_zero_error_point` as `previous`. A different threshold raises `OperatingPointError` there
rather than being written. Both derivations reproduced.

The two gates stay distinct. The margin floor decides abstention and is held at **0** throughout —
a floor chosen against these decisions would be a threshold fitted to the certification set, which
is what §3.4 forbids. The operating point decides admission and is derived, never chosen. D4's
released floors 0.55 and 0.70 are deliberately absent: they are proportions of a k-NN
neighbourhood's acceptance mass, and a projection margin is not a proportion.

**The grid is two cells.** D4 crossed a pre-registered 24-setting k-NN grid with three operating
points; revision 5 pre-registers one class, one regulariser and one confidence, so the only free
coordinate left is the volume point. Everything a reader might otherwise want from a grid is in
the **sweep**: every distinct margin at each volume, 200 points, each marked `selectable: false`,
because choosing one would be the search §3.4 forbids.

The sweep is where the result is legible:

| admitted | errors at 320 | errors at 720 |
|---:|---:|---:|
| 20 | 0 | 0 |
| 26 | 0 | 0 |
| 27 | 1 | **0** |
| 30 | 1 | 1 |
| 40 | 2 | 1 |
| 50 | 3 | **1** |
| 60 | 3 | 2 |
| 100 | 9 | 12 |

At 720 rows the margin ordering admits 50 of 100 decisions with a single error. The zero-error
rule stops at 27 because the 28th-ranked decision is wrong, and the rule admits nothing below its
first error. That gap — 0.27 certified against 0.50 at one error — is the whole content of the
stop.

### Why the ending is step 5 and not step 4 or step 6

§3.3 says "materially higher" and "at or near zero" and quantifies neither. Both readings are
made operational from the power contract rather than from the measurement: five admitted decisions
of a hundred is 0.05 coverage, and zero errors in five decisions bounds the true error rate at
45%, which certifies nothing anybody would act on. So *near zero* is coverage at or below 0.05,
and *material* is a volume difference of at least 0.05. Every raw number is in the record, so a
reader who prefers another reading can apply it without re-running anything.

- Not **step 6**: 0.26 and 0.27 are nowhere near zero. D4's k-NN measured exactly zero at both
  volumes; this class has a real zero-error region on a fresh corpus.
- Not **step 4**: 0.27 − 0.26 = 0.01. A 2.25× volume increase moved the certified boundary by one
  decision. There is no yield curve here for a corpus sprint to extrapolate.
- **Step 5**: coverage above zero, below 0.40, flat across the span, with first-choice rate far
  above the baseline at both volumes. The direction ranks; the margin cannot certify enough of
  what it ranks.

The successor named by the stop kind is therefore a sprint that pre-registers **a different
confidence construction over this same ranker** — split-conformal over the margin being the
obvious candidate — not a different ranker, not a third hypothesis class, and not a larger corpus.

### What volume did and did not do, read both ways

More fitting evidence made the top of the ranking better and the whole ranking slightly worse:
at 720 rows the first 50 admitted decisions carry one error against three at 320, while the
first-choice rate over all 100 answered falls from 0.91 to 0.88. Both directions are in the
record. The honest summary is that the extra 100 groups sharpened the margin's ordering where the
margin is large and cost a little accuracy where it is small, and neither effect is large enough
to move the certified boundary by more than one decision.

### The spent-evidence diagnostic transferred, partly

S21D5-010 justified the class on a diagnostic over spent evidence that measured zero-error
coverage at **0.22** on a disjoint 80-group pool and **0.32** on a combined 179-group pool. The
fresh measurement is **0.26** at 80 groups and **0.27** at 180. The small-pool estimate transferred
well; the large-pool one did not. The pre-registration called those estimates "on authored data
this class has already seen — they justify running the experiment; they do not forecast it", and
that wording held up: the experiment was worth running, and the forecast for the larger pool was
1.2× optimistic.

### S21D5-036 — the typed continuation, and 26 items that stay closed

`scripts/continuation_d5.py`, `evidence/sprint-21d5-continuation.json` (`306b9121d84a3466…`),
stop hash `7b59897d8d83a51b…`.

The decision is read from the selection record rather than restated: `stop`, kind
`selective_margin_bound`, with **26 named items not opened** — S21D5-051 through 059, 060 through
069, and 070 through 074, 076 and 077 — and **15 Gate L2 conditions** left unopened (10, 11,
13–16, 18–23, 25–27). Absence is a claim, and a list is what makes it checkable: an item that is
later opened has to be removed from a named set rather than reinterpreted out of a phrase.

Four things the stop explicitly does **not** cancel, each with its reason in the record: the
retrieval branch and its condition-24 and D1-condition-15 decisions, which share no input with
this measurement; S21D5-037, which depends on the pre-registration; S21D5-075, which the backlog
marks unconditional; and operations, release and the gate-close record, because §8.2 is explicit
that a negative release is a complete release rather than an abandoned one.

### S21D5-037 — condition 20 names the class that produced its confidences

`scripts/promotion_payload_d5.py`, `evidence/sprint-21d5-promotion-payload.json`
(`d5c3ea4d43079501…`).

D4 made the metamorphic/OOD row carry two denominators and the certificate its answered set was
decided under. That says how many decisions were counted and which threshold answered them, and
not *what* was thresholded — and after D5 a stored payload could be about either a k-NN
neighbourhood's acceptance mass or a projection margin. So the row names the class:
`PromotionDecisionCounts.hypothesis_class`, optional, checked in `condition_20_gate` against the
classes the artifact loader actually implements.

Where the check lives is a decision: the domain model accepts any non-empty string and the
builder refuses a class no loader implements. A domain model owning that list would be a second
place for it to go stale, and the refusal belongs beside the loader that has to load one — before
the bytes are stored, not at activation.

`d3-promotion-payload` stays at v2 and the dispatch is unchanged. Three shapes were dispatched and
reloaded to their recorded identity: the legacy v1 assessment, a D4-shaped payload carrying counts
and no class, and a D5 payload naming the class. Five refusals were exercised rather than
described. One behaviour is recorded as deliberately *not* a refusal: a JSON object with no
`schema_name` at all reads as version 1, because the legacy shape predates the field.

**A defect this item's own test found.** `canonical_payload_bytes` excludes nulls, which is what
kept S21D4-048 additive — and it does nothing for `canonical_json`, which is what the contract
hashes. The first version of the extension left the stored bytes stable and silently moved the
`content_hash` of every payload already holding a counts row. The fix is the mechanism D4 built
for exactly this: `hypothesis_class` joins `CANONICAL_ABSENT_WHEN_EMPTY`. Both halves are now
measured — a D4-shaped payload hashes as it did, and naming the class is new bytes and a new
identity. The `D3PromotionPayload` schema pin moves once, additively, to
`f81aefbdbb7215a7…`, with the docstring saying which two items moved it and why the version
did not.

### W2 evidence index

| Item | Record | Integrity hash |
|---|---|---|
| S21D5-030 | `sprint-21d5-snapshots.json` | `ec85be4212ac86c8…` |
| S21D5-031 | `sprint-21d5-invariance-regression.json` | `2543558f322d8cf4…` |
| S21D5-032 | `sprint-21d5-direction-fit.json` | `1f2d9b615d3c8b1d…` |
| S21D5-033 | `sprint-21d5-baseline-ladder.json` | `6cd373eea06988c9…` |
| S21D5-034 | `sprint-21d5-operating-point.json` | `b978c57d0f4ccf1a…` |
| S21D5-035 | `sprint-21d5-learner-selection.json` | `4d45fc00188c00ca…` |
| S21D5-036 | `sprint-21d5-continuation.json` | `306b9121d84a3466…` |
| S21D5-037 | `sprint-21d5-promotion-payload.json` | `d5c3ea4d43079501…` |

### W2 is closed

S21D5-030 through S21D5-037. Snapshots materialised and every scan passed; the invariance sample
resolved with no drift of any kind; the direction fitted and sealed at both volumes before a
calibration label was read; the baseline measured on the same decisions; the operating point
derived once per volume and reproduced across a restart; the risk–coverage curve reported in full;
one typed stop recorded with a complete not-opened map; and the promotion contract extended
additively for the v3 class.

**Gate L2 does not pass and Sprint 22A remains blocked.** The correction branch is closed at
`selective_margin_bound`. The retrieval branch (W3, S21D5-040 through 047) is untouched by this
result and still owes condition 24 and Gate D1 condition 15 an answer on its own freshly authored
holdout.

---

## W3 outcome — the retrieval branch answers, and the answer is a pass

Eight items, four new scripts, one finding about released evidence, and the first D5 gate
condition that closes. D4 measured a **near miss**: fusion cleared the recall floor and missed
MRR@10 by 0.0089. D5 turned the complete surface on, authored a fresh sixty-group pool, read it
once, and one arm cleared both floors.

| arm | Recall@5 | MRR@10 | first failed floor |
|---|---:|---:|---|
| no_memory | 0.0000 | 0.0000 | recall_at_5 |
| exact_signature | 0.0000 | 0.0000 | recall_at_5 |
| **lexical** | **0.7500** | **0.5389** | **none** |
| minilm_vector | 0.7833 | 0.4286 | mrr_at_10 |
| minilm_shortlist_plus_bounded_ged | 0.5667 | 0.3296 | recall_at_5 |
| reciprocal_rank_fusion | 0.7167 | 0.4674 | mrr_at_10 |
| chance baseline | 0.5768 | 0.3317 | — |
| **floor** | **0.70** | **0.50** | — |

Sixty unseen-task queries against a floor of fifty. Every arm inside the two-second query budget,
every arm reproducing its own ranking across two passes, zero timeouts.

**Gate L2 condition 24: met. Gate D1 condition 15: closed.**

### S21D5-040 and S21D5-041 — the complete surface, on D5's corpus

[`sprint-21d5-surface.json`](evidence/sprint-21d5-surface.json), integrity `caf3293baae9cde5…`.

| measurement | D5 | D4, for context |
|---|---:|---:|
| sides carrying terms | **120 of 120** | 94 of 120 |
| sides that needed the structural fallback | **27** | not available |
| candidates with no terms | **0** | 10 |
| distinct candidate term sets | 55 of 60 | — |

Every one of the 120 sides is projected twice — with the flag and without it — because "the
fallback answered D4's residual" is a claim about a difference, and a record that only ran the
flag on has no second number to show it. 27 sides carry no identifier at all under the released
extraction and would have projected empty; under the complete surface none does.

Five collisions of term sets remain, two of them cross-family. A shared term set inside a family
costs nothing — both documents are relevant to the same query — while across families it is a
document the wrong query can reach. Both counts are recorded; the searchable document also
carries domain and task signature, so a shared term set is not a shared document.

The exclusions and the guards were executed rather than read off a field list: a graph carrying
terms and the same graph without them agree on `structural_hash` and on every node label, and a
judgement leak, an over-bound list, an uncanonical list, a repeated term and a forbidden marker
were each refused — including a leak planted in a *fallback* term, since the fallback puts text
in front of the guard that D4 never gave it.

### Finding S21D5-W3-F1 — a released graph set whose bytes are gone

`sprint-21d4-retrieval-emg-root.json` declares sixty pairs and **none of their blobs resolves**.
The root file is byte-identical to the one S21D4-044 recorded (`0960818f07981523…`), and that
record reports `resolved_pairs: 60, intact: true`, so the bytes existed when D4 wrote them. Every
file under `cognitive-os-data` — backups included — was searched by all five hashes each root
child declares: **0 of 60 found under any of them**.

When it happened is not determinable from evidence. D4 released no fingerprint of its own
artifact store; `sprint-21d4-operations.json` recorded `artifacts-s21d4` at 3,990 files before
and after W7, and the D5 baseline's first observation is 4,006 with "no released expectation
exists". Neither count can be decomposed into which files they were.

The consequence is bounded and stated rather than worked around: D4's pool cannot serve as a
development replay pool and its numbers cannot be re-derived from its graphs. Its released
result record remains valid evidence of what was measured; it is simply no longer re-runnable.
Nothing was reconstructed — regenerating the blobs would mean re-executing D4's sixty groups
under D5's runner and calling the result D4's evidence. D5's own pairs are unaffected: they are
projected, stored and read back in D5's own store, and S21D5-044 verifies them there.

### S21D5-042 — the development replay, and a prediction that held

[`sprint-21d5-retrieval-development.json`](evidence/sprint-21d5-retrieval-development.json),
integrity `bd09e347c8f99f6b…`.

D4's replay excused one arm, because W3 had just given the bounded-GED comparator a fixed
iteration budget. **D5 changed no arm, no comparator, no weight and no fusion constant**, so the
prediction declared before the run was stronger: *every* arm reproduces its predecessor value
exactly, on every pool that resolves. It did — six arms on D1's eighty-query set and six on D3's
spent holdout, `arms_that_moved: none` on both, every arm reproducing its own ranking, zero store
writes. The D4 pool is recorded as not replayable with the failed load beside it rather than
omitted.

Both replayed pools carry 0 graphs with terms, which is the point: they were projected before the
surface field existed, so the complete surface contributes nothing there and any movement would
have come from somewhere this wave believed it had not touched.

### S21D5-043 and S21D5-044 — sixty pairs executed, projected and sealed

[`sprint-21d5-retrieval-emg-projection.json`](evidence/sprint-21d5-retrieval-emg-projection.json)
(`54ee47bc5db2efcf…`) and
[`sprint-21d5-retrieval-query-set.json`](evidence/sprint-21d5-retrieval-query-set.json)
(`54cd52274ba16436…`).

Separation first, before a container starts: zero retrieval groups crossing a correction role,
zero task signatures and zero query ids reused from **three** predecessor query sets — D1's, D3's
and D4's, 200 queries in total — zero cross-group near clones, and the sealed pool hash differing
from the spent D4 one.

| | result |
|---|---|
| groups executed, not declared | **60** |
| baselines that failed their hidden suite | **60** |
| repairs that passed their hidden suite | **60** |
| edit-path round trips | **60 of 60** |
| source hashes resolved from the store | **60 of 60** |
| graphs over the resource bounds | **0** |
| seeded refusals (missing, broken link, corrupt) | **3 of 3 refused** |
| graphs carrying terms | **120 of 120** |
| pairs whose two sides differ in terms | **60 of 60** |
| structural hash unmoved by the flag | **true, all 60** |
| **distinct documents, domain and signature removed** | **55 of 60** |
| queries qualifying | **60**, floor 50, ten per family |
| searchable text naming its own judgement | **[]** |

55 of 60 is the number that is comparable across sprints, taken the same way in all three: D3
measured 1, D4 measured 41. It is not a controlled comparison — three pools, three sets of
bodies, and the fallback only on here — and it is the measurement the D3 finding asked for.

### S21D5-045 and S21D5-046 — read once, decided by the frozen floors

[`sprint-21d5-retrieval-holdout-result.json`](evidence/sprint-21d5-retrieval-holdout-result.json)
(`92a553d9f19afa90…`) and
[`sprint-21d5-retrieval-decision.json`](evidence/sprint-21d5-retrieval-decision.json)
(`ccc666c70833d27c…`).

One execution, no rerun after the metrics were known, the queries on disk before the benchmark
subprocess existed, the GED budget inherited from S21D4-041 and not re-decided. The decision is a
separate record that reads the sealed result by hash, under first-failure precedence: a pass
needs one arm to clear *both* floors.

`lexical` clears both, so it is the winning arm under the frozen order. `minilm_vector` has the
better recall (0.7833) and misses MRR; fusion sits between them and misses MRR. Nothing was
reopened to reach the result: fusion variants 0, widths 0, weights 0, metrics 0, holdout members
added 0.

**Three things this result is not.** It is not a controlled comparison with D4's near miss — a
different corpus, a complete surface, and one read of each holdout. It is not an ablation: no
run was made with the fallback off, because the holdout is read once and §3.4 says so. And it is
not a claim that the ranking is good in general — 0.7500 recall against a 0.5768 chance baseline
on sixty queries is a floor cleared, not a wide margin, and the honest reading is that a lexical
arm over structurally complete documents is enough for *this* corpus at *these* floors.

Worth naming explicitly, because it is the mechanism: relevance here is the task family, and the
27 sides that needed the fallback carry AST node-type terms. Same-family tasks share structure by
construction of the corpus, so structural terms are a legitimate signal for the relevance rule
rather than a leak — the family label itself never appears, and the leak guard ran over the
complete text of all 120 documents and found nothing.

### S21D5-047 — the boundary, re-proved over more text than it has ever seen

[`sprint-21d5-advisory-boundary.json`](evidence/sprint-21d5-advisory-boundary.json), integrity
`79269a9d1d03d2d6…`. **Boundary held.**

| property | result |
|---|---|
| mandatory bundle sections byte-identical with and without retrieval | **6 of 6 compared** |
| advisory candidates pinned, required or evidence | **none** |
| advisory candidate carrying an executable body | **none** |
| empty set | **degraded**, not unavailable |
| store-breakage paths ending at `UNVERIFIED` | **4 of 4** |
| a non-advisory purpose | **gets nothing** |

A positive retrieval result is as much a reason to run this as a negative one, and D5 has a
second reason D4 did not: under the complete surface all 120 graphs carry terms, where D4 stored
26 that carried none. The boundary is proved over the text the advisory path is actually handed,
and that text is larger on every graph than anything D1 or D4 proved it against.

### W3 evidence index

| Item | Record | Integrity hash |
|---|---|---|
| S21D5-040, -041 | `sprint-21d5-surface.json` | `caf3293baae9cde5…` |
| S21D5-042 | `sprint-21d5-retrieval-development.json` | `bd09e347c8f99f6b…` |
| S21D5-043 | `sprint-21d5-retrieval-query-set.json` | `54cd52274ba16436…` |
| S21D5-044 | `sprint-21d5-retrieval-emg-projection.json` | `54ee47bc5db2efcf…` |
| S21D5-045 | `sprint-21d5-retrieval-holdout-result.json` | `92a553d9f19afa90…` |
| S21D5-046 | `sprint-21d5-retrieval-decision.json` | `ccc666c70833d27c…` |
| S21D5-047 | `sprint-21d5-advisory-boundary.json` | `79269a9d1d03d2d6…` |

The graph set and the query manifest are `sprint-21d5-retrieval-emg-root.json`
(`92fb4c9ffaa03ecf…`) and `sprint-21d5-retrieval-queries.json`.

### W3 is closed

S21D5-040 through S21D5-047. The complete surface projected and measured on D5's own corpus; the
development benchmarks replayed with every arm reproducing; sixty pairs executed, projected,
stored and verified; sixty queries frozen before any arm ran; six arms evaluated exactly once;
the frozen floors applied under first-failure precedence; and the advisory boundary re-proved.

**Gate L2 still does not pass, and Sprint 22A stays blocked.** One condition of twenty-nine
closed here. The correction branch remains stopped at `selective_margin_bound`, which leaves
conditions 10, 11, 13–16 and 18–23 and 25–27 not opened, and §8.1 requires all twenty-nine.
What W3 changes is that the sprint now has one branch with a positive result to release:
condition 24 is met on a freshly authored holdout read once, and Gate D1 condition 15 closes on
D5's own evidence rather than staying open behind the correction stop.
