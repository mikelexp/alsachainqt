"""XDG paths intentionally shared with ALSAChain."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Paths:
    home: Path
    config_dir: Path
    state_dir: Path
    config_file: Path
    controls_dir: Path
    playback_status_dir: Path
    backups_dir: Path
    asoundrc: Path


def get_paths(env: dict[str, str] | None = None) -> Paths:
    env = os.environ if env is None else env
    home = Path(env.get("HOME", str(Path.home())))
    config_home = Path(env.get("XDG_CONFIG_HOME", home / ".config"))
    state_home = Path(env.get("XDG_STATE_HOME", home / ".local" / "state"))
    config_dir = config_home / "alsachain"
    state_dir = state_home / "alsachain"
    return Paths(home, config_dir, state_dir, config_dir / "config.json", config_dir / "controls", state_dir / "playback", state_dir / "backups", home / ".asoundrc")
