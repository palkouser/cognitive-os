import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.corpus.errors import CorpusSourceError
from cognitive_os.corpus.sources import inspect_local_archive, inspect_local_directory


def _archive(path: Path, name: str, content: bytes) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)


def test_archive_traversal_and_expansion_are_rejected(tmp_path: Path) -> None:
    traversal = tmp_path / "traversal.zip"
    _archive(traversal, "../escape.txt", b"unsafe")
    with pytest.raises(CorpusSourceError, match="traverses"):
        inspect_local_archive(
            traversal,
            source_identity="fixture:traversal",
            source_revision="1",
            config=CorpusConfiguration(),
        )
    bomb = tmp_path / "bomb.zip"
    _archive(bomb, "large.txt", b"0" * 100_000)
    with pytest.raises(CorpusSourceError, match="expansion ratio"):
        inspect_local_archive(
            bomb,
            source_identity="fixture:bomb",
            source_revision="1",
            config=CorpusConfiguration(maximum_archive_expansion_ratio=2),
        )


def test_tar_links_are_rejected(tmp_path: Path) -> None:
    archive_path = tmp_path / "link.tar"
    with tarfile.open(archive_path, "w") as archive:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "target"
        archive.addfile(info, io.BytesIO())
    with pytest.raises(CorpusSourceError, match="links"):
        inspect_local_archive(
            archive_path,
            source_identity="fixture:link",
            source_revision="1",
            config=CorpusConfiguration(),
        )


def test_directory_symlink_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "source.md").write_text("safe", encoding="utf-8")
    (tmp_path / "linked.md").symlink_to(tmp_path / "source.md")
    with pytest.raises(CorpusSourceError, match="symlink"):
        inspect_local_directory(
            tmp_path,
            source_identity="fixture:directory",
            source_revision="1",
            config=CorpusConfiguration(),
        )
