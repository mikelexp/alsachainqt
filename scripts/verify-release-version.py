from __future__ import annotations

import sys
import tomllib
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: verify-release-version.py vx.y.z")
    tag = sys.argv[1]
    if not tag.startswith("v"):
        raise SystemExit(f"Release tag must start with v: {tag}")
    with (ROOT_DIR / "pyproject.toml").open("rb") as file:
        version = tomllib.load(file)["project"]["version"]
    if tag[1:] != version:
        raise SystemExit(f"Tag {tag} does not match project version {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
