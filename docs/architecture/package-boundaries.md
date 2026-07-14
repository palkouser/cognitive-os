# Package boundaries

`src/cognitive_os` is owned and distributed by Cognitive OS. `LightAgent` is the pinned
Apache-2.0 donor runtime kept at the repository root for compatibility testing.

Allowed import direction:

```text
cognitive_os.runtime -> LightAgent public APIs
tests/contract       -> LightAgent public APIs
LightAgent           -> standard library and declared third-party dependencies
```

LightAgent must not import `cognitive_os`. Other Cognitive OS packages must not reach into
LightAgent private implementation details; adapters belong in `cognitive_os.runtime`.
Upstream synchronization starts from the pinned donor commit, is recorded in the provenance
registry, and must rerun the contract suite. The Cognitive OS wheel intentionally excludes
LightAgent during Sprint 1.
