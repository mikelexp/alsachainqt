"""Read-only diagnostics for ALSAChainQT's system dependencies."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

from .runner import CommandRunner


@dataclass(frozen=True, slots=True)
class Dependency:
    name: str
    purpose: str
    ok: bool
    detail: str = ""
    required: bool = True


@dataclass(frozen=True, slots=True)
class DependencyReport:
    dependencies: list[Dependency]
    caps_path: str = ""
    crossfeed_path: str = ""
    ladspa_path: str = ""


def check_dependencies(runner: CommandRunner, env: dict[str, str] | None = None) -> DependencyReport:
    env = os.environ if env is None else env
    ladspa_paths = [Path(item) for item in env.get("LADSPA_PATH", "").split(":") if item]
    default = Path("/usr/lib/ladspa")
    if default not in ladspa_paths:
        ladspa_paths.append(default)
    caps = next((path / "caps.so" for path in ladspa_paths if (path / "caps.so").is_file()), None)
    crossfeed = next((path / "bs2b.so" for path in ladspa_paths if (path / "bs2b.so").is_file()), None)
    alsa_dirs = [Path("/usr/lib/alsa-lib"), Path("/usr/lib64/alsa-lib"), Path("/usr/local/lib/alsa-lib")]
    equal = next((directory for directory in alsa_dirs if (directory / "libasound_module_pcm_equal.so").is_file() and (directory / "libasound_module_ctl_equal.so").is_file()), None)
    status = next((directory for directory in alsa_dirs if (directory / "libasound_module_pcm_alsachain_status.so").is_file()), None)
    return DependencyReport(
        [
            Dependency("aplay", "Discover playback hardware", shutil.which("aplay") is not None),
            Dependency("amixer", "Read and write equalizer controls", shutil.which("amixer") is not None),
            Dependency("alsaequal PCM/CTL modules", "Expose the equalizer PCM and CTL", equal is not None, str(equal or "Not found")),
            Dependency("ALSAChain status PCM module", "Track the active virtual PCM", status is not None, str(status or "Not installed")),
            Dependency("caps.so", "Provide CAPS Eq10 DSP", caps is not None, str(caps or "Not found")),
            Dependency("bs2b LADSPA crossfeed", "Optional headphone crossfeed", crossfeed is not None, str(crossfeed or "Optional"), False),
        ], str(caps or ""), str(crossfeed or ""), ":".join(map(str, ladspa_paths)),
    )
