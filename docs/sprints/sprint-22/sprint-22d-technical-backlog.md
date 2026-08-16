# Sprint 22D Technical Backlog

## Bounded Local English, LLM-Dependence Reduction, and `sprint-22d-language-baseline`

- Predecessor: Sprint 22C. **Its release has not happened yet, and this plan says so rather
  than pretending otherwise.** W0 through W3 are complete on branch `sprint-22c-groundwork`
  at `426b92b57f4140775c12ba3d9ca5887c31a1af25`, exact-head CI run `31879596899`, 30 of 30;
  four of the five exit criteria are met on sealed evidence and the fifth — *at least one
  retained artifact improves a held-out verified task* — is a measured negative, arm A 0 of 4
  and arm B 0 of 4. W4 has not run, no tag exists, and nothing is merged to `main`, which
  still peels to 22B's `dc4006116ff2cfac3f7e581253dd5f549ba3ce52`. **W0 of this sprint blocks
  on 22C's release** exactly as 22C's W0 blocked on rights clearance: no predecessor tag, no
  verified starting state, no sprint.
- Objective and exit, from the
  [execution sprint allocation](execution-sprint-allocation.md), verbatim and moved by
  nobody: demonstrate **bounded technical English capability on local owned resources and
  reduce large-LLM use without reducing verified quality**. Exit: **no large external LLM is
  called during the local microbenchmark**; **local verified success is at least 70 % and at
  least 10 points above retrieval-only**; **large-LLM calls or equivalent cost fall at least
  25 % at non-inferior success**; **factual output is grounded or explicitly uncertain**;
  **prior domain, learning, and safety gates remain green**.
- Migration head: `0015`, unchanged by 22C — `infra/postgres/alembic/versions` still ends at
  `0015_create_provider_output_governance.py`, `EXPECTED_MIGRATION_REVISION` still reads
  `0015`, and every released-code repair 22C made needed no schema change.
  **`0016` stays a refusal by default.** A local model, a benchmark
  manifest and a routing decision are composition over released storage; a wave that finds
  itself needing a migration has found a finding.
- Outcome tag: `sprint-22d-language-baseline`. Negative outcome tag:
  `sprint-22d-evidence-baseline`, the D-series discipline carried.

**22C ended by measuring the exact wall this sprint has to stand on, and the plan is built
around that measurement rather than around the sentence in the allocation.** 22C's handoff
calls the acquired-knowledge store "Layer 1 of the local English roadmap". Layer 1 currently
contains **one artifact** — one worked example, from fifty-nine, across two rights-cleared
textbooks. Two of this sprint's five exits read against that layer. A plan that opened a local
model on top of it and hoped would be measuring an empty shelf, so §1.5 takes 22C's W3-F1
decision head-on and W1 spends itself on it. That is the asymmetry this sprint is scheduled
around, the way 22C was scheduled around its improvement exit and D4–D7 around Gate L2.

---

## 0. Authority and execution contract

Sections 0.1 through 0.4 of the
[Sprint 21D4 Technical Backlog](../sprint-21/sprint-21d4-technical-backlog.md) are 22D's
execution contract unchanged, incorporated by reference. The six rules 22C carried forward
stand. Six more graduate into standing rules here, each paid for once in 22C:

- **22C W1-D2** — *a program may check a licence and advise on it, and may never decide it*:
  classification and authorisation of any material — source text, model weights, adapter
  corpus — is an `OperatorLicenseClearance` with a named human, or the material is refused.
  The program may refuse on its own; it may never permit on its own;
- **22C W3-F1** — *a verification floor decides what can be acquired, and its coverage is
  priced before the campaign, not after*: any wave that intends to retain content states in
  advance which floor will verify it and samples the source against that floor;
- **22C W2-F2** — *two implementations of one contract are tested against each other, not
  each against itself*: any behaviour with an in-memory and a persistent implementation gets
  a parity assertion, because either alone looks reasonable;
- **22C W1-F5 / W2-F4** — *a pipeline may be stricter than a released primitive and never
  more permissive, and it may not invent a value for a released vocabulary*: a distinction
  the platform cannot express is kept in the sprint's own record and named as a finding;
- **22C W1-F1** — *a `--check` that re-derives a world observation cannot survive the world
  changing*: sealed records separate invariants (rebuilt) from observations (recorded and
  re-read);
- **22C W3-D1** — *a component that demands an input it does not use is a refusal with a
  name, never a value supplied to satisfy it*: this applies with force to a language model,
  which will always produce something.

---

## 1. Verified starting state

### 1.1 What 22C hands over by name

**Repaired and released in 22C:** the `MemoryService.create` crash window (record and event
in one transaction, resume repairs; the window is narrowed, not closed, and stays carried);
the post-restore HNSW reindex procedure (clustered recall back over the 0.95 floor); the
PostgreSQL semantic active view (W2-F2), which had been returning superseded and retracted
claims wearing their old belief; and the licence authority, where `OperatorLicenseClearance`
replaced a list that had been making legal determinations on its own.

**Measured, and this sprint's actual starting condition:**

| Reading | Value |
|---|---|
| worked examples located across two rights-cleared textbooks | 59 |
| retained artifacts in the acquired-knowledge store | **1** |
| refused because no registered problem type covers the passage | 53 |
| held-out tasks improved by a retained artifact | **0 of 4** |
| campaign cycles completed, nine stages each | 3 |
| replay rate on the one retained domain, three cycles | 1.0 / 1.0 / 1.0 |

**Carried by name, untouched here unless a wave says so:** 22C W3-A1 (the contradiction
demonstration on real content, which could not run because nothing was acquired to
contradict), 22C W2-A1 (`domain_pilot_runs` has no descriptor-domain path), 22C W2-F3 (the
Tool Plane's solve and verify events go to an in-memory store and are discarded), 22B W2-F2
(the planner answers a filtered ANN query with a sequential scan at 10^6), and the crash
window. **22C W2-F3 stops being cosmetic in this sprint**: the accounting exit needs a durable
record of what executed where, and a Tool Plane whose evidence evaporates cannot supply it.
W0 decides whether that is repaired here or the accounting is sourced elsewhere.

**Gates:** Gate L2 passes 29 of 29. Gate D1 conditions 6, 7 and 15 are closed; its usefulness
floor is what 22C measured and what exit two of this sprint reads against. Gate M is 22E's.

### 1.2 What exists, and what must be built

**Exists and is released — more than the allocation's wording suggests.** `ProviderKind`
already has `LOCAL_API`, so a locally hosted model is a released provider category and not a
new concept. `providers/openai_compatible.py` is a pure, network-free mapping between the
Cognitive OS request/response contracts and the OpenAI chat-completions shape, already shared
by two adapters — which is precisely the wire protocol every mainstream local inference server
speaks, so a local model plugs into the governed model path through an existing seam rather
than a new adapter. `domain/routing.py` carries model profiles with typed capability evidence,
including `DETERMINISTIC_BENCHMARK`, `OPT_IN_LIVE_BENCHMARK` and `OPERATOR_DECLARATION` — the
vocabulary an escalation policy needs to justify itself. `domain/benchmarks.py` carries
`BenchmarkManifest`, `BenchmarkCase`, `BenchmarkRun` and a resource budget with a
`maximum_provider_calls` field, which is where "no large external LLM is called" becomes a
budget rather than an inspection. The twelve fail-closed semantic promotion verifiers, the
`GroundedSourceSpan` contract and 22C's citation walker are the grounding substrate. The
governed teacher records a receipt, a rights decision and a retention directive for every
provider call, local or not.

**Must be built, all composition unless a gap proves otherwise:** the frozen 100-task English
technical microbenchmark and its manifest; the local runtime harness (model, quantization,
context, sampling, all pinned and hashed); the four baseline arms as one runner with one
verifier; the declarative-fact acquisition path of §1.5; the confidence-based escalation
policy as a pre-registered decision function, not a prompt instruction; and the
provider/local compute accounting record. Any of these that needs more than composition over
released primitives is a finding to surface, not to absorb.

**One released vocabulary already looks short.** `BenchmarkDomain` has nine members and none
of them is English or language; the honest first move is to declare the microbenchmark under
an existing member and record the mismatch, per the W2-F4 rule — not to add an enum member,
which is the exact shape 22A spent a sprint dissolving.

### 1.3 The hardware preflight, measured here rather than assumed

The allocation permits local-model hardware benchmarks to begin after a CPU/GPU preflight.
The host reads:

| | |
|---|---|
| CPU | AMD Ryzen 7 5700X, 8 cores / 16 threads |
| RAM | 45 GiB total, ~35 GiB available |
| GPU | NVIDIA GeForce RTX 5070 Ti, 16 GiB VRAM |
| Free disk | 634 GiB |

Two consequences, and they point in opposite directions:

- **The CPU-viable requirement is comfortably met.** A permissively licensed quantized model
  in the 7–8 B class runs on 16 threads with room to spare, and the exit asks for CPU
  viability specifically — a claim about *owned resources*, not about speed. The plan
  therefore treats CPU as the **measured configuration of record** and GPU as an accelerator
  whose numbers are reported separately, because a claim measured only on a GPU is not the
  claim the allocation asks for.
- **The GPU preflight passes, which makes the adapter question live rather than moot.** 16 GiB
  is enough for parameter-efficient fine-tuning of a model in that class. This plan
  nevertheless keeps the adapter **optional and outside every exit** (§2.3): the allocation
  words it as optional, no exit needs it, and a sprint that spends its schedule on adapter
  training while its grounding exit is unmet has chosen the interesting problem over the
  required one. It is reachable in W4 as surplus, with its own rights preflight, or not at
  all.

These numbers are a W0 sealed record, not this document's authority: a plan may name a host,
and only a measurement may bind one.

### 1.4 The two rights gates

**The model's licence.** "Permissively licensed" is not a determination this program may make
— 22C W1-D2 is now a standing rule. W0 surfaces the candidate model with its licence text
hashed, and the gate owner issues an `OperatorLicenseClearance` naming the permitted uses, or
there is no local model and the sprint is blocked at W0. The advisory lists may classify; they
may not authorise. A model whose licence restricts commercial use is still perfectly usable
under a clearance that permits internal use — the distinction the operator draws, recorded, is
the point.

**The corpus, if an adapter is ever attempted.** The allocation is explicit that no adapter
training may use an unapproved corpus. 22C's sealed rights record already clears both textbook
sources for `internal_use`, `derivative_work` and `benchmark_use`, and one of the two is
NC-SA — so an adapter trained on it is internal-only by construction and could never ship in
a released artifact. That constraint is recorded in W0 whether or not the adapter is
attempted, because it decides what the option would be worth.

**The microbenchmark's own content** is a third rights question hiding inside the first exit.
A hundred English technical tasks authored in-repository are ours; a hundred lifted from a
source are not. W0 freezes provenance for every task.

### 1.5 W3-F1's decision, taken — and why it belongs in this sprint

22C's central finding handed the gate owner a decision it explicitly refused to absorb: a
pipeline whose verification floor is deterministic kernels can retain exactly one kind of
artifact, and a held-out task needs *declarative facts* — an atomic mass, a stated speed —
that no registered problem type can verify. Three moves were on the table: register more
problem types, add a verification path for declarative facts that is not a kernel, or accept
that acquisition serves only domains whose content matches their kernels.

**The gate owner has taken the second, and the measurement supports it more sharply than the
argument did.** All four cases in 22C's frozen holdout use problem types that are *already
registered* — `chemistry.molar-conversion` twice, `chemistry.mass-balance`,
`mechanics.uniform-motion`. Every one failed on a withheld declarative fact, not on a missing
problem type. **Registering more problem types could not have moved that exit by a single
case.** It raises campaign yield against the 53-of-59 wall, which is a real but different
problem, and it is deferred to whichever campaign needs the yield.

**Why the work lands here and not in a retrofit of 22C.** 22C's holdout has been read, once,
to 0 of 4. Changing the acceptance path now so that the number improves is post-hoc fitting,
and the whole discipline of the D-series exists to refuse it. 22C therefore releases as the
typed negative it measured, unamended. The declarative-fact path enters 22D as
**pre-registered work against a fresh, unread holdout**, and it is not a favour to 22C: two of
this sprint's own exits depend on it. *Factual output is grounded or explicitly uncertain*
requires something to be grounded **in**; *local verified success at least 10 points above
retrieval-only* requires the acquired layer to contribute something retrieval alone does not.

**The substrate is largely released, which is why this is a wave and not a sprint.** The
semantic memory subsystem already carries the non-kernel floor: twelve required, fail-closed,
registered promotion verifiers — `source_integrity`, `source_grounding`, `observation_schema`,
`predicate_schema`, `valid_interval`, `revision_continuity`, `relation_integrity`,
`supersession_acyclic`, `evidence_minimum`, `evidence_integrity`, `critical_contradiction`,
`belief_policy` — run by `SemanticPromotionGate` before any claim reaches `SUPPORTED`, with
a released refusal that neither a provider nor the controller may decide a promotion. 22C
already drove that gate; W2-F2 was found inside it. What is genuinely missing is one seam:
`ExtractionDecisionOutcome` is a released contract with no implementation, and it is exactly
the step that turns a grounded span in a cleared source into a recorded observation.

**And the kernel floor is not abandoned, it changes role.** A declarative fact cannot be
recomputed, but it can be *corroborated*: if the retained atomic masses reproduce a worked
example's printed result exactly, that example is evidence for the fact. The kernel becomes a
consistency oracle rather than a recomputation, `evidence_minimum` and `evidence_integrity`
are the released verifiers for precisely that shape of evidence chain, and a fact that no
kernel-checkable consequence corroborates is admitted at a *weaker* status that the record
names. **W0 freezes that ladder before any fact is admitted**, because a status boundary
chosen after seeing which facts fall on which side is the same defect as a tolerance chosen
after seeing the answer (22C W1-F3, W3-F2).

Two readings of "grounded" are available and W0 must pick one and hold it:

- **grounded retrieval** — a factual sentence carries a resolvable span into registered source
  bytes, and nothing is asserted to be true. Cheap, sufficient for exit four alone, and it
  makes the acquired layer indistinguishable from a search index;
- **acquired grounded facts** — the fact is a claim that passed the twelve verifiers, carries
  its evidence, and can be superseded and contradicted. Serves exit four *and* gives exit two
  something to be ten points better than.

This plan freezes the second as the sprint's reading, with the first as its floor: **every**
factual output resolves to source bytes, and the acquired layer is what makes some of them
answerable at all.

---

## 2. The readings W0 freezes, before any measured number exists

### 2.1 What 22D asks nobody for

No threshold change — the five exit sentences are the allocation's, verbatim. No new released
enum member. No learner refit, no touch on canary routing or live containment. No promotion of
either pilot domain past `lifecycle: pilot`. No retro-fix of 22C's improvement exit. The
pre-registration is `measured_values: 0` on the microbenchmark and on the new declarative-fact
holdout alike, published before the first arm runs.

### 2.2 The five readings that could bend, fixed in advance

**(a) "No large external LLM is called during the local microbenchmark."** Read as a
**construction**, never as an audit of what happened. The benchmark run composes a provider
registry in which no network adapter is registered at all, and the manifest's
`maximum_provider_calls` for external providers is zero; a call attempt is an error that fails
the run rather than a line in a log someone checks afterwards. "Large external LLM" is
enumerated by name in W0 — every network provider the repository can construct — per the
22A W4-F1 rule that a coverage word is an enumeration with a test asserting it. The local
model's own calls are counted and are not external calls; embedding and reranking models that
already run locally are named in the enumeration as out of scope, so the boundary cannot be
argued about after a number exists.

**(b) "Local verified success is at least 70 % and at least 10 points above retrieval-only."**
One hundred tasks, frozen with content hashes before any arm runs, never used to select the
model, the prompt, the retrieval configuration or the escalation threshold. *Verified* means a
registered verifier from the released registry returns a pass — not a model judging a model,
which is the failure mode this whole programme is built to avoid. The four arms named in the
allocation — no-memory, retrieval-only, external-teacher, local-model — run the same tasks,
the same seeds and the same verifier, and the ten-point comparison is **local-model against
retrieval-only**, both measured in this sprint, neither imported. A task the verifier cannot
decide is counted as a failure for every arm, and the count of such tasks is reported.

**(c) "Large-LLM calls or equivalent cost fall at least 25 % at non-inferior success."**
The baseline is the external-teacher arm on the same hundred tasks, measured here — not a
historical figure from another sprint, per the 22B W4-A1 rule about measuring the middle. The
comparison quantity is fixed in W0 as **calls** and **accounted cost** separately, both
reported, so a reduction cannot be claimed on whichever moved further. *Non-inferior* needs a
pre-registered margin: W0 fixes it as a maximum tolerated absolute drop in verified success,
stated as a number before any arm runs, and a mixed workload that beats the cost target while
falling outside the margin is a failed exit, not a trade-off to narrate.

**(d) "Factual output is grounded or explicitly uncertain."** The binary is the whole exit and
both halves must be mechanical. *Grounded* means the output carries a citation that the
released citation walk resolves **by loading the cited source bytes** — 22C's walker, reused,
because a digest proves bytes and not usability (D7 W3-F1). *Explicitly uncertain* means the
system emitted a typed abstention, frozen in W0 as a value the runtime produces and the
verifier recognises — not a hedging phrase detected in prose, which would make the exit a
string-matching exercise. Every factual output falls in exactly one of the two, the third case
(an ungrounded confident assertion) is counted, and the exit reads that count being zero. The
enumeration of what counts as a *factual output* is frozen in W0 and asserted by a test.

**(e) "Prior domain, learning, and safety gates remain green."** Re-read, not assumed: Gate L2
at 29 of 29, Gate D1's closed conditions still closed, 22A's four exits, 22B's five, and 22C's
four met exits re-executed from their sealed records against this sprint's head. A gate that
cannot be re-read is red for the purposes of this exit.

### 2.3 Explicitly out of scope

- **adapter training**, unless W4 has surplus and both preflights are sealed — it is optional
  in the allocation, no exit needs it, and no result here depends on it;
- registering additional problem types in either pilot domain — the other half of W3-F1's
  decision, deferred to a campaign that needs the yield;
- any retro-fix, re-read or amendment of 22C's improvement exit or its holdout;
- self-improvement proposals, weakness-to-proposal linkage, Gate M — 22E's, entirely;
- packaging, installers, operator runbooks — 23A's, entirely;
- resolving 22C W2-A1 or W3-A1, or any schema change;
- multilingual capability of any kind: the exit says English, and the sprint claims English;
- tuning any pre-registered configuration — model, quantization, prompt, retrieval depth,
  escalation threshold, non-inferiority margin — after its first measured number exists.

---

## 3. Execution waves

| Wave | Work | Exit criterion served |
|---|---|---|
| **W0** | Block until 22C is released: verify its tag from live handles, ancestry into protected `main`, exact-head CI. Seal the hardware preflight (§1.3) and the provider enumeration. Surface both rights gates (§1.4) with a named owner; refuse to proceed on the model without a clearance. Freeze: the 100-task microbenchmark with `measured_values: 0`; the four arms; the verifier set; the abstention value and the factual-output enumeration; the non-inferiority margin; the escalation policy as a decision function; the accounting definition; and the §1.5 grounding ladder. Build the benchmark runner, the local runtime harness and the accounting record, and run every arm end to end at fixture scale — ten tasks, one refused external call, one citation walk, one abstention | every claim's authority |
| **W1** | **The declarative-fact path (§1.5), against a fresh unread holdout frozen in W0.** Implement the one missing seam — a grounded span in a cleared source becomes a recorded observation and then a claim through the twelve released promotion verifiers — with the kernel as consistency oracle for corroboration. Re-run acquisition over 22C's already-cleared chapters, which needs no new rights decision. Measure what Layer 1 holds afterwards, against the 1 artifact it holds now. **If this wave does not materially fill Layer 1, exits two and four are at risk and the sprint knows it in week one** rather than in W3 | grounding; the ≥10-point margin |
| **W2** | The local model: clearance sealed, weights hashed, quantization and sampling pinned, served behind a `LOCAL_API` provider through the released OpenAI-compatible mapping. The **no-memory**, **retrieval-only** and **external-teacher** baselines on the frozen hundred, each sealed. The external-teacher arm is the *only* wave that calls a network provider, and it runs before the local microbenchmark so that the no-external-call construction is never weakened to accommodate it | baselines; no-external-call |
| **W3** | Retrieval-augmented local inference on the acquired layer; the **local-model arm** on the frozen hundred, read once. Confidence-based external escalation and the stable mixed workload, with provider/local compute accounting on both. The 25 % reduction and the non-inferiority margin read once. The grounding exit read once over every factual output | **all four measured exits** |
| **W4** | The five exits read once from sealed records, `--check` rebuilding the document from sources; prior gates re-read (§2.2e); full verification matrix; whole suite; report and handoff naming what 22E inherits; adapter feasibility **only if** surplus and both preflights are sealed; protected release, exact-head CI, annotated tag `sprint-22d-language-baseline`, remote verification, sealers twice | release |

### 3.1 The first vertical slice

W0 runs all four arms, the escalation policy, the accounting record and the grounding walk
against ten fixture tasks and a fixture-scale model before the hundred is touched. Every
sprint since D4 found its cheapest defect in the slice. **This sprint's likeliest slice finding
is that "grounded" has no executable meaning for generated prose.** 22C's citation walk starts
from a *promoted artifact* whose provenance bundle was constructed by the pipeline; a sentence
a language model just produced has no bundle, and the step that attaches one — deciding which
span a clause rests on, and refusing when none does — has never been driven by any runner.
W0 wants that found on ten tasks, not on the hundred.

### 3.2 The four schedule risks, named

**Layer 1 may stay thin even after W1.** The declarative-fact path removes the kernel wall;
it does not guarantee volume, and the corroboration ladder may leave most facts at a status
too weak to retrieve. If W1 ends with a Layer 1 that cannot support the ten-point margin, the
honest response is the one 22C modelled: measure it, say so, and let W3's numbers be a typed
negative with both arms sealed — not to loosen the corroboration ladder until the number
arrives.

**Model licence clearance is on the critical path and outside the repository.** No clearance,
no local model, no sprint. W0's first act if it has not concluded is to surface it as a
blocking dependency with a named owner, never to substitute a "temporary" model — a benchmark
run on unclear weights is evidence that cannot be released.

**Local inference is slow, and the schedule must not buy speed with the claim.** Four arms
over a hundred tasks on CPU is hours, not minutes, and the temptation when it is slow is to
move the measured configuration to the GPU. The CPU configuration is the claim; GPU numbers
are reported beside it and never in place of it.

**The escalation policy is where the sprint could cheat without noticing.** A threshold tuned
until the mixed workload hits both the 25 % cost target and the non-inferiority margin is a
number met by moving what the number reads. The policy is frozen in W0 as a decision function
over quantities the runtime already produces, and is not touched after the first measured
number exists — §2.3, and the rule that has held since D2.

---

## 4. Risks the evidence cannot retire

**One model is one model.** A single quantized model in a single class on a single host
demonstrates that bounded local English capability is reachable, not that it is portable. Every
number in this sprint is conditioned on a pinned weight hash and the host in §1.3.

**A hundred tasks is a microbenchmark, and it is authored by the same repository it measures.**
Task authorship is the oldest way to make a benchmark agree with you. The mitigations are
mechanical — frozen before any arm, hashed, never used for selection, verified by registered
verifiers rather than by judgement — and none of them makes the hundred representative of
technical English.

**Grounding is not truth.** The semantic floor verifies that a claim is anchored in bytes a
cleared source really contains, that its evidence is intact and that it does not contradict
what is already believed. It does not verify that the source is right. A fact corroborated by
a kernel-checkable consequence is stronger than one that is not, and neither is a proof. The
record states which of the two every retained fact is, and the sprint claims exactly that.

**A cost reduction measured on one workload is not an operating cost.** The 25 % is an
existence proof on a frozen mixed workload with a frozen escalation policy. It licenses no
claim about a month of real use, and the accounting record exists so a later sprint can
measure that instead of extrapolating this.

---

## 5. Definition of done

**On a pass:** all five exit criteria met on sealed evidence under the frozen readings — no
external provider constructible during the local microbenchmark, with the enumeration asserted
by a test; local verified success at least 70 % and at least 10 points above retrieval-only on
the frozen hundred, same seeds, same registered verifiers, both arms measured here; external
calls and accounted cost each down at least 25 % against the external-teacher arm measured in
this sprint, inside the pre-registered non-inferiority margin; every factual output either
resolving to loaded source bytes or carrying the typed abstention, with zero in the third
case; and Gate L2, Gate D1's closed conditions and 22A/22B/22C's met exits re-read green —
plus 22C W2-F3 repaired or the accounting's source named, the §1.5 ladder honoured as frozen,
carried findings carried by name, and the annotated tag **`sprint-22d-language-baseline`**
created after exact-head CI and never moved. The handoff names what 22E inherits: a system
that answers bounded technical English questions from its own governed knowledge on its own
hardware, with the measured cost of every escalation it still makes.

**On a stop:** a typed negative under `sprint-22d-evidence-baseline` naming which exit failed,
in which wave, with which measured values. The stop this plan considers most likely is the
ten-point margin, because it is the one that depends on W1 filling a layer that currently holds
one artifact — and the plan's response is designed in: W1 measures Layer 1 in week one, so the
negative, if it comes, arrives with its diagnosis attached. The stop it refuses to reach by
construction is a local claim propped up by an external call, a grounding claim that resolves
no bytes, or a threshold moved after its first number.
