import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QSettings, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar,
    QFileDialog, QToolButton, QSplitter, QLineEdit,
)

from . import config
from .worker import Worker

log = logging.getLogger("transcriber")

PATH_ROLE = Qt.UserRole
TEXT_ROLE = Qt.UserRole + 1
ERROR_ROLE = Qt.UserRole + 2

# key -> (label, hex color or None for the default text color)
STATUS = {
    "pending": ("Queued", None),
    "active": ("Processing…", None),
    "done": ("Done", "#2e9e44"),
    "error": ("Error", "#d13438"),
    "cancelled": ("Cancelled", "#8a8a8a"),
}

MEDIA_FILTER = (
    "Audio/Video (*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v "
    "*.mp3 *.wav *.m4a *.flac *.ogg *.opus *.aac *.wma);;All files (*)"
)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")


def _section(text):
    label = QLabel(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label


class MainWindow(QWidget):
    def __init__(self, log_bridge=None):
        super().__init__()
        self.setWindowTitle("Transcriber")
        self.resize(960, 660)
        self.setAcceptDrops(True)

        self.settings = QSettings(config.ORG, config.APP)
        self.thread = None
        self.worker = None
        self._job_rows = []

        self._type_queue = []
        self._type_timer = QTimer(self)
        self._type_timer.setInterval(16)
        self._type_timer.timeout.connect(self._type_tick)

        self._build_ui()
        self._restore_settings()
        if log_bridge:
            log_bridge.message.connect(self._on_log)

    # ---------- build ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        title = QLabel("Transcriber")
        tf = title.font()
        tf.setPointSize(max(20, tf.pointSize() + 9))
        tf.setBold(True)
        title.setFont(tf)
        subtitle = QLabel("Turn audio and video into text, on your own machine")
        subtitle.setStyleSheet("color: palette(mid);")
        header = QVBoxLayout()
        header.setSpacing(1)
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        files = QVBoxLayout()
        files.setSpacing(8)
        files.addWidget(_section("Files"))
        bar = QHBoxLayout()
        self.add_btn = QPushButton("Add…")
        self.add_btn.clicked.connect(self._add_files)
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_selected)
        bar.addWidget(self.add_btn)
        bar.addWidget(self.remove_btn)
        bar.addStretch(1)
        files.addLayout(bar)
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.itemClicked.connect(self._on_item_clicked)
        files.addWidget(self.list, 1)
        left = QWidget()
        left.setLayout(files)

        out = QVBoxLayout()
        out.setSpacing(8)
        out.addWidget(_section("Live output"))
        self.viewer = QPlainTextEdit()
        self.viewer.setReadOnly(True)
        vf = self.viewer.font()
        vf.setPointSize(vf.pointSize() + 1)
        self.viewer.setFont(vf)
        out.addWidget(self.viewer, 1)
        right = QWidget()
        right.setLayout(out)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([380, 540])
        root.addWidget(splitter, 1)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(QLabel("Model"))
        self.model_box = QComboBox()
        self.model_box.addItems(config.MODELS)
        controls.addWidget(self.model_box)
        controls.addSpacing(14)
        controls.addWidget(QLabel("Language"))
        self.lang_box = QComboBox()
        self.lang_box.addItems([label for label, _ in config.LANGUAGES])
        controls.addWidget(self.lang_box)
        controls.addStretch(1)
        self.ts_check = QCheckBox("Timestamps")
        controls.addWidget(self.ts_check)
        root.addLayout(controls)

        # output folder
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Save to"))
        self.out_edit = QLineEdit()
        self.out_edit.setReadOnly(True)
        out_row.addWidget(self.out_edit, 1)
        self.out_btn = QPushButton("Choose…")
        self.out_btn.clicked.connect(self._choose_output)
        out_row.addWidget(self.out_btn)
        root.addLayout(out_row)

        # optional compact Markdown copy
        md_row = QHBoxLayout()
        self.md_check = QCheckBox("Also save a compact Markdown copy")
        self.md_check.setToolTip(
            "A clean copy without timestamps and trimmed filler words.\n"
            "Point it at a note app folder (e.g. an Obsidian vault) or feed it to an LLM."
        )
        self.md_check.toggled.connect(self._toggle_md)
        md_row.addWidget(self.md_check)
        self.md_edit = QLineEdit()
        self.md_edit.setReadOnly(True)
        self.md_edit.setPlaceholderText("Folder for the Markdown copy")
        md_row.addWidget(self.md_edit, 1)
        self.md_btn = QPushButton("Choose…")
        self.md_btn.clicked.connect(self._choose_md)
        md_row.addWidget(self.md_btn)
        root.addLayout(md_row)

        prog = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: palette(mid);")
        prog.addWidget(self.progress, 1)
        prog.addWidget(self.status)
        root.addLayout(prog)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setEnabled(False)
        self.run_btn = QPushButton("Transcribe")
        self.run_btn.clicked.connect(self._start)
        self.run_btn.setStyleSheet(
            "QPushButton { background: palette(highlight); color: palette(highlighted-text);"
            " border: none; border-radius: 4px; padding: 7px 18px; font-weight: bold; }"
            "QPushButton:disabled { background: palette(button); color: palette(mid); }"
        )
        actions.addWidget(self.cancel_btn)
        actions.addWidget(self.run_btn)
        root.addLayout(actions)

        self.log_toggle = QToolButton()
        self.log_toggle.setText("▸ Log")
        self.log_toggle.setAutoRaise(True)
        self.log_toggle.setCheckable(True)
        self.log_toggle.clicked.connect(self._toggle_log)
        root.addWidget(self.log_toggle, 0, Qt.AlignLeft)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        self.log_view.hide()
        root.addWidget(self.log_view)

    # ---------- files ----------

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select audio or video", str(Path.home()), MEDIA_FILTER
        )
        for path in paths:
            self._add_item(path)

    def _add_item(self, path):
        item = QListWidgetItem()
        item.setData(PATH_ROLE, path)
        self.list.addItem(item)
        self._set_state(self.list.count() - 1, "pending")

    def _remove_selected(self):
        if self._running():
            return
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self._add_item(url.toLocalFile())

    def _on_item_clicked(self, item):
        error = item.data(ERROR_ROLE)
        text = item.data(TEXT_ROLE)
        if not error and not text:
            return
        self._stop_typewriter()
        if error:
            self.viewer.setPlainText(f"Error on {Path(item.data(PATH_ROLE)).name}\n\n{error}")
        else:
            self.viewer.setPlainText(text)

    # ---------- output folders ----------

    def _choose_output(self):
        start = self.out_edit.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", start)
        if folder:
            self.out_edit.setText(folder)

    def _choose_md(self):
        start = self.md_edit.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Choose Markdown folder", start)
        if folder:
            self.md_edit.setText(folder)

    def _toggle_md(self, checked):
        self.md_edit.setEnabled(checked)
        self.md_btn.setEnabled(checked)

    # ---------- typewriter ----------

    def _type_enqueue(self, text):
        self._type_queue.append(text + "\n")
        if not self._type_timer.isActive():
            self._type_timer.start()

    def _type_tick(self):
        if not self._type_queue:
            self._type_timer.stop()
            return
        backlog = sum(len(t) for t in self._type_queue)
        step = min(60, max(1, backlog // 50))
        chunk = self._type_queue[0]
        self.viewer.insertPlainText(chunk[:step])
        self.viewer.ensureCursorVisible()
        if chunk[step:]:
            self._type_queue[0] = chunk[step:]
        else:
            self._type_queue.pop(0)

    def _stop_typewriter(self):
        self._type_timer.stop()
        self._type_queue.clear()

    # ---------- transcription ----------

    def _start(self):
        if self._running():
            return
        if self.list.count() == 0:
            self.status.setText("Add at least one file")
            return

        output_dir = self.out_edit.text().strip() or config.DEFAULTS["output_dir"]
        markdown_dir = ""
        if self.md_check.isChecked():
            markdown_dir = self.md_edit.text().strip()
            if not markdown_dir:
                self.status.setText("Pick a folder for the Markdown copy")
                return

        # only the rows without a saved transcript; finished ones are kept and skipped
        self._job_rows = self._pending_rows()
        if not self._job_rows:
            self.status.setText("No new files to transcribe")
            return
        todo = []
        for i in self._job_rows:
            item = self.list.item(i)
            item.setData(ERROR_ROLE, None)
            self._set_state(i, "pending")
            todo.append(item.data(PATH_ROLE))

        self._stop_typewriter()
        self.viewer.clear()

        lang = config.LANGUAGES[self.lang_box.currentIndex()][1]
        self.worker = Worker(
            todo, self.model_box.currentText(), lang,
            self.ts_check.isChecked(), output_dir, markdown_dir,
        )
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        self.worker.phase.connect(self.status.setText)
        self.worker.busy.connect(self._on_busy)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.status.connect(self.status.setText)
        self.worker.notice.connect(self._on_notice)
        self.worker.segment.connect(self._type_enqueue)
        self.worker.file_started.connect(lambda j: self._set_state(self._job_rows[j], "active"))
        self.worker.file_done.connect(self._on_file_done)
        self.worker.file_error.connect(self._on_file_error)
        self.worker.file_cancelled.connect(lambda j: self._set_state(self._job_rows[j], "cancelled"))
        self.worker.finished.connect(self._on_finished)

        self._set_running(True)
        self.thread.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
            self.status.setText("Cancelling…")

    def _on_busy(self, busy):
        self.progress.setRange(0, 0) if busy else self.progress.setRange(0, 100)

    def _on_notice(self, text):
        self.viewer.appendPlainText(f"⚠  {text}\n")

    def _on_file_done(self, job, transcript, paths):
        row = self._job_rows[job]
        item = self.list.item(row)
        if item:
            item.setData(TEXT_ROLE, transcript)
            self._set_state(row, "done")

    def _on_file_error(self, job, message):
        row = self._job_rows[job]
        item = self.list.item(row)
        if item:
            item.setData(ERROR_ROLE, message)
            self._set_state(row, "error")

    def _on_finished(self):
        self.thread.quit()
        self.thread.wait()
        self.worker = None
        self.thread = None
        self._set_running(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status.setText("Ready")

    def _on_log(self, level, text):
        self.log_view.appendPlainText(f"{level:<5} {text}")

    def _toggle_log(self):
        shown = self.log_toggle.isChecked()
        self.log_view.setVisible(shown)
        self.log_toggle.setText(("▾ " if shown else "▸ ") + "Log")

    # ---------- state ----------

    def _set_state(self, index, key):
        item = self.list.item(index)
        if not item:
            return
        label, color = STATUS[key]
        item.setText(f"{Path(item.data(PATH_ROLE)).name}    —    {label}")
        if key == "active":
            item.setForeground(self.palette().highlight().color())
        elif color:
            item.setForeground(QColor(color))
        else:
            item.setForeground(self.palette().text().color())

    def _set_running(self, running):
        for widget in (self.add_btn, self.remove_btn, self.run_btn, self.model_box,
                       self.lang_box, self.ts_check, self.out_btn, self.md_check):
            widget.setEnabled(not running)
        self.md_btn.setEnabled(not running and self.md_check.isChecked())
        self.cancel_btn.setEnabled(running)

    def _pending_rows(self):
        # rows without a saved transcript: what is left to do (includes failures)
        return [i for i in range(self.list.count()) if not self.list.item(i).data(TEXT_ROLE)]

    def _running(self):
        return self.thread is not None

    # ---------- settings ----------

    def _restore_settings(self):
        s = self.settings
        model = s.value("model", config.DEFAULTS["model"])
        if model in config.MODELS:
            self.model_box.setCurrentText(model)
        labels = [label for label, _ in config.LANGUAGES]
        lang = s.value("language", config.DEFAULTS["language"])
        if lang in labels:
            self.lang_box.setCurrentIndex(labels.index(lang))
        self.ts_check.setChecked(_as_bool(s.value("timestamps", config.DEFAULTS["timestamps"])))
        self.out_edit.setText(s.value("output_dir", config.DEFAULTS["output_dir"]))
        self.md_edit.setText(s.value("markdown_dir", config.DEFAULTS["markdown_dir"]))
        save_md = _as_bool(s.value("save_markdown", config.DEFAULTS["save_markdown"]))
        self.md_check.setChecked(save_md)
        self._toggle_md(save_md)

    def _save_settings(self):
        s = self.settings
        s.setValue("model", self.model_box.currentText())
        s.setValue("language", self.lang_box.currentText())
        s.setValue("timestamps", self.ts_check.isChecked())
        s.setValue("output_dir", self.out_edit.text())
        s.setValue("save_markdown", self.md_check.isChecked())
        s.setValue("markdown_dir", self.md_edit.text())

    def closeEvent(self, event):
        self._save_settings()
        if self.thread:
            self.worker.cancel()
            self.thread.quit()
            self.thread.wait(3000)
        super().closeEvent(event)
