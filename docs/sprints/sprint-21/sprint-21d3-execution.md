# Sprint 21D3 execution log

- **Branch:** `feature/sprint-21d3-invariant-correction-ranking`
- **Wave:** W0 + W1 — pre-registration and invariant correction spine
- **Status:** W0 and W1 implementation complete; draft PR validation recorded below
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
  `358f1361f0b168a825effd1c9b60a0aae787078e27d99127fcd35a7ed6e2f8f0`;
- [typed continuation decision](evidence/sprint-21d3-diagnostic-continuation.json) — SHA-256
  `cc17f9f6826e2cabfbb4c88c763e8d46dd5cbf4c9731b302f5340e23fbf6024a`;
- [v2 seal and resume proof](evidence/sprint-21d3-v2-seal-resume.json) — SHA-256
  `ba2a1983430149366f0f2abe6b0aa4f7360efac57f3f0c78c4de5c917b5f205e`.

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
