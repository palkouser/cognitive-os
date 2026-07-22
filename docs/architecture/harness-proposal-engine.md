# Harness Proposal Engine

Sprint 18 adds a proposal-only bounded context over exact Sprint 17 Weakness Mining evidence. It
turns one eligible weakness revision into a deterministic, reviewable hypothesis for a future
isolated experiment. It cannot apply changes, edit a source subsystem, execute a patch or shell
command, approve itself, merge code, deploy, or promote an experiment.

The authority decisions are [ADR 0061](../adr/0061-sprint-18-baseline.md) through
[ADR 0068](../adr/0068-proposal-framework-policy.md).

## Flow and ownership

```text
Weakness Mining (read-only exact revision)
        |
        v
source snapshot -> deterministic proposal -> 22 verifiers -> immutable revision
                                                        |
                                                        v
                                  explicit review -> deterministic queue

PostgreSQL: identity, revisions, review, queue, access metadata
Artifact Store: source snapshots, proposal bodies, reports
Event Store: lifecycle evidence
Destination subsystems: no Sprint 18 write path
```

The public contracts are exported under `schemas/v1/proposals/`. They cover identity and revision,
typed artifact/configuration/repository-file operations, exact source snapshot, change
specification, expected benefit, minimality, risks, alternatives, validation, rollback, verifier
bundle, review, queue, statistics, access, and replay manifest.

## Types, lifecycle, and verification

The registry contains exactly 15 types: prompt template, context profile, retrieval policy, memory
policy, skill, strategy, routing policy, tool definition, verifier, workflow, retry policy,
benchmark, configuration, source code, and documentation change. Every type binds a template,
surface tier, typed operation, allowed target kind, validation sections, rollback sections, and all
22 mandatory verifier capabilities.

The legal lifecycle is `draft -> generated -> validated -> staged_for_review ->
approved_for_experiment`; rejection, supersession, and retraction are governed terminal branches.
Validated and later states require a passing verifier bundle. Approval names one exact revision
and authorizes only a future isolated experiment.

Generation is deterministic and credential-free by default. Optional provider prose is bounded to
host-selected sources and cannot alter type, scope, typed operations, authority, or verifier
results. Provider availability failure returns to the deterministic result; an authority violation
fails closed.

## Queue and persistence

The queue key is deterministic and operator priority is only one explicit input. Learned or
provider priority is absent. Exact active signatures are unique; related signatures are not merged.
Queue removal appends an inactive record.

Migration `0010` creates ten tables and controlled functions. Proposal revision, component, review,
queue, and access histories are append-only. Large content stays in the existing content-addressed
Artifact Store. See the [operations guide](../operations/harness-proposals.md),
[security model](../security/harness-proposals.md), and
[benchmark guide](../benchmarks/harness-proposals.md).

## Limitations and Sprint 19 hand-off

Expected benefit is a hypothesis, not a causal conclusion. Sprint 18 does not measure a candidate
effect. Sprint 19 may consume only an explicitly approved exact revision, its source snapshot,
verifier bundle, validation plan, rollback plan, and artifact hashes in an isolated experiment. It
must define separate promotion authority.
