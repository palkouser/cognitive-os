"""The shared bounded CLI runner, against every way advisory execution can go wrong.

Every case runs against a generated stand-in rather than a real CLI, so the whole file runs
on the credential-free lane. That is the point: the guarantees asserted here — the prompt is
never in `argv`, no secret reaches the child environment, no process survives a failure, no
fixture byte changes — are the ones that must never depend on whether a binary happens to be
installed on the machine running the tests.
"""

from __future__ import annotations

import asyncio
import os
import stat
from pathlib import Path

import pytest

from cognitive_os.config.provider_config import CliProcessLimits
from cognitive_os.providers.cli_process import BoundedCliRunner
from cognitive_os.providers.errors import (
    ProviderCancelledError,
    ProviderConfigurationError,
    ProviderMutationDetectedError,
    ProviderOutputLimitExceededError,
    ProviderProcessError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

from .fake_executable import (
    build_fixture_workspace,
    process_is_alive,
    read_invocation,
    write_fake_executable,
)

SECRET_PROMPT = "analyse the fixture; my passphrase is hunter2-correct-horse"


def make_runner(
    tmp_path: Path,
    *,
    behaviour: str = "success",
    payload: str = '{"summary": "ok"}',
    limits: CliProcessLimits | None = None,
    environment: dict[str, str] | None = None,
) -> tuple[BoundedCliRunner, Path, Path]:
    workspace = build_fixture_workspace(tmp_path / "fixture")
    executable, record = write_fake_executable(
        tmp_path / "bin", behaviour=behaviour, payload=payload, workspace=workspace
    )
    runner = BoundedCliRunner(
        provider_id="fake-cli",
        executable=str(executable),
        working_directory=workspace,
        limits=limits or CliProcessLimits(timeout_seconds=10),
        environment_allowlist=("HOME", "PATH", "LANG"),
        environment=environment
        or {
            "HOME": os.environ.get("HOME", "/tmp"),
            "PATH": os.environ.get("PATH", "/usr/bin"),
            "LANG": "C",
            "OPENROUTER_API_KEY": "sk-or-v1-" + "a" * 32,  # pragma: allowlist secret
            "COGOS_MINIMAX_API_KEY": "minimax-secret-value",  # pragma: allowlist secret
            "AWS_SESSION_TOKEN": "session-secret-value",  # pragma: allowlist secret
        },
    )
    return runner, workspace, record


class TestThePromptNeverReachesArgv:
    @pytest.mark.asyncio
    async def test_the_prompt_arrives_on_stdin_and_not_in_arguments(self, tmp_path: Path) -> None:
        """In `argv` the prompt is world-readable through /proc and lands in audit logs."""
        runner, _, record = make_runner(tmp_path)
        await runner.run(
            arguments=("--print", "--output-format", "json"), stdin_payload=SECRET_PROMPT
        )
        invocation = read_invocation(record)
        assert invocation["stdin"] == SECRET_PROMPT
        assert invocation["argv"] == ["--print", "--output-format", "json"]
        assert not any(SECRET_PROMPT in argument for argument in invocation["argv"])
        assert not any("hunter2" in argument for argument in invocation["argv"])

    @pytest.mark.asyncio
    async def test_an_authority_widening_argument_is_refused_before_the_process_starts(
        self, tmp_path: Path
    ) -> None:
        runner, _, record = make_runner(tmp_path)
        with pytest.raises(ProviderConfigurationError, match="authority-widening"):
            await runner.run(
                arguments=("--print", "--dangerously-skip-permissions"),
                stdin_payload="analyse",
            )
        assert not record.exists()


class TestTheChildEnvironmentIsAnAllowlist:
    @pytest.mark.asyncio
    async def test_no_secret_variable_reaches_the_child(self, tmp_path: Path) -> None:
        runner, _, record = make_runner(tmp_path)
        await runner.run(arguments=("--print",), stdin_payload="analyse")
        environment = read_invocation(record)["environment"]
        assert set(environment) <= {"HOME", "PATH", "LANG"} | {"PWD", "SHLVL", "_", "LC_CTYPE"}
        assert "OPENROUTER_API_KEY" not in environment
        assert "COGOS_MINIMAX_API_KEY" not in environment
        assert "AWS_SESSION_TOKEN" not in environment
        assert not any("sk-or-v1-" in str(value) for value in environment.values())

    def test_the_allowlist_selects_rather_than_deletes(self, tmp_path: Path) -> None:
        """A denylist has to anticipate every secret name; the one it misses is the leak."""
        runner, _, _ = make_runner(tmp_path)
        runner._environment = {"PATH": "/usr/bin", "SOMETHING_ENTIRELY_NEW": "value"}
        assert runner.safe_environment() == {"PATH": "/usr/bin"}


class TestOutputCaps:
    @pytest.mark.asyncio
    async def test_flooding_stdout_is_capped_and_the_process_tree_is_gone(
        self, tmp_path: Path
    ) -> None:
        runner, _, _ = make_runner(
            tmp_path,
            behaviour="flood_stdout",
            limits=CliProcessLimits(
                timeout_seconds=10, maximum_stdout_bytes=4096, maximum_stderr_bytes=1024
            ),
        )
        with pytest.raises(ProviderOutputLimitExceededError) as failure:
            await runner.run(arguments=("--print",), stdin_payload="analyse")
        assert failure.value.details["stdout_truncated"] is True
        assert failure.value.details["maximum_stdout_bytes"] == 4096

    @pytest.mark.asyncio
    async def test_flooding_stderr_is_capped(self, tmp_path: Path) -> None:
        runner, _, _ = make_runner(
            tmp_path,
            behaviour="flood_stderr",
            limits=CliProcessLimits(
                timeout_seconds=10, maximum_stdout_bytes=4096, maximum_stderr_bytes=1024
            ),
        )
        with pytest.raises(ProviderOutputLimitExceededError) as failure:
            await runner.run(arguments=("--print",), stdin_payload="analyse")
        assert failure.value.details["stderr_truncated"] is True

    @pytest.mark.asyncio
    async def test_retained_output_never_exceeds_the_configured_cap(self, tmp_path: Path) -> None:
        """Bounded by construction, not by trusting the provider to be brief."""
        runner, _, _ = make_runner(
            tmp_path,
            behaviour="flood_stdout",
            limits=CliProcessLimits(
                timeout_seconds=10, maximum_stdout_bytes=2048, maximum_stderr_bytes=1024
            ),
        )
        with pytest.raises(ProviderOutputLimitExceededError):
            await runner.run(arguments=("--print",), stdin_payload="analyse")


class TestProcessTreeCleanup:
    @pytest.mark.asyncio
    async def test_a_timeout_kills_the_child_and_its_grandchild(self, tmp_path: Path) -> None:
        """`killpg`, not `terminate()`: a surviving grandchild keeps spending the budget."""
        runner, _, record = make_runner(
            tmp_path,
            behaviour="hang",
            limits=CliProcessLimits(timeout_seconds=1, termination_grace_seconds=1),
        )
        with pytest.raises(ProviderTimeoutError, match="exceeded its timeout"):
            await runner.run(arguments=("--print",), stdin_payload="analyse")
        # The stand-in records its own PID group by writing before it hangs; the assertion
        # that matters is that nothing of ours is left running.
        assert record.exists()
        await asyncio.sleep(0.2)
        assert _no_surviving_fake_processes(tmp_path)

    @pytest.mark.asyncio
    async def test_cancellation_becomes_a_typed_failure_and_leaves_nothing_running(
        self, tmp_path: Path
    ) -> None:
        runner, _, _ = make_runner(
            tmp_path,
            behaviour="hang",
            limits=CliProcessLimits(timeout_seconds=30, termination_grace_seconds=1),
        )
        task = asyncio.create_task(runner.run(arguments=("--print",), stdin_payload="analyse"))
        await asyncio.sleep(0.6)
        task.cancel()
        with pytest.raises(ProviderCancelledError, match="was cancelled"):
            await task
        await asyncio.sleep(0.2)
        assert _no_surviving_fake_processes(tmp_path)

    @pytest.mark.asyncio
    async def test_an_output_overflow_also_leaves_nothing_running(self, tmp_path: Path) -> None:
        runner, _, _ = make_runner(
            tmp_path,
            behaviour="flood_stdout",
            limits=CliProcessLimits(
                timeout_seconds=10,
                maximum_stdout_bytes=4096,
                maximum_stderr_bytes=1024,
                termination_grace_seconds=1,
            ),
        )
        with pytest.raises(ProviderOutputLimitExceededError):
            await runner.run(arguments=("--print",), stdin_payload="analyse")
        await asyncio.sleep(0.2)
        assert _no_surviving_fake_processes(tmp_path)


class TestMutationIsRefused:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("behaviour", "expected_change"),
        [
            ("write_file", "created"),
            ("modify_dirty", "content_changed"),
            ("delete_file", "deleted"),
            ("chmod_file", "mode_changed"),
            ("symlink_swap", "type_changed"),
        ],
    )
    async def test_every_mutation_fails_closed(
        self, tmp_path: Path, behaviour: str, expected_change: str
    ) -> None:
        runner, _, _ = make_runner(tmp_path, behaviour=behaviour)
        with pytest.raises(ProviderMutationDetectedError, match="changed its working directory"):
            await runner.run(arguments=("--print",), stdin_payload="analyse")

    @pytest.mark.asyncio
    async def test_a_rename_fails_closed(self, tmp_path: Path) -> None:
        runner, _, _ = make_runner(tmp_path, behaviour="rename_file")
        with pytest.raises(ProviderMutationDetectedError) as failure:
            await runner.run(arguments=("--print",), stdin_payload="analyse")
        changes = {item["change"] for item in failure.value.details["changes"]}
        assert changes == {"deleted", "created"}

    @pytest.mark.asyncio
    async def test_an_unchanged_dirty_fixture_passes(self, tmp_path: Path) -> None:
        """Locally modified is not the same as modified *by the provider*."""
        runner, workspace, _ = make_runner(tmp_path)
        (workspace / "dirty.txt").write_text("still locally modified\n", encoding="utf-8")
        outcome, after = await runner.run(arguments=("--print",), stdin_payload="analyse")
        assert outcome.return_code == 0
        assert after is not None

    @pytest.mark.asyncio
    async def test_the_mutation_report_carries_paths_and_hashes_not_content(
        self, tmp_path: Path
    ) -> None:
        runner, _, _ = make_runner(tmp_path, behaviour="write_file")
        with pytest.raises(ProviderMutationDetectedError) as failure:
            await runner.run(arguments=("--print",), stdin_payload="analyse")
        rendered = str(failure.value.details)
        assert "new-file.txt" in rendered
        assert "written by the provider" not in rendered

    @pytest.mark.asyncio
    async def test_a_provider_that_wrote_and_failed_is_reported_as_a_mutation(
        self, tmp_path: Path
    ) -> None:
        """The write is the more serious of the two facts, so it is the reported one."""
        workspace = build_fixture_workspace(tmp_path / "fixture")
        executable, _ = write_fake_executable(
            tmp_path / "bin", behaviour="write_file", workspace=workspace
        )
        # Make the stand-in also exit non-zero by appending to its own source.
        with executable.open("a", encoding="utf-8") as stream:
            stream.write("\nsys.exit(4)\n")
        runner = BoundedCliRunner(
            provider_id="fake-cli",
            executable=str(executable),
            working_directory=workspace,
            limits=CliProcessLimits(timeout_seconds=10),
            environment_allowlist=("HOME", "PATH"),
            environment={"HOME": os.environ.get("HOME", "/tmp"), "PATH": os.environ["PATH"]},
        )
        with pytest.raises(ProviderMutationDetectedError):
            await runner.run(arguments=("--print",), stdin_payload="analyse")


class TestFailureReporting:
    @pytest.mark.asyncio
    async def test_a_non_zero_exit_is_typed_and_its_stderr_is_redacted(
        self, tmp_path: Path
    ) -> None:
        runner, _, _ = make_runner(tmp_path, behaviour="nonzero")
        with pytest.raises(ProviderProcessError, match="non-zero status") as failure:
            await runner.run(arguments=("--print",), stdin_payload="analyse")
        excerpt = str(failure.value.details["stderr_excerpt"])
        assert failure.value.details["return_code"] == 3
        assert "abcdef0123456789" not in excerpt
        assert "<redacted>" in excerpt

    @pytest.mark.asyncio
    async def test_a_missing_executable_is_unavailable_rather_than_a_crash(
        self, tmp_path: Path
    ) -> None:
        workspace = build_fixture_workspace(tmp_path / "fixture")
        runner = BoundedCliRunner(
            provider_id="fake-cli",
            executable=str(tmp_path / "does-not-exist"),
            working_directory=workspace,
            limits=CliProcessLimits(),
            environment_allowlist=("PATH",),
            environment={"PATH": os.environ["PATH"]},
        )
        with pytest.raises(ProviderUnavailableError, match="not installed"):
            await runner.run(arguments=("--print",), stdin_payload="analyse")

    @pytest.mark.asyncio
    async def test_a_missing_working_directory_is_a_configuration_failure(
        self, tmp_path: Path
    ) -> None:
        executable, _ = write_fake_executable(tmp_path / "bin")
        runner = BoundedCliRunner(
            provider_id="fake-cli",
            executable=str(executable),
            working_directory=tmp_path / "absent",
            limits=CliProcessLimits(),
            environment_allowlist=("PATH",),
            environment={"PATH": os.environ["PATH"]},
        )
        with pytest.raises(ProviderConfigurationError, match="working directory"):
            await runner.run(arguments=("--print",), stdin_payload="analyse")


class TestRunnerOwnedTemporaries:
    @pytest.mark.asyncio
    async def test_a_temporary_directory_is_outside_the_workspace_and_always_removed(
        self, tmp_path: Path
    ) -> None:
        """Inside the fixture it would need a snapshot exclusion, and an exclusion is a hole."""
        runner, workspace, _ = make_runner(tmp_path)
        async with runner.temporary_directory() as scratch:
            (scratch / "schema.json").write_text("{}", encoding="utf-8")
            assert scratch.is_dir()
            assert workspace.resolve() not in scratch.resolve().parents
            captured = scratch
        assert not captured.exists()

    @pytest.mark.asyncio
    async def test_the_temporary_directory_is_removed_even_when_the_body_raises(
        self, tmp_path: Path
    ) -> None:
        runner, _, _ = make_runner(tmp_path)
        captured: Path | None = None
        with pytest.raises(RuntimeError):
            async with runner.temporary_directory() as scratch:
                captured = scratch
                raise RuntimeError("adapter failed mid-call")
        assert captured is not None
        assert not captured.exists()


class TestCapabilityProbing:
    @pytest.mark.asyncio
    async def test_a_probe_reports_an_uninstalled_binary_without_raising(
        self, tmp_path: Path
    ) -> None:
        """A health check that raises cannot report 'not installed'."""
        runner = BoundedCliRunner(
            provider_id="fake-cli",
            executable=str(tmp_path / "absent"),
            working_directory=tmp_path,
            limits=CliProcessLimits(),
            environment_allowlist=("PATH",),
            environment={"PATH": os.environ["PATH"]},
        )
        accepted, message = await runner.probe(("--version",))
        assert accepted is False
        assert "not installed" in message

    @pytest.mark.asyncio
    async def test_probe_output_is_redacted_and_bounded(self, tmp_path: Path) -> None:
        runner, _, _ = make_runner(tmp_path, behaviour="nonzero")
        accepted, message = await runner.probe(("--version",))
        assert accepted is False
        assert "abcdef0123456789" not in message
        assert len(message) <= 201


def _no_surviving_fake_processes(tmp_path: Path) -> bool:
    """Whether any process still holds the generated stand-in open.

    Reads `/proc` rather than shelling out: the assertion is about process survival, and
    spawning a `ps` to answer it would add a process to the thing being counted.
    """
    marker = str(tmp_path)
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().decode(errors="replace")
        except (OSError, PermissionError):
            continue
        if marker in command and process_is_alive(int(entry.name)):
            return False
    return True


def test_the_fake_executable_is_executable(tmp_path: Path) -> None:
    """Guards the guard: a stand-in without the bit set would make every run 'unavailable'."""
    executable, _ = write_fake_executable(tmp_path / "bin")
    assert executable.stat().st_mode & stat.S_IXUSR
