from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .paths import get_paths
from .service import ALSAChainService
from .theme import configure_qt_theme, ensure_placeholder_text_contrast, ensure_runtime_style
from .ui import MainWindow

APP_ICON = Path(__file__).resolve().parents[2] / "icon.png"

APP_STYLESHEET = """
    QPushButton {
        color: palette(button-text);
        background: palette(button);
        border: 1px solid palette(mid);
        border-radius: 4px;
        padding: 6px 10px;
    }
    QPushButton:pressed { background: palette(midlight); }
    QPushButton:disabled { color: palette(placeholder-text); background: palette(window); border-color: palette(midlight); }
    QPushButton#secondaryButton:hover { background: palette(light); border-color: palette(highlight); }
    QDialogButtonBox QPushButton:hover { background: palette(light); border-color: palette(highlight); }
    QPushButton#primaryButton { color: white; background: #2563eb; border-color: #1d4ed8; }
    QPushButton#primaryButton:hover { background: #1d4ed8; border-color: #1e40af; }
    QPushButton#infoButton { color: white; background: #0f766e; border-color: #115e59; }
    QPushButton#infoButton:hover { background: #115e59; border-color: #134e4a; }
    QPushButton#dspButton { color: white; background: #7c3aed; border-color: #6d28d9; }
    QPushButton#dspButton:hover { background: #6d28d9; border-color: #5b21b6; }
    QPushButton#modeButton { color: white; background: #b45309; border-color: #92400e; }
    QPushButton#modeButton:hover { background: #92400e; border-color: #78350f; }
    QPushButton#dangerButton { color: white; background: #b42318; border-color: #8f1d14; }
    QPushButton#dangerButton:hover { background: #8f1d14; border-color: #751a12; }
        QLabel#applicationTitle { font-size: 20px; font-weight: 700; }
        QLabel#profileTitle { font-size: 20px; font-weight: 700; }
        QLabel#aboutName { font-size: 20px; font-weight: 700; }
        QFrame#profileCard { border: 1px solid palette(mid); border-radius: 4px; }
"""


def main() -> int:
    theme_mode = configure_qt_theme()
    QApplication.setApplicationName("ALSAChainQT")
    app = QApplication(sys.argv)
    app.setOrganizationName("ALSAChainQT")
    app.setWindowIcon(QIcon(str(APP_ICON)))
    app.setStyleSheet(APP_STYLESHEET)
    ensure_placeholder_text_contrast(app)
    runtime_style = ensure_runtime_style(app, theme_mode)
    print(f"Qt theme: {theme_mode}; platform={os.environ.get('QT_QPA_PLATFORMTHEME')}; style={os.environ.get('QT_STYLE_OVERRIDE')}; plugins={os.environ.get('QT_PLUGIN_PATH')}; runtime={runtime_style}")
    window = MainWindow(ALSAChainService(get_paths()))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
