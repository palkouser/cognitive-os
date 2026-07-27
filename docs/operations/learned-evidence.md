# Durable learned evidence

Sprint 21C1 gives the learning substrate a memory. Every lifecycle step, every piece of
evidence, every intake decision and every activation now survives the process that made
it, and can be replayed and verified afterwards.

**It does not make the system learn anything.** No component is trained, no component is
active in any shipped configuration, and no measurement in this sprint claims that a
learned component would perform better than the deterministic path it sits beside. Gate
C1 asks whether learned evidence is durable, replayable, auditable and safe. Gate L2 —
whether the system learns anything useful — remains closed and is untouched by everything
described here.

## Architecture and authority

| Concern | Authority |
|---|---|
| Artifact bytes | the existing Artifact Store and `artifacts` table |
| Learned lifecycle history | append-only `learned_component_revisions` |
| Current component state | `learned_components`, rebuilt from that history |
| Learned domain invariants | `cognitive_os.domain.learned_evidence` contracts |
| Cross-subsystem audit | the existing Event Store |
| Runtime activation lookup | the durable projection, through the learned service |

The consequence that matters day to day: **the Event Store is not a second authority over
learned state.** A missing correlated event is a *warning*, because the append-only
history is still complete and replayable. A projection row without lifecycle history is a
*failure*, because the authority itself is gone. `learned health` reports the two in
separate fields, and never lets the first make the store unhealthy — collapsing them
would make an Event Store outage look identical to learned-state corruption, and the
alarm that matters would be the one nobody trusted.

Nine tables live under the `cognitive_os` schema: one derived projection and eight
append-only ledgers. Every ledger rejects `UPDATE` and `DELETE` through a trigger, against
the owner as well as the application role. `cogos_app` holds `SELECT` and `EXECUTE` on the
controlled functions and nothing else, so an application-role bug cannot rewrite evidence
even if it writes the SQL itself.

See [ADR 0086](../adr/0086-learned-evidence-persistence-authority.md) for the reasoning,
including the one recorded schema deviation from the Sprint 21C1 backlog.

## Configuration

Copy `config/learned.example.yaml` and change nothing to keep the shipped behaviour:

```yaml
learned:
  persistence_enabled: true
  activation_enabled: false
  activation_actors: []
  active_components: []
  quarantine_reviewers: []
```

Persistence is on because recording what happened is never the risk. Activation is off,
nobody is authorised to activate, and no component is active.

**There is no default active component, on any surface.** That is asserted by tests and by
a benchmark case, not merely intended. Enabling `activation_enabled` without naming an
`activation_actors` entry is refused by the loader rather than accepted as a no-op, so the
configuration cannot drift into a state where adding one name silently activates something.

Four settings are permanently false in Sprint 21C1 and the loader refuses to start if any
is true. They exist as named options so that the refusal is explicit:

- `artifact_deserialisation_enabled` — an artifact is data; loading one would make every
  lineage record an execution surface;
- `model_approval_enabled` and `model_review_enabled` — a component that can approve or
  clear its own evidence is not governed;
- `real_run_training_enabled` — real governed runs are evaluation-only, and training on
  them would contaminate the only uncontaminated corpus the system has to measure against.

### Database and Artifact Store

The learned store uses the same PostgreSQL database and the same content-addressed
Artifact Store as the rest of the system. Connection details live only in
`.env.postgres.local`, never inline in a shell history:

```bash
# .env.postgres.local, chmod 0600, gitignored
COGOS_POSTGRES_APP_USER=cogos_app
COGOS_POSTGRES_APP_PASSWORD=...        # generated, never a literal in any document
COGOS_POSTGRES_DATABASE=cognitive_os
COGOS_DATABASE_URL=postgresql+asyncpg://...
COGOS_DATABASE_ADMIN_URL=postgresql+asyncpg://...
COGOS_ARTIFACT_ROOT=/var/lib/cognitive-os/artifacts
```

Load it through the shared helper rather than exporting the variables by hand:

```bash
COGOS_POSTGRES_ENV_FILE="$PWD/.env.postgres.local" uv run python scripts/learned.py health
```

No command in this document prints a credential, and no example above contains one.
Migration `0014` is required; `learned health` fails if the head is not `0014`.

Learned lineage **references** artifacts and never copies bytes, so deduplication, backup
coverage and the restore verifier keep working unchanged, and there is no second copy that
can drift from the first.

## Operating

All commands print one line of sorted JSON. Exit status is `0` healthy, `1` unhealthy or
verification failed, `2` invalid usage, `3` not found.

```bash
uv run python scripts/learned.py health
uv run python scripts/learned.py replay-verify
uv run python scripts/learned.py artifact-verify
uv run python scripts/learned.py component-show --component-id COMPONENT
uv run python scripts/learned.py component-history --component-id COMPONENT
uv run python scripts/learned.py evidence-verify --component-id COMPONENT
uv run python scripts/learned.py observation-list --status accepted
uv run python scripts/learned.py observation-quarantine
```

Activation, approval and rollback have no CLI command. They require evidence a command
line cannot supply, and putting them behind a convenient flag is how a governance control
becomes a formality. They are reachable only through the application service, which checks
that evidence.

### Health

`health` runs twelve checks and reports two separate lists. `integrity_failures` makes the
store unhealthy; `correlation_warnings` never does. It re-reads nothing large: bulk
artifact re-hashing lives in `artifact-verify`, because a health check expensive enough to
be skipped is worse than a cheap one that is not.

`correlation_checked: false` means no Event Store was supplied, and is reported as
unchecked rather than as clean.

### Replay

`replay-verify` rebuilds every projection from append-only history and compares. It
mutates nothing, so it is safe against a live database. If replay and the projection
disagree, **the projection is wrong by definition** — that is the operational meaning of
"history is the authority".

### Recovering from a correlation warning

A correlation warning means a learned write committed but its audit event did not land.
The learned ledger is complete and authoritative; only the audit stream is behind.

1. confirm the learned side is intact: `replay-verify` should report
   `projection_matches: true` and no failures;
2. check the Event Store's own health;
3. once it is available again, the next learned operation on that component appends
   normally. Retry is idempotent — an event is matched by event type and content hash on
   the subject's stream, so re-running an operation does not duplicate it.

Do **not** back-fill a missing audit event by hand. It would carry the timestamp of the
repair rather than of the decision, which is worse than the gap.

## Observations and quarantine

Governed outcomes enter as *observations*, classified with a stable reason code:

| Status | Meaning |
|---|---|
| `accepted` | usable as evaluation evidence |
| `quarantined` | something is ambiguous and a human must decide |
| `rejected` | unusable, and recorded so the refusal is auditable |

An accepted observation is **not** a dataset example. Selection into a dataset is a
separate immutable manifest, so accepting an outcome never silently enrols it in training.
A real governed run that is accepted is evaluation-eligible and never training-eligible.

Quarantine review appends a *replacement* record and leaves the original in place, so the
queue stays a history of what was once uncertain rather than a list of what nobody got
around to. Review requires a named human operator in `quarantine_reviewers` and a reason;
it cannot grant usage rights nobody verified.

Listings return identity, classification and hashes. They never return an example body —
the observation record holds none — and a read that includes anything labelled `internal`
or `restricted` appends an access record naming who looked and why.

## Artifacts

Lineage is recorded only after the referenced bytes are re-read and confirmed to hash to
what the Artifact Store records. Corruption, absence and a size mismatch are all refused,
and a lineage that cannot be verified cannot support an activation or a rollback.

**No artifact is ever deserialised.** `LearnedArtifactFormat.JOBLIB` remains in the enum as
a descriptive legacy value; the learned Artifact Store adapter has no `load`, `open` or
`deserialise` method, and a test asserts their absence. Verification reads bytes and
hashes them; it does not interpret them.

## Backup and restore

Learned evidence is covered by the existing event-store backup. The manifest carries
learned table counts and a content-hash roll-up, and restore verification compares both,
plus four structural checks: no projection row without history, at most one active
component per surface, every activation naming an approval that exists with the same hash,
and every lineage row backed by an artifact row.

```bash
./scripts/backup_event_store.sh
./scripts/restore_event_store.sh --test-restore
```

Missing artifact content is reported, not ignored: the restore refuses with
`artifact metadata references a missing regular file`.

See [event-store-backup.md](event-store-backup.md) and
[event-store-restore.md](event-store-restore.md) for the shared procedure.

## Isolated environments only

Two commands write, and both refuse a database whose name does not end in `_test`:

```bash
uv run python scripts/learned.py smoke --confirm-isolated
COGOS_POSTGRES_ENV_FILE="$PWD/.env.s21c1.local" ./scripts/learned_restart_smoke.sh
```

`smoke` drives the inert reference component through its whole governed lifecycle. The
component abstains unconditionally, so it cannot change a decision even if something did
activate it, and it is never packaged as a default. `learned_restart_smoke.sh` additionally
migrates, restarts the database, backs up and restores, and compares replay across both
boundaries.

Point `COGOS_POSTGRES_ENV_FILE` at an isolated environment file. Exporting the variables
directly is not enough — the shared loader re-reads its own file and will override them,
which is deliberate: it is what stops a mis-scoped command reaching a real database.

## What Sprint 21C1 does not claim

Passing every check in this document says the learned store is durable, replayable,
auditable and safe to operate. It says nothing about whether a learned component would
help. Still missing for Gate L2: enough real governed outcomes to evaluate against, a
trained candidate with reproducible artifacts, material uplift over the deterministic
ladder, acceptable out-of-distribution behaviour, no catastrophic forgetting, safe shadow
performance, and an explicit authorisation to activate something that is actually useful.
