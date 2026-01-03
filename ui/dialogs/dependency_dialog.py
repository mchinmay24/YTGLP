import subprocess

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QLineEdit,
    QApplication,
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
        self.resize(480, 240)

        # -------------------------
        # Determine install command
        # -------------------------
        if is_windows():
            self.install_command = (
                "winget install yt-dlp && winget install ffmpeg"
            )
        else:
            pm, cmd = detect_package_manager()
            if cmd:
                self.install_command = cmd
            else:
                self.install_command = "Install yt-dlp and ffmpeg manually"

        # -------------------------
        # UI Layout
        # -------------------------
        layout = QVBoxLayout(self)

        info_label = QLabel(
            "YTGLP requires the following tools to be installed:\n\n"
            + "\n".join(f"• {tool}" for tool in missing)
        )
        layout.addWidget(info_label)

        command_label = QLabel("The following command will be executed:")
        layout.addWidget(command_label)

        self.command_box = QLineEdit(self.install_command)
        self.command_box.setReadOnly(True)
        self.command_box.setCursorPosition(0)
        layout.addWidget(self.command_box)

        note_label = QLabel(
            "After installation completes, restart this app."
        )
        layout.addWidget(note_label)

        # -------------------------
        # Buttons
        # -------------------------
        self.copy_btn = QPushButton("Copy to Clipboard and Exit")
        self.install_btn = QPushButton(
            "Install with winget and Exit" if is_windows() else "Install and Exit"
        )
        self.exit_btn = QPushButton("Exit")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.install_btn)
        btn_row.addWidget(self.exit_btn)

        layout.addLayout(btn_row)

        # -------------------------
        # Signals
        # -------------------------
        self.copy_btn.clicked.connect(self.copy_command)
        self.install_btn.clicked.connect(self.install)
        self.exit_btn.clicked.connect(self.reject)

    # -------------------------
    # Actions
    # -------------------------
    def copy_command(self):
        QApplication.clipboard().setText(self.install_command)
        self.accept()

    def install(self):
        if is_windows():
            subprocess.Popen([
                "cmd.exe",
                "/k",
                self.install_command
            ])
        else:
            terminal, terminal_args = detect_terminal()
            if not terminal:
                return

            cmd = f"{self.install_command}; exec bash"
            subprocess.Popen(
                terminal_args + ["bash", "-c", cmd]
            )

        # Exit app after launching installer
        self.accept()
