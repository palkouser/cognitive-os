# ADR 0080: Cross-domain pilot gets a CI gate, verified packaging, and release

## Status

Accepted for Sprint 20.

## Decision

This round closes the two backlog items ADR 0079 left open: packaging (S20-064) and release
(S20-066). It also closes a third, undocumented gap found while closing those two: the cross-domain
pilot had no continuous-integration job.

### CI gate

`.github/workflows/ci.yml` gains a `cross-domain-pilot-core` job, in the exact shape every sibling
subsystem's own job already has (weakness, proposal, controlled-change, ...): contract and lifecycle
tests, the schema-drift gate, the deterministic smoke gate, the offline governance gate, the 24-case
CI benchmark, and the 120-case seed benchmark. The `postgres-integration` job gains the domain health
check and the Sprint 20 smoke test as two more steps, matching how every other subsystem's health
check and smoke test already appear there.

`benchmarks/manifests/sprint20-domain-ci.yaml`, `sprint20-domain-seed.yaml`, and
`scripts/domain_smoke_test.py` have existed since the pilot's first round. No prior round added the
CI job that exercises them remotely; every number in every prior round's closure report was produced
by running these locally. This was a real gap, not a documentation omission: the feature branch had
never been pushed, so nothing had ever run these gates outside a local checkout.

### Packaging

No code change was needed; `uv build`, `verify_distribution.sh`, and `verify_editable_install.sh`
already covered the cross-domain pilot's modules through the existing `graft src/cognitive_os` /
`prune` rules in `MANIFEST.in`. What this round adds is verification: the governed path was run from
the installed wheel, in a clean virtual environment, with no optional extra present, and produced the
same result the offline smoke test produces from a source checkout (51/51 fixture cases accepted,
28/28 governance invariants true).

### Release

Pull request #208 merged `feature/sprint-20-cross-domain-pilot` into `main`; `sprint-20-baseline` was
tagged at the merge commit. See "Remote release validation" in the closure report for the exact
commit and CI run identifiers. The runtime did not perform this step — a human operator authorized
and directed the merge and the tag, consistent with the authority boundary ADR 0076 established:
no process or network module is imported anywhere in the pilot package, verified structurally, and
this round changed nothing about that boundary.

## Two regressions the CI gate caught before merge

Wiring the CI job in surfaced two pre-existing defects, both already present in earlier Sprint 20
commits and both invisible until CI actually ran:

1. `scripts/skill_smoke_test.py` and `src/cognitive_os/benchmarks/strategy_adapter.py` compared the
   seed set to the Sprint 12/13 literal counts (8 skills, 7 strategies) instead of the count Sprint 20
   itself grew it to (19 skills, 13 strategies). A prior round's own magic-number cleanup added
   `seed_package_paths()` and `seed_strategy_paths()` as the single source of truth and used them in
   `skill_adapter.py`'s equivalent check, but missed these two call sites.
2. `src/cognitive_os/domain/domains.py`'s `VerificationDisposition.PASS = "pass"` trips Bandit's B105
   heuristic (`hardcoded_password_string`) the same way `domain/context.py`'s `TOKEN_BUDGET` and
   `domain/corpus.py`'s `SECRET_DETECTED` already do — a false positive on an enum member whose name
   happens to match a common-password wordlist entry, not a credential.

Both are fixed in commit `44d0527`, matching each fix to the pattern already established elsewhere in
the same file or a sibling file, rather than introducing a new pattern. The pull-request CI run
against the unfixed commit (`ccda47c`) failed 4 of 27 jobs; the run against the fix (`44d0527`) passed
27/27. Both runs are linked in the closure report rather than only the passing one, because the
failing run is the evidence that adding the CI job did what it was for.

## Alternatives and consequences

Backdating the CI job into an earlier round's commit (rewriting history on the feature branch before
merge) was considered and rejected: each of the four prior rounds' commits already had its own
closure report entry describing its own stated scope, and folding an unrelated CI job and two bug
fixes into one of them would misattribute what that commit actually did. A new commit on top, in the
round that actually needed it, keeps each commit's diff matching its own message.

Fixing the two magic-number regressions with a broader refactor (a shared "expected seed count"
registry across all subsystems) was considered and rejected as out of scope: two call sites needed
the fix that already existed for their sibling call site; inventing a new abstraction for two lines
is not proportionate to the defect.

## Verification

See "Verified evidence" and "Remote release validation" in `docs/sprints/sprint-20/report.md` for
the full, current set of local and remote numbers: full test suite, PostgreSQL integration, wheel and
sdist build and installed-wheel smoke run, both CI runs, and the tag.

## References

- Pull request [#208](https://github.com/palkouser/cognitive-os/pull/208)
- Commits `ccda47c` (CI gate), `44d0527` (regression fixes)
- CI runs [30141686906](https://github.com/palkouser/cognitive-os/actions/runs/30141686906) (failed,
  pre-fix), [30141871053](https://github.com/palkouser/cognitive-os/actions/runs/30141871053)
  (passed, PR), [30141958464](https://github.com/palkouser/cognitive-os/actions/runs/30141958464)
  (passed, post-merge)
- `docs/adr/0079-cross-domain-operations-cli-and-backup.md`
