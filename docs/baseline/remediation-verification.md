# Sprint 0 remediation verification

- Date: 2026-07-14
- Branch: `chore/sprint-0-remediation`
- Baseline: LightAgent v0.9.1 / `8ea4db3c9d8791e0977eea2a4481824441b4ba82`

## Passed

- Origin and upstream URLs are correct; the origin repository is reachable and empty.
- Python 3.12.13 environment is operational.
- A clean CI-like virtual environment can install the remediated requirements.
- Full repository suite: 68 passed.
- Cognitive OS smoke suite: 2 passed.
- Ruff check and formatting check pass.
- mypy passes.
- Bandit reports no findings in Cognitive OS-owned code.
- `uv pip check` reports a compatible environment.
- Detect-secrets baseline reviewed; no real credential found; baseline hook passes.
- Bash syntax validation passes for every project script.
- Git whitespace validation passes.
- Archive HDD mount, hierarchy, write/read test, snapshot, tar validation, and checksum pass.
- Host NVIDIA check passes: `nvidia-smi` exit 0, driver 595.71.05, RTX 5070 Ti detected.
- Git LFS, fd, tree, ShellCheck, smartmontools, nvme-cli, and tmux are installed and verified.
- GitHub CLI 2.96.0 is installed.
- ShellCheck passes for every script; `nvme list` detects both NVMe devices.
- Translated README removals and links are audited.
- MCP and Requests security upgrades pass a clean 68-test regression.

## Expected non-zero checks

- `pip-audit`: four `mem0ai` findings remain; no stable in-place fix is reported. Legacy
  memory is disabled and the dependency is scheduled for removal/isolation in Sprint 1.
- `gh auth status`: installed CLI, but the saved GitHub token is invalid.
- Sandboxed `nvidia-smi`: expected exit 9 because `/dev/nvidia*` is hidden; the authoritative
  unsandboxed host check passes.
- SMART device discovery succeeds outside the sandbox, but health reads require manual
  `sudo smartctl` execution.

## Remote checks pending

- First manual push
- GitHub metadata bootstrap
- GitHub Actions CI
- Closure commit, baseline tag, release, S0-14 closure, and milestone closure

The host remediation is locally complete. Remote publication remains blocked until the
machine owner completes GitHub CLI re-authentication.
