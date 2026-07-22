# ADR 0071: Controlled promotion and rollback

## Status

Accepted for Sprint 19.

## Decision

Tier 1 promotion calls an existing destination application service after exact, separate promotion
approval and destination verification. Tier 0 and Tier 2 produce an immutable operator-executable
repository bundle; runtime never merges it. Tier 3 has no automatic adapter and always requires
manual review unless rejected.

Rollback is validated before eligibility, targets the exact predecessor, records recovery time and
verification evidence, and preserves failed, promoted, and rolled-back history. Repository rollback
is instruction-only until an operator executes it through branch protection.

## Alternatives and consequences

Direct table updates, automatic promotion after assessment, and deletion of failed history were
rejected. Destination adapters remain small because existing lifecycle services retain authority.

## Verification

Tier 1 promotion/rollback, Tier 2 bundle, stale approval, concurrent approval, and Tier 3 denial
tests exercise the decision.
