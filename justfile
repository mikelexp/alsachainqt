python := '.venv/bin/python'
scripts := 'scripts'

default:
    @just --list

help:
    @just --list

run: _ensure-python
    {{python}} -m alsachainqt

test: _ensure-python
    QT_QPA_PLATFORM=offscreen {{python}} -m pytest

check: _ensure-python
    make check

install-deps:
    bash {{scripts}}/install-build-deps.sh

build-standalone: _ensure-python
    make build-standalone

build-onefile: _ensure-python
    make build-onefile

clean:
    make clean

clean-build:
    bash {{scripts}}/clean-build.sh

install:
    bash {{scripts}}/install.sh

uninstall:
    bash {{scripts}}/uninstall.sh

uninstall-purge:
    bash {{scripts}}/uninstall.sh

build-native:
    make build-native

install-native:
    make install-native

version: _ensure-python
    {{python}} {{scripts}}/version.py

set-version VERSION: _ensure-python
    {{python}} {{scripts}}/set-version.py "{{VERSION}}"

aur-update:
    bash {{scripts}}/aur-update.sh

_ensure-python:
    @if [ ! -x '{{python}}' ]; then just install-deps; fi
