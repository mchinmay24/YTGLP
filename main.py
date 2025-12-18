import sys
import os

from PyQt5.QtWidgets import QApplication

from ui.main_window import MainWindow
from core.settings import SettingsManager


def load_theme(app, settings):
    theme = settings.data.get("theme", "dark")
    qss_path = os.path.join("resources", "qss", f"{theme}.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())


def main():
    app = QApplication(sys.argv)
    settings = SettingsManager()
    load_theme(app, settings)
    window = MainWindow(settings=settings, app=app)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
