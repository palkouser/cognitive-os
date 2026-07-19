# Skill Engine operations

Inspect repository packages and run the credential-free smoke path:

```bash
uv run python scripts/skill.py list-packages
uv run python scripts/skill.py inspect-package procedural_skills/coding/repository-inspection
uv run python scripts/skill_smoke_test.py
```

The `skill.py` CLI supports dry-run package import/export, create, revise, stage, verify, deprecate,
supersede, retract, history, and health. Persistent operations require the normal PostgreSQL and
artifact-store configuration. Execution, resume, and cancellation are intentionally accepted only
through a running application that supplies the existing Controller adapter.

Run migration and diagnostics with:

```bash
uv run alembic -c infra/postgres/alembic.ini upgrade head
uv run python scripts/skill_health.py
```

Backup and isolated restore use the existing event-store scripts. Their manifests verify skill item
and revision counts plus the canonical revision history digest and package-reference integrity.
