# ADR-0003: Python 3.12 and uv

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

Ubuntu 26.04 provides Python 3.14 while the selected runtime supports Python 3.10–3.12.

## Decision

Pin Python 3.12 and manage the isolated environment with uv. Never install project
packages into the operating-system Python.

## Alternatives considered

System Python, pyenv, Conda, and Poetry-managed environments.

## Consequences

The environment is reproducible but uv and the managed interpreter must be bootstrapped.

## Verification

`.venv/bin/python --version` reports 3.12 and `.python-version` is tracked.

## References

`.python-version`
