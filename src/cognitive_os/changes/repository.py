"""Dependency-light append-only controlled-change repository."""

from typing import TypeVar
from uuid import UUID

from cognitive_os.domain.changes import (
    ChangeAccessRecord,
    ChangeCandidate,
    ChangeExperiment,
    ChangeExperimentRevision,
    ChangeIsolationManifest,
    ChangeRunManifest,
    EvaluationRun,
    PromotionAssessment,
    PromotionBundle,
    PromotionReceipt,
    PromotionReview,
    RegressionComparison,
    RollbackReceipt,
)

from .service import ChangeConflictError

Key = TypeVar("Key")
Value = TypeVar("Value")


class InMemoryChangeRepository:
    def __init__(self) -> None:
        self.experiments: dict[UUID, ChangeExperiment] = {}
        self.revisions: dict[tuple[UUID, int], ChangeExperimentRevision] = {}
        self.request_signatures: dict[str, UUID] = {}
        self.isolations: dict[UUID, ChangeIsolationManifest] = {}
        self.candidates: dict[UUID, ChangeCandidate] = {}
        self.evaluations: dict[UUID, EvaluationRun] = {}
        self.comparisons: dict[str, RegressionComparison] = {}
        self.assessments: dict[UUID, PromotionAssessment] = {}
        self.reviews: dict[UUID, PromotionReview] = {}
        self.bundles: dict[UUID, PromotionBundle] = {}
        self.promotions: dict[UUID, PromotionReceipt] = {}
        self.rollbacks: dict[UUID, RollbackReceipt] = {}
        self.accesses: dict[UUID, ChangeAccessRecord] = {}
        self.manifests: dict[tuple[UUID, int], ChangeRunManifest] = {}

    async def create(
        self, experiment: ChangeExperiment, revision: ChangeExperimentRevision
    ) -> None:
        if revision.experiment_id != experiment.experiment_id or revision.revision != 1:
            raise ChangeConflictError("invalid initial experiment revision")
        signature = experiment.canonical_hash(
            exclude={"experiment_id", "requested_by", "approved_by", "created_at", "content_hash"}
        )
        existing = self.request_signatures.get(signature)
        if existing is not None and existing != experiment.experiment_id:
            raise ChangeConflictError("duplicate experiment request")
        self._immutable(self.experiments, experiment.experiment_id, experiment)
        self._immutable(self.revisions, (experiment.experiment_id, 1), revision)
        self.request_signatures[signature] = experiment.experiment_id

    async def append_revision(
        self, revision: ChangeExperimentRevision, *, expected_revision: int
    ) -> None:
        current = await self.get_current_revision(revision.experiment_id)
        if current is None or current.revision != expected_revision:
            raise ChangeConflictError("experiment revision compare-and-set failed")
        if revision.revision != expected_revision + 1:
            raise ChangeConflictError("experiment revision is not contiguous")
        self._immutable(self.revisions, (revision.experiment_id, revision.revision), revision)

    async def get_exact_revision(
        self, experiment_id: UUID, revision: int
    ) -> ChangeExperimentRevision | None:
        return self.revisions.get((experiment_id, revision))

    async def get_current_revision(self, experiment_id: UUID) -> ChangeExperimentRevision | None:
        values = [
            item for (identity, _), item in self.revisions.items() if identity == experiment_id
        ]
        return max(values, key=lambda item: item.revision, default=None)

    async def find_by_request_signature(self, signature: str) -> ChangeExperiment | None:
        identity = self.request_signatures.get(signature)
        return self.experiments.get(identity) if identity else None

    async def record_isolation(self, value: ChangeIsolationManifest) -> None:
        self._immutable(self.isolations, value.experiment_id, value)

    async def record_candidate(self, value: ChangeCandidate) -> None:
        self._immutable(self.candidates, value.candidate_id, value)

    async def record_evaluation(self, value: EvaluationRun) -> None:
        self._immutable(self.evaluations, value.evaluation_run_id, value)

    async def record_comparison(self, value: RegressionComparison) -> None:
        self._immutable(self.comparisons, value.content_hash, value)

    async def record_assessment(self, value: PromotionAssessment) -> None:
        self._immutable(self.assessments, value.assessment_id, value)

    async def record_review(self, value: PromotionReview) -> None:
        self._immutable(self.reviews, value.review_id, value)

    async def get_review(self, review_id: UUID) -> PromotionReview | None:
        return self.reviews.get(review_id)

    async def record_bundle(self, value: PromotionBundle) -> None:
        self._immutable(self.bundles, value.promotion_bundle_id, value)

    async def record_promotion(self, value: PromotionReceipt) -> None:
        self._immutable(self.promotions, value.promotion_id, value)

    async def record_rollback(self, value: RollbackReceipt) -> None:
        self._immutable(self.rollbacks, value.rollback_id, value)

    async def record_access(self, value: ChangeAccessRecord) -> None:
        self._immutable(self.accesses, value.access_id, value)

    async def record_manifest(self, value: ChangeRunManifest) -> None:
        self._immutable(self.manifests, (value.experiment_id, value.experiment_revision), value)

    async def list_current(self) -> tuple[ChangeExperimentRevision, ...]:
        values = [
            await self.get_current_revision(item) for item in sorted(self.experiments, key=str)
        ]
        return tuple(item for item in values if item is not None)

    @staticmethod
    def _immutable(store: dict[Key, Value], key: Key, value: Value) -> None:
        existing = store.get(key)
        if existing is not None and existing != value:
            raise ChangeConflictError("immutable controlled-change record changed")
        store[key] = value
