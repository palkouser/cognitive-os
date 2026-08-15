# Sprint 22D Execution Log

Bounded local English, LLM-dependence reduction, and the instrument every later wave is bound
to. Executed against the
[Sprint 22D Technical Backlog](sprint-22d-technical-backlog.md), whose §0 incorporates the
[Sprint 21D4](../sprint-21/sprint-21d4-technical-backlog.md) execution contract unchanged and
adds six standing rules 22C paid for.

Waves are recorded newest first.

---

## W3 — the fourth arm, the deployed composition, and four exits read once

W3 owed the `local_model` arm on the frozen hundred, the confidence-based escalation and the
mixed workload with accounting on both, and the four measured exits read once. It added **no
instrument**: `run_arm` still owns verification, accounting, escalation and the citation walk,
the readers still refuse rather than repair, and the retrieval predicate is the one S22D-200
priced *before* any arm ran. One seam widened in W0's runner — the mixed workload is scored by
the same runner under a name of its own, because a second runner would have been a second set
of accounting and the whole point of the 25 % is that both sides came from one definition.

| Item | What it owed | Outcome |
|---|---|---|
| **S22D-301** — `local_model` | retrieval-augmented local inference, read once | **66 verified, 4 grounded**, 0 external calls |
| **S22D-302** — mixed workload | the frozen policy in front of the teacher | **85 verified**, 96 escalations, 96 calls |
| **S22D-300** — the exits | four measured exits, read once from sealed records | **1 of 4 met — a typed negative** |
| tests | W3 evidence | **36**, none of them asserting a fact about this machine |

| Workload | verified | abstained | grounded | ungrounded | undecidable | malformed | ext calls | cost units |
|---|---|---|---|---|---|---|---|---|
| `local_model` | **66** | 0 | **4** | 26 | 13 | 3 | 0 | 9.00 |
| `mixed_workload` | **85** | 0 | 4 | 26 | 15 | 9 | 96 | 127.95 |
| `external_teacher` (W2) | 87 | 0 | 0 | 30 | 12 | 6 | 100 | 120.83 |
| `no_memory` (W2) | 66 | 0 | 0 | 30 | 13 | 3 | 0 | 8.87 |
| `retrieval_only` (W2) | 4 | 96 | 4 | 0 | 0 | 0 | 0 | 0.00 |

**Nothing under `src/` was touched.** Three lines moved in W0's runner: a constant naming the
mixed workload, the arm check that admits it, and the external-call refusal reading a tuple
instead of one name. `ARMS` is still the four the allocation named and the readings hash still
matches the pre-registration, so no measured number moved anything frozen.

### The four exits, read once

| Exit | Reading | Met |
|---|---|---|
| **(a)** no external LLM during the local microbenchmark | 0 calls in the arm; all four enumerated providers refused; budget `maximum_provider_calls: 0` | **yes** |
| **(b)** ≥ 70 % and ≥ 10 points over retrieval-only | 66.0 %; margin **62.0** points over 4.0 | **no** — the margin is met and the floor is not |
| **(c)** ≥ 25 % fewer calls or cost at non-inferior success | calls **−4.0 %**, cost **+5.9 %**, non-inferiority drop 2.0 ≤ 3.0 | **no** — non-inferiority holds, neither reduction does |
| **(d)** factual output grounded or explicitly uncertain | **26** ungrounded assertions of 30 factual outputs | **no** |

Exit (e) is W4's: §2.2(e) re-reads the prior gates from their sealed records, and §3's wave
table puts that in the release wave.

### W3-F1 — the escalation policy escalates what the grounding exit never reads

`escalate` was frozen in W0 as three mechanical signals, one of which is the count of grounding
spans. It says nothing about *output kind* — so the seventy closed-form computations, which have
no source to rest on and which §2.2(d) explicitly does not read, escalate for lacking a citation
nobody ever wanted from them. **96 of 100 tasks escalated; 70 of those were arithmetic.**

That single omission is why exit (c) could not pass at any local success rate. A workload that
escalates all but four tasks pays for the teacher almost in full and adds the local pass on top,
which is exactly what the numbers say: 4 % fewer calls and 5.9 % *more* accounted cost.

It ran as frozen. §2.3 forbids tuning the escalation threshold after its first measured number
exists, and the version of this wave that quietly added `and task.output_kind in
FACTUAL_OUTPUT_KINDS` before running would have produced a 25 % reduction and no evidence. The
policy is a pre-registered configuration; what it cost is a finding, not a patch.

The repair belongs to whoever writes the next plan, and it is one line: **a policy that reads
grounding must read the same output enumeration the grounding exit reads.** Until then the
escalation gate is a *coverage* gate wearing a confidence gate's name.

### W3-F2 — "grounded" as frozen cannot tell support from bytes

§2.2(d) defines grounded as *"the output carries a citation that the released citation walk
resolves by loading the cited source bytes"*. §3.1 predicted the slice would find that this has
no executable meaning for generated prose. It does not, and the loophole is bigger than
predicted: **a runner that stapled the retrieved span onto whatever the model said would satisfy
that sentence exactly** — the walk loads the bytes, slices the range, hashes it, and reports
`resolves: true`, for an answer with no relation to the span.

W3 refused that and imposed a stricter rule, `grounded_in`: the citation is attached only where
the answer carries **the value the source states**, compared as a number, *and* the cited span
**contains that value**. Two checks, both in bytes, neither of them a model judging a model.

Both halves are asserted as executable evidence rather than described. One test constructs the
staple — answer `41.9`, citation resolving perfectly onto the bytes that say `12.01` — and shows
the released walk calling it `grounded`; the next line shows `grounded_in` refusing it. Stricter
is allowed and looser is not, so nothing here amends the exit; it is recorded so that a later
reader does not have to discover that the exit could have been passed by stapling.

### W3-F3 — the baseline the margin is measured against does not repeat itself

The mixed workload re-asked the teacher, through the same provider with the same prompts, the
ninety-six tasks W2 had already asked it. That makes it an **accidental second run of the
baseline** §2.2(c) reads. It moved: **12 of 96 verdicts changed**, for a net of −2 points.

The non-inferiority margin is **3 absolute points**, and exit (c)'s non-inferiority half is met
at a drop of **2**. A difference of two points against a baseline whose own re-run moves twelve
tasks is not distinguishable from the baseline moving. The margin was fixed in W0 before any
measured number existed, and §2.3 forbids amending it now, so the exit is read exactly as
frozen and the qualification is recorded beside it rather than folded into it.

The local side of the same comparison is the control, and it is clean: on the ninety-six tasks
the layer offered nothing for, `local_model`'s prompt is byte-identical to `no_memory`'s, and
**zero verdicts diverged**. The instability is the external provider's, not the harness's.

Both readings are marked `observation` in the record. Nothing recomputes them and no exit reads
them (22B S22B-002), and inventing a tolerance for them after the fact would be the same error
in the other direction.

### W3-F4 — the acquired layer bought grounding, not accuracy

§3.2 named this risk in advance: *"Layer 1 may stay thin even after W1 … the honest response is
the one 22C modelled: measure it, say so, and let W3's numbers be a typed negative."* Measured:

* `local_model` 66 verified, `no_memory` 66 verified — the layer's contribution to the success
  exit is **exactly zero points**;
* all four retrieved facts were answered correctly *and* rested on their spans, moving four
  outputs from ungrounded assertion to **grounded** — 30 ungrounded down to 26.

The layer did precisely what eight facts can do. Every one of them landed, and eight facts
against a hundred tasks cannot move a success rate. The subtraction exit (b) reads —
`local_model` minus `retrieval_only`, 62 points — isolates the *model*; the one that would
isolate the layer is `local_model` minus `no_memory`, and it is 0.0. Both are in the record,
because W2-F3 already noted that the allocation reads the first and means something closer to
the second.

**No model arm has abstained once**, across four measured workloads and four hundred answers.
The typed abstention is offered in every prompt and the reader recognises it; nothing produces
it. Exit (d) has two ways to pass and this system has only ever tried one of them.

### What the numbers do not say

The local model was measured on **one** configuration — Qwen3-8B Q6_K, CPU, `--reasoning off`,
temperature 0, seed 22 — against **one hundred** authored tasks in **one** language over **two**
cleared textbooks. A 66 is that model on those tasks; it is not "a local model can do 66 %". The
W2-F2 notation tax is still inside every one of these numbers, and it is worth roughly a dozen
tasks per model arm.

### Evidence

| File | SHA-256 of the sealed body |
|---|---|
| `evidence/sprint-22d-w3-local-model.json` | `5b2ab62914932e09e23e5c16edd06c2a29311abe5736ed73b1b63763e732f832` |
| `evidence/sprint-22d-w3-mixed-workload.json` | `4dbc8dcbe062124936568af749f8ba73a5df01e3a0cb41c0a6078cc107599513` |
| `evidence/sprint-22d-w3-exits.json` | `ec1fa4bbfcb7f2e380a8642d0ec3a2d56e461c24db7fdcae696818ca5fa87769` |

### What W4 inherits

A **typed negative with one exit met**, and every number in it produced by an instrument frozen
before it ran. W4 owes exit (e) — the prior domain, learning and safety gates re-read from their
sealed records against this head — the five exits read once with `--check` rebuilding the
document from sources, and the release under the negative-outcome tag
`sprint-22d-evidence-baseline` rather than `sprint-22d-language-baseline`, because §2.1 fixed
both names in advance and three of the four measured exits are not met.

It also inherits four repairs that are **not** this sprint's to make: W3-F1's output-kind blind
spot in the escalation policy, W3-F2's grounding definition, W2-F1's missing union member, and a
Layer 1 that needs to be two orders of magnitude larger before the ten-point margin means
anything.

---

## W2 — three baselines, and a comparator that was priced before it was read

W2 owed the three non-local arms on the frozen hundred, each sealed, with the external arm run
through the governed boundary. The runner did not change: W0 built `run_arm` to own
verification, accounting, escalation and the citation walk while an arm owns only what it
answered, so this wave is **three answerers**, not a second runner.

| Item | What it owed | Outcome |
|---|---|---|
| **S22D-200** — comparator coverage | the model-free arm's ceiling, priced first | **sealed at 4 of 100**, before any arm ran |
| **S22D-201** — `external_teacher` | the only network arm in the sprint | **87 verified**, 100 calls, 0 failures |
| **S22D-202** — `no_memory` | the local model with nothing behind it | **66 verified**, 1 007 output tokens |
| **S22D-203** — `retrieval_only` | model-free, over W1's eight facts | **4 verified, 4 grounded, 96 abstained** |
| §2.2(a) | no external call outside one arm | **construction held**, refusal executed in test |
| tests | W2 evidence, portable | **29**, verified with the weights hidden and `PATH` stripped |

| Arm | verified | abstained | grounded | ungrounded | undecidable | malformed | external calls | output tokens |
|---|---|---|---|---|---|---|---|---|
| `external_teacher` | **87** | 0 | 0 | 30 | 12 | 6 | 100 | 41 441 |
| `no_memory` | **66** | 0 | 0 | 30 | 13 | 3 | 0 | 1 007 |
| `retrieval_only` | **4** | 96 | 4 | 0 | 0 | 0 | 0 | 0 |

**Nothing under `src/` was touched.** One line moved in W0's runner — awaiting an outcome that
is awaitable — so an arm reaching an async governed boundary and an arm reading an index can be
the same kind of thing to one runner. Two runners would have been two sets of accounting.

### A deviation from the plan's ordering, and why it did not cost anything

§3's W2 row says the external arm "runs before the local microbenchmark so that the
no-external-call construction is never weakened to accommodate it". **It ran third**, because it
waited on a credential and then on two provider decisions, and the two local arms were reachable
meanwhile. Recorded rather than glossed: a plan that names an order is owed either compliance or
a reason.

The reason it cost nothing is that the construction is not an ordering. `run_arm` raises
`ExternalProviderRefused` the moment a non-external arm reports a provider call, and that refusal
is executed in a test rather than trusted — so no local arm *could* have been quietly widened to
accommodate the third one, whenever it ran. Had the construction been an audit of what happened,
the order would have mattered exactly as much as §3 implies.

### W2-F1 — the union member W0-F3 asked for is out of this sprint's scope

W0-F3 said W2 must add "a `LocalApiProviderConfig` member of the discriminated provider union".
It cannot. `ProviderAdapterConfig` discriminates on `adapter: ProviderAdapterKind`, and that
enum is not only Python: `provider_output_tables.py` hard-codes its six values into a
`CheckConstraint`. Widening it is a **schema change**, which §2.3 excludes outright, and §2.1
separately refuses new released enum members.

Resolved by this sprint's own precedent rather than by preference — W0-F2 found `BenchmarkDomain`
had no English member and the answer was *declare under an existing member, record the mismatch,
widen nothing* (22C W2-F4). The local model therefore reaches the released
`openai_compatible` mapping through this sprint's runner, its calls are counted by W0's
accounting record, and the missing union member is carried to 22E. The no-external-call
construction is **stronger** for it, not weaker: still no registrable network adapter.

### W2-F2 — a dozen tasks per arm turn on typography rather than on physics

The registered physics verifiers decide `m/s**2`, `m/s^2`, `kg*m/s` and `N s`. They **error** on
`m/s²`, `kg·m/s` and `Ω` — the spellings a model actually writes. A probe against the local
model returned `15 kg·m/s`, `9.8 m/s²`, `6 Ω`: correct physics, unparseable notation. **Fifty of
the hundred tasks are exposed**, and both model arms lost twelve or thirteen to it.

The damage is not only the lost points. `6 Ω` is also the *wrong* answer, and an undecidable
verdict hides that in both directions — a wrong answer and a right one arrive at the same
verdict for a reason neither is about.

**Not repaired, by decision.** A measured number existed by the time it was found, and §2.3
forbids tuning a pre-registered configuration — the answer-form prompt included — after that
point. §2.2(b) already requires the undecidable count to be reported, so the repair the sprint
is allowed is the one it takes: report the count, the cause, and the per-verifier breakdown, so
the number cannot be read as capability. **W3 must read the seventy per cent floor knowing the
instrument taxes notation**, and a successor re-freezing the answer-form contract is where the
real fix belongs.

> **Generalisable, and it is W0-F1 one layer out: a verifier that starts and cannot decide is
> not evidence about the answer.** Count it, name its cause, and never let it sit in the same
> column as a verdict.

### W2-F3 — the comparator's ceiling is four, and the ten-point margin barely bites

S22D-200 priced `retrieval_only` **before** it ran: Layer 1 holds eight facts, and exactly four
of the hundred tasks ask for a quantity it holds. The arm then verified exactly four, all four
grounded, nothing ungrounded. That is what pricing first buys — the number was read, not
explained.

But it makes §2.2(b)'s second half nearly vacuous. "At least ten points above retrieval-only"
is a bar of fourteen per cent when the comparator sits at four, and the **seventy per cent
absolute floor is the criterion that actually bites**. There is a second reading worth stating:
comparing `local_model` against a model-free arm isolates the *model*, not the layer — the
layer's contribution is the distance between `local_model` and `no_memory`, which the plan does
not read. Both are recorded and **neither is changed**: §2.3 forbids retuning a pre-registered
configuration, and W1-F1's repair was to publish the pricing and read the instrument as frozen.

**W1-F3's alias debt came due here and was paid before any number existed.** The layer holds
`g = 9.80 m/s2` at ladder status `grounded`, but the microbenchmark asks for "standard
acceleration due to gravity" — a third vocabulary after the source's notation and the holdout's
wording. Without the alias the arm would have missed for a plumbing reason and the record would
have read as a coverage failure, which W1-F3 exists to prevent. The alias was added **on the
fact**, the movement it caused is stated in S22D-200 (three servable tasks to four), and every
W1 seal still rebuilds byte-identically.

### W2-F4 — a retry that could not tell "try again" from "you have no budget left"

The first external arm ran on OpenRouter's strongest free route and produced a record that would
have been read as a weak teacher: 30 verified, 62 undecidable. It was neither. **68 of 100 tasks
never got an answer**, 207 of 239 attempts failed, and the cause was not capacity — OpenRouter's
free tier allows **fifty free-model requests a day**. A hundred-task arm could never have
completed there. It is arithmetic, not weather.

And the bounded retry made it worse: it treated the daily allowance like a transient failure and
spent 239 attempts against a limit of fifty. Of the 32 answers that did arrive, **30 were
correct** — a 94 % teacher, on its way to being recorded as a 30 % one.

Fixed as a distinction rather than as a number: a 404 is capacity and earns another attempt; a
429 is the allowance and stops the whole arm, because every further attempt spends budget the
run still needs. The abandoned record is **kept, sealed and renamed**
(`sprint-22d-w2-external-teacher-abandoned.json`) — a route swapped without the evidence for the
swap is a route swapped until the number was liked.

The teacher of record is `claude-code`, **one of W0's four frozen external providers**, so the
enumeration did not widen. It completed 100 tasks in 100 calls with zero failures.

> **Generalisable: an availability failure and a capability result look identical in a score.**
> Count attempts apart from answers, and let a run refuse rather than finish, because a finished
> run is the one nobody re-reads.

### What the two model arms say about the grounding exit

Both were offered the typed abstention in the prompt. **Neither used it once in a hundred
tasks.** Every one of the thirty factual outputs is therefore an ungrounded assertion, in both
arms. §2.2(d) reads that count being zero, so W2 establishes where W3 starts: **thirty, twice**,
and only the retrieval arm — which answers from a span or not at all — is at zero today.

### W2-F5 — the same portability lesson, a third variant, and it cost a red CI again

GC-F4 taught that a test asserting a fact about the machine it runs on is not testing the code,
and the pre-push check that came out of it hid the weights and stripped `PATH`. **It did not
remove the optional extra.** One W2 test drives `run_arm`, which refuses *before* the first task
when a frozen verifier is registered but unavailable — W0-F1's own refusal, working exactly as
designed. In the CI test lane, which installs no `verification-physics`, the test asserted one
refusal and received another.

The environment is now reproduced rather than approximated: the same `uv sync` line the lane
uses, with the weights moved aside and `PATH` stripped — **91 passed, 10 skipped**, where the
approximate simulation had reported 98 and 3. The seven-test difference *was* the bug.

> **Generalisable: a portability check must reproduce the environment, not resemble it.** Host
> facts, installed binaries and **optional dependencies** are three separate axes, and a
> simulation that covers two of them is green for the same reason the real thing is red.

### Evidence

| File | SHA-256 of the sealed body |
|---|---|
| `evidence/sprint-22d-w2-retrieval-coverage.json` | `1b5b1b0f9a480d605bebfed9d0120dae6f26238f7ca43e0fb49bbd94367d2ad3` |
| `evidence/sprint-22d-w2-external-teacher.json` | `ccc12b83f8ce11ccebcd6367375bb8f9c56e2d62ce174a3f395479258f924f31` |
| `evidence/sprint-22d-w2-external-teacher-abandoned.json` | `e08f5e257e16ba10881063c7b289c7ee370a8ac6ec3098ec64a055bed525113c` |
| `evidence/sprint-22d-w2-no-memory.json` | `749e9a5a312234df517330395c400862e4e0955557493ad8779871805f8e8b15` |
| `evidence/sprint-22d-w2-retrieval-only.json` | `3ddbdd1cd4d69672521558f3d42722bc61138d7b3e6c5936bce3f91d03ac8806` |

### What W3 inherits

The bar is **87**, so non-inferiority needs 84 and the absolute floor needs 70 — from an arm
that scored 66 without retrieval. The layer must be worth eighteen points. It inherits W2-F2's
notation tax on that reading, W2-F1's missing union member, thirty ungrounded assertions to
drive to zero, and the fact that **no language-model arm has yet abstained even once**.

---

## Gate closure — the two blocking dependencies, and the four things that would have let them shut

W0 finished around two gates rather than through them, named an owner on each, and left
`w2_may_proceed: false`. This is not a wave in the plan; it is the work that turns that flag
over, and it is recorded because closing a gate honestly turned out to be most of the job.

| Item | What it owed | Outcome |
|---|---|---|
| **S22D-003** — model licence | an `OperatorLicenseClearance` over named bytes, decided by the owner | **sealed** — Qwen3-8B-GGUF Q6_K, Apache-2.0, `internal_use` + `benchmark_use` |
| **S22D-004** — serving runtime | something on this host that serves the cleared weights | **sealed** — `llama-server` b10442, CPU, answered through the released mapping |
| the licence gate | conclude only on a determination | **GC-F1**, it concluded on a file existing |
| the runtime gate | conclude only on a runtime that serves | **GC-F2**, it concluded on `PATH` |
| the first real local call | §1.2's seam, executed | **GC-F3**, the model returned nothing and the mapping was content with it |
| preflight | re-read, both gates concluded | **`w2_may_proceed: true`**, `invariants_hash` unmoved |
| tests | gate-closure evidence, portable | **30, verified with the weights hidden and `PATH` stripped** |

**Nothing under `src/` was touched.** The clearance is a released contract, the advisory is a
released list and the wire mapping is a released module; the two gate repairs are in this
sprint's own driver.

### The search was decided by a requirement, not by a preference

The preflight asks for the licence text **read out of the distribution**, not transcribed from
a model card (22C W1-D2). Four candidates were examined and **three could not satisfy that at
all** — not because their licences are restrictive, but because there were no bytes to hash:

| Candidate | Licence tag | `LICENSE` beside the weights |
|---|---|---|
| `Qwen/Qwen3-8B-GGUF` | apache-2.0 | **present** |
| `bartowski/Mistral-7B-Instruct-v0.3-GGUF` | apache-2.0 | absent — and upstream ships none either |
| `unsloth/Phi-4-mini-instruct-GGUF` | mit | absent — upstream's covers different bytes |
| `lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF` | llama3.1 | absent, upstream `gated: manual`, advice `unknown` |

A repository licence tag is a publisher's assertion in metadata. `source_content_hash` exists
so a clearance cannot drift onto a different edition of the same work, and a tag is exactly the
drift it is built to catch.

Two comparisons were then made that a licence identifier does not supply. The archived text was
diffed against **apache.org's own copy**: the only substantive difference is the appendix
copyright line filled in as `Copyright 2025 Alibaba Cloud`, which is what the appendix is for.
No rider, no acceptable-use policy, no field-of-use clause — *"it says Apache License at the
top"* and *"it is the Apache License"* are different facts and only the second one was
recorded. And the weight file's SHA-256 was compared against **the publisher's own object id**
in the distribution tree: a local hash says the file did not change after it landed, and only
the publisher's id says the file that landed is the file that was published.

The determination itself is the owner's and is recorded as given: `internal_use` and
`benchmark_use`, **six rights withheld**. That gap is a decision with a consequence — without
`modification`, `derivative_work` or `model_training` the optional §2.3 adapter is now closed
by the operator's own grant as well as by the chemistry corpus being NC-SA. Two independent
reasons, so W4 surplus cannot reopen it by finding spare schedule.

### GC-F1 — a gate that concluded on a file existing

`_model_licence_gate` reported `concluded: True` for any JSON at the clearance path and read
`cleared_by` and `permitted_uses` off it without asking whether they meant anything. An empty
object would have flipped `w2_may_proceed` with `cleared_by: null`, and W2 would have served a
model nobody had cleared while the record said someone had.

`OperatorLicenseClearance` already refuses `unknown` and `conflicting` on its own — a decision
or nothing — so the repair is to ask the contract rather than the filesystem, plus one rule the
contract cannot know: a determination that does not permit `internal_use` describes a model
that may not be served, and a cleared model that cannot run is not a cleared model.

> **Generalisable: the presence of an artefact is not the conclusion of the review that
> produces it.** Where a released contract already encodes the refusals, validate through it;
> a gate that reads fields off unvalidated JSON has replaced a decision with a filename.

Testing that repair turned up a stronger property than the repair itself. `OperatorLicenseClearance`
is a **hashed** experience contract, so widening `permitted_uses` in the sealed record fails on
the clearance's own digest *before* any rule here looks at the value. The decision belongs to
the person who made it rather than to whoever last had write access — which is why the two
cases are now tested apart: a tampered record fails on the hash, and a *coherent* clearance
carrying an inadequate grant has to be built through the contract to reach the rule it is about.

### GC-F2 — a gate that concluded on `PATH`

`_local_runtime` probed `shutil.which` over four candidate names. Once `llama-server` was
symlinked onto `PATH` the gate would have said yes, and nothing had answered a request. The
blocking dependency was never "a binary with this name"; it was *a runtime for the cleared
weights*, and the two are only the same thing if you never ask the runtime anything.

The gate now reads the sealed S22D-004 record and recomputes its seal, and `PATH` presence is
kept as a separate, weaker fact. Before the proof existed the preflight was run with the
symlink already in place and still reported `local_serving_runtime` blocking — which is the
only reason this repair is known to work rather than believed to.

`llama-server` was chosen over a model manager for an evidential reason rather than an
aesthetic one: the clearance must name the SHA-256 of the weight file, and a runtime that
stores weights in its own blob store under its own manifest digest cannot produce that number.

### GC-F3 — the first real local call, and an empty answer nobody would have noticed

§1.2 claims a local model reaches the governed path through the existing `openai_compatible`
seam. That was a reading of the source until a real server's bytes went through it, and running
it produced the finding this closure is worth most for. **The cleared model is a hybrid
reasoning model, and how much of its output budget goes to thinking is a runtime setting that
no mainstream default pins.** Both settings were run, on the same prompt:

| `--reasoning` | content | `finish_reason` | output tokens |
|---|---|---|---|
| `on` | *(empty)* | `length` | **64** |
| `off` | `ready` | `completed` | **2** |

`map_response` reads `message.content`, found an empty string, and **returned a valid response
without complaint**. So an answer nobody wrote and an answer the model declined to give arrive
downstream in the same shape, separated only by a token count nobody was comparing — and the
frozen escalation policy escalates on invalid answer form while the accounting exit divides
cost by answers produced. W3 would have escalated every task, charged thirty-two times the
tokens for output nobody could read, and the record would have called it a capability result.

The repair is to pin the reasoning mode into the runtime harness alongside model, quantization,
context and sampling, as §1.2 asks. The failing configuration is **kept and re-run**, because a
pinned flag with no reason attached is one the next person removes.

> **Generalisable: a model that produces nothing is not the same event as a model that produces
> a wrong answer, and a normalizer that reads one field cannot tell them apart.** Assert on the
> content, not on the call succeeding.

### GC-F4 — three tests that could only be green on one machine

The first CI run on this head failed, and every failure was a test written against *this host*
rather than against the claim it was supposed to make — in the same change whose driver
docstring says a check that can only pass in one place has stopped saying anything.

- one asserted `llama-server` is genuinely on `PATH`, which is true here and false everywhere
  else. Worse than a red build: on any other machine the gate would have refused for the wrong
  reason and the defect replay would have passed **vacuously**, which is 22A W4-F2 with the
  colours reversed;
- one recomputed `invariants_hash` from the running machine and compared it against the sealed
  record. `invariants_hash` binds the *declared* host, so recomputing it elsewhere asks whether
  the reader is the writer — a different question, and one that always answers no;
- one exercised a refusal that sits *behind* the refusal for absent weights, so where the 6.7 GB
  file is not on disk the driver refused first and for something else.

Repaired as three different things, because they are three different mistakes. `PATH` is now
**simulated** with a stub so the replay is meaningful on every host; the invariants claim is a
comparison of two **recorded** values against W0's pinned hash; and the ordering-dependent
refusal carries the `_NEEDS_WEIGHTS` skip the repository already uses for the cleared sources —
losing nothing, because the same rule is asserted host-independently against the preflight gate.
A second gate test was added so the runtime gate is now watched saying **yes** as well as no.

Then the fix was verified the way it should have been written: the suite was re-run with the
weight file moved aside and `PATH` stripped of the symlink — **28 passed, 2 skipped** — before
anything was pushed.

> **Generalisable: a test asserting a fact about the machine it runs on is not testing the
> code.** Simulate the environment the rule reads; pin recorded values rather than recomputing
> host state; and where an ordering genuinely needs a local artefact, skip explicitly rather
> than letting an earlier refusal answer for a later one.

### Evidence

| File | SHA-256 of the sealed body |
|---|---|
| `evidence/sprint-22d-model-rights.json` | `1a844ffb1ecb553ad9f113270507fcc86351194148a6b6acd0b26e5c616f0707` |
| `evidence/sprint-22d-runtime.json` | `5a7e4d011fe4cdbf216af1b4e306482949d2e66a3fd284111603826a9e25f3d7` |
| `evidence/sprint-22d-preflight.json` | `3a27dd3b65106d1915dda19ca3b7fd430e2346bfe955b204befe669eea00af16` |

| Bytes named by the records | SHA-256 |
|---|---|
| the archived licence text (`evidence/sprint-22d-model-licence.txt`, 11 544 B) | `5de36594c10839788a8c589443a8ef9d8b8d17c65a1b5807206ae037fc36c6bd` |
| the cleared weight file (`Qwen3-8B-Q6_K.gguf`, 6 725 899 040 B) | `cb042ccd76795a8830d6be6bd4165245847cc68e41797b13bd61aed4c2cfbce6` |
| `llama-server` b10442 | `4d9d7873bc61c197fb11182e961192d4e2ba0341558b8053814744f01bdddd8d` |

The preflight record's hash moved and W0's did not become wrong: W0 sealed
`0732e027…` when both gates were open, and a gate closing is a change in the world rather than
in the declared host. `invariants_hash` is `122bcd40…` in both, which is the check that says so
— the CPU, the GPU, the platform and the Python version had no business moving because a person
made a decision (22B S22B-002).

**Recomputable here, observed there.** The licence bytes are archived in this repository, so CI
recomputes that hash on every run. The weight file is 6.7 GB and the binary is a release
artefact; both live outside the repository, so their hashes are recomputed where the files exist
and compared against nothing where they do not. A `--check` that demanded the weights would fail
everywhere except this host, and a green check that can only be green in one place has stopped
saying anything.

### What this deliberately did not build

W0-F3 named three missing things and this closes one. The `LocalApiProviderConfig` union member
and the adapter that constructs it are **released code**, and released code belongs in a wave
with its own review rather than in a gate closure — so `what_this_does_not_yet_provide` names
both in the record. W2 inherits them, plus **W1-F3**: the layer is keyed as the source writes
and asked as the asker speaks, and the alias belongs on the fact.

---

## W1 — Layer 1 goes from one artifact to eight facts, and a holdout from 0 to 4

The plan gave W1 one job and one deadline: implement §1.5's declarative-fact path against a
fresh unread holdout, and **know in week one** whether Layer 1 can be filled at all, because
exits two and four both rest on it.

| Item | What it owed | Outcome |
|---|---|---|
| **S22D-100** — coverage | the verification floor's coverage priced **before** the campaign | **sealed**, 8 candidates and 7 refusals across the five cleared chapters |
| **S22D-101** — acquisition | grounded span → observation → claim through the twelve released verifiers | **8 of 8 promoted**, Layer 1 **1 → 8** |
| the ladder | the kernel as consistency oracle, exact comparison | **5 corroborated, 3 grounded** |
| the seam | `ExtractionDecisionOutcome`, which had no implementation | **15 decisions**, one per candidate *and* per refusal |
| parity | in-memory against the provisioned store (22C W2-F2) | **layers identical** |
| **S22D-102** — the holdout | read once, both arms | **arm A 0 / 12, arm B 4 / 12, improvement 4** |
| gates | ruff, format, mypy, bandit, schema, language | **clean** |
| tests | W0 and W1 evidence | **42 passed** |

### W1-F1 — the standing rule this sprint carries, broken by the wave that carries it

22C W3-F1 graduated into §0 as a standing rule: *a verification floor decides what can be
acquired, and its coverage is priced before the campaign, not after — any wave that intends to
retain content states in advance which floor will verify it and samples the source against that
floor.* **W0 froze a twelve-case declarative-fact holdout without sampling the cleared sources
against it.** Nothing in the W0 record prices what chapters 2, 3, 4 and 6 actually state.

The tempting repair is the wrong one. Once the coverage is measured it is obvious which cases
could be made answerable, and re-cutting the holdout to match would be choosing the questions to
fit the answers. `measured_values: 0` does not make that honest — no arm had run, but the
*selection* would have been made against the data. So the holdout stayed exactly as frozen, its
case hashes are still W0's, and `test_the_holdout_was_not_re_cut_after_the_coverage_was_seen`
is the assertion that says so.

What W1 did instead was pay the debt in the right order: **price the coverage, publish it, then
acquire.** `sprint-22d-w1-coverage.json` is `S22D-100` and it precedes `S22D-101` in both
sequence and evidence.

> Generalisable rule: **when a wave discovers that its own instrument was specified without its
> coverage priced, publish the pricing and read the instrument anyway.** Re-specifying it is
> the one move that destroys the reading.

### What the cleared chapters actually hold

| | |
|---|---|
| candidates located | **8** — C, H, O, Na, Cl from an element-mass table; K stated in prose; an aspirin molecule; `g` |
| refusals | **7** — 5 numerals that lost their exponent, 2 subjects that are sentence fragments |
| chapters yielding nothing | chemistry 4, physics 2, physics 4 |

Three locators, fixed by the books' own layout rather than by the facts wanted — the same rule
22C's chapter reader follows, and the campaign takes whatever it finds.

**The table header is the whole safety argument.** Chemistry chapter 4 is full of lines shaped
exactly like an element-mass row — `C` then `1`, `H` then `4` — and they are stoichiometric
subscripts. A locator keyed on the row shape alone retains *the atomic mass of C is 1*, and
every verifier downstream agrees with it, because nothing after the locator knows what the
number was supposed to mean. Gating on the header (`Average Atomic Mass (amu)` beside `Molar
Mass (g/mol)`) is what keeps chapter 4's yield at zero, and
`test_the_table_header_keeps_stoichiometric_subscripts_out_of_the_layer` pins it.

### W1-F2 — the refusals are the locator's most useful output

`pdftotext` renders 6.02214076 x 10^23 as `6.02214076 1023`: the multiplication sign and the
superscript are gone and what is left reads as two numbers. This is 22C's "maths is an image"
wall in its cheapest form, and the honest response is a **refusal with a name** rather than a
repair — 22C W3-D1, generalised from a kernel input to a numeral.

Two things had to be fixed inside the wave before that was true rather than merely intended.
The first locator pass recorded **zero refusals**, because the table row pattern stopped one
column short of the Atoms/Mole column where the mangled exponent lives, and the stated-quantity
pattern excluded spaces so *"the molecular mass of chloroform, which is 119.37 amu"* silently
failed to match. Both are the same defect wearing two faces: **a locator that narrows until the
awkward cases stop matching hides exactly what a locator that refuses them counts.** An unread
column is indistinguishable from a column that is not there, and only one of those is a source
problem worth reporting. Now both reasons fire on real content — 5 and 2 — and 22A W4-F2's rule
is satisfied by execution rather than by design intent.

**And one defect that only running found.** Reading the Atoms/Mole column made the row pattern
consume the newline the *next* row starts with; `finditer` cannot overlap, so the table read as
every other row — three of five, with H and Na simply absent and nothing anywhere saying so.
The boundary is a lookahead now.

### The path itself, which is composition and not a new pipeline

Every retained fact travels the released route 22C already drove: the Corpus Factory ingests the
chapter under **22C's own operator clearance**, rebuilt through `CampaignSourceRights` from
S22C-020 — W1 needs no new rights decision and makes none. A `GroundedSourceSpan` names a byte
range in the *registered* artifact, and the offsets are **found by locating the excerpt in the
loaded bytes** rather than carried over from the raw chapter: the Corpus Factory normalizes, and
a span whose offsets predate normalization cites the wrong bytes. An excerpt that cannot be
found is refused by name rather than re-grounded onto the whole artifact, because a span that
silently widens to the entire chapter is a citation that has stopped meaning anything.

What W1 adds to the released stack is exactly two things: one predicate
(`domain.declarative_fact`, functional and bitemporal, so two different atomic masses for one
element over overlapping validity is a contradiction the *released* detector reports), and the
decision record below. It adds **no promotion rule** — all eight facts passed the twelve
required semantic verifiers through `SemanticPromotionGate` unchanged.

> A released contract's value is not obvious until something reads it: `ClaimPromotionOutcome`
> has no `promoted` member, and comparing against one refuses every fact the gate accepted while
> the record cheerfully prints the gate's own `supported` verdict beside the rejection. Compare
> against the enum, never against the word you expected it to use.

### `ExtractionDecision`, the seam that had no implementation

§1.2 named it as the one genuinely missing step, and this is what it buys: **15 decisions for 8
candidates and 7 refusals**, each with reason codes and a named decider. Without it, 22C's
53-of-59 wall is an *absence* — a fact that is not in the store looks exactly like a fact nobody
looked for. With it, every one of the seven refusals says which rule declined it and why.

### The ladder, and the kernel as consistency oracle

§1.5 frozen in W0: `corroborated`, `grounded`, `refused`. A declarative fact cannot be
recomputed — there is nothing to derive an atomic mass *from* — but a kernel-checkable
consequence can corroborate it. The element-mass table prints the consequence in the next
column, so the released `chemistry.molar-conversion` kernel is fed the **retained** atomic mass
and asked what one printed molar mass in grams amounts to. It must answer exactly 1 mol,
compared over `Fraction`, **never within a tolerance** (22C W1-F3).

| Rung | Count | Which |
|---|---:|---|
| `corroborated` | **5** | C, H, O, Na, Cl — the table prints their molar mass beside their atomic mass |
| `grounded` | **3** | K, an aspirin molecule, `g` — stated with no printed consequence in range |
| `refused` | **7** | the locator refusals |

The three on the weaker rung are not weaker *facts*; they are facts the source states without
also printing something a kernel can check. The record says which of the two every retained fact
is, which is exactly what §4 requires it to claim and no more.

### Both stores, compared against each other

22C W2-F2 is a standing rule because its own worst find was a PostgreSQL active view returning
superseded and retracted claims wearing their old belief — a defect only PostgreSQL had,
invisible to a suite that ran entirely in memory. So W1 acquires **twice**, in memory and on a
provisioned `cognitive_os_s22d_campaign` at migration head `0015`, and compares the acquired
layers rather than the claim identifiers a store assigns. **Identical.** The database has a name
of its own so 22C's sealed campaign store was never opened, let alone written to.

### S22D-102 — the holdout, read once

| Arm | What it is | Verified |
|---|---|---:|
| **A** | the acquired layer as 22C left it — kernel-retained worked examples, no declarative facts | **0 / 12** |
| **B** | the layer after this wave | **4 / 12** |

**Improvement 4, and it is the first non-zero improvement in this lineage** — 22C measured 0 of
4 on both arms and released as a typed negative. Neither arm is a different model or a different
prompt; the only difference is what the store holds, which is the one thing the holdout was
frozen to measure.

The reading is not circular, and that took care. Each case's expected answer was computed *from*
the value it withholds, so an arm that compared the layer's value against that withheld value
would be proving that arithmetic is arithmetic. Arm B instead **derives the answer from whatever
the layer actually holds** and hands it to the case's own registered verifier. The derivation is
code added in W1, not case content, so the frozen hashes are byte-identical — asserted by
`test_the_derivation_table_covers_every_frozen_case_and_moves_no_hash`.

Every one of the eight refusals names the fact it wanted:

| Refused for | Cases |
|---|---|
| sulfur | h-01, h-09 |
| calcium, magnesium, aluminium, iron, copper | h-02, h-04, h-05, h-06, h-07 |
| the Faraday constant | h-12 |

**That is the coverage record, arriving as a holdout result.** The cleared chapters state the
masses their own worked examples happen to use; a holdout drawn from the same domain still wants
facts that live in a periodic table nobody cleared. Which is precisely the number W0 should have
priced before freezing twelve cases, and W1-F1 is where that is recorded.

### W1-F3 — the layer is keyed as the source writes, and asked as the asker speaks

The acquired layer holds `Cl`, `Na`, `g`. A question asks for "chlorine", "sodium", "standard
gravitational field strength". Without a resolution step every case misses for a plumbing reason
and the record reads as a **coverage** failure — the wrong diagnosis entirely, and one that would
have understated what acquisition achieved.

The retrieval path therefore carries an entity-alias table: the first thirty elements plus the
two named constants, general and written once. Cutting it to the names this holdout happens to
ask for would be the questions answering themselves. Carried as a finding because the alias
belongs in the acquired layer — a fact should know its own synonyms — and putting it in the
reader is where W2 will find it again.

### Findings

| ID | Finding | Disposition |
|---|---|---|
| **W1-F1** | W0 froze the holdout without pricing the cleared sources' coverage, breaking the 22C W3-F1 rule §0 carries | **paid in wave** — coverage published before acquisition; holdout **not** re-cut |
| **W1-F2** | The first locator pass recorded zero refusals: the row pattern stopped short of the mangled-exponent column and the sentence pattern excluded spaces; then reading that column made the pattern eat the next row's newline | **fixed in wave** — both reasons now fire on real content, lookahead boundary, all five rows read |
| **W1-F3** | Retrieval needed an entity-alias step the acquired layer does not carry | **carried to W2** — the alias belongs on the fact, not in the reader |
| **W1-A1** | `ClaimPromotionOutcome` has no `promoted` member; comparing against one refuses every fact the gate accepted | **fixed in wave**, recorded because the failure printed the gate's own passing verdict beside its rejection |

### Evidence index

| Record | Item | SHA-256 |
|---|---|---|
| `sprint-22d-w1-coverage.json` | S22D-100 | `ca1364915d1c341c6ab07e1886a8fd37b6bb16bc6485f74fd00d47ed19be591f` |
| `sprint-22d-w1-acquisition.json` | S22D-101, S22D-102 | `befee46f34d092aab6c26bb8d08cec6b176d948c4255054812828ad91ff79a76` |
| `sprint-22d-w1-holdout-read.json` | S22D-102 | `d52c33f3c5a2ee9b9d9658869d3d1b5a51445d8889844f10cf6a3d4ff6af3763` |

`--check` on the acquisition record re-runs the **in-memory** half and compares the acquired
layer and the holdout improvement. The provisioned store is an *observation*, not an invariant:
re-ingesting identical content is refused by the Corpus Factory by design, exactly as 22C's
`--cycle` is not idempotent, and 22C W1-F1's split is what keeps the validator from demanding a
world that cannot be rebuilt.

### What this means for the sprint

Exit two needs the local arm at least ten points above retrieval-only, and exit four needs every
factual output grounded. Both rest on Layer 1, and Layer 1 is no longer one artifact. **It is
also not large**: eight facts, of which the frozen hundred's thirty factual tasks can be served
only where the cleared chapters happen to state the constant. §3.2's named risk — *Layer 1 may
stay thin even after W1* — is neither retired nor realised; it is now a number, in week one, with
its diagnosis attached, which is what the plan asked for.

### Validation

`ruff check` and `ruff format --check` over `src tests scripts infra`: clean.
`mypy src/cognitive_os`: **no issues in 638 source files**. `bandit -r src/cognitive_os`: **0
issues at every severity**. Schema export `--check` and the repository language check: passed.
`facts_22d.py --coverage --check`, `--acquire --check`, `holdout_22d.py --check`: all reproduce.
`tests/cognitive_os/language/`: **42 passed** with the `verification-physics` extra.
Whole suite: **4 570 passed / 235 skipped** in 4 m 09 s.

The W1 tests that read the cleared PDFs skip where those files are absent — they live outside
the repository — while every assertion over the *records* they produced runs unconditionally,
because the records are committed and are what later waves are bound to.

No file under `src/` was touched in W1 either. The declarative-fact path is composition over
released primitives plus one predicate and one decision record, which is what §1.5 predicted
when it called the substrate "largely released".

---

## W0 — the readings frozen, the gates surfaced, and fifty tasks that would have scored zero

W0 measures nothing. It settles what every later number will mean, and it ends with a
fixture-scale run of all four arms that decides no exit criterion and says so in its own body.

| Item | What it owed | Outcome |
|---|---|---|
| **blocking check** | 22C released, verified from live handles | **satisfied** — the plan's §0 was already stale |
| **S22D-001/002** — preflight and gates | the host measured, the enumeration derived, three rights gates surfaced | **sealed**, two blocking dependencies named with an owner |
| **S22D-010…016** — pre-registration | every §2.2 reading and §1.5's ladder frozen before an arm exists | **sealed**, `measured_values: 0`, `amendments_made_by_22d: 0` |
| **S22D-020** — the W1 holdout | fresh, unread, disjoint, arms proved different without spending a case | **sealed**, 12 cases, probe outside the set |
| **S22D-030** — the §3.1 slice | ten fixture tasks, four arms, one refused external call, one citation walk, one abstention | **ran**, and found W0-F1 |
| gates | ruff, format, mypy, bandit, schema drift, repository language | **clean** |
| tests | the W0 evidence file, in an environment with the extra and one without | **20 passed / 16 passed + 4 skipped** |

### The blocking check, and a plan sentence that had gone stale

§0 of the backlog states, at some length, that 22C's release *had not happened* and that W0
blocks on it. Between the plan being written and this wave running, it did. W0's first act was
to read it back rather than assume either way:

| Handle | Read from | Value |
|---|---|---|
| tag object | `git ls-remote --tags origin` | `22d88878251e6670cb365b76dce925eee6da1c13` |
| peels to | the remote's own peeled ref | `5ecb7c9ebd18c73ec78ac012103c9c77b61443f4` |
| ancestry | `git merge-base --is-ancestor … origin/main` | **ancestor**, and equal to `origin/main` |
| exact-head CI | `actions/runs?head_sha=5ecb7c9…` | run **31885260162**, `success` |
| protection | `branches/main/protection` | 27 required checks, `enforce_admins: true` |

The blocking dependency is therefore **satisfied rather than waived**, and the preflight record
says so in a field of its own so that nobody later reads the plan's §0 as this sprint's state.

### The host, and why the CPU number is the claim

§1.3's table is reproduced by measurement rather than transcription — `/proc/cpuinfo`,
`nvidia-smi`, `statvfs` — and split the way 22B's reference host and 22C's W1-F1 require:
**invariants** are recomputed by `--check`, **observations** are recorded and compared by
nothing. Free memory and free disk move every minute of every day; sealing them as invariants
is how a validator ends up tempting somebody to edit history so it passes.

| | |
|---|---|
| CPU | AMD Ryzen 7 5700X, 8 cores / 16 threads |
| GPU | NVIDIA GeForce RTX 5070 Ti, 16 303 MiB |
| CPU-viable for a 7–8 B quantized model | **yes** |
| GPU sufficient for parameter-efficient fine-tuning | **yes** |

The GPU passing is exactly why the adapter stays outside every exit (§2.3). The exit asks for
**CPU viability** — a claim about owned resources, not about speed — so the CPU configuration
is the configuration of record and GPU numbers are reported beside it, never in place of it.

### W0-F1 — fifty of the hundred would have scored zero, and the record would have called it capability

**The wave's real finding, and §3.1 is the only reason it was found on ten tasks instead of a
hundred.** The frozen verifier set names five released verifiers. Three of them —
`physics.unit_conversion`, `physics.quantity`, `physics.dimension` — live behind the
`verification-physics` optional extra.

`build_builtin_registry()` does not omit a verifier whose dependency is absent. It registers it
as *unavailable*, and `list_all()` returns it alongside the ones that can actually run. So a
verifier set chosen by reading the registry looks complete, and `VerifierRegistry.get()` then
answers `None` for half of it. The runner's honest reading of that — §2.2(b): *a task the
verifier cannot decide is counted as a failure for every arm* — turned **50 of 100 tasks into
silent zeros**. The 70 % floor becomes unreachable by construction, and the shortfall reads as
a capability result in a record that mentions no dependency anywhere.

The repair is a refusal, not a count. `require_benchmark_verifiers()` runs before the first arm
and raises `BenchmarkVerifiersUnavailable`; `verify_answer` uses `registry.require()` rather
than `get()`, because `require` distinguishes *unavailable* from *not registered* and `get`
throws that distinction away. §2.2(b)'s allowance was always about an **answer** the verifier
cannot decide. It was never about a verifier that cannot start.

> Generalisable rule: **a registry that reports what it cannot run is not an availability
> check.** Read `list_available()`, call `require()`, and treat a missing dependency as a
> refusal before the run rather than as a zero inside it.

With the extra present, all 110 frozen tasks — the hundred and the ten fixture tasks — are
decided correctly by their registered verifiers, asserted by
`test_every_frozen_task_is_decidable_by_its_registered_verifier`.

**What that check proves, and what it does not.** It supplies each task's own expected answer
and requires a pass, so it proves the instrument *runs*: the verifier is available, the
configuration is well-formed, the units parse, the tolerance is sane. It does **not** prove the
expected answer is the right answer to the English prompt — nothing mechanical here can, and
§4's "authored by the same repository it measures" is exactly that limitation. W0-F4 below is
what happens when that gap is not stated.

### W0-F4 — an expected answer that was really a tolerance, and the class it belongs to

Auditing the holdout's arithmetic by hand found `s22d-h-02` authored with `0.005` — its
tolerance — sitting in the expected-answer slot. The correct answer is 2.00 moles. **No
decidability check could have caught it**, because `{"expected": "0.005", "relative_tolerance":
"0.005"}` is a perfectly well-formed verifier configuration that passes when handed its own
expectation. One case in twelve would have been unwinnable by any arm, and W1's improvement
number would have carried a silent ceiling of 11 of 12.

The fix is the class, not the instance. Holdout cases now **compute** the expected answer from
the withheld fact — `_moles`, `_mass_of`, `_molar_mass`, `_weight` — instead of taking both as
literals side by side, so the two can no longer disagree. Typing a derived value next to the
value it derives from is the defect; one of them has to be the other's output.

Auditing the same way found a second, quieter problem: `s22d-h-08` and `s22d-h-09` were methane
and ammonia, whose molar masses need carbon and nitrogen — **two facts the frozen hundred asks
about directly**. The disjointness check compares withheld-fact names against the hundred's
prompts and passed them, because the withheld fact was hydrogen in both. They are now hydrogen
chloride and hydrogen sulfide, built only from facts this holdout already owns.

> Generalisable rule: **a disjointness check over the field a case declares cannot see the
> facts a case depends on.** Separation has to be argued over the whole derivation, not over
> the one input the record names.

### W0-F2 — a released vocabulary with no word for this benchmark

`BenchmarkDomain` has nine members and none of them is English or language. Per the 22C W2-F4
rule — *a pipeline may be stricter than a released primitive and never more permissive, and it
may not invent a value for a released vocabulary* — the microbenchmark is declared under
`GENERIC` and the mismatch is carried as a finding. Adding an enum member is the exact shape
22A spent a sprint dissolving, and this sprint is not the one to re-add it.

### W0-F3 — `LOCAL_API` is a released kind with nothing behind it

§1.2 reads the shared `providers/openai_compatible.py` mapping as meaning a local model "plugs
into the governed model path through an existing seam rather than a new adapter". **Half of
that is true.** The wire mapping is genuinely reusable and is already shared by two adapters.
But `ProviderAdapterConfig` is a closed discriminated union of four members and every one of
them is `NETWORK_API` or `CLI_AGENT`; there is no `LocalApiProviderConfig` and no adapter that
points at a local server. `ProviderKind.LOCAL_API` is a released enum member with **zero**
configuration classes behind it — the same shape as `ExtractionDecisionOutcome`, a released
contract with no implementation.

W2 therefore adds released code rather than composing over it: a union member, an adapter over
the existing mapping, and a serving runtime, none of which exists on this host today
(`ollama`, `llama-server`, `llama-cli`, `vllm` all absent). Surfaced rather than absorbed
(§1.2), because a wave that quietly writes a new adapter has spent its budget on a gap the plan
priced at zero.

### The three rights gates, and the one this program refuses to decide

22C W1-D2 is a standing rule now: *a program may check a licence and advise on it, and may
never decide it.*

| Gate | State | Blocks |
|---|---|---|
| the model's licence | **not concluded** — no clearance exists | W2, W3's local arm, exits one to four |
| the adapter corpus | **concluded by 22C** — both sources cleared, `model_training` not among the granted rights | nothing (§2.3 puts the adapter outside every exit) |
| the microbenchmark's own content | **concluded here** — 100 of 100 authored in-repository | nothing |

The model gate is reported as a blocking dependency with a named owner and an exact required
artefact: an `OperatorLicenseClearance` naming the weight file's SHA-256, the SHA-256 of the
licence text **read out of the distribution rather than transcribed from a model card**, and
the `CorpusUsageRight` values the operator permits. No model is nominated here and no
"temporary" one is substituted — §3.2 — because a benchmark run on unclear weights is evidence
that cannot be released.

The corpus gate's answer is recorded whether or not the adapter is ever attempted, because it
decides what the option would be worth: one cleared source is CC BY-NC-SA 4.0, so every
adaptation inherits noncommercial and ShareAlike and an adapter trained on it is internal-only
by construction.

The third gate is §1.4's question hiding inside the first exit. Every prompt and every expected
answer in the hundred is written here. The *facts* the thirty factual tasks ask about are
ordinary constants the two cleared sources state, and both are cleared for `benchmark_use`;
asking an original question about a stated fact is authorship, and nothing is copied out of a
source into this repository.

### What the pre-registration freezes, and why each piece could otherwise bend

`sprint-22d-pre-registration.json` and `sprint-22d-contracts.json`, revision 1, published
before the first arm. The five exit sentences are the allocation's, verbatim;
`amendments_made_by_22d` is **structurally** zero because 22D's plan contains no gate-owner
amendment path at all.

**S22D-011 — "no large external LLM" is a construction, never an audit.** The four external
adapters are enumerated by name and *derived from the discriminated union* rather than typed
out beside it, so `test_the_external_provider_enumeration_matches_the_released_union` fails if
a fifth ever appears. That test is the only mechanism keeping the first exit true after W0
stops looking (22A W4-F1). The local components that already run on this host — embeddings,
reranking, the verifier registry, and the model under measurement — are named out of scope, so
the boundary cannot be argued about once a number exists.

**S22D-012 — the hundred.** 100 tasks, one content hash each, `measured_values: 0`. Seventy
are closed-form computations over values the prompt itself states; twenty state a declarative
fact; ten derive a result that consumes one. The ten-point margin compares **local-model against
retrieval-only**, both measured in this sprint, neither imported (22B W4-A1). `retrieval_only`
is deliberately model-free — it returns what the index found and nothing interprets it — which
is what makes "the acquired layer contributed something" decidable rather than a description of
a better prompt.

**S22D-013 — the margin nobody has met yet.** The non-inferiority margin is fixed at **3.0
absolute points** of verified success, and the 25 % reduction is read on **calls** and
**accounted cost** *separately*, so it cannot be claimed on whichever moved further.

**S22D-014 — grounded, uncertain, and the third case.** The typed abstention is a value
(`cogos.abstain.insufficient_grounding.v1`) the runtime produces and the runner recognises;
an abstaining outcome carries no answer at all, enforced in the contract's constructor, so
there is nothing for a verifier to mistake for one. Grounded means the walk **loads the cited
bytes and hashes the cut span** — a digest proves bytes and not usability (D7 W3-F1). The
thirty factual task ids are listed in full, and the exit reads the third case being zero.

**S22D-015 — §1.5's ladder, before any fact is admitted.** `corroborated`, `grounded`,
`refused`. The kernel changes role rather than being abandoned: a declarative fact cannot be
recomputed, but a kernel-checkable consequence can corroborate it. Frozen now, because a status
boundary chosen after seeing which facts fall on which side is the same defect as a tolerance
chosen after seeing the answer (22C W1-F3, W3-F2).

**S22D-016 — the escalation policy, executed rather than described.** §3.2 names this as the
place the sprint could cheat without noticing, so the record carries the decision function's
**entire truth table** over its three signals — abstained, grounded-span count, answer form —
and a test replays every row. There is no self-reported confidence anywhere in it: 22C W3-D1's
rule applies with force to a language model, since a model's opinion of itself is precisely
the value it will always produce. Grounding support is counted, never asked for.

### The W1 holdout, frozen unread, with its arms already proved different

§1.5's decision — a non-kernel verification path for declarative facts — lands as W1 against a
**fresh** holdout, because 22C's was read once to 0 of 4 and changing the acceptance path now
so the number improves is post-hoc fitting. `sprint-22d-holdout.json` carries 12 cases, each
withholding exactly one declared fact.

Two things it does that a prose holdout could not:

*The arms are known to be mechanically different before W1 is paid for.* The probe runs the arm
mechanism on a case **deliberately outside the holdout set** — 22C's own move — so arm A is
shown to refuse by name (`fact_not_in_acquired_layer`) while arm B answers and the released
verifier passes it, and the holdout still reads `measured_values: 0`.

*It is disjoint from the hundred, asserted rather than intended.* No case id and no withheld
fact appears in the frozen hundred. A holdout sharing facts with the microbenchmark would leak
a W1 reading into a W3 measurement.

### The §3.1 slice — four arms, and a record that can print more than one outcome

Ten fixture tasks, a fixture-scale runtime with no weights and no clearance, and two refusals
executed rather than described.

| Arm | verified | grounded | abstained | ungrounded | escalated | external calls |
|---|---:|---:|---:|---:|---:|---:|
| `no_memory` | 8/10 | 0 | 0 | **5** | 10 | 0 |
| `retrieval_only` | 0/10 | 5 | 0 | 0 | 5 | 0 |
| `external_teacher` | 10/10 | 0 | 0 | 5 | 10 | 10 |
| `local_model` | 9/10 | 4 | **1** | **0** | 6 | 0 |

External calls outside the teacher arm: **0**, and `run_arm` raises if any other arm records
one. Both refusals fired: registering `openrouter` inside a benchmark run, and benchmarking
uncleared weights.

**The row that matters is `no_memory`.** It answers five factual tasks correctly and cites
nothing, so it scores 8 of 10 on the success reading and **fails the grounding exit five times
over**. That is the whole point of separating the two readings, and it is why the slice needed
the third disposition to be non-zero somewhere: 22C W4's lesson is that a record whose verdict
cannot flip has verified nothing either way. `local_model` reads zero ungrounded assertions,
and `test_the_third_disposition_can_be_non_zero_so_the_record_can_print_two_outcomes` drives a
local answer to one to prove the zero is a measurement.

§3.1 predicted the slice's likeliest finding would be that "grounded" has no executable meaning
for generated prose — 22C's walker starts from a *promoted artifact* whose provenance bundle
the pipeline built, and a sentence a model just produced has no bundle. That prediction was
right about the gap and the walk starts one hop earlier because of it: an answer's own citation
names a registered source and a byte range, the range is cut out of the **loaded** bytes and
hashed, and a citation's offsets are *found* from its quote rather than written down beside it —
hard-coded offsets stop resolving the moment a sentence gains a comma, and the number still
looks like a number.

### Findings

| ID | Finding | Disposition |
|---|---|---|
| **W0-F1** | `build_builtin_registry()` registers unavailable verifiers and `list_all()` returns them, so a frozen verifier set can look complete while half of it errors; 50 of 100 tasks scored as silent undecidables | **fixed in wave** — `require_benchmark_verifiers()` refuses before the first arm; `verify_answer` uses `require()` not `get()` |
| **W0-F2** | `BenchmarkDomain` has no English or language member | **carried** — declared under `GENERIC`, recorded, no enum widened (22C W2-F4) |
| **W0-F3** | `ProviderKind.LOCAL_API` is released with zero configuration classes and no adapter; no serving runtime on this host | **carried to W2** with the three items it must add |
| **W0-F4** | `s22d-h-02` was authored with its tolerance as its expected answer, and two cases depended on facts the frozen hundred asks about | **fixed in wave** — expected answers are computed from the withheld fact, and the two cases rebuilt from holdout-only facts; frozen before anything read the holdout |
| **W0-A1** | §0 of the backlog states 22C is unreleased; it was released before this wave ran | **recorded** in the preflight rather than by editing the plan |

### Carried from 22C, untouched here

22C W3-A1 (the contradiction demonstration, still with nothing acquired to contradict),
22C W2-A1 (`domain_pilot_runs` has no descriptor-domain path), 22C W2-F3 (the Tool Plane's
events go to an in-memory store), 22B W2-F2 (the planner answers a filtered ANN query with a
sequential scan at 10^6), and the `MemoryService.create` crash window. **W2-F3 stops being
cosmetic in this sprint** — the accounting exit needs a durable record of what executed where.
W0 built the accounting record as a driver-side structure; whether W2-F3 is repaired or the
accounting's source is named otherwise is W2's call, and §5 requires one of the two.

### Migration head

`0015`, unchanged. `infra/postgres/alembic/versions` still ends at
`0015_create_provider_output_governance.py` and nothing in W0 needed a schema change. **`0016`
stays a refusal by default.**

### Evidence index

| Record | Item | SHA-256 |
|---|---|---|
| `sprint-22d-preflight.json` | S22D-001, S22D-002 | `0732e0278105a895869bc33d5d90fb626e7704f43f32462544fa174c0ee9d111` |
| `sprint-22d-pre-registration.json` | S22D-010…016 | `a878f109de88bed7d0b7ec42eb3fc40d2de3b355eb57d286216cd98fcfdcb20b` |
| `sprint-22d-holdout.json` | S22D-020 | `5977343023e7d0e774529eb299b303e378416650ac44bdf3197b8c84012fab34` |
| `sprint-22d-w0-slice.json` | S22D-030 | `012dd90b6d1c21d9527f238a3fd1f758f6c8b5095374028a38feb3b084f5af9a` |
| `sprint-22d-contracts.json` | S22D-010…016 | file digest `48b7e864abdbd670686b0e97b318c2905a24729539e528e895b195f0b417692f` |

The first four are each record's own `integrity_content_hash`, recomputed from its body.
`sprint-22d-contracts.json` carries no seal of its own on purpose — it is the readings, and it
is bound by the pre-registration that hashes them from the modules that implement them, so a
contracts file edited by hand fails `pre_registration_22d.py --check` rather than passing a
self-consistency test it wrote for itself.

Three frozen values worth naming separately, because later waves cite these rather than the
files that carry them:

| | |
|---|---|
| microbenchmark `manifest_hash` | `0ebd6c2d30d32aafadd3b2816519bffe995471515ebbe73e53538b02fe3c2f99` |
| `readings_hash` — every §2.2 reading in one value | `9826f1254611a57743af3030a4fdc3b2d72b8054a8434905bf955a5efccc1a5f` |
| W1 `holdout_hash` | `f4ef86385d32561f7e0e716ebdae8719056ec2250a3b1f3ef46a9a4cc217e081` |

Every one of the four sealed records rebuilds byte-for-byte from its sources, and all four
still rebuilt identically **after** `ruff format` reflowed all five drivers — which is the
proof that the seals depend on the frozen data and not on the drivers' source layout.

### Validation

`ruff check` and `ruff format --check` with `--config ruff.cognitive-os.toml` over
`src tests scripts infra`: clean. `mypy src/cognitive_os`: **no issues in 638 source files**.
`bandit -r src/cognitive_os`: **0 issues at every severity**.
`python -m cognitive_os.schemas.export --check`: passed.
`scripts/check_repository_language.sh`: passed.
`scripts/benchmark_22d.py --check`, `holdout_22d.py --check`, `preflight_22d.py --check`,
`pre_registration_22d.py --check`: all reproduce.
`tests/cognitive_os/language/`: **21 passed** with the `verification-physics` extra,
**17 passed / 4 skipped** without it — both directions of W0-F1's refusal exercised.
Whole suite: **4 548 passed / 235 skipped** in 4 m 16 s.

No file under `src/` was touched. W0 is composition over released primitives plus its own
drivers, evidence and tests, which is what §1.2 asked for — and the three gaps that proved not
to be composition are carried as findings rather than absorbed.

### Drivers

| Driver | What it owns |
|---|---|
| `scripts/benchmark_22d.py` | every §2.2 reading, §1.5's ladder, the escalation function, the accounting, the runner, the answer-citation walk, `--slice`, `--check` |
| `scripts/tasks_22d.py` | the frozen hundred, the fixture ten, the fixture sources and arm answers |
| `scripts/holdout_22d.py` | S22D-020, the arm-mechanism probe, the disjointness assertion |
| `scripts/preflight_22d.py` | S22D-001/002, the host, the enumeration, the three rights gates |
| `scripts/pre_registration_22d.py` | S22D-010…016, hashed from the modules that implement them |

**The drivers require the `verification-physics` extra.** That is W0-F1 stated as an operating
fact: run them as
`uv run --extra verification-physics python scripts/…`, or they refuse rather than measure.
