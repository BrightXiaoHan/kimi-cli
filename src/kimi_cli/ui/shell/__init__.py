import asyncio
import getpass
from typing import override

from kosong.base.message import ContentPart, TextPart, ToolCall, ToolCallPart
from kosong.chat_provider import ChatProviderError
from kosong.tooling import ToolResult
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.patch_stdout import patch_stdout
from rich.panel import Panel

from kimi_cli.event import (
    ContextUsageUpdate,
    EventQueue,
    RunBegin,
    RunEnd,
    StepBegin,
    StepInterrupted,
)
from kimi_cli.logging import logger
from kimi_cli.soul import MaxStepsReached, Soul
from kimi_cli.ui import BaseApp
from kimi_cli.ui.shell.console import console
from kimi_cli.ui.shell.liveview import StepLiveView
from kimi_cli.ui.shell.metacmd import (
    MetaCommandCompleter,
    get_meta_command,
)


class ShellApp(BaseApp):
    def __init__(self, soul: Soul, welcome_info: dict[str, str]):
        self.soul = soul
        self.welcome_info = welcome_info

    @override
    def run(self, command: str | None = None) -> bool:
        if command is not None:
            # run single command and exit
            logger.info("Running agent with command: {command}", command=command)
            return self._soul_run(command)

        session = PromptSession(
            message=FormattedText([("bold", f"{getpass.getuser()}✨ ")]),
            prompt_continuation=FormattedText([("fg:#4d4d4d", "... ")]),
            completer=MetaCommandCompleter(),
            complete_while_typing=True,
        )

        welcome = f"[bold]Welcome to {self.soul.name}![/bold]"
        if self.welcome_info:
            welcome += "\n\n" + "\n".join(
                f"[grey30]{key}: {value}[/grey30]" for key, value in self.welcome_info.items()
            )

        console.print()
        console.print(
            Panel(
                welcome,
                border_style="blue",
                expand=False,
                padding=(1, 2),
            )
        )
        console.print()

        while True:
            try:
                with patch_stdout():
                    user_input = str(session.prompt()).strip()
            except KeyboardInterrupt:
                logger.debug("Exiting by KeyboardInterrupt")
                console.print("[grey30]Tip: press Ctrl-D or send 'exit' to quit[/grey30]")
                continue
            except EOFError:
                logger.debug("Exiting by EOF")
                console.print("Bye!")
                break

            if not user_input:
                logger.debug("Got empty input, skipping")
                continue

            logger.debug("Got user input: {user_input}", user_input=user_input)

            if user_input in ["exit", "quit", "/exit", "/quit"]:
                logger.debug("Exiting by meta command")
                console.print("Bye!")
                break
            if user_input.startswith("/"):
                logger.debug("Running meta command: {user_input}", user_input=user_input)
                self._run_meta_command(user_input[1:])
                continue

            logger.info("Running agent with user input: {user_input}", user_input=user_input)
            self._soul_run(user_input)

        return True

    def _soul_run(self, user_input: str) -> bool:
        """Run the soul with the given user input and return whether the run is successful."""
        try:
            asyncio.run(self.soul.run(user_input, self._visualize))
            return True
        except ChatProviderError as e:
            logger.exception("LLM provider error:")
            console.print(f"[bold red]LLM provider error: {e}[/bold red]")
        except MaxStepsReached as e:
            logger.warning("Max steps reached: {n_steps}", n_steps=e.n_steps)
            console.print(f"[bold yellow]Max steps reached: {e.n_steps}[/bold yellow]")
        except KeyboardInterrupt:
            logger.error("Interrupted by user")
            console.print("[bold red]Interrupted by user[/bold red]")
        except BaseException as e:
            logger.exception("Unknown error:")
            console.print(f"[bold red]Unknown error: {e}[/bold red]")
        return False

    async def _visualize(self, event_queue: EventQueue):
        """
        A loop to consume agent events and visualize the agent behavior.
        This loop never raise any exception.
        """
        # expect a RunBegin
        assert isinstance(await event_queue.get(), RunBegin)
        # expect a StepBegin
        assert isinstance(await event_queue.get(), StepBegin)

        while True:
            # spin the moon at the beginning of each step
            with console.status("", spinner="moon"):
                event = await event_queue.get()

            with StepLiveView(self.soul.context_usage) as step:
                # visualization loop for one step
                while True:
                    match event:
                        case TextPart(text=text):
                            step.append_text(text)
                        case ContentPart():
                            # TODO: support more content parts
                            step.append_text(f"[{event.__class__.__name__}]")
                        case ToolCall():
                            step.append_tool_call(event)
                        case ToolCallPart():
                            step.append_tool_call_part(event)
                        case ToolResult():
                            step.append_tool_result(event)
                        case ContextUsageUpdate(usage_percentage=usage):
                            step.update_context_usage(usage)
                        case _:
                            break  # break the step loop
                    event = await event_queue.get()

                # cleanup the step live view
                if isinstance(event, StepInterrupted):
                    step.interrupt()
                else:
                    step.finish()

            if isinstance(event, StepInterrupted):
                # for StepInterrupted, the visualization loop should end immediately
                break

            assert isinstance(event, StepBegin | RunEnd), "expect a StepBegin or RunEnd"
            if isinstance(event, StepBegin):
                # start a new step
                continue
            else:
                # end the run
                break

    def _run_meta_command(self, command_str: str):
        parts = command_str.split(" ")
        command_name = parts[0]
        command_args = parts[1:]
        command = get_meta_command(command_name)
        if command is None:
            console.print(f"Meta command /{command_name} not found")
            return
        logger.debug(
            "Running meta command: {command_name} with args: {command_args}",
            command_name=command_name,
            command_args=command_args,
        )
        command.func(self, command_args)
