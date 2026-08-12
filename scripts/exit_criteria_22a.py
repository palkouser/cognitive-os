#!/usr/bin/env python
"""S22A-051: the sprint's four exit criteria, decided where they can be measured.

    scripts/exit_criteria_22a.py [--check]

The four are the allocation's, not this script's:

1. both new domains register **without changing the core controller or storage schema**;
2. cross-domain items are **stored once and exposed through multiple governed views**;
3. **global and per-domain replay remain green**;
4. **invalid domain packages fail closed**.

Each criterion is decided in one of two ways, and the record says which for every claim.
A *measured* claim is recomputed here, in this process, from the tree or from a command this
script runs. A *recorded* claim is read from a sealed wave record and binds that record's
SHA-256, because the thing it claims happened in a process this one cannot re-enter — a
registration the store will not accept twice, a solve that ran against a database.

Three things this script does that the wave records it reads did not.

*It measures "the core controller did not change" instead of asserting it.* W2 and W3 both
wrote `core_controller_changed: false` as a literal, which is a sentence rather than a check.
Here the eleven controller modules and the fifteen migration files are compared byte for byte
against the predecessor commit the baseline sealed — and the *set* of them is sealed too, so a
new controller module or a sixteenth migration is a finding rather than an invisible widening.
(That is W2-F1 read forwards: a check may glob a directory as long as the glob's result is
compared against a sealed list rather than trusted.)

*It executes the replays rather than carrying their numbers.* W2's sealer recorded four
manifests with a note that re-running them inside a `--check` would fail for want of a
database. The note is wrong: every one of these manifests is credential-free by construction,
and six of them run in about twelve seconds. So they run here, in both `--write` and
`--check`, and the record seals each manifest's own hash with the case count and pass rate it
produced (W3-F1: a carried number proves someone typed it).

*It replays the coding domain.* "Per-domain replay" over four released domains was, in every
wave until this one, four manifests covering three domains — `sprint20-domain-*` carries
logic, mathematics and physics, and the coding domain's cases live in `sprint22-coding-*`,
which no 22A wave ran. See W4-F1.

The record is written with a timestamp but every claim in it is timestamp-free, so `--check`
in a fresh process re-derives the measurements and re-verifies the seal.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess  # nosec B404 - fixed argv lists of repository commands, never a shell
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22a-exit-criteria.json"
BASELINE = EVIDENCE / "sprint-22a-baseline.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22a-pre-registration.json"
SURVEY = EVIDENCE / "sprint-22a-domain-survey.json"
W2_RECORD = EVIDENCE / "sprint-22a-w2-pilot.json"
W3_RECORD = EVIDENCE / "sprint-22a-w3-pilot.json"

MIGRATIONS = REPO / "infra/postgres/alembic/versions"

#: Every manifest that replays a released domain or the surface 22A had to leave alone.
#: The coding pair is here for the first time in this sprint; see W4-F1.
REPLAYS: tuple[tuple[str, str], ...] = (
    ("sprint20-domain-ci", "domain-pilot"),
    ("sprint20-domain-seed", "domain-pilot"),
    ("sprint22-coding-ci", "domain-pilot"),
    ("sprint22-coding-seed", "domain-pilot"),
    ("sprint21c1-learned-ci", "learned-replay"),
    ("sprint21c1-learned-seed", "learned-replay"),
)

#: What each manifest covers, so "per-domain" is a claim a reader can check rather than a word.
REPLAY_COVERS = {
    "sprint20-domain-ci": ["logic", "mathematics", "physics"],
    "sprint20-domain-seed": ["logic", "mathematics", "physics"],
    "sprint22-coding-ci": ["coding"],
    "sprint22-coding-seed": ["coding"],
    "sprint21c1-learned-ci": ["the correction surface 22A must not touch"],
    "sprint21c1-learned-seed": ["the correction surface 22A must not touch"],
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return body


def _script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, REPO / f"scripts/{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _controller_modules() -> list[str]:
    """Every module under `src/cognitive_os` whose name says it is a controller.

    Globbed rather than typed, and then sealed: `_frozen_files` compares this list against
    the one the record carries, so a controller module that appears after the release is a
    refusal instead of a row nobody wrote.
    """
    return sorted(
        str(path.relative_to(REPO))
        for path in (REPO / "src/cognitive_os").rglob("*controller*.py")
        if "__pycache__" not in path.parts
    )


def _migration_files() -> list[str]:
    return sorted(str(path.relative_to(REPO)) for path in MIGRATIONS.glob("[0-9]*.py"))


def _predecessor_bytes(commit: str, path: str) -> bytes:
    completed = subprocess.run(  # nosec B603 B607 - fixed argv list, shell=False
        ["git", "show", f"{commit}:{path}"],
        capture_output=True,
        check=True,
        cwd=REPO,
    )
    return completed.stdout


def _frozen_files(commit: str) -> dict[str, Any]:
    """The controller and the storage schema, compared to the commit 22A branched from.

    At `--write` the comparison is against the predecessor's blobs, read out of git. At
    `--check` there is no git: the sealed per-file hash *is* the predecessor's hash, so
    re-hashing the working tree and comparing to it asks exactly the same question in a
    process that may be a shallow checkout with no history to ask git about.
    """
    groups: dict[str, Any] = {}
    for name, paths in (
        ("core_controller", _controller_modules()),
        ("storage_schema", _migration_files()),
    ):
        files = {}
        for path in paths:
            current = (REPO / path).read_bytes()
            files[path] = {
                "sha256": _sha256(current),
                "predecessor_sha256": _sha256(_predecessor_bytes(commit, path)),
            }
        groups[name] = {
            "files": files,
            "file_count": len(files),
            "every_file_identical_to_the_predecessor": all(
                item["sha256"] == item["predecessor_sha256"] for item in files.values()
            ),
        }
    return groups


def _check_frozen_files(record: dict[str, Any]) -> list[str]:
    """Re-derive the frozen-file claim without git, and without trusting the sealed set."""
    findings: list[str] = []
    current = {"core_controller": _controller_modules(), "storage_schema": _migration_files()}
    for name, group in record["unchanged_since_the_predecessor"].items():
        if name not in current:
            continue
        sealed = sorted(group["files"])
        if sealed != current[name]:
            added = sorted(set(current[name]) - set(sealed))
            removed = sorted(set(sealed) - set(current[name]))
            findings.append(f"the {name} file set moved: added {added}, removed {removed}")
            continue
        for path, item in group["files"].items():
            if _sha256((REPO / path).read_bytes()) != item["predecessor_sha256"]:
                findings.append(f"{path} is no longer the predecessor's bytes")
    return findings


def _replay(directory: Path) -> dict[str, Any]:
    """Run every manifest and read its own report back. Executed, not remembered."""
    results: dict[str, Any] = {}
    for name, mode in REPLAYS:
        target = directory / name
        completed = subprocess.run(  # nosec B603 - fixed argv list, shell=False
            [
                sys.executable,
                str(REPO / "scripts/benchmark_run.py"),
                "--manifest",
                str(REPO / f"benchmarks/manifests/{name}.yaml"),
                "--mode",
                mode,
                "--report-directory",
                str(target),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO,
        )
        reports = sorted(target.glob("*.json"))
        body = _load(reports[0]) if len(reports) == 1 else {}
        metrics = body.get("aggregate_metrics", {})
        results[name] = {
            "mode": mode,
            "covers": REPLAY_COVERS[name],
            "exit_status": completed.returncode,
            "manifest_sha256": _sha256((REPO / f"benchmarks/manifests/{name}.yaml").read_bytes()),
            "manifest_hash_reported": body.get("manifest_hash"),
            "status": body.get("status"),
            "cases": int(metrics.get("case_count", 0)),
            "pass_rate": metrics.get("case_pass_rate"),
            "green": completed.returncode == 0
            and body.get("status") == "completed"
            and metrics.get("case_pass_rate") == 1.0,
        }
    released = {"logic", "mathematics", "physics", "coding"}
    covered = {item for name in results for item in REPLAY_COVERS[name]}
    return {
        "manifests": results,
        "manifest_count": len(results),
        "cases": sum(int(item["cases"]) for item in results.values()),
        "every_manifest_green": all(item["green"] for item in results.values()),
        "released_domains_replayed": sorted(released & covered),
        "every_released_domain_replayed": released <= covered,
        "executed_here": (
            "each manifest is run as a subprocess by this script, in both --write and "
            "--check. Every one is credential-free by construction, which is what makes "
            "executing them cheaper than carrying their numbers forward"
        ),
    }


def _coupling() -> dict[str, Any]:
    counted = _script("domain_survey_22a")._enum_coupling()
    sealed = _load(SURVEY)["enum_coupling"]
    at_w3 = _load(W3_RECORD)["silo_regression"]["at_w3"]
    return {
        "at_w0": {"modules": sealed["module_count"], "references": sealed["reference_count"]},
        "at_w3": at_w3,
        "at_w4": {
            "modules": counted["module_count"],
            "references": counted["reference_count"],
        },
        "grew_since_w0": counted["reference_count"] > sealed["reference_count"],
        "grew_since_w3": counted["reference_count"] > at_w3["references"],
        "added_by_two_pilots": counted["reference_count"] - at_w3["references"],
    }


def _released_behaviour() -> dict[str, Any]:
    """The four released domains, measured in a process where both pilots are registered."""
    chemistry = _script("chemistry_22a")
    descriptors = chemistry._with_both_pilots_registered()
    compatibility = _script("pilot_22a")._compatibility(descriptors[-1])
    return {
        "released_snapshot_hash": compatibility["released_snapshot_hash"],
        "released_snapshot_unchanged": compatibility["released_snapshot_unchanged"],
        "whole_registry_snapshot_differs": compatibility["whole_registry_snapshot_differs"],
        "released_entries": compatibility["released_entries"],
        "descriptor_hashes_unchanged": sum(
            1 for item in compatibility["descriptors"].values() if item["unchanged"]
        ),
        "descriptor_count": len(compatibility["descriptors"]),
        "pilots_registered": [item.domain_id for item in descriptors],
    }


def _bound(path: Path, keys: tuple[str, ...]) -> dict[str, Any]:
    """A claim this process cannot re-run, read from the record that made it and bound to it."""
    body = _load(path)
    return {
        "record": path.name,
        "sha256": _sha256(path.read_bytes()),
        "values": {key: body[key] for key in keys if key in body},
    }


def _views() -> dict[str, Any]:
    w2 = _load(EVIDENCE / "sprint-22a-w2-pilot-views.json")
    w3 = _load(EVIDENCE / "sprint-22a-w3-pilot-views.json")
    # Shared, not owned. The pilots own six concepts and share four; the two they keep are as
    # much a part of "governed views" as the four they expose, because a view that showed them
    # anyway would not be governed by the sharer's declaration.
    shared = dict(w3["shared_concepts"])
    in_the_target_view = sorted(item["concept_id"] for item in w3["views"]["physics"])
    return {
        "target_view": in_the_target_view,
        "target_view_is_exactly_the_shared_set": in_the_target_view == sorted(shared),
        "shared_concepts": sorted(shared),
        "concept_count": len(shared),
        "concepts_owned_by_the_pilots": len(w3["owners"]),
        "concepts_kept_private": sorted(set(w3["owners"]) - set(shared)),
        "owner_count": len(set(shared.values())),
        "every_shared_concept_visible_from_the_target": (
            w2["every_shared_concept_visible_from_physics"]
            and w3["every_shared_concept_visible_from_physics"]
        ),
        "stored_once": w3["stored_once"],
        "same_content_hash_in_both_views": (
            w2["same_content_hash_in_both_views"] and w3["same_content_hash_in_both_views"]
        ),
        "physics_owns_none_of_them": w3["physics_owns_none_of_them"],
        "physics_sees_two_pilots": w3["physics_sees_two_pilots"],
        "bound": [
            _bound(
                EVIDENCE / "sprint-22a-w2-pilot-views.json",
                ("every_shared_concept_visible_from_physics", "same_content_hash_in_both_views"),
            ),
            _bound(
                EVIDENCE / "sprint-22a-w3-pilot-views.json",
                (
                    "every_shared_concept_visible_from_physics",
                    "physics_sees_two_pilots",
                    "physics_owns_none_of_them",
                ),
            ),
        ],
    }


def _fail_closed() -> dict[str, Any]:
    rejections = _load(EVIDENCE / "sprint-22a-w3-pilot-rejections.json")
    return {
        "case_count": rejections["case_count"],
        "layers": rejections["layers"],
        "every_case_refused": rejections["every_case_refused"],
        "nothing_registered_halfway": rejections["nothing_registered_halfway"],
        "entries_unchanged_overall": rejections["entries_unchanged_overall"],
        "sealed_cases_executed": rejections["sealed_cases_executed"],
        "bound": [
            _bound(
                EVIDENCE / "sprint-22a-w3-pilot-rejections.json",
                ("every_case_refused", "nothing_registered_halfway", "entries_unchanged_overall"),
            ),
            _bound(
                EVIDENCE / "sprint-22a-w1-slice-refusals.json",
                ("every_case_refused", "registrations_after"),
            ),
            _bound(
                EVIDENCE / "sprint-22a-w1-slice-tamper.json",
                ("refused", "named_the_domain", "still_parses_as_a_package"),
            ),
        ],
    }


def _pilots() -> dict[str, Any]:
    w3 = _load(W3_RECORD)["pilots"]
    return {
        "registered": sorted(w3["registered"]),
        "pilot_count": w3["pilot_count"],
        "problem_types_total": w3["problem_types_total"],
        "every_one_resolves_to_itself": all(
            item["resolves_to_itself"] for item in w3["registered"].values()
        ),
        "every_one_is_a_pilot": all(
            item["lifecycle"] == "pilot" for item in w3["registered"].values()
        ),
        "bound": [
            _bound(W2_RECORD, ("every_released_claim_holds",)),
            _bound(W3_RECORD, ("every_released_claim_holds",)),
        ],
    }


def _criteria(
    frozen: dict[str, Any],
    coupling: dict[str, Any],
    behaviour: dict[str, Any],
    replay: dict[str, Any],
    views: dict[str, Any],
    fail_closed: dict[str, Any],
    pilots: dict[str, Any],
) -> dict[str, Any]:
    return {
        "registers_without_changing_the_core_controller_or_storage_schema": {
            "statement": (
                "both new domains register without changing the core controller or the "
                "storage schema"
            ),
            "decided_by": "measured",
            "checks": {
                "two_pilots_registered": pilots["pilot_count"] == 2,
                "core_controller_byte_identical": frozen["core_controller"][
                    "every_file_identical_to_the_predecessor"
                ],
                "migrations_byte_identical": frozen["storage_schema"][
                    "every_file_identical_to_the_predecessor"
                ],
                "migration_head_is_still_0015": _migration_files()[-1].endswith(
                    "0015_create_provider_output_governance.py"
                ),
                "no_domainkind_branch_added": not coupling["grew_since_w3"],
                "released_snapshot_unchanged": behaviour["released_snapshot_unchanged"],
            },
            "counts": {
                "controller_modules_checked": frozen["core_controller"]["file_count"],
                "migration_files": frozen["storage_schema"]["file_count"],
                "domainkind_references": coupling["at_w4"]["references"],
                "added_by_two_pilots": coupling["added_by_two_pilots"],
            },
            "what_did_change_and_why_it_is_not_the_schema": (
                "one new event contract, domain.descriptor_registered, and the events module "
                "that emits it. An event type is a contract over a stream the released store "
                "already has; it allocates no table, no column and no enum member, which is "
                "what the criterion forbids"
            ),
        },
        "cross_domain_items_stored_once_and_exposed_through_governed_views": {
            "statement": (
                "cross-domain items are stored once and exposed through multiple governed views"
            ),
            "decided_by": "recorded",
            "checks": {
                "more_than_one_owner": views["owner_count"] > 1,
                "every_shared_concept_visible_from_the_target": views[
                    "every_shared_concept_visible_from_the_target"
                ],
                "same_content_hash_in_both_views": views["same_content_hash_in_both_views"],
                "target_owns_none_of_them": views["physics_owns_none_of_them"],
                "target_sees_both_pilots": views["physics_sees_two_pilots"],
                # The two concepts the pilots kept are absent from the target's view, checked
                # against the view itself rather than inferred from the sharing declaration.
                "an_undeclared_concept_stays_private": (
                    bool(views["concepts_kept_private"])
                    and views["target_view_is_exactly_the_shared_set"]
                ),
            },
            "counts": {
                "concepts_shared": views["concept_count"],
                "concepts_owned": views["concepts_owned_by_the_pilots"],
                "owners": views["owner_count"],
            },
            "why_recorded": (
                "the views are computed over a catalogue built from registrations that live in "
                "22A's store; the processes that read them were W2's and W3's, and their "
                "records are bound here by hash"
            ),
        },
        "global_and_per_domain_replay_green": {
            "statement": "global and per-domain replay remain green",
            "decided_by": "measured",
            "checks": {
                "every_manifest_green": replay["every_manifest_green"],
                "every_released_domain_replayed": replay["every_released_domain_replayed"],
            },
            "counts": {
                "manifests": replay["manifest_count"],
                "cases": replay["cases"],
            },
            "released_domains_replayed": replay["released_domains_replayed"],
        },
        "invalid_domain_packages_fail_closed": {
            "statement": "invalid domain packages fail closed",
            "decided_by": "recorded",
            "checks": {
                "every_case_refused": fail_closed["every_case_refused"],
                "nothing_registered_halfway": fail_closed["nothing_registered_halfway"],
                "entries_unchanged_overall": fail_closed["entries_unchanged_overall"],
                "refused_at_more_than_one_layer": len(fail_closed["layers"]) > 1,
            },
            "counts": {"cases": fail_closed["case_count"], "layers": len(fail_closed["layers"])},
            "layers": fail_closed["layers"],
            "why_recorded": (
                "a refusal is only evidence if the thing it refused could otherwise have "
                "reached a store, so the suite runs against 22A's store; W3's record is bound "
                "here, together with W1's slice refusals and its tampered-byte case"
            ),
        },
    }


def _verdicts(criteria: dict[str, Any]) -> dict[str, Any]:
    """Every check is a boolean and every one of them has to be true.

    Counts live in `counts`, deliberately: D4's matrix decided a string-valued row by
    truthiness and would have passed on a wording that reported the opposite result. A
    criterion whose `checks` contained a number would be deciding a release on `!= 0`.
    """
    for name, body in criteria.items():
        for key, value in body["checks"].items():
            if not isinstance(value, bool):
                raise SystemExit(f"{name}.{key} is not a boolean, so it decides nothing")
    met = {name: all(body["checks"].values()) for name, body in criteria.items()}
    return {
        "by_criterion": met,
        "met": sum(1 for value in met.values() if value),
        "of": len(met),
        "all_four_met": all(met.values()),
    }


def _write() -> None:
    predecessor = _load(BASELINE)["branch"]["merge_base_with_origin_main"]
    frozen = _frozen_files(predecessor)
    coupling = _coupling()
    behaviour = _released_behaviour()
    with tempfile.TemporaryDirectory(prefix="s22a-w4-replay-") as directory:
        replay = _replay(Path(directory))
    views = _views()
    fail_closed = _fail_closed()
    pilots = _pilots()
    criteria = _criteria(frozen, coupling, behaviour, replay, views, fail_closed, pilots)
    verdicts = _verdicts(criteria)

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W4",
        "items": ["S22A-050", "S22A-051", "S22A-052"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "predecessor_commit": predecessor,
        "predecessor_read_from": {
            "record": BASELINE.name,
            "sha256": _sha256(BASELINE.read_bytes()),
        },
        "criteria": criteria,
        "verdicts": verdicts,
        "unchanged_since_the_predecessor": frozen,
        "enum_coupling": coupling,
        "released_behaviour": behaviour,
        "replay": replay,
        "governed_views": views,
        "fail_closed": fail_closed,
        "pilots": pilots,
        "outcome": "pass" if verdicts["all_four_met"] else "stop",
        "outcome_tag": (
            "sprint-22a-domain-baseline"
            if verdicts["all_four_met"]
            else "sprint-22a-evidence-baseline"
        ),
        "tag_not_created_here": (
            "this script decides the criteria; it creates no tag, no merge and no push. The "
            "tag is created once, on the commit exact-head CI passed on, after that CI"
        ),
        "what_a_pass_here_does_not_mean": [
            "the Cognitive Controller's own state machine was reached: it was not, and W2's "
            "record names the released contract that would have to widen first",
            "a pilot has a persisted-run path: W2-A1's three-domain CHECK constraint still "
            "stands, and widening it is the migration this sprint forbids",
            "two pilots make the registry general: both lean on unit-carrying deterministic "
            "verification, which is the substrate the released physics domain built",
        ],
    }
    seal = _sha256(_canonical(record))
    OUTPUT.write_bytes(_canonical({**record, "integrity_content_hash": seal}))
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "verdicts": verdicts,
                "replay": {
                    "manifests": replay["manifest_count"],
                    "cases": replay["cases"],
                    "green": replay["every_manifest_green"],
                },
                "outcome": record["outcome"],
                "integrity_content_hash": seal,
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check() -> None:
    record = _load(OUTPUT)
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    if _sha256(_canonical(body)) != record["integrity_content_hash"]:
        raise SystemExit(f"{OUTPUT.name} integrity hash does not match its content")
    if record["pre_registration_sha256"] != _sha256(PRE_REGISTRATION.read_bytes()):
        raise SystemExit("the exit-criteria record does not carry the published pre-registration")

    findings = _check_frozen_files(record)
    for group in (record["governed_views"], record["fail_closed"], record["pilots"]):
        for item in group["bound"]:
            path = EVIDENCE / item["record"]
            if _sha256(path.read_bytes()) != item["sha256"]:
                findings.append(f"{item['record']} changed after this record bound it")

    coupling = _coupling()
    if coupling["at_w4"] != record["enum_coupling"]["at_w4"]:
        findings.append("the DomainKind coupling census no longer reproduces its sealed count")
    behaviour = _released_behaviour()
    if (
        behaviour["released_snapshot_hash"]
        != record["released_behaviour"]["released_snapshot_hash"]
    ):
        findings.append("the released snapshot hash moved with both pilots registered")
    if behaviour["descriptor_hashes_unchanged"] != behaviour["descriptor_count"]:
        findings.append("a released domain no longer derives its sealed descriptor hash")

    with tempfile.TemporaryDirectory(prefix="s22a-w4-replay-") as directory:
        replay = _replay(Path(directory))
    for name, sealed in record["replay"]["manifests"].items():
        observed = replay["manifests"].get(name)
        if observed is None:
            findings.append(f"{name} was sealed as replayed and is no longer run")
        elif not observed["green"]:
            findings.append(f"{name} is no longer green")
        elif observed["cases"] != sealed["cases"]:
            findings.append(
                f"{name} replayed {observed['cases']} cases against a sealed {sealed['cases']}"
            )
        elif observed["manifest_sha256"] != sealed["manifest_sha256"]:
            findings.append(f"{name}'s manifest bytes changed after the release measured them")
    # The verdict is recomputed from the criteria the record carries rather than read off it.
    # A record whose `outcome` disagreed with its own checks would otherwise verify happily.
    if _verdicts(record["criteria"]) != record["verdicts"]:
        findings.append("the sealed verdicts do not follow from the sealed criteria")
    if record["outcome"] != ("pass" if record["verdicts"]["all_four_met"] else "stop"):
        findings.append("the recorded outcome does not follow from the verdicts")

    if findings:
        raise SystemExit("\n".join(findings))
    print(
        json.dumps(
            {
                "checked": OUTPUT.name,
                "criteria_met": f"{record['verdicts']['met']} of {record['verdicts']['of']}",
                "controller_modules_verified": record["unchanged_since_the_predecessor"][
                    "core_controller"
                ]["file_count"],
                "migration_files_verified": record["unchanged_since_the_predecessor"][
                    "storage_schema"
                ]["file_count"],
                "replay_manifests_executed": replay["manifest_count"],
                "replay_cases": replay["cases"],
                "outcome": record["outcome"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    _check() if arguments.check else _write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
