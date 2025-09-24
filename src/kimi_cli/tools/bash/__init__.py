import asyncio
from pathlib import Path
from typing import override

from kosong.base.tool import ParametersType
from kosong.tooling import CallableTool, ToolError, ToolOk, ToolReturnType


class Bash(CallableTool):
    name: str = "Bash"
    description: str = (Path(__file__).parent / "bash.md").read_text()
    parameters: ParametersType = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute.",
            },
            "timeout": {
                "type": "number",
                "description": "The timeout in seconds for the command to execute. \
                    If the command takes longer than this, it will be killed.",
                "default": 60,
            },
        },
        "required": ["command"],
    }

    @override
    async def __call__(self, command: str, timeout: int = 60) -> ToolReturnType:
        output = []

        def stdout_cb(line: bytes):
            line_str = line.decode()
            output.append(line_str)

        def stderr_cb(line: bytes):
            line_str = line.decode()
            output.append(line_str)

        try:
            exitcode = await _stream_subprocess(command, stdout_cb, stderr_cb, timeout)
            # TODO: truncate/compress the output if it is too long
            output_str = "".join(output)
            if exitcode == 0:
                return ToolOk(output=output_str, message="Command executed successfully.")
            return ToolError(
                output=output_str,
                message=f"Command failed with exit code: {exitcode}",
                brief=f"Failed with exit code: {exitcode}",
            )
        except TimeoutError:
            output_str = "".join(output)
            return ToolError(
                output=output_str,
                message=f"Command killed by timeout ({timeout}s)",
                brief=f"Killed by timeout ({timeout}s)",
            )


async def _stream_subprocess(command: str, stdout_cb, stderr_cb, timeout: int) -> int:
    async def _read_stream(stream, cb):
        while True:
            line = await stream.readline()
            if line:
                cb(line)
            else:
                break

    # FIXME: if the event loop is cancelled, an exception may be raised when the process finishes
    process = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    try:
        await asyncio.wait_for(
            asyncio.gather(
                _read_stream(process.stdout, stdout_cb),
                _read_stream(process.stderr, stderr_cb),
            ),
            timeout,
        )
        return await process.wait()
    except TimeoutError:
        process.kill()
        raise
