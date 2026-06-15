from pathlib import Path

ORG = "kde-transcriber"
APP = "KDE Transcriber"

HOME = Path.home()
DATA_DIR = HOME / ".local" / "share" / "kde-transcriber"
LOG_FILE = DATA_DIR / "kde-transcriber.log"

DEFAULT_OUTPUT = HOME / "Transcriptions"

MODELS = ["large-v3", "large-v3-turbo", "medium", "small"]
LANGUAGES = [("Automatic", None), ("English", "en"), ("Spanish", "es")]

DEFAULTS = {
    "model": "large-v3",
    "language": "Automatic",
    "timestamps": False,
    "output_dir": str(DEFAULT_OUTPUT),
    "save_markdown": False,
    "markdown_dir": "",
}
