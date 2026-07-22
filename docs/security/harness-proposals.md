# Harness Proposal Engine security model

The engine treats weakness evidence, repository content, provider output, and proposal artifacts as
untrusted input. Its authority boundary is fixed by [ADR 0063](../adr/0063-proposal-source-boundary.md),
[ADR 0064](../adr/0064-proposal-generation-boundary.md), and
[ADR 0065](../adr/0065-proposal-review-authority.md).

## Trust boundaries

- Weakness Mining is read-only and exact-revision resolution fails closed.
- Provider assistance is off by default and never owns sources, type, scope, operations, lifecycle,
  review, queue priority, or verifier results.
- Typed operations describe bounded future work; they are data and have no execution adapter.
- Review approval means only “eligible for a future isolated experiment.”
- PostgreSQL runtime roles use narrow functions; append-only tables reject updates and deletes.
- Artifacts are content-addressed and references are verified during backup and restore.

## Threats and controls

| Threat | Control |
| --- | --- |
| Prompt injection or executable patch text | disallowed-instruction verifier, typed operations, no executor |
| Path traversal or wildcard scope | relative wildcard-free scope validation |
| Stale weakness evidence | exact revision, queue, evidence, impact, and hash checks |
| Unsupported causal claim | hypothesis-only benefit contract and causal-claim verifier |
| Provider self-approval or scope expansion | actor validation, exact type/scope/citation checks |
| Automatic destination mutation | no destination port; no patch, shell, commit, or promotion path |
| Secret disclosure | bounded summaries, no credential reads, secret scan, artifact access audit |
| History tampering | append-only triggers, content hashes, compare-and-set revisions |
| Queue manipulation | deterministic key and explicit bounded operator priority |
| Confusing experiment approval with promotion | separate status and documented Sprint 19 authority |

High-risk surfaces do not gain permission from their risk tier. Verifier changes are tier 3 and
still remain proposals. A provider authority violation is rejected rather than converted into a
deterministic fallback. Availability failures may fall back because they add no provider content.

Known limitations: static text checks cannot prove semantic safety, source evidence may later
become historical, and a passing proposal verifier does not demonstrate real-world improvement.
Those questions belong to a future isolated experiment and separate promotion review.
