"""Credential-free Sprint 15 Corpus Factory smoke path."""

import asyncio

from cognitive_os.corpus.factory import CorpusFactory
from cognitive_os.corpus.fixtures import FixtureArtifactStore, build_corpus_fixture
from cognitive_os.corpus.repository import InMemoryCorpusRepository


async def _smoke() -> None:
    request, source = build_corpus_fixture("cognitive-os-export")
    first = await CorpusFactory(InMemoryCorpusRepository(), FixtureArtifactStore()).ingest(
        request, source
    )
    second = await CorpusFactory(InMemoryCorpusRepository(), FixtureArtifactStore()).ingest(
        request, source
    )
    assert first == second
    assert first.manifest is not None
    assert first.export is not None and first.export.reproduced
    assert first.receipts and not first.receipts[0].promoted
    assert first.usage["destination_writes"] == 0
    assert first.usage["training_actions"] == 0
    print(first.manifest.model_dump_json())


def main() -> int:
    asyncio.run(_smoke())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
