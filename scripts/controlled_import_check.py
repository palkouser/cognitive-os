"""Fixed sandbox helper for importing validated module names."""

from __future__ import annotations

import importlib
import re
import sys


def main(arguments: list[str]) -> int:
    if not arguments:
        return 2
    for module_name in arguments:
        if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", module_name):
            return 2
        importlib.import_module(module_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
