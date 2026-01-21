#!/usr/bin/env python3
import os
import sys

from orchestrator import Orchestrator
from _version import __version__

os.environ.setdefault("ESCDELAY", "25")


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv

    if args:
        option = args[0]
        if option in {"--version", "-V"}:
            print(__version__)
            return
        if option in {"--help", "-h"}:
            print("Vios - Vim-inspired terminal file navigator")
            print("Usage: vios [--version] [--help]")
            return

    orchestrator = Orchestrator(start_path=os.getcwd())
    orchestrator.run()


if __name__ == "__main__":
    main()
