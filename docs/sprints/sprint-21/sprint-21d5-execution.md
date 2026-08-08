# Sprint 21D5 execution log

- Branch: `feature/sprint-21d5-pairwise-selective-ranking`
- Backlog: [Sprint 21D5 Technical Backlog](sprint-21d5-technical-backlog.md)
- **Status: W0 complete. W1 in progress — S21D5-020 through S21D5-023 closed: both corpora
  authored, validated, proven separated and sealed.**
  W2 through W8 not started.
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

### What W1 still owes

- pre-execution feature seals and both campaigns, 720 fitting and 400 calibration outcomes
  (S21D5-025, S21D5-026).

Section 6.2 of the backlog governs a shortfall: if W1 could not reach 100 groups, the honest
response was to author fewer, record the achieved independent-decision count and let §2.3's floor
decide the outcome — never to lower the floor, and never to reinstate replicated decisions to
reach it. **The provision did not have to be used.** The corpus reached 100 with no floor touched,
no threshold changed and `shortfall: 0` on the validator's own report.
