"""The baseline ladder: every comparison a learned component has to survive.

Phase 21.6. The plan's trial order is constant/majority → kNN → decision tree → random
forest → gradient boosting, with the rule that "a complex model is never promoted for
beating a weak straw man". This module is that rule made executable.

The ladder climbs only while climbing is warranted. On the skill-selection corpus it
stops at the deterministic rung, because that rung scores 1.000 and nothing above it can
do better than tie — so no parametric tier was installed, and `scikit-learn`,
`xgboost`, and their transitive dependencies stayed out of the repository. Stopping is
recorded as a result, not as an omission: `ladder_stopped_at` says where and why.

Two splits are produced, and both are needed:

* **group-aware by case** — a split that let labels from one case appear on both sides
  would measure memorisation, so cases are partitioned whole;
* **held-out domain** — the honest generalisation test, and the one that exposed the
  kNN answering confidently about a capability vocabulary it had never seen.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.domain.learned import (
    BaselineKind,
    BaselineLadder,
    BaselineRung,
    CounterfactualLabelValue,
    OutOfDistributionAssessment,
    SituationVector,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME, build_all_cases
from cognitive_os.infrastructure.learned.knn import (
    DEFAULT_CONFIDENCE_FLOOR,
    ExperienceKnn,
    StoredExperience,
)

from .features import encode
from .selfplay import SURFACE, SkillCandidate, build_corpus, skill_candidates

HARMFUL = CounterfactualLabelValue.HARMFUL.value
NEUTRAL = CounterfactualLabelValue.NEUTRAL.value

#: Deterministic corpus, so it is built once per process. Keyed by `case_limit`.
_EXAMPLE_CACHE: dict[int | None, tuple[Example, ...]] = {}

#: Why the ladder stops below the parametric tiers on this corpus.
STOPPED_REASON = (
    "the deterministic requirements-available rule scores 1.000 on every split, so no "
    "parametric tier can beat it and none was installed"
)


@dataclass(frozen=True, slots=True)
class Example:
    """One labelled situation, carrying the grouping keys the splits need."""

    situation: SituationVector
    label: str
    case_id: str
    domain: str
    candidate: SkillCandidate
    case: DomainBenchmarkCase


def _quantise(value: float) -> Decimal:
    return Decimal(f"{value:.4f}")


async def build_examples(*, case_limit: int | None = None) -> tuple[Example, ...]:
    """Encode the labelled corpus into evaluable examples.

    Memoised because building it costs 1020 governed runs — roughly 27 seconds — and the
    result is bit-identical every time, which is the property phase 21.1 verified. Without
    this, each caller re-runs the whole corpus; the ladder alone has seven of them.
    """
    if case_limit in _EXAMPLE_CACHE:
        return _EXAMPLE_CACHE[case_limit]
    cases = {case.case_id: case for case in build_all_cases()}
    candidates = {item.canonical_name: item for item in await skill_candidates()}
    corpus = await build_corpus(case_limit=case_limit)
    examples = []
    for label in corpus.labels:
        case = cases[label.case_id]
        candidate = candidates[label.variation_identity]
        examples.append(
            Example(
                situation=encode(case, candidate),
                label=label.label.value,
                case_id=label.case_id,
                domain=case.domain.value,
                candidate=candidate,
                case=case,
            )
        )
    _EXAMPLE_CACHE[case_limit] = tuple(examples)
    return _EXAMPLE_CACHE[case_limit]


# --- the rungs -------------------------------------------------------------------


def majority_label(train: Sequence[Example]) -> str:
    counts = {HARMFUL: 0, NEUTRAL: 0}
    for item in train:
        counts[item.label] = counts.get(item.label, 0) + 1
    return max(sorted(counts), key=lambda key: counts[key])


def score_majority(train: Sequence[Example], test: Sequence[Example]) -> BaselineRung:
    """Rung 1, trivial: always answer the training majority."""
    winner = majority_label(train)
    correct = sum(1 for item in test if item.label == winner)
    return BaselineRung(
        name=f"majority[{winner}]",
        kind=BaselineKind.TRIVIAL,
        score=_quantise(correct / len(test)),
        evaluated_count=len(test),
        abstained=0,
        confident_errors=len(test) - correct,
    )


def deterministic_predicts_harm(example: Example) -> bool:
    """The rule the Skill Engine already implements as `_requirements_available`.

    A skill whose *required* verifier capability is not among the capabilities the case
    declares cannot have that verifier run, so it cannot be accepted. Nothing here is
    learned and nothing is observed after the fact — `required_verifiers` is declared on
    the case before it runs.
    """
    declared = set(example.case.required_verifiers)
    return not set(example.candidate.declared_capabilities) <= declared


def score_deterministic(test: Sequence[Example]) -> BaselineRung:
    """Rung 2, deterministic: needs no training, so it takes no train set."""
    correct = sum(
        1
        for item in test
        if (HARMFUL if deterministic_predicts_harm(item) else NEUTRAL) == item.label
    )
    return BaselineRung(
        name="requirements_available",
        kind=BaselineKind.DETERMINISTIC,
        score=_quantise(correct / len(test)),
        evaluated_count=len(test),
        abstained=0,
        confident_errors=len(test) - correct,
    )


async def score_knn(
    train: Sequence[Example],
    test: Sequence[Example],
    *,
    k: int = 3,
) -> tuple[BaselineRung, int]:
    """Rung 3, learned. Returns the rung and its confident-error count.

    An abstention is not counted as correct. A component that abstains on everything
    would otherwise score perfectly by declining to answer, which is the mirror image of
    the straw-man problem.
    """
    component = ExperienceKnn(
        tuple(StoredExperience(situation=item.situation, label=item.label) for item in train),
        k=k,
    )
    correct = abstained = confident_errors = 0
    for item in test:
        prediction = await component.predict(item.situation)
        if prediction.abstained:
            abstained += 1
        elif prediction.prediction == item.label:
            correct += 1
        else:
            confident_errors += 1
    rung = BaselineRung(
        name=f"{component.component_id}[k={k}]",
        kind=BaselineKind.LEARNED,
        score=_quantise(correct / len(test)),
        evaluated_count=len(test),
        abstained=abstained,
        confident_errors=confident_errors,
    )
    return rung, confident_errors


# --- the splits ------------------------------------------------------------------


def group_aware_split(
    examples: Sequence[Example], *, every: int = 3
) -> tuple[tuple[Example, ...], tuple[Example, ...]]:
    """Partition whole cases, never individual labels.

    Splitting labels would put the same case on both sides, and since the label is a
    function of (domain, candidate) the model would simply recall the answer.
    """
    case_ids = sorted({item.case_id for item in examples})
    held = set(case_ids[::every])
    train = tuple(item for item in examples if item.case_id not in held)
    test = tuple(item for item in examples if item.case_id in held)
    return train, test


def held_out_domain_split(
    examples: Sequence[Example], domain: str
) -> tuple[tuple[Example, ...], tuple[Example, ...]]:
    train = tuple(item for item in examples if item.domain != domain)
    test = tuple(item for item in examples if item.domain == domain)
    return train, test


async def evaluate_ladder(
    examples: Sequence[Example],
    *,
    split_name: str,
    train: Sequence[Example],
    test: Sequence[Example],
    k: int = 3,
) -> BaselineLadder:
    """Run every rung on one split and record all of them."""
    if not train or not test:
        raise ValueError("a ladder needs a non-empty train and test partition")
    knn_rung, _ = await score_knn(train, test, k=k)
    return BaselineLadder(
        ladder_id=uuid5(NAMESPACE_URL, f"ladder:{SURFACE}:{split_name}:{len(test)}"),
        surface=SURFACE,
        split=split_name,
        rungs=(score_majority(train, test), score_deterministic(test), knn_rung),
        created_at=FIXTURE_TIME,
    )


async def assess_out_of_distribution(
    examples: Sequence[Example],
    *,
    component_id: str = ExperienceKnn.component_id,
    k: int = 3,
    confidence_threshold: Decimal = DEFAULT_CONFIDENCE_FLOOR,
) -> OutOfDistributionAssessment:
    """Hold out each domain in turn and count confident mistakes.

    This is the measurement that decides whether the component knows what it does not
    know. Every domain is held out rather than one, because a component might happen to
    generalise into a single domain by luck.
    """
    domains = sorted({item.domain for item in examples})
    evaluated = abstained = confident_errors = 0
    for domain in domains:
        train, test = held_out_domain_split(examples, domain)
        if not train or not test:
            continue
        rung, errors = await score_knn(train, test, k=k)
        evaluated += rung.evaluated_count
        abstained += rung.abstained
        confident_errors += errors
    return OutOfDistributionAssessment(
        assessment_id=uuid5(NAMESPACE_URL, f"ood:{component_id}:{evaluated}"),
        component_id=component_id,
        held_out_groups=tuple(domains),
        evaluated_count=evaluated,
        abstained=abstained,
        confident_errors=confident_errors,
        confidence_threshold=confidence_threshold,
        created_at=FIXTURE_TIME,
    )


@dataclass(frozen=True, slots=True)
class LadderReport:
    """Everything 21.6 measured, in one returnable value."""

    group_aware: BaselineLadder
    per_domain: tuple[BaselineLadder, ...]
    out_of_distribution: OutOfDistributionAssessment
    ladder_stopped_at: str
    stopped_reason: str

    @property
    def learned_beats_deterministic(self) -> bool:
        """The 21.6 exit question, asked of the group-aware split."""
        learned = max(
            rung.score for rung in self.group_aware.rungs if rung.kind is BaselineKind.LEARNED
        )
        return learned > self.group_aware.strongest_non_learned


async def run_ladder(*, case_limit: int | None = None, k: int = 3) -> LadderReport:
    """Execute phase 21.6's full measurement."""
    examples = await build_examples(case_limit=case_limit)
    train, test = group_aware_split(examples)
    group_aware = await evaluate_ladder(
        examples, split_name="group-aware-by-case", train=train, test=test, k=k
    )
    per_domain = []
    for domain in sorted({item.domain for item in examples}):
        domain_train, domain_test = held_out_domain_split(examples, domain)
        if not domain_train or not domain_test:
            continue
        per_domain.append(
            await evaluate_ladder(
                examples,
                split_name=f"held-out-domain:{domain}",
                train=domain_train,
                test=domain_test,
                k=k,
            )
        )
    return LadderReport(
        group_aware=group_aware,
        per_domain=tuple(per_domain),
        out_of_distribution=await assess_out_of_distribution(examples, k=k),
        ladder_stopped_at=group_aware.strongest_deterministic_name,
        stopped_reason=STOPPED_REASON,
    )
