"""Shell-free asynchronous Docker CLI runner."""

import asyncio

from cognitive_os.tools.errors import SandboxExecutionError


async def docker(*arguments: str, timeout: float = 30) -> tuple[int, bytes, bytes]:
    process = await asyncio.create_subprocess_exec(
        "docker", *arguments, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        async with asyncio.timeout(timeout):
            stdout, stderr = await process.communicate()
    except TimeoutError:
        process.kill()
        await process.wait()
        raise SandboxExecutionError("Docker command timed out") from None
    return process.returncode or 0, stdout, stderr
