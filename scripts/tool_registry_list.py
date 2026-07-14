"""List the deterministic provider-visible Tool Registry."""

import argparse
from pathlib import Path

from cognitive_os.config.tool_config import load_tool_configuration
from cognitive_os.tools.factory import build_builtin_registry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    registry = build_builtin_registry(load_tool_configuration(parser.parse_args().config))
    for descriptor in registry.list_all():
        print(f"{descriptor.tool_id}\t{descriptor.version}\t{descriptor.risk_level.value}")


if __name__ == "__main__":
    main()
