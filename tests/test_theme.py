import os

from alsachainqt.theme import configure_qt_theme


def test_theme_preserves_empty_user_overrides(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORMTHEME", "")
    monkeypatch.setenv("QT_STYLE_OVERRIDE", "")

    assert configure_qt_theme() == "user override"
    assert os.environ["QT_QPA_PLATFORMTHEME"] == ""
    assert os.environ["QT_STYLE_OVERRIDE"] == ""
