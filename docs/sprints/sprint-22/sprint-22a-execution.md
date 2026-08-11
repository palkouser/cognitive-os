# Sprint 22A execution log

- Branch: `sprint-22a-groundwork`
- Backlog: [Sprint 22A Technical Backlog](sprint-22a-technical-backlog.md)
- **W0 closed.** S22A-000 through S22A-005, S22A-010 and S22A-011, and S22A-013 through
  S22A-019 are done. The groundwork is tested and merged-ready, both §2.2 governance decisions
  are on the record, and revision 1 is published with `measured_values: 0`. **No threshold
  moved, no migration was allocated, and no released domain changed.**
- Pre-registration: revision 1, SHA-256
  `dc40727db85be1cebef88220fc74624af0bfd6f84204979ce3914072a75bbafb`
- Predecessor: `sprint-21-learning-baseline`, verified live — annotated tag object
  `3025082526cef6d9…`, peeling to `3f5d7379caf85290da45885e22138506211bee2e`; post-merge
  exact-head CI run `31476479587` re-read from the API, **30 of 30 successful**. Gate L2
  passes 29 of 29; Gate D1 conditions 6, 7 and 15 are closed. 22A's dependency is discharged.
- Migration head: `0015`, unchanged. `0016` remains unallocated and is a **refusal**, not a
  plan item.
- Wave commit `82cad8b`, pull request **#231** against protected `main`; CI run
  **`31485332864`** on that exact head, **30 of 30 jobs successful**. The merge is the gate
  owner's, not the wave's — W0 leaves the branch reviewable rather than merged.
- **Three findings, two of them defects in the groundwork this wave was written to test, and
  both fixed inside the wave.** See W0 findings.
- W0 measures nothing and registers nothing. It establishes the authority every later wave is
  bound to. Gate L2 and Gate D1 are untouched: 22A opens no condition and closes none.

---

## W0 outcome — the groundwork executed, two decisions taken, one revision frozen

Three scripts, five sealed records (four written here plus the carried groundwork survey),
three test modules, **three findings** and one advisory that constrains W3.

Unlike every D-series W0, this wave had no threshold in front of it and asked the gate owner
for no amendment. What it asked for instead was a **decision it was forbidden to drift into**
— whether 22A takes the D7 handoff's cheap win — and the answer was to defer it under its own
record rather than to fold a released-runtime change into a sprint about domain registration.

### S22A-005 — the groundwork, executed rather than read

The backlog's §1.2 was explicit that `descriptors.py` and `domain_survey_22a.py` were
"written and verified, **not yet merged and not yet tested**". Three test modules now exist
and CI runs them:

| Module | Tests | What it holds |
|---|---:|---|
| `tests/cognitive_os/domain/test_domain_descriptors.py` | 43 | the id grammar, closed-world validation, the package boundary, the released adapter |
| `tests/cognitive_os/domain/test_domain_survey_22a.py` | 7 | the sealed survey reproduces; the 9/57 coupling fence |
| `tests/cognitive_os/domain/test_sprint_22a_w0_evidence.py` | 16 | the four W0 seals, and both `--check` validators |

Two properties in that table are worth naming because they are the sprint's fences rather
than its tests. The **coupling recount** (9 modules, 57 references, counted from the AST of
`src/cognitive_os`) now runs on every CI job, so §3.5's silo regression exists from W0 rather
than from W3 — a wave that adds a `DomainKind` branch fails before it can claim a pilot
registered without one. And the **compatibility hashes** are asserted against the sealed
survey record, never against constants typed into a test, so an authorised change to a
released domain re-binds a record instead of editing a literal (W4-F1).

The survey reproduction check compares every measured field and deliberately excludes
`recorded_at` and the seal over it, so it cannot fail because a clock moved (W2-F1/F2).

### S22A-000 and S22A-002 — the starting point, read from the authority that owns it

[`sprint-22a-baseline.json`](evidence/sprint-22a-baseline.json), integrity
`86ac7a4924005ef3…`.

| Fact | Result |
|---|---|
| `sprint-21-learning-baseline` resolves remotely as an annotated tag | yes, object `3025082526cef6d9…` peeling to `3f5d7379caf85290…` |
| local and remote tag handles agree | yes |
| branch descends from current `origin/main` | yes, one commit ahead |
| both 22A outcome tags | **absent**, checked rather than assumed |
| D7 exact-head CI run `31476479587` | re-read from the API, **30 of 30 successful** |
| branch protection | administrators enforced, 27 required checks, strict, no force pushes, no deletions |
| migration head | `0015` |
| **eleven** predecessor artifact roots | fingerprinted; the nine with a live released expectation match it |
| stores written to by W0 | **none** — W0 provisions nothing, because 22A's own store is W1's item |

The two D7 roots are the wave's first finding, below.

### S22A-010 and S22A-011 — the two §2.2 decisions, priced by recomputation

[`sprint-22a-decisions.json`](evidence/sprint-22a-decisions.json), integrity
`7eebcc9c90538fc1…`. **Thresholds changed: 0. Measured values: 0.**

**(a) The rung as product — deferred under its own record, not refused.** The either/or was
put to the gate owner with both branches priced out of D7's sealed evidence rather than
described, and the prices are recomputed from
[`sprint-21d7-ladder-ruling.json`](../sprint-21/evidence/sprint-21d7-ladder-ruling.json) and
[`sprint-21d7-runtime.json`](../sprint-21/evidence/sprint-21d7-runtime.json) at write time, so
a record that drifts from the evidence it cites fails its own `--check`:

| pool | containment ordering | released fallback (`lexical_similarity`) | strongest released rung |
|---|---:|---:|---|
| D5 calibration | **0.92** | 0.41 | `fixed_input_order`, 0.42 |
| D6 certification | **0.84** | 0.62 | `lexical_similarity`, 0.62 |

What made this a decision rather than a free win: the released runtime's deterministic
fallback is **gate evidence**. Condition 23 is closed on a record that names the lexical
ordering and reports all seventeen fallback codes reached, so swapping the advisory re-opens
that condition and needs its own evidence trail and its own replay. 22A's four exit criteria
say nothing about the correction surface. The margin is not lost, it is **unspent**, and any
successor may take it under its own record.

**(b) The steady-state door stays closed**, recorded as a decision rather than left as a
default. The component keeps routing its five canary groups; the sealed canary→steady
transition condition remains the named key, and taking it is a separate governed decision.

### S22A-013 through S22A-019 — revision 1

[`sprint-22a-contracts.json`](evidence/sprint-22a-contracts.json), integrity
`fe579caa439ed558…`, and
[`sprint-22a-pre-registration.json`](evidence/sprint-22a-pre-registration.json), integrity
`660aeaa9152c2349…`.

The D-series pre-registered learners. 22A fits nothing, so revision 1 freezes **a vocabulary
and a refusal**:

| Contract | Item | Hash | What it freezes |
|---|---|---|---|
| `descriptor_schema_v1` | S22A-013 | `a8c2f6a273f298df` | the schema (`d34d4e0b89accb74…`), the grammar, the 64 KiB ceiling, the pilot-only claim rule, and that identity is (`domain_id`, `revision`) |
| `enum_reading` | S22A-014 | `e50bad883d849dc2` | §2.3: the enum survives as the adapter's closed vocabulary; no new member; the coupling may not grow |
| `pilot_domains` | S22A-015 | `2749f6dea0ba90c4` | `engineering.mechanics` and `science.chemistry`, and that neither may be substituted after a failure |
| `backward_compatibility` | S22A-016 | `aad2b883f4a8bfba` | the four compat hashes and the registry snapshot hash, read from the sealed survey |
| `storage_without_a_schema` | S22A-017 | `b4c5efdb2268a3ff` | head `0015`, `0016` as a refusal, and the startup-rebuild hash check |
| `exit_and_decision_tree` | S22A-018 | `90ee948340298705` | the four exit criteria as the gate, and five endings that may not be chosen after the evidence |

Freezing the pilot ids is the one that would be easy to skip and expensive to lose: answering
"does a domain register?" by choosing an easier domain after seeing how the first one went
measures the chooser, not the registry.

The publication's `--check` re-derives the descriptor schema hash **from the live module**, so
a wave that widens the contract to admit a pilot fails the check rather than the review.

---

## W0 evidence index

| Record | SHA-256 | Integrity | Items |
|---|---|---|---|
| `sprint-22a-domain-survey.json` (carried) | `5b6be6a4c4554d5c…` | `298233818691b90d…` | groundwork |
| `sprint-22a-baseline.json` | `18f27686f342da90…` | `86ac7a4924005ef3…` | S22A-000, S22A-002 |
| `sprint-22a-decisions.json` | `e012567f36061100…` | `7eebcc9c90538fc1…` | S22A-010, S22A-011 |
| `sprint-22a-contracts.json` | `7698e205220ee236…` | `fe579caa439ed558…` | S22A-013 … S22A-018 |
| `sprint-22a-pre-registration.json` | `dc40727db85be1ce…` | `660aeaa9152c2349…` | S22A-019 |

Scripts, none of them released: `baseline_22a.py`, `decisions_22a.py`,
`pre_registration_22a.py`. The `*_d2` through `*_d7` families stay exactly as they are.

`src/cognitive_os/domain/descriptors.py` as W0 merges it: `5e39ff688b52246d…`. It is **not**
the module the baseline fingerprinted — W0-F2 and W0-F3 were fixed after the baseline was
taken and before the publication, and the contract record says so rather than letting the
baseline move to match.

---

## W0 findings

### W0-F1 — the only released fingerprint of D7's own store describes a state D7 left behind

`sprint-21d7-authority-isolation-after.json` was written in **D7's W0**, at
`2026-08-10T13:31Z`, and fingerprints `artifacts-s21d7` as empty because at that moment it
was. D7's W1 through W3 then wrote **173 files** into it and no later record re-took the
fingerprint. `artifacts-s21d7-measured` — the store D7's measured campaign actually lives in,
**2511 files** — was never named by any released record at all.

So the two roots holding the bytes behind a released, tagged sprint were under no freeze. This
is the third consecutive sprint to find it: D6 found it as `artifacts-s21d6-measured`, D7
found it again, and each time the successor froze it.

**Handled, not patched.** 22A freezes both as first observations and names the stale
expectation explicitly rather than editing D7's sealed record to agree (W4-F1: an authorised
change re-binds, it does not edit). The nine roots with a live expectation all match it, and
`unexplained_drift` is empty. The recurrence is a standing weakness in the freeze discipline —
**the after-phase fingerprint is taken before the sprint's own waves run** — and the fix
belongs to whichever sprint next writes an isolation-after record, which is 22A's W4.

### W0-F2 — a package could claim `active`, which is a promotion it did not earn

`DomainLifecycleState`'s own docstring says *"`PILOT` is the only state a fresh package may
claim; promotion beyond it is a governance decision with evidence"*. Nothing enforced it. A
hostile package declaring `"lifecycle": "active"` validated cleanly through
`validate_domain_package`, arriving with the promotion as well as the domain — through exactly
the door §3.5's rejection suite and both pilots use.

**Fixed inside the wave.** The boundary now refuses any lifecycle but `pilot`, with a
diagnosis. The released four are unaffected and the rule costs them nothing: the adapter
builds them as contracts directly and never parses them from a package. A pleasant
consequence, now a test: **a released domain's descriptor, serialised and offered at the
package door, is refused** — the lifecycle is the one thing an impersonating package cannot
bring with it.

### W0-F3 — `shared_with` admitted the same domain twice

Concept ids, related domain ids and problem types were all deduplicated; the sharing list was
not. A concept naming `physics` twice is a cross-domain view that disagrees with itself about
how many domains expose an item — precisely the count W2's "stored once, exposed through
multiple governed views" claim rests on.

**Fixed inside the wave**, in the same validator, with a test.

### W0-A1 — the package boundary accepts a released domain id, and must

A package claiming `domain_id: "coding"` at revision 1 validates. This is **correct at this
layer** and is recorded so W3 does not discover it as a surprise: the boundary parses bytes
into a contract and has no business knowing what is registered. The impersonation refusal
§3.5 requires — *revision supersession is a governance path, not a package upload* — belongs
to the **registry**, at registration, alongside the re-registration refusal. W3's rejection
suite must exercise it there. W0-F2's fix raises the price of the attempt but does not close
it: a package may still impersonate a released id **as a pilot**.

---

## W0 validation

Every gate below was run on the exact tree this wave commits.

| Gate | Result |
|---|---|
| `ruff check --config ruff.cognitive-os.toml src tests scripts infra` | all checks passed |
| `ruff format --check` over the same paths | 1184 files already formatted |
| `mypy src/cognitive_os` | success, no issues in 633 source files |
| `bandit -r src/cognitive_os` | 0 issues at every severity |
| `python -m cognitive_os.schemas.export --check` | contract schema check passed |
| `scripts/check_repository_language.sh` | passed |
| `pytest -q` (whole repository) | **4156 passed, 217 skipped** |
| `scripts/decisions_22a.py --check` | 2 decisions verified, 2 priced D7 records verified |
| `scripts/pre_registration_22a.py --check` | 6 contracts, 3 W0 children, 4 compat hashes, schema unchanged |
| `detect-secrets-hook --baseline .secrets.baseline` | clean; the baseline was regenerated for the hash-dense evidence |

The `--check` validators are not left to run by hand: `test_sprint_22a_w0_evidence.py` invokes
both, so every wave of this sprint executes them without choosing to.

---

## What W0 did not do

- **registered no domain, authored no pilot package and built no seam.** `descriptors.py`
  still registers nothing at runtime and routes nothing; the registry seam is W1;
- **provisioned no store and allocated no migration.** Head stays `0015`;
- **touched no released domain.** The four compat hashes and the registry snapshot hash are
  the ones the groundwork sealed;
- **touched nothing that learns.** The live correction component keeps routing its five canary
  groups, the conformal bar and admitted set are where D7 left them, and the deterministic
  fallback is still `lexical_similarity` — by decision, now, rather than by default;
- **opened and closed no gate condition.** Gate L2 stays at 29 of 29 on D7's evidence.

## What W1 needs, and what would stop it

W1 builds the registry seam and artifact-backed storage, and its first act is the **vertical
slice** of §4.1: one fixture descriptor through package bytes → boundary → artifact store →
**process restart** → registry rebuild → problem-type resolution → a tampered-byte refusal.
The restart is not decoration; it is the one place "storage without a schema" can silently
become "state in memory", and D7's lifecycle lesson was that separate processes are the only
proof.

W1 inherits three fences and one open question:

- the **compat hashes and the registry snapshot hash** — the released four must not be able to
  tell the seam exists, and the assertion names the sealed record rather than a literal;
- the **coupling recount**, already running in CI, which fails if the seam grows a
  `DomainKind` branch instead of removing one;
- the **`0016` refusal** — a wave that finds itself allocating a migration has left the
  sprint's contract and stops rather than proceeds;
- and W0-A1: where the impersonation and re-registration refusals live. W1 builds the registry
  that will have to hold them, so it should seat them there rather than leave them to W3 to
  discover.

The stop W0 considers most likely is still the one the backlog named — a pilot whose honest
verification floor cannot be met by deterministic kernels — and it belongs to W3, not to W1.
