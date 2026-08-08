from pathlib import Path

from alsachainqt.models import Config, Profile, Stage
from alsachainqt.paths import get_paths
from alsachainqt.store import Store


def test_store_round_trips_alsachain_config(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path / "config"), "XDG_STATE_HOME": str(tmp_path / "state")})
    store = Store(paths)
    profile = Profile("dac", "DAC", "dac", "plughw:CARD=USB,DEV=0", 2, True, True)

    store.save(Config([profile]))

    loaded = store.load()
    assert loaded.profiles[0].to_dict() == profile.to_dict()


def test_controls_cannot_escape_managed_directory(tmp_path: Path) -> None:
    paths = get_paths({"HOME": str(tmp_path), "XDG_CONFIG_HOME": str(tmp_path / "config"), "XDG_STATE_HOME": str(tmp_path / "state")})
    store = Store(paths)
    profile = Profile("dac", "DAC", "dac", "plughw:CARD=USB,DEV=0", 2, True, False, [Stage("eq", "equalizer", "dac", str(tmp_path / "outside.bin"))])

    try:
        store.save(Config([profile]))
    except ValueError as error:
        assert "managed controls directory" in str(error)
    else:
        raise AssertionError("Expected controls path validation to fail")


def test_custom_crossfeed_settings_load_from_config() -> None:
    stage = Stage.from_dict({"id": "crossfeed", "type": "crossfeed", "settings": {"cutoff": 700, "feed": 6}})

    assert stage.settings == {"cutoff": 700, "feed": 6}
