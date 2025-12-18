from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
import re


class ClipboardWatcher(QThread):
    """Background thread that watches the system clipboard for URLs.

    Emits:
        url_detected(str): emitted when a new text value that looks like a URL
                           appears on the clipboard.
    """

    url_detected = pyqtSignal(str)

    def __init__(self, parent=None, interval_ms: int = 500):
        super().__init__(parent)
        self._running = True
        self._interval_ms = max(50, int(interval_ms))  # avoid too-small values

    def stop(self):
        """Ask the thread to stop and wait until it finishes."""
        self._running = False
        # wait() is safe to call from the GUI thread
        self.wait()

    def run(self):
        clipboard = QApplication.clipboard()
        last = ""
        while self._running:
            text = clipboard.text()
            if text != last and self._looks_like_url(text):
                self.url_detected.emit(text)
                last = text
            # Sleep a bit without blocking the interpreter like time.sleep
            self.msleep(self._interval_ms)

    def _looks_like_url(self, t: str) -> bool:
        if not t:
            return False
        return bool(re.match(r"https?://", t.strip()))
