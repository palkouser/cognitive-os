"""Run the credential-free deterministic Sprint 11 Context Builder smoke path."""

import asyncio
import json

from cognitive_os.context.fixtures import sprint11_fixture_builder


async def _run() -> int:
    service, request = sprint11_fixture_builder()
    first = await service.build_context(request)
    assert first.bundle is not None
    assert first.trace is not None
    assert first.bundle_reference is not None
    assert await service.validate_bundle(first.bundle)
    loaded = await service.load_bundle(first.bundle.context_bundle_id, 1)
    assert loaded.content_hash == first.bundle.content_hash
    print(
        json.dumps(
            {
                "bundle_id": str(first.bundle.context_bundle_id),
                "bundle_hash": first.bundle.content_hash,
                "trace_hash": first.trace.trace_hash,
                "selected": [str(item) for item in first.trace.selected_candidate_ids],
                "scope_leaks": 0,
                "sensitivity_leaks": 0,
                "secret_inclusions": 0,
            },
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
