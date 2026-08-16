"""S22E-002. The active surface, enumerated from a released contract and fingerprinted.

§2.2(a) says a rejected proposal must cause **zero active-state mutation**, and 22A W4-F2 says
a claim about what did not change must be able to notice a change. Both collapse into one
requirement: an enumerated surface, a fingerprint per member computed the same way before and
after, and a comparison that is *recomputed* rather than asserted.

**The enumeration is derived, not typed.** `ActiveStateProtectionSnapshot` is a released
contract with exactly five fields, and the surface this sprint protects is those five. Typing
the list out beside the contract is how a sixth surface appears later and nothing notices —
22A W4-F1's rule is that a coverage word is an enumeration with a test asserting it, so the
enumeration comes off `model_fields` and a test asserts the two agree.

**What each member's fingerprint reads, and what it deliberately does not.**

* `repository_commit` — `git rev-parse HEAD`. The commit, not the branch: a branch is a name
  that can be repointed.
* `repository_status_hash` — the porcelain status, so an *untracked* file counts as a
  mutation. A worktree-isolated candidate that leaks a file into the real tree is exactly the
  seam §3.1 predicts, and a fingerprint over tracked files alone would not see it.
* `repository_manifest_hash` — path-and-size over the tracked tree, which is what
  `reality_integrity.fingerprint` computes for an artifact root, applied to the working tree.
* `active_database_fingerprint` — every governed table's name and exact row count, hashed.
  It reads no row contents on purpose: the question is "did anything get written here", and a
  count answers it without a second copy of the store. `verify_artifact_store.sh` is the
  content check, and this is deliberately its cheaper sibling.
* `active_artifact_namespace_hash` — `reality_integrity.fingerprint` over the active artifact
  root, released and unmodified.

**W0-F3. The released contract cannot express one of the surfaces §2.2(a) enumerates.** The
plan lists six things: the working tree and protected `main`, the governed stores, the active
learned pointer, the artifact roots, and the registry snapshot. Five map onto
`ActiveStateProtectionSnapshot`. The sixth does not, and the reason is 22A's own achievement:
the domain registry is **data**, not a table — `registry.snapshot_hash()` is computed over the
resolution surface, and a store with 114 tables holds none of it. A candidate that registered
a domain would move nothing in any of the released contract's five fields.

Carried as an explicit sixth member outside the contract rather than dropped, and rather than
pretended into the database fingerprint. `contract_members` and `additional_members` are
reported separately so a reader can see exactly which part of the surface the released
snapshot could carry into `ControlledChangeService` and which part this sprint has to hold
beside it. Widening `ActiveStateProtectionSnapshot` is a released-contract change and is
therefore owed to a successor, not taken here.

The active learned pointer *is* in the store (`learned_components` and
`learned_activation_history`), so it is covered by the database fingerprint **and** counted out
by name in `governed_pointers`, because a surface that is only covered transitively is a
surface nobody can show was covered.

    UV_CACHE_DIR=.cache/uv uv run python scripts/surface_22e.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from cognitive_os.coding.reality_integrity import fingerprint  # noqa: E402
from cognitive_os.domain.changes import ActiveStateProtectionSnapshot  # noqa: E402

#: The released contract the enumeration is derived from. Named as a string as well, so the
#: record says where the list came from and a reader does not have to trust that it was derived.
SURFACE_CONTRACT = "cognitive_os.domain.changes.ActiveStateProtectionSnapshot"

#: The five fields that are surfaces. Two of the contract's seven are not: `captured_at` is a
#: timestamp, and `content_hash` is the snapshot's own seal, inherited from
#: `HashedExperienceContract` — a hash *of* the five, so treating it as a sixth would make
#: every comparison count the same movement twice. Excluded here rather than filtered at each
#: call site, and the derivation is what surfaced `content_hash` in the first place: a
#: hand-typed list of five would simply never have mentioned it.
NOT_A_SURFACE = ("captured_at", "content_hash")

#: §2.2(a)'s active learned pointer, counted out by name rather than left to the table sweep.
#: These are asserted to exist: a pointer table that quietly disappears would otherwise make
#: this list shorter and the record would read as if nothing were missing.
GOVERNED_POINTER_TABLES = (
    "learned_components",
    "learned_activation_history",
)

#: W0-F3. The surface member the released contract has no field for.
ADDITIONAL_SURFACE_MEMBERS = ("domain_registry_snapshot_hash",)


def audit_trail_tables() -> frozenset[str]:
    """**W1-F1.** The controlled-change ledger, which is the loop's *output*, not its subject.

    W0 read §2.2(a)'s "the governed stores" as all 114 tables of the governed store, and that
    over-read makes exit one unsatisfiable by construction: `ControlledChangeService`'s very
    first stage, `request_experiment`, persists the experiment and its revision *before any
    gate can refuse anything*. There is no path to a rejection that does not first write here.
    A surface counting those rows reports every correct rejection as a mutation.

    So the plan's sentence and W0's derivation of it are different things, and it is the
    derivation that was wrong. §2.2(a) enumerates the surfaces a bad candidate could *damage* —
    the working tree, protected `main`, the learned pointer, the artifact roots, the registry.
    The change ledger is the audit record that the refusal happened; a rejection that left it
    untouched would be a loop with no evidence, which is the opposite of what the exit wants.

    The repair is a split rather than a removal, and it is strictly more information than
    before: the protected fingerprint excludes these tables and must not move, the audit-trail
    fingerprint covers exactly these tables, is reported beside it, and a real traversal is
    *required* to move it. Nothing became invisible; one number became two.

    The set is derived from the released tables module rather than matched on a `change_`
    prefix, because a prefix is a naming convention and this needs to be a fact about which
    tables the controlled-change repository actually writes.
    """
    from sqlalchemy import Table

    from cognitive_os.infrastructure.changes.postgres import tables

    return frozenset(value.name for value in vars(tables).values() if isinstance(value, Table))


def contract_surface_members() -> tuple[str, ...]:
    """The part of the surface the released contract can carry."""
    return tuple(
        name for name in ActiveStateProtectionSnapshot.model_fields if name not in NOT_A_SURFACE
    )


def active_surface_members() -> tuple[str, ...]:
    """The whole enumerated surface: the released contract's five, plus W0-F3's sixth."""
    return (*contract_surface_members(), *ADDITIONAL_SURFACE_MEMBERS)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def _repository_commit() -> str:
    return _git("rev-parse", "HEAD")


def _repository_status_hash() -> str:
    """Porcelain status, hashed. An untracked file is a mutation and must be visible as one."""
    return _sha256(_git("status", "--porcelain=v1", "--untracked-files=all").encode("utf-8"))


def _repository_manifest_hash() -> str:
    """Path-and-size over the tracked tree — `reality_integrity.fingerprint`'s shape.

    Tracked paths only, because the untracked half is already carried by the status hash and
    counting it twice would make a single new file move two fingerprints for one event.
    """
    rows = []
    for name in _git("ls-files", "-z").split("\0"):
        if not name:
            continue
        path = REPO / name
        rows.append((name, path.stat().st_size if path.is_file() else -1))
    body = "\n".join(f"{name} {size}" for name, size in sorted(rows))
    return _sha256(body.encode("utf-8"))


async def _database_fingerprint(url: str) -> dict[str, Any]:
    """Every governed table and its exact row count, hashed into one value.

    `count(*)` per table rather than a sampled estimate: `pg_class.reltuples` is whatever the
    last autovacuum thought, and a zero-mutation claim read off a statistic is a claim about
    the statistics collector.

    **SQLAlchemy is imported here rather than at module scope**, and that is 22D W4-F1 a third
    time in this wave. `pre_registration_22e` imports this module for `active_surface_members`
    — a question about a released contract, with no database in it — and a top-level
    `from sqlalchemy import text` made the pre-registration's `--check` fail under the command
    line the main CI lane uses. The enumeration must be answerable everywhere; only the
    fingerprint needs the extra.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            names = [
                row[0]
                for row in (
                    await connection.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema = 'cognitive_os' AND table_type = 'BASE TABLE' "
                            "ORDER BY table_name"
                        )
                    )
                ).all()
            ]
            counts = {}
            for name in names:
                result = await connection.execute(
                    text(f'SELECT count(*) FROM cognitive_os."{name}"')
                )
                counts[name] = int(result.scalar_one())
    finally:
        await engine.dispose()

    audit = audit_trail_tables()
    protected = {name: count for name, count in counts.items() if name not in audit}
    trail = {name: count for name, count in counts.items() if name in audit}

    def _hash(values: dict[str, int]) -> str:
        return _sha256(
            "\n".join(f"{name} {count}" for name, count in sorted(values.items())).encode("utf-8")
        )

    return {
        "fingerprint": _hash(protected),
        "audit_trail_fingerprint": _hash(trail),
        "tables": len(counts),
        "protected_tables": len(protected),
        "audit_trail_tables": sorted(trail),
        "total_rows": sum(counts.values()),
        "protected_rows": sum(protected.values()),
        "audit_trail_rows": sum(trail.values()),
        "governed_pointers": {
            name: counts.get(name) for name in GOVERNED_POINTER_TABLES if name in counts
        },
        "governed_pointer_tables_absent": sorted(
            name for name in GOVERNED_POINTER_TABLES if name not in counts
        ),
    }


async def capture(*, database_url: str, artifact_root: Path) -> dict[str, Any]:
    """One fingerprint per enumerated surface member. Called before and after, identically."""
    from cognitive_os.domains import registry

    database = await _database_fingerprint(database_url)
    artifact_hash, artifact_files = fingerprint(artifact_root)
    values = {
        "repository_commit": _repository_commit(),
        "repository_status_hash": _repository_status_hash(),
        "repository_manifest_hash": _repository_manifest_hash(),
        "active_database_fingerprint": database["fingerprint"],
        "active_artifact_namespace_hash": artifact_hash,
        "domain_registry_snapshot_hash": registry.snapshot_hash(),
    }
    members = active_surface_members()
    if set(values) != set(members):
        raise ValueError(
            f"the captured surface does not match the enumeration: "
            f"captured {sorted(values)}, enumerated {sorted(members)}"
        )
    if database["governed_pointer_tables_absent"]:
        raise ValueError(
            "§2.2(a)'s active learned pointer is not in this store: "
            f"{database['governed_pointer_tables_absent']}"
        )
    return {
        "surface_contract": SURFACE_CONTRACT,
        "members": list(members),
        "contract_members": list(contract_surface_members()),
        "additional_members": list(ADDITIONAL_SURFACE_MEMBERS),
        "additional_members_exist_because": (
            "W0-F3 — the domain registry is data rather than a table (22A), and "
            "ActiveStateProtectionSnapshot has no field for it; widening the released "
            "contract is owed to a successor"
        ),
        "values": values,
        # W1-F1. Carried at the top level rather than only inside `database`, because
        # `compare` has to read it and a comparison that had to reach into a sub-object for
        # half its answer is a comparison that will eventually stop reaching.
        "audit_trail_fingerprint": database["audit_trail_fingerprint"],
        "database": {key: value for key, value in database.items() if key != "fingerprint"},
        "artifact_root_files": artifact_files,
        "surface_hash": _sha256(
            json.dumps(values, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ),
    }


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """**Recomputed, never asserted.** 22A W4-F2: this must be able to say a thing moved.

    The per-member equality is computed here rather than reported by whoever captured the two
    snapshots, and `mutated_members` is a list rather than a boolean so that a record naming a
    mutation names *which* surface moved.
    """
    members = active_surface_members()
    per_member = {name: before["values"][name] == after["values"][name] for name in members}
    mutated = sorted(name for name, unchanged in per_member.items() if not unchanged)
    trail_moved = before.get("audit_trail_fingerprint") != after.get("audit_trail_fingerprint")
    return {
        "members_compared": list(members),
        "per_member_unchanged": per_member,
        "mutated_members": mutated,
        "zero_active_state_mutation": not mutated,
        "surface_hash_before": before["surface_hash"],
        "surface_hash_after": after["surface_hash"],
        # W1-F1's other half. The split would be a weakening if it only ever excused the
        # audit trail; reported this way it is a second question, and for a real governed
        # traversal the *expected* answer is `true` — a rejection that wrote no record is a
        # loop nobody can audit. The in-memory W0 slice is the one case where `false` is
        # correct, and it says which case it is rather than sharing a verdict with the other.
        "audit_trail_moved": trail_moved,
        "audit_trail_fingerprint_before": before.get("audit_trail_fingerprint"),
        "audit_trail_fingerprint_after": after.get("audit_trail_fingerprint"),
        "comparison_is_recomputed": (
            "every member's equality is computed here from the two captures; nothing in this "
            "record is an `unchanged: true` literal supplied by the thing being checked "
            "(22A W4-F2)"
        ),
    }


async def _main() -> int:
    database_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    artifact_root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not database_url or not artifact_root:
        print(
            "REFUSED: source .env.s22e.local first (COGOS_DATABASE_ADMIN_URL, COGOS_ARTIFACT_ROOT)"
        )
        return 1
    captured = await capture(database_url=database_url, artifact_root=Path(artifact_root))
    print(json.dumps(captured, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
