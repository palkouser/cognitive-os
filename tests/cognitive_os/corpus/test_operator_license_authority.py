"""W1-D2: the program advises on a licence; a person decides it.

The Corpus Factory used to decide licence status from an allowlist of four software
identifiers, and write the outcome into a `LicenseDeclaration` whose `declared_by` named an
operator who had decided nothing. The field said a human had declared it; the list had.

That is a design error rather than a short list. Classifying material and authorising its
use is a legal determination, and the legal responsibility for it is the operator's — so the
determination has to be theirs. A program may read a licence, recognise it if it can, and
say what it thinks.

These pin the asymmetry that follows, which is the whole of the design:

**The program may refuse on its own. It may never permit on its own.** No clearance and an
unrecognised licence still quarantines, exactly as before; a clearance is the only thing that
makes material usable, and no configuration file can substitute for one.

And they pin the two ways the old shape could come back: a `*_action` setting that nothing
reads, and a `status` on a declaration that no named person stands behind.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.corpus.factory import (
    RECOGNISED_INTERNAL_LICENSES,
    RECOGNISED_PERMISSIVE_LICENSES,
    CorpusFactory,
)
from cognitive_os.corpus.fixtures import FixtureArtifactStore, build_corpus_fixture
from cognitive_os.corpus.repository import InMemoryCorpusRepository
from cognitive_os.domain.corpus import (
    CorpusLicenseStatus,
    CorpusRouteStatus,
    CorpusUsageRight,
    OperatorLicenseClearance,
)

#: A real open content licence. The platform has never recognised it and does not need to.
CONTENT_LICENCE = "CC-BY-4.0"
DECIDED_AT = datetime(2026, 8, 15, tzinfo=UTC)
HASH = "d" * 64


def _clearance(
    *,
    identifier: str = CONTENT_LICENCE,
    status: CorpusLicenseStatus = CorpusLicenseStatus.APPROVED,
    uses: tuple[CorpusUsageRight, ...] = (
        CorpusUsageRight.INTERNAL_USE,
        CorpusUsageRight.DERIVATIVE_WORK,
    ),
) -> OperatorLicenseClearance:
    return OperatorLicenseClearance(
        identifier=identifier,
        status=status,
        permitted_uses=uses,
        cleared_by="a named person, not a role",
        cleared_at=DECIDED_AT,
        evidence_hash=HASH,
        source_content_hash="e" * 64,
    )


def _ingest(*, clearances: tuple[OperatorLicenseClearance, ...], identifier: str = CONTENT_LICENCE):
    request, source = build_corpus_fixture("document")
    request = request.model_copy(
        update={
            "content_hash": "",
            "license_identifiers": (identifier,),
            "license_clearances": clearances,
        }
    )
    return asyncio.run(
        CorpusFactory(InMemoryCorpusRepository(), FixtureArtifactStore()).ingest(request, source)
    )


def _routes(result) -> set[CorpusRouteStatus]:
    return {decision.status for decision in result.route_decisions}


# --- the asymmetry -------------------------------------------------------------


def test_without_a_clearance_an_unrecognised_licence_still_quarantines() -> None:
    """Fail-closed is unchanged. The ruling removed an authority, not a safeguard."""
    result = _ingest(clearances=())
    licence = result.licenses[0]
    assert licence.status is CorpusLicenseStatus.UNKNOWN
    assert licence.advisory_status is CorpusLicenseStatus.UNKNOWN
    assert licence.operator_decided is False
    assert licence.decided_by is None
    assert _routes(result) == {CorpusRouteStatus.QUARANTINED}


def test_with_a_clearance_the_operators_determination_governs() -> None:
    result = _ingest(clearances=(_clearance(),))
    licence = result.licenses[0]
    assert licence.status is CorpusLicenseStatus.APPROVED
    assert licence.operator_decided is True
    assert licence.decided_by == "a named person, not a role"
    assert licence.decided_at == DECIDED_AT
    assert licence.clearance_evidence_hash == HASH
    assert CorpusRouteStatus.QUARANTINED not in _routes(result)


def test_the_advice_is_kept_beside_the_decision_and_the_disagreement_is_visible() -> None:
    """The platform said "I do not recognise this". A person said "use it". Both are facts."""
    licence = _ingest(clearances=(_clearance(),)).licenses[0]
    assert licence.advisory_status is CorpusLicenseStatus.UNKNOWN
    assert licence.status is CorpusLicenseStatus.APPROVED
    assert licence.operator_departed_from_the_advice is True


def test_the_declaration_names_whoever_actually_decided() -> None:
    """`declared_by` used to name a requester while an allowlist decided. Now it is true."""
    cleared = _ingest(clearances=(_clearance(),))
    assert cleared.source_manifest.license_declarations[0].declared_by == (
        "a named person, not a role"
    )
    uncleared = _ingest(clearances=())
    assert uncleared.source_manifest.license_declarations[0].declared_by != (
        "a named person, not a role"
    )


def test_a_clearance_for_a_different_licence_does_not_clear_this_one() -> None:
    result = _ingest(clearances=(_clearance(identifier="CC-BY-SA-4.0"),))
    assert result.licenses[0].status is CorpusLicenseStatus.UNKNOWN
    assert _routes(result) == {CorpusRouteStatus.QUARANTINED}


def test_an_operator_may_also_decide_a_licence_is_restricted() -> None:
    """The authority runs both ways: a person may refuse what the platform would allow."""
    result = _ingest(
        clearances=(_clearance(identifier="Apache-2.0", status=CorpusLicenseStatus.RESTRICTED),),
        identifier="Apache-2.0",
    )
    licence = result.licenses[0]
    assert licence.advisory_status is CorpusLicenseStatus.APPROVED
    assert licence.status is CorpusLicenseStatus.RESTRICTED
    assert _routes(result) == {CorpusRouteStatus.DENIED}


# --- the contract's own refusals -----------------------------------------------


def test_a_clearance_cannot_hold_an_undecided_status() -> None:
    """ "Unknown" is the absence of a decision, and is expressed by having no clearance."""
    for status in (CorpusLicenseStatus.UNKNOWN, CorpusLicenseStatus.CONFLICTING):
        with pytest.raises(ValidationError):
            _clearance(status=status)


def test_a_clearance_covers_bytes_so_it_cannot_drift_onto_another_edition() -> None:
    clearance = _clearance()
    assert len(clearance.source_content_hash) == 64
    assert len(clearance.evidence_hash) == 64
    with pytest.raises(ValidationError):
        OperatorLicenseClearance(
            identifier=CONTENT_LICENCE,
            status=CorpusLicenseStatus.APPROVED,
            permitted_uses=(CorpusUsageRight.INTERNAL_USE, CorpusUsageRight.INTERNAL_USE),
            cleared_by="somebody",
            cleared_at=DECIDED_AT,
            evidence_hash=HASH,
            source_content_hash="e" * 64,
        )


# --- the recognition lists are advice ------------------------------------------


def test_the_recognition_lists_are_short_and_that_no_longer_decides_anything() -> None:
    """Lengthening them would change advice and would make nothing new usable."""
    assert (
        frozenset({"Apache-2.0", "MIT", "BSD-3-Clause", "CC0-1.0"})
        == RECOGNISED_PERMISSIVE_LICENSES
    )
    assert not any(name.startswith("CC-BY-") for name in RECOGNISED_PERMISSIVE_LICENSES)
    assert RECOGNISED_INTERNAL_LICENSES


# --- the configuration is read now ---------------------------------------------


def test_the_licence_actions_are_read_rather_than_advertised() -> None:
    """W1-F6's second half. Six settings described behaviour nothing consulted."""
    import inspect

    from cognitive_os.corpus import factory

    source = inspect.getsource(factory.CorpusFactory._route)
    for name in (
        "unknown_license_action",
        "conflicting_license_action",
        "restricted_license_action",
    ):
        assert name in source


def test_a_stricter_configured_action_actually_changes_the_outcome() -> None:
    request, source = build_corpus_fixture("document")
    request = request.model_copy(
        update={"content_hash": "", "license_identifiers": (CONTENT_LICENCE,)}
    )
    strict = CorpusConfiguration(unknown_license_action="reject")
    result = asyncio.run(
        CorpusFactory(
            InMemoryCorpusRepository(), FixtureArtifactStore(), configuration=strict
        ).ingest(request, source)
    )
    assert {decision.status for decision in result.route_decisions} == {CorpusRouteStatus.DENIED}


def test_configuration_may_choose_how_to_refuse_and_may_not_choose_to_permit() -> None:
    """`allow` is not a legal action: permission comes from a person, not from a file."""
    with pytest.raises(ValidationError):
        CorpusConfiguration(unknown_license_action="allow")
    with pytest.raises(ValidationError):
        CorpusConfiguration(restricted_license_action="ignore")


def test_an_unreadable_action_is_refused_at_load_and_not_at_ingest() -> None:
    """A typo in a configuration file must not surface as a KeyError mid-run."""
    with pytest.raises(ValidationError):
        CorpusConfiguration(conflicting_license_action="quarantien")
