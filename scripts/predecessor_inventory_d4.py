"""S21D4-003. What the Sprint 21D3 predecessor authority actually contains.

The inventory exists to find out, not to restate. It reads the committed D3 evidence and then
reads the D3 store read-only, and reports both -- because the interesting case is the one where
they disagree, and that is the case this run found.

**The D3 learned store holds no observations and no explicit datasets.** The D3 execution log
records 200 fitting and 80 calibration `SELF_PLAY` outcomes ingested and two immutable
revision-3 datasets materialised. `cognitive_os_s21d3_test` contains zero of each, while
holding the 3,306 artifacts, 1,971 artifact blobs and 1,731 events that prove the campaign ran
against exactly this database. Sprint 21D2's store, read as a control, holds its documented 480
observations and 2 datasets.

This does not disturb the D3 result. The learner selection was computed in-process and its
evidence is committed, self-consistent and independently recomputable -- S21D4-001 recomputes
its full 24-setting grid from that file. What it changes is what a successor may assume: there
are no D3 rows to reuse, so every D4 exemplar has to come from a campaign D4 runs itself, which
is what the D4 backlog already requires.

    UV_CACHE_DIR=.cache/uv uv run python scripts/predecessor_inventory_d4.py

Read-only. It opens the predecessor store for counts and writes to nothing.
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
D3_DATABASE = "cognitive_os_s21d3_test"
D2_DATABASE = "cognitive_os_s21d2_test"

COUNTED_TABLES = (
    "learned_observations",
    "learned_datasets",
    "learned_artifacts",
    "learned_components",
    "learned_component_revisions",
    "learned_activation_approvals",
    "learned_activation_history",
    "learned_accesses",
    "learned_evidence_records",
    "artifacts",
    "artifact_blobs",
    "events",
)


def _counts(database: str) -> dict[str, int]:
    """Read-only row counts. `count(*)` rather than `n_live_tup`, which is an estimate."""
    query = "set search_path to cognitive_os; " + " union all ".join(
        f"select '{table}='||count(*) from {table}" for table in COUNTED_TABLES
    )
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", OWNER, "-d", database, "-tAc", query],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    counts = {}
    for line in out.splitlines():
        if "=" in line:
            name, _, value = line.partition("=")
            counts[name.strip()] = int(value)
    return counts


def _evidence_claims() -> dict[str, Any]:
    campaign = json.loads(
        (EVIDENCE / "sprint-21d3-self-play-campaign.json").read_text(encoding="utf-8")
    )
    partitions = {part["partition"]: part for part in campaign["partitions"]}
    return {
        "source": "sprint-21d3-self-play-campaign.json",
        "source_sha256": hashlib.sha256(
            (EVIDENCE / "sprint-21d3-self-play-campaign.json").read_bytes()
        ).hexdigest(),
        "partitions": {
            name: {
                "groups": part.get("groups"),
                "outcomes": part.get("outcomes") or part.get("recorded_outcomes"),
                "dataset_id": part.get("dataset_id"),
            }
            for name, part in partitions.items()
        },
    }


def _stops() -> dict[str, str]:
    selection = json.loads(
        (EVIDENCE / "sprint-21d3-learner-selection.json").read_text(encoding="utf-8")
    )
    holdout = json.loads(
        (EVIDENCE / "sprint-21d3-retrieval-holdout-result.json").read_text(encoding="utf-8")
    )
    return {
        "correction_selection": selection["selection"]["content_hash"],
        "retrieval_holdout": holdout["decision"]["stop_hash"],
    }


def _not_opened() -> dict[str, Any]:
    checkpoint = json.loads(
        (EVIDENCE / "sprint-21d3-pre-final-checkpoint.json").read_text(encoding="utf-8")
    )
    mapping = checkpoint.get("not_opened") or checkpoint.get("dependent_not_opened") or []
    items = sorted(row["item"] for row in mapping)
    stops = sorted({row["stop_hash"] for row in mapping})
    return {
        "authorised": checkpoint["decision"]["authorised"],
        "bound_to_one_stop_hash": len(stops) == 1,
        "stop_hashes": stops,
        "count": len(items),
        "items": items,
        "final_or_canary_outcomes_inspected": checkpoint.get(
            "final_or_canary_outcomes_inspected", 0
        ),
    }


def build() -> dict[str, Any]:
    d3 = _counts(D3_DATABASE)
    d2 = _counts(D2_DATABASE)
    claims = _evidence_claims()

    store_holds_no_learned_rows = d3["learned_observations"] == 0 and d3["learned_datasets"] == 0
    campaign_ran_against_this_store = d3["artifacts"] > 0 and d3["events"] > 0

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W0",
        "items": ["S21D4-003"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authority": "committed D3 evidence plus read-only SQL counts over the D3 store",
        "d3_store_counts": d3,
        "d2_store_counts_as_control": d2,
        "evidence_claims": claims,
        "finding": {
            "id": "D4-W0-F1",
            "subject": "the D3 learned store",
            "store_holds_no_learned_observations_or_datasets": store_holds_no_learned_rows,
            "campaign_demonstrably_ran_against_this_store": campaign_ran_against_this_store,
            "control_holds_its_documented_rows": d2["learned_observations"] == 480
            and d2["learned_datasets"] == 2,
            "observed": (
                "cognitive_os_s21d3_test contains 0 learned observations and 0 learned "
                f"datasets while holding {d3['artifacts']} artifacts, "
                f"{d3['artifact_blobs']} artifact blobs and {d3['events']} events. The D3 "
                "execution log records 280 ingested SELF_PLAY outcomes and two materialised "
                "revision-3 datasets. cognitive_os_s21d2_test, read as a control, holds its "
                f"documented {d2['learned_observations']} observations and "
                f"{d2['learned_datasets']} datasets."
            ),
            "does_not_disturb": (
                "The D3 result stands. The learner selection is committed evidence and "
                "S21D4-001 recomputes its full 24-setting grid from that file without touching "
                "the store."
            ),
            "consequence_for_d4": (
                "There are no D3 rows to reuse. Every D4 fitting exemplar must come from a "
                "campaign D4 executes itself under new run identities, which the D4 backlog "
                "already requires. S21D4-012's fitting pool is therefore a set of task "
                "packages to re-run, never a set of rows to read."
            ),
        },
        "stop_hashes": _stops(),
        "dependent_not_opened": _not_opened(),
        "protected_roles": {
            "final_a": {"groups": 30, "candidate_slots": 120, "outcomes": 0},
            "final_b": {"groups": 30, "candidate_slots": 120, "outcomes": 0},
            "canary": {"groups": 5, "candidate_slots": 20, "outcomes": 0},
            "source": "sprint-21d3-sealed-manifests.json",
        },
        "invalid_selection_patterns": [
            "all observations on this surface",
            "latest seal for this partition",
            "every artifact in this store",
        ],
        "zero_predecessor_writes": True,
    }
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", default=str(EVIDENCE / "sprint-21d4-predecessor-inventory.json")
    )
    arguments = parser.parse_args()

    record = build()
    Path(arguments.output).write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": Path(arguments.output).name,
                "d3_learned_observations": record["d3_store_counts"]["learned_observations"],
                "d3_learned_datasets": record["d3_store_counts"]["learned_datasets"],
                "d2_control_observations": record["d2_store_counts_as_control"][
                    "learned_observations"
                ],
                "finding": record["finding"]["id"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
