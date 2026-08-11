"""S22A-W0: the descriptor contract, its fail-closed boundary, and the released adapter.

The groundwork module was written and never executed against a test. Everything Sprint 22A
claims rests on three properties of it, and each is a section below.

*The grammar is the anti-silo policy.* A domain id is a string with a shape, and nothing in
the shape names a science. If the grammar leaks — an uppercase member, a leading digit, an
id long enough to be a payload — the "data-driven" registry has an unbounded key space.

*Validation is closed-world.* Every cross-reference resolves inside the package's own
declared world or the package is refused. A concept shared into a domain the descriptor
never declared is exactly the silo the sprint exists to prevent, wearing a sharing field.

*The four released domains are derived, not transcribed.* The adapter's four content hashes
are the backward-compatibility contract, and they are compared against the **sealed survey
record** rather than against constants typed here — W4-F1's rule: an assertion names the
sealed record it reads, and an authorised change re-binds that record rather than editing a
literal in a test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from cognitive_os.domain.descriptors import (
    DOMAIN_ID_MAX_LENGTH,
    DOMAIN_PACKAGE_MAX_BYTES,
    RELEASED_DOMAIN_IDS,
    SCHEMA_VERSION,
    DomainCapabilityRequirements,
    DomainConcept,
    DomainDescriptorV1,
    DomainLifecycleState,
    DomainPackageError,
    DomainTransferLink,
    released_domain_descriptors,
    validate_domain_package,
)
from cognitive_os.domain.domains import DomainKind, ProvenanceRef

REPOSITORY = Path(__file__).resolve().parents[3]
SURVEY = REPOSITORY / "docs/sprints/sprint-22/evidence/sprint-22a-domain-survey.json"


def _survey() -> dict[str, Any]:
    return json.loads(SURVEY.read_text(encoding="utf-8"))


def _provenance() -> ProvenanceRef:
    return ProvenanceRef(
        source="sprint-22a test fixture",
        revision="none",
        licence="internal",
        redistributable=False,
    )


def _capabilities() -> DomainCapabilityRequirements:
    return DomainCapabilityRequirements(
        verifier_capabilities=("physics.dimension",),
        tool_capabilities=("physics.kernel",),
    )


def _descriptor(**overrides: Any) -> DomainDescriptorV1:
    fields: dict[str, Any] = {
        "domain_id": "engineering.mechanics",
        "revision": 1,
        "display_name": "mechanics",
        "lifecycle": DomainLifecycleState.PILOT,
        "capabilities": _capabilities(),
        "provenance": _provenance(),
    }
    fields.update(overrides)
    return DomainDescriptorV1(**fields)


def _package(**overrides: Any) -> bytes:
    payload: dict[str, Any] = {
        "domain_id": "engineering.mechanics",
        "revision": 1,
        "display_name": "mechanics",
        "lifecycle": "pilot",
        "capabilities": {
            "verifier_capabilities": ["physics.dimension"],
            "tool_capabilities": ["physics.kernel"],
        },
        "provenance": {
            "source": "sprint-22a test fixture",
            "revision": "none",
            "licence": "internal",
            "redistributable": False,
        },
    }
    payload.update(overrides)
    return json.dumps(payload).encode()


# ----------------------------------------------------------------- the grammar


@pytest.mark.parametrize(
    "identifier",
    ["physics", "engineering.mechanics", "science.chemistry", "a", "a1.b_2.c3"],
)
def test_the_grammar_admits_a_dotted_lowercase_namespace(identifier: str) -> None:
    assert _descriptor(domain_id=identifier).domain_id == identifier


@pytest.mark.parametrize(
    "identifier",
    [
        "Mechanics",  # an uppercase member is a different key that reads as the same domain
        "1mechanics",  # a leading digit
        "engineering.",  # a trailing separator, so an empty segment
        ".engineering",  # a leading separator
        "engineering..mechanics",  # an empty middle segment
        "engineering mechanics",  # whitespace
        "engineering-mechanics",  # a separator the grammar does not define
        "engineering/mechanics",  # a path, which is what a package would like it to be
    ],
)
def test_the_grammar_refuses_everything_it_does_not_define(identifier: str) -> None:
    with pytest.raises(ValidationError):
        _descriptor(domain_id=identifier)


def test_an_identifier_longer_than_the_ceiling_is_refused() -> None:
    """A key space with no length bound is a payload channel, not an identity."""
    at_the_ceiling = "a" * DOMAIN_ID_MAX_LENGTH
    assert _descriptor(domain_id=at_the_ceiling).domain_id == at_the_ceiling
    with pytest.raises(ValidationError):
        _descriptor(domain_id="a" * (DOMAIN_ID_MAX_LENGTH + 1))


def test_the_grammar_binds_parents_and_related_ids_too() -> None:
    """A malformed id reached through a link is still a malformed id."""
    with pytest.raises(ValidationError):
        _descriptor(parent_domain_id="Engineering")
    with pytest.raises(ValidationError):
        _descriptor(related_domain_ids=("Physics",))


# ------------------------------------------------------- closed-world validation


def test_an_unknown_field_is_a_refusal_not_a_warning() -> None:
    with pytest.raises(ValidationError):
        _descriptor(controller_branch="mechanics")


def test_a_domain_cannot_be_its_own_parent_or_its_own_relation() -> None:
    with pytest.raises(ValidationError):
        _descriptor(parent_domain_id="engineering.mechanics")
    with pytest.raises(ValidationError):
        _descriptor(related_domain_ids=("engineering.mechanics",))


def test_related_ids_problem_types_and_concept_ids_are_unique() -> None:
    with pytest.raises(ValidationError):
        _descriptor(related_domain_ids=("physics", "physics"))
    with pytest.raises(ValidationError):
        _descriptor(problem_types=("statics_equilibrium", "statics_equilibrium"))
    with pytest.raises(ValidationError):
        _descriptor(
            concepts=(
                DomainConcept(concept_id="rigid_body", description="one"),
                DomainConcept(concept_id="rigid_body", description="another"),
            )
        )


def test_problem_type_uniqueness_is_case_insensitive() -> None:
    """Two spellings of one problem type are one problem type with a resolution ambiguity."""
    with pytest.raises(ValidationError):
        _descriptor(problem_types=("statics_equilibrium", "Statics_Equilibrium"))


def _concept(*shared_with: str) -> DomainConcept:
    return DomainConcept(
        concept_id="rigid_body",
        description="a body whose deformation is neglected",
        shared_with=tuple(shared_with),
    )


def test_a_shared_concept_must_resolve_inside_the_declared_world() -> None:
    declared = _descriptor(related_domain_ids=("physics",), concepts=(_concept("physics"),))
    assert declared.concepts[0].shared_with == ("physics",)

    with pytest.raises(ValidationError):
        _descriptor(concepts=(_concept("physics"),))
    with pytest.raises(ValidationError):
        _descriptor(concepts=(_concept("engineering.mechanics"),))


def test_a_concept_edited_under_its_old_seal_is_refused() -> None:
    """The sharing field cannot be edited in flight: the stale hash is caught by the base."""
    with pytest.raises(ValidationError):
        DomainConcept.model_validate(_concept().model_dump() | {"shared_with": ("physics",)})


def test_a_parent_also_counts_as_the_declared_world() -> None:
    concept = DomainConcept(
        concept_id="rigid_body", description="a body", shared_with=("engineering",)
    )
    assert _descriptor(parent_domain_id="engineering", concepts=(concept,)).parent_domain_id


def test_a_transfer_link_targets_a_declared_domain_and_never_itself() -> None:
    link = DomainTransferLink(target_domain_id="physics", direction="from")
    assert _descriptor(related_domain_ids=("physics",), transfer_links=(link,)).transfer_links
    with pytest.raises(ValidationError):
        _descriptor(transfer_links=(link,))
    with pytest.raises(ValidationError):
        _descriptor(
            transfer_links=(
                DomainTransferLink(target_domain_id="engineering.mechanics", direction="from"),
            )
        )


def test_a_transfer_link_carries_no_evidence_until_one_exists() -> None:
    """Declaring a link authorises nothing: it pre-registers a place for a measurement."""
    link = DomainTransferLink(target_domain_id="physics", direction="from")
    assert link.evidence_hash is None


def test_a_domain_needs_at_least_one_verifier_and_one_tool() -> None:
    """A domain that names no verifier cannot be judged, which is the honesty floor."""
    with pytest.raises(ValidationError):
        DomainCapabilityRequirements(verifier_capabilities=(), tool_capabilities=("t",))
    with pytest.raises(ValidationError):
        DomainCapabilityRequirements(verifier_capabilities=("v",), tool_capabilities=())


def test_revision_starts_at_one_and_the_schema_version_is_bounded() -> None:
    assert _descriptor().schema_version == SCHEMA_VERSION
    with pytest.raises(ValidationError):
        _descriptor(revision=0)
    with pytest.raises(ValidationError):
        _descriptor(schema_version=SCHEMA_VERSION + 1)


def test_identity_is_domain_id_plus_revision() -> None:
    """A changed domain is a new revision with a new hash; the old one stays intact."""
    first = _descriptor()
    second = _descriptor(revision=2)
    assert first.content_hash != second.content_hash
    assert _descriptor().content_hash == first.content_hash


# -------------------------------------------------------- the package boundary


def test_a_valid_package_becomes_a_contract() -> None:
    descriptor = validate_domain_package(_package())
    assert descriptor.domain_id == "engineering.mechanics"
    assert descriptor.lifecycle is DomainLifecycleState.PILOT


def test_the_size_ceiling_is_checked_before_anything_is_parsed() -> None:
    """Refused on length, so a package too large to trust is never handed to a parser."""
    with pytest.raises(DomainPackageError) as refusal:
        validate_domain_package(b" " * (DOMAIN_PACKAGE_MAX_BYTES + 1))
    assert "ceiling" in refusal.value.diagnostics[0]


@pytest.mark.parametrize(
    ("case", "payload"),
    [
        ("not_json", b"\xff\xfe not a descriptor"),
        ("not_an_object", b'["a", "list"]'),
        ("empty", b""),
    ],
)
def test_bytes_that_are_not_a_descriptor_object_are_refused(case: str, payload: bytes) -> None:
    with pytest.raises(DomainPackageError) as refusal:
        validate_domain_package(payload)
    assert refusal.value.diagnostics, case


def test_a_contract_violation_is_reported_as_diagnostics_not_a_stack_trace() -> None:
    """Every pydantic finding is flattened, so a rejected package is a report."""
    with pytest.raises(DomainPackageError) as refusal:
        validate_domain_package(_package(domain_id="Mechanics!", revision=0))
    diagnostics = refusal.value.diagnostics
    assert len(diagnostics) >= 1
    assert all(": " in item for item in diagnostics)
    assert "revision" in "; ".join(diagnostics)


def test_the_six_sealed_refusal_cases_are_all_still_refused() -> None:
    """The survey sealed six refusals; a boundary that stops refusing one is the finding."""
    sealed = _survey()["package_boundary"]
    assert sealed["every_refusal_refused"] is True
    for case, diagnostics in sealed["refusals"].items():
        assert diagnostics, case
        assert not diagnostics[0].startswith("ACCEPTED"), case


# ------------------------------------------------------- the released adapter


def test_the_released_ids_are_the_enum_values_verbatim() -> None:
    """So every stored record that says "coding" today resolves without a migration."""
    assert {kind: kind.value for kind in DomainKind} == RELEASED_DOMAIN_IDS
    assert len(RELEASED_DOMAIN_IDS) == 4


def test_the_four_released_domains_reproduce_their_sealed_content_hashes() -> None:
    """The backward-compatibility contract, read out of the sealed record rather than typed.

    A wave that changes any hash here has changed released behaviour, and this assertion
    names the domain it changed.
    """
    sealed = _survey()["released_domains_as_descriptors"]["descriptors"]
    derived = {item.domain_id: item for item in released_domain_descriptors()}

    assert set(derived) == set(sealed)
    for domain_id, expected in sealed.items():
        assert derived[domain_id].content_hash == expected["content_hash"], domain_id
        assert derived[domain_id].revision == expected["revision"], domain_id
        assert list(derived[domain_id].problem_types) == expected["problem_types"], domain_id


def test_the_adapter_is_derived_from_the_registry_rather_than_transcribed() -> None:
    """Every capability a descriptor claims is one the released registry resolves."""
    from cognitive_os.domains import registry

    for descriptor in released_domain_descriptors():
        entries = [
            entry for entry in registry.entries() if entry.domain.value == descriptor.domain_id
        ]
        assert entries, descriptor.domain_id
        assert set(descriptor.problem_types) == {entry.problem_type for entry in entries}
        assert set(descriptor.capabilities.verifier_capabilities) == {
            name for entry in entries for name in entry.required_verifiers
        }
        assert set(descriptor.capabilities.tool_capabilities) == {
            name for entry in entries for name in entry.required_tools
        }


def test_every_released_domain_is_active_and_none_is_a_pilot() -> None:
    assert all(
        item.lifecycle is DomainLifecycleState.ACTIVE for item in released_domain_descriptors()
    )


def test_the_derivation_is_deterministic_across_calls() -> None:
    """Sorted everywhere, so the compat contract is a fact about the registry, not a run."""
    first = [item.content_hash for item in released_domain_descriptors()]
    assert first == [item.content_hash for item in released_domain_descriptors()]


def test_a_released_descriptor_cannot_be_uploaded_as_a_package() -> None:
    """W0-F2. The four released domains are `active`, and `active` is not a claimable state.

    So the descriptor of a released domain, serialised and offered at the door a hostile
    package knocks on, is refused for the reason that makes impersonation expensive: the
    lifecycle a package claims is the one thing it cannot bring with it.
    """
    for descriptor in released_domain_descriptors():
        payload = descriptor.model_dump_json(exclude={"content_hash"}).encode()
        with pytest.raises(DomainPackageError) as refusal:
            validate_domain_package(payload)
        assert "lifecycle" in refusal.value.diagnostics[0], descriptor.domain_id


def test_only_a_pilot_lifecycle_may_be_claimed_by_a_package() -> None:
    """W0-F2: the state the module documented as unclaimable is now the state it refuses."""
    assert validate_domain_package(_package()).lifecycle is DomainLifecycleState.PILOT
    for state in DomainLifecycleState:
        if state is DomainLifecycleState.PILOT:
            continue
        with pytest.raises(DomainPackageError) as refusal:
            validate_domain_package(_package(lifecycle=state.value))
        assert "governed promotion" in refusal.value.diagnostics[0], state


def test_the_adapter_still_builds_the_active_released_four() -> None:
    """The rule costs the released domains nothing: the adapter builds contracts, not packages."""
    assert {item.lifecycle for item in released_domain_descriptors()} == {
        DomainLifecycleState.ACTIVE
    }


def test_a_concept_may_not_name_the_same_domain_twice() -> None:
    """W0-F4. Every other list in the contract is deduplicated; a membership counted twice
    is a cross-domain view that disagrees with itself about how many domains expose an item."""
    with pytest.raises(ValidationError):
        _descriptor(related_domain_ids=("physics",), concepts=(_concept("physics", "physics"),))
