"""The public synthetic advisory fixture, and the verifier that scores an answer to it.

One task, three providers, one verifier. OpenRouter, Claude Code and Codex are handed the
same read-only diagnosis task from the same committed workspace, and the same deterministic
function decides whether the answer is right. Without that, "the provider worked" would mean
whatever each adapter's own parser was willing to accept.

Two rules shape the verifier, and both exist because the obvious alternative is worse:

* **Schema validity is not correctness.** `AdvisoryResult` proves shape. A perfectly formed
  result that names no defect, or names the wrong one, is a failure here. Any provider can
  produce valid JSON; the question is whether it read the code.
* **All required concepts must appear in one finding.** Splitting "the file", "the function",
  "empty input" and "ZeroDivisionError" across four unrelated findings is a shotgun, not a
  diagnosis, and `maximum_findings` refuses the same trick by volume.

The fixture is synthetic, Apache-2.0, contains no repository or personal content, and its
provenance declares `is_real_governed_outcome: false` — so an answer to it can never be
counted as a real governed run no matter which store it reaches. See ADR 0087.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr

from .advisory_schema import AdvisoryResult

#: Bumped when the fixture's meaning changes, not when its wording is corrected.
ADVISORY_FIXTURE_SCHEMA_VERSION = "1"

#: Where the committed fixture lives, relative to the repository root.
DEFAULT_FIXTURE_PATH = Path("tests/fixtures/providers/advisory")


class FixtureVerdict(StrEnum):
    """Why an answer was accepted or refused. Typed so a report can group failures."""

    CORRECT = "correct"
    #: Valid `AdvisoryResult` shape, but it reported nothing.
    NO_FINDINGS = "no_findings"
    #: More findings than a single-defect fixture can justify.
    TOO_MANY_FINDINGS = "too_many_findings"
    #: Findings exist, but no single one covers every required concept.
    WRONG_DEFECT = "wrong_defect"
    #: The result did not parse as an `AdvisoryResult` at all.
    MALFORMED = "malformed"


class FixtureProvenance(ImmutableContractModel):
    """Where the fixture came from and what it is not."""

    origin: NonEmptyStr
    license: NonEmptyStr
    author: NonEmptyStr
    created_at: NonEmptyStr
    contains_repository_content: bool
    contains_personal_data: bool
    #: Always false, and enforced rather than documented: a fixture that could claim to be a
    #: real governed outcome would be the shortest path from synthetic text into the corpus.
    is_real_governed_outcome: bool

    @field_validator("is_real_governed_outcome", "contains_repository_content")
    @classmethod
    def _must_be_false(cls, value: bool) -> bool:
        if value:
            raise ValueError(
                "the advisory fixture must be synthetic and must not be labelled a real "
                "governed outcome"
            )
        return value


class ExpectedFinding(ImmutableContractModel):
    """What a correct answer has to say, expressed as concepts rather than exact wording.

    Each entry in `required_concepts` is a group of accepted phrasings; a finding satisfies
    the group if it contains any one of them. Grouping is what keeps the verifier from
    grading style: "raises ZeroDivisionError" and "divides by zero" are the same diagnosis.
    """

    target_path: NonEmptyStr
    required_concepts: dict[str, tuple[str, ...]]
    minimum_findings: int = Field(default=1, ge=1)
    maximum_findings: int = Field(default=3, ge=1)

    @field_validator("required_concepts")
    @classmethod
    def _groups_must_offer_alternatives(
        cls, value: dict[str, tuple[str, ...]]
    ) -> dict[str, tuple[str, ...]]:
        if not value:
            raise ValueError("an expected finding with no required concept accepts anything")
        for group, alternatives in value.items():
            if not alternatives:
                raise ValueError(f"concept group {group!r} lists no accepted phrasing")
        return value


class AdvisoryFixture(ImmutableContractModel):
    """The committed task, its workspace, its rights, and the answer it expects."""

    fixture_id: NonEmptyStr
    fixture_version: NonEmptyStr
    schema_version: NonEmptyStr
    title: NonEmptyStr
    task_path: NonEmptyStr
    workspace_path: NonEmptyStr
    provenance: FixtureProvenance
    usage_rights: NonEmptyStr
    expected_finding: ExpectedFinding
    #: Relative path to SHA-256, for every file the provider is allowed to read.
    content_manifest: dict[str, str]
    #: SHA-256 over the canonical JSON of `content_manifest`. One value to pin in a report.
    content_hash: NonEmptyStr

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, value: str) -> str:
        if value != ADVISORY_FIXTURE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported advisory fixture schema {value!r}; "
                f"this build reads {ADVISORY_FIXTURE_SCHEMA_VERSION!r}"
            )
        return value


class FixtureVerification(ImmutableContractModel):
    """The verifier's decision, with enough detail to explain a refusal without the text."""

    verdict: FixtureVerdict
    correct: bool
    fixture_id: NonEmptyStr
    fixture_content_hash: NonEmptyStr
    finding_count: int = Field(ge=0)
    matched_concepts: tuple[str, ...] = ()
    missing_concepts: tuple[str, ...] = ()
    #: Never the provider's prose. A hash is enough to prove two runs agreed.
    answer_hash: NonEmptyStr | None = None


class LoadedFixture:
    """A fixture whose bytes have been checked against its own manifest."""

    def __init__(self, root: Path, manifest: AdvisoryFixture) -> None:
        self.root = root
        self.manifest = manifest

    @property
    def workspace(self) -> Path:
        return self.root / self.manifest.workspace_path

    def task_prompt(self) -> str:
        return (self.root / self.manifest.task_path).read_text(encoding="utf-8")


def content_hash_for(content_manifest: dict[str, str]) -> str:
    """The single value that pins the whole fixture, computed the same way everywhere."""
    canonical = json.dumps(content_manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_advisory_fixture(root: Path = DEFAULT_FIXTURE_PATH) -> LoadedFixture:
    """Read the fixture and verify every byte against its manifest.

    A drifted fixture is refused rather than repaired. If the workspace no longer matches the
    manifest, the expected finding may no longer describe the code, and a benchmark scoring
    answers against a stale expectation would still report a pass rate.
    """
    manifest_path = root / "manifest.json"
    manifest = AdvisoryFixture.model_validate_json(manifest_path.read_bytes())

    recomputed = content_hash_for(manifest.content_manifest)
    if recomputed != manifest.content_hash:
        raise ValueError(
            f"advisory fixture content hash mismatch: manifest declares "
            f"{manifest.content_hash}, its own file list hashes to {recomputed}"
        )
    for relative, expected in sorted(manifest.content_manifest.items()):
        path = root / relative
        if not path.is_file():
            raise ValueError(f"advisory fixture is missing {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(
                f"advisory fixture file {relative} hashes to {actual}, manifest expects {expected}"
            )
    unlisted = sorted(
        entry.relative_to(root).as_posix()
        for entry in _walk(root)
        if entry.name != "manifest.json"
        and entry.relative_to(root).as_posix() not in manifest.content_manifest
    )
    if unlisted:
        # An unlisted file is readable by the provider but unscored and unpinned, which is
        # exactly how sensitive content would arrive in a fixture nobody re-hashed.
        raise ValueError(f"advisory fixture contains unlisted files: {', '.join(unlisted)}")
    return LoadedFixture(root, manifest)


def verify_advisory_answer(
    fixture: AdvisoryFixture, result: AdvisoryResult | None
) -> FixtureVerification:
    """Decide whether an answer diagnosed the fixture's one defect.

    `result` is `None` when the adapter could not parse the provider's reply into the shared
    schema at all. That is a verdict, not an exception: an unparsable answer is a failed
    answer, and the caller still needs a receipt saying so.
    """
    expected = fixture.expected_finding
    if result is None:
        return FixtureVerification(
            verdict=FixtureVerdict.MALFORMED,
            correct=False,
            fixture_id=fixture.fixture_id,
            fixture_content_hash=fixture.content_hash,
            finding_count=0,
            missing_concepts=tuple(sorted(expected.required_concepts)),
        )

    answer_hash = hashlib.sha256(
        result.model_dump_json().encode("utf-8"),
    ).hexdigest()
    count = len(result.findings)

    def verdict(
        outcome: FixtureVerdict,
        *,
        matched: tuple[str, ...] = (),
        missing: tuple[str, ...] = (),
    ) -> FixtureVerification:
        return FixtureVerification(
            verdict=outcome,
            correct=outcome is FixtureVerdict.CORRECT,
            fixture_id=fixture.fixture_id,
            fixture_content_hash=fixture.content_hash,
            finding_count=count,
            matched_concepts=matched,
            missing_concepts=missing,
            answer_hash=answer_hash,
        )

    if count < expected.minimum_findings:
        every_concept = tuple(sorted(expected.required_concepts))
        return verdict(FixtureVerdict.NO_FINDINGS, missing=every_concept)
    if count > expected.maximum_findings:
        # An answer that reports everything has diagnosed nothing, and letting volume buy a
        # pass would make the benchmark reward guessing.
        return verdict(FixtureVerdict.TOO_MANY_FINDINGS)

    best_matched: tuple[str, ...] = ()
    best_missing = tuple(sorted(expected.required_concepts))
    for finding in result.findings:
        matched, missing = _score(finding_text(finding), expected)
        if len(matched) > len(best_matched):
            best_matched, best_missing = matched, missing
        if not missing:
            break

    return verdict(
        FixtureVerdict.CORRECT if not best_missing else FixtureVerdict.WRONG_DEFECT,
        matched=best_matched,
        missing=best_missing,
    )


def finding_text(finding: object) -> str:
    """Title, description and evidence as one lowercase haystack.

    Providers put the same diagnosis in different fields — Codex favours the description,
    Claude Code often puts the file path only in evidence — so scoring per field would
    measure formatting habits instead of whether the defect was found.
    """
    parts = [
        str(getattr(finding, "title", "")),
        str(getattr(finding, "description", "")),
        " ".join(getattr(finding, "evidence", ()) or ()),
    ]
    return " ".join(parts).lower()


def _score(haystack: str, expected: ExpectedFinding) -> tuple[tuple[str, ...], tuple[str, ...]]:
    matched: list[str] = []
    missing: list[str] = []
    for group, alternatives in sorted(expected.required_concepts.items()):
        if any(alternative.lower() in haystack for alternative in alternatives):
            matched.append(group)
        else:
            missing.append(group)
    return tuple(matched), tuple(missing)


def _walk(root: Path) -> Iterator[Path]:
    for entry in sorted(root.rglob("*")):
        if entry.is_file() and "__pycache__" not in entry.parts:
            yield entry
