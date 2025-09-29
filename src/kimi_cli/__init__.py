import asyncio
import importlib.metadata
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Literal

import click
from pydantic import SecretStr

from kimi_cli.agent import (
    AgentGlobals,
    BuiltinSystemPromptArgs,
    get_agents_dir,
    load_agent,
    load_agents_md,
)
from kimi_cli.config import (
    DEFAULT_KIMI_BASE_URL,
    DEFAULT_KIMI_MODEL,
    ConfigError,
    LLMModel,
    LLMProvider,
    LoopControl,
    load_config,
)
from kimi_cli.context import Context
from kimi_cli.denwarenji import DenwaRenji
from kimi_cli.llm import LLM
from kimi_cli.logging import logger
from kimi_cli.metadata import Session, continue_session, new_session
from kimi_cli.share import get_share_dir
from kimi_cli.soul import Soul
from kimi_cli.ui.print import PrintApp
from kimi_cli.ui.shell import ShellApp
from kimi_cli.utils.provider import augment_provider_with_env_vars, create_llm

__version__ = importlib.metadata.version("ensoul")

DEFAULT_AGENT_FILE = get_agents_dir() / "koder" / "agent.yaml"

UIMode = Literal["shell", "print"]


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(__version__)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Print verbose information (default: no)",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Log debug information (default: no)",
)
@click.option(
    "--agent",
    "agent_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    default=DEFAULT_AGENT_FILE,
    help="Custom agent specification file (default: builtin Kimi Koder)",
)
@click.option(
    "--model",
    "-m",
    "model_name",
    type=str,
    default=None,
    help="LLM model to use (default: default model set in config file)",
)
@click.option(
    "--work-dir",
    "-w",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Working directory for the agent (default: current directory)",
)
@click.option(
    "--continue",
    "-C",
    "continue_",
    is_flag=True,
    default=False,
    help="Continue the previous session for the working directory (default: no)",
)
@click.option(
    "--command",
    "-c",
    "--query",
    "-q",
    "command",
    type=str,
    default=None,
    help="User query to the agent (default: interactive mode)",
)
@click.option(
    "--ui",
    "ui",
    type=click.Choice(["shell", "print"]),
    default="shell",
    help="UI mode to use (default: shell)",
)
def kimi(
    verbose: bool,
    debug: bool,
    agent_file: Path,
    model_name: str | None,
    work_dir: Path,
    continue_: bool,
    command: str | None,
    ui: UIMode,
):
    """Kimi, your next CLI agent."""
    echo = click.echo if verbose else lambda *args, **kwargs: None

    logger.add(
        get_share_dir() / "logs" / "kimi.log",
        level="DEBUG" if debug else "INFO",
        rotation="06:00",
        retention="10 days",
    )

    work_dir = work_dir.absolute()

    try:
        config = load_config()
    except ConfigError as e:
        raise click.ClickException(f"Failed to load config: {e}") from e
    echo(f"✓ Loaded config: {config}")

    model: LLMModel | None = None
    provider: LLMProvider | None = None

    # try to use config file
    if not model_name and config.default_model:
        # no --model specified && default model is set in config
        model = config.models[config.default_model]
        provider = config.providers[model.provider]
    if model_name and model_name in config.models:
        # --model specified && model is set in config
        model = config.models[model_name]
        provider = config.providers[model.provider]

    if not model:
        model = LLMModel(provider="", model=DEFAULT_KIMI_MODEL)
        provider = LLMProvider(type="kimi", base_url=DEFAULT_KIMI_BASE_URL, api_key=SecretStr(""))

    # try overwrite with environment variables
    assert provider is not None
    augment_provider_with_env_vars(provider)

    if not provider.api_key:
        raise click.ClickException("API key is not set")

    echo(f"✓ Using LLM provider: {provider}")
    echo(f"✓ Using LLM model: {model}")
    stream = ui != "print"  # use non-streaming mode for print UI
    llm = create_llm(provider, model, stream=stream)

    if continue_:
        session = continue_session(work_dir)
        if session is None:
            raise click.BadOptionUsage(
                "--continue", "No previous session found for the working directory"
            )
        echo(f"✓ Continuing previous session: {session.id}")
    else:
        session = new_session(work_dir)
        echo(f"✓ Created new session: {session.id}")
    echo(f"✓ Session history file: {session.history_file}")

    if command is None and not sys.stdin.isatty():
        command = sys.stdin.read().strip()
        echo(f"✓ Read command from stdin: {command}")

    if ui == "print" and command is None:
        raise click.BadOptionUsage("--ui", "Command is required for print UI")

    succeeded = kimi_run(
        llm=llm,
        work_dir=work_dir,
        session=session,
        continue_=continue_,
        command=command,
        agent_file=agent_file,
        loop_control=config.loop_control,
        verbose=verbose,
        ui=ui,
    )
    if not succeeded:
        sys.exit(1)


def kimi_run(
    *,
    llm: LLM,
    work_dir: Path,
    session: Session,
    continue_: bool = False,
    command: str | None = None,
    agent_file: Path = DEFAULT_AGENT_FILE,
    loop_control: LoopControl | None = None,
    verbose: bool = True,
    ui: UIMode = "shell",
) -> bool:
    """Run Kimi CLI."""
    echo = click.echo if verbose else lambda *args, **kwargs: None

    ls = subprocess.run(["ls", "-la"], capture_output=True, text=True)
    agents_md = load_agents_md(work_dir) or ""
    if agents_md:
        echo(f"✓ Loaded agents.md: {textwrap.shorten(agents_md, width=100)}")

    agent_globals = AgentGlobals(
        llm=llm,
        builtin_args=BuiltinSystemPromptArgs(
            ENSOUL_WORK_DIR=work_dir,
            ENSOUL_WORK_DIR_LS=ls.stdout,
            ENSOUL_AGENTS_MD=agents_md,
        ),
        denwa_renji=DenwaRenji(),
        session=session,
    )
    try:
        agent = load_agent(agent_file, agent_globals)
    except ValueError as e:
        raise click.BadParameter(f"Failed to load agent: {e}") from e
    echo(f"✓ Loaded agent: {agent.name}")
    echo(f"✓ Loaded system prompt: {textwrap.shorten(agent.system_prompt, width=100)}")
    echo(f"✓ Loaded tools: {[tool.name for tool in agent.toolset.tools]}")

    if command is not None:
        command = command.strip()
        if not command:
            raise click.BadParameter("Command cannot be empty")

    context = Context(session.history_file)
    if continue_:
        asyncio.run(context.restore())
        echo(f"✓ Restored history from {session.history_file}")

    soul = Soul(
        agent,
        agent_globals,
        context=context,
        loop_control=loop_control or LoopControl(),
    )

    original_cwd = Path.cwd()
    os.chdir(work_dir)

    try:
        if ui == "shell":
            app = ShellApp(
                soul,
                welcome_info={
                    "Model": llm.chat_provider.model_name,
                    "Working directory": str(work_dir),
                    "Session": session.id,
                },
            )
        elif ui == "print":
            app = PrintApp(soul)
        else:
            raise click.BadParameter(f"Invalid UI mode: {ui}")

        return app.run(command)
    finally:
        os.chdir(original_cwd)


def main():
    kimi()


if __name__ == "__main__":
    main()
