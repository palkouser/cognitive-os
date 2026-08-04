"""Canonical Python source for correction-ranking-v2.

The ranker must not learn how a task author happened to spell a local name.  This module
therefore alpha-normalises source-local bindings and their resolved uses before the source is
embedded.  It deliberately emits an AST representation rather than executable Python: the
representation is a feature authority, not a source rewriter.

Only the Python 3.12 standard-library AST is used.  Reflections that can observe local names
are refused because renaming them would otherwise change semantics invisibly.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from hashlib import sha256

CANONICAL_PREFIX = b"cogos-correction-source-ast-v2\npython-grammar=3.12\n"
NORMALIZER_VERSION = "cogos-python-alpha-normalizer-v2"
_RESERVED_PREFIX = "__cogos_"
_PLACEHOLDER = re.compile(r"^__cogos_s\d{4}_b\d{4}$")
_REFLECTION_CALLS = {
    "eval",
    "exec",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "hasattr",
}


class SourceNormalizationError(ValueError):
    """Source cannot be canonicalised without changing or guessing its binding semantics."""


@dataclass(slots=True)
class _Scope:
    index: int
    kind: str
    parent: _Scope | None
    node: ast.AST
    bindings: dict[str, str] = field(default_factory=dict)
    imported: set[str] = field(default_factory=set)
    declared: set[str] = field(default_factory=set)
    globals: set[str] = field(default_factory=set)
    nonlocals: set[str] = field(default_factory=set)
    children: dict[int, _Scope] = field(default_factory=dict)
    functions: dict[str, _Scope] = field(default_factory=dict)

    def placeholder(self, name: str) -> str:
        if name in self.imported:
            raise SourceNormalizationError(
                f"mapping collision: {name!r} is both imported and source-local in one scope"
            )
        current = self.bindings.get(name)
        if current is not None:
            return current
        placeholder = f"{_RESERVED_PREFIX}s{self.index:04d}_b{len(self.bindings):04d}"
        if not _PLACEHOLDER.fullmatch(placeholder) or placeholder in self.bindings.values():
            raise SourceNormalizationError("mapping collision while allocating a placeholder")
        self.bindings[name] = placeholder
        return placeholder


def _argument_names(arguments: ast.arguments) -> tuple[str, ...]:
    names = [arg.arg for arg in (*arguments.posonlyargs, *arguments.args)]
    if arguments.vararg is not None:
        names.append(arguments.vararg.arg)
    names.extend(arg.arg for arg in arguments.kwonlyargs)
    if arguments.kwarg is not None:
        names.append(arguments.kwarg.arg)
    return tuple(names)


def _bound_pattern_names(pattern: ast.pattern) -> tuple[str, ...]:
    names: list[str] = []
    for node in ast.walk(pattern):
        if isinstance(node, ast.MatchAs | ast.MatchStar) and node.name is not None:
            names.append(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest is not None:
            names.append(node.rest)
    return tuple(names)


class _Binder(ast.NodeVisitor):
    """Assign scopes and collect lexical first bindings before any use is rewritten."""

    def __init__(self, tree: ast.Module) -> None:
        self.root = _Scope(index=0, kind="module", parent=None, node=tree)
        self.scope = self.root
        self._next_scope = 1

    def _child(self, node: ast.AST, kind: str) -> _Scope:
        child = _Scope(index=self._next_scope, kind=kind, parent=self.scope, node=node)
        self._next_scope += 1
        self.scope.children[id(node)] = child
        return child

    def _bind(self, name: str) -> None:
        _validate_name(name)
        target = self.scope
        if name in self.scope.globals:
            target = self.root
        elif name in self.scope.nonlocals:
            target = _nonlocal_scope(self.scope, name)
            if name not in target.bindings:
                # The outer binding may appear later in its code block. Its own lexical walk
                # allocates the placeholder; this nested declaration must not move that order.
                return
        if name.startswith("__") and name.endswith("__"):
            return
        target.declared.add(name)
        target.placeholder(name)

    def _declarations(self, body: list[ast.stmt]) -> None:
        # Declarations apply to the whole code block, so collect them before stores even when
        # their AST node appears later. Nested scopes are intentionally not descended into.
        def local_nodes(node: ast.AST):
            yield node
            for child in ast.iter_child_nodes(node):
                if isinstance(
                    child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda
                ):
                    continue
                yield from local_nodes(child)

        for statement in body:
            if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                self.scope.declared.add(statement.name)
                continue
            for node in local_nodes(statement):
                if isinstance(node, ast.Global):
                    self.scope.globals.update(node.names)
                elif isinstance(node, ast.Nonlocal):
                    self.scope.nonlocals.update(node.names)
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
                    self.scope.declared.add(node.id)
                elif isinstance(node, ast.ExceptHandler) and node.name is not None:
                    self.scope.declared.add(node.name)
                elif isinstance(node, ast.Import | ast.ImportFrom):
                    self.scope.declared.update(
                        alias.asname or alias.name.split(".", 1)[0]
                        for alias in node.names
                        if alias.name != "*"
                    )
        overlap = self.scope.globals & self.scope.nonlocals
        if overlap:
            raise SourceNormalizationError(
                f"ambiguous binding declared global and nonlocal: {sorted(overlap)}"
            )

    def visit_Module(self, node: ast.Module) -> None:
        self._declarations(node.body)
        for statement in node.body:
            self.visit(statement)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if getattr(node, "type_params", ()):
            raise SourceNormalizationError("unsupported syntax: generic type parameters")
        if node.name in self.scope.bindings or node.name in self.scope.imported:
            raise SourceNormalizationError(f"ambiguous local function binding: {node.name!r}")
        self._bind(node.name)
        child = self._child(node, "function")
        self.scope.functions[node.name] = child
        for decorator in node.decorator_list:
            self.visit(decorator)
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            if argument.annotation is not None:
                self.visit(argument.annotation)
        for argument in (node.args.vararg, node.args.kwarg):
            if argument is not None and argument.annotation is not None:
                self.visit(argument.annotation)
        for item in (*node.args.defaults, *node.args.kw_defaults):
            if item is not None:
                self.visit(item)
        if node.returns is not None:
            self.visit(node.returns)
        previous, self.scope = self.scope, child
        self._declarations(node.body)
        for name in _argument_names(node.args):
            self.scope.declared.add(name)
            self._bind(name)
        for statement in node.body:
            self.visit(statement)
        self.scope = previous

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Lambda(self, node: ast.Lambda) -> None:
        child = self._child(node, "lambda")
        for item in (*node.args.defaults, *node.args.kw_defaults):
            if item is not None:
                self.visit(item)
        previous, self.scope = self.scope, child
        for name in _argument_names(node.args):
            self.scope.declared.add(name)
            self._bind(name)
        self.visit(node.body)
        self.scope = previous

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if getattr(node, "type_params", ()):
            raise SourceNormalizationError("unsupported syntax: generic type parameters")
        self._bind(node.name)
        child = self._child(node, "class")
        for item in (*node.decorator_list, *node.bases, *node.keywords):
            self.visit(item)
        previous, self.scope = self.scope, child
        self._declarations(node.body)
        for statement in node.body:
            self.visit(statement)
        self.scope = previous

    def _visit_comprehension_scope(self, node: ast.AST) -> None:
        generators = node.generators  # type: ignore[attr-defined]
        if not generators:
            return
        child = self._child(node, "comprehension")
        # Python evaluates the first iterable outside the implicit comprehension scope.
        self.visit(generators[0].iter)
        previous, self.scope = self.scope, child
        for index, generator in enumerate(generators):
            if index:
                self.visit(generator.iter)
            self.visit(generator.target)
            for condition in generator.ifs:
                self.visit(condition)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)  # type: ignore[attr-defined]
        self.scope = previous

    visit_ListComp = _visit_comprehension_scope
    visit_SetComp = _visit_comprehension_scope
    visit_DictComp = _visit_comprehension_scope
    visit_GeneratorExp = _visit_comprehension_scope

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".", 1)[0]
            _validate_name(name)
            if name in self.scope.bindings:
                raise SourceNormalizationError(f"mapping collision for imported name {name!r}")
            self.scope.imported.add(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                raise SourceNormalizationError("ambiguous binding from wildcard import")
            name = alias.asname or alias.name
            _validate_name(name)
            if name in self.scope.bindings:
                raise SourceNormalizationError(f"mapping collision for imported name {name!r}")
            self.scope.imported.add(name)

    def visit_Name(self, node: ast.Name) -> None:
        _validate_name(node.id)
        if isinstance(node.ctx, ast.Store | ast.Del):
            if node.id in self.scope.functions:
                raise SourceNormalizationError(
                    f"ambiguous reassignment of local function {node.id!r}"
                )
            self._bind(node.id)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is not None:
            self.visit(node.type)
        if node.name is not None:
            self._bind(node.name)
        for statement in node.body:
            self.visit(statement)

    def visit_Match(self, node: ast.Match) -> None:
        self.visit(node.subject)
        for case in node.cases:
            for name in _bound_pattern_names(case.pattern):
                self._bind(name)
            self.visit(case.pattern)
            if case.guard is not None:
                self.visit(case.guard)
            for statement in case.body:
                self.visit(statement)

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.NamedExpr):
            raise SourceNormalizationError("unsupported syntax: assignment expression")
        if type(node).__name__ == "TypeAlias":
            raise SourceNormalizationError("unsupported syntax: type alias statement")
        super().generic_visit(node)

    def validate(self) -> None:
        def scopes(scope: _Scope):
            yield scope
            for child in scope.children.values():
                yield from scopes(child)

        for scope in scopes(self.root):
            for name in scope.nonlocals:
                target = _nonlocal_scope(scope, name)
                if name not in target.bindings and name not in target.imported:
                    raise SourceNormalizationError(
                        f"nonlocal name {name!r} has no resolved outer binding"
                    )


def _validate_name(name: str) -> None:
    if name.startswith(_RESERVED_PREFIX):
        raise SourceNormalizationError(f"reserved normalizer prefix in identifier {name!r}")


def _nonlocal_scope(scope: _Scope, name: str) -> _Scope:
    parent = scope.parent
    while parent is not None and parent.kind != "module":
        if parent.kind != "class" and (name in parent.bindings or name in parent.declared):
            return parent
        parent = parent.parent
    raise SourceNormalizationError(f"nonlocal name {name!r} has no unambiguous outer binding")


def _resolve(scope: _Scope, name: str) -> _Scope | None:
    if name in scope.globals:
        root = scope
        while root.parent is not None:
            root = root.parent
        return root if name in root.bindings else None
    if name in scope.nonlocals:
        target = _nonlocal_scope(scope, name)
        return None if name in target.imported else target
    current: _Scope | None = scope
    origin = scope
    while current is not None:
        if name in current.imported:
            return None
        if name in current.bindings:
            return current
        current = current.parent
        if origin.kind in {"function", "lambda", "comprehension"}:
            while current is not None and current.kind == "class":
                current = current.parent
    return None


class _Normalizer(ast.NodeTransformer):
    def __init__(self, binder: _Binder) -> None:
        self.root = binder.root
        self.scope = self.root

    def _mapped(self, name: str) -> str:
        resolved = _resolve(self.scope, name)
        return name if resolved is None else resolved.bindings[name]

    def visit_Name(self, node: ast.Name) -> ast.Name:
        resolved = _resolve(self.scope, node.id)
        if isinstance(node.ctx, ast.Load) and node.id in _REFLECTION_CALLS and resolved is None:
            raise SourceNormalizationError(f"reflection-unsafe binding through {node.id}")
        mapped = node.id if resolved is None else resolved.bindings[node.id]
        return ast.copy_location(ast.Name(id=mapped, ctx=node.ctx), node)

    def visit_Global(self, node: ast.Global) -> ast.Global:
        return ast.copy_location(
            ast.Global(names=[self._mapped(name) for name in node.names]), node
        )

    def visit_Nonlocal(self, node: ast.Nonlocal) -> ast.Nonlocal:
        return ast.copy_location(
            ast.Nonlocal(names=[self._mapped(name) for name in node.names]), node
        )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        if node.type is not None:
            node.type = self.visit(node.type)
        if node.name is not None:
            node.name = self._mapped(node.name)
        node.body = [self.visit(item) for item in node.body]
        return node

    def visit_MatchAs(self, node: ast.MatchAs) -> ast.MatchAs:
        if node.pattern is not None:
            node.pattern = self.visit(node.pattern)
        if node.name is not None:
            node.name = self._mapped(node.name)
        return node

    def visit_MatchStar(self, node: ast.MatchStar) -> ast.MatchStar:
        if node.name is not None:
            node.name = self._mapped(node.name)
        return node

    def visit_MatchMapping(self, node: ast.MatchMapping) -> ast.MatchMapping:
        node.keys = [self.visit(item) for item in node.keys]
        node.patterns = [self.visit(item) for item in node.patterns]
        if node.rest is not None:
            node.rest = self._mapped(node.rest)
        return node

    def _visit_arguments(self, arguments: ast.arguments) -> ast.arguments:
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs):
            argument.arg = self._mapped(argument.arg)
        if arguments.vararg is not None:
            arguments.vararg.arg = self._mapped(arguments.vararg.arg)
        if arguments.kwarg is not None:
            arguments.kwarg.arg = self._mapped(arguments.kwarg.arg)
        return arguments

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
        parent = self.scope
        node.name = self._mapped(node.name)
        node.decorator_list = [self.visit(item) for item in node.decorator_list]
        for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            if argument.annotation is not None:
                argument.annotation = self.visit(argument.annotation)
        for argument in (node.args.vararg, node.args.kwarg):
            if argument is not None and argument.annotation is not None:
                argument.annotation = self.visit(argument.annotation)
        node.args.defaults = [self.visit(item) for item in node.args.defaults]
        node.args.kw_defaults = [
            None if item is None else self.visit(item) for item in node.args.kw_defaults
        ]
        if node.returns is not None:
            node.returns = self.visit(node.returns)
        self.scope = parent.children[id(node)]
        node.args = self._visit_arguments(node.args)
        node.body = [self.visit(item) for item in node.body]
        self.scope = parent
        return node

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        parent = self.scope
        node.args.defaults = [self.visit(item) for item in node.args.defaults]
        node.args.kw_defaults = [
            None if item is None else self.visit(item) for item in node.args.kw_defaults
        ]
        self.scope = parent.children[id(node)]
        node.args = self._visit_arguments(node.args)
        node.body = self.visit(node.body)
        self.scope = parent
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        parent = self.scope
        node.name = self._mapped(node.name)
        node.decorator_list = [self.visit(item) for item in node.decorator_list]
        node.bases = [self.visit(item) for item in node.bases]
        node.keywords = [self.visit(item) for item in node.keywords]
        self.scope = parent.children[id(node)]
        node.body = [self.visit(item) for item in node.body]
        self.scope = parent
        return node

    def _visit_comprehension_scope(self, node: ast.AST) -> ast.AST:
        generators = node.generators  # type: ignore[attr-defined]
        generators[0].iter = self.visit(generators[0].iter)
        parent = self.scope
        self.scope = parent.children[id(node)]
        for index, generator in enumerate(generators):
            if index:
                generator.iter = self.visit(generator.iter)
            generator.target = self.visit(generator.target)
            generator.ifs = [self.visit(item) for item in generator.ifs]
        if isinstance(node, ast.DictComp):
            node.key = self.visit(node.key)
            node.value = self.visit(node.value)
        else:
            node.elt = self.visit(node.elt)  # type: ignore[attr-defined]
        self.scope = parent
        return node

    visit_ListComp = _visit_comprehension_scope
    visit_SetComp = _visit_comprehension_scope
    visit_DictComp = _visit_comprehension_scope
    visit_GeneratorExp = _visit_comprehension_scope

    def visit_Call(self, node: ast.Call) -> ast.AST:
        original_function = node.func.id if isinstance(node.func, ast.Name) else None
        resolved = None if original_function is None else _resolve(self.scope, original_function)
        if original_function in _REFLECTION_CALLS and resolved is None:
            raise SourceNormalizationError(
                f"reflection-unsafe binding through {original_function}()"
            )
        function_scope = None if resolved is None else resolved.functions.get(original_function)
        node.func = self.visit(node.func)
        node.args = [self.visit(item) for item in node.args]
        for keyword in node.keywords:
            keyword.value = self.visit(keyword.value)
            if keyword.arg is not None and function_scope is not None:
                keyword.arg = function_scope.bindings.get(keyword.arg, keyword.arg)
        return node


def canonical_source_bytes(source: str) -> bytes:
    """Return the exact v2 canonical bytes, or refuse when name semantics are uncertain."""
    try:
        tree = ast.parse(source, mode="exec", feature_version=(3, 12))
    except (SyntaxError, ValueError) as error:
        raise SourceNormalizationError(f"Python 3.12 parse failure: {error}") from error
    binder = _Binder(tree)
    binder.visit(tree)
    binder.validate()
    normalized = _Normalizer(binder).visit(tree)
    ast.fix_missing_locations(normalized)
    payload = ast.dump(normalized, annotate_fields=True, include_attributes=False).encode()
    return CANONICAL_PREFIX + payload


def canonical_source_hash(source: str) -> str:
    return sha256(canonical_source_bytes(source)).hexdigest()
