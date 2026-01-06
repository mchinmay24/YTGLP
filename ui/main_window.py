import os
import re
from core.downloader import VideoDownloader
from core.metadata import MetadataFetcher
from core.clipboard_watcher import ClipboardWatcher
from functools import partial
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QDesktopServices
from PyQt5.QtWidgets import (
    QWidget,
    QMainWindow,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QProgressBar,
    QMessageBox,
    QFrame,
    QSpacerItem,
    QSizePolicy,
    QCheckBox,
    QListWidget,
    QDialog,
    QListWidgetItem,
    QGraphicsOpacityEffect,
)
from PyQt5.QtCore import (
    Qt,
    QThread,
    QObject,
    pyqtSignal,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QUrl,
)

class DownloadWorker(QObject):


    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    finished = pyqtSignal(str)  # url

    def __init__(
        self,
        downloader,
        url,
        fmt,
        res,
        out_folder,
        subs,
        trim,
        trim_start,
        trim_end,
        parent=None,
    ):
        super().__init__(parent)
        self.downloader = downloader
        self.url = url
        self.fmt = fmt
        self.res = res
        self.out_folder = out_folder
        self.subs = subs
        self.trim = trim
        self.trim_start = trim_start
        self.trim_end = trim_end

    def run(self):
        self.status_changed.emit("Downloading...")

        def progress_cb(val: int):
            self.progress_changed.emit(val)

        try:
            self.downloader.download(
                self.url,
                self.fmt,
                self.res,
                self.out_folder,
                progress_callback=progress_cb,
                download_subs=self.subs,
                trim=self.trim,
                trim_start=self.trim_start,
                trim_end=self.trim_end,
            )
        finally:
            self.finished.emit(self.url)


class QueueWorker(QObject):


    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    item_started = pyqtSignal(int, str)  # index, url
    item_finished = pyqtSignal(int, str)  # index, url
    queue_finished = pyqtSignal()

    def __init__(self, downloader, items, out_folder, parent=None):
        super().__init__(parent)
        self.downloader = downloader

        self.items = list(items)
        self.out_folder = out_folder

    def run(self):
        total_items = len(self.items)
        for idx, item in enumerate(self.items):
            url = item["url"]
            self.item_started.emit(idx, url)

            def progress_cb(val: int):
                self.progress_changed.emit(val)

            self.status_changed.emit(
                f"Downloading {idx + 1}/{total_items} in queue..."
            )

            try:
                self.downloader.download(
                    url,
                    item["format"],
                    item["resolution"],
                    self.out_folder,
                    progress_callback=progress_cb,
                    download_subs=item["subs"],
                    trim=item["trim"],
                    trim_start=item["trim_start"],
                    trim_end=item["trim_end"],
                )
            finally:
                self.item_finished.emit(idx, url)

        self.status_changed.emit("Queue finished.")
        self.queue_finished.emit()


class MainWindow(QMainWindow):

    def __init__(self, settings=None, app=None):
        super().__init__()
        self.setWindowTitle("YTGLP")
        self.resize(950, 620)

        self.app = app
        self.settings = settings if settings is not None else None
        
        self.fetcher = MetadataFetcher()
        self.downloader = VideoDownloader()

        self.is_fetching = False
        self.queue = []

        # Clipboard
        self.clipboard_watcher = ClipboardWatcher(parent=self)
        self.clipboard_watcher.url_detected.connect(self.on_clipboard_url)
        self.clipboard_watcher.start()


        self._dl_thread = None
        self._queue_thread = None

        # I hope this works
        self._queue_opacity_effect = None
        self._queue_anim = None

        # No one ever uses this anyway
        self.setAcceptDrops(True)

        self._init_ui()


    # ---------- UI SETUP ----------

    def _init_ui(self):
        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(1, 1, 1, 1)
        root_layout.setSpacing(10)


        # Left side: main controls
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        top_row = QHBoxLayout()
        title = QLabel("Youtube Video Downloader")
        title.setAlignment(Qt.AlignVCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        top_row.addWidget(title)
        top_row.addStretch()
        


        # URL row

        self.download_button = QPushButton("Download")
        self.download_button.setStyleSheet(
            "QPushButton { background-color: #4527a0 }"
        )
        self.download_button.clicked.connect(self.download_current)

        self.add_queue_btn = QPushButton("Add to Queue")
        self.add_queue_btn.clicked.connect(self.add_to_queue)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter or drop a YouTube video URL…")
        self.url_input.textChanged.connect(self.on_url_changed)

        paste_btn = QPushButton("Paste")
        paste_btn.clicked.connect(self.paste_from_clipboard)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_url)

        url_row.addSpacing(10)
        url_row.addWidget(self.download_button)
        url_row.addWidget(self.url_input, stretch=1)
        url_row.addWidget(self.add_queue_btn)
        url_row.addWidget(paste_btn)
        url_row.addWidget(clear_btn)
        left_layout.addLayout(url_row)
        url_row.addSpacing(10)


        # Row beneath URL: Download + Add to Queue
        actions_row = QHBoxLayout()

        fmt_label = QLabel("Format:")
        self.format_box = QComboBox()
        self.format_box.addItems(["mp4", "mp3", "webm", "wav"])

        res_label = QLabel("Resolution:")
        self.resolution_box = QComboBox()
        self.resolution_box.addItems(["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"])

        self.subs_checkbox = QCheckBox("Download subtitles (en)")

        self.trim_checkbox = QCheckBox("Trim")
        self.trim_start_edit = QLineEdit("00:00:00")
        self.trim_end_edit = QLineEdit("")
        self.trim_start_edit.setPlaceholderText("Start (hh:mm:ss)")
        self.trim_end_edit.setPlaceholderText("End (hh:mm:ss)")
        

        actions_row.addSpacing(10)
        actions_row.addWidget(fmt_label)
        actions_row.addWidget(self.format_box)
        actions_row.addWidget(res_label)
        actions_row.addWidget(self.resolution_box)
        actions_row.addWidget(self.subs_checkbox)
        actions_row.addWidget(self.trim_checkbox)
        actions_row.addWidget(QLabel("From:"))
        actions_row.addWidget(self.trim_start_edit)
        actions_row.addWidget(QLabel("To:"))
        actions_row.addWidget(self.trim_end_edit)
        
        left_layout.addLayout(actions_row)

        output_row = QHBoxLayout()
        out_folder = (
            self.settings.data["output_folder"]
            if self.settings is not None
            else os.getcwd()
        )
        self.output_label = QLabel(f"Output: {out_folder}")
        self.output_label.setStyleSheet("color: #ffffff;")
        self.output_label.setWordWrap(True)
        

        self.downloadFolder = QPushButton("Downloads")
        self.videoFolder = QPushButton("Videos")
        self.musicFolder = QPushButton("Music")
        self.desktopFolder = QPushButton("Desktop")
        self.output_button = QPushButton("Custom Folder…")
        
        self.output_button.clicked.connect(self.select_output)

        

        output_row.addWidget(self.output_label, stretch=1)
        output_row.addWidget(self.videoFolder)
        output_row.addWidget(self.musicFolder)
        output_row.addWidget(self.downloadFolder)
        output_row.addWidget(self.desktopFolder)
        output_row.addWidget(self.output_button)
        output_row.setSpacing(10)
        left_layout.addLayout(output_row)

        self.downloadFolder.clicked.connect(
            partial(self.set_output_to_system_folder, "downloads")
        )
        self.videoFolder.clicked.connect(
            partial(self.set_output_to_system_folder, "videos")
        )
        self.musicFolder.clicked.connect(
            partial(self.set_output_to_system_folder, "music")
        )
        self.desktopFolder.clicked.connect(
            partial(self.set_output_to_system_folder, "desktop")
        )



        # Preview card: thumbnail + metadata + options inside
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame { border: 1px solid #555; border-radius: 8px; padding: 8px; }"
        )
        card_layout = QHBoxLayout(card)
        card_layout.setSpacing(12)

        # Thumbnail
        self.thumbnail_label = QLabel("No preview")
        # self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setFixedSize(320, 180)
        self.thumbnail_label.setStyleSheet(
            "background-color: #222; color: #aaa;"
        )
        card_layout.addWidget(self.thumbnail_label)

        # Metadata + options
        meta_layout = QVBoxLayout()
        self.title_label = QLabel("Title: ")
        self.uploader_label = QLabel("Channel: ")
        self.duration_label = QLabel("Duration: ")

        for lbl in (self.title_label, self.uploader_label, self.duration_label):
            lbl.setStyleSheet("font-size: 14px;")

        meta_layout.addWidget(self.title_label)
        meta_layout.addWidget(self.uploader_label)
        meta_layout.addWidget(self.duration_label)

        meta_layout.addSpacing(8)
        
        meta_layout.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        card_layout.addLayout(meta_layout)
        left_layout.addWidget(card)

        # Trim options (before download)
        trim_row = QHBoxLayout()
        self.trim_checkbox = QCheckBox("Trim after download")
        self.trim_start_edit = QLineEdit("00:00:00")
        self.trim_end_edit = QLineEdit("")
        self.trim_start_edit.setPlaceholderText("Start (hh:mm:ss)")
        self.trim_end_edit.setPlaceholderText("End (hh:mm:ss)")

        trim_row.addWidget(self.trim_checkbox)
        trim_row.addWidget(QLabel("From:"))
        trim_row.addWidget(self.trim_start_edit)
        trim_row.addWidget(QLabel("To:"))
        trim_row.addWidget(self.trim_end_edit)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        left_layout.addWidget(self.progress)


        # Add left layout to root
        root_layout.addLayout(left_layout, stretch=3)


        # Right side: queue panel (hidden until used)
        self.queue_panel = QFrame()
        self.queue_panel.setFrameShape(QFrame.StyledPanel)
        self.queue_panel.setStyleSheet(
            "QFrame { border: 1px solid #555; border-radius: 8px; }"
        )
        queue_layout = QVBoxLayout(self.queue_panel)
        queue_layout.setContentsMargins(8, 8, 8, 8)
        queue_layout.setSpacing(6)

        queue_title = QLabel("Download Queue")
        queue_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        queue_layout.addWidget(queue_title)

        self.start_queue_btn = QPushButton("Start Queue")
        self.start_queue_btn.clicked.connect(self.start_queue)
        queue_layout.addWidget(self.start_queue_btn)

        self.queue_list = QListWidget()
        queue_layout.addWidget(self.queue_list)


        # Row for queue manipulation buttons
        queue_btn_row = QHBoxLayout()
        self.remove_queue_btn = QPushButton("Remove Selected")
        self.remove_queue_btn.clicked.connect(self.remove_selected_queue_item)
        self.clear_queue_btn = QPushButton("Clear Queue")
        self.clear_queue_btn.clicked.connect(self.clear_queue)

        queue_btn_row.addWidget(self.remove_queue_btn)
        queue_btn_row.addWidget(self.clear_queue_btn)
        queue_layout.addLayout(queue_btn_row)

        self.queue_panel.setVisible(False)
        root_layout.addWidget(self.queue_panel, stretch=2)

        container = QWidget()
        container.setLayout(root_layout)
        self.setCentralWidget(container)

        # Timer for debounced metadata fetching
        self.metadata_timer = QTimer(self)
        self.metadata_timer.setSingleShot(True)
        self.metadata_timer.timeout.connect(self.fetch_metadata)


    # ---------- HELPERS ----------

    def highlight_folder_button(self, active_btn):
        for btn in (
            self.downloadFolder,
            self.videoFolder,
            self.musicFolder,
            self.desktopFolder,
        ):
            btn.setStyleSheet("")

        active_btn.setStyleSheet("background-color: #5e35b1")


    def set_output_to_system_folder(self, folder_name):
        home = os.path.expanduser("~")

        folder_map = {
            "downloads": os.path.join(home, "Downloads"),
            "videos": os.path.join(home, "Videos"),
            "music": os.path.join(home, "Music"),
            "desktop": os.path.join(home, "Desktop"),
        }

        path = folder_map.get(folder_name.lower())
        if not path:
            return

        os.makedirs(path, exist_ok=True)

        self.settings.data["output_folder"] = path
        self.settings.save()
        self.output_label.setText(f"Output: {path}")


    def paste_from_clipboard(self):
        from PyQt5.QtWidgets import QApplication

        text = QApplication.clipboard().text()
        if text:
            self.url_input.setText(text)

    def clear_url(self):
        self.url_input.clear()
        self.thumbnail_label.setText("No preview")
        self.thumbnail_label.setPixmap(QPixmap())
        self.title_label.setText("Title:")
        self.uploader_label.setText("Channel Name:")
        self.duration_label.setText("Length:")

    def on_clipboard_url(self, url):
        if self.url_input.text().strip() == "":
            self.url_input.setText(url)

    def on_url_changed(self):
        url = self.url_input.text().strip()
        pattern = r"(youtube\.com|youtu\.be)"
        if re.search(pattern, url) and len(url) > 20:
            # debounce metadata fetching
            self.metadata_timer.start(500)
        else:
            self.metadata_timer.stop()

    def select_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            if self.settings is not None:
                self.settings.data["output_folder"] = folder
                self.settings.save()
            self.output_label.setText(f"Output: {folder}")

    def format_duration(self, seconds):
        try:
            seconds = int(seconds)
        except Exception:
            return "Unknown"

        if seconds <= 0:
            return "Unknown"

        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60

        parts = []
        if h > 0:
            parts.append(f"{h}h")
        if m > 0 or h > 0:
            parts.append(f"{m}m")
        parts.append(f"{s}s")
        return " ".join(parts)

    # ---------- METADATA / PREVIEW ----------

    def fetch_metadata(self):
        if self.is_fetching:
            return
        self.is_fetching = True

        url = self.url_input.text().strip()
        if not url:
            self.is_fetching = False
            return

        info = self.fetcher.get_raw_info(url)
        if not info:
            QMessageBox.warning(self, "Error", "Failed to fetch metadata.")
            self.is_fetching = False
            return

        self.title_label.setText(f"Title: {info.get('title', 'Unknown')}")
        self.uploader_label.setText(f"Channel : {info.get('uploader', 'Unknown')}")

        duration_sec = info.get("duration", 0)
        human = self.format_duration(duration_sec)
        self.duration_label.setText(f"Duration: {human}")

        thumb_url = info.get("thumbnail")
        thumb_path = "thumbnail.jpg"
        self.fetcher.download_thumbnail(thumb_url, out_path=thumb_path)
        if os.path.exists(thumb_path):
            pix = QPixmap(thumb_path)
            if not pix.isNull():
                self.thumbnail_label.setPixmap(
                    pix.scaled(
                        self.thumbnail_label.width(),
                        self.thumbnail_label.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            else:
                self.thumbnail_label.setText("No preview")
        else:
            self.thumbnail_label.setText("No preview")

        self.is_fetching = False

    # ---------- QUEUE UTILS ----------

    def _ensure_queue_panel_visible_with_animation(self):
        """Show the queue panel with a subtle fade-in animation."""
        if self.queue_panel.isVisible():
            return

        self.queue_panel.setVisible(True)
        # Grow the window horizontally a bit to make space for the queue
        # self.resize(self.width(), self.height())

        # Setup opacity effect for fade-in
        effect = QGraphicsOpacityEffect(self.queue_panel)
        self.queue_panel.setGraphicsEffect(effect)
        self._queue_opacity_effect = effect

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(250)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._queue_anim = anim
        anim.start()

    # ---------- QUEUE ----------

    def add_to_queue(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Enter a URL before adding to queue.")
            return

        item = {
            "url": url,
            "format": self.format_box.currentText(),
            "resolution": self.resolution_box.currentText(),
            "subs": self.subs_checkbox.isChecked(),
            "trim": self.trim_checkbox.isChecked(),
            "trim_start": self.trim_start_edit.text().strip(),
            "trim_end": self.trim_end_edit.text().strip(),
        }
        self.queue.append(item)

        # Update queue list UI
        display_text = f"{item['format']} {item['resolution']} | {url}"
        self.queue_list.addItem(display_text)

        # Show queue panel with animation on first use
        self._ensure_queue_panel_visible_with_animation()

    def remove_selected_queue_item(self):
        if not self.queue:
            return

        if self._queue_thread is not None:
            QMessageBox.information(
                self,
                "Queue",
                "Cannot remove items while the queue is running.",
            )
            return

        row = self.queue_list.currentRow()
        if row < 0 or row >= len(self.queue):
            return

        # Remove from internal list and UI list
        self.queue.pop(row)
        self.queue_list.takeItem(row)

    def clear_queue(self):
        if not self.queue:
            return

        if self._queue_thread is not None and self._queue_thread.isRunning():
            QMessageBox.information(
                self,
                "Queue",
                "Cannot clear the queue while it is running.",
            )
            return

        self.queue.clear()
        self.queue_list.clear()

    def start_queue(self):
        if not self.queue:
            QMessageBox.information(self, "Queue", "Queue is empty.")
            return

        if self._queue_thread is not None and self._queue_thread.isRunning():
            QMessageBox.information(self, "Queue", "Queue is already running.")
            return

        out_folder = (
            self.settings.data["output_folder"]
            if self.settings is not None
            else os.getcwd()
        )

        self.progress.setValue(0)

        self._queue_thread = QThread(self)
        self._queue_worker = QueueWorker(self.downloader, self.queue, out_folder)
        self._queue_worker.moveToThread(self._queue_thread)

        self._queue_thread.started.connect(self._queue_worker.run)
        self._queue_worker.progress_changed.connect(self.progress.setValue)
        self._queue_worker.status_changed.connect(self.statusBar().showMessage)

        def on_item_started(idx, url):
            self.queue_list.setCurrentRow(idx)

        self._queue_worker.item_started.connect(on_item_started)

        def on_queue_finished():
            # Clear queue and list
            self.queue.clear()
            self.queue_list.clear()
            self.statusBar().showMessage("Queue finished.", 5000)
            self._queue_thread.quit()
            self._queue_thread = None

        self._queue_worker.queue_finished.connect(on_queue_finished)

        self._queue_worker.queue_finished.connect(self._queue_worker.deleteLater)
        self._queue_thread.finished.connect(self._queue_thread.deleteLater)

        # Disable controls while queue runs
        self.start_queue_btn.setEnabled(False)
        self.download_button.setEnabled(False)
        self.add_queue_btn.setEnabled(False)
        self.remove_queue_btn.setEnabled(False)
        self.clear_queue_btn.setEnabled(False)

        def reenable():
            self.start_queue_btn.setEnabled(True)
            self.download_button.setEnabled(True)
            self.add_queue_btn.setEnabled(True)
            self.remove_queue_btn.setEnabled(True)
            self.clear_queue_btn.setEnabled(True)

        self._queue_thread.finished.connect(reenable)

        self._queue_thread.start()

    # ---------- DOWNLOAD SINGLE ----------

    def download_current(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL first.")
            return

        fmt = self.format_box.currentText()
        res = self.resolution_box.currentText()
        subs = self.subs_checkbox.isChecked()
        trim = self.trim_checkbox.isChecked()
        trim_start = self.trim_start_edit.text().strip()
        trim_end = self.trim_end_edit.text().strip()
        out_folder = (
            self.settings.data["output_folder"]
            if self.settings is not None
            else os.getcwd()
        )

        # Reset progress bar for new download
        self.progress.setValue(0)

        if self._dl_thread is not None:
            QMessageBox.information(
                self, "Download", "A download is already in progress."
            )
            return

        self._dl_thread = QThread(self)
        self._dl_worker = DownloadWorker(
            self.downloader,
            url,
            fmt,
            res,
            out_folder,
            subs,
            trim,
            trim_start,
            trim_end,
        )
        self._dl_worker.moveToThread(self._dl_thread)

        self._dl_thread.started.connect(self._dl_worker.run)
        self._dl_worker.progress_changed.connect(self.progress.setValue)
        self._dl_worker.status_changed.connect(self.statusBar().showMessage)

        def on_finished(finished_url: str):
            self.statusBar().showMessage("Download finished.", 5000)
            self._dl_thread.quit()
            self._dl_thread = None

        self._dl_worker.finished.connect(on_finished)
        self._dl_worker.finished.connect(self._dl_worker.deleteLater)
        self._dl_thread.finished.connect(self._dl_thread.deleteLater)

        # Disable download button while running
        self.download_button.setEnabled(False)

        def reenable():
            self.download_button.setEnabled(True)

        self._dl_thread.finished.connect(reenable)

        self._dl_thread.start()

    # ---------- CLEANUP ----------

    def closeEvent(self, event):
        # Stop clipboard watcher cleanly
        try:
            if (
                hasattr(self, "clipboard_watcher")
                and self.clipboard_watcher is not None
            ):
                self.clipboard_watcher.stop()
        except Exception:
            pass

        # Let base class handle the rest
        super().closeEvent(event)
