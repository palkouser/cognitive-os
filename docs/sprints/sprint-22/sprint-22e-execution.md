# Sprint 22E Execution Log

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
