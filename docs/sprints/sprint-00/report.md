# Sprint 0 report

Status: Locally complete – remote verification pending

## Sprint goal

Create a reproducible, documented, and safely usable development foundation without
implementing Cognitive OS runtime features.

## Environment

The source and active data use a dedicated NVMe with ample reserve. Python 3.12 is
operational. The 4 TB archive HDD is mounted persistently at `/home/palkouser/backup`; its
archive hierarchy, write test, source snapshot, and checksum validation are complete.
All Sprint 0 host tools, including GitHub CLI, are installed. The host NVIDIA driver is
healthy; the earlier NVML failure was isolated to the Codex sandbox. GitHub CLI
re-authentication remains the only manual action before remote publication. See
`docs/baseline/development-machine.md`.

## LightAgent baseline

Upstream tag v0.9.1 is pinned to commit
`8ea4db3c9d8791e0977eea2a4481824441b4ba82`. The remote tag was independently checked
before cloning.

## Completed elements

- Local upstream snapshot and thin-fork layout
- Source/data/cache separation
- Project instructions and Codex sandbox policy
- License, notice, donor policy, and provenance registry
- Project charter and trust-boundary model
- Initial ADR set
- VS Code, quality, smoke-test, CI, issue, and PR skeletons
- Machine baseline and baseline collection script
- Persistent archive hierarchy and verified source snapshot
- Audited translated README removals and immutable upstream links
- Sprint 1 editable-install and dependency carry-over
- Local `origin` configured for `palkouser/cognitive-os`; empty remote verified

## Test results

Python 3.12.13 and all upstream requirements are installed. Direct imports pass, and
`uv pip check` reports a compatible environment. Ruff, Ruff format, mypy, and Bandit
pass on Cognitive OS-owned code. All 68 collected repository tests pass, including the two
Cognitive OS offline import smoke tests. Dependency audit findings are documented under
`docs/security/dependency-audit-baseline.md`. MCP and Requests advisories were remediated
with regression-tested pins; four `mem0ai` advisories remain isolated as Sprint 1 work.

## Known issues

- GitHub CLI token is invalid and requires interactive re-authentication before push
- Upstream editable installation fails because its setuptools backend discovers multiple
  top-level flat-layout packages; the documented requirements fallback is in use
- GitHub repository is reachable but empty; manual push, metadata bootstrap, CI, tag, and
  release are pending

## Security status

Local secrets and runtime data are ignored. Codex defaults to workspace-write with network
disabled and secret-like environment variables excluded. No real API key is required for
Sprint 0 smoke tests.

## License status

Apache-2.0 is retained. NOTICE, third-party notices, donor policy, and the initial donor
registry are present.

## Sprint 1 carry-over

- Restore editable installation.
- Normalize Python package discovery and uv project metadata.
- Review and reduce mandatory upstream dependencies.
- Remove or isolate vulnerable legacy `mem0ai` support from the core installation.

## Restore point

The immutable source baseline is LightAgent v0.9.1 at the pinned commit. The final
`sprint-0-baseline` tag will be created only after all Definition of Done checks pass.
