# Trust boundaries

| Zone | Contents | Trust level |
| --- | --- | --- |
| A | Cognitive OS core, configuration, event store access, providers, verifiers | Trusted core |
| B | PostgreSQL, OpenTelemetry Collector, optional local model server | Trusted local services |
| C | Generated code, shell/build/test execution, foreign repositories | Untrusted execution |
| D | MiniMax, Claude Code, and future external providers | External |

Zone C must not write directly to Zone A or B state. Access crosses an explicit,
schema-validated and audited tool or application boundary. Zone D never owns exclusive
durable state and receives only policy-approved, redacted context. Secrets stay outside
Git and outside untrusted execution environments.
