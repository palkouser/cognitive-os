import json
from uuid import uuid4

from cognitive_os.coding.reporting import redact_secrets, render_outcome_json
from cognitive_os.domain.coding import (
    CodingOutcome,
    CodingOutcomeStatus,
    RepositoryProfile,
    RepositoryProfileStatus,
    RiskRecord,
    WorkspaceDisposition,
)
from cognitive_os.domain.common import utc_now


def test_report_is_canonical_and_secret_safe() -> None:
    outcome = CodingOutcome(
        task_run_id=uuid4(),
        status=CodingOutcomeStatus.FAILED,
        repository_profile=RepositoryProfile(
            status=RepositoryProfileStatus.SUPPORTED,
            git_repository=True,
            has_pyproject=True,
            python_version=">=3.12,<3.13",
            has_pytest=True,
            has_ruff=True,
            has_mypy=True,
            package_layout="src",
            rootless_docker=True,
        ),
        base_commit="a" * 40,
        risks=(RiskRecord(code="provider", message="token=top-secret", severity="high"),),
        workspace_disposition=WorkspaceDisposition.ARCHIVE,
        completed_at=utc_now(),
    )

    encoded = render_outcome_json(outcome)
    assert b"top-secret" not in encoded
    assert b"[REDACTED]" in encoded
    assert json.loads(encoded)["status"] == "failed"
    assert encoded == render_outcome_json(outcome)


def test_common_credential_shapes_are_redacted() -> None:
    value = "api_key=abc123 github_pat_abcdefghijklmnopqrstuvwxyz"
    redacted = redact_secrets(value)
    assert "abc123" not in redacted
    assert "github_pat_" not in redacted
