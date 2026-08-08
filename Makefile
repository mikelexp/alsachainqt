PYTHON := .venv/bin/python
NATIVE_MODULE := build/libasound_module_pcm_alsachain_status.so
SCRIPTS := scripts

.PHONY: help run test check install-deps build-standalone build-onefile clean clean-build install uninstall uninstall-purge build-native install-native version set-version aur-update verify-release-version

help:
	@echo "Targets:"
	@echo "  run                    Run the app from the virtual environment"
	@echo "  test                   Run the offscreen test suite"
	@echo "  check                  Compile, build the native module, and run tests"
	@echo "  install-deps           Create the virtual environment and install dev/build dependencies"
	@echo "  build-standalone       Build a Nuitka standalone distribution"
	@echo "  build-onefile          Build a Nuitka onefile binary"
	@echo "  clean-build            Remove Nuitka build artifacts"
	@echo "  install                Install a built app into ~/.local"
	@echo "  uninstall              Remove the ~/.local app installation"
	@echo "  uninstall-purge        Alias for uninstall; ALSAChain data is always retained"
	@echo "  build-native           Build the alsachain_status ALSA module"
	@echo "  install-native         Install the ALSA module system-wide (requires sudo)"
	@echo "  version                Print the project version"
	@echo "  set-version            Set the version (use VERSION=x.y.z)"
	@echo "  aur-update             Update and push the AUR package after a GitHub release"

run: $(PYTHON)
	$(PYTHON) -m alsachainqt

test: $(PYTHON)
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest

check: $(PYTHON) build-native
	$(PYTHON) -m compileall -q src
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest
	QT_QPA_PLATFORM=offscreen $(PYTHON) -c 'import os; from alsachainqt.theme import configure_qt_theme; configure_qt_theme(); from PySide6.QtWidgets import QApplication; app=QApplication([]); print(os.environ.get("QT_QPA_PLATFORMTHEME")); print(os.environ.get("QT_STYLE_OVERRIDE")); print(os.environ.get("QT_PLUGIN_PATH")); print(app.style().objectName())'

install-deps:
	@bash $(SCRIPTS)/install-build-deps.sh

build-standalone: $(PYTHON) build-native
	@bash $(SCRIPTS)/build-standalone.sh

build-onefile: $(PYTHON) build-native
	@bash $(SCRIPTS)/build-onefile.sh

build-native:
	$(MAKE) -C native

install-native: build-native
	sudo install -Dm755 $(NATIVE_MODULE) /usr/lib/alsa-lib/libasound_module_pcm_alsachain_status.so

clean:
	rm -rf build dist .pytest_cache

clean-build:
	@bash $(SCRIPTS)/clean-build.sh

install:
	@bash $(SCRIPTS)/install.sh

uninstall uninstall-purge:
	@bash $(SCRIPTS)/uninstall.sh

version:
	@$(PYTHON) $(SCRIPTS)/version.py

set-version:
	@test -n "$(VERSION)" || (echo "Usage: make set-version VERSION=x.y.z"; exit 1)
	@$(PYTHON) $(SCRIPTS)/set-version.py "$(VERSION)"

aur-update:
	@bash $(SCRIPTS)/aur-update.sh

verify-release-version:
	@test -n "$(TAG)" || (echo "Usage: make verify-release-version TAG=vx.y.z"; exit 1)
	@$(PYTHON) $(SCRIPTS)/verify-release-version.py "$(TAG)"

$(PYTHON):
	$(MAKE) install-deps
