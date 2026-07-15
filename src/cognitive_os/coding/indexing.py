"""Bounded, import-free Python repository indexing and context construction."""

from __future__ import annotations

import ast
import json
import os
from hashlib import sha256
from pathlib import Path

from cognitive_os.domain.coding import (
    CodingLimits,
    ImportEntry,
    PythonModuleEntry,
    PythonSymbolEntry,
    RepositoryContextBundle,
    RepositoryFileEntry,
    RepositoryIndex,
    RepositorySearchRequest,
    RepositorySearchResult,
)

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}


def _binary(content: bytes) -> bool:
    return b"\x00" in content[:8192]


def _module_name(path: str) -> str:
    value = path.removesuffix(".py").replace("/", ".")
    return value[4:] if value.startswith("src.") else value


def _symbols(tree: ast.AST) -> tuple[PythonSymbolEntry, ...]:
    result: list[PythonSymbolEntry] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.ClassDef):
            kind = "class"
        elif isinstance(node, ast.AsyncFunctionDef):
            kind = "async_function"
        else:
            kind = "test_function" if node.name.startswith("test_") else "function"
        decorators = tuple(
            sorted(
                item.id if isinstance(item, ast.Name) else item.attr
                for item in node.decorator_list
                if isinstance(item, (ast.Name, ast.Attribute))
            )
        )
        result.append(
            PythonSymbolEntry(
                name=node.name,
                kind=kind,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                decorators=decorators,
                has_docstring=ast.get_docstring(node, clean=False) is not None,
            )
        )
    return tuple(sorted(result, key=lambda item: (item.start_line, item.name, item.kind)))


def _imports(tree: ast.AST) -> tuple[ImportEntry, ...]:
    result: list[ImportEntry] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.append(ImportEntry(module=alias.name, line=node.lineno))
        elif isinstance(node, ast.ImportFrom):
            result.append(
                ImportEntry(
                    module=("." * node.level) + (node.module or ""),
                    names=tuple(sorted(alias.name for alias in node.names)),
                    line=node.lineno,
                )
            )
    return tuple(sorted(result, key=lambda item: (item.line, item.module)))


class RepositoryIndexer:
    def __init__(self, limits: CodingLimits):
        self.limits = limits

    def build(self, root: Path, base_commit: str, workspace_revision: int) -> RepositoryIndex:
        files: list[RepositoryFileEntry] = []
        modules: list[PythonModuleEntry] = []
        warnings: list[str] = []
        total_seen = 0
        total_bytes = 0
        truncated = False
        for current, directories, names in os.walk(root, followlinks=False):
            symlink_directories = sorted(
                item for item in directories if (Path(current) / item).is_symlink()
            )
            for name in symlink_directories:
                relative = (Path(current) / name).relative_to(root).as_posix()
                files.append(
                    RepositoryFileEntry(
                        path=relative,
                        size_bytes=0,
                        file_type="symlink",
                        symlink=True,
                        ignored_reason="symlink_not_followed",
                    )
                )
            directories[:] = sorted(
                item
                for item in directories
                if item not in IGNORED_DIRECTORIES and item not in symlink_directories
            )
            for name in sorted(names):
                total_seen += 1
                if len(files) >= self.limits.maximum_repository_files:
                    truncated = True
                    break
                path = Path(current) / name
                relative = path.relative_to(root).as_posix()
                if relative == ".git":
                    continue
                if path.is_symlink():
                    files.append(
                        RepositoryFileEntry(
                            path=relative,
                            size_bytes=0,
                            file_type="symlink",
                            symlink=True,
                            ignored_reason="symlink_not_followed",
                        )
                    )
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    warnings.append(f"stat_failed:{relative}")
                    continue
                if size > self.limits.maximum_indexed_file_bytes:
                    files.append(
                        RepositoryFileEntry(
                            path=relative,
                            size_bytes=size,
                            file_type="oversized",
                            ignored_reason="file_byte_limit",
                        )
                    )
                    continue
                if total_bytes + size > self.limits.maximum_total_index_bytes:
                    truncated = True
                    break
                try:
                    content = path.read_bytes()
                except OSError:
                    warnings.append(f"read_failed:{relative}")
                    continue
                total_bytes += len(content)
                binary = _binary(content)
                entry = RepositoryFileEntry(
                    path=relative,
                    size_bytes=len(content),
                    content_hash=sha256(content).hexdigest(),
                    file_type="binary" if binary else "text",
                    language="python" if relative.endswith(".py") else None,
                    generated=relative.startswith(("dist/", "build/")),
                    binary=binary,
                    test_file=relative.startswith("tests/") or "/test_" in relative,
                    configuration=relative.endswith((".toml", ".yaml", ".yml", ".ini")),
                    ignored_reason="binary" if binary else None,
                )
                files.append(entry)
                if relative.endswith(".py") and not binary:
                    try:
                        source = content.decode("utf-8")
                        tree = ast.parse(source, filename=relative)
                    except (UnicodeDecodeError, SyntaxError) as error:
                        modules.append(
                            PythonModuleEntry(
                                path=relative,
                                module=_module_name(relative),
                                parse_error=type(error).__name__,
                            )
                        )
                    else:
                        modules.append(
                            PythonModuleEntry(
                                path=relative,
                                module=_module_name(relative),
                                symbols=_symbols(tree),
                                imports=_imports(tree),
                            )
                        )
            if truncated:
                break
        return RepositoryIndex(
            base_commit=base_commit,
            workspace_revision=workspace_revision,
            files=tuple(sorted(files, key=lambda item: item.path)),
            modules=tuple(sorted(modules, key=lambda item: item.path)),
            warnings=tuple(sorted(warnings)),
            truncated=truncated,
            total_files_seen=total_seen,
            total_bytes_indexed=total_bytes,
        )

    def search(
        self, root: Path, request: RepositorySearchRequest
    ) -> tuple[RepositorySearchResult, ...]:
        results: list[RepositorySearchResult] = []
        for path in sorted(root.rglob("*")):
            if len(results) >= request.maximum_results:
                break
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root).as_posix()
            if any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts):
                continue
            if request.path_filters and not any(
                relative == prefix or relative.startswith(f"{prefix}/")
                for prefix in request.path_filters
            ):
                continue
            try:
                content = path.read_bytes()
                if _binary(content) or len(content) > self.limits.maximum_indexed_file_bytes:
                    continue
                lines = content.decode("utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, start=1):
                matched = request.query in line
                if request.regex:
                    import re

                    matched = re.search(request.query, line) is not None
                if matched:
                    results.append(
                        RepositorySearchResult(path=relative, line=number, text=line[:2000])
                    )
                    if len(results) >= request.maximum_results:
                        break
        return tuple(results)

    def context(
        self,
        index: RepositoryIndex,
        profile_summary: dict[str, object],
        searches: tuple[RepositorySearchResult, ...],
    ) -> RepositoryContextBundle:
        safe_summary = json.loads(json.dumps(profile_summary))
        return RepositoryContextBundle(
            base_commit=index.base_commit,
            workspace_revision=index.workspace_revision,
            index_hash=index.canonical_hash(),
            profile_summary=safe_summary,
            search_results=searches[: self.limits.maximum_search_results],
            exclusions=tuple(
                sorted(item.path for item in index.files if item.ignored_reason is not None)
            ),
            truncated=index.truncated or len(searches) > self.limits.maximum_search_results,
        )
