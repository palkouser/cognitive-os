# ADR 0043: Agent Skills interchange

## Status

Accepted for Sprint 12.

## Decision

Cognitive OS accepts a bounded Agent Skills-compatible package containing `SKILL.md`,
`metadata.yaml`, and optional `resources/`, `templates/`, `scripts/`, and `tests/` directories.
Compatibility is an interchange boundary, not runtime authority.

Directory and ZIP imports reject absolute or parent paths, links, devices, hard links, `.git`
metadata, Unicode and case collisions, duplicate YAML keys, unknown metadata fields, archive bombs,
oversized content, and secret-bearing text. ZIP content is inspected and loaded without extraction.
Scripts are stored as package data and never executed directly. Deterministic exports preserve the
validated file bytes and report the canonical package hash.

Internal scope, lifecycle, promotion, access, registry, execution, and statistics fields are not
trusted from interchange metadata. Imports always create drafts and must pass host verifiers before
promotion.

## Consequences and verification

Round-trip tests compare file bytes and package hashes. Eight repository seed packages use the same
format and validation path. Network package downloads, model downloads, automatic generation, and
automatic promotion remain disabled.
