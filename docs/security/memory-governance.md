# Memory governance

The host configuration is the maximum authority. Provider input cannot increase write, query,
scope, sensitivity, embedding, or result budgets. Provider-only and automatic writes are denied
by default, and provider confidence is ignored for promotion. Secret-like content is rejected
before persistence and provider exposure.

Public, internal, confidential, and restricted sensitivity levels are monotonic. Lowering a
classification requires a trusted actor and a new revision. Default provider retrieval stops at
internal and excludes restricted memory. Scope resolution never widens task or repository scope.

Explicit conflicts in Sprint 9 are retracted or superseded source memory, an authoritative user
correction, a policy dispute, an explicit conflict link, or an invalid source. Similarity is not
contradiction detection and no LLM acts as conflict judge. Memory text is labeled and handled as
untrusted data; instruction-like content cannot authorize tools or change controller policy.
