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

from cognitive_os.domain.learned import LearnedComponentState

#: A ranker larger than this is not a ranker this runtime agreed to load. Deliberately the
#: same number as the artifact loader's own bound, and deliberately not imported from it: the
#: resolver must not reach into `learning.correction_artifact`, because that module is where
#: the direct evaluation boundary lives and the runtime may not be able to select it.
MAXIMUM_RUNTIME_ARTIFACT_BYTES = 64 * 1024 * 1024


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
    #: S21D3-052. The ledger row is not in the state a routing decision may rely on —
    #: registered, shadow, verified-but-never-activated, or disabled after a kill switch.
    #: Named apart from `NO_ACTIVE_REVISION`, which means the surface has no row at all.
    LIFECYCLE_NOT_ACTIVE = "lifecycle_not_active"
    #: The row is active and carries no approval, or carries one this host was not told to
    #: expect. An activation without its approval is the failure the approval exists to stop.
    COMPONENT_NOT_APPROVED = "component_not_approved"
    #: The host is running a configuration other than the sealed one. Refused rather than
    #: reconciled: the sealed bytes are what the evidence was produced under.
    CONFIGURATION_HASH_MISMATCH = "configuration_hash_mismatch"
    #: The bytes are there and do not hash to what the store recorded.
    ARTIFACT_CORRUPT = "artifact_corrupt"
    ARTIFACT_OVERSIZED = "artifact_oversized"


@dataclass(frozen=True, slots=True)
class ArtifactAvailability:
    """What the store says about the model bytes, without handing any of them over.

    Three separate facts because they fail for different reasons and an operator has to tell
    them apart: an absent artifact is a provisioning problem, an oversized one is a fitting
    problem, and bytes that no longer hash to their record are a corruption problem.
    """

    present: bool
    bytes_verified: bool = True
    size_bytes: int = 0


@dataclass(frozen=True, slots=True)
class ActiveComponentState:
    """What the durable ledger says. Read-only input to the resolver."""

    component_id: str
    surface: str
    revision: int
    model_artifact_id: UUID
    lineage_verified: bool
    descriptor_revision: int
    #: The ledger's own state column, not an assertion by whoever assembled this list. A
    #: caller that filtered for "active" and got it wrong is exactly what this re-checks.
    lifecycle_state: LearnedComponentState = LearnedComponentState.ACTIVE
    approval_hash: str | None = None


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
    #: The canonical runtime configuration this host is actually running — the exact canary
    #: or bounded steady-state bytes sealed at the pre-final checkpoint.
    runtime_configuration_hash: str = ""


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
    maximum_artifact_bytes: int = MAXIMUM_RUNTIME_ARTIFACT_BYTES

    def resolve(
        self,
        *,
        policy: RoutingPolicy,
        active_states: Sequence[ActiveComponentState],
        group: str,
        artifact: ArtifactAvailability,
        local_embedding: EmbeddingIdentity,
        expected_routing_manifest_hash: str | None = None,
        expected_configuration_hash: str | None = None,
        expected_approval_hash: str | None = None,
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
        # Before anything about this task: the ledger state and the approval that authorised
        # it. Checking routing first would report "group not routed" for a disabled component,
        # which reads as a configuration choice rather than as a kill switch that fired.
        if state.lifecycle_state is not LearnedComponentState.ACTIVE:
            return _fallback(
                RuntimeHealthReason.LIFECYCLE_NOT_ACTIVE,
                component_id=state.component_id,
                detail=f"the ledger has it {state.lifecycle_state.value}",
            )
        if expected_approval_hash is not None and state.approval_hash != expected_approval_hash:
            return _fallback(
                RuntimeHealthReason.COMPONENT_NOT_APPROVED,
                component_id=state.component_id,
                detail=(
                    "the active revision carries no approval"
                    if state.approval_hash is None
                    else "the active revision carries another approval"
                ),
            )
        if (
            expected_configuration_hash is not None
            and policy.runtime_configuration_hash != expected_configuration_hash
        ):
            return _fallback(
                RuntimeHealthReason.CONFIGURATION_HASH_MISMATCH, component_id=state.component_id
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

        if not artifact.present:
            return _fallback(RuntimeHealthReason.ARTIFACT_MISSING, component_id=state.component_id)
        if artifact.size_bytes > self.maximum_artifact_bytes:
            return _fallback(
                RuntimeHealthReason.ARTIFACT_OVERSIZED,
                component_id=state.component_id,
                detail=f"{artifact.size_bytes} bytes above {self.maximum_artifact_bytes}",
            )
        if not artifact.bytes_verified:
            return _fallback(RuntimeHealthReason.ARTIFACT_CORRUPT, component_id=state.component_id)
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
