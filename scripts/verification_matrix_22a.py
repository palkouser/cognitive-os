#!/usr/bin/env python
"""S22A-050: every check expected before release, run once, with its actual exit status.

    scripts/verification_matrix_22a.py [--output docs/.../sprint-22a-verification-matrix.json]

One row per check. Each records what was run, what it was expected to do, what it actually
did, how long it took, and the SHA-256 of its combined output — so a row that passes today and
fails tomorrow can be compared without anyone having kept the log.

The three rules are the D-series matrix's, unchanged and incorporated deliberately:

*Negative rows must fail for their expected reason.* A row declared `expect: nonzero` is a
finding when it succeeds, and a refusal carrying a different message is also a finding. A
destructive check that passes because it never ran is the failure mode this exists to prevent.

*Nothing is silently skipped.* A row whose preconditions are absent is recorded as `skipped`
with the reason, and the totals count it.

*The record checks itself, here.* `_structural_findings` runs where the record is written
rather than in a test module, because the matrix runs the whole suite as one of its rows: a
test reading this record during that run would read the *previous* one, and a release command
that needs two runs to go green is a defect in the command.

It takes no environment. The matrix runs the whole suite as one of its rows, and D4-W7-F1's
operational half is that a suite run with a sprint environment file sourced truncates the
sprint's own evidence store. Every row that needs a store names one itself.

What 22A's matrix carries that D7's could not
---------------------------------------------

*Seven `--check` validators, and one of them replays.* 22A sealed a record per wave, each
re-derivable in a fresh process. The seventh, `exit_criteria_22a.py --check`, executes all six
benchmark manifests as part of its own check — so replay is a *measured* row of this matrix by
way of that row, not a number copied out of a wave record. There are deliberately no separate
replay rows: running the same six manifests twice in one matrix would report one fact as two.

*A chronology row over the whole sprint.* Every wave record must carry the published
pre-registration's hash and postdate it. One row asks that of all of them at once, so a record
back-dated into the sprint is a failed row rather than a reading exercise.

*Two negative rows, not six.* 22A's refusals are package-level — sixty-five kilobytes,
malformed JSON, a released id at a new revision, a share the target never declared — and every
one of them refuses *inside* a process that needs 22A's store to prove nothing was written.
They are recorded here from the sealed rejection suite instead, and the two command-level
negatives are the ones that hold without a store: the pilot chain refusing to guess a store,
and the released smoke fence refusing a database that is not a test database. That fence is
what stands between this matrix's own full-suite row and `cognitive_os_s22a_*`.
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
EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-22" / "evidence"
RUFF_CONFIG = "ruff.cognitive-os.toml"

#: Every record the sprint published after its pre-registration, in the order it published
#: them. The chronology row asks all of them at once; a record added later and left off this
#: list is a record nothing checks, so `_structural_findings` compares it against the rows.
WAVE_RECORDS = (
    "sprint-22a-w1-seam.json",
    "sprint-22a-w2-pilot.json",
    "sprint-22a-w3-pilot.json",
    "sprint-22a-exit-criteria.json",
)


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
    #: string or a number: a row decided by truthiness reports `0` as a failure and any
    #: wording at all as a pass.
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
    Row(
        "domain_slice",
        ("uv", "run", "pytest", "-q", "tests/cognitive_os/domains", "tests/cognitive_os/domain"),
    ),
    # ------------------------------------------------------------------ contracts and policy
    Row("schema_export", ("uv", "run", "python", "-m", "cognitive_os.schemas.export", "--check")),
    Row("repository_language", ("bash", "scripts/check_repository_language.sh")),
    # This matrix's own output is excluded, and only its own: a file whose hashes are written
    # at the end of a run cannot be scanned by the run that writes it.
    Row(
        "secrets_scan",
        (
            "bash",
            "-c",
            "git ls-files -z | grep -zv sprint-22a-verification-matrix.json | "
            "xargs -0 uv run detect-secrets-hook --baseline .secrets.baseline",
        ),
    ),
    Row("dependency_audit", ("uv", "run", "pip-audit")),
    Row("packaging_build", ("uv", "build")),
    Row("wheel_installation", ("bash", "scripts/verify_distribution.sh")),
    Row("editable_installation", ("bash", "scripts/verify_editable_install.sh")),
    # ------------------------------------------------- the released cross-domain gates
    # 22A moved domain identity out of an enum. These two are the released surface's own
    # offline gates, and they answer the question a snapshot hash cannot: whether the four
    # released domains still solve and still govern.
    Row("domain_smoke", ("uv", "run", "python", "scripts/domain_smoke_test.py")),
    Row("domain_health", ("uv", "run", "python", "scripts/domain.py", "health")),
    # ------------------------------------------------------- 22A's own released validators
    Row("pre_registration", ("uv", "run", "python", "scripts/pre_registration_22a.py", "--check")),
    Row(
        "chronology",
        (
            "uv",
            "run",
            "python",
            "scripts/pre_registration_22a.py",
            "--check-chronology",
            "--later",
            *(f"docs/sprints/sprint-22/evidence/{name}" for name in WAVE_RECORDS),
        ),
    ),
    Row("w0_decisions", ("uv", "run", "python", "scripts/decisions_22a.py", "--check")),
    Row("w2_decisions", ("uv", "run", "python", "scripts/decisions_22a_w2.py", "--check")),
    Row("w1_seam", ("uv", "run", "python", "scripts/seam_22a.py", "--check")),
    Row("w2_pilot", ("uv", "run", "python", "scripts/pilot_22a.py", "--check")),
    Row("w3_pilot", ("uv", "run", "python", "scripts/chemistry_22a.py", "--check")),
    # The replay row, by another name: this check runs all six benchmark manifests itself.
    Row("exit_criteria", ("uv", "run", "python", "scripts/exit_criteria_22a.py", "--check")),
    # ------------------------------------------------------------------ negative rows
    # The pilot chain refuses to guess a store. S21D5-W0-F1 is the reason it is a refusal
    # rather than a default: a chain that fell back to the development pair would have written
    # a pilot registration into a store nobody nominated.
    Row(
        "chain_refuses_an_unnominated_store",
        ("uv", "run", "python", "scripts/pilot_chain_22a.py", "register", "--pilot", "mechanics"),
        expect="nonzero",
        because="COGOS_DATABASE_URL and COGOS_ARTIFACT_ROOT are required",
        env={"COGOS_DATABASE_URL": "", "COGOS_ARTIFACT_ROOT": ""},
    ),
    # The released truncation fence, carried from D7 for 22A's own reason: this matrix runs
    # the whole suite, 22A's store is `cognitive_os_s22a_*`, and this is the guard that keeps
    # a smoke run from truncating whatever database happens to be configured.
    Row(
        "smoke_refuses_a_non_test_database",
        ("uv", "run", "python", "scripts/learned.py", "smoke", "--confirm-isolated"),
        expect="nonzero",
        because="isolated *_test database",
        env={
            "COGOS_DATABASE_ADMIN_URL": "postgresql+asyncpg://u@h/cognitive_os_dev",
            "COGOS_ARTIFACT_ROOT": "/tmp/s22a-matrix-never-opened",  # nosec B108
        },
    ),
    # ------------------------------------------------- rows recorded from committed evidence
    Row(
        "all_four_exit_criteria_met",
        (),
        evidence=("sprint-22a-exit-criteria.json", "verdicts.all_four_met"),
    ),
    Row(
        "sprint_outcome",
        (),
        evidence=("sprint-22a-exit-criteria.json", "outcome"),
        wanted="pass",
    ),
    Row(
        "every_released_domain_replayed",
        (),
        evidence=("sprint-22a-exit-criteria.json", "replay.every_released_domain_replayed"),
    ),
    Row(
        "core_controller_byte_identical_to_the_predecessor",
        (),
        evidence=(
            "sprint-22a-exit-criteria.json",
            "unchanged_since_the_predecessor.core_controller."
            "every_file_identical_to_the_predecessor",
        ),
    ),
    Row(
        "storage_schema_byte_identical_to_the_predecessor",
        (),
        evidence=(
            "sprint-22a-exit-criteria.json",
            "unchanged_since_the_predecessor.storage_schema."
            "every_file_identical_to_the_predecessor",
        ),
    ),
    # Zero, named rather than left to truthiness: zero is falsy, and a row decided by
    # truthiness here would report the silo regression's success as a failure.
    Row(
        "two_pilots_added_no_domainkind_branch",
        (),
        evidence=("sprint-22a-w3-pilot.json", "silo_regression.added_by_both_pilots"),
        wanted="0",
    ),
    Row(
        "released_snapshot_unchanged_with_both_pilots",
        (),
        evidence=("sprint-22a-w3-pilot.json", "backward_compatibility.released_snapshot_unchanged"),
    ),
    Row(
        "every_hostile_package_refused",
        (),
        evidence=("sprint-22a-w3-pilot.json", "rejection_suite.every_case_refused"),
    ),
    Row(
        "nothing_registered_halfway",
        (),
        evidence=("sprint-22a-w3-pilot.json", "rejection_suite.nothing_registered_halfway"),
    ),
    Row(
        "concepts_visible_from_a_domain_that_owns_none_of_them",
        (),
        evidence=("sprint-22a-w3-pilot.json", "pilots.physics_owns_none_of_them"),
    ),
    # W2 handed this to W4's matrix by name, and a boundary is only a boundary while somebody
    # keeps checking that it was not crossed.
    Row(
        "the_cognitive_controller_was_not_reached",
        (),
        evidence=("sprint-22a-w2-pilot.json", "boundaries.not_reached.what"),
        wanted="the Cognitive Controller's own state machine",
    ),
    Row(
        "w2_released_claims_hold",
        (),
        evidence=("sprint-22a-w2-pilot.json", "every_released_claim_holds"),
    ),
    Row(
        "w1_released_claims_hold",
        (),
        evidence=("sprint-22a-w1-seam.json", "every_released_claim_holds"),
    ),
    Row(
        "pre_registration_measured_nothing",
        (),
        evidence=("sprint-22a-pre-registration.json", "measured_values"),
        wanted="0",
    ),
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(value: object) -> bytes:
    """The bytes that are hashed are the bytes that are written."""
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
    value = _dig(document, key)
    if row.wanted:
        passed = str(value) == row.wanted
        detail = f"{key}={value!r}, expected {row.wanted!r}"
    else:
        # No expected value, so truthiness decides — a real check for a boolean and no check
        # at all for anything else. `_structural_findings` keeps those rows from arriving here.
        passed = value is True
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

    A disclosure never turns a failed row green: `failed_rows` still names it and the exit
    status still refuses. Empty on a clean run, which is the honest shape — a disclosure that
    outlived its finding is a claim about a state the repository has left.
    """
    return []


def _structural_findings(report: dict[str, Any]) -> list[str]:
    """What the record has to be able to be false about, checked where it is written."""
    rows = {row["name"]: row for row in report["rows"]}
    findings: list[str] = []

    commands = [row for row in report["rows"] if row["kind"] == "command"]
    if not commands:
        findings.append("no row ran a command, so this matrix measured nothing")
    for row in commands:
        if not row["command"] or row["duration_seconds"] <= 0 or len(row["output_sha256"]) != 64:
            findings.append(f"{row['name']} recorded no measured cost")

    negatives = {name for name, row in rows.items() if row.get("expect") == "nonzero"}
    # Asserted rather than derived from ROWS: a required set computed from the rows present
    # can never notice a row that is absent.
    required = {"chain_refuses_an_unnominated_store", "smoke_refuses_a_non_test_database"}
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

    # A recorded row whose key does not hold `True` and names no expected value is decided by
    # truthiness, which for a string or a number is not a decision.
    for row in ROWS:
        if row.evidence is None or row.wanted:
            continue
        path = EVIDENCE / row.evidence[0]
        if not path.is_file():
            continue
        value = _dig(json.loads(path.read_text(encoding="utf-8")), row.evidence[1])
        if not isinstance(value, bool):
            findings.append(f"{row.name} reads a non-boolean and names no expected value")

    # The chronology row is only as wide as the list it was given, and a wave record that is
    # published but never chronology-checked is exactly the gap W4-F1 warns about.
    #
    # This record is excluded, and only this one. It is written *after* the row that would
    # check it, so a run that demanded its own presence on the list would pass the first time
    # and fail every time after — the same idempotence defect D5 hit by putting these checks in
    # a test module, arriving here by a different door. See W4-F3.
    published = sorted(
        path.name
        for path in EVIDENCE.glob("sprint-22a-*.json")
        if path.name != "sprint-22a-verification-matrix.json"
        and "pre_registration_sha256" in json.loads(path.read_text(encoding="utf-8"))
    )
    unchecked = sorted(set(published) - set(WAVE_RECORDS))
    if unchecked:
        findings.append(
            f"records carrying a pre-registration hash but not chronology-checked: {unchecked}"
        )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=EVIDENCE / "sprint-22a-verification-matrix.json"
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
        "sprint": "22A",
        "wave": "W4",
        "item": "S22A-050",
        "purpose": (
            "Every check expected before release, run once, with its actual exit status. "
            "Negative rows must refuse for their declared reason; nothing is silently skipped."
        ),
        "started_at": started,
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _digest(
            (EVIDENCE / "sprint-22a-pre-registration.json").read_text(encoding="utf-8")
        ),
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "database": os.environ.get("COGOS_POSTGRES_DATABASE", "not set"),
            "artifact_root": os.environ.get("COGOS_ARTIFACT_ROOT", "not set"),
        },
        "rows": results,
        "replay": {
            "run_by": "exit_criteria",
            "why_no_separate_rows": (
                "exit_criteria_22a.py --check executes all six benchmark manifests as part of "
                "its own check. Separate replay rows here would run the same six manifests a "
                "second time and report one fact as two"
            ),
            "manifests": 6,
        },
        "not_carried_from_the_d_series_matrix": {
            "rows": [
                "corpus_complete",
                "d3_evidence_report_still_green",
                "d4_evidence_report_still_green",
                "d5_evidence_report_still_green",
                "campaign_refuses_the_d5_store",
                "campaign_refuses_the_d6_store",
                "campaign_refuses_the_development_pair",
            ],
            "why": (
                "every one of them reads a learning-surface store or a certification corpus. "
                "22A registers domains and touches nothing that learns, so those rows would "
                "report on a surface this sprint did not change. Naming them is the point: a "
                "reader should not have to count rows to discover which claims are not made"
            ),
            "what_stands_in_their_place": [
                "seven 22A validators under --check, one of which executes all six replays",
                "a chronology row over every record that carries the pre-registration's hash",
                "the two released cross-domain gates, domain_smoke_test and domain.py health",
                "fourteen rows recorded from sealed W0 through W4 evidence, including the "
                "silo regression's zero and the boundary W2 handed to this matrix by name",
            ],
            "what_this_matrix_still_does_not_cover": (
                "the hostile-package suite is not re-run here. Refusing a package is only "
                "evidence if the package could otherwise have reached a store, so the suite "
                "runs against 22A's database; `every_hostile_package_refused` and "
                "`nothing_registered_halfway` record W3's result and bind its bytes instead"
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
