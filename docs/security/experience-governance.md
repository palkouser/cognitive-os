# Experience governance and security

All trajectory sources, artifacts, repository content, provider output, and candidate bodies are
untrusted. Source IDs must be logical, exact revisions and hashes are mandatory, source bytes are
never executed, and missing mandatory evidence fails closed. Scope and sensitivity can only stay the
same or become more restrictive. Candidate summaries reject credential-like content.

The deterministic compiler is credential-free, network-free, and GPU-independent. Optional provider
analysis receives bounded excerpts and exact evidence IDs through the existing provider layer.
Fabricated evidence, unsupported causality, secret requests, destination actions, candidate status
changes, and unbounded output are rejected.

The runtime role can select and append metadata and call controlled status functions. It cannot
update or delete history, alter schema, or write destination stores. Health checks are read-only.
Security gates require zero source mutations, fabricated evidence accepted, unsupported causal
claims, scope leaks, sensitivity leaks, automatic promotions, destination writes, and unexplained
access gaps.
