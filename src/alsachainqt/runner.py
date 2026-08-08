"""Argument-only command runner; ALSA device data is never passed to a shell."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True, slots=True)
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int


class CommandRunner:
    def run(self, command: str, args: list[str] | None = None) -> CommandResult:
        try:
            result = subprocess.run([command, *(args or [])], capture_output=True, text=True, check=False, timeout=10)
        except FileNotFoundError:
            return CommandResult("", f"{command} not found", 127)
        except subprocess.TimeoutExpired:
            return CommandResult("", f"{command} timed out", 124)
        return CommandResult(result.stdout, result.stderr, result.returncode)
