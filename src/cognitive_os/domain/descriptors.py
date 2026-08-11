"""Versioned domain descriptors — Sprint 22A's primitive, grounded before its first wave.

Sprint 21 closed its learning gate on four subjects that live in the code as an enum:
`DomainKind` has four members, and the domain survey measures eight modules keying tables off
them. That shape was the right price for a pilot and is exactly what Sprint 22A exists to
dissolve: *"stable string domain IDs and versioned descriptors … both new domains register
without changing the core controller or storage schema"*. The unit of that change is the
descriptor, and this module defines it — the contract, its fail-closed package boundary, and
the backward-compatible adapter that expresses the four released domains as descriptors
derived from the released registry rather than authored beside it.

Three rules, each the codification of a Sprint 21 lesson:

**A domain is data, and its identity is a string with a grammar.** No enum member, no core
branch, no controller edit. A new domain is a package that validates or a package that is
refused with a diagnosis; there is no third path, because the third path is where an
unbounded capability would live.

**A package is untrusted until it validates, and validation is closed-world.** The contract
base forbids unknown fields, every cross-reference must resolve inside the package's own
declared world (parents, related domains, shared concepts), and the loader takes bytes with a
size ceiling rather than objects — a package too large to read is refused before it is
parsed. W1-F2's lesson generalises here: a collision invisible to detectors is caught by
reading the closest released thing in full, so descriptor identity is `domain_id` *plus*
`revision`, and re-registering either is a refusal, never a replace (the exact failure D7's
W1 found in the template registry, where a duplicate key silently replaced its predecessor).

**The four released domains are derived, not transcribed.** `released_domain_descriptors()`
builds their descriptors out of the released problem-type registry — capabilities, tools,
skills, strategies and problem types come from `domains.registry`'s own tables — so the
adapter cannot drift from the code it describes. A transcription would be a second copy with
one more place to be wrong, which is the duplication lesson every D-sprint paid for once.

What this module deliberately does not do: it registers nothing at runtime, routes nothing,
and changes no behaviour of the four released domains. The runtime registry seam, the two
pilot packages (mechanics/engineering and chemistry) and the multi-domain views are 22A wave
work under 22A's own plan; a groundwork module that also wired itself in would be the sprint
pre-empting its own gate.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum

from pydantic import Field, model_validator

from cognitive_os.domain.common import NonEmptyStr
from cognitive_os.domain.domains import DomainKind, ProvenanceRef
from cognitive_os.domain.experience import HashedExperienceContract

#: Stable string identity: lowercase, dot-separated segments, no leading digit. The grammar
#: is the whole anti-silo policy in one line — nothing about it names a science.
DOMAIN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
DOMAIN_ID_MAX_LENGTH = 64

#: A package larger than this is refused before parsing. Generous against every real
#: descriptor (the released four serialise under 4 KiB each) and small against abuse.
DOMAIN_PACKAGE_MAX_BYTES = 65_536

SCHEMA_VERSION = 1


class DomainLifecycleState(StrEnum):
    """Where a domain stands in its governed life. `PILOT` is the only state a fresh
    package may claim; promotion beyond it is a governance decision with evidence,
    the same shape Sprint 21 used for learned components."""

    PILOT = "pilot"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class DomainConcept(HashedExperienceContract):
    """One concept a domain contributes, with the domains it is shared into.

    Multi-domain membership lives here and only here: a shared concept names the other
    domains that expose it, so a knowledge item can be stored once and viewed from several
    domains without any domain owning a copy.
    """

    concept_id: NonEmptyStr
    description: NonEmptyStr
    shared_with: tuple[NonEmptyStr, ...] = ()


class DomainCapabilityRequirements(HashedExperienceContract):
    """What a domain's tasks need to run and be judged: named capabilities, not code.

    Verifier and tool names follow the released `<domain>.<capability>` convention. The
    descriptor states requirements; whether an installation satisfies them is the verifier
    registry's question at resolution time, exactly as the released factory answers it.
    """

    verifier_capabilities: tuple[NonEmptyStr, ...] = Field(min_length=1)
    tool_capabilities: tuple[NonEmptyStr, ...] = Field(min_length=1)
    skills: tuple[NonEmptyStr, ...] = ()
    strategies: tuple[NonEmptyStr, ...] = ()
    units: tuple[NonEmptyStr, ...] = ()


class DomainCorpusRef(HashedExperienceContract):
    """A corpus a domain claims, by name and content hash, never by content."""

    corpus_id: NonEmptyStr
    content_hash: NonEmptyStr
    role: NonEmptyStr


class DomainTransferLink(HashedExperienceContract):
    """A declared transfer relationship to another domain, as a claim to be measured.

    Declaring a link authorises nothing: Sprint 21's transfer record is the model — the
    declaration names the pair and the direction so that a later measurement has a
    pre-registered place to land, and `evidence_hash` is empty until one exists.
    """

    target_domain_id: NonEmptyStr
    direction: NonEmptyStr
    evidence_hash: NonEmptyStr | None = None


class DomainDescriptorV1(HashedExperienceContract):
    """One domain, one revision, everything the platform may know about it.

    Identity is (`domain_id`, `revision`) and both are immutable: a changed domain is a new
    revision with the old one intact, the supersession discipline every Sprint 21 artifact
    kept. `problem_types` is how the descriptor stays honest about scope — a domain with no
    problem types is a namespace, and a registry may accept it as one, but it cannot claim a
    solver surface it does not name.
    """

    schema_version: int = Field(default=SCHEMA_VERSION, ge=1, le=SCHEMA_VERSION)
    domain_id: NonEmptyStr
    revision: int = Field(ge=1)
    display_name: NonEmptyStr
    lifecycle: DomainLifecycleState
    parent_domain_id: NonEmptyStr | None = None
    related_domain_ids: tuple[NonEmptyStr, ...] = ()
    problem_types: tuple[NonEmptyStr, ...] = ()
    concepts: tuple[DomainConcept, ...] = ()
    capabilities: DomainCapabilityRequirements
    corpora: tuple[DomainCorpusRef, ...] = ()
    transfer_links: tuple[DomainTransferLink, ...] = ()
    provenance: ProvenanceRef

    @model_validator(mode="after")
    def the_descriptor_is_closed_and_acyclic_at_depth_one(self) -> DomainDescriptorV1:
        for identifier in (
            self.domain_id,
            *((self.parent_domain_id,) if self.parent_domain_id else ()),
            *self.related_domain_ids,
        ):
            if len(identifier) > DOMAIN_ID_MAX_LENGTH or not DOMAIN_ID_PATTERN.fullmatch(
                identifier
            ):
                raise ValueError(
                    f"domain id {identifier!r} does not match the grammar "
                    f"{DOMAIN_ID_PATTERN.pattern!r} within {DOMAIN_ID_MAX_LENGTH} characters"
                )
        if self.parent_domain_id == self.domain_id:
            raise ValueError("a domain cannot be its own parent")
        if self.domain_id in self.related_domain_ids:
            raise ValueError("a domain cannot be related to itself")
        if len(set(self.related_domain_ids)) != len(self.related_domain_ids):
            raise ValueError("related domains must be unique")
        if len({item.lower() for item in self.problem_types}) != len(self.problem_types):
            raise ValueError("problem types must be unique")
        concept_ids = [concept.concept_id for concept in self.concepts]
        if len(set(concept_ids)) != len(concept_ids):
            raise ValueError("concept ids must be unique within a descriptor")
        for concept in self.concepts:
            if len(set(concept.shared_with)) != len(concept.shared_with):
                raise ValueError(
                    f"concept {concept.concept_id!r} names a domain twice in `shared_with`; a "
                    "membership counted twice is a cross-domain view that disagrees with itself"
                )
        known = {self.domain_id, *(self.related_domain_ids)}
        if self.parent_domain_id:
            known.add(self.parent_domain_id)
        for concept in self.concepts:
            for shared in concept.shared_with:
                if shared == self.domain_id:
                    raise ValueError(
                        f"concept {concept.concept_id!r} shares itself with its own domain"
                    )
                if shared not in known:
                    raise ValueError(
                        f"concept {concept.concept_id!r} is shared with {shared!r}, which "
                        "the descriptor does not declare as parent or related; a shared "
                        "concept must resolve inside the package's own declared world"
                    )
        for link in self.transfer_links:
            if link.target_domain_id == self.domain_id:
                raise ValueError("a transfer link cannot target its own domain")
            if link.target_domain_id not in known:
                raise ValueError(
                    f"transfer link targets {link.target_domain_id!r}, which the "
                    "descriptor does not declare as parent or related"
                )
        return self


class DomainPackageError(ValueError):
    """An untrusted package was refused. `diagnostics` says why, one finding per line,
    so a rejected package is a report rather than a stack trace."""

    def __init__(self, diagnostics: tuple[str, ...]) -> None:
        super().__init__("; ".join(diagnostics))
        self.diagnostics = diagnostics


def validate_domain_package(payload: bytes) -> DomainDescriptorV1:
    """Parse and validate one untrusted descriptor package, fail-closed.

    Bytes in, contract or refusal out. Size is checked before parsing, JSON before
    validation, and every pydantic finding is flattened into the diagnostics — the
    closed-world field policy (`extra="forbid"`) comes from the contract base, so an
    unknown field is a refusal, not a warning.

    **A package may claim `pilot` and nothing else.** Every other lifecycle state is reached
    by a governed promotion with evidence behind it, so a package that arrives already
    claiming `active` is claiming the promotion as well as the domain. The released four are
    `active` and are built as contracts by the adapter, never parsed from a package, so the
    rule costs them nothing.
    """
    if len(payload) > DOMAIN_PACKAGE_MAX_BYTES:
        raise DomainPackageError(
            (
                f"package is {len(payload)} bytes against a ceiling of "
                f"{DOMAIN_PACKAGE_MAX_BYTES}; a descriptor is metadata, not a corpus",
            )
        )
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DomainPackageError((f"package is not UTF-8 JSON: {error}",)) from error
    if not isinstance(raw, dict):
        raise DomainPackageError(("a descriptor package is a JSON object",))
    try:
        descriptor = DomainDescriptorV1.model_validate(raw)
    except ValueError as error:
        findings = getattr(error, "errors", None)
        if callable(findings):
            diagnostics = tuple(
                f"{'.'.join(str(part) for part in item['loc']) or '<root>'}: {item['msg']}"
                for item in findings()
            )
        else:
            diagnostics = (str(error),)
        raise DomainPackageError(diagnostics) from error
    if descriptor.lifecycle is not DomainLifecycleState.PILOT:
        raise DomainPackageError(
            (
                f"lifecycle: a package may claim {DomainLifecycleState.PILOT.value!r} and "
                f"nothing else; {descriptor.lifecycle.value!r} is reached by a governed "
                "promotion with evidence, not by declaring it in the package",
            )
        )
    return descriptor


#: The released enum member each derived descriptor stands for, and the id it takes. The
#: string ids are the enum values verbatim, so every stored record that says "coding" today
#: resolves to the descriptor of the same name without a migration.
RELEASED_DOMAIN_IDS: dict[DomainKind, str] = {kind: kind.value for kind in DomainKind}


def released_domain_descriptors() -> tuple[DomainDescriptorV1, ...]:
    """The four released domains as descriptors, derived from the released registry.

    Derived, not transcribed: problem types, verifier capabilities, tools, skills and
    strategies are read out of `domains.registry`'s resolved entries, so this adapter is
    exactly as correct as the code it describes and cannot drift from it. Lifecycle is
    `ACTIVE` because these four are the released surface; provenance names the release
    that proved them.
    """
    from cognitive_os.domains import registry

    descriptors = []
    for kind in DomainKind:
        entries = [entry for entry in registry.entries() if entry.domain is kind]
        if not entries:
            raise DomainPackageError(
                (f"released domain {kind.value!r} resolves no registry entries",)
            )
        verifiers = sorted({name for entry in entries for name in entry.required_verifiers})
        tools = sorted({name for entry in entries for name in entry.required_tools})
        skills = sorted({name for entry in entries for name in entry.skills})
        strategies = sorted({name for entry in entries for name in entry.strategies})
        descriptors.append(
            DomainDescriptorV1(
                domain_id=RELEASED_DOMAIN_IDS[kind],
                revision=1,
                display_name=kind.value,
                lifecycle=DomainLifecycleState.ACTIVE,
                problem_types=tuple(sorted(entry.problem_type for entry in entries)),
                capabilities=DomainCapabilityRequirements(
                    verifier_capabilities=tuple(verifiers),
                    tool_capabilities=tuple(tools),
                    skills=tuple(skills),
                    strategies=tuple(strategies),
                ),
                provenance=ProvenanceRef(
                    source="cognitive-os released problem-type registry",
                    revision="sprint-21-learning-baseline",
                    licence="internal",
                    redistributable=False,
                ),
            )
        )
    return tuple(descriptors)
