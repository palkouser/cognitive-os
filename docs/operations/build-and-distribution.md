# Build and distribution

Build and install the wheel in a clean environment:

```bash
uv build
./scripts/verify_distribution.sh
```

The distribution includes only `cognitive_os`. It excludes LightAgent, tests, documentation,
runtime data, environment files, traces, models, and translated README files.
