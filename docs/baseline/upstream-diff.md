# Upstream diff register

Baseline: LightAgent v0.9.1 at `8ea4db3c9d8791e0977eea2a4481824441b4ba82`.

## Sprint 0 changes to upstream-owned files

| File | Reason | Runtime impact |
| --- | --- | --- |
| `.gitignore` | Protect local environments, credentials, caches, and runtime data | None |
| `README.md` | Identify the thin fork and link ADR/provenance records | None |
| `.github/workflows/ci.yml` | Establish the Python 3.12 offline smoke and quality CI skeleton | CI only |
| `.github/pull_request_template.md` | Enforce issue, validation, provenance, and secret checks | Workflow only |
| Translated `README.*.md` files | Keep fork documentation focused; immutable upstream links retained | Documentation only |
| `requirements.txt`, `pyproject.toml` | Raise MCP to 1.23.0 and Requests to 2.33.0 to resolve three advisories | Dependency-only; 68-test regression passes |

No file under `LightAgent/` has been modified. The existing CI's Python 3.10–3.12 matrix
is intentionally replaced for Cognitive OS, whose development interpreter is pinned to
3.12. The workflow uses the documented requirements fallback because the upstream
editable setuptools build fails package discovery at this baseline.

The dependency changes are narrow security remediations. The remaining `mem0ai`
advisories have no stable, in-place upgrade at this baseline and are carried into Sprint 1
dependency minimization.
