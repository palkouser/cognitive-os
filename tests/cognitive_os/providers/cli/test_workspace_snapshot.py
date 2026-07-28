"""The mutation guard, against every change a `git status` comparison would miss.

The first case is the one this module exists for: a file that was already modified locally,
then modified again by the provider. `git status --porcelain` prints the same line before
and after, so the Sprint 21C1 guard reported success.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from cognitive_os.providers.workspace_snapshot import (
    WorkspaceEntryKind,
    snapshot_workspace,
)

from .fake_executable import build_fixture_workspace


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return build_fixture_workspace(tmp_path / "fixture")


class TestChangeDetection:
    def test_an_untouched_tree_reports_no_change(self, workspace: Path) -> None:
        before = snapshot_workspace(workspace)
        after = snapshot_workspace(workspace)
        assert before.difference(after) == ()
        assert before.digest == after.digest

    def test_rewriting_an_already_dirty_file_is_detected(self, workspace: Path) -> None:
        """The defect this replaces: identical `git status` output, different content."""
        before = snapshot_workspace(workspace)
        (workspace / "dirty.txt").write_text("rewritten by the provider\n", encoding="utf-8")
        changes = before.difference(snapshot_workspace(workspace))
        assert [(item.path, item.change) for item in changes] == [("dirty.txt", "content_changed")]
        assert changes[0].before != changes[0].after

    def test_creation_is_detected(self, workspace: Path) -> None:
        before = snapshot_workspace(workspace)
        (workspace / "new.txt").write_text("new\n", encoding="utf-8")
        changes = before.difference(snapshot_workspace(workspace))
        assert [(item.path, item.change) for item in changes] == [("new.txt", "created")]

    def test_deletion_is_detected(self, workspace: Path) -> None:
        before = snapshot_workspace(workspace)
        (workspace / "fixture.txt").unlink()
        changes = before.difference(snapshot_workspace(workspace))
        assert [(item.path, item.change) for item in changes] == [("fixture.txt", "deleted")]

    def test_a_rename_is_reported_as_a_deletion_and_a_creation(self, workspace: Path) -> None:
        """Two honest changes rather than one guessed pairing."""
        before = snapshot_workspace(workspace)
        (workspace / "fixture.txt").rename(workspace / "renamed.txt")
        changes = before.difference(snapshot_workspace(workspace))
        assert {(item.path, item.change) for item in changes} == {
            ("fixture.txt", "deleted"),
            ("renamed.txt", "created"),
        }

    def test_a_mode_change_alone_is_detected(self, workspace: Path) -> None:
        """Content identical, permissions not: a script that became executable."""
        target = workspace / "fixture.txt"
        before = snapshot_workspace(workspace)
        target.chmod(target.stat().st_mode | stat.S_IXUSR)
        changes = before.difference(snapshot_workspace(workspace))
        assert [(item.path, item.change) for item in changes] == [("fixture.txt", "mode_changed")]

    def test_replacing_a_file_with_a_symlink_is_detected(self, workspace: Path) -> None:
        """`lstat`, not `stat`: following the link would hash the target and see nothing."""
        target = workspace / "fixture.txt"
        before = snapshot_workspace(workspace)
        target.unlink()
        target.symlink_to("/etc/hostname")
        changes = before.difference(snapshot_workspace(workspace))
        assert [(item.path, item.change) for item in changes] == [("fixture.txt", "type_changed")]
        assert changes[0].after == WorkspaceEntryKind.SYMLINK.value

    def test_retargeting_an_existing_symlink_is_detected(self, workspace: Path) -> None:
        link = workspace / "link"
        link.symlink_to("fixture.txt")
        before = snapshot_workspace(workspace)
        link.unlink()
        link.symlink_to("dirty.txt")
        changes = before.difference(snapshot_workspace(workspace))
        assert [(item.path, item.change) for item in changes] == [("link", "content_changed")]

    def test_removing_an_empty_directory_is_detected(self, workspace: Path) -> None:
        (workspace / "empty").mkdir()
        before = snapshot_workspace(workspace)
        (workspace / "empty").rmdir()
        changes = before.difference(snapshot_workspace(workspace))
        assert [(item.path, item.change) for item in changes] == [("empty", "deleted")]

    def test_a_nested_change_is_reported_with_its_relative_path(self, workspace: Path) -> None:
        before = snapshot_workspace(workspace)
        (workspace / "nested" / "module.py").write_text("def add(a, b):\n    return a + b\n")
        changes = before.difference(snapshot_workspace(workspace))
        assert [item.path for item in changes] == ["nested/module.py"]


class TestTheSnapshotCarriesNoContent:
    def test_entries_carry_hashes_and_never_bytes(self, workspace: Path) -> None:
        snapshot = snapshot_workspace(workspace)
        serialized = snapshot.model_dump_json()
        assert "original fixture content" not in serialized
        assert "def add" not in serialized
        assert all(len(entry.content_hash) == 64 for entry in snapshot.entries)

    def test_a_difference_reports_hashes_not_the_changed_text(self, workspace: Path) -> None:
        before = snapshot_workspace(workspace)
        (workspace / "dirty.txt").write_text("a secret the provider wrote\n", encoding="utf-8")
        changes = before.difference(snapshot_workspace(workspace))
        serialized = "".join(change.model_dump_json() for change in changes)
        assert "a secret the provider wrote" not in serialized


class TestSnapshotShape:
    def test_entries_are_ordered_so_two_runs_hash_the_same(self, workspace: Path) -> None:
        first = snapshot_workspace(workspace)
        second = snapshot_workspace(workspace)
        assert [entry.path for entry in first.entries] == [entry.path for entry in second.entries]
        assert first.digest == second.digest

    def test_an_exclusion_covers_a_whole_subtree(self, workspace: Path) -> None:
        (workspace / "runner-temp").mkdir()
        (workspace / "runner-temp" / "schema.json").write_text("{}", encoding="utf-8")
        snapshot = snapshot_workspace(workspace, exclude=frozenset({"runner-temp"}))
        assert not any(entry.path.startswith("runner-temp") for entry in snapshot.entries)

    def test_a_missing_root_is_refused_rather_than_reported_as_empty(self, tmp_path: Path) -> None:
        """An empty snapshot of a directory that does not exist would compare equal to one."""
        with pytest.raises(ValueError, match="not a directory"):
            snapshot_workspace(tmp_path / "absent")
