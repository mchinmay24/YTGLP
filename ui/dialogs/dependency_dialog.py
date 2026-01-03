# ui/dialogs/dependency_dialog.py
import subprocess
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from core.dependencies import (
    is_windows,
    detect_package_manager,
    detect_terminal,
)


class DependencyDialog(QDialog):
    def __init__(self, missing, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Missing Dependencies")
        self.setModal(True)
        self.resize(420, 200)

        layout = QVBoxLayout(self)

        label = QLabel(
            "YTGLP requires the following tools and you will have to restart it manually(This happens only once)\n\n"
            + "\n".join(f"• {m}" for m in missing)
        )
        layout.addWidget(label)

        self.install_btn = QPushButton("Install and Exit")
        self.exit_btn = QPushButton("Exit")

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(self.install_btn)
        btns.addWidget(self.exit_btn)

        layout.addLayout(btns)

        self.exit_btn.clicked.connect(self.reject)
        self.install_btn.clicked.connect(self.install)

        if is_windows():
            self.install_btn.setText("Install with winget")

    def install(self):
        if is_windows():
            self._install_windows()
        else:
            self._install_linux()

        self.accept()

    def _install_windows(self):
        subprocess.Popen([
            "cmd.exe",
            "/k",
            "winget install yt-dlp && winget install ffmpeg"
        ])

    def _install_linux(self):
        pm, install_cmd = detect_package_manager()
        terminal, terminal_args = detect_terminal()

        if not pm or not terminal:
            return

        cmd = f"{install_cmd}; exec bash"

        subprocess.Popen(
            terminal_args + ["bash", "-c", cmd]
        )
