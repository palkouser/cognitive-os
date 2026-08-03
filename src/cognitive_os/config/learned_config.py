"""Fail-closed host configuration for durable learned evidence.

The defaults here are the whole safety argument. Persistence is on, because recording
what happened is never the risk. Activation is off, the authorised-actor set is empty,
and the active-component set is empty — so a deployment that reads this file and changes
nothing runs exactly the deterministic system it ran before.

The validator refuses configurations that would quietly widen that: naming an active
component without naming who may activate it, enabling artifact deserialisation at all,
or letting a model identity approve or review. Those are not options with a sensible
setting; they are the failures Sprint 21C1 exists to make unreachable. See ADR 0086.
"""

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel


class LearnedPersistenceConfiguration(ImmutableContractModel):
    #: Recording lifecycle history, evidence and intake decisions. Safe by construction:
    #: an append-only ledger changes no decision the system makes.
    persistence_enabled: bool = True

    #: Whether the runtime may activate a learned component at all. Off by default, and
    #: off is the state every Sprint 21C1 deployment should stay in: nothing has been
    #: trained, so there is nothing whose activation could be justified.
    activation_enabled: bool = False

    #: Callers permitted to activate or roll back. Empty means nobody, which is what
    #: makes `activation_enabled` alone insufficient.
    activation_actors: tuple[str, ...] = ()

    #: Components the runtime should treat as active. Empty is the shipped state and the
    #: only state Sprint 21C1 supports; a name here without a stored activation receipt
    #: would be a claim the learned ledger cannot back.
    active_components: tuple[str, ...] = ()

    #: Operators permitted to review quarantined observations.
    quarantine_reviewers: tuple[str, ...] = ()

    #: How long an artifact verification stays usable as activation evidence, in hours.
    artifact_verification_max_age_hours: int = Field(default=168, ge=1, le=8_760)

    #: Bounds on every listing the learned plane exposes.
    maximum_page_size: int = Field(default=500, ge=1, le=500)
    maximum_quarantine_page_size: int = Field(default=200, ge=1, le=200)

    #: Sensitivity labels whose reads must leave an access record.
    audited_sensitivities: tuple[str, ...] = ("internal", "restricted")

    #: Permanently false in Sprint 21C1. An artifact is data; a learned plane that
    #: executed an object graph supplied as data would turn every lineage record into a
    #: remote-code-execution surface.
    artifact_deserialisation_enabled: bool = False

    #: Permanently false. A component that can approve or clear its own evidence is not
    #: governed, whatever the rest of the configuration says.
    model_approval_enabled: bool = False
    model_review_enabled: bool = False

    #: Permanently false. Training on real governed runs would contaminate the only
    #: uncontaminated corpus the system has to measure against.
    real_run_training_enabled: bool = False

    #: Sprint 21D2 canary routing. Empty is the shipped state: an approved component is
    #: active on its surface, and this narrows *where* the runtime consults it. Canary is a
    #: hash-bound configuration subset of an already approved scope, not a lifecycle state —
    #: so it lives here rather than in the approval contract, which has no field for it.
    correction_ranking_groups: tuple[str, ...] = ()
    #: The manifest those groups came from. Without it a group list is an assertion; with it
    #: the resolver can refuse a routing set that does not match the sealed canary manifest.
    correction_ranking_manifest_hash: str = ""

    @model_validator(mode="after")
    def reject_ungoverned_configuration(self) -> "LearnedPersistenceConfiguration":
        if self.artifact_deserialisation_enabled:
            raise ValueError(
                "artifact deserialisation cannot be enabled: an artifact is data, and "
                "loading one would make every lineage record an execution surface"
            )
        if self.model_approval_enabled or self.model_review_enabled:
            raise ValueError(
                "a model or provider identity cannot approve an activation or review "
                "quarantined evidence; a component that can clear itself is not governed"
            )
        if self.real_run_training_enabled:
            raise ValueError(
                "real governed runs are evaluation-only: training on them would "
                "contaminate the corpus every later comparison is measured against"
            )
        if self.active_components and not self.activation_enabled:
            raise ValueError(
                "active components are declared while activation is disabled; the "
                "configuration contradicts itself and the safe reading is not obvious"
            )
        if self.activation_enabled and not self.activation_actors:
            raise ValueError(
                "activation is enabled with no authorised actor, which would either do "
                "nothing or invite one to be added without review"
            )
        if self.correction_ranking_groups and not self.correction_ranking_manifest_hash:
            raise ValueError(
                "correction-ranking routing names groups without the manifest hash they came "
                "from; an unbound routing set cannot be checked against the sealed canary"
            )
        if self.correction_ranking_manifest_hash and not self.correction_ranking_groups:
            raise ValueError(
                "correction-ranking routing declares a manifest but routes no group, which "
                "reads as active while changing nothing"
            )
        return self


def load_learned_configuration(path: Path) -> LearnedPersistenceConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("learned"), dict):
        raise ValueError("learned configuration requires a learned mapping")
    return LearnedPersistenceConfiguration.model_validate(raw["learned"])
