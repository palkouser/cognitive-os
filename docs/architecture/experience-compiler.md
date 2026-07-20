# Experience Compiler

Sprint 14 freezes a terminal task run into an immutable source snapshot and compiles it through a
fixed credential-free pipeline: resolve, validate, reconstruct, segment, assess, extract paths,
analyze corrections and contributions, assess generalizability, generate proposed candidates,
verify, decide, and manifest. Stage hashes and one idempotency key make replay deterministic.

Source systems remain authoritative. PostgreSQL stores bounded compilation metadata and append-only
history; the event store stores lifecycle evidence; the artifact store stores large source and
generated bodies. The compiler neither executes source artifacts nor calls destination services.
Provider-assisted proposals are optional, bounded, run after deterministic analysis, and cannot add
sources, assert causality, change candidate status, or write a destination.

Failure is explicit. Missing mandatory sources fail before reconstruction. Gaps and conflicts remain
visible. Cancellation retains completed immutable artifacts. Resume requires unchanged source,
profile, generator-registry, verifier-registry, and stage hashes.

Gate G remains partial: Sprint 15 must normalize, deduplicate, classify, license, quality-score,
stage, quarantine, reject, or route exported candidates.
