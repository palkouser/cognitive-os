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
from collections.abc import Iterable
from dataclasses import dataclass
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

#: **The seam** (Sprint 22A W1, §3.1). The four released domains' capability requirements, as
#: descriptor data keyed by string id rather than by enum member. This is where the
#: `_DOMAIN_METADATA` and `_REQUIRED_TOOLS` tables lived until W1 moved them: the registry now
#: reads them from here through `released_domain_descriptors()`, so a domain's capabilities are
#: data about a domain rather than a branch on a Python enum.
#:
#: Moving a released table is only safe if the move is provably lossless, and it is: the four
#: derived descriptors still hash to the values Sprint 22A's groundwork sealed before anything
#: moved, and the registry's own snapshot hash is unchanged. The comments below are the ones
#: the registry tables carried, kept with the data they explain rather than left behind.
RELEASED_DOMAIN_CAPABILITIES: dict[str, DomainCapabilityRequirements] = {
    DomainKind.MATHEMATICS.value: DomainCapabilityRequirements(
        verifier_capabilities=("mathematics.exact_arithmetic", "mathematics.numeric"),
        tool_capabilities=("mathematics.kernel",),
        skills=("exact-arithmetic-decomposition", "cross-domain-result-review"),
        strategies=("decompose-compute-verify", "two-independent-methods"),
    ),
    DomainKind.PHYSICS.value: DomainCapabilityRequirements(
        verifier_capabilities=("physics.dimension", "physics.quantity"),
        tool_capabilities=("physics.kernel",),
        skills=("unit-aware-physics-calculation", "dimensional-analysis-review"),
        strategies=("units-first-physics-modelling", "assumption-mismatch-detection"),
    ),
    DomainKind.LOGIC.value: DomainCapabilityRequirements(
        verifier_capabilities=("logic.truth_table", "logic.counterexample"),
        tool_capabilities=("logic.kernel",),
        skills=("logic-formalization", "constraint-solving"),
        strategies=("hypothesis-constraint-solver-counterexample", "two-independent-methods"),
    ),
    DomainKind.CODING.value: DomainCapabilityRequirements(
        # The check capabilities name what the in-process checker actually does: compare
        # the candidate against the case's golden reference, and confirm that every
        # declared edit landed. Deliberately NOT `coding.pytest` — that capability means
        # sandboxed pytest execution everywhere else in the system
        # (`verification/coding/commands.py`), and a check that never ran pytest must not
        # borrow its name. See ADR 0085.
        verifier_capabilities=("coding.golden_equality", "coding.required_checks"),
        # Coding declares two tools: `coding.pytest` is what a real repair of these tasks
        # needs and what the permitted skills match their tool precondition against, while
        # `coding.kernel` is the deterministic in-process solve the Sprint 21C.1 baseline
        # actually performs and cites.
        tool_capabilities=("coding.pytest", "coding.kernel"),
        # Two permitted skills (the python-repair and focused-tests families) keep
        # selection tight and the ADR 0084 statistic-binding story uniform.
        skills=("verification-driven-python-repair", "focused-test-execution"),
        # Registered strategies only — both already declare exactly these two skills.
        strategies=("python-bug-fix", "verification-driven-repair"),
    ),
}


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


class ConceptExposure(StrEnum):
    """How a domain comes to see a concept: it declared it, or another domain shared it in."""

    OWNED = "owned"
    SHARED = "shared"


@dataclass(frozen=True, slots=True)
class ConceptView:
    """One concept as one domain sees it, with the domain that actually holds it named.

    The view carries the concept itself rather than a copy of its fields, so both sides of
    a shared concept compare equal and hash identically. That is the whole cross-domain
    claim in one line: two governed views, one stored item.
    """

    concept: DomainConcept
    owner_domain_id: str
    exposure: ConceptExposure

    @property
    def concept_id(self) -> str:
        return self.concept.concept_id

    @property
    def content_hash(self) -> str:
        return self.concept.content_hash


def concept_owners(descriptors: Iterable[DomainDescriptorV1]) -> dict[str, str]:
    """`concept_id -> owning domain id`, refusing any concept two domains both claim.

    A concept with two owners is a concept stored twice, which is the silo this sprint
    exists to prevent. It is refused here rather than resolved by a rule, because every
    resolution rule ("first wins", "highest revision wins") silently picks a winner and the
    caller never learns the two descriptions disagreed.
    """
    owners: dict[str, str] = {}
    for descriptor in descriptors:
        for concept in descriptor.concepts:
            existing = owners.get(concept.concept_id)
            if existing is not None and existing != descriptor.domain_id:
                raise DomainPackageError(
                    (
                        f"concept {concept.concept_id!r} is declared by both {existing!r} and "
                        f"{descriptor.domain_id!r}; a cross-domain concept is stored once by "
                        "one owner and shared, never declared twice",
                    )
                )
            owners[concept.concept_id] = descriptor.domain_id
    return owners


def validate_shared_concepts(descriptors: Iterable[DomainDescriptorV1]) -> None:
    """Refuse a share into a domain that never declared it back (Sprint 22A §3.5).

    A single package's validator can only check that a share resolves inside *its own*
    declared world, which is why a package may name any related domain it likes. Whether
    that domain agrees is a question about the whole catalogue, and it is asked here.

    Two rules, and the asymmetry between them is deliberate:

    - the target must be a domain the catalogue actually knows. A concept shared into a
      domain that exists nowhere is stored once and exposed to nobody, which is a silo with
      extra steps;
    - a **pilot** target must declare the sharing domain as parent or related. Two pilots
      cannot enrol each other unilaterally. A **released** domain is open by construction:
      the released four are the shared substrate every pilot builds on, they are derived
      from the problem-type registry rather than authored, and there is nowhere for them to
      declare anything back. Requiring reciprocity of them would forbid every share a pilot
      could usefully make.
    """
    catalogue = tuple(descriptors)
    known = {item.domain_id: item for item in catalogue}
    for descriptor in catalogue:
        for concept in descriptor.concepts:
            for target in concept.shared_with:
                other = known.get(target)
                if other is None:
                    raise DomainPackageError(
                        (
                            f"concept {concept.concept_id!r} is shared into {target!r}, which "
                            "no registered or released domain answers to; a view into a "
                            "domain that does not exist is not a view",
                        )
                    )
                if other.lifecycle is DomainLifecycleState.PILOT and descriptor.domain_id not in {
                    other.parent_domain_id,
                    *other.related_domain_ids,
                }:
                    raise DomainPackageError(
                        (
                            f"concept {concept.concept_id!r} is shared into {target!r}, which "
                            f"does not declare {descriptor.domain_id!r} as parent or related; "
                            "a pilot does not enrol another pilot's view without its consent",
                        )
                    )


def concept_views(
    descriptors: Iterable[DomainDescriptorV1],
) -> dict[str, tuple[ConceptView, ...]]:
    """Every domain's governed view of the concepts it can see, owned and shared alike.

    This is the exit criterion's "stored once, exposed through multiple governed views" as
    a function: a shared concept appears in the owner's view as `OWNED` and in each target's
    view as `SHARED`, and it is the *same* `DomainConcept` in both — one item, two views.
    A domain that is named only as a share target still gets a view, which is what makes
    the released `physics` able to see a pilot's concepts without knowing the pilot exists.
    """
    catalogue = tuple(descriptors)
    concept_owners(catalogue)
    validate_shared_concepts(catalogue)
    views: dict[str, list[ConceptView]] = {item.domain_id: [] for item in catalogue}
    for descriptor in catalogue:
        for concept in descriptor.concepts:
            views[descriptor.domain_id].append(
                ConceptView(concept, descriptor.domain_id, ConceptExposure.OWNED)
            )
            for target in concept.shared_with:
                views.setdefault(target, []).append(
                    ConceptView(concept, descriptor.domain_id, ConceptExposure.SHARED)
                )
    return {
        domain_id: tuple(sorted(items, key=lambda view: view.concept_id))
        for domain_id, items in sorted(views.items())
    }
