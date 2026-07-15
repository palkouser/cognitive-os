# LLM Wiki v3

LLM Wiki v3 is a deterministic Markdown projection, not an LLM-authored authority. The renderer
uses fixed sections in this order: current supported claims, disputed claims, open contradictions,
superseded history, evidence index, and revision metadata. It escapes Markdown and HTML control
characters and never calls a provider.

Each displayed claim records its exact claim ID, revision, belief, interval, confidence, evidence
count, and contradiction marker. `wiki_page_claims` persists section and display order; the page
snapshot hash covers exact claim lineage. Evidence entries retain source identities and hashes,
not source content. Wiki pages cannot be submitted as an independent semantic source type.

Current and as-of pages have explicit temporal parameters. Repeated byte-identical rendering is
idempotent. Changed claims, evidence, contradictions, or temporal parameters produce an append-only
page revision. Missing claim revisions or a hash mismatch fail closed and never mutate claims.
Restored pages can be verified or regenerated from authoritative semantic rows.
