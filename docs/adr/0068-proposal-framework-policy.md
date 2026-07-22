# ADR 0068: External proposal framework policy

## Status

Accepted for Sprint 18.

## Decision

EvoAgentX, GEPA, and DSPy are conceptual pattern donors only. Sprint 18 adds no dependency, copied
source, model download, optimizer runtime, provider credential, or external authority.

## Alternatives

Embedding an evolution framework, using a donor as a second controller, and adopting a database or
optimizer for speculative flexibility were rejected.

## Consequences

The implementation reuses existing Pydantic, SQLAlchemy, Alembic, asyncpg, pytest, and Hypothesis
surfaces. `uv.lock` remains unchanged.

## Rollback and migration impact

There is no donor dependency to remove and no donor migration to reverse. Future source reuse
requires an exact commit, license, provenance, notice, dependency review, and a separate ADR.
