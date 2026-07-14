# LightAgent test baseline

- Baseline: LightAgent v0.9.1
- Commit: `8ea4db3c9d8791e0977eea2a4481824441b4ba82`
- Python: 3.12.13
- Date: 2026-07-13

## Results

| Scope | Total | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Full repository suite | 68 | 68 | 0 | 0 |
| Cognitive OS import smoke subset | 2 | 2 | 0 | 0 |

No test required a real API key or provider network call. Test collection initially failed
because the upstream setuptools editable build is invalid for its flat repository layout.
Installing `requirements.txt` and adding the repository root to pytest's import path makes
the unmodified upstream package testable from the checkout.

## Reproduction

```bash
uv run pytest --collect-only -q
uv run pytest -q
uv run pytest tests/cognitive_os/smoke -q
```

## Sprint 1 follow-up

Repair packaging while preserving the thin-fork boundary, then add mock-provider, tool-call,
tool-error, iteration-limit, trace, LightFlow, checkpoint, and resume contract tests.
