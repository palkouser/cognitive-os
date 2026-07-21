# ADR 0057: Weakness signals and signatures

## Status

Accepted for Sprint 17.

## Decision

A signal requires exact source references, task identity, normalized failure code, component,
severity, confidence, observation time, and explicit causal limitation. Outcome claims require an
authoritative acceptance or routing-outcome record; provider and shadow records cannot supply that
authority.

`weakness-signature-v1` hashes the weakness type, normalized TaskSignature, registered failure
code, component identities, exact skill/strategy/provider/tool/verifier/routing references, risk,
and scope. It contains neither raw prompts nor provider prose. Unknown codes normalize to
`unknown`; they are not guessed.

For example, two `verifier_gap` signals with the same TaskSignature, verifier identity, scope, and
normalized code form one exact group even if observed at different times. Changing the verifier
identity creates a different signature and group. Stable weakness identity derives from the
signature; immutable group snapshots also bind the exact signal set and profile revision.

## Rejected alternatives

Free-text similarity as identity, raw-prompt hashing, provider classification as authority, and
mutable signatures are rejected.
