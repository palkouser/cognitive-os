"""The two-sided counterfactual: replace the selected skill, do not merely constrain it.

Phase 21B follow-up. The `SELECTION_FORCED` harness in `selfplay.py` varies a run by
*adding* a required capability, which only ever adds a way to fail. Under that variation a
rejected baseline can never become accepted, so `useful` is impossible by construction and
the three-valued label is binary in practice. `CounterfactualVariation` now refuses the
combination outright, so this module exists to provide the variation that is genuinely
two-sided.

Here the baseline is whatever the Skill Engine actually selects, and the variation is
another permitted skill selected in its place — through the ordinary governed selection
path, by narrowing the permitted set to that one name, never by bypassing selection. So:

* baseline accepted, alternative rejected -> `harmful`
* baseline rejected, alternative accepted -> `useful` (now reachable)
* unchanged -> `neutral`

An alternative the selector refuses to choose at all is recorded as a rejected outcome
rather than skipped. Forcing a skill the governed path will not select means the task
cannot proceed, which is a real consequence and exactly the kind of thing a corpus should
carry rather than silently drop.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.domain.learned import (
    CounterfactualLabel,
    CounterfactualLabelValue,
    CounterfactualVariation,
    LabelBalance,
    ProvenanceClass,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME, build_all_cases
from cognitive_os.domains.registry import resolve
from cognitive_os.domains.skill_runner import (
    SkillFixtureBundle,
    run_case_as_skill,
    select_domain_skill,
    skill_fixture_bundle,
)

from .selfplay import ACCEPTED, REJECTED, SURFACE, balance_of


@dataclass(frozen=True, slots=True)
class ReplacementCorpus:
    labels: tuple[CounterfactualLabel, ...]
    balance: LabelBalance
    case_count: int
    #: Cases whose selected skill had no permitted alternative to compare against.
    cases_without_alternative: tuple[str, ...]

    @property
    def useful_is_reachable(self) -> bool:
        """Structural, not empirical: the variation permits an improvement at all."""
        return not CounterfactualVariation.SELECTION_REPLACED.monotone_restriction


def _outcome(accepted: bool) -> str:
    return ACCEPTED if accepted else REJECTED


def _determinism_proof(case_id: str, baseline_name: str, outcome: str) -> str:
    """Digest binding a label to the baseline selection it was compared against."""
    return sha256(f"{SURFACE}:replaced:{case_id}:{baseline_name}:{outcome}".encode()).hexdigest()


async def _canonical_name(bundle: SkillFixtureBundle, skill_id: object, revision: int) -> str:
    _, skill_registry, _ = bundle
    for item, value in skill_registry.query():
        if value.skill_id == skill_id and value.revision == revision:
            return item.identity.canonical_name
    raise LookupError(f"selected skill {skill_id} is not in the registry")


async def label_case_by_replacement(
    case: DomainBenchmarkCase, bundle: SkillFixtureBundle
) -> tuple[CounterfactualLabel, ...]:
    """Compare the selector's choice against every other permitted skill."""
    baseline = await run_case_as_skill(case, bundle=bundle)
    if baseline.selection is None or baseline.selection.selected_revision is None:
        raise RuntimeError(f"case {case.case_id!r} produced no selection to vary")
    baseline_name = await _canonical_name(
        bundle, baseline.selection.selected_skill_id, baseline.selection.selected_revision
    )
    baseline_outcome = _outcome(baseline.accepted)
    proof = _determinism_proof(case.case_id, baseline_name, baseline_outcome)

    labels: list[CounterfactualLabel] = []
    for alternative in resolve(case.problem_type).skills:
        if alternative == baseline_name:
            continue
        repository, skill_registry, _ = bundle
        decision = await select_domain_skill(
            case, repository, skill_registry, restrict_to=frozenset({alternative})
        )
        if decision.selected_skill_id is None:
            # The governed path will not select it, so the task cannot proceed.
            varied_outcome = REJECTED
        else:
            varied = await run_case_as_skill(
                case, bundle=bundle, restrict_to=frozenset({alternative})
            )
            varied_outcome = _outcome(varied.accepted)

        if varied_outcome == baseline_outcome:
            value = CounterfactualLabelValue.NEUTRAL
        elif varied_outcome == ACCEPTED:
            value = CounterfactualLabelValue.USEFUL
        else:
            value = CounterfactualLabelValue.HARMFUL
        labels.append(
            CounterfactualLabel(
                label_id=uuid5(NAMESPACE_URL, f"{SURFACE}:replaced:{case.case_id}:{alternative}"),
                surface=SURFACE,
                case_id=case.case_id,
                variation_kind=CounterfactualVariation.SELECTION_REPLACED,
                variation_identity=alternative,
                baseline_outcome=baseline_outcome,
                varied_outcome=varied_outcome,
                label=value,
                determinism_proof=proof,
                provenance_class=ProvenanceClass.SELF_PLAY,
                created_at=FIXTURE_TIME,
            )
        )
    return tuple(labels)


async def build_replacement_corpus(
    *, case_limit: int | None = None, cases: Sequence[DomainBenchmarkCase] | None = None
) -> ReplacementCorpus:
    """Label every case by replacement, over one shared registry.

    The registry is shared so skill statistics accumulate exactly as they do in a real
    sweep; a fresh registry per case would make the baseline selection depend on nothing
    but the canonical tie-break.
    """
    subjects = tuple(cases if cases is not None else build_all_cases())
    if case_limit is not None:
        subjects = subjects[:case_limit]
    bundle = await skill_fixture_bundle()
    labels: list[CounterfactualLabel] = []
    without: list[str] = []
    for case in subjects:
        produced = await label_case_by_replacement(case, bundle)
        if not produced:
            without.append(case.case_id)
        labels.extend(produced)
    return ReplacementCorpus(
        labels=tuple(labels),
        balance=balance_of(labels),
        case_count=len(subjects),
        cases_without_alternative=tuple(without),
    )
