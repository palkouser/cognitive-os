"""Reading persisted graph evidence, reporting on it, and the operator commands over it.

S21D1-063 and S21D1-064. The integrity checks live in `coding/reality_integrity` because the
unified report lives there, but they are tested here, next to the fixtures that build the four
states they have to tell apart: healthy, degraded, corrupt and missing.

Every assertion about a "read-only" command is made the only way it can be trusted — by
fingerprinting the store before and after and comparing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from cognitive_os.coding.reality_integrity import (
    FAILURE,
    WARNING,
    experience_graph_checks,
    experience_graph_is_configured,
    fingerprint,
)
from cognitive_os.domain.experience_graph import (
    GRAPH_RESOURCE_POLICY_REVISION_1_HASH,
    GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
    ActionDecisionGraph,
    ExperienceGraphEdge,
    ExperienceGraphEdgeKind,
    ExperienceGraphNode,
    ExperienceGraphNodeKind,
    FailedSuccessGraphPair,
)
from cognitive_os.domains.fixtures import FIXTURE_TIME
from cognitive_os.experience.graph_projection import derive_edit_path
from cognitive_os.experience.graph_store import blob_path, load_evidence
from scripts.experience import BENCHMARK_SCHEMA_VERSION

REPOSITORY = Path(__file__).resolve().parents[3]
CLI = REPOSITORY / "scripts" / "experience.py"
HASH = "d" * 64


def _graph(count: int, *, accepted: bool, group: str, signature: str) -> ActionDecisionGraph:
    return ActionDecisionGraph(
        graph_id=f"{signature}:{'ok' if accepted else 'failed'}",
        domain="logic",
        group=group,
        task_signature=signature,
        accepted=accepted,
        nodes=tuple(
            ExperienceGraphNode(
                logical_id=f"s{index:04d}",
                kind=ExperienceGraphNodeKind.OBSERVATION,
                attributes=(("status", "completed"),),
                source_hash=HASH,
            )
            for index in range(1, count + 1)
        ),
        edges=tuple(
            ExperienceGraphEdge(
                source_id=f"s{index:04d}",
                target_id=f"s{index + 1:04d}",
                kind=ExperienceGraphEdgeKind.NEXT,
            )
            for index in range(1, count)
        ),
        source_manifest_hash=HASH,
    )


def _pair(signature: str, *, legacy: bool = False) -> FailedSuccessGraphPair:
    failed = _graph(2, accepted=False, group=f"g.{signature}", signature=signature)
    successful = _graph(3, accepted=True, group=f"g.{signature}", signature=signature)
    return FailedSuccessGraphPair(
        pair_id=signature,
        domain="logic",
        group=f"g.{signature}",
        task_signature=signature,
        failed=failed,
        successful=successful,
        edit_path=derive_edit_path(failed, successful, path_id=signature),
        legacy_recompilation_unavailable=legacy,
        verification_mode="legacy" if legacy else "byte_identical_recompilation",
        compiled_at=FIXTURE_TIME,
    )


def _store(root: Path, pairs: tuple[FailedSuccessGraphPair, ...]) -> tuple[Path, Path]:
    """Write a graph set the way the D1 evidence pair holds one, and return its two paths."""
    artifacts = root / "store"
    children = []
    for index, pair in enumerate(pairs):
        raw = pair.model_dump_json().encode()
        digest = sha256(raw).hexdigest()
        path = blob_path(artifacts, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        children.append(
            {
                "pair_id": pair.pair_id,
                "artifact_id": f"00000000-0000-0000-0000-{index:012d}",
                "content_hash": digest,
                "pair_hash": pair.content_hash,
                "failed_structural": pair.failed.structural_hash,
                "successful_structural": pair.successful.structural_hash,
                "edit_path_hash": pair.edit_path.content_hash,
                "role": "dataset",
            }
        )
    manifest = root / "root.json"
    manifest.write_text(
        json.dumps({"graph_set_id": "test-set", "pair_count": len(pairs), "children": children})
    )
    return manifest, artifacts


@pytest.fixture
def healthy(tmp_path: Path) -> tuple[Path, Path]:
    return _store(tmp_path, (_pair("alpha"), _pair("beta")))


class TestLoadingEvidence:
    def test_an_intact_set_loads_every_pair(self, healthy: tuple[Path, Path]) -> None:
        evidence = load_evidence(*healthy)
        assert evidence.intact
        assert len(evidence.pairs) == evidence.declared_pairs == 2
        assert not evidence.legacy_recompilation

    def test_missing_bytes_are_named_and_are_not_called_corruption(self, tmp_path: Path) -> None:
        manifest, artifacts = _store(tmp_path, (_pair("alpha"), _pair("beta")))
        root = json.loads(manifest.read_text())
        blob_path(artifacts, root["children"][0]["content_hash"]).unlink()

        evidence = load_evidence(manifest, artifacts)
        assert evidence.missing_bytes == ("alpha",)
        assert not evidence.corrupt_bytes
        assert not evidence.intact

    def test_altered_bytes_are_corruption_and_are_not_called_missing(self, tmp_path: Path) -> None:
        manifest, artifacts = _store(tmp_path, (_pair("alpha"),))
        root = json.loads(manifest.read_text())
        blob_path(artifacts, root["children"][0]["content_hash"]).write_bytes(b"{}")

        evidence = load_evidence(manifest, artifacts)
        assert evidence.corrupt_bytes == ("alpha",)
        assert not evidence.missing_bytes
        assert not evidence.pairs

    def test_a_root_that_declares_the_wrong_hash_is_a_broken_link(self, tmp_path: Path) -> None:
        manifest, artifacts = _store(tmp_path, (_pair("alpha"),))
        root = json.loads(manifest.read_text())
        root["children"][0]["successful_structural"] = "0" * 64
        manifest.write_text(json.dumps(root))

        evidence = load_evidence(manifest, artifacts)
        assert evidence.broken_links == ("alpha",)
        assert not evidence.corrupt_bytes, "the bytes are fine; the root disagrees with them"

    def test_a_legacy_pair_loads_and_does_not_condemn_the_set(self, tmp_path: Path) -> None:
        manifest, artifacts = _store(tmp_path, (_pair("alpha", legacy=True), _pair("beta")))
        evidence = load_evidence(manifest, artifacts)
        assert evidence.intact
        assert evidence.legacy_recompilation == ("alpha",)

    def test_a_missing_pair_leaves_the_declared_count_unmet(self, tmp_path: Path) -> None:
        manifest, artifacts = _store(tmp_path, (_pair("alpha"),))
        root = json.loads(manifest.read_text())
        root["pair_count"] = 2
        manifest.write_text(json.dumps(root))
        assert not load_evidence(manifest, artifacts).intact


class TestIntegrityReporting:
    def _named(self, evidence: object) -> dict[str, tuple[bool, str]]:
        return {c.name: (c.ok, c.severity) for c in experience_graph_checks(evidence)}

    def test_a_healthy_set_reports_no_failure(self, healthy: tuple[Path, Path]) -> None:
        checks = self._named(load_evidence(*healthy))
        assert all(ok for ok, severity in checks.values() if severity == FAILURE)

    def test_legacy_recompilation_is_a_warning_not_a_failure(self, tmp_path: Path) -> None:
        manifest, artifacts = _store(tmp_path, (_pair("alpha", legacy=True),))
        checks = self._named(load_evidence(manifest, artifacts))
        assert checks["experience_graph_legacy_recompilation"] == (False, WARNING)
        assert checks["experience_graph_bytes_resolve"][0], "a legacy pair resolves"
        assert checks["experience_graph_edit_paths_round_trip"][0]

    def test_unresolved_bytes_are_a_failure_and_not_the_legacy_warning(
        self, tmp_path: Path
    ) -> None:
        manifest, artifacts = _store(tmp_path, (_pair("alpha"),))
        root = json.loads(manifest.read_text())
        blob_path(artifacts, root["children"][0]["content_hash"]).unlink()
        checks = self._named(load_evidence(manifest, artifacts))
        assert checks["experience_graph_bytes_resolve"] == (False, FAILURE)
        assert checks["experience_graph_legacy_recompilation"][0], "nothing legacy was found"

    def test_corruption_and_retriever_availability_are_different_answers(
        self, tmp_path: Path
    ) -> None:
        manifest, artifacts = _store(tmp_path, (_pair("alpha"), _pair("beta")))
        root = json.loads(manifest.read_text())
        blob_path(artifacts, root["children"][0]["content_hash"]).write_bytes(b"not a pair")
        checks = self._named(load_evidence(manifest, artifacts))
        assert checks["experience_graph_bytes_are_uncorrupted"] == (False, FAILURE)
        assert checks["experience_graph_retriever_is_available"] == (True, WARNING), (
            "one surviving pair still gives the retriever something to offer"
        )

    def test_an_empty_set_is_a_capability_report_not_damage(self, tmp_path: Path) -> None:
        manifest, artifacts = _store(tmp_path, ())
        checks = self._named(load_evidence(manifest, artifacts))
        assert checks["experience_graph_retriever_is_available"] == (False, WARNING)
        assert all(ok for ok, severity in checks.values() if severity == FAILURE)

    def test_an_unconfigured_host_is_warned_about_not_condemned(self) -> None:
        check = experience_graph_is_configured(None, None)
        assert (check.ok, check.severity) == (False, WARNING)


def _cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    # The store variables are scrubbed rather than inherited. A developer with a configured
    # evidence pair in their shell would otherwise see the "refuses to guess" tests pass for
    # the wrong reason, and a CI host with one set would see them fail.
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"COGOS_GRAPH_ROOT", "COGOS_ARTIFACT_ROOT"}
    }
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        capture_output=True,
        text=True,
        cwd=REPOSITORY,
        env=environment,
    )


class TestOperatorCommands:
    def test_verify_reports_an_intact_set_and_exits_zero(self, healthy: tuple[Path, Path]) -> None:
        manifest, artifacts = healthy
        done = _cli(
            "graph-verify",
            "--graph-root",
            str(manifest),
            "--artifact-root",
            str(artifacts),
        )
        assert done.returncode == 0, done.stderr
        assert json.loads(done.stdout)["intact"] is True

    def test_verify_exits_non_zero_on_damage(self, tmp_path: Path) -> None:
        manifest, artifacts = _store(tmp_path, (_pair("alpha"),))
        root = json.loads(manifest.read_text())
        blob_path(artifacts, root["children"][0]["content_hash"]).unlink()
        done = _cli(
            "graph-verify",
            "--graph-root",
            str(manifest),
            "--artifact-root",
            str(artifacts),
        )
        assert done.returncode == 1
        assert json.loads(done.stdout)["missing_bytes"] == ["alpha"]

    def test_health_is_machine_readable_and_declares_its_writes(
        self, healthy: tuple[Path, Path]
    ) -> None:
        manifest, artifacts = healthy
        done = _cli(
            "graph-health",
            "--graph-root",
            str(manifest),
            "--artifact-root",
            str(artifacts),
        )
        assert done.returncode == 0, done.stderr
        payload = json.loads(done.stdout)
        assert payload["healthy"] is True
        assert payload["writes"] == 0
        assert payload["resource_policy"]["returned_results"] == 10

    def test_build_needs_no_store_at_all(self) -> None:
        done = _cli("graph-build", "--fixture", "repaired-bug-fix")
        assert done.returncode == 0, done.stderr
        assert len(json.loads(done.stdout)["structural_hash"]) == 64

    def test_every_read_only_command_leaves_the_store_untouched(
        self, healthy: tuple[Path, Path]
    ) -> None:
        manifest, artifacts = healthy
        before = fingerprint(artifacts)
        for action in ("graph-verify", "graph-health"):
            _cli(action, "--graph-root", str(manifest), "--artifact-root", str(artifacts))
        _cli(
            "graph-query",
            "--graph-root",
            str(manifest),
            "--artifact-root",
            str(artifacts),
            "--arm",
            "lexical",
            "--query-text",
            "a failing step",
        )
        assert fingerprint(artifacts) == before

    @pytest.mark.parametrize(
        ("arguments", "expected"),
        [
            (("graph-verify",), "need --graph-root and --artifact-root"),
            (
                (
                    "graph-verify",
                    "--graph-root",
                    "/nowhere.json",
                    "--artifact-root",
                    "/tmp",
                ),
                "is not a file",
            ),
            (("graph-query", "--arm", "minilm_vector"), "need --graph-root"),
        ],
    )
    def test_an_incomplete_configuration_is_refused_rather_than_guessed(
        self, arguments: tuple[str, ...], expected: str
    ) -> None:
        done = _cli(*arguments)
        assert done.returncode != 0
        assert expected in done.stderr

    def test_a_vector_arm_without_a_model_is_refused_never_substituted(
        self, healthy: tuple[Path, Path]
    ) -> None:
        manifest, artifacts = healthy
        done = _cli(
            "graph-query",
            "--graph-root",
            str(manifest),
            "--artifact-root",
            str(artifacts),
            "--arm",
            "minilm_vector",
            "--query-text",
            "a failing step",
        )
        assert done.returncode != 0
        assert "--model is required" in done.stderr


def _queries(tmp_path: Path) -> Path:
    queries = tmp_path / "queries.json"
    queries.write_text(
        json.dumps(
            [
                {
                    "query_id": "q:alpha",
                    "domain": "logic",
                    "task_signature": "alpha",
                    "relevance_tier": 1,
                    "excluded_groups": ["g.alpha"],
                    "relevant_pair_ids": ["beta"],
                }
            ]
        )
    )
    return queries


class TestTheBenchmarkNamesThePolicyItRanUnder:
    """S21D3-040. A benchmark that takes the defaults publishes revision-1 numbers silently.

    That is not hypothetical: Sprint 21D1's stored results were produced under the class
    defaults, and Sprint 21D2's narrative then described the same surface as revision 2. The
    repair is that the measurement surface has to say which policy it used, and be refused
    when the answer is not one this repository froze.
    """

    def test_it_refuses_to_run_without_a_policy(
        self, tmp_path: Path, healthy: tuple[Path, Path]
    ) -> None:
        manifest, artifacts = healthy
        done = _cli(
            "graph-benchmark",
            "--graph-root",
            str(manifest),
            "--artifact-root",
            str(artifacts),
            "--queries",
            str(_queries(tmp_path)),
        )
        assert done.returncode != 0
        assert "needs --policy-hash" in done.stderr

    def test_it_refuses_a_hash_that_names_no_frozen_policy(
        self, tmp_path: Path, healthy: tuple[Path, Path]
    ) -> None:
        manifest, artifacts = healthy
        done = _cli(
            "graph-benchmark",
            "--graph-root",
            str(manifest),
            "--artifact-root",
            str(artifacts),
            "--queries",
            str(_queries(tmp_path)),
            "--policy-hash",
            "0" * 64,
        )
        assert done.returncode != 0
        assert "names no frozen resource policy" in done.stderr

    def test_the_named_policy_is_the_one_the_measurement_ran_under(
        self, tmp_path: Path, healthy: tuple[Path, Path]
    ) -> None:
        manifest, artifacts = healthy
        done = _cli(
            "graph-benchmark",
            "--graph-root",
            str(manifest),
            "--artifact-root",
            str(artifacts),
            "--queries",
            str(_queries(tmp_path)),
            "--policy-hash",
            GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
        )
        assert done.returncode == 0, done.stderr
        payload = json.loads(done.stdout)

        assert payload["resource_policy"]["content_hash"] == GRAPH_RESOURCE_POLICY_REVISION_2_HASH
        assert payload["resource_policy"]["vector_shortlist"] == 20
        assert payload["arms_without_a_model"] is True
        assert set(payload["arms"]) == {"no_memory", "lexical", "exact_signature"}

    def test_it_emits_the_complete_pre_registered_metric_set(
        self, tmp_path: Path, healthy: tuple[Path, Path]
    ) -> None:
        """Every metric S21D3-016 declared, plus the identities that make one comparable."""
        manifest, artifacts = healthy
        done = _cli(
            "graph-benchmark",
            "--graph-root",
            str(manifest),
            "--artifact-root",
            str(artifacts),
            "--queries",
            str(_queries(tmp_path)),
            "--policy-hash",
            GRAPH_RESOURCE_POLICY_REVISION_1_HASH,
        )
        assert done.returncode == 0, done.stderr
        payload = json.loads(done.stdout)

        assert payload["schema_version"] == BENCHMARK_SCHEMA_VERSION
        assert len(payload["content_hash"]) == 64
        assert payload["repeated_ranking_agreement"] is True
        assert (
            payload["query_manifest"]["sha256"]
            == sha256(_queries(tmp_path).read_bytes()).hexdigest()
        )
        assert payload["graph_set"]["resolved_pairs"] == 2
        assert payload["model"] is None
        assert set(payload["arms"]["lexical"]) >= {
            "top_5_recall",
            "mrr_at_10",
            "ndcg_at_10",
            "coverage",
            "p50_latency_ms",
            "p95_latency_ms",
            "max_latency_ms",
            "timeouts",
            "budget_cutoffs",
            "mean_candidates_considered",
            "top_5_recall_by_domain",
            "top_5_recall_by_tier",
        }
        assert payload["per_query"]["lexical"][0]["query_id"] == "q:alpha"
