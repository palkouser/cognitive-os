# ADR-0006: Project storage layout

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

Source, runtime data, caches, and archives have different lifecycle and security needs.

## Decision

Store source at `/home/palkouser/projekt/cognitive-os`, active data in the sibling
`cognitive-os-data`, cache in `cognitive-os-cache`, and archival data on the 4 TB HDD.

## Alternatives considered

Keeping all data in the repository or placing active databases on the HDD.

## Consequences

Git stays clean and active data stays on NVMe; deployment must configure explicit paths.

## Verification

Check filesystem locations, permissions, ignore rules, free-space reserve, and archive
mount availability.

## References

`.env.example`
