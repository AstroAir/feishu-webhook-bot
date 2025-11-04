from __future__ import annotations

import argparse
import builtins
import os
import subprocess
from collections.abc import Callable, Sequence


def run(cmd: Sequence[str]) -> int:
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd)
    return proc.returncode


actions: dict[str, Callable[[], int]] = {}


def action(fn: Callable[[], int]) -> Callable[[], int]:
    actions[fn.__name__.replace("_", ":")] = fn
    return fn


@action
def setup() -> int:
    return run(["uv", "sync", "--all-groups"])


@action
def lint() -> int:
    return run(["uv", "run", "ruff", "check", "."])


@action
def format() -> int:
    return run(["uv", "run", "black", "."])


@action
def typecheck() -> int:
    return run(["uv", "run", "mypy", "."])


@action
def test() -> int:
    return run(["uv", "run", "pytest", "-q"])


@action
def build() -> int:
    return run(["uv", "build"])


@action
def docs_build() -> int:
    return run(["uv", "run", "mkdocs", "build", "--strict"])


@action
def docs_serve() -> int:
    host = os.environ.get("MKDOCS_HOST", "127.0.0.1:8000")
    return run(["uv", "run", "mkdocs", "serve", "-a", host])


@action
def ci() -> int:  # run common checks
    codes = [
        lint(),
        run(["uv", "run", "black", "--check", "."]),
        typecheck(),
        test(),
        build(),
        docs_build(),
    ]
    return 0 if builtins.all(code == 0 for code in codes) else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Task runner for common dev workflows")
    task_list = ", ".join(sorted(actions))
    parser.add_argument("task", nargs="?", default="ci", help=f"Task to run: {task_list}")
    args, extras = parser.parse_known_args(argv)

    task_name = args.task.replace("_", ":")
    fn = actions.get(task_name)
    if not fn:
        print(f"Unknown task '{args.task}'. Known tasks: {', '.join(sorted(actions))}")
        return 2
    return fn()


if __name__ == "__main__":
    raise SystemExit(main())
