"""Sprint 21 follow-up: the domain path selects its skill instead of indexing a table.

Three defects are pinned here, each found by running the code rather than reading it.

1. `run_case_as_skill` took `entry.skills[0]`, so the Skill Engine's selector never ran on
   the cross-domain path and the static table's *ordering* silently decided.
2. Preconditions do not narrow selection to a problem type's permitted skills — several
   mathematics skills legitimately satisfy `mathematics.numeric` — so selection reached
   outside the permitted set the first time it was wired in.
3. `SkillSelectionDecision.reason` reported the winner's own attributes rather than the key
   that discriminated, claiming `exact_signature` when accumulated statistics broke a tie.
"""

from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import pytest

import cognitive_os.domains.registry as problem_registry
from cognitive_os.domain.domains import VerificationDisposition
from cognitive_os.domain.skills import SkillExclusionReason, SkillSelectionReason
from cognitive_os.domains.fixtures import build_all_cases
from cognitive_os.domains.registry import resolve
from cognitive_os.domains.skill_runner import (
    run_case_as_skill,
    run_corpus_as_skills,
    select_domain_skill,
    skill_fixture_bundle,
)

CASES = build_all_cases()
PHYSICS = [case for case in CASES if case.domain.value == "physics"]
MATHEMATICS = [case for case in CASES if case.domain.value == "mathematics"]


def _declared_canonical_names(paths: Iterable[Path], manifest: str) -> set[str]:
    """The `canonical_name` each package declares, not the directory it sits in."""
    names: set[str] = set()
    for path in paths:
        descriptor = path / manifest
        if not descriptor.is_file():
            continue
        for line in descriptor.read_text(encoding="utf-8").splitlines():
            if line.startswith("canonical_name:"):
                names.add(line.split(":", 1)[1].strip())
                break
        else:  # pragma: no cover - a package without a canonical name is a bug
            raise AssertionError(f"{descriptor} declares no canonical_name")
    return names


class TestSelectionActuallyRuns:
    @pytest.mark.asyncio
    async def test_a_run_carries_the_selection_decision_it_made(self) -> None:
        run = await run_case_as_skill(CASES[0])
        assert run.selection is not None, "the domain path must record its selection"
        assert run.selection.selected_skill_id is not None
        assert run.selection.decision_hash, "the decision must be content-sealed"
        assert run.accepted

    @pytest.mark.asyncio
    async def test_the_selected_skill_stays_inside_the_permitted_set(self) -> None:
        """The problem-type registry is the authority, not the whole skill registry."""
        bundle = await skill_fixture_bundle()
        for case in (MATHEMATICS[0], PHYSICS[0]):
            run = await run_case_as_skill(case, bundle=bundle)
            assert run.selection is not None
            chosen = next(
                item
                for item, revision in bundle[1].query()
                if revision.skill_id == run.selection.selected_skill_id
            )
            assert chosen.identity.canonical_name in resolve(case.problem_type).skills

    @pytest.mark.asyncio
    async def test_skills_outside_the_permitted_set_are_excluded_not_hidden(self) -> None:
        """Restricting by exclusion keeps the rejected names in the decision record.

        Pre-filtering the candidate query would have produced the same choice and a
        decision that could not say what it was not allowed to consider.
        """
        repository, registry, _ = await skill_fixture_bundle()
        decision = await select_domain_skill(MATHEMATICS[0], repository, registry)
        reasons = Counter(item.reason for item in decision.exclusions)
        assert reasons[SkillExclusionReason.NOT_PERMITTED] > 0
        permitted = resolve(MATHEMATICS[0].problem_type).skills
        assert len(decision.candidates) <= len(permitted)

    @pytest.mark.asyncio
    async def test_an_unsatisfiable_candidate_is_excluded_by_its_own_precondition(self) -> None:
        """`cross-domain-result-review` needs `generic.exact_value`, never emitted here."""
        repository, registry, _ = await skill_fixture_bundle()
        decision = await select_domain_skill(MATHEMATICS[0], repository, registry)
        reasons = {item.reason for item in decision.exclusions}
        assert SkillExclusionReason.PRECONDITION in reasons
        assert len(decision.candidates) == 1, "only one mathematics skill is satisfiable"

    @pytest.mark.asyncio
    async def test_every_case_selects_and_lands_on_its_declared_outcome(self) -> None:
        """The whole corpus still selects and runs, so wiring selection in changed no outcome.

        Sprint 21C.1: the coding fixtures declared in `FALLIBLE_CODING_CASES`
        are expected to reject, and every other case to be accepted. Selection
        is recorded either way — a rejected baseline is still a governed,
        recorded selection, which is exactly what makes it usable as 21D corpus
        material.
        """
        runs = await run_corpus_as_skills(CASES)
        assert len(runs) == len(CASES)
        assert all(run.selection is not None for run in runs)
        for run, case in zip(runs, CASES, strict=True):
            expected_pass = case.expected_disposition is VerificationDisposition.PASS
            assert run.accepted is expected_pass, case.case_id


class TestAccumulatedStatisticsBreakTies:
    @pytest.mark.asyncio
    async def test_physics_offers_a_genuine_tie(self) -> None:
        """Both physics candidates declare `physics.dimension`, so both are satisfiable."""
        repository, registry, _ = await skill_fixture_bundle()
        decision = await select_domain_skill(PHYSICS[0], repository, registry)
        assert len(decision.candidates) == 2
        keys = {(item.specificity_score, item.scope_score) for item in decision.candidates}
        assert len(keys) == 1, "the tie is what makes statistics the deciding key"

    @pytest.mark.asyncio
    async def test_a_cold_registry_breaks_the_tie_canonically(self) -> None:
        """Below the configured sample threshold there is nothing to rank on."""
        run = await run_case_as_skill(PHYSICS[0])
        assert run.selection is not None
        assert run.selection.reason is SkillSelectionReason.CANONICAL_TIE_BREAK
        assert not run.selected_by_statistics
        assert all(item.statistics_score == 0 for item in run.selection.candidates)

    @pytest.mark.asyncio
    async def test_accumulated_outcomes_take_over_once_the_sample_is_reached(self) -> None:
        """The fix for an inert `statistics_score`: continuity, not new arithmetic.

        `SkillExecutionService` already rebuilt statistics after every run and the selector
        already turned them into a score. A fresh registry per case meant every selection
        saw an empty execution log, so the score was always 0 and ties fell through to
        `str(skill_id)`. Sharing the registry is the entire change.
        """
        runs = await run_corpus_as_skills(PHYSICS)
        by_statistics = [run for run in runs if run.selected_by_statistics]
        assert by_statistics, "accumulated outcomes must eventually decide"
        first = next(index for index, run in enumerate(runs) if run.selected_by_statistics)
        assert first > 0, "statistics cannot decide before any outcome is recorded"
        winner = by_statistics[-1].selection
        assert winner is not None
        scores = [item.statistics_score for item in winner.candidates]
        chosen = next(
            item for item in winner.candidates if item.skill_id == winner.selected_skill_id
        )
        assert chosen.statistics_score == max(scores)
        assert len(set(scores)) > 1, "the statistics must actually differ to decide"

    @pytest.mark.asyncio
    async def test_the_reported_reason_names_the_discriminating_key(self) -> None:
        """Defect 3: the record used to claim `exact_signature` for a statistics win.

        Both physics candidates score specificity 2 and scope 2, so specificity cannot have
        decided anything — yet the old derivation read the winner's own specificity and
        said so.
        """
        runs = await run_corpus_as_skills(PHYSICS)
        deciding = next(run for run in runs if run.selected_by_statistics)
        assert deciding.selection is not None
        candidates = deciding.selection.candidates
        assert candidates[0].specificity_score == candidates[1].specificity_score
        assert candidates[0].scope_score == candidates[1].scope_score
        assert deciding.selection.reason is SkillSelectionReason.VERIFIED_STATISTICS

    @pytest.mark.asyncio
    async def test_a_sole_candidate_reports_its_own_merit(self) -> None:
        """With one candidate the ordering never ran, so there is no discriminator."""
        run = await run_case_as_skill(MATHEMATICS[0])
        assert run.selection is not None
        assert len(run.selection.candidates) == 1
        assert run.selection.reason is SkillSelectionReason.EXACT_SIGNATURE


class TestPermittedSetsAreCoherent:
    def test_every_problem_type_offers_a_real_choice(self) -> None:
        """A permitted set of exactly one is decorative selection; none is no selection.

        The released four each declare two skills and two strategies, and that is the
        guarantee this test was written for. Sprint 22A adds a third case: a
        descriptor-registered domain may declare **no** permitted set at all, because it
        solves through the deterministic tool path and never reaches skill selection.
        Inventing two names to satisfy a count would be exactly the false-capability
        failure ADR 0085 and §3.4 both warn about.

        What must never exist, for any domain, is a set of exactly one — it looks like a
        choice in every record it appears in, and is not one.
        """
        entries = list(problem_registry._ENTRIES.values())
        assert entries
        assert all(len(entry.skills) != 1 for entry in entries)
        assert all(len(entry.strategies) != 1 for entry in entries)

        released = [entry for entry in entries if entry.domain is not None]
        assert len(released) == 28
        assert all(len(entry.skills) >= 2 for entry in released)
        assert all(len(entry.strategies) >= 2 for entry in released)

    def test_each_permitted_skill_is_a_registered_seed_skill(self) -> None:
        """A permitted set is authority, so every name in it has to resolve.

        The directory name and the canonical name differ (`coding/python-repair`
        declares `verification-driven-python-repair`), so the declaration is what
        counts, not the folder.
        """
        from cognitive_os.skills.fixtures import seed_package_paths

        seeds = _declared_canonical_names(seed_package_paths(), "metadata.yaml")
        for entry in problem_registry._ENTRIES.values():
            unknown = set(entry.skills) - seeds
            assert not unknown, f"{entry.problem_type} names an unknown skill: {sorted(unknown)}"

    def test_each_permitted_strategy_is_a_registered_strategy(self) -> None:
        """The same authority argument as for skills, and the reason it exists.

        Sprint 21C.1 first registered the coding domain with two invented
        strategy names. Nothing caught it, because only skills were checked,
        and the names still reached every coding case plan's
        `strategy_revisions` as provenance for a strategy that did not exist.
        """
        from pathlib import Path

        root = Path(__file__).resolve().parents[3] / "strategies"
        assert root.is_dir(), f"strategy package root not found at {root}"
        known = _declared_canonical_names(sorted(root.iterdir()), "strategy.yaml")
        for entry in problem_registry._ENTRIES.values():
            unknown = set(entry.strategies) - known
            assert not unknown, (
                f"{entry.problem_type} names an unregistered strategy: {sorted(unknown)}"
            )
