"""Validated data model shared on disk with ALSAChain version 1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any, Literal

ALSA_NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
TARGET = re.compile(r"^plughw:CARD=[A-Za-z0-9_-]+,DEV=\d+$")
StageType = Literal["equalizer", "crossfeed", "gain"]


def timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def require_alsa_name(value: str, field_name: str = "name") -> str:
    if not ALSA_NAME.fullmatch(value):
        raise ValueError(f"{field_name} must use a safe ALSA identifier")
    return value


@dataclass(slots=True)
class Stage:
    id: str
    type: StageType
    ctl_name: str | None = None
    controls_path: str | None = None
    settings: str | dict[str, float] | None = None
    gain_db: float | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Stage":
        stage_type = value.get("type")
        if stage_type not in {"equalizer", "crossfeed", "gain"}:
            raise ValueError("Unsupported DSP stage")
        stage = cls(
            id=require_alsa_name(str(value.get("id", "")), "stage id"),
            type=stage_type,
            ctl_name=value.get("ctlName"),
            controls_path=value.get("controlsPath"),
            settings=value.get("settings"),
            gain_db=value.get("gainDb"),
        )
        if stage.type == "equalizer":
            require_alsa_name(str(stage.ctl_name or ""), "CTL name")
            if not isinstance(stage.controls_path, str) or not stage.controls_path:
                raise ValueError("Equalizer controls path is required")
        if stage.type == "crossfeed":
            if isinstance(stage.settings, str):
                if stage.settings not in {"gentle", "normal", "strong"}:
                    raise ValueError("Invalid crossfeed settings")
            else:
                if not isinstance(stage.settings, dict):
                    raise ValueError("Invalid crossfeed settings")
                cutoff, feed = stage.settings.get("cutoff"), stage.settings.get("feed")
                if not isinstance(cutoff, int) or not 300 <= cutoff <= 2000:
                    raise ValueError("Crossfeed cutoff must be 300 to 2000 Hz")
                if not isinstance(feed, (int, float)) or not 1 <= feed <= 15:
                    raise ValueError("Crossfeed feed must be 1 to 15 dB")
        if stage.type == "gain" and (not isinstance(stage.gain_db, (int, float)) or not -24 <= stage.gain_db <= 12):
            raise ValueError("Gain must be from -24 to +12 dB")
        return stage

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"id": self.id, "type": self.type}
        if self.type == "equalizer":
            value.update({"ctlName": self.ctl_name, "controlsPath": self.controls_path})
        elif self.type == "crossfeed":
            value["settings"] = self.settings
        else:
            value["gainDb"] = self.gain_db
        return value


@dataclass(slots=True)
class Profile:
    id: str
    display_name: str
    pcm_name: str
    target: str
    channels: int
    enabled: bool
    bitperfect: bool
    stages: list[Stage] = field(default_factory=list)
    eq_enabled: bool | None = None
    crossfeed: str | dict[str, float] | None = None
    ctl_name: str | None = None
    controls_path: str | None = None
    internal_pcm_name: str | None = None
    created_at: str = field(default_factory=timestamp)
    updated_at: str = field(default_factory=timestamp)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Profile":
        profile = cls(
            id=require_alsa_name(str(value.get("id", "")), "profile id"),
            display_name=str(value.get("displayName", "")).strip(),
            pcm_name=require_alsa_name(str(value.get("pcmName", "")), "PCM name"),
            target=str(value.get("target", "")),
            channels=value.get("channels"),
            enabled=value.get("enabled"),
            bitperfect=value.get("bitperfect"),
            stages=[Stage.from_dict(item) for item in value.get("stages", [])],
            eq_enabled=value.get("eqEnabled"),
            crossfeed=value.get("crossfeed"),
            ctl_name=value.get("ctlName"),
            controls_path=value.get("controlsPath"),
            internal_pcm_name=value.get("internalPcmName"),
            created_at=str(value.get("createdAt", "")),
            updated_at=str(value.get("updatedAt", "")),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        if not self.display_name or len(self.display_name) > 100:
            raise ValueError("Visible name must contain 1 to 100 characters")
        if not TARGET.fullmatch(self.target):
            raise ValueError("Target must be a stable plughw:CARD=...,DEV=... device")
        if not isinstance(self.channels, int) or not 1 <= self.channels <= 32:
            raise ValueError("Channels must be from 1 to 32")
        if not isinstance(self.enabled, bool) or not isinstance(self.bitperfect, bool):
            raise ValueError("Profile flags must be booleans")
        ids = [stage.id for stage in self.stages]
        types = [stage.type for stage in self.stages]
        if len(ids) != len(set(ids)) or len(types) != len(set(types)):
            raise ValueError("A profile may contain one stage of each type")
        if self.channels != 2 and "crossfeed" in types:
            raise ValueError("Crossfeed is available only for stereo profiles")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "id": self.id,
            "displayName": self.display_name,
            "pcmName": self.pcm_name,
            "target": self.target,
            "channels": self.channels,
            "enabled": self.enabled,
            "bitperfect": self.bitperfect,
            "stages": [stage.to_dict() for stage in self.stages],
            "eqEnabled": self.eq_enabled,
            "crossfeed": self.crossfeed,
            "ctlName": self.ctl_name,
            "controlsPath": self.controls_path,
            "internalPcmName": self.internal_pcm_name,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    def equalizer(self) -> Stage | None:
        return next((stage for stage in self.stages if stage.type == "equalizer"), None)


@dataclass(slots=True)
class Config:
    profiles: list[Profile] = field(default_factory=list)
    version: int = 1

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Config":
        if value.get("version") != 1 or not isinstance(value.get("profiles"), list):
            raise ValueError("Unsupported ALSAChain configuration")
        config = cls([Profile.from_dict(item) for item in value["profiles"]])
        config.validate()
        return config

    def validate(self) -> None:
        ids = [profile.id for profile in self.profiles]
        pcms = [profile.pcm_name for profile in self.profiles]
        ctls = [stage.ctl_name for profile in self.profiles for stage in profile.stages if stage.type == "equalizer"]
        controls = [str(Path(stage.controls_path or "").resolve()) for profile in self.profiles for stage in profile.stages if stage.type == "equalizer"]
        if len(ids) != len(set(ids)) or len(pcms) != len(set(pcms)) or len(ctls) != len(set(ctls)) or len(controls) != len(set(controls)):
            raise ValueError("Profile ALSA names or controls paths collide")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"version": 1, "profiles": [profile.to_dict() for profile in self.profiles]}
