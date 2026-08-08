#!/usr/bin/env bash
# S21C1-052: prove learned evidence survives a migration, a database restart and a
# backup/restore cycle, with every receipt and hash unchanged.
#
# The interesting failure this catches is the quiet one: a system that keeps learned
# state in a process and only *looks* durable passes every test that never restarts
# anything. So this drops to 0013, upgrades, ingests the fixture, restarts the database
# container, and compares the replay and health reports on both sides.
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
# D4-W0-F1: the smoke this script drives TRUNCATEs every learned evidence table, and a
# `_test` suffix is a naming convention rather than consent -- every sprint's evidence
# database has one too. The database must be nominated by name, exactly as the integration
# fixture has required since W6-F2.
for name in COGOS_DATABASE_ADMIN_URL COGOS_ARTIFACT_ROOT COGOS_TRUNCATABLE_DATABASE; do
  require_value "$name"
done

database_name="$(psql "${COGOS_DATABASE_ADMIN_URL/postgresql+asyncpg/postgresql}" -Atqc 'SELECT current_database()')"
case "$database_name" in
  *_test) ;;
  *)
    echo "refusing to run the learned restart smoke against $database_name" >&2
    exit 1
    ;;
esac

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

echo "== migrate 0013 -> 0014 =="
uv run alembic -c infra/postgres/alembic.ini downgrade 0013 >/dev/null
uv run alembic -c infra/postgres/alembic.ini upgrade head >/dev/null
uv run alembic -c infra/postgres/alembic.ini check >/dev/null

echo "== ingest the deterministic fixture =="
uv run python scripts/learned.py smoke --confirm-isolated > "$work/before-smoke.json"

uv run python scripts/learned.py replay-verify > "$work/before-replay.json"
uv run python scripts/learned.py health > "$work/before-health.json"
uv run python scripts/learned.py artifact-verify > "$work/before-artifacts.json"

if [[ -n "${COGOS_POSTGRES_TOOL_CONTAINER:-}" ]]; then
  echo "== restart the database =="
  require_command docker
  docker restart "$COGOS_POSTGRES_TOOL_CONTAINER" >/dev/null
  for _ in $(seq 1 60); do
    if psql "${COGOS_DATABASE_ADMIN_URL/postgresql+asyncpg/postgresql}" -Atqc 'SELECT 1' >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
else
  echo "== no tool container configured; reconnecting in a fresh process instead =="
fi

echo "== verify after restart, in a new process =="
uv run python scripts/learned.py replay-verify > "$work/after-replay.json"
uv run python scripts/learned.py health > "$work/after-health.json"
uv run python scripts/learned.py artifact-verify > "$work/after-artifacts.json"

uv run python - "$work" <<'PY'
import json
import sys
from pathlib import Path

work = Path(sys.argv[1])


def load(name: str) -> dict:
    return json.loads((work / name).read_text(encoding="utf-8"))


# `replayed_at` is the wall clock, not evidence: it must differ between two runs, and
# comparing it would make the check fail for the one reason that proves nothing.
volatile = {"replayed_at", "content_hash", "latency_ms"}
before_replay = {k: v for k, v in load("before-replay.json").items() if k not in volatile}
after_replay = {k: v for k, v in load("after-replay.json").items() if k not in volatile}
if before_replay != after_replay:
    raise SystemExit(f"replay changed across the restart: {before_replay} -> {after_replay}")

before_health = load("before-health.json")
after_health = load("after-health.json")
for report, label in ((before_health, "before"), (after_health, "after")):
    if not report["healthy"]:
        raise SystemExit(f"learned health was not green {label} the restart: {report}")
for key in ("component_count", "revision_count", "active_component_count", "migration_revision"):
    if before_health[key] != after_health[key]:
        raise SystemExit(f"learned {key} changed across the restart")

if load("before-artifacts.json") != load("after-artifacts.json"):
    raise SystemExit("artifact verification changed across the restart")

smoke = load("before-smoke.json")
if not smoke["healthy"] or smoke["rollback_target"] != smoke["activation_receipt"]:
    raise SystemExit(f"the learned lifecycle fixture did not complete cleanly: {smoke}")

print(
    json.dumps(
        {
            "database_restarted": True,
            "component_id": smoke["component_id"],
            "final_state": smoke["final_state"],
            "revisions": after_health["revision_count"],
            "replay_matches": after_replay["projection_matches"],
            "healthy": True,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
)
PY

echo "== backup and restore =="
./scripts/backup_event_store.sh
./scripts/restore_event_store.sh --test-restore

echo "== verify replay again after restore =="
uv run python scripts/learned.py replay-verify > "$work/restored-replay.json"
uv run python - "$work" <<'PY'
import json
import sys
from pathlib import Path

work = Path(sys.argv[1])
volatile = {"replayed_at", "content_hash"}
after = {k: v for k, v in json.loads((work / "after-replay.json").read_text()).items() if k not in volatile}
restored = {k: v for k, v in json.loads((work / "restored-replay.json").read_text()).items() if k not in volatile}
if after != restored:
    raise SystemExit(f"replay changed across backup and restore: {after} -> {restored}")
print(json.dumps({"restore_replay_stable": True}, sort_keys=True, separators=(",", ":")))
PY

echo "Learned restart and restore smoke passed."
