# Sprint 22E Execution Log

## W3 — the one approved change, and the two seams the first real landing opened

W3 spent the sprint's single approved change on **L7**, the entry the gate owner selected in
S22E-201: 22E's own W1-F7, repaired through the loop that found it. The driver reads that sealed
decision and refuses to run against any other entry, because a driver that hard-codes the
selection is a driver that makes it.

**The chain, and what each leg measured.** The weakness was mined from the sealed ledger
revision, a live claude-code draft was admitted by `merge_provider_draft`'s own host
verification, and the repair was applied by `deterministic_replace` in a real worktree, one
hash-chained step per file. Then the full released matrix: **nine gates ran and nine passed** in
286.5 s, including `historical_regression` over the whole suite and `compatibility` over 638
files; six gates are driver-decided and named as such. **Zero active-state mutation**, every
surface member recomputed and reported individually, with `audit_trail_moved: true` beside it —
a governed traversal that wrote no audit record would be a loop nobody can audit. Sealed in
`sprint-22e-w3-approved-change.json` (`831d3a2df724bd1b…`).

**The repair, and the type checker that changed it.** The obvious minimal fix is
`merged.seal_content()` — the contract's own sealer, called on the copy. It runs correctly and
`compatibility` rejects it:

    service.py:693: error: "PydanticDescriptorProxy[ModelValidatorDecoratorInfo]" not callable

A `@model_validator` is a descriptor proxy at type level, not a callable. **So a caller that
blanks a hashed contract's seal has no typed way to put it back** — the only sealing entry point
the contract exposes is a validator, and validators are exactly what `model_copy` skips. That is
the deeper cause of W1-F7 rather than a detail of its repair, and it is why the repair went to
revalidation, the mechanism that does re-run them. The narrow version was tried first and the
gate is what rejected it, which is the difference between a design decision and a preference.

**The negative controls, both directions.** The probe fails on the unrepaired active checkout
with the released refusal in its tail, and all nine of its assertions hold on the repaired tree.
The candidate's own new test fails without the repair (`1 failed, 7 passed`) and passes with it
(`8 passed`). A probe green on both trees would measure nothing, and the record carries both
runs rather than the flattering one.

**Why the defect survived release, stated where it can be checked.** `test_proposal_engine.py`
had two provider tests and both assert a *failure*: the unsafe draft must be refused, the
unavailable provider must fall back. Nothing exercised an **admitted** draft, so every assertion
about the provider-assisted path was an assertion about how it fails. The candidate carries the
missing test with the repair, because a repair without the test that would have caught it leaves
the next instance to the next sprint.

### W3-F1 — a live reproduction cannot survive its own repair

Found by the first run, inside the candidate's own evaluation matrix. W2 chose to **re-execute**
both new ledger reproductions on every `--check` rather than quote them, on W0-F1's lesson that
a quoted finding's price expires silently when a successor ships half of it. The opposite
failure mode is now measured: with the repair present in the worktree, `merged_seal_is_blank`
came back `False`, the sealed record stopped reproducing, and `focused_target_tests` and
`historical_regression` both failed on it. **A governed self-improvement loop whose evidence
re-executes breaks its own evidence on its first success.**

The resolution is neither to stop re-executing nor to weaken the comparison. The checker now
answers a two-outcome question — *does the defect still reproduce, or does the repaired
behaviour hold field by field?* — and reads **both** sides: the stored reproduction must still
be the sealed defect before its disappearance can be explained by a repair, so a tampered stored
record is still a mismatch in a repaired tree, and the merged seal must be a real 64-hex hash
rather than merely non-blank. Drift satisfies neither branch. The sealed record is untouched and
stays true of the commit it was sealed against; what changed is that the checker can now say
which of the two worlds it is looking at instead of reporting the repair as corruption.

### W3-F2 — the released promotion chain cannot name a real repository file

`capture_candidate` was called with the real changed paths and refused: **`candidate changed a
forbidden path`**. The manifest's whole allowed scope is `proposal-scope/source_code_change.py`,
because `build_change_specification` synthesises `proposal-scope/<type>.py` for every
`repository_file` proposal, `prepare_isolation` copies it into the manifest, and
`capture_candidate` compares against it. `changes/demo.py` — the only prior exercise of this
chain — passes `isolation.allowed_repository_paths` straight back in, so both sides agreed and
the seam never opened. This is W1's finding family for the third time: released code that had
never been run with a real subject.

**Consequence, and what was not done about it.** No `ChangeCandidate` exists for this change, so
`PromotionAssessment`, `PromotionReview` and `PromotionBundle` are all unbuildable and
`approve_promotion` cannot be called. The placeholder was **not** substituted and an empty file
list was **not** passed; either would have been the driver certifying its own scope. The refusal
is recorded as a stage the run entered, with the real paths and the manifest's beside it, and a
test re-derives the synthetic path from the released builder rather than quoting it.

The gate owner ruled that L7 stays the sprint's one approved change and W3-F2 goes to the
successor's ledger. The selection is sealed and the repair is proven; §2.3 forbids a second
repair, and spending the change on the seam discovered while walking to it is exactly how one
approved change becomes two.

### The named human, and where the approval had to go

§2.2(b) puts "approval by the named user" between the matrix and the PR, and W3-F2 makes the
released home for it unreachable. So the approval is sealed as its own act in
`sprint-22e-w3-approval.json` (`04d0dea836663876…`): the approver, what they approved bound by
the change record's hash and the candidate's exact diff hash, the gate evidence it was granted
against, and — explicitly — what it does **not** permit. A human act nobody can re-check is not
evidence that a human acted.

**PR [#237](https://github.com/palkouser/cognitive-os/pull/237)** carries exactly the two
approved files, byte-identical to what the matrix evaluated (verified by hash against the sealed
record before the commit was made).

**The landing.** The gate owner instructed the merge explicitly; it went in as a squash at
`f4a6305` on protected `main`, and the **post-merge exact-head CI is `success`, 30 of 30 jobs**
(run 31955173908, head `f4a6305`). Sealed in `sprint-22e-w3-promotion.json`
(`4160b7bcac67e98c…`) under the name and read path W0 pre-registered for Gate M condition 8, so
W4 resolves that binding against exactly this record.

The one thing that record **recomputes** rather than observes is the thing most worth being
unable to fake: both approved files are hashed straight out of the merged commit and compared
with the hashes the evaluation matrix ran over. They match, and `--check` re-derives the
comparison from git every time. A promotion record that quoted a PR number and a green tick
would prove only that something merged.

### The re-measurement, resolved rather than skipped

§3 makes the re-measurement conditional on the landed repair touching a Gate M condition. The
ledger records L7 as touching **none**, and the gate owner's own arithmetic premise names L1 for
condition 6 and L2 for condition 7 — disjoint sets, neither of which is what landed. So **no
re-measurement is licensed**, the frozen instrument was not re-run, and conditions 6 and 7 keep
reading 22D's sealed negatives. Sealed in `sprint-22e-w3-remeasurement.json`
(`50d21098a5ff8d99…`) rather than left as an absence, because a measurement skipped in silence
is indistinguishable later from one that was never owed.

This was predicted before any candidate existed: the decision record states it as the arithmetic
premise of the selection, and §4 states it as a risk the evidence cannot retire. **Gate M cannot
fully close in 22E under any selection**, and the sprint chose which certain negative was worth
the most rather than discovering the arithmetic in W4.

---

## W2 — the loop run three ways, the rollback executed, and the decisions sealed

W2 opened by paying W1's two named debts in order: the check asymmetry (recorded as
[W1-F9](#w1-f9--two-drivers-whose-records-only-one-command-line-could-check) and closed with
both drivers' `--check` reproducing twice and under the CI lane), and **the ledger revision**
— `sprint-22e-weakness-ledger-2.json`, sealed `b1879172db84a080…`.

The revision mechanism is 22B W1-D2's, because the W0 ledger is a sealed record every later
wave binds by hash: **superseded, never edited**. The W0 file is byte-identical, revision 2
binds its predecessor's file hash and seal, carries the five W0 entries by reference with
their sealed ranks unchanged, and adds two entries whose reproductions are **executed on
every `--check`** rather than quoted — both are credential-free, so unlike the W1 records this
one has an empty `recorded_not_recomputed`:

| Entry | Finding | Reproduced, live | Rank |
|---|---|---|---|
| **L6** | 22E W1-F5 | request default 120 s independent of the adapter's limit; the cancellation conversion sits below the timeout's owner; `ProviderTimeoutError` retryable, `ProviderCancelledError` **not** | 6 |
| **L7** | 22E W1-F7 | `merge_provider_draft` returns a revision whose seal is `""`; the released `ProposalCreated` refuses it; the reseal through the contract recovers a 64-hex seal | 7 |

Ranks 6 and 7 follow the W0 rule — neither touches a Gate M condition — and the record states
that L7's real weight sits outside that rule: it decides whether §2.2(b)'s chain can be walked
as written, which is the gate owner's W3 question. Seven tests hold the revision, including
the predecessor's byte-identity and a tampered-reproduction refusal.

### W2-F1 — the compatibility gate refused every candidate, including an empty one

Found while re-deriving L1's "real price" for the W3 decision brief, by W1-F4's own rule: a
sealed finding's diagnosis is evidence about what its author saw, and has to be re-derived.
Dry run 1's `compatibility` failure reads, in the sealed record's own tail,
`import-not-found: numpy` in two **learning** modules — nothing about the repaired file. Run
against the *unrepaired* active tree, the gate's exact command fails with the same two errors;
run with `--extra memory-postgres` — the sync the CI mypy lane actually uses, whose pgvector
dependency transitively installs numpy — it is clean over all 638 files.

So the gate did not reproduce the lane it claims to reproduce (W1-F3's rule, violated by the
gate map's own `compatibility` entry), and **dry run 1's rejection was a false rejection in
W1-F3's class**: real gate, real run, real non-zero exit — and a reason that was not about
the candidate. The W1 log's sentence "widening a released contract's validation surface is
something mypy has an opinion about" is wrong and is corrected here rather than edited there;
the sealed record stays as written, and what it sealed — the command, the exit code, the tail
naming numpy — is exactly what made this re-derivation possible. W1's exit-one evidence is
untouched: the zero-mutation claim never depended on *why* the gate refused. What changes is
the decision input the wave handed W3: **L1's mypy price does not exist.** The repair edits
one string literal, and the corrected gate is expected clean over it — the definitive re-run
belongs to whichever run next carries the candidate. The command is fixed in the gate map
with the reason attached, a test asserts the extra is present, and W2's dry runs 2–3 run
under the corrected gate.

### S22E-201 — the two W3 decisions, taken and sealed

Both decisions W1 forced were put to the gate owner with the priced ledger, the W2-F1
correction and a written recommendation in front of them, and taken on 2026-08-16. Sealed in
`sprint-22e-decisions.json` (`72303b27815306e9…`) with the alternatives they rejected,
because a reading that does not say what it chose against is a reading nobody can audit.

**Decision one: §2.2(b) is walked by repairing it.** The one approved change **is the L7
repair**, and the traversal that installs it documents its own exception — the repaired
behaviour cannot be required of the traversal that installs the repair. No frozen reading is
amended. **Decision two: the selection is L7.** The premise is recomputed by the record's
`--check` from both sealed ledgers rather than asserted: condition 6 is touched only by L1,
condition 7 only by L2, the sets are disjoint, one change may land — **Gate M cannot fully
close in 22E under any selection**, so the certain typed negative was made worth the most:
the loop repairs itself, §2.2(b) becomes walkable for every successor, and the successor
closes conditions 6 and 7 by landing L1 and L2 through the walkable chain, the D-series
precedent (D5's and D6's negatives made the instrument sound; Gate L2 closed in D7). L1 and
L2 are rejected with their measured risks attached — L1's ceiling is not a forecast, L2's
margin sits inside 22D W3-F3's measured baseline noise.

### The dry run 1 continuation — one traversal, and both halves of what W2 owed it

The same L1 candidate was carried through the whole lifecycle again — live claude-code draft
admitted by host verification, repair applied by `deterministic_replace` in a fresh worktree
(`w2-dryrun1-continuation`; the sealed W1 record's worktree identity and file are never
reused, the driver grew `--label`/`--output` for exactly that), zero active-state mutation
recomputed — under the corrected compatibility command.
`sprint-22e-w2-dryrun1-continuation.json`, sealed `8427ffdff2072da7…`, and it delivered two
things at once:

**W2-F1's definitive proof.** `compatibility` — the gate that refused this exact candidate in
W1 — **passes it in 14.4 s** under the command that reproduces the CI lane. The mypy price
never existed.

### W2-F2 — a test that pins a defect's existence blocks the defect's repair

**And the honest failure §2.2(c) requires, which nobody planted.** `focused_target_tests`
refused the candidate — because the W1-F4 diagnosis test,
`test_the_defect_is_the_repository_allowlist_and_not_the_unit_library`, asserts **live** that
the contract refuses the written notation, and in the repaired worktree it no longer does.
The gate's verdict is evidence about the candidate: the repair changes released behaviour a
test currently pins. That is the evaluation matrix doing its exact job, and it prices
something the ledger's L1 entry did not carry: **landing L1 requires updating the pin test in
the same candidate**, so its change specification must allow the test file beside
`quantities.py` — a diagnosis pin is a fence around a *sealed correction*, and it has to move
in the same change that moves the behaviour it pins. Dry run 1's W1 refusal stays what W2-F1
reclassified it (a false rejection); *this* refusal is the honest one, and the record carries
both under one traversal shape — the same candidate, refused twice, only once for a reason
that was its own.

### S22E-202 — the experience leg: compiled, stored, and queried back

W1's unbuilt second half exists and is demonstrated on the **failed kind** — both sealed
dry-run-1 traversals, which refuse at different gates for different reasons.
`sprint-22e-w2-experience.json`, sealed; the side store manifest beside it.

The timeline is **derived from the sealed records, never invented** — the record itself, the
stage stream, the governed receipt, one VERIFIER entry per executed gate with the refusing
one FAILED, and a failed ACCEPTANCE — and compiled through the released `ExperienceCompiler`
(both decisions `completed`). Each traversal is projected by the released projection and
stored **content-addressed under the campaign artifact root** at the released `blob_path`
shape, as a side document carrying the graph *and* the timeline; the manifest calls them
**sides, not pairs**, because the successful twin is the approved change's (§2.2(e)'s own
sentence) and sealing a pair before W3 produces it would seal a pair that does not exist.
Every side is read back, hash-verified and contract-validated before it is claimed
(D7 W3-F1).

**The retrieval has distractors and the answer comes from the store.** The pool is the two
sides plus three released compiler fixtures projected through the same path. The first run
scored **five identical zeros** — the released projection is structural by the leak
discipline, so a natural-language question matches nothing — and the recorded query
therefore speaks the search surface's own language. Both traversals rank 1–2 (0.333) above
every distractor (0.200, 0.125, 0.095), and the record then reads the top-ranked side's blob
**out of the store by its content hash** and answers §2.2(e)'s three questions from the
retrieved bytes: what was tried (the allowlist repair), what failed (refused at a gate), and
why (the numpy environment / the diagnosis pin) — all three `true`, from the store, not from
the driver. `--check` recomputes the entire record in a verify mode that writes nothing; six
tests hold the leg, gated on the artifact root exactly as the sqlalchemy-needing tests
already are.

### Dry runs 2 and 3 — three classes covered, the rollback executed, and a second pin

The driver became entry-generic — a repair spec per ledger entry, applied as a hash-chained
sequence of released `deterministic_replace` steps, a probe per entry, `--full-matrix`, and
mining extended to the revision ledger's added entries under their own seal. All four sealed
dry-run records reproduce under the spec-aware `--check`.

**Dry run 2 — L2, `policy_decision_function`** (`sprint-22e-w2-dryrun2.json`): the 22D
escalation predicate gains an output-kind gate with a defaulted parameter, so the frozen
pre-registration display's call site keeps its exact behaviour. All four probe verdicts
hold (closed-form no longer escalates; factual still does; abstention still does; the
defaulted call is unchanged), and **every gate of the full fifteen-gate matrix passes**,
including `historical_regression` at 259.8 s — the success-shaped stop at
approval-eligible. Then **the rollback W2 owed was executed in isolation**: the steps
reversed through the same released mechanism, every intermediate hash-checked, the restored
bytes hash-identical to the recorded baseline, and the released capture reporting an empty
diff. An eleventh stage, `rollback_executed_in_isolation`, closes the record.

**Dry run 3 — L6, `provider_boundary`** (`sprint-22e-w2-dryrun3.json`): the candidate
cleans up and re-raises the cancellation instead of converting it, so an expired caller
deadline surfaces as `TimeoutError` at the layer that owns the deadline. The probes hold
(the conversion is gone, the timeout path is intact, the module imports), eight gates pass
— and `historical_regression` **honestly refuses it: exactly one released test fails out of
4 603**, `test_cancellation_becomes_a_typed_failure_and_leaves_nothing_running`, the pin
that asserts the very conversion the candidate removes. W2-F2's class, second instance:
landing L6 requires that pin to move in the same candidate. The refusal is evidence about
the candidate, and the record carries it as the dry run's outcome.

**W2's owed list is now empty**: the check asymmetry closed (W1-F9), the ledger revision
landed (L6, L7), the two W3 decisions sealed (S22E-201), the experience leg built and
queried back (S22E-202), three dry runs across three distinct weakness classes
(`verifier_instrument`, `policy_decision_function`, `provider_boundary`) with two honest
refusals and one full-matrix pass, and one rollback executed in isolation. **W3 is next**:
mine L7 under decision one's ruling, carry the repair through the full chain, and stop at
the named-user approval — the human step the loop exists to respect.

---

## W1 — the loop meets the real repository, and eight findings come back with it

W0's slice was a fixture refusing a fixture and said so in a field of its own. W1 is the first
time this repository's self-improvement loop has touched its own worktree, its own persisted
store and a live provider — and what it produced is mostly **findings**, which is exactly what
§3.1 predicted and priced.

| Item | What it owed | Outcome |
|---|---|---|
| **S22E-100** — the substrate | §1.3's four seams against the *real* repository | **measured**, and it found W1-F1 and W1-F3 |
| **S22E-110** — weakness-to-proposal | a proposal mined from real sealed evidence | **sealed**, L1 → 6 signals, impact **75** |
| **S22E-120** — dry run 1 | a live provider-assisted candidate carried to a real gate rejection | **ran end to end**, refused at `compatibility` |
| exit one | rejected proposal → zero active-state mutation | **held**, 0 of 6 members moved, recomputed |
| experience compiled and queried back | the second half of W1's exit | **not built** — owed, and named as owed |
| gates | ruff, format, mypy, bandit, schema drift, repository language | **clean** |

### The four seams, measured

| Seam | Result |
|---|---|
| worktree vs. branch protection | real `git worktree`, **detached**, **locked**, **outside** the active checkout — all three read back from `git worktree list`, not asserted |
| clone vs. released grants | separate database at head `0015`; all three released `validate_database_clone` refusals executed and refused |
| matrix vs. the real suite | **15 of 15** gates mapped to commands that actually run; measured wall clock **293 s**, slowest `historical_regression` at **262 s** |
| in-memory transition vs. persisted store | `PostgresChangeRepository` drives the released transitions and the content hash survives the round trip |

### W1-F1 — W0's own surface enumeration made exit one unsatisfiable

`ControlledChangeService.request_experiment` — the **first** stage — persists the experiment and
its revision before any gate can refuse anything. There is no path to a rejection that does not
first write to the governed store. W0 read §2.2(a)'s "the governed stores" as all 114 tables, so
**every correct rejection would have reported a mutation**.

The plan's sentence and W0's derivation of it are different things, and it was the derivation
that was wrong: §2.2(a) enumerates surfaces a bad candidate could *damage*, and the change
ledger is the audit record that the refusal happened. A rejection that left it untouched would
be a loop with no evidence.

Repaired as a **split rather than a removal**, and it is strictly more information than before:
the protected fingerprint excludes exactly the released ledger tables and must not move; the
audit-trail fingerprint covers exactly those tables, is reported beside it, and a real traversal
is *required* to move it. One number became two, and nothing became invisible. The table set is
derived from the released tables module rather than matched on a `change_` prefix, because a
prefix is a naming convention and this needed to be a fact.

### W1-F2 — a seal computed over the fields the check excludes

The W0 slice's `--check` compared the rebuilt record against the stored one *including*
`integrity_content_hash`, while excluding the two surface captures the seal is computed over. It
was therefore green only while nothing wrote to the governed store between two runs — which held
for exactly as long as W0 lasted, and broke on W1's first write. The stored seal is still
verified against the stored body; what changed is that the rebuild comparison no longer demands
a hash of something it deliberately did not rebuild.

### W1-F3 — the gate inherited the operator's shell, and turned refusals into a regression

The first substrate run inherited `os.environ`, so the gates ran with this sprint's
`COGOS_TEST_DATABASE_URL` pointing at the governed campaign store. That woke 104 PostgreSQL
integration tests the CI lane skips for want of credentials, and the released suite did exactly
the right thing — it **refused**:

    Failed: refusing provider-output integration tests against database: cognitive_os_s22e_campaign

**The store was never in danger. The verdict was.** 104 released refusals arrived at the
evaluation matrix as `historical_regression` *failed*, which is indistinguishable from a
candidate that broke something. A gate that reports a refusal as a regression rejects good
candidates for a reason that is not about them.

The matrix now runs in a **declared** environment: an allowlist of nine host variables plus the
uv cache, built as a fresh dictionary rather than a filtered copy — "we removed the dangerous
ones" decays every time somebody adds a variable, and "we passed only these" does not.

> Generalisable: **an evaluation gate must reproduce the lane it claims to reproduce.**
> Inheriting an ambient shell is how it silently stops doing that, and the failure mode is a
> false rejection rather than a false pass.

### W1-F4 — the notation defect is a regex in this repository, not a limit of Pint

22D W2-F2 reads "the registered physics verifiers ... **error** on `m/s²`, `kg·m/s` and `Ω`",
and a reader takes that to mean the sealed unit registry cannot parse them. Measured side by
side:

| Unit | `PhysicalQuantity` contract | Pint |
|---|---|---|
| `ohm`, `kg*m/s`, `m/s**2` | accepts | parses |
| `Ω`, `kg·m/s`, `m/s²` | **refuses** — "unit expression is not allowed" | **parses** |

What refuses them is this repository's own character-class allowlist,
`SAFE_UNIT = re.compile(r"^[A-Za-z0-9_/*^ .-]{1,128}$")`, in `PhysicalQuantity.safe_unit`. The
W0 ceiling (+10 on `local_model`) is unchanged; the **diagnosis** changes, and it changes the
repair from "replace the unit library" to "widen an allowlist by four characters, keeping its
injection-safety intent". The repair adds `·`, `²`, `³` and `Ω` and nothing else — deliberately
not `\w` or a Unicode category, because this validator exists to keep a unit expression from
being an injection surface, and the probe measures that negative case beside the positive ones.

> Generalisable: **a sealed finding's stated cause is evidence about what its author saw, not
> about what the code does.** The reproduction is inheritable; the diagnosis has to be re-derived.

### W1-F5 — a timeout that reports itself as a cancellation

`ModelProviderRequest.timeout_seconds` defaults to **120** while the claude-code adapter's own
CLI limit is **300**. So the request expires first, `ModelExecutionService._execute_once` cancels
`provider.complete`, and `BoundedCliRunner._communicate` catches that cancellation and converts
it to `ProviderCancelledError` **before** the outer `except TimeoutError` can see it.

Three consequences, each worse than the slow call itself: an expired call reads as one somebody
cancelled; `events.timed_out` never fires, so the stream records no timeout; and
`ProviderCancelledError` is not in `retryable_error_types` while `ProviderTimeoutError` is, so
the retry policy silently stops doing what it was configured to do.

Two live calls were lost to this before a bisection separated the layers — the adapter answers
in 34 s on its own, and the same call through the governed service "cancelled" every time. The
caller-side repair is to stop asking for less time than the adapter is allowed to take. The
released defect is carried to the ledger.

### W1-F6 — the caller and the boundary asked one model for two different objects

`ClaudeCodeAdvisoryProvider.safety_arguments` puts `--json-schema <AdvisoryResult>` on the
command line unconditionally. A caller that asks for a different shape in its prompt gets
neither: prose, which arrives at the reader as a malformed answer and would be recorded as a
provider failure. It is not a provider failure — it is a caller asking for something the
boundary already forbade, and **nothing in the released code compares the two**.

Related, and mine rather than the code's: the adapter validates the full advisory result into
`structured_output` and sets `content` to `advisory.summary` alone. Reading `content` gets a
correct but lossy view — the summary arrives and the findings, recommendations, risks and
verification steps are silently gone. That cost two more live calls before it was noticed.

### W1-F7 — the released provider-assisted path raises on its own success path

**The wave's most valuable finding**, and the one a fixture could never have produced.
`merge_provider_draft` ends with

    return revision.model_copy(update={..., "content_hash": ""})

blanking the hash so the contract's `seal_content` validator recomputes it. But
`model_copy(update=...)` **does not re-run validators** in Pydantic v2, so the merged revision
keeps `content_hash == ""`, and the very next released statement —
`ProposalCreated(proposal_content_hash=generated.content_hash)` — refuses it against
`^[0-9a-f]{64}$`.

So `create_from_weakness(provider_assisted=True)` cannot complete for any draft that passes host
verification. §1.3 is why nobody had seen it: *no candidate had ever been generated by a real
provider*. The fixture demo has no provider and the tests have no live model, so the path had
never run.

**Its second consequence is worse than the first.** The released transitions read the current
revision back out of the repository, and the only released writer of a *merged* revision is the
call that cannot complete. So the `provider_assisted` mark cannot survive to an approved
revision by any caller's route. Dry run 1's draft was live, host-verified and admitted — and the
approved revision reads `deterministic`. Both halves are recorded, and a test asserts both, so
no successor can read this dry run as having produced a provider-assisted approved revision.

This driver reseals the merged revision through the contract so the dry run can continue, and
the record calls that a **workaround rather than a repair**. A released fix belongs on the
governed path, which is the whole point of the sprint; fixing it here would spend the one
approved change outside the loop that is supposed to earn it.

### W1-F8 — a governed loop that could not be run twice

`ChangeWorktreeIsolation.prepare` refuses when the experiment's root already exists, and the
experiment id is a `uuid5` of its label — deterministic on purpose, so a record names the same
experiment every time. Together they mean **a dry run that fails partway can never be re-run**:
the released cleanup removes the git worktree but leaves the `<experiment_id>/` directory, and
the next attempt is refused however the first one ended.

Repaired in the caller, not the released layer: the released refusal is correct — it protects a
live experiment — and what was missing is a caller that knows its own previous attempt is dead.

### W1-F9 — two drivers whose records only one command line could check

Found in review after the wave's partial close, not by a run failing, and recorded here before
W2 begins rather than folded into it silently. The four W0 sealers have a `--check`;
`isolation_22e.py` and `dryrun_22e.py` did not. Both W1 records *were* checked — the test file
recomputes each seal and twenty further tests read their fields — but only from one command
line, which is exactly the shape §0's portability rule (22D W4-F1) exists to name. The omission
had a defensible half and an indefensible one, and the repair keeps them apart: re-deriving
either record would be a 282-second matrix run and a **billed** provider call, and 22C W1-F1
forbids a validator that needs the world — but that is a reason to *split* the check, not to
omit it.

Closed with the split the sealers already use: each driver's `--check` **recomputes the
invariants** — the seal, the matrix coverage against the released `build_evaluation_matrix`,
the environment declaration against the code constants, the arithmetic every summary number
owes its own rows, the probe's verdict booleans from its own accepted map, and the
zero-mutation comparison re-derived from the two captures the record itself carries — and
**re-reads the observations** by name: gate verdicts, wall clocks, worktree facts, clone
heads, the provider receipt. The output prints `recomputed` and `recorded_not_recomputed` so a
green can never be read as more than it is. Both checks run twice with identical output
(22A W4-F3), both reproduce under the main CI lane's configuration as well as the postgres
one, and five tests hold the closure — including a tampered gate verdict, a planted
zero-mutation claim and an injection case quietly marked accepted, each of which the check
must refuse (22A W4-F2).

### Dry run 1, end to end

Ten stages, in order, none skipped: weakness mined from the sealed ledger → proposal created →
live provider draft merged through host verification and resealed → approved for experiment →
experiment requested on the persisted store → isolation prepared → repair applied through
`deterministic_replace` → repair probed → candidate captured through the released worktree
capture → evaluation run.

| Gate | Result |
|---|---|
| `focused_target_tests` | passed, 3.1 s |
| `security` | passed, 5.3 s |
| `policy` | passed, 0.02 s |
| `schema` | passed, 1.8 s |
| **`compatibility` (mypy)** | **failed, 12.3 s** |

**The rejection is real and nobody planted it.** The candidate is a correct repair — the probe
shows written notation accepted, ASCII notation still accepted and an injection string still
refused — and a released gate refused it anyway, because widening a released contract's
validation surface is something mypy has an opinion about. That is precisely what a dry run is
for: the loop reports the repair and the refusal together, and neither cancels the other.

Only the allowed path changed (`src/cognitive_os/verification/physics/quantities.py`), and the
active surface moved on **none** of its six members.

The audit trail did not move either, and that is worth stating rather than glossing: both
sealed runs are **re-runs of a deterministic experiment id**, and `request_experiment` is
idempotent by request signature — it finds the existing experiment and returns it, so a repeat
writes nothing. W1-F1's split therefore reports `audit_trail_moved: false` on these records and
is correct to. The claim the split supports is that the trail *can* move and is watched when it
does, not that every traversal writes; a test that demanded movement would have been a test of
whether a run happened to be the first one.

### What W1 did not do, and is owed

**Experience compiled and queried back was not built.** It is the second half of W1's exit
criterion, and D7 W3-F1's rule is that retention without a demonstrated read is a hope. A
component that was not written cannot be reported as having demonstrated anything, so W1 closes
as **partial**: the substrate, the mining, the live provider path and the rejection are done and
sealed; the Experience Compiler leg is owed to W2, which already carries the compile-and-retrieve
requirement for dry runs 2 and 3.

**W1-F7 is owed to the ledger.** The W0 ledger is a sealed W0 record that every later wave is
bound to by hash, and re-sealing it in W1 would invalidate the record the tests check. The entry
is therefore carried here and added in W2, where a ledger revision is a wave's own act rather
than a retro-edit of a predecessor's seal.

**And W1-F7 changes what W3 is choosing between.** §2.2(b)'s chain names a *provider-assisted
candidate* for the one approved change. That mark is currently unreachable by any caller, so
either W3's approved change is the W1-F7 repair, or §2.2(b)'s chain cannot be walked as written.
That is a gate-owner decision and it is stated here rather than discovered in W3.

---

## W0 — the readings frozen, the ledger priced, and a candidate that was never what the plan thought

W0 measures nothing about the loop. It settles what every later claim will mean, and it ends
with a fixture proposal driven to a rejection that decides no exit criterion and says so in its
own body.

| Item | What it owed | Outcome |
|---|---|---|
| **blocking check** | 22D released, verified from live handles | **satisfied**, not waived — tag, peel, ancestry, exact-head CI and protection all re-read from the remote |
| **S22E-001/002** — preflight and surface | the host measured, the stores at `0015`, the predecessor roots fingerprinted, §2.2(a)'s surface enumerated | **sealed**, no blocking dependency, and the enumeration found W0-F3 |
| **S22E-020** — the weakness ledger | §1.4's five findings ranked, priced from sealed records and live probes, reproduction handle per entry | **sealed**, 5 entries, 4 eligible — and W0-F1 |
| **S22E-010…016** — pre-registration | every §2.2 reading and both §2.1 gate-owner decisions frozen before any candidate exists | **sealed**, `measured_values: 0`, `amendments_made_by_22e: 0` |
| **S22E-030** — the §3.1 slice | the released demo, then a fixture proposal through every stage to a rejection, zero-mutation recomputed | **ran**, 8 stages, refusal raised, zero mutation |
| gates | ruff, format, mypy, bandit, schema drift, repository language | **clean** |
| tests | the W0 evidence file, in the physics lane and in the main CI lane's configuration | **42 passed / 50 passed** |

### The blocking check, read rather than assumed

§0's contract is that a wave verifies its predecessor from live handles. Every value below was
read off the remote at W0; none was transcribed from the backlog.

| Handle | Read from | Value |
|---|---|---|
| tag object | `git ls-remote --tags origin` | `c546ac8c903cf9a3693c47ac88b7cce04c012a53` |
| peels to | the remote's own peeled ref | `cb4d4ada82145ce31033823e2c70a06e308340d8` |
| ancestry | `git merge-base --is-ancestor … origin/main` | **ancestor**, and equal to `origin/main` |
| exact-head CI | `actions/runs?head_sha=cb4d4ad…` | run **31932062537**, `success`, 0 jobs not successful |
| protection | `branches/main/protection` | 27 required checks, `enforce_admins: true` |

`--check` deliberately does **not** re-read any of this. A validator that needs a network fails
for reasons that are not about the record, which is 22C W1-F1's rule; `preflight_22e.py
--verify-release` is the mode that re-reads it, and it was run and agreed.

Stores provisioned at migration head **`0015`** — governed, clone and integration, all three
confirmed at head by query rather than by the provisioning script's exit code. The clone is a
separate database **by construction**: its name is not derivable from `COGOS_DATABASE_URL`, so
a driver handed only the governed URL cannot reach it by any code path. That is 22B W1-F6's
rule applied to a clone rather than to a holdout.

### The two gate-owner decisions, taken with the ledger visible and before any candidate existed

§2.1 asks for exactly two, and §1.2 is explicit that deciding condition 5 afterwards would be
choosing a verdict. Both were put to the gate owner in W0, with the priced ledger in front of
them, and both are sealed with the alternative they rejected — because a reading that does not
say what it chose against is a reading nobody can audit.

**Condition 5 reads 22D's grounded holdout answers**, and therefore **holds**. The reasoning is
about the sentence rather than about the number: the allocation's verb is *applied*, and the
word *improved* appears nowhere in condition 5. 22C's improvement arithmetic is 22C's own exit
5, a different sentence, and reading it into this condition would write a word into a frozen
one — which §2.3 forbids in either direction, including the strict direction. The risk is
stated in the record rather than managed away: this is the reading that moves a condition from
ambiguous to holding, and both numbers were sealed and visible when it was taken. The
mitigation is that the rejected reading and *its* verdict (fails, 0 of 4) are published beside
it and will be re-published in the W4 assessment, so a reader can apply either without
re-deriving anything.

**`0016` stays a refusal**, so ledger entry L5 (22D W2-F1, the `LOCAL_API` configuration class)
is ineligible. Two reasons, both measured rather than aesthetic: it touches no Gate M condition,
so spending the one approved change there licenses no re-measurement at all; and a schema
migration would put a second variable into the single governed traversal, leaving a failure
ambiguous between the loop and the migration. Migration head stays `0015` at W0 and must still
read `0015` at W4.

Conditions 6 and 7 keep §1.2's rule as written: they fail as sealed, and a 22E re-measurement
replaces either reading **only** behind a repair that landed through the governed path first.

### The honest starting score, bound to records rather than to prose

All ten conditions are bound to a record and a dotted field path, published in W0 and executed
in W4. Seven read a predecessor and all seven resolve today; three read records this sprint has
not written yet, and are deferred by construction.

| # | Reads | Path | Today |
|---|---|---|---|
| 1 | `sprint-21d7-gate-l2.json` | `counts.met` | **holds**, 29 |
| 2 | `sprint-22a-exit-criteria.json` | `outcome` | **holds**, `pass` |
| 3 | `sprint-22b-exit-criteria.json` | `all_met` | **holds**, 5 of 5 |
| 4 | `sprint-22c-exit-criteria.json` | `criteria.every cycle replays all retained domains` | **holds**, 19 of 19 |
| 5 | `sprint-22d-w1-holdout-read.json` | `arm_b_verified` | **holds** under the W0 reading, 4 |
| 6 | `sprint-22d-exit-criteria.json` | `criteria[1].met` | **fails as sealed**, `false` |
| 7 | `sprint-22d-exit-criteria.json` | `criteria[2].met` | **fails as sealed**, `false` |
| 8 | `sprint-22e-w3-promotion.json` | `post_merge_ci.conclusion` | 22E's to earn |
| 9 | `sprint-22e-w4-gates.json` | `lanes` | 22E's to earn |
| 10 | `sprint-22e-release.json` | `tag.peels_to` | 22E's to earn |

Condition 4 is bound to 22C's **replay criterion** specifically and not to 22C's outcome. 22C
released as a typed negative, but it earned that on its improvement exit — an exit condition 4
does not read. Binding to the sprint's verdict rather than to the sentence would have marked a
holding condition as failing, which is the mirror image of the mistake §1.2 warns about.

### W0-F1 — the ledger's cleanest candidate is neither clean nor a candidate for what the plan wants

**The wave's real finding.** §1.4 lists 22B W3-F1 — the `MemoryService.create` two-transaction
crash window — as "confirmed still unrepaired in released code", "the cleanest **low-risk**
candidate", "provable to `items_missing_an_event == 0` by re-running a measurement that already
exists". Reading the released code and 22C's sealed records rather than the plan's sentence:

- **the permanence half shipped in 22C.** `MemoryService.create` now asks
  `MemoryEventService.ensure_item_created` — the *stream* — rather than asking whether the
  record existed before the write. Sealed in `sprint-22c-w1-event-repair.json`
  (`resume_repaired_the_orphan: true`, `resume_is_idempotent: true`) and in
  `sprint-22c-w1-crash.json` (`repair_closed_every_orphan: true`,
  `items_missing_an_event_after_resume: 0`);
- **the window itself is still open**, and `items_missing_an_event_after_recovery` is still `1`
  in the run where the window opened;
- **closing it is not a small change.** 22C's own record says why it stopped: the closure needs
  a transactional boundary that `MemoryRepositoryPort` and `EventStorePort` do not share. Two
  released ports, not one released service.

So the priced benefit is wrong in both directions at once. The number the plan names as the
proof — `items_missing_an_event == 0` — is **already true today** under a resume, so landing
this candidate would move it by zero; and the residual reading that *could* move costs a
two-port refactor. The entry is not struck out, because it is a real defect and a real
candidate. It is re-ranked as what it is: **risk class `high`, expected benefit 0 on the
reading the plan names**, fourth of five rather than the low-risk pick a gate owner would
reach for first.

> Generalisable, and it is why §1.4's field had to be re-derived rather than transcribed: **a
> finding's price expires when a successor ships half of it.** A ledger inherits the
> reproduction, never the valuation, and a plan written before the successor released is a plan
> quoting a number that has since moved.

The same re-derivation confirmed the other four entries and sharpened one of them. 22D W2-F2's
notation tax is real and now has a **measured ceiling** rather than "roughly a dozen": every
undecidable task minus every malformed answer, per arm, because 22D counts those apart and
malformed answers are undecidable for a different reason.

| Arm | Verified | Undecidable | Malformed | Recoverable ceiling | Verified at the ceiling |
|---|---:|---:|---:|---:|---:|
| `local_model` | 66 | 13 | 3 | **10** | **76** |
| `mixed_workload` | 85 | 15 | 9 | 6 | 91 |
| `external_teacher` | 87 | 12 | 6 | 6 | 93 |

Against a 70 % floor, condition 6 is **reachable and not implied**, and the record says
`is_a_ceiling_not_a_forecast: true` in the field itself. Not one of those ten tasks is
guaranteed to verify once the notation parses: 22D's own probe recorded `6 Ω` as correct
notation over a *wrong* magnitude, and an undecidable verdict hides a wrong answer exactly as
well as it hides a right one.

The notation defect was reproduced live rather than quoted, through the released reader and
the released verifier, one answer string per spelling:

| Task | ASCII spelling | Written spelling | Reader | Verifier |
|---|---|---|---|---|
| `s22d-convert-15` | `4700 ohm` → verified | `4700 Ω` | **accepted** | **ERROR → undecidable** |
| `s22d-dimension-02` | `1 kg*m/s` → verified | `1 kg·m/s` | accepted | ERROR |
| `s22d-dimension-05` | `1 m/s**2` → verified | `1 m/s²` | accepted | ERROR |
| `s22d-dimension-08` | `1 kg/m**3` → verified | `1 kg/m³` | accepted | ERROR |
| `s22d-dimension-09` | `1 N*m` → verified | `1 N·m` | accepted | ERROR |
| `s22d-dimension-10` | `1 ohm` → verified | `1 Ω` | accepted | ERROR |

`1 m/s^2` (caret) verifies and `1 m/s²` (superscript) does not, which is the sharpest available
statement of the defect: the boundary is typography, and the reader waves it through before the
sealed unit registry refuses it.

And 22D W3-F1 is now a count rather than an adjective: **70 of 100** tasks on the `local_model`
arm were escalated while not being factual outputs at all — every one of them a
`closed_form_computation`, escalated for lacking a citation the grounding exit never reads.

### W0-F2 — the same portability defect, twice, in one wave

22D W4-F1 graduated into §0 as a standing rule: *nothing may be green under only one command
line*. It was violated twice here, both times by this wave's own new code, and both were found
by running the sealers under the main CI lane's configuration rather than under the one that
happened to be convenient.

**Instance one: `ledger_22e.py --check` raised `VerifierUnavailableError`** under
`uv run --exact`, because the live notation probe needs the `verification-physics` extra and the
main CI lane installs no physics extra at all. Fixed with `preflight_22d`'s own split — whether
Pint is importable is a property of the interpreter, not of the ledger — so the probe block is
recomputed where it can be and re-read where it cannot, and `--check` prints
`live_probe_recomputed` and `recorded_not_recomputed` so a green in the CI lane can never be
read as a green over the probe. Writing the ledger without the extra is a **named refusal**
rather than a degraded record: a reproduction block saying "probe not run" would otherwise be
sealed under a hash as if it were evidence.

**Instance two: `pre_registration_22e.py --check` raised `ModuleNotFoundError: sqlalchemy`**
under the same lane, because it imports `surface_22e` for the surface *enumeration* — a question
about a released contract, with no database in it — and that module imported SQLAlchemy at
module scope. Fixed by moving the import into the one function that fingerprints a store.

The first instance also produced a **false green** worth recording, because it is the trap the
rule exists for. Running `uv run --extra verification-physics` once installed Pint into the
project virtualenv, where it persisted; the next plain `uv run … --check` therefore *passed*,
having silently kept the extra. Only `uv run --exact`, which prunes, reproduced the failure.
**A lane is not proved by omitting a flag; it is proved by pruning the environment.**

### W0-F3 — the released snapshot contract cannot express one of §2.2(a)'s surfaces

§2.2(a) enumerates six things the active surface holds. `ActiveStateProtectionSnapshot` — the
released contract `ControlledChangeService` actually carries — has five, and the sixth has no
field. The reason is 22A's own achievement: since the registry became **data**, the domain
resolution surface is `registry.snapshot_hash()` and not a table, so a store with 114 tables
holds none of it. **A candidate that registered a domain would move nothing in any of the
contract's five fields**, and a zero-mutation claim built only on them would say so honestly and
be wrong.

Carried as an explicit sixth member beside the contract rather than dropped, and rather than
pretended into the database fingerprint. `contract_members` and `additional_members` are
reported separately so a reader can see which half of the surface the released snapshot can
carry into `ControlledChangeService` and which half this sprint holds alongside it. Widening the
contract is a released-contract change and is **owed to a successor**, not taken here.

The same derivation surfaced a smaller thing worth keeping: the contract's seven fields include
`content_hash`, the snapshot's own seal — a hash *of* the five. Treating it as a surface would
have made every comparison count one movement twice. A hand-typed list of five would simply
never have mentioned it, which is the argument for deriving the list.

### W0-F4 — two Gate M bindings pointed at nothing, and W4 is the wrong wave to find that in

§2.2(d) requires an unresolvable path to **raise** rather than render false, and the reason is
that a condition which renders false because a key was renamed is indistinguishable, in a table
of ten, from a condition that was measured and did not hold. Only one of those is a result.

Having written the rule, this wave then wrote two bindings that resolved to nothing:
`sprint-22d-preflight.json#gate_l2.conditions_passing`, which was never a field of that record,
and `sprint-22d-w1-holdout-read.json#holdout.grounded`, whose record keys the number
`arm_b_verified`. Both were wrong in the same way — **written from what the plan's prose calls
the number rather than from what the record calls it**. A third, condition 2, resolved but to a
criterion object rather than to a decidable value.

Fixed by executing the bindings in W0 rather than describing them:
`pre_registration_22e.py --verify-bindings` resolves every predecessor path, compares it against
the value the pre-registration expects, and is asserted by a test. Seven resolve, seven match,
three are deferred with a stated reason. The resolver lives in the pre-registration module and
W4 imports it, so the syntax that is published and the syntax that is executed are one piece of
code (22B W1-F2).

> Generalisable: **a gate wired in the wave that writes it is a wave's own cheap finding; a gate
> wired in the wave that reads it is a release-day surprise.** Resolving the paths cost minutes
> here and would have cost a wave in W4.

### W0-A1 — a stage list written twice disagreed with itself

The slice's `no_stage_skipped` compared the stages the run appended against a list retyped
inside the result dictionary, and the retyped copy omitted `assessed`. A complete, correct,
eight-stage run therefore reported `no_stage_skipped: false`. Fixed by declaring
`EXPECTED_STAGE_ORDER` once and comparing against it — the same discipline the rest of this
programme applies to enumerations, applied to a list that looked too small to need it.

### The slice, and what it deliberately does not decide

The released `changes/demo.py` chain runs end to end, credential-free and in memory, all eleven
stages, ending in `eligible_for_operator_approval` with the separate-actor rule enforced. Then
one fixture proposal is driven through the whole lifecycle to a **rejection**:

| Stage | Outcome |
|---|---|
| experiment requested → isolation prepared → plan → candidate captured → matrix built | entered in order, none skipped |
| evaluation | one cell fails on `security_regression`; every other cell passes |
| assessment | `security_regression` — arrived through `FAILURE_DECISIONS`, not by default |
| promotion | **called**, and `ChangeAuthorityError` raised |
| active surface | 6 members compared, **0 mutated** |

Three deliberate choices. The failure is planted in **one** cell rather than all of them,
because a candidate that failed everything would be rejected by any reading and would not show
that the matrix is read per gate. The failure code is `SECURITY_REGRESSION` rather than a
generic one, because `FAILURE_DECISIONS` maps it to a *named* promotion decision — a rejection
that had to travel through the released mapping to arrive proves more than one that fell through
to the default. And `approve_promotion` is **called** on the rejected assessment and required to
raise, rather than skipped on the grounds that its precondition was not met: a refusal nobody
attempted is a refusal nobody has evidence of.

**It decides no exit criterion, and the record says so in a field.** Exit one wants a *real*
rejection — a genuine provider-generated candidate refused at a genuine gate (§2.2a) — and this
is a fixture refusing a fixture, which the plan names as explicitly not enough. Every seam in
§1.3's last sentence remains unmeasured: worktree against branch protection, sandbox against
the real ~4.5-minute suite, clone against a store with released grants, and a stage transition
that has only ever run in memory meeting a persisted store. §3.1 puts all four in W1.

### The zero-mutation claim can notice a change

22A W4-F2 is the standing rule that made this the largest single piece of W0's test file. The
comparison is **parametrised over every one of the six members**: each is moved on its own and
the comparison must name it, because a comparison that only ever watched the first field would
pass a single-member test and miss five surfaces. A capture that *plants* a
`zero_active_state_mutation: true` flag on itself is also fed in, and must still be reported as
mutated — the claim is recomputed from the two captures and never accepted from the thing being
checked.

Without those tests, exit one's whole apparatus would be a function that had only ever been
observed returning `True`.

### Validation

| Gate | Command | Result |
|---|---|---|
| ruff check | `--config ruff.cognitive-os.toml src tests scripts infra` | **clean** |
| ruff format | same, `--check` | **clean**, 1263 files |
| mypy | `src/cognitive_os` | **clean**, 638 files |
| bandit | `-r src/cognitive_os` | **clean**, exit 0 |
| schema drift | `export_contract_schemas.sh --check` | **passed** |
| repository language | `check_repository_language.sh` | **passed** |
| sealers, twice each | `--check` on all four W0 drivers (22A W4-F3) | **reproduced**, both runs |
| release re-read | `preflight_22e.py --verify-release` | **still agrees** |
| bindings | `pre_registration_22e.py --verify-bindings` | 7 resolve, 7 match, 3 deferred |

### Evidence

| Record | Seal (first 16) | Holds |
|---|---|---|
| `sprint-22e-preflight.json` | `c22be642e4caa98a` | blocking check, host, stores at `0015`, predecessor roots, the W0 surface |
| `sprint-22e-weakness-ledger.json` | `c51b6d149f2f5657` | 5 ranked entries, priced from sealed records, W0-F1 attached to L4 |
| `sprint-22e-pre-registration.json` | `7ab42855ea8d9ab9` | five exits, ten Gate M bindings, both gate-owner decisions, `measured_values: 0` |
| `sprint-22e-contracts.json` | *(projection, rebuilt by `--check`)* | the seven S22E-01x readings |
| `sprint-22e-w0-slice.json` | `a6e665a78d22d711` | the released demo, the fixture rejection, the recomputed zero-mutation comparison |

### What W1 inherits

A priced field and a settled gate, and one correction to the plan's expectations. The ledger's
four eligible entries are ranked L1 (notation, condition 6, low risk, ceiling +10 on a 66
against a floor of 70), L2 (escalation, condition 7, low risk, 70 needless escalations), L3
(abstention, no condition, moderate), L4 (the crash window, no condition, **high** risk and zero
benefit on the reading the plan named). §1.4's expectation that the crash window would be the
easy low-risk pick does not survive contact with 22C's released repair, and W3's selection
should be made knowing that the two candidates with measured leverage are also the two lowest-
risk ones.

W1 owes the isolation substrate against the **real** repository and dry run 1. §3.1's prediction
stands untested: nothing in W0 touched a worktree, a sandbox, a database clone or branch
protection, and the fixture slice is precisely the thing that cannot see those seams.
