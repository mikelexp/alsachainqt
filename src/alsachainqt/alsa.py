"""ALSA discovery and the status-file protocol written by alsachain_status."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

from .runner import CommandRunner


@dataclass(frozen=True, slots=True)
class Device:
    card_id: str
    card_index: int
    card_name: str
    device: int
    description: str
    target: str


@dataclass(frozen=True, slots=True)
class PlaybackState:
    state: str = "Inactive"
    rate: str = ""
    format: str = ""
    channels: int | None = None


def parse_aplay_list(text: str) -> list[Device]:
    pattern = re.compile(r"^card (\d+): ([^ ]+) \[(.+?)\], device (\d+): (.+?) \[(.+?)\]$")
    devices: list[Device] = []
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        card_index, card_id, card_name, device, title, description = match.groups()
        devices.append(Device(card_id, int(card_index), card_name, int(device), f"{title} ({description})", f"plughw:CARD={card_id},DEV={device}"))
    return devices


def discover_devices(runner: CommandRunner) -> list[Device]:
    result = runner.run("aplay", ["-l"])
    return parse_aplay_list(result.stdout) if result.exit_code == 0 else []


def playback_status(path: Path) -> PlaybackState:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return PlaybackState()
    except OSError:
        return PlaybackState("Unavailable")
    pid_match = re.search(r"^pid:\s*(\d+)$", text, re.MULTILINE)
    if not pid_match:
        return PlaybackState("Unknown")
    try:
        os.kill(int(pid_match.group(1)), 0)
    except ProcessLookupError:
        path.unlink(missing_ok=True)
        return PlaybackState()
    except PermissionError:
        pass
    state = re.search(r"^state:\s*(\S+)$", text, re.MULTILINE)
    rate = re.search(r"^rate:\s*(.+)$", text, re.MULTILINE)
    sample_format = re.search(r"^format:\s*(.+)$", text, re.MULTILINE)
    channels = re.search(r"^channels:\s*(\d+)$", text, re.MULTILINE)
    return PlaybackState(
        state.group(1) if state and state.group(1) in {"Inactive", "Prepared", "Playing", "Paused", "XRUN"} else "Unknown",
        rate.group(1).strip() if rate else "",
        sample_format.group(1).strip() if sample_format else "",
        int(channels.group(1)) if channels else None,
    )
