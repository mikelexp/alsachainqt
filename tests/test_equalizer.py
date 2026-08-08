from types import SimpleNamespace

from alsachainqt.equalizer import EqualizerBand, flat_value, slider_to_value, value_to_slider
from alsachainqt.models import Profile
from alsachainqt.service import ALSAChainService


def test_equalizer_slider_centers_zero_db_without_changing_control_range() -> None:
    band = EqualizerBand("63Hz", "63 Hz", 0, 72, 49)

    assert value_to_slider(band, 49) == 0
    assert slider_to_value(band, -49) == 0
    assert slider_to_value(band, 0) == 49
    assert slider_to_value(band, 48) == 72


def test_new_equalizer_bands_are_initialized_at_zero_db(tmp_path) -> None:
    service = object.__new__(ALSAChainService)
    service.paths = SimpleNamespace(controls_dir=tmp_path)
    bands = [EqualizerBand("63Hz", "63 Hz", 0, 72, 12), EqualizerBand("125Hz", "125 Hz", 0, 72, 60)]
    saved = []
    service.update_stages = lambda profile, stages: setattr(profile, "stages", stages)
    service.equalizer_bands = lambda profile: bands
    service.set_equalizer_band = lambda profile, band, value: saved.append((band.control, value))
    profile = Profile("dac", "DAC", "dac", "plughw:CARD=USB,DEV=0", 2, True, False)

    service.add_stage(profile, "equalizer")

    assert saved == [(band.control, flat_value(band)) for band in bands]
