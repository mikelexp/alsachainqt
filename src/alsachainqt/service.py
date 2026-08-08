"""Application operations, kept synchronous so GUI work can be dispatched safely."""

from __future__ import annotations

from pathlib import Path

from .alsa import Device, PlaybackState, discover_devices, playback_status
from .deps import DependencyReport, check_dependencies
from .equalizer import EqualizerBand, flat_value, parse_bands
from .models import Config, Profile, Stage, require_alsa_name, timestamp
from .paths import Paths
from .runner import CommandRunner
from .store import Store


class ALSAChainService:
    def __init__(self, paths: Paths, runner: CommandRunner | None = None):
        self.paths = paths
        self.runner = runner or CommandRunner()
        self.store = Store(paths)

    def list_profiles(self) -> list[Profile]:
        return self.store.load().profiles

    def devices(self) -> list[Device]:
        return discover_devices(self.runner)

    def diagnostics(self) -> DependencyReport:
        return check_dependencies(self.runner)

    def state(self, profile: Profile) -> PlaybackState:
        return playback_status(self.paths.playback_status_dir / f"{profile.id}.status")

    def apply_config(self, config: Config) -> None:
        report = self.diagnostics()
        stages = [stage for profile in config.profiles if profile.enabled and not profile.bitperfect for stage in profile.stages]
        if any(stage.type == "equalizer" for stage in stages) and not report.caps_path:
            raise ValueError("caps.so is unavailable")
        if any(stage.type == "crossfeed" for stage in stages) and not report.crossfeed_path:
            raise ValueError("bs2b LADSPA plugin is unavailable; install ladspa-bs2b first")
        self.store.apply_asoundrc(config, report.caps_path, report.crossfeed_path, lambda: self.validate_all(config))

    def validate_all(self, config: Config | None = None) -> bool:
        for profile in (config or self.store.load()).profiles:
            stage = profile.equalizer()
            if profile.enabled and not profile.bitperfect and stage:
                result = self.runner.run("amixer", ["-D", stage.ctl_name or "", "scontrols"])
                if result.exit_code != 0:
                    return False
        return True

    def save_profile(self, profile: Profile, previous_id: str | None = None) -> None:
        config = self.store.load()
        profile.updated_at = timestamp()
        profile.validate()
        matches = [item for item in config.profiles if item.id == profile.id and item.id != previous_id]
        if matches:
            raise ValueError(f"Identifier {profile.id} already exists")
        index = next((index for index, item in enumerate(config.profiles) if item.id == previous_id), -1)
        if index >= 0:
            config.profiles[index] = profile
        else:
            config.profiles.append(profile)
        self.apply_config(config)
        self.store.save(config)

    def create_profile(self, identifier: str, display_name: str, target: str) -> Profile:
        identifier = require_alsa_name(identifier, "Identifier")
        now = timestamp()
        return Profile(identifier, display_name.strip() or identifier, identifier, target, 2, True, True, [], False, None, identifier, str(self.paths.controls_dir / f"{identifier}.bin"), f"{identifier}_internal", now, now)

    def delete_profile(self, profile: Profile, delete_controls: bool) -> None:
        config = self.store.load()
        config.profiles = [item for item in config.profiles if item.id != profile.id]
        self.apply_config(config)
        self.store.save(config)
        if delete_controls:
            stage = profile.equalizer()
            if stage:
                self.store.delete_controls_file(stage.controls_path or "")

    def set_bitperfect(self, profile: Profile, enabled: bool) -> None:
        profile.bitperfect = enabled
        self.save_profile(profile, profile.id)

    def update_stages(self, profile: Profile, stages: list[Stage]) -> None:
        profile.stages = stages
        profile.bitperfect = False
        equalizer = profile.equalizer()
        profile.eq_enabled = equalizer is not None
        profile.ctl_name = equalizer.ctl_name if equalizer else None
        profile.controls_path = equalizer.controls_path if equalizer else None
        self.save_profile(profile, profile.id)

    def add_stage(self, profile: Profile, stage_type: str) -> None:
        if any(stage.type == stage_type for stage in profile.stages):
            raise ValueError("That DSP stage is already in this chain")
        if stage_type == "crossfeed" and profile.channels != 2:
            raise ValueError("Crossfeed is available only for stereo profiles")
        if stage_type == "equalizer":
            stage = Stage("eq", "equalizer", profile.id, str(self.paths.controls_dir / f"{profile.id}.bin"))
        elif stage_type == "crossfeed":
            stage = Stage("crossfeed", "crossfeed", settings="normal")
        else:
            stage = Stage("gain", "gain", gain_db=0)
        self.update_stages(profile, [*profile.stages, stage])
        if stage_type == "equalizer":
            for band in self.equalizer_bands(profile):
                self.set_equalizer_band(profile, band, flat_value(band))

    def move_stage(self, profile: Profile, index: int, direction: int) -> None:
        destination = index + direction
        if not 0 <= index < len(profile.stages) or not 0 <= destination < len(profile.stages):
            return
        stages = [*profile.stages]
        stages[index], stages[destination] = stages[destination], stages[index]
        self.update_stages(profile, stages)

    def equalizer_bands(self, profile: Profile) -> list[EqualizerBand]:
        stage = profile.equalizer()
        if not stage or profile.bitperfect:
            raise ValueError("EQ is unavailable while bit-perfect mode is active")
        result = self.runner.run("amixer", ["-D", stage.ctl_name or "", "scontents"])
        if result.exit_code:
            raise ValueError(result.stderr.strip() or "Unable to read equalizer controls")
        bands = parse_bands(result.stdout)
        if not bands:
            raise ValueError("The equalizer CTL exposes no bands")
        return bands

    def set_equalizer_band(self, profile: Profile, band: EqualizerBand, value: int) -> None:
        if not band.minimum <= value <= band.maximum:
            raise ValueError("Equalizer value is outside the reported range")
        stage = profile.equalizer()
        if not stage or profile.bitperfect:
            raise ValueError("EQ is unavailable while bit-perfect mode is active")
        result = self.runner.run("amixer", ["-D", stage.ctl_name or "", "sset", band.control, str(value)])
        if result.exit_code:
            raise ValueError(result.stderr.strip() or f"Unable to update {band.control}")
