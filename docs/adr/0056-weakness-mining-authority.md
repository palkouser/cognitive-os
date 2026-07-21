# ADR 0056: Weakness Mining authority

## Status

Accepted for Sprint 17.

## Decision

Authoritative source systems retain their existing records and never expose write authority to the
miner. PostgreSQL owns immutable mining metadata, signals, exact groups, weakness revisions, impact
scores, queue records, and access audits. The event store owns lifecycle evidence; the artifact
store owns referenced large evidence content.

```text
authoritative sources --exact revision/read--> source snapshot --> signals --> exact groups
                                                                    |              |
                                                                    v              v
event store <--lifecycle-- candidate revisions <-- evidence/impact --+          advisory clusters
                                  |
                                  +--> deterministic Weakness Queue
```

Exact groups and host-validated weakness revisions are authoritative. Optional clusters are
disposable comparison projections and cannot merge records, establish causality, change status, or
write to a source. Provider output is proposal-only. Backup preserves PostgreSQL and artifact
hashes; restore validates lineage and deterministic replay rebuilds projections without source
mutation.

## Rejected alternatives

Provider-authored diagnoses, automatic confirmation, direct source mutation, learned authoritative
ranking, an external graph database, and a second Controller are rejected.
