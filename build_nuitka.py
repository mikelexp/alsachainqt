#!/usr/bin/env python3
"""Build ALSAChainQT distributions with Nuitka."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = PROJECT_ROOT / "run_alsachainqt.py"
ICON_FILE = PROJECT_ROOT / "icon.png"
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"


def project_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as file:
        return tomllib.load(file)["project"]["version"]


def build_command(onefile: bool) -> list[str]:
    version = project_version()
    file_version = version.split("-", maxsplit=1)[0] + ".0"
    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--assume-yes-for-downloads",
        "--mode=onefile" if onefile else "--mode=standalone",
        "--enable-plugin=pyside6",
        "--output-filename=alsachainqt.bin",
        "--include-qt-plugins=platforms,platformthemes,iconengines,imageformats,wayland-shell-integration,wayland-decoration-client,wayland-graphics-integration-client,xcbglintegrations",
        f"--output-dir={DIST_DIR}",
        "--remove-output",
        "--show-progress",
        "--show-scons",
        "--follow-imports",
        "--python-flag=no_site",
        "--warn-unusual-code",
        "--company-name=Mikele",
        "--product-name=ALSAChainQT",
        "--file-description=Native Qt desktop manager for ALSAChain virtual PCM profiles",
        f"--file-version={file_version}",
        f"--product-version={file_version}",
        "--nofollow-import-to=tkinter,test,unittest,pydoc",
        f"--include-data-files={ICON_FILE}=icon.png",
        str(MAIN_SCRIPT),
    ]
    return command


def clean() -> None:
    for target in (DIST_DIR, PROJECT_ROOT / "alsachainqt.build", PROJECT_ROOT / "alsachainqt.dist", PROJECT_ROOT / "alsachainqt.onefile-build", PROJECT_ROOT / "alsachainqt.bin"):
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ALSAChainQT with Nuitka.")
    parser.add_argument("--onefile", action="store_true", help="Build a onefile binary instead of standalone.")
    parser.add_argument("--clean", action="store_true", help="Remove build artifacts before building.")
    parser.add_argument("--clean-only", action="store_true", help="Only remove build artifacts.")
    args = parser.parse_args()

    if args.clean or args.clean_only:
        clean()
    if args.clean_only:
        return 0

    BUILD_DIR.mkdir(exist_ok=True)
    DIST_DIR.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["XDG_CACHE_HOME"] = str(BUILD_DIR / ".cache")
    command = build_command(onefile=args.onefile)
    print("Running:", " ".join(command))
    return subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
