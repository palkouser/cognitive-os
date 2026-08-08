# Sprint 21D5 execution log

- Branch: `feature/sprint-21d5-pairwise-selective-ranking`
- Backlog: [Sprint 21D5 Technical Backlog](sprint-21d5-technical-backlog.md)
- **Status: W0 complete.** W1 through W8 not started.
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
