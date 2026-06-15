from pathlib import Path

ORG = "transcriber"
APP = "Transcriber"

HOME = Path.home()
DATA_DIR = HOME / ".local" / "share" / "transcriber"
LOG_FILE = DATA_DIR / "transcriber.log"

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
