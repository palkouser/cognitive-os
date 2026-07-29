"""The public advisory fixture and the verifier that scores answers to it.

Two things are being protected. The fixture must stay pinned, public and impossible to
mistake for a real governed outcome. The verifier must refuse a well-formed answer that did
not diagnose the defect — otherwise every live smoke measures JSON formatting.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.providers.advisory_fixture import (
    ADVISORY_FIXTURE_SCHEMA_VERSION,
    AdvisoryFixture,
    ExpectedFinding,
    FixtureProvenance,
    FixtureVerdict,
    content_hash_for,
    load_advisory_fixture,
    verify_advisory_answer,
)
from cognitive_os.providers.advisory_schema import AdvisoryFinding, AdvisoryResult

FIXTURE_ROOT = Path("tests/fixtures/providers/advisory")

#: Pinned deliberately. If a wording change moves this value the fixture changed, and every
#: recorded receipt that named the old hash described a different task.
EXPECTED_CONTENT_HASH = (
    "0e2dc4d10c6bd1a79d704081193febfee549ab58b022abaad63d8db690744eb6"  # pragma: allowlist secret
)


@pytest.fixture(scope="module")
def fixture() -> AdvisoryFixture:
    return load_advisory_fixture(FIXTURE_ROOT).manifest


def _finding(**overrides: object) -> AdvisoryFinding:
    payload: dict[str, object] = {
        "title": "arithmetic_mean divides by the length of an empty sequence",
        "severity": "high",
        "description": (
            "arithmetic_mean returns total / len(values) with no guard, so calling it with "
            "an empty list raises ZeroDivisionError."
        ),
        "evidence": ("workspace/statistics_helper.py",),
    }
    payload.update(overrides)
    return AdvisoryFinding.model_validate(payload)


def _result(*findings: AdvisoryFinding) -> AdvisoryResult:
    return AdvisoryResult(summary="reviewed the workspace", findings=findings)


class TestTheCommittedFixture:
    def test_it_loads_and_every_byte_matches_its_manifest(self) -> None:
        loaded = load_advisory_fixture(FIXTURE_ROOT)
        assert loaded.manifest.schema_version == ADVISORY_FIXTURE_SCHEMA_VERSION
        assert loaded.workspace.is_dir()
        assert "statistics_helper.py" in loaded.task_prompt()

    def test_the_content_hash_is_stable(self, fixture: AdvisoryFixture) -> None:
        assert fixture.content_hash == EXPECTED_CONTENT_HASH
        assert content_hash_for(fixture.content_manifest) == EXPECTED_CONTENT_HASH

    def test_every_workspace_file_is_listed_and_hashed(self, fixture: AdvisoryFixture) -> None:
        for relative, digest in fixture.content_manifest.items():
            path = FIXTURE_ROOT / relative
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest

    def test_the_workspace_really_contains_the_defect(self) -> None:
        """The verifier's expectation is only worth anything if the code still misbehaves."""
        source = (FIXTURE_ROOT / "workspace" / "statistics_helper.py").read_text(encoding="utf-8")
        namespace: dict[str, object] = {}
        exec(compile(source, "statistics_helper.py", "exec"), namespace)
        assert namespace["running_total"]([]) == []  # type: ignore[operator]
        with pytest.raises(ZeroDivisionError):
            namespace["arithmetic_mean"]([])  # type: ignore[operator]

    def test_it_cannot_be_labelled_a_real_governed_outcome(self, fixture: AdvisoryFixture) -> None:
        assert fixture.provenance.is_real_governed_outcome is False
        assert fixture.provenance.contains_repository_content is False
        assert fixture.provenance.contains_personal_data is False
        with pytest.raises(ValidationError, match="must not be labelled a real"):
            FixtureProvenance.model_validate(
                fixture.provenance.model_dump() | {"is_real_governed_outcome": True}
            )


class TestADriftedFixtureIsRefused:
    def test_a_changed_file_fails_to_load(self, tmp_path: Path) -> None:
        root = _copy_fixture(tmp_path)
        target = root / "workspace" / "statistics_helper.py"
        target.write_text(target.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
        with pytest.raises(ValueError, match="manifest expects"):
            load_advisory_fixture(root)

    def test_a_missing_file_fails_to_load(self, tmp_path: Path) -> None:
        root = _copy_fixture(tmp_path)
        (root / "task.md").unlink()
        with pytest.raises(ValueError, match=r"is missing task\.md"):
            load_advisory_fixture(root)

    def test_an_unlisted_file_fails_to_load(self, tmp_path: Path) -> None:
        """An unlisted file is readable by the provider, unscored, and unpinned."""
        root = _copy_fixture(tmp_path)
        (root / "workspace" / "notes.txt").write_text("extra\n", encoding="utf-8")
        with pytest.raises(ValueError, match="unlisted files"):
            load_advisory_fixture(root)

    def test_a_manifest_whose_own_hash_disagrees_fails_to_load(self, tmp_path: Path) -> None:
        root = _copy_fixture(tmp_path)
        document = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        document["content_hash"] = "0" * 64
        (root / "manifest.json").write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(ValueError, match="content hash mismatch"):
            load_advisory_fixture(root)

    def test_an_unknown_schema_version_is_refused(self, fixture: AdvisoryFixture) -> None:
        with pytest.raises(ValidationError, match="unsupported advisory fixture schema"):
            AdvisoryFixture.model_validate(fixture.model_dump() | {"schema_version": "99"})


class TestTheVerifierAcceptsOnlyTheExpectedFinding:
    def test_the_expected_diagnosis_is_correct(self, fixture: AdvisoryFixture) -> None:
        verification = verify_advisory_answer(fixture, _result(_finding()))
        assert verification.correct is True
        assert verification.verdict is FixtureVerdict.CORRECT
        assert verification.missing_concepts == ()
        assert verification.answer_hash is not None

    @pytest.mark.parametrize(
        ("phrasing", "missing_group"),
        [
            (
                "statistics_helper.py: arithmetic_mean fails on an empty list "
                "with a division by zero",
                None,
            ),
            (
                "statistics_helper.py: arithmetic_mean crashes when the caller "
                "passes nothing at all",
                "failure",
            ),
            (
                "statistics_helper.py: dividing by zero when there are no elements",
                "function",
            ),
        ],
    )
    def test_wording_is_scored_by_concept_not_by_phrase(
        self, fixture: AdvisoryFixture, phrasing: str, missing_group: str | None
    ) -> None:
        """Different wording of the same diagnosis passes; a missing concept does not."""
        verification = verify_advisory_answer(
            fixture,
            _result(_finding(title="review note", description=phrasing, evidence=())),
        )
        if missing_group is None:
            assert verification.correct is True
        else:
            assert verification.correct is False
            assert missing_group in verification.missing_concepts

    def test_a_valid_but_empty_result_is_not_correct(self, fixture: AdvisoryFixture) -> None:
        """Schema validity proves shape. Any provider can emit well-formed JSON."""
        verification = verify_advisory_answer(fixture, _result())
        assert verification.correct is False
        assert verification.verdict is FixtureVerdict.NO_FINDINGS
        assert set(verification.missing_concepts) == set(fixture.expected_finding.required_concepts)

    def test_a_confident_answer_about_the_wrong_function_is_not_correct(
        self, fixture: AdvisoryFixture
    ) -> None:
        wrong = _finding(
            title="running_total accumulates in a float",
            description=(
                "running_total in statistics_helper.py starts from 0.0, so integer inputs "
                "come back as floats."
            ),
            evidence=("workspace/statistics_helper.py",),
        )
        verification = verify_advisory_answer(fixture, _result(wrong))
        assert verification.correct is False
        assert verification.verdict is FixtureVerdict.WRONG_DEFECT
        assert "file" in verification.matched_concepts
        assert "failure" in verification.missing_concepts

    def test_concepts_spread_across_findings_do_not_add_up(self, fixture: AdvisoryFixture) -> None:
        """A shotgun is not a diagnosis: one finding has to carry the whole answer."""
        verification = verify_advisory_answer(
            fixture,
            _result(
                _finding(description="statistics_helper.py has a problem", evidence=()),
                _finding(description="something raises ZeroDivisionError", evidence=()),
            ),
        )
        assert verification.correct is False
        assert verification.verdict is FixtureVerdict.WRONG_DEFECT

    def test_burying_the_right_answer_in_noise_is_refused(self, fixture: AdvisoryFixture) -> None:
        noise = [
            _finding(title=f"style note {index}", description="prefer f-strings")
            for index in range(4)
        ]
        verification = verify_advisory_answer(fixture, _result(_finding(), *noise))
        assert verification.correct is False
        assert verification.verdict is FixtureVerdict.TOO_MANY_FINDINGS

    def test_an_unparsable_answer_is_a_verdict_not_an_exception(
        self, fixture: AdvisoryFixture
    ) -> None:
        verification = verify_advisory_answer(fixture, None)
        assert verification.verdict is FixtureVerdict.MALFORMED
        assert verification.correct is False
        assert verification.answer_hash is None

    def test_the_same_answer_always_hashes_the_same(self, fixture: AdvisoryFixture) -> None:
        first = verify_advisory_answer(fixture, _result(_finding()))
        second = verify_advisory_answer(fixture, _result(_finding()))
        assert first.answer_hash == second.answer_hash

    def test_the_verification_carries_no_provider_prose(self, fixture: AdvisoryFixture) -> None:
        """A receipt records that the answer was right, never what it said."""
        sensitive_phrase = "an internal hostname the provider echoed back"
        verification = verify_advisory_answer(
            fixture,
            _result(_finding(description=f"{sensitive_phrase} — arithmetic_mean divides by zero")),
        )
        assert sensitive_phrase not in verification.model_dump_json()


class TestTheExpectedFindingContract:
    def test_an_expectation_with_no_concepts_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="accepts anything"):
            ExpectedFinding(target_path="workspace/x.py", required_concepts={})

    def test_a_concept_group_with_no_phrasing_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="no accepted phrasing"):
            ExpectedFinding(target_path="workspace/x.py", required_concepts={"failure": ()})


def _copy_fixture(tmp_path: Path) -> Path:
    from shutil import copytree

    root = tmp_path / "advisory"
    copytree(FIXTURE_ROOT, root)
    return root
