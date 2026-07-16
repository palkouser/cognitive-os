# Context Builder architecture

Sprint 11 adds one host-controlled pipeline between Controller provider actions and
`ModelExecutionService`:

```text
ContextRequest -> deterministic query plan -> source retrievers -> exact deduplication
  -> weighted RRF -> policy and safety filters -> diversity and budget selection
  -> progressive hydration -> trust-separated sections -> verified ContextBundleRevision
  -> typed ModelProviderRequest reference
```

Authoritative task, event, artifact, Memory Plane, semantic, repository, and workspace systems are
read through existing ports. The Context Builder does not own another database and cannot write
memory or claims. Requests, traces, bundles, and rendered context are immutable artifacts; minimal
events preserve lifecycle references.

The frozen registry supports task state, execution plan, recent events, provider results, tool
results, artifacts, governed memory and user corrections, bitemporal semantic claims, bounded exact
relations, Wiki revisions, repository indexes, and active coding workspaces. Retrieval is read-only,
bounded, cancellable, and separated from body hydration. Memory and semantic adapters preserve the
existing access audit.

Provider actions build and validate a bundle, immediately revalidate mutable source snapshots, and
only then construct a request. Retrieved text is an ordinary named user/data message, never a
system instruction. `ModelExecutionService` rejects a typed bundle reference when its validator is
missing, invalid, or stale.

Recovery reloads content-addressed artifacts, verifies hashes and source snapshots, and reuses only
an immutable valid bundle. A changed task stream, plan, repository, or workspace forces a new bundle
revision. Missing required context, unsafe required content, cancellation, or a budget overflow
prevents the provider call.

See [ADR 0038](../adr/0038-context-builder-authority.md),
[hybrid retrieval](hybrid-retrieval.md), and [Context Bundle](context-bundle.md).
