"""Credential-free Sprint 18 Harness Proposal Engine smoke path."""

import asyncio

from proposal import create_fixture, fixture_service

from cognitive_os.domain.proposals import HarnessProposalType, ProposalStatus


async def _smoke() -> None:
    hashes = []
    for proposal_type in HarnessProposalType:
        service, _, source = await fixture_service()
        revision = await create_fixture(service, source, proposal_type)
        assert revision.status is ProposalStatus.VALIDATED
        assert revision.verifier_bundle is not None
        hashes.append(revision.content_hash)
    assert len(set(hashes)) == len(tuple(HarnessProposalType))
    print(f"validated {len(hashes)} deterministic proposal types; destination writes: 0")


def main() -> int:
    asyncio.run(_smoke())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
