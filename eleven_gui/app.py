from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from eleven_gui.config import load_config
from eleven_gui.theme import apply_theme
from eleven_gui.ui.main_window import MainWindow


def run() -> int:
    config = load_config()

    app = QApplication(sys.argv)
    app.setApplicationName("Eleven GUI")
    app.setOrganizationName("Late Signal")
    apply_theme(app)

    icon_path = str(config.assets_dir / "app_icon.svg")
    app.setWindowIcon(QIcon(icon_path))

    window = MainWindow(config)
    window.show()
    return app.exec()
