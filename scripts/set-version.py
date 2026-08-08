from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^v?\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?$")


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text()
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"Could not update {path.relative_to(ROOT_DIR)}")
    path.write_text(updated)


def main() -> int:
    if len(sys.argv) != 2 or not VERSION_PATTERN.fullmatch(sys.argv[1]):
        raise SystemExit("Usage: set-version.py [v]x.y.z or [v]x.y.z-beta.N")

    version = sys.argv[1].removeprefix("v")
    arch_version = version.replace("-", "")
    replace_once(ROOT_DIR / "pyproject.toml", r'^version = ".*"$', f'version = "{version}"')
    replace_once(ROOT_DIR / "src/alsachainqt/__init__.py", r'^__version__ = ".*"$', f'__version__ = "{version}"')
    replace_once(ROOT_DIR / "PKGBUILD", r"^pkgver=.*$", f"pkgver={arch_version}")
    replace_once(ROOT_DIR / "PKGBUILD", r"^_upstream_version=.*$", f"_upstream_version={version}")
    replace_once(ROOT_DIR / "PKGBUILD", r"^pkgrel=.*$", "pkgrel=1")
    print(f"Set version to {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
