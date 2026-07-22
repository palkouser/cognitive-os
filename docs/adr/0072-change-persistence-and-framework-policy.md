# ADR 0072: Controlled-change persistence and external framework policy

## Status

Accepted for Sprint 19.

## Decision

Migration `0011` adds 11 controlled-change tables, ten append-only histories, compare-and-set
experiment revisions, controlled record functions, least-privilege grants, access audit, backup,
restore, and health checks. Large patches, builds, logs, and restore packages remain in the existing
content-addressed Artifact Store. Downgrade removes Sprint 19 records and restores schema `0010`;
operators must back up Sprint 19 evidence before downgrade.

OpenEvolve, GEPA, and EvoAgentX are conceptual pattern donors only. The external-evolution adapter
is disabled and no donor dependency, source, model, credential, database, or authority enters the
runtime. Existing Pydantic, SQLAlchemy, Alembic, asyncpg, pytest, and Hypothesis are sufficient;
`uv.lock` remains unchanged.

## Alternatives and consequences

A generic optimizer database and new orchestration framework were rejected as duplicate authority
and unnecessary dependency surface.

## Verification

Migration round trip, grants, append-only triggers, schema drift, dependency audit, packaging,
backup, and isolated restore are release gates.
