# Governed Strategy Evolution Graph

Sprint 13 adds strategic memory above verified Sprint 12 skills. A strategy is an immutable,
manually authored coordination revision: applicability conditions, phases, deterministic branches,
exact or governed skill bindings, static model roles, Context profiles, budgets, repair rules, stop
conditions, and typed lineage edges. It is not executable code and cannot grant permissions.

PostgreSQL migration `0005` owns strategy identities, revisions, edges, selections, outcomes,
statistics projections, and access audits. The event store records bounded lifecycle evidence, and
the artifact store holds verifier, comparison, graph, plan, and outcome reports. External nodes such
as skills, tools, verifiers, Context Bundles, task runs, and semantic claims remain owned by their
existing subsystems; graph edges contain only exact references and hashes.

Selection is provider-independent. The host filters status, exact scope, sensitivity,
applicability, required capabilities, permissions, graph validity, and unsafe history. Measured
candidates use the fixed `strategy-ranking-v1` profile. Sparse candidates follow an explicit
cold-start policy and require operator approval. Canonical name and exact revision are the final
tie-break. Registry, evaluator, ranking, skill, tool, verifier, provider, Context, and statistics
snapshots make the decision replayable.

Plan instantiation maps each strategy phase to one existing `ExecutionPlan` step. Effective limits
are the minimum of host, Controller, strategy, phase, and skill budgets. The existing Controller is
the only runtime state machine and retains tool, provider, approval, verifier, cancellation,
continuation, and acceptance authority. Strategy fallback is static, exact-revision, bounded, and
cycle checked.

Verified strategies are available to the Context Builder as the `strategy` source type. Metadata,
summary, selective lineage, and full declarative content hydrate progressively with exact revision
provenance and access auditing. Strategy data is rendered in the existing retrieved-data trust
boundary and never becomes a system instruction. A strategy does not duplicate `SKILL.md`
instructions.

NetworkX remains an optional, lazy analytical projection for comparison. PostgreSQL records and
the dependency-light core traversal are authoritative. Sprint 13 does not generate or promote
strategies automatically, learn rankings, adapt routing, add a graph database, or implement the
Sprint 14 Experience Compiler.
