from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, NamedTuple, overload

from prompt_toolkit.completion import Completer, Completion
from rich.panel import Panel

from kimi_cli.ui.tui.console import console

if TYPE_CHECKING:
    from kimi_cli.ui.tui import App

type MetaCmdFunc = Callable[["App", list[str]], None]


class MetaCommand(NamedTuple):
    name: str
    description: str
    func: MetaCmdFunc
    aliases: list[str]

    def slash_name(self):
        """/name (aliases)"""
        if self.aliases:
            return f"/{self.name} ({', '.join(self.aliases)})"
        return f"/{self.name}"


# primary name -> MetaCommand
_meta_commands: dict[str, MetaCommand] = {}
# primary name or alias -> MetaCommand
_meta_command_aliases: dict[str, MetaCommand] = {}


def get_meta_command(name: str) -> MetaCommand | None:
    return _meta_command_aliases.get(name)


def get_meta_commands() -> list[MetaCommand]:
    """Get all unique primary meta commands (without duplicating aliases)."""
    return list(_meta_commands.values())


@overload
def meta_command(func: MetaCmdFunc, /) -> MetaCmdFunc: ...


@overload
def meta_command(
    *,
    name: str | None = None,
    aliases: Sequence[str] | None = None,
) -> Callable[[MetaCmdFunc], MetaCmdFunc]: ...


def meta_command(
    func: MetaCmdFunc | None = None,
    *,
    name: str | None = None,
    aliases: Sequence[str] | None = None,
) -> (
    MetaCmdFunc
    | Callable[
        [MetaCmdFunc],
        MetaCmdFunc,
    ]
):
    """Decorator to register a meta command with optional custom name and aliases.

    Usage examples:
      @meta_command
      def help(app: App, args: list[str]): ...

      @meta_command(name="run")
      def start(app: App, args: list[str]): ...

      @meta_command(aliases=["h", "?", "assist"])
      def help(app: App, args: list[str]): ...
    """

    def _register(f: MetaCmdFunc):
        primary = name or f.__name__
        alias_list = list(aliases) if aliases else []

        # Create the primary command with aliases
        cmd = MetaCommand(
            name=primary,
            description=(f.__doc__ or "").strip(),
            func=f,
            aliases=alias_list,
        )

        # Register primary command
        _meta_commands[primary] = cmd
        _meta_command_aliases[primary] = cmd

        # Register aliases pointing to the same command
        for alias in alias_list:
            _meta_command_aliases[alias] = cmd

        return f

    if func is not None:
        return _register(func)
    return _register


class MetaCommandCompleter(Completer):
    """A completer that:
    - Shows one line per meta command in the form: "/name (alias1, alias2)"
    - Matches by primary name or any alias while inserting the canonical "/name"
    - Only activates when the current token starts with '/'
    """

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        # Only consider the last token (allowing future arguments after a space)
        last_space = text.rfind(" ")
        token = text[last_space + 1 :]
        if not token.startswith("/"):
            return

        typed = token[1:]
        typed_lower = typed.lower()

        for cmd in sorted(get_meta_commands(), key=lambda c: c.name):
            names = [cmd.name] + list(cmd.aliases)
            if typed == "" or any(n.lower().startswith(typed_lower) for n in names):
                yield Completion(
                    text=f"/{cmd.name}",
                    start_position=-len(token),
                    display=cmd.slash_name(),
                    display_meta=cmd.description,
                )


@meta_command(aliases=["quit"])
def exit(app: "App", args: list[str]):
    """Exit the application"""
    # should be handled by `App`
    raise NotImplementedError


@meta_command(aliases=["h", "?"])
def help(app: "App", args: list[str]):
    """Show help information"""
    console.print(
        Panel(
            f"Send message to {app.soul.name} to get things done!\n\n"
            "Meta commands are also available:\n\n"
            + "\n".join(
                f"  {command.slash_name()}: {command.description}"
                for command in get_meta_commands()
            ),
            border_style="wheat4",
            expand=False,
            padding=(1, 2),
        )
    )
