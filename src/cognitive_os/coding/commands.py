"""Resolution of provider-independent coding command identities to sealed argv vectors."""

from __future__ import annotations

import re

from cognitive_os.domain.coding import CodingCommandPolicy, command_hash

from .diff import DiffPolicyError

_SAFE_ARGUMENT = re.compile(r"^[A-Za-z0-9_./:=,+@() -]{1,256}$")


class CodingCommandResolver:
    def __init__(self, policy: CodingCommandPolicy):
        self.policy = policy

    def resolve(
        self, identity: str, arguments: tuple[str, ...] = ()
    ) -> tuple[tuple[str, ...], str]:
        if identity in self.policy.project_commands:
            if arguments:
                raise DiffPolicyError(
                    "project_command_arguments_forbidden",
                    "project-specific commands have a fixed host argv",
                )
            argv = self.policy.project_commands[identity]
        elif identity == "pytest" and identity in self.policy.allowed_executables:
            argv = ("pytest", *(arguments or ("-q",)))
        elif identity == "ruff-check" and "ruff" in self.policy.allowed_executables:
            argv = ("ruff", "check", *arguments)
        elif identity == "ruff-format-check" and "ruff" in self.policy.allowed_executables:
            argv = ("ruff", "format", "--check", *arguments)
        elif identity == "mypy" and identity in self.policy.allowed_executables:
            argv = ("mypy", *arguments)
        elif identity == "controlled-import" and identity in self.policy.allowed_executables:
            argv = ("controlled-import", *arguments)
        else:
            raise DiffPolicyError("unknown_command", "command identity is not registered")
        if any(
            not _SAFE_ARGUMENT.fullmatch(item) or item.startswith("/") or ".." in item.split("/")
            for item in argv
        ):
            raise DiffPolicyError("unsafe_command_argument", "command argument is outside policy")
        forbidden = {"sudo", "pip", "uv", "poetry", "curl", "wget", "docker", "git"}
        if argv[0] in forbidden:
            raise DiffPolicyError("forbidden_executable", "command executable is forbidden")
        return argv, command_hash(argv)
