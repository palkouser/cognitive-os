# Regression-gated controlled change management

Sprint 19 turns one exact approved proposal revision into an isolated candidate and immutable
promotion assessment. It does not grant Cognitive OS runtime authority to merge, tag, publish, or
release repository changes.

## Flow and ownership

1. `ApprovedProposalIntake` resolves the exact proposal, predecessor approval, verifier bundle, and
   artifacts through a read-only port.
2. `ChangeSurfaceRegistry` assigns one of four tiers, an isolation profile, verifier set, adapter,
   and promotion mode. Unknown surfaces fail closed.
3. `ChangeWorktreeIsolation` reuses the Coding Agent workspace boundary. Configuration, PostgreSQL,
   and artifact isolation use distinct identities and never reuse active credentials or namespaces.
4. A typed `ChangeImplementationPlan` contains exact preconditions and artifacts. Arbitrary shell
   text is not an operation.
5. Deterministic transformation, the existing Coding Agent, and bounded Claude Code advisory roles
   may produce immutable candidates. The external evolution boundary is disabled.
6. A baseline-owned `EvaluationMatrix` runs target and non-target evidence in fixed order.
7. `RegressionComparison` preserves raw case references and deterministic hard-failure codes.
8. `PromotionAssessment` keeps expected benefit separate from measured benefit.
9. A separate exact promotion review permits a Tier 1 destination call or Tier 0/2 bundle. Tier 3
   remains manual-only.
10. Rollback returns the exact predecessor and retains all history.

PostgreSQL owns identities, revisions, assessments, approvals, promotions, rollbacks, and accesses.
The event store owns lifecycle evidence; the Artifact Store owns large immutable bytes; source and
destination subsystems retain their own authority.
