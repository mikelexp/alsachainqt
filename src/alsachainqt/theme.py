"""Safe Qt/Plasma bootstrap executed before QApplication is constructed."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from PySide6.QtCore import QLibraryInfo, QSettings, qVersion
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

SYSTEM_PLUGIN_PATHS = (Path("/usr/lib/qt6/plugins"), Path("/usr/lib64/qt6/plugins"), Path("/usr/lib/x86_64-linux-gnu/qt6/plugins"))


def is_plasma_session() -> bool:
    session = " ".join(os.environ.get(key, "") for key in ("XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "DESKTOP_SESSION")).lower()
    return "kde" in session or "plasma" in session


def system_qt_matches() -> bool:
    for command in (("qtpaths6", "--qt-version"), ("qmake6", "-query", "QT_VERSION")):
        if not shutil.which(command[0]):
            continue
        try:
            version = subprocess.run(command, capture_output=True, text=True, timeout=1, check=False).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if version:
            return version.split(".")[:2] == qVersion().split(".")[:2]
    return False


def selected_plasma_style() -> str:
    settings_path = Path.home() / ".config" / "kdeglobals"
    if settings_path.is_file():
        value = QSettings(str(settings_path), QSettings.Format.IniFormat).value("KDE/widgetStyle", "", type=str).strip()
        if value:
            return value
    if not shutil.which("kreadconfig6"):
        return ""
    try:
        return subprocess.run(["kreadconfig6", "--group", "KDE", "--key", "widgetStyle"], capture_output=True, text=True, timeout=1, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def compatible_system_plugin_path(style: str) -> Path | None:
    if not system_qt_matches():
        return None
    for directory in SYSTEM_PLUGIN_PATHS:
        kde = directory / "platformthemes" / "KDEPlasmaPlatformTheme6.so"
        style_plugin = directory / "styles" / f"{style.lower()}6.so" if style else None
        if kde.is_file() or (style_plugin and style_plugin.is_file()):
            return directory
    return None


def configure_qt_theme() -> str:
    """Preserve user overrides, keeping bundled PySide plugins first."""
    bundled = str(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    user_plugins = [item for item in os.environ.get("QT_PLUGIN_PATH", "").split(os.pathsep) if item]
    platform_override = "QT_QPA_PLATFORMTHEME" in os.environ
    style_override = "QT_STYLE_OVERRIDE" in os.environ
    plasma = sys.platform.startswith("linux") and is_plasma_session()
    style = "" if style_override or not plasma else selected_plasma_style()
    system_path = compatible_system_plugin_path(style) if plasma else None
    paths = list(dict.fromkeys([bundled, *user_plugins, *([str(system_path)] if system_path else [])]))
    os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(paths)
    if plasma and not platform_override and system_path:
        os.environ["QT_QPA_PLATFORMTHEME"] = "kde"
    if plasma and not style_override and style and system_path and (system_path / "styles" / f"{style.lower()}6.so").is_file():
        os.environ["QT_STYLE_OVERRIDE"] = style
    if platform_override or style_override:
        return "user override"
    if os.environ.get("QT_QPA_PLATFORMTHEME") == "kde":
        return f"kde/{style}" if style else "kde"
    return "default"


def ensure_runtime_style(app: QApplication, theme_mode: str) -> str:
    runtime = app.style().objectName()
    requested = os.environ.get("QT_STYLE_OVERRIDE", "")
    if theme_mode.startswith("kde/") and requested and runtime.lower() in {"fusion", "windows"}:
        style = QStyleFactory.create(requested)
        if style is not None:
            app.setStyle(style)
            runtime = app.style().objectName()
    return runtime


def ensure_placeholder_text_contrast(app: QApplication) -> None:
    palette = app.palette()
    base = palette.color(QPalette.ColorRole.Base)
    placeholder = palette.color(QPalette.ColorRole.PlaceholderText)
    if contrast_ratio(base, placeholder) < 2.0:
        palette.setColor(QPalette.ColorRole.PlaceholderText, palette.color(QPalette.ColorRole.Disabled, QPalette.ColorRole.Text))
        app.setPalette(palette)


def contrast_ratio(first: QColor, second: QColor) -> float:
    def luminance(color: QColor) -> float:
        channels = [color.redF(), color.greenF(), color.blueF()]
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)
