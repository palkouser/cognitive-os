# Sprint 21D3 execution log

- **Branch:** `feature/sprint-21d3-invariant-correction-ranking`
- **Wave:** W0 + W1 + W2 — pre-registration, invariant correction spine, fresh correction evidence
- **Status:** W0, W1 and W2 complete; W2 ends in a null candidate selection and leaves the
  independent retrieval branch open for W3
- **Migration:** none; all isolated databases are at `0015`
- **Pre-registration SHA-256:**
  `191b3757ded21a1c2c85459a34902f8dee3f2f35b0979b557f84c1a37fe6a191`
- **D3 measurements before pre-registration:** zero

## W0 outcome

The exact D2 and planning baseline was re-read locally and remotely. The implementation branch
descends from `origin/main` at `9fe03cea3975e81bbae57b870e7bc50d8cc29f49`; the D2 annotated tag
object is `3f3c00e216879b4d1443ca20ac3e5f14c1bc0e29`, peeled to
`ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5`. PRs `#219` and `#220` are merged, and all four
required exact-head runs completed 30 of 30 jobs successfully. Main still has 27 strict required
contexts, `enforce_admins`, conversation resolution, no force-push, no deletion, and no approving
review requirement because the repository still has one collaborator.

The four predecessor Artifact Store pairs reproduced their released fingerprints and received
zero D3 writes. The D3 authorities are isolated under:

- PostgreSQL: `cognitive_os_s21d3_test`, `cognitive_os_s21d3_integration_test`, and
  `cognitive_os_s21d3_restore_test`;
- Artifact Store: `/home/palkouser/projekt/cognitive-os-data/artifacts-s21d3`;
- backups: `/home/palkouser/projekt/cognitive-os-data/backups-s21d3`;
- scratch: `/home/palkouser/projekt/cognitive-os-data/scratch-s21d3`.

The repository provisioning guard rejected `cognitive_os_dev`, created only the three prefixed
databases, and was idempotent on its second run. It did not invoke `postgres_bootstrap_roles.sh`
or alter the existing roles.

## Immutable D2 erratum

[The reconciliation record](evidence/sprint-21d3-d2-reconciliation.json) is the authoritative
D3 interpretation and changes no D1 or D2 byte.

- The D2 calibration OOD probe contains **10 task-group ranking decisions and 40 candidate
  outcomes**, not 40 ranking decisions. One rank-or-abstain call is one decision and every
  decision resolves four independently verified candidate labels.
- The canonical width-20 graph development values are Recall@5 `0.5875`, MRR@10 `0.3634`, and
  nDCG@10 `0.2333`; MiniLM vector is `0.5375`/`0.4392`/`0.3740`; lexical is
  `0.5250`/`0.4145`/`0.3327`.
- The D2 narrative values `0.3628`/`0.2327` and its MiniLM recall `0.6750` are not the computed
  machine-readable fields. The frozen 80-query replay remains development-only and does not
  close D1 condition 15.

## Frozen predecessor and holdout decisions

The read-only inventory names all 480 retained D2 observations, both 240-row datasets, the exact
240 member/hash pairs selected by the authoritative dataset, all six feature seals, their
chronology, campaign and bundle identities, and the null selection/continuation hashes. A
store-wide or latest-seal query is explicitly invalid.

The final-A, final-B, and canary catalogue/root/access audit resolved no protected body or
individual body hash. All three whole roles are eligible for `reuse`: their released source and
manifest identities are unchanged, membership remains 30/120, 30/120, and 5/20, they share no
group, and there are zero outcomes, predictions, or body-access receipts. Revision 3 binds the
three decisions and the complete replacement procedure if any later child check fails.

## Revision-3 contract publication

The W0 code adds refusal-oriented contract models only; it does not implement or run the v2
encoder, a learner, a campaign, or retrieval. The released D2 v1 contract hashes remain
unchanged.

| Item | Contract hash |
|---|---|
| unit-correct ranking terminology | `6ab4d81abe264f726d5c8fb38b0aa043ded239a6034927846c55763ee963c8a9` |
| spent-D2 channel diagnostic | `f36ad969623b210341a7e8a44e0c5ce6e011bb3299458777dd76f6ea4081529d` |
| `correction-ranking-v2` feature boundary | `492c90a5df420de9d1662d17155ac8b28713e69bbd4bbe56208415d6ca076362` |
| explicit dataset and grouping authority | `170df51806520af633163f6be7c60795909abb22e7eea0f2c1b924bfcb6b5d3f` |
| power and yield | `8d20e2627d57bc2da1e35aa796701b63906847159c8ea77cff51fc6db2a8abb9` |
| six-case transformation protocol | `bdcdc923e103b5a1c879407f7307d027cde55bd555ff0be60121b799e42b81d0` |
| fixed equal-weight RRF retrieval | `0233bc5deae303fb895724415211c1ad28bc86c2c47fa71222f6b35103eeb10c` |
| 29-condition Gate L2 manifest | `45a8e9b07fbb2f08033bfbe55b486c7a11a8c2f6f473cc62af98180aca5a439e` |

The automated check is:

```bash
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
  uv run python scripts/pre_registration_d3.py --check
```

Later evidence must carry the exact pre-registration file SHA and pass
`--check-chronology --later-evidence <path>`.

## Evidence index

- [baseline](evidence/sprint-21d3-baseline.json)
- [D2 reconciliation](evidence/sprint-21d3-d2-reconciliation.json)
- [authority isolation](evidence/sprint-21d3-authority-isolation.json)
- [predecessor inventory](evidence/sprint-21d3-predecessor-inventory.json)
- [holdout reuse audit](evidence/sprint-21d3-holdout-reuse-audit.json)
- [revision-3 contracts](evidence/sprint-21d3-contracts.json)
- [power and yield](evidence/sprint-21d3-power-and-yield.json)
- [gate manifest](evidence/sprint-21d3-gate-manifest.json)
- [pre-registration revision 3](evidence/sprint-21d3-pre-registration.json)

## Publication and draft PR

The first commit containing the exact pre-registration bytes is
`1c6bf106c85b5013bfcba25fed5e84475b855d4f`. Reading the file back from that commit reproduces
the pre-registration SHA-256 above. Draft PR [#221](https://github.com/palkouser/cognitive-os/pull/221)
was opened against `main` with initial head
`1c6bf106c85b5013bfcba25fed5e84475b855d4f`; its initial CI run is `30805570230`. These external
identities are recorded outside the pre-registration to avoid a self-referential commit hash.

The unchanged strict required-check inventory contains 27 contexts:

```text
benchmark-regression, build, coding-agent, cognitive-controller, context-builder-core,
controlled-changes-core, corpus-factory-core, cross-domain-pilot-core,
experience-compiler-core, harness-proposals-core, inspect-adapter, memory-plane-core,
migration, model-routing-core, optional-boundary, postgres-integration, provider-offline,
quality, sandbox, security, semantic-memory-core, skill-engine-core, strategy-engine-core,
test, tool-plane, verifier-domains, weakness-mining-core
```

## Validation

Focused D2/D3 contract validation: `78 passed`. The first sandboxed full-suite attempt reached
`3034 passed, 107 skipped` and reported 24 subprocess failures because the environment refused
to create stream file descriptors. An unchanged-source retry of exactly those provider tests in
the permitted execution environment passed `87/87`; the full suite then passed `3058 passed,
107 skipped` with zero failures. The required Ruff lint, Ruff format, repository-language,
pre-registration integrity, and diff-whitespace checks also pass.

## W1 invariant correction spine

W1 implements S21D3-020 through S21D3-028 without changing the frozen revision-3
pre-registration or any D2 artifact. The production Python 3.12 AST normaliser now assigns
scope-aware lexical first-binding placeholders and preserves imports, attributes, builtins,
magic names, and string literals. It refuses parse failures, reserved-prefix and mapping
collisions, wildcard imports, reflective ambiguity, ambiguous function rebinding, and syntax
whose binding semantics are not supported. Golden and metamorphic tests cover module, class,
function, lambda, comprehension, exception, pattern, nested, global, and nonlocal scopes.

`correction-ranking-v2` fits exactly six declared scalar features plus 384 semantically named
canonical-source embedding dimensions. Raw diff counts, task embeddings, query/delta cosine,
and every excluded input remain outside the fitted representation. Encoder-version dispatch
preserves the D2 v1 byte contract and prevents mixed-version neighbour search. Matrix projection
and validation inspect all 390 fitted dimensions for allowlist, finite/range, identity,
duplicate/near-duplicate label, and perfect-separation violations.

Explicit-selection identity revision 3 binds the feature schema, selection role, surface,
campaign, transitive group mapping, exact member hashes, and canonical partition digest. The
artifact-stored manifest extends the existing split-manifest role, refuses a mismatched existing
dataset, leaves the D2 legacy identity readable, and requires no migration. The corrected OOD
contracts bind every case to its source group, transformation/composition, seed, candidate set,
and manifest. Decisions are now exactly answered plus abstained, while the four candidate
outcomes per decision are reported separately with both all-decision and answered-only error
rates.

The versioned campaign receipt binds bundle identities and hashes, feature seal/root/schema,
selected members, partition, mode, and exact candidate order. Replay validates these bindings
against the current campaign. The single effective-remainder API excludes sealed skips from the
ordinary remainder, reruns only exactly named missing outcomes, and reruns a whole unsealed task.
Repeated resume is stable. The existing event payload and migration `0015` remain unchanged.
The two new receipt contracts are included in the public reality schema export.

## W1 diagnostic and continuation

The frozen D2 diagnostic executed 60 cases with four independent candidate outcomes each and
reproduced the released behavior: clean answered/abstained `9/1`, clean first-choice rate
`0.9`, combined answered/abstained `8/2`, 20 accepted labels, and one confident error. All 240
v1 feature-seal hashes reproduced. The evidence records every case, candidate, raw hash, scalar,
all 384 named embedding dimensions, cosine, neighbour, ranking, confidence, abstention, and
verifier label. It is development-only, derives no threshold, records zero D3
calibration/final/canary access and zero D2 writes.

The observed movement was confined to the pre-registered lexical, candidate-delta,
query-cosine, and diff-shape channels. No structural or test-boundary failure occurred. The v2
exact-invariance replay checked all 240 spent-D2 excluded-input cases with zero failures, so the
typed S21D3-027 outcome is `proceed`; S21D3-028 and W2 preparation are open without an improvised
feature branch.

The seeded W4-F3 vertical fixture wrote real content-addressed artifact bytes and metadata,
sealed v2 features at `09:00Z`, recorded the first outcome at `10:00Z`, and recorded the sequence
receipt at `10:01Z`. A new post-outcome seal was refused. Restart replay reproduced the feature
seal and dataset record, preserved the stored seal time, resolved identical receipt/dataset
members, verified every artifact byte and lineage, and produced an empty effective remainder.

## W1 evidence index

- [per-channel diagnostic](evidence/sprint-21d3-channel-invariance-diagnostic.json) — SHA-256
  `5d0a8a95b37afb10d0154e5ba4592a904025ef69543f4452688907b11be35df5`;
- [typed continuation decision](evidence/sprint-21d3-diagnostic-continuation.json) — SHA-256
  `5e37210f93670e2c4e24324487d2701aa7e92d0dbe884ed23c2a65839d666008`;
- [v2 seal and resume proof](evidence/sprint-21d3-v2-seal-resume.json) — SHA-256
  `2953cc7f9a80bc9f6bcd2d5ab43130fd5cc6111f66775af6ebcad3c93bf8d382`.

All three carry the immutable pre-registration SHA-256
`191b3757ded21a1c2c85459a34902f8dee3f2f35b0979b557f84c1a37fe6a191`; the automated chronology
check accepts all three.

## W1 validation

Focused final W1 validation passed `62` tests. The complete repository suite passed `3101 passed,
107 skipped` in `216.02s` with zero failures in the permitted execution environment. Required
Ruff lint and format checks, contract-schema export, repository-language, pre-registration
integrity, three-file chronology, and diff-whitespace checks also pass. W1 added only the two
public receipt JSON schemas; it changed no event field, database migration, predecessor artifact,
calibration/final/canary body, and used no provider, network, credential, or GPU.

Draft-PR CI then exposed two boundary defects that the dependency-complete local environment had
masked. Bandit rejected assertion-based revision-3 authority narrowing, so the dataset service now
uses an explicit runtime authority check that cannot disappear under `python -O`. The
`experience-graph-core` lane also has no SQLAlchemy by design; `LearnedArtifactStore` had typed its
dependency as the concrete PostgreSQL-backed `ArtifactService`, making a filesystem-only fixture
import PostgreSQL transitively. It now depends on the existing `ArtifactStorePort`. The exact
603-test experience/learning lane passes locally, and the W1 fixture also passes with every
`sqlalchemy` import deliberately refused.

## W2 fresh correction evidence

W2 executes S21D3-030 through S21D3-039. The corpora are new, the campaign is new, and the
result is a **null selection**: the revised feature contract is exactly invariant on fresh
evidence, and no setting in the frozen grid is selectable on it. Final A, final B and canary
were never opened; the independent retrieval branch stays open for W3.

### Authored corpora, separation, and the seal

Twenty fresh four-candidate calibration groups and one vertical-slice fixture were authored in
`reality_task_specs_d3.py`, plus an overproduced pool of sixty failed/success retrieval groups in
`reality_retrieval_specs_d3.py`. Every body was executed rather than declared: 210 correction
runs and 120 retrieval runs, all matching their declaration — 21 baselines pass their visible
suites and fail their hidden ones, 42 declared repairs pass both, 42 partial fixes pass visible
and fail hidden, and each of the sixty retrieval pairs has a failed state the verifier rejects
and a repair it accepts.

Separation is clean over all 850 candidate bodies of the C3, D2 and D3 corpora: zero cross-group
near-clone collisions on either detector, zero groups crossing any role, and a seeded restatement
is still caught. The ten intra-pair structural matches are a retrieval group's own two states,
which is the edit path the graph projection derives rather than two tasks.

The seal reuses D2's four released catalogues by carrying their objects, so the fitting, final A,
final B and canary hashes are identical to the ones S21D3-004 bound rather than merely equal to
them. Fresh calibration is sealed under D3's own seed and generator path.

| Role | Groups | Slots | Origin |
|---|---:|---:|---|
| fitting | 50 | 200 | carried from D2 |
| calibration | 20 | 80 | authored for D3 |
| final A / final B | 30 / 30 | 120 / 120 | carried from D2, unopened |
| canary | 5 | 20 | carried from D2, unopened |
| retrieval pool | 60 | — | authored for D3, unopened |

The two revision-3 transformation submanifests hold 120 calibration cases and 360 promotion
cases — six for every one of the sixty final groups, so the reserve the manifest-order rule
selects from at S21D3-060 is visible now rather than chosen later. D3 seal hash:
`96d9937f8190d5ec63ab7037bff7cbf4cfaca99ff3b6441e8e472acd8b19db4c`.

### Vertical slice, seals and campaigns

The slice ran `d3_fixture.trim_suffix`, a group in no partition, from package through v2 feature
seal, sandboxed self-play, hidden-verifier labels, receipt, role-bound observation, revision-3
dataset identity, fitted matrix, k-NN ranking and restart replay. The ranker abstained
(`below_confidence_floor`) and the deterministic order stood; the dataset rebuilt to the same
identity and the receipt's effective remainder was empty.

280 v2 feature records were sealed before the first container of their partition started, and
both partitions then executed under `label_all`: 200 `SELF_PLAY` outcomes over the exact 50
fitting groups and 80 over the exact 20 calibration groups, acceptance 0.5 in both, zero
baselines passing hidden verification, zero `REAL_GOVERNED_RUN` rows anywhere.

The campaign was then re-run as a receipt-aware resume. All 350 recorded run identities replayed
without a new container, both feature seals reproduced their recorded hashes byte for byte, both
dataset identities reproduced, and the effective remainder was zero on both partitions. That is
S21D3-025's receipt boundary exercised on a real campaign rather than on a fixture.

Two immutable revision-3 datasets were materialised — fitting `183a0c6d-1bdb-5eaa-9fde-4da1515f9335`
and calibration `04fff167-542c-5285-b39d-8c4f0fc36ea0`, both rebuilt identically — and the fitted
matrix was built from the fitting snapshot alone. All eleven scans pass over **390 fitted
dimensions**: allowlist, finite/range on every scalar and all 384 embedding dimensions,
chronology, source chain, group split, contradictions, near-duplicates (highest cross-split
similarity 0.984172 against a 0.999 floor) and perfect separation on both splits.

Both datasets carry `CorpusRole.TRAINING`. The released enum's other value is `evaluation`, which
calibration is not; what separates them is revision-3 identity — partition, split and selection
digest — so no new corpus role and therefore no migration is needed to keep them two datasets.

### Fresh metamorphic set

All 120 sealed calibration cases resolved: six per group over twenty groups, none inapplicable,
480 transformed candidates executed against their own hidden suites, and **zero verifier label
changes** — every transformation preserved every label it was supposed to preserve. Every
transformed feature record was sealed before its transformed candidate ran.

### Ladder, grid and selection

The strongest deterministic rung is `lexical_similarity` at **0.5**. `frozen_minilm_cosine` is
reported ineligible with its reason: v2 removes the query-to-candidate cosine from the fitted
representation, so the channel that rung orders by does not exist under it. The graph rung stays
ineligible for the released reason.

All 24 frozen settings were measured. The intervention worked on the question it was designed
for and failed on a different one:

- **action preservation is 1.00 for every setting**, across all six transformation cases;
- equivalence coverage never falls below clean coverage — maximum loss 0.00;
- the strongest setting reaches **0.65** clean first-choice against the 0.5 baseline, with 0.95
  coverage and 14 changed decisions, so the signal is real;
- but every setting that answers is confidently wrong on some semantics-preserving case — 12 to
  36 confident errors of 120 decisions — and the contract allows exactly zero.

No setting survived. `decide_continuation` records `fail_and_stop` with failure kind
`ood_deficient`, and S21D3-039 records an immutable null selection. Maximum measured inference
was 34.267 ms against the 250 ms budget.

This is not D2's finding repeated. D2 could say only that *something* moved under an opaque
combined perturbation. D3 separates the two questions: the alpha-normalised source encoding is
exactly invariant — the same contract spelled differently reaches the same first action every
time — and what remains is absolute ranking accuracy, which at 0.65 cannot produce a
zero-confident-error metamorphic set. A capacity residual, not an invariance one.

Per §10.2 the null leaves final A, final B and canary unopened and opens no parametric rung. The
`dependent_not_opened` list in the selection record names S21D3-051, -054, -056, -059, -060
through -069 and -070 through -077. Retrieval continues independently in W3.

### W2 findings

| ID | Subject | Observed | Action |
|---|---|---|---|
| W2-F1 | the v2 canonical-source embedding | The frozen MiniLM reads 256 word-pieces; all 280 canonical `ast.dump` texts tokenise to 284–1549 pieces, median 654. Fed whole, the model saw the docstring and the signature and discarded the body, so eight distinct candidates produced three distinct embeddings and the vertical slice's matrix reported identical rows carrying both labels. | The canonical bytes are embedded in 400-character windows and mean-pooled, renormalised onto the unit sphere. Same declared input, same model identity and revision, same channels, same 384 dimensions — the encoder now receives the input the contract says it embeds. 16 distinct signatures on the same fixture afterwards. |
| W2-F2 | the baseline ladder | `deterministic_static_ordering` read `added_line_count`, `ast_node_count` and `hunk_count`, and `frozen_minilm_cosine` read `query_to_candidate_cosine` — none of which exist in a v2 vector. Two of four eligible rungs would have raised on the D3 calibration matrix. | The ladder dispatches on encoder version: the static rung reads the v2 structural columns and keeps its "smallest edit first" prior, and the cosine rung is reported ineligible with its own reason instead of being scored on a column that is gone. |
| W2-F3 | `calibration_ood._retoken` | The released token-stream rename also renamed the module part of `from step_gaps import step_gaps`, so a task whose module and function share a name was perturbed into `from q0 import q0` and its suite failed to collect. Sixteen of 480 transformed candidates changed label for that reason and none other. | The module path of an import is guarded like an attribute. Zero label changes afterwards. The metamorphic set was re-sealed and re-resolved under the fixed generator; the discarded resolution influenced nothing, because the selection rule is frozen and deterministic. |
| W2-A5 | `calibration_ood._retoken` | The same primitive renamed attribute names, so a module binding a local called `items` and calling `counts.items()` was perturbed into a module that does not run — and would not have been the same canonical source either. | Attributes are skipped at the shared function. No D2 calibration group is affected, so the released W1 diagnostic still reproduces; six training, one final-A, one final-B and one canary group would perturb differently, and none of those has been perturbed yet. |

Authoring defects W2-A1 through W2-A4 — a declared repair that handed the remainder to the wrong
shares, a baseline whose second edge case was never actually broken, fourteen bodies colliding
with C3 or D2 shapes, and two failed states that passed their own suites — are recorded in the
corpus evidence's defect ledger. All were found by execution or by a detector, none by reading.

### W2 evidence index

| Evidence | SHA-256 |
|---|---|
| [corpus](evidence/sprint-21d3-corpus.json) | `60a9493e52e4fa68833dc659bd4afec4234c5674ba03d3ed839951550a5dcbfd` |
| [separation](evidence/sprint-21d3-separation.json) | `e450634efee088e4fa30e141200d9b78ccca097800e67f07ed5b1e2f3f2dbd7a` |
| [sealed manifests](evidence/sprint-21d3-sealed-manifests.json) | `5d267fe27538937dd07eb44b3622228b60084bdf5b0fa3004446a1efdb378ced` |
| [vertical slice](evidence/sprint-21d3-vertical-slice.json) | `85b1aec2a64221b2d11af2e0ff805748857cfbef54c83c8fb7fa856b8f678c1d` |
| [self-play campaign](evidence/sprint-21d3-self-play-campaign.json) | `ea48783e6d4e142afd8771a79f4b9a9dcb157f6094910fd34d4e49948ace1167` |
| [calibration metamorphic](evidence/sprint-21d3-calibration-metamorphic.json) | `e3228af759388b05a8d9ff6516ea1d744d3026ceec37ed624f4a76c9686511c5` |
| [learner selection](evidence/sprint-21d3-learner-selection.json) | `216b196f491af5f9f128ba93a6193831b0ab4ebb84ad9cbe4476df554d756b5f` |

All five chronology-bound files carry the immutable pre-registration SHA-256
`191b3757ded21a1c2c85459a34902f8dee3f2f35b0979b557f84c1a37fe6a191`, and
`--check-chronology` accepts all five. The three operator commands are:

```bash
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run python scripts/corpus_d3.py
UV_CACHE_DIR=... uv run python scripts/reality_campaign_d3.py --model <frozen-minilm> \
  --output docs/.../sprint-21d3-self-play-campaign.json \
  --vertical-slice-output docs/.../sprint-21d3-vertical-slice.json
UV_CACHE_DIR=... uv run python scripts/learner_selection_d3.py \
  --campaign docs/.../sprint-21d3-self-play-campaign.json --model <frozen-minilm>
```

### W2 validation

The complete repository suite passes with zero failures, as do Ruff lint and format, the
contract-schema export check, the pre-registration integrity and five-file chronology checks, and
the tracked-file secrets scan. A new focused module,
`tests/cognitive_os/learning/test_d3_corpus_and_transformations.py`, pins 37 cases: both
`_retoken` guards, the two rename maps' independence, the hard-coded oracle, the six-case
canonical invariance of all 21 authored groups, the embedding windows and pooling, the ladder's
encoder dispatch, and the seal's counts, disjointness and reuse-by-hash.

W2 added no database migration, no event field, no new corpus or artifact role, no dependency and
no provider, network, credential or GPU call. Migration stays at `0015`. The four predecessor
Artifact Store pairs received zero writes, and the campaign reports zero worktree mutations.

Draft PR [#221](https://github.com/palkouser/cognitive-os/pull/221) carries the W2 commit at head
`fa32c550f58c`; its CI run `30979833725` completed **30 of 30 jobs successfully**, so the lanes
that caught W1's Bandit and SQLAlchemy boundaries are green on this wave without a follow-up fix.
