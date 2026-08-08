# ALSAChainQT

ALSAChainQT is a standalone PySide6 desktop application for managing ALSAChain
virtual PCM profiles. It shares ALSAChain's XDG configuration, controls,
playback-status records, and managed `.asoundrc` block, but does not require
the ALSAChain executable or its JavaScript runtime.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m alsachainqt
.venv/bin/python -m pytest
make check
```

## Builds and releases

`make build-standalone` and `make build-onefile` compile a Nuitka build after
building the native ALSA module. The equivalent `just` commands are available.
`make install` installs a compiled app under `~/.local`; it intentionally does
not alter ALSA system paths or profile data. See [RELEASE.md](RELEASE.md) for
the GitHub Release and AUR publication flow.

The app owns only `~/.config/alsachain/`, `$XDG_STATE_HOME/alsachain/`, and the
`ALSACHAIN` marked block in `~/.asoundrc`.

## Native status plugin

The application includes the source for the `alsachain_status` ALSA PCM plugin.
Build it with `make build-native`; installing it under `/usr/lib/alsa-lib/`
requires `sudo make install-native`. The plugin is required only for per-profile
playback attribution, not to open the desktop application.
