from pathlib import Path

from alsachainqt.asound import BEGIN_MARKER, END_MARKER, render_block, replace_managed_block
from alsachainqt.models import Profile, Stage


def profile() -> Profile:
    return Profile(
        "dac_eq", "USB DAC", "dac_eq", "plughw:CARD=USB_DAC,DEV=0", 2, True, False,
        [Stage("eq", "equalizer", "dac_eq", "/tmp/controls/dac_eq.bin"), Stage("gain", "gain", gain_db=-3)],
    )


def test_rendered_block_uses_public_pcm_status_wrapper_and_stage_order() -> None:
    rendered = render_block([profile()], "/usr/lib/ladspa/caps.so", "", Path("/tmp/playback"))

    assert "pcm.dac_eq_stage_01_eq" in rendered
    assert "pcm.dac_eq_stage_02_gain" in rendered
    assert rendered.index("stage_01_eq") < rendered.index("stage_02_gain")
    assert 'pcm.dac_eq_status {' in rendered
    assert 'slave.pcm "dac_eq_status"' in rendered
    assert BEGIN_MARKER in rendered and END_MARKER in rendered


def test_replace_managed_block_preserves_unmanaged_configuration() -> None:
    source = "pcm.other { type null }\n"
    result = replace_managed_block(source, "# BEGIN ALSACHAIN\n# END ALSACHAIN\n")

    assert result.startswith(source)
    assert "pcm.other" in result
