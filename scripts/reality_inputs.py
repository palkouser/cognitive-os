#!/usr/bin/env python3
"""The one operator entry point for the Sprint 21C3 reality inputs. §S21C3-060.

    scripts/reality_inputs.py validate                      # offline, the default posture
    scripts/reality_inputs.py generate --root /tmp/tasks
    scripts/reality_inputs.py stats
    scripts/reality_inputs.py harvest
    scripts/reality_inputs.py verify --model /abs/model/dir
    scripts/reality_inputs.py run    -- --output evidence.json [--tasks N]
    scripts/reality_inputs.py resume -- --output evidence.json --resume-from previous.json
    scripts/reality_inputs.py embed  -- --model /abs/model/dir --evidence out.json
    scripts/reality_inputs.py provider -- run --config … --output … --live

Two kinds of subcommand, and the split is deliberate rather than tidy.

The **read-only** ones — `generate`, `validate`, `stats`, `harvest`, `verify` — are implemented
here. They open nothing but a read connection, they need no credentials, and they are the
default way to use this tool.

The **campaign** ones — `run`, `resume`, `embed`, `provider` — are the existing operator
scripts, executed as subprocesses with everything after `--` forwarded verbatim. Re-declaring
their flags here would mean two argument surfaces drifting apart, and the first symptom of
that drift is an operator passing a flag that is silently dropped. There is nothing to drift
if there is nothing to re-declare.

Nothing here prompts. `provider` refuses without `--live` and says so; it does not ask.

Exit codes
----------

* ``0`` — the command did what it says, and every check it ran passed.
* ``1`` — the command ran and something it checked failed: a broken authority link, a missing
  artifact, a threshold not met. Evidence is still written.
* ``2`` — the command refused before doing anything: a missing opt-in, an unusable path, an
  environment without the isolated C3 handles.

Isolation handles
-----------------

`COGOS_DATABASE_URL` and `COGOS_ARTIFACT_ROOT` select the store, normally from
`.env.s21c3.local`. Every subcommand that touches storage reads exactly those two, and none of
them is ever printed: receipts carry the database *name*, never the URL that authenticates to
it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess  # nosec B404 - fixed sibling scripts, never a shell, never operator text
import sys
from pathlib import Path
from urllib.parse import urlsplit

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parent / "src"))

from cognitive_os.coding import reality_integrity  # noqa: E402
from cognitive_os.coding.reality_retrieval import (  # noqa: E402
    build_benchmark,
    cross_group_leakage,
    kind_counts,
)
from cognitive_os.coding.reality_tasks import (  # noqa: E402
    available_templates,
    build_manifest,
    write_task,
)

#: The development pair from S21C3-003, which C3 must never write to. Values are the ones
#: every wave of this sprint has published; a change here is a finding, not a maintenance task.
DEVELOPMENT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts")
DEVELOPMENT_DIGEST = "7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf"
DEVELOPMENT_FILES = 5

#: `<command> -> script`. Everything after `--` goes to the script unchanged.
DELEGATED: dict[str, str] = {
    "run": "reality_campaign.py",
    "resume": "reality_campaign.py",
    "embed": "retrieval_benchmark.py",
    "provider": "reality_provider_campaign.py",
}

FIXTURE_EPOCH = "2026-07-30T00:00:00+00:00"


def _receipt(payload: dict[str, object]) -> None:
    """Machine-readable, and sanitized by construction: nothing here reads a credential."""
    print(json.dumps(payload, indent=2, sort_keys=True))


def _database_name() -> str | None:
    """The database name, never the URL. A receipt must be safe to paste into a ticket."""
    url = os.environ.get("COGOS_DATABASE_URL")
    return urlsplit(url).path.lstrip("/") or None if url else None


def _engine():  # type: ignore[no-untyped-def]
    from sqlalchemy.ext.asyncio import create_async_engine

    url = os.environ.get("COGOS_DATABASE_URL")
    if not url:
        raise SystemExit(2)
    return create_async_engine(url, pool_pre_ping=True)


# ------------------------------------------------------------------ read-only commands


def _generate(root: Path, limit: int | None) -> int:
    from datetime import datetime
    from uuid import UUID

    if not root.is_absolute():
        print("refused: --root must be an absolute path", file=sys.stderr)
        return 2
    created_at = datetime.fromisoformat(FIXTURE_EPOCH)
    written = []
    for template_id in available_templates()[: limit or None]:
        task = write_task(
            template_id,
            root=root / template_id,
            seed=1,
            hidden_bundle_artifact_id=UUID("00000000-0000-0000-0000-0000000021c3"),
            hidden_bundle_hash="0" * 64,
            created_at=created_at,
        )
        written.append(
            {
                "template_id": template_id,
                "task_id": str(task.manifest.task_id),
                "workspace": str(task.workspace),
                "control": str(task.control),
            }
        )
    _receipt({"command": "generate", "root": str(root), "tasks": written})
    return 0


def _validate() -> int:
    """Everything checkable without a store, a network or a model. The default posture."""
    from cognitive_os.coding import reality_leakage
    from cognitive_os.coding.reality_tasks import template

    benchmark = build_benchmark()
    determinism = reality_integrity.task_generation_is_deterministic()

    leaked: list[str] = []
    query_text = "\n".join(case.text for case in benchmark.cases)
    from datetime import datetime
    from uuid import UUID

    for template_id in available_templates():
        manifest = build_manifest(
            template_id,
            seed=1,
            hidden_bundle_artifact_id=UUID("00000000-0000-0000-0000-0000000021c3"),
            hidden_bundle_hash="0" * 64,
            created_at=datetime.fromisoformat(FIXTURE_EPOCH),
        )
        tokens = reality_leakage.control_tokens(manifest, template(template_id))
        leaked.extend(token for token in tokens if token in query_text)

    leakage = cross_group_leakage(benchmark)
    ok = determinism.ok and not leaked and not leakage
    _receipt(
        {
            "command": "validate",
            "ok": ok,
            "templates": len(available_templates()),
            "task_generation_is_deterministic": determinism.ok,
            "benchmark_manifest_hash": benchmark.manifest_hash,
            "benchmark_cases": len(benchmark.cases),
            "benchmark_documents": len(benchmark.documents),
            "benchmark_query_kinds": kind_counts(benchmark),
            "control_tokens_in_queries": sorted(set(leaked)),
            "cross_group_leakage": list(leakage),
        }
    )
    return 0 if ok else 1


async def _stats_async() -> int:
    from sqlalchemy import text as sql

    engine = _engine()
    try:
        async with engine.connect() as connection:
            counts = json.loads(await connection.scalar(sql(reality_integrity.COUNT_QUERY)))
    finally:
        await engine.dispose()
    _receipt({"command": "stats", "database": _database_name(), "counts": counts})
    return 0


async def _harvest_async() -> int:
    """Read back what the campaign recorded. A receipt, not a second write path."""
    from sqlalchemy import text as sql

    engine = _engine()
    statement = sql(
        """
        SELECT json_build_object(
          'observations', (SELECT count(*) FROM cognitive_os.learned_observations),
          'by_provenance', (
            SELECT COALESCE(json_object_agg(provenance_class, total), '{}'::json)
            FROM (SELECT provenance_class, count(*) AS total
                  FROM cognitive_os.learned_observations GROUP BY provenance_class) p),
          'by_status', (
            SELECT COALESCE(json_object_agg(status, total), '{}'::json)
            FROM (SELECT status, count(*) AS total
                  FROM cognitive_os.learned_observations GROUP BY status) s),
          'evaluation_only_real_runs', (
            SELECT count(*) FROM cognitive_os.learned_observations
            WHERE provenance_class = 'real_governed_run' AND evaluation_eligible IS TRUE)
        )::text
        """
    )
    try:
        async with engine.connect() as connection:
            harvested = json.loads(await connection.scalar(statement))
    finally:
        await engine.dispose()
    _receipt({"command": "harvest", "database": _database_name(), **harvested})
    return 0


async def _verify_async(model: Path | None) -> int:
    engine = _engine()
    try:
        async with engine.connect() as connection:
            report, counts = await reality_integrity.inspect(
                connection,
                development_root=DEVELOPMENT_ROOT,
                development_digest=DEVELOPMENT_DIGEST,
                development_files=DEVELOPMENT_FILES,
                model_root=model,
            )
    finally:
        await engine.dispose()
    _receipt(
        {
            "command": "verify",
            "database": _database_name(),
            "counts": counts,
            **report.as_dict(),
        }
    )
    return 0 if report.healthy else 1


# ------------------------------------------------------------------ delegated commands


def _delegate(command: str, forwarded: list[str]) -> int:
    script = SCRIPTS / DELEGATED[command]
    if not script.is_file():
        print(f"refused: {script} is not present", file=sys.stderr)
        return 2
    if command == "provider" and "--live" not in forwarded:
        print(
            "refused: provider work reaches a real provider and needs an explicit --live",
            file=sys.stderr,
        )
        return 2
    if command == "resume" and not any(item == "--resume-from" for item in forwarded):
        print("refused: resume needs --resume-from <previous evidence file>", file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, str(script), *forwarded])  # nosec B603


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="write task packages to a directory")
    generate.add_argument("--root", type=Path, required=True)
    generate.add_argument("--tasks", type=int, default=None)

    commands.add_parser("validate", help="offline structural checks; no store, no network")
    commands.add_parser("stats", help="row counts read back out of the C3 store")
    commands.add_parser("harvest", help="what the campaign recorded, by provenance and status")

    verify = commands.add_parser("verify", help="the unified C3 integrity report")
    verify.add_argument("--model", type=Path, default=None, help="local embedding model directory")

    for name in DELEGATED:
        delegated = commands.add_parser(name, help=f"forwarded to scripts/{DELEGATED[name]}")
        delegated.add_argument("forwarded", nargs=argparse.REMAINDER)

    arguments = parser.parse_args(argv)
    if arguments.command in DELEGATED:
        forwarded = list(arguments.forwarded)
        if forwarded and forwarded[0] == "--":
            forwarded = forwarded[1:]
        return _delegate(arguments.command, forwarded)
    if arguments.command == "generate":
        return _generate(arguments.root, arguments.tasks)
    if arguments.command == "validate":
        return _validate()
    if arguments.command == "stats":
        return asyncio.run(_stats_async())
    if arguments.command == "harvest":
        return asyncio.run(_harvest_async())
    model = arguments.model.resolve() if arguments.model else None
    return asyncio.run(_verify_async(model))


if __name__ == "__main__":
    raise SystemExit(main())
