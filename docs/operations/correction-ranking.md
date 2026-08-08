# Operating the correction-ranking evidence

Sprint 21D2 built a learned correction-ranking surface, measured it, and did not activate it.
This document covers what exists and can be operated. Section
[*What was never opened*](#what-was-never-opened) lists what does not, so that nobody goes
looking for a command that was deliberately not built.

There is no activation, approval, canary or rollback procedure here. Not because they are
undocumented — because on this sprint's outcome they have no subject. See
[learned evidence](learned-evidence.md) for the lifecycle those operations belong to.

## Prerequisites, and the one that costs a wasted hour

```bash
set -a && . ./.env.s21d2.local && set +a      # the isolated D2 pair, never the development one
```

That is enough for the Python commands. **It is not enough for the shell scripts.** Every
`scripts/*.sh` in this repository re-reads its own environment file inside `set -a`, so it
overwrites exported handles with the development ones. This is deliberate: it is what stops a
mis-scoped command reaching a real database. The consequence is that a shell script must be
*told* which file to read:

```bash
COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d2.local ./scripts/backup_event_store.sh
COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d2.local ./scripts/restore_event_store.sh --test-restore
COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d2.local ./scripts/postgres_migration_check.sh
```

Skipping it does not fail loudly. `backup_event_store.sh` backs up `cognitive_os_dev` and says
so in one line that is easy to read past; `postgres_migration_check.sh` reports *"Database is
not on all head revisions"*, which is true about the development database and alarming about
the wrong one. Both happened during Sprint 21D2 W9 and are recorded as W9-F1 in
[`sprint-21d2-operations.json`](../sprints/sprint-21/evidence/sprint-21d2-operations.json).

`.env.s21d2.local` is gitignored, mode 0600, and contains credentials. No command in this
document prints one, and no example here contains one.

| Handle | What it names |
| --- | --- |
| `COGOS_DATABASE_URL` | the D2 evidence database, `cognitive_os_s21d2_test` |
| `COGOS_ARTIFACT_ROOT` | the D2 artifact pair |
| `COGOS_INTEGRATION_DATABASE_URL` | a *separate* database for the suites, which truncate every table they find |
| `COGOS_RESTORE_DATABASE_URL` | the restore target; refused unless the name ends in `_test` |
| `COGOS_BACKUP_ROOT` | where dumps and archives land |

The integration database is separate on purpose. `tests/integration/postgres` truncates
everything, and the guard in `postgres_common.sh` keys on a `_test` suffix — which the
evidence database also has. Sprint 21C3 lost its evidence store to this twice.

## Reading the store

```bash
uv run python scripts/learned.py health
uv run python scripts/learned.py artifact-verify
uv run python scripts/learned.py correction-runtime --config <configuration> --group <group>
uv run python scripts/learned.py correction-integrity \
  --seals docs/sprints/sprint-21/evidence/sprint-21d2-self-play-campaign.json \
  --stop-record docs/sprints/sprint-21/evidence/sprint-21d2-w9-stop-record.json \
  --inherited <json naming the inherited roots and their digests>
```

All four print one line of sorted JSON. Exit status is `0` healthy, `1` unhealthy or a
verification failed, `2` invalid usage, `3` not found.

`correction-runtime` answers *why the deterministic ordering is in use*. On this sprint's
outcome the answer is always that no component is active, and the reason code says which of
the four authorities disagreed. It cannot activate anything; there is no flag that does.

### `correction-integrity`

Eight classes over the correction-ranking evidence: role crossing, chronology, manifest
membership, artifact lineage, activation state, receipt chain, model identity, and store
isolation. Three severities, and the third is the one that needs explaining.

* A **failure** means recorded evidence is wrong — a row whose role disagrees with the
  partition that sealed it, an outcome earlier than its own feature record, a lineage row
  with no bytes, a gap in the compare-and-set receipt chain, an inherited store that moved.
* A **warning** means the store is sound but is not what a naive reader would assume. There
  is exactly one on this evidence: two campaign manifests were sealed three times each,
  because the campaign was executed more than once, so a dataset built from "every row on
  this surface" would silently span two executions.
* **`not_opened`** means the class has no subject. It is never a pass. Each such check
  carries `bound_hash` — the content hash of the record that closed it — and the report
  refuses to construct an unbound one. Two classes are `not_opened` here: activation state
  and model identity.

`not_opened` is not a way to stop looking. If the store holds a component on the stopped
surface, the claim becomes a **failure** naming it: the stop record asserts the store is
empty, and that assertion is checked like any other.

`--seals` is required and names the campaign evidence, because the sealed feature-set
artifacts are the authority for six of the eight classes and this command must not be free to
invent them. The command additionally discovers every seal in the store, which matters when a
campaign was executed more than once — measuring a row against a seal it did not run under
reports sound evidence as damage.

## Backup, restore, and what a restore has to reproduce

```bash
COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d2.local ./scripts/backup_event_store.sh
COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d2.local ./scripts/restore_event_store.sh --test-restore
```

`scripts/operations_d2.py --output <file>` runs the whole procedure and records it: back up,
restart PostgreSQL, restore into the isolated restore database, extract the artifact archive
to a scratch directory, and compare the two copies. It writes to the backup root, the restore
database and a scratch directory, and to nothing else; it fingerprints all four artifact pairs
before and after.

What it compares, and why each one is needed:

| Compared | Because |
| --- | --- |
| row counts | the cheapest check, and the one that catches a truncated restore |
| a digest over every hashed row | counts would not notice a row whose content changed while the total held |
| every artifact blob, re-hashed from the archive | the database and the filesystem are two stores, and only one of them is in the dump |
| the campaign receipt sets | `plan_resume_with_receipts` reads them; a lost receipt makes a resume re-run work the campaign chose not to do |
| recorded run identities and candidate outcomes | the other two store-side inputs to the same planner |
| the full integrity report, verdict by verdict | so a difference between the copies is a difference in the evidence, not in the reader |

**On this outcome, what must survive the restore is an absence.** There is no active model, so
the assertion is that the restored store holds zero components, revisions, evidence records,
approvals and activations. That is the easiest thing for a restore to get wrong in the
safe-looking direction, which is why it is asserted rather than assumed.

## Damage, and what refuses it

`scripts/operations_d2.py` also runs ten damage cases against the *extracted copy* — never
against the evidence pair. Each is recorded with what was damaged, what was expected, and what
happened.

| Damage | What refuses it |
| --- | --- |
| a byte appended to a stored blob | the re-hash; content-addressed storage makes the name the claim |
| a blob deleted | the read path. A re-hash of what remains would report a clean store one file smaller |
| a lineage row with no bytes | `every_correction_lineage_row_resolves_to_its_bytes` |
| a lineage row whose declared hash is stale | the same check, reported apart |
| the database read against the wrong artifact root | the artifact store, before the report begins |
| a value edited inside a sealed feature set | the contract, at deserialisation — it re-seals on load and never becomes an object |
| a *valid* seal from another execution served under the declared identity | only the independently recorded hash. This is the attack the case above cannot mount |
| a component fabricated on the stopped surface | the `not_opened` claim becomes a failure |
| a truncated receipt stream | `every_campaign_receipt_chains_to_its_predecessor` |
| an inherited pair checked against a digest that is not its own | the per-store isolation check, named for the store |

## Prohibitions that do not expire

These are properties of the design, not settings.

* **No artifact is ever deserialised into code.** `LearnedArtifactFormat.JOBLIB` stays in the
  enum as a descriptive legacy value with no runtime load path. The correction artifact is
  canonical JSON with no format dispatch, no class name and no import path, so a tampered
  artifact yields a wrong ranker or no ranker — never a different kind of object.
* **Real governed runs are never trained on.** All 214 inherited C3 and D1 outcomes, including
  the 120 deferred correction-ranking examples, are evaluation-eligible and training-ineligible
  for the life of the programme. The projector binds the role from the sealed partition and
  refuses to take one as an argument.
* **No learned acceptance.** Every learned-first ordering still runs the independent hidden
  verifier. Ordering is the only thing a learned component may influence.
* **No online weight updates**, and no path that would produce one.
* **The development, C3 and D1 artifact pairs are read-only to D2.** Their fingerprints are
  recorded in [`sprint-21d2-baseline.json`](../sprints/sprint-21/evidence/sprint-21d2-baseline.json)
  and re-checked by every D2 command that touches storage.

## What was never opened

Sprint 21D2 stopped at S21D2-049 with no candidate. The following have no procedure because
they have no subject, and inventing one would be documenting a system that does not exist.

| Not opened | Why |
| --- | --- |
| final batches A and B | S21D2-060 was never authorised; the holdout is closed |
| benefit, forgetting, OOD and shadow measurement | they measure a selected candidate |
| promotion assessment | it assesses a component that exists |
| operator approval, activation, canary, kill switch | they need an approved component |
| governed rollback, real leg | it needs an active component. The scratch proof from W3c stands |

Each is recorded in
[`sprint-21d2-verification-matrix.json`](../sprints/sprint-21/evidence/sprint-21d2-verification-matrix.json)
under `not_opened`, carrying the hash of the selection record that closed it — rather than
being omitted, which would be indistinguishable from a row someone trimmed.

## What passing every check here does not claim

That the store is durable, replayable, auditable and correctly refuses damage. It says nothing
about whether a learned correction ranker would help, because Sprint 21D2 measured that
separately and the answer was no: the bounded k-NN ranked an accepted candidate first in nine
of ten calibration groups against a 0.3 deterministic baseline, and then reversed at full
confidence under a rename that changed no behaviour. Gate L2 does not pass. See the
[Gate L2 assessment](../sprints/sprint-21/gate-l2-assessment.md) and the
[Sprint 21D2 report](../sprints/sprint-21/sprint-21d2-report.md).

---

# Sprint 21D3: the v2 encoder, and the second null

Sprint 21D3 rebuilt the feature representation, re-ran the campaign on fresh evidence, and
stopped again — for a different reason. Everything above still describes D2's evidence, which
is immutable. This section describes D3's, which lives in a different pair.

**What D3 changed, and what it did not.** The encoder changed; the answer did not. The
alpha-normalised v2 encoding is exactly invariant — the same contract spelled differently
reaches the same first action every time, and action preservation is 1.00 for all twenty-four
frozen settings. What remains is absolute ranking accuracy, and that is a capacity residual no
encoding change reaches. Do not read the D3 evidence as "the same result again": D2 could not
tell the two apart, and D3 can.

## Prerequisites

```bash
set -a && . ./.env.s21d3.local && set +a      # the isolated D3 pair, never a predecessor
```

The shell-script caveat above applies unchanged, with the D3 file:

```bash
COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21d3.local ./scripts/backup_event_store.sh
```

The D3 Python commands additionally **refuse a wrong environment before opening anything**. A
database whose name lacks `s21d3`, or an artifact root that is one of the four predecessor
stores, is rejected on the value rather than on a failure later:

```console
$ COGOS_ARTIFACT_ROOT=/…/artifacts-s21d2 uv run python scripts/learned.py d3-integrity
refusing to open the predecessor store at /…/artifacts-s21d2
```

That check exists because `artifacts` and `artifacts-s21d3` differ by a suffix, and the first is
the development store.

## The one report that covers everything

```bash
uv run python scripts/learned.py d3-integrity                      # offline, no store needed
uv run python scripts/learned.py d3-integrity --rehash-blobs \
  --data-root /home/palkouser/projekt/cognitive-os-data            # every authority
```

Eleven classes, four states. The states are the point:

| State | Means |
|---|---|
| `clean` | the evidence exists and the rule holds |
| `failed` | the evidence exists and the rule does not hold |
| `warning` | **this run could not check it.** Not a pass |
| `not_opened` | a stop closed it, and the row carries the stop hash |

Run without `--rehash-blobs` and `--data-root`, the artifact and isolation classes report
`warning` rather than `clean`. That is deliberate and it is the most important thing in this
document: **a class nobody checked is never reported as passing.** A report showing eleven
green rows from a command that opened no store would be a report about the command.

On the committed evidence with every authority supplied: 10 clean, 1 not opened, 0 failed.

## What the v2 encoder records, and what it removed

The frozen contract hashes to `492c90a5df420de9…` and declares **390 fitted channels**: six
structural scalars then 384 embedding components, in that fixed order. A reordered channel list
is a different model and the artifact loader refuses it.

Seven v1 inputs are **removed**, not deprecated: `changed_file_count`, `hunk_count`,
`added_line_count`, `removed_line_count`, `task_requirement_embedding`,
`candidate_delta_embedding` and `query_to_candidate_cosine`. Two baseline rungs read those
columns, so the ladder now dispatches on encoder version and reports `frozen_minilm_cosine` as
**ineligible with its reason** rather than scoring it on a column that no longer exists.

The matrix scan covers all 390 columns, embedding included. `fitted_columns: 390` in the
vertical-slice evidence is what the `matrix_embedding_scans` class checks.

## Counting units, and the correction that made them honest

D2 reported forty ranking decisions where there were ten. The corrected contract counts **one
ranking decision per case** and four independently verified candidate labels under it. D3's
calibration metamorphic set is therefore **120 decisions over 480 candidate outcomes**, and the
`ood_units` integrity class fails if those two numbers are ever equal.

When you read any rate in the D3 evidence, check which denominator it names. The two are not
interchangeable and one of them is four times the other.

## The retrieval arm and its policy

The fixed fusion arm is equal-weight lexical + MiniLM reciprocal-rank fusion, constant 60, one
post-fusion truncation, no sweeps. The benchmark **refuses to run without `--policy-hash`** and
resolves that hash against the two frozen graph resource policies; a revision name is not
accepted, and an unfrozen hash has no entry to resolve.

```bash
uv run python scripts/experience.py graph-benchmark --graph-root <root> \
  --artifact-root <store> --queries <manifest> --model <frozen-minilm> \
  --policy-hash d0e8520e3d3bc3637ce75f632c79aa00c1f456a8af1a4956601dad359c8474ab
```

Two things to know before reading a benchmark result:

- **`timeouts` and `budget_cutoffs` are different fields.** D1 reported sixty of the second
  under the first's name. A timeout is a comparison that ran out of time; a cutoff is one the
  query budget refused to start, and the remedies differ entirely.
- **`minilm_shortlist_plus_bounded_ged` does not reproduce itself.** `graph_edit_distance`
  under a wall-clock timeout is an anytime search, so its score depends on how much search fits
  in 90 ms. Four identical runs produced four different metric triples. Its D1 and D2 numbers
  are not reproducible by anyone, and the benchmark now reports agreement per arm rather than
  for the run.

## Final access, and the checkpoint that refused it

There is no final-batch, canary or activation procedure for D3 either — for the same reason as
D2, recorded differently. The pre-final checkpoint evaluates every precondition in backlog
order, stops at the first failure, and writes the not-opened map:

```bash
uv run python scripts/artifact_runtime_d3.py     # writes the checkpoint and the invariance record
```

`authorised: false`, first failed precondition *S21D3-039 selected one candidate*, twenty
dependent tasks bound to one stop hash. **Neither runtime configuration is sealed** — sealing
happens at authorised access, and access was not authorised. Two canonical configuration
documents exist with reproducible hashes; they are declared, not in force.

## Artifact verification, and the two boundaries

D3 has two ways to read a correction artifact, and they are deliberately not the same door:

1. **the direct evaluation boundary** — for calibration, final and shadow reads while the
   component is unapproved or in SHADOW. It rehashes the exact bytes *before* reading a field,
   accepts only one named artifact hash, and **refuses to exist past SHADOW**;
2. **the runtime resolver** — for canary and steady routing. It is ACTIVE, configuration and
   approval gated, holds no capability for the first boundary, and does not import it.

Verification never deserialises anything. The Artifact Store re-reads bytes and reports whether
they still hash to their record; that is the whole extent of the contact.

## Recovery and damage, on the D3 pair

```bash
set -a && . ./.env.s21d3.local && set +a
uv run python scripts/operations_d3.py           # provisioning, backup, restart, restore, matrix
uv run python scripts/verification_matrix_d3.py  # every release check, with its exit status
```

The first writes to the backup root, the restore database and the declared scratch root, and
**nothing else**. Every damage case is applied to the extracted copy or to a throwaway copy of
the evidence directory. Predecessor fingerprints are taken before and after and both are
recorded.

What the restore has to reproduce, and did: counts, the hashed-row roll-up, both resume inputs,
2,077 blob rehashes, and the **stopped state** — zero components on
`experience.correction_ranking`. That last one is checked by surface rather than by counting
learned rows, because the credential-free smoke legitimately registers an unrelated inert
component on `skill.selection` and a count would have made that look like a D3 component.

One damage case is worth reading in full. Removing a blob leaves every remaining file hashing
correctly, so a rehash reports a store one blob smaller as perfectly clean. What catches it is
the declared-versus-observed comparison, and the matrix records both facts side by side.

## Prohibitions that do not expire, for D3

Everything in [*Prohibitions that do not expire*](#prohibitions-that-do-not-expire) applies,
plus three that are D3's own:

- **The D3 calibration and metamorphic evidence is spent.** It selected nothing, but a selection
  rule read it. It may not decide anything again.
- **The D3 retrieval holdout was read once**, which is all the protocol allows. There is no
  second read, and no re-decision on it.
- **No parametric rung, threshold revision, refit or encoder revision opens on D3's evidence.**
  §10.2 closes all four, and the capacity residual is D4's input rather than D3's to chase.

## Sprint 21D4: independent decisions, the twelfth integrity class, and one fence

D4 changed three things an operator has to know about, and none of them is a model.

### A replicated decision is not a decision

This is the one that cost a sprint. D3 recorded 120 metamorphic ranking decisions; six
semantics-preserving transformations of one group encode to **one** fitted vector, so those 120
were 20 decisions repeated six times, and every rate in that sprint divided by the wrong number.
Zero errors in 20 decisions bounds the true rate at 13.9%, not at zero.

Revision 4's rule: a decision set reports `nominal_decisions`, `independent_decisions` and
`replicated_decisions`, independence is equality of the fitted vector, and every accuracy, error
and coverage rate divides by the independent count and says so in its own bytes. When you read
any D4 number, read the denominator beside it.

### The twelve-class report, and its two commands

```bash
COGOS_POSTGRES_DATABASE=cognitive_os_s21d4_test \
  uv run python scripts/learned.py d4-integrity
```

Read-only and offline. It reads the committed evidence directory and nothing else, which is why
a CI lane with no database, no store and no credential can run it. Two classes need an authority
this form does not have, and they say so:

```bash
set -a && . ./.env.s21d4.local && set +a
COGOS_POSTGRES_DATABASE=cognitive_os_s21d4_test \
  uv run python scripts/learned.py d4-integrity \
  --rehash-blobs --data-root /home/palkouser/projekt/cognitive-os-data
```

**A `warning` class is not a pass.** `artifact_bytes` warns when no store was opened;
`isolation` warns when no data root was given to re-take the predecessor fingerprints. Neither
means clean. The offline form reports 9 clean, 2 warnings and 1 not opened; the full form reports
11 clean and 1 not opened, and only the second is a statement about the store.

`not_opened` is not a soft pass either. `lifecycle` is `not_opened` because the pre-final
checkpoint says so by hash, and it becomes `failed` the moment that record claims otherwise.

The twelfth class is `decision_independence`. It scans every committed file for a rate taken
over the counted decisions rather than the distinct ones, for a census that does not add up, and
for a record claiming more distinct decisions than it counted. It also fails when it finds
*nothing* to scan — a denominator check over zero denominators is worth nothing.

The environment boundary is checked on the values before anything is opened, over five
predecessor roots. `artifacts` and `artifacts-s21d3` differ by a suffix; the first is the
development store and the second is the previous sprint's.

### One fence for every path that truncates

Eleven paths in this repository issue a `TRUNCATE` against the `cognitive_os` schema. All eleven
call `infrastructure.postgres.truncation.require_nominated_for_truncation`, and none of them
accepts "the database name ends in `_test`" as consent — every sprint's *evidence* database ends
in `_test` too.

```bash
COGOS_TRUNCATABLE_DATABASE=<the scratch database you mean> \
  uv run python scripts/learned.py smoke --confirm-isolated
```

Nominate the database you actually mean. Nominating one and connecting to another is refused
loudly, because the next statement would have been a `TRUNCATE`. Nominating nothing skips rather
than fails, so a whole-repository run cannot erase a store it was never pointed at on purpose.

Three of those eleven are scale baselines and one of them truncates `events`, `artifacts` and
`artifact_blobs` — the append-only store itself. Treat every scale baseline as destructive.

### The two W7 commands, and the one that takes no environment

```bash
set -a && . ./.env.s21d4.local && set +a
UV_CACHE_DIR=.cache/uv uv run python scripts/operations_d4.py
```

Provisioning, backup, container restart, restore into the D4 restore database, and 22 damage
cases. It writes to the backup root, the restore database and a scratch directory, and to
nothing else; every predecessor fingerprint is taken before and after.

```bash
UV_CACHE_DIR=.cache/uv uv run python scripts/verification_matrix_d4.py
```

**Deliberately no sourced environment.** Every row that needs a database names one itself. A
release matrix run with an evidence environment exported puts that evidence database in front of
whatever its rows run, which is how a full-suite row came to truncate one.

### What D4 did not do, and does not claim

D4 fitted no artifact. S21D4-039 selected no candidate, so nothing was loaded, sequenced,
registered, verified or activated against a real model, and no D4 surface below the selection is
described here as exercised. The rollback and refusal paths were proved on the isolated lifecycle
fixture with the abstaining reference component, which is what S21D4-075 asks for and all it
claims.
