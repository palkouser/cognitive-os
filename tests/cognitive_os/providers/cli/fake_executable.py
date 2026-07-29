"""A scriptable stand-in for a provider CLI.

Real binaries are not usable here: normal CI has neither Claude Code nor Codex installed,
and a test that needed one would turn into a skip on the lane that matters most. The fake
is a small Python script the test writes and marks executable, so `argv`, stdin, the child
environment and every failure path are observable exactly as they would be for the real
thing — including spawning a grandchild, which is what makes process-tree cleanup testable.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

#: Behaviours the fake understands, chosen by the `COGOS_FAKE_BEHAVIOUR` variable the test
#: sets *inside the script itself* rather than in the environment: the runner's allowlist
#: would strip an environment variable, which is precisely what it is for.
_TEMPLATE = '''#!/usr/bin/env python3
"""Generated provider stand-in. Not shipped, not importable."""
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

BEHAVIOUR = {behaviour!r}
PAYLOAD = {payload!r}
WORKSPACE = Path({workspace!r})
RECORD = Path({record!r})

prompt = sys.stdin.read()
RECORD.write_text(
    json.dumps(
        {{
            "argv": sys.argv[1:],
            "stdin": prompt,
            "environment": dict(os.environ),
            "cwd": os.getcwd(),
        }}
    ),
    encoding="utf-8",
)

if BEHAVIOUR == "success":
    sys.stdout.write(PAYLOAD)
elif BEHAVIOUR == "flood_stdout":
    while True:
        sys.stdout.write("x" * 4096)
        sys.stdout.flush()
elif BEHAVIOUR == "flood_stderr":
    while True:
        sys.stderr.write("y" * 4096)
        sys.stderr.flush()
elif BEHAVIOUR == "hang":
    # A grandchild that outlives a naive parent-only kill. `sleep` is exec'd in its own
    # right so the process tree really has two levels.
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    time.sleep(120)
elif BEHAVIOUR == "nonzero":
    sys.stderr.write("failed with Authorization: Bearer abcdef0123456789 in the message\\n")
    sys.exit(3)
elif BEHAVIOUR == "malformed":
    sys.stdout.write("this is not JSON at all")
elif BEHAVIOUR == "write_file":
    (WORKSPACE / "new-file.txt").write_text("written by the provider\\n", encoding="utf-8")
elif BEHAVIOUR == "modify_dirty":
    (WORKSPACE / "dirty.txt").write_text("provider rewrote this\\n", encoding="utf-8")
elif BEHAVIOUR == "delete_file":
    (WORKSPACE / "fixture.txt").unlink()
elif BEHAVIOUR == "rename_file":
    (WORKSPACE / "fixture.txt").rename(WORKSPACE / "renamed.txt")
elif BEHAVIOUR == "chmod_file":
    target = WORKSPACE / "fixture.txt"
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
elif BEHAVIOUR == "symlink_swap":
    target = WORKSPACE / "fixture.txt"
    target.unlink()
    target.symlink_to("/etc/hostname")
elif BEHAVIOUR == "leak_secret":
    sys.stdout.write(json.dumps({{"summary": "leaked sk-or-v1-" + "a" * 32}}))
sys.stdout.flush()
'''


def write_fake_executable(
    directory: Path,
    *,
    behaviour: str = "success",
    payload: str = '{"summary": "synthetic advisory result", "findings": []}',
    workspace: Path | None = None,
    name: str = "fake-cli",
) -> tuple[Path, Path]:
    """Write the stand-in and return its path plus the path it records invocations to."""
    directory.mkdir(parents=True, exist_ok=True)
    record = directory / f"{name}-invocation.json"
    script = directory / name
    script.write_text(
        _TEMPLATE.format(
            behaviour=behaviour,
            payload=payload,
            workspace=str(workspace or directory),
            record=str(record),
        ),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script, record


def read_invocation(record: Path) -> dict[str, object]:
    """What the stand-in was actually given: argv, stdin, environment and cwd."""
    return json.loads(record.read_text(encoding="utf-8"))


def build_fixture_workspace(root: Path) -> Path:
    """A small fixture tree, including a file that is already 'dirty'.

    The dirty file is the whole point of the content snapshot: `git status` reports it as
    modified both before and after, so a status-only guard cannot see a second rewrite.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "fixture.txt").write_text("original fixture content\n", encoding="utf-8")
    (root / "dirty.txt").write_text("locally modified before the call\n", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir(exist_ok=True)
    (nested / "module.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    return root


def process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
