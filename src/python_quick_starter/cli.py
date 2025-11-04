from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python-quick-starter",
        description="Say hello from the python-quick-starter template",
    )
    parser.add_argument(
        "--name",
        default="world",
        help="Name to greet (default: world)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional sequence of CLI arguments (without the program name).

    Returns:
        Process exit code. 0 for success.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    print(f"Hello, {args.name}!")
    return 0
