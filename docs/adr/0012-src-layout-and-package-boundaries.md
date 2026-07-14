# ADR 0012: src layout and package boundaries

- Status: Accepted
- Date: 2026-07-14

## Context

Automatic flat-layout discovery made editable installation fail and risked packaging donor,
runtime, documentation, and private workspace directories.

## Decision

Cognitive OS-owned Python code uses `src/cognitive_os`. Setuptools discovery is explicit and
includes only `cognitive_os*`. The upstream `LightAgent` directory remains at its pinned
repository location and is not included in the Cognitive OS distribution during Sprint 1.

LightAgent compatibility is tested from the repository checkout. New integration code must
approach the donor runtime through `cognitive_os.runtime`; future wrapping must not create
reverse imports from LightAgent into Cognitive OS.

## Consequences

Editable and wheel installations exercise an unambiguous Cognitive OS package. A standalone
Cognitive OS wheel does not contain LightAgent; consumers of the donor runtime use the
repository checkout until a later packaging decision explicitly changes that boundary.
