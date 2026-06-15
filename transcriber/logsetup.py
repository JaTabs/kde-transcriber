import logging
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, Signal

from .config import LOG_FILE


class LogBridge(QObject):
    message = Signal(str, str)


class _QtHandler(logging.Handler):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def emit(self, record):
        self.bridge.message.emit(record.levelname, record.getMessage())


def setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("transcriber")
    logger.setLevel(logging.INFO)

    bridge = LogBridge()
    if logger.handlers:
        return logger, bridge

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)-5s  %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(file_handler)
    logger.addHandler(_QtHandler(bridge))
    return logger, bridge
