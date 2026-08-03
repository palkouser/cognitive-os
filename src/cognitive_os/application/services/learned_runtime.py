"""Whether the runtime may use a learned ordering on this task, and why not when it may not.

S21D2-053 and S21D2-055. Four independent authorities have to agree before a correction is
ordered by anything other than the frozen deterministic baseline:

1. the durable ledger says this component is `ACTIVE` on this surface;
2. the host configuration allows it *and* routes this task's group;
3. the model artifact's lineage is verified and its descriptor matches the active revision;
4. the local embedding model is the one the artifact was fitted against.

Disagreement is not an error and not a degraded mode. It is the deterministic path, which is
what the system did before any of this existed — so the failure mode of every check here is
"behave exactly like Sprint 21C3", carrying a reason a health report can print.

The snapshot is resolved once per task and is immutable. Re-resolving mid-task would let a
disable land between two candidates of the same decision, which is a decision made half one
way and half the other.

This is not a second lifecycle. It reads durable state; it never advances it, and it never
replays it into `LearnedComponentRegistry`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class RuntimeHealthReason(StrEnum):
    """Why the deterministic path is in use. Every value is a fallback except `ACTIVE`."""

    ACTIVE = "active"
    PERSISTENCE_DISABLED = "persistence_disabled"
    ACTIVATION_DISABLED = "activation_disabled"
    NO_ACTIVE_REVISION = "no_active_revision"
    COMPONENT_NOT_ALLOWLISTED = "component_not_allowlisted"
    MULTIPLE_ACTIVE_REVISIONS = "multiple_active_revisions"
    GROUP_NOT_ROUTED = "group_not_routed"
    ROUTING_MANIFEST_MISMATCH = "routing_manifest_mismatch"
    ARTIFACT_MISSING = "artifact_missing"
    ARTIFACT_UNVERIFIED = "artifact_unverified"
    DESCRIPTOR_REVISION_MISMATCH = "descriptor_revision_mismatch"
    EMBEDDING_UNAVAILABLE = "embedding_unavailable"
    EMBEDDING_IDENTITY_MISMATCH = "embedding_identity_mismatch"


@dataclass(frozen=True, slots=True)
class ActiveComponentState:
    """What the durable ledger says. Read-only input to the resolver."""

    component_id: str
    surface: str
    revision: int
    model_artifact_id: UUID
    lineage_verified: bool
    descriptor_revision: int


@dataclass(frozen=True, slots=True)
class EmbeddingIdentity:
    model_id: str
    revision: str
    available: bool


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    """The configuration half: who may be active, and which groups are routed to them."""

    persistence_enabled: bool
    activation_enabled: bool
    active_components: tuple[str, ...]
    routed_groups: tuple[str, ...]
    routing_manifest_hash: str


@dataclass(frozen=True, slots=True)
class ResolvedComponent:
    """One task's immutable answer. `learned_ordering_permitted` is the whole question."""

    learned_ordering_permitted: bool
    reason: RuntimeHealthReason
    component_id: str | None = None
    revision: int | None = None
    model_artifact_id: UUID | None = None
    #: Names only, never exemplars or thresholds: a health report is not a model dump.
    detail: str = ""

    @property
    def uses_deterministic_fallback(self) -> bool:
        return not self.learned_ordering_permitted


@dataclass(frozen=True, slots=True)
class RuntimeHealth:
    """What an operator sees. It never claims active when the runtime uses the baseline."""

    surface: str
    active: bool
    reason: RuntimeHealthReason
    component_id: str | None
    revision: int | None
    routed_group_count: int
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "surface": self.surface,
            "active": self.active,
            "reason": self.reason.value,
            "component_id": self.component_id,
            "revision": self.revision,
            "routed_group_count": self.routed_group_count,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class LearnedRuntimeResolver:
    """Reconciles the four authorities. Pure: every input is passed in, nothing is fetched.

    Purity is the point. A resolver that reached for a repository would resolve differently
    depending on when it was called, and the contract is that one task gets one answer.
    """

    surface: str
    expected_embedding: EmbeddingIdentity

    def resolve(
        self,
        *,
        policy: RoutingPolicy,
        active_states: Sequence[ActiveComponentState],
        group: str,
        artifact_present: bool,
        local_embedding: EmbeddingIdentity,
        expected_routing_manifest_hash: str | None = None,
    ) -> ResolvedComponent:
        if not policy.persistence_enabled:
            return _fallback(RuntimeHealthReason.PERSISTENCE_DISABLED)
        if not policy.activation_enabled:
            return _fallback(RuntimeHealthReason.ACTIVATION_DISABLED)

        mine = [state for state in active_states if state.surface == self.surface]
        if not mine:
            return _fallback(RuntimeHealthReason.NO_ACTIVE_REVISION)
        if len(mine) > 1:
            # Fail closed rather than picking one: two active revisions on one surface means
            # the ledger disagrees with itself, and guessing would hide that.
            return _fallback(
                RuntimeHealthReason.MULTIPLE_ACTIVE_REVISIONS,
                detail=f"{len(mine)} active revisions on {self.surface}",
            )
        state = mine[0]

        if state.component_id not in policy.active_components:
            return _fallback(
                RuntimeHealthReason.COMPONENT_NOT_ALLOWLISTED, component_id=state.component_id
            )
        if group not in policy.routed_groups:
            return _fallback(RuntimeHealthReason.GROUP_NOT_ROUTED, component_id=state.component_id)
        if (
            expected_routing_manifest_hash is not None
            and policy.routing_manifest_hash != expected_routing_manifest_hash
        ):
            return _fallback(
                RuntimeHealthReason.ROUTING_MANIFEST_MISMATCH, component_id=state.component_id
            )

        if not artifact_present:
            return _fallback(RuntimeHealthReason.ARTIFACT_MISSING, component_id=state.component_id)
        if not state.lineage_verified:
            return _fallback(
                RuntimeHealthReason.ARTIFACT_UNVERIFIED, component_id=state.component_id
            )
        if state.descriptor_revision != state.revision:
            return _fallback(
                RuntimeHealthReason.DESCRIPTOR_REVISION_MISMATCH,
                component_id=state.component_id,
                detail=f"descriptor {state.descriptor_revision} against active {state.revision}",
            )

        if not local_embedding.available:
            return _fallback(
                RuntimeHealthReason.EMBEDDING_UNAVAILABLE, component_id=state.component_id
            )
        if (local_embedding.model_id, local_embedding.revision) != (
            self.expected_embedding.model_id,
            self.expected_embedding.revision,
        ):
            return _fallback(
                RuntimeHealthReason.EMBEDDING_IDENTITY_MISMATCH,
                component_id=state.component_id,
                detail="the local model is not the one the artifact was fitted against",
            )

        return ResolvedComponent(
            learned_ordering_permitted=True,
            reason=RuntimeHealthReason.ACTIVE,
            component_id=state.component_id,
            revision=state.revision,
            model_artifact_id=state.model_artifact_id,
        )

    def health(self, resolved: ResolvedComponent, *, routed_groups: int) -> RuntimeHealth:
        return RuntimeHealth(
            surface=self.surface,
            active=resolved.learned_ordering_permitted,
            reason=resolved.reason,
            component_id=resolved.component_id,
            revision=resolved.revision,
            routed_group_count=routed_groups,
            detail=resolved.detail,
        )


def _fallback(
    reason: RuntimeHealthReason, *, component_id: str | None = None, detail: str = ""
) -> ResolvedComponent:
    return ResolvedComponent(
        learned_ordering_permitted=False,
        reason=reason,
        component_id=component_id,
        detail=detail,
    )
