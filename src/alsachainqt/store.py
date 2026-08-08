"""Atomic shared configuration persistence with ALSA validation rollback."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

from .asound import render_block, replace_managed_block
from .models import Config, Profile
from .paths import Paths


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(content)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class Store:
    def __init__(self, paths: Paths):
        self.paths = paths

    def load(self) -> Config:
        try:
            config = Config.from_dict(json.loads(self.paths.config_file.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return Config()
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"Invalid ALSAChain configuration: {error}") from error
        self.assert_controls_isolation(config.profiles)
        return config

    def save(self, config: Config) -> None:
        self.assert_controls_isolation(config.profiles)
        atomic_write(self.paths.config_file, json.dumps(config.to_dict(), indent=2) + "\n")

    def assert_controls_path(self, controls: str) -> None:
        candidate = Path(controls)
        try:
            candidate.resolve().relative_to(self.paths.controls_dir.resolve())
        except ValueError as error:
            raise ValueError("Controls file must stay in the managed controls directory") from error
        if candidate.is_symlink():
            raise ValueError("Controls file cannot be a symlink")

    def assert_controls_isolation(self, profiles: list[Profile]) -> None:
        identities: set[tuple[int, int]] = set()
        for profile in profiles:
            profile.validate()
            for stage in profile.stages:
                if stage.type != "equalizer":
                    continue
                self.assert_controls_path(stage.controls_path or "")
                try:
                    info = Path(stage.controls_path or "").stat()
                except FileNotFoundError:
                    continue
                identity = (info.st_dev, info.st_ino)
                if identity in identities:
                    raise ValueError("Profiles must not share hard-linked controls files")
                identities.add(identity)

    def delete_controls_file(self, controls: str) -> None:
        self.assert_controls_path(controls)
        Path(controls).unlink(missing_ok=True)

    def apply_asoundrc(self, config: Config, caps_path: str, crossfeed_path: str, validate: callable) -> None:
        self.assert_controls_isolation(config.profiles)
        self.paths.controls_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.paths.playback_status_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self.paths.asoundrc.resolve() if self.paths.asoundrc.is_symlink() else self.paths.asoundrc
        original = target.read_text(encoding="utf-8") if target.exists() else ""
        self.paths.backups_dir.mkdir(parents=True, exist_ok=True)
        backup = self.paths.backups_dir / f"{uuid4()}.asoundrc"
        atomic_write(backup, original)
        try:
            block = render_block(config.profiles, caps_path, crossfeed_path, self.paths.playback_status_dir)
            atomic_write(target, replace_managed_block(original, block))
            if not validate():
                raise ValueError("Generated ALSA configuration did not validate")
            self.prune_backups()
        except BaseException:
            atomic_write(target, original)
            raise

    def list_backups(self) -> list[Path]:
        return sorted(self.paths.backups_dir.glob("*.asoundrc"), reverse=True) if self.paths.backups_dir.exists() else []

    def prune_backups(self) -> None:
        for backup in self.list_backups()[10:]:
            backup.unlink(missing_ok=True)
