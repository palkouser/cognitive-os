# Deterministic task signatures

`TaskSignature` records bounded categorical requirements: domain, problem class, output type,
repository profile, complexity, required tools and structured output, Context-size class, risk,
verifier, latency and cost classes, exact strategy and skill revisions, and execution role.

Prompt text, instruction content, credentials, and secrets are not signature fields. Sets are
canonically sorted before hashing. Cohort lookup follows one fixed chain: exact signature, signature
without exact skill revisions, problem class plus output plus repository profile, domain plus output
plus risk, domain, then global. Each broader fallback increases uncertainty and cannot cross a
prohibited risk boundary.
