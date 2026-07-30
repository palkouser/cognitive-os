# Running the reality-input campaign

`scripts/reality_inputs.py` is the one entry point. Everything below is non-interactive after
the setup in [provider configuration](provider-configuration.md) and
[the local embedding model](local-embedding-model.md); nothing prompts.

```bash
set -a && . ./.env.s21c3.local && set +a      # the isolated C3 pair, never the development one
scripts/reality_inputs.py validate            # offline: no store, no network, no credentials
```

## Subcommands

| Command | Needs | What it does |
| ------- | ----- | ------------ |
| `validate` | nothing | Regenerates all thirty tasks, rebuilds the retrieval benchmark, scans every query for control tokens. The command to run first. |
| `generate --root <abs>` | nothing | Writes task packages: `workspace/` for the candidate, `control/` beside it and never inside it. |
| `stats` | `COGOS_DATABASE_URL` | Row counts read back out of the store. |
| `harvest` | `COGOS_DATABASE_URL` | Recorded observations by provenance and status. |
| `verify [--model <abs>]` | `COGOS_DATABASE_URL` | The unified integrity report — see below. |
| `run -- …` | store | The offline campaign; forwarded to `scripts/reality_campaign.py`. |
| `resume -- --resume-from <file>` | store | The same, skipping every run identity the Event Store already has an outcome for. |
| `embed -- …` | store, model | The retrieval benchmark; forwarded to `scripts/retrieval_benchmark.py`. |
| `provider -- … --live` | store, provider config | Live provider work; forwarded to `scripts/reality_provider_campaign.py`. |

Everything after `--` goes to the delegated script unchanged. The delegated scripts keep their
own flags; this CLI does not re-declare them, because two argument surfaces drift and the first
symptom is a flag that is silently dropped.

**Exit codes.** `0` did what it says. `1` ran and something it checked failed — evidence is
still written. `2` refused before doing anything: a missing opt-in, a relative path, an
environment with no isolated handles.

**Receipts** are JSON on stdout. They name the database, never the URL that authenticates to
it, so a receipt is safe to paste into a ticket.

## Reading `verify`

Two severities, and the distinction is the whole point of the report.

* A **failure** means recorded evidence is wrong: an artifact row with no bytes, a corpus item
  citing a source that is gone, a repository group in two splits, an accepted real governed run
  that is not evaluation-only. `healthy` is false and the exit code is 1.
* A **warning** means a capability is unavailable *right now* — most often that this host has
  never fetched the local embedding model. `healthy` stays true and the exit code is 0.

Collapsing the two would be expensive in both directions: a missing model would condemn a
store that is perfectly intact, and — worse — an operator who learned that this report goes
amber for ordinary reasons would stop reading it on the day it means something.

## Backup, restore, restart, resume

The existing commands cover the C3 evidence; no C3-specific backup path exists, and no table
was added for one.

```bash
COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21c3.local ./scripts/backup_event_store.sh
COGOS_POSTGRES_ENV_FILE=$PWD/.env.s21c3.local ./scripts/restore_event_store.sh --test-restore
```

`--test-restore` restores into a *separate* database and artifact root and then verifies
counts, history hashes and every artifact byte against the backup manifest. Missing or altered
bytes fail it; that refusal is asserted in `tests/cognitive_os/coding/test_reality_operations.py`
rather than trusted.

**Resume is safe and is the default.** `RealityCampaignLedger` reconstructs which run
identities already have a recorded outcome from the Event Store, and skips them, so re-running
after a crash costs containers rather than duplicate outcomes. A resumed run reports
`replayed_runs` — the number it skipped — and `duplicates_excluded`, which must stay zero.

**Restarting PostgreSQL changes nothing.** Counts, integrity checks and retrieval rankings are
identical across a restart; that is what `verify` and `embed` are for after one.

## Two stores, and why they are never the same one

The C3 pair holds **evidence**. A second database and artifact root exist to be **erased**:

```
COGOS_DATABASE_URL / COGOS_ARTIFACT_ROOT                     evidence — never handed to a test
COGOS_INTEGRATION_DATABASE_URL / COGOS_INTEGRATION_DATABASE_ADMIN_URL   scratch — truncated freely
```

`tests/integration/postgres` truncates every table in the `cognitive_os` schema, and several
unit suites write into whatever `COGOS_DATABASE_URL` and `COGOS_ARTIFACT_ROOT` name. Its
fixture used to guard only on the database name ending in `_test` — which the evidence store
also does — and that was enough to destroy a campaign when the release matrix was pointed at
it. The guard is now consent, not convention:

* `COGOS_TRUNCATABLE_DATABASE` must name the connected database, or the fixture refuses;
* with nothing nominated, the PostgreSQL tests **skip** with that reason, so a whole-repository
  run cannot erase a store it was never deliberately pointed at;
* `scripts/verification_matrix.py` gives every test row the scratch handles and refuses to run
  at all if the scratch handle names the evidence database.

Create the scratch database once:

```bash
psql "$COGOS_DATABASE_BOOTSTRAP_URL" -c 'CREATE DATABASE cognitive_os_s21c3_integration_test'
COGOS_DATABASE_ADMIN_URL=<that database> alembic -c infra/postgres/alembic.ini upgrade head
```

## The release matrix

```bash
scripts/verification_matrix.py --output docs/sprints/sprint-21/evidence/…-matrix.json
```

Runs every release command in one pass and records each one's exit code and duration. A
command whose prerequisite is absent is recorded as skipped *with the reason*: a row that is
simply missing cannot be told apart from a row that was quietly dropped after it failed.
Nothing is retried — a command that needed a second attempt is a finding, not a flake.

## What must never be committed

Credential values, the local model tree, task databases, artifact roots, runtime traces. The
model lives outside the working tree; `.env.s21c3.local` is untracked; receipts carry names,
not URLs.
