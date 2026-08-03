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
