# Sprint 21D1 — execution wave plan

Working plan for executing [the D1 technical backlog](sprint-21d1-technical-backlog.md).
It does not replace the backlog's `§6` wave table; it refines it against measured
repository facts: four splits along real dependencies, one missing gate inserted, one
read-only probe added. Task numbering is unchanged (S21D1-000 … -074, 54 tasks).

Status: **W0 complete**. Evidence:
[`sprint-21d1-baseline.json`](evidence/sprint-21d1-baseline.json),
[`sprint-21d1-c3-inventory.json`](evidence/sprint-21d1-c3-inventory.json).

---

## 1. Findings

| # | Where | Finding | Status |
|---|---|---|---|
| F1 | repository state | D1 planning documents were uncommitted on the already squash-merged `docs/sprint-21c3-gate-close`; the D1 feature branch did not exist. | **Fixed in W0** (W0-D3) |
| F2 | S21D1-001 | The task names a D1 pair and the inconsistent development pair, but not the third, read-only C3 source pair (`artifacts-s21c3`, 8503 files, `.env.s21c3.local`). Reading it through application services would write `corpus_accesses` / `memory_accesses` rows. | **Fixed in W0** — all three pairs and the SELECT-only access rule are recorded |
| F3 | S21D1-016 ↔ 020/022 | Circular: 016 depends on 015, 020 depends on 016 "if applicable", but the eligibility count is only known after 020/022. A late shortfall would force the canonical view to be rebuilt. | **Fixed in the plan** — read-only probe `E1.5` after 011; 020 is built once |
| F4 | `§6.1` | The first vertical slice is mandatory before bulk projection but has no task ID and no wave, so `§6`'s "no wave completes with a red P0 dependency" cannot be audited against it. | **Fixed in the plan** — standalone `VS` gate between W3 and W4 |
| F5 | W3 runnability | `z3` is not installed. `verification/factory.py:146` registers the four logic verifiers only when `find_spec("z3")` succeeds, otherwise `register_unavailable`. Without it the 10 logic runs are not verifier-backed and the registry snapshot hash diverges from CI. | **W3b entry condition** (W0-D4): `uv sync --locked --all-groups --extra verification-logic`. sympy 1.14.0, sentence-transformers, networkx 3.6.1 present |
| F6 | S21D1-066 | The D1 CI lane needs `--extra semantic-graph` plus the verification extras. The pattern exists (`semantic-memory-core`, `verifier-domains`); none of the 29 jobs covers the D1 combination. | Recorded for W6c |
| F7 | `§8.2` / S21D1-035 | "50 task signatures" = 30 coding (60 pairs over 30 tasks) + 20 fresh. **Zero margin**: one duplicated fresh signature fails the threshold. Stock is 16 `LOGIC_CASES` and 18 `MATHEMATICS_CASES`. | Hard constraint on S21D1-030 |
| F8 | `§4.7` | 64 nodes per graph. The node/edge/depth distribution of the 60 C3 trajectories is unmeasured. `§4.7` requires any bound change to be committed *before* the affected benchmark. | Size probe first in W4 |
| **F10** | `§1.2` | The C3 evidence store was never emptied between waves (C3 deviation W3-D1), so **five denominators coexist**: 214 released / 641 raw `coding.outcome_recorded` events / 960 intake observations / 500 final C3 evaluation dataset / 150 enumerated campaign runs. The backlog names only the 214↔960 trap; the 641 event count is a ~3x inflation it does not mention. | **Recorded in W0**; drives W1/W2 |
| **F11** | S21D1-034 | The 60 historical manifests are counted but not enumerated by identity in the released evidence. Derivable rule: `experience_compilations` joined to the 150 enumerated campaign run IDs yields **exactly 60 of 60**. | **Resolved in W0** — verified selector for W3a |
| **F12** | `§3.3` | The 64 governed benchmark outcomes have no per-case identity in the released C3 evidence. The 6 benchmark run IDs are not observation `source_run_id`s (0 rows); the campaign time window yields 40, not 64. If unresolvable, the eligible population is **150**, inside the 150–199 band. | **Open — first W1 decision.** Decides whether S21D1-016 runs |

Verified and correct, no action: tag `497f959b…` → peel `05809446…`; `origin/main` =
`1856b853…`; PRs #215/#216 merged with those exact merge commits; CI runs 30571166301 and
30572361952 both success on the exact heads, 29 of 29 jobs; migration head `0015`;
27 required contexts, `enforce_admins` on, 1 collaborator, 0 open PRs; development pair
fingerprint `7e85d9a6…` / 5 files; MiniLM `1110a243fdf4` healthy; every API the backlog
references exists.

---

## 2. Wave map

| Wave | Tasks | Character | Parallel | Exit gate |
|---|---|---|---|---|
| **W0** ✅ | 000–003 | evidence, no code | — | exact parent, frozen inventory, three stores separated |
| **W1** | 004, 010–015 (+E1.5) | strictly sequential | none | **one-way door**: after 014/015 the surface is frozen |
| **W2** | 016*, 020–026 | dataset + baseline | none | ≥200 eligible outcomes, ≥20 changeable decisions, strongest rung named |
| **W3a** | 034 | read-only resolution | ‖ W3b | 60/60 sources resolved, 0 bytes changed |
| **W3b** | 030–033 | real execution | ‖ W3a | 20 failures + 20 successes, 20/20 byte-identical recompilations |
| **W3c** | 035 | freeze | after W3a+W3b | 80 pairs, 3 domains, 50 signatures |
| **VS** | `§6.1` (new gate) | one pair end to end | — | 9 steps green, without legacy timestamps |
| **W4** | 040–047 | graph vertical | none | 80/80 edit-path round trips, root persisted, migration stays `0015` |
| **W5a** | 050–054 | retrieval arms | ‖ W5b | 5 arms on identical frozen queries, strongest simpler arm named |
| **W5b** | 055–057 | advisory context | ‖ W5a (after 046) | verified/advisory/non-pinned candidate, deterministic fallback |
| **W6a** | 060–062 | decision | ‖ W6b | FGW go/no-go ADR, zero unused dependency |
| **W6b** | 063–065 | operations | ‖ W6a | CLI, integrity report, restart + restore exact hashes |
| **W6c** | 066–067 | CI + matrix | after W6a+W6b | credential-free lane + full scratch-store matrix |
| **W7** | 070–074 | release | none | protected merge, exact-head CI, annotated tag, D2 handoff |

`*` 016 runs only if the E1.5 probe lands in 150–199.

**Deltas from backlog `§6`:** W3 splits three ways (034 is independent of the fresh runs);
new `VS` gate; W5 splits two ways (055 depends on 046, not on 054); W6 splits three ways;
E1.5 probe inserted.

---

## 3. Wave notes

### W0 — release authority and isolation (000–003) ✅
Branch `feature/sprint-21d1-learning-surface-emg` created from the verified `origin/main`,
four planning documents carried over. D1 pair created: database `cognitive_os_s21d1_test`
(114 tables, alembic 0015, migration check clean), `artifacts-s21d1` (0 files),
`backups-s21d1`, and a separate `cognitive_os_s21d1_integration_test` so the truncating
integration suite never sees evidence. Development pair fingerprint identical before and
after, 0 writes. C3 pair declared read-only with a SELECT-only access rule. Four deviations
and five limitations recorded without workarounds.

### W1 — draft PR and surface pre-registration (004, 010–015 + E1.5)
Order is fixed: `010 → 011 → E1.5 → 012 → 013 → 014 → 015`, with 004 first.

**First decision of the wave (F12):** resolve or quarantine the 64 benchmark outcomes.
Resolved → the population is 214. Quarantined → it is 150, inside the 150–199 band, and
S21D1-016 becomes required.

**E1.5 (new, read-only probe):** deduplication and eligibility count over the *enumerated*
campaign identities — never over `cognitive_os.events` or `learned_observations`, per F10.
No held-out metric is read. Its number decides 016, so 020 is built exactly once.

`014/015` is a **one-way door**. After it the feature schema, label, action policy, groups,
baselines and thresholds change only by a new revision, which invalidates affected results.

### W2 — primary dataset and baseline (016*, 020–026)
016 only on shortfall: at most 50 new outcomes, new groups, zero network.
Gate at 022: fewer than 200 outcomes or fewer than 20 changeable decisions keeps the gate
open; definitions are not relaxed. The four-rung ladder belongs in `learning/baselines.py`.

### W3a — 60 historical coding pairs (034)
Read-only, parallelizable. Selector verified in W0 (F11). Every pair carries
`legacy_recompilation_unavailable=true`. Artifact hashes recorded before and after.

### W3b — 20 fresh logic and mathematics pairs (030–033)
**Entry condition (F5):** `uv sync --locked --all-groups --extra verification-logic`.
`wrong_answer_for(case)` plus `run_case_with_learning(case, candidate_override=...)` for the
failing run; `FIXTURE_TIME` (2026-07-24T00:00Z) as the fixed epoch for compilation.
**F7:** 10 + 10 distinct signatures, zero margin.

### W3c — freeze the combined pair set (035)
60 + 20 = 80, 3 domains, 50 signatures, 0 group crossing, 100% source resolution.

### VS — first vertical slice (new gate, `§6.1`)
Before bulk projection. One fresh logic pair end to end: runs → exact recompilation → two
canonical graphs → edit path round trip → Artifact Store plus lineage → one frozen query →
lexical, vector and bounded graph ranking → advisory `ContextCandidate` → restart and exact
replay. Creates the minimal W4/W5 code and is the only place the full D1 authority is
testable without legacy C3 timestamps.

### W4 — graph vertical (040–047)
`§4.4` contracts into `domain/experience_graph.py`, projection and edit paths into
`experience/graph_projection.py`. **Size probe first (F8):** node, edge and depth
distribution of the 60 trajectories *before* any benchmark; if 64/128/32 is tight, the
revised policy is committed first. Default 047 outcome: migration `0016` not required.

### W5a — retrieval arms (050–054)
Five arms, identical queries, pool and exclusions. Floor: at least one bounded arm with
top-5 recall ≥ 0.70 and MRR@10 ≥ 0.50. The graph arm has no mandatory uplift threshold.

### W5b — advisory context (055–057)
Starts after 046; does not wait for 054. Additive `EXPERIENCE_GRAPH` source type; the
existing 15 `ContextSourceType` values and fixtures stay valid.

### W6a / W6b / W6c
6a: residual taxonomy → licence and dependency review → FGW ADR ("no-go" is a valid output
with zero new packages). 6b: extend `scripts/experience.py` (no second entry point) and
`coding/reality_integrity.py` (no second report); restart, backup, restore. 6c: CI lane with
`--extra semantic-graph --extra verification-logic --extra verification-math` (F6), then the
full verification matrix on scratch stores only.

### W7 — release (070–074)
Documentation → Gate D1 assessment over the 21 conditions → D1 report → protected merge,
exact-head main CI, annotated `sprint-21d1-emg-baseline` → D2 handoff. Gate L2 stays closed.

---

## 4. Stop points

1. ~~Before W0~~ — done.
2. **After W0, before W1** — current position.
3. End of W1, before the 014/015 commit — one-way door.
4. W2 / 022 — if the count misses the threshold, the gate stays open.
5. The VS gate — if it does not run end to end, bulk projection in W4 does not start.
6. Before W7 — protected merge.
