# Cognitive OS project charter

## Purpose

Cognitive OS is a local-first, model-independent agent harness. It owns durable state,
memory, strategies, skills, verification, and evolution; language models remain
replaceable reasoning and execution providers.

## Runtime foundation

LightAgent v0.9.1 at commit `8ea4db3c9d8791e0977eea2a4481824441b4ba82`
provides the initial agent runtime. Cognitive OS uses a thin-fork strategy: owned code
lives in `src/cognitive_os/`, integrations use adapters and hooks, and upstream changes are
exceptional, isolated, tested, and documented.

## Sprint 0 boundary

Sprint 0 establishes a reproducible environment, repository governance, architecture
decisions, licensing and provenance, offline smoke tests, and a CI skeleton. It does not
implement memory, strategy evolution, provider routing, or self-improvement.

## Success criteria

- A Python 3.12 environment can be recreated without modifying system Python.
- The exact upstream source and dependency baseline are reproducible.
- Source, active data, cache, and archive storage have explicit ownership boundaries.
- No secret or runtime data is tracked by Git.
- Architectural decisions and donor provenance are auditable.
- Provider-free smoke and quality checks run locally and in CI.
