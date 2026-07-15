"""Strict parser for the bounded text-only unified diff subset."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import TypeAdapter

from cognitive_os.domain.coding import ChangeType, RelativeRepositoryPath


class DiffPolicyError(ValueError):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: tuple[str, ...]


@dataclass(frozen=True)
class FilePatch:
    old_path: str | None
    new_path: str | None
    change_type: ChangeType
    hunks: tuple[DiffHunk, ...]

    @property
    def path(self) -> str:
        value = self.new_path or self.old_path
        if value is None:  # pragma: no cover - construction invariant
            raise DiffPolicyError("missing_path", "file patch has no path")
        return value


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_PATH = TypeAdapter(RelativeRepositoryPath)


def _path(header: str, prefix: str) -> str | None:
    raw = header.split("\t", 1)[0].strip()
    if raw == "/dev/null":
        return None
    if not raw.startswith(prefix):
        raise DiffPolicyError("invalid_path_header", "diff path has an invalid prefix")
    return _PATH.validate_python(raw[len(prefix) :])


def parse_unified_diff(value: str, *, maximum_bytes: int = 2_000_000) -> tuple[FilePatch, ...]:
    encoded = value.encode("utf-8")
    if len(encoded) > maximum_bytes:
        raise DiffPolicyError("patch_too_large", "patch exceeds byte limit")
    forbidden_markers = (
        "GIT binary patch",
        "Binary files ",
        "old mode ",
        "new mode ",
        "new file mode 160000",
        "Subproject commit ",
        "rename from ",
        "rename to ",
    )
    if any(marker in value for marker in forbidden_markers):
        raise DiffPolicyError("unsupported_diff_feature", "binary, mode, submodule, or rename diff")
    lines = value.splitlines(keepends=True)
    patches: list[FilePatch] = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith("diff --git "):
            index += 1
            continue
        index += 1
        while index < len(lines) and not lines[index].startswith("--- "):
            if lines[index].startswith("diff --git "):
                raise DiffPolicyError("missing_file_headers", "diff lacks file headers")
            index += 1
        if index + 1 >= len(lines) or not lines[index + 1].startswith("+++ "):
            raise DiffPolicyError("missing_file_headers", "diff lacks old/new file headers")
        old_path = _path(lines[index][4:], "a/")
        new_path = _path(lines[index + 1][4:], "b/")
        index += 2
        hunks: list[DiffHunk] = []
        while index < len(lines) and not lines[index].startswith("diff --git "):
            match = _HUNK.match(lines[index].rstrip("\n"))
            if not match:
                if lines[index].strip():
                    raise DiffPolicyError("malformed_hunk", "unexpected content outside a hunk")
                index += 1
                continue
            old_start, old_count, new_start, new_count = (
                int(match.group(1)),
                int(match.group(2) or 1),
                int(match.group(3)),
                int(match.group(4) or 1),
            )
            index += 1
            hunk_lines: list[str] = []
            while index < len(lines):
                line = lines[index]
                if line.startswith(("@@ ", "diff --git ")):
                    break
                if line.startswith("\\ No newline at end of file"):
                    index += 1
                    continue
                if not line.startswith((" ", "+", "-")):
                    raise DiffPolicyError("malformed_hunk", "invalid hunk line prefix")
                hunk_lines.append(line)
                index += 1
            old_actual = sum(line[0] in " -" for line in hunk_lines)
            new_actual = sum(line[0] in " +" for line in hunk_lines)
            if old_actual != old_count or new_actual != new_count:
                raise DiffPolicyError("hunk_count_mismatch", "hunk header counts do not match")
            hunks.append(DiffHunk(old_start, old_count, new_start, new_count, tuple(hunk_lines)))
        if not hunks:
            raise DiffPolicyError("empty_file_patch", "file patch has no hunks")
        if old_path is None:
            change_type = ChangeType.ADDED
        elif new_path is None:
            change_type = ChangeType.DELETED
        else:
            if old_path != new_path:
                raise DiffPolicyError("rename_forbidden", "renames are not supported")
            change_type = ChangeType.MODIFIED
        patches.append(FilePatch(old_path, new_path, change_type, tuple(hunks)))
    if not patches:
        raise DiffPolicyError("empty_patch", "unified diff contains no file patches")
    paths = [item.path.casefold() for item in patches]
    if len(paths) != len(set(paths)):
        raise DiffPolicyError("path_collision", "patch contains duplicate or case-colliding paths")
    return tuple(patches)


def apply_file_patch(original: bytes | None, patch: FilePatch) -> bytes | None:
    if original is None and patch.change_type is not ChangeType.ADDED:
        raise DiffPolicyError("missing_target", "patch target does not exist")
    if original is not None and b"\x00" in original:
        raise DiffPolicyError("binary_target", "binary targets are forbidden")
    try:
        source = [] if original is None else original.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        raise DiffPolicyError("invalid_utf8", "patch target is not UTF-8") from None
    output: list[str] = []
    cursor = 0
    for hunk in patch.hunks:
        expected = max(hunk.old_start - 1, 0)
        if expected < cursor or expected > len(source):
            raise DiffPolicyError("hunk_position", "hunk position is invalid")
        output.extend(source[cursor:expected])
        cursor = expected
        for line in hunk.lines:
            content = line[1:]
            if line[0] in " -":
                if cursor >= len(source) or source[cursor] != content:
                    raise DiffPolicyError("context_mismatch", "patch context does not match target")
                if line[0] == " ":
                    output.append(content)
                cursor += 1
            else:
                output.append(content)
    output.extend(source[cursor:])
    if patch.change_type is ChangeType.DELETED:
        if output:
            raise DiffPolicyError("incomplete_delete", "delete patch leaves file content")
        return None
    rendered = "".join(output)
    if output and original is not None and original.endswith(b"\n") and not rendered.endswith("\n"):
        rendered += "\n"
    return rendered.encode("utf-8")
