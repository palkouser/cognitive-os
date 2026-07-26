"""Frozen registry for optional learned components.

Same shape as the verifier, tool, retriever, skill, and strategy registries: a
component is declared, registered before use, and the registry is frozen so the
active set cannot change under a running task. Absence is a first-class, tested
state — a component that is not installed leaves the deterministic path exactly as
it was.

A component reaches `ACTIVE` only if its descriptor supports abstention. That is
enforced here as well as in `LearnedPromotionAssessment`, because a registry that
can activate an unpromotable component makes the promotion gate advisory.
"""

from __future__ import annotations

from cognitive_os.application.ports.learned import LearnedComponentPort
from cognitive_os.domain.learned import LearnedComponentDescriptor, LearnedComponentState


class LearnedComponentRegistryError(RuntimeError):
    """Raised on a registration or lifecycle transition the registry refuses."""


_ALLOWED: dict[LearnedComponentState, frozenset[LearnedComponentState]] = {
    LearnedComponentState.REGISTERED: frozenset(
        {LearnedComponentState.SHADOW, LearnedComponentState.RETRACTED}
    ),
    LearnedComponentState.SHADOW: frozenset(
        {
            LearnedComponentState.VERIFIED,
            LearnedComponentState.DISABLED,
            LearnedComponentState.RETRACTED,
        }
    ),
    LearnedComponentState.VERIFIED: frozenset(
        {
            LearnedComponentState.ACTIVE,
            LearnedComponentState.DISABLED,
            LearnedComponentState.RETRACTED,
        }
    ),
    LearnedComponentState.ACTIVE: frozenset(
        {LearnedComponentState.DISABLED, LearnedComponentState.RETRACTED}
    ),
    LearnedComponentState.DISABLED: frozenset(
        {LearnedComponentState.SHADOW, LearnedComponentState.RETRACTED}
    ),
    #: Terminal. A retracted component is history, not a candidate.
    LearnedComponentState.RETRACTED: frozenset(),
}


def legal_transitions(current: LearnedComponentState) -> frozenset[LearnedComponentState]:
    """The states reachable from `current`.

    Exported so durable persistence consults the same table the in-memory registry
    does. A second copy of this policy in the persistence layer would let the two
    disagree, and the one that disagreed silently would be the one that wrote to disk.
    """
    return _ALLOWED[current]


def transition_is_legal(current: LearnedComponentState, target: LearnedComponentState) -> bool:
    return target in _ALLOWED[current]


def durable_transition_is_legal(
    current: LearnedComponentState,
    target: LearnedComponentState,
    *,
    rollback_target_revision: int | None = None,
) -> bool:
    """Transition legality for a durable lifecycle record.

    Identical to `transition_is_legal` with one named exception: `DISABLED -> ACTIVE` is
    legal when, and only when, the record names the prior activation revision it
    restores. The generic path still refuses it, so the single most dangerous transition
    stays unreachable through the ordinary API, and a rollback has to say what it is
    rolling back to. `LearnedComponentRevisionRecord` separately requires any record
    reaching `ACTIVE` to carry a promotion assessment and an approval hash, so a
    rollback re-states the evidence of the activation it restores. See ADR 0086.
    """
    if (
        current is LearnedComponentState.DISABLED
        and target is LearnedComponentState.ACTIVE
        and rollback_target_revision is not None
    ):
        return True
    return transition_is_legal(current, target)


class LearnedComponentRegistry:
    def __init__(self) -> None:
        self._components: dict[str, LearnedComponentPort] = {}
        self._states: dict[str, LearnedComponentState] = {}
        self._frozen = False

    def register(self, component: LearnedComponentPort) -> None:
        if self._frozen:
            raise LearnedComponentRegistryError("the learned-component registry is frozen")
        descriptor = component.descriptor
        if descriptor.component_id in self._components:
            raise LearnedComponentRegistryError(
                f"duplicate learned component: {descriptor.component_id}"
            )
        self._components[descriptor.component_id] = component
        self._states[descriptor.component_id] = LearnedComponentState.REGISTERED

    def freeze(self) -> None:
        self._frozen = True

    @property
    def frozen(self) -> bool:
        return self._frozen

    def component_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._components))

    def descriptor(self, component_id: str) -> LearnedComponentDescriptor:
        return self._require(component_id).descriptor

    def state(self, component_id: str) -> LearnedComponentState:
        self._require(component_id)
        return self._states[component_id]

    def transition(self, component_id: str, target: LearnedComponentState) -> None:
        descriptor = self._require(component_id).descriptor
        current = self._states[component_id]
        if target not in _ALLOWED[current]:
            raise LearnedComponentRegistryError(
                f"illegal learned-component transition {current.value} -> {target.value}"
            )
        if target is LearnedComponentState.ACTIVE and not descriptor.promotable:
            raise LearnedComponentRegistryError(
                "a component that cannot abstain cannot become active"
            )
        self._states[component_id] = target

    def active_for(self, surface: str) -> LearnedComponentPort | None:
        """The one active component for a surface, or `None`.

        `None` is the normal case and the deterministic path's signal to proceed
        unchanged, which is why every caller must handle it.
        """
        active = [
            component
            for component_id, component in sorted(self._components.items())
            if self._states[component_id] is LearnedComponentState.ACTIVE
            and component.descriptor.surface == surface
        ]
        if len(active) > 1:
            raise LearnedComponentRegistryError(
                f"more than one active learned component for surface {surface!r}"
            )
        return active[0] if active else None

    def shadow_for(self, surface: str) -> tuple[LearnedComponentPort, ...]:
        return tuple(
            component
            for component_id, component in sorted(self._components.items())
            if self._states[component_id] is LearnedComponentState.SHADOW
            and component.descriptor.surface == surface
        )

    def _require(self, component_id: str) -> LearnedComponentPort:
        component = self._components.get(component_id)
        if component is None:
            raise LearnedComponentRegistryError(f"unknown learned component: {component_id}")
        return component
