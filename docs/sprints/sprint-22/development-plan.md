# Cognitive OS Learning, Memory, and Scale Development Plan

Status: active execution plan

Revision: 7

Assessment date: 2026-08-03

Current protected predecessor release: `sprint-21d2-evidence-baseline` (negative)

Protected predecessor commit: `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5`

Current planning head: `origin/main` at
`9fe03cea3975e81bbae57b870e7bc50d8cc29f49`

Next execution sprint: Sprint 21D3 — Invariant Correction Ranking, Independent Retrieval
Closure, and Gate L2

Primary scope: finish Sprint 21 correctly, execute Sprint 22, and define the evidence
required before Sprint 23 alpha

Repository language: English only

Execution documents:

- [Execution sprint allocation](execution-sprint-allocation.md)
- [Sprint 21R technical backlog](../sprint-21/sprint-21r-technical-backlog.md)
- [Sprint 21C1 technical backlog](../sprint-21/sprint-21c1-technical-backlog.md)
- [Sprint 21C2 technical backlog](../sprint-21/sprint-21c2-technical-backlog.md)
- [Sprint 21C3 technical backlog](../sprint-21/sprint-21c3-technical-backlog.md)
- [Sprint 21D1 technical backlog](../sprint-21/sprint-21d1-technical-backlog.md)
- [Sprint 21D2 technical backlog](../sprint-21/sprint-21d2-technical-backlog.md)
- [Sprint 21D3 technical backlog](../sprint-21/sprint-21d3-technical-backlog.md)
- [Sprint 21D2 report](../sprint-21/sprint-21d2-report.md)
- [Sprint 21D3 handoff](../sprint-21/sprint-21d3-handoff.md)
- [Sprint 21D1 report](../sprint-21/sprint-21d1-report.md)
- [Gate D1 assessment](../sprint-21/gate-d1-assessment.md)
- [Sprint 21 Gate L assessment](../sprint-21/gate-l-assessment.md)
- [Sprint 21 substrate report](../sprint-21/report.md)
- [Sprint 21 technical plan](../sprint-21/technical-plan.md)

## 1. Executive decision

Cognitive OS is an agent that must learn, retain, revise, and apply knowledge. Machine
learning is therefore a mandatory product capability, not an optional experiment.
The project must not claim Sprint 21 or Sprint 22 complete until all of the following
are true:

1. learned evidence, model artifacts, evaluations, and activation decisions survive
   process restart and are auditable;
2. at least one owned learned component is active on a bounded runtime path and
   materially improves a task outcome over the strongest honest deterministic
   baseline;
3. all earlier accepted capabilities remain protected by a cross-domain replay and
   anti-forgetting gate;
4. out-of-distribution input, low confidence, missing artifacts, and model failure
   fall back to a safe deterministic path;
5. new knowledge can supersede old knowledge without erasing provenance or losing
   the ability to roll back;
6. the architecture has a demonstrated path from the current `10^5` envelope to at
   least `10^6` learned items;
7. external LLMs act as teachers, reviewers, or bounded providers, while Cognitive OS
   owns the retained corpus, verification, memory, learning, and promotion decision.

This requirement does not make every individual model mandatory. A particular k-NN,
tree, embedding model, GNN, or small language model may be rejected. The mandatory
part is the governed learning plane and at least one proven, activated learned
behavior. If the first learning surface or algorithm fails, the project must improve
the corpus, choose a better surface, or try the next bounded learner. It may not
close the gate by declaring machine learning unnecessary.

Three additional decisions follow from the assessment:

- Domains are useful as governance, evaluation, verifier, and curriculum boundaries.
  They must not become hard-coded knowledge silos or require a new core enum and
  controller branch for every scientific field.
- Graph memory already has sound foundations in temporal semantic memory and the
  Strategy Evolution Graph. Experience Memory Graph work should receive higher
  priority, but it should extend the existing Experience Compiler and PostgreSQL
  authority rather than introduce a graph database prematurely.
- Sprint 21 and Sprint 22 form one learning programme. Sprint 21 establishes a real,
  persistent, useful learned behavior; Sprint 22 proves breadth, continual learning,
  scale, knowledge acquisition, and a bounded local English capability.

## 2. Source material and interpretation

This revision is based on:

- the original project plan, `Cognitive OS Development Plan.md`;
- the Experience Memory Graph summary,
  `EMG-Experience-Memory-Graph-osszefoglalo.md`;
- the previous revision of this document;
- the Sprint 20 report and Sprint 21 technical plan;
- the Sprint 21 Gate L assessment;
- the active branch implementation, tests, benchmark artifacts, commits, and ADRs;
- the current `main` GitHub Actions state;
- current official provider documentation and the EMG preprint.

The target is interpreted as a self-learning and self-improving agent. In its early
stages it may use the user, advanced LLMs, books, papers, corpora, tools, and other
agents as sources. Cognitive OS must own the source lineage, quality checks,
transformation, memory integration, evaluation, and promotion of what it learns.
Automatic source extraction by Cognitive OS itself is useful but is not a prerequisite
for the first learning gate.

## 3. Verified current state

### 3.1 Release state

| Item | Verified state | Consequence |
|---|---|---|
| Current `origin/main` | `9fe03cea3975e81bbae57b870e7bc50d8cc29f49` | Includes D2 implementation and gate-close PR `#220` |
| D2 release tag | Annotated negative `sprint-21d2-evidence-baseline`, tag object `3f3c00e216879b4d1443ca20ac3e5f14c1bc0e29`, peeled to `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5` | Immutable D3 implementation predecessor evidence |
| Sprint 21D2 pull requests | `#219` implementation and `#220` gate-close documentation, merged | D2 behavior, negative assessment, report, and remediation handoff are on `main` |
| D2 release CI | Run `30788129259`, 30 of 30 jobs successful on the peeled release commit | Exact implementation-release evidence exists |
| Latest `main` CI | Run `30789985887`, 30 of 30 jobs successful on exact current `origin/main` | Gate-close planning head is green |
| Alembic head | `0015_create_provider_output_governance.py` | D3 uses existing stores by default; `0016` requires measured need |
| Next branch | `feature/sprint-21d3-invariant-correction-ranking` | Create from revalidated current `origin/main`, retaining gate-close documentation |
| Gate state | Gate D1 conditions 6, 7 and 15 open; Gate L2 does not pass; Sprint 22A blocked | D3 invariant-feature and independent-retrieval remediation is next |

Sprint 21R, Sprint 21C1, Sprint 21C2, Sprint 21C3, D1, and D2 are complete releases.
D2 is a valid negative experiment, not a passed gate: its k-NN found clean calibration signal
but failed semantics-preserving OOD, selected no artifact, opened no final holdout, and activated
nothing. Sprint 21D3 must preserve that result, correct the OOD denominator and retrieval
evidence discrepancies, run one pre-registered invariant feature revision on fresh evidence,
and close retrieval independently before Gate L2 can pass.

### 3.2 Final Sprint 21D2 verification

The C1, C2, C3, D1, and D2 reports and annotated tags retain the full commands,
environments, hashes, and limitations. The latest release evidence includes:

| Check | Result |
|---|---:|
| D2 release CI | `30/30` jobs passed on `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5` |
| Current gate-close CI | run `30789985887` passed `30/30` on `9fe03cea3975e81bbae57b870e7bc50d8cc29f49` |
| Full local suite | `3324 passed, 74 skipped` |
| Local evidence matrix | 29 of 29 rows reached their expected status |
| Correction corpus | 125 disjoint groups, 500 candidate slots, 95 groups authored for D2 |
| Fitting/calibration | 200/50 and 40/10 `SELF_PLAY`; zero `REAL_GOVERNED_RUN` fitted |
| Clean calibration | k-NN `0.9` at `0.9` coverage versus strongest deterministic `0.3` |
| D2 OOD result | zero eligible settings; confident errors or complete silence; selection is null |
| Untouched correction roles | final A 30/120, final B 30/120, canary 5/20; no outcomes |
| Corrected D2 graph development baseline | width-20 Recall@5 `0.5875`, MRR@10 `0.3634`; zero cutoffs |
| MiniLM vector development baseline | Recall@5 `0.5375`, MRR@10 `0.4392` |
| Gate state | D1 conditions 6, 7 and 15 open; Gate L2 does not pass |
| Migration | Remained at `0015`; `0016` unallocated |

Sprint 21D3 preserves these controls, publishes revision 3 before any D3
candidate/development/holdout measurement, changes the unstable feature boundary once, creates
fresh calibration and retrieval evidence, and either completes the existing governed activation
sequence or releases the first failed condition. Immutable D2 reconciliation replay is the
baseline-only chronology exception.

### 3.3 What the released substrate has completed

The released Sprint 21 substrate provides:

- typed learning records, feature schemas, model artifact metadata, promotion
  decisions, replay, invariance, replacement, self-play, and capacity contracts;
- durable learned-evidence, corpus, evaluation, promotion, artifact-lineage, and
  activation ledgers in PostgreSQL with controlled append paths;
- governed, replayable OpenRouter, Claude Code, and Codex advisory boundaries;
- provider-output rights, sensitivity, retention, verifier, revision, and learned
  intake evidence;
- a deterministic baseline ladder and a bounded k-NN implementation;
- governed learned skill selection with deterministic fallback;
- four domain pilots: logic, mathematics, physics, and coding;
- coding fixtures with accepted and rejected cases;
- PostgreSQL approximate vector indexes and a measured `10^5` retrieval envelope;
- canonical failed/success action-decision graphs, verified edit paths, bounded EMG
  retrieval, and an advisory Experience Graph Context source;
- a hash-bound surface audit and pre-registration system that found and rejected a
  perfect construction oracle rather than training on it;
- a Gate L assessment that honestly recorded the original no-go result;
- an oracle-free 125-group correction corpus, pre-outcome feature seals, explicit snapshots,
  bounded correction k-NN, canonical JSON artifact/loader/runtime contracts, restart-safe
  campaign receipts, and a valid negative selection result;
- width-20 bounded graph retrieval measured without cutoffs, including the evidence that the
  wider shortlist is worse rather than a near-pass.

D1 identifies `experience.correction_ranking` as the only balanced deferred surface,
with 120 eligible real-run examples and 30 changeable task rankings. This is useful
development evidence, but real governed outcomes remain evaluation-only and it is not
yet proof of useful agent learning.

### 3.4 Critical gaps

1. No learned component is active because of demonstrated downstream benefit.
2. The D2 ranker is dominated by a raw candidate-diff embedding and a duplicated
   requirement/delta cosine. It reverses confidently under semantics-preserving change.
3. D2 counted four candidate labels as four OOD decisions although the ranker made one
   group-level action; D3 needs at least 100 actual decisions, not slots.
4. The fitted-matrix audits name 11 scalar columns but do not expose the 384 fitted embedding
   dimensions as inspected columns; D3 must close that audit boundary.
5. Existing explicit dataset identity does not include feature-schema and canonical partition
   selection, so v2 could silently resolve the D2/v1 dataset.
6. D2 calibration/OOD evidence is spent. D3 requires fresh self-play calibration and a new
   metamorphic/OOD selection set after revision-3 feature seals.
7. The 65 unexecuted D2 correction groups are numerically sufficient for exact final A/B and
   canary reuse only after a body/outcome/access/hash audit.
8. A separate retrieval holdout does not exist. At least 50 new group-disjoint unseen queries
   are required; final A/B cannot serve both experiments.
9. Width-20 graph retrieval is below the 0.70/0.50 floors at 0.5875/0.3634. D3 evaluates one
   fixed equal-weight lexical+MiniLM reciprocal-rank fusion and does not tune it on the holdout.
10. Final benefit, retention, promotion-scale OOD, shadow, approval, canary, kill-switch,
    restart, activation, and rollback evidence remains unopened.
11. Receipt-aware resume does not yet bind every campaign hash/mode/order or prevent callers
    from consulting the ordinary remainder for intentionally skipped candidates.
12. Generic lifecycle advancement must be prevented from reaching VERIFIED; focused
    verification and activation must rehash the exact payload artifact bytes.
13. OpenRouter remains outside the D3 critical path; evidence completeness cannot depend on a
    network or provider.
14. The `10^6` capacity envelope, incremental maintenance, consolidation, and restore
    evidence do not exist.
15. No accelerator path is verified at the D3 planning head, and the D1/D2 reference
    evidence is CPU-only. CPU-first execution remains the default until a measured
    workload justifies and reproduces an accelerator path.
16. The inconsistent development Artifact Store pair remains intentionally untouched; all D3
    evidence must use a new isolated consistent pair, while the D2 pair also becomes read-only.
17. One collaborator means required approving reviews remain unavailable; the
    project retains 27 required checks and `enforce_admins` in accepted
    single-maintainer release mode.

## 4. Non-negotiable learning architecture

### 4.1 Learning plane, not one universal model

The robust design is a shared governed learning plane with multiple replaceable
learned components:

```text
sources and executions
        |
        v
immutable raw evidence + rights + provenance
        |
        v
normalized corpus and experience records
        |
        +--> semantic memory and revision graph
        +--> strategy and skill evidence
        +--> experience action-decision graphs
        |
        v
candidate learner or retrieval policy
        |
        v
frozen evaluation + verifier + anti-forgetting gate
        |
        v
staged activation with deterministic fallback
        |
        v
runtime outcomes returned as new evidence
```

Logic, mathematics, coding, chemistry, and engineering should share evidence,
features, provenance, model lifecycle, retrieval, and promotion contracts. They may
have different verifiers, tools, curricula, and specialized learned artifacts.
Forcing all knowledge into one model now would make verification, rollback,
catastrophic-forgetting control, and resource use worse.

### 4.2 Knowledge revision instead of destructive overwrite

“Continuous growth” must not mean append-only retrieval of every historical claim.
It means:

- raw source and execution evidence are immutable;
- normalized knowledge has stable identity and revision lineage;
- a new claim may support, refine, contradict, or supersede an older claim;
- the active view suppresses superseded or refuted knowledge;
- provenance, prior revisions, and the reason for change remain queryable;
- retrieval uses validity interval, confidence, domain, source quality, and current
  status;
- rollback can restore the prior active view without reconstructing history.

The existing temporal semantic memory and controlled-change infrastructure should
remain authoritative for these transitions.

### 4.3 Catastrophic-forgetting controls

Every trained or fitted artifact must pass all of these controls:

1. **Frozen splits:** corpus version, feature version, group split, random seed, and
   verifier version are recorded before training.
2. **Group isolation:** tasks, repositories, source documents, and near-duplicates
   cannot cross train and evaluation boundaries.
3. **Cross-domain replay:** every evaluation includes the frozen retained set for all
   previously accepted domains and learning surfaces.
4. **Safety preservation:** zero accepted-to-rejected transitions are allowed on
   safety, governance, permission, secret, and destructive-action cases.
5. **Performance preservation:** no domain may fall by more than two absolute
   percentage points, and aggregate verified success may not fall by more than one
   point. For small suites, any regression must be reviewed case by case.
6. **Backward-transfer reporting:** gains and losses are reported per domain,
   difficulty, source, tool, and time slice; aggregate accuracy alone is
   insufficient.
7. **Staged artifacts:** training never mutates the active artifact. It creates a new
   candidate whose staging manifest records the parent artifact identity; lineage fields
   retain their defined contract meaning.
8. **Shadow and canary:** a candidate first runs in shadow, then in a bounded canary
   with a kill switch and deterministic fallback.
9. **Rollback:** activation is a reversible pointer or governed status transition,
   not an in-place model replacement.
10. **No unrestricted online weight updates:** valid verifier-backed runtime rows enter
    accepted evaluation-only replay intake; unresolved, invalid, or policy-ineligible
    rows enter quarantine. Neither path updates active weights directly, and current
    `REAL_GOVERNED_RUN` rows remain permanently training-ineligible unless a future
    contract and policy revision creates newly eligible evidence.

For later neural adapters, replay data, parameter isolation, regularization, and
distillation may be compared. None of those techniques replaces the external frozen
evaluation and rollback contract.

### 4.4 Material-benefit rule

A learned component qualifies as the mandatory active component only if it meets a
pre-registered test:

- it changes at least `20` held-out decisions or retrievals;
- evaluation contains at least `200` held-out verified outcomes, unless a power
  analysis justifies a larger number;
- it achieves at least `+5` percentage points absolute verified success or `20%`
  relative error reduction over the strongest honest deterministic baseline; or it
  reduces large-LLM calls or cost by at least `25%` at non-inferior verified success;
- a paired bootstrap confidence interval has a lower bound above zero for the primary
  outcome;
- no catastrophic-forgetting or safety threshold is violated;
- low-confidence and out-of-distribution cases abstain and fall back;
- benefit persists in at least two independent evaluation batches;
- the complete artifact, corpus, evaluator, and decision record are reproducible.

The large-LLM/cost alternative is a programme-level rule for workloads that actually use
providers. It was non-applicable to D2's credential-free zero/zero campaign and remains
non-applicable to D3; D3 can pass material benefit only through the fixed verified-success/
error threshold.

A parity-only tie-break can prove wiring and safety, but it cannot satisfy the
mandatory-benefit rule.

## 5. Learner priority and stopping order

Methods are tried in the following order. The first method that satisfies the
material-benefit and operational gates is activated. More complex methods are not
implemented merely because they are fashionable.

| Priority | Method | Intended use | Promotion condition |
|---:|---|---|---|
| 0 | Strong deterministic baseline | Establish honest headroom | Always required |
| 1 | Exact/typed retrieval and calibrated k-NN | Experience, correction, or strategy retrieval | Material benefit and safe OOD behavior |
| 2 | Logistic regression or `SGDClassifier` | Sparse, interpretable classification/routing | Beats k-NN or solves a distinct surface |
| 3 | Small decision tree or bounded ensemble | Nonlinear structured features | Measured need and bounded artifact |
| 4 | Contextual bandit in shadow mode | Repeated routing with delayed outcomes | Only after stable attribution exists |
| 5 | Small MLP or adapter | Dense nonlinear mapping | Only after data volume and GPU/CPU evidence justify it |
| 6 | GNN or FGW-assisted graph learner | Graph-structured experience | Only after simple graph retrieval is inadequate |
| 7 | Local small language model adapter | Bounded English generation/reasoning | Only after local inference and corpus-rights gates |

The core environment remains lightweight. `scikit-learn`, local embedding packages,
graph alignment libraries, and neural runtimes stay in explicit optional extras until
an accepted artifact needs them. OpenRouter should use the already installed OpenAI
Python client through its OpenAI-compatible endpoint; a LiteLLM dependency is not
needed for the initial integration.

## 6. Domain strategy

### 6.1 Decision

Domains are the right abstraction for:

- curriculum and benchmark ownership;
- verifier and tool policy;
- failure and weakness analysis;
- per-domain replay and regression reporting;
- source and model eligibility;
- domain-specific skill packages.

Domains are not the right abstraction for:

- independent memory databases;
- independent copies of the controller;
- one hard-coded model per subject;
- mutually exclusive labels for cross-domain knowledge;
- a growing `if/elif` or enum change for every new scientific field.

### 6.2 Domain Registry v2

Replace the closed domain-kind seam with data-driven descriptors while preserving
backward compatibility for the four current domains. Each descriptor must include:

- stable string `domain_id`;
- display name and version;
- optional parent and related domains;
- concept and capability tags;
- accepted problem and artifact schemas;
- required verifiers, tools, units, and sandbox policy;
- feature adapters and embedding policy;
- corpus and benchmark manifests;
- transfer eligibility;
- minimum evidence and promotion thresholds;
- owner, lifecycle status, and provenance.

Knowledge items may have multiple domain memberships and concept links. A mechanics
item may belong to physics, engineering, mathematics, and coding without
duplication. Shared concepts should be represented in semantic memory; domain
descriptors select views and verification rules.

### 6.3 Expansion order

1. **Mechanics/engineering:** closest to current physics, unit checks, equations, and
   coding tools; best first proof of data-driven expansion.
2. **Chemistry:** introduces stoichiometry, units, formula parsing, and safety
   metadata; proves a distinct verifier family.
3. **Astronomy:** combines physics, mathematics, temporal data, uncertainty, and
   source freshness.
4. Further domains enter through the same registry and evidence gate.

The acceptance test for Domain Registry v2 is adding both mechanics and chemistry by
descriptor, fixtures, and verifier packages without editing the core controller,
learning contracts, or storage schema.

## 7. Experience Memory Graph plan

### 7.1 Architectural weight

Graph memory is already represented at the semantic and strategy levels. The missing
piece is a retrieval-ready graph of failed reasoning, decisions, tool actions,
corrections, and successful alternatives. This work should be a first-class Sprint
21D experiment because it can improve small-model and non-parametric learning without
placing all knowledge in neural weights.

The EMG paper is promising but is a 2026 preprint. It relies on paired failed and
expert trajectories, and its FGW alignment is approximate and computationally
expensive. Cognitive OS must reproduce the idea as a controlled experiment rather
than assume the published result generalizes.

### 7.2 Data model

Extend the existing normalized trajectory structures with a derived,
non-authoritative action-decision graph:

- **nodes:** normalized observation, reasoning step, tool action, tool result,
  verification result, correction, and accepted outcome;
- **edges:** `next`, `branches_to`, `caused_by`, `supports`, `contradicts`,
  `corrected_by`, and `recovers_to`;
- **node metadata:** trajectory ID, segment ID, domain IDs, tool, timestamp,
  provider/model, source, sensitivity, verifier result, and content hash;
- **graph metadata:** task signature, problem family, failed/success state, corpus
  version, normalizer version, and derivation lineage;
- **edit artifact:** matched nodes, removed failed steps, inserted corrective steps,
  confidence, algorithm, and evidence.

PostgreSQL remains authoritative for trajectory identity, metadata, revisions, and
status. Graph payloads and edit paths may be immutable artifacts. A bounded NetworkX
projection is sufficient for the first implementation.

### 7.3 Experiment ladder

1. Canonical task and step signatures with exact matching.
2. Vector retrieval over trajectory and node summaries.
3. Simple labeled graph edit or maximum-common-subgraph baseline on bounded graphs.
4. Failed-to-successful correction path retrieval.
5. Only if steps 1-4 leave measured headroom, compare FGW alignment.
6. Only if FGW is beneficial and its runtime is acceptable, evaluate a GNN or learned
   graph encoder.

The experiment must compare:

- no experience memory;
- text lesson retrieval;
- vector trajectory retrieval;
- simple graph/edit-path retrieval;
- FGW-assisted retrieval, if implemented.

Primary outcomes are first-attempt verified success, accepted correction rate, large
LLM calls per accepted task, token/cost use, retrieval precision, edit-path validity,
latency, and unseen-task generalization.

### 7.4 Safety and licensing

- Expert trajectories must be rights-cleared and withheld from the task solver.
- Evaluation tasks and near-duplicates must be isolated from the graph build set.
- Retrieved edits are advisory context, never direct authority to modify code or
  memory.
- Tool results and secrets are redacted before graph storage.
- No EMG paper code is imported without a dependency and license review. The cited
  preprint is published under a non-commercial share-alike license, which is not a
  safe default for code copied into this Apache-licensed repository. Initial work is
  a clean-room implementation of documented ideas using compatible dependencies.
- Failure of FGW does not remove graph memory. It selects the simpler graph projection
  and moves learning effort to a better surface.

## 8. External LLM and provider integration

### 8.1 Provider roles

External providers may:

- generate candidate explanations, structured lessons, skills, test cases, or repair
  proposals;
- review source transformation and identify omissions;
- produce a successful reference trajectory for an eligible task;
- act as a benchmark teacher or judge when an independent deterministic verifier
  also exists;
- help prepare a distillation corpus.

They may not:

- write active memory or activate a model directly;
- bypass source rights, secret handling, or verification;
- approve their own output;
- mutate the repository during advisory analysis;
- become the only retained record of learning.

### 8.2 Open-development provider data policy

For project-owned, generated, or rights-verified open-project material, development
speed takes priority over enterprise-style retention restrictions:

- `require_zero_data_retention=false` is the default;
- `allow_data_collection=true` is the default;
- provider storage, collection, and sharing are accepted without a per-call ZDR
  waiver or interactive retention confirmation;
- live access still requires an enabled campaign configuration and an explicit
  runtime `--live` opt-in;
- free-only routing and a zero-spend ceiling remain independent controls.

This policy does not make credentials public. API keys, tokens, authorization
material, subscription identities, undisclosed personal data, and
rights-restricted third-party content remain excluded. Source rights and license
evidence also remain required: they protect lawful reuse and provenance, not
enterprise confidentiality.

The existing directive and provider configuration contracts are the single policy
surface. Do not create a second retention subsystem or an interactive ZDR approval
workflow.

### 8.3 OpenRouter

Implement a generic OpenAI-compatible provider using the existing OpenAI Python
client:

- base URL defaults to `https://openrouter.ai/api/v1`;
- API key is read only from `OPENROUTER_API_KEY`;
- no key, token, or request authorization header is persisted;
- model discovery and health checks are explicit;
- requests record requested model, resolved response model, provider metadata when
  available, parameters, latency, usage, and finish status;
- a replay fixture covers all normal CI tests without network or credentials;
- live tests are opt-in and quota-bounded.

The user-provided name “Gamma 4” is interpreted as **Gemma 4**. Two live smoke modes
should be supported:

- `openrouter/free` to test the current free-model router;
- a runtime-validated pinned model such as
  `google/gemma-4-26b-a4b-it:free` when available.

Free model availability and quotas change. The model catalog must be checked at run
time, and the resolved model must be recorded. A disappearing free model is a health
or skip outcome, not a reason to weaken offline CI.

### 8.4 Claude Code

Harden the existing `providers/claude_code` advisory adapter:

- non-interactive print mode;
- structured JSON output with schema validation;
- `plan` permission mode and an empty or explicit read-only tool allowlist;
- bounded turns, timeout, output size, and process tree;
- no session persistence for campaign calls;
- working-tree before/after comparison;
- subscription login health reported without exposing credentials;
- replay and failure fixtures for missing CLI, not logged in, timeout, malformed
  JSON, and attempted mutation.

The installed CLI and a Claude subscription can support local operator-initiated
evaluation. Unattended service operation requires a separately approved
authentication and terms path.

### 8.5 Codex

Add a sibling `providers/codex_cli` advisory adapter around stable non-interactive
`codex exec`:

- `--ephemeral`;
- `--json`;
- `--output-schema`;
- `--sandbox read-only`;
- `--ask-for-approval never`;
- explicit working directory;
- empty or explicitly governed tool/MCP configuration;
- timeout, output, and process limits;
- working-tree mutation check;
- replay fixtures and structured event normalization.

The assessed installation is logged in with ChatGPT. That is suitable for
operator-initiated local trials. API-key authentication is the preferred future path
for unattended CI or service automation. Cognitive OS must not copy or manage Codex
login credentials.

### 8.6 Teacher-output retention

Normalized provider output for eligible open-development data is retained by default
when it contributes to evaluation, corpus construction, or reproducibility. A
retained item must include:

- provider, requested model, resolved model, request hash, response hash, and time;
- prompt/template version and sampling parameters;
- input source IDs and source-rights status;
- output sensitivity and secret-scan result;
- verifier and reviewer decisions;
- intended use: transient advice, evaluation evidence, corpus candidate, skill
  candidate, or model-training candidate;
- terms/rights decision for the intended use;
- expiry or retention policy.

Raw transport bodies remain optional because normalized governed output is normally
the smallest useful record. An output that is acceptable as advice or evaluation
evidence is not automatically acceptable as training data; verifier, rights, and
lineage gates still decide that use.

## 9. Knowledge acquisition and self-improvement

### 9.1 Knowledge Acquisition Factory

The current Corpus Factory, semantic memory, Experience Compiler, Skill Engine, and
controlled-change system should be composed into one governed pipeline:

1. **Register source:** hash, edition/version, author/publisher, location, rights,
   sensitivity, domain tags, and extraction status.
2. **Extract:** an external agent or LLM may segment and structure the source.
3. **Normalize:** convert content into claims, concepts, examples, problems,
   solutions, procedures, skills, tests, and citations.
4. **Cross-check:** use deterministic checks, independent provider review, source
   grounding, unit checks, code execution, or proof tools as appropriate.
5. **Quarantine:** unresolved contradictions, low-confidence claims, and
   unverifiable procedures remain inactive.
6. **Compile:** create candidate corpus entries, semantic revisions, skill packages,
   experience graphs, and evaluation cases.
7. **Evaluate:** run frozen holdouts, adversarial cases, cross-domain replay, and
   source-leakage checks.
8. **Promote:** only governed, reversible candidates become active.
9. **Observe:** runtime outcomes return to the evidence store and weakness miner.

The first end-to-end demonstration must process at least one rights-cleared technical
chapter or paper in two domains, retain exact source citations, reject at least one
planted or detected error, and improve a held-out verified task outcome.

### 9.2 Self-improvement of code

Self-improvement remains proposal-driven:

- weakness evidence creates a bounded improvement proposal;
- Codex, Claude, OpenRouter, or another provider may propose a patch;
- the Coding Agent works in an isolated worktree and sandbox;
- tests, security checks, language policy, benchmark regression, and controlled-change
  gates run;
- Cognitive OS records outcome and compiles the experience;
- a human approves material repository changes during Sprint 22;
- no provider may merge, tag, or deploy autonomously.

Sprint 22 must demonstrate at least three complete proposal dry runs and one
human-approved low-risk improvement through the full governed path. This proves the
loop without claiming unrestricted autonomous code evolution.

## 10. Local English capability roadmap

Local embeddings improve retrieval but do not constitute language ability. English
capability is delivered in layers:

### Layer 1: owned non-parametric language memory

- local embeddings for English technical text;
- concepts, terminology, definitions, relations, examples, and procedures stored
  with provenance;
- retrieval and grounded answer assembly without a large external LLM;
- vocabulary and concept coverage metrics.

### Layer 2: teacher corpus

- rights-cleared instruction, explanation, classification, tool-selection, and
  correction examples;
- output schemas and verifier labels;
- difficulty, domain, source, and teacher metadata;
- train/evaluation isolation and duplicate detection.

### Layer 3: local small-model inference

- select one permissively licensed, CPU-viable quantized English model after a
  reproducible hardware benchmark;
- integrate through a local provider boundary such as llama.cpp or an existing
  compatible server;
- measure bounded comprehension, extraction, routing, tool-schema generation, and
  grounded response tasks;
- record large-LLM call avoidance and local latency.

### Layer 4: local adaptation

- perform LoRA or another parameter-efficient adaptation only after the GPU driver,
  VRAM, dependency, corpus-rights, and baseline gates pass;
- compare frozen base, retrieval-augmented base, and adapted model;
- use replay and adapter lineage to prevent or detect forgetting;
- keep the base model immutable and activation reversible.

The Sprint 22 claim is deliberately bounded: Cognitive OS must demonstrate useful
local English comprehension and structured generation on a frozen technical
microbenchmark without calling a large external LLM. General language competence is
a later programme.

## 11. Execution plan

### Phase R0: reconcile and release the existing branch

#### R0-01 — Refresh branch evidence

Tasks:

- update the Gate L assessment to include the coding domain and current head;
- distinguish fixture prediction from real sandboxed coding success;
- record current local checks and remaining skipped PostgreSQL tests;
- add a Sprint 21 branch report with exact commits and benchmark artifact hashes;
- verify generated schemas and repository language.

Expected outputs:

- updated `docs/sprints/sprint-21/gate-l-assessment.md`;
- new Sprint 21 report or explicit report addendum;
- reproducible command/evidence table;
- no claim that Gate L is closed.

Acceptance:

- every metric is tied to an artifact or command;
- stale three-domain and old-head statements are removed;
- the report states why `0.9396` rule accuracy is headroom, not an agent-success gate.

#### R0-02 — PR and protected release

Tasks:

- open a PR for `feature/sprint-21a-learning-substrate`;
- run the complete remote matrix, including PostgreSQL integration, migrations,
  backup/restore, security, optional boundaries, benchmarks, and distribution checks;
- repair only evidence-backed branch failures;
- merge after review;
- observe successful post-merge `main` CI;
- create and push an annotated `sprint-21-substrate-baseline` tag;
- verify local, origin `main`, and peeled tag SHAs.

Acceptance:

- PR CI successful;
- merged commit present on `origin/main`;
- post-merge `main` CI successful;
- annotated tag resolves to the same protected commit;
- release report contains PR, run, commit, and tag handles.

No Sprint 21C persistence migration should merge before this baseline is protected.

### Sprint 21C: persistent evidence and reality-grade learning inputs

#### S21C-01 — Learned Evidence Store

Tasks:

- create the next Alembic migration from verified head `0013`, expected identifier
  `0014_create_learned_evidence_store.py`;
- persist corpus versions, feature schema versions, learning examples, splits,
  artifact lineage, evaluations, promotion decisions, activation state, and rollback
  target;
- store large artifacts in the existing artifact plane and hashes in PostgreSQL;
- add idempotent repositories and restart/replay tests;
- extend backup/restore and least-privilege grants.

Expected code areas:

- `src/cognitive_os/domain/learned.py`;
- `src/cognitive_os/learning/`;
- `src/cognitive_os/infrastructure/learning/postgres/`;
- `infra/postgres/alembic/versions/`;
- schema exports and contract tests.

Acceptance:

- fitted artifact, evaluation, and activation survive restart;
- duplicate ingestion is idempotent;
- artifact hash mismatch fails closed;
- downgrade/re-upgrade, drift, backup, and restore pass;
- active artifact can roll back without deleting evidence.

#### S21C-02 — Real-run outcome harvester

Tasks:

- map provider calls, tool calls, task attempts, strategy/skill selections, context
  candidates, verifier outcomes, corrections, and costs into learning rows;
- require derivation back to immutable evidence;
- define attribution strength: direct, contributing, unknown;
- quarantine rows with weak attribution, missing verifier result, policy violation,
  secret risk, or inconsistent timestamps;
- publish corpus statistics by domain, source, outcome, and attribution.

Acceptance:

- at least `200` verified task outcomes and `50` failed-to-corrected trajectories are
  harvested from executable or real provider-assisted runs;
- no synthetic fixture is labeled as a real run;
- every promoted row has a verifier result and provenance;
- governed normalized provider output is retained for eligible open-development
  evidence; raw transport-body retention remains optional rather than prohibited.

#### S21C-03 — Provider adapters and live smoke

Tasks:

- implement the OpenRouter/OpenAI-compatible adapter;
- harden and live-test the Claude Code adapter;
- implement the Codex CLI adapter;
- add offline replay fixtures, health commands, redaction, timeouts, schemas, and
  mutation guards;
- add opt-in live smoke commands with strict call and spend limits;
- document local subscription use versus unattended API authentication.

Acceptance:

- credential-free CI covers all adapter contracts;
- one operator-approved live smoke succeeds for OpenRouter, Claude Code, and Codex;
- OpenRouter records the resolved free model;
- missing login, missing key, quota, timeout, malformed output, and model
  unavailability are typed outcomes;
- no credential or secret enters logs, artifacts, or git;
- advisory calls leave the working tree unchanged.

#### S21C-04 — Reality-grade coding corpus

Tasks:

- reuse the existing Coding Agent worktree and sandbox infrastructure;
- build at least `30` rights-clean repair tasks with actual failing and passing tests;
- include multiple plausible candidate strategies or provider proposals;
- keep golden patches, hidden tests, and derived answer features inaccessible to
  selection and training;
- split by repository and task family;
- record runtime, tests, mutation scope, and accepted outcome.

Acceptance:

- submitted code actually executes in the restricted sandbox;
- at least `10` tasks require a correction after an initial failed attempt;
- an “apply all declared edits” shortcut cannot solve the corpus;
- train/evaluation leakage checks pass;
- deterministic, retrieval, and learned-selection surfaces all face the same hidden
  verifier.

#### S21C-05 — Local embedding and storage calibration

Tasks:

- activate one local CPU embedding model behind the existing optional extra;
- record model ID, revision, dimension, normalization, license, and content hash;
- compare current vector storage with half-precision storage on quality, size, ingest,
  and latency;
- if justified, create the next migration after the evidence-store migration;
- keep fallback hash/deterministic embeddings for credential-free tests only.

Acceptance:

- real English technical text can be embedded locally and retrieved;
- recall and ranking quality do not regress beyond the declared threshold;
- storage reduction and migration cost are measured;
- missing local model fails to a declared capability state, not silently to fake
  production embeddings.

### Sprint 21D: mandatory useful machine learning and EMG

#### S21D-01 — Pre-register real learning surfaces

Candidate surfaces:

1. correction ranking over failed-to-corrected trajectories;
2. retrieval-augmented repair context;
3. verifier-outcome triage from strictly pre-outcome evidence;
4. strategy selection among genuinely different candidates.

Tasks:

- audit each surface for label leakage, class balance, actionability, sample size,
  group structure, attribution, deterministic headroom, and verifier quality;
- select one primary and one secondary surface before viewing held-out results;
- publish feature, label, action, group, baseline, metric, and evaluation manifests;
- use the 214 unique C3 outcomes rather than counting 960 intake observations as
  independent examples;
- create at most 50 deterministic, provider-free evaluation outcomes only when the
  audited shortfall is between 1 and 50.

Acceptance:

- the chosen primary surface has at least `200` held-out outcomes and `20` decisions
  that a learned policy can change;
- the strongest deterministic baseline is explicit;
- labels measure downstream accepted outcome, not only internal prediction accuracy.
- a triage prediction may prioritize verification or request repair context but cannot
  bypass the independent verifier;
- real governed runs remain evaluation-only.

D1 result: no primary surface qualified. `experience.correction_ranking` was deferred
with 120 eligible real-run examples and 30 changeable rankings. D2 created revision 2,
200/50 self-play fitting and 40/10 calibration evidence, but its candidate failed OOD and final
access remained closed. D3 creates revision 3 and fresh calibration; all inherited real-run
examples remain development/evaluation-only.

#### S21D-02 — Experience Memory Graph baseline

Tasks:

- resolve the 60 historical C3 coding correction manifests without rewriting their
  legacy wall-clock timestamps;
- execute and exactly recompile 10 fresh logic and 10 fresh mathematics
  failed/success pairs;
- derive bounded action-decision graphs through focused coding and domain adapters;
- pair failed and successful trajectories by task signature without evaluation
  leakage;
- implement no-memory, lexical, exact-signature, frozen MiniLM vector, and bounded
  simple graph-edit baselines;
- retrieve correction paths as advisory Context Candidates;
- store derivation, source hashes, resource policy, confidence, and algorithm version
  through existing Artifact Store and learned artifact lineage;
- retain PostgreSQL authority and avoid a graph database or migration by default.

Acceptance:

- at least `80` failed-to-success graph pairs across coding, logic, and mathematics;
- all fresh pairs pass exact Experience Compiler recompilation;
- all graph edit paths reconstruct the successful graph exactly;
- malformed, cyclic, oversized, and poisoned graphs fail closed;
- retrieval is bounded to 64 nodes, 128 edges, depth 32, 250 ms per GED comparison,
  2 seconds per query, and 10 returned results;
- evaluation reports unseen tasks separately;
- graph retrieval is compared with text and vector baselines.

D1 result: all graph construction and advisory-context conditions passed, but the best
bounded arm reached only 0.6750 Recall@5 and 0.4481 MRR@10 with 60 cutoffs. D2 fixed the
shortlist truncation, froze width 20, and measured 0.5875/0.3634 with zero cutoffs on D1
development evidence; its separate unseen-task holdout never opened. D3 freezes one simple RRF
candidate and evaluates it once on a distinct 50-query minimum holdout.

#### S21D-03 — Learner ladder

Execution allocation: D2 completed the original ladder with a null OOD result; Sprint 21D3
executes one invariant feature revision and the existing bounded k-NN only.

Tasks:

- preserve durable `CorpusRole.TRAINING/EVALUATION`, immutable campaign partitions, the
  role-bound projector, four neutral candidates, and capability-isolated holdouts;
- revise explicit dataset identity to bind feature schema, canonical partition selection,
  campaign, and observation-to-group membership;
- publish `correction-ranking-v2` before D3 measurement, alpha-normalise candidate source with
  an exact Python 3.12 AST grammar tested by an independent perturbation oracle, remove unstable
  issue/diff channels, and scan every fitted scalar and embedding dimension;
- audit final A/B/canary catalogue/root/access identities without resolving protected bodies,
  freeze a complete whole-role replacement branch with isolated throwaway authoring validation
  and capability revocation, add 20 fresh calibration groups, and create a separate retrieval
  corpus yielding at least 50 unseen queries;
- execute a new v2-sealed 200/50 fitting campaign and 80 outcomes over 20 fresh calibration
  groups;
- keep all C3/D1/D2 real governed outcomes outside fitting and calibration;
- resolve at least 100 fresh metamorphic selection decisions with unit-correct denominators,
  non-silence, action-preservation, and zero-confident-error rules;
- calibrate the unchanged bounded k-NN grid;
- do not open logistic/SGD or a tree inside D3; a fresh capacity residual may name one
  successor rung without opening final data;
- use fixed splits, seeds, feature versions, and artifact hashes;
- evaluate per-domain and cross-domain retention;
- stop when one candidate passes all gates or the pre-registered ladder is exhausted;
- select at most one immutable artifact before either final evaluation batch is opened;
  a null selection completes a protected negative result without opening final data.

Acceptance:

- result bundle contains predictions, confidence, abstentions, errors, latency, and
  provenance with ranking decisions separated from candidate outcomes;
- no evaluation split is used for feature or threshold selection;
- a failed candidate remains recorded but cannot activate;
- candidate can be replayed from persisted evidence;
- final evaluation contains exact 30-group/120-outcome A and B batches when reusable, plus at
  least 20 changed task rankings when final access is authorised;
- a pre-registered stop produces immutable not-opened records rather than fabricated
  downstream success.

#### S21D-04 — FGW decision

Tasks:

- preserve ADR 0090's no-go and D2's measured width-20 negative result;
- measure the pre-registered equal-weight RRF and existing comparators on new D3 retrieval
  evidence;
- reopen only a future experiment when reranking error is dominant and a new holdout,
  dependency, licence, benefit, and resource review are approved;
- do not install or evaluate FGW on D3 holdout queries.

Acceptance:

- the D3 continuation record names the simpler baseline, residual class, benefit
  threshold, resource budget, and future evidence requirement;
- no FGW dependency or implementation enters D3;
- paper concepts are used clean-room and no CC BY-NC-SA code or assets are copied into
  the Apache-licensed repository.

#### S21D-05 — Shadow, canary, and activation

Execution allocation: D2 stopped before this lifecycle opened; Sprint 21D3 inherits it
unchanged after Gate L2 remained closed.

Tasks:

- register the selected component and enter SHADOW before any governed shadow run;
- run `label_all` final evidence in deterministic baseline order while recording learned
  order only;
- classify disagreements and verifier outcomes;
- move SHADOW to VERIFIED only through a focused evidence-revalidating transition after
  final, retrieval, forgetting, invariance, OOD, and promotion evidence pass; generic
  state advancement cannot reach VERIFIED or ACTIVE;
- use a bounded `RealityCampaignRunner` sequencer for canary/active execution, trying
  learned order and stopping only after independent verifier acceptance;
- persist a versioned sequence receipt with compare-and-set on the existing Event Store
  campaign stream, and make `RealityCampaignLedger.plan_resume()` preserve actual
  attempts, accepted stop, and intentionally unattempted candidates;
- canary only within a separately hash-recorded fail-closed configuration subset of the
  approved correction-sequencing campaign surface;
- bind canary and bounded steady configuration hashes plus their transition condition inside the
  versioned promotion payload, re-verify its exact bytes inside activation, then test kill switch,
  missing artifact, corrupt artifact, OOD input, and restart;
- produce cause-bound disable and rollback decisions that structurally forbid restoration
  after a failed canary.

Acceptance:

- one owned learned component satisfies the material-benefit rule;
- cross-domain replay and all safety suites pass;
- OOD false-confident action rate is at most `1%` for reporting and exactly zero for
  promotion under the existing contract;
- deterministic fallback is exercised successfully;
- activation and rollback survive restart.

#### Gate L2 — Sprint 21 learning gate

Gate L2 passes only when:

1. the Sprint 21 substrate has a protected release baseline;
2. the Learned Evidence Store and real-run harvester are operational;
3. all four current domains have retained regression evidence;
4. the reality-grade coding corpus executes hidden tests;
5. at least one learned component is active because of material downstream benefit;
6. anti-forgetting, OOD, shadow, canary, and rollback evidence is green;
7. OpenRouter, Claude Code, and Codex have offline contracts and opt-in live evidence;
8. EMG has at least a simple graph/edit-path baseline and a documented FGW decision;
9. all evidence is persisted, reproducible, and included in PR and post-merge CI;
10. an annotated `sprint-21-learning-baseline` tag is verified.

Failure of item 5 blocks the gate. It is not converted into an “ML optional” no-go.

### Sprint 22: continual learning, breadth, scale, and local capability

#### S22-01 — Domain Registry v2

Tasks:

- implement data-driven domain descriptors and hierarchical/multi-domain membership;
- migrate the four current domains through a backward-compatible adapter;
- add mechanics/engineering and chemistry pilots;
- expose domain diagnostics, corpus coverage, verifier readiness, and transfer edges.

Acceptance:

- two new domains are added without core controller or storage-schema changes;
- cross-domain items are stored once and retrieved through multiple views;
- per-domain and global replay reports remain available;
- invalid or untrusted domain packages cannot self-register.

#### S22-02 — `10^6` storage and retrieval envelope

Tasks:

- build deterministic uniform and clustered `10^6` datasets using real embedding
  dimensions and declared hardware;
- measure exact, ANN, filtered ANN, hybrid, temporal, graph-assisted, and stale-item
  retrieval;
- test incremental inserts, updates, supersession, tombstones, index bloat, reindex,
  and concurrent reads;
- measure storage, memory, CPU, ingest throughput, recall, and warm/cold latency;
- add backup and point-in-time restore evidence at scale.

Initial acceptance targets on the declared reference host:

- ANN recall@10 at least `0.95`;
- warm filtered ANN p95 at most `300 ms`;
- bounded graph-assisted retrieval p95 at most `500 ms`;
- sustained ingest at least `100 items/s` for the synthetic envelope;
- no unbounded in-process materialization;
- successful restore with item counts, hashes, active revisions, and learned artifact
  pointers intact.

Thresholds may be revised only before running the final benchmark and with an
evidence-backed hardware note.

#### S22-03 — Continual-learning campaign engine

Tasks:

- create campaign manifests for source, domain, goals, budget, provider eligibility,
  curriculum, holdouts, and stop conditions;
- schedule acquisition, execution, verification, training, shadow, and review jobs;
- perform rolling time-slice and source-slice evaluation;
- add drift, uncertainty, contradiction, and forgetting alerts;
- require human approval for active model promotion during Sprint 22.

Acceptance:

- at least three campaign cycles add new verified knowledge;
- every cycle replays all retained domains;
- a planted harmful or contradictory update is quarantined;
- a valid superseding update changes the active view without deleting history;
- rollback restores the previous model and knowledge view.

#### S22-04 — Knowledge Acquisition Factory demonstration

Tasks:

- process at least one rights-cleared technical chapter or paper in two domains;
- use at least two independent transformation/review paths where practical;
- compile claims, concepts, examples, problems, procedures, skills, and tests;
- run grounding, duplicate, contradiction, and verifier checks;
- evaluate held-out task use.

Acceptance:

- exact citations and source hashes survive every derived artifact;
- at least one error is detected and rejected or quarantined;
- at least one retained artifact improves a held-out task;
- raw, candidate, active, superseded, and rejected states are distinguishable;
- provider output rights are recorded for its intended use.

#### S22-05 — Bounded local English capability

Tasks:

- define a frozen English technical microbenchmark with at least `100` tasks covering
  comprehension, extraction, terminology, routing, tool-schema generation, and
  grounded responses;
- establish no-memory, retrieval-only, external-teacher, and local-model baselines;
- select and integrate one CPU-viable permissively licensed small model;
- evaluate retrieval-augmented local inference;
- attempt adapter training only after hardware and rights preflight.

Acceptance:

- no large external LLM is called during the local evaluation;
- the local path reaches at least `70%` verified success and exceeds the
  retrieval-only baseline by at least `10` points on the declared benchmark;
- all generated factual content is grounded or marked uncertain;
- latency, memory, energy proxy, and model/license metadata are reported;
- earlier domain and safety capabilities do not regress.

#### S22-06 — LLM-dependence reduction

Tasks:

- define a stable mixed workload;
- measure large-LLM calls, tokens, cost, latency, verified success, and correction
  count per accepted task;
- apply owned memory, EMG retrieval, learned routing, and local English capability;
- retain external escalation for low-confidence or high-risk cases.

Acceptance:

- at least `25%` fewer large-LLM calls or equivalent cost reduction at non-inferior
  verified success;
- high-risk tasks do not lose required escalation;
- savings are not achieved by hiding failed or abandoned tasks;
- provider and local compute costs are reported separately.

#### S22-07 — Governed self-improvement loop

Tasks:

- connect weakness mining, proposal generation, provider review, isolated coding,
  verification, controlled change, and experience compilation;
- execute three dry-run proposals;
- execute one user-approved low-risk repository improvement;
- feed outcomes back into the learning and EMG stores.

Acceptance:

- no provider has direct merge, tag, deployment, or active-memory authority;
- rejected proposals leave no active-state mutation;
- accepted change passes PR CI and post-merge `main` CI;
- regression and rollback evidence is attached;
- experience from both failure and success is retrievable.

#### Gate M — Sprint 22 scale and autonomy gate

Gate M passes only when:

1. Gate L2 passes;
2. Domain Registry v2 adds two domains without core branching;
3. the `10^6` capacity, maintenance, backup, and restore envelope passes;
4. three continual-learning cycles pass cross-domain anti-forgetting;
5. a rights-cleared source is acquired, verified, learned, and applied end to end;
6. bounded local English capability passes without a large external LLM;
7. large-LLM dependence falls by at least the declared threshold;
8. one governed self-improvement reaches protected `main`;
9. security, provider, migration, distribution, and repository-language gates pass;
10. post-merge `main` CI and the annotated `sprint-22-baseline` tag are verified.

### Sprint 23: controlled alpha

Sprint 23 should not add a new learning architecture. It should package the proven
one:

- installation and upgrade path;
- operator configuration for providers and local models;
- source-rights and data-retention documentation;
- backup, restore, and rollback runbooks;
- benchmark and campaign examples;
- observability for learning, forgetting, drift, provider use, cost, and graph
  retrieval;
- alpha limitations and safety boundaries;
- a clean default install with all heavy ML capabilities optional at packaging level
  but at least one supported learned configuration required for the Cognitive OS
  product claim.

## 12. Dependency and critical path

```text
R0 protected substrate release
  -> persistent learned evidence
  -> real outcomes + provider adapters + executable coding corpus
  -> pre-registered learning surfaces
  -> EMG/simple retrieval + bounded learner ladder
  -> material-benefit activation and Gate L2
  -> domain registry + 10^6 scale + campaigns
  -> knowledge acquisition + local English capability
  -> measured LLM-dependence reduction
  -> governed self-improvement
  -> Gate M and Sprint 23 alpha
```

Parallel work is safe only where it does not create conflicting authority:

- provider replay fixtures can proceed beside evidence-store implementation;
- the executable coding corpus can proceed beside local embedding calibration;
- EMG normalization can begin once persistent trajectory identities are stable;
- domain descriptors can be designed early but should merge after Gate L2 contracts
  are stable;
- GPU-dependent adapter work must not begin before hardware preflight and corpus
  rights pass.

## 13. Required evidence for every implementation PR

Every PR in this programme must include, as applicable:

- exact baseline and head SHAs;
- migration head and upgrade/downgrade/drift evidence;
- unit, contract, integration, adversarial, and benchmark results;
- corpus manifest, source rights, hashes, split, and duplicate report;
- feature, model, normalizer, verifier, and artifact versions;
- deterministic baseline and learned candidate comparison;
- per-domain gains, regressions, abstentions, and OOD results;
- safety and catastrophic-forgetting report;
- resource use, latency, storage, provider calls, tokens, and cost;
- shadow/canary disagreements and activation/rollback result;
- secret scan and repository-language check;
- PR CI, post-merge `main` CI, and release/tag evidence at gate closure.

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Synthetic headroom mistaken for useful learning | Require executable hidden verifiers and downstream task outcomes |
| Catastrophic forgetting | Frozen cross-domain replay, staged artifacts, canary, rollback, no direct online updates |
| New information conflicts with old information | Immutable evidence, revision graph, active view, contradiction workflow |
| Domain explosion | Data-driven hierarchical registry and shared memory |
| One model fails across heterogeneous fields | Shared contracts with replaceable domain-aware learned components |
| External LLM becomes hidden authority | Teacher/advisory role, independent verifier, governed promotion |
| Provider output cannot be retained for training | Per-item intended-use and rights decision |
| Free model disappears or quota changes | Runtime discovery, resolved-model recording, offline replay, typed skip/failure |
| Subscription CLI is unreliable for automation | Local operator trials only; API auth for unattended work |
| EMG does not generalize | Compare against text/vector/simple graph baselines on unseen tasks |
| FGW is too expensive or legally awkward | Bounded go/no-go; keep simple graph projection; no copied code |
| Graph database adds complexity without evidence | PostgreSQL authority and bounded NetworkX projection |
| Million-item indexes degrade under updates | Incremental, bloat, reindex, concurrent-read, backup/restore benchmarks |
| Local language model is too weak | Retrieval first, teacher corpus, bounded benchmark, external escalation |
| GPU unavailable | CPU-first milestones; explicit GPU driver and VRAM preflight |
| Self-improvement damages the repository | Isolated worktree, sandbox, controlled change, human approval, protected release |

## 15. External references

- Experience Memory Graph preprint:
  <https://arxiv.org/abs/2607.13884>
- Experience Memory Graph preprint license:
  <https://creativecommons.org/licenses/by-nc-sa/4.0/>
- NetworkX similarity and graph edit distance:
  <https://networkx.org/documentation/stable/reference/algorithms/similarity.html>
- NetworkX bounded graph edit distance:
  <https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.similarity.graph_edit_distance.html>
- OpenRouter free models:
  <https://openrouter.ai/models?max_price=0>
- OpenRouter free-model router:
  <https://openrouter.ai/openrouter/free>
- OpenRouter API quick start:
  <https://openrouter.ai/docs/quickstart>
- Codex authentication:
  <https://developers.openai.com/codex/auth/>
- Codex non-interactive mode:
  <https://learn.chatgpt.com/docs/non-interactive-mode>
- Claude Code CLI reference:
  <https://docs.anthropic.com/en/docs/claude-code/cli-usage>
- Claude Code getting started:
  <https://docs.anthropic.com/en/docs/claude-code/getting-started>

## 16. Immediate next action

Sprint 21R, Sprint 21C1, Sprint 21C2, Sprint 21C3, Sprint 21D1, and Sprint 21D2 are
complete releases. The immediate implementation action is **Sprint 21D3 — Invariant
Correction Ranking, Independent Retrieval Closure, and Gate L2**:

1. verify current `origin/main` at `9fe03cea3975e81bbae57b870e7bc50d8cc29f49`
   and separately verify the annotated negative D2 tag object and peeled release;
2. retain the 27 required checks and `enforce_admins`, record the one-collaborator review
   reality, keep development/C3/D1/D2 stores read-only, and isolate every D3 write;
3. publish a non-destructive D2 reconciliation: one group ranking is one decision, while four
   candidate labels are outcomes; replay and reconcile the inconsistent retrieval narrative;
4. publish pre-registration revision 3 before any D3 channel/development/holdout measurement,
   feature result, campaign, or retrieval score, with one fixed diagnostic response and no
   open-ended tuning; immutable D2 reconciliation replay remains baseline-only;
5. implement `correction-ranking-v2`: alpha-normalised candidate-source embedding, no issue or
   raw-diff input, complete scalar/embedding matrix scans, and feature/partition-sensitive
   explicit dataset identity;
6. run the frozen per-channel diagnostic on spent D2 evidence for diagnosis only, then stop if
   the result lies outside the registered response;
7. seal v2 features before a new 200/50 fitting campaign, execute 80 outcomes over 20 fresh
   calibration groups, and resolve at least 100 fresh metamorphic selection decisions;
8. calibrate the unchanged 24-setting bounded k-NN grid, enforce non-silence and exact
   equivalence rules, and select at most one artifact before final access;
9. independently implement one fixed equal-weight lexical+MiniLM reciprocal-rank fusion and
   evaluate all frozen arms once on at least 50 new group-disjoint unseen-task queries;
10. if the correction checkpoint passes, execute exact final A/B (30 groups/120 outcomes each),
    prove paired material benefit, retention, 100+ correctly counted promotion OOD decisions,
    shadow, artifact lineage, and the three D1 conditions;
11. only on a complete pass, use a versioned promotion payload, exact existing human-approval
    fields with transitive configuration binding, focused evidence-bound verification,
    activation-time byte rehash, canary, cause-bound disable, receipt-selected rollback/refusal,
    and bounded steady state;
12. complete an outcome-appropriate protected release: success uses
    `sprint-21-learning-baseline` and unblocks Sprint 22A only after gate-close CI; any first
    failure uses `sprint-21d3-evidence-baseline`, keeps Gate L2 closed, and publishes the smallest
    evidence-backed remediation handoff.

The implementation authority is the
[Sprint 21D3 Technical Backlog](../sprint-21/sprint-21d3-technical-backlog.md).
