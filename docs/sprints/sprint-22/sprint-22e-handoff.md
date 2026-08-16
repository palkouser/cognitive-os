# Sprint 22E Handoff — what 23A inherits, priced

**Outcome: typed negative.** Three of five exits met, Gate M seven of ten, released under
`sprint-22e-evidence-baseline` at `395fe7d`. The loop works; the gate it was asked to close was
not closable by any change this sprint was allowed to make, and the plan said so before a single
candidate existed.

---

## 1. What is now true that was not

**The governed self-improvement loop has run end to end against the real repository.** Not a
fixture refusing a fixture: a weakness mined from the programme's own sealed findings ledger, a
live provider draft admitted by the released host verification, a repair applied by
`deterministic_replace` in an isolated worktree, fifteen released gates evaluated, a named human
approving, a PR to protected `main`, a gate-owner merge, and post-merge exact-head CI. The bytes
on `main` were hashed out of the merged commit and compared with what the matrix evaluated.

**Five traversals were carried to a refusal and none of them moved the active state.** Seven
zero-mutation comparisons in total, each recomputed per surface member, never asserted.

**Both kinds of experience are retained and retrievable**, and — beyond what the exit asks —
they are told apart: the successful traversal ranks first for an acceptance query and fourth for
a refusal query, while the two failed ones invert exactly.

---

## 2. What 23A inherits, with prices attached

### 2.1 The two Gate M conditions 22E could not move

| Condition | Reads | Value | What would move it |
|---|---|---|---|
| **6** — bounded local English without a large external LLM | `sprint-22d-exit-criteria.json#criteria[1].met` | `false` (66 % against a 70 % floor) | ledger **L1** landed through the governed path, then the frozen 22D instrument re-run per workload |
| **7** — large-LLM dependence falls by the declared threshold | `sprint-22d-exit-criteria.json#criteria[2].met` | `false` (calls −4 %, accounted cost +5.9 %) | ledger **L2** landed the same way |

Both are **one approved change each**, and 22E was allowed exactly one in total. The arithmetic
was published in the gate owner's decision record before any candidate existed: the sets are
disjoint, so no single selection closes both, and the sprint chose which certain negative was
worth the most rather than discovering the constraint in W4.

**L1's price is now known and smaller than the ledger said.** W2-F1 established that its supposed
mypy cost was a false rejection — the gate was not reproducing the lane it claimed to. The repair
edits one character class in one released contract. The measured ceiling is **66 → at most 76**
against a floor of 70, computed in W0 from the sealed per-task records, and it is a ceiling, not
a forecast: at least 4 of the 10 recoverable tasks must actually verify.

**L2 is noisier than L1 and the ledger says so.** The non-inferiority margin is 3 points and 22D
W3-F3 measured the baseline itself moving 12 of 96.

### 2.2 Condition 10 cannot be met by a sprint that fails anything else

`sprint-22-baseline` is created only on a pass, and condition 10 requires it to peel. So the
condition is **structurally unreachable** for any sprint that fails one of the other nine — it
does not measure an independent property so much as restate the conjunction. 23A should either
read it that way explicitly or rebind it to the release record's post-merge CI, which is the half
of its sentence that is actually independent. This is a reading question for the gate owner, not
a defect.

### 2.3 The four findings 22E leaves in the ledger

| Entry | Finding | What it costs today |
|---|---|---|
| **L1** | 22D W2-F2 | condition 6; low risk, repair known, ceiling +10 |
| **L2** | 22D W3-F1 | condition 7; low risk, noisy margin |
| **L3** | 22D abstention observation | no condition; moderate |
| **L4** | 22B W3-F1 | no condition; **high** risk, zero benefit on the plan's own reading |
| **L5** | 22D W2-F1 | ineligible — behind `0016`, which stays a refusal |
| **L6** | 22E W1-F5 | provider timeout misreported as cancellation and silently not retried |
| **L7** | 22E W1-F7 | **closed by this sprint** |

**New, and not yet in the ledger — 23A's first act should be to price them:**

- **22E W3-F2 — the released promotion chain cannot name a real repository file.**
  `build_change_specification` synthesises `proposal-scope/<type>.py` as the whole allowed scope
  of every `repository_file` proposal; `prepare_isolation` copies it into the manifest;
  `capture_candidate` refuses anything else. So `ChangeCandidate`, `PromotionAssessment`,
  `PromotionReview` and `PromotionBundle` are **unbuildable for any real change**, and
  `approve_promotion` cannot be called. `changes/demo.py` passed the placeholder back in, so both
  sides agreed and the seam never opened. **This is the single highest-value repair on the board
  for a sprint that wants the governed promotion record, not just the governed merge.**
- **22E W3-F1 — a live reproduction cannot survive its own repair.** The ledger's reproductions
  re-execute on every `--check`; the first successful repair made one of them stop reproducing
  and failed two gates inside the candidate's own matrix. Resolved here with a two-outcome
  checker that reads both sides. **Any successor ledger must be built this way from the start**,
  or its first success breaks its own evidence.

---

## 3. What the loop cost, measured

| | |
|---|---|
| Full evaluation matrix, once | **~285 s**, 9 gates runnable of 15 |
| Live provider draft | one governed call per traversal, receipt sealed, retention `none` |
| Traversals carried to a refusal | 5 |
| Traversals carried to `main` | 1 |
| Findings the loop produced about itself | **12** across W0–W4 |

**Nine of the twelve findings were caller-side or seam-side, not a released component
misbehaving inside its own boundary.** That is the sprint's most portable result and it held from
W1 to W4: the defects live where two released things assume different contracts about the same
call and nothing compares the two. Fixtures cannot find them, because a fixture encodes the same
assumption as the code it exercises.

---

## 4. Standing rules this sprint added

- **A live reproduction needs a two-outcome check** — still reproduces, or the named repair
  landed and its shape holds field by field. Both sides read; drift satisfies neither. (W3-F1)
- **A caller that blanks a hashed contract's seal has no typed way to restore it** — the only
  sealing entry point is a validator, and `model_copy` skips validators. Reseal by revalidating,
  inside the function that blanks it. (W3, from W1-F7)
- **Query a structural search surface in its own vocabulary.** `status=completed`, not
  `completed`. A malformed query returns a plausible ranking rather than an error. (W4-F1)
- **A stricter probe must never redefine the sentence it tests beside.** Report it separately.
- **A lane is proved by pruning, not by omitting a flag** — and `uv run --exact` also removes the
  pre-commit hooks' own tooling. (W0-F2, four times over)
- **Run a governed traversal against a quiescent tree.** A file created while a run is in flight
  moves `repository_status_hash`, and the zero-mutation check will correctly blame the author.

---

## 5. The one-line recommendation

**Spend 23A's approved changes on L1 and W3-F2, in that order.** L1 is the only entry on the
board that can move a Gate M condition and its repair is known, small and now correctly priced.
W3-F2 is what stands between this programme and a governed promotion *record* rather than a
governed merge — and every successor that wants to walk §2.2(b) as written pays for it until it
is repaired.
