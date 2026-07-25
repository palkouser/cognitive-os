"""Self-play counterfactual labelling over the existing verified fixtures.

The training corpus is produced by re-running deterministic, provider-free governed
cases with one decision varied at a time. Nothing here contacts a provider, needs a
credential, touches the network, or requires an optional extra.

Why counterfactual rather than observational: an observational record says "skill S
ran and the case was accepted", which cannot distinguish S causing the acceptance
from S being irrelevant to it. Forcing each candidate in turn and comparing against
the same baseline run answers the causal question directly, and it is affordable
only because a governed domain run is deterministic and costs about 25 ms.

The variation used for the skill-selection surface is `SELECTION_FORCED`: the
capability a skill revision declares is required of the run, so a skill whose
declared verifier never runs on this case cannot be accepted.

**Correction, phase 21.6.** This module previously claimed that the deterministic
selector "cannot predict" that consequence, because which checks a problem type
emits is a runtime property. Measurement disproved it. The rule "harmful iff a
declared capability is absent from the case's `required_verifiers`" scores **1.000
on all 969 labels**, `required_verifiers` is declared on the case before it runs,
and `SkillSelectionService._requirements_available` already implements exactly that
test. The label is a pure function of `(domain, candidate)` — 57 groups, none
ambiguous.

The corpus is therefore still a valid causal corpus, and still useful as the
substrate's proving ground, but it contains **no signal a learned component could
own**: `learning/baselines.py` measures the tie, and the claim above was an
assertion that should have been a measurement.
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
from cognitive_os.domains.runner import run_case_controlled
from cognitive_os.domains.skill_execution import declared_verifier_capabilities

SURFACE = "skill.selection"

ACCEPTED = "accepted"
REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    """One selectable skill and the verifier capability its package declares."""

    canonical_name: str
    declared_capabilities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LabelledCorpus:
    labels: tuple[CounterfactualLabel, ...]
    balance: LabelBalance
    case_count: int
    candidate_count: int

    @property
    def run_count(self) -> int:
        """Baseline runs plus one varied run per candidate per case."""
        return self.case_count * (self.candidate_count + 1)


def _outcome(accepted: bool) -> str:
    return ACCEPTED if accepted else REJECTED


def _determinism_proof(case_id: str, outcome: str) -> str:
    """Digest binding a label to the baseline it was compared against."""
    return sha256(f"{SURFACE}:{case_id}:{outcome}".encode()).hexdigest()


async def skill_candidates() -> tuple[SkillCandidate, ...]:
    """Every verified seed skill, with the verifier capability it declares."""
    from cognitive_os.skills.fixtures import sprint12_verified_skills

    _, registry, _ = await sprint12_verified_skills()
    return tuple(
        sorted(
            (
                SkillCandidate(
                    canonical_name=item.identity.canonical_name,
                    declared_capabilities=declared_verifier_capabilities(revision),
                )
                for item, revision in registry.query()
            ),
            key=lambda item: item.canonical_name,
        )
    )


async def label_case(
    case: DomainBenchmarkCase, candidates: Sequence[SkillCandidate]
) -> tuple[CounterfactualLabel, ...]:
    """Force each candidate for one case and label the effect on the outcome."""
    baseline = await run_case_controlled(case)
    baseline_outcome = _outcome(baseline.accepted)
    proof = _determinism_proof(case.case_id, baseline_outcome)

    labels: list[CounterfactualLabel] = []
    for candidate in candidates:
        varied = await run_case_controlled(
            case, required_capabilities=candidate.declared_capabilities
        )
        varied_outcome = _outcome(varied.accepted)
        if varied_outcome == baseline_outcome:
            value = CounterfactualLabelValue.NEUTRAL
        elif varied.accepted:
            value = CounterfactualLabelValue.USEFUL
        else:
            value = CounterfactualLabelValue.HARMFUL
        identity = f"{SURFACE}:{case.case_id}:{candidate.canonical_name}"
        labels.append(
            CounterfactualLabel(
                label_id=uuid5(NAMESPACE_URL, identity),
                surface=SURFACE,
                case_id=case.case_id,
                variation_kind=CounterfactualVariation.SELECTION_FORCED,
                variation_identity=candidate.canonical_name,
                baseline_outcome=baseline_outcome,
                varied_outcome=varied_outcome,
                label=value,
                determinism_proof=proof,
                provenance_class=ProvenanceClass.SELF_PLAY,
                created_at=FIXTURE_TIME,
            )
        )
    return tuple(labels)


def balance_of(labels: Sequence[CounterfactualLabel]) -> LabelBalance:
    return LabelBalance(
        useful=sum(1 for item in labels if item.label is CounterfactualLabelValue.USEFUL),
        neutral=sum(1 for item in labels if item.label is CounterfactualLabelValue.NEUTRAL),
        harmful=sum(1 for item in labels if item.label is CounterfactualLabelValue.HARMFUL),
    )


async def build_corpus(*, case_limit: int | None = None) -> LabelledCorpus:
    """Label the whole fixture corpus, or a bounded prefix of it.

    `case_limit` exists for CI, where a bounded sweep proves the harness works
    without spending the full corpus's runtime on every job.
    """
    cases = build_all_cases()
    if case_limit is not None:
        cases = cases[:case_limit]
    candidates = await skill_candidates()
    labels: list[CounterfactualLabel] = []
    for case in cases:
        labels.extend(await label_case(case, candidates))
    return LabelledCorpus(
        labels=tuple(labels),
        balance=balance_of(labels),
        case_count=len(cases),
        candidate_count=len(candidates),
    )
