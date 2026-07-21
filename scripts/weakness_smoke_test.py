"""Credential-free Sprint 17 Weakness Mining smoke path."""

import asyncio

from weakness import fixture_service


async def _smoke() -> None:
    first_service, request, profile = fixture_service(18)
    first = await first_service.mine(request, profile)
    second_service, _, _ = fixture_service(18)
    second = await second_service.mine(request, profile)
    assert first == second
    assert first.manifest is not None
    assert first.manifest.summary.signal_count == 18
    assert first.manifest.summary.weakness_count > 0
    print(first.manifest.model_dump_json())


def main() -> int:
    asyncio.run(_smoke())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
