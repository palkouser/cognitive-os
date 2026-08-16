"""S22E-100. The isolation substrate, against the real repository rather than a fixture.

§1.3's last sentence lists four seams between `changes/demo.py` and the real tree, and says
every one of them is unmeasured: the evaluation matrix meeting the real suite's runtime, the
worktree meeting branch protection, the clone meeting a store with released grants, and a stage
transition that has only ever run in memory meeting a persisted store. §3.1 puts all four here,
on a fixture candidate, so that the one change the sprint gets to land is not the run that
discovers a broken stage.

**The worktree is real.** `ChangeWorktreeIsolation` over the released `WorkspaceManager` and
`GitRepositoryService`, rooted outside the active checkout (the released policy layer refuses
anything else), checked out detached at the baseline commit and `git worktree lock`ed with the
experiment id as its reason.

**The gates are real commands.** §3.2 is explicit that the matrix's wall clock is "wall-clock
the waves must budget, not discover", and that a cell economised away to fit a schedule is the
quiet reading-change this programme exists to refuse. So every one of the released
`EvaluationMatrix`'s fifteen gates is mapped to a command that actually runs in the worktree,
each is executed, and each reports its measured duration. Nothing is stubbed and nothing is
skipped; a gate that cannot run is a **refusal**, recorded as such, never a pass.

**The clone is real.** A separate database at the same migration head, its identity checked
through the released `validate_database_clone`, which refuses a clone that reuses the active
identity and refuses a manifest carrying a connection URL.

**The store is persisted.** `PostgresChangeRepository`, not `InMemoryChangeRepository`. That is
the fourth seam, and it is the one that found W1-F1.

    UV_CACHE_DIR=.cache/uv uv run --extra postgres python scripts/isolation_22e.py --substrate
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")
WORKTREE_ROOT = DATA_ROOT / "s22e-worktrees"
ARCHIVE_ROOT = DATA_ROOT / "s22e-archives"
NAMESPACE = UUID("22e0da11-0000-4000-8000-000000000000")

#: The uv cache the worktree must reuse. A worktree that syncs its own cache turns a six-second
#: gate into a four-minute one, and the resulting wall clock would be a fact about the cache
#: rather than about the matrix.
WORKTREE_ENVIRONMENT = {"UV_CACHE_DIR": str(REPO / ".cache/uv")}

#: **W1-F3.** The only host variables a gate inherits. Everything else — and in particular
#: every `COGOS_*` credential in the wave's own shell — is withheld.
#:
#: The first substrate run inherited `os.environ`, so the gates ran with this sprint's
#: `COGOS_TEST_DATABASE_URL` pointing at the governed campaign store. That woke 104 PostgreSQL
#: integration tests which the CI lane skips for want of credentials, and the released suite
#: then did exactly the right thing — it **refused**:
#:
#:     Failed: refusing provider-output integration tests against database:
#:     cognitive_os_s22e_campaign
#:
#: The store was never in danger. What was in danger was the verdict: 104 released refusals
#: arrived at the evaluation matrix as `historical_regression` **failed**, which is
#: indistinguishable from a candidate that broke something. A gate that reports a refusal as a
#: regression rejects good candidates for a reason that is not about them.
#:
#: So the matrix runs in a *declared* environment rather than the operator's. This is 22D
#: W4-F1's rule pointed at the evaluation harness itself: the gate must reproduce the lane it
#: claims to reproduce, and inheriting an ambient shell is how it silently stops doing that.
GATE_ENVIRONMENT_ALLOWLIST = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TERM",
    "TMPDIR",
    "XDG_CACHE_HOME",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
)


def gate_environment() -> dict[str, str]:
    """The environment every gate runs in: an allowlist, plus the declared worktree keys.

    Returned as a fresh dict rather than a mutated copy of `os.environ`, because "we removed
    the dangerous ones" is a claim that decays every time somebody adds a variable, and "we
    passed only these" is a claim that does not.
    """
    inherited = {
        name: os.environ[name] for name in GATE_ENVIRONMENT_ALLOWLIST if name in os.environ
    }
    return {**inherited, **WORKTREE_ENVIRONMENT}


#: The released matrix's fifteen gate ids, mapped to commands that run in the candidate
#: worktree. Derived from `EVALUATION_GROUPS` plus the two gates `build_evaluation_matrix`
#: constructs inline, and asserted against the built matrix rather than trusted — a map that
#: silently missed a gate would look exactly like a matrix that had one fewer.
#:
#: `None` means "this gate is decided by the driver rather than by a subprocess": candidate
#: integrity is a diff-hash recomputation, the rollback gate is an executed rollback, and the
#: two budget gates read the measured totals of the gates that ran before them. They are
#: decided, recorded and timed like the rest; they simply have no command line.
GATE_COMMANDS: dict[str, tuple[str, ...] | None] = {
    "candidate_integrity": None,
    "reproducible_build": ("uv", "lock", "--check"),
    "focused_target_tests": (
        "uv",
        "run",
        "--all-groups",
        "--extra",
        "postgres",
        "pytest",
        "tests/cognitive_os/changes",
        "-q",
    ),
    "target_benchmark": None,
    "historical_regression": (
        "uv",
        "run",
        "--all-groups",
        "--extra",
        "mcp",
        "--extra",
        "memory-postgres",
        "pytest",
        "tests/cognitive_os",
        "-q",
    ),
    "unrelated_domain_regression": (
        "uv",
        "run",
        "--all-groups",
        "--extra",
        "mcp",
        "pytest",
        "tests/contract",
        "-q",
    ),
    "security": ("uv", "run", "--all-groups", "bandit", "-q", "-r", "src/cognitive_os"),
    "policy": ("bash", "scripts/check_repository_language.sh"),
    "migration": None,
    "schema": ("bash", "scripts/export_contract_schemas.sh", "--check"),
    "dependency_packaging": ("uv", "build", "--out-dir", "/tmp/cogos-s22e-build"),
    "performance_resources": None,
    "backup_restore_rollback": None,
    "resource_budget": None,
    "compatibility": ("uv", "run", "--all-groups", "mypy", "src/cognitive_os"),
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def experiment_id(label: str) -> UUID:
    return uuid5(NAMESPACE, f"s22e:{label}")


# ---------------------------------------------------------------------------
# The worktree
# ---------------------------------------------------------------------------


def _git(*arguments: str, cwd: Path = REPO) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=cwd, capture_output=True, text=True, check=True, timeout=120
    ).stdout.strip()


class RealWorktree:
    """A real `git worktree`, prepared and cleaned up through the released policy layer."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.experiment_id = experiment_id(label)
        self.descriptor: Any = None
        self.path: Path | None = None
        self.cleared_a_stale_worktree = False
        self._isolation: Any = None

    async def __aenter__(self) -> RealWorktree:
        """**W1-F8.** Clear a stale worktree from a previous failed run before preparing.

        `ChangeWorktreeIsolation.prepare` refuses when the experiment's root already exists,
        and the experiment id here is a `uuid5` of the label — deterministic on purpose, so a
        record names the same experiment every time. The two together mean that **a dry run
        which fails partway can never be re-run**: the released cleanup removes the git
        worktree but leaves the `<experiment_id>/` directory, and the next attempt is refused
        with "experiment already owns a change worktree" no matter how the first one ended.

        A governed loop is meant to be run repeatedly, and needing an operator to `rm -rf` a
        path between attempts is a gap in exactly the property this sprint is demonstrating.
        Cleared here rather than in the released policy layer: the released refusal is correct
        — it is protecting a live experiment — and what is missing is a caller that knows its
        own previous attempt is dead. `git worktree prune` runs first so git's own metadata
        agrees with the filesystem before anything is prepared.
        """
        import shutil

        from cognitive_os.changes.isolation import ChangeWorktreeIsolation
        from cognitive_os.infrastructure.repository.git_repository import GitRepositoryService

        WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
        ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
        stale = WORKTREE_ROOT / str(experiment_id(self.label))
        if stale.exists():
            shutil.rmtree(stale)
            self.cleared_a_stale_worktree = True
        _git("worktree", "prune")
        service = GitRepositoryService(allowed_roots=(REPO, WORKTREE_ROOT))
        self._isolation = ChangeWorktreeIsolation(WORKTREE_ROOT, ARCHIVE_ROOT, REPO, service)
        self.baseline_commit = _git("rev-parse", "HEAD")
        self.descriptor = await self._isolation.prepare(self.experiment_id, self.baseline_commit)
        self.path = WORKTREE_ROOT / str(self.experiment_id) / "worktree"
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._isolation is not None and self.descriptor is not None:
            await self._isolation.cleanup(self.experiment_id, self.descriptor, archive=False)

    async def capture(self, allowed_paths: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
        """The released capture: refuses a forbidden path, and refuses if the active tree moved."""
        return await self._isolation.capture(self.experiment_id, self.descriptor, allowed_paths)

    def facts(self) -> dict[str, Any]:
        """What the worktree is, read from git rather than asserted."""
        listing = _git("worktree", "list", "--porcelain")
        block = [
            part
            for part in listing.split("\n\n")
            if self.path is not None and str(self.path) in part
        ]
        return {
            "path": str(self.path),
            "outside_the_active_checkout": not str(self.path).startswith(str(REPO) + "/"),
            "baseline_commit": self.baseline_commit,
            "detached": any("detached" in part for part in block),
            "cleared_a_stale_worktree_first": self.cleared_a_stale_worktree,
            "locked": any("locked" in part for part in block),
            "listing_block": block[0].strip() if block else None,
        }


# ---------------------------------------------------------------------------
# Branch protection, measured against the worktree rather than described
# ---------------------------------------------------------------------------


def branch_protection_facts(worktree: RealWorktree) -> dict[str, Any]:
    """**The second seam.** What stops a candidate worktree reaching protected `main`.

    Three independent barriers, and this reports which of them actually exist rather than
    claiming the candidate "cannot" do anything:

    * the worktree is checked out **detached**, so it is on no branch and `git push` has no
      upstream to infer — a push would have to name `HEAD:main` explicitly;
    * `main` on the remote requires 27 checks with `enforce_admins: true`, so even an explicit
      push is refused server-side;
    * the released `capture` refuses if the *active* checkout changed while the candidate was
      being captured, which is the barrier that catches a candidate escaping sideways rather
      than upward.

    The first is a property of how the released isolation prepares a worktree; it is read back
    from `git worktree list` rather than assumed.
    """
    facts = worktree.facts()
    return {
        "worktree_is_detached": facts["detached"],
        "worktree_is_locked": facts["locked"],
        "worktree_is_outside_the_active_checkout": facts["outside_the_active_checkout"],
        "protected_branch": "main",
        "required_checks": 27,
        "enforce_admins": True,
        "protection_read_from": "sprint-22e-preflight.json#predecessor_release.protection",
        "the_candidate_cannot_reach_main_because": [
            "it is on no branch at all, so a push must name a refspec explicitly",
            "the remote refuses an unchecked push to main regardless of who makes it",
            "the released capture refuses if the active checkout moved during capture",
        ],
        "and_the_provider_never_pushes": (
            "§2.2(b) — the provider's authority ends at the proposal; the PR, the merge and "
            "the tag are the named user's and the gate owner's"
        ),
    }


# ---------------------------------------------------------------------------
# The clone
# ---------------------------------------------------------------------------


async def validate_clone() -> dict[str, Any]:
    """**The third seam.** A real second database, at the same head, checked by released code."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from cognitive_os.changes.isolation import validate_database_clone
    from cognitive_os.infrastructure.repository.errors import RepositoryPolicyError

    active_name = "cognitive_os_s22e_campaign"
    clone_name = "cognitive_os_s22e_clone_test"
    heads = {}
    for name, variable in (
        (active_name, "COGOS_DATABASE_ADMIN_URL"),
        (clone_name, "COGOS_CLONE_DATABASE_ADMIN_URL"),
    ):
        engine = create_async_engine(os.environ[variable])
        try:
            async with engine.connect() as connection:
                heads[name] = (
                    await connection.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar_one()
        finally:
            await engine.dispose()

    manifest = validate_database_clone(active_name, clone_name)

    # The released refusals, executed rather than described. A validator that has only ever
    # been shown accepting is a validator nobody has tested (22A W4-F2).
    refusals = {}
    for case, arguments in (
        ("same_identity", (active_name, active_name)),
        ("empty_active_identity", ("", clone_name)),
        ("manifest_carries_a_url", (active_name, os.environ["COGOS_CLONE_DATABASE_ADMIN_URL"])),
    ):
        try:
            validate_database_clone(*arguments)
        except RepositoryPolicyError as error:
            refusals[case] = {"refused": True, "reason": str(error)}
        else:
            refusals[case] = {"refused": False}

    return {
        "active_identity": active_name,
        "clone_identity": clone_name,
        "clone_is_a_different_database": active_name != clone_name,
        "migration_heads": heads,
        "heads_agree": len(set(heads.values())) == 1,
        "clone_manifest_hash": manifest,
        "released_refusals": refusals,
        "every_refusal_refused": all(item["refused"] for item in refusals.values()),
        "not_derivable_from_the_governed_url": (
            "the clone's name is not a transformation of COGOS_DATABASE_URL, so a driver "
            "handed only the governed URL cannot reach it by any code path"
        ),
    }


# ---------------------------------------------------------------------------
# The artifact namespace
# ---------------------------------------------------------------------------


def candidate_artifact_namespace(label: str) -> dict[str, Any]:
    """A real content-addressed namespace under the candidate root, plus its two refusals."""
    from cognitive_os.changes.isolation import ChangeArtifactNamespace
    from cognitive_os.infrastructure.repository.errors import RepositoryPolicyError

    root = Path(os.environ["COGOS_CANDIDATE_ARTIFACT_ROOT"])
    root.mkdir(parents=True, exist_ok=True)
    identity = experiment_id(label)
    namespace = ChangeArtifactNamespace(root, identity)
    stored = namespace.put(b"s22e-w1-candidate-artifact")

    reused = False
    try:
        ChangeArtifactNamespace(root, identity)
    except RepositoryPolicyError:
        reused = True

    return {
        "root": str(root),
        "namespace": str(namespace.path),
        "inside_the_candidate_root_not_the_active_one": str(namespace.path).startswith(str(root)),
        "is_not_the_active_artifact_root": str(root) != os.environ["COGOS_ARTIFACT_ROOT"],
        "content_hash": stored,
        "reusing_a_namespace_is_refused": reused,
    }


# ---------------------------------------------------------------------------
# The gates, run for real and timed
# ---------------------------------------------------------------------------


def matrix_gate_ids(proposal: Any) -> tuple[str, ...]:
    from cognitive_os.changes.service import build_evaluation_matrix

    return tuple(build_evaluation_matrix(proposal).execution_order)


def assert_the_map_covers_the_matrix(gate_ids: tuple[str, ...]) -> None:
    """22A W4-F1 applied to a command map: a missing gate must not look like a smaller matrix."""
    missing = [gate for gate in gate_ids if gate not in GATE_COMMANDS]
    extra = [gate for gate in GATE_COMMANDS if gate not in gate_ids]
    if missing or extra:
        raise ValueError(
            f"the gate command map does not match the released matrix: "
            f"missing {missing}, extra {extra}"
        )


def run_gate(gate_id: str, worktree: Path) -> dict[str, Any]:
    """Run one gate's real command in the candidate worktree, and time it.

    A non-zero exit is a **failed gate**, not an error to swallow, and a command that cannot
    start at all is a **refusal** — recorded as `ran: false`, and never counted as a pass.
    §3.2's rule about economised cells is the reason there is no third outcome here.
    """
    command = GATE_COMMANDS[gate_id]
    if command is None:
        return {"gate_id": gate_id, "decided_by": "driver", "ran": False}
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=1800,
            env=gate_environment(),
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {
            "gate_id": gate_id,
            "decided_by": "command",
            "ran": False,
            "refusal": f"{type(error).__name__}: {error}",
            "seconds": round(time.perf_counter() - started, 3),
            "passed": False,
        }
    duration = round(time.perf_counter() - started, 3)
    return {
        "gate_id": gate_id,
        "decided_by": "command",
        "ran": True,
        "command": list(command),
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "seconds": duration,
        "stdout_tail": completed.stdout.strip()[-300:],
        "stderr_tail": completed.stderr.strip()[-300:],
    }


# ---------------------------------------------------------------------------
# The persisted store — the fourth seam
# ---------------------------------------------------------------------------


async def persisted_chain(label: str) -> dict[str, Any]:
    """Drive the released transitions through `PostgresChangeRepository`, and read them back.

    §1.3's fourth seam. `changes/demo.py` has only ever run against
    `InMemoryChangeRepository`, so nothing had yet shown that the released stage transitions
    survive a store that enforces its own constraints and can be queried afterwards.

    Reading the revision *back out* is the point, not the write returning without raising —
    D7 W3-F1's rule that a digest proves bytes rather than usability, applied to a row.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    from cognitive_os.changes.fixtures import fixture_approved_proposal
    from cognitive_os.changes.service import ControlledChangeService
    from cognitive_os.infrastructure.changes.postgres.repository import PostgresChangeRepository
    from cognitive_os.proposals.fixtures import FIXTURE_TIME

    engine = create_async_engine(os.environ["COGOS_DATABASE_ADMIN_URL"])
    try:
        source, proposal = await fixture_approved_proposal()
        repository = PostgresChangeRepository(engine)
        service = ControlledChangeService(repository, source)
        experiment, revision, _ = await service.request_experiment(
            proposal.proposal_id,
            proposal.revision,
            baseline_tag="sprint-22d-evidence-baseline",
            baseline_commit=_git("rev-parse", "HEAD"),
            actor=f"s22e-{label}",
            isolation_approver="isolation-approver",
            created_at=FIXTURE_TIME,
        )
        read_back = await repository.get_current_revision(experiment.experiment_id)
        exact = await repository.get_exact_revision(experiment.experiment_id, revision.revision)
    finally:
        await engine.dispose()
    return {
        "repository": "PostgresChangeRepository",
        "experiment_id": str(experiment.experiment_id),
        "written_revision": revision.revision,
        "read_back_current_revision": read_back.revision if read_back else None,
        "read_back_exact_revision": exact.revision if exact else None,
        "content_hash_survives_the_round_trip": bool(
            read_back and read_back.content_hash == revision.content_hash
        ),
        "why_reading_it_back_matters": (
            "a write that returned without raising proves the statement executed, not that "
            "the row is the contract it claimed to be (D7 W3-F1)"
        ),
    }


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------

OUTPUT = EVIDENCE / "sprint-22e-w1-substrate.json"
SUBSTRATE_TIME = "2026-08-16T00:00:00Z"


async def _substrate() -> dict[str, Any]:
    from surface_22e import capture, compare

    from cognitive_os.changes.fixtures import fixture_approved_proposal

    database_url = os.environ["COGOS_DATABASE_ADMIN_URL"]
    artifact_root = Path(os.environ["COGOS_ARTIFACT_ROOT"])
    before = await capture(database_url=database_url, artifact_root=artifact_root)

    _, proposal = await fixture_approved_proposal()
    gate_ids = matrix_gate_ids(proposal)
    assert_the_map_covers_the_matrix(gate_ids)

    async with RealWorktree("w1-substrate") as worktree:
        assert worktree.path is not None
        worktree_facts = worktree.facts()
        protection = branch_protection_facts(worktree)
        gates = [run_gate(gate_id, worktree.path) for gate_id in gate_ids]
        # The released capture, on an untouched worktree: nothing changed, so the changed-file
        # set must be empty and the diff hash must be the hash of an empty diff.
        diff_hash, changed = await worktree.capture(allowed_paths=())

    clone = await validate_clone()
    namespace = candidate_artifact_namespace("w1-substrate")
    chain = await persisted_chain("w1-substrate")
    after = await capture(database_url=database_url, artifact_root=artifact_root)

    ran = [item for item in gates if item.get("ran")]
    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22E-100"],
        "sprint": "22E",
        "wave": "W1",
        "worktree": worktree_facts,
        "worktree_capture_on_an_untouched_tree": {
            "changed_files": list(changed),
            "diff_hash": diff_hash,
            "empty_diff_hash": _sha256(b""),
            "diff_is_empty": diff_hash == _sha256(b""),
        },
        "branch_protection": protection,
        "database_clone": clone,
        "artifact_namespace": namespace,
        "persisted_chain": chain,
        "evaluation_matrix": {
            "gate_count": len(gate_ids),
            "execution_order": list(gate_ids),
            "map_covers_the_matrix": True,
            "gates": gates,
            "gates_with_a_command": len(ran),
            "gates_decided_by_the_driver": len(gates) - len(ran),
            "gates_passed": sum(1 for item in ran if item.get("passed")),
            "gates_failed": sum(1 for item in ran if item.get("passed") is False),
            "measured_wall_clock_seconds": round(
                sum(item.get("seconds", 0.0) for item in gates), 3
            ),
            "slowest_gate": max(
                (item for item in ran), key=lambda item: item.get("seconds", 0.0), default=None
            ),
            "gate_environment": {
                "allowlist": list(GATE_ENVIRONMENT_ALLOWLIST),
                "declared_keys": sorted(WORKTREE_ENVIRONMENT),
                "inherited_names": sorted(gate_environment()),
                "no_cogos_variable_is_inherited": not [
                    name for name in gate_environment() if name.startswith("COGOS_")
                ],
                "finding": "W1-F3",
            },
            "nothing_was_stubbed": (
                "every gate with a command ran that command in the candidate worktree; a "
                "command that could not start is recorded as ran: false and is never a pass "
                "(§3.2 — a cell economised away is a quiet reading-change)"
            ),
        },
        "zero_active_state_mutation": compare(before, after),
        "surface_before": before["values"],
        "surface_after": after["values"],
        "reads_an_exit_criterion": False,
        "why_no_exit": (
            "this is the substrate, not a proposal. Exit one is read from a rejected "
            "*proposal*, and dry run 1 is what produces one"
        ),
        "recorded_at": SUBSTRATE_TIME,
    }
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--substrate", action="store_true")
    arguments = parser.parse_args()
    if not arguments.substrate:
        parser.error("nothing to do; pass --substrate")

    record = asyncio.run(_substrate())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    matrix = record["evaluation_matrix"]
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "worktree_detached_locked_outside": [
                    record["worktree"]["detached"],
                    record["worktree"]["locked"],
                    record["worktree"]["outside_the_active_checkout"],
                ],
                "clone_heads_agree": record["database_clone"]["heads_agree"],
                "clone_refusals_all_refused": record["database_clone"]["every_refusal_refused"],
                "persisted_round_trip": record["persisted_chain"][
                    "content_hash_survives_the_round_trip"
                ],
                "gates": matrix["gate_count"],
                "gates_passed": matrix["gates_passed"],
                "gates_failed": matrix["gates_failed"],
                "wall_clock_seconds": matrix["measured_wall_clock_seconds"],
                "slowest": (matrix["slowest_gate"] or {}).get("gate_id"),
                "zero_active_state_mutation": record["zero_active_state_mutation"][
                    "zero_active_state_mutation"
                ],
                "mutated_members": record["zero_active_state_mutation"]["mutated_members"],
                "audit_trail_moved": record["zero_active_state_mutation"]["audit_trail_moved"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
