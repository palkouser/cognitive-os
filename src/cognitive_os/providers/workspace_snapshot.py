"""Content-and-mode snapshots of a provider working directory.

The Sprint 21C1 guard compared `git status --porcelain` before and after execution. That
misses the case that matters most: a file that was *already* dirty and was then modified
again produces byte-identical status output, so the guard reports success while the
provider has rewritten the fixture.

This module hashes what actually changed. For every entry under the root it records the
relative path, the entry type, the executable bit and — for regular files — the content
hash; for symlinks, the hash of the link target, so replacing a file with a link to
somewhere else is a change rather than a coincidence. Comparing two snapshots therefore
detects modification of a dirty file, creation, deletion, rename, mode change and symlink
substitution, and needs no Git repository at all.

Diagnostics carry paths and hashes. Never content: a mutation report that quoted the bytes
an advisory provider wrote would put that content into the log, the event and the report.
See ADR 0087.
"""

from __future__ import annotations

import stat
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex

#: Read in blocks so a large fixture file cannot be pulled into memory whole.
_READ_BLOCK = 1024 * 1024


class WorkspaceEntryKind(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    OTHER = "other"


class WorkspaceEntry(ImmutableContractModel):
    """One path, what it is, whether it is executable, and what it contains."""

    path: NonEmptyStr
    kind: WorkspaceEntryKind
    executable: bool
    content_hash: Sha256Hex

    @property
    def fingerprint(self) -> tuple[str, str, bool, str]:
        return (self.path, self.kind.value, self.executable, self.content_hash)


class WorkspaceChange(ImmutableContractModel):
    """One difference between two snapshots, described without quoting content."""

    path: NonEmptyStr
    change: NonEmptyStr
    before: NonEmptyStr | None = None
    after: NonEmptyStr | None = None


class WorkspaceSnapshot(ImmutableContractModel):
    """Every entry under one root, in a stable order."""

    root: NonEmptyStr
    entries: tuple[WorkspaceEntry, ...]

    @property
    def digest(self) -> str:
        """One hash over the whole tree, for a cheap equality check and for evidence."""
        joined = "\n".join(
            "|".join((entry.path, entry.kind.value, str(entry.executable), entry.content_hash))
            for entry in self.entries
        )
        return sha256(joined.encode()).hexdigest()

    def difference(self, other: WorkspaceSnapshot) -> tuple[WorkspaceChange, ...]:
        """What changed between this snapshot and a later one.

        A rename surfaces as one deletion and one creation. That is deliberate: naming it a
        rename would require guessing which pair belongs together, and for a guard whose job
        is "nothing changed", two reported changes are the honest answer.
        """
        before = {entry.path: entry for entry in self.entries}
        after = {entry.path: entry for entry in other.entries}
        changes: list[WorkspaceChange] = []
        for path in sorted(set(before) - set(after)):
            changes.append(
                WorkspaceChange(path=path, change="deleted", before=before[path].content_hash)
            )
        for path in sorted(set(after) - set(before)):
            changes.append(
                WorkspaceChange(path=path, change="created", after=after[path].content_hash)
            )
        for path in sorted(set(before) & set(after)):
            old, new = before[path], after[path]
            if old.kind is not new.kind:
                changes.append(
                    WorkspaceChange(
                        path=path,
                        change="type_changed",
                        before=old.kind.value,
                        after=new.kind.value,
                    )
                )
            elif old.executable != new.executable:
                changes.append(
                    WorkspaceChange(
                        path=path,
                        change="mode_changed",
                        before=f"executable={old.executable}",
                        after=f"executable={new.executable}",
                    )
                )
            elif old.content_hash != new.content_hash:
                changes.append(
                    WorkspaceChange(
                        path=path,
                        change="content_changed",
                        before=old.content_hash,
                        after=new.content_hash,
                    )
                )
        return tuple(changes)


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(_READ_BLOCK):
            digest.update(block)
    return digest.hexdigest()


def _entry_for(path: Path, relative: str) -> WorkspaceEntry:
    # `lstat`, not `stat`: following the link would hash the target's content and report a
    # symlink swap as no change at all.
    info = path.lstat()
    mode = info.st_mode
    executable = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
    if stat.S_ISLNK(mode):
        return WorkspaceEntry(
            path=relative,
            kind=WorkspaceEntryKind.SYMLINK,
            executable=executable,
            content_hash=sha256(str(path.readlink()).encode()).hexdigest(),
        )
    if stat.S_ISDIR(mode):
        # Directories are recorded so that removing an empty one is still a change; there
        # is nothing to hash, so the hash is of the kind itself.
        return WorkspaceEntry(
            path=relative,
            kind=WorkspaceEntryKind.DIRECTORY,
            executable=executable,
            content_hash=sha256(b"directory").hexdigest(),
        )
    if stat.S_ISREG(mode):
        return WorkspaceEntry(
            path=relative,
            kind=WorkspaceEntryKind.FILE,
            executable=executable,
            content_hash=_hash_file(path),
        )
    # A socket, FIFO or device node under a fixture is not something to hash, and it is
    # also not something to ignore: its appearance or disappearance is a change.
    return WorkspaceEntry(
        path=relative,
        kind=WorkspaceEntryKind.OTHER,
        executable=executable,
        content_hash=sha256(f"other:{stat.S_IFMT(mode)}".encode()).hexdigest(),
    )


def snapshot_workspace(root: Path, *, exclude: frozenset[str] = frozenset()) -> WorkspaceSnapshot:
    """Hash every entry under `root`.

    `exclude` holds relative paths the runner itself owns. It is deliberately narrow: an
    excluded path is a path a provider could change unobserved, so the runner keeps its own
    temporary files outside the working directory and passes nothing here in normal use.
    """
    resolved = root.resolve()
    if not resolved.is_dir():
        raise ValueError(f"workspace root is not a directory: {root}")
    entries: list[WorkspaceEntry] = []
    for path in sorted(resolved.rglob("*")):
        relative = path.relative_to(resolved).as_posix()
        if relative in exclude or any(relative.startswith(f"{excluded}/") for excluded in exclude):
            continue
        entries.append(_entry_for(path, relative))
    return WorkspaceSnapshot(root=resolved.as_posix(), entries=tuple(entries))
