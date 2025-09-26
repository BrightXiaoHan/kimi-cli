# ruff: noqa

from inline_snapshot import snapshot

from kimi_cli.tools.bash import Bash
from kimi_cli.tools.file.glob import Glob
from kimi_cli.tools.file.grep import Grep
from kimi_cli.tools.file.read import ReadFile
from kimi_cli.tools.file.replace import StrReplaceFile
from kimi_cli.tools.file.write import WriteFile
from kimi_cli.tools.todo import SetTodoList


def test_set_todo_list_params_schema(set_todo_list_tool: SetTodoList):
    """Test the schema of SetTodoList tool parameters."""
    assert set_todo_list_tool.base.parameters == snapshot(
        {
            "$defs": {
                "Todo": {
                    "properties": {
                        "title": {
                            "description": "The title of the todo",
                            "minLength": 1,
                            "type": "string",
                        },
                        "status": {
                            "description": "The status of the todo",
                            "enum": ["Pending", "In Progress", "Done"],
                            "type": "string",
                        },
                    },
                    "required": ["title", "status"],
                    "type": "object",
                }
            },
            "properties": {
                "todos": {
                    "description": "The updated todo list",
                    "items": {"$ref": "#/$defs/Todo"},
                    "type": "array",
                }
            },
            "required": ["todos"],
            "type": "object",
        }
    )


def test_bash_params_schema(bash_tool: Bash):
    """Test the schema of Bash tool parameters."""
    assert bash_tool.base.parameters == snapshot(
        {
            "properties": {
                "command": {
                    "description": "The bash command to execute.",
                    "type": "string",
                },
                "timeout": {
                    "default": 60,
                    "description": "The timeout in seconds for the command to execute. If the command takes longer than this, it will be killed.",
                    "maximum": 300,
                    "minimum": 1,
                    "type": "integer",
                },
            },
            "required": ["command"],
            "type": "object",
        }
    )


def test_read_file_params_schema(read_file_tool: ReadFile):
    """Test the schema of ReadFile tool parameters."""
    assert read_file_tool.base.parameters == snapshot(
        {
            "properties": {
                "path": {
                    "description": "The absolute path to the file to read",
                    "type": "string",
                },
                "line_offset": {
                    "default": 1,
                    "description": "The line number to start reading from. By default read from the beginning of the file. Set this when the file is too large to read at once.",
                    "minimum": 1,
                    "type": "integer",
                },
                "n_lines": {
                    "default": 1000,
                    "description": "The number of lines to read. By default read up to 1000 lines, which is the max allowed value. Set this value when the file is too large to read at once.",
                    "minimum": 1,
                    "type": "integer",
                },
            },
            "required": ["path"],
            "type": "object",
        }
    )


def test_glob_params_schema(glob_tool: Glob):
    """Test the schema of Glob tool parameters."""
    assert glob_tool.base.parameters == snapshot(
        {
            "properties": {
                "pattern": {
                    "description": "Glob pattern to match files/directories.",
                    "type": "string",
                },
                "directory": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "default": None,
                    "description": "Absolute path to the directory to search in (defaults to working directory).",
                },
                "include_dirs": {
                    "default": True,
                    "description": "Whether to include directories in results.",
                    "type": "boolean",
                },
            },
            "required": ["pattern"],
            "type": "object",
        }
    )


def test_grep_params_schema(grep_tool: Grep):
    """Test the schema of Grep tool parameters."""
    assert grep_tool.base.parameters == snapshot(
        {
            "properties": {
                "pattern": {
                    "description": "The regular expression pattern to search for in file contents",
                    "type": "string",
                },
                "path": {
                    "default": ".",
                    "description": "File or directory to search in. Defaults to current working directory. If specified, it must be an absolute path.",
                    "type": "string",
                },
                "glob": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "default": None,
                    "description": "Glob pattern to filter files (e.g. `*.js`, `*.{ts,tsx}`). No filter by default.",
                },
                "output_mode": {
                    "default": "files_with_matches",
                    "description": "`content`: Show matching lines (supports `-B`, `-A`, `-C`, `-n`, `head_limit`); `files_with_matches`: Show file paths (supports `head_limit`); `count_matches`: Show total number of matches. Defaults to `files_with_matches`.",
                    "type": "string",
                },
                "-B": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "default": None,
                    "description": "Number of lines to show before each match (the `-B` option). Requires `output_mode` to be `content`.",
                },
                "-A": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "default": None,
                    "description": "Number of lines to show after each match (the `-A` option). Requires `output_mode` to be `content`.",
                },
                "-C": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "default": None,
                    "description": "Number of lines to show before and after each match (the `-C` option). Requires `output_mode` to be `content`.",
                },
                "-n": {
                    "default": False,
                    "description": "Show line numbers in output (the `-n` option). Requires `output_mode` to be `content`.",
                    "type": "boolean",
                },
                "-i": {
                    "default": False,
                    "description": "Case insensitive search (the `-i` option).",
                    "type": "boolean",
                },
                "type": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "default": None,
                    "description": "File type to search. Examples: py, rust, js, ts, go, java, etc. More efficient than `glob` for standard file types.",
                },
                "head_limit": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "default": None,
                    "description": "Limit output to first N lines, equivalent to `| head -N`. Works across all output modes: content (limits output lines), files_with_matches (limits file paths), count_matches (limits count entries). By default, no limit is applied.",
                },
                "multiline": {
                    "default": False,
                    "description": "Enable multiline mode where `.` matches newlines and patterns can span lines (the `-U` and `--multiline-dotall` options). By default, multiline mode is disabled.",
                    "type": "boolean",
                },
            },
            "required": ["pattern"],
            "type": "object",
        }
    )


def test_write_file_params_schema(write_file_tool: WriteFile):
    """Test the schema of WriteFile tool parameters."""
    assert write_file_tool.base.parameters == snapshot(
        {
            "properties": {
                "path": {
                    "description": "The absolute path to the file to write",
                    "type": "string",
                },
                "content": {
                    "description": "The content to write to the file",
                    "type": "string",
                },
                "mode": {
                    "default": "overwrite",
                    "description": "The mode to use to write to the file. Two modes are supported: `overwrite` for overwriting the whole file and `append` for appending to the end of an existing file.",
                    "enum": ["overwrite", "append"],
                    "type": "string",
                },
            },
            "required": ["path", "content"],
            "type": "object",
        }
    )


def test_str_replace_file_params_schema(str_replace_file_tool: StrReplaceFile):
    """Test the schema of StrReplaceFile tool parameters."""
    assert str_replace_file_tool.base.parameters == snapshot(
        {
            "$defs": {
                "Edit": {
                    "properties": {
                        "old": {
                            "description": "The old string to replace. Can be multi-line.",
                            "type": "string",
                        },
                        "new": {
                            "description": "The new string to replace with. Can be multi-line.",
                            "type": "string",
                        },
                        "replace_all": {
                            "default": False,
                            "description": "Whether to replace all occurrences.",
                            "type": "boolean",
                        },
                    },
                    "required": ["old", "new"],
                    "type": "object",
                }
            },
            "properties": {
                "path": {
                    "description": "The absolute path to the file to edit.",
                    "type": "string",
                },
                "edit": {
                    "anyOf": [
                        {"$ref": "#/$defs/Edit"},
                        {"items": {"$ref": "#/$defs/Edit"}, "type": "array"},
                    ],
                    "description": "The edit(s) to apply to the file. You can provide a single edit or a list of edits here.",
                },
            },
            "required": ["path", "edit"],
            "type": "object",
        }
    )
