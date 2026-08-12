# Sprint 22A handoff — a registry that reads its domains, and the enum that outlived it

- Predecessor for Sprint 22B: this sprint, branch `sprint-22a-groundwork`, PR **#231**,
  outcome tag **`sprint-22a-domain-baseline`** (created on the post-merge commit, after
  exact-head CI — see [the report](sprint-22a-report.md) §6)
- Exit criteria: **4 of 4 met**, in
  [`sprint-22a-exit-criteria.json`](evidence/sprint-22a-exit-criteria.json)
- Migration head: `0015`. Sprint 22A allocated none, and `0016` is still unallocated
- Pre-registration: revision 1, `measured_values: 0`, **no revision after W0**

---

## 1. The one sentence

**A domain is now a package of bytes that a fail-closed boundary either admits or refuses**, and
the four released domains cannot tell that two more registered — but a descriptor domain is a
*resolution-table citizen*, not an enum member, and everything the released system gives an enum
member it still withholds from a pilot.

That second clause is the whole handoff. Sprint 22B inherits a registry it can enumerate
domains from; it does not inherit a system in which those domains are first-class.

## 2. What was measured, in the order it matters

| Claim | Value | How it was decided |
|---|---:|---|
| `DomainKind` references, with both pilots registered | **52** | AST census, recomputed by the sealed survey's own function |
| References added by two pilots | **0** | the same census against W3's count |
| `released_snapshot_hash()` | `00187f2b…` unchanged | recomputed in a process where both pilots are registered |
| Released descriptor hashes | **4 of 4** unchanged | derived through the adapter, compared to W0's seal |
| Controller modules identical to the branch point | **11 of 11** | byte comparison against `c5119cc`, over a sealed file set |
| Migration files identical to the branch point | **15 of 15** | the same, and the set is sealed so a sixteenth is a refusal |
| Hostile packages refused | **10**, four layers | executed against 22A's store, entries unchanged after each |
| Replay | **6 manifests, 248 cases, 1.0** | executed by the exit-criteria check, not carried |
| Concepts owned / shared / private | 6 / 4 / 2 | the target's view compared to the sharing declaration |

## 3. The three findings a successor should read before its own W1

**W2-F1 — check which registry a handoff means.** W1 handed W2 a question premised on the
domain registry's `snapshot_hash()` being bound into released records. It is not; that hash
belongs to a different registry with a similar method name, and the domain registry's had no
production caller at all. The premise was corrected by counting callers from the AST with the
*receiver* kept, because several registries publish a method of that name. A handoff sentence is
a claim, and this one was wrong.

**W2-F3 — a released assertion can assume the world cannot grow.** Two of them did: a floor of
"at least two skills for every problem type" and a released-domains block reading the
whole-registry hash. Both passed for three waves and failed the moment a pilot registered, and
only the *whole suite with a pilot registered* found them. If 22B changes what the registry can
contain, run everything, not the slice.

**W4-F1 — count what "per-domain" covers, do not read it.** Three waves ran four manifests and
called it per-domain replay across four released domains. The coding domain's manifests are
named for a different sprint and were never in the set. The fix is one line of coverage data and
a test that asserts the four; the lesson is that a claim about *coverage* has to name the things
covered.

## 4. What Sprint 22B inherits, and what it must not assume

**Inherits, usable without re-deriving:**

- **a registry keyed by string domain id**: `ProblemTypeEntry.domain_id` is the general
  identity, `domain: DomainKind | None` is the released adapter vocabulary, and
  `registry.domain_ids()` / `problem_types_for()` enumerate what is there. A million-item scale
  test can walk it;
- **a fail-closed package boundary** with a 64 KiB ceiling and five ordered refusals, and a
  registry door that refuses released-id impersonation, empty problem-type sets, duplicate
  `(domain_id, revision)`, missing kernels and problem-type collisions — every one decided
  *before* an entry is written;
- **storage without a schema**: content-addressed package artifacts plus
  `domain.descriptor_registered` events as the index, rebuilt cold at startup with a refusal on
  a tampered byte that names the domain rather than a storage key;
- **the descriptor spine** — `DomainDescriptorV1`, concepts with `OWNED`/`SHARED` exposure,
  `concept_owners()`, `concept_views()`, `validate_shared_concepts()` — which 22C's campaign
  manifests can bind to;
- **two worked pilots as templates**: a committed package file, a kernel table, and checkers
  whose independent route is a different computation rather than the solver's own arithmetic
  re-run.

**Must not assume:**

- **that a pilot can be run and recorded like a released domain.** W2-A1: `domain_pilot_runs`
  has `CHECK (domain IN ('mathematics','physics','logic'))` in its schema and
  `record_domain_pilot_run` refuses everything else — it never learned about `coding` either.
  There is no persisted-run path for a descriptor domain, and creating one is a migration;
- **that a pilot can reach the Cognitive Controller.** `run_case_controlled` takes a
  `DomainBenchmarkCase` whose `domain` is a `DomainKind`, mapped through two per-domain tables.
  Both pilots run end to end through `domains.solve` and `domains.checker` — which resolve by
  problem type alone — and stop exactly there;
- **that a released domain can refuse a view.** W3-A1: released descriptors are derived by the
  adapter and carry no `related_domain_ids`, so reciprocity is asked of pilot targets only. A
  rule that demanded it of the released four would forbid every share a pilot makes;
- **that two pilots make the registry general.** Both lean on unit-carrying deterministic
  verification. A domain whose honest verification floor cannot be met by deterministic kernels
  is 22C's question, and 22A's own definition of done calls attempting it here a stop;
- **that a capability name is enforced by naming it.** W3-A2: the only authority on what a
  checker emits is running it. A static declaration on the kernel would be a second copy of the
  truth, free to drift, and would move a real refusal to a layer that only agrees with itself;
- **that a digest proves usability.** D7's W3-F1, carried and used twice here: W4 executed the
  six manifests and the six sealed refusal cases rather than binding their hashes.

## 5. What this handoff refuses

**Not a `DomainKind` removal.** §2.3's reading is a fence, not a dissolution. The enum is the
closed vocabulary of the released four, and the day a fifth domain needs what only its members
get, that is a finding for a successor's contract — not a quiet exception.

**Not a promotion path.** Both pilots are `lifecycle: pilot`, the only lifecycle a package may
claim; W0-F2 removed `active` from what a package can assert. Promotion is a governance path
somebody has to design, and 22A deliberately did not.

**Not a scale claim.** The registry can be enumerated; nothing here says what it does at a
million items. That is 22B's measurement to make, and it should make it against the enumeration
surface above rather than against the pilots.

---

## Evidence handles

| Record | Seal (`integrity_content_hash`) |
|---|---|
| `sprint-22a-pre-registration.json` | revision 1, `measured_values: 0` |
| `sprint-22a-domain-survey.json` | `298233818691b90d…` |
| `sprint-22a-decisions.json` | `7eebcc9c90538fc1…` |
| `sprint-22a-w1-seam.json` | `cdb70a979d7a92a6…` |
| `sprint-22a-w2-decisions.json` | `facaafbe78ed6476…` (S22A-030) |
| `sprint-22a-w2-pilot.json` | `9224c1468b2a94ca…` |
| `sprint-22a-w3-pilot.json` | `19994e342023e88e…` |
| `sprint-22a-exit-criteria.json` | 4 of 4 met, outcome `pass` |
| `sprint-22a-verification-matrix.json` | 0 failed, 0 skipped, 0 structural findings |
| `sprint-22a-release.json` | written by `scripts/release_22a.py` from live handles |

The per-wave evidence indexes in [`sprint-22a-execution.md`](sprint-22a-execution.md) carry the
hash of every record, including the phase records this table does not name.
