# ADR 0078: A real cross-domain capability gap is mined, proposed, and isolated-experimented

## Status

Accepted for Sprint 20.

## Decision

`src/cognitive_os/domains/weakness.py` and `src/cognitive_os/domains/improvement.py` close the last
Gate K condition 8 gap: weakness mining, proposal generation, and the controlled-change cycle. As with
gaps 1 and 2, the domain package contributes evidence and nothing else — the Weakness Mining Service,
the Harness Proposal Engine, and the Controlled Change Service each make every decision that belongs
to them.

### The weakness is real, not staged

`polynomial-equation` is a registered task class that accepts any real quadratic. Its solver is
exact-rational by design (ADR 0076): `x^2 - 2 = 0` is a legitimate input — nothing malformed, nothing
out of budget, nothing adversarial — that the plan admits and the solver then cannot answer. The
probes (`IRRATIONAL_ROOT_PROBES`) are three such honest witnesses. Each is run through the same
`run_case_controlled` governed path every other case uses; each genuinely fails there. Mining reads
back what those runs actually recorded — it does not assert a failure that did not happen.

`observe_probes` refuses to proceed if any probe stops failing: `is_capability_gap` requires both a
recorded `tool_call.failed` and a rejected acceptance decision. If the underlying gap is ever closed,
this raises `DomainWeaknessError` instead of silently reporting a stale weakness.

### Mining (S20-052)

`mine_domain_weaknesses` composes the unmodified `WeaknessMiningService` with a domain-scoped source
resolver and extractor. Each probe contributes two sources — its failed tool call and the acceptance
decision that owns the outcome — and `DomainCapabilityGapExtractor` emits one `WeaknessSignal` per
probe, classified `MISSING_SKILL` because the tool behaved exactly as specified and simply has no
answer for this input; classifying it as a tool or verifier failure would blame a component that did
nothing wrong. `CausalRelationshipType.OBSERVED_FAILURE` because the run recorded the failure
directly, not from correlation.

**Determinism.** `ProbeObservation.observation_hash` deliberately excludes each run's real event
payload hashes from the mined-signal identity. A payload carries a fresh acceptance `decision_id` and
wall clock on every execution; hashing it would make the same weakness mine to a different identity
every time, when a weakness is a property of the harness, not of one run. The hash instead covers the
case identity, the task class, the failure code, and the recorded control-flow shape. Per-run payload
hashes remain on the observation for audit, and every mined signal still cites its real
`task_run_id` — itself a `uuid5` derivation of the case, so it is stable across runs too.

Three probes group into exactly one weakness signature; `WeaknessMiningService` groups, scores, and
persists it unmodified.

### Confirmation and proposal (S20-053)

`confirm_domain_weakness` performs the `CANDIDATE -> CONFIRMED` transition explicitly, through the
real `transition_revision`, with a stated reason — mining alone never confirms. `propose_from_domain_
weakness` then calls `HarnessProposalService.create_from_weakness` with `provider_assisted=False`, so
nothing in the resulting proposal traces to model prose. The proposal type is `TOOL_DEFINITION_CHANGE`:
the fix the evidence supports is a change to `domains.solve`'s declared capability (decline an
irrational-root input at validation rather than fail at solve time), not new surd-arithmetic code,
which would widen the mandatory path's scope past what ADR 0076 declared. The Proposal Engine — not
this module — computes the minimality analysis, expected benefit, alternatives, risk assessment,
validation plan, and rollback plan from the frozen weakness snapshot.

### Controlled change (S20-054)

`run_isolated_experiment` requests an experiment, prepares isolation, captures a candidate, evaluates
it against `build_evaluation_matrix`'s own gates, and produces a `PromotionAssessment` — using the
unmodified `ControlledChangeService`. `TOOL_DEFINITION_CHANGE` is tier 3 in the existing
`ChangeSurfaceRegistry`, so `PromotionMode.MANUAL_REVIEW_ONLY` applies: the assessment decision is
`REQUIRES_MANUAL_REVIEW` with a stated approval requirement, and the cycle stops there. The isolation
manifest proves the active checkout is not touched — `baseline_commit` matches the protection
snapshot's `repository_commit`, the network policy is `disabled`, and exactly one file is in scope.

## Alternatives and consequences

Widening the solver to cover irrational roots (adding an algebraic-number type) was rejected as the
proposed fix: it would resolve this one probe but contradicts the sprint's declared scope — "exact
rational arithmetic only, irrational results raise rather than being approximated" — and a
mandatory-path scope change is exactly the kind of decision the Proposal Engine's risk assessment and
an operator's manual review exist to make, not something this module should decide for them.

Confirming the weakness automatically inside `mine_domain_weaknesses` was rejected: mining is
diagnostic only (`test_mining_is_deterministic_and_diagnostic_only` asserts no revision mentions a
proposal), and confirmation is an operator act with its own stated reason. Folding it into mining would
blur that boundary.

Promoting the assessed candidate automatically was never implemented and was not close to being
implemented: `TOOL_DEFINITION_CHANGE` is tier 3 by the registry's own classification, and this module
holds no promotion authority by design, matching ADR 0076's "no runtime release authority" stance.

## Verification

Mining: 3 signals from 3 independently-run probes group into 1 weakness signature; every signal cites
its own recorded `task_run_id`, carries non-shadow authoritative evidence and an outcome-authoritative
source, and running mining twice produces an identical manifest. Confirmation: an explicit
`CANDIDATE -> CONFIRMED` transition with `reproducible` reproduction status and a queue entry that
references the exact confirmed revision hash. Proposal: reaches `APPROVED_FOR_EXPERIMENT`, its change
specification names exactly one allowed file, and its snapshot's weakness content hash matches the
confirmed revision's. Experiment: isolation kind `declarative_copy`, network `disabled`, 15 evaluation
gates, 0 hard failures, and a `REQUIRES_MANUAL_REVIEW` decision with a stated approval requirement.
The full cycle is deterministic — two independent runs produce byte-identical experiment, isolation,
and assessment content hashes.

Three governance invariants — `weakness_from_recorded_failure`, `proposal_traces_to_weakness`,
`change_cannot_self_promote` — run in the seed benchmark manifest and as parametrised tests, bringing
the pilot's total to 28.

Fixed alongside this: `DomainActionExecutor.execute` let a `ToolPlaneError` from a failing tool
propagate past the Controller instead of returning a failed `ActionOutcome`, and the shared
`ControllerVerificationService._subject` built an invalid `VerificationSubject` when a step produced
no output. Both were found because this weakness's probes are the first cases in the pilot that
genuinely fail at the tool layer; every prior fixture either fully succeeded or was rejected only at
verification. See `docs/sprints/sprint-20/report.md` for the full account.
