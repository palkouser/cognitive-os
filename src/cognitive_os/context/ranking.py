"""Exact deduplication, weighted RRF, modifiers, and bounded selection."""

from collections import Counter
from decimal import Decimal
from hashlib import sha256

from cognitive_os.config.context_config import ContextConfiguration
from cognitive_os.domain.context import (
    ContextCandidate,
    ContextExclusion,
    ContextExclusionReason,
    ContextRequest,
    ContextScoreBreakdown,
    ContextSourceType,
    ContextTrustClass,
    ContextWarning,
    ContextWarningType,
    DeduplicationDecision,
    RankingProfileReference,
    RetrievalMode,
)

from .errors import ContextBudgetError
from .query import reseal_candidate
from .tokenization import ConservativeUtf8TokenEstimator

_AUTHORITY_ORDER = {
    ContextSourceType.TASK_STATE: 0,
    ContextSourceType.EXECUTION_PLAN: 1,
    ContextSourceType.SEMANTIC_CLAIM: 2,
    ContextSourceType.MEMORY: 3,
    ContextSourceType.ARTIFACT: 4,
    ContextSourceType.REPOSITORY_INDEX: 5,
    ContextSourceType.WORKSPACE: 6,
    ContextSourceType.WIKI: 7,
}
_TRUST_SCORE = {
    ContextTrustClass.SYSTEM: Decimal("1.0"),
    ContextTrustClass.VERIFIED: Decimal("0.9"),
    ContextTrustClass.USER_PROVIDED: Decimal("0.8"),
    ContextTrustClass.UNVERIFIED: Decimal("0.4"),
    ContextTrustClass.EXTERNAL: Decimal("0.2"),
    ContextTrustClass.DISPUTED: Decimal("0.1"),
}


def ranking_profile(configuration: ContextConfiguration) -> RankingProfileReference:
    values = configuration.ranking
    return RankingProfileReference(
        profile_id="context-rrf-v1",
        version="1",
        weights={
            "trust": Decimal(str(values.trust_weight)),
            "scope": Decimal(str(values.scope_weight)),
            "verification": Decimal(str(values.verification_weight)),
            "recency": Decimal(str(values.recency_weight)),
            "salience": Decimal(str(values.salience_weight)),
            "graph": Decimal(str(values.graph_weight)),
            "contradiction": Decimal(str(values.contradiction_weight)),
        },
        rrf_k=values.rrf_k,
        score_precision=values.score_precision,
    )


def _scopes(candidate: ContextCandidate) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((item.scope_type.value, item.scope_id) for item in candidate.scopes))


def _merge(kept: ContextCandidate, duplicate: ContextCandidate) -> ContextCandidate:
    routes = {
        (item.retriever_id, item.mode.value, item.rank, item.raw_score, item.weight): item
        for item in (*kept.retrieval_routes, *duplicate.retrieval_routes)
    }
    provenance = {item.canonical_hash(): item for item in (*kept.provenance, *duplicate.provenance)}
    warnings = {item.canonical_hash(): item for item in (*kept.warnings, *duplicate.warnings)}
    return reseal_candidate(
        kept,
        retrieval_routes=tuple(
            routes[key]
            for key in sorted(routes, key=lambda item: (item[0], item[1], item[2], str(item[3])))
        ),
        provenance=tuple(provenance[key] for key in sorted(provenance)),
        warnings=tuple(warnings[key] for key in sorted(warnings)),
        pinned=kept.pinned or duplicate.pinned,
        required=kept.required or duplicate.required,
        evidence=kept.evidence or duplicate.evidence,
        recent=kept.recent or duplicate.recent,
        wiki_claim_references=tuple(
            sorted(set((*kept.wiki_claim_references, *duplicate.wiki_claim_references)))
        ),
    )


def deduplicate_candidates(
    candidates: tuple[ContextCandidate, ...],
) -> tuple[
    tuple[ContextCandidate, ...],
    tuple[ContextExclusion, ...],
    tuple[DeduplicationDecision, ...],
]:
    kept: dict[tuple[object, ...], ContextCandidate] = {}
    exclusions: list[ContextExclusion] = []
    decisions: list[DeduplicationDecision] = []
    for candidate in sorted(candidates, key=lambda item: str(item.candidate_id)):
        identity_key = (
            candidate.source_type,
            candidate.source_identity,
            candidate.source_revision,
            _scopes(candidate),
        )
        existing = kept.get(identity_key)
        if existing is None:
            kept[identity_key] = candidate
            continue
        if existing.content_hash != candidate.content_hash:
            raise ValueError("one exact source revision returned conflicting content hashes")
        kept[identity_key] = _merge(existing, candidate)
        decisions.append(
            DeduplicationDecision(
                kept_candidate_id=existing.candidate_id,
                removed_candidate_id=candidate.candidate_id,
            )
        )
        exclusions.append(_duplicate_exclusion(candidate))

    by_content: dict[tuple[str, tuple[tuple[str, str], ...]], ContextCandidate] = {}
    for candidate in sorted(
        kept.values(),
        key=lambda item: (_AUTHORITY_ORDER.get(item.source_type, 99), str(item.candidate_id)),
    ):
        content_key = candidate.content_hash, _scopes(candidate)
        existing = by_content.get(content_key)
        if existing is None:
            by_content[content_key] = candidate
            continue
        by_content[content_key] = _merge(existing, candidate)
        decisions.append(
            DeduplicationDecision(
                kept_candidate_id=existing.candidate_id,
                removed_candidate_id=candidate.candidate_id,
            )
        )
        exclusions.append(_duplicate_exclusion(candidate))

    semantic = {
        f"{item.source_identity}:{item.source_revision}": item
        for item in by_content.values()
        if item.source_type is ContextSourceType.SEMANTIC_CLAIM
    }
    final: list[ContextCandidate] = []
    for candidate in by_content.values():
        if candidate.source_type is ContextSourceType.WIKI:
            claim = next(
                (semantic[key] for key in candidate.wiki_claim_references if key in semantic),
                None,
            )
            if claim is not None:
                semantic[f"{claim.source_identity}:{claim.source_revision}"] = _merge(
                    claim, candidate
                )
                decisions.append(
                    DeduplicationDecision(
                        kept_candidate_id=claim.candidate_id,
                        removed_candidate_id=candidate.candidate_id,
                    )
                )
                exclusions.append(_duplicate_exclusion(candidate))
                continue
        final.append(candidate)
    replacements = {item.candidate_id: item for item in semantic.values()}
    final = [replacements.get(item.candidate_id, item) for item in final]
    return (
        tuple(sorted(final, key=lambda item: str(item.candidate_id))),
        tuple(sorted(exclusions, key=lambda item: str(item.candidate_id))),
        tuple(sorted(decisions, key=lambda item: str(item.removed_candidate_id))),
    )


def _duplicate_exclusion(candidate: ContextCandidate) -> ContextExclusion:
    return ContextExclusion(
        candidate_id=candidate.candidate_id,
        source_identity_hash=sha256(candidate.source_identity.encode()).hexdigest(),
        reason=ContextExclusionReason.DUPLICATE,
        detail_code="exact_duplicate_merged",
    )


def rank_candidates(
    candidates: tuple[ContextCandidate, ...],
    request: ContextRequest,
    profile: RankingProfileReference,
) -> tuple[ContextCandidate, ...]:
    quantum = Decimal(1).scaleb(-profile.score_precision)
    ranked = []
    for candidate in candidates:
        rrf = sum(
            (
                route.weight / Decimal(profile.rrf_k + route.rank)
                for route in candidate.retrieval_routes
            ),
            start=Decimal(0),
        )
        lexical = max(
            (
                item.raw_score
                for item in candidate.retrieval_routes
                if item.mode is RetrievalMode.LEXICAL
            ),
            default=Decimal(0),
        )
        vector = max(
            (
                item.raw_score
                for item in candidate.retrieval_routes
                if item.mode is RetrievalMode.EXACT_VECTOR
            ),
            default=Decimal(0),
        )
        graph = max(
            (
                item.raw_score
                for item in candidate.retrieval_routes
                if item.mode is RetrievalMode.GRAPH
            ),
            default=Decimal(0),
        )
        trust = _TRUST_SCORE[candidate.trust_class]
        scope = Decimal(int(any(item in request.required_scopes for item in candidate.scopes)))
        verification = Decimal(
            int(candidate.trust_class in {ContextTrustClass.SYSTEM, ContextTrustClass.VERIFIED})
        )
        recency = Decimal(int(candidate.recent))
        salience = candidate.score_breakdown.salience
        contradiction = Decimal(int(candidate.trust_class is ContextTrustClass.DISPUTED))
        final = (
            rrf
            + trust * profile.weights["trust"]
            + scope * profile.weights["scope"]
            + verification * profile.weights["verification"]
            + recency * profile.weights["recency"]
            + salience * profile.weights["salience"]
            + graph * profile.weights["graph"]
            - contradiction * profile.weights["contradiction"]
        ).quantize(quantum)
        breakdown = ContextScoreBreakdown(
            lexical=lexical.quantize(quantum),
            vector=vector.quantize(quantum),
            graph_proximity=graph.quantize(quantum),
            recency=recency.quantize(quantum),
            trust=trust.quantize(quantum),
            verification=verification.quantize(quantum),
            scope=scope.quantize(quantum),
            salience=salience.quantize(quantum),
            contradiction_penalty=contradiction.quantize(quantum),
            rrf_contribution=rrf.quantize(quantum),
            final_score=final,
        )
        ranked.append(reseal_candidate(candidate, score_breakdown=breakdown))
    return tuple(
        sorted(ranked, key=lambda item: (-item.score_breakdown.final_score, str(item.candidate_id)))
    )


def select_candidates(
    candidates: tuple[ContextCandidate, ...],
    request: ContextRequest,
    configuration: ContextConfiguration,
    estimator: ConservativeUtf8TokenEstimator,
) -> tuple[tuple[ContextCandidate, ...], tuple[ContextExclusion, ...], tuple[ContextWarning, ...]]:
    estimated = tuple(
        reseal_candidate(
            item,
            token_estimate=estimator.estimate_text(
                item.content or item.summary or item.source_identity
            ),
        )
        for item in candidates
    )
    required = [item for item in estimated if item.required]
    if len(required) > request.budget.maximum_items:
        raise ContextBudgetError("required item count exceeds the Context Budget")
    if sum(item.token_estimate for item in required) > request.budget.available_tokens:
        raise ContextBudgetError("required context does not fit the provider budget")

    selected: list[ContextCandidate] = []
    selected_ids: set[object] = set()
    source_counts: Counter[ContextSourceType] = Counter()
    tokens = 0

    def add(item: ContextCandidate) -> bool:
        nonlocal tokens
        if item.candidate_id in selected_ids:
            return True
        if len(selected) >= min(request.budget.maximum_items, configuration.maximum_selected_items):
            return False
        if source_counts[item.source_type] >= min(
            request.budget.maximum_items_per_source,
            configuration.maximum_items_per_source_type,
        ):
            return False
        if tokens + item.token_estimate > request.budget.available_tokens:
            return False
        selected.append(item)
        selected_ids.add(item.candidate_id)
        source_counts[item.source_type] += 1
        tokens += item.token_estimate
        return True

    for item in estimated:
        if item.required:
            add(item)
    for item in estimated:
        if item.pinned:
            add(item)
    for predicate in (
        lambda item: item.evidence,
        lambda item: item.recent,
        lambda item: item.source_type not in source_counts,
    ):
        for item in estimated:
            if predicate(item):
                add(item)
    for item in estimated:
        add(item)

    contradictions = {
        item.contradiction_group for item in selected if item.contradiction_group is not None
    }
    for group in sorted(contradictions):
        counterpart = next(
            (
                item
                for item in estimated
                if item.contradiction_group == group and item.candidate_id not in selected_ids
            ),
            None,
        )
        if counterpart is not None:
            add(counterpart)

    if any(item.required and item.candidate_id not in selected_ids for item in estimated):
        raise ContextBudgetError("a required candidate was excluded")
    exclusions = tuple(
        ContextExclusion(
            candidate_id=item.candidate_id,
            source_identity_hash=sha256(item.source_identity.encode()).hexdigest(),
            reason=(
                ContextExclusionReason.SOURCE_LIMIT
                if source_counts[item.source_type]
                >= min(
                    request.budget.maximum_items_per_source,
                    configuration.maximum_items_per_source_type,
                )
                else ContextExclusionReason.TOKEN_BUDGET
            ),
            detail_code="candidate_not_selected_by_bounded_greedy_packing",
        )
        for item in estimated
        if item.candidate_id not in selected_ids
    )
    warnings: list[ContextWarning] = []
    if sum(item.recent for item in selected) < request.budget.minimum_recent_items:
        warnings.append(
            ContextWarning(
                warning_type=ContextWarningType.QUOTA_UNMET,
                code="minimum_recent_items_unmet",
                message="Available safe candidates did not satisfy the recent-item quota.",
            )
        )
    if sum(item.evidence for item in selected) < request.budget.minimum_evidence_items:
        warnings.append(
            ContextWarning(
                warning_type=ContextWarningType.QUOTA_UNMET,
                code="minimum_evidence_items_unmet",
                message="Available safe candidates did not satisfy the evidence quota.",
            )
        )
    return tuple(selected), exclusions, tuple(warnings)
