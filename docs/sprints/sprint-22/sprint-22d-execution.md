# Sprint 22D Execution Log

Bounded local English, LLM-dependence reduction, and the instrument every later wave is bound
to. Executed against the
[Sprint 22D Technical Backlog](sprint-22d-technical-backlog.md), whose §0 incorporates the
[Sprint 21D4](../sprint-21/sprint-21d4-technical-backlog.md) execution contract unchanged and
adds six standing rules 22C paid for.

Waves are recorded newest first.

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
