"""D4-W0-F1. Why the Sprint 21D3 learned store is empty, established rather than guessed.

The question S21D4-003 raised was whether the D3 campaign's observations and datasets were
never persisted or were persisted and later removed. Three independent signals answer it, and
they agree.

1. The append-only Event Store, which was never truncated, holds committed
   `learned.observation_recorded` events. Observations were written *and committed*.
2. `pg_stat_user_tables` reports inserts into `learned_observations` with `n_tup_del = 0`.
   Rows entered and no DELETE ever ran.
3. Every one of the nine `learned_*` tables has `relfilenode != oid`, in one contiguous block,
   while every other table in the database still has `relfilenode == oid` and Sprint 21D2's
   store is untouched. A table is rewritten like that by TRUNCATE -- which is also why signal 2
   shows no deletes, since TRUNCATE does not count them.

The mechanism is `cognitive_os.learned_smoke.run_learned_smoke`, which truncates exactly
`LEARNED_EVIDENCE_TABLES` and, before this sprint, was fenced only by the database name ending
in `_test`. Every sprint's evidence database ends in `_test`.

    UV_CACHE_DIR=.cache/uv uv run python scripts/finding_w0_f1_d4.py

Read-only. Every statement is a SELECT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"

CONTAINER = "compose-postgres-1"
OWNER = "cogos_owner"
SUBJECT = "cognitive_os_s21d3_test"
CONTROL = "cognitive_os_s21d2_test"


def _psql(database: str, query: str) -> list[str]:
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", OWNER, "-d", database, "-tAc", query],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def _tuple_stats(database: str) -> dict[str, dict[str, int]]:
    rows = _psql(
        database,
        "select relname||'|'||n_tup_ins||'|'||n_tup_del||'|'||n_live_tup||'|'||n_dead_tup "
        "from pg_stat_user_tables where relname in "
        "('learned_observations','learned_datasets','artifacts','events') order by relname",
    )
    out = {}
    for row in rows:
        name, ins, dele, live, dead = row.split("|")
        out[name] = {
            "inserted": int(ins),
            "deleted": int(dele),
            "live": int(live),
            "dead": int(dead),
        }
    return out


def _rewritten(database: str) -> dict[str, Any]:
    rows = _psql(
        database,
        "select c.relname||'|'||c.oid||'|'||c.relfilenode from pg_class c "
        "join pg_namespace n on n.oid=c.relnamespace "
        "where n.nspname='cognitive_os' and c.relkind='r' order by c.relname",
    )
    rewritten, untouched = [], []
    for row in rows:
        name, oid, node = row.split("|")
        (rewritten if oid != node else untouched).append(name)
    return {
        "rewritten": sorted(rewritten),
        "rewritten_count": len(rewritten),
        "untouched_count": len(untouched),
        "every_rewritten_table_is_a_learned_table": all(
            name.startswith("learned_") or name == "provider_output_records" for name in rewritten
        ),
    }


def _observation_events(database: str) -> dict[str, Any]:
    rows = _psql(
        database,
        "set search_path to cognitive_os; select count(*)||'|'||min(occurred_at)||'|'||"
        "max(occurred_at) from events where event_type='learned.observation_recorded'",
    )
    count, first, last = rows[-1].split("|")
    return {"committed_events": int(count), "first": first, "last": last}


def build() -> dict[str, Any]:
    subject_stats = _tuple_stats(SUBJECT)
    control_stats = _tuple_stats(CONTROL)
    subject_files = _rewritten(SUBJECT)
    control_files = _rewritten(CONTROL)
    events = _observation_events(SUBJECT)

    observations = subject_stats["learned_observations"]
    persisted_and_committed = events["committed_events"] > 0
    no_delete_ran = observations["deleted"] == 0
    tables_were_rewritten = "learned_observations" in subject_files["rewritten"]

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W0",
        "items": ["S21D4-003"],
        "finding": "D4-W0-F1",
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "question": (
            "Were the Sprint 21D3 learned observations and datasets never persisted, or "
            "persisted and later removed?"
        ),
        "answer": "persisted and committed, then removed by TRUNCATE",
        "signals": {
            "committed_observation_events": events,
            "tuple_statistics": {"subject": subject_stats, "control": control_stats},
            "table_rewrites": {"subject": subject_files, "control": control_files},
        },
        "reasoning": {
            "persisted_and_committed": persisted_and_committed,
            "no_delete_statement_ever_ran": no_delete_ran,
            "learned_tables_were_rewritten": tables_were_rewritten,
            "why_truncate_and_not_rollback": (
                "A rollback leaves no committed events, and this store holds "
                f"{events['committed_events']} committed learned.observation_recorded events. A "
                "rollback also does not assign a new relfilenode; TRUNCATE does, and does not "
                "increment n_tup_del, which is exactly the pattern observed."
            ),
            "why_truncate_and_not_delete": (
                f"n_tup_del is {observations['deleted']} on learned_observations. DELETE would "
                "have counted."
            ),
        },
        "mechanism": {
            "callable": "cognitive_os.learned_smoke.run_learned_smoke",
            "statement": "TRUNCATE <LEARNED_EVIDENCE_TABLES> RESTART IDENTITY CASCADE",
            "fence_before_this_sprint": "the database name had to end in _test",
            "why_the_fence_failed": (
                "every sprint's evidence database also ends in _test, so the name check passed"
            ),
            "precedent": (
                "postgres_provision_evidence.sh records that the same _test-suffix guard is how "
                "the C3 evidence store was truncated twice; W6-F2 answered it for the "
                "integration suite by giving that suite its own database. This code path never "
                "got the same treatment."
            ),
        },
        "consequences": {
            "d3_result_disturbed": False,
            "why_not": (
                "the learner selection is committed evidence and S21D4-001 recomputes its full "
                "24-setting grid from that file without reading the store"
            ),
            "irrecoverable": (
                "every backup of the D3 store was taken after the erasure, so the observations "
                "and the two materialised revision-3 datasets cannot be restored"
            ),
            "w7_restore_proof_is_vacuous_for_learned_tables": (
                "the restore verified matching counts between a source and a copy whose learned "
                "tables were both already empty"
            ),
        },
        "remedy": {
            "item": "S21D4-003 finding fix, this sprint",
            "primary_fence": {
                "change": "cognitive_os.learned_smoke._require_nomination",
                "rule": "COGOS_TRUNCATABLE_DATABASE must name the connected database",
                "why_this_one": (
                    "it is the released convention, not a new one: the PostgreSQL integration "
                    "fixture has required the same variable since W6-F2 for the same reason. A "
                    "second mechanism answering the same question differently is how an "
                    "operator ends up knowing one fence and meeting the other."
                ),
                "callers_updated": [
                    "scripts/learned_restart_smoke.sh",
                    "docs/operations/learned-evidence.md",
                ],
                "callers_already_compliant": [
                    ".github/workflows/ci.yml postgres-integration lane",
                    "scripts/verification_matrix.py",
                ],
            },
            "change": "cognitive_os.learned_smoke._require_erasable",
            "rule": (
                "refuse when the learned store holds an observation, a dataset, or a component "
                "other than the inert reference one"
            ),
            "why_this_second_fence_exists": (
                "nomination is consent, and consent can be given by mistake -- an operator "
                "following a runbook against the wrong sprint's environment nominates exactly "
                "the database that must not be erased. Kept against the usual rule about second "
                "mechanisms because the failure it prevents is irreversible data loss."
            ),
            "regression_test": ("tests/cognitive_os/learned_evidence/test_learned_smoke_guard.py"),
        },
        "zero_predecessor_writes": True,
    }
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d4-finding-w0-f1.json"))
    arguments = parser.parse_args()

    record = build()
    Path(arguments.output).write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": Path(arguments.output).name,
                "answer": record["answer"],
                "committed_observation_events": record["signals"]["committed_observation_events"][
                    "committed_events"
                ],
                "learned_tables_rewritten": record["signals"]["table_rewrites"]["subject"][
                    "rewritten_count"
                ],
                "control_tables_rewritten": record["signals"]["table_rewrites"]["control"][
                    "rewritten_count"
                ],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
