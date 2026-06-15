import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .logsetup import setup_logging
from .main_window import MainWindow


def main():
    logger, bridge = setup_logging()

    # No custom stylesheet or forced font: inherit the system theme (native look).
    app = QApplication(sys.argv)
    app.setApplicationName("KDE Transcriber")

    icon = Path(__file__).resolve().parent.parent / "resources" / "kde-transcriber.svg"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    window = MainWindow(bridge)
    window.show()
    logger.info("KDE Transcriber started")
    sys.exit(app.exec())
