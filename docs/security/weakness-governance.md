# Weakness Mining governance

All repository, external, artifact, and provider content is untrusted. Source resolvers accept only
exact revisions in the requested scope and sensitivity boundary. Signals cannot cite material
outside the frozen snapshot. Provider-only and shadow-routing evidence cannot establish an outcome,
causality, confirmation, priority, or source write.

PostgreSQL grants the runtime role reads and narrowly scoped inserts. Append-only triggers reject
updates and deletes; controlled functions enforce mining-state, weakness-revision, and queue
transitions. Contracts reject unknown fields, non-finite impact values, incomplete evidence,
unbounded paths, proposal activation, illegal status transitions, and provider actors.

The core path performs no network access, model download, credential storage, source mutation,
automatic proposal, automatic confirmation, repair, execution, or promotion. Access records and
event envelopes expose hashes and identifiers, never secrets or raw prompts.
