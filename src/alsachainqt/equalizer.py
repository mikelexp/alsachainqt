"""Discover Eq10 controls from amixer; no fixed band count is assumed."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class EqualizerBand:
    control: str
    label: str
    minimum: int
    maximum: int
    value: int


def parse_bands(output: str) -> list[EqualizerBand]:
    bands: list[EqualizerBand] = []
    for section in re.split(r"(?=^Simple mixer control )", output, flags=re.MULTILINE):
        control = re.search(r"^Simple mixer control '(.+)',\d+$", section, re.MULTILINE)
        limits = re.search(r"^\s+Limits: Playback (-?\d+) - (-?\d+)$", section, re.MULTILINE)
        values = re.findall(r"^\s+[^:]+: Playback (-?\d+) \[", section, re.MULTILINE)
        if not control or not limits or not values:
            continue
        bands.append(EqualizerBand(control.group(1), re.sub(r"^\d+\.\s*", "", control.group(1)), int(limits.group(1)), int(limits.group(2)), round(sum(map(int, values)) / len(values))))
    return bands


def flat_value(band: EqualizerBand) -> int:
    # Eq10's unity gain is control step 49 in its 0-72 scale.
    return round(band.minimum + (49 / 72) * (band.maximum - band.minimum))


def value_to_db(band: EqualizerBand, value: int) -> int:
    return value - flat_value(band)


def slider_limit(band: EqualizerBand) -> int:
    flat = flat_value(band)
    return max(flat - band.minimum, band.maximum - flat)


def value_to_slider(band: EqualizerBand, value: int) -> int:
    decibels = value_to_db(band, value)
    limit = slider_limit(band)
    if not decibels:
        return 0
    range_db = band.maximum - flat_value(band) if decibels > 0 else flat_value(band) - band.minimum
    return round(decibels * limit / range_db)


def slider_to_value(band: EqualizerBand, slider_value: int) -> int:
    limit = slider_limit(band)
    if not slider_value:
        return flat_value(band)
    range_db = band.maximum - flat_value(band) if slider_value > 0 else flat_value(band) - band.minimum
    decibels = round(slider_value * range_db / limit)
    return max(band.minimum, min(band.maximum, flat_value(band) + decibels))
