# Dependency audit baseline

- Initial audit: 2026-07-13
- Remediation audit: 2026-07-14
- Command: `uv run pip-audit`

## Remediated findings

| Package | Old version | New version | Advisories resolved | Regression |
| --- | --- | --- | --- | --- |
| mcp | 1.10.1 | 1.23.0 | PYSEC-2026-1617 | 68 tests passed |
| requests | 2.32.3 | 2.33.0 | PYSEC-2026-1872, PYSEC-2026-2275 | 68 tests passed |

PYSEC-2026-1617 is a high-severity DNS-rebinding issue affecting unauthenticated local
HTTP MCP servers. MCP 1.23.0 enables the relevant protection by default for localhost.

## Remaining upstream findings

The final audit reports four advisories in one mandatory upstream dependency:

| Package | Version | Advisory | Stable fixed version reported |
| --- | --- | --- | --- |
| mem0ai | 0.1.70 | PYSEC-2026-2635 | none |
| mem0ai | 0.1.70 | PYSEC-2026-2634 | none |
| mem0ai | 0.1.70 | PYSEC-2026-2633 | none |
| mem0ai | 0.1.70 | PYSEC-2026-2636 | none; pip-audit lists only 2.0.0b2 |

## Disposition

Legacy memory is not enabled as a Cognitive OS baseline capability. Sprint 1 must remove
`mem0ai` from the mandatory core dependency set, isolate it behind an opt-in feature, and
re-audit before any use. Installing a beta major version during Sprint 0 would be an
unreviewed runtime migration and is therefore rejected.
