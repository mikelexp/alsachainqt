from __future__ import annotations

import tomllib
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

with (ROOT_DIR / "pyproject.toml").open("rb") as file:
    print(tomllib.load(file)["project"]["version"])
