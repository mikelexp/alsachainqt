PYTHON := .venv/bin/python
NATIVE_MODULE := build/libasound_module_pcm_alsachain_status.so

.PHONY: run test check build-native install-native clean

run:
	$(PYTHON) -m alsachainqt

test:
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest

check: build-native
	$(PYTHON) -m compileall -q src
	QT_QPA_PLATFORM=offscreen $(PYTHON) -m pytest
	QT_QPA_PLATFORM=offscreen $(PYTHON) -c 'import os; from alsachainqt.theme import configure_qt_theme; configure_qt_theme(); from PySide6.QtWidgets import QApplication; app=QApplication([]); print(os.environ.get("QT_QPA_PLATFORMTHEME")); print(os.environ.get("QT_STYLE_OVERRIDE")); print(os.environ.get("QT_PLUGIN_PATH")); print(app.style().objectName())'

build-native:
	$(MAKE) -C native

install-native: build-native
	sudo install -Dm755 $(NATIVE_MODULE) /usr/lib/alsa-lib/libasound_module_pcm_alsachain_status.so

clean:
	rm -rf build .pytest_cache
