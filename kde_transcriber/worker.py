import logging
import tempfile
from datetime import date
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from . import engine, media, output

log = logging.getLogger("kde_transcriber")


class Worker(QObject):
    phase = Signal(str)
    busy = Signal(bool)
    progress = Signal(int)
    status = Signal(str)
    notice = Signal(str)
    segment = Signal(str)
    file_started = Signal(int)
    file_done = Signal(int, str, list)
    file_error = Signal(int, str)
    file_cancelled = Signal(int)
    finished = Signal()

    def __init__(self, files, model_name, language, timestamps, output_dir, markdown_dir):
        super().__init__()
        self.files = files
        self.model_name = model_name
        self.language = language
        self.timestamps = timestamps
        self.output_dir = output_dir
        self.markdown_dir = markdown_dir
        self.model = None
        self._cancel = False

    def cancel(self):
        self._cancel = True

    @Slot()
    def run(self):
        try:
            self._run()
        except Exception as exc:
            log.error("Worker failure: %s", exc)
            self.notice.emit(f"Error: {exc}")
        finally:
            self.finished.emit()

    def _run(self):
        total = len(self.files)
        self.busy.emit(True)
        self.phase.emit("Loading model…")
        self.model, device, note = engine.load_model(self.model_name, on_status=self.phase.emit)
        if note:
            self.notice.emit(note)
        elif device == "cpu":
            self.notice.emit("No GPU detected — using CPU (slower).")

        for i, src in enumerate(self.files):
            if self._cancel:
                self.file_cancelled.emit(i)
                continue
            self.file_started.emit(i)
            self.status.emit(f"{Path(src).name}  ({i + 1}/{total})")
            try:
                self._process(i, src)
            except Exception as exc:
                log.error("Error on %s: %s", Path(src).name, exc)
                self.file_error.emit(i, str(exc))

    def _process(self, index, src):
        self.busy.emit(True)
        self.progress.emit(0)
        self.phase.emit("Preparing audio…")
        if not media.has_audio_stream(src):
            raise media.MediaError("The file has no audio track.")

        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "audio.wav"
            media.extract_audio(src, wav)

            self.busy.emit(False)
            self.phase.emit("Transcribing…")
            segments, info = engine.transcribe(self.model, wav, self.language)

            duration = info.duration or 0
            collected = []
            for seg in segments:
                if self._cancel:
                    self.file_cancelled.emit(index)
                    return
                text = seg.text.strip()
                collected.append((seg.start, seg.end, text))
                self.segment.emit(f"[{output.hms(seg.start)}] {text}" if self.timestamps else text)
                if duration:
                    self.progress.emit(min(100, int(seg.end / duration * 100)))

        meta = {
            "source": Path(src).name,
            "date": date.today().isoformat(),
            "duration": output.hms(duration),
            "model": self.model_name,
            "language": info.language or "?",
        }
        paths = output.write_results(
            collected, src, meta, self.timestamps, self.output_dir, self.markdown_dir
        )
        self.progress.emit(100)
        log.info("Done %s -> %s", Path(src).name, ", ".join(str(p) for p in paths))
        self.file_done.emit(index, output.raw_text(collected, self.timestamps), [str(p) for p in paths])
