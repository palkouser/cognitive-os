"""Governed append-only strategy lifecycle service."""

from collections.abc import Callable
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.strategy_repository import StrategyRepositoryPort
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.strategies import (
    StrategyActor,
    StrategyCreatorType,
    StrategyEdgeSet,
    StrategyItem,
    StrategyPromotionDecision,
    StrategyPromotionOutcome,
    StrategyRevision,
    StrategyStatus,
    StrategyVerificationSnapshot,
)
from cognitive_os.events.strategy_event_service import StrategyEventService
from cognitive_os.events.strategy_events import (
    StrategyCreated,
    StrategyDeprecated,
    StrategyRetracted,
    StrategyRevisionAppended,
    StrategyStaged,
    StrategyStatusChanged,
    StrategySuperseded,
    StrategyVerified,
)
from cognitive_os.strategies.engine import validate_lifecycle_transition
from cognitive_os.strategies.errors import StrategyPolicyError


class StrategyService:
    def __init__(
        self,
        repository: StrategyRepositoryPort,
        *,
        clock: Callable[[], datetime] = utc_now,
        events: StrategyEventService | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._events = events

    async def create(
        self,
        item: StrategyItem,
        revision: StrategyRevision,
        edge_set: StrategyEdgeSet,
    ) -> StrategyItem:
        if revision.status is not StrategyStatus.DRAFT:
            raise StrategyPolicyError("a strategy must start as draft")
        if revision.created_by.creator_type in {
            StrategyCreatorType.PROVIDER,
            StrategyCreatorType.IMPORT_SERVICE,
        }:
            raise StrategyPolicyError("untrusted actor cannot create authoritative strategy")
        result = await self._repository.create_strategy(item, revision, edge_set)
        if self._events:
            await self._events.append(
                revision.strategy_id,
                StrategyCreated(
                    strategy_id=revision.strategy_id,
                    revision=revision.revision,
                    status=revision.status,
                    content_hash=revision.content_hash,
                    occurred_at=revision.created_at,
                ),
                correlation_id=revision.strategy_id,
            )
        return result

    async def transition(
        self,
        strategy_id: UUID,
        requested_status: StrategyStatus,
        *,
        expected_revision: int,
        actor: StrategyActor,
        reason: str,
        verification: StrategyVerificationSnapshot | None = None,
        promotion: StrategyPromotionDecision | None = None,
    ) -> StrategyRevision:
        current = await self._repository.get_current(strategy_id)
        if current is None or current[0].current_revision != expected_revision:
            raise StrategyPolicyError("strategy revision is stale or unavailable")
        _, revision = current
        validate_lifecycle_transition(revision.status, requested_status)
        if actor.creator_type in {
            StrategyCreatorType.PROVIDER,
            StrategyCreatorType.IMPORT_SERVICE,
        }:
            raise StrategyPolicyError("untrusted actor cannot authorize strategy transition")
        if requested_status is StrategyStatus.VERIFIED:
            if verification is None or not verification.passed or promotion is None:
                raise StrategyPolicyError(
                    "verified strategy promotion requires complete verifier evidence"
                )
            if (
                verification.strategy_id != strategy_id
                or verification.revision != revision.revision
                or promotion.strategy_id != strategy_id
                or promotion.revision != revision.revision
                or promotion.outcome is not StrategyPromotionOutcome.VERIFY
            ):
                raise StrategyPolicyError("strategy promotion targets another revision")
        next_revision = StrategyRevision.model_validate(
            {
                **revision.model_dump(mode="python", exclude={"content_hash"}),
                "revision": revision.revision + 1,
                "previous_revision": revision.revision,
                "status": requested_status,
                "created_at": self._clock(),
                "created_by": actor,
                "reason": reason,
            }
        )
        old_edges = await self._repository.read_edge_set(strategy_id, expected_revision)
        next_edges = StrategyEdgeSet(
            strategy_id=strategy_id,
            revision=next_revision.revision,
            edges=tuple(
                edge.__class__.model_validate(
                    {
                        **edge.model_dump(mode="python", exclude={"edge_id", "edge_hash"}),
                        "edge_id": uuid5(
                            NAMESPACE_URL,
                            f"strategy-edge:{strategy_id}:{next_revision.revision}:"
                            f"{edge.edge_type.value}:{edge.target.canonical_hash()}",
                        ),
                        "source_revision": next_revision.revision,
                        "created_at": next_revision.created_at,
                    }
                )
                for edge in old_edges.edges
            ),
        )
        appended = await self._repository.append_revision(
            next_revision,
            expected_revision=expected_revision,
            edge_set=next_edges,
        )
        if self._events:
            await self._events.append(
                strategy_id,
                StrategyRevisionAppended(
                    strategy_id=strategy_id,
                    revision=appended.revision,
                    previous_revision=revision.revision,
                    status=appended.status,
                    content_hash=appended.content_hash,
                    occurred_at=appended.created_at,
                ),
                correlation_id=strategy_id,
            )
            event_type: type[StrategyStatusChanged] = {
                StrategyStatus.STAGED: StrategyStaged,
                StrategyStatus.VERIFIED: StrategyVerified,
                StrategyStatus.DEPRECATED: StrategyDeprecated,
                StrategyStatus.SUPERSEDED: StrategySuperseded,
                StrategyStatus.RETRACTED: StrategyRetracted,
            }[requested_status]
            await self._events.append(
                strategy_id,
                event_type(
                    strategy_id=strategy_id,
                    revision=appended.revision,
                    previous_status=revision.status,
                    status=requested_status,
                    reason_code=reason,
                    occurred_at=appended.created_at,
                ),
                correlation_id=strategy_id,
            )
        return appended

    async def revise(
        self,
        strategy_id: UUID,
        proposed: StrategyRevision,
        edge_set: StrategyEdgeSet,
        *,
        expected_revision: int,
        actor: StrategyActor,
        reason: str,
    ) -> StrategyRevision:
        """Append operator-authored content as a new draft revision."""
        current = await self._repository.get_current(strategy_id)
        if current is None or current[0].current_revision != expected_revision:
            raise StrategyPolicyError("strategy revision is stale or unavailable")
        if proposed.strategy_id != strategy_id or edge_set.strategy_id != strategy_id:
            raise StrategyPolicyError("strategy revision targets another identity")
        if actor.creator_type in {
            StrategyCreatorType.PROVIDER,
            StrategyCreatorType.IMPORT_SERVICE,
        }:
            raise StrategyPolicyError("untrusted actor cannot author a strategy revision")
        created_at = self._clock()
        revision = StrategyRevision.model_validate(
            {
                **proposed.model_dump(
                    mode="python",
                    exclude={
                        "content_hash",
                        "revision",
                        "previous_revision",
                        "status",
                        "created_at",
                        "created_by",
                        "reason",
                    },
                ),
                "strategy_id": strategy_id,
                "revision": expected_revision + 1,
                "previous_revision": expected_revision,
                "status": StrategyStatus.DRAFT,
                "created_at": created_at,
                "created_by": actor,
                "reason": reason,
            }
        )
        revised_edges = StrategyEdgeSet(
            strategy_id=strategy_id,
            revision=revision.revision,
            edges=tuple(
                edge.__class__.model_validate(
                    {
                        **edge.model_dump(mode="python", exclude={"edge_id", "edge_hash"}),
                        "edge_id": uuid5(
                            NAMESPACE_URL,
                            f"strategy-edge:{strategy_id}:{revision.revision}:"
                            f"{edge.edge_type.value}:{edge.target.canonical_hash()}",
                        ),
                        "source_strategy_id": strategy_id,
                        "source_revision": revision.revision,
                        "created_at": created_at,
                    }
                )
                for edge in edge_set.edges
            ),
        )
        appended = await self._repository.append_revision(
            revision,
            expected_revision=expected_revision,
            edge_set=revised_edges,
        )
        if self._events:
            await self._events.append(
                strategy_id,
                StrategyRevisionAppended(
                    strategy_id=strategy_id,
                    revision=appended.revision,
                    previous_revision=expected_revision,
                    status=appended.status,
                    content_hash=appended.content_hash,
                    occurred_at=appended.created_at,
                ),
                correlation_id=strategy_id,
            )
        return appended
