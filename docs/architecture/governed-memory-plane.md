# Governed Memory Plane v1

Sprint 9 persists explicitly selected experience without autonomous learning. PostgreSQL is the
memory authority, the event store owns lifecycle audit evidence, and the artifact store owns
large content. Providers and LightAgent use application services and never import the PostgreSQL
adapter.

```text
events + artifacts + accepted evidence
                  │
                  v
source validation -> write policy -> typed revision -> PostgreSQL
                                             │              │
                                             v              v
                                      lifecycle event   exact retrieval
                                                            │
                                                            v
                                                    append-only access audit
```

Every durable revision has at least one typed source. Creation is candidate-first; verified
promotion requires accepted authoritative evidence and an explicit trusted policy. Content,
status, confidence, salience, sensitivity, or provenance changes create a new revision. Retraction,
expiry, and supersession preserve history.

Retrieval executes exactly one mode: metadata, PostgreSQL full text, or exact cosine vector.
There is no HNSW, IVFFlat, lexical/vector fusion, reranker, graph expansion, or Context Builder.
Memory text is untrusted data: it grants no tools, budget, policy, or execution authority.

Sprint 10 may add temporal observation claims and explicit evidence links without replacing the
Sprint 9 identity, revision, provenance, embedding, retrieval, or audit foundations.
