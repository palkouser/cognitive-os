# Sprint 15 report

Status: Released on `main`; remote CI passed and `sprint-15-baseline` published

## Baseline and authority

Sprint 15 branches from `sprint-14-baseline`. The implementation follows the Group 3 technical
specification and preserves all Sprint 9–14 authority boundaries. PostgreSQL remains authoritative
for governed metadata, the event store retains lifecycle evidence, the artifact store owns large
content, and destination subsystems retain validation and promotion authority. No upstream
LightAgent runtime file is changed.

The implementation was merged through PR `#200` at
`1ab3591e385246a747c3b54660b833b3b30879ba` after all 22 required remote checks passed in GitHub
Actions run `29848740564`. The `sprint-15-baseline` annotated tag identifies the final
CI-validated release-report merge commit.

The factory is deterministic and post-execution. Source and provider prose remain untrusted data.
The factory cannot execute sources, acquire content over the network, write destination state,
promote candidates, upload exports, change policy, or start model training.

## Delivered scope

- Immutable source, inspection, normalization, lineage, duplicate, classification, license,
  usage-right, sensitivity, quality, item, route, package, manifest, split, export, access,
  lifecycle, and verifier contracts with generated JSON Schemas.
- Bounded local file, directory, ZIP, and TAR inspection with traversal, absolute-path, link,
  device, normalized-name collision, count, depth, size, and expansion-ratio protection.
- Fixed-order deterministic normalization for JSON, safe YAML, Markdown, text, Python, diff,
  patch, and JSONL; original and normalized bytes remain separate content-addressed artifacts.
- Exact content deduplication with distinct source attribution, advisory-only near-duplicate
  contracts, complete lineage, deterministic classification, explicit license and usage-right
  evaluation, secret detection, and twelve-dimensional reproducible quality scoring.
- Fail-closed staging, quarantine, rejection, and package-only routing across governed memory,
  semantic observation, skill, strategy, routing, weakness, benchmark, replay, negative-example,
  training, and reference destinations. Packages contain no authority claim.
- Versioned manifests, lineage-safe deterministic splits, reproducible JSONL exports, twenty
  verifier capabilities, ten lifecycle event types, access auditing, cancellation, resume, and
  in-process idempotency.
- Migration `0007` with nine Corpus Factory tables, eight append-only history triggers, validated
  initial item and manifest states, one closed compare-and-set item transition function,
  least-privilege grants, PostgreSQL repository, health checks, and backup/restore manifest fields.
- Twelve source-family fixtures plus exact Sprint 14 coverage for all nine proposed Experience
  candidate types, a 14-case CI benchmark, 56-case seed benchmark, CLI, smoke, scale, security,
  architecture, configuration, and operations surfaces.
- DVC, DataTrove, and Distilabel were evaluated and intentionally not added. Existing manifests,
  artifact storage, bounded transforms, and non-authoritative provider boundaries meet Sprint 15
  without new dependencies.

## Local validation

- Required Ruff lint and format checks passed.
- Strict MyPy passed on 408 source files.
- Contract schema drift check passed with 136 registered event types.
- Cognitive OS tests passed with **623 passed and 5 opt-in tests skipped**; contract tests passed
  **65/65**; the full repository passed with **764 passed and 34 opt-in tests skipped**.
- Corpus unit, adversarial, event-catalog, smoke, 14-case, and 56-case credential-free gates
  passed. The provider-dataset case was correctly quarantined for unknown licensing.
- PostgreSQL migration `0007` upgrade, downgrade to `0006`, re-upgrade, head verification, Alembic
  drift check, runtime grants, append-only triggers, direct-route denial, repository integration,
  health checks, and the full PostgreSQL/Controller integration set passed **23/23**.
- The deterministic smoke manifest hash is
  `2ea4a53b0ede29da75d8453e058b0f4aeaa9c7ac77a2a1d2ab41f9b4f01e8fb1`.
- The 14-case and 56-case benchmarks produced 14 and 56 unique reproducible result hashes,
  respectively, with zero provider calls, destination writes, uploads, promotions, or training
  actions.
- The CPU-only scale path processed **10,000** fixtures in **54.377 seconds** with p50 **4.861 ms**
  and p95 **5.804 ms**; 9,167 were routed and 833 provider-origin fixtures were correctly
  quarantined, with zero provider calls, destination writes, or training actions.

## Restore instructions

Apply migration `0007`, create a backup with `scripts/backup_event_store.sh`, and restore only into
an isolated `_test` database with `scripts/restore_event_store.sh --test-restore`. Corpus source,
item, route, manifest, export, access, and current-item history counts and hashes are included in
the backup manifest and restore comparison.

## Known limitations

Near-duplicate detection remains advisory and disabled by default. Only bounded UTF-8 text and
structured formats are normalized; binaries, OCR, audio, video, network sources, remote clones,
and automatic web ingestion are rejected. Provider-assisted annotations, DVC, DataTrove, and
Distilabel are deferred. A destination must independently consume and validate an emitted package;
the factory never performs that write or promotion.

## Stage-gate correction and Sprint 16 hand-off

The Sprint 15 closure originally labeled governed corpus transformation as Gate H. The corrected
roadmap defines Gate G as Sprint 14 plus Sprint 15, and Gate H as Sprint 16 plus Sprint 17. Gate G
is complete: Cognitive OS can safely transform
exact local and internal source revisions into deterministic, provenance-complete, policy-assessed
corpus packages and exports without granting source or provider content any authority. Sprint 16
may consume versioned corpus manifests, packages, classifications, quality assessments, lineage,
and access evidence, but it must not bypass destination validation, reinterpret provider prose as
fact, mutate source records, or weaken Controller, policy, verifier, event, artifact, or PostgreSQL
authority.
