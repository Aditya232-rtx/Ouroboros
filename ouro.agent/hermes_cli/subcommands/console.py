"""``ouro console`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_console_parser(subparsers, *, cmd_console: Callable) -> None:
    """Attach the safe Ouro Console REPL subcommand."""
    console_parser = subparsers.add_parser(
        "console",
        help="Open the safe Ouro command console",
        description=(
            "Open a curated Ouro command REPL. This is not a raw shell and "
            "does not expose the full Ouro CLI."
        ),
    )
    console_parser.set_defaults(func=cmd_console)
