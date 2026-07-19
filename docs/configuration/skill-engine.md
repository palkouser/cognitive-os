# Skill Engine configuration

`config/skills.example.yaml` contains the complete fail-closed configuration surface. Limits cover
package size and shape, preconditions, steps, requirements, fallbacks, tool/provider/Context calls,
execution duration, repairs, and statistics thresholds.

Deferred authority flags default to `false` and validation rejects enabling imported verification,
dynamic capability registration, arbitrary precondition code, direct scripts, network downloads,
automatic generation or promotion, provider selection, and unverified execution. Global scope is
also disabled by default.

Production persistence uses `COGOS_DATABASE_URL` and `COGOS_ARTIFACT_ROOT`. Never place either value
or any credential in skill packages, events, reports, or tracked configuration.
