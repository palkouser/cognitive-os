#!/usr/bin/env python3
"""Generate and verify Sprint 21D3 W0 evidence and pre-registration revision 3.

The command has two deliberately separate jobs:

* ``--write`` records the already-read remote baseline, the read-only predecessor inventory,
  the isolated local authority receipt, and the frozen revision-3 contracts;
* ``--check`` validates the committed evidence without requiring GitHub, PostgreSQL, or the
  operator's evidence roots.

No D3 feature encoder, learner, campaign, holdout, or retrieval implementation is imported or
executed here. The only replay is the explicitly exempt reconciliation of immutable D2 fields.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_integrity import fingerprint  # noqa: E402
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionDatasetProtocolV3,
    CorrectionDiagnosticProtocolV3,
    CorrectionFeatureContractV2,
    CorrectionPowerYieldAnalysisV3,
    CorrectionRankingUnitContractV3,
    CorrectionRetrievalProtocolV3,
    CorrectionTransformationProtocolV3,
    D3GateBinding,
    D3GateManifest,
    D3OpenGateBinding,
)

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
D2_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d2")
D2_EXAMPLE_MANIFEST_BLOB = (
    D2_ARTIFACT_ROOT / "sha256/3a/3af045cf78451e3c108a989b0787ba0a87b083d8ac287871e0efa83f1dcb2c42"
)
BASE_COMMIT = "9fe03cea3975e81bbae57b870e7bc50d8cc29f49"
D2_TAG_OBJECT = "3f3c00e216879b4d1443ca20ac3e5f14c1bc0e29"
D2_RELEASE_COMMIT = "ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5"
D2_DIAGNOSTIC = EVIDENCE / "sprint-21d2-d1-retrieval-diagnostic.json"
D2_CAMPAIGN = EVIDENCE / "sprint-21d2-self-play-campaign.json"
D2_CATALOGUES = EVIDENCE / "sprint-21d2-sealed-catalogues.json"
D2_SELECTION = EVIDENCE / "sprint-21d2-learner-selection.json"
D2_CORPUS = EVIDENCE / "sprint-21d2-corpus.json"
D2_OPERATIONS = EVIDENCE / "sprint-21d2-operations.json"

OUTPUTS = {
    "baseline": EVIDENCE / "sprint-21d3-baseline.json",
    "reconciliation": EVIDENCE / "sprint-21d3-d2-reconciliation.json",
    "isolation": EVIDENCE / "sprint-21d3-authority-isolation.json",
    "inventory": EVIDENCE / "sprint-21d3-predecessor-inventory.json",
    "reuse": EVIDENCE / "sprint-21d3-holdout-reuse-audit.json",
    "contracts": EVIDENCE / "sprint-21d3-contracts.json",
    "power": EVIDENCE / "sprint-21d3-power-and-yield.json",
    "gates": EVIDENCE / "sprint-21d3-gate-manifest.json",
    "pre_registration": EVIDENCE / "sprint-21d3-pre-registration.json",
}

PREDECESSOR_STORES = {
    "development": (
        Path("/home/palkouser/projekt/cognitive-os-data/artifacts"),
        5,
        "7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf",
    ),
    "sprint_21c3": (
        Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21c3"),
        8503,
        "7d19e3c8e45455296520eb8b6edf524d2454d6f5e07a432b751939eb23dfe593",
    ),
    "sprint_21d1": (
        Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d1"),
        83,
        "f7b14ac7a66508c5ad41f8f310a02544d1dc8e1d513dcc5bbdab82106cfbf30f",
    ),
    "sprint_21d2": (
        D2_ARTIFACT_ROOT,
        1511,
        "39417f1a03f6824cfe6f9c4b7e6bd5a3cd34da8329fb95cff0a35595899438aa",
    ),
}

REQUIRED_CONTEXTS = (
    "benchmark-regression",
    "build",
    "coding-agent",
    "cognitive-controller",
    "context-builder-core",
    "controlled-changes-core",
    "corpus-factory-core",
    "cross-domain-pilot-core",
    "experience-compiler-core",
    "harness-proposals-core",
    "inspect-adapter",
    "memory-plane-core",
    "migration",
    "model-routing-core",
    "optional-boundary",
    "postgres-integration",
    "provider-offline",
    "quality",
    "sandbox",
    "security",
    "semantic-memory-core",
    "skill-engine-core",
    "strategy-engine-core",
    "test",
    "tool-plane",
    "verifier-domains",
    "weakness-mining-core",
)

GATE_REQUIREMENTS = (
    "current baseline and exact predecessor release",
    "immutable predecessor stores and negative D2 release",
    "unit and retrieval reconciliation",
    "revision-3 pre-registration chronology",
    "verifier remains label and acceptance authority",
    "v2 fitted matrix contains no forbidden field",
    "transitive groups never cross roles",
    "minimum fit and calibration counts",
    "zero real governed runs in fit or calibration",
    "two exact independent final batches",
    "holdout inaccessible and candidate selected before access",
    "strongest deterministic baseline and revised k-NN first",
    "at least twenty changed final group decisions",
    "absolute or relative benefit floor",
    "paired group bootstrap lower bound above zero",
    "positive direction in final A and final B",
    "unit-correct operational denominators",
    "zero accepted safety or governance regressions",
    "retention floors by domain and aggregate",
    "one hundred promotion metamorphic decisions with safety ceiling",
    "shadow executes no changed decision",
    "canonical inert JSON artifact with complete lineage",
    "structured deterministic fallback on every failure",
    "new retrieval holdout clears recall and MRR floors",
    "hash-bound canary with verifier and kill switch",
    "restart-safe lifecycle, disable, restore and rollback",
    "exact human approval authority and no self-approval",
    "isolated recovery and complete validation matrix",
    "protected release, exact-head CI, documents and verified tag",
)

GATE_FLOORS = (
    "fresh local and remote reads",
    "four fingerprints unchanged",
    "ten D2 OOD decisions and canonical D2 retrieval values",
    "zero D3 measurements before publication",
    "prediction may only order attempts",
    "zero forbidden, identity, outcome or answer fields",
    "zero cross-role groups or near clones",
    "fit 200/50 and calibration 80/20 target",
    "exactly zero",
    "120 outcomes over 30 groups in each batch",
    "exact artifact and prediction seals before access",
    "all attempted rungs retained",
    "at least 20",
    "at least 0.05 absolute or 0.20 relative error reduction",
    "seed 21041, 2000 resamples, 95% lower bound above zero",
    "strictly positive in each batch",
    "every rate names numerator and denominator units",
    "zero",
    "domain loss at most 0.02 and aggregate loss at most 0.01",
    "at least 100 decisions/10 groups, report <=0.01, promotion zero errors",
    "zero executed changes",
    "canonical JSON only; unsafe loaders refuse",
    "immediate fallback with reason",
    "Recall@5 >=0.70 and MRR@10 >=0.50 on at least 50 queries",
    "exact canary manifest and immediate kill switch",
    "all transitions reproduce after restart",
    "existing eleven approval fields and human operator",
    "all required isolated and repository checks pass",
    "protected merge, post-merge main CI and annotated remote tag",
)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _sha256_bytes(_canonical_bytes(value))
    return sealed


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _git_output(*arguments: str) -> str:
    return subprocess.run(  # nosec B603 - fixed repository command and caller-owned arguments
        ["git", *arguments],
        cwd=REPOSITORY,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_file_hash(path: str, revision: str | None = None) -> str:
    if revision is None:
        return _sha256_file(REPOSITORY / path)
    data = subprocess.run(  # nosec B603 - fixed git command and pinned revision
        ["git", "show", f"{revision}:{path}"],
        cwd=REPOSITORY,
        check=True,
        capture_output=True,
    ).stdout
    return _sha256_bytes(data)


def _tree_binding(paths: tuple[str, ...]) -> dict[str, Any]:
    files = {path: _git_file_hash(path) for path in paths}
    joined = "\n".join(f"{path} {digest}" for path, digest in sorted(files.items())).encode()
    return {
        "algorithm": "sha256 of sorted '<path> <sha256>' lines",
        "files": files,
        "sha256": _sha256_bytes(joined),
    }


def _store_receipts() -> dict[str, Any]:
    receipts: dict[str, Any] = {}
    for name, (root, expected_files, expected_digest) in PREDECESSOR_STORES.items():
        actual_digest, actual_files = fingerprint(root)
        if (actual_files, actual_digest) != (expected_files, expected_digest):
            raise SystemExit(f"predecessor store changed: {name}")
        receipts[name] = {
            "access": "read_only_zero_write_fingerprint",
            "absolute_root": str(root),
            "files": actual_files,
            "path_and_size_fingerprint_sha256": actual_digest,
            "matches_expected": True,
        }
    return receipts


def _baseline(recorded_at: str, stores: dict[str, Any]) -> dict[str, Any]:
    runs = (
        (
            30787401395,
            "139a149c1f6ee592cb534dec3c832d2b1c4a4e91",
            "pull_request",
            "2026-08-03T05:31:26Z",
            "2026-08-03T05:46:29Z",
        ),
        (
            30788129259,
            D2_RELEASE_COMMIT,
            "push",
            "2026-08-03T05:46:54Z",
            "2026-08-03T06:00:49Z",
        ),
        (
            30789042482,
            "e40a67d7c73b08ce1304b55f5707f22f33d5f50e",
            "pull_request",
            "2026-08-03T06:05:34Z",
            "2026-08-03T06:21:39Z",
        ),
        (
            30789985887,
            BASE_COMMIT,
            "push",
            "2026-08-03T06:22:17Z",
            "2026-08-03T06:36:44Z",
        ),
    )
    return _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W0",
            "items": ["S21D3-000"],
            "recorded_at": recorded_at,
            "read_policy": "fresh local and remote reads; no remote mutation",
            "branch": {
                "name": "feature/sprint-21d3-invariant-correction-ranking",
                "local_head": BASE_COMMIT,
                "origin_main": BASE_COMMIT,
                "merge_base_with_origin_main": BASE_COMMIT,
                "commits_ahead_at_baseline": 0,
                "descends_from_current_origin_main": True,
            },
            "d2_release": {
                "tag": "sprint-21d2-evidence-baseline",
                "local_tag_object": D2_TAG_OBJECT,
                "remote_tag_object": D2_TAG_OBJECT,
                "local_peeled_commit": D2_RELEASE_COMMIT,
                "remote_peeled_commit": D2_RELEASE_COMMIT,
                "remote": "https://github.com/palkouser/cognitive-os",
            },
            "pull_requests": [
                {
                    "number": 219,
                    "state": "MERGED",
                    "head": "139a149c1f6ee592cb534dec3c832d2b1c4a4e91",
                    "merge_commit": D2_RELEASE_COMMIT,
                    "merged_at": "2026-08-03T05:46:52Z",
                    "url": "https://github.com/palkouser/cognitive-os/pull/219",
                },
                {
                    "number": 220,
                    "state": "MERGED",
                    "head": "e40a67d7c73b08ce1304b55f5707f22f33d5f50e",
                    "merge_commit": BASE_COMMIT,
                    "merged_at": "2026-08-03T06:22:14Z",
                    "url": "https://github.com/palkouser/cognitive-os/pull/220",
                },
            ],
            "ci_runs": [
                {
                    "run_id": run_id,
                    "head_sha": head,
                    "event": event,
                    "status": "completed",
                    "conclusion": "success",
                    "successful_jobs": 30,
                    "job_count": 30,
                    "created_at": created,
                    "updated_at": updated,
                    "url": f"https://github.com/palkouser/cognitive-os/actions/runs/{run_id}",
                }
                for run_id, head, event, created, updated in runs
            ],
            "main_protection": {
                "strict": True,
                "required_contexts": list(REQUIRED_CONTEXTS),
                "required_context_count": 27,
                "enforce_admins": True,
                "required_conversation_resolution": True,
                "allow_force_pushes": False,
                "allow_deletions": False,
                "required_pull_request_reviews": None,
                "queried_json_sha256_including_trailing_newline": (
                    "f22c91f8fc462ee523bfe4d04b8cf9db8be641d410f8ac7e185544b5b346b1f0"
                ),
            },
            "collaborators": {
                "count": 1,
                "eligible_reviewers_other_than_maintainer": 0,
                "logins": ["palkouser"],
                "maintainer_permission": "admin",
                "approving_review_requirement": "unset_because_no_second_eligible_reviewer",
            },
            "migration": {"repository_head": "0015", "planned_d3_migration": None},
            "learned_state_in_cognitive_os_s21d2_test": {
                "surface": "experience.correction_ranking",
                "components": 0,
                "approvals": 0,
                "activations": 0,
                "query": "read-only counts over the three learned lifecycle tables",
            },
            "predecessor_artifact_stores": stores,
            "commands": [
                "git fetch origin",
                (
                    "git ls-remote origin main refs/tags/sprint-21d2-evidence-baseline "
                    "refs/tags/sprint-21d2-evidence-baseline^{}"
                ),
                "gh pr view 219/220 --repo palkouser/cognitive-os --json ...",
                (
                    "gh run view 30787401395/30788129259/30789042482/30789985887 "
                    "--repo palkouser/cognitive-os --json ..."
                ),
                "gh api repos/palkouser/cognitive-os/branches/main/protection",
                "gh api repos/palkouser/cognitive-os/collaborators",
                "uv run alembic -c infra/postgres/alembic.ini heads",
                (
                    "uv run python scripts/artifact_store_fingerprint.py <root> "
                    "--expect <digest> --expect-files <count> --json"
                ),
            ],
            "zero_predecessor_writes": True,
        }
    )


def _reconciliation(recorded_at: str) -> dict[str, Any]:
    diagnostic = _read_json(D2_DIAGNOSTIC)
    arms = diagnostic["arms"]
    canonical = {
        "width_20_bounded_graph": {
            "json_pointer": "/arms/minilm_shortlist_plus_bounded_ged",
            "recall_at_5": arms["minilm_shortlist_plus_bounded_ged"]["top_5_recall"],
            "mrr_at_10": arms["minilm_shortlist_plus_bounded_ged"]["mrr_at_10"],
            "ndcg_at_10": arms["minilm_shortlist_plus_bounded_ged"]["ndcg_at_10"],
            "timeouts": arms["minilm_shortlist_plus_bounded_ged"]["timeouts"],
        },
        "minilm_vector": {
            "json_pointer": "/arms/minilm_vector",
            "recall_at_5": arms["minilm_vector"]["top_5_recall"],
            "mrr_at_10": arms["minilm_vector"]["mrr_at_10"],
            "ndcg_at_10": arms["minilm_vector"]["ndcg_at_10"],
            "timeouts": arms["minilm_vector"]["timeouts"],
        },
        "lexical": {
            "json_pointer": "/arms/lexical",
            "recall_at_5": arms["lexical"]["top_5_recall"],
            "mrr_at_10": arms["lexical"]["mrr_at_10"],
            "ndcg_at_10": arms["lexical"]["ndcg_at_10"],
            "timeouts": arms["lexical"]["timeouts"],
        },
    }
    expected = {
        "width_20_bounded_graph": (0.5875, 0.3634, 0.2333, 0),
        "minilm_vector": (0.5375, 0.4392, 0.374, 0),
        "lexical": (0.525, 0.4145, 0.3327, 0),
    }
    for name, values in expected.items():
        actual = canonical[name]
        if (
            actual["recall_at_5"],
            actual["mrr_at_10"],
            actual["ndcg_at_10"],
            actual["timeouts"],
        ) != values:
            raise SystemExit(f"D2 diagnostic changed at {name}")
    return _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W0",
            "items": ["S21D3-001"],
            "recorded_at": recorded_at,
            "purpose": "non-destructive correction of D2 denominators and narrative drift",
            "ranking_units": {
                "candidate_outcome": "one verifier label for one candidate",
                "ranking_decision": "one rank-or-abstain call for one four-candidate task group",
                "metamorphic_case": "one transformation of one group and one ranking decision",
                "formula": "candidate_outcomes = ranking_decisions * 4",
                "d2_ood_groups": 10,
                "d2_ood_ranking_decisions": 10,
                "d2_ood_candidate_outcomes": 40,
                "d2_recorded_decisions_field": 40,
                "d2_recorded_field_interpretation": (
                    "candidate outcome slots, incorrectly labelled decisions"
                ),
                "authoritative_d3_interpretation": (
                    "ten ranking decisions and forty candidate outcomes"
                ),
            },
            "retrieval": {
                "calculation_source": "machine-readable computed arm fields",
                "query_count": diagnostic["query_set"]["queries"],
                "query_set_hash": diagnostic["query_set"]["sha256"],
                "canonical_development_values": canonical,
                "mismatches": [
                    {
                        "location": "sprint-21d2-report.md narrative",
                        "recorded": "graph MRR/nDCG 0.3628/0.2327 and MiniLM recall 0.6750",
                        "authoritative": "graph 0.3634/0.2333 and MiniLM recall 0.5375",
                    },
                    {
                        "location": "/findings/0/observed",
                        "recorded": "graph MRR/nDCG 0.3628/0.2327",
                        "authoritative": "computed /arms fields 0.3634/0.2333",
                    },
                    {
                        "location": "D2 report limitation and handoff OOD prose",
                        "recorded": "40 OOD decisions",
                        "authoritative": "10 group decisions and 40 candidate outcomes",
                    },
                ],
                "scope": "frozen D1 development replay only; not D1 condition 15 closure",
            },
            "source_evidence": {
                str(D2_DIAGNOSTIC.relative_to(REPOSITORY)): _sha256_file(D2_DIAGNOSTIC),
                "docs/sprints/sprint-21/sprint-21d2-report.md": _sha256_file(
                    REPOSITORY / "docs/sprints/sprint-21/sprint-21d2-report.md"
                ),
                str(D2_SELECTION.relative_to(REPOSITORY)): _sha256_file(D2_SELECTION),
            },
            "replay": {
                "command": "uv run python scripts/pre_registration_d3.py --write",
                "algorithm": (
                    "read the frozen 80-query JSON computed arm fields without "
                    "recomputation, tuning, or rounding substitution"
                ),
                "result_hash": _sha256_bytes(_canonical_bytes(canonical)),
            },
            "protected_objects_unchanged": True,
            "d1_or_d2_evidence_files_written": 0,
        }
    )


def _isolation(recorded_at: str, stores: dict[str, Any]) -> dict[str, Any]:
    env_file = REPOSITORY / ".env.s21d3.local"
    keys = sorted(
        line.split("=", 1)[0]
        for line in env_file.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    roots = {
        "artifact": "/home/palkouser/projekt/cognitive-os-data/artifacts-s21d3",
        "backup": "/home/palkouser/projekt/cognitive-os-data/backups-s21d3",
        "scratch": "/home/palkouser/projekt/cognitive-os-data/scratch-s21d3",
        "evidence": str(EVIDENCE),
    }
    return _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W0",
            "items": ["S21D3-002"],
            "recorded_at": recorded_at,
            "environment": {
                "file": ".env.s21d3.local",
                "mode": oct(env_file.stat().st_mode & 0o777),
                "present_keys": keys,
                "values_recorded": False,
                "explicit_for_every_shell_operation": "COGOS_POSTGRES_ENV_FILE",
            },
            "provisioning": {
                "command": (
                    "COGOS_POSTGRES_ENV_FILE=.env.s21d3.local "
                    "./scripts/postgres_provision_evidence.sh cognitive_os_s21d3_test "
                    "cognitive_os_s21d3_integration_test cognitive_os_s21d3_restore_test"
                ),
                "databases": [
                    "cognitive_os_s21d3_test",
                    "cognitive_os_s21d3_integration_test",
                    "cognitive_os_s21d3_restore_test",
                ],
                "first_run": "three created",
                "second_run": "three existed; idempotent",
                "outside_prefix_guard": {
                    "target": "cognitive_os_dev",
                    "exit_status": 1,
                    "result": "refused outside prefix cognitive_os_s21d3",
                },
                "role_changes": 0,
                "existing_owner_superuser_note_retained": True,
                "postgres_bootstrap_roles_invoked": False,
            },
            "databases": {
                database: {
                    "migration": "0015",
                    "owner": "cogos_owner",
                    "owner_schema_usage": True,
                    "app_schema_usage": True,
                    "app_events_select": True,
                    "components": 0,
                    "approvals": 0,
                    "activations": 0,
                    "observations": 0,
                }
                for database in (
                    "cognitive_os_s21d3_test",
                    "cognitive_os_s21d3_integration_test",
                    "cognitive_os_s21d3_restore_test",
                )
            },
            "absolute_roots": roots,
            "root_modes": {
                name: oct(Path(path).stat().st_mode & 0o777)
                for name, path in roots.items()
                if name != "evidence"
            },
            "writable_root_policy": {
                "d3_artifact_root": roots["artifact"],
                "predecessor_roots_writable_by_d3": [],
                "predecessor_fingerprints_before": stores,
                "predecessor_fingerprints_after": stores,
            },
        }
    )


def _inventory(recorded_at: str) -> dict[str, Any]:
    campaign = _read_json(D2_CAMPAIGN)
    selection = _read_json(D2_SELECTION)
    operations = _read_json(D2_OPERATIONS)
    manifest = _read_json(D2_EXAMPLE_MANIFEST_BLOB)
    members = manifest["members"]
    if len(members) != 240:
        raise SystemExit("the authoritative D2 example manifest no longer has 240 members")
    member_lines = "\n".join(f"{member[0]}\t{member[1]}" for member in sorted(members)).encode()
    partitions = []
    for entry in campaign["partitions"]:
        partitions.append(
            {
                "partition": entry["partition"],
                "campaign_id": entry["campaign_id"],
                "campaign_manifest_hash": entry["campaign_manifest_hash"],
                "feature_set_artifact_id": entry["feature_set_artifact_id"],
                "feature_set_hash": entry["feature_set_hash"],
                "features_sealed_at": entry["features_sealed_at"],
                "first_outcome_at": entry["first_outcome_at"],
                "seal_precedes_first_outcome": entry["features_sealed_at"]
                < entry["first_outcome_at"],
                "groups": entry["groups_executed"],
                "observations": entry["observations_recorded"],
                "bundle_artifacts": entry["bundle_artifacts"],
                "bundle_count": len(entry["bundle_artifacts"]),
            }
        )
    return _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W0",
            "items": ["S21D3-003"],
            "recorded_at": recorded_at,
            "authority": "explicit D2 dataset and artifact manifests plus read-only SQL counts",
            "store_counts": {
                "database": "cognitive_os_s21d2_test",
                "learned_observations": 480,
                "distinct_observation_ids": 480,
                "learned_datasets": 2,
                "learned_artifacts": 4,
                "learned_components": 0,
                "learned_approvals": 0,
                "learned_activations": 0,
                "learned_accesses": 0,
            },
            "duplicate_execution_warning": {
                "pieces_of_intended_work": 240,
                "stored_real_executions": 480,
                "executions_per_piece": 2,
                "rows_deleted": 0,
                "rule": "select the exact 240 members; never select the surface or latest seal",
            },
            "authoritative_snapshot": {
                "dataset_id": campaign["snapshot"]["dataset_id"],
                "corpus_role": campaign["snapshot"]["corpus_role"],
                "observation_count": campaign["snapshot"]["observation_count"],
                "fit_observations": campaign["snapshot"]["fit_observations"],
                "calibration_observations": campaign["snapshot"]["calibration_observations"],
                "example_manifest_hash": campaign["snapshot"]["example_manifest_hash"],
                "split_manifest_hash": campaign["snapshot"]["split_manifest_hash"],
                "feature_schema_hash": (
                    "550646d6a2b22852ef26e6ab4960c98aeea2541da1afa39104d5828a0b4165c8"
                ),
                "example_manifest_blob_sha256": _sha256_file(D2_EXAMPLE_MANIFEST_BLOB),
                "member_pair_digest_sha256": _sha256_bytes(member_lines),
                "members": members,
                "member_count": len(members),
                "selection_kind": "explicit_member_pairs",
            },
            "all_d2_datasets": [
                {
                    "dataset_id": "257f46b5-073f-5749-aa34-49f9c727a8dc",
                    "observation_count": 240,
                    "example_manifest_hash": (
                        "f92b245c5940802797a425200d16a48083a175ce05db65107c620157fb1b3657"
                    ),
                    "split_manifest_hash": (
                        "ec5c7a9ff87381f5a0a5105fe0621bc4daf92f678502750bceeadba963f5e687"
                    ),
                    "created_at": "2026-08-02T05:31:02.265315+00:00",
                    "role": "superseded_duplicate_execution_snapshot",
                },
                {
                    "dataset_id": "0a1c570f-2185-5bb4-a9a5-9033d9363e70",
                    "observation_count": 240,
                    "example_manifest_hash": (
                        "41e67e1568a93fd5ee7251ef126dc11a7d5e6a9acfbde99116d6223bb939ddce"
                    ),
                    "split_manifest_hash": (
                        "5ebeb997fd89768d487f06e5ad27dcb68682e66d62e5bd32ac1ae8ae0c40f8f8"
                    ),
                    "created_at": "2026-08-02T05:36:01.172905+00:00",
                    "role": "authoritative_explicit_snapshot",
                },
            ],
            "partition_seals_and_chronology": partitions,
            "all_feature_seals": operations["source_integrity_report"]["counts"][
                "sealed_partitions"
            ],
            "all_feature_seals_summary": {
                "training": 3,
                "calibration": 3,
                "declared_by_campaign_evidence": 2,
                "additional_real_seals_retained": 4,
                "earliest_seal": "2026-08-02T05:26:52.696319+00:00",
                "earliest_outcome": "2026-08-02T05:26:55.066887+00:00",
                "all_480_observations_follow_the_first_seal_of_their_campaign": True,
                "warning": (
                    "two campaign manifests were each sealed three times; explicit member "
                    "selection is mandatory"
                ),
            },
            "catalogue_seal": {
                "root_hash": "521e620fc251545fe323444fa4a3bf925d0d4b0039efd79b097bb1f015e6fa96",
                "partition_hashes": {
                    "training": "37eb59f2c374a06f02764ffcd5a21a4e8b1923ee5a0c62af0093567b708dfda9",
                    "calibration": (
                        "39dcb9613d843e840b23db99fd3b99fd774ed8a324d4e718fcb951e084a253e2"
                    ),
                    "final_a": "69d5eedcaeccdfdcc183b050c89c3e4b49b709474a35511620c39f6f0292fb46",
                    "final_b": "06a0c2f6641e4bf330d2fd29a9fab54b636c77d689917976133bafc92bf22a33",
                    "canary": "027f2d78500a14b393cf527d09c80961094097d6436cafce5b370340bdd639e7",
                },
                "outcomes_present_at_seal": False,
            },
            "selection": {
                "content_hash": selection["candidate_selection"]["content_hash"],
                "selected": selection["candidate_selection"]["selected"],
                "authorises_final_access": selection["candidate_selection"][
                    "authorises_final_access"
                ],
                "continuation_hash": selection["continuation"]["content_hash"],
                "continuation": selection["continuation"]["outcome"],
                "failure_kind": selection["continuation"]["failure_kind"],
            },
            "protected_roles": {
                "final_a": {"groups": 30, "candidate_slots": 120, "outcomes": 0},
                "final_b": {"groups": 30, "candidate_slots": 120, "outcomes": 0},
                "canary": {"groups": 5, "candidate_slots": 20, "outcomes": 0},
                "prediction_records": 0,
                "body_access_receipts": 0,
            },
            "invalid_selection_patterns": [
                "all observations on experience.correction_ranking",
                "latest feature seal for a partition",
                "latest dataset for a surface",
            ],
            "source_hashes": {
                str(D2_CAMPAIGN.relative_to(REPOSITORY)): _sha256_file(D2_CAMPAIGN),
                str(D2_SELECTION.relative_to(REPOSITORY)): _sha256_file(D2_SELECTION),
                str(D2_CATALOGUES.relative_to(REPOSITORY)): _sha256_file(D2_CATALOGUES),
                str(D2_OPERATIONS.relative_to(REPOSITORY)): _sha256_file(D2_OPERATIONS),
                "explicit_example_manifest_blob": _sha256_file(D2_EXAMPLE_MANIFEST_BLOB),
            },
        }
    )


def _reuse_audit(recorded_at: str) -> dict[str, Any]:
    catalogue_path = "src/cognitive_os/learning/correction_catalogue.py"
    source_path = "src/cognitive_os/coding/reality_task_specs_d2.py"
    tracked_evidence_path = "docs/sprints/sprint-21/evidence/sprint-21d2-sealed-catalogues.json"
    source_files = {}
    for path in (catalogue_path, source_path, tracked_evidence_path):
        released = _git_file_hash(path, D2_RELEASE_COMMIT)
        current = _git_file_hash(path)
        source_files[path] = {
            "d2_release_sha256": released,
            "current_sha256": current,
            "unchanged": released == current,
        }
    if not all(record["unchanged"] for record in source_files.values()):
        raise SystemExit("a protected-role source changed after the D2 release")
    role_specs = (
        (
            "final_a",
            30,
            120,
            "69d5eedcaeccdfdcc183b050c89c3e4b49b709474a35511620c39f6f0292fb46",
        ),
        (
            "final_b",
            30,
            120,
            "06a0c2f6641e4bf330d2fd29a9fab54b636c77d689917976133bafc92bf22a33",
        ),
        (
            "canary",
            5,
            20,
            "027f2d78500a14b393cf527d09c80961094097d6436cafce5b370340bdd639e7",
        ),
    )
    roles = []
    for role, groups, slots, manifest_hash in role_specs:
        roles.append(
            {
                "role": role,
                "decision": "reuse",
                "groups": groups,
                "candidate_slots": slots,
                "catalogue_manifest_hash": manifest_hash,
                "catalogue_root_hash": (
                    "521e620fc251545fe323444fa4a3bf925d0d4b0039efd79b097bb1f015e6fa96"
                ),
                "unchanged_catalogue_source_and_manifest": True,
                "pairwise_shared_groups": 0,
                "pairwise_shared_clone_clusters": 0,
                "pairwise_shared_source_lineages": 0,
                "authoritative_outcomes": 0,
                "prediction_records": 0,
                "body_access_receipts": 0,
                "fitting_can_resolve_member_or_body": False,
                "d2_selection_authorises_access": False,
                "individual_body_hashes_resolved_by_audit": 0,
                "revision3_child_binding": (
                    "pre-registration binds this exact role/root/manifest decision; "
                    "S21D3-032 binds later v2 child identities before execution"
                ),
            }
        )
    return _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W0",
            "items": ["S21D3-004"],
            "recorded_at": recorded_at,
            "audit_surface": "sealed catalogue, root, tracked source, and access identities only",
            "protected_bodies_resolved": 0,
            "individual_body_hashes_resolved": 0,
            "roles": roles,
            "source_files": source_files,
            "group_disjointness": {
                "protected_role_pairs": 3,
                "pairs_sharing_a_group": 0,
                "source": str(D2_CATALOGUES.relative_to(REPOSITORY)),
                "source_sha256": _sha256_file(D2_CATALOGUES),
            },
            "access_and_outcome_authority": {
                "learned_access_rows": 0,
                "learned_evidence_prediction_rows": 0,
                "final_a_opened": False,
                "final_b_opened": False,
                "canary_opened": False,
                "selection_hash": (
                    "274a7a932ce110d12892f3dab102f10308ad556c563483d414979cbc69950536"
                ),
                "selection_authorises_final_access": False,
                "capability_seal_exposes_final_or_canary_identifiers": 0,
            },
            "whole_role_replacement_contract": {
                "trigger": "any later mismatch in role/root/source/access/child binding",
                "counts": {
                    "final_a": {"groups": 30, "candidate_slots": 120},
                    "final_b": {"groups": 30, "candidate_slots": 120},
                    "canary": {"groups": 5, "candidate_slots": 20},
                },
                "partial_reuse_allowed": False,
                "authoring_exception": (
                    "isolated throwaway validation only; no learned, event, artifact, or "
                    "metric write"
                ),
                "procedure": (
                    "S21D3-030 authors the complete role, S21D3-031 proves separation, "
                    "S21D3-032 seals it before measurement"
                ),
            },
        }
    )


def _golden_hashes() -> dict[str, Any]:
    fixtures = {
        "input_module": "def total(items):\n    value = sum(items)\n    return value\n",
        "rename_a": "def q0(q1):\n    q2 = sum(q1)\n    return q2\n",
        "rename_b": "def z0(z1):\n    z2 = sum(z1)\n    return z2\n",
        "input_issue": "Function returns a total when values are present.",
        "issue_a": (
            "Reported behaviour: Function gives back a total in the case where values are present."
        ),
        "issue_b": "Equivalent contract: Function produces a total provided values are present.",
    }
    return {name: _sha256_bytes(value.encode()) for name, value in fixtures.items()}


def _gate_manifest() -> D3GateManifest:
    bindings = []
    for condition, (requirement, floor) in enumerate(
        zip(GATE_REQUIREMENTS, GATE_FLOORS, strict=True), 1
    ):
        if condition == 1:
            handle = "sprint-21d3-baseline.json"
        elif condition in {2, 3}:
            handle = "sprint-21d3-d2-reconciliation.json"
        elif condition == 4:
            handle = "sprint-21d3-pre-registration.json"
        elif condition == 24:
            handle = "sprint-21d3-retrieval-holdout-result.json"
        elif condition == 29:
            handle = "sprint-21d3-release.json"
        else:
            handle = f"sprint-21d3-gate-l2-condition-{condition}.json"
        bindings.append(
            D3GateBinding(
                condition=condition,
                metric_or_invariant=requirement,
                floor_or_rule=floor,
                evidence_handle=handle,
                predecessor_reuse=condition in {1, 2},
                stop_status="w0_evidence_complete"
                if condition in {1, 2, 3, 4}
                else "future_required",
            )
        )
    return D3GateManifest(
        gate_l2=tuple(bindings),
        gate_d1_open=(
            D3OpenGateBinding(
                condition=6,
                closure_rule=(
                    "at least 200 unique eligible verifier-backed primary-surface outcomes"
                ),
                evidence_handle="sprint-21d3-d1-condition-6.json",
            ),
            D3OpenGateBinding(
                condition=7,
                closure_rule="at least 20 primary-surface examples change advisory action",
                evidence_handle="sprint-21d3-d1-condition-7.json",
            ),
            D3OpenGateBinding(
                condition=15,
                closure_rule="new unseen-task retrieval holdout independently clears both floors",
                evidence_handle="sprint-21d3-retrieval-holdout-result.json",
            ),
        ),
    )


def _contracts(
    recorded_at: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    ranking = CorrectionRankingUnitContractV3()
    diagnostic = CorrectionDiagnosticProtocolV3()
    feature = CorrectionFeatureContractV2()
    dataset = CorrectionDatasetProtocolV3()
    power = CorrectionPowerYieldAnalysisV3()
    transformations = CorrectionTransformationProtocolV3()
    retrieval = CorrectionRetrievalProtocolV3()
    gate = _gate_manifest()
    source_tree = _tree_binding(
        (
            "src/cognitive_os/learning/correction_protocol.py",
            "src/cognitive_os/learning/calibration_ood.py",
            "src/cognitive_os/experience/graph_retrieval.py",
            "scripts/pre_registration_d3.py",
            "tests/cognitive_os/learning/test_correction_protocol_v3.py",
        )
    )
    contract_evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W0",
            "items": [
                "S21D3-010",
                "S21D3-011",
                "S21D3-012",
                "S21D3-013",
                "S21D3-015",
                "S21D3-016",
            ],
            "recorded_at": recorded_at,
            "contracts": {
                "ranking_units": ranking.model_dump(mode="json"),
                "diagnostic": diagnostic.model_dump(mode="json"),
                "feature_v2": feature.model_dump(mode="json"),
                "dataset_v3": dataset.model_dump(mode="json"),
                "transformations_v3": transformations.model_dump(mode="json"),
                "retrieval_v3": retrieval.model_dump(mode="json"),
            },
            "diagnostic_execution_binding": {
                "d2_resolved_member_hash": diagnostic.d2_resolved_set_hash,
                "d2_exact_setting": diagnostic.d2_setting_identity,
                "perturbation_code": {
                    "path": "src/cognitive_os/learning/calibration_ood.py",
                    "sha256": _git_file_hash("src/cognitive_os/learning/calibration_ood.py"),
                    "seed": 21024606,
                },
                "applicability": "a case records not_applicable rather than substituting a member",
                "selection_authority": False,
            },
            "feature_v1_to_v2_diff": {
                "added": [
                    "canonical_candidate_source_embedding_000..383",
                    "candidate_source_ast_node_count semantic identity",
                    "normalizer and Python grammar identity",
                ],
                "removed": list(feature.removed_v1_inputs),
                "semantically_changed": {
                    "candidate_delta_embedding": (
                        "canonical alpha-normalised candidate-source embedding"
                    ),
                    "ast_node_count": "candidate_source_ast_node_count",
                    "graph_node_count": "statement_graph_node_count",
                    "graph_edge_count": "statement_graph_edge_count",
                    "graph_path_length": "statement_graph_path_count",
                    "declared_verifier_capabilities": "declared_verifier_capability_count",
                },
                "unchanged_authority": "verifier labels and acceptance; prediction orders only",
            },
            "dataset_seeded_mismatch_cases": [
                "same members different feature schema",
                "same schema different partition role",
                "reordered equivalent explicit selection",
                "cross-surface identity collision",
                "legacy default identity read",
            ],
            "transformation_algorithms": {
                "rename_a": "released lexical first-binding order mapped to q{zero_based_index}",
                "rename_b": (
                    "the same independently enumerated bindings mapped to z{zero_based_index}"
                ),
                "issue_a": (
                    "released ordered D2 phrase table followed by 'Reported behaviour: ' prefix"
                ),
                "issue_b": (
                    "ordered replacements returns->produces and when->provided followed by "
                    "'Equivalent contract: ' prefix"
                ),
                "combined_a": "rename_a then issue_a on separate module and issue channels",
                "combined_b": "rename_b then issue_b on separate module and issue channels",
                "case_id": transformations.case_id_formula,
                "golden_input_and_output_hashes": _golden_hashes(),
                "seeds": {"calibration": 21031501, "promotion": 21031502},
                "hard_coded_oracle": (
                    "golden hashes are stored here and production normalization is never called"
                ),
            },
            "retrieval_exact_test_vector": {
                "documents": {
                    "a": {"lexical_rank": 1, "vector_rank": 3},
                    "b": {"lexical_rank": 2, "vector_rank": 1},
                    "c": {"lexical_rank": None, "vector_rank": 2},
                },
                "scores": {
                    "a": str(retrieval.fused_score(1, 3)),
                    "b": str(retrieval.fused_score(2, 1)),
                    "c": str(retrieval.fused_score(None, 2)),
                },
                "ordering": ["b", "a", "c"],
                "tie_break": "stable pair_id ascending",
            },
            "source_tree": source_tree,
            "d2_contract_compatibility": {
                "CorrectionSurfaceContract": (
                    "f2a15b8c523de24fe514d47ec13c2407074917a8c376e048b5038dd6d2d03ca6"
                ),
                "CorrectionFeatureContract": (
                    "550646d6a2b22852ef26e6ab4960c98aeea2541da1afa39104d5828a0b4165c8"
                ),
                "changed": False,
            },
        }
    )
    power_evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W0",
            "items": ["S21D3-014"],
            "recorded_at": recorded_at,
            "outcome_access": 0,
            "contract": power.model_dump(mode="json"),
            "formulas": {
                "fitting": "50 groups * 4 = 200 outcomes",
                "calibration": "20 groups * 4 = 80 outcomes",
                "final_each": "30 groups * 4 = 120 outcomes",
                "canary": "5 groups * 4 = 20 sealed candidate slots",
                "metamorphic_each_stage": (
                    "20 groups * 6 cases = 120 nominal decisions; "
                    "100 valid decisions * 4 = 400 candidate outcomes"
                ),
                "metamorphic_reserve": "120 nominal - 100 required = 20 decisions",
                "conservative_changed_decision_yield": (
                    "60 final groups * 0.40 = 24, above the fixed floor of 20"
                ),
                "retrieval_yield": (
                    "60 overproduced groups * 0.85 = 51 qualifying queries, above the floor of 50"
                ),
            },
            "paired_effect_envelope": {
                "paired_unit": "task_group",
                "minimum_changed_decisions": 20,
                "detectable_registered_effect": (
                    "at least 0.05 absolute gain or 0.20 relative error reduction"
                ),
                "uncertainty_rule": (
                    "seed 21041, 2000 paired group bootstrap resamples, 95% lower bound above zero"
                ),
                "claim": (
                    "pre-registered gate envelope, not an observed or retrospective power estimate"
                ),
            },
            "assumptions": {
                "changed_decision_rate": "0.40 conservative planning assumption",
                "retrieval_qualification_yield": "0.85 conservative planning assumption",
                "no_member_or_outcome_read": True,
            },
        }
    )
    gate_evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W0",
            "items": ["S21D3-017"],
            "recorded_at": recorded_at,
            "manifest": gate.model_dump(mode="json"),
            "benefit_and_retention_budgets": {
                "absolute_gain": "0.05",
                "relative_error_reduction": "0.20",
                "maximum_domain_loss": "0.02",
                "maximum_aggregate_loss": "0.01",
                "retrieval_recall_at_5": "0.70",
                "retrieval_mrr_at_10": "0.50",
            },
            "first_failure_rule": (
                "the first applicable failure seals one stop hash; every dependent item "
                "records typed not_opened against it"
            ),
        }
    )
    return contract_evidence, power_evidence, gate_evidence


def _pre_registration(
    recorded_at: str, reuse: dict[str, Any], contracts: dict[str, Any]
) -> dict[str, Any]:
    child_hashes = {
        name: _sha256_file(path) for name, path in OUTPUTS.items() if name != "pre_registration"
    }
    contract_hashes = {
        name: value["content_hash"] for name, value in contracts["contracts"].items()
    }
    return _seal(
        {
            "schema_version": 1,
            "sprint": "21D3",
            "wave": "W0",
            "items": ["S21D3-018"],
            "revision": 3,
            "recorded_at": recorded_at,
            "supersedes": "revision 2 without modifying it",
            "predecessor": {
                "base_commit": BASE_COMMIT,
                "d2_tag_object": D2_TAG_OBJECT,
                "d2_release_commit": D2_RELEASE_COMMIT,
                "d2_reconciliation_is_baseline_only_exception": True,
            },
            "publication_binding": {
                "rule": (
                    "the first Git commit containing these exact bytes is the publication "
                    "commit; its SHA is recorded in the execution log because a commit cannot "
                    "contain its own SHA"
                ),
                "pre_registration_blob_sha256": (
                    "resolved after this file is written and before any later measurement"
                ),
                "post_publication_edits_allowed": False,
            },
            "evidence_children_sha256": child_hashes,
            "contract_hashes": contract_hashes,
            "intervention": {
                "feature": "correction-ranking-v2 alpha-normalised candidate-source embedding",
                "learner": "existing bounded pure-Python k-NN only",
                "retrieval": (
                    "equal-weight lexical plus MiniLM reciprocal-rank fusion with constant 60"
                ),
                "second_feature_variant": False,
                "parametric_rung": False,
                "migration": None,
            },
            "knn_grid": {
                "k": [3, 5, 7],
                "similarity_floor": ["0.30", "0.50"],
                "agreement_floor": ["0.60", "0.80"],
                "confidence_floor": ["0.55", "0.70"],
                "embedding_weight": "0.7",
            },
            "data_roles": {
                "fitting": "50 groups / 200 new SELF_PLAY outcomes",
                "calibration": "20 fresh groups / 80 SELF_PLAY outcomes",
                "calibration_metamorphic": "120 nominal / at least 100 decisions",
                "final_a": "30 groups / 120 REAL_GOVERNED_RUN outcomes",
                "final_b": "30 groups / 120 REAL_GOVERNED_RUN outcomes",
                "promotion_metamorphic": "120 nominal / at least 100 decisions",
                "canary": "5 groups / 20 presealed slots",
                "retrieval": "at least 60 source groups until at least 50 queries qualify",
            },
            "final_and_canary_reuse": {
                "audit_sha256": child_hashes["reuse"],
                "decisions": {record["role"]: record["decision"] for record in reuse["roles"]},
                "bound_role_hashes": {
                    record["role"]: record["catalogue_manifest_hash"] for record in reuse["roles"]
                },
                "conditional_whole_role_replacement": reuse["whole_role_replacement_contract"],
                "not_yet_authored_members_claimed": False,
            },
            "non_silence": {
                "clean_first_choice_above_strongest_baseline": True,
                "clean_coverage_floor": "0.80",
                "equivalence_coverage_floor": "0.80",
                "maximum_equivalence_coverage_loss": "0.05",
                "confident_equivalence_errors_allowed": 0,
                "covered_action_preservation": "1.00",
                "minimum_changed_clean_decisions": 1,
            },
            "holdout_stop_lines": [
                (
                    "no feature, grid, threshold, eligibility, or member change after fresh "
                    "calibration resolution"
                ),
                (
                    "no fit, refit, threshold, artifact, or final-manifest change after "
                    "candidate selection"
                ),
                "final B confirms final A and never repairs it",
                (
                    "retrieval arms, resources, queries, judgements, and metric code freeze "
                    "before the one holdout read"
                ),
                (
                    "first failure creates typed not_opened children and selects the negative "
                    "release route"
                ),
            ],
            "exits": {
                "positive": (
                    "all fixed conditions pass, existing governed lifecycle completes, "
                    "sprint-21-learning-baseline becomes eligible"
                ),
                "negative": (
                    "first failed condition, complete not_opened chain, Gate L2 stays closed, "
                    "sprint-21d3-evidence-baseline only"
                ),
            },
            "chronology": {
                "immutable_d2_reconciliation_replays": 1,
                "d3_channel_measurements": 0,
                "d3_feature_implementation_results": 0,
                "d3_campaigns_started": 0,
                "d3_candidate_settings_scored": 0,
                "d3_development_scores": 0,
                "correction_final_outcomes_inspected": 0,
                "canary_outcomes_inspected": 0,
                "retrieval_holdout_queries_resolved": 0,
                "retrieval_scores": 0,
            },
            "automated_check": "uv run python scripts/pre_registration_d3.py --check",
            "later_evidence_check": (
                "uv run python scripts/pre_registration_d3.py --check-chronology "
                "--later-evidence <path>"
            ),
        }
    )


def _write() -> None:
    recorded_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if _git_output("merge-base", "HEAD", "origin/main") != BASE_COMMIT:
        raise SystemExit("the implementation branch no longer descends from the frozen baseline")
    stores = _store_receipts()
    baseline = _baseline(recorded_at, stores)
    reconciliation = _reconciliation(recorded_at)
    isolation = _isolation(recorded_at, stores)
    inventory = _inventory(recorded_at)
    reuse = _reuse_audit(recorded_at)
    contracts, power, gates = _contracts(recorded_at)
    values = {
        "baseline": baseline,
        "reconciliation": reconciliation,
        "isolation": isolation,
        "inventory": inventory,
        "reuse": reuse,
        "contracts": contracts,
        "power": power,
        "gates": gates,
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for name, value in values.items():
        OUTPUTS[name].write_bytes(_json_bytes(value))
    pre_registration = _pre_registration(recorded_at, reuse, contracts)
    OUTPUTS["pre_registration"].write_bytes(_json_bytes(pre_registration))
    print(
        json.dumps(
            {
                "recorded_at": recorded_at,
                "outputs": {
                    name: str(path.relative_to(REPOSITORY)) for name, path in OUTPUTS.items()
                },
                "pre_registration_sha256": _sha256_file(OUTPUTS["pre_registration"]),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _verify_seal(path: Path, value: dict[str, Any]) -> None:
    recorded = value.get("integrity_content_hash")
    body = {key: item for key, item in value.items() if key != "integrity_content_hash"}
    expected = _sha256_bytes(_canonical_bytes(body))
    if recorded != expected:
        raise SystemExit(f"integrity hash mismatch: {path}")


def _check_chronology(later_evidence: tuple[Path, ...]) -> None:
    pre_path = OUTPUTS["pre_registration"]
    pre = _read_json(pre_path)
    _verify_seal(pre_path, pre)
    chronology = pre["chronology"]
    nonzero = {
        key: value
        for key, value in chronology.items()
        if key != "immutable_d2_reconciliation_replays" and value != 0
    }
    if chronology["immutable_d2_reconciliation_replays"] != 1 or nonzero:
        raise SystemExit(f"pre-registration contains pre-publication measurements: {nonzero}")
    pre_time = datetime.fromisoformat(pre["recorded_at"].replace("Z", "+00:00"))
    pre_hash = _sha256_file(pre_path)
    for path in later_evidence:
        value = _read_json(path)
        later_time = datetime.fromisoformat(value["recorded_at"].replace("Z", "+00:00"))
        if later_time <= pre_time:
            raise SystemExit(f"later evidence does not follow pre-registration: {path}")
        if value.get("pre_registration_sha256") != pre_hash:
            raise SystemExit(f"later evidence does not bind the pre-registration bytes: {path}")
    print(
        json.dumps(
            {
                "chronology": "valid",
                "later_evidence_checked": len(later_evidence),
                "pre_registration_sha256": pre_hash,
            },
            sort_keys=True,
        )
    )


def _check() -> None:
    values = {name: _read_json(path) for name, path in OUTPUTS.items()}
    for name, value in values.items():
        _verify_seal(OUTPUTS[name], value)
    pre = values["pre_registration"]
    for name, expected in pre["evidence_children_sha256"].items():
        if _sha256_file(OUTPUTS[name]) != expected:
            raise SystemExit(f"pre-registration child hash mismatch: {name}")
    contracts = values["contracts"]["contracts"]
    CorrectionRankingUnitContractV3.model_validate(contracts["ranking_units"])
    CorrectionDiagnosticProtocolV3.model_validate(contracts["diagnostic"])
    CorrectionFeatureContractV2.model_validate(contracts["feature_v2"])
    CorrectionDatasetProtocolV3.model_validate(contracts["dataset_v3"])
    CorrectionTransformationProtocolV3.model_validate(contracts["transformations_v3"])
    CorrectionRetrievalProtocolV3.model_validate(contracts["retrieval_v3"])
    CorrectionPowerYieldAnalysisV3.model_validate(values["power"]["contract"])
    D3GateManifest.model_validate(values["gates"]["manifest"])
    inventory = values["inventory"]
    if inventory["authoritative_snapshot"]["member_count"] != 240:
        raise SystemExit("the committed predecessor inventory is not the explicit 240-member set")
    if inventory["store_counts"]["learned_observations"] != 480:
        raise SystemExit("the committed predecessor inventory hides a D2 execution")
    if any(
        record["decision"] not in {"reuse", "replacement_required"}
        for record in values["reuse"]["roles"]
    ):
        raise SystemExit("a protected role has no whole-role decision")
    _check_chronology(())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--write", action="store_true", help="generate all W0 evidence")
    actions.add_argument("--check", action="store_true", help="validate committed W0 evidence")
    actions.add_argument(
        "--check-chronology",
        action="store_true",
        help="validate pre-registration ordering",
    )
    parser.add_argument(
        "--later-evidence",
        action="append",
        type=Path,
        default=[],
        help="later D3 JSON evidence that must bind and follow revision 3",
    )
    arguments = parser.parse_args()
    if arguments.write:
        _write()
    elif arguments.check:
        _check()
    else:
        _check_chronology(tuple(path.resolve() for path in arguments.later_evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
