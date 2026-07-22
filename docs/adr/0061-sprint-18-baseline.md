# ADR 0061: Sprint 18 baseline and inventory

## Status

Accepted for Sprint 18.

## Decision

Sprint 18 starts from `sprint-17-baseline` at
`e8ca551dc9697886a935687265073bd402efe06c`, with Alembic head `0009`. The reconstructed preflight
inventory is generated at `artifacts/sprint-18/preflight/repository-inventory.json`; its SHA-256 is
`b33d5fe5db7b20ac5df51536821e3295a58b40393559d9879fd056eb341744bc`.

## Alternatives

Using a moving branch or an unverified local database was rejected because neither gives a
reproducible authority boundary.

## Consequences

Migration, backup, and closure evidence can name one exact parent. The inventory contains hashes,
not credentials or runtime data.

## Rollback and migration impact

Rollback returns to the named tag and migration `0009`. This decision grants no source-write,
execution, approval, or promotion authority.
