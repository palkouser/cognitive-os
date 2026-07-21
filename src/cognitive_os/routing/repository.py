"""Dependency-light append-only routing repository."""

from typing import Any
from uuid import UUID

from cognitive_os.domain.routing import (
    ModelCapabilityProfile,
    RoutingAccessRecord,
    RoutingDecision,
    RoutingExperiment,
    RoutingObservation,
    RoutingOutcome,
    RoutingPolicyRevision,
    RoutingStatistics,
)

from .errors import RoutingConflictError


class InMemoryCapabilityRepository:
    def __init__(self) -> None:
        self.profiles: dict[tuple[str, int], ModelCapabilityProfile] = {}
        self.policies: dict[tuple[str, int], RoutingPolicyRevision] = {}
        self.observations: dict[UUID, RoutingObservation] = {}
        self.decisions: dict[UUID, RoutingDecision] = {}
        self.outcomes: dict[UUID, RoutingOutcome] = {}
        self.statistics: dict[UUID, RoutingStatistics] = {}
        self.experiments: dict[UUID, RoutingExperiment] = {}
        self.accesses: dict[UUID, RoutingAccessRecord] = {}

    async def register_profile(self, profile: ModelCapabilityProfile) -> None:
        identity = profile.model_identity.content_hash
        key = identity, profile.profile_revision
        existing = self.profiles.get(key)
        if existing is not None and existing != profile:
            raise RoutingConflictError("capability profile revision changed")
        if (
            profile.profile_revision > 1
            and (identity, profile.profile_revision - 1) not in self.profiles
        ):
            raise RoutingConflictError("capability profile predecessor is unavailable")
        self.profiles[key] = profile

    async def get_profile(
        self, model_identity_hash: str, revision: int | None = None
    ) -> ModelCapabilityProfile | None:
        if revision is not None:
            return self.profiles.get((model_identity_hash, revision))
        revisions = [
            profile
            for (identity, _), profile in self.profiles.items()
            if identity == model_identity_hash
        ]
        return max(revisions, key=lambda item: item.profile_revision, default=None)

    async def query_profiles(self, *, limit: int = 256) -> tuple[ModelCapabilityProfile, ...]:
        current: dict[str, ModelCapabilityProfile] = {}
        for (identity, _), profile in self.profiles.items():
            previous = current.get(identity)
            if previous is None or profile.profile_revision > previous.profile_revision:
                current[identity] = profile
        return tuple(
            sorted(current.values(), key=lambda item: item.model_identity.content_hash)[:limit]
        )

    async def create_policy(self, policy: RoutingPolicyRevision) -> None:
        key = policy.policy_id, policy.revision
        existing = self.policies.get(key)
        if existing is not None and existing != policy:
            raise RoutingConflictError("routing policy revision changed")
        if policy.revision > 1 and (policy.policy_id, policy.revision - 1) not in self.policies:
            raise RoutingConflictError("routing policy predecessor is unavailable")
        self.policies[key] = policy

    async def get_policy(
        self, policy_id: str, revision: int | None = None
    ) -> RoutingPolicyRevision | None:
        if revision is not None:
            return self.policies.get((policy_id, revision))
        revisions = [
            policy for (identity, _), policy in self.policies.items() if identity == policy_id
        ]
        return max(revisions, key=lambda item: item.revision, default=None)

    async def record_observation(self, observation: RoutingObservation) -> None:
        await self._immutable(self.observations, observation.observation_id, observation)

    async def list_observations(self, *, limit: int = 10_000) -> tuple[RoutingObservation, ...]:
        return tuple(
            sorted(self.observations.values(), key=lambda item: str(item.observation_id))[:limit]
        )

    async def record_decision(self, decision: RoutingDecision) -> None:
        await self._immutable(self.decisions, decision.decision_id, decision)

    async def record_outcome(self, outcome: RoutingOutcome) -> None:
        if outcome.decision_id not in self.decisions:
            raise RoutingConflictError("routing outcome references an unknown decision")
        await self._immutable(self.outcomes, outcome.outcome_id, outcome)

    async def record_statistics(self, statistics: RoutingStatistics) -> None:
        await self._immutable(self.statistics, statistics.statistics_id, statistics)

    async def list_statistics(self, *, limit: int = 100_000) -> tuple[RoutingStatistics, ...]:
        return tuple(
            sorted(self.statistics.values(), key=lambda item: str(item.statistics_id))[:limit]
        )

    async def record_experiment(self, experiment: RoutingExperiment) -> None:
        await self._immutable(self.experiments, experiment.experiment_id, experiment)

    async def record_access(self, access: RoutingAccessRecord) -> None:
        await self._immutable(self.accesses, access.access_id, access)

    @staticmethod
    async def _immutable(store: dict[Any, Any], key: object, value: object) -> None:
        existing = store.get(key)
        if existing is not None and existing != value:
            raise RoutingConflictError("immutable routing record changed")
        store[key] = value
