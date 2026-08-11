#!/usr/bin/env python
"""S21D7-040: every check expected before release, run once, with its actual exit status.

    scripts/verification_matrix_d7.py [--output docs/.../sprint-21d7-verification-matrix.json]

One row per check. Each records what was run, what it was expected to do, what it actually did,
how long it took, and the SHA-256 of its combined output — so a row that passes today and fails
tomorrow can be compared without anyone having kept the log.

Three rules make this a matrix rather than a list.

*Negative rows must fail for their expected reason.* A row declared `expect: nonzero` is a
finding when it succeeds, and a row that fails with a message other than the one it names is
also a finding. A destructive check that passes because it never ran is the failure mode this
exists to prevent.

*Nothing is silently skipped.* A row whose preconditions are absent is recorded as `skipped`
with the reason, and the totals count it — an evidence file reporting thirty passes out of
thirty rows when four never ran would be a report about the host, not about the release.

*The record checks itself, here.* `_structural_findings` asserts what the record has to be able
to be false about — every command row measured a cost, every negative row exists and refused,
every recorded row binds the bytes it read — and folds the result into the exit status. Those
checks began as a test module in D5, which could not work: this command runs the whole suite as
one of its rows, so a test reading this record saw the previous run's copy and the command needed
two runs to go green. A release command that is not idempotent is a defect in the command.

The command is read-only with respect to every store. The one row that touches a corpus,
`corpus_complete`, writes generated bodies into a temporary directory and nothing else.

*It takes no environment, and that is D4-W7-F1's operational half.* The matrix runs the whole
suite as one of its rows. When D4 ran that row with `.env.s21d4.local` sourced, five test modules
truncated the D4 evidence store. Every row that needs a database or a store names one itself, the
`environment` block records `not set` rather than claiming a handle it did not use, and the
released truncation fence is what stands between the suite and any store that was not nominated
for erasure.

What D7's matrix carries that D6's did not
------------------------------------------

*Six `--check` validators instead of two.* D7 wrote four records whose whole verification story
is that a second process re-derives them byte for byte — the direction, the ladder, the step-0
rulings and the selection. They are timestamp-free by construction so that `--check` in a fresh
process *is* the reproduction proof, and a release that did not run them would be taking W2's
word for its own arithmetic.

*Twelve recorded rows, and eight of them are about things D6 never reached.* D6 stopped at the
bar. D7 has an artifact that re-ranks, a resolver that reaches every code, two final batches, a
promotion payload and a live activation, and each of those has a boolean in a sealed record that
this matrix is willing to be wrong about.

*The canary row reads a zero.* `proposals_accepted_without_a_verifier_label` must be exactly
`0`, named as `wanted` rather than left to truthiness — a zero is falsy, and a row that decided
this one by truthiness would report a failure as a pass.

*One negative row is D7's own.* D7 reads D5's numeric bounds and D6's whole conformal half out
of their stores, exactly as D6 read D5's, and the guard that keeps it from *writing* there is one
function with one list. `campaign_refuses_the_d6_store` and `campaign_refuses_the_d5_store` prove
the list still has both on it.

*No `d7-integrity` row exists to run.* The twelve-class report commands are `learned.py
d3-integrity`, `d4-integrity` and `d5-integrity`; D6 added none and neither did D7. What stands in
its place is D7's own six validators plus the three predecessor reports, which still have to be
green over their own evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess  # nosec B404 - fixed argv lists of repository commands, never a shell
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
RUFF_CONFIG = "ruff.cognitive-os.toml"


@dataclass(frozen=True, slots=True)
class Row:
    """One check: what it is, how to run it, and what counts as the right answer."""

    name: str
    argv: tuple[str, ...]
    #: `zero` for a check that must succeed, `nonzero` for one that must refuse.
    expect: str = "zero"
    #: For a negative row, a fragment its output must contain. A refusal for the wrong reason
    #: is not the refusal the row claims to demonstrate.
    because: str = ""
    #: Environment overrides. Used only by the negative rows, which exist to prove that a
    #: wrong environment is refused.
    env: dict[str, str] = field(default_factory=dict)
    #: An evidence file this row records rather than re-runs, with the key that decides it.
    evidence: tuple[str, str] | None = None
    #: The exact value a recorded row's key must have. Required whenever the key holds a
    #: string: D4's matrix decided string-valued rows by truthiness, so `first_failed_floor`
    #: would have passed on any wording at all, including a wording that reported the opposite
    #: result. `_structural_findings` refuses a string-valued row that names nothing.
    wanted: str = ""


ROWS: tuple[Row, ...] = (
    # ------------------------------------------------------------------ formatting and lint
    Row(
        "ruff_check",
        ("uv", "run", "ruff", "check", "--config", RUFF_CONFIG, "src", "tests", "scripts", "infra"),
    ),
    Row(
        "ruff_format",
        (
            "uv",
            "run",
            "ruff",
            "format",
            "--check",
            "--config",
            RUFF_CONFIG,
            "src",
            "tests",
            "scripts",
            "infra",
        ),
    ),
    Row("mypy", ("uv", "run", "mypy", "src/cognitive_os")),
    Row("bandit", ("uv", "run", "bandit", "-q", "-r", "src/cognitive_os")),
    # ------------------------------------------------------------------ suites
    Row("full_suite", ("uv", "run", "pytest", "-q", "--timeout=600")),
    Row("correction_slice", ("uv", "run", "pytest", "-q", "tests/cognitive_os/learning")),
    Row("corpus_slice", ("uv", "run", "pytest", "-q", "tests/cognitive_os/coding")),
    Row(
        "lifecycle_slice",
        ("uv", "run", "pytest", "-q", "tests/cognitive_os/learned_evidence"),
    ),
    # ------------------------------------------------------------------ contracts and policy
    Row("schema_export", ("uv", "run", "python", "-m", "cognitive_os.schemas.export", "--check")),
    Row("repository_language", ("bash", "scripts/check_repository_language.sh")),
    # The released CI commands, not approximations of them. This matrix's own output is
    # excluded, and only its own: a file whose hashes are written at the end of a run cannot be
    # scanned by the run that writes it. The release workflow regenerates the baseline and
    # re-scans afterwards, which is what covers it.
    Row(
        "secrets_scan",
        (
            "bash",
            "-c",
            "git ls-files -z | grep -zv sprint-21d7-verification-matrix.json | "
            "xargs -0 uv run detect-secrets-hook --baseline .secrets.baseline",
        ),
    ),
    Row("dependency_audit", ("uv", "run", "pip-audit")),
    Row("packaging_build", ("uv", "build")),
    Row("wheel_installation", ("bash", "scripts/verify_distribution.sh")),
    Row("editable_installation", ("bash", "scripts/verify_editable_install.sh")),
    # ------------------------------------------------------- D7's own released validators
    #
    # Six, not D6's two. Four of these records carry no timestamp by construction, so a second
    # process re-deriving them either produces the same bytes or the check fails: `--check` is
    # the restart-reproduction proof rather than a report about one.
    Row("pre_registration", ("uv", "run", "python", "scripts/pre_registration_d7.py", "--check")),
    Row("sealed_manifests", ("uv", "run", "python", "scripts/sealed_manifests_d7.py", "--check")),
    Row("w2_rulings", ("uv", "run", "python", "scripts/w2_rulings_d7.py", "--check")),
    Row("w2_direction", ("uv", "run", "python", "scripts/w2_direction_d7.py", "--check")),
    Row("w2_ladder", ("uv", "run", "python", "scripts/w2_ladder_d7.py", "--check")),
    Row("learner_selection", ("uv", "run", "python", "scripts/learner_selection_d7.py", "--check")),
    # The corpus validator, over all hundred certification groups and the four W3 replacements.
    # Slow, and included anyway: a release matrix that drops a check to finish sooner is the
    # failure mode it exists for.
    Row("corpus_complete", ("uv", "run", "python", "scripts/corpus_d7.py")),
    # ------------------------------------------------------------------ evidence reports
    # No d7-integrity row exists to run; see the module docstring. The three released reports
    # still have to be green over their own evidence, and D7 refactored none of them, so this is
    # a claim about this release rather than about the last four.
    Row(
        "d5_evidence_report_still_green",
        ("uv", "run", "python", "scripts/learned.py", "d5-integrity"),
        env={"COGOS_POSTGRES_DATABASE": "cognitive_os_s21d5_test"},
    ),
    Row(
        "d4_evidence_report_still_green",
        ("uv", "run", "python", "scripts/learned.py", "d4-integrity"),
        env={"COGOS_POSTGRES_DATABASE": "cognitive_os_s21d4_test"},
    ),
    Row(
        "d3_evidence_report_still_green",
        ("uv", "run", "python", "scripts/learned.py", "d3-integrity"),
        env={"COGOS_POSTGRES_DATABASE": "cognitive_os_s21d3_test"},
    ),
    Row(
        "benchmark_replay_ci",
        (
            "uv",
            "run",
            "python",
            "scripts/benchmark_run.py",
            "--manifest",
            "benchmarks/manifests/sprint21c1-learned-ci.yaml",
            "--mode",
            "learned-replay",
            "--report-directory",
            "/tmp/s21d7-matrix-ci",
        ),
    ),  # nosec B108
    Row(
        "benchmark_replay_seed",
        (
            "uv",
            "run",
            "python",
            "scripts/benchmark_run.py",
            "--manifest",
            "benchmarks/manifests/sprint21c1-learned-seed.yaml",
            "--mode",
            "learned-replay",
            "--report-directory",
            "/tmp/s21d7-matrix-seed",
        ),
    ),  # nosec B108
    # ------------------------------------------------------------------ negative rows
    Row(
        "predecessor_store_refused",
        ("uv", "run", "python", "scripts/learned.py", "d5-integrity"),
        expect="nonzero",
        because="refusing to open",
        env={
            "COGOS_POSTGRES_DATABASE": "cognitive_os_s21d5_test",
            "COGOS_ARTIFACT_ROOT": "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d2",
        },
    ),
    Row(
        "predecessor_database_refused",
        ("uv", "run", "python", "scripts/learned.py", "d5-integrity"),
        expect="nonzero",
        because="require an s21d5 database",
        env={"COGOS_POSTGRES_DATABASE": "cognitive_os_s21d4_test"},
    ),
    # The artifact root is supplied so the refusal under test is the *database name*. This
    # matrix runs with no sourced environment, and without a root the smoke refuses for a
    # missing root instead -- a refusal for the wrong reason, which counts as a failure here.
    Row(
        "smoke_refuses_a_non_test_database",
        ("uv", "run", "python", "scripts/learned.py", "smoke", "--confirm-isolated"),
        expect="nonzero",
        because="isolated *_test database",
        env={
            "COGOS_DATABASE_ADMIN_URL": "postgresql+asyncpg://u@h/cognitive_os_dev",
            "COGOS_ARTIFACT_ROOT": "/tmp/s21d7-matrix-never-opened",  # nosec B108
        },
    ),
    # D7 reads D5's numeric bounds and D6's entire conformal half out of their stores, exactly
    # as D6 read D5's. The guard that keeps it from *writing* there is one function with one
    # list, and these two rows prove the list still has both sprints on it.
    Row(
        "campaign_refuses_the_d5_store",
        ("uv", "run", "python", "scripts/reality_campaign_d7.py", "--stage", "snapshot"),
        expect="nonzero",
        because="refusing to run against s21d5",
        env={
            "COGOS_DATABASE_URL": "postgresql+asyncpg://u@h/cognitive_os_s21d5_test",
            "COGOS_ARTIFACT_ROOT": "/tmp/s21d7-matrix-never-opened",  # nosec B108
        },
    ),
    Row(
        "campaign_refuses_the_d6_store",
        ("uv", "run", "python", "scripts/reality_campaign_d7.py", "--stage", "snapshot"),
        expect="nonzero",
        because="refusing to run against s21d6",
        env={
            "COGOS_DATABASE_URL": "postgresql+asyncpg://u@h/cognitive_os_s21d6_measured",
            "COGOS_ARTIFACT_ROOT": "/tmp/s21d7-matrix-never-opened",  # nosec B108
        },
    ),
    Row(
        "campaign_refuses_the_development_pair",
        ("uv", "run", "python", "scripts/reality_campaign_d7.py", "--stage", "snapshot"),
        expect="nonzero",
        because="inconsistent development pair",
        env={
            "COGOS_DATABASE_URL": "postgresql+asyncpg://u@h/cognitive_os_s21d7_measured",
            "COGOS_ARTIFACT_ROOT": "/home/palkouser/projekt/cognitive-os-data/artifacts",
        },
    ),
    # ------------------------------------------------- rows recorded from committed evidence
    Row(
        "correction_branch_selected",
        (),
        evidence=("sprint-21d7-learner-selection.json", "ending.name"),
        wanted="1_select",
    ),
    Row(
        "conformal_bar_derived_at_the_preregistered_alpha",
        (),
        evidence=("sprint-21d7-learner-selection.json", "conformal_point.alpha"),
        wanted="0.20",
    ),
    Row(
        "first_action_preserved_on_the_invariance_sample",
        (),
        evidence=("sprint-21d7-invariance-regression.json", "first_action.preservation"),
        wanted="100%",
    ),
    Row(
        "gate_l2_condition_24_inherited",
        (),
        evidence=("sprint-21d7-condition-24-ruling.json", "gate_l2_condition_24_recorded_as"),
        wanted="met by inheritance, with the source hash bound",
    ),
    Row(
        "artifact_reproduces_every_first_choice_and_margin",
        (),
        evidence=("sprint-21d7-artifact.json", "boundary.every_first_choice_and_margin_reproduced"),
    ),
    Row(
        "artifact_refusals_all_refused",
        (),
        evidence=("sprint-21d7-artifact.json", "every_refusal_refused"),
    ),
    Row(
        "every_runtime_reason_code_reached",
        (),
        evidence=("sprint-21d7-runtime.json", "reason_codes.every_code_reached"),
    ),
    Row(
        "every_fallback_is_the_released_rung_ordering",
        (),
        evidence=(
            "sprint-21d7-runtime.json",
            "deterministic_fallback.every_fallback_produced_the_rung_ordering",
        ),
    ),
    # W3-F1's chronology, which is the whole authorisation: an audit that licensed replacement
    # bodies after they existed would be a description of what someone already did.
    Row(
        "final_role_audit_preceded_the_replacements",
        (),
        evidence=(
            "sprint-21d7-final-role-audit.json",
            "chronology.authorisation_precedes_any_replacement_body",
        ),
    ),
    Row(
        "final_evidence_conditions_met",
        (),
        evidence=("sprint-21d7-final-evidence.json", "all_conditions_met"),
    ),
    Row(
        "promotion_conditions_met",
        (),
        evidence=("sprint-21d7-promotion.json", "all_conditions_met"),
    ),
    Row(
        "lifecycle_conditions_met",
        (),
        evidence=("sprint-21d7-lifecycle.json", "all_conditions_met"),
    ),
    # Named rather than left to truthiness on purpose. The value that must hold is zero, and
    # zero is falsy: a row decided by truthiness here would report a failure as a pass.
    Row(
        "no_canary_proposal_was_accepted_without_a_verifier_label",
        (),
        evidence=(
            "sprint-21d7-lifecycle.json",
            "phases.observe.sequencer.proposals_accepted_without_a_verifier_label",
        ),
        wanted="0",
    ),
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(value: object) -> bytes:
    """The bytes that are hashed are the bytes that are written.

    D3's originals hashed a compact serialisation and wrote an indented one, so recomputing the
    seal from the file gave a different number. Every other D4 record uses this rule, and two
    records that verified differently from the other twenty would be a trap rather than a
    difference.
    """
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode(
        "utf-8"
    )


def _dig(document: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(document, dict) or part not in document:
            return None
        document = document[part]
    return document


def _from_evidence(row: Row) -> dict[str, Any]:
    """A row this command records rather than re-runs, decided by the evidence file itself."""
    assert row.evidence is not None
    name, key = row.evidence
    path = EVIDENCE / name
    if not path.is_file():
        return {
            "status": "skipped",
            "reason": f"{name} is not present, so this row was not decided",
            "evidence": name,
        }
    document = json.loads(path.read_text(encoding="utf-8"))
    if key == "corruption_matrix":
        rows = document.get("corruption_matrix", [])
        passed = bool(rows) and all(item["observed"]["failed_closed"] for item in rows)
        detail: Any = f"{len(rows)} rows, all held" if passed else "a case stayed open"
    else:
        value = _dig(document, key)
        if row.wanted:
            passed = str(value) == row.wanted
            detail = f"{key}={value!r}, expected {row.wanted!r}"
        else:
            # No expected value, so truthiness decides — which is a real check for a boolean
            # and no check at all for a string. `_structural_findings` is what keeps a
            # string-valued row from arriving here.
            passed = bool(value) and not isinstance(value, str)
            detail = f"{key}={value}"
    return {
        "status": "passed" if passed else "failed",
        "evidence": name,
        "evidence_sha256": _digest(path.read_text(encoding="utf-8")),
        "detail": detail,
    }


def _execute(row: Row) -> dict[str, Any]:
    if row.evidence is not None:
        return {"name": row.name, "kind": "recorded", **_from_evidence(row)}

    started = time.monotonic()
    completed = subprocess.run(  # nosec B603 - fixed argv list, shell=False
        list(row.argv),
        capture_output=True,
        text=True,
        check=False,
        cwd=REPOSITORY,
        env={**os.environ, **row.env},
    )
    elapsed = round(time.monotonic() - started, 2)
    output = completed.stdout + completed.stderr
    refused = completed.returncode != 0
    if row.expect == "zero":
        passed = not refused
        reason = "" if passed else output.strip().splitlines()[-1][:200] if output else ""
    else:
        passed = refused and row.because in output
        reason = (
            ""
            if passed
            else f"expected a refusal naming {row.because!r}, got exit {completed.returncode}"
        )
    return {
        "name": row.name,
        "kind": "command",
        "command": " ".join(row.argv),
        "environment_overrides": sorted(row.env),
        "expect": row.expect,
        "expected_reason": row.because,
        "exit_status": completed.returncode,
        "duration_seconds": elapsed,
        "output_sha256": _digest(output),
        "status": "passed" if passed else "failed",
        "detail": reason,
    }


def _disclosures() -> list[dict[str, Any]]:
    """Findings a row records that the release is nonetheless not blocked by, and why.

    Kept apart from the rows so neither can quietly become the other. A disclosure never turns
    a failed row green: `failed_rows` still names it, and the exit status still refuses. What
    this adds is the reason a reader would otherwise have to reconstruct.

    The list is empty on a clean run, and that is the honest shape: a disclosure that outlived
    the finding it explains is a claim about a state the repository has left.
    """
    return []


def _structural_findings(report: dict[str, Any]) -> list[str]:
    """What the record has to be able to be false about, checked where it is written.

    These used to be a test class, and a test that reads this record cannot pass during the run
    that writes it: the matrix runs the whole suite as one of its own rows, so the suite saw the
    *previous* record and the command needed two runs to go green. A release command that is not
    idempotent is a defect in the command, so the checks moved here, where they contribute to
    the exit status instead of to the next run.
    """
    rows = {row["name"]: row for row in report["rows"]}
    findings: list[str] = []

    commands = [row for row in report["rows"] if row["kind"] == "command"]
    if not commands:
        findings.append("no row ran a command, so this matrix measured nothing")
    for row in commands:
        if not row["command"] or row["duration_seconds"] <= 0 or len(row["output_sha256"]) != 64:
            findings.append(f"{row['name']} recorded no measured cost")

    negatives = {name for name, row in rows.items() if row.get("expect") == "nonzero"}
    # D7's six. Asserted rather than derived from ROWS, and that is the point: a required set
    # computed from the rows present can never notice a row that is absent. D6 inherited D5's
    # set verbatim, named a row it did not run, and found out because this check said so.
    required = {
        "predecessor_store_refused",
        "predecessor_database_refused",
        "smoke_refuses_a_non_test_database",
        "campaign_refuses_the_d5_store",
        "campaign_refuses_the_d6_store",
        "campaign_refuses_the_development_pair",
    }
    if not required <= negatives:
        findings.append(f"negative rows missing: {sorted(required - negatives)}")
    for name in sorted(negatives):
        if rows[name]["exit_status"] == 0:
            findings.append(f"{name} was expected to refuse and did not")

    recorded = [row for row in report["rows"] if row["kind"] == "recorded"]
    if not recorded:
        findings.append("no row was decided from committed evidence")
    for row in recorded:
        path = EVIDENCE / str(row.get("evidence", ""))
        if not path.is_file():
            findings.append(f"{row['name']} names evidence that is not committed")
        elif row.get("evidence_sha256") != _digest(path.read_text(encoding="utf-8")):
            findings.append(f"{row['name']} does not bind the bytes it read")

    # A recorded row whose key holds a string and names no expected value is decided by
    # truthiness, which for a string is not a decision. Checked here rather than trusted,
    # because the row that would have needed it in D4 was the one reporting a failed floor.
    for row in ROWS:
        if row.evidence is None or row.wanted or row.evidence[1] == "corruption_matrix":
            continue
        path = EVIDENCE / row.evidence[0]
        if not path.is_file():
            continue
        value = _dig(json.loads(path.read_text(encoding="utf-8")), row.evidence[1])
        if isinstance(value, str):
            findings.append(f"{row.name} reads a string and names no expected value")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=EVIDENCE / "sprint-21d7-verification-matrix.json"
    )
    parser.add_argument("--only", help="run one row by name, for iterating on it")
    arguments = parser.parse_args()

    selected = [row for row in ROWS if not arguments.only or row.name == arguments.only]
    started = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    results = [_execute(row) for row in selected]
    totals = {
        state: sum(1 for item in results if item["status"] == state)
        for state in ("passed", "failed", "skipped")
    }

    report = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W4",
        "item": "S21D7-040",
        "purpose": (
            "Every check expected before release, run once, with its actual exit status. "
            "Negative rows must refuse for their declared reason; nothing is silently skipped."
        ),
        "started_at": started,
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _digest(
            (EVIDENCE / "sprint-21d7-pre-registration.json").read_text(encoding="utf-8")
        ),
        "final_outcomes_inspected": False,
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "database": os.environ.get("COGOS_POSTGRES_DATABASE", "not set"),
            "artifact_root": os.environ.get("COGOS_ARTIFACT_ROOT", "not set"),
        },
        "rows": results,
        "not_carried_from_d6": {
            "rows": [
                "postgres_backup_restart_restore",
                "corruption_and_isolation_matrix",
                "provisioning_and_migration",
                "d7_evidence_report",
            ],
            "why": (
                "the first three read D5's W7 operations record, and neither D6's backlog nor "
                "D7's allocates an operations wave, so there is no evidence for them to read. "
                "The fourth would run a learned.py d7-integrity report and no such command "
                "exists. Naming them is the point: a reader should not have to count rows to "
                "discover which claims this matrix does not make"
            ),
            "what_stands_in_their_place": [
                "six D7 validators under --check, four of which are timestamp-free by "
                "construction so the check is itself the restart-reproduction proof",
                "corpus_complete, the hundred-group corpus validator plus W3's four "
                "replacement groups",
                "the three predecessor integrity reports, which still report over their evidence",
                "three campaign refusals: D5's store, D6's store and the development pair",
                "twelve rows recorded from sealed W2 and W3 evidence, including the live "
                "activation's three conditions",
            ],
            "what_this_matrix_still_does_not_cover": (
                "the restart half of condition 26 is not re-run here. It needs a database "
                "container restart between processes, which this matrix has no environment to "
                "perform; `lifecycle_conditions_met` records the sealed result instead, and the "
                "record it reads names both restarts and the four process ids"
            ),
        },
        "totals": {**totals, "rows": len(results)},
        "every_row_decided": totals["skipped"] == 0,
        "failed_rows": [item["name"] for item in results if item["status"] == "failed"],
        "disclosures": _disclosures(),
        "skipped_rows": [item["name"] for item in results if item["status"] == "skipped"],
    }
    report["structural_findings"] = _structural_findings(report)
    seal = hashlib.sha256(_canonical(report)).hexdigest()

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(_canonical({**report, "integrity_content_hash": seal}))
    report["integrity_content_hash"] = seal
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "totals": report["totals"],
                "failed_rows": report["failed_rows"],
                "skipped_rows": report["skipped_rows"],
                "structural_findings": report["structural_findings"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return (
        0
        if not report["failed_rows"]
        and report["every_row_decided"]
        and not report["structural_findings"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
